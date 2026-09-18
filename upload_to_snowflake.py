"""
SynapseCortex AI – upload_to_snowflake.py
Uploads clinical docs and CSV files to Snowflake stage,
then runs COPY INTO to load the RAW tables.
Run from the project root:
    python upload_to_snowflake.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from snowflake.snowpark import Session

# ── Load credentials from .env ────────────────────────────────────────────────
load_dotenv()

connection_params = {
    "account":   os.environ["SNOWFLAKE_ACCOUNT"],
    "user":      os.environ["SNOWFLAKE_USER"],
    "password":  os.environ["SNOWFLAKE_PASSWORD"],
    "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
    "database":  os.environ["SNOWFLAKE_DATABASE"],
    "schema":    "RAW",
    "role":      os.environ["SNOWFLAKE_ROLE"],
}

BASE = Path(__file__).parent

# ── Files to upload ───────────────────────────────────────────────────────────
CLINICAL_DOCS = [
    (BASE / "clinical_docs/clinical_notes/hero1_note_ROBERT_CALLAHAN.txt",          "@RAW.CLINICAL_STAGE/clinical_notes/"),
    (BASE / "clinical_docs/clinical_notes/hero2_note_LINDA_MORENO.txt",             "@RAW.CLINICAL_STAGE/clinical_notes/"),
    (BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt","@RAW.CLINICAL_STAGE/clinical_notes/"),
    (BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt","@RAW.CLINICAL_STAGE/clinical_notes/"),
    (BASE / "clinical_docs/clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt",       "@RAW.CLINICAL_STAGE/clinical_notes/"),
    (BASE / "clinical_docs/fda_inserts/fda_insert_METFORMIN.txt",                   "@RAW.CLINICAL_STAGE/fda_inserts/"),
    (BASE / "clinical_docs/fda_inserts/fda_insert_HBA1C_MONITORING_STANDARD.txt",   "@RAW.CLINICAL_STAGE/fda_inserts/"),
    (BASE / "clinical_docs/fda_inserts/fda_insert_POLYPHARMACY_HIGH_RISK.txt",      "@RAW.CLINICAL_STAGE/fda_inserts/"),
]

CSV_FILES = [
    (BASE / "data_generator/output/patients.csv",   "@RAW.CLINICAL_STAGE/data/"),
    (BASE / "data_generator/output/encounters.csv", "@RAW.CLINICAL_STAGE/data/"),
    (BASE / "data_generator/output/claims.csv",     "@RAW.CLINICAL_STAGE/data/"),
    (BASE / "data_generator/output/labs.csv",       "@RAW.CLINICAL_STAGE/data/"),
]

def upload_file(session, local_path: Path, stage_path: str):
    local_str = str(local_path).replace("\\", "/")
    print(f"  Uploading {local_path.name} → {stage_path} ...", end=" ")
    session.file.put(
        f"file://{local_str}",
        stage_path,
        auto_compress=False,
        overwrite=True,
    )
    print("✓")

def run_copy(session, sql: str, table: str):
    print(f"  COPY INTO {table} ...", end=" ")
    result = session.sql(sql).collect()
    rows = result[0]["rows_loaded"] if result else 0
    print(f"✓  {rows} rows loaded")

print("\n━━━ Connecting to Snowflake ━━━")
session = Session.builder.configs(connection_params).create()
print(f"  Connected as {connection_params['user']} on {connection_params['account']}")

# ── Upload clinical docs ──────────────────────────────────────────────────────
print("\n━━━ Uploading clinical notes & FDA inserts ━━━")
for local_path, stage_path in CLINICAL_DOCS:
    upload_file(session, local_path, stage_path)

# ── Upload CSVs ───────────────────────────────────────────────────────────────
print("\n━━━ Uploading CSV data files ━━━")
for local_path, stage_path in CSV_FILES:
    upload_file(session, local_path, stage_path)

# ── Refresh stage directory ───────────────────────────────────────────────────
print("\n━━━ Refreshing stage directory ━━━")
session.sql("ALTER STAGE RAW.CLINICAL_STAGE REFRESH").collect()
rows = session.sql("LIST @RAW.CLINICAL_STAGE").collect()
print(f"  Stage contains {len(rows)} files")
for r in rows:
    print(f"    {r['name']}")

# ── COPY INTO RAW tables ──────────────────────────────────────────────────────
print("\n━━━ Loading RAW tables ━━━")

run_copy(session, """
COPY INTO RAW.PATIENTS (
    PATIENT_ID,FIRST_NAME,LAST_NAME,DATE_OF_BIRTH,AGE,GENDER,RACE,ETHNICITY,
    ADDRESS_LINE1,CITY,STATE,ZIP_CODE,PHONE,EMAIL,INSURANCE_ID,INSURANCE_PLAN,
    PRIMARY_CARE_NPI,ACTIVE_FLAG,CREATED_AT,UPDATED_AT
) FROM @RAW.CLINICAL_STAGE/data/patients.csv
FILE_FORMAT=(FORMAT_NAME=RAW.CLINICAL_CSV_FORMAT)
ON_ERROR='ABORT_STATEMENT' PURGE=FALSE
""", "RAW.PATIENTS")

run_copy(session, """
COPY INTO RAW.ENCOUNTERS (
    ENCOUNTER_ID,PATIENT_ID,ENCOUNTER_DATE,ENCOUNTER_TYPE,FACILITY_NAME,
    FACILITY_NPI,ATTENDING_NPI,PRIMARY_DX_CODE,PRIMARY_DX_DESC,
    SECONDARY_DX_CODES,PROCEDURE_CODES,PRESCRIPTION_LIST,DISCHARGE_DATE,
    DISCHARGE_STATUS,NOTES_REF,CREATED_AT,UPDATED_AT
) FROM @RAW.CLINICAL_STAGE/data/encounters.csv
FILE_FORMAT=(FORMAT_NAME=RAW.CLINICAL_CSV_FORMAT)
ON_ERROR='ABORT_STATEMENT' PURGE=FALSE
""", "RAW.ENCOUNTERS")

run_copy(session, """
COPY INTO RAW.CLAIMS (
    CLAIM_ID,PATIENT_ID,ENCOUNTER_ID,CLAIM_TYPE,CLAIM_DATE,SERVICE_FROM_DATE,
    SERVICE_TO_DATE,BILLED_AMOUNT,ALLOWED_AMOUNT,PAID_AMOUNT,PATIENT_COPAY,
    CLAIM_STATUS,DENIAL_REASON,DX_CODE_PRIMARY,DX_CODE_SECONDARY,PROCEDURE_CODE,
    PROCEDURE_DESC,NDC_CODE,DRUG_NAME,PROVIDER_NPI,PAYER_ID,PAYER_NAME,
    CREATED_AT,UPDATED_AT
) FROM @RAW.CLINICAL_STAGE/data/claims.csv
FILE_FORMAT=(FORMAT_NAME=RAW.CLINICAL_CSV_FORMAT)
ON_ERROR='ABORT_STATEMENT' PURGE=FALSE
""", "RAW.CLAIMS")

run_copy(session, """
COPY INTO RAW.LABS (
    LAB_ID,PATIENT_ID,ENCOUNTER_ID,ORDER_DATE,RESULT_DATE,LAB_TEST_CODE,
    LAB_TEST_NAME,RESULT_VALUE,RESULT_UNIT,REFERENCE_RANGE,ABNORMAL_FLAG,
    RESULT_STATUS,PERFORMING_LAB,ORDERING_NPI,CREATED_AT,UPDATED_AT
) FROM @RAW.CLINICAL_STAGE/data/labs.csv
FILE_FORMAT=(FORMAT_NAME=RAW.CLINICAL_CSV_FORMAT)
ON_ERROR='ABORT_STATEMENT' PURGE=FALSE
""", "RAW.LABS")

# ── Validate row counts ───────────────────────────────────────────────────────
print("\n━━━ Validation — Row Counts ━━━")
counts = session.sql("""
    SELECT 'PATIENTS'   AS T, COUNT(*) AS N FROM RAW.PATIENTS  UNION ALL
    SELECT 'ENCOUNTERS',       COUNT(*)      FROM RAW.ENCOUNTERS UNION ALL
    SELECT 'CLAIMS',           COUNT(*)      FROM RAW.CLAIMS     UNION ALL
    SELECT 'LABS',             COUNT(*)      FROM RAW.LABS
""").collect()
expected = {"PATIENTS": 50, "ENCOUNTERS": 102, "CLAIMS": 215, "LABS": 150}
all_ok = True
for row in counts:
    status = "✓" if row["N"] == expected[row["T"]] else "✗"
    print(f"  {status} {row['T']:<12} {row['N']:>4} rows  (expected {expected[row['T']]})")
    if row["N"] != expected[row["T"]]:
        all_ok = False

print("\n" + ("✅ All data loaded successfully!" if all_ok else "⚠️  Some counts don't match — check errors above."))
session.close()
