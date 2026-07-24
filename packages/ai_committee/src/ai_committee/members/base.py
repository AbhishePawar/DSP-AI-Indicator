"""Abstract committee member interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contracts.enums import EngineSource

from ai_committee.models import CommitteeInput, Opinion

__all__ = ["CommitteeMember"]


class CommitteeMember(ABC):
    """Base class every AI Investment Committee member must implement.

    A member does not run an upstream engine. It reads that engine's
    already-produced analysis from :class:`CommitteeInput` and returns
    one standardized :class:`~ai_committee.models.Opinion`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical, lowercase identifier for this member."""

    @property
    @abstractmethod
    def source_engine(self) -> EngineSource:
        """Provenance tag for the upstream engine this member represents."""

    @abstractmethod
    def analyze(self, context: CommitteeInput) -> Opinion:
        """Produce an :class:`Opinion` from the deliberation context.

        Args:
            context: Upstream engine outputs for this deliberation.

        Returns:
            A standardized member opinion.
        """
