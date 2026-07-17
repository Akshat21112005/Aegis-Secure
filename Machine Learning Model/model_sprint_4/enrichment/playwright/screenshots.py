from playwright.async_api import Page


async def capture_screenshot(
    page: Page,
    full_page: bool = True,
) -> bytes:

    return await page.screenshot(
        type="png",
        full_page=full_page,
    )