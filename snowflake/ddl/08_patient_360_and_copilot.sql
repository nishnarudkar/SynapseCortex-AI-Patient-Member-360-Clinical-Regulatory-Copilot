-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 08_patient_360_and_copilot.sql
-- Purpose : Build the TRANSFORMED.PATIENT_360_VIEW — the authoritative
--           longitudinal patient record combining PATIENTS, ENCOUNTERS,
--           CLAIMS, and LABS with:
--             • Aggregated clinical metrics
--             • Deterministic risk stratification (RISK_TIER)
--             • HEDIS-aligned care gap detection (CARE_GAP_STATUS)
--           Also creates an APP.PATIENT_360_SNAPSHOT materialised table for
--           the Python RAG engine to query efficiently.
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================
-- PREREQUISITES:
--   Scripts 01–07 executed. RAW tables populated via 04_stage_and_load.sql.
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE WAREHOUSE SYNAPSE_WH;          -- replace with your warehouse name

-- ─────────────────────────────────────────────────────────────────────────────
-- HELPER: current date anchor (parameterise to simplify testing)
-- Change this value to back-date the care gap window for testing.
-- ─────────────────────────────────────────────────────────────────────────────
SET REFERENCE_DATE = CURRENT_DATE();   -- 2026-09-13 in production

-- =============================================================================
-- SECTION A  –  INTERMEDIATE CTEs (reusable aggregation building blocks)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- A1. Claims roll-up per patient
--     • total_claims_cost  : sum of all BILLED_AMOUNT regardless of claim status
--     • paid_claims_cost   : sum of PAID_AMOUNT on Paid claims only
--     • claim_count        : total claim records
--     • active_rx_count    : distinct pharmacy drug names on PAID claims
--       (proxy for active medication count when an active Rx table is absent)
-- ─────────────────────────────────────────────────────────────────────────────
-- A2. Lab roll-up per patient
--     • last_hba1c_date    : most recent RESULT_DATE for LOINC 4548-4
--     • last_hba1c_value   : corresponding result
--     • last_egfr_value    : most recent eGFR (LOINC 33914-3)
--     • last_creatinine    : most recent creatinine (LOINC 2160-0)
-- ─────────────────────────────────────────────────────────────────────────────
-- A3. Encounter roll-up per patient
--     • encounter_count           : total encounters
--     • last_encounter_date       : most recent visit
--     • all_dx_codes              : ARRAY_AGG of all primary DX codes
--     • all_dx_descs              : ARRAY_AGG of all primary DX descriptions
--     • all_medications           : flattened list of all prescribed drug strings
--     • has_diabetes_dx           : TRUE if any primary DX code starts with E10/E11
--     • has_ckd_dx                : TRUE if any primary DX code starts with N18
--     • has_cad_dx                : TRUE if any primary DX code = I25.x
--     • has_copd_dx               : TRUE if any primary DX code starts with J44
--     • has_htn_dx                : TRUE if any primary DX code = I10
-- ─────────────────────────────────────────────────────────────────────────────

-- =============================================================================
-- SECTION B  –  PATIENT_360_VIEW
-- =============================================================================

CREATE OR REPLACE VIEW TRANSFORMED.PATIENT_360_VIEW
COMMENT = 'SynapseCortex AI Patient 360 – longitudinal profile with risk stratification and care gap flags. Source: RAW.PATIENTS + ENCOUNTERS + CLAIMS + LABS.'
AS

WITH

