# SynapseCortex AI – Patient 360 & Clinical Regulatory Copilot

**Hackathon:** Snowflake AI Data Engineering – Patient 360 & Clinical Copilot  
**Built with:** Snowflake Cortex AI · Python · SnowSQL · Snowpark  
**Status:** Full Pipeline Implemented ✅

---

## What Is SynapseCortex AI?

SynapseCortex AI is a unified clinical intelligence platform built natively on Snowflake. It combines structured EHR data, unstructured clinical documents, and Snowflake Cortex AI to deliver three capabilities:

- **Patient 360 View** — A single longitudinal record joining demographics, encounters, claims, and labs with deterministic risk stratification and HEDIS-aligned care gap detection.
- **Cortex Document Intelligence** — Clinical encounter notes and FDA package inserts parsed via `AI_PARSE_DOCUMENT` (LAYOUT mode) and indexed in a `CORTEX SEARCH SERVICE` for semantic + lexical retrieval.
- **Dual-RAG Clinical Copilot** — Answers clinical questions by combining structured Patient 360 data (Arm 1) with vector-searched document chunks (Arm 2), synthesised by `CORTEX.COMPLETE` (`llama3.3-70b`) with strict inline citations.

---

## Repository Structure

```
SynapseCortex AI Patient & Member 360 & Clinical Regulatory Copilot/
│
├── snowflake/
│   ├── ddl/
│   │   ├── 01_database_schemas.sql      ← SYNAPSE_HEALTH DB + RAW / TRANSFORMED / APP schemas
│   │   ├── 02_raw_tables.sql            ← PATIENTS, ENCOUNTERS, CLAIMS, LABS DDL (PK/FK)
│   │   ├── 03_clinical_stage.sql        ← @RAW.CLINICAL_STAGE (SNOWFLAKE_SSE) + file formats
│   │   ├── 05_parsed_clinical_docs.sql  ← TRANSFORMED.PARSED_CLINICAL_DOCS via AI_PARSE_DOCUMENT
│   │   ├── 06_cortex_search_service.sql ← APP.CLINICAL_DOC_SEARCH Cortex Search Service
│   │   ├── 07_validate_cortex_pipeline.sql ← End-to-end pipeline validation + SDK examples
│   │   └── 08_patient_360_and_copilot.sql  ← PATIENT_360_VIEW + risk/care-gap rules + snapshot
│   └── stage/
│       └── 04_stage_and_load.sql        ← PUT clinical docs + COPY INTO table loads
│
├── app/
│   ├── app.py                           ← Streamlit in Snowflake UI (two-tab application)
│   └── rag_engine.py                    ← Dual-RAG Copilot engine (Snowpark + Cortex)
│
├── data_generator/
│   ├── generate_synthetic_data.py       ← Faker: 50 patients, 3 hero cases, referential integrity
│   └── output/                          ← Generated CSVs (runtime, not committed)
│       ├── patients.csv
│       ├── encounters.csv
│       ├── claims.csv
│       └── labs.csv
│
├── clinical_docs/
│   ├── clinical_notes/
│   │   ├── hero1_note_ROBERT_CALLAHAN.txt              ← Hero 1: Safety Violation – CKD + Metformin
│   │   ├── hero2_note_LINDA_MORENO.txt                 ← Hero 2: Care Gap – Diabetes, no HbA1c 14mo
│   │   ├── hero3_note_JAMES_WHITFIELD_inpatient.txt    ← Hero 3: High Risk – NSTEMI admission
│   │   ├── hero3_note_JAMES_WHITFIELD_outpatient.txt   ← Hero 3: COPD exacerbation follow-up
│   │   └── hero3_note_JAMES_WHITFIELD_ED.txt           ← Hero 3: Hypertensive crisis ED visit
│   └── fda_inserts/
│       ├── fda_insert_METFORMIN.txt                    ← FDA PI: Metformin CKD contraindication
│       ├── fda_insert_HBA1C_MONITORING_STANDARD.txt    ← HEDIS/ADA HbA1c monitoring reference
│       └── fda_insert_POLYPHARMACY_HIGH_RISK.txt       ← Beers Criteria + DDI analysis
│
├── requirements.txt                     ← Python dependencies (pinned versions)
└── Readme.md
```

---

## Hero Test Cases

Three clinically precise patients are embedded in the dataset to drive every demo scenario:

