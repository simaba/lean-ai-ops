# Lean AI Ops

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/simaba/lean-ai-ops)](https://github.com/simaba/lean-ai-ops/commits/main)

**Lean AI Ops is a local AI-powered Lean Six Sigma assistant for turning messy process problems into structured improvement plans, metrics, action trackers, and exportable project packages.**

It is designed for people who need to improve a process but do not want to start from a blank page.

You describe the problem in plain language. The app helps organize it into a practical Lean Six Sigma package using DMAIC, root-cause analysis, process-waste thinking, control planning, and quantitative analysis tools.

---

## Plain-English summary

Lean AI Ops helps answer questions like:

- What exactly is the process problem?
- What should we measure?
- What are the likely root causes?
- Which actions should we try first?
- Who should own each action?
- How do we know if the improvement worked?
- How do we explain this clearly to a manager, PM, engineer, quality lead, or executive?

The goal is not to replace a Lean Six Sigma expert. The goal is to give teams a structured first draft, a measurement starting point, and a better way to discuss process improvement.

---

## Who this is for

This repo is useful for:

| User | How it helps |
|---|---|
| Program managers | Turns vague delivery problems into structured actions, owners, risks, and metrics |
| Project managers | Creates clear improvement plans, summaries, and trackers |
| Quality teams | Frames problems using CTQs, DMAIC, root-cause logic, and control plans |
| Operations teams | Identifies waste, bottlenecks, rework, and review cadence needs |
| Engineering teams | Helps translate process pain into measurable workflow improvements |
| Executives | Produces concise summaries focused on impact, risk, and decisions needed |
| Learners | Demonstrates how Lean Six Sigma methods can be applied to real process problems |

---

## What the app does

### 1. Project Wizard

The Project Wizard takes a plain-language problem description and generates a structured improvement package.

Example input:

```text
Supplier change requests are taking too long to move from intake to decision. Teams keep asking for status updates, ownership is unclear, and requests often need rework because the right information is missing.
```

Example outputs:

| Output | Meaning |
|---|---|
| Cleaned problem statement | A clearer, more measurable version of the problem |
| CTQs | Critical-to-Quality needs, meaning what customers or stakeholders actually care about |
| SIPOC | A simple map of Suppliers, Inputs, Process, Outputs, and Customers |
| DMAIC structure | Define, Measure, Analyze, Improve, and Control plan |
| Root-cause hypotheses | Possible causes using structured reasoning, not random brainstorming |
| Suggested metrics | What to track to understand and improve the process |
| Improvement actions | Specific actions with likely impact |
| Control plan | How to keep the improvement from fading after the first fix |
| Action tracker | Actions, owners, priorities, and status |
| Role-aware summary | A summary adapted for PMs, managers, engineers, quality leads, or executives |

Every generated item is tagged as:

- **supported**: grounded in the input you provided
- **inferred**: a reasonable hypothesis that still needs validation
- **missing**: an evidence gap that should be investigated

This evidence labeling is one of the most important parts of the app. It helps prevent AI output from sounding more certain than it really is.

---

### 2. Analytics Workbench

The Analytics Workbench gives you quantitative tools commonly used in process improvement and quality work.

| Tool area | What it helps with |
|---|---|
| Process Capability | Understand whether a process can meet specification limits using Cp, Cpk, Pp, Ppk, sigma level, and DPMO |
| MSA / Gauge R&R | Check whether measurement variation may be coming from the measurement system itself |
| Hypothesis Testing | Compare means, proportions, paired data, categorical data, or multiple groups |
| SPC Charts | Monitor process stability using I-MR, Xbar-R, and p-charts |
| FMEA | Prioritize risks using severity, occurrence, detection, and RPN |
| Regression | Explore relationships between process variables |
| DOE | Select an experimental-design approach for testing factors systematically |
| Benefits & COPQ | Estimate cost of poor quality, ROI, payback, NPV, and benefit timing |

These tools are meant to support analysis, not to replace statistical judgment. Outputs should be checked by someone who understands the process and the data.

---

### 3. Exports

Lean AI Ops can export project packages in multiple formats:

- PDF
- Word (`.docx`)
- Excel (`.xlsx`)
- HTML
- Markdown

This makes the output easier to share in review meetings, project updates, quality reviews, and improvement workshops.

---

## Why this project matters

Many process-improvement efforts fail before they start because the problem is vague, the data is incomplete, the root causes are assumed too early, or the action plan is not owned by anyone.

Lean AI Ops tries to make the first step easier and more disciplined:

1. structure the problem
2. separate facts from hypotheses
3. identify what evidence is missing
4. propose practical actions
5. define metrics and control points
6. generate a reviewable project package

The benefit is not just faster documentation. The benefit is better thinking, clearer ownership, and more consistent improvement discipline.

---

## How it works

Lean AI Ops has two operating modes:

### With an Anthropic API key

The app can use an Anthropic model to generate richer Lean Six Sigma analysis from your project description.

### Without an API key

The app still works in deterministic fallback mode. This means you can run the demo and generate structured outputs even without any paid API key.

That fallback path is important because it makes the repo easier to test, demo, and evaluate.

---

## Quick start for non-GitHub users

You do not need to understand GitHub deeply to try the app. At a high level:

1. Download or clone this repository.
2. Install Python 3.10 or newer.
3. Open a terminal in the project folder.
4. Install the required packages.
5. Run the Streamlit app.
6. Open the local link that Streamlit shows in your browser.

Commands:

```bash
git clone https://github.com/simaba/lean-ai-ops.git
cd lean-ai-ops
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, this may also work:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

When Streamlit starts, it will show a local URL such as `http://localhost:8501`. Open that link in your browser.

---

## Run the CLI demo

The repository includes a sample project input file at `templates/sample_project.json`.

Run:

```bash
python run_demo.py --input templates/sample_project.json --mode dmaic --audience pm
```

This prints a structured Markdown improvement package in the terminal.

You can also try different modes:

```bash
python run_demo.py --input templates/sample_project.json --mode root_cause --audience quality_lead
python run_demo.py --input templates/sample_project.json --mode process_waste --audience manager
python run_demo.py --input templates/sample_project.json --mode control_plan --audience executive
```

---

## Methodology modes

| Mode | Use when |
|---|---|
| DMAIC | You want a full Define, Measure, Analyze, Improve, Control structure |
| Kaizen | You want fast, practical, low-overhead improvements |
| Root Cause | You want deeper 5 Whys and fishbone-style analysis |
| Process Waste | You want to identify waste using TIMWOODS-style thinking |
| Control Plan | You want monitoring, ownership, cadence, and escalation triggers |

---

## Audience modes

| Audience | Output emphasis |
|---|---|
| Engineer | Process mapping, measurement points, bottlenecks, and instrumentation |
| PM | Stakeholder alignment, action ownership, risks, and next steps |
| Manager | Accountability, top actions, cadence, and unblockers |
| Quality Lead | CTQs, measurement integrity, evidence gaps, and control rigor |
| Executive | Business impact, risk, decision needed, and expected outcome |

---

## Repository structure

```text
app.py                  Streamlit UI entry point
run_demo.py             CLI demo entry point
src/
  models.py             Data models
  engine.py             Assessment orchestration
  phases/               LLM and deterministic assessment logic
  renderers.py          Markdown and HTML renderers
analytics/              Workbench tools for capability, SPC, MSA, FMEA, etc.
storage/                Project persistence
ui/                     UI components
templates/              Input templates including sample_project.json
examples/               Example projects and outputs
tests/                  Analytics and smoke tests
.github/workflows/      CI configuration
```

---

## Current quality guardrails

The repository currently includes:

- deterministic fallback mode when no API key is available
- CI checks for Python imports, tests, and CLI smoke path
- unit tests for analytics modules
- sample project input for repeatable demos
- evidence tags to separate facts, hypotheses, and missing information
- multi-format export support

---

## Current limitations

This is a working prototype, not a finished commercial product.

Known limitations:

- `app.py` still carries too much responsibility and should be modularized further.
- Statistical outputs should be checked by a qualified person before real decisions.
- AI-generated recommendations are structured drafts, not validated findings.
- The tool does not know your organization’s real constraints unless you provide them.
- It does not replace Lean Six Sigma training, Black Belt review, or domain expertise.

---

## Architecture roadmap

The app already works, but the next quality step is to make the architecture easier to maintain and review.

Target direction:

```text
app.py                         Thin Streamlit entry point
ui/
  theme.py                     Styling and visual constants
  layout.py                    Shared page layout
  pages/
    project_wizard.py          Project-input and package-generation flow
    analytics_workbench.py     Statistical tool views
    export_center.py           Export controls and previews
services/
  assessment_service.py        Business logic orchestration
  export_service.py            PDF, DOCX, XLSX, HTML, Markdown export logic
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

---

## Example use cases

- A project manager needs to turn recurring escalation issues into a structured action plan.
- A quality lead wants to frame a process problem before a DMAIC workshop.
- A manager wants a clearer review cadence and control plan after a process fix.
- An engineering team wants to identify where delays and rework are happening.
- A student or practitioner wants to learn how Lean Six Sigma tools connect to real operational problems.

---

## Scope and disclaimer

This repository is shared in a personal capacity. It is not statistical certification, process certification, legal advice, compliance certification, or official Lean Six Sigma training material.

AI-generated outputs should be treated as structured drafts and hypotheses. Validate assumptions, measurements, root causes, statistical interpretations, and improvement actions with real process data and qualified domain experts.

---

## Related repositories

| Repository | Purpose |
|---|---|
| [governance-playbook](https://github.com/simaba/governance-playbook) | End-to-end AI operating model |
| [release-governance](https://github.com/simaba/release-governance) | Risk-based release gates for AI systems |
| [release-checklist](https://github.com/simaba/release-checklist) | CLI validator for YAML-based release readiness |
| [everything-program-management](https://github.com/simaba/everything-program-management) | PM templates, agents, skills, and structured operating artifacts |
| [ai-prism](https://github.com/simaba/ai-prism) | Curated governance resources |

---

*Shared in a personal capacity. Open to collaborations and feedback via [LinkedIn](https://linkedin.com/in/simaba) or [Medium](https://medium.com/@bagheri.sima).*
