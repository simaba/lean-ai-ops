from __future__ import annotations

import streamlit as st


_GLOBAL_CSS = r"""

/* ── Fonts & base ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.stApp {
  background: #F1F4FB !important;
}
.main .block-container {
  padding-top: 2.2rem !important;
  padding-bottom: 3rem !important;
  max-width: 1200px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1E1B4B 0%, #16133A 100%) !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] > div:first-child {
  background: transparent !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span,
[data-testid="stSidebar"] .stMarkdown li,
[data-testid="stSidebar"] .stMarkdown h2 {
  color: #CBD5E1 !important;
}
[data-testid="stSidebar"] [data-testid="stCaption"] p {
  color: #64748B !important;
}
[data-testid="stSidebar"] hr {
  border-color: rgba(255,255,255,0.10) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
  color: #CBD5E1 !important;
  background: rgba(255,255,255,0.07) !important;
  border-color: rgba(255,255,255,0.12) !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.10) !important;
  color: #E2E8F0 !important;
  border-color: rgba(255,255,255,0.15) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,0.18) !important;
}
[data-testid="stSidebarCollapseButton"] svg { color: #94A3B8 !important; }

/* ── Primary buttons ───────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #4361EE 0%, #3A0CA3 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 0.95em !important;
  padding: 0.58rem 1.5rem !important;
  box-shadow: 0 4px 16px rgba(67,97,238,0.32) !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease !important;
  letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(67,97,238,0.42) !important;
}
.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
  background: #FFFFFF !important;
  color: #4361EE !important;
  border: 2px solid #4361EE !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
.stButton > button[kind="secondary"]:hover {
  background: #EEF2FF !important;
}

/* ── Form inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
  border: 2px solid #E2E8F0 !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
  font-size: 0.93em !important;
  color: #1E293B !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #4361EE !important;
  box-shadow: 0 0 0 3px rgba(67,97,238,0.12) !important;
  outline: none !important;
}
[data-testid="stWidgetLabel"] p { font-weight: 600 !important; color: #374151 !important; }

/* ── Radio buttons → card-style ────────────────────────────────────────────── */
[data-testid="stRadio"] > div {
  gap: 10px !important;
  flex-wrap: wrap !important;
}
[data-testid="stRadio"] label {
  background: #FFFFFF !important;
  border: 2px solid #E2E8F0 !important;
  border-radius: 12px !important;
  padding: 12px 18px !important;
  cursor: pointer !important;
  transition: border-color 0.18s, background 0.18s !important;
  font-weight: 600 !important;
  flex: 1 1 auto !important;
}
[data-testid="stRadio"] label:hover {
  border-color: #4361EE !important;
  background: #F8FAFF !important;
}
[data-testid="stRadio"] label:has(input:checked) {
  border-color: #4361EE !important;
  background: #EEF2FF !important;
  color: #4361EE !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #FFFFFF !important;
  border-radius: 12px 12px 0 0 !important;
  border-bottom: 2px solid #E2E8F0 !important;
  padding: 8px 12px 0 12px !important;
  gap: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 8px 8px 0 0 !important;
  padding: 10px 20px !important;
  font-weight: 600 !important;
  font-size: 0.88em !important;
  letter-spacing: 0.015em !important;
  color: #64748B !important;
  background: transparent !important;
  border: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: #4361EE !important;
  background: #F0F4FF !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #4361EE !important;
  background: #EEF2FF !important;
  border-bottom: 3px solid #4361EE !important;
}
[data-testid="stTabsContent"] {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  padding: 28px 24px !important;
}

/* ── Metrics ───────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: #FFFFFF !important;
  border-radius: 12px !important;
  padding: 18px 20px !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
}
[data-testid="stMetricValue"] {
  font-size: 2.4em !important;
  font-weight: 800 !important;
  color: #1E1B4B !important;
}
[data-testid="stMetricLabel"] {
  font-size: 0.78em !important;
  font-weight: 700 !important;
  color: #64748B !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

/* ── Expanders ─────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
  background: #FFFFFF !important;
  overflow: hidden !important;
  margin-bottom: 10px !important;
}
[data-testid="stExpander"] summary {
  background: #FFFFFF !important;
  font-weight: 700 !important;
  color: #1E1B4B !important;
  padding: 12px 16px !important;
}
[data-testid="stExpander"] summary:hover { background: #F8FAFF !important; }

/* ── Dataframe ─────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }

/* ── Alerts ────────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  border: none !important;
}

/* ── Download buttons ──────────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
  border-radius: 10px !important;
  font-weight: 700 !important;
  padding: 0.6rem 1.2rem !important;
}

/* ── Evidence badges ───────────────────────────────────────────────────────── */
.ev-supported {
  display:inline-block; background:#DCFCE7; color:#166534;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}
.ev-inferred {
  display:inline-block; background:#FEF9C3; color:#854D0E;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}
.ev-missing {
  display:inline-block; background:#FEE2E2; color:#991B1B;
  padding:2px 10px; border-radius:20px; font-size:0.73em; font-weight:700;
  letter-spacing:0.03em; white-space:nowrap; vertical-align:middle;
}

/* ── Custom cards ──────────────────────────────────────────────────────────── */
.lss-card {
  background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px;
  padding:22px 24px; margin-bottom:16px;
  box-shadow:0 2px 12px rgba(0,0,0,0.05);
}
.lss-card-accent {
  background:#FFFFFF; border-left:4px solid #4361EE;
  border-radius:0 12px 12px 0; padding:18px 22px; margin-bottom:12px;
  box-shadow:0 2px 8px rgba(67,97,238,0.08);
}
.hero-banner {
  background: linear-gradient(135deg, #4361EE 0%, #3A0CA3 100%);
  color: white; border-radius: 16px; padding: 28px 32px; margin-bottom: 28px;
}
.hero-banner h2 { color:white !important; margin:0 0 8px 0; font-size:1.5em; }
.hero-banner p  { color:rgba(255,255,255,0.85) !important; margin:0; font-size:0.95em; }
.phase-define  { border-left:4px solid #3B82F6 !important; }
.phase-measure { border-left:4px solid #8B5CF6 !important; }
.phase-analyze { border-left:4px solid #F59E0B !important; }
.phase-improve { border-left:4px solid #10B981 !important; }
.phase-control { border-left:4px solid #06B6D4 !important; }
.export-card {
  background:#FFFFFF; border:2px solid #E2E8F0; border-radius:14px;
  padding:24px; text-align:center; transition:border-color 0.2s, box-shadow 0.2s;
  height:100%;
}
.export-card:hover { border-color:#4361EE; box-shadow:0 4px 20px rgba(67,97,238,0.12); }
.export-icon { font-size:2.5em; margin-bottom:10px; }
.export-title { font-size:1.05em; font-weight:700; color:#1E1B4B; margin-bottom:6px; }
.export-desc  { font-size:0.84em; color:#64748B; margin-bottom:16px; line-height:1.5; }
.sipoc-table { width:100%; border-collapse:collapse; margin-top:8px; font-size:0.88em; }
.sipoc-table th {
  background:#EEF2FF; color:#4361EE; font-weight:700; padding:10px 12px;
  text-align:left; border:1px solid #C7D2FE; font-size:0.82em; text-transform:uppercase; letter-spacing:0.06em;
}
.sipoc-table td { padding:8px 12px; border:1px solid #E2E8F0; vertical-align:top; color:#374151; }
.sipoc-table tr:nth-child(even) td { background:#F8FAFF; }
.step-badge {
  display:inline-block; background:rgba(67,97,238,0.12); color:#4361EE;
  border-radius:20px; padding:3px 14px; font-size:0.78em; font-weight:700;
  letter-spacing:0.05em; margin-bottom:6px;
}
.signal-item {
  background:#F8FAFF; border-left:3px solid #4361EE; border-radius:0 8px 8px 0;
  padding:10px 14px; margin-bottom:8px; font-size:0.92em; color:#1E293B;
}
.ev-legend {
  display:flex; gap:14px; align-items:center; flex-wrap:wrap;
  background:#F8FAFF; border-radius:8px; padding:10px 14px;
  margin-bottom:16px; font-size:0.82em;
}
"""


def inject_global_styles() -> None:
    """Inject the shared Streamlit visual system."""
    st.markdown("<style>\n" + _GLOBAL_CSS + "\n</style>", unsafe_allow_html=True)
