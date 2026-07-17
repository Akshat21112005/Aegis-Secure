"""Runtime specialist package.

Collectors observe live browser behavior. The predictor loads the local model
only when prediction is requested.
"""

from .evidence_builder import build_evidence

__all__ = ["build_evidence"]
