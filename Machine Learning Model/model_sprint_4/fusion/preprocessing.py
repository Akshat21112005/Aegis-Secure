from __future__ import annotations

import re
from html import unescape
from typing import Any

try:
    from enrichment.url_discovery.canonicalizer import canonicalize_urls
    from enrichment.url_discovery.html import extract_urls_from_html
    from enrichment.url_discovery.text import extract_urls_from_text
except ImportError:
    import sys
    from pathlib import Path

    sprint_root = Path(__file__).resolve().parent.parent
    if str(sprint_root) not in sys.path:
        sys.path.insert(0, str(sprint_root))
    from enrichment.url_discovery.canonicalizer import canonicalize_urls  # type: ignore
    from enrichment.url_discovery.html import extract_urls_from_html  # type: ignore
    from enrichment.url_discovery.text import extract_urls_from_text  # type: ignore


CommunicationObject = dict[str, Any]
SemanticObject = dict[str, Any]
UrlIntelligenceObject = dict[str, Any]


def _clean_html_text(html: str) -> str:
    if not html:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)

    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _collect_header_text(headers: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in headers.items() if value)


def _extract_urls_from_headers(headers: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in headers.values():
        if isinstance(value, str):
            urls.extend(extract_urls_from_text(value))
    return urls


def _extract_urls_from_attachments(attachments: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for attachment in attachments:
        metadata_urls = attachment.get("metadata_urls") or []
        if isinstance(metadata_urls, list):
            urls.extend(str(url) for url in metadata_urls if url)
        for key in ("filename", "content_location", "content_id"):
            value = attachment.get(key)
            if isinstance(value, str):
                urls.extend(extract_urls_from_text(value))
    return urls


def _extract_urls_from_embedded_images(images: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for image in images:
        metadata_urls = image.get("metadata_urls") or []
        if isinstance(metadata_urls, list):
            urls.extend(str(url) for url in metadata_urls if url)
        for key in ("src", "content_location", "filename"):
            value = image.get(key)
            if isinstance(value, str):
                urls.extend(extract_urls_from_text(value))
    return urls


def _extract_urls_from_metadata(metadata: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in metadata.values():
        if isinstance(value, str):
            urls.extend(extract_urls_from_text(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    urls.extend(extract_urls_from_text(item))
    return urls


def build_jo1(communication: CommunicationObject) -> SemanticObject:
    """Build JO1 — semantic-only object. No URL intelligence or specialist outputs."""

    source = str(communication.get("source") or "gmail").lower()
    headers = dict(communication.get("headers") or {})
    metadata = dict(communication.get("metadata") or {})
    timestamps = dict(communication.get("timestamps") or {})
    plain_text_body = str(communication.get("plain_text_body") or communication.get("plain_text") or "")
    html_body = str(communication.get("html_body") or communication.get("html") or "")

    jo1: SemanticObject = {
        "object_type": "JO1",
        "source": source,
        "message_id": communication.get("message_id", ""),
        "thread_id": communication.get("thread_id", ""),
        "sender": communication.get("sender", ""),
        "receiver": communication.get("receiver", ""),
        "subject": communication.get("subject", ""),
        "plain_text_body": plain_text_body,
        "cleaned_html_text": _clean_html_text(html_body),
        "headers": headers,
        "metadata": metadata,
        "timestamps": timestamps,
    }

    if source == "sms":
        jo1["carrier_metadata"] = dict(communication.get("carrier_metadata") or {})

    return jo1


def build_jo2(communication: CommunicationObject, *, ocr_urls: list[str] | None = None) -> UrlIntelligenceObject:
    """Build JO2 — URL intelligence object from all supported non-OCR locations."""

    source = str(communication.get("source") or "gmail").lower()
    subject = str(communication.get("subject") or "")
    plain_text_body = str(communication.get("plain_text_body") or communication.get("plain_text") or "")
    html_body = str(communication.get("html_body") or communication.get("html") or "")
    headers = dict(communication.get("headers") or {})
    metadata = dict(communication.get("metadata") or {})
    attachments = list(communication.get("attachments") or [])
    embedded_images = list(communication.get("embedded_images") or [])

    discovered: list[tuple[str, str]] = []

    def add_urls(values: list[str], location: str) -> None:
        for value in values:
            if value:
                discovered.append((value, location))

    add_urls(extract_urls_from_text(subject), "subject")
    add_urls(extract_urls_from_text(plain_text_body), "plain_text_body")
    add_urls(extract_urls_from_html(html_body), "html_body")
    add_urls(_extract_urls_from_headers(headers), "headers")
    add_urls(_extract_urls_from_metadata(metadata), "metadata")
    add_urls(_extract_urls_from_attachments(attachments), "attachment_metadata")
    add_urls(_extract_urls_from_embedded_images(embedded_images), "embedded_images")

    future_ocr_urls = list(ocr_urls or [])
    add_urls(future_ocr_urls, "ocr")

    raw_urls = [url for url, _ in discovered]
    normalized_urls = canonicalize_urls(raw_urls)

    url_sources: dict[str, list[str]] = {}
    for url, location in discovered:
        canonical = canonicalize_urls([url])
        if not canonical:
            continue
        canonical_url = canonical[0]
        url_sources.setdefault(canonical_url, [])
        if location not in url_sources[canonical_url]:
            url_sources[canonical_url].append(location)

    return {
        "object_type": "JO2",
        "source": source,
        "message_id": communication.get("message_id", ""),
        "urls": normalized_urls,
        "url_count": len(normalized_urls),
        "url_sources": url_sources,
        "ocr_urls": future_ocr_urls,
    }


def preprocess_communication(
    communication: CommunicationObject,
    *,
    ocr_urls: list[str] | None = None,
) -> tuple[SemanticObject, UrlIntelligenceObject]:
    """Convert one communication object into JO1 and JO2."""

    if communication.get("source") not in {None, "gmail", "sms"}:
        raise ValueError("Only Gmail and SMS communication sources are supported in this sprint.")

    jo1 = build_jo1(communication)
    jo2 = build_jo2(communication, ocr_urls=ocr_urls)
    return jo1, jo2
