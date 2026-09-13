"""
=============================================================================
SynapseCortex AI | Patient 360 & Clinical Regulatory Copilot
Script  : generate_synthetic_data.py
Purpose : Generate 50 synthetic, referentially intact patient records using
          Faker and write them as CSV files ready for bulk-load into
          SYNAPSE_HEALTH.RAW (PATIENTS, ENCOUNTERS, CLAIMS, LABS).

          Three hero test cases are embedded with clinical precision:
            - Hero 1 (Safety Violation) : Age 58, Renal Impairment + Metformin
            - Hero 2 (Care Gap)         : Age 62, Diabetes, no HbA1c in 14 months
            - Hero 3 (High Risk)        : Age 71, multi-chronic, claims > $50,000

Dependencies:
    pip install faker==24.0.0 pandas==2.2.2

Usage:
    python generate_synthetic_data.py
    (outputs CSV files into ./output/ ready for Snowflake PUT / COPY INTO)
=============================================================================
"""

import csv
import os
import random
import uuid
from datetime import date, datetime, timedelta

from faker import Faker

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY = date(2026, 9, 13)

# ── Reference data ────────────────────────────────────────────────────────────
GENDERS         = ["Male", "Female", "Non-binary"]
RACES           = ["White", "Black or African American", "Asian", "Hispanic or Latino",
                   "American Indian or Alaska Native", "Two or more races"]
ETHNICITIES     = ["Not Hispanic or Latino", "Hispanic or Latino"]
ENCOUNTER_TYPES = ["Outpatient", "Inpatient", "Telehealth", "ED", "Specialist"]
CLAIM_TYPES     = ["Medical", "Pharmacy"]
CLAIM_STATUSES  = ["Paid", "Denied", "Pending", "Adjusted"]
RESULT_STATUSES = ["Final", "Preliminary", "Corrected"]
ABNORMAL_FLAGS  = ["N", "H", "L", "HH", "LL", "A"]
INSURANCE_PLANS = ["BlueCross PPO", "Aetna HMO", "United Gold", "Cigna Open Access",
                   "Humana Choice", "Medicare Advantage", "Medicaid MCO"]
PAYER_NAMES     = ["BlueCross BlueShield", "Aetna", "UnitedHealthcare",
                   "Cigna", "Humana", "CMS Medicare", "State Medicaid"]

# Common chronic ICD-10 codes
ICD10_COMMON = [
    ("E11.9",  "Type 2 diabetes mellitus without complications"),
    ("I10",    "Essential (primary) hypertension"),
    ("J44.1",  "Chronic obstructive pulmonary disease with acute exacerbation"),
    ("M79.3",  "Panniculitis"),
    ("F32.1",  "Major depressive disorder, single episode, moderate"),
    ("K21.0",  "Gastro-esophageal reflux disease with oesophagitis"),
    ("N18.3",  "Chronic kidney disease, stage 3"),
    ("E78.5",  "Hyperlipidemia, unspecified"),
    ("Z87.39", "Personal history of other musculoskeletal disorders"),
    ("G47.33", "Obstructive sleep apnea"),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris"),
    ("E66.9",  "Obesity, unspecified"),
    ("M54.5",  "Low back pain"),
    ("Z79.4",  "Long-term (current) use of insulin"),
]

# Common labs (LOINC)
LOINC_COMMON = [
    ("2160-0",  "Creatinine [Mass/volume] in Serum or Plasma",  "mg/dL",   "0.6-1.2"),
    ("33914-3", "eGFR [Volume Rate/Area] in Serum or Plasma",   "mL/min",  "60-120"),
    ("2085-9",  "HDL Cholesterol",                              "mg/dL",   "40-60"),
    ("2089-1",  "LDL Cholesterol",                              "mg/dL",   "<100"),
    ("2093-3",  "Total Cholesterol",                            "mg/dL",   "<200"),
    ("2571-8",  "Triglycerides",                                "mg/dL",   "<150"),
    ("4548-4",  "Hemoglobin A1c/Hemoglobin.total in Blood",     "%",       "4.0-5.6"),
    ("6690-2",  "WBC [#/volume] in Blood",                      "K/uL",    "4.5-11.0"),
    ("718-7",   "Hemoglobin [Mass/volume] in Blood",            "g/dL",    "12.0-17.5"),
    ("2823-3",  "Potassium [Moles/volume] in Serum or Plasma",  "mEq/L",   "3.5-5.0"),
    ("2951-2",  "Sodium [Moles/volume] in Serum or Plasma",     "mEq/L",   "136-145"),
    ("14627-4", "Bicarbonate [Moles/volume] in Venous blood",   "mEq/L",   "22-29"),
    ("6768-6",  "Alkaline phosphatase [Enzymatic activity/volume] in Serum", "U/L", "44-147"),
    ("1742-6",  "ALT [Enzymatic activity/volume] in Serum",     "U/L",     "7-56"),
]

# Drugs
DRUG_POOL = [
    "Lisinopril 10mg", "Atorvastatin 20mg", "Metoprolol 25mg",
    "Amlodipine 5mg",  "Omeprazole 20mg",   "Levothyroxine 50mcg",
    "Sertraline 50mg", "Hydrochlorothiazide 25mg", "Gabapentin 300mg",
    "Albuterol Inhaler 90mcg", "Aspirin 81mg", "Clopidogrel 75mg",
    "Furosemide 40mg", "Pantoprazole 40mg", "Losartan 50mg",
]