| # | Patient | Age | Clinical Profile | AI Copilot Alert |
|---|---------|-----|-----------------|-----------------|
| 1 | **Robert Callahan** (`HERO-PT-001`) | 58 | CKD Stage 3 (eGFR 38) + active Metformin 1000 mg BID | ⚠️ **Safety Violation** – Metformin contraindicated (eGFR 30–44 high-risk zone); lactic acidosis risk |
| 2 | **Linda Moreno** (`HERO-PT-002`) | 62 | Type 2 Diabetes + last HbA1c 14 months ago (7.8%) | ⚠️ **Care Gap** – HbA1c overdue per ADA/HEDIS CDC NQF-0059; CMS Star Rating impact |
| 3 | **James Whitfield** (`HERO-PT-003`) | 71 | 8 chronic diagnoses, 3 encounters, 9-drug polypharmacy | ⚠️ **High Risk** – Claims $51,755; 5 DDI flags; 38% 30-day readmission risk |

---

## Full Data Architecture

```
SYNAPSE_HEALTH (Database)
│
├── RAW (Schema)                          ← Immutable landing zone
│   ├── PATIENTS                          PK: PATIENT_ID (UUID)
│   ├── ENCOUNTERS                        FK → PATIENTS
│   ├── CLAIMS                            FK → PATIENTS, ENCOUNTERS
│   ├── LABS                              FK → PATIENTS, ENCOUNTERS
│   └── @CLINICAL_STAGE                   Internal stage (SNOWFLAKE_SSE)
│       ├── clinical_notes/               Free-text encounter notes
│       ├── fda_inserts/                  FDA regulatory reference docs
│       └── data/                         Bulk CSV loads
│
├── TRANSFORMED (Schema)                  ← Curated and enriched layer
│   ├── PARSED_CLINICAL_DOCS              AI_PARSE_DOCUMENT output (page_text per file)
│   └── PATIENT_360_VIEW                  4-way join + risk/care-gap logic (VIEW)
│
└── APP (Schema)                          ← Application serving layer
    ├── CLINICAL_DOC_SEARCH               Cortex Search Service (semantic + lexical)
    └── PATIENT_360_SNAPSHOT              Materialised Patient 360 (TABLE, for RAG)
```

---

## Pipeline Execution Order

Run scripts **in this exact order**:

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `snowflake/ddl/01_database_schemas.sql` | Create `SYNAPSE_HEALTH` DB + 3 schemas |
| 2 | `snowflake/ddl/02_raw_tables.sql` | Create `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, `LABS` |
| 3 | `snowflake/ddl/03_clinical_stage.sql` | Create `@RAW.CLINICAL_STAGE` + file formats |
| 4 | `data_generator/generate_synthetic_data.py` | Generate 50-patient CSV dataset |
| 5 | `snowflake/stage/04_stage_and_load.sql` | PUT docs → stage; COPY CSV → tables |
| 6 | `snowflake/ddl/05_parsed_clinical_docs.sql` | Parse docs with `AI_PARSE_DOCUMENT` |
| 7 | `snowflake/ddl/06_cortex_search_service.sql` | Create `APP.CLINICAL_DOC_SEARCH` |
| 8 | `snowflake/ddl/07_validate_cortex_pipeline.sql` | Validate stage + search service |
| 9 | `snowflake/ddl/08_patient_360_and_copilot.sql` | Build `PATIENT_360_VIEW` + snapshot |
| 10 | `app/rag_engine.py` | Run Dual-RAG Copilot |
| 11 | `app/app.py` | Launch Streamlit in Snowflake UI |

---

## Quick Start

### Prerequisites

- Python >= 3.10
- Snowflake account with `SYSADMIN` or equivalent role
- Role granted `SNOWFLAKE.CORTEX_USER` database role
- SnowSQL CLI (for `PUT` commands in step 5)
- Warehouse named `SYNAPSE_WH` (or update the warehouse name in each script)

### 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

Key packages:

| Package | Version | Purpose |
|---------|---------|---------|
| `faker` | 24.0.0 | Synthetic patient data generation |
| `pandas` | 2.2.2 | CSV output for data generator |
| `snowflake-snowpark-python` | 1.23.0 | Snowflake session + SQL execution |
| `snowflake-ml-python` | 1.6.4 | `snowflake.cortex.Complete()` helper |
| `snowflake-core` | 0.10.0 | Cortex Search `Root` / `svc.search()` SDK |
| `snowflake-connector-python` | 3.10.1 | Standalone external connections |
| `python-dotenv` | 1.0.1 | Load env vars from `.env` file |

### 2 — Configure Snowflake credentials

For standalone use, create a `.env` file in the project root (never commit this):

```bash
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=SYNAPSE_WH
SNOWFLAKE_DATABASE=SYNAPSE_HEALTH
SNOWFLAKE_SCHEMA=APP
SNOWFLAKE_ROLE=SYSADMIN
```

Grant Cortex access (run once as ACCOUNTADMIN):

```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SYSADMIN;
```

### 3 — Run DDL scripts in Snowflake

```sql
-- In a Snowflake worksheet, run scripts 01–03 in order:
-- 01_database_schemas.sql → 02_raw_tables.sql → 03_clinical_stage.sql
```

### 4 — Generate synthetic data

```bash
cd data_generator
python generate_synthetic_data.py
```

Expected output:
```
  Patients   :    50  (3 hero + 47 synthetic)
  Encounters :   102
  Claims     :   215
  Labs       :   150

  Hero 1 [HERO-PT-001-...] – CKD N18.3 + Metformin → Safety Violation
  Hero 2 [HERO-PT-002-...] – Diabetes + No HbA1c 14mo → Care Gap
  Hero 3 [HERO-PT-003-...] – Multi-chronic, Claims = $51,755.00 → High Risk ✓
