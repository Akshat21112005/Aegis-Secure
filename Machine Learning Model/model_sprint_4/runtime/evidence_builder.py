from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse


try:
    from .behavior.forms import collect_forms
    from .behavior.javascript_runtime import collect_javascript, install_javascript_monitoring
    from .behavior.network import attach_network_listeners
    from .behavior.permissions import collect_permissions
    from .behavior.storage import collect_storage
    from .browser import close_session, create_session, navigate
    from .preprocessing import preprocess_evidence
except ImportError:
    from behavior.forms import collect_forms  # type: ignore
    from behavior.javascript_runtime import collect_javascript, install_javascript_monitoring  # type: ignore
    from behavior.network import attach_network_listeners  # type: ignore
    from behavior.permissions import collect_permissions  # type: ignore
    from behavior.storage import collect_storage  # type: ignore
    from browser import close_session, create_session, navigate  # type: ignore
    from preprocessing import preprocess_evidence  # type: ignore


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _same_site_domain(page_host: str, host: str) -> bool:
    if not page_host or not host:
        return False
    return host == page_host or host.endswith(f".{page_host}")


def _network_evidence(network, page_url: str) -> dict[str, Any]:
    page_host = urlparse(page_url).hostname or ""
    resource_types: dict[str, int] = {}
    third_party_domains: set[str] = set()
    failed_hosts: list[str] = []
    status_codes: dict[str, int] = {}

    for request in network.requests:
        resource_type = str(request.get("resource_type") or "other")
        resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
        host = urlparse(str(request.get("url") or "")).hostname or ""
        if host and not _same_site_domain(page_host, host):
            third_party_domains.add(host)

    for response in network.responses:
        status = str(response.get("status") or "unknown")
        status_codes[status] = status_codes.get(status, 0) + 1

    for failed in network.failed_requests:
        host = urlparse(str(failed.get("url") or "")).hostname or ""
        if host and host not in failed_hosts:
            failed_hosts.append(host)

    return {
        "request_count": len(network.requests),
        "response_count": len(network.responses),
        "failed_request_count": len(network.failed_requests),
        "download_count": len(network.downloads),
        "websocket_count": len(network.websockets),
        "resource_types": resource_types,
        "third_party_domain_count": len(third_party_domains),
        "third_party_domains": sorted(third_party_domains)[:12],
        "failed_hosts": failed_hosts[:8],
        "status_codes": status_codes,
    }


async def build_evidence_async(
    url: str,
    *,
    timeout_ms: int = 30_000,
    headless: bool = True,
    preprocess: bool = True,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "module": "Runtime Analysis",
        "input_url": url,
        "url": url,
        "collected_at": _utc_now_iso(),
    }

    session = await create_session(headless=headless)
    page = session.page

    network = attach_network_listeners(page)
    js_monitor = await install_javascript_monitoring(page)

    try:
        evidence["navigation"] = await navigate(session, url, timeout_ms=timeout_ms)

        forms, storage, javascript, permissions = await asyncio.gather(
            collect_forms(page),
            collect_storage(page),
            collect_javascript(page, js_monitor),
            collect_permissions(page),
        )

        evidence["forms"] = forms
        evidence["storage"] = storage
        evidence["javascript"] = javascript
        evidence["permissions"] = permissions
        evidence["network"] = _network_evidence(network, page.url)
    finally:
        await close_session(session)

    return preprocess_evidence(evidence) if preprocess else evidence


def build_evidence(
    url: str,
    *,
    timeout_ms: int = 30_000,
    headless: bool = True,
    preprocess: bool = True,
) -> dict[str, Any]:
    return asyncio.run(
        build_evidence_async(
            url,
            timeout_ms=timeout_ms,
            headless=headless,
            preprocess=preprocess,
        )
    )


if __name__ == "__main__":
    from pprint import pprint

    target = input("URL: ")
    pprint(build_evidence(target))
