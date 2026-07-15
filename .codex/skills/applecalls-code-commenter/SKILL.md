---
name: applecalls-code-commenter
description: Code-commenting and maintainability workflow for the AppleCalls Python project. Use when Codex edits GUI, diagnostics, logic, or build files and needs to keep each important part understandable with docstrings and focused comments while preserving current behavior.
---

# AppleCalls Code Commenter

## Overview

Keep AppleCalls readable for future maintenance without flooding the codebase
with noisy comments.

## Workflow

1. Read the target file fully before adding comments.
2. Prefer module, class, and function docstrings for broad explanations.
3. Add inline comments only around logic that is easy to misuse or hard to infer:
   - background-thread GUI coordination
   - PowerShell or `netsh` parsing
   - Phone Link runtime-state parsing and calls-entry detection
   - build/version synchronization
4. Preserve behavior first. If the comment reveals unclear logic, fix the code
   and the comment together.
5. If edits change behavior, update tests or docs in the same pass.

## Constraints

- Do not add filler comments that merely restate Python syntax.
- Keep comments short and concrete.
- Preserve compatibility with the current Windows/Tkinter flow.
- When the user asks what each part does, prefer docstrings plus comments in the
  non-obvious sections instead of line-by-line narration everywhere.
