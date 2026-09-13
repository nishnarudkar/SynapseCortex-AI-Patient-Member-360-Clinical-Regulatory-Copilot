-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 03_clinical_stage.sql
-- Purpose : Internal Snowflake stage for clinical notes and FDA package inserts
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE SCHEMA RAW;

-- ─────────────────────────────────────────────────────────────────────────────
-- INTERNAL STAGE: CLINICAL_STAGE
-- Encrypted with Snowflake SSE (server-side encryption using Snowflake-managed keys).
-- Stores:
--   clinical_notes/   → free-text clinical notes per encounter
--   fda_inserts/      → FDA drug package insert text for AI parsing
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE STAGE RAW.CLINICAL_STAGE
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    DIRECTORY  = (ENABLE = TRUE)
    COMMENT    = 'SynapseCortex AI: encrypted internal stage for unstructured clinical text and FDA inserts';

-- Grant usage to the application role (adjust role name to your environment)
-- GRANT READ, WRITE ON STAGE RAW.CLINICAL_STAGE TO ROLE SYNAPSECORTEX_APP_ROLE;

-- ─────────────────────────────────────────────────────────────────────────────
-- FILE FORMAT: Clinical text files (UTF-8 plain text)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FILE FORMAT RAW.CLINICAL_TEXT_FORMAT
    TYPE             = 'CSV'
    FIELD_DELIMITER  = NONE
    RECORD_DELIMITER = '\n'
    SKIP_HEADER      = 0
    ENCODING         = 'UTF-8'
    COMMENT          = 'Single-column text format for raw clinical note and FDA insert files';

-- ─────────────────────────────────────────────────────────────────────────────
-- FILE FORMAT: Structured CSV for tabular data loads
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FILE FORMAT RAW.CLINICAL_CSV_FORMAT
    TYPE                   = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF                = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL    = TRUE
    DATE_FORMAT            = 'YYYY-MM-DD'
    TIMESTAMP_FORMAT       = 'YYYY-MM-DD HH24:MI:SS'
    SKIP_HEADER            = 1
    ENCODING               = 'UTF-8'
    COMMENT                = 'Standard CSV format for patient/encounter/claims/labs bulk loads';

-- ─────────────────────────────────────────────────────────────────────────────
-- Confirm stage creation
-- ─────────────────────────────────────────────────────────────────────────────
SHOW STAGES IN SCHEMA RAW;
LIST @RAW.CLINICAL_STAGE;
