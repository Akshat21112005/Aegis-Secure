from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScreenshotArtifact:
    url: str = ""
    bytes_data: bytes | None = None
    width: int = 0
    height: int = 0


@dataclass
class PlaywrightArtifact:
    url: str = ""
    final_url: str = ""
    title: str = ""
    html: str = ""
    text: str = ""
    screenshot: bytes | None = None
    requests: list[dict[str, Any]] = field(default_factory=list)
    responses: list[dict[str, Any]] = field(default_factory=list)
    redirects: list[str] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    cookies: list[dict[str, Any]] = field(default_factory=list)
    scripts: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    iframes: list[dict[str, Any]] = field(default_factory=list)
    local_storage: dict[str, Any] = field(default_factory=dict)
    session_storage: dict[str, Any] = field(default_factory=dict)
    console_logs: list[dict[str, Any]] = field(default_factory=list)
    meta_refresh: str = ""
    page_language: str = ""
    performance: dict[str, Any] = field(default_factory=dict)
    status_code: int = 0
    load_time: float = 0.0
    success: bool = False
    error: str = ""