# =============================================================================
# Helper utilities
# =============================================================================

def new_id() -> str:
    return str(uuid.uuid4())


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def rand_npi() -> str:
    return str(random.randint(1000000000, 9999999999))


def rand_drugs(n: int = 2) -> str:
    """Return a JSON-style array string of medications."""
    drugs = random.sample(DRUG_POOL, min(n, len(DRUG_POOL)))
    return '["' + '", "'.join(drugs) + '"]'


def rand_dx_array(codes: list, n: int = 2) -> str:
    selected = random.sample(codes, min(n, len(codes)))
    arr = [c[0] for c in selected]
    return '["' + '", "'.join(arr) + '"]'


def rand_proc_codes(n: int = 1) -> str:
    cpt = [str(random.randint(99201, 99499)) for _ in range(n)]
    return '["' + '", "'.join(cpt) + '"]'


def billed_amount(low: float, high: float) -> float:
    return round(random.uniform(low, high), 2)


def dob_from_age(age: int) -> date:
    birth_year = TODAY.year - age
    return date(birth_year, random.randint(1, 12), random.randint(1, 28))


# =============================================================================
# Data containers
# =============================================================================
patients_rows  = []
encounter_rows = []
claims_rows    = []
labs_rows      = []


# =============================================================================
# Hero Patient 1 – Safety Violation
#   Age 58 | Renal Impairment (N18.3 CKD Stage 3) | Metformin prescribed
# =============================================================================
HERO1_ID  = "HERO-PT-001-" + str(uuid.uuid4())[:8]
HERO1_DOB = dob_from_age(58)

hero1_patient = {
    "PATIENT_ID":       HERO1_ID,
    "FIRST_NAME":       "Robert",
    "LAST_NAME":        "Callahan",
    "DATE_OF_BIRTH":    HERO1_DOB.isoformat(),
    "AGE":              58,
    "GENDER":           "Male",
    "RACE":             "White",
    "ETHNICITY":        "Not Hispanic or Latino",
    "ADDRESS_LINE1":    "4812 Oakwood Drive",
    "CITY":             "Atlanta",
    "STATE":            "GA",
    "ZIP_CODE":         "30301",
    "PHONE":            "404-555-0191",
    "EMAIL":            "r.callahan@synapsedemo.org",
    "INSURANCE_ID":     "BC-88441122",
    "INSURANCE_PLAN":   "BlueCross PPO",
    "PRIMARY_CARE_NPI": rand_npi(),
    "ACTIVE_FLAG":      True,
    "CREATED_AT":       datetime(2026, 1, 10, 9, 0, 0),
    "UPDATED_AT":       datetime(2026, 9, 1, 14, 22, 0),
}
patients_rows.append(hero1_patient)

# Encounter with CKD + Metformin prescription
HERO1_ENC_ID = new_id()
hero1_encounter = {
    "ENCOUNTER_ID":      HERO1_ENC_ID,
    "PATIENT_ID":        HERO1_ID,
    "ENCOUNTER_DATE":    date(2026, 8, 5).isoformat(),
    "ENCOUNTER_TYPE":    "Outpatient",
    "FACILITY_NAME":     "Piedmont Atlanta Medical Center",
    "FACILITY_NPI":      rand_npi(),
    "ATTENDING_NPI":     rand_npi(),
    "PRIMARY_DX_CODE":   "N18.3",
    "PRIMARY_DX_DESC":   "Chronic kidney disease, stage 3 (moderate)",
    "SECONDARY_DX_CODES":'["I10", "E11.9", "E78.5"]',
    "PROCEDURE_CODES":   '["99214"]',
    "PRESCRIPTION_LIST": '["Metformin 1000mg", "Lisinopril 10mg", "Atorvastatin 20mg"]',
    "DISCHARGE_DATE":    date(2026, 8, 5).isoformat(),
    "DISCHARGE_STATUS":  "Discharged to home",
    "NOTES_REF":         "clinical_notes/hero1_note_ROBERT_CALLAHAN.txt",
    "CREATED_AT":        datetime(2026, 8, 5, 10, 30, 0),
    "UPDATED_AT":        datetime(2026, 8, 5, 16, 45, 0),
}
encounter_rows.append(hero1_encounter)

# Claims for Hero 1
for i, (desc, amount, drug_name, ndc) in enumerate([
    ("Office visit – established patient",  320.00, None,        None),
    ("Metformin 1000mg – 90-day supply",    89.50,  "Metformin", "0093-1048-01"),
    ("Lisinopril 10mg – 90-day supply",     42.00,  "Lisinopril", "0093-2183-01"),
    ("Comprehensive metabolic panel",       215.00, None,        None),
    ("eGFR / Renal function panel",         198.00, None,        None),
]):
    claims_rows.append({
        "CLAIM_ID":           new_id(),
        "PATIENT_ID":         HERO1_ID,
        "ENCOUNTER_ID":       HERO1_ENC_ID if i == 0 else None,
        "CLAIM_TYPE":         "Pharmacy" if drug_name else "Medical",
        "CLAIM_DATE":         date(2026, 8, 10).isoformat(),
        "SERVICE_FROM_DATE":  date(2026, 8, 5).isoformat(),
        "SERVICE_TO_DATE":    date(2026, 8, 5).isoformat(),
        "BILLED_AMOUNT":      amount,
        "ALLOWED_AMOUNT":     round(amount * 0.85, 2),
        "PAID_AMOUNT":        round(amount * 0.80, 2),
        "PATIENT_COPAY":      round(amount * 0.05, 2),
        "CLAIM_STATUS":       "Paid",
        "DENIAL_REASON":      None,
        "DX_CODE_PRIMARY":    "N18.3",
        "DX_CODE_SECONDARY":  '["I10", "E11.9"]',
        "PROCEDURE_CODE":     "99214" if not drug_name else None,
        "PROCEDURE_DESC":     desc,
        "NDC_CODE":           ndc,
        "DRUG_NAME":          drug_name,
        "PROVIDER_NPI":       hero1_encounter["ATTENDING_NPI"],
        "PAYER_ID":           "BC-001",
        "PAYER_NAME":         "BlueCross BlueShield",
        "CREATED_AT":         datetime(2026, 8, 10, 8, 0, 0),
        "UPDATED_AT":         datetime(2026, 8, 10, 8, 0, 0),
    })

