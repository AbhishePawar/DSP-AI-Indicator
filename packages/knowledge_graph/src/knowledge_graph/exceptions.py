"""Knowledge Graph package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["KnowledgeGraphError"]


class KnowledgeGraphError(DSPAIError):
    """Raised for Knowledge Graph domain invariant violations."""
