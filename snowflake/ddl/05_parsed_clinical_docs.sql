-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 05_parsed_clinical_docs.sql
-- Purpose : Parse all staged clinical notes and FDA inserts using
--           SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT (LAYOUT mode) and persist
--           the flattened page-level text into TRANSFORMED.PARSED_CLINICAL_DOCS
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================
-- PREREQUISITES:
--   1. Scripts 01–04 executed successfully
--   2. All 8 .txt files PUT into @RAW.CLINICAL_STAGE (clinical_notes/ + fda_inserts/)
--   3. Role has SNOWFLAKE.CORTEX_USER database role granted:
--        GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <your_role>;
--   4. ALTER STAGE RAW.CLINICAL_STAGE REFRESH; run after PUTs
--
-- ⚠️  FILE FORMAT NOTE:
--   Our staged documents are plain-text (.txt) files.
--   AI_PARSE_DOCUMENT supports 'page_split': true ONLY for PDF, DOCX, and PPTX.
--   For .txt files the function returns a single JSON object:
--       { "content": "<full document text>" }
--   There is NO "pages" array for .txt input — page splitting is not available.
--
--   Billing for .txt: 1 credit unit per 3,000 characters (rounded up).
--
--   UPGRADE PATH (when PDFs are available):
--   If clinical notes are converted to PDF and re-staged, replace the INSERT
--   block with the LATERAL FLATTEN block in Section C below.
--   The table schema is forward-compatible with both paths.
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE WAREHOUSE SYNAPSE_WH;      -- replace with your warehouse name

-- ─────────────────────────────────────────────────────────────────────────────
-- SECTION A: Target table DDL
-- TRANSFORMED.PARSED_CLINICAL_DOCS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE TRANSFORMED.PARSED_CLINICAL_DOCS (

    -- ── Identity ─────────────────────────────────────────────────────────────
    DOC_ID          VARCHAR(36)     NOT NULL DEFAULT UUID_STRING()
                                    COMMENT 'Surrogate PK for each parsed page/chunk row',

    -- ── Source traceability ──────────────────────────────────────────────────
    FILE_NAME       VARCHAR(500)    NOT NULL
                                    COMMENT 'RELATIVE_PATH from DIRECTORY(@RAW.CLINICAL_STAGE)',
    DOC_CATEGORY    VARCHAR(50)     NOT NULL
                                    COMMENT 'clinical_note | fda_insert',
    HERO_PATIENT    VARCHAR(50)
                                    COMMENT 'HERO-PT-001 | HERO-PT-002 | HERO-PT-003 | NULL',

    -- ── Page/chunk identity ───────────────────────────────────────────────────
    PAGE_NUMBER     NUMBER(5,0)     NOT NULL
                                    COMMENT '1-based page index. For .txt files always 1 (no page split). For PDF: actual page number.',

    -- ── Extracted content ────────────────────────────────────────────────────
    PAGE_TEXT       VARCHAR(16777216) NOT NULL
                                    COMMENT 'LAYOUT-mode Markdown-formatted extracted text for this page/chunk',

    -- ── Parse metadata ────────────────────────────────────────────────────────
    PARSE_MODE      VARCHAR(20)     NOT NULL DEFAULT 'LAYOUT'
                                    COMMENT 'AI_PARSE_DOCUMENT mode used: LAYOUT | OCR',
    PAGE_SPLIT_USED BOOLEAN         NOT NULL DEFAULT FALSE
                                    COMMENT 'TRUE when page_split was applied (PDF/DOCX/PPTX only)',
    RAW_PARSE_JSON  VARIANT
                                    COMMENT 'Full JSON output from AI_PARSE_DOCUMENT for debugging/reprocessing',

    -- ── Audit ────────────────────────────────────────────────────────────────
    PARSED_AT       TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP()
                                    COMMENT 'Timestamp when this row was inserted',
    STAGE_FILE_URL  VARCHAR(1000)
                                    COMMENT 'Snowflake file URL from DIRECTORY table (FILE_URL column)',

    CONSTRAINT PK_PARSED_CLINICAL_DOCS PRIMARY KEY (DOC_ID)
)
DATA_RETENTION_TIME_IN_DAYS = 7
CHANGE_TRACKING = TRUE           -- required for Cortex Search incremental refresh
COMMENT = 'Page-level text extracted from staged clinical notes and FDA inserts via AI_PARSE_DOCUMENT (LAYOUT mode). CHANGE_TRACKING=TRUE supports Cortex Search incremental refresh.'
;

