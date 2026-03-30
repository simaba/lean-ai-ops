from __future__ import annotations

from typing import Iterable


def build_briefing_html(
    project_name: str,
    leadership_summary: Iterable[str],
    status_narrative: str,
    top_actions: Iterable[str],
    top_risks: Iterable[str],
) -> str:
    summary_html = "".join(f"<li>{item}</li>" for item in leadership_summary)
    actions_html = "".join(f"<li>{item}</li>" for item in top_actions)
    risks_html = "".join(f"<li>{item}</li>" for item in top_risks)
    return f"""
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <title>{project_name} - Executive Briefing</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #0f172a; }}
    h1 {{ margin-bottom: 6px; }}
    .sub {{ color: #475569; margin-bottom: 24px; }}
    .card {{ border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px 18px; margin-bottom: 18px; }}
    .title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
  </style>
</head>
<body>
  <h1>{project_name}</h1>
  <div class='sub'>Executive briefing export</div>

  <div class='card'>
    <div class='title'>Status narrative</div>
    <div>{status_narrative}</div>
  </div>

  <div class='card'>
    <div class='title'>Leadership summary</div>
    <ul>{summary_html}</ul>
  </div>

  <div class='card'>
    <div class='title'>Top actions</div>
    <ul>{actions_html}</ul>
  </div>

  <div class='card'>
    <div class='title'>Top risks</div>
    <ul>{risks_html}</ul>
  </div>
</body>
</html>
"""
