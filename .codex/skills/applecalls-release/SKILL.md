---
name: applecalls-release
description: Versioning, build, tag, and push workflow for the AppleCalls project. Use when Codex needs to bump the Vx.x.x version, keep source and README aligned, rebuild the Windows executable with the local icon, prepare a conventional commit, or push tags and code to GitHub for this repository.
---

# AppleCalls Release

## Overview

Keep AppleCalls release-ready without drifting version strings, build artifacts,
or git metadata.

## Workflow

1. Read `applecalls/__init__.py`, `README.md`, `scripts/build_exe.ps1`, and
   `docs/spec-driven-development.md` before changing release state.
2. Determine whether the change is `patch`, `minor`, or `major`.
3. Keep the selected version aligned in:
   - `applecalls/__init__.py`
   - `README.md`
   - executable name produced by `scripts/build_exe.ps1`
   - git tag
4. Run the local validation steps before building:
   - `python -m unittest discover -s tests`
   - `python -m compileall .`
5. Build the executable with:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`
6. Summarize the exact commit message, tag, and push commands that match the
   selected version.

## Constraints

- Do not claim that AppleCalls reproduces the private Mac Wi-Fi relay on
  Windows.
- Prefer the existing build script instead of hand-written PyInstaller
  commands.
- If git is not initialized yet, initialize it before preparing commit/tag/push
  steps.
- If a GitHub remote is missing, create or connect `origin` before pushing.

