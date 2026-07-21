"""Standards-based SIP/VoIP softphone integration for AppleCalls.

This module is a genuinely independent calling mechanism. It is NOT a clone
of Microsoft Phone Link and it does NOT use any private Apple Continuity API.
It implements a real SIP (RFC 3261) user agent with RTP/G.711 media, built on
top of the third-party `pyVoIP` library. The intended real-world setup is:
the user forwards their real iPhone number to a SIP/VoIP DID number (through
their carrier or a VoIP provider of their choice), and this module registers
directly with that SIP account -- no Bluetooth, no Microsoft companion app,
no Apple push infrastructure involved.

Threading contract (mirrors the queue+after() idiom already used in
`applecalls/app.py` for diagnostics and Phone Link installs): every pyVoIP
and sounddevice callback in this module runs on a background thread. None of
them ever touch Tkinter widgets. Instead, `SipPhoneController` pushes named
events onto a plain `queue.Queue` (`SipPhoneController.events`) that the GUI
polls from the Tk main loop via `self.after(...)`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# NOTE: `audioop` is stdlib in Python 3.12 but is deprecated for removal
# starting in Python 3.13 (PEP 594). This is a known future-Python-version
# risk for this project; no workaround is attempted here because the app
# currently targets Python 3.12.
import audioop
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any

import keyring
import keyring.errors
import sounddevice
from pyVoIP.VoIP.VoIP import (
    CallState,
    InvalidRangeError,
    InvalidStateError,
    NoPortsAvailableError,
    VoIPCall,
    VoIPPhone,
)
from pyVoIP.VoIP.status import PhoneStatus

from applecalls.process_utils import merge_hidden_process_kwargs


logger = logging.getLogger(__name__)

# Re-exported so callers of this module do not need to import pyVoIP directly.
__all__ = [
    "CallState",
    "InvalidRangeError",
    "InvalidStateError",
    "NoPortsAvailableError",
    "PhoneStatus",
    "SipAccount",
    "SipPhoneController",
    "call_state_to_key",
    "delete_password",
    "ensure_firewall_rules",
    "g711_linear_to_pcm16",
    "load_account",
    "load_password",
    "pcm16_to_g711_linear",
    "phone_status_to_key",
    "save_account",
    "save_password",
]

CONFIG_DIR_NAME = "AppleCalls"
CONFIG_FILE_NAME = "voip_account.json"

# Service name used for every OS-backed credential store lookup. Literal, on
# purpose, so a user can find/manage the stored secret from the Windows
# Credential Manager UI if they ever need to.
KEYRING_SERVICE_NAME = "AppleCalls"

DEFAULT_SIP_PORT = 5060
DEFAULT_RTP_PORT_LOW = 10000
# This app only ever holds one call at a time, so the RTP range only needs a
# handful of ports. Keeping it narrow keeps the firewall rule (see
# `ensure_firewall_rules`) narrow too.
DEFAULT_RTP_PORT_HIGH = 10019

AUDIO_SAMPLE_RATE = 8000
AUDIO_FRAME_SAMPLES = 160  # 20ms of audio at 8kHz, standard G.711 packetization.

FIREWALL_SIP_RULE_NAME = "AppleCalls SIP (UDP)"
FIREWALL_RTP_RULE_NAME = "AppleCalls RTP (UDP)"

# Bounded wait applied to the background "stop" thread during shutdown so a
# hung/unreachable SIP server can never prevent the window from closing.
DEFAULT_SHUTDOWN_TIMEOUT = 2.0
# Bounded wait applied to each audio bridging thread during teardown.
DEFAULT_AUDIO_JOIN_TIMEOUT = 1.0
# Poll interval used while watching a call's state on a background thread.
CALL_WATCH_POLL_SECONDS = 0.2


@dataclass(slots=True)
class SipAccount:
    """Non-secret SIP account configuration.

    Deliberately does NOT hold the password. The password is stored
    separately through `save_password`/`load_password`, backed by the OS
    credential store (Windows Credential Manager via `keyring`), and must
    never be serialized to this dataclass or to JSON.
    """

    server: str
    username: str
    display_number: str = ""
    port: int = DEFAULT_SIP_PORT
    sip_port: int = DEFAULT_SIP_PORT
    rtp_port_low: int = DEFAULT_RTP_PORT_LOW
    rtp_port_high: int = DEFAULT_RTP_PORT_HIGH

    def to_dict(self) -> dict[str, Any]:
        """Serializes the account to a plain (secret-free) dict."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SipAccount":
        """Builds a `SipAccount` from a previously saved dict, defensively."""

        return cls(
            server=str(data.get("server", "")),
            username=str(data.get("username", "")),
            display_number=str(data.get("display_number", "")),
            port=int(data.get("port", DEFAULT_SIP_PORT)),
            sip_port=int(data.get("sip_port", DEFAULT_SIP_PORT)),
            rtp_port_low=int(data.get("rtp_port_low", DEFAULT_RTP_PORT_LOW)),
            rtp_port_high=int(data.get("rtp_port_high", DEFAULT_RTP_PORT_HIGH)),
        )


