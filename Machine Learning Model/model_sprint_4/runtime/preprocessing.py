from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlparse


MAX_SUMMARY_TOKENS = 500
APPROX_CHARS_PER_TOKEN = 4
MAX_SUMMARY_CHARS = MAX_SUMMARY_TOKENS * APPROX_CHARS_PER_TOKEN


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


def _hostname(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _summarize_navigation(evidence: dict[str, Any]) -> str:
    navigation = evidence.get("navigation") or {}
    if not navigation:
        return "Navigation evidence unavailable."
    status = navigation.get("status", "unknown")
    final_url = navigation.get("final_url") or evidence.get("url", "")
    status_code = navigation.get("status_code")
    if status == "ok":
        return f"Navigation succeeded to {final_url} with HTTP status {status_code}."
    error = navigation.get("error", "unknown error")
    return f"Navigation failed for {final_url}: {error}."


def _summarize_network(evidence: dict[str, Any], page_host: str) -> str:
    network = evidence.get("network") or {}
    if not network:
        return "Network evidence unavailable."

    parts = [
        (
            f"Observed {network.get('request_count', 0)} requests, "
            f"{network.get('response_count', 0)} responses, "
            f"{network.get('failed_request_count', 0)} failed requests, "
            f"{network.get('download_count', 0)} downloads, and "
            f"{network.get('websocket_count', 0)} websocket connections"
        ),
    ]

    resource_types = network.get("resource_types") or {}
    if resource_types:
        breakdown = ", ".join(f"{count} {name}" for name, count in sorted(resource_types.items()))
        parts.append(f"Resource mix: {breakdown}")

    third_party_count = network.get("third_party_domain_count", 0)
    third_party_domains = network.get("third_party_domains") or []
    if third_party_count:
        sample = ", ".join(third_party_domains[:6])
        parts.append(f"{third_party_count} third-party domains contacted, including {sample}")

    failed_hosts = network.get("failed_hosts") or []
    if failed_hosts:
        parts.append(f"Failed requests involved hosts: {', '.join(failed_hosts[:5])}")

    status_codes = network.get("status_codes") or {}
    if status_codes:
        codes = ", ".join(f"{code} ({count})" for code, count in sorted(status_codes.items()))
        parts.append(f"Response status codes: {codes}")

    return _join(parts)


def _summarize_forms(evidence: dict[str, Any]) -> str:
    forms = evidence.get("forms") or {}
    summary = forms.get("summary") or {}
    if not summary:
        return "No rendered form evidence collected."

    parts = [f"Rendered page contains {summary.get('form_count', 0)} form(s)"]
    if summary.get("password_fields"):
        parts.append(f"{summary['password_fields']} password field(s)")
    if summary.get("email_fields"):
        parts.append(f"{summary['email_fields']} email field(s)")
    if summary.get("hidden_inputs"):
        parts.append(f"{summary['hidden_inputs']} hidden input(s)")
    if summary.get("external_actions"):
        parts.append(f"{summary['external_actions']} form(s) submit to external domains")
    if summary.get("javascript_actions"):
        parts.append(f"{summary['javascript_actions']} form(s) use javascript actions")
    if summary.get("post_forms"):
        parts.append(f"{summary['post_forms']} POST form(s)")
    return _join(parts)


def _summarize_javascript(evidence: dict[str, Any]) -> str:
    javascript = evidence.get("javascript") or {}
    if not javascript:
        return "JavaScript runtime evidence unavailable."

    parts = [
        (
            f"Console shows {javascript.get('console_error_count', 0)} error(s) and "
            f"{javascript.get('console_warning_count', 0)} warning(s)"
        ),
        f"{javascript.get('page_error_count', 0)} unhandled page error(s)",
        f"{javascript.get('dialog_count', 0)} dialog(s)",
    ]

    runtime = javascript.get("runtime_metrics") or {}
    hook_hits = [
        f"{count} {name}"
        for name, count in sorted(runtime.items())
        if isinstance(count, (int, float)) and count > 0 and name.endswith("_calls") or name.endswith("_insertions") or name == "mutation_count"
    ]
    # filter properly
    active_hooks = []
    for key, count in sorted(runtime.items()):
        if isinstance(count, (int, float)) and count > 0:
            active_hooks.append(f"{int(count)} {key.replace('_', ' ')}")
    if active_hooks:
        parts.append("Runtime hooks: " + ", ".join(active_hooks[:10]))

    dom = javascript.get("dom_metrics") or {}
    if dom:
        parts.append(
            (
                f"Live DOM has {dom.get('form_count', 0)} form(s), "
                f"{dom.get('password_fields', 0)} password field(s), "
                f"{dom.get('iframe_count', 0)} iframe(s), "
                f"{dom.get('script_count', 0)} script(s), and "
                f"{dom.get('hidden_inputs', 0)} hidden input(s)"
            )
        )
        if dom.get("title"):
            parts.append(f"Document title is '{dom['title']}'")

    return _join(parts)


def _summarize_storage(evidence: dict[str, Any]) -> str:
    storage = evidence.get("storage") or {}
    if not storage:
        return "Browser storage evidence unavailable."

    parts = []
    cookies = storage.get("cookies") or {}
    if cookies:
        parts.append(
            (
                f"{cookies.get('count', 0)} cookie(s); "
                f"{cookies.get('secure', 0)} secure, "
                f"{cookies.get('http_only', 0)} HttpOnly, "
                f"{cookies.get('session', 0)} session, "
                f"{cookies.get('persistent', 0)} persistent"
            )
        )

    local_storage = storage.get("local_storage") or {}
    if local_storage.get("count"):
        parts.append(f"localStorage has {local_storage['count']} key(s), size {local_storage.get('size', 0)}")

    session_storage = storage.get("session_storage") or {}
    if session_storage.get("count"):
        parts.append(f"sessionStorage has {session_storage['count']} key(s)")

    indexed_db = storage.get("indexed_db") or {}
    if indexed_db.get("count"):
        parts.append(f"IndexedDB has {indexed_db['count']} database(s)")

    cache_api = storage.get("cache_api") or {}
    if cache_api.get("count"):
        parts.append(f"Cache API has {cache_api['count']} cache(s)")

    service_worker = storage.get("service_worker") or {}
    if service_worker.get("registered"):
        parts.append(f"{service_worker.get('count', 0)} service worker registration(s)")

    return _join(parts) if parts else "No meaningful browser storage was observed."


def _summarize_permissions(evidence: dict[str, Any]) -> str:
    permissions = evidence.get("permissions") or {}
    if not permissions:
        return "Permission evidence unavailable."

    states = permissions.get("permission_states") or {}
    granted = [name for name, state in states.items() if state == "granted"]
    prompted = [name for name, state in states.items() if state == "prompt"]
    denied = [name for name, state in states.items() if state == "denied"]

    parts = []
    if granted:
        parts.append(f"Granted permissions: {', '.join(granted)}")
    if prompted:
        parts.append(f"Permissions awaiting prompt: {', '.join(prompted)}")
    if denied:
        parts.append(f"Denied permissions: {', '.join(denied)}")

    apis = permissions.get("api_availability") or {}
    available = [name for name, available in apis.items() if available]
    if available:
        parts.append(f"Browser APIs available: {', '.join(available[:8])}")

    return _join(parts) if parts else "No unusual permission activity observed."


def build_evidence_summary(evidence: dict[str, Any]) -> str:
    """Convert raw runtime evidence into a compact paragraph for the model."""

    url = evidence.get("url") or evidence.get("input_url") or "unknown URL"
    page_host = _hostname(str(url))
    sections = [
        f"Runtime analysis for {url}.",
        _summarize_navigation(evidence),
        _summarize_network(evidence, page_host),
        _summarize_forms(evidence),
        _summarize_javascript(evidence),
        _summarize_storage(evidence),
        _summarize_permissions(evidence),
    ]
    return truncate_to_token_budget(_join(sections))


def _compact_metrics(evidence: dict[str, Any]) -> dict[str, Any]:
    network = evidence.get("network") or {}
    forms = (evidence.get("forms") or {}).get("summary") or {}
    javascript = evidence.get("javascript") or {}
    storage = evidence.get("storage") or {}
    permissions = (evidence.get("permissions") or {}).get("summary") or {}

    return {
        "navigation_status": _status(evidence.get("navigation")),
        "request_count": network.get("request_count", 0),
        "failed_request_count": network.get("failed_request_count", 0),
        "third_party_domain_count": network.get("third_party_domain_count", 0),
        "form_count": forms.get("form_count", 0),
        "password_fields": forms.get("password_fields", 0),
        "external_actions": forms.get("external_actions", 0),
        "console_error_count": javascript.get("console_error_count", 0),
        "page_error_count": javascript.get("page_error_count", 0),
        "cookie_count": (storage.get("cookies") or {}).get("count", 0),
        "local_storage_keys": (storage.get("local_storage") or {}).get("count", 0),
        "permission_prompt_count": permissions.get("prompt_count", 0),
    }


def preprocess_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Compress runtime collector output into a model-ready summary payload."""

    source = deepcopy(evidence)
    summary = build_evidence_summary(source)
    return {
        "module": source.get("module", "Runtime Analysis"),
        "url": source.get("url") or source.get("input_url", ""),
        "input_url": source.get("input_url", ""),
        "collected_at": source.get("collected_at", ""),
        "evidence_summary": summary,
        "summary_tokens_estimated": estimate_tokens(summary),
        "metrics": _compact_metrics(source),
    }


def to_model_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return evidence already prepared for prompting, or summarize raw evidence."""

    if evidence.get("evidence_summary"):
        return evidence
    return preprocess_evidence(evidence)
