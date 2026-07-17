from urllib.parse import urlparse, urlunparse


def canonicalize_url(url: str) -> str:

    url = url.strip()

    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:

        parsed = urlparse(url)

        scheme = parsed.scheme.lower()

        netloc = parsed.netloc.lower()

        path = parsed.path.rstrip("/")

        return urlunparse((
            scheme,
            netloc,
            path,
            "",
            parsed.query,
            "",
        ))

    except Exception:

        return ""


def canonicalize_urls(urls: list[str]) -> list[str]:

    seen = set()

    result = []

    for url in urls:

        canonical = canonicalize_url(url)

        if not canonical:
            continue

        if canonical in seen:
            continue

        seen.add(canonical)

        result.append(canonical)

    return result