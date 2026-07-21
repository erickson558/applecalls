"""Unit tests for the SIP/VoIP softphone module (`applecalls/voip.py`).

Everything that would otherwise touch a real network socket, a real audio
device, or the real OS credential store is monkeypatched here. These tests
must stay safe to run on a `windows-latest` GitHub Actions runner with no
real SIP server and no real audio hardware.
"""

from __future__ import annotations

from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import keyring.errors

from applecalls import voip


class SipAccountConfigTests(unittest.TestCase):
    """Covers `SipAccount` JSON config load/save round trips against a tmp dir."""

    def test_round_trip_preserves_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            account = voip.SipAccount(
                server="sip.example.com",
                username="user1",
                display_number="+15550001111",
                port=5061,
                sip_port=5070,
                rtp_port_low=12000,
                rtp_port_high=12019,
            )

            voip.save_account(account, base_dir=base_dir)
            loaded = voip.load_account(base_dir=base_dir)

        self.assertEqual(loaded, account)

    def test_saved_config_never_contains_a_password_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            account = voip.SipAccount(server="sip.example.com", username="user1")
            voip.save_account(account, base_dir=base_dir)
            raw = (base_dir / voip.CONFIG_FILE_NAME).read_text(encoding="utf-8")

        self.assertNotIn("password", raw.lower())

    def test_load_account_missing_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertIsNone(voip.load_account(base_dir=Path(temp_dir)))

    def test_save_account_creates_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "nested" / "AppleCalls"
            account = voip.SipAccount(server="sip.example.com", username="user1")

            voip.save_account(account, base_dir=base_dir)

            self.assertTrue((base_dir / voip.CONFIG_FILE_NAME).exists())

    def test_load_account_survives_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            (base_dir / voip.CONFIG_FILE_NAME).write_text("{not json", encoding="utf-8")

            self.assertIsNone(voip.load_account(base_dir=base_dir))

    def test_load_account_rejects_non_dict_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            (base_dir / voip.CONFIG_FILE_NAME).write_text("[1, 2, 3]", encoding="utf-8")

            self.assertIsNone(voip.load_account(base_dir=base_dir))

    def test_from_dict_fills_defaults_for_missing_keys(self) -> None:
        account = voip.SipAccount.from_dict({"server": "sip.example.com", "username": "user1"})

        self.assertEqual(account.port, voip.DEFAULT_SIP_PORT)
        self.assertEqual(account.sip_port, voip.DEFAULT_SIP_PORT)
        self.assertEqual(account.rtp_port_low, voip.DEFAULT_RTP_PORT_LOW)
        self.assertEqual(account.rtp_port_high, voip.DEFAULT_RTP_PORT_HIGH)
        self.assertEqual(account.display_number, "")


class CredentialWrapperTests(unittest.TestCase):
    """Covers the keyring wrapper functions with `keyring` fully monkeypatched."""

    def test_save_password_success(self) -> None:
        with patch.object(voip.keyring, "set_password") as mock_set:
            result = voip.save_password("user1", "secret")

        self.assertTrue(result)
        mock_set.assert_called_once_with(voip.KEYRING_SERVICE_NAME, "user1", "secret")

    def test_save_password_failure_is_caught_and_reported(self) -> None:
        with patch.object(
            voip.keyring, "set_password", side_effect=keyring.errors.KeyringError("boom")
        ):
            result = voip.save_password("user1", "secret")

        self.assertFalse(result)

    def test_load_password_success(self) -> None:
        with patch.object(voip.keyring, "get_password", return_value="secret"):
            result = voip.load_password("user1")

        self.assertEqual(result, "secret")

    def test_load_password_failure_returns_none(self) -> None:
        with patch.object(
            voip.keyring, "get_password", side_effect=keyring.errors.KeyringError("boom")
        ):
            result = voip.load_password("user1")

        self.assertIsNone(result)

    def test_delete_password_success(self) -> None:
        with patch.object(voip.keyring, "delete_password") as mock_delete:
            result = voip.delete_password("user1")

        self.assertTrue(result)
        mock_delete.assert_called_once_with(voip.KEYRING_SERVICE_NAME, "user1")

    def test_delete_password_treats_missing_entry_as_success(self) -> None:
        with patch.object(
            voip.keyring,
            "delete_password",
            side_effect=keyring.errors.PasswordDeleteError("not found"),
        ):
            result = voip.delete_password("user1")

        self.assertTrue(result)

    def test_delete_password_other_failure_returns_false(self) -> None:
        with patch.object(
            voip.keyring, "delete_password", side_effect=keyring.errors.KeyringError("boom")
        ):
            result = voip.delete_password("user1")

        self.assertFalse(result)


