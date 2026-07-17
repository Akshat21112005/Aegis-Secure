from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CommunicationEvent:
    """Normalized email or SMS message used by ingestion and enrichment."""

    message_id: str = ""
    thread_id: str = ""
    history_id: str = ""
    subject: str = ""
    sender: str = ""
    receiver: str = ""
    cc: str = ""
    bcc: str = ""
    reply_to: str = ""
    date: datetime | None = None
    plain_text: str = ""
    html: str = ""
    snippet: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
