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

**`build/`** stays gitignored (regenerable PyInstaller scratch). The versioned GUI bundle may live under **`dist/Anything_Auto/`** (tracked with **Git LFS** — see repo `.gitattributes`). Run `git lfs install` once, then `git lfs track` is already implied by attributes; add/commit that folder only after a clean `pyinstaller` build. Hosts such as GitHub reject plain Git blobs **>100 MB**; LFS (or release ZIPs) is required for the bundled Qt WebEngine DLLs.

For a **fully offline** machine: copy the whole `dist/Anything_Auto/` directory (or install from a release archive). No network is required at runtime for core features (SQLite, desktop steps). Optional extras still need their own offline prep: Playwright ships with your build only if you bundle Chromium into the folder yourself; `open_url` may still invoke a browser that must exist locally.

## Smoke test after build

1. Launch the bundled app from `dist/Anything_Auto/`.
2. Confirm sidebar navigation loads and SQLite initializes under the configured data directory (`ANYTHING_AUTO_DATA_DIR` or default user path).
3. Optional: open **流程**, save a trivial flow, then **运行** executes it once.

See also `docs/RUN.md` and `docs/ACCEPTANCE_CHECKLIST.md`.