-- ─────────────────────────────────────────────────────────────────────────────
-- SECTION B: Populate from .txt files
-- AI_PARSE_DOCUMENT in LAYOUT mode, no page_split (not supported for .txt).
-- Each staged .txt file → one row in PARSED_CLINICAL_DOCS (PAGE_NUMBER = 1).
--
-- Pattern:
--   1. DIRECTORY(@RAW.CLINICAL_STAGE) lists all staged files with RELATIVE_PATH
--   2. Filter to clinical_notes/ and fda_inserts/ sub-paths
--   3. Call AI_PARSE_DOCUMENT(TO_FILE(...), {'mode':'LAYOUT'}) per file
--   4. Parse the returned JSON → extract .content as PAGE_TEXT
--   5. Derive DOC_CATEGORY and HERO_PATIENT from the file name
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO TRANSFORMED.PARSED_CLINICAL_DOCS (
    FILE_NAME,
    DOC_CATEGORY,
    HERO_PATIENT,
    PAGE_NUMBER,
    PAGE_TEXT,
    PARSE_MODE,
    PAGE_SPLIT_USED,
    RAW_PARSE_JSON,
    PARSED_AT,
    STAGE_FILE_URL
)
WITH

-- ── Step 1: enumerate all .txt files from the stage directory table ────────
staged_files AS (
    SELECT
        RELATIVE_PATH                               AS file_name,
        FILE_URL                                    AS stage_file_url,
        LAST_MODIFIED                               AS last_modified
    FROM  DIRECTORY(@RAW.CLINICAL_STAGE)
    WHERE RELATIVE_PATH LIKE '%.txt'            -- clinical notes + FDA inserts only
      AND (
            RELATIVE_PATH LIKE 'clinical_notes/%'
         OR RELATIVE_PATH LIKE 'fda_inserts/%'
          )
),

-- ── Step 2: call AI_PARSE_DOCUMENT on every file row ─────────────────────
parsed_raw AS (
    SELECT
        sf.file_name,
        sf.stage_file_url,
        sf.last_modified,
        -- LAYOUT mode; no page_split — .txt files return {"content":"..."}
        -- AI_PARSE_DOCUMENT already returns OBJECT/VARIANT; PARSE_JSON is not needed
        AI_PARSE_DOCUMENT(
            TO_FILE('@RAW.CLINICAL_STAGE', sf.file_name),
            {
                'mode'      : 'LAYOUT'
                -- 'page_split': true  ← enable only after converting to PDF/DOCX
            }
        )                                           AS parsed_json
    FROM staged_files sf
),

-- ── Step 3: extract page text from the JSON ───────────────────────────────
-- For .txt files: parsed_json looks like {"content":"<text>"}
-- For PDF/PPTX/DOCX with page_split: {"pages":[{"content":"...","index":0},...]}
-- This CASE handles both so the query is forward-compatible with PDFs.
page_content AS (
    SELECT
        pr.file_name,
        pr.stage_file_url,
        pr.parsed_json,
        CASE
            -- PDF/DOCX/PPTX with page_split: pages array is present
            WHEN pr.parsed_json:pages IS NOT NULL
                THEN NULL   -- handled in the LATERAL FLATTEN block (Section C)
            -- .txt (and single-page docs): single content string
            ELSE TO_VARCHAR(pr.parsed_json:content)
        END                                         AS page_text,
        CASE
            WHEN pr.parsed_json:pages IS NOT NULL THEN TRUE
            ELSE FALSE
        END                                         AS is_paged
    FROM parsed_raw pr
    WHERE pr.parsed_json IS NOT NULL               -- skip NULL (parse error)
),

-- ── Step 4: classify each file ────────────────────────────────────────────
classified AS (
    SELECT
        pc.file_name,
        pc.stage_file_url,
        pc.page_text,
        pc.parsed_json,
        pc.is_paged,
        -- DOC_CATEGORY from path prefix
        CASE
            WHEN pc.file_name LIKE 'clinical_notes/%' THEN 'clinical_note'
            WHEN pc.file_name LIKE 'fda_inserts/%'    THEN 'fda_insert'
            ELSE 'unknown'
        END                                         AS doc_category,
        -- HERO_PATIENT from file name pattern
        CASE
            WHEN pc.file_name ILIKE '%hero1%'
              OR pc.file_name ILIKE '%ROBERT_CALLAHAN%'  THEN 'HERO-PT-001'
            WHEN pc.file_name ILIKE '%hero2%'
              OR pc.file_name ILIKE '%LINDA_MORENO%'     THEN 'HERO-PT-002'
            WHEN pc.file_name ILIKE '%hero3%'
              OR pc.file_name ILIKE '%JAMES_WHITFIELD%'  THEN 'HERO-PT-003'
            WHEN pc.file_name ILIKE '%METFORMIN%'        THEN 'HERO-PT-001'
            WHEN pc.file_name ILIKE '%HBA1C%'            THEN 'HERO-PT-002'
            WHEN pc.file_name ILIKE '%POLYPHARMACY%'     THEN 'HERO-PT-003'
            ELSE NULL
        END                                         AS hero_patient
    FROM page_content pc
    WHERE pc.is_paged = FALSE  -- only .txt / single-content files here
)