class AudioConversionTests(unittest.TestCase):
    """Covers the 8-bit <-> 16-bit linear PCM helpers (stdlib `audioop`)."""

    def test_downconvert_halves_the_byte_length(self) -> None:
        pcm16 = b"\x10\x20" * 80  # 80 16-bit samples.
        pcm8 = voip.pcm16_to_g711_linear(pcm16)

        self.assertEqual(len(pcm8), 80)

    def test_round_trip_doubles_back_to_original_length(self) -> None:
        pcm16 = b"\x10\x20" * 80
        pcm8 = voip.pcm16_to_g711_linear(pcm16)
        back_to_16 = voip.g711_linear_to_pcm16(pcm8)

        self.assertEqual(len(back_to_16), len(pcm16))

    def test_round_trip_silence_is_lossless(self) -> None:
        silence16 = b"\x00\x00" * 160
        pcm8 = voip.pcm16_to_g711_linear(silence16)
        back = voip.g711_linear_to_pcm16(pcm8)

        self.assertEqual(back, silence16)


class StateMappingTests(unittest.TestCase):
    """Covers the pure PhoneStatus/CallState -> i18n-key mapping helpers."""

    def test_phone_status_mapping_is_exhaustive(self) -> None:
        for status in voip.PhoneStatus:
            key = voip.phone_status_to_key(status)
            self.assertTrue(key.startswith("voip_status_"))

    def test_call_state_mapping_is_exhaustive(self) -> None:
        for state in voip.CallState:
            key = voip.call_state_to_key(state)
            self.assertTrue(key.startswith("voip_call_state_"))

    def test_call_state_mapping_handles_no_active_call(self) -> None:
        self.assertEqual(voip.call_state_to_key(None), "voip_call_state_idle")


class FirewallHelperTests(unittest.TestCase):
    """Covers the best-effort netsh firewall helper with subprocess fully mocked."""

    def test_ensure_firewall_rules_adds_missing_rules(self) -> None:
        show_missing = MagicMock(returncode=1, stdout="No rules match the specified criteria.")
        add_ok = MagicMock(returncode=0, stdout="Ok.")

        with patch.object(
            voip, "_run_hidden", side_effect=[show_missing, add_ok, show_missing, add_ok]
        ) as mock_run:
            voip.ensure_firewall_rules(5060, 10000, 10019)

        self.assertEqual(mock_run.call_count, 4)

    def test_ensure_firewall_rules_skips_existing_rules(self) -> None:
        show_present = MagicMock(returncode=0, stdout="Rule Name: AppleCalls SIP (UDP)")

        with patch.object(voip, "_run_hidden", return_value=show_present) as mock_run:
            voip.ensure_firewall_rules(5060, 10000, 10019)

        self.assertEqual(mock_run.call_count, 2)

    def test_ensure_firewall_rules_never_raises(self) -> None:
        with patch.object(voip, "_run_hidden", side_effect=OSError("no netsh")):
            try:
                voip.ensure_firewall_rules(5060, 10000, 10019)
            except Exception as exc:  # pragma: no cover - failure path
                self.fail(f"ensure_firewall_rules raised unexpectedly: {exc}")