# Labs for Hero 1 – elevated creatinine confirming CKD
for (loinc, name, unit, ref), val, flag in [
    (("2160-0",  "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL", "0.6-1.2"),  "2.4", "H"),
    (("33914-3", "eGFR [Volume Rate/Area] in Serum or Plasma",  "mL/min","60-120"),   "38",  "L"),
    (("2823-3",  "Potassium [Moles/volume] in Serum or Plasma", "mEq/L", "3.5-5.0"),  "5.2", "H"),
    (("6690-2",  "WBC [#/volume] in Blood",                     "K/uL",  "4.5-11.0"), "7.1", "N"),
]:
    labs_rows.append({
        "LAB_ID":           new_id(),
        "PATIENT_ID":       HERO1_ID,
        "ENCOUNTER_ID":     HERO1_ENC_ID,
        "ORDER_DATE":       date(2026, 8, 5).isoformat(),
        "RESULT_DATE":      date(2026, 8, 6).isoformat(),
        "LAB_TEST_CODE":    loinc,
        "LAB_TEST_NAME":    name,
        "RESULT_VALUE":     val,
        "RESULT_UNIT":      unit,
        "REFERENCE_RANGE":  ref,
        "ABNORMAL_FLAG":    flag,
        "RESULT_STATUS":    "Final",
        "PERFORMING_LAB":   "Quest Diagnostics Atlanta",
        "ORDERING_NPI":     hero1_encounter["ATTENDING_NPI"],
        "CREATED_AT":       datetime(2026, 8, 6, 7, 0, 0),
        "UPDATED_AT":       datetime(2026, 8, 6, 7, 0, 0),
    })


# =============================================================================
# Hero Patient 2 – Care Gap
#   Age 62 | Diabetes (E11.9) | No HbA1c in past 14 months (last: July 2025)
# =============================================================================
HERO2_ID  = "HERO-PT-002-" + str(uuid.uuid4())[:8]
HERO2_DOB = dob_from_age(62)

hero2_patient = {
    "PATIENT_ID":       HERO2_ID,
    "FIRST_NAME":       "Linda",
    "LAST_NAME":        "Moreno",
    "DATE_OF_BIRTH":    HERO2_DOB.isoformat(),
    "AGE":              62,
    "GENDER":           "Female",
    "RACE":             "Hispanic or Latino",
    "ETHNICITY":        "Hispanic or Latino",
    "ADDRESS_LINE1":    "1102 Sunflower Lane",
    "CITY":             "San Antonio",
    "STATE":            "TX",
    "ZIP_CODE":         "78201",
    "PHONE":            "210-555-0382",
    "EMAIL":            "l.moreno@synapsedemo.org",
    "INSURANCE_ID":     "AE-77221133",
    "INSURANCE_PLAN":   "Aetna HMO",
    "PRIMARY_CARE_NPI": rand_npi(),
    "ACTIVE_FLAG":      True,
    "CREATED_AT":       datetime(2025, 3, 15, 9, 0, 0),
    "UPDATED_AT":       datetime(2026, 8, 20, 11, 0, 0),
}
patients_rows.append(hero2_patient)

HERO2_ENC_ID = new_id()
hero2_encounter = {
    "ENCOUNTER_ID":      HERO2_ENC_ID,
    "PATIENT_ID":        HERO2_ID,
    "ENCOUNTER_DATE":    date(2026, 8, 20).isoformat(),
    "ENCOUNTER_TYPE":    "Outpatient",
    "FACILITY_NAME":     "Methodist Healthcare San Antonio",
    "FACILITY_NPI":      rand_npi(),
    "ATTENDING_NPI":     rand_npi(),
    "PRIMARY_DX_CODE":   "E11.9",
    "PRIMARY_DX_DESC":   "Type 2 diabetes mellitus without complications",
    "SECONDARY_DX_CODES":'["I10", "E78.5", "E66.9"]',
    "PROCEDURE_CODES":   '["99213"]',
    "PRESCRIPTION_LIST": '["Metformin 500mg", "Glipizide 5mg", "Lisinopril 10mg"]',
    "DISCHARGE_DATE":    date(2026, 8, 20).isoformat(),
    "DISCHARGE_STATUS":  "Discharged to home",
    "NOTES_REF":         "clinical_notes/hero2_note_LINDA_MORENO.txt",
    "CREATED_AT":        datetime(2026, 8, 20, 9, 0, 0),
    "UPDATED_AT":        datetime(2026, 8, 20, 15, 0, 0),
}
encounter_rows.append(hero2_encounter)

