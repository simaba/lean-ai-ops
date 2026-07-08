"""Assessment orchestration with explicit model/fallback provenance."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Any, Dict

from src.models import AssessmentResult, ProjectInput
from src.phases import (
    _SYSTEM_PROMPT,
    _build_user_message,
    _deterministic_fallback,
    _parse_dmaic,
    _parse_items,
)


MODEL_NAME = "claude-sonnet-4-6"


class AssessmentGenerationError(RuntimeError):
    """Raised when an LLM result is required but cannot be generated."""


def _generation_note(mode: str, reason: str | None = None) -> str:
    """Return a concise provenance note suitable for user-visible summaries."""
    if mode == "llm":
        return f"Generation note: live model output ({MODEL_NAME})."
    suffix = reason or "Deterministic fallback was used."
    return f"Generation note: deterministic fallback. {suffix}"


def _soften_fallback_certainty(result: AssessmentResult) -> AssessmentResult:
    """Keep deterministic starter output from overstating unvalidated inputs."""
    define_items = [
        replace(
            item,
            statement=item.statement.replace(
                "Problem confirmed:", "Reported problem statement:"
            ),
        )
        for item in result.dmaic_structure.get("define", [])
    ]
    dmaic_structure = {**result.dmaic_structure, "define": define_items}
    return replace(
        result,
        cleaned_problem_statement=result.cleaned_problem_statement.replace(
            "has a measurable performance gap:",
            "has a reported performance concern:",
        ),
        role_summary=result.role_summary.replace(
            "has a confirmed performance gap", "has a reported performance concern"
        ),
        dmaic_structure=dmaic_structure,
    )


def _fallback(
    project: ProjectInput,
    mode: str,
    audience: str,
    reason: str,
) -> AssessmentResult:
    """Return a deterministic result that records why it was used."""
    result = _soften_fallback_certainty(_deterministic_fallback(project, mode, audience))
    return replace(
        result,
        role_summary=f"{_generation_note('deterministic_fallback', reason)}\n\n{result.role_summary}",
        generation_mode="deterministic_fallback",
        model_name=None,
        fallback_reason=reason,
    )


def _reason_from_exception(exc: Exception) -> str:
    """Provide an actionable category without exposing credentials or payloads."""
    if isinstance(exc, json.JSONDecodeError):
        return "The model response was not valid JSON for the required assessment structure."
    if isinstance(exc, (KeyError, TypeError, ValueError, IndexError)):
        return "The model response did not match the required assessment structure."
    if isinstance(exc, ImportError):
        return "The optional Anthropic client package is unavailable in this environment."
    return "The live model request could not be completed."


def run_assessment_with_provenance(
    project: ProjectInput,
    mode: str,
    audience: str,
    *,
    require_llm: bool = False,
) -> AssessmentResult:
    """Generate an assessment and label whether it came from the LLM or fallback.

    The fallback remains useful for demonstrations and offline work. When
    ``require_llm`` is true, an unavailable or malformed live response raises a
    concise error instead of silently substituting deterministic output.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        reason = "No ANTHROPIC_API_KEY is configured; deterministic fallback was used."
        if require_llm:
            raise AssessmentGenerationError(reason)
        return _fallback(project, mode, audience, reason)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(project, mode, audience)}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
            raw = raw.strip()
        data: Dict[str, Any] = json.loads(raw)
        return AssessmentResult(
            project_name=project.project_name,
            mode=mode,
            audience=audience,
            cleaned_problem_statement=data["cleaned_problem_statement"],
            ctqs=_parse_items(data["ctqs"]),
            sipoc=data["sipoc"],
            dmaic_structure=_parse_dmaic(data["dmaic_structure"]),
            root_causes=_parse_items(data["root_causes"]),
            suggested_metrics=_parse_items(data["suggested_metrics"]),
            improvement_actions=_parse_items(data["improvement_actions"]),
            control_plan=_parse_items(data["control_plan"]),
            action_tracker=data["action_tracker"],
            project_memory=data["project_memory"],
            role_summary=f"{_generation_note('llm')}\n\n{data['role_summary']}",
            generation_mode="llm",
            model_name=MODEL_NAME,
            fallback_reason=None,
        )
    except Exception as exc:
        reason = _reason_from_exception(exc)
        if require_llm:
            raise AssessmentGenerationError(reason) from exc
        return _fallback(project, mode, audience, reason)
