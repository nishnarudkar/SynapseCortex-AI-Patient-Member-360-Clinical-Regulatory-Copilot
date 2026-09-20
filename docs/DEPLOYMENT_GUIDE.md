# SynapseCortex AI — Deployment & Setup Guide

## Prerequisites & System Requirements

Before deploying SynapseCortex AI, verify that the following prerequisites are satisfied:

- **Python Runtime**: Python version 3.10 or higher (Tested on Python 3.13).
- **Snowflake Account**: Enterprise Edition account with `ACCOUNTADMIN` or `SYSADMIN` administrative credentials.
- **Cortex AI Access**: Database role `SNOWFLAKE.CORTEX_USER` granted to the active user role.
- **Git**: Git client installed for repository management.

---

## 1. Environment Configuration

Clone the repository and initialize a Python virtual environment:

```bash
git clone https://github.com/nishnarudkar/SynapseCortex-AI-Patient-Member-360-Clinical-Regulatory-Copilot.git
cd SynapseCortex-AI-Patient-Member-360-Clinical-Regulatory-Copilot

# Create virtual environment
python -m venv venv

# Activate environment (Linux/macOS)
source venv/bin/activate

# Activate environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt
```

Create a `.env` configuration file in the project root:

```env
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=SYNAPSE_WH
SNOWFLAKE_DATABASE=SYNAPSE_HEALTH
SNOWFLAKE_SCHEMA=APP
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

---

## 2. Database Objects & Data Pipeline Setup

### Option A: Automated Script Ingestion (Recommended)

Run the automated Python upload and parsing pipeline:

```bash
# Upload synthetic CSVs and text files to Snowflake stage
python upload_to_snowflake.py

# Execute local document parsing into TRANSFORMED.PARSED_CLINICAL_DOCS
python parse_and_load_docs.py
```

### Option B: Manual SQL Execution via Snowsight

Open **Snowsight Worksheets** and execute the DDL scripts under `snowflake/ddl/` in the following sequence:

1. `01_database_schemas.sql` — Provisions database `SYNAPSE_HEALTH`, schemas `RAW`, `TRANSFORMED`, `APP`, and warehouse `SYNAPSE_WH`.
2. `02_raw_tables.sql` — Constructs structured tables `PATIENTS`, `ENCOUNTERS`, `CLAIMS`, and `LABS`.
3. `03_clinical_stage.sql` — Creates internal stage `@CLINICAL_STAGE` with `SNOWFLAKE_SSE` encryption.
4. `05_parsed_clinical_docs.sql` — Creates `TRANSFORMED.PARSED_CLINICAL_DOCS` with `CHANGE_TRACKING = TRUE`.
5. `06_cortex_search_service.sql` — Initializes `APP.CLINICAL_DOC_SEARCH` Cortex Search Service.
6. `08_patient_360_and_copilot.sql` — Generates `PATIENT_360_VIEW` and materializes `PATIENT_360_SNAPSHOT`.

---

## 3. Deploying to Streamlit in Snowflake (SiS)

1. Log into your **Snowflake Snowsight Console**.
2. In the left navigation menu, navigate to **Projects** → **Streamlit**.
3. Click **+ Streamlit App** in the top right corner.
4. Set application metadata:
   - **App Title**: `SynapseCortex AI`
   - **App Location**: Database `SYNAPSE_HEALTH`, Schema `APP`
   - **Warehouse**: `SYNAPSE_WH`
5. Copy the entire contents of `app/app.py` into the main code editor window.
6. In the left file tree panel, click **+ File**, name it `rag_engine.py`, and paste the contents of `app/rag_engine.py`.
7. Click **Run** to execute and launch the application natively inside Snowflake.

---

## 4. Local Development Verification

To run and verify the Streamlit app locally against your Snowflake instance:

```bash
streamlit run app/app.py
```

The application will launch on `http://localhost:8501`.