# Claims for Hero 2
for i, (desc, amount, drug, ndc) in enumerate([
    ("Office visit – established patient",  285.00, None,         None),
    ("Metformin 500mg – 90-day supply",     55.00,  "Metformin",  "0093-1033-01"),
    ("Glipizide 5mg – 90-day supply",       38.00,  "Glipizide",  "0093-1035-01"),
    ("HbA1c test (ordered, declined)",      125.00, None,         None),
]):
    claims_rows.append({
        "CLAIM_ID":           new_id(),
        "PATIENT_ID":         HERO2_ID,
        "ENCOUNTER_ID":       HERO2_ENC_ID if i == 0 else None,
        "CLAIM_TYPE":         "Pharmacy" if drug else "Medical",
        "CLAIM_DATE":         date(2026, 8, 25).isoformat(),
        "SERVICE_FROM_DATE":  date(2026, 8, 20).isoformat(),
        "SERVICE_TO_DATE":    date(2026, 8, 20).isoformat(),
        "BILLED_AMOUNT":      amount,
        "ALLOWED_AMOUNT":     round(amount * 0.82, 2),
        "PAID_AMOUNT":        round(amount * 0.75, 2),
        "PATIENT_COPAY":      round(amount * 0.07, 2),
        "CLAIM_STATUS":       "Denied" if "declined" in desc else "Paid",
        "DENIAL_REASON":      "Patient refused laboratory collection" if "declined" in desc else None,
        "DX_CODE_PRIMARY":    "E11.9",
        "DX_CODE_SECONDARY":  '["I10", "E78.5"]',
        "PROCEDURE_CODE":     "83036" if "HbA1c" in desc else "99213",
        "PROCEDURE_DESC":     desc,
        "NDC_CODE":           ndc,
        "DRUG_NAME":          drug,
        "PROVIDER_NPI":       hero2_encounter["ATTENDING_NPI"],
        "PAYER_ID":           "AE-002",
        "PAYER_NAME":         "Aetna",
        "CREATED_AT":         datetime(2026, 8, 25, 8, 0, 0),
        "UPDATED_AT":         datetime(2026, 8, 25, 8, 0, 0),
    })

# HbA1c from July 2025 (14 months ago – triggers care gap)
labs_rows.append({
    "LAB_ID":           new_id(),
    "PATIENT_ID":       HERO2_ID,
    "ENCOUNTER_ID":     None,
    "ORDER_DATE":       date(2025, 7, 10).isoformat(),
    "RESULT_DATE":      date(2025, 7, 11).isoformat(),
    "LAB_TEST_CODE":    "4548-4",
    "LAB_TEST_NAME":    "Hemoglobin A1c/Hemoglobin.total in Blood",
    "RESULT_VALUE":     "7.8",
    "RESULT_UNIT":      "%",
    "REFERENCE_RANGE":  "4.0-5.6",
    "ABNORMAL_FLAG":    "H",
    "RESULT_STATUS":    "Final",
    "PERFORMING_LAB":   "LabCorp San Antonio",
    "ORDERING_NPI":     hero2_encounter["ATTENDING_NPI"],
    "CREATED_AT":       datetime(2025, 7, 11, 7, 30, 0),
    "UPDATED_AT":       datetime(2025, 7, 11, 7, 30, 0),
})

# Additional routine labs at recent visit (NO HbA1c – the care gap)
for (loinc, name, unit, ref), val, flag in [
    (("2085-9",  "HDL Cholesterol",          "mg/dL", "40-60"),   "38", "L"),
    (("2089-1",  "LDL Cholesterol",          "mg/dL", "<100"),   "128", "H"),
    (("2093-3",  "Total Cholesterol",        "mg/dL", "<200"),   "218", "H"),
]:
    labs_rows.append({
        "LAB_ID":           new_id(),
        "PATIENT_ID":       HERO2_ID,
        "ENCOUNTER_ID":     HERO2_ENC_ID,
        "ORDER_DATE":       date(2026, 8, 20).isoformat(),
        "RESULT_DATE":      date(2026, 8, 21).isoformat(),
        "LAB_TEST_CODE":    loinc,
        "LAB_TEST_NAME":    name,
        "RESULT_VALUE":     val,
        "RESULT_UNIT":      unit,
        "REFERENCE_RANGE":  ref,
        "ABNORMAL_FLAG":    flag,
        "RESULT_STATUS":    "Final",
        "PERFORMING_LAB":   "LabCorp San Antonio",
        "ORDERING_NPI":     hero2_encounter["ATTENDING_NPI"],
        "CREATED_AT":       datetime(2026, 8, 21, 7, 0, 0),
        "UPDATED_AT":       datetime(2026, 8, 21, 7, 0, 0),
    })


# =============================================================================
# Hero Patient 3 – High Risk
#   Age 71 | Multiple chronic diagnoses | Total claims > $50,000
# =============================================================================
HERO3_ID  = "HERO-PT-003-" + str(uuid.uuid4())[:8]
HERO3_DOB = dob_from_age(71)

