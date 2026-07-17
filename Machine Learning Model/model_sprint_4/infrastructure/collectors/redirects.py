from __future__ import annotations

from typing import Any

from ._utils import DEFAULT_USER_AGENT, extract_hostname, make_absolute_url, normalize_url, registered_domain, safe_error


def collect_redirects(
    url: str,
    *,
    timeout: float = 8.0,
    max_redirects: int = 10,
    enable_network: bool = True,
) -> dict[str, Any]:
    target = normalize_url(url)
    evidence: dict[str, Any] = {
        "collector": "redirects",
        "status": "unknown",
        "url": target,
        "redirect_count": 0,
        "chain": [],
        "final_url": "",
        "https_upgrade": False,
        "cross_domain_redirect": False,
        "loop_detected": False,
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

        session = requests.Session()
        session.max_redirects = max_redirects
        response = session.get(
            target,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        chain = []
        for item in response.history:
            location = item.headers.get("Location", "")
            destination = make_absolute_url(item.url, location) if location else item.url
            chain.append(
                {
                    "status_code": item.status_code,
                    "from": item.url,
                    "location": location,
                    "to": destination,
                }
            )
        evidence["status"] = "ok"
        evidence["redirect_count"] = len(chain)
        evidence["chain"] = chain
        evidence["final_url"] = response.url
        evidence["https_upgrade"] = target.startswith("http://") and response.url.startswith("https://")
        start_domain = registered_domain(extract_hostname(target))
        final_domain = registered_domain(extract_hostname(response.url))
        evidence["cross_domain_redirect"] = bool(start_domain and final_domain and start_domain != final_domain)
        if len(chain) >= max_redirects:
            evidence["loop_detected"] = True
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = safe_error(exc)
        if "TooManyRedirects" in evidence["error"]:
            evidence["loop_detected"] = True
    return evidence

