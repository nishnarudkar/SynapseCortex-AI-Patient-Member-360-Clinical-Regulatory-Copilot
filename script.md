# Video Demonstration & Pitch Script: SynapseCortex AI

**Project Name**: SynapseCortex AI — Patient & Member 360 & Clinical Regulatory Copilot  
**Target Duration**: 3 to 5 Minutes  
**Audience**: Hackathon Judges, Healthcare Executives, Solutions Architects, & Clinical Informatics Leaders  

---

## 🎬 Overview & Timing Breakdown

| Scene | Section | Duration (3-Min Pitch) | Duration (5-Min Demo) | Key Visual Focus |
| :--- | :--- | :--- | :--- | :--- |
| **Scene 1** | **Title & Executive Problem Statement** | 0:00 – 0:35 | 0:00 – 0:45 | Title Slide / Streamlit Header |
| **Scene 2** | **Architecture & Snowflake-Native Advantage** | 0:35 – 1:00 | 0:45 – 1:30 | Pipeline Diagram / Architecture |
| **Scene 3** | **Demo 1: Patient 360 & Medication Safety (Hero 1)** | 1:00 – 1:45 | 1:30 – 2:45 | Tab 1 & Tab 2 (Robert Callahan) |
| **Scene 4** | **Demo 2: Care Quality Gaps & HEDIS (Hero 2)** | 1:45 – 2:15 | 2:45 – 3:30 | Tab 1 (Linda Moreno) |
| **Scene 5** | **Demo 3: High-Risk Polypharmacy & MCP Action Dispatch** | 2:15 – 2:45 | 3:30 – 4:30 | Tab 2 Dispatcher & MCP Payload |
| **Scene 6** | **Conclusion & Business Impact Summary** | 2:45 – 3:00 | 4:30 – 5:00 | Snowsight Architecture & URLs |

---

## 🎙️ Scene-by-Scene Script & Recording Guide

### 📍 Scene 1: Introduction & The Healthcare Data Paradox
**Screen Action**: Show the **SynapseCortex AI Streamlit App header** in Snowsight or open the main landing view.

- **[VISUAL CUE]**: Cursor hovers over top banner: *"SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot"*.

- **[VOICEOVER]**:
  > *"Hello everyone! Welcome to the demonstration of **SynapseCortex AI** — a Snowflake-native clinical intelligence platform designed to solve one of healthcare's greatest challenges: **the data fragmentation paradox**.*
  >
  > *Over 80% of actionable clinical information — such as physician consult notes and complex FDA regulatory package inserts — remains trapped in unstructured text documents. At the same time, critical patient metrics like lab results, claims cost, and diagnoses sit isolated in relational database tables.*
  >
  > *SynapseCortex AI unifies structured Electronic Health Record data with unstructured clinical narratives and FDA package inserts — executing **100% natively inside Snowflake** under strict citation enforcement."*

---

### 📍 Scene 2: Snowflake-Native Dual-RAG Architecture
**Screen Action**: Switch to the **Data Processing Pipeline & Architecture Diagram** (or scroll to the pipeline flowchart in `Readme.md`).

- **[VISUAL CUE]**: Highlight the 4 layers: Raw Data Ingestion → Data Transformation → Serving (Cortex Search) → Dual-RAG Engine (`llama3.3-70b`).

- **[VOICEOVER]**:
  > *"Architecturally, SynapseCortex AI operates under a **Zero Data Movement** paradigm. 
  > 
  > 1. Structured lab observations, claims, and encounter records are combined in Snowflake via `TRANSFORMED.PATIENT_360_VIEW`.
  > 2. Clinical encounter notes and FDA package inserts are staged in an SSE-encrypted stage and indexed by **Snowflake Cortex Search** using `snowflake-arctic-embed-l-v2.0` embeddings.
  > 3. When a clinician asks a question, our **Dual-RAG Engine** retrieves both the structured Patient 360 snapshot and vector document chunks, synthesizing them with **Snowflake Cortex COMPLETE (`llama3.3-70b`)**.
  >
  > *Because everything runs inside Snowflake, zero protected health data ever leaves your security perimeter."*

---

### 📍 Scene 3: Demo 1 — Patient 360 & Medication Safety (Hero 1)
**Screen Action**: Navigate to **Tab 1 (Patient 360 Dashboard)**. Select **`Hero 1 — Safety Violation: Robert Callahan`**.

- **[VISUAL CUE]**: Point out the red top metric banner: **`ALERT: Metformin active with eGFR < 45 (CKD contraindication)`**. Scroll down to show eGFR 38 mL/min and Creatinine 2.4 mg/dL in the LOINC Lab Results table.

- **[VOICEOVER]**:
  > *"Let's look at our first hero profile: **Robert Callahan**, a 58-year-old patient with Stage 3 Chronic Kidney Disease. 
  > 
  > *Notice on Tab 1, our deterministic SQL engine immediately flags a **Drug Safety Alert**: Robert has an active Metformin prescription despite an eGFR of 38 mL/min.*
  >
  > *Now let's switch to **Tab 2 — Clinical & Regulatory Copilot**.*

