from __future__ import annotations

import json

import streamlit as st

from src.engine import run_assessment
from src.models import ProjectInput
from src.renderers import render_markdown_summary
from storage.projects import list_saved_projects, load_project_snapshot, save_project_snapshot
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

st.subheader("1. Describe the project")
project_data = collect_project_input(selected_defaults)

left, right = st.columns(2)
with left:
    generate = st.button("Generate assessment", type="primary", use_container_width=True)
with right:
    save_snapshot = st.button("Save project snapshot", use_container_width=True)

if save_snapshot and project_data.get("project_name", "").strip():
    save_path = save_project_snapshot(project_data)
    st.success(f"Saved snapshot: {save_path}")

if generate:
    result = run_assessment(ProjectInput(**project_data), mode=mode, audience=audience)

    st.subheader("2. Review the key outputs")
    render_header_cards(result)
    render_assessment_tabs(result)

    st.subheader("3. Executive signals")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Root causes", len(result.root_causes))
    with m2:
        st.metric("Action items", len(result.improvement_actions))
    with m3:
        st.metric("Control items", len(result.control_plan))
    with m4:
        st.metric("Baseline metrics", len(result.project_memory.get("baseline", [])))

    st.subheader("4. Confirm or refine")
    with st.expander("Review CTQs", expanded=False):
        for item in result.ctqs:
            st.checkbox(item.statement, value=True, key=f"ctq_{item.statement}")

    with st.expander("Review root causes", expanded=False):
        for item in result.root_causes:
            st.selectbox(item.statement, ["likely", "uncertain", "reject"], index=0, key=f"root_{item.statement}")

    with st.expander("Review improvement actions", expanded=False):
        for idx, item in enumerate(result.improvement_actions):
            st.text_input(f"Action {idx + 1}", value=item.statement, key=f"action_{idx}")

    markdown_output = render_markdown_summary(result)
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
    st.info("Complete the form and click Generate assessment.")
