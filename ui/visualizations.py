from __future__ import annotations

import altair as alt
import pandas as pd
from src.models import ProjectInput


def plot_control_chart(metrics: dict[str, float]) -> alt.Chart:
    data = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
    return alt.Chart(data).mark_line().encode(
        x='Metric:N',
        y='Value:Q',
        color='Metric:N',
    ).properties(title='Control Chart')


def plot_pareto_chart(issues: dict[str, float]) -> alt.Chart:
    data = pd.DataFrame(list(issues.items()), columns=["Issue", "Frequency"])
    data['Cumulative'] = data['Frequency'].cumsum() / data['Frequency'].sum() * 100
    return alt.Chart(data).mark_bar().encode(
        x='Frequency:Q',
        y='Issue:N',
        color='Issue:N',
    ).properties(title='Pareto Chart').interactive()


def plot_impact_vs_effort(actions: list[dict[str, Any]]) -> alt.Chart:
    data = pd.DataFrame(actions)
    return alt.Chart(data).mark_circle(size=100).encode(
        x='effort:Q',
        y='impact:Q',
        color='priority:N',
        tooltip=['action:N', 'effort:Q', 'impact:Q', 'priority:N']
    ).properties(title='Impact vs Effort Matrix')


def plot_trend_line(metrics: dict[str, float]) -> alt.Chart:
    data = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
    return alt.Chart(data).mark_line().encode(
        x='Metric:N',
        y='Value:Q',
        color='Metric:N',
    ).properties(title='Metric Trend Line')
