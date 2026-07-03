from __future__ import annotations

import pytest

from src.assessment_service import AssessmentGenerationError
from src.engine import run_assessment
from src.models import ProjectInput


def project() -> ProjectInput:
    return ProjectInput(
        project_name="Fictional intake delay",
        problem_statement="A fictional request-intake process has avoidable delay and rework.",
        current_symptoms=["requests wait for review", "some requests are reworked"],
        current_metrics={"cycle_time_days": "12"},
        constraints=["No production change during the fictional pilot"],
        stakeholder_concerns=["Operations: reduce waiting time"],
    )


def test_missing_api_key_is_disclosed_as_deterministic_fallback(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = run_assessment(project(), mode="dmaic", audience="pm")

    assert result.generation_mode == "deterministic_fallback"
    assert result.model_name is None
    assert result.fallback_reason
    assert "No ANTHROPIC_API_KEY" in result.fallback_reason
    assert result.role_summary.startswith("Generation note: deterministic fallback.")


def test_fallback_does_not_present_unvalidated_input_as_confirmed(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = run_assessment(project(), mode="dmaic", audience="executive")

    assert "confirmed performance gap" not in result.role_summary
    assert "reported performance concern" in result.role_summary
    assert "measurable performance gap" not in result.cleaned_problem_statement
    assert "reported performance concern" in result.cleaned_problem_statement
    assert result.dmaic_structure["define"][0].statement.startswith(
        "Reported problem statement:"
    )


def test_require_llm_fails_instead_of_silently_falling_back(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(AssessmentGenerationError, match="No ANTHROPIC_API_KEY"):
        run_assessment(project(), mode="dmaic", audience="pm", require_llm=True)
