from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path("saved_reviews")
BASE_DIR.mkdir(exist_ok=True)


def _safe_name(name: str) -> str:
    cleaned = "_".join(name.strip().lower().split())
    return cleaned or "untitled_review"


def save_review_state(project_name: str, payload: dict[str, Any]) -> str:
    path = BASE_DIR / f"{_safe_name(project_name)}_review.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def list_saved_reviews() -> list[str]:
    return sorted(str(path) for path in BASE_DIR.glob("*.json"))


def load_review_state(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    return json.loads(path.read_text(encoding="utf-8"))