-- ── Final projection ──────────────────────────────────────────────────────
SELECT
    cl.file_name                        AS FILE_NAME,
    cl.doc_category                     AS DOC_CATEGORY,
    cl.hero_patient                     AS HERO_PATIENT,
    1                                   AS PAGE_NUMBER,      -- always 1 for .txt
    cl.page_text                        AS PAGE_TEXT,
    'LAYOUT'                            AS PARSE_MODE,
    FALSE                               AS PAGE_SPLIT_USED,
    cl.parsed_json                      AS RAW_PARSE_JSON,
    CURRENT_TIMESTAMP()                 AS PARSED_AT,
    cl.stage_file_url                   AS STAGE_FILE_URL
FROM classified cl
WHERE cl.page_text IS NOT NULL
  AND LENGTH(TRIM(cl.page_text)) > 0
;

-- ─────────────────────────────────────────────────────────────────────────────
-- SECTION C: PDF UPGRADE PATH (run this instead of Section B when files are PDF)
-- Uncomment and execute after converting .txt → .pdf and re-staging.
-- This uses LATERAL FLATTEN on the pages array returned by page_split: true.
-- ─────────────────────────────────────────────────────────────────────────────
/*
INSERT INTO TRANSFORMED.PARSED_CLINICAL_DOCS (
    FILE_NAME, DOC_CATEGORY, HERO_PATIENT, PAGE_NUMBER, PAGE_TEXT,
    PARSE_MODE, PAGE_SPLIT_USED, RAW_PARSE_JSON, PARSED_AT, STAGE_FILE_URL
)
WITH staged_files AS (
    SELECT RELATIVE_PATH AS file_name, FILE_URL AS stage_file_url
    FROM   DIRECTORY(@RAW.CLINICAL_STAGE)
    WHERE  RELATIVE_PATH LIKE '%.pdf'
      AND  (RELATIVE_PATH LIKE 'clinical_notes/%' OR RELATIVE_PATH LIKE 'fda_inserts/%')
),
parsed_raw AS (
    SELECT
        sf.file_name,
        sf.stage_file_url,
        -- AI_PARSE_DOCUMENT already returns OBJECT/VARIANT; PARSE_JSON is not needed
        AI_PARSE_DOCUMENT(
            TO_FILE('@RAW.CLINICAL_STAGE', sf.file_name),
            { 'mode': 'LAYOUT', 'page_split': true }
        ) AS parsed_json
    FROM staged_files sf
),
-- LATERAL FLATTEN expands the pages array: one row per page per document
page_rows AS (
    SELECT
        pr.file_name,
        pr.stage_file_url,
        pr.parsed_json,
        p.value                            AS page_obj,
        p.value:index::NUMBER + 1          AS page_number,   -- convert 0-based → 1-based
        TO_VARCHAR(p.value:content)        AS page_text
    FROM parsed_raw pr,
    LATERAL FLATTEN(input => pr.parsed_json:pages) p
    WHERE pr.parsed_json:pages IS NOT NULL
      AND p.value:content IS NOT NULL
)
SELECT
    pr2.file_name,
    CASE WHEN pr2.file_name LIKE 'clinical_notes/%' THEN 'clinical_note'
         WHEN pr2.file_name LIKE 'fda_inserts/%'    THEN 'fda_insert' ELSE 'unknown' END,
    CASE WHEN pr2.file_name ILIKE '%ROBERT_CALLAHAN%'  THEN 'HERO-PT-001'
         WHEN pr2.file_name ILIKE '%LINDA_MORENO%'     THEN 'HERO-PT-002'
         WHEN pr2.file_name ILIKE '%JAMES_WHITFIELD%'  THEN 'HERO-PT-003'
         WHEN pr2.file_name ILIKE '%METFORMIN%'        THEN 'HERO-PT-001'
         WHEN pr2.file_name ILIKE '%HBA1C%'            THEN 'HERO-PT-002'
         WHEN pr2.file_name ILIKE '%POLYPHARMACY%'     THEN 'HERO-PT-003' ELSE NULL END,
    pr2.page_number,
    pr2.page_text,
    'LAYOUT',
    TRUE,
    pr2.parsed_json,
    CURRENT_TIMESTAMP(),
    pr2.stage_file_url
FROM page_rows pr2
WHERE LENGTH(TRIM(pr2.page_text)) > 0;
*/

-- ─────────────────────────────────────────────────────────────────────────────
-- SECTION D: Quick sanity check after insert
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DOC_CATEGORY,
    HERO_PATIENT,
    COUNT(*)                                AS total_rows,
    MIN(PAGE_NUMBER)                        AS min_page,
    MAX(PAGE_NUMBER)                        AS max_page,
    AVG(LENGTH(PAGE_TEXT))                  AS avg_text_length,
    MIN(PARSED_AT)                          AS first_parsed
FROM TRANSFORMED.PARSED_CLINICAL_DOCS
GROUP BY 1, 2
ORDER BY 1, 2;

-- Expected: 8 rows total (one per staged .txt file), all PAGE_NUMBER = 1
-- After PDF upgrade: multiple rows per doc matching actual page counts




