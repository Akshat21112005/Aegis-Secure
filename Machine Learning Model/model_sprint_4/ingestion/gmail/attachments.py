import base64


TEXT_MIME_TYPES = {
    "text/plain",
    "text/html",
}


def extract_attachments(payload: dict) -> list[dict]:

    attachments = []

    _walk(
        payload,
        attachments,
    )

    return attachments


def _walk(
    part: dict,
    attachments: list[dict],
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

    if (
        mime_type not in TEXT_MIME_TYPES
        and data
    ):

        try:

            content = base64.urlsafe_b64decode(
                data
            )

        except Exception:

            content = b""

        attachments.append(
            {
                "filename": part.get(
                    "filename",
                    "",
                ),
                "mime_type": mime_type,
                "content": content,
                "size": body.get(
                    "size",
                    0,
                ),
            }
        )

    for child in part.get(
        "parts",
        [],
    ):

        _walk(
            child,
            attachments,
        )