-- ── A1: Claims aggregation ────────────────────────────────────────────────
claims_agg AS (
    SELECT
        c.PATIENT_ID,
        ROUND(SUM(c.BILLED_AMOUNT), 2)                      AS total_claims_cost,
        ROUND(SUM(
            CASE WHEN c.CLAIM_STATUS = 'Paid'
                 THEN COALESCE(c.PAID_AMOUNT, 0) ELSE 0 END
        ), 2)                                               AS paid_claims_cost,
        COUNT(c.CLAIM_ID)                                   AS claim_count,
        -- Active medication count: distinct drug names on paid pharmacy claims
        COUNT(DISTINCT
            CASE WHEN c.CLAIM_TYPE  = 'Pharmacy'
                  AND c.CLAIM_STATUS = 'Paid'
                  AND c.DRUG_NAME IS NOT NULL
                 THEN UPPER(TRIM(c.DRUG_NAME)) END
        )                                                   AS active_medication_count,
        LISTAGG(DISTINCT
            CASE WHEN c.CLAIM_TYPE  = 'Pharmacy'
                  AND c.CLAIM_STATUS = 'Paid'
                  AND c.DRUG_NAME IS NOT NULL
                 THEN c.DRUG_NAME END,
            ' | '
        ) WITHIN GROUP (ORDER BY c.DRUG_NAME)              AS active_medications_list,
        MAX(c.CLAIM_DATE)                                   AS last_claim_date
    FROM RAW.CLAIMS c
    GROUP BY c.PATIENT_ID
),

-- ── A2: Lab aggregation ───────────────────────────────────────────────────
labs_agg AS (
    SELECT
        l.PATIENT_ID,
        -- HbA1c (LOINC 4548-4)
        MAX(CASE WHEN l.LAB_TEST_CODE = '4548-4'
                 THEN l.RESULT_DATE  END)                   AS last_hba1c_date,
        MAX(CASE WHEN l.LAB_TEST_CODE = '4548-4'
                  AND l.RESULT_DATE = (
                          SELECT MAX(l2.RESULT_DATE)
                          FROM RAW.LABS l2
                          WHERE l2.PATIENT_ID   = l.PATIENT_ID
                            AND l2.LAB_TEST_CODE = '4548-4'
                      )
                 THEN TRY_TO_DECIMAL(l.RESULT_VALUE, 5, 2)
            END)                                            AS last_hba1c_value,
        -- eGFR (LOINC 33914-3)
        MAX(CASE WHEN l.LAB_TEST_CODE = '33914-3'
                  AND l.RESULT_DATE = (
                          SELECT MAX(l2.RESULT_DATE)
                          FROM RAW.LABS l2
                          WHERE l2.PATIENT_ID   = l.PATIENT_ID
                            AND l2.LAB_TEST_CODE = '33914-3'
                      )
                 THEN TRY_TO_DECIMAL(l.RESULT_VALUE, 6, 1)
            END)                                            AS last_egfr_value,
        -- Creatinine (LOINC 2160-0)
        MAX(CASE WHEN l.LAB_TEST_CODE = '2160-0'
                  AND l.RESULT_DATE = (
                          SELECT MAX(l2.RESULT_DATE)
                          FROM RAW.LABS l2
                          WHERE l2.PATIENT_ID   = l.PATIENT_ID
                            AND l2.LAB_TEST_CODE = '2160-0'
                      )
                 THEN TRY_TO_DECIMAL(l.RESULT_VALUE, 5, 2)
            END)                                            AS last_creatinine_value,
        COUNT(DISTINCT l.LAB_ID)                            AS total_lab_results,
        SUM(CASE WHEN l.ABNORMAL_FLAG IN ('H','L','HH','LL','A') THEN 1 ELSE 0 END)
                                                            AS abnormal_lab_count
    FROM RAW.LABS l
    GROUP BY l.PATIENT_ID
),