def _default_config_dir() -> Path:
    """Returns the real `%LOCALAPPDATA%\\AppleCalls` directory."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / CONFIG_DIR_NAME


def _config_path(base_dir: Path | None) -> Path:
    """Resolves the account config file path, honoring an override directory."""

    directory = base_dir if base_dir is not None else _default_config_dir()
    return directory / CONFIG_FILE_NAME


def load_account(base_dir: Path | None = None) -> SipAccount | None:
    """Loads the saved SIP account config, or None if absent/unreadable.

    `base_dir` overrides the directory that would otherwise be derived from
    `%LOCALAPPDATA%`, which keeps this function testable against a tmp_path
    without monkeypatching environment variables.
    """

    path = _config_path(base_dir)
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read VoIP account config at %s: %s", path, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse VoIP account config at %s: %s", path, exc)
        return None

    if not isinstance(data, dict):
        logger.warning("VoIP account config at %s has an unexpected shape.", path)
        return None

    try:
        return SipAccount.from_dict(data)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to build SipAccount from %s: %s", path, exc)
        return None


def save_account(account: SipAccount, base_dir: Path | None = None) -> None:
    """Persists the (secret-free) SIP account config as JSON.

    Creates the destination directory if missing. `base_dir` overrides the
    `%LOCALAPPDATA%`-derived directory for testability, same as `load_account`.
    """

    path = _config_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(account.to_dict(), indent=2), encoding="utf-8")


def save_password(username: str, password: str) -> bool:
    """Stores the SIP account password in the OS credential store.

    Returns True on success, False on any credential-store failure (missing
    backend, locked keyring, headless CI, etc). Never raises -- some
    environments (like CI runners) have no OS credential backend at all, and
    that must not crash the app, only fail this one operation.
    """

    try:
        keyring.set_password(KEYRING_SERVICE_NAME, username, password)
        return True
    except keyring.errors.KeyringError as exc:
        logger.warning("Failed to store the VoIP password: %s", exc)
        return False


def load_password(username: str) -> str | None:
    """Reads the SIP account password from the OS credential store.

    Returns None both when the password is absent and when the credential
    store itself failed -- callers should treat both the same way (prompt
    the user to re-enter the password).
    """

    try:
        return keyring.get_password(KEYRING_SERVICE_NAME, username)
    except keyring.errors.KeyringError as exc:
        logger.warning("Failed to read the VoIP password: %s", exc)
        return None


def delete_password(username: str) -> bool:
    """Removes the stored SIP account password, if any.

    Returns True when the credential is gone afterwards (including the case
    where it never existed), False only when the credential store itself
    failed to perform the deletion.
    """

    try:
        keyring.delete_password(KEYRING_SERVICE_NAME, username)
        return True
    except keyring.errors.PasswordDeleteError:
        # Nothing was stored for this username -- the end state the caller
        # wants (no stored password) is already true.
        return True
    except keyring.errors.KeyringError as exc:
        logger.warning("Failed to delete the VoIP password: %s", exc)
        return False


def pcm16_to_g711_linear(data: bytes) -> bytes:
    """Downconverts 16-bit linear PCM (from sounddevice) to the raw 8-bit
    linear PCM that `VoIPCall.write_audio` expects."""

    return audioop.lin2lin(data, 2, 1)


def g711_linear_to_pcm16(data: bytes) -> bytes:
    """Upconverts the raw 8-bit linear PCM returned by `VoIPCall.read_audio`
    to 16-bit linear PCM suitable for a sounddevice output stream."""

    return audioop.lin2lin(data, 1, 2)


_PHONE_STATUS_KEYS: dict[PhoneStatus, str] = {
    PhoneStatus.INACTIVE: "voip_status_inactive",
    PhoneStatus.REGISTERING: "voip_status_registering",
    PhoneStatus.REGISTERED: "voip_status_registered",
    PhoneStatus.DEREGISTERING: "voip_status_deregistering",
    PhoneStatus.FAILED: "voip_status_failed",
}


def phone_status_to_key(status: PhoneStatus) -> str:
    """Maps a pyVoIP `PhoneStatus` to an i18n key, pure and side-effect free."""

    return _PHONE_STATUS_KEYS.get(status, "voip_status_inactive")


_CALL_STATE_KEYS: dict[CallState, str] = {
    CallState.DIALING: "voip_call_state_dialing",
    CallState.RINGING: "voip_call_state_ringing",
    CallState.ANSWERED: "voip_call_state_answered",
    CallState.ENDED: "voip_call_state_ended",
}


def call_state_to_key(state: CallState | None) -> str:
    """Maps a pyVoIP `CallState` (or None, meaning no active call) to an i18n key."""

    if state is None:
        return "voip_call_state_idle"
    return _CALL_STATE_KEYS.get(state, "voip_call_state_ended")


def _run_hidden(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    """Runs a command with no visible console window; returns None on failure."""

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **merge_hidden_process_kwargs(),
        )
    except OSError as exc:
        logger.warning("Failed to run %s: %s", command, exc)
        return None


def _firewall_rule_exists(rule_name: str) -> bool:
    """Checks (best-effort) whether a Windows Firewall rule already exists."""

    result = _run_hidden(
        ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"]
    )
    if result is None:
        # Unknown state: treat as "exists" so we do not attempt (and
        # possibly fail) an add on top of a broken netsh invocation.
        return True
    return result.returncode == 0 and "No rules match" not in result.stdout


def _add_firewall_udp_rule(rule_name: str, local_port: str) -> None:
    """Adds an inbound UDP allow rule (best-effort, never raises)."""

    _run_hidden(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={rule_name}",
            "dir=in",
            "action=allow",
            "protocol=UDP",
            f"localport={local_port}",
        ]
    )


def ensure_firewall_rules(sip_port: int, rtp_port_low: int, rtp_port_high: int) -> None:
    """Best-effort: opens inbound UDP for the local SIP port and RTP range.

    Idempotent (checks with `netsh ... show rule` before adding) and always
    non-fatal -- if `netsh` is missing, blocked by policy, or fails for any
    reason, this only logs a warning. Incoming calls/audio may then be
    blocked by the Windows Firewall, but the app itself must keep running.
    """

    if os.name != "nt":
        return

    try:
        if not _firewall_rule_exists(FIREWALL_SIP_RULE_NAME):
            _add_firewall_udp_rule(FIREWALL_SIP_RULE_NAME, str(sip_port))
        if not _firewall_rule_exists(FIREWALL_RTP_RULE_NAME):
            _add_firewall_udp_rule(
                FIREWALL_RTP_RULE_NAME, f"{rtp_port_low}-{rtp_port_high}"
            )
    except Exception as exc:  # pragma: no cover - defensive, must never crash the app
        logger.warning("Failed to configure Windows Firewall rules for VoIP: %s", exc)


class SipPhoneController:
    """Owns the SIP registration/call lifecycle and the audio bridge.

    Every method that touches pyVoIP or sounddevice runs the blocking parts
    on a background daemon thread and reports back through `self.events` (a
    `queue.Queue`), never by touching Tkinter directly. The GUI is expected
    to poll `self.events` with `self.after(...)`, exactly like the existing
    `_diagnostic_queue`/`_phone_link_queue` pattern in `applecalls/app.py`.

    Event tuples pushed onto `self.events`:
      ("status", PhoneStatus)          -- registration status changed.
      ("call_state", CallState)        -- the tracked call's state changed.
      ("incoming_call", {"number": str, "caller": str}) -- a call is ringing.
      ("error", str)                   -- a user-facing operation failed.
    """

    def __init__(self, events: "queue.Queue[tuple[str, Any]] | None" = None) -> None:
        self.events: "queue.Queue[tuple[str, Any]]" = (
            events if events is not None else queue.Queue()
        )
        self._phone: VoIPPhone | None = None
        self._current_call: VoIPCall | None = None
        self._lock = threading.Lock()
        self._firewall_configured = False

        self._audio_stop_event = threading.Event()
        self._capture_thread: threading.Thread | None = None
        self._playback_thread: threading.Thread | None = None

    # -- status -----------------------------------------------------------

    def get_status(self) -> PhoneStatus:
        """Returns the current SIP registration status."""

        phone = self._phone
        if phone is None:
            return PhoneStatus.INACTIVE
        return phone.get_status()

    def get_current_call_state(self) -> CallState | None:
        """Returns the tracked call's state, or None if there is no call."""

        call = self._current_call
        return call.state if call is not None else None

    # -- connection lifecycle ----------------------------------------------

    def connect(self, account: SipAccount, password: str) -> None:
        """Starts SIP registration on a background thread. Never blocks the caller.

        Building the `VoIPPhone` object itself is cheap (attribute
        assignment only, no I/O), but opening Windows Firewall rules and the
        REGISTER handshake are not -- both run on the background thread so
        this method can be called directly from a Tkinter button handler.
        """

        with self._lock:
            if self._phone is not None:
                raise RuntimeError("Already connected; call disconnect() first.")

            phone = VoIPPhone(
                account.server,
                account.port,
                account.username,
                password,
                myIP="0.0.0.0",
                callCallback=self._on_incoming_call,
                sipPort=account.sip_port,
                rtpPortLow=account.rtp_port_low,
                rtpPortHigh=account.rtp_port_high,
            )
            self._phone = phone

        self.events.put(("status", PhoneStatus.REGISTERING))
        threading.Thread(
            target=self._start_worker, args=(phone, account), daemon=True
        ).start()

    def _start_worker(self, phone: VoIPPhone, account: SipAccount) -> None:
        """Runs the firewall setup and the blocking REGISTER handshake off the Tk thread."""

        if not self._firewall_configured:
            ensure_firewall_rules(
                account.sip_port, account.rtp_port_low, account.rtp_port_high
            )
            self._firewall_configured = True

        try:
            phone.start()
        except Exception as exc:
            logger.warning("SIP registration failed: %s", exc)
            self.events.put(("error", str(exc)))
            self.events.put(("status", PhoneStatus.FAILED))
            return
        self.events.put(("status", phone.get_status()))

    def disconnect(self) -> None:
        """Asynchronously hangs up any active call and deregisters.

        Never blocks the caller -- the actual `phone.stop()` network I/O
        runs on a background daemon thread. Use `shutdown()` instead when a
        bounded wait is required (e.g. on window close).
        """

        self._stop_audio_bridge()

        with self._lock:
            phone = self._phone
            self._phone = None
            self._current_call = None

        if phone is None:
            return

        threading.Thread(target=self._stop_worker, args=(phone,), daemon=True).start()

    def _stop_worker(self, phone: VoIPPhone) -> None:
        try:
            phone.stop()
        except Exception as exc:
            logger.warning("SIP deregistration failed: %s", exc)
        finally:
            self.events.put(("status", PhoneStatus.INACTIVE))

    def shutdown(self, timeout: float = DEFAULT_SHUTDOWN_TIMEOUT) -> None:
        """Best-effort, bounded teardown for the app's window-close handler.

        Hangs up/declines any active call, then stops the SIP phone with a
        time budget of `timeout` seconds so an unreachable SIP server can
        never delay the window from closing. Never raises.
        """

        with self._lock:
            call = self._current_call
            phone = self._phone
            self._current_call = None
            self._phone = None

        self._stop_audio_bridge()

        if call is not None:
            try:
                if call.state == CallState.ANSWERED:
                    call.hangup()
                elif call.state == CallState.RINGING:
                    call.deny()
            except InvalidStateError:
                pass
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Error tearing down the active call on shutdown: %s", exc)

        if phone is not None:
            stop_thread = threading.Thread(target=self._safe_stop, args=(phone,), daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=timeout)

    def _safe_stop(self, phone: VoIPPhone) -> None:
        try:
            phone.stop()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Error stopping the SIP phone: %s", exc)

    # -- outbound calls -----------------------------------------------------

    def dial(self, number: str) -> None:
        """Places an outbound call on a background thread (never blocks the caller).

        `VoIPPhone.call()` performs a blocking SIP INVITE handshake wait
        internally, so it must not run on the Tk thread.
        """

        phone = self._phone
        if phone is None:
            self.events.put(("error", "not_connected"))
            return

        threading.Thread(target=self._dial_worker, args=(phone, number), daemon=True).start()

    def _dial_worker(self, phone: VoIPPhone, number: str) -> None:
        try:
            call = phone.call(number)
        except Exception as exc:
            logger.warning("Failed to place the outbound call: %s", exc)
            self.events.put(("error", str(exc)))
            return

        with self._lock:
            self._current_call = call
        self.events.put(("call_state", call.state))
        self._watch_call(call)

    # -- inbound calls --------------------------------------------------------

    def _on_incoming_call(self, call: VoIPCall) -> None:
        """pyVoIP's `callCallback`. Runs on a pyVoIP-managed thread, never the Tk thread.

        This app only ever tracks one call at a time. If a second call rings
        in while one is already DIALING/RINGING/ANSWERED, immediately send
        busy on the new one instead of silently overwriting
        `_current_call` -- otherwise the first call becomes unreachable
        (no way to answer/decline/hang it up from the UI) while its audio
        bridge threads keep running.
        """

        with self._lock:
            existing = self._current_call
            already_busy = existing is not None and existing.state != CallState.ENDED
            if not already_busy:
                self._current_call = call

        if already_busy:
            try:
                call.deny()
            except InvalidStateError:
                pass
            return

        from_header = call.request.headers.get("From", {}) or {}
        payload = {
            "number": str(from_header.get("number") or ""),
            "caller": str(from_header.get("caller") or ""),
        }
        self.events.put(("incoming_call", payload))
        self.events.put(("call_state", call.state))
        self._watch_call(call)

    def answer_current_call(self) -> None:
        """Answers the tracked call. Guarded against a call that already ended."""

        call = self._current_call
        if call is None:
            return
        try:
            call.answer()
        except InvalidStateError as exc:
            logger.info("Could not answer the call: %s", exc)
            self.events.put(("error", str(exc)))

    def decline_current_call(self) -> None:
        """Declines the tracked call. Guarded against a call that already ended."""

        call = self._current_call
        if call is None:
            return
        try:
            call.deny()
        except InvalidStateError as exc:
            logger.info("Could not decline the call: %s", exc)
            self.events.put(("error", str(exc)))

    def hangup_current_call(self) -> None:
        """Hangs up the tracked call. Guarded against a call that is not answered."""

        call = self._current_call
        if call is None:
            return
        try:
            call.hangup()
        except InvalidStateError as exc:
            logger.info("Could not hang up the call: %s", exc)
            self.events.put(("error", str(exc)))

    # -- call state watching / audio bridge -----------------------------------

    def _watch_call(self, call: VoIPCall) -> None:
        threading.Thread(target=self._call_state_watcher, args=(call,), daemon=True).start()

    def _call_state_watcher(self, call: VoIPCall) -> None:
        """Polls `call.state` until it ends, starting/stopping the audio bridge.

        pyVoIP has no call-state-changed callback, so polling on a dedicated
        background thread is the documented way to observe ANSWERED/ENDED
        transitions driven by the SIP signaling pyVoIP handles internally.
        """

        last_state: CallState | None = None
        audio_started = False

        while True:
            state = call.state
            if state != last_state:
                self.events.put(("call_state", state))
                last_state = state

            if state == CallState.ANSWERED and not audio_started:
                self._start_audio_bridge(call)
                audio_started = True

            if state == CallState.ENDED:
                self._stop_audio_bridge()
                with self._lock:
                    if self._current_call is call:
                        self._current_call = None
                break

            time.sleep(CALL_WATCH_POLL_SECONDS)

    def _start_audio_bridge(self, call: VoIPCall) -> None:
        # A fresh Event per call, never a shared one reset with `.clear()`.
        # Reusing one mutable Event across calls let a still-shutting-down
        # previous call's audio thread have its stop signal silently
        # un-set by the next call's start, leaking a thread that holds the
        # microphone/speaker open indefinitely.
        stop_event = threading.Event()
        self._audio_stop_event = stop_event
        self._capture_thread = threading.Thread(
            target=self._capture_loop, args=(call, stop_event), daemon=True
        )
        self._playback_thread = threading.Thread(
            target=self._playback_loop, args=(call, stop_event), daemon=True
        )
        self._capture_thread.start()
        self._playback_thread.start()

    def _stop_audio_bridge(self) -> None:
        self._audio_stop_event.set()
        for thread in (self._capture_thread, self._playback_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=DEFAULT_AUDIO_JOIN_TIMEOUT)
        self._capture_thread = None
        self._playback_thread = None

    def _capture_loop(self, call: VoIPCall, stop_event: threading.Event) -> None:
        """Reads microphone audio and feeds it into the call. Never touches Tkinter."""

        try:
            with sounddevice.RawInputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=AUDIO_FRAME_SAMPLES,
            ) as stream:
                while not stop_event.is_set():
                    frame, _overflowed = stream.read(AUDIO_FRAME_SAMPLES)
                    call.write_audio(pcm16_to_g711_linear(bytes(frame)))
        except Exception as exc:
            # Includes the case where no microphone is available at all --
            # must degrade gracefully, never crash the GUI thread.
            logger.warning("Microphone capture failed: %s", exc)
            self.events.put(("error", f"audio_capture_failed: {exc}"))

    def _playback_loop(self, call: VoIPCall, stop_event: threading.Event) -> None:
        """Reads received call audio and plays it through the speakers."""

        try:
            with sounddevice.RawOutputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=AUDIO_FRAME_SAMPLES,
            ) as stream:
                while not stop_event.is_set():
                    data = call.read_audio(length=AUDIO_FRAME_SAMPLES, blocking=True)
                    if data:
                        stream.write(g711_linear_to_pcm16(data))
        except Exception as exc:
            logger.warning("Speaker playback failed: %s", exc)
            self.events.put(("error", f"audio_playback_failed: {exc}"))
