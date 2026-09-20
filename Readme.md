<div align="center">

# 🧠 SynapseCortex AI
### Patient 360 & Clinical Regulatory Copilot

*A Snowflake-native clinical intelligence platform unifying structured EHR data, unstructured clinical documentation, and generative AI under strict citation enforcement.*

[![Snowflake Cortex AI](https://img.shields.io/badge/Snowflake-Cortex%20AI-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)](https://www.snowflake.com/en/data-cloud/cortex/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-in%20Snowflake-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
[![LLM](https://img.shields.io/badge/LLM-llama3.3--70b-7C3AED?style=for-the-badge)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
[![Embeddings](https://img.shields.io/badge/Embeddings-arctic--embed--l--v2.0-0284C7?style=for-the-badge)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search)
[![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)](LICENSE)

<br/>

[🚀 **Open Live Application in Snowsight**](https://app.snowflake.com/streamlit/cnwxskg/mw91931/#/apps/b2pmsuf3ml5nmm3cmolf) &nbsp;•&nbsp; [📐 **Architecture**](#-architecture) &nbsp;•&nbsp; [🧪 **Hero Demo Cases**](#-hero-demo-walkthrough) &nbsp;•&nbsp; [⚙️ **Setup Guide**](#%EF%B8%8F-setup--deployment-guide)

</div>

---

## 📋 Table of Contents

- [Executive Summary](#-executive-summary)
- [Key Platform Capabilities](#-key-platform-capabilities)
- [Elevator Pitch](#-elevator-pitch)
- [Architecture](#-architecture)
  - [End-to-End Data Pipeline](#end-to-end-data-pipeline)
  - [Dual-RAG Intelligence Engine](#dual-rag-intelligence-engine)
- [Hero Demo Walkthrough](#-hero-demo-walkthrough)
  - [Hero 1 — Safety Violation (Robert Callahan)](#hero-1--safety-violation-%EF%B8%8F-robert-callahan)
  - [Hero 2 — Care Gap (Linda Moreno)](#hero-2--care-gap--linda-moreno)
  - [Hero 3 — High Risk & Polypharmacy (James Whitfield)](#hero-3--high-risk--james-whitfield)
- [Snowflake Object Schema Inventory](#-snowflake-object-schema-inventory)
- [Clinical & FDA Reference Documents](#-clinical--fda-reference-documents)
- [Setup & Deployment Guide](#%EF%B8%8F-setup--deployment-guide)
- [Security, Compliance & Governance](#-security-compliance--governance)
- [License & Acknowledgments](#-license--acknowledgments)

---

## 💡 Executive Summary

Healthcare organizations face an overwhelming challenge: **over 80% of critical clinical data resides in unstructured clinical notes and regulatory filings**, while structured longitudinal patient records remain trapped in siloed relational databases. Clinicians and care managers spend hours manually correlating EHR lab values with FDA package inserts and quality guidelines.

**SynapseCortex AI** solves this problem by providing a single, Snowflake-native clinical decision support system that answers three foundational healthcare questions:

| Clinical Challenge | How SynapseCortex AI Answers It | Business & Regulatory Impact |
| :--- | :--- | :--- |
| **Medication Safety** | Detects drug–disease & drug–lab contraindications by cross-referencing FDA package inserts with real-time eGFR/Creatinine lab values in SQL. | Prevents adverse drug events (ADEs), reduces ICU admissions, and minimizes liability. |
| **Care Quality Gaps** | Evaluates longitudinal lab histories against CMS Star / HEDIS NQF-0059 guidelines to flag overdue diabetic screenings. | Protects health plan quality ratings (e.g., maintaining 4+ Star status) and value-based care revenue. |
| **Risk Stratification** | Calculates deterministic risk tiers over multi-year claims cost, age, chronic condition burden, and 30-day readmission risk. | Focuses complex care management resources on top-decile high-cost, high-risk members. |

---

## ✨ Key Platform Capabilities

- **Unified Patient 360 View**: 4-way SQL join of `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, and `LABS` with dynamic risk tiering and safety rule evaluation.
- **Cortex Document Search Service**: Hybrid semantic + lexical vector search over clinical encounter notes and FDA package inserts powered by `snowflake-arctic-embed-l-v2.0`.
- **Dual-RAG Clinical Copilot**: Evidence-grounded conversational engine driven by `llama3.3-70b` with mandatory inline citation enforcement (`[Doc: <file>, Page: <n>]`).
- **Clinical Care Action Dispatcher**: Interactive workflow dispatcher supporting simulated MCP triggers for Jira, Slack, Email, and PagerDuty notifications.
- **Zero Data Movement**: Built 100% inside Snowflake — storage, vector indexing, LLM inference, and Streamlit UI execute entirely within the customer's governance perimeter.

---

## 🎙️ Elevator Pitch

> *"SynapseCortex AI is a clinical intelligence platform built natively on Snowflake. It unifies a patient's entire medical record — diagnoses, pharmacy claims, lab results, and encounter notes — with FDA regulatory guidelines and HEDIS quality standards inside a single AI-powered application.*
>
> *The platform automatically highlights critical safety violations, overdue preventive care gaps, and high-risk patients. When a clinician asks a question, SynapseCortex AI performs vector search over FDA package inserts and clinical notes using Cortex Search, then uses llama3.3-70b to synthesize a cited answer grounded strictly in evidence — with zero hallucination.*
>
> *Everything runs natively inside Snowflake with enterprise-grade governance and zero external data export."*

---

## 📐 Architecture

### End-to-End Data Pipeline

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         SYNAPSE_HEALTH  (Snowflake Database)                           │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ RAW SCHEMA (Landing Layer)                                                       │  │
│  │  • PATIENTS (50 synthetic records)    • CLAIMS (215 medical/pharmacy records)   │  │
│  │  • ENCOUNTERS (102 clinical visits)   • LABS (150 LOINC-coded lab results)       │  │
│  │  • @CLINICAL_STAGE (Internal stage with 8 clinical & FDA reference files)        │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                            │
│                                           ▼  Python Parsers + SQL Transforms           │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ TRANSFORMED SCHEMA (Enriched Layer)                                              │  │
│  │  • PARSED_CLINICAL_DOCS (Document chunks with metadata & CHANGE_TRACKING=TRUE)   │  │
│  │  • PATIENT_360_VIEW (4-way join + RISK_TIER + CARE_GAP_STATUS + DRUG_SAFETY)     │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                            │
│                                           ▼  Cortex Search Service + Snapshot          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ APP SCHEMA (Serving & Application Layer)                                          │  │
│  │  • CLINICAL_DOC_SEARCH (Cortex Search Service using arctic-embed-l-v2.0)        │  │
│  │  • PATIENT_360_SNAPSHOT (Materialized 50-row table for instant RAG lookup)        │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                            │
│                                           ▼  Streamlit in Snowflake                    │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ app/app.py (Streamlit Web UI)                                                    │  │
│  │  • Tab 1: Patient 360 Dashboard (Metrics, Encounters, Labs, Medications, Claims)  │  │
│  │  • Tab 2: Clinical & Regulatory Copilot (Dual-RAG Chat + Care Action Dispatcher)  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Dual-RAG Intelligence Engine

```
                       Clinician Query
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  Enrich Query with Patient Metadata       │
        │  (ICD-10 codes, active drugs, lab values) │
        └─────────────────────┬─────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
  ┌───────────────────────┐       ┌───────────────────────┐
  │  Cortex Search Engine │       │ Structured Snapshot   │
  │  (Vector Search over  │       │ (SQL Patient 360      │
  │  Clinical & FDA Docs) │       │  Demographics & Labs) │
  └───────────┬───────────┘       └───────────┬───────────┘
              │                               │
              │  Top-5 Relevant Chunks        │  Patient 360 JSON
              └───────────────┬───────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  Dual-RAG Context Synthesizer             │
        │  [System] Strict Citation Instructions    │
        │  [Context A] Structured Patient 360       │
        │  [Context B] Retrieved Document Chunks    │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  SNOWFLAKE.CORTEX.COMPLETE                │
        │  Model: llama3.3-70b (Temp: 0.05)         │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  Evidence-Grounded Response               │
        │  Inline Citations: [Doc: file, Page: n]   │
        └───────────────────────────────────────────┘
```

---

## 🧪 Hero Demo Walkthrough

The synthetic cohort embeds three clinically precise **Hero Patients** designed for demonstration and validation.

### Hero 1 — Safety Violation 🔴 `Robert Callahan`

- **Demographics**: 58-year-old male | Insurance: Medicare Advantage | Patient ID: `HERO-PT-001`
- **Clinical Profile**: CKD Stage 3 (eGFR 38 mL/min, Creatinine 2.4 mg/dL) | Active prescription: **Metformin 1000mg BID**
- **Triggered Alert**: `🚨 ALERT: Metformin active with eGFR < 45`

#### Demo Steps:
1. Open the app sidebar and select **⚠️ Hero 1 – Safety Violation | Robert Callahan**.
2. Navigate to **Tab 1 (Patient 360 Dashboard)**:
   - Observe the **Drug Safety Check** card displaying the red alert badge.
   - Inspect the **Lab Results** table — eGFR (38 mL/min) is highlighted red as abnormal.
   - Inspect the **Active Medications** table — Metformin is flagged with a red alert background.
3. Switch to **Tab 2 (Clinical & Regulatory Copilot)**:
   - Click the suggested query: **"Is Metformin contraindicated for this patient given their kidney function?"**
   - The copilot synthesizes the response citing the FDA Black Box Warning:
     > *"Metformin is contraindicated in patients with eGFR < 30 mL/min and requires dose reduction / monitoring in eGFR 30–44 mL/min due to risk of severe lactic acidosis [Doc: fda_inserts/fda_insert_METFORMIN.txt, Page: 1]. The patient's current eGFR is 38 mL/min [Doc: Structured Data, Page: N/A]."*

---

### Hero 2 — Care Gap 🟡 `Linda Moreno`

- **Demographics**: 62-year-old female | Insurance: Commercial PPO | Patient ID: `HERO-PT-002`
- **Clinical Profile**: Type 2 Diabetes Mellitus | Last HbA1c: **7.8%** on 2025-07-11 (14 months overdue)
- **Triggered Alert**: `⚠️ GAP: Overdue HbA1c Lab`

#### Demo Steps:
1. Select **⚠️ Hero 2 – Care Gap | Linda Moreno** in the sidebar.
2. View **Tab 1**:
   - The **Care Quality Gap** metric card highlights `⚠️ GAP: Overdue HbA1c Lab`.
   - Secondary metric **Last HbA1c** shows `7.8%` with delta date over 1 year ago.
3. View **Tab 2**:
   - Click: **"What care gaps exist for this diabetic patient?"**
   - Copilot response highlights:
     > *"The patient has an unclosed care gap under HEDIS NQF-0059 for HbA1c testing [Doc: Structured Data, Page: N/A]. Per ADA 2026 guidelines, diabetic patients with HbA1c > 7.0% require testing every 6 months [Doc: fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt, Page: 1]. Delaying testing risks CMS Star Rating degradation from 4 to 3 Stars."*

---

### Hero 3 — High Risk & Polypharmacy 🔴 `James Whitfield`

- **Demographics**: 71-year-old male | Insurance: Medicare | Patient ID: `HERO-PT-003`
- **Clinical Profile**: 8 Chronic Conditions | 9-Drug Polypharmacy | 3 Inpatient/ED visits | YTD Claims: **$51,755**
- **Triggered Alert**: `🔴 HIGH RISK` + 5 Drug–Drug Interaction flags

#### Demo Steps:
1. Select **⚠️ Hero 3 – High Risk | James Whitfield** in the sidebar.
2. View **Tab 1**:
   - Total Claims Cost shows `$51,755`.
   - Multiple abnormal labs (Potassium, Creatinine, BNP) highlighted in red.
3. View **Tab 2**:
   - Click: **"Summarise the drug-drug interactions in this patient's current regimen."**
   - Copilot response details multi-drug interaction vectors (Carvedilol + Albuterol, Lisinopril + Furosemide) backed by citations from `fda_insert_POLYPHARMACY_HIGH_RISK.txt`.
   - Click **⚡ Dispatch Care Action** to trigger an automated case management alert payload for Jira or PagerDuty.

---

## 📊 Snowflake Object Schema Inventory

All database objects are organized cleanly into four isolated schemas under `SYNAPSE_HEALTH`:

| Schema | Object Name | Object Type | Description / Purpose |
| :--- | :--- | :--- | :--- |
| **`RAW`** | `PATIENTS` | Table | 50 synthetic patient demographic records |
| **`RAW`** | `ENCOUNTERS` | Table | 102 outpatient, inpatient, ED, and telehealth encounter logs |
| **`RAW`** | `CLAIMS` | Table | 215 medical and pharmacy claim records |
| **`RAW`** | `LABS` | Table | 150 LOINC-coded laboratory test results |
| **`RAW`** | `@CLINICAL_STAGE` | Internal Stage | SSE-encrypted stage containing raw text clinical notes & FDA inserts |
| **`TRANSFORMED`** | `PARSED_CLINICAL_DOCS` | Table | Extracted text chunks with file metadata (`CHANGE_TRACKING=TRUE`) |
| **`TRANSFORMED`** | `PATIENT_360_VIEW` | View | 4-way join view with embedded SQL logic for Risk Tier & Care Gaps |
| **`APP`** | `CLINICAL_DOC_SEARCH` | Cortex Search | Hybrid vector search service (`arctic-embed-l-v2.0`) |
| **`APP`** | `PATIENT_360_SNAPSHOT` | Table | Materialized 50-row Patient 360 record optimized for low-latency RAG |

---

## 📄 Clinical & FDA Reference Documents

Eight staged documents provide the unstructured knowledge base indexed by Cortex Search:

| Document Path | Document Category | Patient / Context | Key Clinical Content |
| :--- | :--- | :--- | :--- |
| `hero1_note_ROBERT_CALLAHAN.txt` | Clinical Note | Hero 1 | Nephrology consult note details eGFR 38 mL/min & Metformin regimen |
| `hero2_note_LINDA_MORENO.txt` | Clinical Note | Hero 2 | Primary care visit note detailing overdue HbA1c lab test |
| `hero3_note_JAMES_WHITFIELD_inpatient.txt` | Clinical Note | Hero 3 | Inpatient discharge summary for NSTEMI / PCI intervention |
| `hero3_note_JAMES_WHITFIELD_outpatient.txt` | Clinical Note | Hero 3 | Cardiology follow-up note for COPD exacerbation & polypharmacy |
| `hero3_note_JAMES_WHITFIELD_ED.txt` | Clinical Note | Hero 3 | Emergency department note for acute hypertensive crisis |
| `fda_insert_METFORMIN.txt` | FDA Package Insert | FDA Reference | Dosing contraindications, eGFR thresholds, and Black Box Warnings |
| `fda_insert_HBA1C_MONITORING_STANDARD.txt` | Quality Guideline | Clinical Reference | HEDIS NQF-0059 & ADA 2026 diabetes monitoring compliance standards |
| `fda_insert_POLYPHARMACY_HIGH_RISK.txt` | Clinical Reference | Clinical Reference | Beers Criteria & Drug-Drug Interaction (DDI) risk evaluation matrix |

---

## ⚙️ Setup & Deployment Guide

### Prerequisites

- **Python**: Version 3.10+ (Tested on Python 3.13)
- **Snowflake Account**: Enterprise Edition with `ACCOUNTADMIN` or equivalent administrative role.
- **Privileges**: Granted `SNOWFLAKE.CORTEX_USER` database role for Cortex Search & Complete API access.

### 1. Repository Setup & Environment Configuration

Clone the repository and install required dependencies:

```bash
git clone https://github.com/nishnarudkar/SynapseCortex-AI-Patient-Member-360-Clinical-Regulatory-Copilot.git
cd SynapseCortex-AI-Patient-Member-360-Clinical-Regulatory-Copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=SYNAPSE_WH
SNOWFLAKE_DATABASE=SYNAPSE_HEALTH
SNOWFLAKE_SCHEMA=APP
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

---

### 2. Database DDL & Ingestion Pipeline

Execute the Snowflake DDL scripts in sequence to construct the database objects and populate data:

```bash
# Step 1: Upload seed CSVs & clinical documents to Snowflake stage
python upload_to_snowflake.py

# Step 2: Parse clinical documents into TRANSFORMED.PARSED_CLINICAL_DOCS
python parse_and_load_docs.py
```

Alternatively, run the DDL scripts directly in **Snowsight Worksheets**:
1. `snowflake/ddl/01_database_schemas.sql` — Creates `SYNAPSE_HEALTH` DB, schemas, and warehouse.
2. `snowflake/ddl/02_raw_tables.sql` — Builds `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, and `LABS` tables.
3. `snowflake/ddl/03_clinical_stage.sql` — Configures internal stage `@CLINICAL_STAGE`.
4. `snowflake/ddl/05_parsed_clinical_docs.sql` — Creates document parsing table.
5. `snowflake/ddl/06_cortex_search_service.sql` — Provisions `CLINICAL_DOC_SEARCH` Cortex Search Service.
6. `snowflake/ddl/08_patient_360_and_copilot.sql` — Creates `PATIENT_360_VIEW` & `PATIENT_360_SNAPSHOT`.

---

### 3. Deploying Streamlit in Snowflake (SiS)

1. Log into **Snowsight**.
2. Navigate to **Projects** → **Streamlit** → Click **+ Streamlit App**.
3. Set the App details:
   - **App Name**: `SynapseCortex AI`
   - **Warehouse**: `SYNAPSE_WH`
   - **Database**: `SYNAPSE_HEALTH`
   - **Schema**: `APP`
4. Replace the default app code with `app/app.py`.
5. Upload `app/rag_engine.py` as a stage file into the same Streamlit package directory.
6. Click **Run** to launch the production application!

---

## 🔒 Security, Compliance & Governance

- **Strict Zero-Hallucination Guardrails**: System prompts mandate strict adherence to retrieved context. Unsubstantiated queries return `Insufficient evidence.`
- **Snowflake Server-Side Encryption (SSE)**: All staged documents and database tables are encrypted at rest using AES-256 (`SNOWFLAKE_SSE`).
- **HIPAA Readiness**: Data processing and LLM inference occur entirely within Snowflake's compliant security perimeter; no data is ever transmitted to third-party public AI APIs.
- **Audit Logging**: All care action dispatches record immutable event payloads with ISO-8601 timestamps for compliance review.

---

## 📜 License & Acknowledgments

Distributed under the **MIT License**. See `LICENSE` for details.

Developed for the **Snowflake Cortex AI Hackathon 2026** leveraging:
- [Snowflake Cortex AI Services](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
- [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- Meta's `llama3.3-70b` and Snowflake's `arctic-embed-l-v2.0` models.
