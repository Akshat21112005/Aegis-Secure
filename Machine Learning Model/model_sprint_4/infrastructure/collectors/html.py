from __future__ import annotations

import re
from typing import Any

from ._utils import DEFAULT_USER_AGENT, limit_string, make_absolute_url, normalize_url, safe_error, unique


def _empty(target: str, status: str, error: str = "") -> dict[str, Any]:
    return {
        "collector": "html",
        "status": status,
        "url": target,
        "title": "",
        "language": "",
        "charset": "",
        "viewport": "",
        "canonical_url": "",
        "meta_refresh": "",
        "meta_count": 0,
        "form_count": 0,
        "password_field_count": 0,
        "hidden_input_count": 0,
        "external_form_actions": [],
        "input_types": {},
        "button_count": 0,
        "anchor_count": 0,
        "image_count": 0,
        "iframe_count": 0,
        "script_count": 0,
        "external_script_count": 0,
        "inline_script_count": 0,
        "stylesheet_count": 0,
        "comment_count": 0,
        "resource_domains": [],
        "script_sources": [],
        "inline_script_samples": [],
        "_html_source": "",
        "error": error,
    }


def _parse_with_bs4(target: str, html: str) -> dict[str, Any]:
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(html, "html.parser")
    evidence = _empty(target, "ok")
    evidence["_html_source"] = html
    if soup.title and soup.title.string:
        evidence["title"] = limit_string(soup.title.string, 180)
    html_tag = soup.find("html")
    if html_tag:
        evidence["language"] = limit_string(html_tag.get("lang", ""), 40)
    charset_tag = soup.find("meta", attrs={"charset": True})
    if charset_tag:
        evidence["charset"] = limit_string(charset_tag.get("charset", ""), 80)
    viewport = soup.find("meta", attrs={"name": lambda value: str(value).lower() == "viewport"})
    if viewport:
        evidence["viewport"] = limit_string(viewport.get("content", ""), 200)
    canonical = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    if canonical:
        evidence["canonical_url"] = make_absolute_url(target, canonical.get("href", ""))
    refresh = soup.find("meta", attrs={"http-equiv": lambda value: str(value).lower() == "refresh"})
    if refresh:
        evidence["meta_refresh"] = limit_string(refresh.get("content", ""), 250)

    forms = soup.find_all("form")
    evidence["form_count"] = len(forms)
    external_actions: list[str] = []
    for form in forms:
        action = make_absolute_url(target, form.get("action", ""))
        if action:
            external_actions.append(action)
    evidence["external_form_actions"] = unique(external_actions, 20)

    input_types: dict[str, int] = {}
    for input_tag in soup.find_all("input"):
        input_type = str(input_tag.get("type", "text") or "text").lower()
        input_types[input_type] = input_types.get(input_type, 0) + 1
    evidence["input_types"] = input_types
    evidence["password_field_count"] = input_types.get("password", 0)
    evidence["hidden_input_count"] = input_types.get("hidden", 0)
    evidence["button_count"] = len(soup.find_all(["button", "input"], attrs={"type": "submit"}))
    evidence["anchor_count"] = len(soup.find_all("a"))
    evidence["image_count"] = len(soup.find_all("img"))
    evidence["iframe_count"] = len(soup.find_all("iframe"))
    evidence["meta_count"] = len(soup.find_all("meta"))
    evidence["stylesheet_count"] = len(soup.find_all("link", rel=lambda value: value and "stylesheet" in value))
    evidence["comment_count"] = len(soup.find_all(string=lambda text: isinstance(text, Comment)))

    scripts = soup.find_all("script")
    script_sources: list[str] = []
    inline_samples: list[str] = []
    for script in scripts:
        src = script.get("src", "")
        if src:
            script_sources.append(make_absolute_url(target, src))
        else:
            text = script.string or script.get_text(" ", strip=True)
            if text:
                inline_samples.append(limit_string(text, 1000))
    evidence["script_count"] = len(scripts)
    evidence["script_sources"] = unique(script_sources, 50)
    evidence["external_script_count"] = len(evidence["script_sources"])
    evidence["inline_script_samples"] = inline_samples[:8]
    evidence["inline_script_count"] = len(inline_samples)

    resources = evidence["script_sources"][:]
    for tag, attr in [("img", "src"), ("link", "href"), ("iframe", "src")]:
        for item in soup.find_all(tag):
            absolute = make_absolute_url(target, item.get(attr, ""))
            if absolute:
                resources.append(absolute)
    domains = []
    for resource in resources:
        from ._utils import extract_hostname

        host = extract_hostname(resource)
        if host:
            domains.append(host)
    evidence["resource_domains"] = unique(domains, 50)
    return evidence


def _parse_with_regex(target: str, html: str) -> dict[str, Any]:
    evidence = _empty(target, "ok")
    evidence["_html_source"] = html
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if title:
        evidence["title"] = limit_string(re.sub(r"\s+", " ", title.group(1)), 180)
    evidence["form_count"] = len(re.findall(r"<form\b", html, re.I))
    evidence["password_field_count"] = len(re.findall(r'type=["\']?password', html, re.I))
    evidence["hidden_input_count"] = len(re.findall(r'type=["\']?hidden', html, re.I))
    evidence["anchor_count"] = len(re.findall(r"<a\b", html, re.I))
    evidence["image_count"] = len(re.findall(r"<img\b", html, re.I))
    evidence["iframe_count"] = len(re.findall(r"<iframe\b", html, re.I))
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.I | re.S)
    evidence["script_count"] = len(re.findall(r"<script\b", html, re.I))
    evidence["inline_script_samples"] = [limit_string(script, 1000) for script in scripts[:8] if script.strip()]
    evidence["inline_script_count"] = len(evidence["inline_script_samples"])
    evidence["external_script_count"] = len(re.findall(r"<script\b[^>]+src=", html, re.I))
    evidence["stylesheet_count"] = len(re.findall(r"<link\b[^>]+stylesheet", html, re.I))
    evidence["comment_count"] = len(re.findall(r"<!--", html))
    return evidence


def collect_html(url: str, *, timeout: float = 8.0, enable_network: bool = True) -> dict[str, Any]:
    target = normalize_url(url)
    if not target:
        return _empty("", "no_url")
    if not enable_network:
        return _empty(target, "skipped")
    try:
        import requests

        response = requests.get(
            target,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower() and "<html" not in response.text[:500].lower():
            evidence = _empty(target, "non_html")
            evidence["content_type"] = limit_string(content_type, 160)
            return evidence
        html = response.text[:500_000]
        try:
            return _parse_with_bs4(target, html)
        except Exception:
            return _parse_with_regex(target, html)
    except Exception as exc:
        return _empty(target, "failed", safe_error(exc))

