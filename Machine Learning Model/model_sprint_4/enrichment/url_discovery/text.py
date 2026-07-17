# Plain text URL extraction logic.
import re


URL_PATTERN = re.compile(
    r"""
    (?:
        https?://
        |
        www\.
    )
    [^\s<>"'()]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_urls_from_text(text: str) -> list[str]:

    if not text:
        return []

    urls = []

    for match in URL_PATTERN.finditer(text):

        url = match.group(0).rstrip(
            ".,;:!?)]}>\"'"
        )

        urls.append(url)

    return urls