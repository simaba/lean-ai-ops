from __future__ import annotations

import json

import altair as alt
import pandas as pd
import streamlit as st

from src.engine import run_assessment
from src.models import ProjectInput
from src.renderers import render_markdown_summary
from storage.projects import list_saved_projects, load_project_snapshot, save_project_snapshot
from ui.dashboard_insights import (
    executive_bullets,
    metric_bar_chart,
    pareto_chart,
    target_gap_chart,
)
from ui.forms import collect_project_input, load_sample_project
from ui.render import render_assessment_tabs, render_header_cards
from ui.scoring import build_before_after_metrics, build_control_operating_model, score_actions


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px;}
        .hero-card {padding: 1rem 1.2rem; border-radius: 18px; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white;}
        .section-card {padding: 0.8rem 1rem; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0;}
        .small-muted {color: #475569; font-size: 0.92rem;}
        h2, h3 {padding-top: 0.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _before_after_chart(df: pd.DataFrame) -> alt.Chart:
    melted = df.melt(id_vars=["metric"], value_vars=["before", "after"], var_name="state", value_name="value")
    return (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title="Metric"),
            y=alt.Y("value:Q", title="Value"),
            xOffset="state:N",
            color=alt.Color("state:N", title="Scenario"),
            tooltip=["metric", "state", "value"],
        )
        .properties(title="Before vs after improvement view", height=320)
    )


def _priority_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_circle(size=260)
        .encode(
            x=alt.X("effort:Q", title="Implementation effort"),
            y=alt.Y("impact:Q", title="Expected impact"),
            color=alt.Color("bucket:N", title="Priority bucket"),
            size=alt.Size("priority_score:Q", title="Priority score"),
            tooltip=["action", "impact", "effort", "risk", "priority_score", "bucket"],
        )
        .properties(title="Improvement prioritization matrix", height=340)
    )


st.set_page_config(page_title="Lean Six Sigma Copilot", layout="wide")
_inject_style()

st.title("Lean Six Sigma Copilot")
st.caption("Polished project-improvement intelligence for non-technical and technical audiences.")

with st.sidebar:
    st.header("Workflow Settings")
    mode = st.selectbox("Mode", ["dmaic", "kaizen", "root_cause", "process_waste", "control_plan"], index=0)
    audience = st.selectbox("Audience", ["engineer", "pm", "manager", "quality_lead", "executive"], index=1)
    source = st.radio("Project source", ["sample", "saved", "manual"], horizontal=False)

sample_data = load_sample_project()
saved_projects = list_saved_projects()
selected_defaults = None

if source == "sample":
    selected_defaults = sample_data
elif source == "saved":
    if saved_projects:
        selected_path = st.sidebar.selectbox("Saved project", saved_projects)
        selected_defaults = load_project_snapshot(selected_path)
    else:
        st.sidebar.info("No saved project snapshots found yet.")
        selected_defaults = sample_data

st.markdown('<div class="hero-card"><h3 style="margin:0;">Structure problems. Expose root causes. Prioritize action. Create control.</h3><div class="small-muted" style="color:#cbd5e1;">Use the guided intake below, then review the dashboard, prioritization, and control views.</div></div>', unsafe_allow_html=True)

st.markdown("## 1. Project intake")
project_data = collect_project_input(selected_defaults)

b1, b2 = st.columns(2)
with b1:
    generate = st.button("Generate assessment", type="primary", use_container_width=True)
with b2:
    save_snapshot = st.button("Save project snapshot", use_container_width=True)

if save_snapshot and project_data.get("project_name", "").strip():
    save_path = save_project_snapshot(project_data)
    st.success(f"Saved snapshot: {save_path}")

if generate:
    project = ProjectInput(**project_data)
    result = run_assessment(project, mode=mode, audience=audience)
    markdown_output = render_markdown_summary(result)

    baseline_df = build_before_after_metrics(project)
    action_df = score_actions(result, project)
    root_df = pd.DataFrame({"root_cause": [x.statement[:80] for x in result.root_causes], "weight": [35, 25, 20, 12, 8][: len(result.root_causes)]})
    control_df = build_control_operating_model(result)
    metric_df = pd.DataFrame({"metric": baseline_df["metric"], "current": baseline_df["before"], "target": baseline_df["after"]})

    st.markdown("## 2. Executive dashboard")
    render_header_cards(result)

    c1, c2 = st.columns([1.2, 0.8])
    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Leadership summary")
        for bullet in executive_bullets(result):
            st.write(f"- {bullet}")
        st.info(result.role_summary)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Decision snapshot")
        st.metric("Baseline metrics", len(result.project_memory.get("baseline", [])))
        st.metric("Likely root causes", len(result.root_causes))
        st.metric("Action candidates", len(result.improvement_actions))
        st.metric("Control items", len(result.control_plan))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("## 3. Baseline, target, and improvement view")
    g1, g2 = st.columns(2)
    with g1:
        st.altair_chart(metric_bar_chart(metric_df), use_container_width=True)
    with g2:
        st.altair_chart(target_gap_chart(metric_df), use_container_width=True)
    st.altair_chart(_before_after_chart(baseline_df), use_container_width=True)

    st.markdown("## 4. Root cause concentration and prioritization")
    g3, g4 = st.columns(2)
    with g3:
        if not root_df.empty:
            st.altair_chart(pareto_chart(root_df), use_container_width=True)
    with g4:
        st.altair_chart(_priority_chart(action_df), use_container_width=True)

    st.markdown("## 5. Priority actions")
    st.dataframe(action_df, use_container_width=True, hide_index=True)

    st.markdown("## 6. Control operating model")
    st.dataframe(control_df, use_container_width=True, hide_index=True)

    st.markdown("## 7. Detailed structured assessment")
    render_assessment_tabs(result)

    st.markdown("## 8. Review and refine")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("### Confirm CTQs")
        for item in result.ctqs:
            st.checkbox(item.statement, value=True, key=f"ctq_{item.statement}")
    with r2:
        st.markdown("### Review root causes")
        for item in result.root_causes:
            st.selectbox(item.statement, ["likely", "uncertain", "reject"], index=0, key=f"root_{item.statement}")
    with r3:
        st.markdown("### Refine actions")
        for idx, item in enumerate(result.improvement_actions):
            st.text_input(f"Action {idx + 1}", value=item.statement, key=f"action_{idx}")

    st.download_button(
        "Download markdown summary",
        markdown_output,
        file_name=f"{project_data['project_name'].replace(' ', '_').lower()}_summary.md",
        mime="text/markdown",
        use_container_width=True,
    )

    with st.expander("View raw project JSON"):
        st.code(json.dumps(project_data, indent=2), language="json")
else:
    st.info("Complete the intake form, then click Generate assessment.")
