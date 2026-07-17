from schemas.communication_event import CommunicationEvent

from .attachments import extract_attachments
from .headers import parse_headers
from .mime_parser import parse_mime


def parse_gmail_message(message: dict) -> CommunicationEvent:

    payload = message.get(
        "payload",
        {},
    )

    headers = parse_headers(
        payload.get(
            "headers",
            [],
        )
    )

    plain_text, html = parse_mime(
        payload,
    )

    attachments = extract_attachments(
        payload,
    )

    return CommunicationEvent(

        message_id=message.get(
            "id",
            "",
        ),

        thread_id=message.get(
            "threadId",
            "",
        ),

        subject=headers.get(
            "subject",
            "",
        ),

        sender=headers.get(
            "from",
            "",
        ),

        receiver=headers.get(
            "to",
            "",
        ),

        cc=headers.get(
            "cc",
            "",
        ),

        bcc=headers.get(
            "bcc",
            "",
        ),

        reply_to=headers.get(
            "reply-to",
            "",
        ),

        date=headers.get(
            "parsed_date",
        ),

        plain_text=plain_text,

        html=html,

        attachments=attachments,

        labels=message.get(
            "labelIds",
            [],
        ),

        snippet=message.get(
            "snippet",
            "",
        ),

        history_id=message.get(
            "historyId",
            "",
        ),
    )