from dataclasses import dataclass, field


@dataclass
class PlaywrightArtifact:

    url: str = ""

    final_url: str = ""

    title: str = ""

    html: str = ""

    text: str = ""

    screenshot: bytes | None = None

    requests: list[dict] = field(default_factory=list)

    responses: list[dict] = field(default_factory=list)

    redirects: list[str] = field(default_factory=list)

    forms: list[dict] = field(default_factory=list)

    cookies: list[dict] = field(default_factory=list)

    scripts: list[dict] = field(default_factory=list)

    links: list[dict] = field(default_factory=list)

    images: list[dict] = field(default_factory=list)

    iframes: list[dict] = field(default_factory=list)

    local_storage: dict = field(default_factory=dict)

    session_storage: dict = field(default_factory=dict)

    console_logs: list[dict] = field(default_factory=list)

    meta_refresh: str = ""

    page_language: str = ""

    performance: dict = field(default_factory=dict)

    status_code: int = 0

    load_time: float = 0.0

    success: bool = False

    error: str = ""