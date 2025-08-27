# Agent Guidelines

- Run `pytest` before committing any code.
- Do not commit real credentials. The `.env` file in the repo holds placeholder values for packaging.
- Tests rely on `KIDUM_USERNAME` and `KIDUM_PASSWORD`; set them locally when running tests but keep them out of commits.
- Packaging uses PyInstaller via `build/message_automation.spec`; update the spec if entry points change.
- The application targets local desktop use; keep documentation focused on local execution rather than cloud deployment.
- Use `scripts/make_installer.sh` to bundle the PyInstaller build into a self-extracting installer. Keep `dist/` and `installer/` out of commits.
