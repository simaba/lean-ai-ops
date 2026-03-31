from __future__ import annotations

from src.canonical_phases import (
    build_action_tracker,
    build_control_plan,
    build_ctqs,
    build_dmaic_structure,
    build_improvement_actions,
    build_project_memory,
    build_role_summary,
    build_root_causes,
    build_sipoc,
    build_suggested_metrics,
    clean_problem_statement,
)
from src.models import AssessmentResult, ProjectInput


def run_assessment(project: ProjectInput, mode: str, audience: str) -> AssessmentResult:
    cleaned_problem_statement = clean_problem_statement(project)
    ctqs = build_ctqs(project)
    sipoc = build_sipoc(project)
    dmaic_structure = build_dmaic_structure(project)
    root_causes = build_root_causes(project)
    suggested_metrics = build_suggested_metrics(project)
    improvement_actions = build_improvement_actions(project)
    control_plan = build_control_plan(project, improvement_actions)
    action_tracker = build_action_tracker(improvement_actions)
    project_memory = build_project_memory(project, root_causes, control_plan)
    role_summary = build_role_summary(project, audience, mode, improvement_actions, control_plan)

    return AssessmentResult(
        project_name=project.project_name,
        mode=mode,
        audience=audience,
        cleaned_problem_statement=cleaned_problem_statement,
        ctqs=ctqs,
        sipoc=sipoc,
        dmaic_structure=dmaic_structure,
        root_causes=root_causes,
        suggested_metrics=suggested_metrics,
        improvement_actions=improvement_actions,
        control_plan=control_plan,
        action_tracker=action_tracker,
        project_memory=project_memory,
        role_summary=role_summary,
    )
