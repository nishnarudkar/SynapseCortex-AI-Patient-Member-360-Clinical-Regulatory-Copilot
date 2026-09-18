"""
=============================================================================
SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
Module  : rag_engine.py
Purpose : Dual-RAG Copilot Engine
          1. Fetches structured Patient 360 context from
             APP.PATIENT_360_SNAPSHOT (structured SQL history)
          2. Executes semantic vector search against
             APP.CLINICAL_DOC_SEARCH (unstructured clinical/FDA documents)
          3. Synthesises both contexts via SNOWFLAKE.CORTEX.COMPLETE
             using llama3.3-70b with strict citation enforcement

Usage:
    # Inside Snowflake Notebook / Streamlit in Snowflake:
    from app.rag_engine import ClinicalCopilot
    from snowflake.snowpark.context import get_active_session

    session = get_active_session()
    copilot = ClinicalCopilot(session)
    result  = copilot.answer(
        patient_id = "HERO-PT-001-xxxxxxxx",
        user_query = "Is this patient's Metformin prescription safe given their lab results?"
    )
    print(result.answer)

    # Standalone (external Python):
    copilot = ClinicalCopilot.from_connection_params({
        "account":   "your_account",
        "user":      "your_user",
        "password":  "your_password",
        "warehouse": "SYNAPSE_WH",
        "database":  "SYNAPSE_HEALTH",
        "schema":    "APP",
        "role":      "SYSADMIN",
    })
    result = copilot.answer(patient_id="HERO-PT-002-xxxxxxxx",
                            user_query="Does this patient have any overdue care gaps?")

Dependencies:
    pip install snowflake-snowpark-python==1.23.0 snowflake-core==0.10.0
=============================================================================
"""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass, field
from typing import Any

# Snowflake Snowpark + Cortex
from snowflake.snowpark import Session
from snowflake.core import Root                # Cortex Search SDK

# Complete import is optional — only used in older SDK versions
# Our _call_complete method uses SQL which works in all environments
try:
    from snowflake.cortex import Complete
except ImportError:
    Complete = None

logger = logging.getLogger(__name__)
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
SNOWFLAKE_DATABASE       = "SYNAPSE_HEALTH"
SNOWFLAKE_SCHEMA_APP     = "APP"
SNOWFLAKE_SCHEMA_TRANS   = "TRANSFORMED"
PATIENT_SNAPSHOT_TABLE   = "APP.PATIENT_360_SNAPSHOT"
CORTEX_SEARCH_SERVICE    = "CLINICAL_DOC_SEARCH"
CORTEX_LLM_MODEL         = "llama3.3-70b"      # confirmed valid in 2025/2026

# Search config
DOC_SEARCH_LIMIT         = 5    # top-k document chunks retrieved per query
DOC_SEARCH_COLUMNS       = [    # all must be in ATTRIBUTES of CLINICAL_DOC_SEARCH
    "file_name",
    "page_number",
    "doc_category",
    "hero_patient",
    "page_text",
]

# LLM config
LLM_TEMPERATURE          = 0.05   # near-zero for deterministic clinical answers
LLM_MAX_TOKENS           = 1024

