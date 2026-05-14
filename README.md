# Anything Auto

Windows 优先的跨应用轻量 RPA 桌面客户端：Excel 批量驱动、流程 DSL、SQLite 持久化、执行日志与可选录制/浏览器步骤。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

开发与本机测试：

```bash
pip install -e ".[dev]"
python -m pytest -q
```

可选能力：

- **浏览器（Playwright / CDP）**：`pip install -e ".[browser]"` 并执行 `playwright install chromium`
- **录制 Tab（pynput）**：`pip install -e ".[recorder]"`
- **打包**：见 [`docs/BUILD.md`](docs/BUILD.md)

更完整的运行说明见 [`docs/RUN.md`](docs/RUN.md)；打包与 PyInstaller 见 [`docs/BUILD.md`](docs/BUILD.md)；验收项见 [`docs/ACCEPTANCE_CHECKLIST.md`](docs/ACCEPTANCE_CHECKLIST.md)。

## 仓库说明

- 包名：`anything-auto`（`pyproject.toml`）
- 详细需求与背景草案：[`project.md`](project.md)
- 阶段规划：`docs/DEVELOPMENT_PLAN.md` · 立项章程：`docs/PROJECT_CHARTER.md`
