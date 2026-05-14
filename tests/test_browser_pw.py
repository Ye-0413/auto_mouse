from __future__ import annotations

from unittest.mock import MagicMock, patch

from rpa_assistant.app.automation import browser_pw
from rpa_assistant.app.automation.browser_pw import PlaywrightSession


def test_run_pw_goto_requires_cdp() -> None:
    r = browser_pw.run_pw_goto(
        url="https://example.com",
        cdp_url=None,
        default_cdp_url=None,
    )
    assert not r.ok
    assert "CDP" in r.message


def test_run_pw_goto_install_hint_on_import_failure() -> None:
    with patch.object(browser_pw, "_try_import_playwright", return_value=(None, "No module named playwright")):
        r = browser_pw.run_pw_goto(
            url="https://example.com",
            cdp_url="http://127.0.0.1:9222",
            default_cdp_url=None,
        )
    assert not r.ok
    assert "pip install" in r.message


def test_playwright_session_reuses_browser() -> None:
    mock_page = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser = MagicMock()
    mock_browser.contexts = [mock_ctx]

    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.connect_over_cdp.return_value = mock_browser
    entry = MagicMock()
    entry.start.return_value = mock_pw_instance
    fake_sp = MagicMock(return_value=entry)

    with patch.object(browser_pw, "_try_import_playwright", return_value=(fake_sp, None)):
        session = PlaywrightSession()
        try:
            r1 = session.run_step(
                "pw_goto",
                {"url": "https://a.example", "cdp_url": "http://127.0.0.1:1"},
                default_cdp_url=None,
            )
            r2 = session.run_step(
                "pw_click_text",
                {"text": "OK", "cdp_url": "http://127.0.0.1:1"},
                default_cdp_url=None,
            )
        finally:
            session.close()

    assert r1.ok and r2.ok
    mock_pw_instance.chromium.connect_over_cdp.assert_called_once()
    mock_page.goto.assert_called_once()
    mock_page.get_by_text.return_value.first.click.assert_called_once()


def test_playwright_session_unknown_step() -> None:
    mock_page = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser = MagicMock()
    mock_browser.contexts = [mock_ctx]
    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.connect_over_cdp.return_value = mock_browser
    entry = MagicMock()
    entry.start.return_value = mock_pw_instance
    fake_sp = MagicMock(return_value=entry)

    with patch.object(browser_pw, "_try_import_playwright", return_value=(fake_sp, None)):
        session = PlaywrightSession()
        try:
            r = session.run_step(
                "pw_nope",
                {"cdp_url": "http://127.0.0.1:1"},
                default_cdp_url=None,
            )
        finally:
            session.close()
    assert not r.ok
