"""Tkinter desktop application for AppleCalls."""

from __future__ import annotations

from pathlib import Path
import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from applecalls import __version__
from applecalls.diagnostics import (
    DiagnosticReport,
    PhoneLinkInfo,
    build_fallback_report,
    collect_phone_link_info,
    collect_report,
)
from applecalls.i18n import get_text
from applecalls.logic import SupportEvaluation, evaluate_support, format_report
from applecalls.process_utils import merge_hidden_process_kwargs


MICROSOFT_PHONE_LINK_URL = (
    "https://support.microsoft.com/en-us/windows/apps/make-and-receive-phone-calls-from-your-pc"
)
APPLE_CONTINUITY_URL = "https://support.apple.com/en-us/102405"
PAYPAL_URL = "https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN"
PHONE_LINK_PRODUCT_ID = "9NMPJ99VJBWV"
PHONE_LINK_SHELL_TARGET = r"shell:AppsFolder\Microsoft.YourPhone_8wekyb3d8bbwe!App"
PHONE_LINK_STORE_TARGET = f"ms-windows-store://pdp/?ProductId={PHONE_LINK_PRODUCT_ID}"
PHONE_LINK_CALLS_TARGET = (
    "ms-phone:calling?startScenarioId=feature_calling&ref=AppleCalls&scenarioId=feature_calling"
)


