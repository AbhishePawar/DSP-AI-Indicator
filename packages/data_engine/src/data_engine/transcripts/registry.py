"""Transcript provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.transcripts.service import TranscriptProviderPort

__all__ = ["TranscriptProviderRegistry"]


class TranscriptProviderRegistry(PriorityProviderRegistry[TranscriptProviderPort]):
    """Registry of authenticated transcript providers, ordered by priority."""
