# SynapseCortex AI – Patient 360 & Clinical Regulatory Copilot

**Hackathon:** Snowflake AI Data Engineering – Patient 360 & Clinical Copilot  
**Built with:** Snowflake · Python (Faker) · SnowSQL · Cortex AI  
**Status:** Data Foundation Complete ✅

---

## What Is SynapseCortex AI?

SynapseCortex AI is a unified clinical intelligence platform built on Snowflake that provides:

- **Patient 360 View** – A single longitudinal record combining demographics, encounters, claims, and labs for every member.
- **Clinical Regulatory Copilot** – AI-assisted detection of medication safety violations, care gaps, and high-risk patient flags, grounded in FDA prescribing guidelines, HEDIS quality measures, and ADA clinical standards.
- **Unstructured Clinical NLP** – Free-text clinical notes and FDA package inserts staged in an encrypted Snowflake internal stage, ready for Cortex AI document intelligence.

---

## Repository Structure

```
SynapseCortex AI Patient & Member 360 & Clinical Regulatory Copilot/
│
├── snowflake/
│   ├── ddl/
│   │   ├── 01_database_schemas.sql     ← Create SYNAPSE_HEALTH DB + RAW/TRANSFORMED/APP schemas
│   │   ├── 02_raw_tables.sql           ← DDL for PATIENTS, ENCOUNTERS, CLAIMS, LABS (with FKs)
│   │   └── 03_clinical_stage.sql       ← Internal stage CLINICAL_STAGE (SNOWFLAKE_SSE) + file formats
│   └── stage/
│       └── 04_stage_and_load.sql       ← PUT clinical docs + COPY INTO table loads + validation queries
│
├── data_generator/
│   ├── generate_synthetic_data.py      ← Faker script: 50 patients, 3 hero cases, referential integrity
│   └── output/                         ← Generated CSV files (created at runtime)
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
│       ├── fda_insert_METFORMIN.txt                    ← FDA PI: Metformin – CKD contraindication
│       ├── fda_insert_HBA1C_MONITORING_STANDARD.txt   ← HEDIS/ADA HbA1c monitoring reference
│       └── fda_insert_POLYPHARMACY_HIGH_RISK.txt       ← Polypharmacy + drug-drug interaction guide
│
└── Readme.md
```

---

## Hero Test Cases

Three clinically precise hero patients are embedded in the dataset to drive demo scenarios:

| # | Patient | Age | Profile | AI Copilot Alert |
|---|---------|-----|---------|-----------------|
| 1 | **Robert Callahan** (`HERO-PT-001`) | 58 | CKD Stage 3 (eGFR 38) + active Metformin 1000mg BID | ⚠️ **Safety Violation** – Metformin contraindicated at eGFR < 30; high-risk zone at eGFR 30–44 |
| 2 | **Linda Moreno** (`HERO-PT-002`) | 62 | Type 2 Diabetes + last HbA1c 14 months ago (7.8%) | ⚠️ **Care Gap** – HbA1c overdue per ADA/HEDIS CDC NQF-0059; CMS Star Rating risk |
| 3 | **James Whitfield** (`HERO-PT-003`) | 71 | 8 chronic diagnoses, 3 encounters in 2026, 9-drug polypharmacy | ⚠️ **High Risk** – Total billed claims $51,755; 5 DDI flags; 38% 30-day readmission risk |

---

## Data Architecture

```
SYNAPSE_HEALTH (Database)
│
├── RAW (Schema)                   ← Immutable landing zone
│   ├── PATIENTS                   PK: PATIENT_ID (UUID)
│   ├── ENCOUNTERS                 FK → PATIENTS
│   ├── CLAIMS                     FK → PATIENTS, ENCOUNTERS
│   ├── LABS                       FK → PATIENTS, ENCOUNTERS
│   └── @CLINICAL_STAGE            Internal stage (SNOWFLAKE_SSE encryption)
│       ├── clinical_notes/        Free-text encounter notes (AI-parseable)
│       ├── fda_inserts/           FDA/clinical regulatory reference docs
│       └── data/                  Bulk CSV loads
│
├── TRANSFORMED (Schema)           ← Curated, conformed entities (future build)
│   └── (views and tables TBD)
│
└── APP (Schema)                   ← Patient 360 views, risk scores, copilot outputs
    └── (feature tables TBD)
```

---

## Quick Start

### Prerequisites

```
Python >= 3.10
pip install faker==24.0.0 pandas==2.2.2
Snowflake account with SYSADMIN or equivalent role
SnowSQL CLI (for PUT commands)
```

### Step 1 – Set up Snowflake objects

Run the DDL scripts **in order** from a Snowflake worksheet or SnowSQL:

```sql
-- In Snowflake worksheet (or SnowSQL):
!source snowflake/ddl/01_database_schemas.sql
!source snowflake/ddl/02_raw_tables.sql
!source snowflake/ddl/03_clinical_stage.sql
```

### Step 2 – Generate synthetic data

```bash
cd data_generator
python generate_synthetic_data.py
```

Expected output:
```
─── Dataset Summary ────────────────────────────────────────
  Patients   :    50  (50 total, 3 hero + 47 synthetic)
  Encounters :   ~85
  Claims     :  ~200
  Labs       :  ~180

  Hero 1 [HERO-PT-001-...] – CKD N18.3 + Metformin → Safety Violation
  Hero 2 [HERO-PT-002-...] – Diabetes + No HbA1c 14mo → Care Gap
  Hero 3 [HERO-PT-003-...] – Multi-chronic, Claims = $51,755.00 → High Risk ✓
────────────────────────────────────────────────────────────

  ✓ Wrote   50 rows → output/patients.csv
  ✓ Wrote   ~85 rows → output/encounters.csv
  ✓ Wrote  ~200 rows → output/claims.csv
  ✓ Wrote  ~180 rows → output/labs.csv
```

