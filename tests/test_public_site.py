from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_public_site_required_assets_exist() -> None:
    required = [
        DOCS / "index.html",
        DOCS / "assets" / "styles.css",
        DOCS / "assets" / "app.js",
        DOCS / "project-manifest.json",
        DOCS / "data" / "sample-project.json",
        DOCS / ".nojekyll",
    ]
    assert all(path.exists() for path in required)


def test_public_site_contract_sections_are_present() -> None:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    for section_id in ("home", "workspace", "demo", "tools", "architecture", "learn"):
        assert f'id="{section_id}"' in html
    assert "does not call an AI service" in html
    assert "Runs entirely in this page" in html
    assert "Full assessment generation remains in the Python application" in html


def test_project_manifest_is_valid_and_matches_product_contract() -> None:
    manifest = json.loads((DOCS / "project-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["project"]["repository"] == "simaba/lean-ai-ops"
    assert manifest["journeys"]["dmaic"] == [
        "Define",
        "Measure",
        "Analyze",
        "Improve",
        "Control",
    ]
    assert set(manifest["evidence_states"]) == {"supported", "inferred", "missing"}
    assert {"pdf", "docx", "xlsx", "html", "markdown"}.issubset(manifest["exports"])


def test_sample_project_is_explicitly_demo_data() -> None:
    sample = json.loads((DOCS / "data" / "sample-project.json").read_text(encoding="utf-8"))
    assert sample["project_name"] == "Supplier Change Request Intake"
    assert "demo" in sample["notice"].lower()
    assert "validated findings" in sample["notice"].lower()


def test_static_asset_references_are_local_and_present() -> None:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'href="assets/styles.css"' in html
    assert 'src="assets/app.js"' in html
    assert (DOCS / "assets" / "styles.css").stat().st_size > 1000
    assert (DOCS / "assets" / "app.js").stat().st_size > 1000