```

### 5 — Stage and load

Edit `snowflake/stage/04_stage_and_load.sql`, replace `<LOCAL_BASE_PATH>` and `<LOCAL_DATA_PATH>` with your absolute paths, then:

```bash
snowsql -a <account> -u <user> -f snowflake/stage/04_stage_and_load.sql
```

### 6–9 — Run remaining DDL scripts in order

```sql
-- 05_parsed_clinical_docs.sql      → parses all staged .txt files
-- 06_cortex_search_service.sql     → creates APP.CLINICAL_DOC_SEARCH
-- 07_validate_cortex_pipeline.sql  → validates pipeline end-to-end
-- 08_patient_360_and_copilot.sql   → builds PATIENT_360_VIEW + snapshot
```

### 10 — Run the Dual-RAG Copilot

**Inside Snowflake Notebook / Streamlit in Snowflake:**

```python
from app.rag_engine import ClinicalCopilot, print_result
from snowflake.snowpark.context import get_active_session

session = get_active_session()
copilot = ClinicalCopilot(session)

result = copilot.answer(
    patient_id = "HERO-PT-001-xxxxxxxx",   # replace with actual patient ID
    user_query = "Is this patient's Metformin prescription safe given their kidney function?"
)
print_result(result)
```

**Standalone (external Python):**

```bash
cd app
python rag_engine.py      # runs 3-hero demo using SNOWFLAKE_* env vars
```

### 11 — Deploy the Streamlit in Snowflake App

1. In Snowsight, navigate to **Projects → Streamlit → + Streamlit App**
2. Set:
   - **Warehouse**: `SYNAPSE_WH`
   - **Database**: `SYNAPSE_HEALTH`
   - **Schema**: `APP`
3. Upload both `app/app.py` and `app/rag_engine.py` to the app's file stage
4. Set `app.py` as the main file and click **Run**

The app opens with a two-tab layout:
- **Tab 1 – Patient 360 Dashboard**: metric cards, diagnoses, medications, encounters, lab history, claims
- **Tab 2 – Clinical & Regulatory Copilot**: chat interface, demo questions, document chunk drawer, Dispatch Care Action panel

---

## Streamlit Application — UI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  SIDEBAR                        │  MAIN PANEL                       │
│  ─────────────────────────────  │  ─────────────────────────────── │
│  🧠 SynapseCortex AI            │  🧠 SynapseCortex AI Header        │
│                                 │                                   │
│  Patient Selector ▼             │  [Tab 1: Patient 360 Dashboard]   │
│  ⚠️ Hero 1 – Robert Callahan    │  [Tab 2: Clinical Copilot]        │
│  ⚠️ Hero 2 – Linda Moreno       │                                   │
│  ⚠️ Hero 3 – James Whitfield    │  TAB 1                            │
│  ... 47 more patients ...       │  ┌────┬────────┬───────┬───────┐  │
│                                 │  │Age │Risk    │Claims │Care   │  │
│  Patient mini-card:             │  │    │Tier 🔴 │Cost   │Gap ⚠️ │  │
│  Robert Callahan                │  └────┴────────┴───────┴───────┘  │
│  Age 58 · Male                  │  + Drug Safety card               │
│  🔴 LOW RISK                    │                                   │
│  ✅ NO GAP                      │  Diagnoses table                  │
│                                 │  Medications table (🚨 Metformin) │
│                                 │  Encounters table                 │
│                                 │  Lab Results (🟥 abnormals)       │
│                                 │  Claims expander                  │
│                                 │                                   │
│                                 │  TAB 2                            │
│                                 │  Patient banner + badges          │
│                                 │  Demo question buttons            │
│                                 │  Chat history (citations styled)  │
│                                 │  📄 Document chunk expander       │
│                                 │  [Chat input box]                 │
│                                 │  ─────────────────────────────── │
│                                 │  🚨 Dispatch Care Action panel    │
│                                 │  Action type + Channel selectors  │
│                                 │  ⚡ Dispatch Care Action button   │
│                                 │  📋 Action log expander           │
└─────────────────────────────────────────────────────────────────────┘
```



