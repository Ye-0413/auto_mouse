# Anything Auto — 运行说明

## 环境

- Python **3.11+**（推荐与 `pyproject.toml` 一致）。
- **macOS / Windows / Linux** 均可启动界面；桌面自动化（模拟键鼠、窗口）以 **Windows** 验收为主。

## 安装

```bash
cd /path/to/Anything_Auto
pip install -r requirements.txt
```

可选：通过 CDP 控制已打开的 Chromium/Chrome（Playwright）：

```bash
pip install "anything-auto[browser]"
playwright install chromium
```

## 启动

```bash
python main.py
```

首次运行会在用户数据目录创建 `data/app.sqlite3`、日志与截图目录（见 `rpa_assistant/paths.py`，可通过环境变量覆盖）。

## 配置提示

- **配置** 页中的 **浏览器 CDP 地址**（如 `http://127.0.0.1:9222`）会传给流程中的 `pw_goto` / `pw_click_text` 步骤；步骤内也可单独填写 **CDP 覆盖**。
- 使用 CDP 前请用远程调试参数启动 Chrome/Chromium，并保持窗口打开。

## 开发自检

```bash
pip install -e ".[dev]"
python -m pytest -q
```
