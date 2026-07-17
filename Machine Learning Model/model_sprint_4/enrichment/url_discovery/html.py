import re

from bs4 import BeautifulSoup

from .text import extract_urls_from_text


URL_ATTRIBUTES = (
    ("a", "href"),
    ("img", "src"),
    ("script", "src"),
    ("iframe", "src"),
    ("link", "href"),
    ("form", "action"),
)


def extract_urls_from_html(html: str) -> list[str]:

    if not html:
        return []

    urls = []

    try:

        soup = BeautifulSoup(html, "lxml")

    except Exception:

        return []

    for tag, attribute in URL_ATTRIBUTES:

        for element in soup.find_all(tag):

            value = element.get(attribute)

            if value:

                urls.append(value.strip())

    for meta in soup.find_all("meta"):

        http_equiv = meta.get("http-equiv", "").lower()

        if http_equiv != "refresh":
            continue

        content = meta.get("content", "")

        match = re.search(
            r'url\s*=\s*(.+)',
            content,
            re.IGNORECASE,
        )

        if match:

            urls.append(match.group(1).strip())

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    urls.extend(
        extract_urls_from_text(text)
    )

    return urls