class AppleCallsApp(tk.Tk):
    """Desktop UI that diagnoses the supported Windows+iPhone calling path."""

    def __init__(self) -> None:
        super().__init__()
        self.language = tk.StringVar(value="es")
        self.report_text = tk.StringVar()
        self.status_title = tk.StringVar()
        self.status_summary = tk.StringVar()
        self._diagnostic_queue: queue.Queue[tuple[int, DiagnosticReport, SupportEvaluation]] = queue.Queue()
        self._phone_link_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._diagnostic_request_id = 0
        self._phone_link_task_running = False
        self.latest_report: DiagnosticReport | None = None

        self.base_dir = Path(__file__).resolve().parent.parent
        self.icon_path = self.base_dir / "iphone_apple_mac_171.ico"

        self._configure_root()
        self._configure_styles()
        self._build_ui()
        self.after(120, self._poll_diagnostic_queue)
        self.after(160, self._poll_phone_link_queue)
        self.refresh_ui()

    def _configure_root(self) -> None:
        """Sets base window properties."""

        self.title("AppleCalls")
        self.geometry("1040x760")
        self.minsize(920, 680)
        self.configure(bg="#F3EFE8")

        if self.icon_path.exists():
            try:
                self.iconbitmap(default=str(self.icon_path))
            except tk.TclError:
                pass

    def _configure_styles(self) -> None:
        """Applies a restrained custom theme."""

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Main.TFrame", background="#F3EFE8")
        style.configure("Card.TFrame", background="#FFFDFC", relief="flat")
        style.configure("Header.TLabel", background="#F3EFE8", foreground="#1F2937")
        style.configure("Title.TLabel", background="#F3EFE8", foreground="#111827", font=("Segoe UI Semibold", 22))
        style.configure("Subtitle.TLabel", background="#F3EFE8", foreground="#4B5563", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe", background="#FFFDFC", foreground="#0F172A")
        style.configure("Section.TLabelframe.Label", background="#FFFDFC", foreground="#0F172A", font=("Segoe UI Semibold", 10))
        style.configure("Body.TLabel", background="#FFFDFC", foreground="#1F2937", font=("Segoe UI", 10))
        style.configure("StatusValue.TLabel", background="#FFFDFC", foreground="#0F172A", font=("Segoe UI Semibold", 18))
        style.configure("Summary.TLabel", background="#FFFDFC", foreground="#374151", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=9)
        style.map("Accent.TButton", background=[("active", "#155E75"), ("!disabled", "#0E7490")], foreground=[("!disabled", "#FFFFFF")])
        style.configure("TCombobox", padding=6)

    def _build_ui(self) -> None:
        """Creates the window layout."""

        root = ttk.Frame(self, style="Main.TFrame", padding=20)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, style="Main.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        # The header shows the app name and the current version that should
        # match the git tag and the generated executable name.
        self.title_var = tk.StringVar(value=f"AppleCalls {__version__}")
        ttk.Label(header, textvariable=self.title_var, style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.subtitle_label = ttk.Label(header, style="Subtitle.TLabel", wraplength=780, justify="left")
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        lang_box = ttk.Frame(header, style="Main.TFrame")
        lang_box.grid(row=0, column=1, rowspan=2, sticky="e")
        self.lang_label = ttk.Label(lang_box, style="Header.TLabel")
        self.lang_label.grid(row=0, column=0, padx=(0, 8))
        selector = ttk.Combobox(
            lang_box,
            textvariable=self.language,
            values=("es", "en"),
            width=8,
            state="readonly",
        )
        selector.grid(row=0, column=1)
        selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_ui())

        summary_frame = ttk.LabelFrame(root, style="Section.TLabelframe")
        summary_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        summary_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(summary_frame, style="Body.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        self.status_value = ttk.Label(summary_frame, textvariable=self.status_title, style="StatusValue.TLabel")
        self.status_value.grid(row=1, column=0, sticky="w", padx=16)
        self.summary_value = ttk.Label(
            summary_frame,
            textvariable=self.status_summary,
            style="Summary.TLabel",
            wraplength=560,
            justify="left",
        )
        self.summary_value.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 14))

        self.notes_label = ttk.Label(summary_frame, style="Body.TLabel")
        self.notes_label.grid(row=3, column=0, sticky="w", padx=16)
        self.notes_value = tk.Text(
            summary_frame,
            height=8,
            wrap="word",
            relief="flat",
            bg="#FFFDFC",
            fg="#1F2937",
            font=("Segoe UI", 10),
            padx=12,
            pady=10,
        )
        self.notes_value.grid(row=4, column=0, sticky="nsew", padx=16, pady=(6, 16))
        self.notes_value.configure(state="disabled")
        summary_frame.rowconfigure(4, weight=1)

        actions_frame = ttk.LabelFrame(root, style="Section.TLabelframe")
        actions_frame.grid(row=1, column=1, sticky="nsew", pady=(0, 10))
        actions_frame.columnconfigure(0, weight=1)

        self.refresh_button = ttk.Button(actions_frame, style="Accent.TButton", command=self.refresh_diagnostics)
        self.refresh_button.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        self.phone_link_button = ttk.Button(actions_frame, command=self.open_phone_link)
        self.phone_link_button.grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        self.phone_link_calls_button = ttk.Button(actions_frame, command=self.open_phone_link_calls)
        self.phone_link_calls_button.grid(row=2, column=0, sticky="ew", padx=16, pady=8)

        self.phone_link_install_button = ttk.Button(actions_frame, command=self.install_or_update_phone_link)
        self.phone_link_install_button.grid(row=3, column=0, sticky="ew", padx=16, pady=8)

        self.bluetooth_button = ttk.Button(actions_frame, command=lambda: self.open_uri("ms-settings:bluetooth"))
        self.bluetooth_button.grid(row=4, column=0, sticky="ew", padx=16, pady=8)

        self.ms_button = ttk.Button(actions_frame, command=lambda: webbrowser.open(MICROSOFT_PHONE_LINK_URL))
        self.ms_button.grid(row=5, column=0, sticky="ew", padx=16, pady=8)

        self.apple_button = ttk.Button(actions_frame, command=lambda: webbrowser.open(APPLE_CONTINUITY_URL))
        self.apple_button.grid(row=6, column=0, sticky="ew", padx=16, pady=8)

        self.copy_button = ttk.Button(actions_frame, command=self.copy_report)
        self.copy_button.grid(row=7, column=0, sticky="ew", padx=16, pady=8)

        self.donate_button = ttk.Button(actions_frame, command=lambda: webbrowser.open(PAYPAL_URL))
        self.donate_button.grid(row=8, column=0, sticky="ew", padx=16, pady=(8, 16))

        diagnostic_frame = ttk.LabelFrame(root, style="Section.TLabelframe")
        diagnostic_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        diagnostic_frame.columnconfigure(0, weight=1)
        diagnostic_frame.rowconfigure(0, weight=1)

        self.report_box = tk.Text(
            diagnostic_frame,
            height=16,
            wrap="word",
            relief="flat",
            bg="#FFFDFC",
            fg="#111827",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        self.report_box.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.report_box.configure(state="disabled")

        detail_frame = ttk.Frame(root, style="Card.TFrame")
        detail_frame.grid(row=2, column=1, sticky="nsew")
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        guide_frame = ttk.LabelFrame(detail_frame, style="Section.TLabelframe")
        guide_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        guide_frame.columnconfigure(0, weight=1)
        guide_frame.rowconfigure(0, weight=1)
        self.guide_label = tk.Text(
            guide_frame,
            height=9,
            wrap="word",
            relief="flat",
            bg="#FFFDFC",
            fg="#1F2937",
            font=("Segoe UI", 10),
            padx=12,
            pady=10,
        )
        self.guide_label.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.guide_label.configure(state="disabled")

        limitations_frame = ttk.LabelFrame(detail_frame, style="Section.TLabelframe")
        limitations_frame.grid(row=1, column=0, sticky="nsew")
        limitations_frame.columnconfigure(0, weight=1)
        limitations_frame.rowconfigure(0, weight=1)
        self.limitations_label = tk.Text(
            limitations_frame,
            height=9,
            wrap="word",
            relief="flat",
            bg="#FFFDFC",
            fg="#1F2937",
            font=("Segoe UI", 10),
            padx=12,
            pady=10,
        )
        self.limitations_label.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.limitations_label.configure(state="disabled")

        self.summary_frame = summary_frame
        self.actions_frame = actions_frame
        self.diagnostic_frame = diagnostic_frame
        self.guide_frame = guide_frame
        self.limitations_frame = limitations_frame

    def refresh_ui(self) -> None:
        """Refreshes labels and reruns diagnostics."""

        language = self.language.get()
        self.subtitle_label.configure(text=get_text(language, "app_subtitle"))
        self.lang_label.configure(text=get_text(language, "language"))
        self.status_label.configure(text=get_text(language, "status_label"))
        self.notes_label.configure(text=get_text(language, "notes_label"))
        self.summary_frame.configure(text=get_text(language, "status_label"))
        self.actions_frame.configure(text=get_text(language, "actions_panel"))
        self.diagnostic_frame.configure(text=get_text(language, "diagnostic_panel"))
        self.guide_frame.configure(text=get_text(language, "guide_panel"))
        self.limitations_frame.configure(text=get_text(language, "limitations_panel"))
        self.refresh_button.configure(text=get_text(language, "refresh"))
        self.phone_link_button.configure(text=get_text(language, "open_phone_link"))
        self.phone_link_calls_button.configure(text=get_text(language, "open_calls"))
        self.phone_link_install_button.configure(text=get_text(language, "install_phone_link"))
        self.bluetooth_button.configure(text=get_text(language, "open_bluetooth"))
        self.ms_button.configure(text=get_text(language, "open_ms_guide"))
        self.apple_button.configure(text=get_text(language, "open_apple_guide"))
        self.copy_button.configure(text=get_text(language, "copy_report"))
        self.donate_button.configure(text=get_text(language, "donate"))
        self._set_text_widget(self.guide_label, get_text(language, "guide_text"))
        self._set_text_widget(self.limitations_label, get_text(language, "limitations_text"))
        self.refresh_diagnostics()

    def refresh_diagnostics(self) -> None:
        """Executes the system checks on a worker thread.

        PowerShell and netsh can take a few seconds. Running them outside of the
        Tkinter main loop prevents the window from freezing during startup or
        when the user refreshes the report.
        """

        language = self.language.get()
        self._diagnostic_request_id += 1
        request_id = self._diagnostic_request_id

        self.refresh_button.configure(state="disabled")
        self.status_title.set(get_text(language, "status_loading"))
        self.status_summary.set(get_text(language, "summary_loading"))
        self._set_text_widget(self.notes_value, get_text(language, "loading_notes"))
        self._set_text_widget(self.report_box, get_text(language, "loading_report"))
        self._apply_status_color("partial")

        worker = threading.Thread(
            target=self._run_diagnostics_worker,
            args=(request_id,),
            daemon=True,
        )
        worker.start()

    def _run_diagnostics_worker(self, request_id: int) -> None:
        """Collects diagnostics and passes the result back to the UI queue."""

        try:
            report = collect_report()
        except Exception as exc:  # pragma: no cover - defensive GUI fallback
            report = build_fallback_report(str(exc))

        evaluation = evaluate_support(report)
        self._diagnostic_queue.put((request_id, report, evaluation))

    def _poll_diagnostic_queue(self) -> None:
        """Applies the latest worker result without touching Tkinter from threads."""

        try:
            while True:
                request_id, report, evaluation = self._diagnostic_queue.get_nowait()
                if request_id == self._diagnostic_request_id:
                    self._apply_diagnostics(report, evaluation)
        except queue.Empty:
            pass

        self.after(120, self._poll_diagnostic_queue)

    def _apply_diagnostics(self, report: DiagnosticReport, evaluation: SupportEvaluation) -> None:
        """Updates the UI from the latest completed diagnostic run."""

        language = self.language.get()
        self.refresh_button.configure(state="normal")
        self.latest_report = report
        self.status_title.set(get_text(language, evaluation.title_key))
        self.status_summary.set(get_text(language, evaluation.summary_key))

        notes = "\n\n".join(f"- {get_text(language, key)}" for key in evaluation.note_keys)
        self._set_text_widget(self.notes_value, notes)

        report_content = (
            f"{format_report(report)}\n\n"
            f"Application version: {__version__}\n"
            f"Suggested result: {get_text(language, evaluation.title_key)}"
        )
        self.report_text.set(report_content)
        self._set_text_widget(self.report_box, report_content)
        self._apply_status_color(evaluation.level)

    def _apply_status_color(self, level: str) -> None:
        """Changes the headline color based on the computed result."""

        colors = {
            "ready": "#0F766E",
            "partial": "#B45309",
            "blocked": "#B91C1C",
        }
        self.status_value.configure(foreground=colors.get(level, "#0F172A"))

    def _set_text_widget(self, widget: tk.Text, content: str) -> None:
        """Replaces the content of a read-only text widget."""

        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def copy_report(self) -> None:
        """Copies the last generated report to the clipboard."""

        self.clipboard_clear()
        self.clipboard_append(self.report_text.get())
        self.update_idletasks()
        messagebox.showinfo(
            get_text(self.language.get(), "copied_title"),
            get_text(self.language.get(), "copied_message"),
        )

    def open_phone_link(self) -> None:
        """Launches Phone Link if possible."""

        if self._open_phone_link_direct():
            return

        phone_link = self._get_current_phone_link_info(prefer_fresh=False)
        if phone_link.launch_uri and self.open_uri(phone_link.launch_uri):
            return

        if self.open_uri(PHONE_LINK_SHELL_TARGET):
            return

        self.install_or_update_phone_link()

    def open_phone_link_calls(self) -> None:
        """Launches Phone Link directly in the calls experience when available."""

        phone_link = self._get_current_phone_link_info(prefer_fresh=False)
        if phone_link.calls_uri and self.open_uri(phone_link.calls_uri):
            return

        phone_link = self._get_current_phone_link_info(prefer_fresh=True)
        if phone_link.calls_uri and self.open_uri(phone_link.calls_uri):
            return

        if self.open_uri(PHONE_LINK_CALLS_TARGET):
            return

        self.open_phone_link()

    def _open_phone_link_direct(self) -> bool:
        """Opens the installed Phone Link executable when available.

        The `ms-phone-link:` URI may resolve to a Store search instead of
        launching the app. Using the installed stub executable is more reliable
        on systems where the URI association is broken.
        """

        phone_link = self._get_current_phone_link_info(prefer_fresh=False)
        if phone_link.stub_executable and self.open_uri(phone_link.stub_executable):
            return True

        phone_link = self._get_current_phone_link_info(prefer_fresh=True)
        if phone_link.stub_executable and self.open_uri(phone_link.stub_executable):
            return True

        return False

    def _get_current_phone_link_info(self, *, prefer_fresh: bool) -> PhoneLinkInfo:
        """Returns Phone Link metadata, using a live lookup when requested."""

        if not prefer_fresh and self.latest_report is not None:
            return self.latest_report.phone_link
        return collect_phone_link_info()

    def install_or_update_phone_link(self) -> None:
        """Installs or updates Phone Link silently with winget."""

        if self._phone_link_task_running:
            messagebox.showinfo(
                get_text(self.language.get(), "install_title"),
                get_text(self.language.get(), "install_in_progress"),
            )
            return

        self._phone_link_task_running = True
        self.phone_link_button.configure(state="disabled")
        self.phone_link_calls_button.configure(state="disabled")
        self.phone_link_install_button.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self.status_title.set(get_text(self.language.get(), "status_installing"))
        self.status_summary.set(get_text(self.language.get(), "summary_installing"))
        self._set_text_widget(self.notes_value, get_text(self.language.get(), "installing_notes"))
        self._set_text_widget(self.report_box, get_text(self.language.get(), "installing_report"))
        self._apply_status_color("partial")

        worker = threading.Thread(target=self._install_phone_link_worker, daemon=True)
        worker.start()

    def _install_phone_link_worker(self) -> None:
        """Runs the silent winget flow and reports the outcome back to the UI."""

        phone_link = collect_phone_link_info()
        command = [
            "winget",
            "upgrade" if phone_link.installed else "install",
            "--id",
            PHONE_LINK_PRODUCT_ID,
            "--source",
            "msstore",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--silent",
            "--disable-interactivity",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                **merge_hidden_process_kwargs(),
            )
            refreshed_phone_link = collect_phone_link_info()
            details = (result.stdout.strip() or result.stderr.strip() or "No output.").strip()

            if not refreshed_phone_link.installed:
                self._phone_link_queue.put(("install_failed", details))
                return

            if refreshed_phone_link.stub_executable or result.returncode == 0:
                self._phone_link_queue.put(("installed", details))
                return

            self._phone_link_queue.put(
                (
                    "launcher_missing",
                    f"{details}\n\n{get_text('en', 'launcher_not_ready')}",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive worker fallback
            self._phone_link_queue.put(("install_failed", str(exc)))

    def _poll_phone_link_queue(self) -> None:
        """Applies silent-install results on the Tkinter thread."""

        try:
            while True:
                status, details = self._phone_link_queue.get_nowait()
                self._phone_link_task_running = False
                self.phone_link_button.configure(state="normal")
                self.phone_link_calls_button.configure(state="normal")
                self.phone_link_install_button.configure(state="normal")
                self.refresh_button.configure(state="normal")
                self.refresh_diagnostics()

                if status == "installed":
                    opened = self._open_phone_link_direct() or self.open_uri(PHONE_LINK_SHELL_TARGET)
                    message_key = "install_success" if opened else "open_after_install_failed"
                    messagebox.showinfo(
                        get_text(self.language.get(), "install_title"),
                        f"{get_text(self.language.get(), message_key)}\n\n"
                        f"{get_text(self.language.get(), 'install_details')}: {details}",
                    )
                elif status == "launcher_missing":
                    self.open_uri(PHONE_LINK_STORE_TARGET)
                    messagebox.showerror(
                        get_text(self.language.get(), "install_title"),
                        f"{get_text(self.language.get(), 'open_after_install_failed')}\n\n"
                        f"{get_text(self.language.get(), 'install_details')}: {details}",
                    )
                else:
                    self.open_uri(PHONE_LINK_STORE_TARGET)
                    messagebox.showerror(
                        get_text(self.language.get(), "install_title"),
                        f"{get_text(self.language.get(), 'install_failed')}\n\n"
                        f"{get_text(self.language.get(), 'install_details')}: {details}",
                    )
        except queue.Empty:
            pass

        self.after(160, self._poll_phone_link_queue)

    def open_uri(self, target: str) -> bool:
        """Opens a Windows URI or shell target with best-effort fallbacks."""

        try:
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        except OSError:
            pass
        except AttributeError:
            pass

        try:
            subprocess.Popen(["explorer.exe", target])
            return True
        except OSError:
            return False


def run() -> None:
    """Starts the desktop application."""

    app = AppleCallsApp()
    app.mainloop()
