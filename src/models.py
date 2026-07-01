from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ProjectInput:
    project_name: str
    problem_statement: str
    current_symptoms: List[str]
    current_metrics: Dict[str, str]
    constraints: List[str]
    stakeholder_concerns: List[str]


@dataclass
class EvidenceItem:
    statement: str
    evidence_tag: str


@dataclass
class PhaseOutput:
    title: str
    items: List[EvidenceItem] = field(default_factory=list)


@dataclass
class AssessmentResult:
    project_name: str
    mode: str
    audience: str
    cleaned_problem_statement: str
    ctqs: List[EvidenceItem]
    sipoc: Dict[str, List[str]]
    dmaic_structure: Dict[str, List[EvidenceItem]]
    root_causes: List[EvidenceItem]
    suggested_metrics: List[EvidenceItem]
    improvement_actions: List[EvidenceItem]
    control_plan: List[EvidenceItem]
    action_tracker: List[Dict[str, str]]
    project_memory: Dict[str, List[str]]
    role_summary: str
