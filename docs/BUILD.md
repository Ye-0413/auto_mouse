# Building Anything Auto (GUI)

Windows is the primary deployment target; builds can be produced from macOS/Linux for smoke-testing, but **always validate on a Windows machine** before release.

## Prerequisites

- Python **3.11+**
- Git checkout of this repository

## Virtual environment

```bash
cd /path/to/Anything_Auto
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev,packaging]"
```

Optional groups:

- `browser` — Playwright steps (`pip install -e ".[browser]"` then `playwright install chromium`).
- `recorder` — `pynput` for the **录制** tab (`pip install -e ".[recorder]"`).

## PyInstaller (one-folder)

From the repo root (with the venv activated):

```bash
pyinstaller anything_auto.spec
```

**Output:** `dist/Anything_Auto/` — run `Anything_Auto.exe` (Windows) or the generated executable inside that folder on other platforms.

Prefer **one-folder** (`COLLECT` in the spec) for faster cold start on Windows versus one-file extraction.

### Known pitfalls

| Issue | Mitigation |
|--------|------------|
| PySide6 plugins/Qt DLLs missing | The spec uses `collect_all('PySide6')` to bundle Qt libs and imports; if a plugin error appears, add the missing submodule under `hiddenimports` in `anything_auto.spec`. |
| `ModuleNotFoundError` at runtime | Add the package to `hiddenimports` or `--hidden-import` once; heavy deps (Playwright browsers, `pynput` listeners) may need extra manual bundling or remain optional post-install. |
| macOS code signing / Gatekeeper | Sign/notarize separately for distribution; dev builds are unsigned. |
| Antivirus false positives (one-file) | Prefer one-folder; avoid UPX if AV complains (`upx=False` in spec). |

Clean rebuild:

```bash
rm -rf build dist
pyinstaller anything_auto.spec
```

Artifacts **`dist/`** and **`build/`** are gitignored — do not commit them.

## Smoke test after build

1. Launch the bundled app from `dist/Anything_Auto/`.
2. Confirm tabs load and SQLite initializes under the configured data directory (`ANYTHING_AUTO_DATA_DIR` or default user path).
3. Optional: open **流程**, create a trivial flow, save.

See also `docs/RUN.md` and `docs/ACCEPTANCE_CHECKLIST.md`.
