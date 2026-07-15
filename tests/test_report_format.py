"""Formatting-oriented tests for the diagnostic report."""

from applecalls.diagnostics import BluetoothAdapter, DiagnosticReport, NetworkInfo, PhoneLinkInfo
from applecalls.logic import format_report
import unittest


class FormatReportTests(unittest.TestCase):
    """Verifies that the plain text report keeps key troubleshooting fields."""

    def test_format_report_includes_network_and_bluetooth_sections(self) -> None:
        report = DiagnosticReport(
            platform_name="Windows",
            release="11",
            version="10.0.22631",
            build="22631",
            python_version="3.12.10",
            is_windows=True,
            phone_link=PhoneLinkInfo(
                installed=True,
                version="1.0",
                connected_device_name="iPhone 14 Pro Max",
                device_tag="device-ios",
                calls_uri="ms-phone:calling?startScenarioId=feature_calling",
                recent_call_titles=["Incoming call from Test"],
                companion_state_path="C:/Users/Test/StartMenuCompanion.json",
            ),
            bluetooth_adapters=[BluetoothAdapter(name="Adapter", status="OK")],
            bluetooth_call_profiles=[
                BluetoothAdapter(name="iPhone Hands-Free HF", status="OK"),
                BluetoothAdapter(name="Auriculares (SoundPlay ANC)", status="OK", class_name="AudioEndpoint"),
            ],
            network=NetworkInfo(
                profile_name="OfficeNet",
                interface_alias="Ethernet",
                network_category="Private",
                wifi_connected=False,
                ipv4_addresses=["192.168.1.5"],
            ),
            errors=[],
        )

        text = format_report(report)

        self.assertIn("Network profile: OfficeNet", text)
        self.assertIn("Network interface: Ethernet", text)
        self.assertIn("Wi-Fi connected: no", text)
        self.assertIn("Bluetooth adapters active: 1", text)
        self.assertIn("Phone Link connected device: iPhone 14 Pro Max", text)
        self.assertIn("Phone Link calls entry available: yes", text)
        self.assertIn("Bluetooth hands-free profile: yes", text)
        self.assertIn("External Bluetooth audio blockers: 1", text)


if __name__ == "__main__":
    unittest.main()
