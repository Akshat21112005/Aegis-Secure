from __future__ import annotations

from typing import Any

from ._utils import DEFAULT_USER_AGENT, limit_string, normalize_url, safe_error


SECURITY_HEADERS = [
    "content-security-policy",
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-xss-protection",
]

CACHE_HEADERS = ["cache-control", "expires", "pragma", "etag", "last-modified"]


def _headers_subset(headers: Any, names: list[str]) -> dict[str, str]:
    lowered = {str(key).lower(): str(value) for key, value in dict(headers or {}).items()}
    return {name: limit_string(lowered.get(name, ""), 500) for name in names if lowered.get(name)}


def collect_http(url: str, *, timeout: float = 8.0, enable_network: bool = True) -> dict[str, Any]:
    target = normalize_url(url)
    evidence: dict[str, Any] = {
        "collector": "http",
        "status": "unknown",
        "url": target,
        "status_code": None,
        "reason": "",
        "content_type": "",
        "content_length": "",
        "server": "",
        "powered_by": "",
        "encoding": "",
        "security_headers": {},
        "cache_headers": {},
        "all_header_names": [],
        "error": "",
    }
    if not target:
        evidence["status"] = "no_url"
        return evidence
    if not enable_network:
        evidence["status"] = "skipped"
        return evidence

    try:
        import requests

        response = requests.get(
            target,
            timeout=timeout,
            allow_redirects=False,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        headers = response.headers
        evidence.update(
            {
                "status": "ok",
                "status_code": response.status_code,
                "reason": limit_string(response.reason, 120),
                "content_type": limit_string(headers.get("Content-Type", ""), 180),
                "content_length": limit_string(headers.get("Content-Length", ""), 80),
                "server": limit_string(headers.get("Server", ""), 160),
                "powered_by": limit_string(headers.get("X-Powered-By", ""), 160),
                "encoding": limit_string(headers.get("Content-Encoding", ""), 80),
                "security_headers": _headers_subset(headers, SECURITY_HEADERS),
                "cache_headers": _headers_subset(headers, CACHE_HEADERS),
                "all_header_names": sorted(str(key).lower() for key in headers.keys())[:80],
            }
        )
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = safe_error(exc)
    return evidence