class SipPhoneControllerTests(unittest.TestCase):
    """Covers the controller's pure/bridging logic with pyVoIP fully mocked.

    No real socket or thread-timing dependent behavior is exercised: worker
    methods are either called directly, or exercised through `connect()`/
    `dial()` against a mocked `VoIPPhone` whose blocking calls return
    immediately, then observed through the bounded `queue.get(timeout=...)`.
    """

    def _make_account(self) -> voip.SipAccount:
        return voip.SipAccount(server="sip.example.com", username="user1")

    def test_get_status_without_a_phone_is_inactive(self) -> None:
        controller = voip.SipPhoneController()
        self.assertEqual(controller.get_status(), voip.PhoneStatus.INACTIVE)

    def test_connect_raises_if_already_connected(self) -> None:
        controller = voip.SipPhoneController()
        controller._phone = MagicMock()

        with self.assertRaises(RuntimeError):
            controller.connect(self._make_account(), "secret")

    def test_connect_reports_registering_then_registered(self) -> None:
        fake_phone = MagicMock()
        fake_phone.get_status.return_value = voip.PhoneStatus.REGISTERED

        with patch.object(voip, "VoIPPhone", return_value=fake_phone), patch.object(
            voip, "ensure_firewall_rules"
        ) as mock_firewall:
            controller = voip.SipPhoneController()
            controller.connect(self._make_account(), "secret")

            self.assertEqual(
                controller.events.get(timeout=2), ("status", voip.PhoneStatus.REGISTERING)
            )
            self.assertEqual(
                controller.events.get(timeout=2), ("status", voip.PhoneStatus.REGISTERED)
            )

        fake_phone.start.assert_called_once()
        mock_firewall.assert_called_once()

    def test_connect_reports_error_and_failed_status_on_exception(self) -> None:
        fake_phone = MagicMock()
        fake_phone.start.side_effect = RuntimeError("no answer from server")

        with patch.object(voip, "VoIPPhone", return_value=fake_phone), patch.object(
            voip, "ensure_firewall_rules"
        ):
            controller = voip.SipPhoneController()
            controller.connect(self._make_account(), "secret")

            self.assertEqual(
                controller.events.get(timeout=2), ("status", voip.PhoneStatus.REGISTERING)
            )
            kind, payload = controller.events.get(timeout=2)
            self.assertEqual(kind, "error")
            self.assertEqual(
                controller.events.get(timeout=2), ("status", voip.PhoneStatus.FAILED)
            )

    def test_on_incoming_call_extracts_caller_id_and_queues_events(self) -> None:
        fake_call = MagicMock()
        fake_call.state = voip.CallState.RINGING
        fake_call.request.headers = {"From": {"number": "15551234567", "caller": "Jane"}}

        controller = voip.SipPhoneController()
        with patch.object(controller, "_watch_call") as mock_watch:
            controller._on_incoming_call(fake_call)

        self.assertEqual(
            controller.events.get_nowait(),
            ("incoming_call", {"number": "15551234567", "caller": "Jane"}),
        )
        self.assertEqual(controller.events.get_nowait(), ("call_state", voip.CallState.RINGING))
        self.assertIs(controller._current_call, fake_call)
        mock_watch.assert_called_once_with(fake_call)

    def test_on_incoming_call_tolerates_missing_from_header_fields(self) -> None:
        fake_call = MagicMock()
        fake_call.state = voip.CallState.RINGING
        fake_call.request.headers = {"From": {}}

        controller = voip.SipPhoneController()
        with patch.object(controller, "_watch_call"):
            controller._on_incoming_call(fake_call)

        kind, payload = controller.events.get_nowait()
        self.assertEqual(kind, "incoming_call")
        self.assertEqual(payload, {"number": "", "caller": ""})

    def test_answer_current_call_without_a_call_is_a_noop(self) -> None:
        controller = voip.SipPhoneController()
        controller.answer_current_call()

        with self.assertRaises(queue.Empty):
            controller.events.get_nowait()

    def test_answer_current_call_guards_invalid_state_race(self) -> None:
        fake_call = MagicMock()
        fake_call.answer.side_effect = voip.InvalidStateError("call is not ringing")

        controller = voip.SipPhoneController()
        controller._current_call = fake_call

        controller.answer_current_call()  # must not raise

        kind, _payload = controller.events.get_nowait()
        self.assertEqual(kind, "error")

    def test_decline_current_call_guards_invalid_state_race(self) -> None:
        fake_call = MagicMock()
        fake_call.deny.side_effect = voip.InvalidStateError("call is not ringing")

        controller = voip.SipPhoneController()
        controller._current_call = fake_call

        controller.decline_current_call()  # must not raise

        kind, _payload = controller.events.get_nowait()
        self.assertEqual(kind, "error")

    def test_hangup_current_call_guards_invalid_state_race(self) -> None:
        fake_call = MagicMock()
        fake_call.hangup.side_effect = voip.InvalidStateError("call is not answered")

        controller = voip.SipPhoneController()
        controller._current_call = fake_call

        controller.hangup_current_call()  # must not raise

        kind, _payload = controller.events.get_nowait()
        self.assertEqual(kind, "error")

    def test_dial_without_connection_reports_error(self) -> None:
        controller = voip.SipPhoneController()
        controller.dial("+15550001111")

        kind, _payload = controller.events.get(timeout=2)
        self.assertEqual(kind, "error")

    def test_dial_worker_tracks_the_call_and_watches_it(self) -> None:
        fake_call = MagicMock()
        fake_call.state = voip.CallState.DIALING
        fake_phone = MagicMock()
        fake_phone.call.return_value = fake_call

        controller = voip.SipPhoneController()
        with patch.object(controller, "_watch_call") as mock_watch:
            controller._dial_worker(fake_phone, "+15550001111")

        fake_phone.call.assert_called_once_with("+15550001111")
        self.assertIs(controller._current_call, fake_call)
        self.assertEqual(
            controller.events.get_nowait(), ("call_state", voip.CallState.DIALING)
        )
        mock_watch.assert_called_once_with(fake_call)

    def test_dial_worker_reports_error_when_call_raises(self) -> None:
        fake_phone = MagicMock()
        fake_phone.call.side_effect = voip.NoPortsAvailableError("no RTP ports free")

        controller = voip.SipPhoneController()
        controller._dial_worker(fake_phone, "+15550001111")

        kind, _payload = controller.events.get_nowait()
        self.assertEqual(kind, "error")
        self.assertIsNone(controller._current_call)

    def test_second_incoming_call_is_denied_while_one_is_active(self) -> None:
        """A second ringing call must never silently replace the tracked one.

        Regression test: overwriting `_current_call` orphaned the first call
        (no longer reachable from answer/decline/hangup) while its audio
        bridge threads kept running.
        """

        first_call = MagicMock()
        first_call.state = voip.CallState.RINGING
        first_call.request.headers = {"From": {"number": "111", "caller": ""}}

        second_call = MagicMock()
        second_call.state = voip.CallState.RINGING
        second_call.request.headers = {"From": {"number": "222", "caller": ""}}

        controller = voip.SipPhoneController()
        with patch.object(controller, "_watch_call"):
            controller._on_incoming_call(first_call)
            controller._on_incoming_call(second_call)

        self.assertIs(controller._current_call, first_call)
        second_call.deny.assert_called_once()

    def test_incoming_call_replaces_tracker_once_previous_call_ended(self) -> None:
        first_call = MagicMock()
        first_call.state = voip.CallState.ENDED
        first_call.request.headers = {"From": {"number": "111", "caller": ""}}

        second_call = MagicMock()
        second_call.state = voip.CallState.RINGING
        second_call.request.headers = {"From": {"number": "222", "caller": ""}}

        controller = voip.SipPhoneController()
        with patch.object(controller, "_watch_call"):
            controller._on_incoming_call(first_call)
            controller._current_call = first_call  # simulate the prior call having ended
            controller._on_incoming_call(second_call)

        self.assertIs(controller._current_call, second_call)
        second_call.deny.assert_not_called()

    def test_start_audio_bridge_uses_a_fresh_event_each_call(self) -> None:
        """Regression test: reusing/clearing one shared Event across calls let a
        still-shutting-down previous call's audio thread have its stop signal
        silently un-set by the next call's start."""

        controller = voip.SipPhoneController()
        with patch.object(voip.threading, "Thread") as mock_thread:
            mock_thread.return_value = MagicMock()

            controller._start_audio_bridge(MagicMock())
            first_event = controller._audio_stop_event

            controller._start_audio_bridge(MagicMock())
            second_event = controller._audio_stop_event

        self.assertIsNot(first_event, second_event)
        self.assertFalse(second_event.is_set())


if __name__ == "__main__":
    unittest.main()