**Screen Action**: Click on **Tab 2 (Clinical & Regulatory Copilot)** and select the suggested query: *"Is Metformin contraindicated for this patient given their kidney function?"*

- **[VISUAL CUE]**: Point to the answer text and highlight inline citation badges: `[Structured Data · p.N/A]` and `[fda_inserts/fda_insert_METFORMIN.txt · p.1]`. Expand the **Retrieved Document Chunks** drawer.

- **[VOICEOVER]**:
  > *"Notice how the Copilot responds. Every factual assertion is grounded with exact inline citations. It references both the structured lab data from Snowflake tables AND page 1 of the official FDA Metformin Package Insert, warning the prescriber of renal impairment risks and recommending safer alternatives.*
  >
  > *If evidence is missing, the model is strictly prompt-engineered to return 'Insufficient evidence' — eliminating clinical hallucinations."*

---

### 📍 Scene 4: Demo 2 — Preventive Care Quality Gap (Hero 2)
**Screen Action**: Switch back to **Tab 1** and select **`Hero 2 — Care Gap: Linda Moreno`**.

- **[VISUAL CUE]**: Point to the gold banner: **`GAP: Overdue HbA1c Lab (HEDIS NQF-0059 · CMS Star)`**. Show last recorded HbA1c of 7.8% dated over 14 months ago.

- **[VOICEOVER]**:
  > *"Next, let's examine **Linda Moreno**, a 62-year-old diabetic member. 
  > 
  > *Here, SynapseCortex AI evaluates longitudinal lab timelines against **HEDIS NQF-0059** and **CMS Star Rating** rules. Because Linda hasn't completed an HbA1c test in 14 months, the platform flags an unclosed quality gap.*
  >
  > *Closing these care gaps proactively protects Medicare Advantage Star Ratings and prevents costly diabetes complications."*

---

### 📍 Scene 5: Demo 3 — High-Risk Polypharmacy & MCP Action Dispatcher
**Screen Action**: Select **`Hero 3 — High Risk: James Whitfield`** on **Tab 2**. Scroll down to the **Clinical Action Required** box.

- **[VISUAL CUE]**: Point out James's 8 chronic conditions, $51,755 claims expenditure, and 7 active medications. Select Action type: **`Pharmacovigilance Review`** and Dispatch via: **`Jira Ticket`**. Click **`Dispatch Care Action`**. Expand the **Action Payload (MCP Trigger Simulation)** JSON viewer.

- **[VOICEOVER]**:
  > *"Finally, consider **James Whitfield**, a 71-year-old high-risk patient with $51,000 in YTD claims and complex polypharmacy across COPD and CKD.*
  >
  > *When a high-risk safety or care gap flag is identified, clinicians can trigger immediate workflow actions using our **Clinical Action Dispatcher**.*
  >
  > *Here, we simulate a **Model Context Protocol (MCP) trigger** to automatically create an audited Jira Ticket for pharmacovigilance review. The system generates an immutable, ISO-timestamped JSON payload for full regulatory compliance and auditability."*

---

### 📍 Scene 6: Conclusion & Executive Summary
**Screen Action**: Return to the **Streamlit main header** or open the **Snowsight App view**.

- **[VISUAL CUE]**: Display the repo link: `github.com/nishnarudkar/SynapseCortex-AI-Patient-Member-360-Clinical-Regulatory-Copilot` and Snowsight URL.

- **[VOICEOVER]**:
  > *"To summarize: **SynapseCortex AI** bridges the gap between structured EHR relational data and unstructured clinical narratives. 
  > 
  > *By leveraging **Snowflake Cortex Search**, **CORTEX.COMPLETE with llama3.3-70b**, and native Streamlit UI — all inside Snowflake — we deliver real-time medication safety, automated care quality gap closure, and compliant workflow automation with zero data egress.*
  >
  > *Thank you for watching! Check out our full open-source code and technical documentation on GitHub."*

---

## 🎥 Recording & Presentation Checklist

### 1. Pre-Recording Setup
- [ ] Open Snowsight or local Streamlit app at `http://localhost:8501`.
- [ ] Set browser zoom level to **100% or 110%** for clear screen readability.
- [ ] Ensure full screen resolution (1920x1080 or 4K scaled).
- [ ] Close extra browser tabs and notifications.

### 2. Audio & Speech Tips
- [ ] Speak clearly and at a moderate, confident pace (~130-150 words per minute).
- [ ] Pause 1-2 seconds after clicking buttons or tabs to allow visual transition.
- [ ] Emphasize key terms: **"Snowflake-Native"**, **"Zero Data Movement"**, **"Dual-RAG"**, **"Strict Inline Citations"**, and **"MCP Workflow Dispatcher"**.

### 3. Screen Pointer / Mouse Movement
- [ ] Smoothly guide mouse cursor to elements before speaking about them.
- [ ] Highlight the red alert banners, LOINC table values, citation badges, and JSON payload logs.
