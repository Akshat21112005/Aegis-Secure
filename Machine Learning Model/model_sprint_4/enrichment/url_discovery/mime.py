from __future__ import annotations

from .html import extract_urls_from_html
from .text import extract_urls_from_text


def extract_urls_from_mime(payload: dict) -> list[str]:
    """Extract URLs from a Gmail-style MIME payload tree."""

    plain_parts: list[str] = []
    html_parts: list[str] = []
    _walk(payload, plain_parts, html_parts)

    urls: list[str] = []
    for part in plain_parts:
        urls.extend(extract_urls_from_text(part))
    for part in html_parts:
        urls.extend(extract_urls_from_html(part))
    return urls


def _walk(part: dict, plain_parts: list[str], html_parts: list[str]) -> None:
    mime_type = part.get("mimeType", "")
    body = part.get("body", {})
    data = body.get("data")

    if data:
        text = _decode_part(data)
        if mime_type == "text/plain":
            plain_parts.append(text)
        elif mime_type == "text/html":
            html_parts.append(text)

    for child in part.get("parts", []):
        _walk(child, plain_parts, html_parts)


def _decode_part(data: str) -> str:
    import base64

    try:
        raw = base64.urlsafe_b64decode(data)
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""
