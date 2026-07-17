"""Shared data schemas for the AEGIS pipeline."""

from .communication_event import CommunicationEvent
from .errors import EnrichmentError, FusionError, SpecialistError, Sprint4Error
from .evidence import EvidenceItem, EvidenceType
from .playwright_artifact import PlaywrightArtifact, ScreenshotArtifact
from .prediction_response import CompatibilityResponse, PredictionResponse
from .specialist_outputs import (
    InfrastructureEvidence,
    RuntimeEvidence,
    SemanticEvidence,
    SpecialistOutput,
    VisualEvidence,
)

__all__ = [
    "CommunicationEvent",
    "CompatibilityResponse",
    "EnrichmentError",
    "EvidenceItem",
    "EvidenceType",
    "FusionError",
    "InfrastructureEvidence",
    "PlaywrightArtifact",
    "PredictionResponse",
    "RuntimeEvidence",
    "ScreenshotArtifact",
    "SemanticEvidence",
    "SpecialistError",
    "SpecialistOutput",
    "Sprint4Error",
    "VisualEvidence",
]
