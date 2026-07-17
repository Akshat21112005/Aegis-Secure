from playwright.async_api import Browser, BrowserContext, Page
from playwright.async_api import async_playwright


class BrowserLauncher:

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def launch(
        self,
        headless: bool = True,
    ) -> tuple[Browser, BrowserContext, Page]:

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
        )

        context = await self._browser.new_context(
            ignore_https_errors=True,
            java_script_enabled=True,
            viewport={
                "width": 1366,
                "height": 768,
            },
        )

        page = await context.new_page()

        return (
            self._browser,
            context,
            page,
        )

    async def close(
        self,
        browser: Browser,
        context: BrowserContext,
    ) -> None:

        await context.close()

        await browser.close()

        if self._playwright is not None:
            await self._playwright.stop()