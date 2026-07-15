"""Helpers for launching Windows subprocesses without visible console windows."""

from __future__ import annotations

import os
import subprocess
from typing import Any


def merge_hidden_process_kwargs(**kwargs: Any) -> dict[str, Any]:
    """Merges subprocess kwargs with Windows flags that suppress child consoles."""

    merged = dict(kwargs)

    if os.name != "nt":
        return merged

    # Tkinter apps bundled with `pythonw` or PyInstaller `--windowed` can still
    # flash separate console windows when they spawn `powershell`, `winget`, or
    # other console tools. These flags keep those helpers fully silent.
    creation_flag = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)

    if creation_flag:
        merged["creationflags"] = int(merged.get("creationflags", 0)) | creation_flag

    if startupinfo_factory is not None and "startupinfo" not in merged:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0))
        startupinfo.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
        merged["startupinfo"] = startupinfo

    return merged
