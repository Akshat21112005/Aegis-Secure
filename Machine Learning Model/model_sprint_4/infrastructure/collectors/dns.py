from __future__ import annotations

import socket
from typing import Any

from ._utils import extract_hostname, registered_domain, safe_error, unique


def _empty(hostname: str, status: str, error: str = "") -> dict[str, Any]:
    return {
        "collector": "dns",
        "status": status,
        "hostname": hostname,
        "registered_domain": registered_domain(hostname),
        "records": {
            "A": [],
            "AAAA": [],
            "MX": [],
            "NS": [],
            "TXT": [],
            "SOA": [],
            "CAA": [],
            "CNAME": [],
        },
        "spf_records": [],
        "dmarc_records": [],
        "dnssec": "unknown",
        "errors": [error] if error else [],
    }


def _txt_values(answer: Any) -> list[str]:
    values: list[str] = []
    for record in answer:
        if hasattr(record, "strings"):
            values.append("".join(part.decode("utf-8", "ignore") for part in record.strings))
        else:
            values.append(str(record).strip('"'))
    return values


def _dns_query(resolver: Any, name: str, record_type: str) -> tuple[list[Any], str]:
    try:
        answer = resolver.resolve(name, record_type)
    except Exception as exc:
        return [], safe_error(exc)

    if record_type == "TXT":
        return _txt_values(answer), ""
    if record_type == "MX":
        return [
            {"preference": int(record.preference), "exchange": str(record.exchange).rstrip(".")}
            for record in answer
        ], ""
    if record_type == "SOA":
        return [
            {
                "mname": str(record.mname).rstrip("."),
                "rname": str(record.rname).rstrip("."),
                "serial": int(record.serial),
                "refresh": int(record.refresh),
                "retry": int(record.retry),
                "expire": int(record.expire),
                "minimum": int(record.minimum),
            }
            for record in answer
        ], ""
    if record_type == "CAA":
        return [
            {
                "flags": int(record.flags),
                "tag": str(record.tag),
                "value": record.value.decode("utf-8", "ignore")
                if isinstance(record.value, bytes)
                else str(record.value),
            }
            for record in answer
        ], ""
    return [str(record).rstrip(".") for record in answer], ""


def collect_dns(url: str, *, timeout: float = 5.0, enable_network: bool = True) -> dict[str, Any]:
    hostname = extract_hostname(url)
    if not hostname:
        return _empty("", "no_hostname")
    if not enable_network:
        return _empty(hostname, "skipped")

    evidence = _empty(hostname, "ok")
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        for record_type in evidence["records"]:
            records, error = _dns_query(resolver, hostname, record_type)
            evidence["records"][record_type] = records
            if error and "NoAnswer" not in error and "NXDOMAIN" not in error:
                evidence["errors"].append(f"{record_type}: {error}")

        domain = registered_domain(hostname)
        dmarc_records, dmarc_error = _dns_query(resolver, f"_dmarc.{domain}", "TXT")
        evidence["dmarc_records"] = [value for value in dmarc_records if value.lower().startswith("v=dmarc")]
        if dmarc_error and "NoAnswer" not in dmarc_error and "NXDOMAIN" not in dmarc_error:
            evidence["errors"].append(f"DMARC: {dmarc_error}")

        dnskey_records, dnskey_error = _dns_query(resolver, domain, "DNSKEY")
        evidence["dnssec"] = "enabled" if dnskey_records else "disabled"
        if dnskey_error and "NoAnswer" not in dnskey_error and "NXDOMAIN" not in dnskey_error:
            evidence["dnssec"] = "unknown"
    except Exception as exc:
        evidence["status"] = "resolver_unavailable"
        evidence["errors"].append(safe_error(exc))
        try:
            records = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            addresses = sorted({record[4][0] for record in records if record and record[4]})
            evidence["records"]["A"] = unique([ip for ip in addresses if "." in ip])
            evidence["records"]["AAAA"] = unique([ip for ip in addresses if ":" in ip])
            evidence["status"] = "partial_socket_resolution"
        except Exception as socket_exc:
            evidence["errors"].append(safe_error(socket_exc))
            evidence["status"] = "failed"

    txt_records = evidence["records"].get("TXT", [])
    evidence["spf_records"] = [value for value in txt_records if str(value).lower().startswith("v=spf1")]
    evidence["has_mx"] = bool(evidence["records"].get("MX"))
    evidence["has_spf"] = bool(evidence["spf_records"])
    evidence["has_dmarc"] = bool(evidence["dmarc_records"])
    evidence["name_servers"] = evidence["records"].get("NS", [])
    evidence["ip_addresses"] = unique(evidence["records"].get("A", []) + evidence["records"].get("AAAA", []), 20)
    return evidence

