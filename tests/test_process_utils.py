import os
import subprocess
import unittest

from applecalls.process_utils import merge_hidden_process_kwargs


@unittest.skipUnless(os.name == "nt", "Windows-only subprocess flags")
class WindowsHiddenProcessTests(unittest.TestCase):
    """Ensures background helpers stay silent in the packaged GUI app."""

    def test_hidden_process_kwargs_hide_console_windows(self) -> None:
        kwargs = merge_hidden_process_kwargs()

        self.assertIn("creationflags", kwargs)
        self.assertIn("startupinfo", kwargs)
        self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)
        self.assertTrue(kwargs["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW)
        self.assertEqual(kwargs["startupinfo"].wShowWindow, subprocess.SW_HIDE)

    def test_existing_creationflags_are_preserved(self) -> None:
        kwargs = merge_hidden_process_kwargs(creationflags=0x200)

        self.assertTrue(kwargs["creationflags"] & 0x200)
        self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)
