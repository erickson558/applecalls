"""Unit tests for the support evaluation logic."""

from applecalls.diagnostics import BluetoothAdapter, DiagnosticReport, PhoneLinkInfo
from applecalls.logic import evaluate_support
import unittest


def make_report(
    *,
    is_windows: bool = True,
    build: str = "22631",
    phone_link_installed: bool = True,
    bluetooth_ok: bool = True,
    hands_free_profile: bool = True,
    calls_available: bool = True,
    external_bluetooth_audio: bool = False,
) -> DiagnosticReport:
    """Builds a deterministic report for logic tests."""

    adapters = []
    call_profiles = []
    if bluetooth_ok:
        adapters.append(BluetoothAdapter(name="MediaTek Bluetooth Adapter", status="OK"))
        if hands_free_profile:
            call_profiles.append(BluetoothAdapter(name="iPhone Hands-Free HF", status="OK"))
        if external_bluetooth_audio:
            call_profiles.append(
                BluetoothAdapter(
                    name="Auriculares (SoundPlay ANC)",
                    status="OK",
                    class_name="AudioEndpoint",
                )
            )

    return DiagnosticReport(
        platform_name="Windows" if is_windows else "Linux",
        release="11" if is_windows else "6.9",
        version="10.0.22631",
        build=build,
        python_version="3.12.10",
        is_windows=is_windows,
        phone_link=PhoneLinkInfo(
            installed=phone_link_installed,
            version="1.0",
            calls_uri="ms-phone:calling?startScenarioId=feature_calling" if calls_available else None,
        ),
        bluetooth_adapters=adapters,
        bluetooth_call_profiles=call_profiles,
        errors=[],
    )


class EvaluateSupportTests(unittest.TestCase):
    """Covers the main support branches."""

    def test_ready_when_windows_phone_link_and_bluetooth_exist(self) -> None:
        evaluation = evaluate_support(make_report())
        self.assertEqual(evaluation.level, "ready")

    def test_partial_when_phone_link_is_missing(self) -> None:
        evaluation = evaluate_support(make_report(phone_link_installed=False))
        self.assertEqual(evaluation.level, "partial")

    def test_blocked_when_bluetooth_is_missing(self) -> None:
        evaluation = evaluate_support(make_report(bluetooth_ok=False))
        self.assertEqual(evaluation.level, "blocked")

    def test_partial_when_hands_free_profile_is_missing(self) -> None:
        evaluation = evaluate_support(make_report(hands_free_profile=False))
        self.assertEqual(evaluation.level, "partial")

    def test_partial_when_external_bluetooth_audio_is_active(self) -> None:
        evaluation = evaluate_support(make_report(external_bluetooth_audio=True))
        self.assertEqual(evaluation.level, "partial")

    def test_partial_when_calls_action_is_missing(self) -> None:
        evaluation = evaluate_support(make_report(calls_available=False))
        self.assertEqual(evaluation.level, "partial")

    def test_blocked_when_not_windows(self) -> None:
        evaluation = evaluate_support(make_report(is_windows=False))
        self.assertEqual(evaluation.level, "blocked")

    def test_blocked_when_windows_is_too_old(self) -> None:
        evaluation = evaluate_support(make_report(build="17763"))
        self.assertEqual(evaluation.level, "blocked")


if __name__ == "__main__":
    unittest.main()