# ─────────────────────────────────────────────────────────────────────────────
# System prompt  –  strict citation enforcement
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are the SynapseCortex AI Clinical Regulatory Copilot, a precise and "
    "evidence-grounded clinical assistant operating within a Snowflake-native "
    "Patient 360 platform.\n\n"
    "INSTRUCTIONS:\n"
    "1. Synthesize answers STRICTLY using the two provided contexts:\n"
    "   - CONTEXT A: Patient 360 Structured Data (demographics, diagnoses, "
    "medications, labs, claims, risk tier, care gap status).\n"
    "   - CONTEXT B: Clinical Document Chunks (clinical encounter notes and "
    "FDA package inserts retrieved via vector search).\n"
    "2. For EVERY factual claim in your response, append an inline citation "
    "using this exact format:\n"
    "   [Doc: <file_name>, Page: <page_number>]\n"
    "   Use 'Structured Data' as the source name when citing CONTEXT A fields.\n"
    "   Example: The patient's eGFR is 38 mL/min [Doc: Structured Data, Page: N/A], "
    "which places Metformin in the high-risk contraindication zone "
    "[Doc: fda_inserts/fda_insert_METFORMIN.txt, Page: 1].\n"
    "3. If no supporting evidence exists in EITHER context for a claim, "
    "respond with EXACTLY:\n"
    "   Insufficient evidence.\n"
    "4. Do NOT use any prior training knowledge, external guidelines, or "
    "assumptions beyond the two provided contexts.\n"
    "5. Structure your response with:\n"
    "   • A direct answer to the question (1–2 sentences)\n"
    "   • Supporting evidence (bullet points with inline citations)\n"
    "   • Recommended action (if clinically indicated, cited from context)\n"
)

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Patient360Context:
    """Structured data pulled from APP.PATIENT_360_SNAPSHOT for one patient."""
    patient_id:              str
    full_name:               str
    age:                     int
    gender:                  str
    insurance_plan:          str
    active_medications_list: str | None
    active_medication_count: int
    total_claims_cost:       float
    last_hba1c_date:         str | None
    last_hba1c_value:        float | None
    last_egfr_value:         float | None
    last_creatinine_value:   float | None
    all_dx_codes:            str | None
    all_dx_descriptions:     str | None
    chronic_condition_count: int
    encounter_count:         int
    last_encounter_date:     str | None
    has_diabetes_dx:         bool
    has_ckd_dx:              bool
    risk_tier:               str
    care_gap_status:         str
    drug_safety_flag:        str | None
    view_reference_date:     str
    # Optional extended fields (may not be present in all snapshot versions)
    total_lab_results:       int = 0
    claim_count:             int = 0
    last_claim_date:         str | None = None


@dataclass
class DocumentChunk:
    """A single result from the Cortex Search Service."""
    file_name:    str
    page_number:  int
    doc_category: str
    hero_patient: str | None
    page_text:    str


@dataclass
class CopilotResult:
    """Full output bundle returned by ClinicalCopilot.answer()."""
    patient_id:         str
    user_query:         str
    answer:             str
    patient_context:    Patient360Context | None
    document_chunks:    list[DocumentChunk] = field(default_factory=list)
    model_used:         str = CORTEX_LLM_MODEL
    doc_search_query:   str = ""
    warning:            str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Main engine class
