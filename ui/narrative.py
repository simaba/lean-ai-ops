from __future__ import annotations

import pandas as pd

from src.models import AssessmentResult


def build_executive_insights(result: AssessmentResult, action_df: pd.DataFrame, control_df: pd.DataFrame) -> list[str]:
    insights: list[str] = []
    if not action_df.empty:
        top = action_df.iloc[0]
        insights.append(
            f"Highest-priority action is '{top['action']}' because it combines strong expected impact with manageable delivery burden."
        )
    if result.root_causes:
        insights.append(
            f"The analysis points most strongly to this underlying issue: {result.root_causes[0].statement}"
        )
    if not control_df.empty:
        insights.append(
            f"The operating model should start with {control_df.iloc[0]['cadence'].lower()} reviews owned by {control_df.iloc[0]['owner']}."
        )
    unresolved = result.project_memory.get("unresolved_risks", [])
    if unresolved:
        insights.append(f"The main unresolved risk is: {unresolved[0]}")
    insights.append(
        "The biggest near-term value will come from validating the CTQs, narrowing scope, and piloting one improvement before broader rollout."
    )
    return insights


def build_operational_insights(result: AssessmentResult, action_df: pd.DataFrame) -> list[str]:
    insights: list[str] = []
    quick_wins = action_df[action_df["bucket"] == "Quick win"] if not action_df.empty else pd.DataFrame()
    strategic = action_df[action_df["bucket"] == "Strategic initiative"] if not action_df.empty else pd.DataFrame()

    if not quick_wins.empty:
        insights.append(f"There are {len(quick_wins)} quick wins that can likely be started without major structural change.")
    if not strategic.empty:
        insights.append(f"There are {len(strategic)} strategic initiatives that need tighter sponsorship and follow-through.")
    insights.append("Use the action tracker as a live operating tool, not just a static deliverable.")
    insights.append("Treat inferred hypotheses as items to validate, not as proven facts.")
    return insights


def build_status_narrative(result: AssessmentResult, action_df: pd.DataFrame) -> str:
    if action_df.empty:
        return "The project has been structured, but action prioritization is not yet available."
    top_bucket = action_df.iloc[0]["bucket"]
    return (
        f"The project is now in a structured improvement state. The problem has been clarified, baseline indicators are visible, "
        f"and the current recommendation is to focus first on {top_bucket.lower()} items while validating root-cause assumptions and building control discipline."
    )
