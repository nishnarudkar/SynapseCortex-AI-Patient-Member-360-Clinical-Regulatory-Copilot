# 🏥 SynapseCortex AI: Patient & Member 360 & Clinical Regulatory Copilot

> **Built for the Snowflake CoCo CLI Hackathon**  
> *Unifying siloed EHR, claims, and dense unstructured clinical documents into an auditable, evidence-backed AI Copilot.*

---

## 📌 Problem Statement
Care and life sciences teams struggle with data scattered across structured EHR/claims tables and dense, unstructured PDF documents (discharge summaries, FDA drug inserts, clinical guidelines). Answers are traditionally slow, opaque, and uncited.

**SynapseCortex AI** solves this by unifying structured and unstructured healthcare data directly inside the **Snowflake Data Cloud**, delivering a **Patient 360 Dashboard** paired with a **Dual-RAG Evidence Retrieval Engine** that provides **zero opaque predictions and 100% cited source tracing**.

---

## 🛠️ Tech Stack & Enterprise Architecture

- **Data Cloud Platform:** Snowflake (Data Warehouse, Internal Stages, Dynamic Tables)
- **Developer & Orchestration Tooling:** Snowflake CoCo CLI (`cortex`), Agentic Workflows
- **Unstructured Processing:** Snowflake `SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT`
- **Vector & Search Engine:** Snowflake Cortex Search Service (Hybrid Semantic/Keyword Index)
- **LLM Synthesis & Grounding:** `SNOWFLAKE.CORTEX.COMPLETE` (`llama3.3-70b` / `mistral-large`)
- **Frontend App:** Streamlit in Snowflake (SiS)
- **Action Protocols:** Model Context Protocol (MCP) Integration for Jira/Slack automation

---

## 🚀 Key Features

1. **Privacy-Safe Synthetic Data Pipeline:** Fully synthetic, referentially consistent EHR, claims, and lab datasets generated and orchestrated via CoCo CLI.
2. **Native PDF Extraction (`AI_PARSE_DOCUMENT`):** Layout-aware parsing of clinical notes and FDA package inserts directly in SQL.
3. **Patient 360 & Risk Stratification View:** Real-time semantic aggregation calculating risk tiers (High/Low) and automated Care Gap indicators (e.g., overdue lab tests, contraindications).
4. **Strictly Cited Dual-RAG Copilot:** Answers clinical queries by synthesizing structured history with unstructured PDF chunks. Every claim contains an auditable inline citation (`[Doc: File_Name.pdf, Page: X]`).
5. **Actionable Governance (MCP Integration):** Auto-trigger clinical care tickets in Jira or post safety alerts in Slack directly from copilot findings.

---

## ⚙️ Lifecycle Orchestration via CoCo CLI

This repository demonstrates complete CoCo CLI usage across every lifecycle phase:
- **Planning:** Data model framing, DDL scaffolding, and synthetic dataset generation.
- **Development:** Building dynamic tables, vector indexes, and `AI_PARSE_DOCUMENT` pipelines.
- **Execution:** End-to-end orchestration from natural language input to SQL/Search retrieval.
- **Testing:** Automated accuracy verification and citation validity tests prior to deployment.

---

## 👨‍💻 Developer
Developed Solo by Nishant Narudkar 
*Targeting AI Systems Engineering & Enterprise Data Applications*