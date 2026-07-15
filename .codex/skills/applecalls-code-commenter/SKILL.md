---
name: applecalls-code-commenter
description: Code-commenting and maintainability workflow for the AppleCalls Python project. Use when Codex edits GUI, diagnostics, logic, tests, or build files and the user wants to understand what each part does. Add docstrings and focused comments that explain each important section without changing current behavior.
---

# AppleCalls Code Commenter

## Overview

Keep AppleCalls readable for future maintenance without flooding the codebase
with noisy comments.

## Workflow

1. Read the target file fully before adding comments.
2. Add or improve module docstrings when they help explain the file's purpose.
3. Prefer class and function docstrings for broad explanations of responsibility,
   inputs, outputs, and side effects.
4. When the user explicitly wants to know what each part does, ensure each
   important section has at least one of:
   - a docstring
   - a short block comment above the section
   - a clear variable or helper name introduced during the same edit
5. Add inline comments only around logic that is easy to misuse or hard to infer:
   - background-thread GUI coordination
   - PowerShell or `netsh` parsing
   - Phone Link runtime-state parsing and calls-entry detection
   - validation and version-sync decisions
   - build/version synchronization
6. Preserve behavior first. If the comment reveals unclear logic, fix the code
   and the comment together.
7. If edits change behavior, update tests or docs in the same pass.

## Constraints

- Do not add filler comments that merely restate Python syntax.
- Keep comments short and concrete.
- Preserve compatibility with the current Windows/Tkinter flow.
- When the user asks what each part does, explain each logical block, but avoid
  turning every single line into noise.