# ─────────────────────────────────────────────────────────────────────────────
class ClinicalCopilot:
    """
    Dual-RAG Clinical Copilot for SynapseCortex AI.

    Combines:
    - Arm 1 (Structured RAG): Patient 360 snapshot from Snowflake table
    - Arm 2 (Vector RAG): Cortex Search over clinical notes + FDA inserts
    Then synthesises with CORTEX.COMPLETE (llama3.3-70b) under strict
    citation enforcement.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._root    = Root(session)
        # Pre-build the Cortex Search service handle
        self._search_svc = (
            self._root
            .databases[SNOWFLAKE_DATABASE]
            .schemas[SNOWFLAKE_SCHEMA_APP]
            .cortex_search_services[CORTEX_SEARCH_SERVICE]
        )
        logger.info(
            "ClinicalCopilot initialised | model=%s | search_service=%s",
            CORTEX_LLM_MODEL, CORTEX_SEARCH_SERVICE,
        )

    # ── Factory ──────────────────────────────────────────────────────────────
    @classmethod
    def from_connection_params(cls, params: dict[str, str]) -> "ClinicalCopilot":
        """Create a ClinicalCopilot from an explicit connection parameter dict."""
        session = Session.builder.configs(params).create()
        return cls(session)

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def answer(
        self,
        patient_id:    str,
        user_query:    str,
        doc_filter:    dict | None = None,
        search_limit:  int         = DOC_SEARCH_LIMIT,
    ) -> CopilotResult:
        """
        Execute the full Dual-RAG pipeline for a clinical question.

        Parameters
        ----------
        patient_id   : str   – PATIENT_ID from RAW.PATIENTS / APP.PATIENT_360_SNAPSHOT
        user_query   : str   – Free-text clinical question from the user/clinician
        doc_filter   : dict  – Optional Cortex Search filter (e.g. restrict to
                               fda_inserts or a specific hero_patient). If None,
                               the engine builds a contextual filter automatically.
        search_limit : int   – Max document chunks to retrieve (default 5)

        Returns
        -------
        CopilotResult with .answer (str) and full audit trail
        """
        logger.info("Copilot request | patient=%s | query=%r", patient_id, user_query[:80])

        # ── Step 1: Retrieve structured Patient 360 context ─────────────────
        p360 = self._fetch_patient_360(patient_id)
        if p360 is None:
            return CopilotResult(
                patient_id   = patient_id,
                user_query   = user_query,
                answer       = "Insufficient evidence.",
                patient_context = None,
                warning      = f"Patient '{patient_id}' not found in APP.PATIENT_360_SNAPSHOT.",
            )

        # ── Step 2: Build search query enriched with patient context ─────────
        enriched_search_query = self._build_search_query(user_query, p360)

        # ── Step 3: Retrieve document chunks from Cortex Search ──────────────
        resolved_filter = doc_filter or self._build_doc_filter(p360)
        chunks, search_warning = self._retrieve_document_chunks(
            query       = enriched_search_query,
            doc_filter  = resolved_filter,
            limit       = search_limit,
        )

        # ── Step 4: Assemble the dual-context prompt ─────────────────────────
        messages = self._build_messages(
            user_query = user_query,
            p360       = p360,
            chunks     = chunks,
        )

        # ── Step 5: Call CORTEX.COMPLETE ─────────────────────────────────────
        answer_text = self._call_complete(messages)

        return CopilotResult(
            patient_id       = patient_id,
            user_query       = user_query,
            answer           = answer_text,
            patient_context  = p360,
            document_chunks  = chunks,
            model_used       = CORTEX_LLM_MODEL,
            doc_search_query = enriched_search_query,
            warning          = search_warning,
        )

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    # ── Step 1: Patient 360 lookup ───────────────────────────────────────────
    def _fetch_patient_360(self, patient_id: str) -> Patient360Context | None:
        """
        Query APP.PATIENT_360_SNAPSHOT for a single patient.
        Returns None if the patient is not found.
        """
        sql = f"""
            SELECT
                PATIENT_ID,
                FULL_NAME,
                AGE,
                GENDER,
                INSURANCE_PLAN,
                ACTIVE_MEDICATIONS_LIST,
                ACTIVE_MEDICATION_COUNT,
                TOTAL_CLAIMS_COST,
                TO_VARCHAR(LAST_HBA1C_DATE)         AS LAST_HBA1C_DATE,
                LAST_HBA1C_VALUE,
                LAST_EGFR_VALUE,
                LAST_CREATININE_VALUE,
                ALL_DX_CODES,
                ALL_DX_DESCRIPTIONS,
                CHRONIC_CONDITION_COUNT,
                ENCOUNTER_COUNT,
                TO_VARCHAR(LAST_ENCOUNTER_DATE)     AS LAST_ENCOUNTER_DATE,
                HAS_DIABETES_DX,
                HAS_CKD_DX,
                RISK_TIER,
                CARE_GAP_STATUS,
                DRUG_SAFETY_FLAG,
                TO_VARCHAR(VIEW_REFERENCE_DATE)     AS VIEW_REFERENCE_DATE,
                COALESCE(TOTAL_LAB_RESULTS, 0)      AS TOTAL_LAB_RESULTS,
                COALESCE(CLAIM_COUNT, 0)            AS CLAIM_COUNT,
                TO_VARCHAR(LAST_CLAIM_DATE)         AS LAST_CLAIM_DATE
            FROM {PATIENT_SNAPSHOT_TABLE}
            WHERE PATIENT_ID = '{patient_id}'
            LIMIT 1
        """
        rows = self._session.sql(sql).collect()
        if not rows:
            logger.warning("Patient not found in snapshot: %s", patient_id)
            return None

        r = rows[0].as_dict()
        return Patient360Context(
            patient_id              = r["PATIENT_ID"],
            full_name               = r["FULL_NAME"]               or "",
            age                     = int(r["AGE"]                 or 0),
            gender                  = r["GENDER"]                  or "",
            insurance_plan          = r["INSURANCE_PLAN"]          or "",
            active_medications_list = r["ACTIVE_MEDICATIONS_LIST"],
            active_medication_count = int(r["ACTIVE_MEDICATION_COUNT"] or 0),
            total_claims_cost       = float(r["TOTAL_CLAIMS_COST"] or 0),
            last_hba1c_date         = r["LAST_HBA1C_DATE"],
            last_hba1c_value        = float(r["LAST_HBA1C_VALUE"]) if r["LAST_HBA1C_VALUE"] else None,
            last_egfr_value         = float(r["LAST_EGFR_VALUE"])  if r["LAST_EGFR_VALUE"]  else None,
            last_creatinine_value   = float(r["LAST_CREATININE_VALUE"]) if r["LAST_CREATININE_VALUE"] else None,
            all_dx_codes            = r["ALL_DX_CODES"],
            all_dx_descriptions     = r["ALL_DX_DESCRIPTIONS"],
            chronic_condition_count = int(r["CHRONIC_CONDITION_COUNT"] or 0),
            encounter_count         = int(r["ENCOUNTER_COUNT"]     or 0),
            last_encounter_date     = r["LAST_ENCOUNTER_DATE"],
            has_diabetes_dx         = bool(r["HAS_DIABETES_DX"]),
            has_ckd_dx              = bool(r["HAS_CKD_DX"]),
            risk_tier               = r["RISK_TIER"]               or "LOW RISK",
            care_gap_status         = r["CARE_GAP_STATUS"]         or "NO GAP",
            drug_safety_flag        = r["DRUG_SAFETY_FLAG"],
            view_reference_date     = r["VIEW_REFERENCE_DATE"]     or "",
            total_lab_results       = int(r.get("TOTAL_LAB_RESULTS") or 0),
            claim_count             = int(r.get("CLAIM_COUNT") or 0),
            last_claim_date         = r.get("LAST_CLAIM_DATE"),
        )

    # ── Step 2: Enrich search query with patient clinical context ────────────
    @staticmethod
    def _build_search_query(user_query: str, p360: Patient360Context) -> str:
        """
        Append key patient clinical signals to the user query so that the
        Cortex Search vector retrieval is grounded in the patient's actual context.
        """
        signals: list[str] = [user_query.strip()]

        if p360.all_dx_codes:
            signals.append(p360.all_dx_codes.replace(" | ", " "))
        if p360.active_medications_list:
            # include only the first 3 drugs to keep the query focused
            drugs = p360.active_medications_list.split(" | ")[:3]
            signals.append(" ".join(d.split()[0] for d in drugs))   # drug name only
        if p360.last_egfr_value is not None:
            signals.append(f"eGFR {p360.last_egfr_value}")
        if p360.care_gap_status != "NO GAP":
            signals.append("care gap HbA1c monitoring")
        if p360.drug_safety_flag:
            signals.append("drug safety contraindication")

        enriched = " ".join(signals)
        logger.debug("Enriched search query: %r", enriched[:200])
        return enriched

    # ── Step 3a: Build doc filter from patient context ────────────────────────
    @staticmethod
    def _build_doc_filter(p360: Patient360Context) -> dict | None:
        """
        Derive a Cortex Search filter from the patient's hero_patient tag.
        Falls back to None (no filter = search all documents) when the patient
        is not a hero case — this is the safe default for synthetic background
        patients.
        """
        hero_map = {
            "HERO-PT-001": "HERO-PT-001",
            "HERO-PT-002": "HERO-PT-002",
            "HERO-PT-003": "HERO-PT-003",
        }
        # Check if any hero prefix matches the patient_id
        for prefix, tag in hero_map.items():
            if p360.patient_id.startswith(prefix):
                # Retrieve both the patient-specific docs AND fda_inserts (always useful)
                return {
                    "@or": [
                        {"@eq": {"hero_patient": tag}},
                        {"@eq": {"doc_category": "fda_insert"}},
                    ]
                }
        # Non-hero patient: search all documents without restriction
        return None

    # ── Step 3b: Execute Cortex Search ──────────────────────────────────────
    def _retrieve_document_chunks(
        self,
        query:      str,
        doc_filter: dict | None,
        limit:      int,
    ) -> tuple[list[DocumentChunk], str | None]:
        """
        Call APP.CLINICAL_DOC_SEARCH and return a list of DocumentChunk objects.
        """
        try:
            search_kwargs: dict[str, Any] = {
                "query":   query,
                "columns": DOC_SEARCH_COLUMNS,
                "limit":   limit,
            }
            if doc_filter:
                search_kwargs["filter"] = doc_filter

            result = self._search_svc.search(**search_kwargs)

            chunks = [
                DocumentChunk(
                    file_name    = row["file_name"],
                    page_number  = int(row.get("page_number", 1)),
                    doc_category = row.get("doc_category", ""),
                    hero_patient = row.get("hero_patient"),
                    page_text    = row["page_text"],
                )
                for row in result.results
            ]
            warning = getattr(result, 'warning', None)  # attribute varies by SDK version
            logger.info(
                "Cortex Search returned %d chunks (warning=%s)",
                len(chunks), warning,
            )
            return chunks, warning

        except Exception as exc:
            logger.error("Cortex Search failed: %s", exc, exc_info=True)
            return [], f"Document search unavailable: {exc}"

    # ── Step 4: Assemble dual-context messages array ─────────────────────────
    @staticmethod
    def _build_messages(
        user_query: str,
        p360:       Patient360Context,
        chunks:     list[DocumentChunk],
    ) -> list[dict[str, str]]:
        """
        Build the messages array for CORTEX.COMPLETE.

        Structure:
          [system]  → strict citation system prompt
          [user]    → CONTEXT A (structured Patient 360)
                      CONTEXT B (document chunks)
                      QUESTION
        """
        # ── CONTEXT A: Structured Patient 360 ─────────────────────────────
        context_a = textwrap.dedent(f"""
            CONTEXT A – Patient 360 Structured Data
            ========================================
            Patient ID        : {p360.patient_id}
            Name              : {p360.full_name}
            Age               : {p360.age}
            Gender            : {p360.gender}
            Insurance         : {p360.insurance_plan}

            --- Diagnoses ---
            ICD-10 Codes      : {p360.all_dx_codes or 'None recorded'}
            Descriptions      : {p360.all_dx_descriptions or 'None recorded'}
            Chronic Conditions: {p360.chronic_condition_count} active

            --- Medications ---
            Active Rx Count   : {p360.active_medication_count}
            Active Medications: {p360.active_medications_list or 'None recorded'}

            --- Lab Results ---
            Last HbA1c Date   : {p360.last_hba1c_date  or 'Not on file'}
            Last HbA1c Value  : {f"{p360.last_hba1c_value}%" if p360.last_hba1c_value else 'Not on file'}
            Last eGFR         : {f"{p360.last_egfr_value} mL/min" if p360.last_egfr_value else 'Not on file'}
            Last Creatinine   : {f"{p360.last_creatinine_value} mg/dL" if p360.last_creatinine_value else 'Not on file'}
            Total Lab Results : {p360.total_lab_results}

            --- Claims & Cost ---
            Total Billed Cost : ${p360.total_claims_cost:,.2f}
            Total Claims      : {p360.claim_count}
            Last Claim Date   : {p360.last_claim_date or 'N/A'}

            --- Encounters ---
            Total Encounters  : {p360.encounter_count}
            Last Visit        : {p360.last_encounter_date or 'N/A'}

            --- AI-Derived Flags (Reference Date: {p360.view_reference_date}) ---
            Risk Tier         : {p360.risk_tier}
            Care Gap Status   : {p360.care_gap_status}
            Drug Safety Flag  : {p360.drug_safety_flag or 'None'}
        """).strip()

        # ── CONTEXT B: Document chunks from Cortex Search ─────────────────
        if chunks:
            doc_sections = []
            for i, chunk in enumerate(chunks, start=1):
                doc_sections.append(
                    f"[Chunk {i}] "
                    f"File: {chunk.file_name} | "
                    f"Page: {chunk.page_number} | "
                    f"Category: {chunk.doc_category}\n"
                    f"{chunk.page_text.strip()}"
                )
            context_b = (
                "CONTEXT B – Clinical Document Chunks (vector search results)\n"
                "=============================================================\n"
                + "\n\n---\n\n".join(doc_sections)
            )
        else:
            context_b = (
                "CONTEXT B – Clinical Document Chunks\n"
                "=====================================\n"
                "No relevant document chunks retrieved."
            )

        # ── Assemble user message ─────────────────────────────────────────
        user_content = (
            f"{context_a}\n\n"
            f"{context_b}\n\n"
            f"QUESTION\n"
            f"========\n"
            f"{user_query.strip()}"
        )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

    # ── Step 5: Call CORTEX.COMPLETE ─────────────────────────────────────────
    def _call_complete(self, messages: list[dict[str, str]]) -> str:
        """
        Invoke SNOWFLAKE.CORTEX.COMPLETE via SQL (works with all auth methods).
        Returns the assistant's response as a plain string.
        """
        import json as _json

        logger.info(
            "Calling CORTEX.COMPLETE | model=%s | prompt_chars=%d",
            CORTEX_LLM_MODEL,
            sum(len(m["content"]) for m in messages),
        )
        try:
            # Serialize messages to JSON string for the SQL call
            messages_json = _json.dumps(messages, ensure_ascii=False)
            # Escape single quotes for SQL string literal
            messages_escaped = messages_json.replace("'", "\\'")

            sql = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    '{CORTEX_LLM_MODEL}',
                    PARSE_JSON($${messages_json}$$),
                    {{
                        'temperature': {LLM_TEMPERATURE},
                        'max_tokens': {LLM_MAX_TOKENS}
                    }}
                ) AS answer
            """
            rows = self._session.sql(sql).collect()
            if rows and rows[0]["ANSWER"]:
                result = str(rows[0]["ANSWER"]).strip()
                # The SQL CORTEX.COMPLETE returns a JSON string — extract the message text
                try:
                    parsed = _json.loads(result)
                    # Standard response shape: {"choices": [{"messages": "<text>"}]}
                    result = parsed["choices"][0].get("messages", result)
                except (KeyError, IndexError, TypeError, _json.JSONDecodeError):
                    # If it's already plain text or unexpected shape, use as-is
                    if result.startswith('"') and result.endswith('"'):
                        result = _json.loads(result)
                logger.info("CORTEX.COMPLETE returned %d chars", len(result))
                return result.strip()
            return "Insufficient evidence."

        except Exception as exc:
            logger.error("CORTEX.COMPLETE failed: %s", exc, exc_info=True)
            return "Insufficient evidence."