hero3_patient = {
    "PATIENT_ID":       HERO3_ID,
    "FIRST_NAME":       "James",
    "LAST_NAME":        "Whitfield",
    "DATE_OF_BIRTH":    HERO3_DOB.isoformat(),
    "AGE":              71,
    "GENDER":           "Male",
    "RACE":             "Black or African American",
    "ETHNICITY":        "Not Hispanic or Latino",
    "ADDRESS_LINE1":    "309 Magnolia Street",
    "CITY":             "Chicago",
    "STATE":            "IL",
    "ZIP_CODE":         "60601",
    "PHONE":            "312-555-0710",
    "EMAIL":            "j.whitfield@synapsedemo.org",
    "INSURANCE_ID":     "MA-55991100",
    "INSURANCE_PLAN":   "Medicare Advantage",
    "PRIMARY_CARE_NPI": rand_npi(),
    "ACTIVE_FLAG":      True,
    "CREATED_AT":       datetime(2024, 6, 1, 9, 0, 0),
    "UPDATED_AT":       datetime(2026, 9, 5, 10, 0, 0),
}
patients_rows.append(hero3_patient)

# Multiple encounters for Hero 3
hero3_encounters = [
    {
        "enc_date":    date(2026, 1, 15),
        "type":        "Inpatient",
        "dx_primary":  ("I25.10", "Atherosclerotic heart disease of native coronary artery"),
        "sec_dx":      '["I10", "E11.9", "N18.3", "J44.1", "E78.5"]',
        "proc":        '["93454", "93458"]',
        "rx":          '["Clopidogrel 75mg", "Aspirin 81mg", "Atorvastatin 80mg", "Carvedilol 25mg", "Furosemide 40mg"]',
        "discharge":   date(2026, 1, 20),
        "status":      "Discharged to skilled nursing facility",
        "note_ref":    "clinical_notes/hero3_note_JAMES_WHITFIELD_inpatient.txt",
    },
    {
        "enc_date":    date(2026, 4, 8),
        "type":        "Outpatient",
        "dx_primary":  ("J44.1", "Chronic obstructive pulmonary disease with acute exacerbation"),
        "sec_dx":      '["I25.10", "I10", "E11.9"]',
        "proc":        '["94060"]',
        "rx":          '["Albuterol Inhaler 90mcg", "Tiotropium 18mcg", "Prednisone 40mg"]',
        "discharge":   date(2026, 4, 8),
        "status":      "Discharged to home",
        "note_ref":    "clinical_notes/hero3_note_JAMES_WHITFIELD_outpatient.txt",
    },
    {
        "enc_date":    date(2026, 7, 22),
        "type":        "ED",
        "dx_primary":  ("I10", "Hypertensive crisis"),
        "sec_dx":      '["I25.10", "N18.3", "E11.9"]',
        "proc":        '["99285"]',
        "rx":          '["IV Labetalol 20mg", "Amlodipine 10mg"]',
        "discharge":   date(2026, 7, 22),
        "status":      "Discharged to home",
        "note_ref":    "clinical_notes/hero3_note_JAMES_WHITFIELD_ED.txt",
    },
]

hero3_enc_ids = []
for enc_def in hero3_encounters:
    eid = new_id()
    hero3_enc_ids.append(eid)
    encounter_rows.append({
        "ENCOUNTER_ID":      eid,
        "PATIENT_ID":        HERO3_ID,
        "ENCOUNTER_DATE":    enc_def["enc_date"].isoformat(),
        "ENCOUNTER_TYPE":    enc_def["type"],
        "FACILITY_NAME":     "Northwestern Memorial Hospital",
        "FACILITY_NPI":      rand_npi(),
        "ATTENDING_NPI":     rand_npi(),
        "PRIMARY_DX_CODE":   enc_def["dx_primary"][0],
        "PRIMARY_DX_DESC":   enc_def["dx_primary"][1],
        "SECONDARY_DX_CODES":enc_def["sec_dx"],
        "PROCEDURE_CODES":   enc_def["proc"],
        "PRESCRIPTION_LIST": enc_def["rx"],
        "DISCHARGE_DATE":    enc_def["discharge"].isoformat(),
        "DISCHARGE_STATUS":  enc_def["status"],
        "NOTES_REF":         enc_def["note_ref"],
        "CREATED_AT":        datetime.combine(enc_def["enc_date"], datetime.min.time()),
        "UPDATED_AT":        datetime.combine(enc_def["discharge"], datetime.min.time()),
    })

# Claims for Hero 3 – total must exceed $50,000
hero3_claim_defs = [
    # Inpatient cardiac (high cost)
    ("Inpatient hospital – cardiac catheterization",  28500.00, None,       None,        hero3_enc_ids[0], "Medical", "93454"),
    ("Atorvastatin 80mg – 90-day supply",               112.00, "Atorvastatin", "0071-0156-23", None, "Pharmacy", None),
    ("Clopidogrel 75mg – 90-day supply",                 95.00, "Clopidogrel",  "0173-0721-04", None, "Pharmacy", None),
    ("Aspirin 81mg – 90-day supply",                     12.00, "Aspirin",      "0904-7704-40", None, "Pharmacy", None),
    ("Cardiac rehab program – 12 sessions",            3600.00, None,       None,        None, "Medical", "93797"),
    # COPD outpatient
    ("Pulmonary function test",                          850.00, None,       None,        hero3_enc_ids[1], "Medical", "94060"),
    ("Albuterol Inhaler 90mcg – 2 inhalers",             88.00, "Albuterol", "59310-0579-22", None, "Pharmacy", None),
    ("Tiotropium 18mcg – 30-day supply",                 245.00, "Tiotropium","0597-0075-41", None, "Pharmacy", None),
    # ED hypertensive crisis
    ("Emergency department visit – level 5",            6800.00, None,      None,        hero3_enc_ids[2], "Medical", "99285"),
    ("IV medication administration",                    1200.00, None,       None,        hero3_enc_ids[2], "Medical", "96365"),
    ("Amlodipine 10mg – 90-day supply",                   48.00, "Amlodipine","0069-1540-66", None, "Pharmacy", None),
    # Ongoing chronic condition management
    ("Diabetes management – endocrinology consult",    1850.00, None,        None,        None, "Medical", "99245"),
    ("Annual echocardiogram",                          2200.00, None,        None,        None, "Medical", "93306"),
    ("Renal function monitoring panel",                  320.00, None,       None,        None, "Medical", "80069"),
    ("Furosemide 40mg – 90-day supply",                   35.00, "Furosemide","0781-1268-01", None, "Pharmacy", None),
    ("Home health nursing visits x8",                  5800.00, None,        None,        None, "Medical", "G0299"),
]

