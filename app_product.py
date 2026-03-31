from __future__ import annotations

import json

import altair as alt
import pandas as pd
import streamlit as st

from exports.briefing_html import build_briefing_html
from exports.leadership_deck import build_leadership_deck_markdown
from exports.pdf_briefing import build_pdf_briefing
from exports.review_package import export_review_package
from src.engine_canonical import run_assessment
from src.models import ProjectInput
from src.renderers import render_markdown_summary
from storage.projects import list_saved_projects, load_project_snapshot, save_project_snapshot
from storage.reviews import list_saved_reviews, load_review_state, save_review_state
from ui.dashboard_insights import executive_bullets, metric_bar_chart, pareto_chart, target_gap_chart
from ui.forms import collect_project_input, load_sample_project
from ui.narrative import build_executive_insights, build_operational_insights, build_status_narrative
from ui.render import render_assessment_tabs, render_header_cards
from ui.scoring import build_before_after_metrics, build_control_operating_model, score_actions
from ui.wizard import intake_validation, review_payload


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1240px;}
        .hero-card {padding: 1.1rem 1.3rem; border-radius: 20px; background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%); color: white; margin-bottom: 1rem;}
        .soft-card {padding: 0.85rem 1rem; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0;}
        .small-muted {color: #475569; font-size: 0.92rem;}
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
        .properties(title="Before vs after improvement view", height=300)
    )


def _priority_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_circle(size=280)
        .encode(
            x=alt.X("effort:Q", title="Implementation effort"),
            y=alt.Y("impact:Q", title="Expected impact"),
            color=alt.Color("bucket:N", title="Priority bucket"),
            size=alt.Size("priority_score:Q", title="Priority score"),
            tooltip=["action", "impact", "effort", "risk", "priority_score", "bucket"],
        )
        .properties(title="Improvement prioritization matrix", height=320)
    )


