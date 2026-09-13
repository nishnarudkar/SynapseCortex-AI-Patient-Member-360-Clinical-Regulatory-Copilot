-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 07_validate_cortex_pipeline.sql
-- Purpose : End-to-end validation of the Cortex document parsing pipeline:
--             1. Stage file inventory
--             2. PARSED_CLINICAL_DOCS row counts and content checks
--             3. Cortex Search Service status
--             4. Live search queries against APP.CLINICAL_DOC_SEARCH
--             5. Hero-case targeted retrieval assertions
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================

USE DATABASE SYNAPSE_HEALTH;
USE WAREHOUSE SYNAPSE_WH;      -- replace with your warehouse name

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 1: Stage inventory
-- Expected: 8 .txt files (5 clinical notes + 3 FDA inserts)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 1: Stage file inventory ==' AS check_label;

SELECT
    RELATIVE_PATH                               AS file_path,
    REGEXP_SUBSTR(RELATIVE_PATH, '^[^/]+')      AS subfolder,
    SIZE                                        AS size_bytes,
    LAST_MODIFIED                               AS staged_at
FROM DIRECTORY(@RAW.CLINICAL_STAGE)
WHERE RELATIVE_PATH LIKE '%.txt'
ORDER BY subfolder, file_path;

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 2: PARSED_CLINICAL_DOCS row count and coverage
-- Expected: 8 rows (one per .txt file), all PAGE_NUMBER = 1
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 2: PARSED_CLINICAL_DOCS row counts ==' AS check_label;

SELECT
    DOC_CATEGORY,
    HERO_PATIENT,
    PAGE_SPLIT_USED,
    COUNT(*)                                    AS row_count,
    MIN(PAGE_NUMBER)                            AS min_page,
    MAX(PAGE_NUMBER)                            AS max_page,
    AVG(LENGTH(PAGE_TEXT))                      AS avg_chars,
    MIN(PARSED_AT)                              AS first_parsed_at
FROM TRANSFORMED.PARSED_CLINICAL_DOCS
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- Total must equal 8 for the initial .txt load
SELECT
    CASE WHEN COUNT(*) = 8
         THEN '✓ PASS: 8 rows present (all staged files parsed)'
         ELSE '✗ FAIL: Expected 8 rows, found ' || COUNT(*) || ' — re-run 05_parsed_clinical_docs.sql'
    END AS row_count_check
FROM TRANSFORMED.PARSED_CLINICAL_DOCS;

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 3: Content spot-checks — confirm key clinical text was captured
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 3: Content spot-checks ==' AS check_label;

-- Hero 1: Metformin safety alert text must be present
SELECT
    FILE_NAME,
    HERO_PATIENT,
    CASE WHEN PAGE_TEXT ILIKE '%Metformin%' AND PAGE_TEXT ILIKE '%eGFR%'
         THEN '✓ PASS: Metformin + eGFR text found'
         ELSE '✗ FAIL: Expected clinical content not found'
    END AS content_check
FROM TRANSFORMED.PARSED_CLINICAL_DOCS
WHERE HERO_PATIENT = 'HERO-PT-001'
ORDER BY FILE_NAME;

-- Hero 2: HbA1c care gap content
SELECT
    FILE_NAME,
    HERO_PATIENT,
    CASE WHEN PAGE_TEXT ILIKE '%HbA1c%' AND PAGE_TEXT ILIKE '%care gap%'
         THEN '✓ PASS: HbA1c + care gap text found'
         ELSE '✗ FAIL: Expected clinical content not found'
    END AS content_check
FROM TRANSFORMED.PARSED_CLINICAL_DOCS
WHERE HERO_PATIENT = 'HERO-PT-002'
ORDER BY FILE_NAME;

-- Hero 3: High risk / polypharmacy content
SELECT
    FILE_NAME,
    HERO_PATIENT,
    CASE WHEN PAGE_TEXT ILIKE '%polypharmacy%' OR PAGE_TEXT ILIKE '%high risk%'
         THEN '✓ PASS: Polypharmacy / high risk text found'
         ELSE '✗ FAIL: Expected clinical content not found'
    END AS content_check
