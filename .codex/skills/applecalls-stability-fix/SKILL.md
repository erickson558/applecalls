---
name: applecalls-stability-fix
description: Root-cause-first bug-fix, QA, and release workflow for the AppleCalls Python project. Use when Codex needs to review, validate, and correct real bugs in the existing Windows desktop app without breaking current behavior, add targeted tests or validations, align Vx.x.x versioning across source and README, rebuild the executable, prepare a conventional commit, or push through the correct GitHub account.
---

# AppleCalls Stability Fix

## Overview

Stabilize AppleCalls without blind fixes. Analyze first, preserve supported
behavior, validate the correction, align versioning, and do not push unless the
active GitHub account is `erickson558`.

## Workflow

1. Reproduce or inspect the bug first.
2. Identify the root cause, user impact, and regression risk before editing.
3. Fix the smallest correct surface that resolves the real issue.
4. Validate locally with tests, compile checks, and relevant app-specific smoke checks.
5. Align versioning and release artifacts when behavior changed.
6. Prepare commit, tag, and push only after confirming the correct GitHub account.

## Analysis Phase

- Inspect the current implementation before proposing a fix.
- List the concrete problems found:
  - functional bugs
  - logic errors
  - exception-handling gaps
  - GUI freeze or concurrency risks
  - versioning or release drift
- Explain for each issue:
  - root cause
  - user impact
  - correction risk
- Do not patch speculative causes. If the cause is not yet clear, keep analyzing.

## Correction Phase

- Preserve all working features.
- Prefer patch-level fixes unless the scope clearly expands.
- Add or improve comments and docstrings when they make the changed code easier to understand.
- When the fix touches UI or diagnostics, keep the Tkinter thread responsive and keep PowerShell parsing defensive.
- Update docs, tests, skills, or agents in the same pass when the fix changes their assumptions.

## Validation Phase

- Run at least:
  - `python -m unittest discover -s tests`
  - `python -m compileall .`
- If the change affects packaging, rebuild with:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`
  - Then actually launch the produced `.exe` and confirm the main window
    appears before declaring the build good -- `compileall`/unit tests run
    against source, not the frozen bundle, and `pyVoIP`/`sounddevice`/
    `keyring` have known PyInstaller bundling gotchas (dynamic backend
    resolution, bundled native DLLs) that only a real frozen run catches.
- If the change affects Phone Link logic, confirm the diagnostics still report the calls entry and calling profiles without crashing.
- If the change affects `applecalls/voip.py` or the SIP GUI panel, confirm:
  - no new blocking call was added to a Tk button/close handler (SIP
    registration, firewall rule setup, and `phone.start()`/`phone.stop()`
    must run on a background thread, reported back through
    `SipPhoneController.events` + `self.after(...)`, exactly like the
    existing diagnostics queue pattern)
  - a second incoming call while one is active is still denied, not
    silently tracked over the first one
  - the SIP password still never reaches the on-disk JSON config, a log
    line, or an exception message shown to the user
- If validation cannot be completed, state exactly what was not run and why.

## Versioning Phase

- Use `Vx.x.x`.
- Choose the increment deliberately:
  - `patch` for fixes
  - `minor` for backward-compatible feature work
  - `major` for breaking changes
- Keep the chosen version aligned in:
  - `applecalls/__init__.py`
  - `README.md`
  - generated executable name
  - commit/tag text when applicable

## GitHub Guardrails

- Run `gh auth status` before any push.
- Require the active account to be `erickson558`.
- If another account is active, stop and ask the user to log in or switch accounts.
- Do not recreate the previous wrong remote.
- If `origin` is missing, connect it only after the intended `erickson558` repository is confirmed.

## Release Output

- When the user asks for a full closeout, answer in this order:
  1. Analysis of errors
  2. Changes made
  3. New version
  4. Updated code or file references
  5. Commit message
  6. Step-by-step git commands
