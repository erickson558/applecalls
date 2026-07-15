"""Unit tests for Phone Link runtime-state parsing."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from applecalls.diagnostics import PhoneLinkInfo, _populate_phone_link_runtime_info


class PhoneLinkRuntimeParsingTests(unittest.TestCase):
    """Verifies that local Phone Link companion state is parsed safely."""

    def test_companion_state_exposes_calls_and_recent_items(self) -> None:
        payload = {
            "speak": "iPhone 14 Pro Max - Connected to your PC",
            "companionProperties": {"tag": "device-ios"},
            "body": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Open Phone Link",
                    "url": "ms-phone:?cid=test",
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Calls",
                    "url": "ms-phone:calling?startScenarioId=feature_calling",
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Incoming call from Test",
                    "url": "ms-phone:calling?startScenarioId=recent_call&targetnumber=1",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "StartMenuCompanion.json"
            state_path.write_text(json.dumps(payload), encoding="utf-8")

            with patch("applecalls.diagnostics._get_companion_state_path", return_value=state_path):
                info = _populate_phone_link_runtime_info(
                    PhoneLinkInfo(installed=True, version="1.0"),
                    [],
                )

        self.assertEqual(info.connected_device_name, "iPhone 14 Pro Max")
        self.assertEqual(info.device_tag, "device-ios")
        self.assertEqual(info.calls_uri, "ms-phone:calling?startScenarioId=feature_calling")
        self.assertEqual(info.launch_uri, "ms-phone:?cid=test")
        self.assertEqual(info.recent_call_titles, ["Incoming call from Test"])


if __name__ == "__main__":
    unittest.main()
