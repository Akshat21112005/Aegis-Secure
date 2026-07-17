from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Any

from ._utils import DEFAULT_USER_AGENT, limit_string, normalize_url, safe_error


def _cookie_from_requests(cookie: Any) -> dict[str, Any]:
    rest = getattr(cookie, "_rest", {}) or {}
    return {
        "name": limit_string(getattr(cookie, "name", ""), 120),
        "domain": limit_string(getattr(cookie, "domain", ""), 180),
        "path": limit_string(getattr(cookie, "path", ""), 120),
        "secure": bool(getattr(cookie, "secure", False)),
        "httponly": any(str(key).lower() == "httponly" for key in rest.keys()),
        "samesite": limit_string(rest.get("SameSite") or rest.get("samesite") or "", 80),
        "expires": getattr(cookie, "expires", None),
        "session_cookie": getattr(cookie, "expires", None) is None,
    }


def _cookie_from_header(header: str) -> list[dict[str, Any]]:
    parsed = SimpleCookie()
    try:
        parsed.load(header or "")
    except Exception:
        return []
    cookies = []
    for morsel in parsed.values():
        cookies.append(
            {
                "name": limit_string(morsel.key, 120),
                "domain": limit_string(morsel["domain"], 180),
                "path": limit_string(morsel["path"], 120),
                "secure": bool(morsel["secure"]),
                "httponly": bool(morsel["httponly"]),
                "samesite": limit_string(morsel["samesite"], 80),
                "expires": limit_string(morsel["expires"], 120),
                "session_cookie": not bool(morsel["expires"] or morsel["max-age"]),
            }
        )
    return cookies


def collect_cookies(url: str, *, timeout: float = 8.0, enable_network: bool = True) -> dict[str, Any]:
    target = normalize_url(url)
    evidence: dict[str, Any] = {
        "collector": "cookies",
        "status": "unknown",
        "url": target,
        "cookie_count": 0,
        "cookies": [],
        "set_cookie_header_count": 0,
        "secure_count": 0,
        "httponly_count": 0,
        "samesite_count": 0,
        "session_cookie_count": 0,
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
            allow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        cookies = [_cookie_from_requests(cookie) for cookie in response.cookies]
        raw_set_cookie = response.headers.get("Set-Cookie", "")
        if raw_set_cookie and not cookies:
            cookies = _cookie_from_header(raw_set_cookie)
        evidence["status"] = "ok"
        evidence["cookies"] = cookies[:40]
        evidence["cookie_count"] = len(cookies)
        evidence["set_cookie_header_count"] = 1 if raw_set_cookie else 0
        evidence["secure_count"] = sum(1 for cookie in cookies if cookie.get("secure"))
        evidence["httponly_count"] = sum(1 for cookie in cookies if cookie.get("httponly"))
        evidence["samesite_count"] = sum(1 for cookie in cookies if cookie.get("samesite"))
        evidence["session_cookie_count"] = sum(1 for cookie in cookies if cookie.get("session_cookie"))
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = safe_error(exc)
    return evidence