```
User Query + Patient ID
        │
        ▼
┌───────────────────────────────────────────────┐
│             ClinicalCopilot.answer()           │
│                                               │
│  ARM 1 – Structured RAG                       │
│  ┌─────────────────────────────────────────┐  │
│  │  SQL → APP.PATIENT_360_SNAPSHOT         │  │
│  │  Returns: diagnoses, meds, labs,        │  │
│  │  claims cost, RISK_TIER, CARE_GAP_STATUS│  │
│  └─────────────────────────────────────────┘  │
│                    +                          │
│  ARM 2 – Vector RAG                           │
│  ┌─────────────────────────────────────────┐  │
│  │  APP.CLINICAL_DOC_SEARCH.svc.search()   │  │
│  │  Returns: top-k clinical note +         │  │
│  │  FDA insert chunks (file + page cited)  │  │
│  └─────────────────────────────────────────┘  │
│                    │                          │
│                    ▼                          │
│  CORTEX.COMPLETE (llama3.3-70b)               │
│  System prompt: strict citation enforcement   │
│  [Doc: <file_name>, Page: <page_number>]      │
└───────────────────────────────────────────────┘
        │
        ▼
  CopilotResult.answer  (cited clinical response)
```

---

## Patient 360 View — Key Logic

### Risk Stratification (`RISK_TIER`)
Deterministic rule applied in `TRANSFORMED.PATIENT_360_VIEW`:

```sql
CASE
    WHEN AGE > 65 AND total_claims_cost > 25000 THEN 'HIGH RISK'
    ELSE 'LOW RISK'
END
```

| Patient | Age | Total Claims | Risk Tier |
|---------|-----|-------------|-----------|
| Robert Callahan (Hero 1) | 58 | $864 | LOW RISK |
| Linda Moreno (Hero 2) | 62 | $503 | LOW RISK |
| James Whitfield (Hero 3) | 71 | $51,755 | **HIGH RISK** ✓ |

### Care Gap Detection (`CARE_GAP_STATUS`)
HEDIS CDC NQF-0059 aligned:

```sql
CASE
    WHEN has_diabetes_dx = 1
     AND (last_hba1c_date IS NULL
          OR last_hba1c_date < DATEADD('month', -12, CURRENT_DATE()))
    THEN 'GAP: Overdue HbA1c Lab'
    ELSE 'NO GAP'
END
```

| Patient | Diabetes Dx | Last HbA1c | Care Gap |
|---------|-------------|------------|----------|
| Robert Callahan (Hero 1) | No (CKD primary) | — | NO GAP |
| Linda Moreno (Hero 2) | Yes (E11.9) | 2025-07-11 (14 mo ago) | **GAP: Overdue HbA1c Lab** ✓ |
| James Whitfield (Hero 3) | Yes (E11.9) | 2026-01-16 | NO GAP |

### Drug Safety Flag
Bonus rule surfacing the Hero 1 Metformin/CKD conflict:

```sql
CASE
    WHEN active_medications_list ILIKE '%metformin%'
     AND has_ckd_dx = 1
     AND last_egfr_value < 45
    THEN 'ALERT: Metformin active with eGFR < 45 (CKD contraindication)'
END
```

---

## Cortex Document Pipeline

