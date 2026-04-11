# AI Process Excellence — LLM-powered Lean Six Sigma

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/simaba/lean-ai-ops)](https://github.com/simaba/lean-ai-ops/commits/main)

An AI copilot that turns informal project descriptions into rigorous, evidence-tagged Lean Six Sigma improvement packages — with a full Black Belt analytics workbench for quantitative analysis.

---

## What you get

### 📋 Project Wizard (5-step guided workflow)

Describe your project in plain language → receive a complete structured improvement package:

| Output | What it is |
|--------|-----------|
| **Cleaned problem statement** | Rewritten to be specific, measurable, and scoped |
| **CTQs** | Critical-to-Quality characteristics tied to customer requirements |
| **SIPOC** | Suppliers → Inputs → Process → Outputs → Customers map |
| **Full DMAIC structure** | All five phases: Define / Measure / Analyze / Improve / Control |
| **Root cause analysis** | 5 Whys chain and fishbone structure |
| **Suggested metrics** | What to measure and how |
| **Improvement actions** | Prioritised, with effort and impact context |
| **Control plan** | Owners, review cadence, escalation triggers |
| **Role-aware summary** | Framed for Engineer, PM, Manager, Quality Lead, or Executive |

Every output is tagged with an evidence label so you always know what's fact, what's inference, and what's missing:

- ✓ **Directly supported by input** — grounded in what you provided
- ~ **Inferred hypothesis** — logical inference pending validation
- ! **Missing evidence** — data gaps requiring investigation

### ⚡ Black Belt Analytics Workbench (9 tools)

| Tool | What it does |
|------|-------------|
| **Process Capability** | Cp, Cpk, Pp, Ppk, sigma level, DPMO, capability histogram |
| **MSA / Gauge R&R** | Repeatability, reproducibility, %GRR, NDC (ANOVA / AIAG MSA-4) |
| **Hypothesis Testing** | One-sample t, two-sample t, paired t, proportion tests, chi-square, ANOVA |
| **SPC Charts** | I-MR, Xbar-R, p-chart with Nelson rules and out-of-control detection |
| **FMEA** | Interactive RPN builder, risk matrix, Pareto chart |
| **Regression** | OLS with diagnostics (VIF, Breusch-Pagan, Durbin-Watson) |
| **DOE** | Factor definition, design recommendation (full factorial / fractional / Plackett-Burman) |
| **Benefits & COPQ** | ROI, payback period, 3-year NPV, waterfall and timeline charts |

### 📤 Export formats

PDF · Word (.docx) · Excel (.xlsx, 6-sheet workbench) · HTML · Markdown

---

## Quick start

### Prerequisites

- Python 3.10+
- A Claude API key from [console.anthropic.com](https://console.anthropic.com) *(optional — structured fallback mode runs without it)*

### Install and run

```bash
git clone https://github.com/simaba/lean-ai-ops.git
cd lean-ai-ops
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**Windows:** `py -m streamlit run app.py` also works.

The app opens in your browser at `http://localhost:8501`.

To run without a UI:

```bash
python run_demo.py
```

### Set your API key (optional)

**macOS / Linux**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

**Windows PowerShell**
```powershell
$env:ANTHROPIC_API_KEY="your_key_here"
```

Without a key the app runs in structured fallback mode. You still get the full framework and analytics, without LLM-generated content.

---

## Methodology options

**Five DMAIC approaches:** DMAIC · Kaizen · Root Cause Analysis · Process Waste (TIMWOODS) · Control Planning

**Five audience framings:** Engineer · Project Manager · Manager · Quality Lead · Executive

---

## Repository structure

```text
app.py                  # Streamlit UI entry point
run_demo.py             # CLI entry point
src/
  models.py             # Data models
  engine.py             # LLM orchestration
  phases/               # DMAIC phase handlers
analytics/              # Workbench tools (capability, MSA, SPC, FMEA, ...)
storage/                # Project persistence
examples/               # Sample projects
templates/              # Input templates
```

---

## Design principles

- **Evidence discipline** — every LLM output is tagged supported / inferred / missing
- **Graceful degradation** — full functionality without API key
- **Role-aware outputs** — same analysis, five different framings
- **Integrated quantitative analysis** — not just text generation

---

## Related repositories

This repository is part of a connected toolkit for responsible AI operations:

| Repository | Purpose |
|-----------|---------|
| [Enterprise AI Governance Playbook](https://github.com/simaba/governance-playbook) | End-to-end AI operating model from intake to improvement |
| [AI Release Governance Framework](https://github.com/simaba/release-governance) | Risk-based release gates for AI systems |
| [AI Release Readiness Checklist](https://github.com/simaba/release-checklist) | Risk-tiered pre-release checklists with CLI tool |
| [AI Accountability Design Patterns](https://github.com/simaba/accountability-patterns) | Patterns for human oversight and escalation |
| [Multi-Agent Governance Framework](https://github.com/simaba/multi-agent-governance) | Roles, authority, and escalation for agent systems |
| [Multi-Agent Orchestration Patterns](https://github.com/simaba/agent-orchestration) | Sequential, parallel, and feedback-loop patterns |
| [AI Agent Evaluation Framework](https://github.com/simaba/agent-eval) | System-level evaluation across 5 dimensions |
| [Agent System Simulator](https://github.com/simaba/agent-simulator) | Runnable multi-agent simulator with governance controls |
| [LLM-powered Lean Six Sigma](https://github.com/simaba/lean-ai-ops) | AI copilot for structured process improvement |

---

*Shared in a personal capacity. Open to collaborations and feedback — connect on [LinkedIn](https://linkedin.com/in/simaba) or [Medium](https://medium.com/@bagheri.sima).*