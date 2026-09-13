-- =============================================================================
-- SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
-- Script  : 01_database_schemas.sql
-- Purpose : Create SYNAPSE_HEALTH database and the three top-level schemas
-- Author  : SynapseCortex Data Engineering
-- Date    : 2026-09-13
-- =============================================================================

-- ── Database ─────────────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS SYNAPSE_HEALTH
    DATA_RETENTION_TIME_IN_DAYS = 7
    COMMENT = 'SynapseCortex AI – unified clinical, claims, and lab data platform';

USE DATABASE SYNAPSE_HEALTH;

-- ── Schemas ──────────────────────────────────────────────────────────────────

-- RAW: landing zone for ingested source data (immutable)
CREATE SCHEMA IF NOT EXISTS RAW
    DATA_RETENTION_TIME_IN_DAYS = 7
    COMMENT = 'Raw landing zone – source-of-truth; no transformations applied';

-- TRANSFORMED: curated, conformed, and enriched clinical entities
CREATE SCHEMA IF NOT EXISTS TRANSFORMED
    DATA_RETENTION_TIME_IN_DAYS = 7
    COMMENT = 'Cleaned, conformed, and enriched clinical data ready for analytics';

-- APP: application-layer views, feature tables, and AI/ML serving tables
CREATE SCHEMA IF NOT EXISTS APP
    DATA_RETENTION_TIME_IN_DAYS = 7
    COMMENT = 'Application layer – Patient 360 views, risk scores, copilot artefacts';

-- ── Confirm ───────────────────────────────────────────────────────────────────
SHOW SCHEMAS IN DATABASE SYNAPSE_HEALTH;
