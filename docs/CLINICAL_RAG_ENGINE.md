# SynapseCortex AI — Clinical RAG Engine Specification

## Technical Overview

The `app/rag_engine.py` module implements the Dual-RAG (Retrieval-Augmented Generation) copilot engine powering SynapseCortex AI. The engine synthesizes structured longitudinal patient history with unstructured clinical encounter notes and FDA package inserts under strict citation enforcement.

---

## Key Components

### 1. Context Assembler
The `ClinicalCopilot` class connects to Snowflake using Snowpark (`Session`) and extracts two distinct context sources:

- **Context A (Structured Patient 360)**: Fetched from `APP.PATIENT_360_SNAPSHOT`. Contains demographic attributes, ICD-10 diagnosis codes, active medication lists, LOINC lab observations (eGFR, Creatinine, HbA1c), total claims cost, computed risk tier, and care gap status.
- **Context B (Unstructured Documents)**: Retrieved via `snowflake.core.Root(session).databases[...].schemas[...].cortex_search_services["CLINICAL_DOC_SEARCH"]`. Top-$k$ ($k=5$) text chunks are retrieved using hybrid semantic and lexical vector search.

### 2. Search Service Configuration
- **Cortex Search Service**: `APP.CLINICAL_DOC_SEARCH`
- **Embedding Model**: `snowflake-arctic-embed-l-v2.0`
- **Indexed Table**: `TRANSFORMED.PARSED_CLINICAL_DOCS`
- **Search Attributes**: `file_name`, `page_number`, `doc_category`, `hero_patient`, `page_text`

### 3. LLM Configuration
- **Model**: `llama3.3-70b`
- **Temperature**: `0.05` (Near-zero temperature for deterministic clinical output)
- **Max Tokens**: `1024` tokens
- **Inference Interface**: `SNOWFLAKE.CORTEX.COMPLETE` SQL function / Python SDK

---

## Citation Enforcement Rules

The system prompt strictly regulates LLM output formatting to guarantee evidence traceability:

```text
INSTRUCTIONS:
1. Synthesize answers STRICTLY using the two provided contexts:
   - CONTEXT A: Patient 360 Structured Data
   - CONTEXT B: Clinical Document Chunks (retrieved via Cortex Search)
2. For EVERY factual claim in your response, append an inline citation using this exact format:
   [Doc: <file_name>, Page: <page_number>]
   Use 'Structured Data' as the source name when citing CONTEXT A fields.
3. If no supporting evidence exists in EITHER context for a claim, respond with EXACTLY:
   Insufficient evidence.
4. Structure your response with:
   - A direct answer to the question (1-2 sentences)
   - Supporting evidence (bullet points with inline citations)
   - Recommended action (if clinically indicated, cited from context)
```

---

## Data Structure Definitions

### `Patient360Context` Dataclass
```python
@dataclass
class Patient360Context:
    patient_id: str
    full_name: str
    age: int
    gender: str
    insurance_plan: str
    active_medications_list: str | None
    active_medication_count: int
    total_claims_cost: float
    last_hba1c_date: str | None
    last_hba1c_value: float | None
    last_egfr_value: float | None
    last_creatinine_value: float | None
    all_dx_codes: str | None
    all_dx_descriptions: str | None
    chronic_condition_count: int
    encounter_count: int
    last_encounter_date: str | None
    has_diabetes_dx: bool
    has_ckd_dx: bool
    risk_tier: str
    care_gap_status: str
    drug_safety_flag: str | None
```

### `DocumentChunk` Dataclass
```python
@dataclass
class DocumentChunk:
    file_name: str
    page_number: int
    doc_category: str
    hero_patient: str | None
    page_text: str
    score: float = 0.0
```

### `CopilotResult` Dataclass
```python
@dataclass
class CopilotResult:
    patient_id: str
    query: str
    answer: str
    patient_context: Patient360Context | None
    document_chunks: list[DocumentChunk]
    model_used: str = "llama3.3-70b"
    warning: str | None = None
```

---

## Code Execution Example

```python
from app.rag_engine import ClinicalCopilot
from snowflake.snowpark.context import get_active_session

# Acquire active Snowflake session inside Streamlit / Notebook
session = get_active_session()
copilot = ClinicalCopilot(session)

# Execute Dual-RAG query
result = copilot.answer(
    patient_id="HERO-PT-001",
    user_query="Is Metformin contraindicated for this patient given their lab results?"
)

print("Answer:", result.answer)
print("Retrieved Chunks:", len(result.document_chunks))
```
