from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class SpecialistOutput:
    module: str
    prediction: str
    confidence: float
    risk_score: float
    summary: str = ""
    positive_indicators: list[str] = field(default_factory=list)
    negative_indicators: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    raw_output: str = ""
    error: str = ""
    latency_seconds: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def risk(self) -> float:
        return _clamp(self.risk_score / 100.0 if self.risk_score > 1 else self.risk_score)

    @property
    def confidence_normalized(self) -> float:
        return _clamp(self.confidence / 100.0 if self.confidence > 1 else self.confidence)

    @property
    def available(self) -> bool:
        return not self.error

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "summary": self.summary,
            "positive_indicators": self.positive_indicators,
            "negative_indicators": self.negative_indicators,
            "missing_evidence": self.missing_evidence,
            "raw_output": self.raw_output,
            "error": self.error,
            "latency_seconds": self.latency_seconds,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass
class SemanticEvidence(SpecialistOutput):
    urgency_detected: bool = False
    authority_language: bool = False
    credential_request: bool = False
    financial_pressure: bool = False
    phishing_probability: float = 0.0


@dataclass
class InfrastructureEvidence(SpecialistOutput):
    brand_match: bool = False
    domain_age_days: int | None = None
    spf_valid: bool | None = None
    tls_valid: bool | None = None
    redirect_depth: int = 0


@dataclass
class RuntimeEvidence(SpecialistOutput):
    password_form: bool = False
    otp_form: bool = False
    external_form_action: bool = False
    telegram_exfiltration: bool = False
    suspicious_downloads: bool = False


@dataclass
class VisualEvidence(SpecialistOutput):
    ocr_detected: bool = False
    qr_detected: bool = False
    brand_impersonation: bool = False
    login_screen_detected: bool = False
    suspicious_attachment: bool = False
