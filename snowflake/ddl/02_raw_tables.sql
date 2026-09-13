-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 02_raw_tables.sql
-- Purpose : DDL for RAW schema core clinical tables with relational FK constraints
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE SCHEMA RAW;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: PATIENTS
-- Central demographic and clinical profile for every member/patient.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE RAW.PATIENTS (
    PATIENT_ID          VARCHAR(36)     NOT NULL    COMMENT 'UUID primary key',
    FIRST_NAME          VARCHAR(100)    NOT NULL,
    LAST_NAME           VARCHAR(100)    NOT NULL,
    DATE_OF_BIRTH       DATE            NOT NULL,
    AGE                 NUMBER(3,0)     NOT NULL    COMMENT 'Computed at ingest from DOB',
    GENDER              VARCHAR(10)     NOT NULL,
    RACE                VARCHAR(50),
    ETHNICITY           VARCHAR(50),
    ADDRESS_LINE1       VARCHAR(200),
    CITY                VARCHAR(100),
    STATE               VARCHAR(2),
    ZIP_CODE            VARCHAR(10),
    PHONE               VARCHAR(20),
    EMAIL               VARCHAR(200),
    INSURANCE_ID        VARCHAR(50),
    INSURANCE_PLAN      VARCHAR(100),
    PRIMARY_CARE_NPI    VARCHAR(20)     COMMENT 'NPI of assigned primary care provider',
    ACTIVE_FLAG         BOOLEAN         DEFAULT TRUE,
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_PATIENTS PRIMARY KEY (PATIENT_ID)
)
COMMENT = 'Master patient demographic and insurance registry';

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: ENCOUNTERS
-- Every inpatient/outpatient/telehealth visit tied to a patient.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE RAW.ENCOUNTERS (
    ENCOUNTER_ID        VARCHAR(36)     NOT NULL    COMMENT 'UUID primary key',
    PATIENT_ID          VARCHAR(36)     NOT NULL    COMMENT 'FK → PATIENTS.PATIENT_ID',
    ENCOUNTER_DATE      DATE            NOT NULL,
    ENCOUNTER_TYPE      VARCHAR(50)     NOT NULL    COMMENT 'Inpatient | Outpatient | Telehealth | ED',
    FACILITY_NAME       VARCHAR(200),
    FACILITY_NPI        VARCHAR(20),
    ATTENDING_NPI       VARCHAR(20),
    PRIMARY_DX_CODE     VARCHAR(20)     NOT NULL    COMMENT 'ICD-10-CM primary diagnosis',
    PRIMARY_DX_DESC     VARCHAR(500),
    SECONDARY_DX_CODES  VARIANT         COMMENT 'JSON array of additional ICD-10 codes',
    PROCEDURE_CODES     VARIANT         COMMENT 'JSON array of CPT/HCPCS codes',
    PRESCRIPTION_LIST   VARIANT         COMMENT 'JSON array of medications prescribed',
    DISCHARGE_DATE      DATE,
    DISCHARGE_STATUS    VARCHAR(100),
    NOTES_REF           VARCHAR(200)    COMMENT 'Pointer to clinical note file in @CLINICAL_STAGE',
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_ENCOUNTERS PRIMARY KEY (ENCOUNTER_ID),
    CONSTRAINT FK_ENC_PATIENT
        FOREIGN KEY (PATIENT_ID) REFERENCES RAW.PATIENTS(PATIENT_ID)
)
COMMENT = 'All care encounters linked to master patients';

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: CLAIMS
-- Medical and pharmacy claims submitted against encounters.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE RAW.CLAIMS (
    CLAIM_ID            VARCHAR(36)     NOT NULL    COMMENT 'UUID primary key',
    PATIENT_ID          VARCHAR(36)     NOT NULL    COMMENT 'FK → PATIENTS.PATIENT_ID',
    ENCOUNTER_ID        VARCHAR(36)                 COMMENT 'FK → ENCOUNTERS.ENCOUNTER_ID (nullable for pharmacy)',
    CLAIM_TYPE          VARCHAR(30)     NOT NULL    COMMENT 'Medical | Pharmacy | Dental | Vision',
    CLAIM_DATE          DATE            NOT NULL,
    SERVICE_FROM_DATE   DATE,
    SERVICE_TO_DATE     DATE,
    BILLED_AMOUNT       NUMBER(12,2)    NOT NULL,
    ALLOWED_AMOUNT      NUMBER(12,2),
    PAID_AMOUNT         NUMBER(12,2),
    PATIENT_COPAY       NUMBER(10,2),
    CLAIM_STATUS        VARCHAR(30)     NOT NULL    COMMENT 'Paid | Denied | Pending | Adjusted',
    DENIAL_REASON       VARCHAR(500),
    DX_CODE_PRIMARY     VARCHAR(20),
    DX_CODE_SECONDARY   VARIANT         COMMENT 'JSON array',
    PROCEDURE_CODE      VARCHAR(20),
    PROCEDURE_DESC      VARCHAR(300),
    NDC_CODE            VARCHAR(20)     COMMENT 'National Drug Code for pharmacy claims',
    DRUG_NAME           VARCHAR(200),
    PROVIDER_NPI        VARCHAR(20),
    PAYER_ID            VARCHAR(50),
    PAYER_NAME          VARCHAR(200),
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_CLAIMS PRIMARY KEY (CLAIM_ID),
    CONSTRAINT FK_CLM_PATIENT
        FOREIGN KEY (PATIENT_ID) REFERENCES RAW.PATIENTS(PATIENT_ID),
    CONSTRAINT FK_CLM_ENCOUNTER
        FOREIGN KEY (ENCOUNTER_ID) REFERENCES RAW.ENCOUNTERS(ENCOUNTER_ID)
)
COMMENT = 'Medical and pharmacy claims with full adjudication detail';

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: LABS
-- Laboratory test orders and results linked to patients and encounters.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE RAW.LABS (
    LAB_ID              VARCHAR(36)     NOT NULL    COMMENT 'UUID primary key',
    PATIENT_ID          VARCHAR(36)     NOT NULL    COMMENT 'FK → PATIENTS.PATIENT_ID',
    ENCOUNTER_ID        VARCHAR(36)                 COMMENT 'FK → ENCOUNTERS.ENCOUNTER_ID',
    ORDER_DATE          DATE            NOT NULL,
    RESULT_DATE         DATE,
    LAB_TEST_CODE       VARCHAR(30)     NOT NULL    COMMENT 'LOINC code',
    LAB_TEST_NAME       VARCHAR(300)    NOT NULL,
    RESULT_VALUE        VARCHAR(100),
    RESULT_UNIT         VARCHAR(50),
    REFERENCE_RANGE     VARCHAR(100),
    ABNORMAL_FLAG       VARCHAR(10)     COMMENT 'H | L | HH | LL | N | A',
    RESULT_STATUS       VARCHAR(30)     NOT NULL    COMMENT 'Final | Preliminary | Corrected | Cancelled',
    PERFORMING_LAB      VARCHAR(200),
    ORDERING_NPI        VARCHAR(20),
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_LABS PRIMARY KEY (LAB_ID),
    CONSTRAINT FK_LAB_PATIENT
        FOREIGN KEY (PATIENT_ID) REFERENCES RAW.PATIENTS(PATIENT_ID),
    CONSTRAINT FK_LAB_ENCOUNTER
        FOREIGN KEY (ENCOUNTER_ID) REFERENCES RAW.ENCOUNTERS(ENCOUNTER_ID)
)
COMMENT = 'Laboratory orders and results with LOINC coding';

-- ─────────────────────────────────────────────────────────────────────────────
-- Confirmation
-- ─────────────────────────────────────────────────────────────────────────────
SHOW TABLES IN SCHEMA RAW;