# =============================================================================
# Convenience wrapper: pretty-print a CopilotResult
# =============================================================================
def print_result(result: CopilotResult) -> None:
    """Pretty-print a CopilotResult to stdout."""
    divider = "=" * 80
    print(divider)
    print(f"SynapseCortex AI Clinical Regulatory Copilot")
    print(divider)
    print(f"Patient ID   : {result.patient_id}")
    print(f"Question     : {result.user_query}")
    print(f"Model        : {result.model_used}")
    if result.warning:
        print(f"WARNING      : {result.warning}")
    print()

    if result.patient_context:
        p = result.patient_context
        print(f"Patient      : {p.full_name} | Age {p.age} | {p.gender}")
        print(f"Risk Tier    : {p.risk_tier}")
        print(f"Care Gap     : {p.care_gap_status}")
        if p.drug_safety_flag:
            print(f"Drug Flag    : {p.drug_safety_flag}")
    print()

    print(f"Documents retrieved : {len(result.document_chunks)}")
    for i, c in enumerate(result.document_chunks, 1):
        print(f"  [{i}] {c.file_name} (page {c.page_number})")
    print()

    print("-" * 80)
    print("COPILOT ANSWER")
    print("-" * 80)
    print(result.answer)
    print(divider)


# =============================================================================
# Demo entry point
# =============================================================================
if __name__ == "__main__":
    """
    Run a quick three-hero demo from outside Snowflake (requires a valid
    connection_params dict or environment variables).

    Environment variables (alternative to hardcoding):
        SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
        SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_ROLE
    """
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    # Load .env from project root (one level up from app/)
    load_dotenv(Path(__file__).parent.parent / ".env")

    connection_params = {
        "account":   os.environ.get("SNOWFLAKE_ACCOUNT",   "your_account_here"),
        "user":      os.environ.get("SNOWFLAKE_USER",      "your_user_here"),
        "password":  os.environ.get("SNOWFLAKE_PASSWORD",  "your_password_here"),
        "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "SYNAPSE_WH"),
        "database":  os.environ.get("SNOWFLAKE_DATABASE",  "SYNAPSE_HEALTH"),
        "schema":    os.environ.get("SNOWFLAKE_SCHEMA",    "APP"),
        "role":      os.environ.get("SNOWFLAKE_ROLE",      "ACCOUNTADMIN"),
    }

    copilot = ClinicalCopilot.from_connection_params(connection_params)

    # ── Hero 1: Safety Violation ──────────────────────────────────────────
    # Fetch the actual hero patient ID from the snapshot
    session = copilot._session
    hero_ids = {
        row["PATIENT_ID"]: row["RISK_TIER"]
        for row in session.sql(
            "SELECT PATIENT_ID, RISK_TIER FROM APP.PATIENT_360_SNAPSHOT "
            "WHERE PATIENT_ID LIKE 'HERO-PT-%' ORDER BY PATIENT_ID"
        ).collect()
    }

    DEMO_CASES = [
        {
            "patient_id": next(
                (k for k in hero_ids if k.startswith("HERO-PT-001")), "HERO-PT-001"
            ),
            "user_query": (
                "Is this patient's current Metformin prescription safe "
                "given their kidney function test results? What does the "
                "FDA label say about this combination?"
            ),
        },
        {
            "patient_id": next(
                (k for k in hero_ids if k.startswith("HERO-PT-002")), "HERO-PT-002"
            ),
            "user_query": (
                "What care gaps exist for this diabetic patient and what "
                "is the clinical and payer impact of not completing the "
                "overdue lab test?"
            ),
        },
        {
            "patient_id": next(
                (k for k in hero_ids if k.startswith("HERO-PT-003")), "HERO-PT-003"
            ),
            "user_query": (
                "Summarise this high-risk patient's drug-drug interactions "
                "and flag any medications that are potentially unsafe given "
                "their COPD and CKD diagnoses."
            ),
        },
    ]

    for case in DEMO_CASES:
        result = copilot.answer(
            patient_id = case["patient_id"],
            user_query = case["user_query"],
        )
        print_result(result)
        print()
