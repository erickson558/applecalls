"""System diagnostics used by the AppleCalls desktop app."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import platform
import re
import subprocess
import sys
from typing import Any


@dataclass(slots=True)
class BluetoothAdapter:
    """Represents a Bluetooth device exposed by Windows."""

    name: str
    status: str


@dataclass(slots=True)
class PhoneLinkInfo:
    """Represents the Phone Link installation state."""

    installed: bool
    version: str | None = None
    package_name: str | None = None


@dataclass(slots=True)
class NetworkInfo:
    """Represents the primary network details exposed by Windows."""

    profile_name: str | None = None
    interface_alias: str | None = None
    network_category: str | None = None
    ipv4_connectivity: str | None = None
    wifi_connected: bool = False
    wifi_ssid: str | None = None
    ipv4_addresses: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DiagnosticReport:
    """Aggregates the pieces of information shown in the GUI."""

    platform_name: str
    release: str
    version: str
    build: str
    python_version: str
    is_windows: bool
    phone_link: PhoneLinkInfo
    bluetooth_adapters: list[BluetoothAdapter]
    network: NetworkInfo = field(default_factory=NetworkInfo)
    errors: list[str] = field(default_factory=list)

    @property
    def active_bluetooth_count(self) -> int:
        """Counts adapters that Windows reports as healthy."""

        return sum(1 for adapter in self.bluetooth_adapters if adapter.status.upper() == "OK")


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    """Runs a PowerShell command and returns the raw process result."""

    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Runs a generic command and returns the raw process result."""

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _run_powershell_json(script: str) -> tuple[Any | None, str | None]:
    """Runs PowerShell and attempts to parse its JSON output."""

    result = _run_powershell(script)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown PowerShell error."
        return None, stderr

    payload = result.stdout.strip()
    if not payload:
        return None, None

    try:
        return json.loads(payload), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"


def _get_phone_link_info(errors: list[str]) -> PhoneLinkInfo:
    """Collects Phone Link installation details from AppX metadata."""

    script = (
        "Get-AppxPackage -Name Microsoft.YourPhone "
        "| Select-Object Name, PackageFullName, Version "
        "| ConvertTo-Json -Compress"
    )
    data, error = _run_powershell_json(script)

    if error:
        errors.append(f"Phone Link lookup failed: {error}")

    if not data:
        return PhoneLinkInfo(installed=False)

    return PhoneLinkInfo(
        installed=True,
        version=str(data.get("Version")) if data.get("Version") else None,
        package_name=data.get("PackageFullName"),
    )


def _normalize_items(data: Any) -> list[dict[str, Any]]:
    """Normalizes PowerShell JSON output into a list of dicts."""

    if data is None:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _get_bluetooth_adapters(errors: list[str]) -> list[BluetoothAdapter]:
    """Collects Bluetooth device information from Plug and Play."""

    script = (
        "Get-PnpDevice -Class Bluetooth "
        "| Select-Object Status, FriendlyName "
        "| ConvertTo-Json -Compress"
    )
    data, error = _run_powershell_json(script)

    if error:
        errors.append(f"Bluetooth lookup failed: {error}")
        return []

    adapters: list[BluetoothAdapter] = []
    for item in _normalize_items(data):
        adapters.append(
            BluetoothAdapter(
                name=str(item.get("FriendlyName") or "Unknown device"),
                status=str(item.get("Status") or "Unknown"),
            )
        )

    return adapters


def _get_network_profile(errors: list[str]) -> NetworkInfo:
    """Collects the currently connected Windows network profile."""

    script = (
        "Get-NetConnectionProfile "
        "| Where-Object { $_.IPv4Connectivity -ne 'Disconnected' } "
        "| Select-Object -First 1 Name, InterfaceAlias, NetworkCategory, IPv4Connectivity "
        "| ConvertTo-Json -Compress"
    )
    data, error = _run_powershell_json(script)

    if error:
        errors.append(f"Network profile lookup failed: {error}")
        return NetworkInfo()

    if not isinstance(data, dict):
        return NetworkInfo()

    return NetworkInfo(
        profile_name=str(data.get("Name")) if data.get("Name") else None,
        interface_alias=str(data.get("InterfaceAlias")) if data.get("InterfaceAlias") else None,
        network_category=str(data.get("NetworkCategory")) if data.get("NetworkCategory") else None,
        ipv4_connectivity=str(data.get("IPv4Connectivity")) if data.get("IPv4Connectivity") else None,
    )


