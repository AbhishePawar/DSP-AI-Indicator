"""Tests for CommitteeError hierarchy."""

from __future__ import annotations

import pytest

from ai_committee.exceptions import CommitteeError
from core.exceptions import DSPAIError


class TestCommitteeError:
    """Tests for the committee exception hierarchy."""

    def test_is_a_dspai_error(self) -> None:
        assert issubclass(CommitteeError, DSPAIError)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(CommitteeError):
            raise CommitteeError("deliberation failed")
