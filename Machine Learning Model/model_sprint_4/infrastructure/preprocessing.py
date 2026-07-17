from __future__ import annotations

from copy import deepcopy
from typing import Any


MAX_SUMMARY_TOKENS = 500
APPROX_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


def truncate_to_token_budget(text: str, max_tokens: int = MAX_SUMMARY_TOKENS) -> str:
    budget = max_tokens * APPROX_CHARS_PER_TOKEN
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= budget:
        return cleaned
    trimmed = cleaned[: budget - 3].rsplit(" ", 1)[0]
    return f"{trimmed}..."


def _status(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("status") or "unknown")
    return "unknown"


def _join(parts: list[str]) -> str:
    return ". ".join(part.strip().rstrip(".") for part in parts if part and part.strip()) + "."


def _summarize_whois(evidence: dict[str, Any]) -> str:
    whois = evidence.get("whois") or {}
    if _status(whois) != "ok":
        return f"WHOIS lookup {_status(whois)}."

    parts = [f"Domain {whois.get('domain', 'unknown')} registered with {whois.get('registrar', 'unknown registrar')}"]
    if whois.get("domain_age_days") is not None:
        parts.append(f"domain age {whois['domain_age_days']} day(s)")
    if whois.get("organization"):
        parts.append(f"organization {whois['organization']}")
    if whois.get("country"):
        parts.append(f"country {whois['country']}")
    if whois.get("name_servers"):
        parts.append(f"name servers: {', '.join(whois['name_servers'][:4])}")
    return _join(parts)


def _summarize_dns(evidence: dict[str, Any]) -> str:
    dns = evidence.get("dns") or {}
    if _status(dns) != "ok":
        return f"DNS lookup {_status(dns)}."

    records = dns.get("records") or {}
    parts = [
        (
            f"DNS resolves with {len(records.get('A', []))} A, "
            f"{len(records.get('AAAA', []))} AAAA, "
            f"{len(records.get('MX', []))} MX, and "
            f"{len(records.get('NS', []))} NS record(s)"
        )
    ]
    if dns.get("spf_records"):
        parts.append("SPF record present")
    else:
        parts.append("no SPF record observed")
    if dns.get("dmarc_records"):
        parts.append("DMARC record present")
    else:
        parts.append("no DMARC record observed")
    return _join(parts)


def _summarize_tls(evidence: dict[str, Any]) -> str:
    tls = evidence.get("tls") or {}
    if _status(tls) != "ok":
        return f"TLS inspection {_status(tls)}."

    parts = [
        (
            f"TLS certificate issued to {tls.get('subject', 'unknown')} "
            f"by {tls.get('issuer', 'unknown issuer')}"
        ),
        f"valid for {tls.get('expires_in_days', 'unknown')} more day(s)",
    ]
    if tls.get("hostname_match") is False:
        parts.append("certificate does not match hostname")
    elif tls.get("hostname_match") is True:
        parts.append("certificate matches hostname")
    if tls.get("tls_version"):
        parts.append(f"protocol {tls['tls_version']}")
    return _join(parts)


def _summarize_http(evidence: dict[str, Any]) -> str:
    http = evidence.get("http") or {}
    if _status(http) != "ok":
        return f"HTTP probe {_status(http)}."

    parts = [
        f"HTTP status {http.get('status_code')} from server {http.get('server', 'unknown')}",
        f"content type {http.get('content_type', 'unknown')}",
    ]
    security_headers = http.get("security_headers") or {}
    present = [name for name, value in security_headers.items() if value]
    missing = [name for name, value in security_headers.items() if not value]
    if present:
        parts.append(f"security headers present: {', '.join(present)}")
    if missing:
        parts.append(f"security headers missing: {', '.join(missing[:6])}")
    return _join(parts)


def _summarize_redirects(evidence: dict[str, Any]) -> str:
    redirects = evidence.get("redirects") or {}
    if _status(redirects) != "ok":
        return f"Redirect analysis {_status(redirects)}."

    parts = [f"{redirects.get('redirect_count', 0)} redirect(s) ending at {redirects.get('final_url', 'unknown')}"]
    if redirects.get("https_upgrade"):
        parts.append("HTTP upgraded to HTTPS")
    if redirects.get("cross_domain_redirect"):
        parts.append("cross-domain redirect detected")
    if redirects.get("loop_detected"):
        parts.append("redirect loop detected")
    return _join(parts)


def _summarize_html(evidence: dict[str, Any]) -> str:
    html = evidence.get("html") or {}
    if _status(html) not in {"ok", "non_html"}:
        return f"HTML analysis {_status(html)}."

    parts = [
        f"Page title '{html.get('title', '') or 'untitled'}'",
        (
            f"{html.get('form_count', 0)} form(s), "
            f"{html.get('password_field_count', 0)} password field(s), "
            f"{html.get('hidden_input_count', 0)} hidden input(s)"
        ),
        (
            f"{html.get('script_count', 0)} script(s) "
            f"({html.get('external_script_count', 0)} external, "
            f"{html.get('inline_script_count', 0)} inline)"
        ),
        f"{html.get('iframe_count', 0)} iframe(s) and {html.get('anchor_count', 0)} anchor(s)",
    ]
    if html.get("external_form_actions"):
        parts.append(
            "external form actions: " + ", ".join(str(item) for item in html["external_form_actions"][:3])
        )
    if html.get("meta_refresh"):
        parts.append(f"meta refresh present: {html['meta_refresh']}")
    return _join(parts)


