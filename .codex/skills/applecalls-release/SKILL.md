---
name: applecalls-release
description: Versioning, build, tag, and push workflow for the AppleCalls project. Use when Codex needs to bump the Vx.x.x version, keep source and README aligned, rebuild the Windows executable with the local icon, prepare a conventional commit, or push tags and code to GitHub for this repository. Before any push, verify that the active GitHub CLI account is `erickson558`; if another account is active, stop and ask the user to log in or switch accounts.
---

# AppleCalls Release

## Overview

Keep AppleCalls release-ready without drifting version strings, build artifacts,
or git metadata.

## Workflow

1. Read `applecalls/__init__.py`, `README.md`, `scripts/build_exe.ps1`, and
   `docs/spec-driven-development.md` before changing release state.
2. Determine whether the change is `patch`, `minor`, or `major`.
3. Check GitHub identity before any remote action:
   - Run `gh auth status`
   - Require the active account to be `erickson558`
   - If `erickson558` is not active, stop and ask the user to log in or switch
4. When `origin` is missing, create or reconnect it only for the intended `erickson558` repository.
5. Keep the selected version aligned in:
   - `applecalls/__init__.py`
   - `README.md`
   - executable name produced by `scripts/build_exe.ps1`
   - git tag
6. Run the local validation steps before building:
   - `python -m unittest discover -s tests`
   - `python -m compileall .`
   - Confirm the Phone Link diagnostic still reports calls-entry and hands-free state without crashing
7. Build the executable with:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`
8. Summarize the exact commit message, tag, and push commands that match the
   selected version.

## Constraints

- Do not claim that AppleCalls reproduces the private Mac Wi-Fi relay on
  Windows.
- Keep the release flow aligned with the current Phone Link runtime validation,
  including direct access to the Calls experience when available.
- Do not reuse a stale or wrong GitHub remote. The previous incorrect account
  must not be used for future pushes.
- Prefer the existing build script instead of hand-written PyInstaller
  commands.
- If git is not initialized yet, initialize it before preparing commit/tag/push
  steps.
- If a GitHub remote is missing, create or connect `origin` before pushing, but
  only after confirming the intended `erickson558` destination.
