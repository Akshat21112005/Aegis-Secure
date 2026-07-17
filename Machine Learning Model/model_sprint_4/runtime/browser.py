from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, Response, async_playwright


@dataclass
class BrowserSession:
    """Live Playwright session shared by all Runtime collectors."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


async def create_session(
    *,
    headless: bool = True,
    ignore_https_errors: bool = True,
) -> BrowserSession:
    """Launch Chromium and return a fresh browser context and page."""

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(ignore_https_errors=ignore_https_errors)
    page = await context.new_page()
    return BrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
    )


async def navigate(
    session: BrowserSession,
    url: str,
    *,
    timeout_ms: int = 30_000,
) -> dict[str, Any]:
    """Navigate the shared page and return a normalized navigation summary."""

    try:
        response: Response | None = await session.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        return {
            "status": "ok",
            "final_url": session.page.url,
            "status_code": response.status if response else None,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "final_url": session.page.url,
            "error": str(exc),
        }


async def close_session(session: BrowserSession) -> None:
    """Close browser resources in reverse creation order."""

    await session.context.close()
    await session.browser.close()
    await session.playwright.stop()
