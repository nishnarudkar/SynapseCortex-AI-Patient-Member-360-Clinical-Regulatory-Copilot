-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 06_cortex_search_service.sql
-- Purpose : Create APP.CLINICAL_DOC_SEARCH Cortex Search Service over
--           TRANSFORMED.PARSED_CLINICAL_DOCS, indexing PAGE_TEXT for
--           semantic (vector) + keyword (lexical) hybrid search, with
--           FILE_NAME and PAGE_NUMBER exposed as filter attributes.
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================
-- PREREQUISITES:
--   1. Script 05_parsed_clinical_docs.sql executed and table populated
--   2. TRANSFORMED.PARSED_CLINICAL_DOCS has CHANGE_TRACKING = TRUE
--   3. Role has:
--        - CREATE CORTEX SEARCH SERVICE privilege on schema APP
--        - SELECT privilege on TRANSFORMED.PARSED_CLINICAL_DOCS
--        - USAGE privilege on warehouse SYNAPSE_WH
--        - SNOWFLAKE.CORTEX_USER or SNOWFLAKE.CORTEX_EMBED_USER database role
--
--   Grant template (run as ACCOUNTADMIN if needed):
--     GRANT USAGE ON SCHEMA SYNAPSE_HEALTH.APP TO ROLE <your_role>;
--     GRANT CREATE CORTEX SEARCH SERVICE ON SCHEMA SYNAPSE_HEALTH.APP TO ROLE <your_role>;
--     GRANT SELECT ON TABLE SYNAPSE_HEALTH.TRANSFORMED.PARSED_CLINICAL_DOCS TO ROLE <your_role>;
--     GRANT USAGE ON WAREHOUSE SYNAPSE_WH TO ROLE <your_role>;
--     GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <your_role>;
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE SCHEMA APP;
USE WAREHOUSE SYNAPSE_WH;      -- replace with your warehouse name

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 1: Enable change tracking on the source table
-- Required for incremental refresh (default REFRESH_MODE).
-- Script 05 already sets CHANGE_TRACKING=TRUE on the table; this ALTER is a
-- safety net in case the table was recreated without it.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE TRANSFORMED.PARSED_CLINICAL_DOCS
    SET CHANGE_TRACKING = TRUE;

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 2: Create the Cortex Search Service
--
-- Design decisions:
--   ON page_text          → single search column (semantic + lexical over full
--                           extracted document text)
--   PRIMARY KEY (doc_id)  → enables optimised incremental refresh path; each
--                           re-parse run updates only changed rows
--   ATTRIBUTES            → FILE_NAME and PAGE_NUMBER exposed as equality /
--                           range filters in search queries
--   TARGET_LAG = '1 hour' → search index refreshes within 60 min of any INSERT
--                           or UPDATE to PARSED_CLINICAL_DOCS
--   EMBEDDING_MODEL       → snowflake-arctic-embed-l-v2.0: highest-quality
--                           Snowflake-managed model; good for clinical long text
--   REFRESH_MODE          → INCREMENTAL (default, cost-efficient for new rows)
--   INITIALIZE            → ON_CREATE: build index synchronously so the service
--                           is immediately queryable after this statement
--   REQUEST_LOGGING       → TRUE: capture query logs for RAG debugging /
--                           monitoring in SNOWFLAKE.CORTEX_ANALYST_FEEDBACK
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE CORTEX SEARCH SERVICE APP.CLINICAL_DOC_SEARCH

    ON          page_text

    PRIMARY KEY (doc_id)

    ATTRIBUTES  file_name,
                page_number,
                doc_category,
                hero_patient,
                parse_mode,
                page_split_used,
                parsed_at

    WAREHOUSE   = SYNAPSE_WH

    TARGET_LAG  = '1 hour'

    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'

    REFRESH_MODE    = INCREMENTAL

    INITIALIZE      = ON_CREATE

    REQUEST_LOGGING = TRUE

    COMMENT = 'SynapseCortex AI: semantic + lexical search over parsed clinical notes and FDA regulatory inserts. Supports RAG for Clinical Regulatory Copilot.'

AS (
    SELECT
        doc_id,
        file_name,
        page_number,
        doc_category,
        hero_patient,
        page_text,
        parse_mode,
        page_split_used,
        parsed_at
    FROM TRANSFORMED.PARSED_CLINICAL_DOCS
    WHERE page_text IS NOT NULL
      AND LENGTH(TRIM(page_text)) > 0
);

-- =============================================================================
-- NOTE ON INITIALIZE = ON_CREATE
-- The CREATE statement above will block until the first index build completes.
-- For 8 small .txt documents this is typically < 2 minutes on an XS warehouse.
-- For large PDF corpora, consider INITIALIZE = ON_SCHEDULE and check status
-- with SHOW CORTEX SEARCH SERVICES and the validation queries in script 07.
-- =============================================================================
