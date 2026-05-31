# AI Process Excellence | LLM-powered Lean Six Sigma

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/simaba/lean-ai-ops)](https://github.com/simaba/lean-ai-ops/commits/main)

An AI copilot that turns informal project descriptions into structured Lean Six Sigma improvement packages, with a quantitative analytics workbench for Black Belt style analysis.

## What this repo is for

Use this repository when you want to:

- turn a messy improvement problem into a structured DMAIC package
- generate CTQs, SIPOC, root-cause hypotheses, actions, and control-plan outputs
- run quantitative workbench analyses alongside the narrative outputs
- export a project package to PDF, Word, Excel, HTML, or Markdown

This repository is best understood as a **working application**, not just a framework or document set.

## Maturity

This is a **working app and analytics prototype**. It is useful for structured problem-solving demos, Lean Six Sigma practice, PM/quality workflows, and internal process-improvement exploration. It is not a substitute for certified Black Belt review, validated statistical software, production quality systems, or domain-expert decision-making.

## What you get

### 1. Project Wizard

Describe a project in plain language and receive a structured package including:

| Output | What it is |
|---|---|
| Cleaned problem statement | Rewritten to be specific, measurable, and scoped |
| CTQs | Critical-to-Quality characteristics tied to customer requirements |
| SIPOC | Suppliers, Inputs, Process, Outputs, Customers map |
| DMAIC structure | Define, Measure, Analyze, Improve, Control outputs |
| Root cause analysis | 5 Whys chain and fishbone-style structure |
| Suggested metrics | What to measure and how |
| Improvement actions | Prioritized with effort and impact context |
| Control plan | Owners, cadence, and escalation triggers |
| Role-aware summary | Framed for Engineer, PM, Manager, Quality Lead, or Executive |

Every output is tagged with an evidence label:

- **supported** for items grounded in your input
- **inferred** for logical hypotheses that still need validation
- **missing** for evidence gaps that should be investigated

### 2. Analytics Workbench

The analytics workbench currently includes **8 tool areas**:

| Tool area | What it does |
|---|---|
| Process Capability | Cp, Cpk, Pp, Ppk, sigma level, DPMO, capability histogram |
| MSA / Gauge R&R | Repeatability, reproducibility, %GRR, NDC |
| Hypothesis Testing | One-sample t, two-sample t, paired t, proportions, chi-square, ANOVA |
| SPC Charts | I-MR, Xbar-R, p-chart, out-of-control signals |
| FMEA | Interactive RPN builder, risk matrix, Pareto chart |
| Regression | OLS with diagnostics |
| DOE | Factor definition and design recommendation |
| Benefits & COPQ | ROI, payback period, NPV, waterfall and timeline charts |

### 3. Export formats

PDF, Word (`.docx`), Excel (`.xlsx`), HTML, and Markdown.

## Quick start

### Prerequisites

- Python 3.10+
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com) if you want LLM-generated content

The app still runs without an API key in structured fallback mode.

### Install and run the app

```bash
git clone https://github.com/simaba/lean-ai-ops.git
cd lean-ai-ops
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**Windows:** `py -m streamlit run app.py` also works.

### Run the CLI demo

The repository includes a sample input file at `templates/sample_project.json`.

```bash
python run_demo.py --input templates/sample_project.json --mode dmaic --audience pm
```

This path is also exercised in CI using the deterministic fallback flow, so the documented demo path stays valid even when no API key is set.

## Methodology options

**Modes:** DMAIC, Kaizen, Root Cause Analysis, Process Waste, Control Planning

**Audience framings:** Engineer, Project Manager, Manager, Quality Lead, Executive

## Repository structure

```text
app.py                  # Streamlit UI entry point
run_demo.py             # CLI entry point
src/
  models.py             # Data models
  engine.py             # Assessment orchestration
analytics/              # Workbench tools
storage/                # Project persistence
ui/                     # UI components
templates/              # Input templates including sample_project.json
examples/               # Example projects and outputs
tests/                  # Smoke tests for documented fallback path
```

## Architecture roadmap

The app already works, but the next quality step is to make the architecture easier to maintain and review.

Target direction:

```text
app.py                         # Thin Streamlit entry point
ui/
  theme.py                     # Styling and visual constants
  layout.py                    # Shared page layout
  pages/
    project_wizard.py          # Project-input and package-generation flow
    analytics_workbench.py     # Statistical tool views
    export_center.py           # Export controls and previews
services/
  assessment_service.py        # Business logic orchestration
  export_service.py            # PDF, DOCX, XLSX, HTML, Markdown export logic
analytics/
  capability.py
  msa.py
  hypothesis_testing.py
  spc.py
  fmea.py
  regression.py
  doe.py
  benefits.py
```

This would make `app.py` smaller, reduce coupling between UI and logic, and make the analytics tools easier to test independently.

## Design principles

- **evidence discipline** so users can separate facts from hypotheses
- **graceful degradation** so the app still works without an API key
- **role-aware framing** so the same work can be expressed for different audiences
- **quantitative plus narrative** so the repo is useful for actual improvement work
- **transparent technical debt** so limitations are named and improvements are trackable

## Current quality guardrails

The repository currently has:

- CI checks for imports and tests
- smoke coverage for the documented CLI fallback path
- a bundled sample project input for repeatable demos

The main remaining technical debt is app modularity. `app.py` still carries too much responsibility relative to a gold-standard app architecture. The architecture roadmap above documents the intended direction before deeper refactoring.

## Scope and disclaimer

This repository is shared in a personal capacity. It is not statistical certification, process certification, legal advice, compliance certification, or official Lean Six Sigma training material.

AI-generated outputs should be treated as structured drafts and hypotheses. Validate assumptions, measurements, root causes, statistical interpretations, and improvement actions with real process data and qualified domain experts.

## Related repositories

| Repository | Purpose |
|---|---|
| [governance-playbook](https://github.com/simaba/governance-playbook) | End-to-end AI operating model |
| [release-governance](https://github.com/simaba/release-governance) | Risk-based release gates for AI systems |
| [release-checklist](https://github.com/simaba/release-checklist) | CLI validator for YAML-based release readiness |
| [agent-simulator](https://github.com/simaba/agent-simulator) | Runnable multi-agent simulator |
| [ai-prism](https://github.com/simaba/ai-prism) | Curated governance resources |

---

*Shared in a personal capacity. Open to collaborations and feedback via [LinkedIn](https://linkedin.com/in/simaba) or [Medium](https://medium.com/@bagheri.sima).*
