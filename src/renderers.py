from __future__ import annotations

from src.models import AssessmentResult, EvidenceItem


def _render_items(items: list[EvidenceItem]) -> str:
    return "\n".join(f"- {item.statement} [{item.evidence_tag}]" for item in items)


def render_markdown_summary(result: AssessmentResult) -> str:
    sections = [
        f"# {result.project_name}",
        "",
        f"**Mode:** {result.mode}",
        f"**Audience:** {result.audience}",
        "",
        "## Cleaned-up problem statement",
        result.cleaned_problem_statement,
        "",
        "## Likely CTQs",
        _render_items(result.ctqs),
        "",
        "## SIPOC draft",
        f"- Suppliers: {', '.join(result.sipoc['suppliers'])}",
        f"- Inputs: {', '.join(result.sipoc['inputs'])}",
        f"- Process: {', '.join(result.sipoc['process'])}",
        f"- Outputs: {', '.join(result.sipoc['outputs'])}",
        f"- Customers: {', '.join(result.sipoc['customers'])}",
        "",
        "## DMAIC structure",
    ]

    for phase_name, items in result.dmaic_structure.items():
        sections.append(f"### {phase_name.title()}")
        sections.append(_render_items(items))
        sections.append("")

    sections.extend([
        "## Possible root causes",
        _render_items(result.root_causes),
        "",
        "## Suggested metrics to track",
        _render_items(result.suggested_metrics),
        "",
        "## Suggested improvement actions",
        _render_items(result.improvement_actions),
        "",
        "## Control plan draft",
        _render_items(result.control_plan),
        "",
        "## Action tracker",
    ])

    for row in result.action_tracker:
        sections.append(f"- {row['action']} | owner: {row['owner']} | priority: {row['priority']} | status: {row['status']}")

    sections.extend([
        "",
        "## Project memory",
    ])

    for key, values in result.project_memory.items():
        sections.append(f"### {key.replace('_', ' ').title()}")
        sections.extend(f"- {value}" for value in values)
        sections.append("")

    sections.extend([
        "## Role-aware summary",
        result.role_summary,
    ])

    return "\n".join(sections)