for (desc, amount, drug, ndc, enc_id, ctype, proc_code) in hero3_claim_defs:
    claims_rows.append({
        "CLAIM_ID":           new_id(),
        "PATIENT_ID":         HERO3_ID,
        "ENCOUNTER_ID":       enc_id,
        "CLAIM_TYPE":         ctype,
        "CLAIM_DATE":         date(2026, 8, 1).isoformat(),
        "SERVICE_FROM_DATE":  date(2026, 1, 15).isoformat(),
        "SERVICE_TO_DATE":    date(2026, 9, 1).isoformat(),
        "BILLED_AMOUNT":      amount,
        "ALLOWED_AMOUNT":     round(amount * 0.88, 2),
        "PAID_AMOUNT":        round(amount * 0.84, 2),
        "PATIENT_COPAY":      round(amount * 0.04, 2),
        "CLAIM_STATUS":       "Paid",
        "DENIAL_REASON":      None,
        "DX_CODE_PRIMARY":    "I25.10",
        "DX_CODE_SECONDARY":  '["I10", "E11.9", "N18.3", "J44.1"]',
        "PROCEDURE_CODE":     proc_code,
        "PROCEDURE_DESC":     desc,
        "NDC_CODE":           ndc,
        "DRUG_NAME":          drug,
        "PROVIDER_NPI":       rand_npi(),
        "PAYER_ID":           "MA-001",
        "PAYER_NAME":         "CMS Medicare",
        "CREATED_AT":         datetime(2026, 8, 1, 8, 0, 0),
        "UPDATED_AT":         datetime(2026, 8, 1, 8, 0, 0),
    })

# Labs for Hero 3
for (loinc, name, unit, ref), val, flag, enc_idx in [
    (("2160-0",  "Creatinine [Mass/volume] in Serum or Plasma",  "mg/dL", "0.6-1.2"), "2.1",  "H",  0),
    (("33914-3", "eGFR [Volume Rate/Area] in Serum or Plasma",   "mL/min","60-120"),  "42",   "L",  0),
    (("4548-4",  "Hemoglobin A1c/Hemoglobin.total in Blood",     "%",     "4.0-5.6"), "8.4",  "H",  1),
    (("6690-2",  "WBC [#/volume] in Blood",                      "K/uL",  "4.5-11.0"),"9.8",  "N",  1),
    (("718-7",   "Hemoglobin [Mass/volume] in Blood",            "g/dL",  "12.0-17.5"),"10.2", "L",  2),
    (("2089-1",  "LDL Cholesterol",                              "mg/dL", "<100"),    "142",  "H",  2),
    (("2093-3",  "Total Cholesterol",                            "mg/dL", "<200"),    "235",  "H",  2),
    (("2823-3",  "Potassium [Moles/volume] in Serum or Plasma",  "mEq/L", "3.5-5.0"),"5.6",  "H",  2),
]:
    labs_rows.append({
        "LAB_ID":           new_id(),
        "PATIENT_ID":       HERO3_ID,
        "ENCOUNTER_ID":     hero3_enc_ids[enc_idx],
        "ORDER_DATE":       hero3_encounters[enc_idx]["enc_date"].isoformat(),
        "RESULT_DATE":      (hero3_encounters[enc_idx]["enc_date"] + timedelta(days=1)).isoformat(),
        "LAB_TEST_CODE":    loinc,
        "LAB_TEST_NAME":    name,
        "RESULT_VALUE":     val,
        "RESULT_UNIT":      unit,
        "REFERENCE_RANGE":  ref,
        "ABNORMAL_FLAG":    flag,
        "RESULT_STATUS":    "Final",
        "PERFORMING_LAB":   "Northwestern Memorial Laboratory",
        "ORDERING_NPI":     rand_npi(),
        "CREATED_AT":       datetime.combine(
                                hero3_encounters[enc_idx]["enc_date"] + timedelta(days=1),
                                datetime.min.time()),
        "UPDATED_AT":       datetime.combine(
                                hero3_encounters[enc_idx]["enc_date"] + timedelta(days=1),
                                datetime.min.time()),
    })


# =============================================================================
# Generate 47 additional synthetic patients (IDs 4–50)
# =============================================================================
print("Generating 47 synthetic background patients...")

STATES = ["CA", "TX", "FL", "NY", "PA", "OH", "GA", "NC", "IL", "AZ",
          "WA", "CO", "NV", "TN", "MN", "WI", "MO", "IN", "MA", "MD"]

