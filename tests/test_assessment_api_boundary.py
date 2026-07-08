from __future__ import annotations

import inspect

import src.engine as engine
from src.assessment_service import run_assessment_with_provenance


def test_engine_delegates_to_provenance_aware_generation_service() -> None:
    source = inspect.getsource(engine)

    assert engine.run_assessment.__module__ == "src.engine"
    assert "run_assessment_with_provenance" in source
    assert "run_llm_assessment" not in source


def test_engine_uses_the_supported_generation_service() -> None:
    result = engine.run_assessment

    assert callable(result)
    assert callable(run_assessment_with_provenance)
