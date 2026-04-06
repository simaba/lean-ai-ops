from __future__ import annotations

import os

import streamlit as st

from src.engine import run_assessment
from src.exporters import render_docx_summary, render_pdf_summary, render_xlsx_summary
from src.models import ProjectInput
from src.renderers import render_html_summary, render_markdown_summary
from storage.projects import list_saved_projects, load_project_snapshot, save_project_snapshot
from ui.dashboard_insights import (
    action_matrix_chart,
    build_action_dataframe,
    build_dmaic_coverage_dataframe,
    build_evidence_dataframe,
    build_metric_dataframe,
    build_priority_dataframe,
    build_root_cause_dataframe,
    control_plan_table,
    dmaic_phase_chart,
    evidence_distribution_chart,
    executive_bullets,
    metric_bar_chart,
    pareto_chart,
    priority_distribution_chart,
    target_gap_chart,
)
from ui.forms import collect_project_input, load_sample_project
from ui.analytics_workbench import render_analytics_workbench
from ui.coaching import (
    render_question_coach,
    render_output_state_label,
    render_interpretation_card,
    render_next_step_actions,
)
from ui.tool_recommender import render_tool_recommender
from ui.tollgate import render_tollgate
from examples.project_library import (
    PROJECT_LIBRARY, get_all_domains, get_all_problem_types,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LSS Copilot",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>

/* ── Fonts & base ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.stApp {
  background: #F1F4FB !important;
}
.main .block-container {
  padding-top: 2.2rem !important;
  padding-bottom: 3rem !important;
  max-width: 1200px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1E1B4B 0%, #16133A 100%) !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] > div:first-child {
  background: transparent !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span,
[data-testid="stSidebar"] .stMarkdown li,
[data-testid="stSidebar"] .stMarkdown h2 {
  color: #CBD5E1 !important;
}
[data-testid="stSidebar"] [data-testid="stCaption"] p {
  color: #64748B !important;
}
[data-testid="stSidebar"] hr {
  border-color: rgba(255,255,255,0.10) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
  color: #CBD5E1 !important;
  background: rgba(255,255,255,0.07) !important;
  border-color: rgba(255,255,255,0.12) !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.10) !important;
  color: #E2E8F0 !important;
  border-color: rgba(255,255,255,0.15) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,0.18) !important;
}
[data-testid="stSidebarCollapseButton"] svg { color: #94A3B8 !important; }

/* ── Primary buttons ───────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #4361EE 0%, #3A0CA3 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 0.95em !important;
  padding: 0.58rem 1.5rem !important;
  box-shadow: 0 4px 16px rgba(67,97,238,0.32) !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease !important;
  letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(67,97,238,0.42) !important;
}
.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
  background: #FFFFFF !important;
  color: #4361EE !important;
  border: 2px solid #4361EE !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
.stButton > button[kind="secondary"]:hover {
  background: #EEF2FF !important;
}

/* ── Form inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
  border: 2px solid #E2E8F0 !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
  font-size: 0.93em !important;
  color: #1E293B !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #4361EE !important;
  box-shadow: 0 0 0 3px rgba(67,97,238,0.12) !important;
  outline: none !important;
}
[data-testid="stWidgetLabel"] p { font-weight: 600 !important; color: #374151 !important; }

/* ── Radio buttons → card-style ────────────────────────────────────────────── */
[data-testid="stRadio"] > div {
  gap: 10px !important;
  flex-wrap: wrap !important;
}
[data-testid="stRadio"] label {
  background: #FFFFFF !important;
  border: 2px solid #E2E8F0 !important;
  border-radius: 12px !important;
  padding: 12px 18px !important;
  cursor: pointer !important;
  transition: border-color 0.18s, background 0.18s !important;
  font-weight: 600 !important;
  flex: 1 1 auto !important;
}
[data-testid="stRadio"] label:hover {
  border-color: #4361EE !important;
  background: #F8FAFF !important;
}
[data-testid="stRadio"] label:has(input:checked) {
  border-color: #4361EE !important;
  background: #EEF2FF !important;
  color: #4361EE !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #FFFFFF !important;
  border-radius: 12px 12px 0 0 !important;
  border-bottom: 2px solid #E2E8F0 !important;
  padding: 8px 12px 0 12px !important;
  gap: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 8px 8px 0 0 !important;
  padding: 10px 20px !important;
  font-weight: 600 !important;
  font-size: 0.88em !important;
  letter-spacing: 0.015em !important;
  color: #64748B !important;
  background: transparent !important;
  border: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: #4361EE !important;
  background: #F0F4FF !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #4361EE !important;
  background: #EEF2FF !important;
  border-bottom: 3px solid #4361EE !important;
}
[data-testid="stTabsContent"] {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  padding: 28px 24px !important;
}

/* ── Metrics ───────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: #FFFFFF !important;
  border-radius: 12px !important;
  padding: 18px 20px !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
}
[data-testid="stMetricValue"] {
  font-size: 2.4em !important;
  font-weight: 800 !important;
  color: #1E1B4B !important;
}
[data-testid="stMetricLabel"] {
  font-size: 0.78em !important;
  font-weight: 700 !important;
  color: #64748B !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

/* ── Expanders ─────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
  background: #FFFFFF !important;
  overflow: hidden !important;
  margin-bottom: 10px !important;
}
[data-testid="stExpander"] summary {
  background: #FFFFFF !important;
  font-weight: 700 !important;
  color: #1E1B4B !important;
  padding: 12px 16px !important;
}
[data-testid="stExpander"] summary:hover { background: #F8FAFF !important; }

/* ── Dataframe ─────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }

/* ── Alerts ────────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  border: none !important;
}

/* ── Download buttons ──────────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
  border-radius: 10px !important;
  font-weight: 700 !important;
  padding: 0.6rem 1.2rem !important;
}

/* ── Evidence badges ───────────────────────────────────────────────────────── */
.ev-supported {
  display:inline-block; background:#DCFCE7; color:#166534;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}
.ev-inferred {
  display:inline-block; background:#FEF9C3; color:#854D0E;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}
.ev-missing {
  display:inline-block; background:#FEE2E2; color:#991B1B;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}

/* ── Custom cards ──────────────────────────────────────────────────────────── */
.lss-card {
  background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px;
  padding:22px 24px; margin-bottom:16px;
  box-shadow:0 2px 12px rgba(0,0,0,0.05);
}
.lss-card-accent {
  background:#FFFFFF; border-left:4px solid #4361EE;
  border-radius:0 12px 12px 0; padding:18px 22px; margin-bottom:12px;
  box-shadow:0 2px 8px rgba(67,97,238,0.08);
}
.hero-banner {
  background: linear-gradient(135deg, #4361EE 0%, #3A0CA3 100%);
  color: white; border-radius: 16px; padding: 28px 32px; margin-bottom: 28px;
}
.hero-banner h2 { color:white !important; margin:0 0 8px 0; font-size:1.5em; }
.hero-banner p  { color:rgba(255,255,255,0.85) !important; margin:0; font-size:0.95em; }
.phase-define  { border-left:4px solid #3B82F6 !important; }
.phase-measure { border-left:4px solid #8B5CF6 !important; }
.phase-analyze { border-left:4px solid #F59E0B !important; }
.phase-improve { border-left:4px solid #10B981 !important; }
.phase-control { border-left:4px solid #06B6D4 !important; }
.export-card {
  background:#FFFFFF; border:2px solid #E2E8F0; border-radius:14px;
  padding:24px; text-align:center; transition:border-color 0.2s, box-shadow 0.2s;
  height:100%;
}
.export-card:hover { border-color:#4361EE; box-shadow:0 4px 20px rgba(67,97,238,0.12); }
.export-icon { font-size:2.5em; margin-bottom:10px; }
.export-title { font-size:1.05em; font-weight:700; color:#1E1B4B; margin-bottom:6px; }
.export-desc  { font-size:0.84em; color:#64748B; margin-bottom:16px; line-height:1.5; }
.sipoc-table { width:100%; border-collapse:collapse; margin-top:8px; font-size:0.88em; }
.sipoc-table th {
  background:#EEF2FF; color:#4361EE; font-weight:700; padding:10px 12px;
  text-align:left; border:1px solid #C7D2FE; font-size:0.82em; text-transform:uppercase; letter-spacing:0.06em;
}
.sipoc-table td { padding:8px 12px; border:1px solid #E2E8F0; vertical-align:top; color:#374151; }
.sipoc-table tr:nth-child(even) td { background:#F8FAFF; }
.step-badge {
  display:inline-block; background:rgba(67,97,238,0.12); color:#4361EE;
  border-radius:20px; padding:3px 14px; font-size:0.78em; font-weight:700;
  letter-spacing:0.05em; margin-bottom:6px;
}
.signal-item {
  background:#F8FAFF; border-left:3px solid #4361EE; border-radius:0 8px 8px 0;
  padding:10px 14px; margin-bottom:8px; font-size:0.92em; color:#1E293B;
}
.ev-legend {
  display:flex; gap:14px; align-items:center; flex-wrap:wrap;
  background:#F8FAFF; border-radius:8px; padding:10px 14px;
  margin-bottom:16px; font-size:0.82em;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

for _k, _v in {
    "step": 1, "project_data": None, "mode": "dmaic",
    "audience": "pm", "result": None, "app_mode": "wizard"
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# Evidence helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ev_class(tag: str) -> str:
    if "supported" in tag: return "ev-supported"
    if "missing"   in tag: return "ev-missing"
    return "ev-inferred"

def _ev_label(tag: str) -> str:
    if "supported" in tag: return "✓ supported"
    if "missing"   in tag: return "! missing"
    return "~ inferred"

def _item_html(item, indent: int = 0) -> str:
    cls   = _ev_class(item.evidence_tag)
    label = _ev_label(item.evidence_tag)
    pad   = f"padding-left:{indent}px;" if indent else ""
    return (
        f'<div style="display:flex;align-items:flex-start;gap:10px;'
        f'margin:7px 0;{pad}">'
        f'<span style="color:#94A3B8;font-size:1em;margin-top:2px">•</span>'
        f'<span style="color:#1E293B;font-size:0.93em;line-height:1.55;flex:1">'
        f'{item.statement}</span>'
        f'<span class="{cls}" style="flex-shrink:0">{label}</span>'
        f'</div>'
    )

def _render_items(items) -> None:
    html = "".join(_item_html(i) for i in items)
    st.markdown(html, unsafe_allow_html=True)

def _evidence_legend() -> None:
    st.markdown(
        '<div class="ev-legend">'
        '<strong>Evidence key:</strong>'
        '&nbsp;<span class="ev-supported">✓ supported</span> — directly in your input'
        '&nbsp;&nbsp;<span class="ev-inferred">~ inferred</span> — logical hypothesis'
        '&nbsp;&nbsp;<span class="ev-missing">! missing</span> — data needed'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Navigation
# ─────────────────────────────────────────────────────────────────────────────

def _go(step: int) -> None:
    st.session_state.step = step
    st.rerun()

def _back(to: int, label: str = "← Back") -> None:
    if st.button(label, key=f"back_to_{to}"):
        _go(to)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

_STEP_LABELS = ["Intake", "Configure", "Generate", "Dashboard", "Export"]

def _sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<h2 style="color:#FFFFFF;font-size:1.25em;font-weight:800;'
            'margin-bottom:2px;letter-spacing:-0.02em">⚙ LSS Copilot</h2>'
            '<p style="color:#64748B;font-size:0.8em;margin-top:0">Lean Six Sigma AI assistant</p>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── App mode toggle ──
        app_mode = st.session_state.get("app_mode", "wizard")
        st.markdown(
            '<p style="color:#64748B;font-size:0.78em;font-weight:600;'
            'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">Mode</p>',
            unsafe_allow_html=True,
        )
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            if st.button("📋 Wizard", key="sb_wizard",
                         use_container_width=True,
                         type="primary" if app_mode == "wizard" else "secondary"):
                st.session_state["app_mode"] = "wizard"
                st.rerun()
        with m_col2:
            if st.button("⚡ Analytics", key="sb_wb",
                         use_container_width=True,
                         type="primary" if app_mode == "workbench" else "secondary"):
                st.session_state["app_mode"] = "workbench"
                st.rerun()

        m_col3, m_col4 = st.columns(2)
        with m_col3:
            if st.button("🧭 Recommender", key="sb_rec",
                         use_container_width=True,
                         type="primary" if app_mode == "recommender" else "secondary"):
                st.session_state["app_mode"] = "recommender"
                st.rerun()
        with m_col4:
            if st.button("🚦 Tollgate", key="sb_tg",
                         use_container_width=True,
                         type="primary" if app_mode == "tollgate" else "secondary"):
                st.session_state["app_mode"] = "tollgate"
                st.rerun()

        st.divider()

        # ── Wizard step tracker (only shown in wizard mode) ──
        current = st.session_state.step
        if app_mode == "wizard":  # noqa: E712
            for i, label in enumerate(_STEP_LABELS, 1):
                if i < current:
                    icon, col = "✓", "#475569"
                    weight = "500"
                elif i == current:
                    icon, col = "→", "#818CF8"
                    weight = "700"
                else:
                    icon, col = "○", "#334155"
                    weight = "400"
                st.markdown(
                    f'<div style="color:{col};font-weight:{weight};font-size:0.88em;'
                    f'padding:5px 0;letter-spacing:0.01em">'
                    f'{icon}&nbsp;&nbsp;{i}. {label}</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        has_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
        if has_key:
            st.markdown(
                '<div style="background:rgba(6,214,160,0.15);border:1px solid rgba(6,214,160,0.3);'
                'border-radius:8px;padding:8px 12px;color:#6EE7B7;font-size:0.82em;font-weight:600">'
                '🤖 Claude AI connected</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.25);'
                'border-radius:8px;padding:8px 12px;color:#FCD34D;font-size:0.82em;font-weight:600">'
                '⚠ No API key — structured mode<br>'
                '<span style="font-weight:400;color:#94A3B8">Set ANTHROPIC_API_KEY for<br>AI-powered analysis</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        saved = list_saved_projects()
        if saved:
            st.divider()
            st.markdown('<p style="color:#64748B;font-size:0.78em;font-weight:600;'
                        'text-transform:uppercase;letter-spacing:0.07em">Saved projects</p>',
                        unsafe_allow_html=True)
            names = [p.replace("saved_projects\\","").replace("saved_projects/","").replace(".json","") for p in saved]
            sel = st.selectbox("Load", ["— new project —"] + names, label_visibility="collapsed")
            if sel != "— new project —" and st.button("Load project", use_container_width=True):
                idx = names.index(sel)
                data = load_project_snapshot(saved[idx])
                st.session_state.project_data = {
                    k: v for k, v in data.items()
                    if k in ("project_name","problem_statement","current_symptoms",
                             "current_metrics","constraints","stakeholder_concerns")
                }
                if "mode"     in data: st.session_state.mode     = data["mode"]
                if "audience" in data: st.session_state.audience = data["audience"]
                st.session_state.step = 1
                st.rerun()

_sidebar()


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Intake
# ─────────────────────────────────────────────────────────────────────────────

def _render_example_library() -> None:
    """Render the browsable example project library."""
    st.markdown("### 📚 Example project library")
    st.caption("Browse real-world examples from different industries and problem types. Click **Load this example** to pre-fill the form.")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        domain_filter = st.selectbox(
            "Filter by domain",
            ["All domains"] + get_all_domains(),
            key="ex_domain",
        )
    with fc2:
        type_filter = st.selectbox(
            "Filter by problem type",
            ["All types"] + get_all_problem_types(),
            key="ex_type",
        )
    with fc3:
        complexity_filter = st.selectbox(
            "Filter by complexity",
            ["All levels", "Beginner", "Practitioner", "Black Belt"],
            key="ex_complexity",
        )

    # Apply filters
    filtered = PROJECT_LIBRARY
    if domain_filter != "All domains":
        filtered = [p for p in filtered if p["domain"] == domain_filter]
    if type_filter != "All types":
        filtered = [p for p in filtered if p["problem_type"] == type_filter]
    if complexity_filter != "All levels":
        filtered = [p for p in filtered if p["complexity"] == complexity_filter]

    if not filtered:
        st.info("No examples match the current filters.")
        return

    st.markdown(f"**{len(filtered)} example(s)**")

    for proj in filtered:
        complexity_colour = {"Beginner": "#DCFCE7", "Practitioner": "#EEF2FF", "Black Belt": "#FEF9C3"}.get(proj["complexity"], "#F1F4FB")
        complexity_text   = {"Beginner": "#166534", "Practitioner": "#3730A3", "Black Belt": "#854D0E"}.get(proj["complexity"], "#374151")

        with st.expander(f"**{proj['title']}** — {proj['domain']}", expanded=False):
            tag_html = "".join(
                f'<span style="background:#EEF2FF;color:#4361EE;border-radius:20px;'
                f'padding:2px 10px;font-size:0.75em;font-weight:700;margin-right:4px">{t}</span>'
                for t in proj.get("tags", [])[:5]
            )
            st.markdown(
                f'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px">'
                f'<span style="background:{complexity_colour};color:{complexity_text};border-radius:20px;'
                f'padding:2px 10px;font-size:0.75em;font-weight:700">{proj["complexity"]}</span>'
                f'<span style="background:#F0FDF4;color:#166534;border-radius:20px;'
                f'padding:2px 10px;font-size:0.75em;font-weight:700">{proj["problem_type"]}</span>'
                f'{tag_html}</div>',
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("**Problem statement:**")
                st.info(proj["problem_statement"])
                st.markdown(f"**Recommended tools:** {', '.join(proj.get('typical_tools', []))}")
            with c2:
                st.markdown("**❌ Weak input example:**")
                st.markdown(
                    f'<div style="background:#FEE2E2;border-radius:8px;padding:8px 12px;'
                    f'font-size:0.85em;color:#991B1B;font-style:italic">'
                    f'"{proj["weak_input_example"]}"</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("**✓ Strong input (this example):**")
                st.markdown(
                    f'<div style="background:#DCFCE7;border-radius:8px;padding:8px 12px;'
                    f'font-size:0.85em;color:#166534">'
                    f'{proj["strong_input_example"]}</div>',
                    unsafe_allow_html=True,
                )

            if proj.get("common_mistakes"):
                st.markdown("**⚠ Common mistakes:**")
                for m in proj["common_mistakes"]:
                    st.markdown(f"- {m}")

            if st.button("Load this example →", key=f"load_ex_{proj['id']}", type="primary"):
                st.session_state.project_data = {
                    "project_name":         proj["project_name"],
                    "problem_statement":    proj["problem_statement"],
                    "current_symptoms":     proj["current_symptoms"],
                    "current_metrics":      proj["current_metrics"],
                    "constraints":          proj["constraints"],
                    "stakeholder_concerns": proj["stakeholder_concerns"],
                }
                st.rerun()


def _step_intake() -> None:
    st.markdown('<span class="step-badge">STEP 1 OF 5</span>', unsafe_allow_html=True)
    st.markdown("## Project Intake")

    # Hero banner
    st.markdown("""
    <div class="hero-banner">
      <h2>Turn messy project problems into structured improvement plans</h2>
      <p>Describe your project below. The more detail you provide, the more specific and actionable the outputs.</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick-load buttons
    c_sample, c_browse, _ = st.columns([1, 1, 3])
    with c_sample:
        if st.button("Load sample project", use_container_width=True, key="load_sample"):
            sample = load_sample_project()
            if sample:
                st.session_state.project_data = sample
                st.rerun()
    with c_browse:
        if st.button("📚 Browse examples", use_container_width=True, key="toggle_library"):
            st.session_state["show_library"] = not st.session_state.get("show_library", False)

    # Example library panel
    if st.session_state.get("show_library", False):
        st.divider()
        _render_example_library()

    st.divider()

    defaults = st.session_state.project_data or {}
    form_data = collect_project_input(defaults)

    # Question coach
    prob = form_data.get("problem_statement", "")
    if len(prob.strip()) > 20:
        st.divider()
        render_question_coach(prob)

    st.divider()

    col_hint, col_btn = st.columns([3, 1])
    with col_hint:
        st.caption("All fields except project name and problem statement are optional but improve output quality significantly.")
    with col_btn:
        if st.button("Next: Configure →", type="primary", use_container_width=True, key="intake_next"):
            if not form_data.get("project_name","").strip():
                st.error("Project name is required.")
            elif not form_data.get("problem_statement","").strip():
                st.error("Problem statement is required.")
            else:
                st.session_state.project_data = form_data
                _go(2)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Configure
# ─────────────────────────────────────────────────────────────────────────────

_MODES = {
    "dmaic":        ("📊", "DMAIC",         "Full Define → Measure → Analyze → Improve → Control analysis. Best for structured, medium-to-large improvement projects."),
    "kaizen":       ("⚡", "Kaizen",        "Rapid small-batch improvement cycles and quick wins. Best for fast-moving teams or small scoped issues."),
    "root_cause":   ("🔍", "Root Cause",    "Deep 5 Whys causal chain + fishbone analysis. Best when the cause of the problem is unclear."),
    "process_waste":("♻",  "Process Waste", "TIMWOODS waste identification with countermeasures. Best for flow and efficiency problems."),
    "control_plan": ("🎯", "Control Plan",  "Detailed control plan with owners, cadence, and threshold triggers. Best for sustaining existing gains."),
}

_AUDIENCES = {
    "engineer":     ("👷", "Engineer",      "Process-level detail, measurement systems, observable bottlenecks, technical improvements."),
    "pm":           ("📋", "Project Manager","Stakeholder alignment, open actions, milestone clarity, risk tracking."),
    "manager":      ("👔", "Manager",       "Team accountability, top priorities, review cadence, 30-day action list."),
    "quality_lead": ("✅", "Quality Lead",  "CTQ alignment, measurement integrity, evidence gaps, control plan rigor."),
    "executive":    ("👑", "Executive",     "Business impact, strategic risk, plain language. No jargon. Decision-ready."),
}


def _step_configure() -> None:
    st.markdown('<span class="step-badge">STEP 2 OF 5</span>', unsafe_allow_html=True)
    st.markdown("## Configure")
    st.markdown("Choose how the analysis should be framed and who the primary audience is.")

    st.divider()

    # Mode selection
    st.markdown("### Methodology Mode")
    st.caption("This determines the analytical lens and depth of each output section.")
    mode_cols = st.columns(len(_MODES))
    for col, (mode_id, (icon, label, desc)) in zip(mode_cols, _MODES.items()):
        selected = st.session_state.mode == mode_id
        border = "#4361EE" if selected else "#E2E8F0"
        bg     = "#EEF2FF" if selected else "#FFFFFF"
        txtcol = "#4361EE" if selected else "#374151"
        with col:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {border};border-radius:14px;'
                f'padding:18px 12px;text-align:center;min-height:110px;cursor:pointer;'
                f'transition:all 0.2s">'
                f'<div style="font-size:2em;margin-bottom:8px">{icon}</div>'
                f'<div style="font-weight:700;color:{txtcol};font-size:0.88em">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Select" if not selected else "✓ Selected",
                         key=f"mode_{mode_id}",
                         use_container_width=True,
                         type="primary" if selected else "secondary"):
                st.session_state.mode = mode_id
                st.rerun()

    # Show description for selected mode
    if st.session_state.mode in _MODES:
        _, label, desc = _MODES[st.session_state.mode]
        st.info(f"**{label}:** {desc}")

    st.divider()

    # Audience selection
    st.markdown("### Primary Audience")
    st.caption("The role summary and framing of outputs will be tailored to this audience.")
    aud_cols = st.columns(len(_AUDIENCES))
    for col, (aud_id, (icon, label, desc)) in zip(aud_cols, _AUDIENCES.items()):
        selected = st.session_state.audience == aud_id
        border = "#4361EE" if selected else "#E2E8F0"
        bg     = "#EEF2FF" if selected else "#FFFFFF"
        txtcol = "#4361EE" if selected else "#374151"
        with col:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {border};border-radius:14px;'
                f'padding:18px 12px;text-align:center;min-height:110px;cursor:pointer">'
                f'<div style="font-size:2em;margin-bottom:8px">{icon}</div>'
                f'<div style="font-weight:700;color:{txtcol};font-size:0.88em">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Select" if not selected else "✓ Selected",
                         key=f"aud_{aud_id}",
                         use_container_width=True,
                         type="primary" if selected else "secondary"):
                st.session_state.audience = aud_id
                st.rerun()

    if st.session_state.audience in _AUDIENCES:
        _, label, desc = _AUDIENCES[st.session_state.audience]
        st.info(f"**{label}:** {desc}")

    st.divider()
    c_back, c_next = st.columns([1, 5])
    with c_back: _back(1)
    with c_next:
        if st.button("Next: Generate →", type="primary", key="cfg_next"):
            _go(3)


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Generate
# ─────────────────────────────────────────────────────────────────────────────

def _step_generate() -> None:
    st.markdown('<span class="step-badge">STEP 3 OF 5</span>', unsafe_allow_html=True)
    st.markdown("## Run Assessment")

    data     = st.session_state.project_data or {}
    mode     = st.session_state.mode
    audience = st.session_state.audience
    mode_label, _, _ = _MODES.get(mode, ("", mode.upper(), ""))
    aud_label,  _, _ = _AUDIENCES.get(audience, ("", audience.title(), ""))

    # Summary card
    st.markdown('<div class="lss-card">', unsafe_allow_html=True)
    st.markdown("### Confirmation")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Project**")
        st.markdown(f"_{data.get('project_name','—')}_")
        st.markdown(f"**Mode:** {mode_label}")
        st.markdown(f"**Audience:** {aud_label}")
    with c2:
        syms = data.get("current_symptoms", [])
        mets = data.get("current_metrics", {})
        st.markdown(f"**Symptoms provided:** {len(syms)}")
        st.markdown(f"**Metrics provided:** {len(mets)}")
        st.markdown(f"**Constraints:** {len(data.get('constraints',[]))}")
        st.markdown(f"**Stakeholder concerns:** {len(data.get('stakeholder_concerns',[]))}")
    with c3:
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY","").strip())
        if has_key:
            st.success("Claude AI will generate this assessment", icon="🤖")
        else:
            st.warning("Structured fallback mode (no API key)", icon="⚠️")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    c_back, c_run = st.columns([1, 4])
    with c_back:
        _back(2)
    with c_run:
        if st.button("▶  Run Assessment", type="primary", use_container_width=True, key="run_btn"):
            project = ProjectInput(**data)
            with st.spinner("Structuring your Lean Six Sigma assessment…"):
                result = run_assessment(project, mode=mode, audience=audience)
            st.session_state.result = result
            save_project_snapshot({**data, "mode": mode, "audience": audience})
            _go(4)

    if st.session_state.result is not None:
        st.divider()
        st.info("An assessment has already been generated. View it on the Dashboard or re-run to refresh.")
        if st.button("View Dashboard →", type="primary", key="go_dash"):
            _go(4)


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Dashboard
# ─────────────────────────────────────────────────────────────────────────────

_PHASE_CSS = {
    "define": "phase-define", "measure": "phase-measure",
    "analyze": "phase-analyze", "improve": "phase-improve", "control": "phase-control",
}
_PHASE_COLORS = {
    "define": "#3B82F6", "measure": "#8B5CF6",
    "analyze": "#F59E0B", "improve": "#10B981", "control": "#06B6D4",
}


def _sipoc_table(sipoc: dict) -> str:
    cols = ["suppliers", "inputs", "process", "outputs", "customers"]
    max_rows = max(len(sipoc.get(c, [])) for c in cols)
    rows_html = ""
    for r in range(max_rows):
        cells = ""
        for c in cols:
            items = sipoc.get(c, [])
            val = items[r] if r < len(items) else ""
            cells += f"<td>{val}</td>"
        rows_html += f"<tr>{cells}</tr>"
    headers = "".join(f"<th>{c.title()}</th>" for c in cols)
    return f'<table class="sipoc-table"><thead><tr>{headers}</tr></thead><tbody>{rows_html}</tbody></table>'


def _step_dashboard() -> None:
    result = st.session_state.result
    if result is None:
        st.warning("No assessment generated yet.")
        _back(3, "← Go to Generate")
        return

    # ── Header ──
    c_title, c_nav = st.columns([5, 1])
    with c_title:
        mode_label, _, _ = _MODES.get(result.mode, ("", result.mode.upper(), ""))
        aud_label,  _, _ = _AUDIENCES.get(result.audience, ("", result.audience.title(), ""))
        st.markdown(f"## {result.project_name}")
        st.markdown(
            f'<span style="background:#EEF2FF;color:#4361EE;border-radius:20px;'
            f'padding:3px 12px;font-size:0.82em;font-weight:700;margin-right:8px">'
            f'{mode_label} &nbsp;{result.mode.upper()}</span>'
            f'<span style="background:#F0FDF4;color:#166534;border-radius:20px;'
            f'padding:3px 12px;font-size:0.82em;font-weight:700">'
            f'{aud_label} &nbsp;{result.audience.replace("_"," ").title()}</span>',
            unsafe_allow_html=True,
        )
    with c_nav:
        st.write("")
        if st.button("Export →", type="primary", use_container_width=True, key="to_export"):
            _go(5)

    st.divider()

    # ── Executive signals ──
    with st.expander("Executive signals", expanded=True):
        for bullet in executive_bullets(result):
            st.markdown(f'<div class="signal-item">{bullet}</div>', unsafe_allow_html=True)

    st.divider()

    # ── KPI cards ──
    ev_df = build_evidence_dataframe(result)
    supported_count = int(ev_df.loc[ev_df["type"]=="Supported","count"].sum()) if not ev_df.empty else 0
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("CTQs identified",       len(result.ctqs))
    k2.metric("Root causes",           len(result.root_causes))
    k3.metric("Improvement actions",   len(result.improvement_actions))
    k4.metric("Control plan items",    len(result.control_plan))
    k5.metric("Supported evidence",    supported_count)

    st.divider()

    # ── Evidence legend ──
    _evidence_legend()

    # ── Output state label ──
    render_output_state_label("exploratory")

    # ── Next-step actions ──
    render_next_step_actions(result.mode, step=4)

    st.divider()

    # ── Main tabs ──
    tabs = st.tabs(["📋 Overview", "🔄 DMAIC", "🔍 Root Cause", "🚀 Improvements", "🎯 Control Plan", "📄 Summary"])

    # ════════════════════════════════
    # Tab 1 — Overview
    # ════════════════════════════════
    with tabs[0]:
        col_prob, col_sipoc = st.columns([5, 4])

        with col_prob:
            st.markdown("#### Problem Statement")
            st.info(result.cleaned_problem_statement)
            render_interpretation_card("problem_statement")
            st.markdown("#### Critical-to-Quality (CTQs)")
            _render_items(result.ctqs)
            with st.expander("ℹ What are CTQs?", expanded=False):
                render_interpretation_card("ctqs")

        with col_sipoc:
            st.markdown("#### SIPOC")
            st.markdown(_sipoc_table(result.sipoc), unsafe_allow_html=True)
            with st.expander("ℹ How to use this SIPOC", expanded=False):
                render_interpretation_card("sipoc")

        # Metric charts (only if numeric values exist)
        try:
            metric_df = build_metric_dataframe(ProjectInput(**st.session_state.project_data))
            if not metric_df.empty and metric_df["current"].sum() > 0:
                st.markdown("---")
                st.markdown("#### Baseline Metrics")
                m1, m2 = st.columns(2)
                with m1:
                    st.altair_chart(metric_bar_chart(metric_df), use_container_width=True)
                with m2:
                    st.altair_chart(target_gap_chart(metric_df), use_container_width=True)
        except Exception:
            pass

    # ════════════════════════════════
    # Tab 2 — DMAIC
    # ════════════════════════════════
    with tabs[1]:
        col_phases, col_charts = st.columns([3, 2])

        with col_phases:
            for phase, items in result.dmaic_structure.items():
                phase_col  = _PHASE_COLORS.get(phase, "#4361EE")
                with st.expander(f"**{phase.upper()}**", expanded=True):
                    st.markdown(
                        f'<div style="height:3px;background:{phase_col};border-radius:2px;margin-bottom:10px"></div>',
                        unsafe_allow_html=True,
                    )
                    _render_items(items)

        with col_charts:
            try:
                dm_df = build_dmaic_coverage_dataframe(result)
                st.altair_chart(dmaic_phase_chart(dm_df), use_container_width=True)
            except Exception:
                pass
            try:
                ev_df2 = build_evidence_dataframe(result)
                st.altair_chart(evidence_distribution_chart(ev_df2), use_container_width=True)
            except Exception:
                pass

    # ════════════════════════════════
    # Tab 3 — Root Cause
    # ════════════════════════════════
    with tabs[2]:
        render_interpretation_card("root_causes")
        col_rc, col_pareto = st.columns([3, 2])

        with col_rc:
            st.markdown("#### Root Causes")
            _render_items(result.root_causes)
            st.divider()
            st.markdown("#### Project Memory")
            for key, values in result.project_memory.items():
                label = key.replace("_", " ").title()
                with st.expander(label):
                    for v in values:
                        st.markdown(f"• {v}")

        with col_pareto:
            try:
                rc_df = build_root_cause_dataframe(result)
                st.altair_chart(pareto_chart(rc_df), use_container_width=True)
            except Exception:
                pass

        st.markdown(
            '<div style="background:#F0F9FF;border-radius:10px;padding:12px 16px;'
            'font-size:0.88em;color:#0369A1;margin-top:16px">'
            '<strong>→ Validate these causes:</strong> Go to '
            '<strong>⚡ Analytics Workbench → Hypothesis Tests</strong> to run statistical '
            'validation before proceeding to improvements.</div>',
            unsafe_allow_html=True,
        )

    # ════════════════════════════════
    # Tab 4 — Improvements
    # ════════════════════════════════
    with tabs[3]:
        render_interpretation_card("improvement_actions")
        col_actions, col_matrix = st.columns([3, 2])

        with col_actions:
            st.markdown("#### Improvement Actions")
            _render_items(result.improvement_actions)
            st.markdown("#### Metrics to Track")
            _render_items(result.suggested_metrics)

        with col_matrix:
            try:
                act_df = build_action_dataframe(result)
                st.altair_chart(action_matrix_chart(act_df), use_container_width=True)
            except Exception:
                pass
            try:
                pri_df = build_priority_dataframe(result)
                if not pri_df.empty:
                    st.altair_chart(priority_distribution_chart(pri_df), use_container_width=True)
            except Exception:
                pass

        st.divider()
        st.markdown("#### Action Tracker")
        import pandas as pd
        tracker_df = pd.DataFrame(result.action_tracker) if result.action_tracker else pd.DataFrame()
        if not tracker_df.empty:
            st.data_editor(
                tracker_df,
                use_container_width=True,
                hide_index=True,
                key="action_tracker_editor",
                num_rows="dynamic",
            )
            st.caption("✏ You can edit owners, priorities, and due dates directly in the table above.")
        else:
            st.info("No action tracker items generated.")

    # ════════════════════════════════
    # Tab 5 — Control Plan
    # ════════════════════════════════
    with tabs[4]:
        render_interpretation_card("control_plan")
        col_cp, col_ev = st.columns([3, 2])

        with col_cp:
            st.markdown("#### Control Plan Items")
            _render_items(result.control_plan)

        with col_ev:
            try:
                ev_df3 = build_evidence_dataframe(result)
                st.altair_chart(evidence_distribution_chart(ev_df3), use_container_width=True)
            except Exception:
                pass

        st.divider()
        st.markdown("#### Control Plan Summary Table")
        try:
            cp_df = control_plan_table(result)
            st.data_editor(
                cp_df,
                use_container_width=True,
                hide_index=True,
                key="control_plan_editor",
                num_rows="dynamic",
            )
            st.caption("✏ Edit owners, cadence, and triggers directly above.")
        except Exception:
            pass

    # ════════════════════════════════
    # Tab 6 — Summary
    # ════════════════════════════════
    with tabs[5]:
        st.markdown("#### Role-Aware Summary")
        aud_label2, _, _ = _AUDIENCES.get(result.audience, ("", result.audience.title(), ""))
        st.markdown(
            f'<div class="lss-card-accent" style="border-left-color:#4361EE">'
            f'<div style="font-size:0.78em;font-weight:700;color:#4361EE;text-transform:uppercase;'
            f'letter-spacing:0.07em;margin-bottom:8px">{aud_label2} summary</div>'
            f'<div style="color:#1E293B;font-size:0.95em;line-height:1.7">{result.role_summary}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown("#### Executive Signals")
        for b in executive_bullets(result):
            st.markdown(f'<div class="signal-item">{b}</div>', unsafe_allow_html=True)
        st.caption("Go to Export to download this assessment in your preferred format.")

    st.divider()
    _back(3)


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Export
# ─────────────────────────────────────────────────────────────────────────────

def _step_export() -> None:
    result = st.session_state.result
    if result is None:
        st.warning("No assessment to export. Generate one first.")
        _back(3, "← Go to Generate")
        return

    st.markdown('<span class="step-badge">STEP 5 OF 5</span>', unsafe_allow_html=True)
    st.markdown("## Export")
    st.markdown("Download your assessment in the format best suited for your audience and workflow.")
    st.divider()

    safe_name = result.project_name.replace(" ", "_").replace("/", "-")
    md_content   = render_markdown_summary(result)
    html_content = render_html_summary(result)

    # ── Four format cards ──
    ec1, ec2, ec3, ec4 = st.columns(4)

    _FORMATS = [
        (ec1, "📄", "PDF Report",      "Professional formatted report for printing, emailing, or leadership review.",      "primary"),
        (ec2, "📝", "Word Document",   "Editable .docx file with full structure, tables, and evidence-tagged bullet lists.", "primary"),
        (ec3, "📊", "Excel Workbook",  "Structured .xlsx with six sheets: Overview, DMAIC, Root Causes, Improvements, Control Plan, Summary.", "primary"),
        (ec4, "🌐", "HTML Briefing",   "Self-contained HTML file. Open in any browser. Easy to share or embed in portals.", "primary"),
    ]

    for col, icon, title, desc, _ in _FORMATS:
        with col:
            st.markdown(
                f'<div class="export-card">'
                f'<div class="export-icon">{icon}</div>'
                f'<div class="export-title">{title}</div>'
                f'<div class="export-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")  # spacing

    dl1, dl2, dl3, dl4 = st.columns(4)

    with dl1:
        try:
            pdf_bytes = render_pdf_summary(result)
            st.download_button(
                "Download PDF",
                pdf_bytes,
                file_name=f"{safe_name}_lss_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="dl_pdf",
            )
        except Exception as e:
            st.error(f"PDF error: {e}")

    with dl2:
        try:
            docx_bytes = render_docx_summary(result)
            st.download_button(
                "Download Word",
                docx_bytes,
                file_name=f"{safe_name}_lss_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary",
                key="dl_docx",
            )
        except Exception as e:
            st.error(f"Word error: {e}")

    with dl3:
        try:
            xlsx_bytes = render_xlsx_summary(result)
            st.download_button(
                "Download Excel",
                xlsx_bytes,
                file_name=f"{safe_name}_lss_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
                key="dl_xlsx",
            )
        except Exception as e:
            st.error(f"Excel error: {e}")

    with dl4:
        st.download_button(
            "Download HTML",
            html_content,
            file_name=f"{safe_name}_lss_briefing.html",
            mime="text/html",
            use_container_width=True,
            type="primary",
            key="dl_html",
        )

    st.divider()

    # Markdown also available
    st.markdown("#### Also available: Markdown")
    st.caption("Works in Notion, Confluence, GitHub, and any text editor.")
    st.download_button(
        "Download Markdown (.md)",
        md_content,
        file_name=f"{safe_name}_lss_report.md",
        mime="text/markdown",
        key="dl_md",
    )

    st.divider()
    st.markdown("#### Chart images")
    st.info(
        "To save any chart as an image: right-click the chart → **Save image as…** "
        "(or use the camera icon that appears on hover in some browsers).",
        icon="📸",
    )

    st.divider()
    st.markdown("#### Markdown preview")
    st.code(md_content[:4000] + ("\n\n… (truncated)" if len(md_content) > 4000 else ""), language="markdown")

    st.divider()
    _back(4, "← Dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

_mode = st.session_state.get("app_mode", "wizard")
if _mode == "workbench":
    render_analytics_workbench()
elif _mode == "recommender":
    render_tool_recommender()
elif _mode == "tollgate":
    render_tollgate()
else:
    {1: _step_intake, 2: _step_configure, 3: _step_generate,
     4: _step_dashboard, 5: _step_export}.get(st.session_state.step, _step_intake)()
