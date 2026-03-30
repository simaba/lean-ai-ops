from __future__ import annotations

import re
from typing import Any

import pandas as pd

from src.models import AssessmentResult, ProjectInput


def _num(value: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else 0.0


def build_before_after_metrics(project: ProjectInput) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, raw in project.current_metrics.items():
        current = _num(raw)
        if "rate" in name or "%" in str(raw):
            improved = max(current * 0.8, 0)
        else:
            improved = max(current * 0.85, 0)
        rows.append({"metric": name, "before": current, "after": round(improved, 2)})
    return pd.DataFrame(rows)


def score_actions(result: AssessmentResult, project: ProjectInput) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    constraint_pressure = min(len(project.constraints), 3)
    stakeholder_pressure = min(len(project.stakeholder_concerns), 3)

    for idx, item in enumerate(result.improvement_actions):
        text = item.statement.lower()
        impact = 6
        effort = 4
        risk = 3

        if any(word in text for word in ["ownership", "decision rights", "prioritization", "standardize"]):
            impact += 2
        if any(word in text for word in ["pilot", "reduced-scope", "tracker"]):
            effort -= 1
        if any(word in text for word in ["standardize", "pilot"]):
            risk -= 1
        if constraint_pressure >= 2:
            effort += 1
        if stakeholder_pressure >= 2:
            impact += 1

        impact = min(max(impact, 1), 10)
        effort = min(max(effort, 1), 10)
        risk = min(max(risk, 1), 10)
        priority_score = round((impact * 1.6) - (effort * 0.8) - (risk * 0.6), 1)

        if impact >= 8 and effort <= 4:
            bucket = "Quick win"
        elif impact >= 8 and effort >= 6:
            bucket = "Strategic initiative"
        elif risk >= 5:
            bucket = "Watch closely"
        else:
            bucket = "Useful improvement"

        rows.append(
            {
                "action": item.statement,
                "impact": impact,
                "effort": effort,
                "risk": risk,
                "priority_score": priority_score,
                "bucket": bucket,
                "rank": idx + 1,
            }
        )

    df = pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def build_control_operating_model(result: AssessmentResult) -> pd.DataFrame:
    owners = ["PM", "Process Owner", "Quality Lead", "Operations Lead"]
    cadence = ["Weekly", "Weekly", "Bi-weekly", "Monthly"]
    trigger_logic = [
        "2 consecutive misses",
        "Lead time drifts >10%",
        "Rework rises above target",
        "Escalation recurrence increases",
    ]
    rows = []
    for idx, item in enumerate(result.control_plan):
        rows.append(
            {
                "control_item": item.statement,
                "owner": owners[idx % len(owners)],
                "cadence": cadence[idx % len(cadence)],
                "trigger": trigger_logic[idx % len(trigger_logic)],
                "status": "Draft",
            }
        )
    return pd.DataFrame(rows)
