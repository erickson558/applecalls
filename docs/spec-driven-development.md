# Spec-Driven Development

## Product intent

Build a Windows desktop utility in Python that answers a practical question:

`Can this PC use my iPhone calls, and if not, why not?`

## Core constraint

Apple's native Continuity calling flow is private to the Apple ecosystem.
Windows does not expose a supported Apple API that lets a third-party Python
program receive iPhone calls the way a Mac does over the same Wi-Fi network.

That makes the following a non-goal:

- Re-implement Apple's private Mac call relay on Windows

## Supported scope

- Diagnose whether the Windows-supported path is available
- Inspect Windows version, Phone Link, Bluetooth, and local network state
- Inspect whether Phone Link already exposes its local Calls entry point for the connected iPhone
- Distinguish generic Bluetooth availability from the hands-free profile required for call control
- Detect external Bluetooth audio devices that can prevent Phone Link from presenting an answer-call UI
- Explain the technical limitation clearly
- Provide a stable GUI that does not freeze during diagnostics
- Produce a reproducible Windows `.exe`

## Quality requirements

- Keep current features working
- Avoid blocking the GUI thread with shell diagnostics
- Fail gracefully when PowerShell or netsh commands return incomplete data
- Keep version strings aligned between source, README, build artifact, tag, and commit

## Acceptance criteria

- The GUI launches without crashing on Windows 11
- Running diagnostics keeps the window responsive
- The report includes Windows, Phone Link, Bluetooth, and network details
- The report includes whether Phone Link exposes the Calls view and whether a Bluetooth hands-free profile is present
- The report identifies external Bluetooth audio blockers when they are likely to interfere with incoming-call handling
- The app explicitly states that same-Wi-Fi alone does not unlock Mac-style calling on Windows
- The GUI can open Phone Link directly into the Calls experience when Windows exposes that route
- The project can generate an `.exe` in the project root using the local `.ico`
