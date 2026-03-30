# Architecture

This MVP uses a simple structured pipeline:

1. `run_demo.py` loads a project input JSON file.
2. `src/engine.py` orchestrates the workflow.
3. `src/phases` builds structured Lean Six Sigma outputs.
4. `src/renderers.py` converts the result into readable markdown.

## Core design choices

- structured outputs over free-form advice
- evidence tagging for trustworthiness
- role-aware summaries for different audiences
- reusable project memory for continuity

## Current scope

This is a deterministic starter implementation. It is designed so a real LLM layer can later replace or enhance selected phase builders while preserving the same output structure.