-- ── A3: Encounter aggregation ─────────────────────────────────────────────
encounters_agg AS (
    SELECT
        e.PATIENT_ID,
        COUNT(DISTINCT e.ENCOUNTER_ID)                      AS encounter_count,
        MAX(e.ENCOUNTER_DATE)                               AS last_encounter_date,
        MIN(e.ENCOUNTER_DATE)                               AS first_encounter_date,
        -- Chronic condition flags from primary DX codes
        MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'E10%'
                   OR e.PRIMARY_DX_CODE LIKE 'E11%'
                 THEN 1 ELSE 0 END)                         AS has_diabetes_dx,
        MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'N18%'
                 THEN 1 ELSE 0 END)                         AS has_ckd_dx,
        MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'I25%'
                 THEN 1 ELSE 0 END)                         AS has_cad_dx,
        MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'J44%'
                 THEN 1 ELSE 0 END)                         AS has_copd_dx,
        MAX(CASE WHEN e.PRIMARY_DX_CODE = 'I10'
                 THEN 1 ELSE 0 END)                         AS has_htn_dx,
        -- Active chronic condition count (proxy complexity score)
        (MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'E10%' OR e.PRIMARY_DX_CODE LIKE 'E11%' THEN 1 ELSE 0 END)
       + MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'N18%' THEN 1 ELSE 0 END)
       + MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'I25%' THEN 1 ELSE 0 END)
       + MAX(CASE WHEN e.PRIMARY_DX_CODE LIKE 'J44%' THEN 1 ELSE 0 END)
       + MAX(CASE WHEN e.PRIMARY_DX_CODE = 'I10'     THEN 1 ELSE 0 END)
        )                                                   AS chronic_condition_count,
        -- All primary DX codes and descriptions as pipe-delimited strings
        LISTAGG(DISTINCT e.PRIMARY_DX_CODE, ' | ')
            WITHIN GROUP (ORDER BY e.PRIMARY_DX_CODE)      AS all_dx_codes,
        LISTAGG(DISTINCT e.PRIMARY_DX_DESC, ' | ')
            WITHIN GROUP (ORDER BY e.PRIMARY_DX_DESC)      AS all_dx_descriptions,
        -- Encounter types seen
        LISTAGG(DISTINCT e.ENCOUNTER_TYPE, ' | ')
            WITHIN GROUP (ORDER BY e.ENCOUNTER_TYPE)       AS encounter_types_seen,
        -- Most recent notes reference (for RAG linking)
        MAX(e.NOTES_REF)                                    AS latest_notes_ref
    FROM RAW.ENCOUNTERS e
    GROUP BY e.PATIENT_ID
),

-- ── A4: Core patient profile with all aggregates joined ──────────────────
patient_base AS (
    SELECT
        -- ── Demographics ─────────────────────────────────────────────────
        p.PATIENT_ID,
        p.FIRST_NAME,
        p.LAST_NAME,
        p.FIRST_NAME || ' ' || p.LAST_NAME                 AS full_name,
        p.DATE_OF_BIRTH,
        p.AGE,
        p.GENDER,
        p.RACE,
        p.ETHNICITY,
        p.STATE,
        p.ZIP_CODE,
        p.INSURANCE_PLAN,
        p.PRIMARY_CARE_NPI,
        p.ACTIVE_FLAG,

        -- ── Claims metrics ────────────────────────────────────────────────
        COALESCE(ca.total_claims_cost,      0)              AS total_claims_cost,
        COALESCE(ca.paid_claims_cost,       0)              AS paid_claims_cost,
        COALESCE(ca.claim_count,            0)              AS claim_count,
        COALESCE(ca.active_medication_count,0)              AS active_medication_count,
        ca.active_medications_list,
        ca.last_claim_date,

        -- ── Lab metrics ───────────────────────────────────────────────────
        la.last_hba1c_date,
        la.last_hba1c_value,
        la.last_egfr_value,
        la.last_creatinine_value,
        COALESCE(la.total_lab_results,  0)                  AS total_lab_results,
        COALESCE(la.abnormal_lab_count, 0)                  AS abnormal_lab_count,

        -- ── Encounter metrics ─────────────────────────────────────────────
        COALESCE(ea.encounter_count,            0)          AS encounter_count,
        ea.last_encounter_date,
        ea.first_encounter_date,
        COALESCE(ea.has_diabetes_dx,            0)          AS has_diabetes_dx,
        COALESCE(ea.has_ckd_dx,                 0)          AS has_ckd_dx,
        COALESCE(ea.has_cad_dx,                 0)          AS has_cad_dx,
        COALESCE(ea.has_copd_dx,                0)          AS has_copd_dx,
        COALESCE(ea.has_htn_dx,                 0)          AS has_htn_dx,
        COALESCE(ea.chronic_condition_count,    0)          AS chronic_condition_count,
        ea.all_dx_codes,
        ea.all_dx_descriptions,
        ea.encounter_types_seen,
        ea.latest_notes_ref

    FROM RAW.PATIENTS p
    LEFT JOIN claims_agg    ca ON p.PATIENT_ID = ca.PATIENT_ID
    LEFT JOIN labs_agg      la ON p.PATIENT_ID = la.PATIENT_ID
    LEFT JOIN encounters_agg ea ON p.PATIENT_ID = ea.PATIENT_ID
)

