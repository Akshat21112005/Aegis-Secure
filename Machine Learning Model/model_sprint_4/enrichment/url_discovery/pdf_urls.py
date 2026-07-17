from __future__ import annotations

from pathlib import Path

import fitz

from .text import extract_urls_from_text


def extract_urls_from_pdf(pdf_source: bytes | str) -> list[str]:
    if isinstance(pdf_source, (str, Path)):
        path = Path(pdf_source)
        if not path.is_file():
            return []
        pdf_bytes = path.read_bytes()
    else:
        pdf_bytes = pdf_source

    if not pdf_bytes:
        return []

    urls = []

    try:

        document = fitz.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

    except Exception:

        return []

    for page in document:

        links = page.get_links()

        for link in links:

            uri = link.get("uri")

            if uri:

                urls.append(uri.strip())

        text = page.get_text()

        urls.extend(
            extract_urls_from_text(text)
        )

    document.close()

    return urls