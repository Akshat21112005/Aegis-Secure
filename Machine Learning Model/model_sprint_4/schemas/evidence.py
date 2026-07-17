from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceType(str, Enum):
    MESSAGE_TEXT = "message_text"
    URL = "url"
    SCREENSHOT = "screenshot"
    OCR_TEXT = "ocr_text"
    QR_PAYLOAD = "qr_payload"
    ATTACHMENT = "attachment"
    PLAYWRIGHT = "playwright"
    SPECIALIST = "specialist"


@dataclass
class EvidenceItem:
    evidence_id: str
    evidence_type: EvidenceType
    source: str
    summary: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "source": self.source,
            "summary": self.summary,
            "snippet": self.snippet,
            "metadata": self.metadata,
        }
