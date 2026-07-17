from __future__ import annotations

import socket
from typing import Any

from ._utils import extract_hostname, safe_error, unique


def _resolve_ips(hostname: str, timeout: float) -> list[str]:
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        records = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        return unique([record[4][0] for record in records if record and record[4]], 12)
    finally:
        socket.setdefaulttimeout(old_timeout)


def collect_asn(
    url: str,
    *,
    dns_evidence: dict[str, Any] | None = None,
    timeout: float = 5.0,
    enable_network: bool = True,
) -> dict[str, Any]:
    hostname = extract_hostname(url)
    evidence: dict[str, Any] = {
        "collector": "asn",
        "status": "unknown",
        "hostname": hostname,
        "ip_addresses": [],
        "lookups": [],
        "primary_asn": "",
        "primary_network": "",
        "primary_country": "",
        "error": "",
    }
    if not hostname:
        evidence["status"] = "no_hostname"
        return evidence
    if not enable_network:
        evidence["status"] = "skipped"
        return evidence

    ips = []
    if dns_evidence:
        ips = list(dns_evidence.get("ip_addresses") or [])
    if not ips:
        try:
            ips = _resolve_ips(hostname, timeout)
        except Exception as exc:
            evidence["status"] = "ip_resolution_failed"
            evidence["error"] = safe_error(exc)
            return evidence
    evidence["ip_addresses"] = ips

    try:
        from ipwhois import IPWhois
    except Exception as exc:
        evidence["status"] = "dependency_unavailable"
        evidence["error"] = safe_error(exc)
        return evidence

    for ip in ips[:5]:
        try:
            result = IPWhois(ip).lookup_rdap(depth=0)
            network = result.get("network") or {}
            lookup = {
                "ip": ip,
                "asn": str(result.get("asn") or ""),
                "asn_description": str(result.get("asn_description") or ""),
                "asn_country_code": str(result.get("asn_country_code") or ""),
                "network_name": str(network.get("name") or ""),
                "cidr": str(network.get("cidr") or ""),
                "rir": str(result.get("nir") or result.get("asn_registry") or ""),
            }
            evidence["lookups"].append(lookup)
        except Exception as exc:
            evidence["lookups"].append({"ip": ip, "status": "failed", "error": safe_error(exc)})

    successful = [lookup for lookup in evidence["lookups"] if lookup.get("asn")]
    if successful:
        first = successful[0]
        evidence.update(
            {
                "status": "ok",
                "primary_asn": first.get("asn", ""),
                "primary_network": first.get("asn_description", "") or first.get("network_name", ""),
                "primary_country": first.get("asn_country_code", ""),
            }
        )
    else:
        evidence["status"] = "unavailable"
    return evidence

