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
/* ── Global typography ──────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: "Inter", "Helvetica Neue", sans-serif; }

/* ── Top header bar ─────────────────────────────────────────────────── */
.synapse-header {
    background: linear-gradient(135deg, #1a1f71 0%, #2563eb 100%);
    padding: 1.1rem 1.6rem;
    border-radius: 10px;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.synapse-header h1 {
    color: #ffffff;
    font-size: 1.55rem;
    font-weight: 700;
    margin: 0;
}
.synapse-header .subtitle {
    color: #93c5fd;
    font-size: 0.82rem;
    margin: 0;
}

/* ── Metric cards ───────────────────────────────────────────────────── */
.metric-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1.1rem 1.2rem 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    height: 100%;
}
.metric-card .label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: #6b7280;
    margin-bottom: .35rem;
}
.metric-card .value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #111827;
    line-height: 1.1;
}
.metric-card .sub {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-top: .3rem;
}

/* ── Badge variants ─────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: .22rem .65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: .02em;
}
.badge-high  { background:#fee2e2; color:#b91c1c; }
.badge-low   { background:#dcfce7; color:#15803d; }
.badge-gap   { background:#fef3c7; color:#92400e; }
.badge-nogap { background:#dcfce7; color:#15803d; }
.badge-alert { background:#fee2e2; color:#b91c1c; }
.badge-warn  { background:#fef9c3; color:#854d0e; }

/* ── Section headers ────────────────────────────────────────────────── */
.section-header {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .07em;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: .4rem;
    margin: 1.2rem 0 .7rem;
}

/* ── Chat messages ──────────────────────────────────────────────────── */
.chat-user {
    background: #eff6ff;
    border-left: 3px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: .7rem 1rem;
    margin: .5rem 0;
    font-size: 0.9rem;
}
.chat-ai {
    background: #f8fafc;
    border-left: 3px solid #0ea5e9;
    border-radius: 0 8px 8px 0;
    padding: .8rem 1rem;
    margin: .5rem 0;
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
}
.chat-ai .model-tag {
    font-size: 0.68rem;
    color: #94a3b8;
    margin-top: .5rem;
    font-style: italic;
}

/* ── Citation pill ──────────────────────────────────────────────────── */
.citation {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 5px;
    padding: .1rem .4rem;
    font-size: 0.72rem;
    color: #0369a1;
    font-family: monospace;
}

/* ── Action button ──────────────────────────────────────────────────── */
.dispatch-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: .9rem 1.1rem;
    margin-top: 1rem;
}
.dispatch-box .title {
    font-weight: 700;
    color: #c2410c;
    font-size: 0.88rem;
}

/* ── Chunk expander ─────────────────────────────────────────────────── */
.chunk-header {
    font-size: 0.74rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: .25rem;
}
.chunk-text {
    font-size: 0.78rem;
    color: #374151;
    background: #f9fafb;
    border-radius: 6px;
    padding: .6rem .8rem;
    line-height: 1.55;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
}

