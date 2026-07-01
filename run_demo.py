from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.assessment_service import AssessmentGenerationError
from src.engine import run_assessment
from src.models import ProjectInput
from src.renderers import render_markdown_summary


def load_input(path: Path) -> ProjectInput:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectInput(**data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Lean Six Sigma AI copilot demo.")
    parser.add_argument("--input", type=Path, required=True, help="Path to project input JSON")
    parser.add_argument(
        "--mode",
        choices=["dmaic", "kaizen", "root_cause", "process_waste", "control_plan"],
        default="dmaic",
        help="Operating mode",
    )
    parser.add_argument(
        "--audience",
        choices=["engineer", "pm", "manager", "quality_lead", "executive"],
        default="pm",
        help="Audience for summary emphasis",
    )
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail instead of using deterministic fallback when a live model result is unavailable.",
    )
    args = parser.parse_args()

    project = load_input(args.input)
    try:
        result = run_assessment(
            project,
            mode=args.mode,
            audience=args.audience,
            require_llm=args.require_llm,
        )
    except AssessmentGenerationError as exc:
        parser.error(str(exc))

    print(render_markdown_summary(result))


if __name__ == "__main__":
    main()
