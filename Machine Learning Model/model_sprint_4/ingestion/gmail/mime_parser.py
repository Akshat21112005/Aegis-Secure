import base64
import quopri


def parse_mime(payload: dict) -> tuple[str, str]:

    plain_parts = []

    html_parts = []

    _walk(
        payload,
        plain_parts,
        html_parts,
    )

    plain_text = "\n".join(
        plain_parts
    ).strip()

    html = "\n".join(
        html_parts
    ).strip()

    return plain_text, html


def _walk(
    part: dict,
    plain_parts: list[str],
    html_parts: list[str],
) -> None:

    mime_type = part.get(
        "mimeType",
        "",
    )

    body = part.get(
        "body",
        {},
    )

    data = body.get(
        "data",
    )

    if data:

        headers = {
            header.get("name", "").lower():
            header.get("value", "")
            for header in part.get(
                "headers",
                []
            )
        }

        encoding = headers.get(
            "content-transfer-encoding",
            "base64",
        ).lower()

        text = _decode(
            data,
            encoding,
        )

        if mime_type == "text/plain":

            plain_parts.append(
                text
            )

        elif mime_type == "text/html":

            html_parts.append(
                text
            )

    for child in part.get(
        "parts",
        [],
    ):

        _walk(
            child,
            plain_parts,
            html_parts,
        )


def _decode(
    data: str,
    encoding: str,
) -> str:

    try:

        raw = base64.urlsafe_b64decode(
            data
        )

        if encoding == "quoted-printable":

            raw = quopri.decodestring(
                raw
            )

        return raw.decode(
            "utf-8",
            errors="ignore",
        )

    except Exception:

        return ""