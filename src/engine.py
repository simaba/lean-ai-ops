from __future__ import annotations

from src.assessment_service import run_assessment_with_provenance
from src.models import AssessmentResult, ProjectInput


def run_assessment(
    project: ProjectInput,
    mode: str,
    audience: str,
    *,
    require_llm: bool = False,
) -> AssessmentResult:
    """Generate an assessment with explicit model/fallback provenance."""
    return run_assessment_with_provenance(
        project,
        mode,
        audience,
        require_llm=require_llm,
    )
