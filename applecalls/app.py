"""Tkinter desktop application for AppleCalls."""

from __future__ import annotations

from pathlib import Path
import os
import queue
import subprocess
import threading
import time
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
from applecalls.voip import (
    CallState,
    PhoneStatus,
    SipAccount,
    SipPhoneController,
    call_state_to_key,
    load_account,
    load_password,
    phone_status_to_key,
    save_account,
    save_password,
)
from applecalls.voip import DEFAULT_SIP_PORT as VOIP_DEFAULT_SIP_PORT


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

        # SIP/VoIP softphone state. This is an independent calling mechanism
        # (real SIP/RTP, RFC 3261) that lives alongside the Phone Link
        # diagnostics above -- it never replaces or disables that feature.
        self._voip_controller = SipPhoneController()
        self._voip_account: SipAccount | None = None
        self._voip_last_status: PhoneStatus = PhoneStatus.INACTIVE
        self._voip_last_call_state: CallState | None = None
        self._voip_call_answered_at: float | None = None
        self.voip_server_var = tk.StringVar()
        self.voip_port_var = tk.StringVar(value=str(VOIP_DEFAULT_SIP_PORT))
        self.voip_username_var = tk.StringVar()
        self.voip_password_var = tk.StringVar()
        self.voip_display_number_var = tk.StringVar()
        self.voip_dial_number_var = tk.StringVar()
        self.voip_status_text = tk.StringVar()
        self.voip_call_state_text = tk.StringVar()
        self.voip_duration_text = tk.StringVar()
        self.voip_incoming_text = tk.StringVar()

        self.base_dir = Path(__file__).resolve().parent.parent
        self.icon_path = self.base_dir / "iphone_apple_mac_171.ico"

        self._configure_root()
        self._configure_styles()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_saved_voip_account()
        self._apply_voip_status(PhoneStatus.INACTIVE)
        self._apply_voip_call_state(None)
        self.after(120, self._poll_diagnostic_queue)
        self.after(160, self._poll_phone_link_queue)
        self.after(150, self._poll_voip_queue)
        self.after(500, self._tick_voip_duration)
        self.refresh_ui()

    def _configure_root(self) -> None:
        """Sets base window properties."""

        self.title("AppleCalls")
        self.geometry("1040x1040")
        self.minsize(940, 760)
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
        root.rowconfigure(3, weight=0)

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

        self._build_voip_section(root)

        self.summary_frame = summary_frame
        self.actions_frame = actions_frame
        self.diagnostic_frame = diagnostic_frame
        self.guide_frame = guide_frame
        self.limitations_frame = limitations_frame

    def _build_voip_section(self, root: ttk.Frame) -> None:
        """Builds the independent SIP softphone section.

        This is additive to the Phone Link diagnostics above -- it is a
        separate, standards-based (RFC 3261 SIP + RTP/G.711) calling
        mechanism, not a replacement or a clone of Phone Link or Apple
        Continuity.
        """

        voip_frame = ttk.LabelFrame(root, style="Section.TLabelframe")
        voip_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        voip_frame.columnconfigure(0, weight=3)
        voip_frame.columnconfigure(1, weight=2)

        self.voip_intro_label = ttk.Label(
            voip_frame, style="Body.TLabel", wraplength=880, justify="left"
        )
        self.voip_intro_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))

        account_frame = ttk.Frame(voip_frame, style="Card.TFrame")
        account_frame.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        account_frame.columnconfigure(1, weight=1)

        self.voip_server_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_server_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.voip_server_entry = ttk.Entry(account_frame, textvariable=self.voip_server_var)
        self.voip_server_entry.grid(row=0, column=1, sticky="ew", pady=4)

        self.voip_port_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_port_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.voip_port_entry = ttk.Entry(account_frame, textvariable=self.voip_port_var, width=10)
        self.voip_port_entry.grid(row=1, column=1, sticky="w", pady=4)

        self.voip_username_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_username_label.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        self.voip_username_entry = ttk.Entry(account_frame, textvariable=self.voip_username_var)
        self.voip_username_entry.grid(row=2, column=1, sticky="ew", pady=4)

        self.voip_password_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_password_label.grid(row=3, column=0, sticky="w", padx=(0, 10), pady=4)
        self.voip_password_entry = ttk.Entry(account_frame, textvariable=self.voip_password_var, show="*")
        self.voip_password_entry.grid(row=3, column=1, sticky="ew", pady=4)

        self.voip_display_number_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_display_number_label.grid(row=4, column=0, sticky="w", padx=(0, 10), pady=4)
        self.voip_display_number_entry = ttk.Entry(account_frame, textvariable=self.voip_display_number_var)
        self.voip_display_number_entry.grid(row=4, column=1, sticky="ew", pady=4)

        voip_buttons = ttk.Frame(account_frame, style="Card.TFrame")
        voip_buttons.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        voip_buttons.columnconfigure(0, weight=1)
        voip_buttons.columnconfigure(1, weight=1)
        self.voip_connect_button = ttk.Button(
            voip_buttons, style="Accent.TButton", command=self.save_and_connect_voip
        )
        self.voip_connect_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.voip_disconnect_button = ttk.Button(voip_buttons, command=self.disconnect_voip)
        self.voip_disconnect_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.voip_status_label = ttk.Label(account_frame, style="Body.TLabel")
        self.voip_status_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.voip_status_value = ttk.Label(
            account_frame, textvariable=self.voip_status_text, style="Summary.TLabel"
        )
        self.voip_status_value.grid(row=7, column=0, columnspan=2, sticky="w")

        call_frame = ttk.Frame(voip_frame, style="Card.TFrame")
        call_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        call_frame.columnconfigure(0, weight=1)

        self.voip_dial_label = ttk.Label(call_frame, style="Body.TLabel")
        self.voip_dial_label.grid(row=0, column=0, sticky="w")

        dial_row = ttk.Frame(call_frame, style="Card.TFrame")
        dial_row.grid(row=1, column=0, sticky="ew", pady=(2, 10))
        dial_row.columnconfigure(0, weight=1)
        self.voip_dial_entry = ttk.Entry(dial_row, textvariable=self.voip_dial_number_var)
        self.voip_dial_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.voip_call_button = ttk.Button(
            dial_row, style="Accent.TButton", command=self.dial_voip_number
        )
        self.voip_call_button.grid(row=0, column=1)

        self.voip_call_state_label = ttk.Label(call_frame, style="Body.TLabel")
        self.voip_call_state_label.grid(row=2, column=0, sticky="w")
        self.voip_call_state_value = ttk.Label(
            call_frame, textvariable=self.voip_call_state_text, style="StatusValue.TLabel"
        )
        self.voip_call_state_value.grid(row=3, column=0, sticky="w")
        self.voip_duration_value = ttk.Label(call_frame, textvariable=self.voip_duration_text, style="Body.TLabel")
        self.voip_duration_value.grid(row=4, column=0, sticky="w", pady=(2, 8))

        self.voip_hangup_button = ttk.Button(call_frame, command=self.hangup_voip_call)
        self.voip_hangup_button.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        self.voip_incoming_frame = ttk.Frame(call_frame, style="Card.TFrame")
        self.voip_incoming_frame.grid(row=6, column=0, sticky="ew")
        self.voip_incoming_frame.columnconfigure(0, weight=1)
        self.voip_incoming_frame.columnconfigure(1, weight=1)
        self.voip_incoming_label = ttk.Label(
            self.voip_incoming_frame,
            textvariable=self.voip_incoming_text,
            style="StatusValue.TLabel",
            wraplength=320,
            justify="left",
        )
        self.voip_incoming_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 6))
        self.voip_answer_button = ttk.Button(
            self.voip_incoming_frame, style="Accent.TButton", command=self.answer_voip_call
        )
        self.voip_answer_button.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.voip_decline_button = ttk.Button(self.voip_incoming_frame, command=self.decline_voip_call)
        self.voip_decline_button.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        self.voip_incoming_frame.grid_remove()

        self.voip_dtmf_note_label = ttk.Label(
            call_frame, style="Summary.TLabel", wraplength=340, justify="left"
        )
        self.voip_dtmf_note_label.grid(row=7, column=0, sticky="w", pady=(8, 0))

        self.voip_frame = voip_frame

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
        self._refresh_voip_texts()
        self.refresh_diagnostics()

    def _refresh_voip_texts(self) -> None:
        """Applies the current language to every static string in the SIP section."""

        language = self.language.get()
        self.voip_frame.configure(text=get_text(language, "voip_section_title"))
        self.voip_intro_label.configure(text=get_text(language, "voip_section_intro"))
        self.voip_server_label.configure(text=get_text(language, "voip_field_server"))
        self.voip_port_label.configure(text=get_text(language, "voip_field_port"))
        self.voip_username_label.configure(text=get_text(language, "voip_field_username"))
        self.voip_password_label.configure(text=get_text(language, "voip_field_password"))
        self.voip_display_number_label.configure(text=get_text(language, "voip_field_display_number"))
        self.voip_connect_button.configure(text=get_text(language, "voip_save_connect"))
        self.voip_disconnect_button.configure(text=get_text(language, "voip_disconnect"))
        self.voip_status_label.configure(text=get_text(language, "voip_status_label"))
        self.voip_dial_label.configure(text=get_text(language, "voip_dial_label"))
        self.voip_call_button.configure(text=get_text(language, "voip_call_button"))
        self.voip_call_state_label.configure(text=get_text(language, "voip_call_state_label"))
        self.voip_hangup_button.configure(text=get_text(language, "voip_hangup_button"))
        self.voip_answer_button.configure(text=get_text(language, "voip_answer"))
        self.voip_decline_button.configure(text=get_text(language, "voip_decline"))
        self.voip_dtmf_note_label.configure(text=get_text(language, "voip_no_dtmf_note"))

        # Re-render the dynamic status/state labels in the new language
        # without re-triggering their side effects (timer resets, etc).
        self._apply_voip_status(self._voip_last_status)
        self._apply_voip_call_state(self._voip_last_call_state)

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

    # -- SIP/VoIP softphone -------------------------------------------------
    #
    # This section is a real, independent SIP (RFC 3261) + RTP/G.711
    # softphone client. It is not related to Microsoft Phone Link or Apple
    # Continuity, and it never disables the diagnostics above. The intended
    # setup is call forwarding from the user's iPhone to a SIP/VoIP DID
    # number of their choice.

    def _load_saved_voip_account(self) -> None:
        """Prefills the SIP fields from the last saved account, if any.

        Does not auto-connect -- registering with a real SIP server is a
        deliberate, user-triggered action (the Save and connect button).
        """

        account = load_account()
        if account is None:
            return

        self._voip_account = account
        self.voip_server_var.set(account.server)
        self.voip_port_var.set(str(account.port))
        self.voip_username_var.set(account.username)
        self.voip_display_number_var.set(account.display_number)

        password = load_password(account.username)
        if password:
            self.voip_password_var.set(password)

    def save_and_connect_voip(self) -> None:
        """Validates the form, persists the account, and starts SIP registration."""

        language = self.language.get()
        server = self.voip_server_var.get().strip()
        username = self.voip_username_var.get().strip()
        password = self.voip_password_var.get()
        display_number = self.voip_display_number_var.get().strip()
        port_text = self.voip_port_var.get().strip()

        if not server or not username or not password:
            messagebox.showwarning(
                get_text(language, "voip_error_title"),
                get_text(language, "voip_connect_missing_fields"),
            )
            return

        try:
            port = int(port_text) if port_text else VOIP_DEFAULT_SIP_PORT
        except ValueError:
            port = VOIP_DEFAULT_SIP_PORT
        self.voip_port_var.set(str(port))

        account = SipAccount(
            server=server,
            username=username,
            display_number=display_number,
            port=port,
        )

        try:
            save_account(account)
        except OSError as exc:
            messagebox.showerror(get_text(language, "voip_error_title"), str(exc))
            return

        if not save_password(username, password):
            messagebox.showwarning(
                get_text(language, "voip_error_title"),
                get_text(language, "voip_password_store_failed"),
            )

        self._voip_account = account

        if self._voip_controller.get_status() == PhoneStatus.INACTIVE:
            self._voip_controller.connect(account, password)
        else:
            # A previous account is still connected/connecting. Ask the
            # controller to tear it down first, then connect fresh once the
            # old socket has had a moment to release.
            self._voip_controller.disconnect()
            self.after(300, lambda acc=account, pwd=password: self._voip_controller.connect(acc, pwd))

    def disconnect_voip(self) -> None:
        """Deregisters the SIP account (asynchronous, never blocks the UI)."""

        self._voip_controller.disconnect()

    def dial_voip_number(self) -> None:
        """Places an outbound call to the number typed in the dialer."""

        language = self.language.get()
        number = self.voip_dial_number_var.get().strip()
        if not number:
            return

        if self._voip_last_status != PhoneStatus.REGISTERED:
            messagebox.showwarning(
                get_text(language, "voip_error_title"),
                get_text(language, "voip_error_not_connected"),
            )
            return

        self._voip_controller.dial(number)

    def answer_voip_call(self) -> None:
        """Answers the ringing call. Runs off the Tk thread, guarded against races."""

        threading.Thread(target=self._voip_controller.answer_current_call, daemon=True).start()

    def decline_voip_call(self) -> None:
        """Declines the ringing call. Runs off the Tk thread, guarded against races."""

        threading.Thread(target=self._voip_controller.decline_current_call, daemon=True).start()

    def hangup_voip_call(self) -> None:
        """Hangs up the active call. Runs off the Tk thread, guarded against races."""

        threading.Thread(target=self._voip_controller.hangup_current_call, daemon=True).start()

    def _poll_voip_queue(self) -> None:
        """Applies SIP/call events from the controller without touching Tkinter from threads."""

        try:
            while True:
                kind, payload = self._voip_controller.events.get_nowait()
                if kind == "status":
                    self._apply_voip_status(payload)
                elif kind == "call_state":
                    self._apply_voip_call_state(payload)
                elif kind == "incoming_call":
                    self._apply_voip_incoming_call(payload)
                elif kind == "error":
                    self._apply_voip_error(payload)
        except queue.Empty:
            pass

        self.after(150, self._poll_voip_queue)

    def _apply_voip_status(self, status: PhoneStatus) -> None:
        """Updates the registration status label and the connect/disconnect buttons."""

        self._voip_last_status = status
        language = self.language.get()
        self.voip_status_text.set(get_text(language, phone_status_to_key(status)))

        transitional = status in (PhoneStatus.REGISTERING, PhoneStatus.DEREGISTERING)
        self.voip_connect_button.configure(state="disabled" if transitional else "normal")
        self.voip_disconnect_button.configure(
            state="normal" if status in (PhoneStatus.REGISTERING, PhoneStatus.REGISTERED) else "disabled"
        )
        self._refresh_voip_call_button_state()

    def _apply_voip_call_state(self, state: CallState | None) -> None:
        """Updates the call-state label, duration timer, and call/hangup buttons."""

        self._voip_last_call_state = state
        language = self.language.get()
        self.voip_call_state_text.set(get_text(language, call_state_to_key(state)))
        self._refresh_voip_call_button_state()

        if state == CallState.ANSWERED:
            if self._voip_call_answered_at is None:
                self._voip_call_answered_at = time.monotonic()
            self.voip_hangup_button.configure(state="normal")
            self._hide_voip_incoming_banner()
            return

        self._voip_call_answered_at = None
        self.voip_duration_text.set("")
        self.voip_hangup_button.configure(state="disabled")
        if state != CallState.RINGING:
            self._hide_voip_incoming_banner()

    def _refresh_voip_call_button_state(self) -> None:
        """Enables Call only while registered and no call is already in progress."""

        busy = self._voip_last_call_state in (CallState.DIALING, CallState.RINGING, CallState.ANSWERED)
        registered = self._voip_last_status == PhoneStatus.REGISTERED
        self.voip_call_button.configure(state="normal" if (registered and not busy) else "disabled")

    def _apply_voip_incoming_call(self, payload: dict[str, str]) -> None:
        """Shows the incoming-call banner and makes sure the user notices it."""

        language = self.language.get()
        number = payload.get("number") or payload.get("caller") or "?"
        self.voip_incoming_text.set(f"{get_text(language, 'voip_incoming_call_from')}: {number}")
        self.voip_incoming_frame.grid()
        self._notify_incoming_call()

    def _notify_incoming_call(self) -> None:
        """Raises the window and gives an audible cue so a ringing call is not missed."""

        try:
            self.deiconify()
        except tk.TclError:
            pass
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.bell()

    def _hide_voip_incoming_banner(self) -> None:
        self.voip_incoming_frame.grid_remove()

    def _apply_voip_error(self, message: str) -> None:
        """Surfaces a background SIP/audio failure without crashing the GUI."""

        language = self.language.get()
        text = get_text(language, self._VOIP_ERROR_KEYS.get(message, "")) if message in self._VOIP_ERROR_KEYS else message
        messagebox.showerror(get_text(language, "voip_error_title"), text)

    # Internal event codes (pushed by SipPhoneController) that map to a
    # translated message instead of being shown to the user verbatim.
    _VOIP_ERROR_KEYS = {
        "not_connected": "voip_error_not_connected",
    }

    def _tick_voip_duration(self) -> None:
        """Refreshes the elapsed-call-time label roughly twice a second."""

        if self._voip_call_answered_at is not None:
            elapsed = int(time.monotonic() - self._voip_call_answered_at)
            minutes, seconds = divmod(elapsed, 60)
            language = self.language.get()
            self.voip_duration_text.set(
                f"{get_text(language, 'voip_call_duration_label')}: {minutes:02d}:{seconds:02d}"
            )

        self.after(500, self._tick_voip_duration)

    def _on_close(self) -> None:
        """Stops any active SIP registration/call/audio threads, then closes the window.

        `SipPhoneController.shutdown()` already bounds its own internal
        waits, but running it directly on the Tk thread could still hold the
        window open for a few seconds (audio thread joins plus the SIP stop
        handshake). Give it a short, separate bound here instead: if
        teardown has not finished by then, close the window anyway and let
        the daemon thread keep trying to clean up in the background for
        whatever remains of the process's lifetime.
        """

        def _shutdown() -> None:
            try:
                self._voip_controller.shutdown()
            except Exception:  # pragma: no cover - defensive, must never block close
                pass

        worker = threading.Thread(target=_shutdown, daemon=True)
        worker.start()
        worker.join(timeout=1.5)
        self.destroy()

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
