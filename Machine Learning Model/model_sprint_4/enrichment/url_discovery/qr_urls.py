from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from pyzbar.pyzbar import decode

from .text import extract_urls_from_text


def extract_urls_from_qr(image_source: bytes | str) -> list[str]:
    if isinstance(image_source, (str, Path)):
        path = Path(image_source)
        if not path.is_file():
            return []
        image_bytes = path.read_bytes()
    else:
        image_bytes = image_source

    if not image_bytes:
        return []

    image = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        return []

    urls = []

    for qr in decode(image):

        try:

            payload = qr.data.decode(
                "utf-8",
                errors="ignore",
            )

        except Exception:

            continue

        urls.extend(
            extract_urls_from_text(payload)
        )

    return urls