### Step 3 – Stage files and load tables

Edit `snowflake/stage/04_stage_and_load.sql` and replace `<LOCAL_BASE_PATH>` and `<LOCAL_DATA_PATH>` with your machine's absolute paths, then run:

```bash
# Using SnowSQL:
snowsql -a <account> -u <user> -f snowflake/stage/04_stage_and_load.sql
```

Or execute each PUT/COPY block manually in a Snowflake worksheet.

### Step 4 – Validate

The script includes ready-to-run validation queries at the bottom of `04_stage_and_load.sql`:

```sql
-- Row counts across all four tables
-- Hero 1: Metformin + CKD confirmation
-- Hero 2: HbA1c care gap (days since last test)
-- Hero 3: Total claims > $50,000
-- Referential integrity check (0 orphan rows expected)
```

---

## Clinical Documents in @CLINICAL_STAGE

All 8 documents are staged under `@RAW.CLINICAL_STAGE` and are ready for **Snowflake Cortex AI** document intelligence:

| Path in Stage | Purpose |
|---|---|
| `clinical_notes/hero1_note_ROBERT_CALLAHAN.txt` | Full clinical encounter note with embedded ⚠️ safety alert |
| `clinical_notes/hero2_note_LINDA_MORENO.txt` | Office visit note documenting diabetes care gap |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt` | NSTEMI/PCI inpatient discharge summary |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt` | COPD exacerbation pulmonology follow-up |
| `clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt` | ED note: hypertensive crisis + medication gap |
| `fda_inserts/fda_insert_METFORMIN.txt` | Full FDA-style PI with Black Box Warning + copilot alert |
| `fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt` | HEDIS CDC NQF-0059 + ADA monitoring standards |
| `fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt` | Beers Criteria + STOPP/START + DDI analysis |

---

## RAW Table Schema Summary

### PATIENTS
| Column | Type | Notes |
|--------|------|-------|
| PATIENT_ID | VARCHAR(36) | PK – UUID |
| FIRST_NAME, LAST_NAME | VARCHAR | |
| DATE_OF_BIRTH | DATE | |
| AGE | NUMBER(3,0) | Computed at ingest |
| GENDER, RACE, ETHNICITY | VARCHAR | |
| INSURANCE_ID, INSURANCE_PLAN | VARCHAR | |
| PRIMARY_CARE_NPI | VARCHAR(20) | |
| ACTIVE_FLAG | BOOLEAN | |

### ENCOUNTERS
| Column | Type | Notes |
|--------|------|-------|
| ENCOUNTER_ID | VARCHAR(36) | PK – UUID |
| PATIENT_ID | VARCHAR(36) | FK → PATIENTS |
| ENCOUNTER_DATE, ENCOUNTER_TYPE | | |
| PRIMARY_DX_CODE, PRIMARY_DX_DESC | | ICD-10-CM |
| SECONDARY_DX_CODES, PROCEDURE_CODES, PRESCRIPTION_LIST | VARIANT | JSON arrays |
| NOTES_REF | VARCHAR | Pointer to `@CLINICAL_STAGE` file |

### CLAIMS
| Column | Type | Notes |
|--------|------|-------|
| CLAIM_ID | VARCHAR(36) | PK |
| PATIENT_ID | VARCHAR(36) | FK → PATIENTS |
| ENCOUNTER_ID | VARCHAR(36) | FK → ENCOUNTERS (nullable for pharmacy) |
| CLAIM_TYPE | VARCHAR | Medical \| Pharmacy |
| BILLED_AMOUNT, ALLOWED_AMOUNT, PAID_AMOUNT | NUMBER(12,2) | |
| CLAIM_STATUS | VARCHAR | Paid \| Denied \| Pending \| Adjusted |
| NDC_CODE, DRUG_NAME | | Pharmacy claims |

### LABS
| Column | Type | Notes |
|--------|------|-------|
| LAB_ID | VARCHAR(36) | PK |
| PATIENT_ID | VARCHAR(36) | FK → PATIENTS |
| ENCOUNTER_ID | VARCHAR(36) | FK → ENCOUNTERS |
| LAB_TEST_CODE | VARCHAR(30) | LOINC code |
| RESULT_VALUE, RESULT_UNIT, REFERENCE_RANGE | VARCHAR | |
| ABNORMAL_FLAG | VARCHAR | H \| L \| HH \| LL \| N \| A |

---

## Next Steps (TRANSFORMED & APP Layers)

| Layer | Planned Objects |
|-------|----------------|
| `TRANSFORMED` | `PATIENT_TIMELINE` view (unified encounter + labs + claims per patient) |
| `TRANSFORMED` | `MEDICATION_SAFETY_FLAGS` table (FK contraindications vs. active Rx) |
| `TRANSFORMED` | `CARE_GAP_REGISTRY` table (HEDIS measure gaps per patient per year) |
| `APP` | `PATIENT_360_VIEW` – full longitudinal member profile |
| `APP` | `RISK_SCORE_TABLE` – SynapseCortex AI predicted risk scores |
| `APP` | `COPILOT_ALERTS` – structured output from Cortex AI document analysis |

---

*SynapseCortex AI – Hackathon Build | Data Engineering Foundation | September 2026*
