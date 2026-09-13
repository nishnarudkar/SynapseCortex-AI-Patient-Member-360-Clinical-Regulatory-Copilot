<div align="center">

# 🧠 SynapseCortex AI
### Patient 360 & Clinical Regulatory Copilot

*A Snowflake-native clinical intelligence platform that unifies structured EHR data, unstructured clinical documents, and generative AI into a single, production-ready application.*

[![Snowflake](https://img.shields.io/badge/Snowflake-Cortex%20AI-29B5E8?logo=snowflake&logoColor=white)](https://www.snowflake.com/en/data-cloud/cortex/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-in%20Snowflake-FF4B4B?logo=streamlit&logoColor=white)](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
[![LLM](https://img.shields.io/badge/LLM-llama3.3--70b-blueviolet)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Hackathon:** Snowflake AI Data Engineering — Patient 360 & Clinical Copilot &nbsp;|&nbsp; **Status:** ✅ Full Pipeline Implemented

</div>

---

## Overview

SynapseCortex AI answers three clinical questions that drive real-world healthcare outcomes:

| Question | How SynapseCortex answers it |
|---|---|
| *Is this patient's medication safe?* | Drug–disease contraindication detection via FDA package inserts + structured lab data |
| *Is this patient missing a required quality measure?* | HEDIS NQF-0059 care gap detection with CMS Star Rating impact scoring |
| *Which patients are highest risk and need immediate intervention?* | Deterministic risk stratification over claims cost + age + chronic condition burden |

It does this by combining three pillars built entirely on Snowflake:

- **Patient 360 View** — A longitudinal record joining `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, and `LABS` with deterministic risk and care gap logic applied in SQL.
- **Cortex Document Intelligence** — Eight clinical notes and FDA package inserts parsed with `AI_PARSE_DOCUMENT` (LAYOUT mode) and indexed in a `CORTEX SEARCH SERVICE` for hybrid semantic + lexical retrieval.
- **Dual-RAG Clinical Copilot** — A `llama3.3-70b`-powered assistant that synthesises structured Patient 360 context (Arm 1) with vector-searched document chunks (Arm 2) under a strict citation protocol: every factual claim must reference `[Doc: <file>, Page: <n>]`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SYNAPSE_HEALTH  (Snowflake Database)               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  RAW  (landing zone – immutable)                                     │   │
│  │  PATIENTS · ENCOUNTERS · CLAIMS · LABS     ←  CSV bulk load          │   │
│  │  @CLINICAL_STAGE (SNOWFLAKE_SSE)           ←  PUT clinical docs       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  AI_PARSE_DOCUMENT (LAYOUT)                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TRANSFORMED  (enriched layer)                                       │   │
│  │  PARSED_CLINICAL_DOCS   ←  page_text per file, CHANGE_TRACKING=TRUE  │   │
│  │  PATIENT_360_VIEW        ←  4-way join + RISK_TIER + CARE_GAP_STATUS  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  Cortex Search + Cortex COMPLETE             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  APP  (serving layer)                                                │   │
│  │  CLINICAL_DOC_SEARCH  ←  Cortex Search Service (arctic-embed-l-v2.0) │   │
│  │  PATIENT_360_SNAPSHOT  ←  Materialised Patient 360 for RAG reads     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  Streamlit in Snowflake                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  app/app.py  ·  Two-tab UI                                           │   │
│  │  Tab 1: Patient 360 Dashboard  (metrics, meds, encounters, labs)     │   │
│  │  Tab 2: Clinical Copilot       (Dual-RAG chat, citations, actions)   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Hero Test Cases

Three clinically precise patients are embedded in the synthetic dataset. Every demo scenario flows through these cases.

| # | Patient | Age | Clinical Profile | Alert Type |
|---|---------|:---:|-----------------|-----------|
| 🔴 1 | **Robert Callahan** `HERO-PT-001` | 58 | CKD Stage 3 (eGFR 38 mL/min) · active Metformin 1000 mg BID · Creatinine 2.4 mg/dL | **Safety Violation** — Metformin in CKD eGFR 30–44 high-risk zone; lactic acidosis risk per FDA Black Box Warning |
| 🟡 2 | **Linda Moreno** `HERO-PT-002` | 62 | Type 2 Diabetes (E11.9) · last HbA1c 7.8% on 2025-07-11 (14 months ago) · LDL 128 mg/dL | **Care Gap** — HbA1c overdue per ADA 2026 + HEDIS CDC NQF-0059; CMS Star Rating 3→4 risk |
| 🔴 3 | **James Whitfield** `HERO-PT-003` | 71 | 8 chronic conditions · 9-drug polypharmacy · 3 acute encounters in 2026 · EF 38% | **High Risk** — $51,755 YTD claims; 5 drug–drug interaction flags; 38% predicted 30-day readmission |

---

## Repository Structure

```
SynapseCortex AI/
│
├── snowflake/
│   ├── ddl/
│   │   ├── 01_database_schemas.sql          SYNAPSE_HEALTH DB + RAW / TRANSFORMED / APP schemas
│   │   ├── 02_raw_tables.sql                PATIENTS, ENCOUNTERS, CLAIMS, LABS (PK/FK constraints)
│   │   ├── 03_clinical_stage.sql            @RAW.CLINICAL_STAGE (SNOWFLAKE_SSE) + file formats
│   │   ├── 05_parsed_clinical_docs.sql      TRANSFORMED.PARSED_CLINICAL_DOCS via AI_PARSE_DOCUMENT
│   │   ├── 06_cortex_search_service.sql     APP.CLINICAL_DOC_SEARCH Cortex Search Service
│   │   ├── 07_validate_cortex_pipeline.sql  End-to-end validation + Python SDK query examples
│   │   └── 08_patient_360_and_copilot.sql   PATIENT_360_VIEW + risk/care-gap rules + snapshot table
│   └── stage/
│       └── 04_stage_and_load.sql            PUT clinical docs to stage; COPY CSV into RAW tables
│
├── app/
│   ├── app.py                               Streamlit in Snowflake — two-tab production UI
│   └── rag_engine.py                        Dual-RAG Copilot engine (Snowpark + Cortex)
│
├── data_generator/
│   ├── generate_synthetic_data.py           Faker script — 50 patients, 3 hero cases
│   └── output/                              Seed CSVs (committed for reproducibility)
│       ├── patients.csv                     50 rows
│       ├── encounters.csv                   102 rows
│       ├── claims.csv                       215 rows
│       └── labs.csv                         150 rows
│
├── clinical_docs/
│   ├── clinical_notes/                      5 synthetic encounter notes (hero patients)
│   │   ├── hero1_note_ROBERT_CALLAHAN.txt
│   │   ├── hero2_note_LINDA_MORENO.txt
│   │   ├── hero3_note_JAMES_WHITFIELD_inpatient.txt
│   │   ├── hero3_note_JAMES_WHITFIELD_outpatient.txt
│   │   └── hero3_note_JAMES_WHITFIELD_ED.txt
│   └── fda_inserts/                         3 FDA-style regulatory reference documents
│       ├── fda_insert_METFORMIN.txt         Black Box Warning + CKD dosing table
│       ├── fda_insert_HBA1C_MONITORING_STANDARD.txt   HEDIS CDC NQF-0059 + ADA 2026
│       └── fda_insert_POLYPHARMACY_HIGH_RISK.txt       Beers Criteria + STOPP/START + DDI
│
├── .gitignore
├── requirements.txt                         Pinned Python dependencies
└── Readme.md
```

---

## Pipeline Execution Order

> Run scripts in the numbered order below. Each step is a prerequisite for the next.

| Step | What to run | What it creates |
|:----:|-------------|----------------|
| 1 | `snowflake/ddl/01_database_schemas.sql` | `SYNAPSE_HEALTH` database · `RAW`, `TRANSFORMED`, `APP` schemas |
| 2 | `snowflake/ddl/02_raw_tables.sql` | `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, `LABS` tables with FK constraints |
| 3 | `snowflake/ddl/03_clinical_stage.sql` | `@RAW.CLINICAL_STAGE` internal stage (SSE) · CSV + text file formats |
| 4 | `data_generator/generate_synthetic_data.py` | `output/patients.csv`, `encounters.csv`, `claims.csv`, `labs.csv` |
| 5 | `snowflake/stage/04_stage_and_load.sql` | Stage all 8 clinical docs · bulk-load all 4 RAW tables |
| 6 | `snowflake/ddl/05_parsed_clinical_docs.sql` | `TRANSFORMED.PARSED_CLINICAL_DOCS` (AI_PARSE_DOCUMENT LAYOUT) |
| 7 | `snowflake/ddl/06_cortex_search_service.sql` | `APP.CLINICAL_DOC_SEARCH` Cortex Search Service |
| 8 | `snowflake/ddl/07_validate_cortex_pipeline.sql` | Validation queries · service status · row count assertions |
| 9 | `snowflake/ddl/08_patient_360_and_copilot.sql` | `TRANSFORMED.PATIENT_360_VIEW` · `APP.PATIENT_360_SNAPSHOT` |
| 10 | `app/rag_engine.py` | Dual-RAG Copilot (standalone test via environment variables) |
| 11 | `app/app.py` | Streamlit in Snowflake — deploy via Snowsight |

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Required for `snowflake-snowpark-python` |
| Snowflake account | Any edition; `SYSADMIN` or equivalent role |
| `SNOWFLAKE.CORTEX_USER` database role | Grants access to all Cortex AI functions |
| SnowSQL CLI | Required for `PUT` commands in step 5 |
| Warehouse `SYNAPSE_WH` | Update name in scripts if different |

### Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---------|---------|---------|
| `faker` | 24.0.0 | Synthetic patient data generation |
| `pandas` | 2.2.2 | CSV output from data generator |
| `snowflake-snowpark-python` | 1.23.0 | Snowflake session + SQL execution |
| `snowflake-ml-python` | 1.6.4 | `snowflake.cortex.Complete()` Python helper |
| `snowflake-core` | 0.10.0 | Cortex Search `Root` / `svc.search()` SDK |
| `snowflake-connector-python` | 3.10.1 | Standalone external connections |
| `python-dotenv` | 1.0.1 | Load `SNOWFLAKE_*` vars from `.env` |
| `streamlit` | 1.35.0 | Local testing only (bundled in Snowsight) |

### Step 2 — Configure credentials

Create a `.env` file in the project root (never commit it — it is in `.gitignore`):

```env
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=SYNAPSE_WH
SNOWFLAKE_DATABASE=SYNAPSE_HEALTH
SNOWFLAKE_SCHEMA=APP
SNOWFLAKE_ROLE=SYSADMIN
```

Grant Cortex AI access (run once as `ACCOUNTADMIN`):

```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SYSADMIN;
```

### Step 3 — Run DDL scripts

Execute scripts `01` → `03` in a Snowflake worksheet or SnowSQL, then proceed through steps 4–9 in order.

### Step 4 — Generate synthetic data

```bash
cd data_generator
python generate_synthetic_data.py
```

```
─── Dataset Summary ────────────────────────────────────────────
  Patients   :    50   (3 hero + 47 synthetic)
  Encounters :   102
  Claims     :   215
  Labs       :   150

  Hero 1 [HERO-PT-001-...] – CKD N18.3 + Metformin     → Safety Violation ✓
  Hero 2 [HERO-PT-002-...] – Diabetes + No HbA1c 14mo  → Care Gap         ✓
  Hero 3 [HERO-PT-003-...] – Multi-chronic $51,755      → High Risk        ✓
────────────────────────────────────────────────────────────────
```

### Step 5 — Stage and load

Edit `04_stage_and_load.sql` — replace `<LOCAL_BASE_PATH>` with the absolute path to `clinical_docs/` and `<LOCAL_DATA_PATH>` with the path to `data_generator/`:

```bash
snowsql -a <account> -u <user> -f snowflake/stage/04_stage_and_load.sql
```

### Steps 6–9 — Build the Cortex pipeline

Run scripts `05` through `08` in Snowflake. Script `07` includes a full validation suite with pass/fail assertions for all three hero cases.

### Step 10 — Test the RAG engine

```bash
cd app
python rag_engine.py
```

This runs three demo queries (one per hero patient) and prints cited clinical responses to stdout.

Or use it programmatically inside a Snowflake Notebook:

```python
from rag_engine import ClinicalCopilot, print_result
from snowflake.snowpark.context import get_active_session

session = get_active_session()
copilot = ClinicalCopilot(session)

result = copilot.answer(
    patient_id = "HERO-PT-001-xxxxxxxx",
    user_query = "Is this patient's Metformin safe given their kidney function?"
)
print_result(result)
```

### Step 11 — Deploy the Streamlit app

1. In Snowsight: **Projects → Streamlit → + Streamlit App**
2. Set **Warehouse** = `SYNAPSE_WH`, **Database** = `SYNAPSE_HEALTH`, **Schema** = `APP`
3. Upload `app/app.py` and `app/rag_engine.py` to the app's file stage
4. Set `app.py` as the main file and click **Run**

---

## Application UI

```
┌─────────────────────────────┬───────────────────────────────────────────────┐
│  SIDEBAR                    │  MAIN PANEL                                   │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  🧠 SynapseCortex AI        │  ──── Tab 1: Patient 360 Dashboard ────       │
│                             │                                               │
│  Patient ▼                  │  ┌──────┬──────────┬───────────┬──────────┐  │
│  ⚠️ Hero 1 – R. Callahan    │  │ Age  │ Risk Tier│ Claims    │ Care Gap │  │
│  ⚠️ Hero 2 – L. Moreno      │  │  58  │  🔴 LOW  │  $864     │  ✅ NONE │  │
│  ⚠️ Hero 3 – J. Whitfield   │  └──────┴──────────┴───────────┴──────────┘  │
│  ... 47 background patients │  Drug Safety Flag card                        │
│                             │                                               │
│  ─── Mini Patient Card ───  │  Diagnoses · Medications (🚨 Metformin rows)  │
│  Robert Callahan            │  Encounters · Labs (🟥 abnormal rows)         │
│  Age 58 · Male              │  Claims expander                              │
│  🔴 LOW RISK                │                                               │
│  ✅ NO GAP                  │  ──── Tab 2: Clinical Copilot ────            │
│                             │                                               │
│                             │  Patient banner + live badges                 │
│                             │  4 × Demo question buttons                    │
│                             │  ┌─────────────────────────────────────────┐  │
│                             │  │ 🧑‍⚕️ You: Is Metformin safe?              │  │
│                             │  │ 🤖 Copilot: The eGFR of 38 mL/min...   │  │
│                             │  │ [Doc: fda_insert_METFORMIN.txt, Page: 1]│  │
│                             │  │ 📄 Document Chunks ▼                    │  │
│                             │  └─────────────────────────────────────────┘  │
│                             │  Chat input                                   │
│                             │  🚨 Dispatch Care Action panel                │
│                             │  ⚡ Dispatch → Jira / Slack / Email           │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

---

## Key Technical Decisions

### AI_PARSE_DOCUMENT — `.txt` vs PDF
Our clinical documents are plain-text (`.txt`). Snowflake's `page_split: true` option is only supported for PDF, DOCX, and PPTX. For `.txt` files, `AI_PARSE_DOCUMENT` returns a single `{"content": "..."}` object — each file becomes one row in `PARSED_CLINICAL_DOCS` with `PAGE_NUMBER = 1`. Script `05` includes a commented **PDF upgrade path** using `LATERAL FLATTEN` on the `pages` array for when documents are converted to PDF.

### Cortex Search Service design
`APP.CLINICAL_DOC_SEARCH` is configured with:
- `PRIMARY KEY (doc_id)` — enables the optimised incremental refresh path (only changed rows re-embedded per cycle)
- `EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'` — highest-quality Snowflake-managed model, suited for long clinical text
- `TARGET_LAG = '1 hour'` · `REFRESH_MODE = INCREMENTAL` · `REQUEST_LOGGING = TRUE`

### Dual-RAG context assembly
The copilot enriches the vector search query with the patient's live ICD-10 codes, active drug names, and eGFR before calling `svc.search()`. The filter logic auto-routes hero patients to their own documents plus all FDA inserts; background patients search the full corpus.

### Risk + care gap rules
Both rules are **deterministic SQL** in `TRANSFORMED.PATIENT_360_VIEW` — no LLM inference involved in the flagging logic itself. The LLM is used only for synthesis and explanation.

```sql
-- Risk stratification
CASE WHEN AGE > 65 AND total_claims_cost > 25000 THEN 'HIGH RISK' ELSE 'LOW RISK' END

-- Care gap (HEDIS NQF-0059)
CASE WHEN has_diabetes_dx = 1
      AND (last_hba1c_date IS NULL
           OR last_hba1c_date < DATEADD('month', -12, CURRENT_DATE()))
     THEN 'GAP: Overdue HbA1c Lab' ELSE 'NO GAP' END
```

### Expected rule outputs for hero cases

| Patient | Age | Claims | Risk Tier | Diabetes | Last HbA1c | Care Gap |
|---------|:---:|-------:|-----------|:--------:|:----------:|---------|
| Robert Callahan | 58 | $864 | LOW RISK | ✗ | — | NO GAP |
| Linda Moreno | 62 | $503 | LOW RISK | ✓ | 2025-07-11 | **GAP: Overdue HbA1c Lab** |
| James Whitfield | 71 | $51,755 | **HIGH RISK** | ✓ | 2026-01-16 | NO GAP |

---

## Snowflake Object Inventory

### RAW schema

| Object | Type | Key Columns |
|--------|------|-------------|
| `PATIENTS` | Table | `PATIENT_ID` (PK), `AGE`, `INSURANCE_PLAN`, `ACTIVE_FLAG` |
| `ENCOUNTERS` | Table | `ENCOUNTER_ID` (PK), `PATIENT_ID` (FK), `PRIMARY_DX_CODE`, `PRESCRIPTION_LIST` (VARIANT) |
| `CLAIMS` | Table | `CLAIM_ID` (PK), `PATIENT_ID` (FK), `BILLED_AMOUNT`, `CLAIM_TYPE`, `DRUG_NAME` |
| `LABS` | Table | `LAB_ID` (PK), `PATIENT_ID` (FK), `LAB_TEST_CODE` (LOINC), `RESULT_VALUE`, `ABNORMAL_FLAG` |
| `@CLINICAL_STAGE` | Internal Stage | SNOWFLAKE_SSE encryption · directory table enabled |

### TRANSFORMED schema

| Object | Type | Description |
|--------|------|-------------|
| `PARSED_CLINICAL_DOCS` | Table | `AI_PARSE_DOCUMENT` output · `CHANGE_TRACKING = TRUE` · 8 rows (one per staged file) |
| `PATIENT_360_VIEW` | View | 4-way join + `RISK_TIER` + `CARE_GAP_STATUS` + `DRUG_SAFETY_FLAG` |

### APP schema

| Object | Type | Description |
|--------|------|-------------|
| `CLINICAL_DOC_SEARCH` | Cortex Search Service | `ON page_text` · `arctic-embed-l-v2.0` · incremental refresh |
| `PATIENT_360_SNAPSHOT` | Table | Materialised copy of `PATIENT_360_VIEW` for low-latency RAG reads |

---

## Staged Clinical Documents

| File | Hero Patient | Document Type | Clinical Focus |
|------|-------------|--------------|---------------|
| `clinical_notes/hero1_note_ROBERT_CALLAHAN.txt` | HERO-PT-001 | Encounter Note | CKD + Metformin safety alert |
| `clinical_notes/hero2_note_LINDA_MORENO.txt` | HERO-PT-002 | Encounter Note | Diabetes + HbA1c care gap |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt` | HERO-PT-003 | Discharge Summary | NSTEMI / PCI admission |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt` | HERO-PT-003 | Encounter Note | COPD exacerbation |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt` | HERO-PT-003 | ED Note | Hypertensive crisis |
| `fda_inserts/fda_insert_METFORMIN.txt` | HERO-PT-001 | FDA Package Insert | Black Box Warning · CKD contraindication · DDI |
| `fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt` | HERO-PT-002 | Clinical Quality Reference | HEDIS CDC NQF-0059 · ADA 2026 |
| `fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt` | HERO-PT-003 | Clinical Reference | Beers Criteria · STOPP/START v3 · DDI analysis |

---

## Copilot System Prompt

The `llama3.3-70b` model is constrained by this system prompt on every request:

> *Synthesize answers strictly using the provided Patient 360 structured data and PDF Document Chunks. For every factual claim, append an inline citation: `[Doc: <file_name>, Page: <page_number>]`. If no evidence exists in the context, reply: `Insufficient evidence.`*

This ensures the copilot never halluccinates beyond the two provided contexts — structured Patient 360 data and retrieved document chunks.

---

## Git History

| Commit | Description |
|--------|-------------|
| `5fb53c9` | Streamlit in Snowflake application (`app/app.py`) |
| `126dd55` | `requirements.txt` + README update |
| `9403fa3` | Patient 360 view + Dual-RAG Clinical Copilot engine |
| `6faa7cf` | Cortex document parsing pipeline + Cortex Search Service |
| `70f641d` | SynapseCortex AI data foundation (DDL, faker, clinical docs) |

---

<div align="center">

*Built for the Snowflake AI Data Engineering Hackathon · September 2026*

*Snowflake Cortex AI · llama3.3-70b · Streamlit in Snowflake · Python 3.10*

</div>
