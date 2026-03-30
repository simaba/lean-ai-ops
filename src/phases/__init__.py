from __future__ import annotations

from typing import Dict, List

from src.models import EvidenceItem, ProjectInput


def _supported(statement: str) -> EvidenceItem:
    return EvidenceItem(statement=statement, evidence_tag="directly_supported_by_input")


def _inferred(statement: str) -> EvidenceItem:
    return EvidenceItem(statement=statement, evidence_tag="inferred_hypothesis")


def _missing(statement: str) -> EvidenceItem:
    return EvidenceItem(statement=statement, evidence_tag="missing_evidence")


def clean_problem_statement(project: ProjectInput) -> str:
    symptoms = "; ".join(project.current_symptoms[:3])
    return (
        f"{project.project_name} has a structured improvement need: {project.problem_statement.strip()} "
        f"Current symptoms include {symptoms}."
    )


def build_ctqs(project: ProjectInput) -> List[EvidenceItem]:
    items = [_supported(f"Likely CTQ linked to current metric: {name}") for name in list(project.current_metrics.keys())[:3]]
    items.append(_inferred("Likely CTQ: cycle time or lead time"))
    items.append(_inferred("Likely CTQ: defect, rework, or reopening rate"))
    return items


def build_sipoc(project: ProjectInput) -> Dict[str, List[str]]:
    return {
        "suppliers": ["project team", "upstream stakeholders", "source system owners"],
        "inputs": [project.problem_statement, *project.current_symptoms[:2]],
        "process": ["define", "measure", "analyze", "improve", "control"],
        "outputs": ["improved process performance", "reduced waste", "clearer control plan"],
        "customers": ["project sponsor", "process owner", "downstream teams"],
    }


def build_dmaic_structure(project: ProjectInput) -> Dict[str, List[EvidenceItem]]:
    return {
        "define": [
            _supported(clean_problem_statement(project)),
            _supported(f"Stakeholder concerns: {', '.join(project.stakeholder_concerns[:3])}"),
        ],
        "measure": [
            _supported(f"Current metrics available: {', '.join(project.current_metrics.keys())}"),
            _missing("Historical trend and variance are not yet provided."),
        ],
        "analyze": [
            _inferred("Potential root cause cluster: weak handoffs or decision ownership."),
            _inferred("Potential waste cluster: waiting, rework, or unclear prioritization."),
        ],
        "improve": [
            _inferred("Pilot one high-impact process change before broad rollout."),
            _inferred("Standardize intake, triage, and acceptance criteria."),
        ],
        "control": [
            _inferred("Define control owner, review cadence, and threshold triggers."),
            _inferred("Track recurrence and unresolved risks after rollout."),
        ],
    }


def build_root_causes(project: ProjectInput) -> List[EvidenceItem]:
    items = [
        _inferred("Problem framing may be too vague, causing teams to solve symptoms instead of root issues."),
        _inferred("Role or handoff ambiguity may be driving delay and rework."),
        _inferred("Current measurement may not fully reflect the true CTQs."),
        _inferred("Stakeholder alignment may be insufficient at decision points."),
    ]
    if project.constraints:
        items.append(_supported(f"Constraint influencing the system: {project.constraints[0]}"))
    return items


def build_suggested_metrics(project: ProjectInput) -> List[EvidenceItem]:
    metrics = [_supported(f"Track current metric: {k} = {v}") for k, v in list(project.current_metrics.items())[:4]]
    metrics.extend([
        _inferred("Track cycle time by major workflow stage."),
        _inferred("Track defect or rework rate."),
        _inferred("Track escalation volume and recurrence."),
    ])
    return metrics


def build_improvement_actions(project: ProjectInput) -> List[EvidenceItem]:
    return [
        _inferred("Clarify ownership and decision rights at major handoff points."),
        _inferred("Standardize intake and prioritization criteria."),
        _inferred("Pilot a reduced-scope improvement before scale-up."),
        _inferred("Use a visible action tracker with owner and due date."),
    ]


def build_control_plan(project: ProjectInput, improvement_actions: List[EvidenceItem]) -> List[EvidenceItem]:
    return [
        _inferred("Assign a named owner to each critical metric."),
        _inferred("Review leading indicators weekly during initial stabilization."),
        _inferred("Trigger escalation when a core metric breaches threshold twice in one cycle."),
        _inferred("Document unresolved risks and review them at each checkpoint."),
    ]


def build_action_tracker(improvement_actions: List[EvidenceItem]) -> List[Dict[str, str]]:
    owners = ["PM", "Process owner", "Quality lead", "Analyst"]
    priorities = ["high", "high", "medium", "medium"]
    tracker = []
    for idx, item in enumerate(improvement_actions[:4]):
        tracker.append({
            "action": item.statement,
            "owner": owners[idx],
            "priority": priorities[idx],
            "status": "proposed",
        })
    return tracker


def build_project_memory(project: ProjectInput, root_causes: List[EvidenceItem], control_plan: List[EvidenceItem]) -> Dict[str, List[str]]:
    return {
        "baseline": [f"{k}: {v}" for k, v in project.current_metrics.items()],
        "root_cause_hypotheses": [item.statement for item in root_causes],
        "chosen_actions": ["Validate CTQs", "Pilot one improvement", "Define control cadence"],
        "control_metrics": [item.statement for item in control_plan],
        "unresolved_risks": ["Historical trend data is incomplete", "Stakeholder alignment may still be partial"],
    }


def build_role_summary(project: ProjectInput, audience: str, mode: str, improvement_actions: List[EvidenceItem], control_plan: List[EvidenceItem]) -> str:
    if audience == "executive":
        return (
            f"Executive summary: {project.project_name} is being structured in {mode} mode with focus on measurable CTQs, "
            f"targeted improvement actions, and control discipline to reduce recurrence and improve decision quality."
        )
    if audience == "manager":
        return (
            f"Manager summary: prioritize ownership clarity, pilot scope control, metric review cadence, and follow-through on the top improvement actions."
        )
    if audience == "quality_lead":
        return (
            f"Quality summary: strengthen CTQs, baseline quality signals, defect or rework tracking, and escalation thresholds."
        )
    if audience == "engineer":
        return (
            f"Engineer summary: focus on process handoffs, measurable bottlenecks, standard work, and observable thresholds."
        )
    return (
        f"PM summary: keep the problem statement tight, align stakeholders, validate CTQs, and drive one pilot improvement with a visible control plan."
    )
