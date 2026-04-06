"""
coaching.py
===========
Streamlit UI module providing four coaching sub-systems for the
LLM-powered Lean Six Sigma application:

1. Input coaching       — per-field guidance with good/weak examples
2. Question coach       — dynamic follow-up questions from problem statement
3. Output interpretation cards — what it means / what not to conclude / next step
4. Output state labels  — exploratory / validated / decision-ready / control-ready
5. Next-step actions    — context-aware action suggestion panel
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Colour palette — matches the app's global design system
# ---------------------------------------------------------------------------
_BLUE  = "#4361EE"
_NAVY  = "#1E1B4B"
_GREEN = "#06D6A0"
_AMBER = "#FFB703"
_RED   = "#EF233C"
_GRAY  = "#94A3B8"
_BG    = "#F1F4FB"


# ---------------------------------------------------------------------------
# Helper: inline pill badges
# ---------------------------------------------------------------------------
def _pill(text: str, bg: str, color: str = "#fff") -> str:
    """Return an HTML span styled as a pill badge."""
    return (
        f'<span style="background:{bg};color:{color};padding:6px 12px;'
        f'border-radius:20px;font-size:0.85rem;font-weight:500;'
        f'display:inline-block;margin:4px 0;">{text}</span>'
    )


def _small(text: str) -> str:
    """Return small muted HTML text."""
    return f'<p style="color:{_GRAY};font-size:0.82rem;margin:2px 0;">{text}</p>'


# ---------------------------------------------------------------------------
# FUNCTION 1 — Input coaching
# ---------------------------------------------------------------------------
_FIELD_COACHING: dict[str, dict] = {
    "project_name": {
        "meaning": "A concise title that identifies the process, metric, direction of change, and timeframe. It must be understandable to someone outside your team.",
        "weak": "Quality project",
        "strong": "Assembly Line B Defect Rate Reduction — Q3 2025",
        "template": "[Area/Process] [Metric] [Direction] — [Quarter/Year]",
        "tips": [
            "Name the specific area or process, not just a department.",
            "Include the metric and which way it needs to move (reduction, improvement).",
            "Add the quarter/year so it is unambiguous in future reviews.",
        ],
    },
    "problem_statement": {
        "meaning": "A precise, data-driven description of the gap between current and desired performance. It must include what is wrong, where, when it started, and what the business impact is.",
        "weak": "Quality is bad and customers are unhappy",
        "strong": "Defect rate on Assembly Line B increased from 2.1% to 4.8% over the last 3 months, causing rework cost increase of $45K/month and 2 customer escalations",
        "template": "[Metric] increased/decreased from [X] to [Y] over [time period] in [scope/location], causing [business impact in $, time, or customer terms].",
        "tips": [
            "Be specific — name the exact metric and the exact process or location.",
            "Always include numbers: current value, baseline value, and time period.",
            "Quantify the business impact in dollars, time, or customer terms.",
            "Do NOT state a cause or solution in the problem statement.",
        ],
    },
    "current_symptoms": {
        "meaning": "Observable evidence that the problem exists. Symptoms are what you can see or measure right now — not causes or solutions.",
        "weak": "Things are slow and broken",
        "strong": "Rework volumes increased 40% since March / 3 customer escalations in last 30 days / Overtime up 15h/week",
        "template": "One observable symptom per line. Be specific about magnitude and timing.",
        "tips": [
            "List each symptom on its own line for clarity.",
            "Include magnitude (%, $, count) and timing (since when, over what period).",
            "Symptoms should be observable — avoid opinions or inferred causes.",
        ],
    },
    "current_metrics": {
        "meaning": "The key numeric measures that define the current state of the problem. These feed directly into the analysis engine.",
        "weak": "defects=bad",
        "strong": "defect_rate_pct=4.8 / rework_cost_monthly_usd=45000 / customer_escalations_30d=3",
        "template": "metric_name=numeric_value (use underscores, no spaces)",
        "tips": [
            "Use snake_case names with units in the name (e.g. cost_usd, time_hours).",
            "Values must be numeric — no text values.",
            "Include the most important baseline metric, cost metric, and customer metric.",
        ],
    },
    "constraints": {
        "meaning": "Real boundaries that the solution must stay within. Constraints define what is not negotiable — budget, timeline, resources, scope.",
        "weak": "Not much time",
        "strong": "No capital investment approval until Q4 / Team available 10% FTE max / Cannot stop production line",
        "template": "One constraint per line. Include budget, time, resource, and scope constraints.",
        "tips": [
            "Be honest about constraints — hidden constraints cause solutions to fail at implementation.",
            "Cover at least four categories: budget, time, resources, and scope/access.",
            "Constraints help the AI avoid recommending solutions you cannot implement.",
        ],
    },
    "stakeholder_concerns": {
        "meaning": "What each key stakeholder specifically needs from this project. Different roles have different success criteria.",
        "weak": "Management is worried",
        "strong": "Plant Manager: shipment delays causing customer contract risk / Finance: rework cost must be under $20K/month by Q4 / Quality Lead: wants permanent fix not workaround",
        "template": "[Role]: [their specific concern or requirement]",
        "tips": [
            "Name the role or title, not the person.",
            "State their specific concern, not a generic worry.",
            "Include at least the operational, financial, and quality stakeholder perspectives.",
        ],
    },
}


def render_input_coaching(field_name: str) -> None:
    """Render a collapsible coaching panel for a single input field.

    Parameters
    ----------
    field_name:
        One of ``project_name``, ``problem_statement``, ``current_symptoms``,
        ``current_metrics``, ``constraints``, ``stakeholder_concerns``.
    """
    data = _FIELD_COACHING.get(field_name)
    if data is None:
        return

    label = field_name.replace("_", " ").title()
    with st.expander(f"📖 Coaching: {label}", expanded=False):
        # What this field means
        st.markdown(
            f'<p style="color:{_NAVY};font-weight:600;margin-bottom:4px;">What this field means</p>'
            f'<p style="font-size:0.9rem;color:#374151;margin-top:0;">{data["meaning"]}</p>',
            unsafe_allow_html=True,
        )

        # Weak / Strong examples
        col_weak, col_strong = st.columns(2)
        with col_weak:
            st.markdown(
                f'<p style="font-weight:600;color:{_RED};margin-bottom:4px;">❌ Weak example</p>'
                + _pill(data["weak"], bg="#FEE2E2", color="#991B1B"),
                unsafe_allow_html=True,
            )
        with col_strong:
            st.markdown(
                '<p style="font-weight:600;color:#065F46;margin-bottom:4px;">✓ Strong example</p>'
                + _pill(data["strong"], bg="#D1FAE5", color="#065F46"),
                unsafe_allow_html=True,
            )

        # Fill-in template
        st.markdown(
            f'<p style="font-weight:600;color:{_NAVY};margin-top:12px;margin-bottom:4px;">Fill-in template</p>',
            unsafe_allow_html=True,
        )
        st.code(data["template"], language=None)

        # Tips
        st.markdown(
            f'<p style="font-weight:600;color:{_NAVY};margin-bottom:4px;">Tips</p>',
            unsafe_allow_html=True,
        )
        tips_html = "".join(_small(f"• {tip}") for tip in data["tips"])
        st.markdown(tips_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FUNCTION 2 — Question coach
# ---------------------------------------------------------------------------
_QUESTION_BANK: dict[str, list[str]] = {
    "defect": [
        "Which defect categories occur most often — do you have a Pareto breakdown?",
        "Is the defect rate consistent across all shifts, lines, suppliers, or operators?",
        "Was anything changed (materials, process, people, equipment) before the increase started?",
        "Do you have inspection data to separate internal vs escaped defects?",
        "Is the measurement method for detecting defects stable and agreed upon?",
    ],
    "delay": [
        "Which specific step in the process takes the most time — do you have step-by-step timing data?",
        "Is the delay mostly active processing time or queue/waiting time?",
        "Does the delay vary by product type, customer, team, or time of day/week?",
        "Is the process currently stable, or does cycle time fluctuate widely?",
        "Do you have timestamps or logs you can upload to analyse the flow?",
    ],
    "variation": [
        "Is the variation random (common cause) or does it follow a pattern (special cause)?",
        "Do you have a time-ordered run chart or historical data to visualise the variation?",
        "Is your measurement system validated — could variation partly be from measurement error?",
        "Does the variation correlate with any input variables (machine, shift, material lot)?",
        "What is the current specification limit, and how often does the process exceed it?",
    ],
    "waste": [
        "Which waste type dominates — transportation, inventory, motion, waiting, overproduction, over-processing, or defects?",
        "Have you mapped the current-state value stream to see where time is spent?",
        "What is the ratio of value-added time to total lead time?",
        "Is the waste visible to the people doing the work, or only apparent at the aggregate level?",
        "Are there quick wins (Kaizen) possible, or does this need a deeper structural change?",
    ],
    "customer_dissatisfaction": [
        "Which complaint categories are most frequent — do you have a category breakdown?",
        "Are complaints concentrated in a specific product, region, customer segment, or channel?",
        "Do you have verbatim feedback or CSAT data by touchpoint?",
        "Is the complaint rate rising, stable, or seasonal?",
        "What is the cost per complaint (resolution, compensation, churn)?",
    ],
    "cost": [
        "Is this a one-time cost spike or a recurring trend?",
        "Which cost categories or process steps are driving the increase?",
        "Do you have a cost breakdown by category, department, or process step?",
        "Is the cost increase linked to volume changes, or is it a rate/efficiency problem?",
        "What is the target cost and what is the gap?",
    ],
    "generic": [
        "How long has this problem been occurring, and is it getting better or worse?",
        "Do you have any historical data — defect counts, times, costs — that you can upload?",
        "Is the problem consistent or does it vary by team, location, product, or time period?",
        "What has already been tried, and what were the results?",
        "Who is most affected, and what is the quantified business impact?",
    ],
}

_DETECTION_RULES: list[tuple[str, list[str]]] = [
    ("defect",                  ["defect", "error", "quality", "scrap", "rework"]),
    ("delay",                   ["delay", "slow", "cycle time", "lead time", "waiting", "backlog"]),
    ("variation",               ["variation", "unstable", "inconsistent", "fluctuat"]),
    ("waste",                   ["waste", "inefficien", "unnecessary"]),
    ("customer_dissatisfaction",["complaint", "satisf", "nps", "csat", "return", "warranty"]),
    ("cost",                    ["cost", "spend", "overrun", "budget", "expense"]),
]


def _detect_problem_type(text: str) -> str:
    """Return the problem type key based on keyword detection."""
    lower = text.lower()
    for ptype, keywords in _DETECTION_RULES:
        if any(kw in lower for kw in keywords):
            return ptype
    return "generic"


def render_question_coach(problem_statement: str) -> None:
    """Render dynamic follow-up questions based on the problem statement text.

    Parameters
    ----------
    problem_statement:
        The raw problem statement text entered by the user.
    """
    if not problem_statement or len(problem_statement.strip()) <= 20:
        st.markdown(
            f'<div style="background:{_BG};border-left:4px solid {_AMBER};'
            f'padding:12px 16px;border-radius:6px;font-size:0.88rem;color:#92400E;">'
            f'✏️ Fill in the <strong>Problem Statement</strong> field (more than 20 characters) '
            f'to see tailored coaching questions.</div>',
            unsafe_allow_html=True,
        )
        return

    ptype = _detect_problem_type(problem_statement)
    questions = _QUESTION_BANK[ptype]

    type_labels = {
        "defect": "Defect / Quality",
        "delay": "Delay / Cycle Time",
        "variation": "Process Variation",
        "waste": "Waste / Inefficiency",
        "customer_dissatisfaction": "Customer Dissatisfaction",
        "cost": "Cost Overrun",
        "generic": "General",
    }
    type_label = type_labels.get(ptype, "General")

    questions_html = "".join(
        f'<li style="margin:6px 0;font-size:0.88rem;color:#1E293B;">{q}</li>'
        for q in questions
    )

    st.markdown(
        f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;'
        f'padding:16px 20px;margin-top:8px;">'
        f'<p style="font-weight:700;color:{_BLUE};font-size:0.95rem;margin:0 0 8px 0;">'
        f'💡 Questions to answer before analysing'
        f'<span style="font-weight:400;color:{_GRAY};font-size:0.8rem;margin-left:8px;">'
        f'Detected type: {type_label}</span></p>'
        f'<ol style="margin:0;padding-left:20px;">{questions_html}</ol>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# FUNCTION 3 — Output state labels
# ---------------------------------------------------------------------------
_STATE_CONFIG: dict[str, dict] = {
    "exploratory": {
        "bg":    _AMBER,
        "color": "#1C1917",
        "label": "🔍 Exploratory",
        "desc":  "these are structured hypotheses, not proven conclusions. Validate before acting.",
    },
    "validated": {
        "bg":    _BLUE,
        "color": "#FFFFFF",
        "label": "✓ Validated",
        "desc":  "supported by data or evidence. Ready for decision-making with appropriate caveats.",
    },
    "decision-ready": {
        "bg":    _GREEN,
        "color": "#064E3B",
        "label": "✅ Decision-ready",
        "desc":  "sufficient evidence to proceed. Assign owners and set timelines.",
    },
    "control-ready": {
        "bg":    _NAVY,
        "color": "#E0E7FF",
        "label": "⚙ Control-ready",
        "desc":  "gains are confirmed. Focus on sustaining and monitoring.",
    },
}


def render_output_state_label(state: str) -> None:
    """Render a horizontal badge row explaining the current output state.

    Parameters
    ----------
    state:
        One of ``exploratory``, ``validated``, ``decision-ready``, ``control-ready``.
    """
    cfg = _STATE_CONFIG.get(state, _STATE_CONFIG["exploratory"])

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:10px;'
        f'background:{cfg["bg"]};color:{cfg["color"]};'
        f'padding:8px 18px;border-radius:24px;font-size:0.88rem;font-weight:600;">'
        f'{cfg["label"]}'
        f'<span style="font-weight:400;font-size:0.83rem;">— {cfg["desc"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# FUNCTION 4 — Output interpretation cards
# ---------------------------------------------------------------------------
_INTERPRETATION_DATA: dict[str, dict] = {
    "problem_statement": {
        "title": "Problem Statement",
        "means": "The problem has been restated to be specific, measurable, and scoped. It separates symptom from cause.",
        "not":   "This is not a root cause. Do not jump to solutions yet.",
        "next":  "Validate that stakeholders agree on this framing before proceeding.",
    },
    "ctqs": {
        "title": "Critical-to-Quality Items (CTQs)",
        "means": "These are the process outputs that most directly affect what customers care about.",
        "not":   "CTQs are not yet measures — they need operational definitions and measurement plans.",
        "next":  "For each CTQ, define how it will be measured, by whom, and how often.",
    },
    "sipoc": {
        "title": "SIPOC",
        "means": "A high-level view of the process from suppliers to customers. Shows scope and boundaries.",
        "not":   "SIPOC is not a detailed process map. It does not show sequencing, timing, or variation.",
        "next":  "Use SIPOC to agree on process scope, then drill into the most problematic steps.",
    },
    "dmaic": {
        "title": "DMAIC Roadmap",
        "means": "A structured five-phase improvement roadmap tailored to your project inputs.",
        "not":   "This is a starting framework, not a validated plan. All items are hypotheses until confirmed with data.",
        "next":  "Walk through each phase with your team. Identify what data you need to collect before progressing.",
    },
    "root_causes": {
        "title": "Root Cause Analysis",
        "means": "These are the most likely contributing causes based on the information provided.",
        "not":   "These are hypotheses, not confirmed causes. Do not implement solutions before validating.",
        "next":  "Select the 2-3 most plausible causes and design data collection or hypothesis tests to validate them.",
    },
    "improvement_actions": {
        "title": "Improvement Actions",
        "means": "Prioritised actions addressing validated or likely root causes.",
        "not":   "These are recommendations, not guarantees. Each action needs an owner, timeline, and success measure.",
        "next":  "Assign each action to an owner. Define what 'done' looks like. Schedule a review checkpoint.",
    },
    "control_plan": {
        "title": "Control Plan",
        "means": "A framework for sustaining the gains after improvement. Specifies what to monitor and what to do when signals appear.",
        "not":   "A control plan is not self-executing. It only works if someone reviews the metrics on schedule.",
        "next":  "Implement the control plan before closing the project. Set up the monitoring cadence and confirm owners.",
    },
}


def render_interpretation_card(output_type: str, extra_context: str = "") -> None:
    """Render a styled interpretation card for a given output type.

    Parameters
    ----------
    output_type:
        One of ``problem_statement``, ``ctqs``, ``sipoc``, ``dmaic``,
        ``root_causes``, ``improvement_actions``, ``control_plan``.
    extra_context:
        Optional additional text to append at the bottom of the card.
    """
    data = _INTERPRETATION_DATA.get(output_type)
    if data is None:
        return

    means_block = (
        f'<div style="background:#EFF6FF;border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<p style="font-weight:700;color:{_BLUE};font-size:0.82rem;margin:0 0 4px 0;'
        f'text-transform:uppercase;letter-spacing:0.05em;">📘 What this means</p>'
        f'<p style="font-size:0.88rem;color:#1E293B;margin:0;">{data["means"]}</p>'
        f'</div>'
    )

    not_block = (
        f'<div style="background:#FFFBEB;border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<p style="font-weight:700;color:#B45309;font-size:0.82rem;margin:0 0 4px 0;'
        f'text-transform:uppercase;letter-spacing:0.05em;">⚠️ What NOT to conclude</p>'
        f'<p style="font-size:0.88rem;color:#1E293B;margin:0;">{data["not"]}</p>'
        f'</div>'
    )

    next_block = (
        f'<div style="background:#ECFDF5;border-radius:8px;padding:12px 16px;">'
        f'<p style="font-weight:700;color:#065F46;font-size:0.82rem;margin:0 0 4px 0;'
        f'text-transform:uppercase;letter-spacing:0.05em;">✅ Next step</p>'
        f'<p style="font-size:0.88rem;color:#1E293B;margin:0;">{data["next"]}</p>'
        f'</div>'
    )

    extra_block = ""
    if extra_context.strip():
        extra_block = (
            f'<div style="margin-top:10px;border-top:1px solid #E2E8F0;padding-top:10px;">'
            f'<p style="font-size:0.82rem;color:{_GRAY};margin:0;">{extra_context}</p>'
            f'</div>'
        )

    card_html = (
        f'<div style="border:1px solid #E2E8F0;border-radius:12px;padding:16px;'
        f'background:#FFFFFF;margin-top:8px;">'
        f'<p style="font-weight:700;color:{_NAVY};font-size:0.95rem;margin:0 0 12px 0;">'
        f'🗂 Interpreting: {data["title"]}</p>'
        f'{means_block}'
        f'{not_block}'
        f'{next_block}'
        f'{extra_block}'
        f'</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FUNCTION 5 — Next-step actions
# ---------------------------------------------------------------------------
_NEXT_STEP_ACTIONS: dict[str, list[dict]] = {
    "dmaic": [
        {
            "icon": "📋",
            "title": "Present to sponsor",
            "desc": "Use the Summary tab to brief your project sponsor on findings and proposed next steps",
        },
        {
            "icon": "🧪",
            "title": "Validate root causes",
            "desc": "Switch to the Analytics Workbench → Hypothesis Tests to run statistical validation",
        },
        {
            "icon": "📊",
            "title": "Baseline your metrics",
            "desc": "Upload process data in the Analytics Workbench → Capability tab",
        },
        {
            "icon": "👥",
            "title": "Run a team workshop",
            "desc": "Use the DMAIC structure as the agenda for a focused improvement workshop",
        },
        {
            "icon": "📥",
            "title": "Export & share",
            "desc": "Download PDF or Word for leadership review or Confluence/SharePoint upload",
        },
    ],
    "kaizen": [
        {
            "icon": "⚡",
            "title": "Run a rapid improvement event",
            "desc": "Use the actions list as the Kaizen event agenda",
        },
        {
            "icon": "📋",
            "title": "Assign quick wins today",
            "desc": "From the Improvements tab, pick top 3 quick wins and assign owners now",
        },
        {
            "icon": "📈",
            "title": "Track before/after",
            "desc": "Measure the key metric before and after each quick win",
        },
        {
            "icon": "📥",
            "title": "Export action list",
            "desc": "Download the Excel workbook — it includes a structured action tracker",
        },
    ],
    "root_cause": [
        {
            "icon": "🧪",
            "title": "Test the top cause",
            "desc": "Design a data collection plan to confirm or refute the #1 root cause",
        },
        {
            "icon": "🔍",
            "title": "Run a 5 Whys workshop",
            "desc": "Facilitate a team session using the root cause list as the starting point",
        },
        {
            "icon": "📊",
            "title": "Collect stratified data",
            "desc": "Break your defect/delay data by the suspected cause variable",
        },
        {
            "icon": "📥",
            "title": "Export cause map",
            "desc": "Download the Markdown or Word export to share with the team",
        },
    ],
    "process_waste": [
        {
            "icon": "🗺",
            "title": "Map the value stream",
            "desc": "Use the waste findings to build a current-state value stream map",
        },
        {
            "icon": "⚡",
            "title": "Identify quick wins",
            "desc": "Any waste with low effort and high impact is a Kaizen candidate",
        },
        {
            "icon": "📐",
            "title": "Calculate value-add ratio",
            "desc": "Sum value-add time / total lead time to benchmark current state",
        },
        {
            "icon": "📥",
            "title": "Export waste register",
            "desc": "Download Excel — it has the improvement actions structured as a table",
        },
    ],
    "control_plan": [
        {
            "icon": "⚙",
            "title": "Implement monitoring now",
            "desc": "Set up the review cadence from the control plan immediately",
        },
        {
            "icon": "📈",
            "title": "Create control charts",
            "desc": "Go to Analytics Workbench → SPC Charts to build I-MR or p-charts",
        },
        {
            "icon": "📋",
            "title": "Assign control owners",
            "desc": "Every control item needs a named owner and a review date",
        },
        {
            "icon": "📥",
            "title": "Export control plan",
            "desc": "Download the Excel workbook — Sheet 5 is the formatted control plan table",
        },
    ],
}


def render_next_step_actions(result_mode: str, step: int) -> dict:
    """Render a 'What to do with this output' panel with contextual action cards.

    Parameters
    ----------
    result_mode:
        One of ``dmaic``, ``kaizen``, ``root_cause``, ``process_waste``, ``control_plan``.
    step:
        Current wizard step number (4 = Dashboard, 5 = Export).

    Returns
    -------
    dict
        ``{"rendered": True}`` after rendering completes.
    """
    actions = _NEXT_STEP_ACTIONS.get(result_mode, [])

    mode_labels = {
        "dmaic":         "DMAIC Roadmap",
        "kaizen":        "Kaizen / Rapid Improvement",
        "root_cause":    "Root Cause Analysis",
        "process_waste": "Process Waste Analysis",
        "control_plan":  "Control Plan",
    }
    mode_label = mode_labels.get(result_mode, result_mode.replace("_", " ").title())

    st.markdown(
        f'<p style="font-weight:700;color:{_NAVY};font-size:1rem;margin-bottom:12px;">'
        f'→ Next steps with this output'
        f'<span style="font-weight:400;color:{_GRAY};font-size:0.82rem;margin-left:8px;">'
        f'({mode_label} · Step {step})</span></p>',
        unsafe_allow_html=True,
    )

    if not actions:
        st.markdown(
            f'<p style="color:{_GRAY};font-size:0.88rem;">No actions configured for mode: {result_mode}</p>',
            unsafe_allow_html=True,
        )
        return {"rendered": True}

    # Render cards in columns — up to 4 per row
    chunk_size = 4
    for row_start in range(0, len(actions), chunk_size):
        row_actions = actions[row_start : row_start + chunk_size]
        cols = st.columns(len(row_actions))
        for col, action in zip(cols, row_actions):
            with col:
                col.markdown(
                    f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;'
                    f'border-radius:10px;padding:14px 12px;height:100%;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
                    f'<p style="font-size:1.4rem;margin:0 0 6px 0;">{action["icon"]}</p>'
                    f'<p style="font-weight:700;color:{_NAVY};font-size:0.88rem;'
                    f'margin:0 0 4px 0;">{action["title"]}</p>'
                    f'<p style="font-size:0.80rem;color:#475569;margin:0;">{action["desc"]}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    return {"rendered": True}