/* ── Demo question pills ────────────────────────────────────────────── */
.demo-q {
    font-size: 0.81rem;
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
    return get_active_session()


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
    st.markdown("**Patient 360 & Regulatory Copilot**")
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
        "Select Patient",
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
        st.markdown(f"**{p360_row.get('FULL_NAME', '—')}**")
        st.markdown(f"Age {p360_row.get('AGE', '—')} · {p360_row.get('GENDER', '—')}")
        st.markdown(
            risk_badge(p360_row.get("RISK_TIER", "LOW RISK")),
            unsafe_allow_html=True,
        )
        st.markdown(
            gap_badge(p360_row.get("CARE_GAP_STATUS", "NO GAP")),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption("SynapseCortex AI v1.0  \nSnowflake Cortex · llama3.3-70b  \nHackathon Build · Sep 2026")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="synapse-header">
  <div>
    <h1>🧠 SynapseCortex AI</h1>
    <p class="subtitle">Patient 360 &amp; Clinical Regulatory Copilot &nbsp;·&nbsp; Powered by Snowflake Cortex</p>
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
            <div class="label">Age</div>
            <div class="value">{p360_row.get('AGE', '—')}</div>
            <div class="sub">{p360_row.get('GENDER', '')} · {p360_row.get('INSURANCE_PLAN', '')}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        risk = p360_row.get("RISK_TIER", "LOW RISK")
        risk_color = "#b91c1c" if risk == "HIGH RISK" else "#15803d"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Risk Tier</div>
            <div class="value" style="color:{risk_color}; font-size:1.3rem;">
                {"🔴" if risk == "HIGH RISK" else "🟢"} {risk}
            </div>
            <div class="sub">{p360_row.get('CHRONIC_CONDITION_COUNT', 0)} chronic conditions</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Total Claims Cost</div>
            <div class="value">{format_currency(p360_row.get('TOTAL_CLAIMS_COST', 0))}</div>
            <div class="sub">{p360_row.get('CLAIM_COUNT', 0)} claims · last {p360_row.get('LAST_CLAIM_DATE', '—')}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        gap = p360_row.get("CARE_GAP_STATUS", "NO GAP")
        gap_color = "#92400e" if gap.startswith("GAP") else "#15803d"
        gap_icon  = "⚠️" if gap.startswith("GAP") else "✅"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Care Gap</div>
            <div class="value" style="color:{gap_color}; font-size:1.05rem;">
                {gap_icon} {gap}
            </div>
            <div class="sub">HEDIS NQF-0059 · ADA 2026</div>
        </div>""", unsafe_allow_html=True)

    with col5:
        drug_flag = p360_row.get("DRUG_SAFETY_FLAG") or ""
        flag_color = "#b91c1c" if "ALERT" in drug_flag else ("#854d0e" if drug_flag else "#15803d")
        flag_icon  = "🚨" if "ALERT" in drug_flag else ("⚠️" if drug_flag else "✅")
        flag_text  = drug_flag if drug_flag else "No Drug Safety Flag"
        flag_disp  = (flag_text[:38] + "…") if len(flag_text) > 40 else flag_text
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Drug Safety</div>
            <div class="value" style="color:{flag_color}; font-size:0.88rem; margin-top:.3rem;">
                {flag_icon} {flag_disp}
            </div>
            <div class="sub">FDA contraindication check</div>
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
        banner_cols = st.columns([3, 1, 1, 1])
        banner_cols[0].markdown(
            f"**Consulting on:** {p360_row.get('FULL_NAME', selected_patient_id)}"
            f" · Age {p360_row.get('AGE', '—')} · {p360_row.get('INSURANCE_PLAN', '—')}"
        )
        banner_cols[1].markdown(
            risk_badge(p360_row.get("RISK_TIER", "LOW RISK")),
            unsafe_allow_html=True,
        )
        banner_cols[2].markdown(
            gap_badge(p360_row.get("CARE_GAP_STATUS", "NO GAP")),
            unsafe_allow_html=True,
        )
        if p360_row.get("DRUG_SAFETY_FLAG"):
            banner_cols[3].markdown(
                drug_flag_badge(p360_row.get("DRUG_SAFETY_FLAG")),
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Demo question buttons ──────────────────────────────────────────────
    prefix   = hero_prefix(selected_patient_id)
    demo_qs  = DEMO_QUESTIONS.get(prefix, DEMO_QUESTIONS["__default__"])

    st.markdown('<div class="section-header">Quick Demo Questions</div>', unsafe_allow_html=True)
    btn_cols = st.columns(len(demo_qs))
    triggered_demo_q: str | None = None
    for i, (col, q) in enumerate(zip(btn_cols, demo_qs)):
        short = (q[:42] + "…") if len(q) > 44 else q
        if col.button(short, key=f"demo_q_{i}", help=q, use_container_width=True):
            triggered_demo_q = q

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history display ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Conversation</div>', unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                "*No messages yet — select a demo question above or type below.*",
                help="Start by clicking a demo question or entering your own."
            )
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">🧑‍⚕️ <strong>You</strong><br>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                # Render answer with styled citations
                styled_answer = render_citations(msg["content"])
                st.markdown(
                    f'<div class="chat-ai">'
                    f'🤖 <strong>SynapseCortex Copilot</strong><br><br>'
                    f'{styled_answer}'
                    f'<div class="model-tag">Model: {msg.get("model", "llama3.3-70b")} · '
                    f'{len(msg.get("chunks", []))} document chunk(s) retrieved</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                # ── Document chunk expander ──────────────────────────────
                chunks = msg.get("chunks", [])
                if chunks:
                    with st.expander(
                        f"📄  Retrieved Document Chunks ({len(chunks)})",
                        expanded=False,
                    ):
                        for j, chunk in enumerate(chunks, 1):
                            st.markdown(
                                f'<div class="chunk-header">'
                                f'[{j}] {chunk["file_name"]}  ·  '
                                f'Page {chunk["page_number"]}  ·  '
                                f'<em>{chunk["doc_category"]}</em>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f'<div class="chunk-text">{chunk["page_text"]}</div>',
                                unsafe_allow_html=True,
                            )
                            if j < len(chunks):
                                st.markdown("---")

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
