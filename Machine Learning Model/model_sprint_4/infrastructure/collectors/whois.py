from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ._utils import extract_hostname, limit_string, registered_domain, safe_error


def _first_datetime(value: Any) -> datetime | None:
    if isinstance(value, list):
        for item in value:
            parsed = _first_datetime(item)
            if parsed:
                return parsed
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def _string_list(value: Any, limit: int = 20) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in items:
        text = limit_string(item, 160)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def collect_whois(url: str, *, enable_network: bool = True) -> dict[str, Any]:
    hostname = extract_hostname(url)
    domain = registered_domain(hostname or url)
    evidence: dict[str, Any] = {
        "collector": "whois",
        "status": "unknown",
        "hostname": hostname,
        "domain": domain,
        "registrar": "",
        "creation_date": "",
        "expiration_date": "",
        "updated_date": "",
        "domain_age_days": None,
        "expires_in_days": None,
        "days_since_update": None,
        "name_servers": [],
        "statuses": [],
        "emails": [],
        "organization": "",
        "country": "",
        "dnssec": "",
        "error": "",
    }
    if not domain:
        evidence["status"] = "no_domain"
        return evidence
    if not enable_network:
        evidence["status"] = "skipped"
        return evidence

    try:
        import whois
    except Exception as exc:
        evidence["status"] = "dependency_unavailable"
        evidence["error"] = safe_error(exc)
        return evidence

    try:
        record = whois.whois(domain)
        created = _first_datetime(getattr(record, "creation_date", None))
        expires = _first_datetime(getattr(record, "expiration_date", None))
        updated = _first_datetime(getattr(record, "updated_date", None))
        now = datetime.now(timezone.utc)
        evidence.update(
            {
                "status": "ok" if created or getattr(record, "registrar", None) else "unavailable",
                "registrar": limit_string(getattr(record, "registrar", ""), 160),
                "creation_date": _iso(created),
                "expiration_date": _iso(expires),
                "updated_date": _iso(updated),
                "domain_age_days": (now - created).days if created else None,
                "expires_in_days": (expires - now).days if expires else None,
                "days_since_update": (now - updated).days if updated else None,
                "name_servers": _string_list(getattr(record, "name_servers", None)),
                "statuses": _string_list(getattr(record, "status", None)),
                "emails": _string_list(getattr(record, "emails", None)),
                "organization": limit_string(
                    getattr(record, "org", None) or getattr(record, "organization", None), 160
                ),
                "country": limit_string(getattr(record, "country", ""), 80),
                "dnssec": limit_string(getattr(record, "dnssec", ""), 80),
            }
        )
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = safe_error(exc)
    return evidence

