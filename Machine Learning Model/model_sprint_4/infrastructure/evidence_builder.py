from __future__ import annotations

from typing import Any, Callable

try:
    from .collectors import (
        collect_asn,
        collect_cookies,
        collect_dns,
        collect_html,
        collect_http,
        collect_redirects,
        collect_script_analysis,
        collect_tls,
        collect_whois,
    )
    from .collectors._utils import normalize_url, safe_error, utc_now_iso
    from .preprocessing import preprocess_evidence
except ImportError:  # Allows `python evidence_builder.py` from this directory.
    from collectors import (  # type: ignore
        collect_asn,
        collect_cookies,
        collect_dns,
        collect_html,
        collect_http,
        collect_redirects,
        collect_script_analysis,
        collect_tls,
        collect_whois,
    )
    from collectors._utils import normalize_url, safe_error, utc_now_iso  # type: ignore
    from preprocessing import preprocess_evidence  # type: ignore


Collector = Callable[..., dict[str, Any]]


def _safe_collect(name: str, collector: Collector, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        result = collector(*args, **kwargs)
        if isinstance(result, dict):
            return result
        return {"collector": name, "status": "invalid_output", "error": "collector did not return a dictionary"}
    except Exception as exc:
        return {"collector": name, "status": "failed", "error": safe_error(exc)}


def build_evidence(
    url: str,
    *,
    timeout: float = 8.0,
    enable_network: bool = True,
    preprocess: bool = True,
) -> dict[str, Any]:
    """Collect complete infrastructure evidence for a URL.

    The collectors intentionally avoid final judgments. They return externally
    verifiable facts plus explicit failure states.
    """

    target = normalize_url(url)
    evidence: dict[str, Any] = {
        "module": "Infrastructure Analysis",
        "input_url": url,
        "url": target,
        "collected_at": utc_now_iso(),
        "network_enabled": enable_network,
    }

    evidence["whois"] = _safe_collect("whois", collect_whois, target, enable_network=enable_network)
    evidence["dns"] = _safe_collect("dns", collect_dns, target, timeout=timeout, enable_network=enable_network)
    evidence["tls"] = _safe_collect("tls", collect_tls, target, timeout=timeout, enable_network=enable_network)
    evidence["asn"] = _safe_collect(
        "asn",
        collect_asn,
        target,
        dns_evidence=evidence["dns"],
        timeout=timeout,
        enable_network=enable_network,
    )
    evidence["redirects"] = _safe_collect(
        "redirects",
        collect_redirects,
        target,
        timeout=timeout,
        enable_network=enable_network,
    )
    evidence["http"] = _safe_collect("http", collect_http, target, timeout=timeout, enable_network=enable_network)
    evidence["cookies"] = _safe_collect(
        "cookies",
        collect_cookies,
        target,
        timeout=timeout,
        enable_network=enable_network,
    )
    evidence["html"] = _safe_collect("html", collect_html, target, timeout=timeout, enable_network=enable_network)
    evidence["script_analysis"] = _safe_collect(
        "script_analysis",
        collect_script_analysis,
        target,
        html_evidence=evidence["html"],
        enable_network=enable_network,
    )

    return preprocess_evidence(evidence) if preprocess else evidence


if __name__ == "__main__":
    from pprint import pprint

    user_url = input("URL: ")
    pprint(build_evidence(user_url))

