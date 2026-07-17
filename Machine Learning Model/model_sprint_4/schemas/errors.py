from __future__ import annotations


class Sprint4Error(Exception):
    """Base error for model sprint 4."""


class SpecialistError(Sprint4Error):
    """Raised when a specialist fails to produce usable output."""


class FusionError(Sprint4Error):
    """Raised when fusion cannot produce a final decision."""


class EnrichmentError(Sprint4Error):
    """Raised when enrichment steps fail."""
