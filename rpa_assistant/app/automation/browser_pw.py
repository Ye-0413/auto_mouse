"""Optional Playwright automation over Chrome CDP; imports playwright lazily."""

from __future__ import annotations

from typing import Any, Callable

from rpa_assistant.app.automation.result import ActionResult

_INSTALL_HINT = (
    "浏览器步骤需要可选依赖：pip install 'anything-auto[browser]' "
    "（或 pip install playwright>=1.40），然后执行 playwright install chromium。"
)


def _try_import_playwright() -> tuple[Callable[..., Any] | None, str | None]:
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright, None
    except ImportError as exc:
        return None, str(exc)


def _resolve_cdp_url(
    cdp_url: str | None,
    default_cdp_url: str | None,
) -> str | None:
    u = (cdp_url or "").strip() or (default_cdp_url or "").strip()
    return u or None


def _pick_page(context: Any) -> Any | None:
    if not context:
        return None
    pages = getattr(context, "pages", None) or []
    if pages:
        return pages[0]
    try:
        return context.new_page()
    except Exception:
        return None


def run_pw_goto(
    *,
    url: str,
    cdp_url: str | None,
    default_cdp_url: str | None,
    timeout_ms: int = 30_000,
) -> ActionResult:
    target_cdp = _resolve_cdp_url(cdp_url, default_cdp_url)
    if not target_cdp:
        return ActionResult(
            False,
            "pw_goto：未配置 CDP 地址（步骤 params.cdp_url 或配置中的 browser_cdp_url）",
        )
    u = url.strip()
    if not u:
        return ActionResult(False, "pw_goto：url 为空")

    sp_factory, imp_err = _try_import_playwright()
    if sp_factory is None:
        return ActionResult(False, f"{_INSTALL_HINT}（导入失败: {imp_err}）")

    try:
        with sp_factory() as p:
            browser = p.chromium.connect_over_cdp(target_cdp)
            try:
                if not browser.contexts:
                    return ActionResult(False, "pw_goto：未找到浏览器上下文")
                page = _pick_page(browser.contexts[0])
                if page is None:
                    return ActionResult(False, "pw_goto：无法获取页面对象")
                page.goto(u, timeout=timeout_ms)
            finally:
                browser.close()
        return ActionResult(True)
    except Exception as exc:
        return ActionResult(False, str(exc))


def run_pw_click_text(
    *,
    text: str,
    cdp_url: str | None,
    default_cdp_url: str | None,
    timeout_ms: int = 30_000,
) -> ActionResult:
    target_cdp = _resolve_cdp_url(cdp_url, default_cdp_url)
    if not target_cdp:
        return ActionResult(
            False,
            "pw_click_text：未配置 CDP 地址（步骤 params.cdp_url 或配置中的 browser_cdp_url）",
        )
    label = text.strip()
    if not label:
        return ActionResult(False, "pw_click_text：text 为空")

    sp_factory, imp_err = _try_import_playwright()
    if sp_factory is None:
        return ActionResult(False, f"{_INSTALL_HINT}（导入失败: {imp_err}）")

    try:
        with sp_factory() as p:
            browser = p.chromium.connect_over_cdp(target_cdp)
            try:
                if not browser.contexts:
                    return ActionResult(False, "pw_click_text：未找到浏览器上下文")
                page = _pick_page(browser.contexts[0])
                if page is None:
                    return ActionResult(False, "pw_click_text：无法获取页面对象")
                page.get_by_text(label).first.click(timeout=timeout_ms)
            finally:
                browser.close()
        return ActionResult(True)
    except Exception as exc:
        return ActionResult(False, str(exc))


class PlaywrightSession:
    """One CDP connection reused for consecutive ``pw_*`` steps in a single flow run."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._cdp_url: str | None = None

    def close(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._cdp_url = None

    def run_step(
        self,
        step_type: str,
        params: dict[str, Any],
        *,
        default_cdp_url: str | None,
    ) -> ActionResult:
        raw_cdp = params.get("cdp_url")
        cdp_part = str(raw_cdp).strip() if raw_cdp else None
        target_cdp = _resolve_cdp_url(cdp_part, default_cdp_url)
        if not target_cdp:
            return ActionResult(
                False,
                f"{step_type}：未配置 CDP 地址（步骤 params.cdp_url 或配置中的 browser_cdp_url）",
            )

        sp_factory, imp_err = _try_import_playwright()
        if sp_factory is None:
            return ActionResult(False, f"{_INSTALL_HINT}（导入失败: {imp_err}）")

        try:
            if self._playwright is None:
                self._playwright = sp_factory().start()
            if self._browser is None or self._cdp_url != target_cdp:
                if self._browser is not None:
                    self._browser.close()
                    self._browser = None
                self._browser = self._playwright.chromium.connect_over_cdp(
                    target_cdp,
                )
                self._cdp_url = target_cdp

            if not self._browser.contexts:
                return ActionResult(False, f"{step_type}：未找到浏览器上下文")
            page = _pick_page(self._browser.contexts[0])
            if page is None:
                return ActionResult(False, f"{step_type}：无法获取页面对象")

            timeout_ms = int(params.get("timeout_ms", 30_000))
            st = (step_type or "").strip()
            if st == "pw_goto":
                u = str(params.get("url", "")).strip()
                if not u:
                    return ActionResult(False, "pw_goto：url 为空")
                page.goto(u, timeout=timeout_ms)
                return ActionResult(True)
            if st == "pw_click_text":
                label = str(params.get("text", "")).strip()
                if not label:
                    return ActionResult(False, "pw_click_text：text 为空")
                page.get_by_text(label).first.click(timeout=timeout_ms)
                return ActionResult(True)
            if st == "pw_inner_text":
                css_sel = str(
                    params.get("css", "") or params.get("selector", "") or "",
                ).strip()
                text_label = str(params.get("text", "")).strip()
                nth_raw = params.get("nth", 0)
                try:
                    nth_i = max(0, int(nth_raw))
                except (TypeError, ValueError):
                    nth_i = 0
                exact = bool(params.get("exact", False))
                loc: Any
                if css_sel:
                    loc = page.locator(css_sel).nth(nth_i)
                elif text_label:
                    loc = page.get_by_text(text_label, exact=exact).nth(nth_i)
                else:
                    return ActionResult(
                        False,
                        "pw_inner_text：需要 params.text（可见文案）或 params.css（选择器）",
                    )
                inner = loc.inner_text(timeout=timeout_ms)
                stripped = (inner or "").strip()
                return ActionResult(True, "", value=stripped)
            return ActionResult(False, f"未知 Playwright 步骤: {st}")
        except Exception as exc:
            return ActionResult(False, str(exc))
