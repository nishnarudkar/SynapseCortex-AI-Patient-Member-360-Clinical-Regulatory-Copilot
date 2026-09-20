# SynapseCortex AI — Database Schema Reference

## Database Architecture

All database objects reside within the database `SYNAPSE_HEALTH` and are partitioned across three operational schemas: `RAW`, `TRANSFORMED`, and `APP`.

---

## 1. RAW Schema

The `RAW` schema contains raw ingested tables and internal file staging areas.

### Table: `RAW.PATIENTS`
Stores patient demographics, insurance plan assignments, and baseline clinical attributes.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `PATIENT_ID` | `VARCHAR(64)` | `PRIMARY KEY` | Unique patient identifier (e.g. `HERO-PT-001`) |
| `FIRST_NAME` | `VARCHAR(50)` | `NOT NULL` | Patient given name |
| `LAST_NAME` | `VARCHAR(50)` | `NOT NULL` | Patient surname |
| `FULL_NAME` | `VARCHAR(100)` | `NOT NULL` | Full name string |
| `BIRTH_DATE` | `DATE` | `NOT NULL` | Patient date of birth |
| `GENDER` | `VARCHAR(10)` | `NOT NULL` | Administrative gender (Male/Female) |
| `INSURANCE_PLAN` | `VARCHAR(50)` | `NOT NULL` | Coverage plan type (Medicare, Commercial PPO) |
| `CREATED_AT` | `TIMESTAMP_NTZ` | `DEFAULT CURRENT_TIMESTAMP()` | Record ingestion timestamp |

### Table: `RAW.ENCOUNTERS`
Logs longitudinal clinical visits and encounters across care settings.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `ENCOUNTER_ID` | `VARCHAR(64)` | Unique visit identifier |
| `PATIENT_ID` | `VARCHAR(64)` | Foreign key referencing `RAW.PATIENTS` |
| `ENCOUNTER_DATE` | `DATE` | Date of clinical service |
| `ENCOUNTER_TYPE` | `VARCHAR(30)` | Type of visit (Inpatient, Outpatient, ED, Telehealth) |
| `FACILITY_NAME` | `VARCHAR(100)` | Name of treating medical center |
| `PRIMARY_DX_CODE` | `VARCHAR(15)` | Primary ICD-10 diagnosis code |
| `PRIMARY_DX_DESC` | `VARCHAR(255)` | ICD-10 diagnosis text description |
| `DISCHARGE_STATUS` | `VARCHAR(50)` | Discharge outcome status |

### Table: `RAW.CLAIMS`
Captures medical procedure and pharmacy billing transactions.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `CLAIM_ID` | `VARCHAR(64)` | Unique billing claim ID |
| `PATIENT_ID` | `VARCHAR(64)` | Foreign key referencing `RAW.PATIENTS` |
| `CLAIM_DATE` | `DATE` | Date claim submitted |
| `CLAIM_TYPE` | `VARCHAR(20)` | Professional, Institutional, or Pharmacy |
| `PROCEDURE_DESC` | `VARCHAR(255)` | Service description / Procedure name |
| `DRUG_NAME` | `VARCHAR(100)` | Dispensed drug name (if pharmacy claim) |
| `BILLED_AMOUNT` | `NUMBER(12,2)` | Billed charge amount |
| `PAID_AMOUNT` | `NUMBER(12,2)` | Paid reimbursement amount |
| `CLAIM_STATUS` | `VARCHAR(20)` | Paid, Denied, Pending |

