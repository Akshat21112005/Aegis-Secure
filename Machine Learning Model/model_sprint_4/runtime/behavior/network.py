from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NetworkCapture:
    requests: list[dict[str, Any]] = field(default_factory=list)
    responses: list[dict[str, Any]] = field(default_factory=list)
    failed_requests: list[dict[str, Any]] = field(default_factory=list)
    downloads: list[dict[str, Any]] = field(default_factory=list)
    websockets: list[dict[str, Any]] = field(default_factory=list)


def attach_network_listeners(page) -> NetworkCapture:
    """Attach Playwright listeners and return a mutable capture object."""

    capture = NetworkCapture()

    async def request_listener(request):
        try:
            capture.requests.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                    "headers": dict(request.headers),
                }
            )
        except Exception:
            pass

    async def response_listener(response):
        try:
            capture.responses.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers),
                }
            )
        except Exception:
            pass

    async def request_failed_listener(request):
        try:
            capture.failed_requests.append(
                {
                    "url": request.url,
                    "failure": request.failure,
                }
            )
        except Exception:
            pass

    async def websocket_listener(ws):
        try:
            capture.websockets.append({"url": ws.url})
        except Exception:
            pass

    async def download_listener(download):
        try:
            capture.downloads.append(
                {
                    "url": download.url,
                    "filename": download.suggested_filename,
                }
            )
        except Exception:
            pass

    page.on("request", request_listener)
    page.on("response", response_listener)
    page.on("requestfailed", request_failed_listener)
    page.on("websocket", websocket_listener)
    page.on("download", download_listener)
    return capture