def _summarize_script_analysis(evidence: dict[str, Any]) -> str:
    scripts = evidence.get("script_analysis") or {}
    if _status(scripts) != "ok":
        return f"Static script analysis {_status(scripts)}."

    parts = [
        (
            f"{scripts.get('script_count', 0)} script tag(s) with "
            f"{scripts.get('external_script_count', 0)} external and "
            f"{scripts.get('inline_script_count', 0)} inline script(s)"
        )
    ]
    suspicious = scripts.get("suspicious_tokens") or []
    if suspicious:
        parts.append(f"suspicious JavaScript tokens found: {', '.join(suspicious[:8])}")
    else:
        parts.append("no suspicious JavaScript tokens matched")

    if scripts.get("encoded_urls"):
        parts.append(f"{len(scripts['encoded_urls'])} encoded URL pattern(s) in inline scripts")
    if scripts.get("base64_like_samples"):
        parts.append(f"{len(scripts['base64_like_samples'])} base64-like string(s) in inline scripts")
    return _join(parts)


def _summarize_cookies(evidence: dict[str, Any]) -> str:
    cookies = evidence.get("cookies") or {}
    if _status(cookies) != "ok":
        return f"Cookie inspection {_status(cookies)}."

    parts = [f"{cookies.get('cookie_count', 0)} HTTP cookie(s) observed"]
    parts.append(f"{cookies.get('secure_count', 0)} secure")
    parts.append(f"{cookies.get('httponly_count', 0)} HttpOnly")
    return _join(parts)


def _summarize_asn(evidence: dict[str, Any]) -> str:
    asn = evidence.get("asn") or {}
    if _status(asn) != "ok":
        return f"ASN lookup {_status(asn)}."

    return _join(
        [
            f"Hosting ASN {asn.get('primary_asn', 'unknown')} ({asn.get('primary_network', 'unknown organization')})",
            f"country {asn.get('primary_country', 'unknown')}",
        ]
    )


def build_evidence_summary(evidence: dict[str, Any]) -> str:
    """Convert raw infrastructure evidence into a compact paragraph for the model."""

    url = evidence.get("url") or evidence.get("input_url") or "unknown URL"
    sections = [
        f"Infrastructure analysis for {url}.",
        _summarize_whois(evidence),
        _summarize_dns(evidence),
        _summarize_tls(evidence),
        _summarize_asn(evidence),
        _summarize_http(evidence),
        _summarize_redirects(evidence),
        _summarize_cookies(evidence),
        _summarize_html(evidence),
        _summarize_script_analysis(evidence),
    ]
    return truncate_to_token_budget(_join(sections))


def collector_statuses(evidence: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for key, value in evidence.items():
        if isinstance(value, dict) and "status" in value:
            statuses[key] = str(value.get("status") or "unknown")
    return statuses


def missing_evidence(evidence: dict[str, Any]) -> list[str]:
    statuses = evidence.get("collector_status") or collector_statuses(evidence)
    missing = []
    for collector, status in statuses.items():
        if status not in {"ok", "partial_socket_resolution", "non_html"}:
            missing.append(f"{collector}: {status}")
    return missing


def _compact_metrics(evidence: dict[str, Any]) -> dict[str, Any]:
    whois = evidence.get("whois") or {}
    html = evidence.get("html") or {}
    http = evidence.get("http") or {}
    redirects = evidence.get("redirects") or {}
    scripts = evidence.get("script_analysis") or {}

    return {
        "whois_status": _status(whois),
        "dns_status": _status(evidence.get("dns")),
        "tls_status": _status(evidence.get("tls")),
        "http_status_code": http.get("status_code"),
        "domain_age_days": whois.get("domain_age_days"),
        "redirect_count": redirects.get("redirect_count", 0),
        "cross_domain_redirect": redirects.get("cross_domain_redirect", False),
        "form_count": html.get("form_count", 0),
        "password_field_count": html.get("password_field_count", 0),
        "iframe_count": html.get("iframe_count", 0),
        "suspicious_script_tokens": len(scripts.get("suspicious_tokens") or []),
        "collector_failures": len(missing_evidence(evidence)),
    }


def preprocess_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Compress infrastructure collector output into a model-ready summary payload."""

    source = deepcopy(evidence)
    summary = build_evidence_summary(source)
    return {
        "module": source.get("module", "Infrastructure Analysis"),
        "url": source.get("url") or source.get("input_url", ""),
        "input_url": source.get("input_url", ""),
        "collected_at": source.get("collected_at", ""),
        "network_enabled": source.get("network_enabled", True),
        "evidence_summary": summary,
        "summary_tokens_estimated": estimate_tokens(summary),
        "metrics": _compact_metrics(source),
        "collector_status": collector_statuses(source),
    }


def to_model_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return evidence already prepared for prompting, or summarize raw evidence."""

    if evidence.get("evidence_summary"):
        return evidence
    return preprocess_evidence(evidence)
