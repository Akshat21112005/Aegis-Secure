from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; AEGIS-Infrastructure-Specialist/1.0; "
    "+https://aegis.local)"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(value: str) -> str:
    text = (value or "").strip().replace("\\", "/")
    if not text:
        return ""

    lowered = text.lower()
    if lowered.startswith("http:/") and not lowered.startswith("http://"):
        text = "http://" + text.split(":", 1)[1].lstrip("/")
    elif lowered.startswith("https:/") and not lowered.startswith("https://"):
        text = "https://" + text.split(":", 1)[1].lstrip("/")
    elif lowered.startswith("http:") and not lowered.startswith("http://"):
        text = "http://" + text.split(":", 1)[1].lstrip("/")
    elif lowered.startswith("https:") and not lowered.startswith("https://"):
        text = "https://" + text.split(":", 1)[1].lstrip("/")
    elif not text.startswith(("http://", "https://")):
        text = "https://" + text

    try:
        parsed = urlparse(text)
        if (parsed.hostname or "").lower() in {"http", "https"} and parsed.path:
            repaired = parsed.path.lstrip("/")
            if repaired:
                return normalize_url(repaired)
        if not parsed.hostname:
            return ""
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))
    except Exception:
        return ""


def extract_hostname(value: str) -> str:
    url = normalize_url(value)
    if not url:
        return ""
    return (urlparse(url).hostname or "").lower().strip(".")


def registered_domain(value: str) -> str:
    host = extract_hostname(value) or (value or "").lower().strip(".")
    if not host:
        return ""
    parts = [part for part in host.split(".") if part]
    common_two_part_suffixes = {
        "ac.in",
        "co.in",
        "co.jp",
        "co.nz",
        "co.uk",
        "com.au",
        "com.br",
        "com.cn",
        "com.sg",
        "gov.in",
        "net.in",
        "org.in",
    }
    if len(parts) >= 3 and ".".join(parts[-2:]) in common_two_part_suffixes:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def make_absolute_url(base_url: str, candidate: str) -> str:
    if not candidate:
        return ""
    return normalize_url(urljoin(normalize_url(base_url) or base_url, candidate))


def limit_string(value: Any, limit: int = 500) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def unique(values: list[Any], limit: int = 50) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def safe_error(exc: Exception, limit: int = 240) -> str:
    return limit_string(f"{type(exc).__name__}: {exc}", limit)


def find_encoded_urls(text: str, limit: int = 20) -> list[str]:
    pattern = re.compile(r"https?%3A%2F%2F[^\s\"'<>]+|https?://[^\s\"'<>]+", re.I)
    return unique(pattern.findall(text or ""), limit=limit)