-- =============================================================================
-- SECTION B  –  Final projection with RISK_TIER and CARE_GAP_STATUS
-- =============================================================================
SELECT
    pb.*,

    -- ─────────────────────────────────────────────────────────────────────
    -- RISK_TIER  (deterministic)
    -- Rule: 'HIGH RISK' if age > 65 AND total_claims_cost > 25000
    --       else 'LOW RISK'
    -- ─────────────────────────────────────────────────────────────────────
    CASE
        WHEN pb.AGE > 65
         AND pb.total_claims_cost > 25000
        THEN 'HIGH RISK'
        ELSE 'LOW RISK'
    END                                                     AS risk_tier,

    -- ─────────────────────────────────────────────────────────────────────
    -- CARE_GAP_STATUS  (HEDIS-aligned, deterministic)
    -- Rule: 'GAP: Overdue HbA1c Lab'
    --         if ANY encounter has a Diabetes diagnosis (E10.x or E11.x)
    --         AND (last_hba1c_date IS NULL
    --              OR last_hba1c_date < REFERENCE_DATE minus 12 months)
    --       else 'NO GAP'
    -- Covers: HEDIS CDC NQF-0059 – HbA1c testing ≥ once per 12 months
    -- ─────────────────────────────────────────────────────────────────────
    CASE
        WHEN pb.has_diabetes_dx = 1
         AND (
                pb.last_hba1c_date IS NULL
             OR pb.last_hba1c_date < DATEADD('month', -12, $REFERENCE_DATE)
             )
        THEN 'GAP: Overdue HbA1c Lab'
        ELSE 'NO GAP'
    END                                                     AS care_gap_status,

    -- ─────────────────────────────────────────────────────────────────────
    -- DRUG_SAFETY_FLAG  (bonus – surfaces Hero 1 Metformin/CKD conflict)
    -- Flags when Metformin is active AND eGFR is in the danger zone
    -- ─────────────────────────────────────────────────────────────────────
    CASE
        WHEN pb.active_medications_list ILIKE '%metformin%'
         AND pb.has_ckd_dx = 1
         AND pb.last_egfr_value IS NOT NULL
         AND pb.last_egfr_value < 45
        THEN 'ALERT: Metformin active with eGFR < 45 (CKD contraindication)'
        WHEN pb.active_medications_list ILIKE '%metformin%'
         AND pb.has_ckd_dx = 1
        THEN 'WARN: Metformin active with CKD diagnosis – verify eGFR'
        ELSE NULL
    END                                                     AS drug_safety_flag,

    -- ─────────────────────────────────────────────────────────────────────
    -- Audit fields
    -- ─────────────────────────────────────────────────────────────────────
    $REFERENCE_DATE                                         AS view_reference_date,
    CURRENT_TIMESTAMP()                                     AS view_generated_at

FROM patient_base pb
;

-- =============================================================================
-- SECTION C  –  APP.PATIENT_360_SNAPSHOT
-- A materialised / persisted version of the view for efficient RAG engine
-- point-lookup. The Python rag_engine.py reads from this table directly
-- to avoid re-computing all CTEs on every copilot request.
-- Refresh manually or via a Snowflake Task on a schedule.
-- =============================================================================
CREATE OR REPLACE TABLE APP.PATIENT_360_SNAPSHOT
    DATA_RETENTION_TIME_IN_DAYS = 1
    CHANGE_TRACKING             = FALSE
    COMMENT = 'Materialised snapshot of TRANSFORMED.PATIENT_360_VIEW. Refresh on a schedule for production. Used by rag_engine.py for low-latency patient context retrieval.'
