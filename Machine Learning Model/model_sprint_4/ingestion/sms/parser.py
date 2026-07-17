from datetime import datetime

from schemas.communication_event import CommunicationEvent

from .normalizer import normalize_sms


def parse_sms(message: dict) -> CommunicationEvent:

    timestamp = message.get(
        "date",
    )

    if timestamp:

        try:

            timestamp = datetime.fromtimestamp(
                timestamp / 1000,
            )

        except Exception:

            timestamp = None

    else:

        timestamp = None

    return CommunicationEvent(

        message_id=str(
            message.get(
                "_id",
                "",
            )
        ),

        thread_id=str(
            message.get(
                "thread_id",
                "",
            )
        ),

        history_id="",

        subject="",

        sender=message.get(
            "address",
            "",
        ),

        receiver="",

        cc="",

        bcc="",

        reply_to="",

        date=timestamp,

        plain_text=normalize_sms(
            message.get(
                "body",
                "",
            )
        ),

        html="",

        snippet=message.get(
            "body",
            "",
        )[:120],

        attachments=[],

        labels=[],
    )