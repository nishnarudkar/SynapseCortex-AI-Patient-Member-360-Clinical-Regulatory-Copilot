"""
=============================================================================
SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
File    : app/app.py
Purpose : Production-ready Streamlit in Snowflake application
          Tab 1 — Patient 360 Dashboard  (metrics, medications, encounters, labs)
          Tab 2 — Clinical & Regulatory Copilot (Dual-RAG chat, citations,
                  document drawer, Care Action dispatcher)

Deploy  : Upload this file as a Streamlit in Snowflake app from
          Snowsight → Projects → Streamlit → + Streamlit App
          Set warehouse = SYNAPSE_WH, database = SYNAPSE_HEALTH, schema = APP
=============================================================================
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

# Import the RAG engine from the sibling module.
# In Streamlit in Snowflake, upload both app.py and rag_engine.py;
# the app resolves imports from the same package directory.
from rag_engine import ClinicalCopilot, CopilotResult, Patient360Context, DocumentChunk

# ─────────────────────────────────────────────────────────────────────────────
# Page config  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "SynapseCortex AI",
    page_icon  = "🧠",
    layout     = "wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — clean clinical theme with colour-coded risk tier badges
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts Import ────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* ── Global Typography & Theme ─────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
    color: #1e293b;
}

/* ── Main Container Padding ─────────────────────────────────────────── */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
    max-width: 1380px;
}

/* ── Top Header Bar ─────────────────────────────────────────────────── */
.synapse-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
    padding: 1.4rem 1.8rem;
    border-radius: 16px;
    margin-bottom: 1.6rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25), 0 8px 10px -6px rgba(15, 23, 42, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.synapse-header-left {
    display: flex;
    align-items: center;
    gap: 1.1rem;
}
.synapse-header-icon {
    font-size: 2.3rem;
    background: rgba(255, 255, 255, 0.12);
    width: 54px;
    height: 54px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15);
}
.synapse-header h1 {
    color: #ffffff;
    font-size: 1.7rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.02em;
}
.synapse-header .subtitle {
    color: #38bdf8;
    font-size: 0.86rem;
    font-weight: 500;
    margin-top: 0.15rem;
    letter-spacing: 0.01em;
}
.synapse-header-badges {
    display: flex;
    gap: 0.6rem;
    align-items: center;
}
.synapse-tag {
    background: rgba(255, 255, 255, 0.1);
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 0.35rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    backdrop-filter: blur(6px);
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}
.synapse-tag.active {
    background: rgba(14, 165, 233, 0.25);
    border-color: #38bdf8;
    color: #38bdf8;
}

/* ── Metric Cards ───────────────────────────────────────────────────── */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.25rem 1.3rem 1.1rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.03);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    height: 100%;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    border-radius: 14px 14px 0 0;
}
.metric-card.card-red::before {
    background: linear-gradient(90deg, #ef4444, #f97316);
}
.metric-card.card-amber::before {
    background: linear-gradient(90deg, #f59e0b, #eab308);
}
.metric-card.card-green::before {
    background: linear-gradient(90deg, #10b981, #059669);
}
.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 20px -8px rgba(0, 0, 0, 0.09), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    border-color: #cbd5e1;
}
.metric-card .label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 0.45rem;
}
.metric-card .value {
    font-size: 1.65rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.15;
    letter-spacing: -0.02em;
}
.metric-card .sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.45rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.3rem;
}

/* ── Badge Variants ─────────────────────────────────────────────────── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}
.badge-high  { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.badge-low   { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.badge-gap   { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.badge-nogap { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.badge-alert { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.badge-warn  { background: #fefce8; color: #854d0e; border: 1px solid #fef08a; }

/* ── Section Headers ────────────────────────────────────────────────── */
.section-header {
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 0.45rem;
    margin: 1.4rem 0 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Patient Context Banner (Tab 2) ─────────────────────────────────── */
.patient-banner {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 0.9rem 1.3rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.patient-banner-info {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
}
.patient-banner-sub {
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 500;
}

/* ── Chat Messages ──────────────────────────────────────────────────── */
.chat-user {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 4px solid #0284c7;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin: 0.75rem 0;
    font-size: 0.92rem;
    color: #0f172a;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}
.chat-ai {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin: 0.75rem 0;
    font-size: 0.93rem;
    line-height: 1.65;
    color: #1e293b;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
}
.chat-ai .model-tag {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px dashed #e2e8f0;
    font-weight: 500;
    display: flex;
    justify-content: space-between;
}

/* ── Citation Pill ──────────────────────────────────────────────────── */
.citation {
    background: #e0f2fe;
    border: 1px solid #7dd3fc;
    border-radius: 6px;
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #0369a1;
    font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    margin: 0 0.15rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* ── Care Action Dispatch Box ───────────────────────────────────────── */
.dispatch-box {
    background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
    border: 1px solid #fdba74;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-top: 1.2rem;
    box-shadow: 0 4px 10px -2px rgba(249, 115, 22, 0.12);
}
.dispatch-box .title {
    font-weight: 800;
    color: #c2410c;
    font-size: 0.95rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Chunk Expander Card ────────────────────────────────────────────── */
.chunk-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.chunk-header {
    font-size: 0.78rem;
    font-weight: 700;
    color: #334155;
    margin-bottom: 0.35rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.chunk-text {
    font-size: 0.8rem;
    color: #334155;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.75rem 0.9rem;
    line-height: 1.55;
    max-height: 240px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar Styling ────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
.sidebar-patient-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 1rem;
    margin-top: 0.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
DEMO_QUESTIONS: dict[str, list[str]] = {
    "HERO-PT-001": [
        "Is Metformin contraindicated for this patient given their kidney function?",
        "What does the FDA label say about Metformin and CKD Stage 3?",
        "What is the risk of lactic acidosis for this patient?",
        "What alternative medications should be considered instead of Metformin?",
    ],
    "HERO-PT-002": [
        "What care gaps exist for this diabetic patient?",
        "How long has this patient's HbA1c been overdue and what is the clinical risk?",
        "What is the HEDIS and CMS Star Rating impact of this care gap?",
        "What interventions are recommended to close this care gap?",
    ],
    "HERO-PT-003": [
        "Summarise the drug-drug interactions in this patient's current regimen.",
        "Is carvedilol safe for this patient given their COPD diagnosis?",
        "Why is this patient classified as HIGH RISK and what does that mean?",
        "What complex care management actions are recommended for this patient?",
    ],
    "__default__": [
        "What are the key risk factors for this patient?",
        "Are there any medication safety concerns for this patient?",
        "What care gaps exist for this patient?",
        "Summarise this patient's clinical history.",
    ],
}

CARE_ACTION_CHANNELS = ["Jira Ticket", "Slack Alert", "Email Notification", "PagerDuty"]

# ─────────────────────────────────────────────────────────────────────────────
# Session + cached resources
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to Snowflake…")
def get_session():
    try:
        return get_active_session()
    except Exception:
        import os
        from dotenv import load_dotenv
        from snowflake.snowpark import Session

        load_dotenv()
        params = {
            "account":   os.environ.get("SNOWFLAKE_ACCOUNT", "CNWXSKG-MW91931"),
            "user":      os.environ.get("SNOWFLAKE_USER", "NISHUNARUDKAR"),
            "password":  os.environ.get("SNOWFLAKE_PASSWORD", "Nadunishant@123"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "SYNAPSE_WH"),
            "database":  os.environ.get("SNOWFLAKE_DATABASE", "SYNAPSE_HEALTH"),
            "schema":    os.environ.get("SNOWFLAKE_SCHEMA", "APP"),
            "role":      os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        }
        return Session.builder.configs(params).create()


@st.cache_resource(show_spinner="Initialising Clinical Copilot…")
def get_copilot(_session):
    return ClinicalCopilot(_session)


@st.cache_data(ttl=300, show_spinner="Loading patient list…")
def load_patient_list(_session) -> pd.DataFrame:
    """Return patient_id + display label for the sidebar selector."""
    sql = """
        SELECT
            PATIENT_ID,
            FULL_NAME,
            AGE,
            RISK_TIER,
            CASE
                WHEN PATIENT_ID LIKE 'HERO-PT-001%' THEN '⚠️ Hero 1 – Safety Violation'
                WHEN PATIENT_ID LIKE 'HERO-PT-002%' THEN '⚠️ Hero 2 – Care Gap'
                WHEN PATIENT_ID LIKE 'HERO-PT-003%' THEN '⚠️ Hero 3 – High Risk'
                ELSE NULL
            END AS hero_label
        FROM APP.PATIENT_360_SNAPSHOT
        ORDER BY
            CASE WHEN PATIENT_ID LIKE 'HERO-PT-%' THEN 0 ELSE 1 END,
            PATIENT_ID
    """
    return _session.sql(sql).to_pandas()


@st.cache_data(ttl=120, show_spinner="Loading Patient 360…")
def load_patient_360(_session, patient_id: str) -> dict:
    """Return Patient 360 snapshot row as a plain dict."""
    sql = f"""
        SELECT *
        FROM APP.PATIENT_360_SNAPSHOT
        WHERE PATIENT_ID = '{patient_id}'
        LIMIT 1
    """
    rows = _session.sql(sql).to_pandas()
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


@st.cache_data(ttl=120, show_spinner="Loading encounters…")
def load_encounters(_session, patient_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT
            ENCOUNTER_DATE          AS "Date",
            ENCOUNTER_TYPE          AS "Type",
            FACILITY_NAME           AS "Facility",
            PRIMARY_DX_CODE         AS "Dx Code",
            PRIMARY_DX_DESC         AS "Diagnosis",
            DISCHARGE_STATUS        AS "Discharge Status"
        FROM RAW.ENCOUNTERS
        WHERE PATIENT_ID = '{patient_id}'
        ORDER BY ENCOUNTER_DATE DESC
    """
    return _session.sql(sql).to_pandas()


