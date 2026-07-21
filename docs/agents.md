# Recommended Agents

## 0. Before touching Bluetooth/Continuity requests

If a request asks to "remove Phone Link" or "make calls autonomous like the
Mac" by going through Bluetooth (HFP/ANCS) or a Wi-Fi replica of Apple
Continuity: read the "Investigation history" section of
`docs/spec-driven-development.md` first. Both paths were tested on real
hardware and are dead ends on Windows (Windows itself reserves the HFP AT
channel and BLE ANCS for its own first-party stack; Continuity Calls'
signaling requires Apple ID-authenticated push credentials no third party
can obtain). Do not re-attempt them from scratch -- point back to the SDD and
to the SIP/VoIP softphone as the actual independent path.

## 1. Python QA Stabilizer

Purpose:

- Review GUI behavior
- Detect regressions
- Find blocking operations on the main thread (including SIP registration,
  firewall setup, and the audio-bridge threads in `applecalls/voip.py`)
- Improve error handling without changing supported behavior

Suggested skills:

- Read the project spec in `docs/spec-driven-development.md`
- Preserve current features (both the Phone Link diagnostics panel and the
  SIP softphone)
- Validate Phone Link runtime state, not only installation state
- Validate that SIP account changes, connect/disconnect, and call actions
  never block the Tk thread and never leave a stale audio thread or
  registration behind
- Prefer patch-level fixes unless scope clearly expands
- Use `applecalls-code-commenter` when the user wants each part explained
- Use `applecalls-stability-fix` when the request is a real bug fix with
  validation and release follow-through

## 2. Release and GitHub Manager

Purpose:

- Keep version `Vx.x.x` consistent
- Build the Windows `.exe`
- Prepare commits, tags, and push steps
- Keep GitHub release artifacts aligned with the app version

Suggested skills:

- Read version from `applecalls/__init__.py`
- Use `scripts/build_exe.ps1` for repeatable builds
- Run tests before rebuilding and pushing
- After a build that touches `applecalls/voip.py` or its dependencies,
  actually launch the produced `.exe` once and confirm the main window
  appears (frozen-import smoke test for `pyVoIP`/`sounddevice`/`keyring`) --
  do not assume `python -m compileall` catches a PyInstaller bundling gap
- Tag the same version that the GUI shows
- Prefer conventional commits
- Use `applecalls-release` and require `erickson558` as the active GitHub
  account before any push

## 3. Stability and Release Guard

Purpose:

- Drive root-cause debugging instead of blind fixes
- Protect current behavior while correcting real defects
- Keep version, build, commit, tag, and push steps aligned
- Stop remote actions when the wrong GitHub account is active

Suggested skills:

- Use `applecalls-stability-fix` for the end-to-end workflow
- Use `applecalls-code-commenter` if the changed code must be more
  understandable
- Use `applecalls-release` when the fix is ready to package and publish