def _get_ipv4_addresses(errors: list[str]) -> list[str]:
    """Collects non-loopback IPv4 addresses for the current PC."""

    script = (
        "Get-NetIPAddress -AddressFamily IPv4 "
        "| Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' } "
        "| Select-Object IPAddress "
        "| ConvertTo-Json -Compress"
    )
    data, error = _run_powershell_json(script)

    if error:
        errors.append(f"IPv4 lookup failed: {error}")
        return []

    addresses: list[str] = []
    for item in _normalize_items(data):
        address = str(item.get("IPAddress") or "").strip()
        if address and address not in addresses:
            addresses.append(address)

    return addresses


def _get_wifi_details(errors: list[str]) -> tuple[bool, str | None]:
    """Reads Wi-Fi state and SSID using netsh.

    The `netsh` output is partially localized on Windows, so the parser only relies
    on stable markers such as `SSID` and a generic connected state check.
    """

    result = _run_command(["netsh", "wlan", "show", "interfaces"])

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown netsh error."
        errors.append(f"Wi-Fi lookup failed: {stderr}")
        return False, None

    output = result.stdout
    ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", output, flags=re.MULTILINE)
    state_match = re.search(r"^\s*(?:State|Estado)\s*:\s*(.+)$", output, flags=re.MULTILINE)
    state_value = state_match.group(1).strip().lower() if state_match else ""
    connected = state_value in {"connected", "conectado"}

    if not ssid_match:
        return connected, None

    ssid = ssid_match.group(1).strip()
    if ssid.upper() == "N/A":
        return connected, None

    return connected, ssid


def _get_network_info(errors: list[str]) -> NetworkInfo:
    """Builds a combined network view from PowerShell and netsh."""

    info = _get_network_profile(errors)
    info.ipv4_addresses = _get_ipv4_addresses(errors)
    info.wifi_connected, info.wifi_ssid = _get_wifi_details(errors)
    return info


def collect_report() -> DiagnosticReport:
    """Builds a diagnostic report for the current machine."""

    errors: list[str] = []
    platform_name = platform.system()
    release = platform.release()
    version = platform.version()
    build = ""

    if hasattr(sys, "getwindowsversion"):
        try:
            build = str(sys.getwindowsversion().build)
        except OSError as exc:
            errors.append(f"Windows build lookup failed: {exc}")

    is_windows = platform_name.lower() == "windows"
    phone_link = _get_phone_link_info(errors) if is_windows else PhoneLinkInfo(installed=False)
    bluetooth_adapters = _get_bluetooth_adapters(errors) if is_windows else []
    network = _get_network_info(errors) if is_windows else NetworkInfo()

    return DiagnosticReport(
        platform_name=platform_name,
        release=release,
        version=version,
        build=build,
        python_version=platform.python_version(),
        is_windows=is_windows,
        phone_link=phone_link,
        bluetooth_adapters=bluetooth_adapters,
        network=network,
        errors=errors,
    )


def build_fallback_report(error_message: str) -> DiagnosticReport:
    """Builds a minimal report when diagnostics fail unexpectedly."""

    platform_name = platform.system()
    return DiagnosticReport(
        platform_name=platform_name,
        release=platform.release(),
        version=platform.version(),
        build="",
        python_version=platform.python_version(),
        is_windows=platform_name.lower() == "windows",
        phone_link=PhoneLinkInfo(installed=False),
        bluetooth_adapters=[],
        network=NetworkInfo(),
        errors=[f"Unexpected diagnostic error: {error_message}"],
    )
