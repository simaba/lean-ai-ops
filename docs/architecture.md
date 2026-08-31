# Architecture

Lean AI Ops is organized as a set of explicit contracts with two user-facing interfaces.

## System layers

```text
                         PROJECT CONTEXT
                               |
                               v
                     +-------------------+
                     |   Project intake  |
                     | forms / contracts |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     | Assessment engine |
                     | modes / phases    |
                     +---------+---------+
                               |
             +-----------------+-----------------+
             |                 |                 |
             v                 v                 v
     +---------------+ +---------------+ +------------------+
     | Evidence      | | Analytics     | | Renderers/export |
     | discipline    | | workbench     | | PDF/DOCX/XLSX    |
     +-------+-------+ +-------+-------+ +--------+---------+
             |                 |                  |
             +-----------------+------------------+
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
       +-------------------+       +-------------------+
       | Streamlit runtime |       | GitHub Pages     |
       | real project work |       | public interface |
       +-------------------+       +-------------------+
```

## Working runtime

The Streamlit application is the operational interface for:

- project intake and assessment generation
- deterministic fallback and optional Anthropic-backed generation
- saved project snapshots
- analytics workbench
- tool recommendation and tollgates
- PDF, DOCX, XLSX, HTML, and Markdown export

The shared Streamlit visual system is isolated in `ui/theme.py` so the application entry point does not also own its full styling contract.

## Public interface

`docs/index.html` is a dependency-light static interface for GitHub Pages. It provides orientation and interactive explanation without requiring installation.

Its browser demo is deliberately constrained:

- no AI/API call
- no persistence
- no execution of Python analytics
- no claim that generated hypotheses are validated findings

`docs/project-manifest.json` captures the product capabilities, journeys, evidence states, exports, and interface boundary in a small versioned contract. See `docs/public-interface-contract.md`.

## Core design choices

- structured outputs over free-form advice
- evidence tagging for trustworthiness
- role-aware summaries for different audiences
- reusable project memory for continuity
- statistical functions testable independently of presentation
- explicit separation between demonstration and working runtime
- progressive disclosure for non-technical users

## Evolution direction

The current architecture preserves the working Python implementation while making its interfaces easier to understand and maintain. Further modularization can move page-specific Streamlit code and orchestration into focused UI and service modules without forcing a frontend rewrite.
