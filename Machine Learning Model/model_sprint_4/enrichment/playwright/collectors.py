import time

from playwright.async_api import Page

from .artifacts import PlaywrightArtifact


async def collect_page_artifacts(
    page: Page,
    url: str,
) -> PlaywrightArtifact:

    artifact = PlaywrightArtifact()

    artifact.url = url

    requests = []

    responses = []

    console_logs = []

    redirect_chain = []

    async def on_request(request):

        requests.append(
            {
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "headers": dict(request.headers),
            }
        )

    async def on_response(response):

        responses.append(
            {
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
            }
        )

        redirect_chain.append(response.url)

    async def on_console(message):

        console_logs.append(
            {
                "type": message.type,
                "text": message.text,
            }
        )

    page.on(
        "request",
        on_request,
    )

    page.on(
        "response",
        on_response,
    )

    page.on(
        "console",
        on_console,
    )

    start = time.perf_counter()

    try:

        response = await page.goto(
            url,
            wait_until="networkidle",
        )

    except Exception as e:

        artifact.error = str(e)

        artifact.success = False

        return artifact

    artifact.load_time = (
        time.perf_counter() - start
    )

    artifact.success = response is not None

    if response:

        artifact.status_code = response.status

    artifact.final_url = page.url

    artifact.requests = requests

    artifact.responses = responses

    artifact.redirects = redirect_chain

    artifact.console_logs = console_logs

    try:

        artifact.title = await page.title()

    except Exception:

        artifact.title = ""

    try:

        artifact.html = await page.content()

    except Exception:

        artifact.html = ""

    try:

        artifact.text = await page.locator(
            "body"
        ).inner_text()

    except Exception:

        artifact.text = ""

    try:

        artifact.forms = await page.evaluate(
            """
            () => {
                return Array.from(document.forms).map(form => ({
                    action: form.action,
                    method: form.method,
                    enctype: form.enctype,
                    target: form.target,
                    autocomplete: form.autocomplete,
                    inputs: Array.from(form.elements).map(element => ({
                        tag: element.tagName,
                        type: element.type || "",
                        name: element.name || "",
                        id: element.id || "",
                        placeholder: element.placeholder || "",
                        required: element.required || false
                    }))
                }));
            }
            """
        )

    except Exception:

        artifact.forms = []

    try:

        artifact.scripts = await page.evaluate(
            """
            () => {
                return Array.from(document.scripts).map(script => ({
                    src: script.src,
                    async: script.async,
                    defer: script.defer,
                    type: script.type,
                    integrity: script.integrity
                }));
            }
            """
        )

    except Exception:

        artifact.scripts = []

    try:

        artifact.cookies = await page.context.cookies()

    except Exception:

        artifact.cookies = []

    try:

        artifact.local_storage = await page.evaluate(
            """
            () => {
                const storage = {};

                for (let i = 0; i < localStorage.length; i++) {

                    const key = localStorage.key(i);

                    storage[key] = localStorage.getItem(key);

                }

                return storage;
            }
            """
        )

    except Exception:

        artifact.local_storage = {}

    try:

        artifact.session_storage = await page.evaluate(
            """
            () => {
                const storage = {};

                for (let i = 0; i < sessionStorage.length; i++) {

                    const key = sessionStorage.key(i);

                    storage[key] = sessionStorage.getItem(key);

                }

                return storage;
            }
            """
        )

    except Exception:

        artifact.session_storage = {}

    try:

        artifact.meta_refresh = await page.evaluate(
            """
            () => {
                const meta = document.querySelector(
                    'meta[http-equiv="refresh"]'
                );

                return meta ? meta.content : "";
            }
            """
        )

    except Exception:

        artifact.meta_refresh = ""

    try:

        artifact.page_language = await page.evaluate(
            """
            () => document.documentElement.lang || ""
            """
        )

    except Exception:

        artifact.page_language = ""

    try:

        artifact.links = await page.evaluate(
            """
            () => {
                return Array.from(document.links).map(link => ({
                    text: link.innerText,
                    href: link.href
                }));
            }
            """
        )

    except Exception:

        artifact.links = []

    try:

        artifact.images = await page.evaluate(
            """
            () => {
                return Array.from(document.images).map(image => ({
                    src: image.src,
                    alt: image.alt
                }));
            }
            """
        )

    except Exception:

        artifact.images = []

    try:

        artifact.iframes = await page.evaluate(
            """
            () => {
                return Array.from(
                    document.querySelectorAll("iframe")
                ).map(frame => ({
                    src: frame.src
                }));
            }
            """
        )

    except Exception:

        artifact.iframes = []

    try:

        artifact.performance = await page.evaluate(
            """
            () => {

                const navigation =
                    performance.getEntriesByType("navigation")[0];

                if (!navigation)
                    return {};

                return {

                    domContentLoaded:
                        navigation.domContentLoadedEventEnd,

                    loadEvent:
                        navigation.loadEventEnd,

                    responseEnd:
                        navigation.responseEnd,

                    transferSize:
                        navigation.transferSize

                };

            }
            """
        )

    except Exception:

        artifact.performance = {}

    return artifact