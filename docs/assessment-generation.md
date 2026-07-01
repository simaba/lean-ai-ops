# Assessment Generation Modes

Lean AI Ops can produce a structured assessment in two ways:

| Mode | When it is used | What it means |
|---|---|---|
| `llm` | A configured Anthropic client returns a response that matches the required structure | The assessment was generated from the live model request. Its recommendations still require evidence review and domain validation. |
| `deterministic_fallback` | No API key is configured, the client is unavailable, the live request fails, or the response cannot be parsed into the required structure | The app generated a predictable, evidence-tagged starter package from the project inputs. It is not a live-model result. |

The CLI prints the generation mode before the report. `AssessmentResult` also records `generation_mode`, `model_name`, and `fallback_reason` for callers that want to render provenance in a UI or export.

## Strict live-model mode

Use `--require-llm` when a deterministic fallback would be misleading for your workflow:

```bash
python run_demo.py \
  --input templates/sample_project.json \
  --mode dmaic \
  --audience pm \
  --require-llm
```

In strict mode, the command exits with a concise error when the live model result is unavailable instead of silently substituting fallback output.

## Important limit

A live-model result is still a structured draft. The app's evidence tags distinguish input-supported statements, hypotheses, and missing evidence; they do not validate root causes, statistical conclusions, implementation feasibility, or release decisions.
