"""Pure decision logic used by the GUI and tests."""

from __future__ import annotations

from dataclasses import dataclass

from applecalls.diagnostics import DiagnosticReport


MIN_WINDOWS_BUILD = 18362


@dataclass(slots=True)
class SupportEvaluation:
    """UI-friendly result derived from the diagnostics report."""

    level: str
    title_key: str
    summary_key: str
    note_keys: list[str]


def _safe_int(value: str) -> int:
    """Parses an integer defensively."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def evaluate_support(report: DiagnosticReport) -> SupportEvaluation:
    """Evaluates whether the supported Windows path is available."""

    if not report.is_windows:
        return SupportEvaluation(
            level="blocked",
            title_key="status_blocked",
            summary_key="summary_non_windows",
            note_keys=[
                "note_direct_api",
                "note_mac_scope",
                "note_same_network_not_enough",
            ],
        )

    if _safe_int(report.build) < MIN_WINDOWS_BUILD:
        return SupportEvaluation(
            level="blocked",
            title_key="status_blocked",
            summary_key="summary_old_windows",
            note_keys=[
                "note_windows_requirement",
                "note_direct_api",
                "note_same_network_not_enough",
            ],
        )

    if report.active_bluetooth_count == 0:
        return SupportEvaluation(
            level="blocked",
            title_key="status_blocked",
            summary_key="summary_missing_bluetooth",
            note_keys=[
                "note_bt_required",
                "note_direct_api",
                "note_same_network_not_enough",
            ],
        )

    if not report.phone_link.installed:
        return SupportEvaluation(
            level="partial",
            title_key="status_partial",
            summary_key="summary_install_phone_link",
            note_keys=[
                "note_ios_requirement",
                "note_direct_api",
                "note_same_network_not_enough",
            ],
        )

    if not report.has_hands_free_profile:
        return SupportEvaluation(
            level="partial",
            title_key="status_partial",
            summary_key="summary_missing_calling_profile",
            note_keys=[
                "note_bt_required",
                "note_calls_button",
                "note_same_network_not_enough",
            ],
        )

    if not report.phone_link.calls_available:
        return SupportEvaluation(
            level="partial",
            title_key="status_partial",
            summary_key="summary_calls_not_exposed",
            note_keys=[
                "note_ios_requirement",
                "note_calls_button",
                "note_same_network_not_enough",
            ],
        )

    return SupportEvaluation(
        level="ready",
        title_key="status_ready",
        summary_key="summary_ready",
        note_keys=[
            "note_ios_requirement",
            "note_mac_scope",
            "note_calls_button",
            "note_forwarding_option",
            "note_same_network_not_enough",
        ],
    )


def format_report(report: DiagnosticReport) -> str:
    """Formats a plain text report for the on-screen log and clipboard."""

    bluetooth_lines = [
        f"- {adapter.name} [{adapter.status}]"
        for adapter in report.bluetooth_adapters
    ]
    bluetooth_call_profile_lines = [
        f"- {adapter.name} [{adapter.status}]"
        for adapter in report.bluetooth_call_profiles
    ]

    if not bluetooth_lines:
        bluetooth_lines = ["- No Bluetooth adapters detected."]
    if not bluetooth_call_profile_lines:
        bluetooth_call_profile_lines = ["- No Bluetooth call profiles detected."]

    error_lines = report.errors or ["- No diagnostic errors."]

    phone_link_status = "installed" if report.phone_link.installed else "not installed"
    phone_link_version = report.phone_link.version or "n/a"
    phone_link_device = report.phone_link.connected_device_name or "n/a"
    phone_link_tag = report.phone_link.device_tag or "n/a"
    phone_link_calls = "yes" if report.phone_link.calls_available else "no"
    phone_link_recent_calls = str(report.phone_link.recent_call_count)
    phone_link_companion_state = report.phone_link.companion_state_path or "n/a"
    network_profile = report.network.profile_name or "n/a"
    network_interface = report.network.interface_alias or "n/a"
    network_category = report.network.network_category or "n/a"
    wifi_connected = "yes" if report.network.wifi_connected else "no"
    wifi_ssid = report.network.wifi_ssid or "n/a"
    ipv4_addresses = ", ".join(report.network.ipv4_addresses) or "n/a"
    hands_free_profile = "yes" if report.has_hands_free_profile else "no"
    recent_call_preview = " | ".join(report.phone_link.recent_call_titles[:3]) or "n/a"

    lines = [
        "AppleCalls diagnostic report",
        "",
        f"Platform: {report.platform_name} {report.release}",
        f"Version: {report.version}",
        f"Build: {report.build or 'n/a'}",
        f"Python: {report.python_version}",
        "",
        f"Phone Link: {phone_link_status}",
        f"Phone Link version: {phone_link_version}",
        f"Phone Link connected device: {phone_link_device}",
        f"Phone Link device tag: {phone_link_tag}",
        f"Phone Link calls entry available: {phone_link_calls}",
        f"Phone Link recent calls visible: {phone_link_recent_calls}",
        f"Phone Link companion state: {phone_link_companion_state}",
        "",
        f"Network profile: {network_profile}",
        f"Network interface: {network_interface}",
        f"Network category: {network_category}",
        f"Wi-Fi connected: {wifi_connected}",
        f"Wi-Fi SSID: {wifi_ssid}",
        f"IPv4 addresses: {ipv4_addresses}",
        "",
        f"Bluetooth adapters detected: {len(report.bluetooth_adapters)}",
        f"Bluetooth adapters active: {report.active_bluetooth_count}",
        f"Bluetooth hands-free profile: {hands_free_profile}",
        *bluetooth_lines,
        "",
        f"Bluetooth call profiles detected: {len(report.bluetooth_call_profiles)}",
        *bluetooth_call_profile_lines,
        "",
        f"Recent call preview: {recent_call_preview}",
        "",
        "Errors:",
        *error_lines,
    ]

    return "\n".join(lines)