AS
SELECT * FROM TRANSFORMED.PATIENT_360_VIEW;

-- =============================================================================
-- SECTION D  –  Validation queries
-- =============================================================================

-- D1. Hero case assertions
SELECT
    PATIENT_ID,
    FULL_NAME,
    AGE,
    RISK_TIER,
    CARE_GAP_STATUS,
    DRUG_SAFETY_FLAG,
    TOTAL_CLAIMS_COST,
    ACTIVE_MEDICATION_COUNT,
    LAST_HBAC1_DATE,
    LAST_EGFR_VALUE,
    CHRONIC_CONDITION_COUNT
FROM TRANSFORMED.PATIENT_360_VIEW
WHERE PATIENT_ID LIKE 'HERO-PT-%'
ORDER BY PATIENT_ID;

-- D2. Deterministic rule checks
SELECT
    PATIENT_ID,
    FULL_NAME,
    AGE,
    TOTAL_CLAIMS_COST,
    RISK_TIER,
    -- Hero 1 (Age 58): does NOT meet age > 65, should be LOW RISK
    -- Hero 3 (Age 71, claims $51,755): MUST be HIGH RISK
    CASE
        WHEN PATIENT_ID LIKE 'HERO-PT-001%' AND RISK_TIER = 'LOW RISK'
            THEN '✓ PASS: Hero 1 correctly LOW RISK (age 58 ≤ 65)'
        WHEN PATIENT_ID LIKE 'HERO-PT-003%' AND RISK_TIER = 'HIGH RISK'
            THEN '✓ PASS: Hero 3 correctly HIGH RISK (age 71 > 65, claims > $25K)'
        WHEN PATIENT_ID LIKE 'HERO-PT-002%' AND RISK_TIER = 'LOW RISK'
            THEN '✓ PASS: Hero 2 correctly LOW RISK (age 62 ≤ 65)'
        ELSE '✗ FAIL: Unexpected risk tier for ' || PATIENT_ID
    END AS risk_tier_check,
    CARE_GAP_STATUS,
    LAST_HBAC1_DATE,
    -- Hero 2: Diabetes + HbA1c 14 months ago → MUST be GAP
    CASE
        WHEN PATIENT_ID LIKE 'HERO-PT-002%'
         AND CARE_GAP_STATUS = 'GAP: Overdue HbA1c Lab'
            THEN '✓ PASS: Hero 2 care gap detected (HbA1c overdue)'
        WHEN PATIENT_ID LIKE 'HERO-PT-002%'
            THEN '✗ FAIL: Hero 2 care gap NOT detected — check HbA1c date and reference date'
        WHEN PATIENT_ID LIKE 'HERO-PT-001%'
         AND CARE_GAP_STATUS = 'NO GAP'
            THEN '✓ PASS: Hero 1 no diabetes care gap (CKD, not diabetes primary)'
        ELSE '– N/A'
    END AS care_gap_check
FROM TRANSFORMED.PATIENT_360_VIEW
WHERE PATIENT_ID LIKE 'HERO-PT-%'
ORDER BY PATIENT_ID;

-- D3. Population roll-up
SELECT
    RISK_TIER,
    CARE_GAP_STATUS,
    COUNT(*)                            AS patient_count,
    ROUND(AVG(TOTAL_CLAIMS_COST), 2)   AS avg_claims_cost,
    ROUND(AVG(AGE), 1)                 AS avg_age,
    SUM(CASE WHEN DRUG_SAFETY_FLAG IS NOT NULL THEN 1 ELSE 0 END) AS drug_flag_count
FROM TRANSFORMED.PATIENT_360_VIEW
GROUP BY 1, 2
ORDER BY 1, 2;

-- D4. APP.PATIENT_360_SNAPSHOT row count
SELECT COUNT(*) AS snapshot_rows FROM APP.PATIENT_360_SNAPSHOT;
