from __future__ import annotations

import re
from typing import Any

from ._utils import find_encoded_urls, limit_string, unique


SUSPICIOUS_TOKENS = [
    "eval(",
    "atob(",
    "btoa(",
    "document.write",
    "innerHTML",
    "setTimeout(",
    "setInterval(",
    "fetch(",
    "XMLHttpRequest",
    "navigator.clipboard",
    "localStorage",
    "sessionStorage",
    "crypto.subtle",
    "Function(",
]


def _long_strings(text: str, limit: int = 8) -> list[str]:
    matches = re.findall(r"['\"]([^'\"]{80,})['\"]", text or "")
    return [limit_string(match, 180) for match in matches[:limit]]


def _base64_like(text: str, limit: int = 8) -> list[str]:
    matches = re.findall(r"\b[A-Za-z0-9+/]{80,}={0,2}\b", text or "")
    return [limit_string(match, 160) for match in matches[:limit]]


def collect_script_analysis(
    url: str,
    *,
    html_evidence: dict[str, Any] | None = None,
    enable_network: bool = True,
) -> dict[str, Any]:
    samples = list((html_evidence or {}).get("inline_script_samples") or [])
    sources = list((html_evidence or {}).get("script_sources") or [])
    combined = "\n".join(samples)
    lower = combined.lower()
    token_hits = [token for token in SUSPICIOUS_TOKENS if token.lower() in lower]
    encoded_urls = find_encoded_urls(combined)
    evidence = {
        "collector": "script_analysis",
        "status": "ok" if html_evidence and html_evidence.get("status") == "ok" else (html_evidence or {}).get("status", "unknown"),
        "url": url,
        "script_count": (html_evidence or {}).get("script_count", 0),
        "external_script_count": (html_evidence or {}).get("external_script_count", 0),
        "inline_script_count": (html_evidence or {}).get("inline_script_count", 0),
        "external_sources": sources[:50],
        "suspicious_tokens": unique(token_hits, 30),
        "long_string_samples": _long_strings(combined),
        "base64_like_samples": _base64_like(combined),
        "encoded_urls": encoded_urls,
        "minified_indicator": bool(samples and max((len(sample) for sample in samples), default=0) > 2000 and "\n" not in combined),
        "network_executed": False,
        "network_enabled": enable_network,
    }
    return evidence