@st.cache_data(ttl=120, show_spinner="Loading lab results…")
def load_labs(_session, patient_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT
            RESULT_DATE             AS "Result Date",
            LAB_TEST_NAME           AS "Test",
            RESULT_VALUE            AS "Result",
            RESULT_UNIT             AS "Unit",
            REFERENCE_RANGE         AS "Reference Range",
            ABNORMAL_FLAG           AS "Flag",
            RESULT_STATUS           AS "Status",
            PERFORMING_LAB          AS "Lab"
        FROM RAW.LABS
        WHERE PATIENT_ID = '{patient_id}'
        ORDER BY RESULT_DATE DESC
        LIMIT 50
    """
    return _session.sql(sql).to_pandas()


@st.cache_data(ttl=120, show_spinner="Loading claims…")
def load_claims(_session, patient_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT
            CLAIM_DATE              AS "Date",
            CLAIM_TYPE              AS "Type",
            PROCEDURE_DESC          AS "Description",
            DRUG_NAME               AS "Drug",
            BILLED_AMOUNT           AS "Billed ($)",
            PAID_AMOUNT             AS "Paid ($)",
            CLAIM_STATUS            AS "Status"
        FROM RAW.CLAIMS
        WHERE PATIENT_ID = '{patient_id}'
        ORDER BY CLAIM_DATE DESC
        LIMIT 60
    """
    return _session.sql(sql).to_pandas()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def hero_prefix(patient_id: str) -> str:
    for prefix in ("HERO-PT-001", "HERO-PT-002", "HERO-PT-003"):
        if patient_id.startswith(prefix):
            return prefix
    return "__default__"


def risk_badge(risk_tier: str) -> str:
    cls = "badge-high" if risk_tier == "HIGH RISK" else "badge-low"
    icon = "🔴" if risk_tier == "HIGH RISK" else "🟢"
    return f'<span class="badge {cls}">{icon} {risk_tier}</span>'


def gap_badge(gap_status: str) -> str:
    cls = "badge-gap" if gap_status.startswith("GAP") else "badge-nogap"
    icon = "⚠️" if gap_status.startswith("GAP") else "✅"
    return f'<span class="badge {cls}">{icon} {gap_status}</span>'


def drug_flag_badge(flag: str | None) -> str:
    if not flag:
        return '<span class="badge badge-nogap">✅ No Drug Safety Flag</span>'
    cls = "badge-alert" if "ALERT" in flag else "badge-warn"
    icon = "🚨" if "ALERT" in flag else "⚠️"
    return f'<span class="badge {cls}">{icon} {flag}</span>'


def format_currency(val) -> str:
    try:
        return f"${float(val):,.0f}"
    except (TypeError, ValueError):
        return "—"


def highlight_abnormal(row):
    """Pandas styler: red background for abnormal lab flags."""
    flag = str(row.get("Flag", "")).strip()
    if flag in ("H", "L", "HH", "LL", "A"):
        return ["background-color: #fee2e2"] * len(row)
    return [""] * len(row)


def log_care_action(patient_id: str, action_type: str, channel: str, p360: dict) -> dict:
    """Build and return a simulated MCP care-action payload."""
    return {
        "action_type":    action_type,
        "channel":        channel,
        "patient_id":     patient_id,
        "patient_name":   p360.get("FULL_NAME", ""),
        "risk_tier":      p360.get("RISK_TIER", ""),
        "care_gap":       p360.get("CARE_GAP_STATUS", ""),
        "drug_flag":      p360.get("DRUG_SAFETY_FLAG", ""),
        "total_claims":   float(p360.get("TOTAL_CLAIMS_COST", 0)),
        "dispatched_at":  datetime.utcnow().isoformat() + "Z",
        "system":         "SynapseCortex AI",
        "environment":    "Snowflake Cortex / Streamlit in Snowflake",
        "simulated":      True,
    }


def render_citations(answer_text: str) -> str:
    """Wrap [Doc: ..., Page: ...] citation patterns in styled spans."""
    pattern = r'\[Doc:\s*([^\],]+),\s*Page:\s*([^\]]+)\]'
    def replacer(m):
        fname = m.group(1).strip()
        page  = m.group(2).strip()
        return (f'<span class="citation">'
                f'📄 {fname}, p.{page}'
                f'</span>')
    return re.sub(pattern, replacer, answer_text)


# ─────────────────────────────────────────────────────────────────────────────
# Initialise session state
# ─────────────────────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []        # list[dict{role, content, chunks, model}]
if "last_result" not in st.session_state:
    st.session_state.last_result = None       # most recent CopilotResult
if "action_log" not in st.session_state:
    st.session_state.action_log = []          # list of dispatched action payloads
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────────────────────
session  = get_session()
copilot  = get_copilot(session)
pt_list  = load_patient_list(session)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Global patient selector
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 SynapseCortex AI")
    st.markdown("<div style='font-size:0.82rem; color:#64748b; font-weight:600; margin-top:-0.5rem; margin-bottom:0.8rem;'>Clinical Intelligence & Regulatory Copilot</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Build display options: hero patients first, then alphabetical
    def _label(row) -> str:
        if row["hero_label"]:
            return f"{row['hero_label']}  |  {row['FULL_NAME']}"
        return f"{row['FULL_NAME']}  (Age {row['AGE']}, {row['RISK_TIER']})"

    pt_list["_display"] = pt_list.apply(_label, axis=1)
    options = pt_list["PATIENT_ID"].tolist()
    labels  = pt_list["_display"].tolist()

    # Default to first patient (Hero 1)
    default_idx = 0
    if st.session_state.selected_patient in options:
        default_idx = options.index(st.session_state.selected_patient)

    selected_idx = st.selectbox(
        "Select Patient Profile",
        range(len(options)),
        format_func = lambda i: labels[i],
        index       = default_idx,
        key         = "patient_selector",
    )
    selected_patient_id = options[selected_idx]

    # Clear chat when patient changes
    if st.session_state.selected_patient != selected_patient_id:
        st.session_state.chat_history  = []
        st.session_state.last_result   = None
        st.session_state.selected_patient = selected_patient_id

    st.markdown("---")

    # Patient mini-card in sidebar
    p360_row = load_patient_360(session, selected_patient_id)
    if p360_row:
        st.markdown(f"""
        <div class="sidebar-patient-card">
            <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; color:#64748b; letter-spacing:0.06em;">Active Patient Profile</div>
            <div style="font-size:1.05rem; font-weight:800; color:#0f172a; margin-top:0.15rem;">{p360_row.get('FULL_NAME', '—')}</div>
            <div style="font-size:0.8rem; color:#475569; margin-bottom:0.6rem;">Age {p360_row.get('AGE', '—')} · {p360_row.get('GENDER', '—')} · {p360_row.get('INSURANCE_PLAN', '—')}</div>
            <div style="display:flex; flex-direction:column; gap:0.4rem;">
                {risk_badge(p360_row.get("RISK_TIER", "LOW RISK"))}
                {gap_badge(p360_row.get("CARE_GAP_STATUS", "NO GAP"))}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("SynapseCortex AI v1.0  \nSnowflake Cortex · llama3.3-70b  \nNative Clinical Platform · 2026")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="synapse-header">
  <div class="synapse-header-left">
    <div class="synapse-header-icon">🧠</div>
    <div>
      <h1>SynapseCortex AI</h1>
      <div class="subtitle">Patient 360 &amp; Clinical Regulatory Copilot &nbsp;•&nbsp; Powered by Snowflake Cortex AI</div>
    </div>
  </div>
  <div class="synapse-header-badges">
    <span class="synapse-tag active">⚡ Cortex Search</span>
    <span class="synapse-tag">🦙 llama3.3-70b</span>
    <span class="synapse-tag">🔒 Dual-RAG</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_360, tab_copilot = st.tabs([
    "📋  Patient 360 Dashboard",
    "🤖  Clinical & Regulatory Copilot",
])


# =============================================================================
# TAB 1 — PATIENT 360 DASHBOARD
# =============================================================================
with tab_360:
    if not p360_row:
        st.warning("Patient data not found. Run `08_patient_360_and_copilot.sql` first.")
        st.stop()

    # ── Top metric cards ──────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Patient Demographics</div>
            <div class="value">{p360_row.get('AGE', '—')} yrs</div>
            <div class="sub">👤 {p360_row.get('GENDER', '')} · {p360_row.get('INSURANCE_PLAN', '')}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        risk = p360_row.get("RISK_TIER", "LOW RISK")
        risk_color = "#991b1b" if risk == "HIGH RISK" else "#166534"
        card_cls = "card-red" if risk == "HIGH RISK" else "card-green"
        st.markdown(f"""
        <div class="metric-card {card_cls}">
            <div class="label">Risk Stratification</div>
            <div class="value" style="color:{risk_color}; font-size:1.35rem;">
                {"🔴" if risk == "HIGH RISK" else "🟢"} {risk}
            </div>
            <div class="sub">📋 {p360_row.get('CHRONIC_CONDITION_COUNT', 0)} chronic conditions</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Total Claims Cost</div>
            <div class="value">{format_currency(p360_row.get('TOTAL_CLAIMS_COST', 0))}</div>
            <div class="sub">💳 {p360_row.get('CLAIM_COUNT', 0)} claims · last {p360_row.get('LAST_CLAIM_DATE', '—')}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        gap = p360_row.get("CARE_GAP_STATUS", "NO GAP")
        gap_color = "#92400e" if gap.startswith("GAP") else "#166534"
        gap_icon  = "⚠️" if gap.startswith("GAP") else "✅"
        card_cls  = "card-amber" if gap.startswith("GAP") else "card-green"
        st.markdown(f"""
        <div class="metric-card {card_cls}">
            <div class="label">Care Quality Gap</div>
            <div class="value" style="color:{gap_color}; font-size:1.05rem;">
                {gap_icon} {gap}
            </div>
            <div class="sub">🎯 HEDIS NQF-0059 · CMS Star</div>
        </div>""", unsafe_allow_html=True)

    with col5:
        drug_flag = p360_row.get("DRUG_SAFETY_FLAG") or ""
        flag_color = "#991b1b" if "ALERT" in drug_flag else ("#854d0e" if drug_flag else "#166534")
        flag_icon  = "🚨" if "ALERT" in drug_flag else ("⚠️" if drug_flag else "✅")
        flag_text  = drug_flag if drug_flag else "No Drug Safety Flag"
        flag_disp  = (flag_text[:36] + "…") if len(flag_text) > 38 else flag_text
        card_cls   = "card-red" if "ALERT" in drug_flag else ("card-amber" if drug_flag else "card-green")
        st.markdown(f"""
        <div class="metric-card {card_cls}">
            <div class="label">Drug Safety Check</div>
            <div class="value" style="color:{flag_color}; font-size:0.88rem; margin-top:.2rem;">
                {flag_icon} {flag_disp}
            </div>
            <div class="sub">💊 FDA contraindications</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Secondary metrics row ─────────────────────────────────────────────
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Active Medications",
                 p360_row.get("ACTIVE_MEDICATION_COUNT", 0))
    mcol2.metric("Total Encounters",
                 p360_row.get("ENCOUNTER_COUNT", 0),
                 help="All inpatient/outpatient/ED/telehealth visits")
    mcol3.metric("Abnormal Labs",
                 p360_row.get("ABNORMAL_LAB_COUNT", 0),
                 help="Lab results flagged H/L/HH/LL/A")

    hba1c_date = p360_row.get("LAST_HBAC1_DATE") or p360_row.get("LAST_HBA1C_DATE")
    hba1c_val  = p360_row.get("LAST_HBAC1_VALUE") or p360_row.get("LAST_HBA1C_VALUE")
    hba1c_str  = f"{hba1c_val}%" if hba1c_val else "Not on file"
    mcol4.metric("Last HbA1c",
                 hba1c_str,
                 delta = str(hba1c_date) if hba1c_date else "No date on file",
                 delta_color = "off")

    # ── Diagnosis summary ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Active Diagnoses</div>', unsafe_allow_html=True)
    dx_codes = p360_row.get("ALL_DX_CODES") or ""
    dx_descs = p360_row.get("ALL_DX_DESCRIPTIONS") or ""
    if dx_codes:
        codes = [c.strip() for c in dx_codes.split("|") if c.strip()]
        descs = [d.strip() for d in dx_descs.split("|") if d.strip()]
        dx_df = pd.DataFrame({
            "ICD-10 Code":   codes,
            "Description":   descs if len(descs) == len(codes) else ["—"] * len(codes),
        })
        st.dataframe(dx_df, use_container_width=True, hide_index=True)
    else:
        st.info("No diagnoses on record.")

    # ── Active medications ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Active Medications (Paid Pharmacy Claims)</div>',
                unsafe_allow_html=True)
    med_str = p360_row.get("ACTIVE_MEDICATIONS_LIST") or ""
    if med_str:
        meds = [m.strip() for m in med_str.split("|") if m.strip()]
        med_df = pd.DataFrame({"Medication": meds})
        # Flag Metformin for Hero 1 visibility
        def _flag_med(m):
            if "metformin" in m.lower() and p360_row.get("HAS_CKD_DX", 0):
                return ["background-color: #fee2e2"] * len(m)
            return [""] * len(m)
        st.dataframe(
            med_df.style.apply(
                lambda r: ["background-color: #fee2e2"]
                          if "metformin" in str(r.iloc[0]).lower()
                          and p360_row.get("HAS_CKD_DX", 0) else [""],
                axis=1
            ),
            use_container_width=True,
            hide_index=True,
        )
        if p360_row.get("DRUG_SAFETY_FLAG"):
            st.error(f"🚨 {p360_row['DRUG_SAFETY_FLAG']}")
    else:
        st.info("No active pharmacy claims found.")

    # ── Clinical encounters ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Clinical Encounters</div>', unsafe_allow_html=True)
    enc_df = load_encounters(session, selected_patient_id)
    if not enc_df.empty:
        st.dataframe(enc_df, use_container_width=True, hide_index=True)
    else:
        st.info("No encounters on record.")

    # ── Lab history ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Lab Results</div>', unsafe_allow_html=True)
    lab_df = load_labs(session, selected_patient_id)
    if not lab_df.empty:
        st.dataframe(
            lab_df.style.apply(highlight_abnormal, axis=1),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("🟥 Red rows = abnormal flag (H / L / HH / LL / A)")
    else:
        st.info("No lab results on record.")

    # ── Claims history ───────────────────────────────────────────────────
    with st.expander("💰  Claims History", expanded=False):
        claims_df = load_claims(session, selected_patient_id)
        if not claims_df.empty:
            st.dataframe(claims_df, use_container_width=True, hide_index=True)
            total = claims_df["Billed ($)"].sum() if "Billed ($)" in claims_df.columns else 0
            st.caption(f"Total billed (shown): {format_currency(total)}")
        else:
            st.info("No claims on record.")


# =============================================================================
# TAB 2 — CLINICAL & REGULATORY COPILOT
# =============================================================================
with tab_copilot:

    # ── Patient context banner ─────────────────────────────────────────────
    if p360_row:
        st.markdown(f"""
        <div class="patient-banner">
            <div>
                <div class="patient-banner-info">🧑‍⚕️ Clinical Consultation: {p360_row.get('FULL_NAME', selected_patient_id)}</div>
                <div class="patient-banner-sub">Age {p360_row.get('AGE', '—')} · {p360_row.get('GENDER', '—')} · {p360_row.get('INSURANCE_PLAN', '—')} · Patient ID: {selected_patient_id[:22]}…</div>
            </div>
            <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                {risk_badge(p360_row.get("RISK_TIER", "LOW RISK"))}
                {gap_badge(p360_row.get("CARE_GAP_STATUS", "NO GAP"))}
                {drug_flag_badge(p360_row.get("DRUG_SAFETY_FLAG")) if p360_row.get("DRUG_SAFETY_FLAG") else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Demo question buttons ──────────────────────────────────────────────
    prefix   = hero_prefix(selected_patient_id)
    demo_qs  = DEMO_QUESTIONS.get(prefix, DEMO_QUESTIONS["__default__"])

    st.markdown('<div class="section-header">💡 Suggested Clinical Demo Queries</div>', unsafe_allow_html=True)
    btn_cols = st.columns(len(demo_qs))
    triggered_demo_q: str | None = None
    for i, (col, q) in enumerate(zip(btn_cols, demo_qs)):
        short = (q[:42] + "…") if len(q) > 44 else q
        if col.button(short, key=f"demo_q_{i}", help=q, use_container_width=True):
            triggered_demo_q = q

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history display ──────────────────────────────────────────────
    st.markdown('<div class="section-header">💬 Evidence-Grounded Conversation</div>', unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.info("💡 Select a suggested clinical demo question above or type your query below to begin consultation.")
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">👨‍⚕️ <strong>Clinician Question:</strong><br>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                # Render answer with styled citations
                styled_answer = render_citations(msg["content"])
                st.markdown(
                    f'<div class="chat-ai">'
                    f'<div style="font-weight:800; color:#0f172a; font-size:0.95rem; margin-bottom:0.6rem; display:flex; align-items:center; gap:0.4rem;">'
                    f'🧠 <strong>SynapseCortex Clinical Regulatory Copilot</strong>'
                    f'</div>'
                    f'{styled_answer}'
                    f'<div class="model-tag">'
                    f'<span>⚡ Engine: Snowflake Cortex AI ({msg.get("model", "llama3.3-70b")})</span>'
                    f'<span>🔍 {len(msg.get("chunks", []))} evidence document chunk(s) retrieved</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                # ── Document chunk expander ──────────────────────────────
                chunks = msg.get("chunks", [])
                if chunks:
                    with st.expander(
                        f"📄  Retrieved Document Chunks & Evidence ({len(chunks)})",
                        expanded=False,
                    ):
                        for j, chunk in enumerate(chunks, 1):
                            st.markdown(
                                f'<div class="chunk-card">'
                                f'<div class="chunk-header">'
                                f'<span>[{j}] 📄 <strong>{chunk["file_name"]}</strong> (Page {chunk["page_number"]})</span>'
                                f'<span style="background:#e2e8f0; color:#475569; padding:0.15rem 0.5rem; border-radius:12px; font-size:0.7rem;">{chunk["doc_category"]}</span>'
                                f'</div>'
                                f'<div class="chunk-text">{chunk["page_text"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

    # ── Chat input ────────────────────────────────────────────────────────
    user_input = st.chat_input(
        placeholder="Ask a clinical question about this patient…",
        key="copilot_input",
    )

    # Resolve the active query (typed input takes priority over demo button)
    active_query: str | None = user_input or triggered_demo_q

    if active_query:
        # Append user message to history
        st.session_state.chat_history.append({
            "role":    "user",
            "content": active_query,
        })

        with st.spinner("🔍 Retrieving documents and synthesising answer…"):
            result: CopilotResult = copilot.answer(
                patient_id = selected_patient_id,
                user_query = active_query,
            )

        st.session_state.last_result = result

        # Append AI response + serialised chunks
        st.session_state.chat_history.append({
            "role":    "assistant",
            "content": result.answer,
            "model":   result.model_used,
            "chunks":  [
                {
                    "file_name":    c.file_name,
                    "page_number":  c.page_number,
                    "doc_category": c.doc_category,
                    "page_text":    c.page_text,
                }
                for c in result.document_chunks
            ],
        })

        if result.warning:
            st.warning(f"⚠️ Search service warning: {result.warning}")

        # Rerun to render the new messages
        st.rerun()

    # ── Dispatch Care Action ───────────────────────────────────────────────
    st.markdown("---")

    # Show the action panel only when a safety flag or care gap exists
    has_flag = bool(p360_row.get("DRUG_SAFETY_FLAG")) if p360_row else False
    has_gap  = (p360_row.get("CARE_GAP_STATUS", "NO GAP").startswith("GAP")
                if p360_row else False)
    is_high_risk = (p360_row.get("RISK_TIER") == "HIGH RISK") if p360_row else False

    if has_flag or has_gap or is_high_risk:
        st.markdown(
            '<div class="dispatch-box">'
            '<div class="title">🚨 Clinical Action Required</div>',
            unsafe_allow_html=True,
        )
        action_cols = st.columns([2, 2, 1])

        active_alerts = []
        if has_flag:
            active_alerts.append(p360_row["DRUG_SAFETY_FLAG"])
        if has_gap:
            active_alerts.append(p360_row["CARE_GAP_STATUS"])
        if is_high_risk:
            active_alerts.append("HIGH RISK patient – complex care management indicated")

        with action_cols[0]:
            st.markdown("**Detected alerts:**")
            for alert in active_alerts:
                st.markdown(f"• {alert}")

        with action_cols[1]:
            action_type = st.selectbox(
                "Action type",
                ["Pharmacovigilance Review", "Care Gap Outreach",
                 "Complex Case Management Enrolment", "Urgent Clinical Review"],
                key="action_type_select",
            )
            channel = st.selectbox(
                "Dispatch via",
                CARE_ACTION_CHANNELS,
                key="channel_select",
            )

        with action_cols[2]:
            st.markdown("<br>", unsafe_allow_html=True)
            dispatch_clicked = st.button(
                "⚡ Dispatch Care Action",
                type="primary",
                use_container_width=True,
                key="dispatch_btn",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if dispatch_clicked:
            payload = log_care_action(
                patient_id  = selected_patient_id,
                action_type = action_type,
                channel     = channel,
                p360        = p360_row,
            )
            st.session_state.action_log.append(payload)
            st.success(
                f"✅ Care action dispatched via **{channel}** at "
                f"`{payload['dispatched_at']}`"
            )
            with st.expander("📋  Action Payload (MCP Trigger Simulation)", expanded=True):
                st.code(json.dumps(payload, indent=2), language="json")

    else:
        st.info("✅ No immediate care actions required for this patient.")

    # ── Action log history ────────────────────────────────────────────────
    if st.session_state.action_log:
        with st.expander(
            f"📋  Dispatched Actions Log ({len(st.session_state.action_log)})",
            expanded=False,
        ):
            for i, p in enumerate(reversed(st.session_state.action_log), 1):
                st.markdown(
                    f"**{i}.** `{p['dispatched_at']}` · "
                    f"**{p['action_type']}** → **{p['channel']}** · "
                    f"Patient: {p['patient_name']} ({p['patient_id'][:20]}…)"
                )

    # ── Clear chat ────────────────────────────────────────────────────────
    if st.session_state.chat_history:
        if st.button("🗑️  Clear conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.last_result  = None
            st.rerun()
