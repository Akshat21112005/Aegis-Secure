from playwright.async_api import BrowserContext, Browser, Page

from .artifacts import PlaywrightArtifact
from .collectors import collect_page_artifacts
from .launcher import BrowserLauncher
from .screenshots import capture_screenshot


class PlaywrightAnalyzer:

    def __init__(self) -> None:

        self.launcher = BrowserLauncher()

    async def analyze(
        self,
        url: str,
    ) -> PlaywrightArtifact:

        browser: Browser
        context: BrowserContext
        page: Page

        browser, context, page = await self.launcher.launch()

        try:

            artifact = await collect_page_artifacts(
                page,
                url,
            )

            artifact.screenshot = await capture_screenshot(
                page,
            )

            return artifact

        finally:

            await self.launcher.close(
                browser,
                context,
            )