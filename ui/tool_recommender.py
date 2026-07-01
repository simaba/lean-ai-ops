"""Interactive Lean Six Sigma tool recommender.

The module intentionally keeps recommendation logic separate from Streamlit
rendering so the decision rules can be tested without relying on UI state.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


QUESTION_OPTIONS = {
    "q1": [
        "Too many defects or errors",
        "Process is too slow / long lead times",
        "Results are inconsistent / too much variation",
        "We know there's waste but can't pinpoint it",
        "Need to understand what's driving an outcome (Y)",
        "Need to prevent future failures",
        "Need to sustain / control recent gains",
        "Not sure — I just know something is wrong",
    ],
    "q2": [
        "None yet — haven't started measuring",
        "Some data — a few weeks / small sample",
        "Good data — months of history, 30+ data points",
        "Lots of data — automated / ongoing process data",
    ],
    "q3": [
        "Single machine, station, or step",
        "End-to-end process (multiple steps or departments)",
        "Product or service line",
        "Organisation-wide",
    ],
    "q4": [
        "Immediate — something needs fixing this week",
        "Short-term — 1-4 weeks",
        "Medium-term — 1-3 months project",
        "Long-term — formal improvement programme",
    ],
    "q5": [
        "We have no formal measurement",
        "We measure but haven't validated the measurement system",
        "We've done a basic gauge check",
        "Measurement system is validated (MSA / Gauge R&R done)",
    ],
    "q6": [
        "No idea — haven't investigated yet",
        "Have some hunches but not confirmed",
        "Root cause is known but solution is unclear",
        "Root cause and solution are known — need to implement and sustain",
    ],
    "q7": [
        "No prior LSS training",
        "Yellow Belt — familiar with basics",
        "Green Belt — can run structured projects",
        "Black Belt — full statistical toolkit",
    ],
}


_DATA_RICH = {
    "Good data — months of history, 30+ data points",
    "Lots of data — automated / ongoing process data",
}
_ADVANCED_EXPERIENCE = {
    "Green Belt — can run structured projects",
    "Black Belt — full statistical toolkit",
}


def _recommendation(
    *,
    problem_type: str,
    data_availability: str,
    scope: str,
    urgency: str,
    measurement_confidence: str,
    root_cause_status: str,
    experience: str,
) -> dict[str, Any]:
    """Return a bounded recommendation from the seven diagnostic inputs."""
    def result(
        tool: str,
        icon: str,
        rationale: str,
        inputs: list[str],
        outputs: list[str],
        cautions: list[str],
        next_step: str,
        effort: str,
        supporting: list[str],
    ) -> dict[str, Any]:
        return {
            "tool": tool,
            "icon": icon,
            "rationale": rationale,
            "inputs": inputs,
            "outputs": outputs,
            "cautions": cautions,
            "next_step": next_step,
            "effort": effort,
            "supporting": supporting,
        }

    if (
        root_cause_status
        == "Root cause and solution are known — need to implement and sustain"
        or problem_type == "Need to sustain / control recent gains"
    ):
        return result(
            "Control Plan",
            "🛡️",
            "The immediate need is to sustain an implemented improvement through named owners, review cadence, monitored signals, and escalation triggers.",
            ["validated improvement action", "process owner", "control metric", "review cadence"],
            ["control plan", "owner and escalation map", "monitoring checklist"],
            ["Control limits and specification limits are not the same.", "Validate the measurement system before relying on any threshold."],
            "Open Project Wizard → select Control Plan mode.",
            "1–2 weeks",
            ["SPC Charts", "Hypothesis Testing"],
        )

    if problem_type == "Too many defects or errors":
        if data_availability in _DATA_RICH:
            if measurement_confidence != "Measurement system is validated (MSA / Gauge R&R done)":
                return result(
                    "MSA / Gauge R&R",
                    "🎯",
                    "Before using defect data to choose a solution, check whether the measurement method itself is consistent enough for the decision.",
                    ["representative parts or samples", "operators", "measurement procedure", "specification limits where available"],
                    ["measurement-system variation view", "repeatability/reproducibility signals", "next measurement action"],
                    ["Do not treat an unvalidated measurement method as ground truth.", "Run studies under realistic operating conditions."],
                    "Open Analytics Workbench → MSA / Gauge R&R.",
                    "1–3 days",
                    ["Process Capability", "SPC Charts"],
                )
            return result(
                "Process Capability",
                "📊",
                "You have meaningful data and a validated measurement system, so the next question is whether the process can meet its stated specification limits consistently.",
                ["time-ordered measurements", "specification limits", "validated measurement method"],
                ["capability indicators", "distribution view", "evidence for further investigation"],
                ["Check stability before interpreting capability metrics.", "Non-normal data may need a different analysis approach."],
                "Open Analytics Workbench → Process Capability.",
                "1–2 days",
                ["SPC Charts", "Root Cause Analysis"],
            )
        return _dmaic_recommendation(result)

    if problem_type in {
        "Process is too slow / long lead times",
        "We know there's waste but can't pinpoint it",
    }:
        return result(
            "Lean Flow / Value Stream Analysis",
            "🌊",
            "For flow and waste problems, map the real current process first, including queue and wait time, before selecting improvement actions.",
            ["process steps", "cycle and wait times", "handoffs", "demand or workload pattern"],
            ["current-state flow view", "bottleneck hypotheses", "waste-reduction opportunities"],
            ["Map the actual current state, not the intended process.", "Do not assume a faster local step improves end-to-end flow."],
            "Open Analytics Workbench → Lean Flow.",
            "1–3 weeks",
            ["Process Waste mode", "SPC Charts"],
        )

    if problem_type == "Results are inconsistent / too much variation":
        if data_availability in _DATA_RICH:
            return result(
                "SPC Charts",
                "📈",
                "Time-ordered data can reveal whether variation is a stable common-cause pattern or a special-cause signal that needs investigation.",
                ["time-ordered measurements", "process context", "measurement confidence"],
                ["stability signals", "candidate special causes", "monitoring baseline"],
                ["Control limits are not specification limits.", "Do not reorder the time series before analysis."],
                "Open Analytics Workbench → SPC Charts.",
                "1–3 days",
                ["Process Capability", "Regression"],
            )
        return result(
            "Root Cause Analysis",
            "🌿",
            "With limited data, start by structuring hypotheses and a targeted data-collection plan rather than making a confident causal claim.",
            ["problem statement", "operator and stakeholder observations", "available incident records"],
            ["5 Whys or fishbone draft", "testable hypotheses", "data-collection plan"],
            ["Treat every proposed cause as a hypothesis until evidence supports it.", "Avoid choosing a solution during the first workshop."],
            "Open Project Wizard → select Root Cause mode.",
            "1–2 weeks",
            ["Hypothesis Testing", "SPC Charts"],
        )

    if problem_type == "Need to understand what's driving an outcome (Y)":
        if data_availability in _DATA_RICH and experience in _ADVANCED_EXPERIENCE:
            return result(
                "Regression Analysis",
                "📉",
                "A structured regression can help quantify associations between a defined outcome and candidate input variables when the data and assumptions are appropriate.",
                ["outcome variable", "candidate input variables", "sufficient representative observations"],
                ["association estimates", "diagnostic plots", "candidate drivers for follow-up"],
                ["Association does not prove causation.", "Review model assumptions and multicollinearity before acting."],
                "Open Analytics Workbench → Regression.",
                "2–5 days",
                ["DOE", "Hypothesis Testing"],
            )
        return result(
            "Hypothesis Testing",
            "🔬",
            "A focused test answers a narrow comparison question and is usually a clearer starting point than a broad model when experience or data are limited.",
            ["specific comparison question", "defined groups or conditions", "measurement data"],
            ["test result", "confidence interval", "plain-language interpretation"],
            ["Statistical significance is not the same as practical importance.", "Confirm sample adequacy and measurement quality."],
            "Open Analytics Workbench → Hypothesis Testing.",
            "1–2 days",
            ["Regression", "SPC Charts"],
        )

    if problem_type == "Need to prevent future failures":
        return result(
            "FMEA",
            "⚠️",
            "Use a structured failure-mode review to identify where the process can fail, prioritize prevention work, and assign actions before a problem recurs.",
            ["process steps or functions", "cross-functional knowledge", "known failures or near misses"],
            ["prioritized failure modes", "risk-reduction actions", "owner tracker"],
            ["Numeric risk scores support prioritization but do not override a serious non-negotiable control gap.", "Re-score after mitigation evidence exists."],
            "Open Analytics Workbench → FMEA.",
            "1–2 weeks",
            ["Control Plan", "Root Cause Analysis"],
        )

    if urgency == "Immediate — something needs fixing this week":
        return result(
            "Kaizen / Rapid Improvement",
            "⚡",
            "For an urgent but bounded problem, run a short improvement cycle with a clear safety boundary, a named owner, and a measurable before/after signal.",
            ["narrow scope", "owner", "safe-to-test change", "baseline signal"],
            ["quick-win plan", "review checkpoint", "evidence for next decision"],
            ["Do not let urgency remove necessary safety, quality, or approval controls.", "Escalate broader structural issues into a DMAIC project."],
            "Open Project Wizard → select Kaizen mode.",
            "Days to 2 weeks",
            ["Process Waste mode", "Control Plan"],
        )

    return _dmaic_recommendation(result)


def _dmaic_recommendation(result_builder) -> dict[str, Any]:
    return result_builder(
        "DMAIC Project",
        "🔄",
        "A structured DMAIC path is the safest default when the problem is unclear, data is incomplete, or the team needs a disciplined route from problem framing through control.",
        ["clear problem statement", "initial stakeholder concerns", "available process data", "scope and constraints"],
        ["Define–Measure–Analyze–Improve–Control roadmap", "evidence gaps", "hypotheses and actions", "control plan draft"],
        ["Do not jump from symptoms to solutions.", "Validate measurements and root-cause hypotheses before broad rollout."],
        "Open Project Wizard → select DMAIC mode.",
        "4–12 weeks depending on scope",
        ["SIPOC", "FMEA", "MSA / Gauge R&R"],
    )


def _reset() -> None:
    for key in ["rec_submitted", *[f"rec_{name}" for name in QUESTION_OPTIONS]]:
        st.session_state.pop(key, None)


def render_tool_recommender() -> None:
    """Render the seven-question recommendation workflow."""
    st.markdown("## 🧭 Lean Six Sigma Tool Recommender")
    st.caption("A structured starting point, not a substitute for statistical, quality, safety, or domain review.")

    st.session_state.setdefault("rec_submitted", False)
    if st.session_state["rec_submitted"]:
        if st.button("Start a new recommendation", key="rec_reset"):
            _reset()
            st.rerun()
    else:
        with st.form("tool_recommender_form"):
            q1 = st.radio("What kind of problem are you dealing with?", QUESTION_OPTIONS["q1"], key="rec_q1")
            q2 = st.radio("How much data do you have?", QUESTION_OPTIONS["q2"], key="rec_q2")
            q3 = st.radio("What is the scope of the problem?", QUESTION_OPTIONS["q3"], key="rec_q3")
            q4 = st.radio("How urgently do you need a result?", QUESTION_OPTIONS["q4"], key="rec_q4")
            q5 = st.radio("How confident are you in your measurement system?", QUESTION_OPTIONS["q5"], key="rec_q5")
            q6 = st.radio("Do you know the root cause?", QUESTION_OPTIONS["q6"], key="rec_q6")
            q7 = st.radio("What is your team's LSS experience level?", QUESTION_OPTIONS["q7"], key="rec_q7")
            submitted = st.form_submit_button("Find my best approach", type="primary")
        if submitted:
            st.session_state["rec_submitted"] = True
            st.rerun()
        return

    recommendation = _recommendation(
        problem_type=st.session_state["rec_q1"],
        data_availability=st.session_state["rec_q2"],
        scope=st.session_state["rec_q3"],
        urgency=st.session_state["rec_q4"],
        measurement_confidence=st.session_state["rec_q5"],
        root_cause_status=st.session_state["rec_q6"],
        experience=st.session_state["rec_q7"],
    )

    st.success(f"Recommended starting point: {recommendation['icon']} {recommendation['tool']}")
    st.write(recommendation["rationale"])
    st.caption(f"Typical effort: {recommendation['effort']}")

    left, right = st.columns(2)
    with left:
        st.markdown("#### What you need")
        for item in recommendation["inputs"]:
            st.markdown(f"- {item}")
        st.markdown("#### What you get")
        for item in recommendation["outputs"]:
            st.markdown(f"- {item}")
    with right:
        st.markdown("#### Supporting tools")
        for item in recommendation["supporting"]:
            st.markdown(f"- {item}")
        st.markdown("#### Cautions")
        for item in recommendation["cautions"]:
            st.warning(item)

    st.info(recommendation["next_step"])
