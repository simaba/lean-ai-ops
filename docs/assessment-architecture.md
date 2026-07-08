# Assessment Generation Boundary

## Supported entry point

Use `src.engine.run_assessment()` for every application, CLI, test, or integration call that produces an assessment.

```python
from src.engine import run_assessment

result = run_assessment(project, mode="dmaic", audience="pm")
```

The engine delegates to `src.assessment_service.run_assessment_with_provenance()`. Every returned `AssessmentResult` records one of two modes:

- `llm`: a live model response was parsed into the required assessment structure.
- `deterministic_fallback`: a predictable local starter assessment was used, with a safe reason explaining why.

Set `require_llm=True` when deterministic fallback would be misleading; the call then raises a concise `AssessmentGenerationError` instead of returning fallback output.

## Boundary rule

The phase module contains low-level prompt, parsing, and deterministic-fallback helpers. It is not an application-facing generation API. New code must not call phase-level model-generation helpers directly, because that would bypass provenance and strict-mode behavior.

## Review rule

A regression test verifies that the supported engine is wired to the provenance-aware service and does not import or call the legacy phase-level generator. This preserves the intended public behavior while allowing the lower-level helper module to be refactored separately.
