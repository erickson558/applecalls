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
- Validate Phone Link runtime state, not only installation state
- Prefer patch-level fixes unless scope clearly expands
- Use `applecalls-code-commenter` when the user wants each part explained
- Use `applecalls-stability-fix` when the request is a real bug fix with validation and release follow-through

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
- Tag the same version that the GUI shows
- Prefer conventional commits
- Use `applecalls-release` and require `erickson558` as the active GitHub account before any push

## 3. Stability and Release Guard

Purpose:

- Drive root-cause debugging instead of blind fixes
- Protect current behavior while correcting real defects
- Keep version, build, commit, tag, and push steps aligned
- Stop remote actions when the wrong GitHub account is active

Suggested skills:

- Use `applecalls-stability-fix` for the end-to-end workflow
- Use `applecalls-code-commenter` if the changed code must be more understandable
- Use `applecalls-release` when the fix is ready to package and publish