def _initialize_state() -> None:
    defaults = {
        "step": 1,
        "project_data": None,
        "review_state": None,
        "result": None,
        "action_df": None,
        "control_df": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


st.set_page_config(page_title="Lean Six Sigma Copilot", layout="wide")
_inject_style()
_initialize_state()

st.title("Lean Six Sigma Copilot")
st.caption("Productized flagship workflow for structured improvement analysis.")

with st.sidebar:
    st.header("Workflow Settings")
    mode = st.selectbox("Mode", ["dmaic", "kaizen", "root_cause", "process_waste", "control_plan"], index=0)
    audience = st.selectbox("Audience", ["engineer", "pm", "manager", "quality_lead", "executive"], index=1)
    source = st.radio("Project source", ["sample", "saved project", "saved review", "manual"], horizontal=False)

sample_data = load_sample_project()
saved_projects = list_saved_projects()
saved_reviews = list_saved_reviews()
selected_defaults = None

if source == "sample":
    selected_defaults = sample_data
elif source == "saved project":
    if saved_projects:
        selected_path = st.sidebar.selectbox("Saved project", saved_projects)
        selected_defaults = load_project_snapshot(selected_path)
    else:
        st.sidebar.info("No saved project snapshots found yet.")
        selected_defaults = sample_data
elif source == "saved review":
    if saved_reviews:
        review_path = st.sidebar.selectbox("Saved review", saved_reviews)
        selected_defaults = load_review_state(review_path).get("project", sample_data)
    else:
        st.sidebar.info("No saved review states found yet.")
        selected_defaults = sample_data

st.markdown('<div class="hero-card"><h3 style="margin:0;">Guide the assessment. Review the evidence. Export leadership-ready outputs.</h3><div class="small-muted" style="color:#dbeafe;">This product path uses the canonical backend and a guided five-step workflow.</div></div>', unsafe_allow_html=True)

progress_labels = ["1 Intake", "2 Generate", "3 Dashboard", "4 Review", "5 Export"]
st.progress((st.session_state.step - 1) / 4)
st.write("Current step:", progress_labels[st.session_state.step - 1])

if st.session_state.step == 1:
    st.markdown("## Step 1. Intake")
    project_data = collect_project_input(selected_defaults)
    issues = intake_validation(project_data)
    if issues:
        for issue in issues:
            st.warning(issue)
    left, right = st.columns(2)
    with left:
        if st.button("Save intake snapshot", use_container_width=True):
            save_path = save_project_snapshot(project_data)
            st.success(f"Saved intake snapshot: {save_path}")
    with right:
        if st.button("Continue to generation", type="primary", use_container_width=True, disabled=bool(issues)):
            st.session_state.project_data = project_data
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.markdown("## Step 2. Generate structured assessment")
    project = ProjectInput(**st.session_state.project_data)
    result = run_assessment(project, mode=mode, audience=audience)
    action_df = score_actions(result, project)
    control_df = build_control_operating_model(result)
    st.session_state.result = result
    st.session_state.action_df = action_df
    st.session_state.control_df = control_df
    st.success("Assessment generated successfully.")
    if st.button("Continue to dashboard", type="primary"):
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    result = st.session_state.result
    project = ProjectInput(**st.session_state.project_data)
    action_df = st.session_state.action_df
    control_df = st.session_state.control_df
    baseline_df = build_before_after_metrics(project)
    root_df = pd.DataFrame({"root_cause": [x.statement[:80] for x in result.root_causes], "weight": [35, 25, 20, 12, 8][: len(result.root_causes)]})
    metric_df = pd.DataFrame({"metric": baseline_df["metric"], "current": baseline_df["before"], "target": baseline_df["after"]})

    st.markdown("## Step 3. Dashboard")
    render_header_cards(result)

    c1, c2 = st.columns([1.2, 0.8])
    with c1:
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("Leadership summary")
        for bullet in executive_bullets(result):
            st.write(f"- {bullet}")
        for insight in build_executive_insights(result, action_df, control_df):
            st.write(f"• {insight}")
        st.info(result.role_summary)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("Decision snapshot")
        st.metric("Baseline metrics", len(result.project_memory.get("baseline", [])))
        st.metric("Likely root causes", len(result.root_causes))
        st.metric("Action candidates", len(result.improvement_actions))
        st.metric("Control items", len(result.control_plan))
        st.markdown('</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    with g1:
        st.altair_chart(metric_bar_chart(metric_df), use_container_width=True)
    with g2:
        st.altair_chart(target_gap_chart(metric_df), use_container_width=True)
    st.altair_chart(_before_after_chart(baseline_df), use_container_width=True)

    g3, g4 = st.columns(2)
    with g3:
        if not root_df.empty:
            st.altair_chart(pareto_chart(root_df), use_container_width=True)
    with g4:
        st.altair_chart(_priority_chart(action_df), use_container_width=True)

    if st.button("Continue to review", type="primary"):
        st.session_state.step = 4
        st.rerun()

elif st.session_state.step == 4:
    result = st.session_state.result
    action_df = st.session_state.action_df
    control_df = st.session_state.control_df
    st.markdown("## Step 4. Review and refine")

    confirmed_ctqs = []
    root_labels: dict[str, str] = {}

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("### Confirm CTQs")
        for item in result.ctqs:
            checked = st.checkbox(item.statement, value=True, key=f"ctq_{item.statement}")
            if checked:
                confirmed_ctqs.append(item.statement)
    with r2:
        st.markdown("### Review root causes")
        for item in result.root_causes:
            label = st.selectbox(item.statement, ["likely", "uncertain", "reject"], index=0, key=f"root_{item.statement}")
            root_labels[item.statement] = label

    st.markdown("### Edit action portfolio")
    edited_action_df = st.data_editor(action_df, use_container_width=True, hide_index=True, num_rows="fixed")
    st.markdown("### Edit control operating model")
    edited_control_df = st.data_editor(control_df, use_container_width=True, hide_index=True, num_rows="fixed")

    refined_actions = edited_action_df["action"].tolist() if "action" in edited_action_df.columns else []
    payload = review_payload(confirmed_ctqs, root_labels, refined_actions)
    st.session_state.review_state = payload

    if st.button("Save reviewed state", use_container_width=True):
        saved = save_review_state(st.session_state.project_data["project_name"], {"project": st.session_state.project_data, "review": payload})
        st.success(f"Saved reviewed state: {saved}")

    if st.button("Continue to export", type="primary", use_container_width=True):
        st.session_state.action_df = edited_action_df
        st.session_state.control_df = edited_control_df
        st.session_state.step = 5
        st.rerun()

elif st.session_state.step == 5:
    result = st.session_state.result
    edited_action_df = st.session_state.action_df
    edited_control_df = st.session_state.control_df
    status_narrative = build_status_narrative(result, edited_action_df)
    leadership_summary = build_executive_insights(result, edited_action_df, edited_control_df)
    markdown_output = render_markdown_summary(result)
    top_actions = edited_action_df["action"].head(3).tolist() if "action" in edited_action_df.columns else []
    top_risks = result.project_memory.get("unresolved_risks", [])
    html_briefing = build_briefing_html(st.session_state.project_data["project_name"], leadership_summary, status_narrative, top_actions, top_risks)
    pdf_briefing = build_pdf_briefing(st.session_state.project_data["project_name"], status_narrative, leadership_summary, top_actions, top_risks)
    leadership_deck = build_leadership_deck_markdown(st.session_state.project_data["project_name"], status_narrative, leadership_summary, top_actions, top_risks)

    st.markdown("## Step 5. Export and share")
    st.success(status_narrative)
    for insight in build_operational_insights(result, edited_action_df):
        st.write(f"- {insight}")

    export_payload = {
        "project": st.session_state.project_data,
        "review": st.session_state.review_state,
        "status_narrative": status_narrative,
        "executive_insights": leadership_summary,
    }

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button("Markdown summary", markdown_output, file_name=f"{st.session_state.project_data['project_name'].replace(' ', '_').lower()}_summary.md", mime="text/markdown", use_container_width=True)
    with c2:
        st.download_button("HTML briefing", html_briefing, file_name=f"{st.session_state.project_data['project_name'].replace(' ', '_').lower()}_briefing.html", mime="text/html", use_container_width=True)
    with c3:
        st.download_button("PDF briefing", pdf_briefing, file_name=f"{st.session_state.project_data['project_name'].replace(' ', '_').lower()}_briefing.pdf", mime="application/pdf", use_container_width=True)
    with c4:
        st.download_button("Leadership deck", leadership_deck, file_name=f"{st.session_state.project_data['project_name'].replace(' ', '_').lower()}_deck.md", mime="text/markdown", use_container_width=True)

    if st.button("Export reviewed package", use_container_width=True):
        exported = export_review_package(st.session_state.project_data["project_name"], export_payload, edited_action_df, edited_control_df)
        st.success(f"Exported review package: {exported}")

    with st.expander("Detailed structured assessment"):
        render_assessment_tabs(result)

    if st.button("Start a new assessment"):
        for key in ["step", "project_data", "review_state", "result", "action_df", "control_df"]:
            st.session_state[key] = None if key != "step" else 1
        st.rerun()
