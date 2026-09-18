<div align="center">

# 🧠 SynapseCortex AI
### Patient 360 & Clinical Regulatory Copilot

*A Snowflake-native clinical intelligence platform that unifies structured EHR data, unstructured clinical documents, and generative AI into a single production-ready application.*

[![Snowflake](https://img.shields.io/badge/Snowflake-Cortex%20AI-29B5E8?logo=snowflake&logoColor=white)](https://www.snowflake.com/en/data-cloud/cortex/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-in%20Snowflake-FF4B4B?logo=streamlit&logoColor=white)](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
[![LLM](https://img.shields.io/badge/LLM-llama3.3--70b-blueviolet)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Live App →** [Open in Snowsight](https://app.snowflake.com/streamlit/cnwxskg/mw91931/#/apps/b2pmsuf3ml5nmm3cmolf)

</div>

---

## What Is SynapseCortex AI?

SynapseCortex AI is a clinical intelligence platform built entirely on Snowflake. It answers three questions that drive real-world healthcare outcomes:

| Clinical Question | How SynapseCortex Answers It |
|---|---|
| *Is this patient's medication safe?* | Drug–disease contraindication detection using FDA package inserts + structured lab data |
| *Is this patient missing a required quality measure?* | HEDIS NQF-0059 care gap detection with CMS Star Rating impact scoring |
| *Which patients are highest risk?* | Deterministic risk stratification over claims cost + age + chronic condition burden |

It does this by combining three pillars built entirely on Snowflake:

- **Patient 360 View** — A longitudinal record joining `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, and `LABS` with risk stratification and care gap logic applied in SQL.
- **Cortex Document Intelligence** — Eight clinical notes and FDA package inserts indexed in a `CORTEX SEARCH SERVICE` for hybrid semantic + lexical retrieval.
- **Dual-RAG Clinical Copilot** — A `llama3.3-70b`-powered assistant that synthesises structured Patient 360 context with vector-searched document chunks under strict citation enforcement.

---

## Live Demo

**App URL:** https://app.snowflake.com/streamlit/cnwxskg/mw91931/#/apps/b2pmsuf3ml5nmm3cmolf

The app has two tabs:

### Tab 1 — Patient 360 Dashboard
Shows the full longitudinal clinical profile for any of the 50 synthetic patients:
- Risk tier badge (HIGH RISK / LOW RISK)
- Care gap status (HEDIS NQF-0059)
- Drug safety flag (FDA contraindication check)
- Active medications, diagnoses, encounters, lab results, claims

### Tab 2 — Clinical & Regulatory Copilot
An AI chat interface backed by Dual-RAG:
- Select a patient from the sidebar
- Click a demo question or type your own
- The copilot retrieves relevant document chunks and structured patient data
- Every factual claim in the response includes an inline citation `[Doc: filename, Page: n]`

---

## Demo Walkthrough — Step by Step

### Hero Case 1 — Safety Violation 🔴
**Patient:** Robert Callahan | Age 58 | CKD Stage 3

1. Open the app → select **⚠️ Hero 1 – Safety Violation | Robert Callahan** from the sidebar
2. Go to **Tab 1 (Patient 360 Dashboard)**
   - Notice the red **🚨 ALERT: Metformin active with eGFR < 45** drug safety flag
   - Check the Lab Results table — eGFR is 38 mL/min (abnormal, highlighted red)
   - Metformin row in the medications table is also highlighted red
3. Go to **Tab 2 (Clinical Copilot)**
4. Click the demo question: **"Is Metformin contraindicated for this patient given their kidney function?"**
5. The copilot will respond with:
   - Direct answer citing FDA Black Box Warning for Metformin in CKD eGFR 30–44
   - Supporting evidence from the clinical note (eGFR 38 mL/min)
   - Recommendation to discontinue or dose-reduce, with citations

**What to highlight:** The AI didn't hallucinate — every claim is grounded in the FDA insert and the patient's own lab results. The drug safety flag was computed by deterministic SQL, not LLM inference.

---

### Hero Case 2 — Care Gap 🟡
**Patient:** Linda Moreno | Age 62 | Type 2 Diabetes

1. Select **⚠️ Hero 2 – Care Gap | Linda Moreno** from the sidebar
2. Go to **Tab 1**
   - Notice the yellow **⚠️ GAP: Overdue HbA1c Lab** badge
   - Last HbA1c metric shows 7.8% on 2025-07-11 (14 months ago)
3. Go to **Tab 2**
4. Click: **"What care gaps exist for this diabetic patient?"**
5. The copilot responds with:
   - HbA1c overdue by 14 months, last result 7.8% above target < 7.0%
   - ADA 2026 Standards — should be tested at least twice per year
   - HEDIS NQF-0059 compliance gap
   - CMS Star Rating risk: plan score could drop from 3 → 4 stars
   - Recommendations: order HbA1c immediately, consider therapy intensification

**What to highlight:** The care gap was detected by a pure SQL rule (HEDIS NQF-0059), not AI. The LLM only explains and contextualises it using the retrieved documents.

---

### Hero Case 3 — High Risk 🔴
**Patient:** James Whitfield | Age 71 | 8 chronic conditions, 9-drug polypharmacy

1. Select **⚠️ Hero 3 – High Risk | James Whitfield** from the sidebar
2. Go to **Tab 1**
   - Risk tier shows **🔴 HIGH RISK** (age 71, claims $51,755 YTD)
   - 8 chronic conditions, 9 active medications
   - Multiple abnormal lab results highlighted red
3. Go to **Tab 2**
4. Click: **"Summarise the drug-drug interactions in this patient's current regimen"**
5. The copilot responds with:
   - Carvedilol + Albuterol → worsens bronchospasm in COPD
   - Lisinopril + Furosemide → hyperkalemia risk in CKD
   - Carvedilol + Insulin Glargine → masks hypoglycemia symptoms
   - All cited from the Polypharmacy High Risk FDA insert

**What to highlight:** The RAG engine automatically routed the query to the correct FDA reference document using Cortex Search. The filter logic identified this as a Hero-PT-003 patient and retrieved their specific documents + all FDA inserts.

---

## How to Explain the Project (Elevator Pitch)

> "SynapseCortex AI is a clinical decision support platform built natively on Snowflake. It takes a patient's full medical history — their diagnoses, medications, lab results, and claims — and combines it with FDA drug safety guidelines and clinical quality standards in a single AI-powered interface.
>
> The platform automatically detects three critical clinical scenarios: medication safety violations, overdue care quality measures, and high-risk patients who need urgent intervention. When a clinician asks a question about a patient, the system retrieves the most relevant passages from FDA package inserts and clinical notes using Snowflake's vector search, then uses llama3.3-70b to synthesise a cited answer grounded entirely in evidence — no hallucination, no guessing.
>
> Everything runs inside Snowflake — the data, the AI, and the app. There's no external infrastructure to manage."

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SYNAPSE_HEALTH  (Snowflake Database)               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  RAW  (landing zone)                                                 │   │
│  │  PATIENTS · ENCOUNTERS · CLAIMS · LABS   ←  CSV bulk load           │   │
│  │  @CLINICAL_STAGE (SNOWFLAKE_SSE)         ←  8 clinical text files   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  Python parser + SQL transforms              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TRANSFORMED  (enriched layer)                                       │   │
│  │  PARSED_CLINICAL_DOCS  ←  full text per document                    │   │
│  │  PATIENT_360_VIEW      ←  4-way join + RISK_TIER + CARE_GAP_STATUS  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  Cortex Search + Cortex COMPLETE             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  APP  (serving layer)                                                │   │
│  │  CLINICAL_DOC_SEARCH   ←  Cortex Search (arctic-embed-l-v2.0)       │   │
│  │  PATIENT_360_SNAPSHOT  ←  Materialised Patient 360 for RAG reads    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼  Streamlit in Snowflake                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  app/app.py  ·  Two-tab UI                                           │   │
│  │  Tab 1: Patient 360 Dashboard                                        │   │
│  │  Tab 2: Clinical Copilot  (Dual-RAG chat + citations)                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dual-RAG Engine Flow

```
User Question
     │
     ▼
Enrich query with patient's ICD-10 codes + drug names + eGFR
     │
     ▼
Cortex Search → retrieve top-5 document chunks (semantic + lexical)
     │
     ▼
Fetch Patient 360 structured context from APP.PATIENT_360_SNAPSHOT
     │
     ▼
Assemble prompt:
  [System]  Strict citation enforcement instructions
  [User]    CONTEXT A: Patient 360 structured data
            CONTEXT B: Retrieved document chunks
            QUESTION:  User's clinical query
     │
     ▼
SNOWFLAKE.CORTEX.COMPLETE (llama3.3-70b)
     │
     ▼
Cited clinical answer with [Doc: filename, Page: n] inline references
```

---

## Repository Structure

```
SynapseCortex AI/
│
├── app/
│   ├── app.py                               Streamlit UI (two-tab, production-ready)
│   └── rag_engine.py                        Dual-RAG Copilot engine
│
├── snowflake/
│   ├── ddl/
│   │   ├── 01_database_schemas.sql          SYNAPSE_HEALTH DB + schemas
│   │   ├── 02_raw_tables.sql                PATIENTS, ENCOUNTERS, CLAIMS, LABS
│   │   ├── 03_clinical_stage.sql            Internal stage + file formats
│   │   ├── 05_parsed_clinical_docs.sql      TRANSFORMED.PARSED_CLINICAL_DOCS
│   │   ├── 06_cortex_search_service.sql     APP.CLINICAL_DOC_SEARCH
│   │   ├── 07_validate_cortex_pipeline.sql  End-to-end validation queries
│   │   └── 08_patient_360_and_copilot.sql   PATIENT_360_VIEW + snapshot table
│   └── stage/
│       └── 04_stage_and_load.sql            Stage + COPY INTO reference script
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
│   └── fda_inserts/                         3 FDA-style regulatory reference documents
│
├── upload_to_snowflake.py                   Python uploader (replaces SnowSQL PUT)
├── parse_and_load_docs.py                   Local doc parser (replaces AI_PARSE_DOCUMENT)
├── snowflake.yml                            Snowflake CLI project definition
├── requirements.txt                         Pinned Python dependencies
└── Readme.md
```

---

## Hero Patients

Three clinically precise patients are embedded in the synthetic dataset. Every demo scenario flows through these cases.

| # | Patient | Age | Clinical Profile | Alert Type |
|---|---------|:---:|----------------|-----------|
| 🔴 1 | **Robert Callahan** `HERO-PT-001` | 58 | CKD Stage 3 (eGFR 38) · active Metformin 1000mg BID · Creatinine 2.4 | **Safety Violation** — Metformin in eGFR 30–44 high-risk zone; lactic acidosis risk per FDA Black Box Warning |
| 🟡 2 | **Linda Moreno** `HERO-PT-002` | 62 | Type 2 Diabetes · last HbA1c 7.8% on 2025-07-11 (14 months ago) · LDL 128 | **Care Gap** — HbA1c overdue per ADA 2026 + HEDIS CDC NQF-0059; CMS Star Rating 3→4 risk |
| 🔴 3 | **James Whitfield** `HERO-PT-003` | 71 | 8 chronic conditions · 9-drug polypharmacy · 3 acute encounters · EF 38% | **High Risk** — $51,755 YTD claims; 5 drug–drug interaction flags; 38% predicted 30-day readmission |

---

## Snowflake Object Inventory

| Schema | Object | Type | Purpose |
|--------|--------|------|---------|
| RAW | `PATIENTS` | Table | 50 synthetic patients (3 hero + 47 background) |
| RAW | `ENCOUNTERS` | Table | 102 clinical encounters |
| RAW | `CLAIMS` | Table | 215 medical + pharmacy claims |
| RAW | `LABS` | Table | 150 lab results with LOINC codes |
| RAW | `@CLINICAL_STAGE` | Internal Stage | 8 clinical text files (SSE encrypted) |
| TRANSFORMED | `PARSED_CLINICAL_DOCS` | Table | Extracted text, one row per document, CHANGE_TRACKING=TRUE |
| TRANSFORMED | `PATIENT_360_VIEW` | View | 4-way join + RISK_TIER + CARE_GAP_STATUS + DRUG_SAFETY_FLAG |
| APP | `CLINICAL_DOC_SEARCH` | Cortex Search Service | arctic-embed-l-v2.0 · hybrid semantic+lexical search |
| APP | `PATIENT_360_SNAPSHOT` | Table | Materialised Patient 360, 50 rows, read by RAG engine |

---

## Staged Clinical Documents

| File | Patient | Type |
|------|---------|------|
| `hero1_note_ROBERT_CALLAHAN.txt` | Hero 1 | Encounter note — CKD + Metformin safety |
| `hero2_note_LINDA_MORENO.txt` | Hero 2 | Encounter note — Diabetes + HbA1c care gap |
| `hero3_note_JAMES_WHITFIELD_inpatient.txt` | Hero 3 | Discharge summary — NSTEMI / PCI |
| `hero3_note_JAMES_WHITFIELD_outpatient.txt` | Hero 3 | Encounter note — COPD exacerbation |
| `hero3_note_JAMES_WHITFIELD_ED.txt` | Hero 3 | ED note — Hypertensive crisis |
| `fda_insert_METFORMIN.txt` | Hero 1 | FDA insert — Black Box Warning · CKD dosing |
| `fda_insert_HBA1C_MONITORING_STANDARD.txt` | Hero 2 | Clinical reference — HEDIS NQF-0059 · ADA 2026 |
| `fda_insert_POLYPHARMACY_HIGH_RISK.txt` | Hero 3 | Clinical reference — Beers Criteria · DDI analysis |

---

## Setup & Installation

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Tested on Python 3.13 |
| Snowflake account | Enterprise edition; `ACCOUNTADMIN` role |
| `SNOWFLAKE.CORTEX_USER` database role | Grants access to Cortex AI functions |

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Create a `.env` file in the project root:

```env
SNOWFLAKE_ACCOUNT=CNWXSKG-MW91931
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=SYNAPSE_WH
SNOWFLAKE_DATABASE=SYNAPSE_HEALTH
SNOWFLAKE_SCHEMA=APP
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

### 3. Run Snowflake DDL scripts (in order)

In Snowsight → **Projects → New SQL file** — run each script with **Ctrl+A → Run**:

```
01_database_schemas.sql     → database + 3 schemas
02_raw_tables.sql           → PATIENTS, ENCOUNTERS, CLAIMS, LABS
03_clinical_stage.sql       → internal stage + file formats
```

Also run once as ACCOUNTADMIN:
```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS SYNAPSE_WH
    WAREHOUSE_SIZE = 'X-SMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
```

### 4. Generate synthetic data

```bash
python data_generator/generate_synthetic_data.py
```

### 5. Upload files and load RAW tables

```bash
python upload_to_snowflake.py
```

### 6. Parse clinical documents

```bash
python parse_and_load_docs.py
```

### 7. Build Cortex pipeline (Snowsight)

Run in order:
```
06_cortex_search_service.sql   → Cortex Search Service (takes ~2 min)
08_patient_360_and_copilot.sql → Patient 360 view + snapshot table
```

### 8. Test the RAG engine locally

```bash
# First bypass MFA (60 min window) in Snowsight:
# ALTER USER your_username SET MINS_TO_BYPASS_MFA = 60;

python app/rag_engine.py
```

### 9. Deploy the Streamlit app

In Snowsight → **Projects → Streamlit → + Streamlit App**:
- Warehouse: `SYNAPSE_WH`
- Database: `SYNAPSE_HEALTH`
- Schema: `APP`

Upload `app/app.py` and `app/rag_engine.py`, set `app.py` as the main file, click **Run**.

---

## Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `faker` | 24.0.0 | Synthetic patient data generation |
| `pandas` | 2.2.3 | CSV output (cp313 wheel available) |
| `snowflake-snowpark-python` | 1.55.0 | Snowflake session + SQL execution |
| `snowflake-ml-python` | 2.0.0 | Cortex AI Python helpers |
| `snowflake-core` | 1.13.1 | Cortex Search SDK |
| `snowflake-connector-python` | 4.7.3 | Standalone connections |
| `python-dotenv` | 1.0.1 | Load env vars from `.env` |
| `streamlit` | 1.35.0 | Local testing only (bundled in Snowsight) |

> All versions updated for Python 3.13 compatibility. The original project was pinned to versions that only supported Python ≤ 3.12.

---

## Key Technical Decisions

### Why SQL-based risk and care gap detection?
Both `RISK_TIER` and `CARE_GAP_STATUS` are computed by deterministic SQL rules — no LLM inference involved. This ensures consistency, auditability, and zero hallucination risk for clinical flags that affect patient safety decisions.

```sql
-- Risk stratification
CASE WHEN AGE > 65 AND total_claims_cost > 25000 THEN 'HIGH RISK' ELSE 'LOW RISK' END

-- Care gap (HEDIS NQF-0059)
CASE WHEN has_diabetes_dx = 1
      AND (last_hba1c_date IS NULL
           OR last_hba1c_date < DATEADD('month', -12, CURRENT_DATE()))
     THEN 'GAP: Overdue HbA1c Lab' ELSE 'NO GAP' END
```

### Why Dual-RAG?
A single RAG arm — either structured data or documents alone — is insufficient for clinical reasoning:
- Structured data alone can't explain *why* a medication is dangerous
- Documents alone don't know *this specific patient's* lab values

Dual-RAG combines both: Arm 1 gives patient-specific context, Arm 2 gives regulatory grounding.

### Why Cortex Search over raw vector embedding?
Cortex Search provides hybrid search (semantic + lexical) with incremental refresh, built-in embedding, and filter attributes — all managed by Snowflake. No external vector database, no embedding pipeline to maintain.

### Why `.txt` files instead of PDFs?
Clinical documents are plain text. `AI_PARSE_DOCUMENT` with `page_split: true` only works for PDF/DOCX/PPTX — for `.txt` it returns the raw content directly. We load the text via Python instead, which is equivalent and avoids unnecessary file format conversion. A PDF upgrade path is documented in `05_parsed_clinical_docs.sql`.

### Citation enforcement
The LLM is instructed via system prompt to append `[Doc: <filename>, Page: <n>]` after every factual claim. If no evidence exists in either context, it must respond with `Insufficient evidence.` — preventing hallucination beyond the provided data.

---

## Copilot System Prompt

```
You are the SynapseCortex AI Clinical Regulatory Copilot.
Synthesize answers STRICTLY using:
  - CONTEXT A: Patient 360 Structured Data
  - CONTEXT B: Clinical Document Chunks from vector search

For EVERY factual claim, append: [Doc: <file_name>, Page: <page_number>]
If no evidence exists in either context, respond: Insufficient evidence.
Do NOT use any prior training knowledge beyond the two provided contexts.
```

---

## Git History

| Commit | Description |
|--------|-------------|
| `cf4457c` | Dual-mode session in app.py + snowflake.yml |
| `da69e26` | Fix Complete import for Streamlit in Snowflake |
| `4d76a1c` | Updated seed CSVs + UUID_STRING fix in script 05 |
| `72acf4f` | Python 3.13 + snowflake-ml 2.0 compatibility fixes |
| `97b4e15` | Bump dependencies for Python 3.13 |
| `5dc964e` | Seed CSVs + .gitignore |
| `5fb53c9` | Streamlit in Snowflake application |
| `126dd55` | requirements.txt + initial README |
| `9403fa3` | Patient 360 view + Dual-RAG engine |
| `6faa7cf` | Cortex document parsing + Search Service |
| `70f641d` | Data foundation — DDL, faker, clinical docs |

---

<div align="center">

*Built for the Snowflake AI Data Engineering Hackathon · September 2026*

*Snowflake Cortex AI · llama3.3-70b · Streamlit in Snowflake · Python 3.13*

**Live App →** [https://app.snowflake.com/streamlit/cnwxskg/mw91931/#/apps/b2pmsuf3ml5nmm3cmolf](https://app.snowflake.com/streamlit/cnwxskg/mw91931/#/apps/b2pmsuf3ml5nmm3cmolf)

</div>