### Table: `RAW.LABS`
Contains quantitative LOINC-coded laboratory observations.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `LAB_ID` | `VARCHAR(64)` | Unique lab observation ID |
| `PATIENT_ID` | `VARCHAR(64)` | Foreign key referencing `RAW.PATIENTS` |
| `RESULT_DATE` | `DATE` | Lab collection/specimen date |
| `LAB_TEST_NAME` | `VARCHAR(100)` | LOINC test description (e.g. eGFR, HbA1c, Creatinine) |
| `RESULT_VALUE` | `NUMBER(10,2)` | Quantitative lab value |
| `RESULT_UNIT` | `VARCHAR(20)` | Measurement unit (mL/min, %, mg/dL) |
| `REFERENCE_RANGE` | `VARCHAR(50)` | Expected reference interval |
| `ABNORMAL_FLAG` | `VARCHAR(10)` | Flag indicator (`H`, `L`, `HH`, `LL`, `A`, or null) |
| `RESULT_STATUS` | `VARCHAR(20)` | Final, Amended, Pending |
| `PERFORMING_LAB` | `VARCHAR(100)` | Processing laboratory name |

---

## 2. TRANSFORMED Schema

### Table: `TRANSFORMED.PARSED_CLINICAL_DOCS`
Stores document chunks extracted from encounter notes and FDA inserts. `CHANGE_TRACKING = TRUE` is enabled.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `DOC_ID` | `VARCHAR(64)` | Unique document chunk key |
| `FILE_NAME` | `VARCHAR(255)` | Relative file path |
| `PAGE_NUMBER` | `INTEGER` | Document page index |
| `DOC_CATEGORY` | `VARCHAR(50)` | Clinical Note vs FDA Package Insert |
| `HERO_PATIENT` | `VARCHAR(64)` | Associated patient identifier |
| `PAGE_TEXT` | `VARCHAR` | Parsed body text content |
| `PARSED_AT` | `TIMESTAMP_NTZ` | Ingestion timestamp |

### View: `TRANSFORMED.PATIENT_360_VIEW`
4-way join view calculating longitudinal clinical intelligence attributes.

```sql
SELECT
    p.PATIENT_ID,
    p.FULL_NAME,
    p.AGE,
    p.GENDER,
    p.INSURANCE_PLAN,
    COUNT(DISTINCT c.CLAIM_ID) AS CLAIM_COUNT,
    SUM(c.PAID_AMOUNT) AS TOTAL_CLAIMS_COST,
    -- Deterministic Risk Stratification
    CASE
        WHEN p.AGE >= 65 AND SUM(c.PAID_AMOUNT) > 30000 THEN 'HIGH RISK'
        WHEN COUNT(DISTINCT e.PRIMARY_DX_CODE) >= 5 THEN 'HIGH RISK'
        ELSE 'LOW RISK'
    END AS RISK_TIER,
    -- Deterministic Care Gap Logic (HEDIS NQF-0059)
    CASE
        WHEN l_hba1c.RESULT_DATE IS NULL OR l_hba1c.RESULT_DATE < DATEADD(month, -12, CURRENT_DATE())
        THEN 'GAP: Overdue HbA1c Lab'
        ELSE 'NO GAP'
    END AS CARE_GAP_STATUS,
    -- Deterministic Safety Contraindication Check
    CASE
        WHEN med.DRUG_NAME ILIKE '%metformin%' AND l_egfr.RESULT_VALUE < 45
        THEN 'ALERT: Metformin active with eGFR < 45'
        ELSE NULL
    END AS DRUG_SAFETY_FLAG
FROM RAW.PATIENTS p
LEFT JOIN RAW.ENCOUNTERS e ON p.PATIENT_ID = e.PATIENT_ID
LEFT JOIN RAW.CLAIMS c ON p.PATIENT_ID = c.PATIENT_ID
...
```

---

## 3. APP Schema

### Table: `APP.PATIENT_360_SNAPSHOT`
Materialized 50-row table refreshed from `PATIENT_360_VIEW` for sub-second UI rendering and RAG prompt injection.

### Search Service: `APP.CLINICAL_DOC_SEARCH`
Snowflake Cortex Search Service configured on `TRANSFORMED.PARSED_CLINICAL_DOCS` using `snowflake-arctic-embed-l-v2.0`.
