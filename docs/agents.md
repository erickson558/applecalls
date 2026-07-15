# Recommended Agents

## 1. Python QA Stabilizer

Purpose:

- Review GUI behavior
- Detect regressions
- Find blocking operations on the main thread
- Improve error handling without changing supported behavior

Suggested skills:

- Read the project spec in `docs/spec-driven-development.md`
- Preserve current features
- Prefer patch-level fixes unless scope clearly expands
- Add comments and docstrings when they improve maintainability

## 2. Release and GitHub Manager

Purpose:

- Keep version `Vx.x.x` consistent
- Build the Windows `.exe`
- Prepare commits, tags, and push steps
- Keep GitHub release artifacts aligned with the app version

Suggested skills:

- Read version from `applecalls/__init__.py`
- Use `scripts/build_exe.ps1` for repeatable builds
- Tag the same version that the GUI shows
- Prefer conventional commits

