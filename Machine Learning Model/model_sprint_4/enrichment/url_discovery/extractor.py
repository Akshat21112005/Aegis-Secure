from typing import List

from .mime import extract_urls_from_mime
from .text import extract_urls_from_text
from .html import extract_urls_from_html
from .pdf_urls import extract_urls_from_pdf
from .qr_urls import extract_urls_from_qr
from .canonicalizer import canonicalize_urls


def extract_urls(
    plain_text: str = "",
    html: str = "",
    mime_payload: dict | None = None,
    pdf_paths: List[str] | None = None,
    qr_images: List[str] | None = None,
) -> List[str]:
    """
    Extract every possible URL from a communication.

    Sources:
    - MIME tree
    - Plain text
    - HTML
    - PDFs
    - QR images

    Returns:
        Canonicalized unique URLs.
    """

    urls = []

    if mime_payload is not None:
        urls.extend(extract_urls_from_mime(mime_payload))

    if plain_text:
        urls.extend(extract_urls_from_text(plain_text))

    if html:
        urls.extend(extract_urls_from_html(html))

    if pdf_paths:
        for pdf in pdf_paths:
            urls.extend(extract_urls_from_pdf(pdf))

    if qr_images:
        for image in qr_images:
            urls.extend(extract_urls_from_qr(image))

    return canonicalize_urls(urls)