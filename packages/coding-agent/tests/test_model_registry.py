from __future__ import annotations

from coding_agent.model_registry import ModelRegistry


def test_model_registry_get_all():
    registry = ModelRegistry()
    all_models = registry.get_all()
    assert len(all_models) > 0
    for m in all_models:
        assert m.provider
        assert m.id
        assert m.name


def test_model_registry_get_available():
    registry = ModelRegistry()
    available = registry.get_available(has_auth=["anthropic", "openai"])
    assert isinstance(available, list)


def test_model_registry_find():
    registry = ModelRegistry()
    model = registry.find("anthropic", "claude-3-opus")
    if model:
        assert model.name


def test_model_registry_cycle_model():
    registry = ModelRegistry()
    next_model = registry.cycle_model("anthropic", "claude-3-opus", ["anthropic", "openai"])
    if next_model:
        assert next_model.name
