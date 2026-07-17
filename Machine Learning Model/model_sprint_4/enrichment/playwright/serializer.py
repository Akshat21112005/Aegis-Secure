import base64
from dataclasses import asdict

from .artifacts import PlaywrightArtifact


def serialize(
    artifact: PlaywrightArtifact,
) -> dict:

    data = asdict(artifact)

    if artifact.screenshot is not None:

        data["screenshot"] = base64.b64encode(
            artifact.screenshot
        ).decode("utf-8")

    else:

        data["screenshot"] = None

    return data


def deserialize(
    data: dict,
) -> PlaywrightArtifact:

    screenshot = data.get("screenshot")

    if screenshot is not None:

        screenshot = base64.b64decode(
            screenshot
        )

    return PlaywrightArtifact(

        url=data.get("url", ""),

        final_url=data.get("final_url", ""),

        title=data.get("title", ""),

        html=data.get("html", ""),

        text=data.get("text", ""),

        screenshot=screenshot,

        requests=data.get("requests", []),

        responses=data.get("responses", []),

        redirects=data.get("redirects", []),

        forms=data.get("forms", []),

        cookies=data.get("cookies", []),

        scripts=data.get("scripts", []),

        links=data.get("links", []),

        images=data.get("images", []),

        iframes=data.get("iframes", []),

        local_storage=data.get(
            "local_storage",
            {},
        ),

        session_storage=data.get(
            "session_storage",
            {},
        ),

        console_logs=data.get(
            "console_logs",
            [],
        ),

        meta_refresh=data.get(
            "meta_refresh",
            "",
        ),

        page_language=data.get(
            "page_language",
            "",
        ),

        performance=data.get(
            "performance",
            {},
        ),

        status_code=data.get(
            "status_code",
            0,
        ),

        load_time=data.get(
            "load_time",
            0.0,
        ),

        success=data.get(
            "success",
            False,
        ),

        error=data.get(
            "error",
            "",
        ),
    )