"""
SynapseCortex AI – parse_and_load_docs.py

Workaround for AI_PARSE_DOCUMENT not being available on this account.
Reads the .txt clinical docs and FDA inserts locally and inserts them
directly into TRANSFORMED.PARSED_CLINICAL_DOCS via Snowpark.

This is functionally identical to what AI_PARSE_DOCUMENT does for .txt files
(which just returns the raw text content anyway — no OCR or layout analysis
is applied to plain text files).

Run from the project root:
    python parse_and_load_docs.py
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.snowpark.types import (
    StructType, StructField,
    StringType, IntegerType, BooleanType, TimestampType, VariantType
)

# ── Load credentials ──────────────────────────────────────────────────────────
load_dotenv()

connection_params = {
    "account":   os.environ["SNOWFLAKE_ACCOUNT"],
    "user":      os.environ["SNOWFLAKE_USER"],
    "password":  os.environ["SNOWFLAKE_PASSWORD"],
    "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
    "database":  "SYNAPSE_HEALTH",
    "schema":    "TRANSFORMED",
    "role":      os.environ["SNOWFLAKE_ROLE"],
}

BASE = Path(__file__).parent

# ── Document definitions ──────────────────────────────────────────────────────
DOCS = [
    # (local_path, stage_relative_path, doc_category, hero_patient)
    (
        BASE / "clinical_docs/clinical_notes/hero1_note_ROBERT_CALLAHAN.txt",
        "clinical_notes/hero1_note_ROBERT_CALLAHAN.txt",
        "clinical_note", "HERO-PT-001",
    ),
    (
        BASE / "clinical_docs/clinical_notes/hero2_note_LINDA_MORENO.txt",
        "clinical_notes/hero2_note_LINDA_MORENO.txt",
        "clinical_note", "HERO-PT-002",
    ),
    (
        BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt",
        "clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt",
        "clinical_note", "HERO-PT-003",
    ),
    (
        BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt",
        "clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt",
        "clinical_note", "HERO-PT-003",
    ),
    (
        BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt",
        "clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt",
        "clinical_note", "HERO-PT-003",
    ),
    (
        BASE / "clinical_docs/fda_inserts/fda_insert_METFORMIN.txt",
        "fda_inserts/fda_insert_METFORMIN.txt",
        "fda_insert", "HERO-PT-001",
    ),
    (
        BASE / "clinical_docs/fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt",
        "fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt",
        "fda_insert", "HERO-PT-002",
    ),
    (
        BASE / "clinical_docs/fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt",
        "fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt",
        "fda_insert", "HERO-PT-003",
    ),
]

# ── Connect ───────────────────────────────────────────────────────────────────
print("\n━━━ Connecting to Snowflake ━━━")
session = Session.builder.configs(connection_params).create()
print(f"  Connected as {connection_params['user']}")

# ── Ensure table exists (create if not already created by 05 script) ──────────
print("\n━━━ Creating PARSED_CLINICAL_DOCS table if needed ━━━")
session.sql("""
CREATE TABLE IF NOT EXISTS TRANSFORMED.PARSED_CLINICAL_DOCS (
    DOC_ID          VARCHAR(36)       NOT NULL,
    FILE_NAME       VARCHAR(500)      NOT NULL,
    DOC_CATEGORY    VARCHAR(50)       NOT NULL,
    HERO_PATIENT    VARCHAR(50),
    PAGE_NUMBER     NUMBER(5,0)       NOT NULL,
    PAGE_TEXT       VARCHAR(16777216) NOT NULL,
    PARSE_MODE      VARCHAR(20)       NOT NULL DEFAULT 'LAYOUT',
    PAGE_SPLIT_USED BOOLEAN           NOT NULL DEFAULT FALSE,
    RAW_PARSE_JSON  VARIANT,
    PARSED_AT       TIMESTAMP_NTZ     NOT NULL,
    STAGE_FILE_URL  VARCHAR(1000),
    CONSTRAINT PK_PARSED_CLINICAL_DOCS PRIMARY KEY (DOC_ID)
)
DATA_RETENTION_TIME_IN_DAYS = 7
CHANGE_TRACKING = TRUE
""").collect()
print("  Table ready.")

# ── Clear any existing rows (idempotent re-run) ───────────────────────────────
session.sql("TRUNCATE TABLE IF EXISTS TRANSFORMED.PARSED_CLINICAL_DOCS").collect()
print("  Table truncated (clean insert).")

# ── Read and insert each document ─────────────────────────────────────────────
print("\n━━━ Parsing and inserting documents ━━━")

rows = []
now = datetime.now(timezone.utc).replace(tzinfo=None)

for local_path, stage_rel, doc_category, hero_patient in DOCS:
    text = local_path.read_text(encoding="utf-8")
    char_count = len(text)
    rows.append({
        "DOC_ID":          str(uuid.uuid4()),
        "FILE_NAME":       stage_rel,
        "DOC_CATEGORY":    doc_category,
        "HERO_PATIENT":    hero_patient,
        "PAGE_NUMBER":     1,
        "PAGE_TEXT":       text,
        "PARSE_MODE":      "LAYOUT",
        "PAGE_SPLIT_USED": False,
        "RAW_PARSE_JSON":  None,
        "PARSED_AT":       now,
        "STAGE_FILE_URL":  f"snow://file/RAW.CLINICAL_STAGE/{stage_rel}",
    })
    print(f"  ✓ {local_path.name:<55} {char_count:>6} chars")

# Write via Snowpark
df = session.create_dataframe(rows)
df.write.mode("append").save_as_table("TRANSFORMED.PARSED_CLINICAL_DOCS")
print(f"\n  Inserted {len(rows)} rows into TRANSFORMED.PARSED_CLINICAL_DOCS")

# ── Sanity check ──────────────────────────────────────────────────────────────
print("\n━━━ Validation ━━━")
result = session.sql("""
    SELECT
        DOC_CATEGORY,
        HERO_PATIENT,
        COUNT(*)                    AS total_rows,
        AVG(LENGTH(PAGE_TEXT))      AS avg_text_length
    FROM TRANSFORMED.PARSED_CLINICAL_DOCS
    GROUP BY 1, 2
    ORDER BY 1, 2
""").collect()

print(f"  {'CATEGORY':<15} {'HERO':<12} {'ROWS':>5}  {'AVG CHARS':>10}")
print(f"  {'-'*15} {'-'*12} {'-'*5}  {'-'*10}")
for r in result:
    print(f"  {r['DOC_CATEGORY']:<15} {str(r['HERO_PATIENT']):<12} {r['TOTAL_ROWS']:>5}  {int(r['AVG_TEXT_LENGTH']):>10}")

total = sum(r['TOTAL_ROWS'] for r in result)
print(f"\n  Total rows: {total}  (expected 8)")
print("\n✅ PARSED_CLINICAL_DOCS loaded successfully!" if total == 8 else "⚠️  Row count mismatch.")

session.close()