for i in range(47):
    pid = new_id()
    age = random.randint(18, 85)
    dob = dob_from_age(age)
    gender = random.choice(GENDERS)

    patients_rows.append({
        "PATIENT_ID":       pid,
        "FIRST_NAME":       fake.first_name_male() if gender == "Male" else fake.first_name_female(),
        "LAST_NAME":        fake.last_name(),
        "DATE_OF_BIRTH":    dob.isoformat(),
        "AGE":              age,
        "GENDER":           gender,
        "RACE":             random.choice(RACES),
        "ETHNICITY":        random.choice(ETHNICITIES),
        "ADDRESS_LINE1":    fake.street_address(),
        "CITY":             fake.city(),
        "STATE":            random.choice(STATES),
        "ZIP_CODE":         fake.zipcode(),
        "PHONE":            fake.phone_number()[:20],
        "EMAIL":            fake.email(),
        "INSURANCE_ID":     fake.bothify("??-########").upper(),
        "INSURANCE_PLAN":   random.choice(INSURANCE_PLANS),
        "PRIMARY_CARE_NPI": rand_npi(),
        "ACTIVE_FLAG":      random.choices([True, False], weights=[92, 8])[0],
        "CREATED_AT":       fake.date_time_between(start_date="-3y", end_date="-6m"),
        "UPDATED_AT":       fake.date_time_between(start_date="-6m", end_date="now"),
    })

    # 1–3 encounters per patient
    num_enc = random.randint(1, 3)
    patient_enc_ids = []
    for _ in range(num_enc):
        eid = new_id()
        patient_enc_ids.append(eid)
        dx = random.choice(ICD10_COMMON)
        enc_date = rand_date(date(2025, 1, 1), TODAY)
        enc_type = random.choice(ENCOUNTER_TYPES)
        encounter_rows.append({
            "ENCOUNTER_ID":      eid,
            "PATIENT_ID":        pid,
            "ENCOUNTER_DATE":    enc_date.isoformat(),
            "ENCOUNTER_TYPE":    enc_type,
            "FACILITY_NAME":     fake.company() + " Medical Center",
            "FACILITY_NPI":      rand_npi(),
            "ATTENDING_NPI":     rand_npi(),
            "PRIMARY_DX_CODE":   dx[0],
            "PRIMARY_DX_DESC":   dx[1],
            "SECONDARY_DX_CODES":rand_dx_array(ICD10_COMMON, random.randint(0, 3)),
            "PROCEDURE_CODES":   rand_proc_codes(random.randint(1, 2)),
            "PRESCRIPTION_LIST": rand_drugs(random.randint(1, 4)),
            "DISCHARGE_DATE":    (enc_date + timedelta(days=random.randint(0, 5))).isoformat(),
            "DISCHARGE_STATUS":  "Discharged to home",
            "NOTES_REF":         None,
            "CREATED_AT":        datetime.combine(enc_date, datetime.min.time()),
            "UPDATED_AT":        datetime.combine(enc_date, datetime.min.time()),
        })

        # 1–3 claims per encounter
        for _ in range(random.randint(1, 3)):
            ctype = random.choice(CLAIM_TYPES)
            bill  = billed_amount(50, 4000)
            claims_rows.append({
                "CLAIM_ID":           new_id(),
                "PATIENT_ID":         pid,
                "ENCOUNTER_ID":       eid,
                "CLAIM_TYPE":         ctype,
                "CLAIM_DATE":         (enc_date + timedelta(days=random.randint(3, 15))).isoformat(),
                "SERVICE_FROM_DATE":  enc_date.isoformat(),
                "SERVICE_TO_DATE":    enc_date.isoformat(),
                "BILLED_AMOUNT":      bill,
                "ALLOWED_AMOUNT":     round(bill * random.uniform(0.70, 0.95), 2),
                "PAID_AMOUNT":        round(bill * random.uniform(0.65, 0.90), 2),
                "PATIENT_COPAY":      round(bill * random.uniform(0.01, 0.10), 2),
                "CLAIM_STATUS":       random.choices(CLAIM_STATUSES, weights=[70, 10, 15, 5])[0],
                "DENIAL_REASON":      fake.sentence(nb_words=6) if random.random() < 0.1 else None,
                "DX_CODE_PRIMARY":    dx[0],
                "DX_CODE_SECONDARY":  rand_dx_array(ICD10_COMMON, 1),
                "PROCEDURE_CODE":     str(random.randint(99201, 99499)),
                "PROCEDURE_DESC":     fake.bs()[:100],
                "NDC_CODE":           fake.bothify("####-####-##") if ctype == "Pharmacy" else None,
                "DRUG_NAME":          random.choice(DRUG_POOL) if ctype == "Pharmacy" else None,
                "PROVIDER_NPI":       rand_npi(),
                "PAYER_ID":           fake.bothify("??-####").upper(),
                "PAYER_NAME":         random.choice(PAYER_NAMES),
                "CREATED_AT":         datetime.combine(enc_date, datetime.min.time()),
                "UPDATED_AT":         datetime.combine(enc_date, datetime.min.time()),
            })

        # 0–3 labs per encounter
        for _ in range(random.randint(0, 3)):
            lab = random.choice(LOINC_COMMON)
            order_dt = enc_date
            result_dt = order_dt + timedelta(days=random.randint(0, 3))
            labs_rows.append({
                "LAB_ID":           new_id(),
                "PATIENT_ID":       pid,
                "ENCOUNTER_ID":     eid,
                "ORDER_DATE":       order_dt.isoformat(),
                "RESULT_DATE":      result_dt.isoformat(),
                "LAB_TEST_CODE":    lab[0],
                "LAB_TEST_NAME":    lab[1],
                "RESULT_VALUE":     str(round(random.uniform(0.5, 200.0), 1)),
                "RESULT_UNIT":      lab[2],
                "REFERENCE_RANGE":  lab[3],
                "ABNORMAL_FLAG":    random.choices(ABNORMAL_FLAGS, weights=[60, 15, 10, 5, 5, 5])[0],
                "RESULT_STATUS":    random.choice(RESULT_STATUSES),
                "PERFORMING_LAB":   random.choice(["Quest Diagnostics", "LabCorp", "BioReference"]),
                "ORDERING_NPI":     rand_npi(),
                "CREATED_AT":       datetime.combine(result_dt, datetime.min.time()),
                "UPDATED_AT":       datetime.combine(result_dt, datetime.min.time()),
            })


