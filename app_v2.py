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
st.caption("Turn messy project problems into structured improvement plans.")

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
else:
    selected_defaults = None

st.subheader("Step 1. Describe the project")
project_data = collect_project_input(selected_defaults)

col1, col2 = st.columns(2)
with col1:
    generate = st.button("Generate assessment", type="primary", use_container_width=True)
with col2:
    save_snapshot = st.button("Save project snapshot", use_container_width=True)

if save_snapshot and project_data.get("project_name", "").strip():
    save_path = save_project_snapshot(project_data)
    st.success(f"Saved snapshot: {save_path}")

if generate:
    result = run_assessment(ProjectInput(**project_data), mode=mode, audience=audience)

    st.subheader("Step 2. Review key outputs")
    render_header_cards(result)
    render_assessment_tabs(result)

    st.subheader("Step 3. Confirm or refine")
    with st.expander("Review CTQs"):
        for item in result.ctqs:
            st.checkbox(item.statement, value=True, key=f"ctq_{item.statement}")

    with st.expander("Review root causes"):
        for item in result.root_causes:
            st.selectbox(
                item.statement,
                ["likely", "uncertain", "reject"],
                index=0,
                key=f"root_{item.statement}",
            )

    with st.expander("Review improvement actions"):
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
    st.info("Complete the form, then click Generate assessment.")