FROM TRANSFORMED.PARSED_CLINICAL_DOCS
WHERE HERO_PATIENT = 'HERO-PT-003'
ORDER BY FILE_NAME;

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 4: Cortex Search Service operational status
-- Expected: ACTIVE service with indexedRowCount = 8, no errors
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 4: Cortex Search Service status ==' AS check_label;

-- List all Cortex Search Services in this account
SHOW CORTEX SEARCH SERVICES IN SCHEMA SYNAPSE_HEALTH.APP;

-- Detailed status of our specific service
DESCRIBE CORTEX SEARCH SERVICE APP.CLINICAL_DOC_SEARCH;

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 5: Live search queries via REST / SQL preview
-- Snowflake does not (yet) expose a native SQL SELECT against a Cortex Search
-- Service directly — queries are issued via the REST API or Python SDK.
-- The blocks below show the REST call pattern AND a SQL-based validation
-- using SYSTEM$GET_SERVICE_STATUS and a stored procedure wrapper.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 5: Service status via SYSTEM$GET_SERVICE_STATUS ==' AS check_label;

-- Returns JSON with serviceStatus, indexedRowCount, lastRefreshTime, etc.
SELECT PARSE_JSON(
    SYSTEM$GET_SERVICE_STATUS('SYNAPSE_HEALTH.APP.CLINICAL_DOC_SEARCH')
) AS service_status_json;

-- Extract key fields
WITH status AS (
    SELECT PARSE_JSON(
        SYSTEM$GET_SERVICE_STATUS('SYNAPSE_HEALTH.APP.CLINICAL_DOC_SEARCH')
    ) AS s
)
SELECT
    s:serviceStatus::STRING                     AS service_status,
    s:indexedRowCount::NUMBER                   AS indexed_row_count,
    s:lastRefreshTime::STRING                   AS last_refresh_time,
    s:message::STRING                           AS status_message,
    CASE
        WHEN s:serviceStatus::STRING = 'ACTIVE'
         AND s:indexedRowCount::NUMBER = 8
        THEN '✓ PASS: Service ACTIVE, 8 rows indexed'
        WHEN s:serviceStatus::STRING = 'ACTIVE'
        THEN '⚠ WARN: Service ACTIVE but indexedRowCount = ' || s:indexedRowCount || ' (expected 8)'
        ELSE '✗ FAIL: Service not ACTIVE — status: ' || s:serviceStatus
    END                                         AS validation_result
