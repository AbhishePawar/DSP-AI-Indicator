"""Tests for the generic Registry infrastructure."""

import pytest

from core.registry import Registry


class TestRegistry:
    """Tests for registration, lookup, and discovery on Registry."""

    def test_register_and_get(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("alpha", 1)
        assert registry.get("alpha") == 1

    def test_lookup_is_case_insensitive(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("Alpha", 1)
        assert registry.get("ALPHA") == 1
        assert registry.get("alpha") == 1

    def test_register_returns_item(self) -> None:
        registry: Registry[str] = Registry(kind="item")
        result = registry.register("name", "value")
        assert result == "value"

    def test_reregistering_identical_item_is_a_noop(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("alpha", 1)
        registry.register("alpha", 1)
        assert registry.get("alpha") == 1

    def test_register_conflicting_name_raises(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("alpha", 1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("alpha", 2)

    def test_get_unknown_name_raises(self) -> None:
        registry: Registry[int] = Registry(kind="widget")
        with pytest.raises(KeyError, match="Unknown widget"):
            registry.get("missing")

    def test_list_names_sorted(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("charlie", 3)
        registry.register("alpha", 1)
        registry.register("bravo", 2)
        assert registry.list_names() == ["alpha", "bravo", "charlie"]

    def test_contains(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        registry.register("alpha", 1)
        assert "alpha" in registry
        assert "ALPHA" in registry
        assert "missing" not in registry

    def test_len(self) -> None:
        registry: Registry[int] = Registry(kind="item")
        assert len(registry) == 0
        registry.register("alpha", 1)
        registry.register("bravo", 2)
        assert len(registry) == 2

    def test_default_kind_label(self) -> None:
        registry: Registry[int] = Registry()
        with pytest.raises(KeyError, match="Unknown item"):
            registry.get("missing")

    def test_generic_over_arbitrary_types(self) -> None:
        class Widget:
            pass

        registry: Registry[type[Widget]] = Registry(kind="widget")
        registry.register("basic", Widget)
        assert registry.get("basic") is Widget
