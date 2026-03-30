from __future__ import annotations

from typing import Any, Dict

import json
from pathlib import Path
import streamlit as st


SAMPLE_PATH = Path("examples/sample_project.json")


def load_sample_project() -> Dict[str, Any] | None:
    if not SAMPLE_PATH.exists():
        return None
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def _join_lines(values: list[str] | None) -> str:
    return "\n".join(values or [])


def _metrics_to_text(metrics: dict[str, str] | None) -> str:
    if not metrics:
        return ""
    return "\n".join(f"{k}={v}" for k, v in metrics.items())


def parse_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_metrics(text: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in parse_lines(text):
        if "=" in line:
            key, value = line.split("=", 1)
            metrics[key.strip()] = value.strip()
        else:
            metrics[line] = ""
    return metrics


def collect_project_input(defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    defaults = defaults or {}
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project name", value=defaults.get("project_name", ""))
        problem_statement = st.text_area(
            "Problem statement",
            value=defaults.get("problem_statement", ""),
            height=120,
        )
        current_symptoms = st.text_area(
            "Current symptoms (one per line)",
            value=_join_lines(defaults.get("current_symptoms", [])),
            height=140,
        )
    with col2:
        current_metrics_text = st.text_area(
            "Current metrics (one per line as name=value)",
            value=_metrics_to_text(defaults.get("current_metrics", {})),
            height=140,
        )
        constraints = st.text_area(
            "Constraints (one per line)",
            value=_join_lines(defaults.get("constraints", [])),
            height=100,
        )
        stakeholder_concerns = st.text_area(
            "Stakeholder concerns (one per line)",
            value=_join_lines(defaults.get("stakeholder_concerns", [])),
            height=100,
        )

    return {
        "project_name": project_name,
        "problem_statement": problem_statement,
        "current_symptoms": parse_lines(current_symptoms),
        "current_metrics": parse_metrics(current_metrics_text),
        "constraints": parse_lines(constraints),
        "stakeholder_concerns": parse_lines(stakeholder_concerns),
    }