FROM status;

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 6: Python SDK query reference (run in a Snowflake Notebook or Streamlit)
-- This block is SQL comment documentation — not executable SQL.
-- ─────────────────────────────────────────────────────────────────────────────
/*
──────────────────────────────────────────────────────────────────────────────
PYTHON SDK QUERY EXAMPLES (Snowflake Notebooks / Streamlit in Snowflake)
──────────────────────────────────────────────────────────────────────────────

from snowflake.core import Root
from snowflake.snowpark.context import get_active_session

session = get_active_session()
root    = Root(session)

# Reference the search service
svc = (root
       .databases["SYNAPSE_HEALTH"]
       .schemas["APP"]
       .cortex_search_services["CLINICAL_DOC_SEARCH"])

# ── Query 1: Safety violation – Metformin + CKD ────────────────────────────
result = svc.search(
    query      = "Metformin contraindicated in renal impairment CKD eGFR",
    columns    = ["file_name", "page_number", "page_text", "hero_patient"],
    filter     = {"@eq": {"doc_category": "fda_insert"}},
    limit      = 3
)
print(result.to_pandas())

# ── Query 2: Care gap – HbA1c overdue in diabetic patient ─────────────────
result = svc.search(
    query      = "HbA1c monitoring gap diabetes no test 14 months HEDIS",
    columns    = ["file_name", "page_number", "page_text", "hero_patient"],
    limit      = 3
)
print(result.to_pandas())

# ── Query 3: High-risk polypharmacy – drug interactions ───────────────────
result = svc.search(
    query      = "polypharmacy drug interactions beta blocker COPD carvedilol albuterol",
    columns    = ["file_name", "page_number", "page_text", "hero_patient"],
    filter     = {"@eq": {"hero_patient": "HERO-PT-003"}},
    limit      = 5
)
print(result.to_pandas())

# ── Query 4: FDA Black Box Warning for lactic acidosis ────────────────────
result = svc.search(
    query      = "lactic acidosis black box warning biguanide",
    columns    = ["file_name", "page_text"],
    filter     = {"@eq": {"doc_category": "fda_insert"}},
    limit      = 2
)
print(result.to_pandas())

# ── Query 5: Filter by hero patient + category ────────────────────────────
result = svc.search(
    query      = "discharge medications aspirin clopidogrel statin heart failure",
    columns    = ["file_name", "page_number", "page_text"],
    filter     = {
        "@and": [
            {"@eq": {"hero_patient": "HERO-PT-003"}},
            {"@eq": {"doc_category": "clinical_note"}}
        ]
    },
    limit      = 3
)
print(result.to_pandas())
──────────────────────────────────────────────────────────────────────────────
REST API QUERY EXAMPLE (curl / Postman / Python requests)
──────────────────────────────────────────────────────────────────────────────

POST https://<account>.snowflakecomputing.com/api/v2/cortex/search-services/CLINICAL_DOC_SEARCH:query

Headers:
  Authorization: Bearer <JWT_token>
  Content-Type: application/json
  X-Snowflake-Database: SYNAPSE_HEALTH
  X-Snowflake-Schema: APP

Body:
{
  "query": "Metformin renal impairment contraindication eGFR",
  "columns": ["file_name", "page_number", "page_text", "hero_patient"],
  "filter": { "@eq": { "doc_category": "fda_insert" } },
  "limit": 3
}

Expected response:
{
  "results": [
    {
      "file_name": "fda_inserts/fda_insert_METFORMIN.txt",
      "page_number": 1,
      "page_text": "... eGFR < 30 mL/min → CONTRAINDICATED ...",
      "hero_patient": "HERO-PT-001"
    }
  ],
  "request_id": "...",
  "warning": null
}
──────────────────────────────────────────────────────────────────────────────
*/

-- ─────────────────────────────────────────────────────────────────────────────
-- CHECK 7: End-to-end pipeline summary
-- ─────────────────────────────────────────────────────────────────────────────
SELECT '== CHECK 7: Full pipeline summary ==' AS check_label;

SELECT
    'Stage files (.txt)'            AS component,
    COUNT(*)::VARCHAR               AS count_or_status,
    'Source documents in @RAW.CLINICAL_STAGE' AS notes
FROM DIRECTORY(@RAW.CLINICAL_STAGE)
WHERE RELATIVE_PATH LIKE '%.txt'

UNION ALL

SELECT
    'Parsed rows (PARSED_CLINICAL_DOCS)',
    COUNT(*)::VARCHAR,
    'One row per .txt file (PAGE_NUMBER=1). Expands to N rows per PDF page after upgrade.'
FROM TRANSFORMED.PARSED_CLINICAL_DOCS

UNION ALL

SELECT
    'Cortex Search Service',
    'APP.CLINICAL_DOC_SEARCH',
    'snowflake-arctic-embed-l-v2.0 | TARGET_LAG=1hr | INCREMENTAL refresh | REQUEST_LOGGING=TRUE'

UNION ALL

SELECT
    'Hero 1 documents',
    COUNT(*)::VARCHAR,
    'Safety Violation: CKD + Metformin'
FROM TRANSFORMED.PARSED_CLINICAL_DOCS WHERE HERO_PATIENT = 'HERO-PT-001'

UNION ALL

SELECT
    'Hero 2 documents',
    COUNT(*)::VARCHAR,
    'Care Gap: Diabetes, no HbA1c 14 months'
FROM TRANSFORMED.PARSED_CLINICAL_DOCS WHERE HERO_PATIENT = 'HERO-PT-002'

UNION ALL

SELECT
    'Hero 3 documents',
    COUNT(*)::VARCHAR,
    'High Risk: Multi-chronic, polypharmacy, claims > $50K'
FROM TRANSFORMED.PARSED_CLINICAL_DOCS WHERE HERO_PATIENT = 'HERO-PT-003'
;
