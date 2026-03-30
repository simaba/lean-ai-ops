from __future__ import annotations

import re
from typing import Any

import altair as alt
import pandas as pd

from src.models import AssessmentResult, ProjectInput


def _parse_metric_value(raw: str) -> float:
    if raw is None:
        return 0.0
    text = str(raw).strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    return float(match.group())


def build_metric_dataframe(project: ProjectInput) -> pd.DataFrame:
    rows = []
    for name, value in project.current_metrics.items():
        numeric = _parse_metric_value(value)
        rows.append({"metric": name, "current": numeric, "target": numeric * 0.85 if numeric else 0.0})
    return pd.DataFrame(rows)


def build_action_dataframe(result: AssessmentResult) -> pd.DataFrame:
    presets = [
        (8, 3, "quick win"),
        (7, 4, "priority"),
        (9, 7, "structural"),
        (6, 2, "quick win"),
    ]
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(result.improvement_actions):
        impact, effort, group = presets[idx % len(presets)]
        rows.append(
            {
                "action": item.statement,
                "impact": impact,
                "effort": effort,
                "group": group,
            }
        )
    return pd.DataFrame(rows)


def build_root_cause_dataframe(result: AssessmentResult) -> pd.DataFrame:
    rows = []
    base_weights = [35, 25, 20, 12, 8]
    for idx, item in enumerate(result.root_causes):
        rows.append({"root_cause": item.statement[:80], "weight": base_weights[idx % len(base_weights)]})
    return pd.DataFrame(rows)


def metric_bar_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("metric:N", title="Metric"),
            y=alt.Y("current:Q", title="Current value"),
            tooltip=["metric", "current", "target"],
        )
        .properties(title="Current baseline metrics", height=280)
    )


def target_gap_chart(df: pd.DataFrame) -> alt.Chart:
    melted = df.melt(id_vars=["metric"], value_vars=["current", "target"], var_name="type", value_name="value")
    return (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title="Metric"),
            y=alt.Y("value:Q", title="Value"),
            xOffset="type:N",
            color=alt.Color("type:N", title="Series"),
            tooltip=["metric", "type", "value"],
        )
        .properties(title="Current vs target", height=280)
    )


def action_matrix_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_circle(size=260)
        .encode(
            x=alt.X("effort:Q", title="Implementation effort"),
            y=alt.Y("impact:Q", title="Expected impact"),
            color=alt.Color("group:N", title="Type"),
            tooltip=["action", "impact", "effort", "group"],
        )
        .properties(title="Impact vs effort matrix", height=320)
    )


def pareto_chart(df: pd.DataFrame) -> alt.Chart:
    ordered = df.sort_values("weight", ascending=False).copy()
    ordered["cumulative"] = ordered["weight"].cumsum() / ordered["weight"].sum() * 100
    bars = (
        alt.Chart(ordered)
        .mark_bar()
        .encode(
            x=alt.X("root_cause:N", sort=None, title="Potential root causes"),
            y=alt.Y("weight:Q", title="Relative weight"),
            tooltip=["root_cause", "weight", "cumulative"],
        )
    )
    line = (
        alt.Chart(ordered)
        .mark_line(point=True)
        .encode(
            x=alt.X("root_cause:N", sort=None),
            y=alt.Y("cumulative:Q", axis=alt.Axis(title="Cumulative %")),
        )
    )
    return alt.layer(bars, line).resolve_scale(y="independent").properties(title="Root cause concentration", height=320)


def control_plan_table(result: AssessmentResult) -> pd.DataFrame:
    owners = ["PM", "Process Owner", "Quality Lead", "Operations"]
    cadence = ["Weekly", "Weekly", "Bi-weekly", "Monthly"]
    triggers = [
        "2 consecutive misses",
        "Threshold breach >10%",
        "Escalation recurrence",
        "Missed review cycle",
    ]
    rows = []
    for idx, item in enumerate(result.control_plan):
        rows.append(
            {
                "control_item": item.statement,
                "owner": owners[idx % len(owners)],
                "cadence": cadence[idx % len(cadence)],
                "trigger": triggers[idx % len(triggers)],
            }
        )
    return pd.DataFrame(rows)


def executive_bullets(result: AssessmentResult) -> list[str]:
    bullets = [
        f"Primary problem: {result.cleaned_problem_statement}",
        f"Top likely root cause: {result.root_causes[0].statement if result.root_causes else 'Not available'}",
        f"Top improvement action: {result.improvement_actions[0].statement if result.improvement_actions else 'Not available'}",
        f"Key control focus: {result.control_plan[0].statement if result.control_plan else 'Not available'}",
        f"Main unresolved risk: {result.project_memory.get('unresolved_risks', ['Not available'])[0]}",
    ]
    return bullets