| Object | Type | Description |
|--------|------|-------------|
| `@RAW.CLINICAL_STAGE` | Internal Stage | SSE-encrypted; holds 8 clinical/FDA `.txt` files |
| `TRANSFORMED.PARSED_CLINICAL_DOCS` | Table | `AI_PARSE_DOCUMENT` output; `CHANGE_TRACKING=TRUE` |
| `APP.CLINICAL_DOC_SEARCH` | Cortex Search Service | `llama3.3-70b` embedding; `TARGET_LAG=1hr`; `INCREMENTAL` refresh |

**Staged documents:**

| File | Hero | Category |
|------|------|----------|
| `clinical_notes/hero1_note_ROBERT_CALLAHAN.txt` | HERO-PT-001 | Clinical Note |
| `clinical_notes/hero2_note_LINDA_MORENO.txt` | HERO-PT-002 | Clinical Note |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt` | HERO-PT-003 | Clinical Note |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt` | HERO-PT-003 | Clinical Note |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt` | HERO-PT-003 | Clinical Note |
| `fda_inserts/fda_insert_METFORMIN.txt` | HERO-PT-001 | FDA Insert |
| `fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt` | HERO-PT-002 | FDA Insert |
| `fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt` | HERO-PT-003 | FDA Insert |

---

## RAW Table Schema Summary

### PATIENTS
| Column | Type | Notes |
|--------|------|-------|
| `PATIENT_ID` | VARCHAR(36) | PK – UUID |
| `FIRST_NAME`, `LAST_NAME` | VARCHAR | |
| `DATE_OF_BIRTH` | DATE | |
| `AGE` | NUMBER(3,0) | Computed at ingest |
| `GENDER`, `RACE`, `ETHNICITY` | VARCHAR | |
| `INSURANCE_ID`, `INSURANCE_PLAN` | VARCHAR | |
| `PRIMARY_CARE_NPI` | VARCHAR(20) | |
| `ACTIVE_FLAG` | BOOLEAN | |

### ENCOUNTERS
| Column | Type | Notes |
|--------|------|-------|
| `ENCOUNTER_ID` | VARCHAR(36) | PK |
| `PATIENT_ID` | VARCHAR(36) | FK → PATIENTS |
| `PRIMARY_DX_CODE`, `PRIMARY_DX_DESC` | VARCHAR | ICD-10-CM |
| `SECONDARY_DX_CODES`, `PROCEDURE_CODES`, `PRESCRIPTION_LIST` | VARIANT | JSON arrays |
| `NOTES_REF` | VARCHAR | Pointer to `@CLINICAL_STAGE` file |

### CLAIMS
| Column | Type | Notes |
|--------|------|-------|
| `CLAIM_ID` | VARCHAR(36) | PK |
| `PATIENT_ID` | VARCHAR(36) | FK → PATIENTS |
| `ENCOUNTER_ID` | VARCHAR(36) | FK → ENCOUNTERS (nullable for pharmacy) |
| `CLAIM_TYPE` | VARCHAR | Medical \| Pharmacy |
| `BILLED_AMOUNT`, `ALLOWED_AMOUNT`, `PAID_AMOUNT` | NUMBER(12,2) | |
| `CLAIM_STATUS` | VARCHAR | Paid \| Denied \| Pending \| Adjusted |
| `NDC_CODE`, `DRUG_NAME` | VARCHAR | Pharmacy claims |

### LABS
| Column | Type | Notes |
|--------|------|-------|
| `LAB_ID` | VARCHAR(36) | PK |
| `PATIENT_ID` | VARCHAR(36) | FK → PATIENTS |
| `ENCOUNTER_ID` | VARCHAR(36) | FK → ENCOUNTERS |
| `LAB_TEST_CODE` | VARCHAR(30) | LOINC code |
| `RESULT_VALUE`, `RESULT_UNIT`, `REFERENCE_RANGE` | VARCHAR | |
| `ABNORMAL_FLAG` | VARCHAR | H \| L \| HH \| LL \| N \| A |

---

## Git History

| Commit | Description |
|--------|-------------|
| `9403fa3` | Patient 360 view + Dual-RAG Clinical Copilot engine |
| `6faa7cf` | Cortex document parsing pipeline + Search Service |
| `70f641d` | SynapseCortex AI data foundation |

---

*SynapseCortex AI – Hackathon Build | Snowflake AI Data Engineering | September 2026*
