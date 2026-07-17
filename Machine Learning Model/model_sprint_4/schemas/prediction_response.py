from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .evidence import EvidenceItem
from .specialist_outputs import (
    InfrastructureEvidence,
    RuntimeEvidence,
    SemanticEvidence,
    SpecialistOutput,
    VisualEvidence,
)


@dataclass
class CompatibilityResponse:
    confidence: float
    reasoning: str
    highlighted_text: str
    final_decision: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "highlighted_text": self.highlighted_text,
            "final_decision": self.final_decision,
            "suggestion": self.suggestion,
        }


@dataclass
class PredictionResponse:
    request_id: str
    final_decision: str
    overall_risk_score: float
    confidence: float
    summary: str
    specialist_outputs: list[SpecialistOutput] = field(default_factory=list)
    semantic: SemanticEvidence | None = None
    infrastructure: InfrastructureEvidence | None = None
    runtime: RuntimeEvidence | None = None
    visual: VisualEvidence | None = None
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    highlighted_text: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    compatibility: CompatibilityResponse | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "final_decision": self.final_decision,
            "overall_risk_score": self.overall_risk_score,
            "confidence": self.confidence,
            "summary": self.summary,
            "specialist_outputs": [item.to_dict() for item in self.specialist_outputs],
            "semantic": self.semantic.to_dict() if self.semantic else None,
            "infrastructure": self.infrastructure.to_dict() if self.infrastructure else None,
            "runtime": self.runtime.to_dict() if self.runtime else None,
            "visual": self.visual.to_dict() if self.visual else None,
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "highlighted_text": self.highlighted_text,
            "recommended_actions": self.recommended_actions,
            "compatibility": self.compatibility.to_dict() if self.compatibility else None,
            "metadata": self.metadata,
        }
