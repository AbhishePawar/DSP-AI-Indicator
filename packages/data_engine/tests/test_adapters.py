"""Tests for data_engine.adapters."""

import pytest

from data_engine.adapters import BaseAdapter


class TestBaseAdapter:
    """Tests for the BaseAdapter scaffolding."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseAdapter()  # type: ignore[abstract]

    def test_subclass_must_implement_provider_name(self) -> None:
        class IncompleteAdapter(BaseAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]

    def test_concrete_subclass_exposes_provider_name(self) -> None:
        class FakeAdapter(BaseAdapter):
            @property
            def provider_name(self) -> str:
                return "fake_provider"

        adapter = FakeAdapter()
        assert adapter.provider_name == "fake_provider"
