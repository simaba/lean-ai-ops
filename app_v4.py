from __future__ import annotations

import json

import streamlit as st

from src.engine import run_assessment
from src.models import ProjectInput
from src.renderers import render_markdown_summary
from storage.projects import list_saved_projects, load_project_snapshot, save_project_snapshot
from ui.dashboard_insights import (
    action_matrix_chart,
    build_action_dataframe,
    build_metric_dataframe,
    build_root_cause_dataframe,
    control_plan_table,
    executive_bullets,
    metric_bar_chart,
    pareto_chart,
    target_gap_chart,
)
from ui.forms import collect_project_input, load_sample_project
from ui.render import render_assessment_tabs, render_header_cards

st.set_page_config(page_title="Lean Six Sigma Copilot", layout="wide")

st.title("Lean Six Sigma Copilot")
st.caption("Structured improvement intelligence for real projects.")

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

st.markdown("## 1. Project intake")
project_data = collect_project_input(selected_defaults)

c1, c2 = st.columns(2)
with c1:
    generate = st.button("Generate assessment", type="primary", use_container_width=True)
with c2:
    save_snapshot = st.button("Save project snapshot", use_container_width=True)

if save_snapshot and project_data.get("project_name", "").strip():
    save_path = save_project_snapshot(project_data)
    st.success(f"Saved snapshot: {save_path}")

if generate:
    project = ProjectInput(**project_data)
    result = run_assessment(project, mode=mode, audience=audience)
    markdown_output = render_markdown_summary(result)

    metric_df = build_metric_dataframe(project)
    action_df = build_action_dataframe(result)
    root_df = build_root_cause_dataframe(result)
    control_df = control_plan_table(result)

    st.markdown("## 2. Executive dashboard")
    render_header_cards(result)

    ex1, ex2 = st.columns([1.15, 0.85])
    with ex1:
        st.subheader("Leadership summary")
        for bullet in executive_bullets(result):
            st.write(f"- {bullet}")
        st.subheader("Role-aware summary")
        st.info(result.role_summary)
    with ex2:
        st.subheader("Key signals")
        st.metric("Baseline metrics", len(result.project_memory.get("baseline", [])))
        st.metric("Likely root causes", len(result.root_causes))
        st.metric("Improvement actions", len(result.improvement_actions))
        st.metric("Control items", len(result.control_plan))

    st.markdown("## 3. Baseline and target insight")
    left, right = st.columns(2)
    with left:
        st.altair_chart(metric_bar_chart(metric_df), use_container_width=True)
    with right:
        st.altair_chart(target_gap_chart(metric_df), use_container_width=True)

    st.markdown("## 4. Root cause and prioritization")
    left, right = st.columns(2)
    with left:
        st.altair_chart(pareto_chart(root_df), use_container_width=True)
    with right:
        st.altair_chart(action_matrix_chart(action_df), use_container_width=True)

    st.markdown("## 5. Structured assessment")
    render_assessment_tabs(result)

    st.markdown("## 6. Control plan operating view")
    st.dataframe(control_df, use_container_width=True, hide_index=True)

    st.markdown("## 7. Review and refine")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.markdown("### Confirm CTQs")
        for item in result.ctqs:
            st.checkbox(item.statement, value=True, key=f"ctq_{item.statement}")
    with rc2:
        st.markdown("### Review root causes")
        for item in result.root_causes:
            st.selectbox(item.statement, ["likely", "uncertain", "reject"], index=0, key=f"root_{item.statement}")
    with rc3:
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