# =============================================================================
# Validation summary
# =============================================================================
hero3_total_claims = sum(
    r["BILLED_AMOUNT"] for r in claims_rows if r["PATIENT_ID"] == HERO3_ID
)
print(f"\n─── Dataset Summary ───────────────────────────────────────────")
print(f"  Patients   : {len(patients_rows):>5}  (50 total, 3 hero + 47 synthetic)")
print(f"  Encounters : {len(encounter_rows):>5}")
print(f"  Claims     : {len(claims_rows):>5}")
print(f"  Labs       : {len(labs_rows):>5}")
print(f"\n  Hero 1 [{HERO1_ID[:20]}] – CKD N18.3 + Metformin → Safety Violation")
print(f"  Hero 2 [{HERO2_ID[:20]}] – Diabetes + No HbA1c 14mo → Care Gap")
print(f"  Hero 3 [{HERO3_ID[:20]}] – Multi-chronic, Claims = ${hero3_total_claims:,.2f} → High Risk ✓" if hero3_total_claims > 50000 else f"  Hero 3 – WARNING: total claims ${hero3_total_claims:,.2f} < $50,000!")
print(f"───────────────────────────────────────────────────────────────\n")

assert len(patients_rows)  == 50, "Expected exactly 50 patients"
assert hero3_total_claims  >  50000, f"Hero 3 claims must exceed $50,000 (got {hero3_total_claims})"


# =============================================================================
# Write CSV output files
# =============================================================================
FIELD_MAPS = {
    "PATIENTS":   ["PATIENT_ID","FIRST_NAME","LAST_NAME","DATE_OF_BIRTH","AGE",
                   "GENDER","RACE","ETHNICITY","ADDRESS_LINE1","CITY","STATE",
                   "ZIP_CODE","PHONE","EMAIL","INSURANCE_ID","INSURANCE_PLAN",
                   "PRIMARY_CARE_NPI","ACTIVE_FLAG","CREATED_AT","UPDATED_AT"],
    "ENCOUNTERS": ["ENCOUNTER_ID","PATIENT_ID","ENCOUNTER_DATE","ENCOUNTER_TYPE",
                   "FACILITY_NAME","FACILITY_NPI","ATTENDING_NPI","PRIMARY_DX_CODE",
                   "PRIMARY_DX_DESC","SECONDARY_DX_CODES","PROCEDURE_CODES",
                   "PRESCRIPTION_LIST","DISCHARGE_DATE","DISCHARGE_STATUS",
                   "NOTES_REF","CREATED_AT","UPDATED_AT"],
    "CLAIMS":     ["CLAIM_ID","PATIENT_ID","ENCOUNTER_ID","CLAIM_TYPE","CLAIM_DATE",
                   "SERVICE_FROM_DATE","SERVICE_TO_DATE","BILLED_AMOUNT",
                   "ALLOWED_AMOUNT","PAID_AMOUNT","PATIENT_COPAY","CLAIM_STATUS",
                   "DENIAL_REASON","DX_CODE_PRIMARY","DX_CODE_SECONDARY",
                   "PROCEDURE_CODE","PROCEDURE_DESC","NDC_CODE","DRUG_NAME",
                   "PROVIDER_NPI","PAYER_ID","PAYER_NAME","CREATED_AT","UPDATED_AT"],
    "LABS":       ["LAB_ID","PATIENT_ID","ENCOUNTER_ID","ORDER_DATE","RESULT_DATE",
                   "LAB_TEST_CODE","LAB_TEST_NAME","RESULT_VALUE","RESULT_UNIT",
                   "REFERENCE_RANGE","ABNORMAL_FLAG","RESULT_STATUS",
                   "PERFORMING_LAB","ORDERING_NPI","CREATED_AT","UPDATED_AT"],
}

TABLE_DATA = {
    "PATIENTS":   patients_rows,
    "ENCOUNTERS": encounter_rows,
    "CLAIMS":     claims_rows,
    "LABS":       labs_rows,
}

for table_name, rows in TABLE_DATA.items():
    filepath = os.path.join(OUTPUT_DIR, f"{table_name.lower()}.csv")
    fields   = FIELD_MAPS[table_name]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ Wrote {len(rows):>4} rows → {filepath}")

print("\nAll CSV files ready.  Next step: run snowflake/stage/04_stage_and_load.sql\n")
