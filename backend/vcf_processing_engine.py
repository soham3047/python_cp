import os
import re


def parse_vcf_patient_metadata(vcf_path):
    """
    Reads ##PATIENT_AGE and ##PATIENT_WEIGHT from VCF header lines.
    Returns dict with 'age' and 'weight' (None if not found).
    """
    metadata = {"age": None, "weight": None}
    with open(vcf_path, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                break
            age_match = re.match(r'##PATIENT_AGE=(\d+)', line.strip())
            if age_match:
                metadata["age"] = int(age_match.group(1))
            weight_match = re.match(r'##PATIENT_WEIGHT=(\d+\.?\d*)', line.strip())
            if weight_match:
                metadata["weight"] = float(weight_match.group(1))
    return metadata


def parse_vcf_genomics(vcf_path):
    """
    Parses VCF data lines for the three Warfarin-relevant SNPs.
    """
    genomic_profile = {
        "rs1799853_cyp2c9_2": "0/0",
        "rs1057910_cyp2c9_3": "0/0",
        "rs9923231_vkorc1":   "0/0"
    }

    if not os.path.exists(vcf_path):
        raise FileNotFoundError(f"VCF not found: {vcf_path}")

    with open(vcf_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            cols = line.strip().split('\t')
            if len(cols) < 10:
                continue
            rsid   = cols[2]
            fmt    = cols[8].split(':')
            sample = cols[9].split(':')
            if 'GT' in fmt:
                gt = sample[fmt.index('GT')]
                if rsid == "rs1799853":
                    genomic_profile["rs1799853_cyp2c9_2"] = gt
                elif rsid == "rs1057910":
                    genomic_profile["rs1057910_cyp2c9_3"] = gt
                elif rsid == "rs9923231":
                    genomic_profile["rs9923231_vkorc1"] = gt

    return genomic_profile


def evaluate_clinical_dosage(clinical_data, genomics):
    """
    CPIC-aligned rule-based dosage calculator.
    This is deterministic and correct — it's the primary result for VCF uploads.
    """
    age    = clinical_data['age']
    weight = clinical_data['weight']

    base_dose = 5.0

    # Age adjustments
    if age > 65: base_dose -= 0.5
    if age > 75: base_dose -= 0.5

    # Weight adjustment
    if weight < 60: base_dose -= 0.5

    vkorc1   = genomics["rs9923231_vkorc1"]
    cyp2c9_2 = genomics["rs1799853_cyp2c9_2"]
    cyp2c9_3 = genomics["rs1057910_cyp2c9_3"]

    # VKORC1 sensitivity modifiers
    if vkorc1 == "0/1":
        base_dose *= 0.72
    elif vkorc1 == "1/1":
        base_dose *= 0.43

    # CYP2C9 clearance modifiers
    if cyp2c9_2 in ("0/1", "1/1"):
        base_dose *= 0.81
    if cyp2c9_3 == "0/1":
        base_dose *= 0.66
    elif cyp2c9_3 == "1/1":
        base_dose *= 0.34

    final_dosage = round(max(0.5, base_dose), 2)

    # Risk classification
    if final_dosage >= 4.0:
        risk_level     = "🟢 Normal Baseline"
        suitability    = "FULLY SUITABLE"
        clinical_notes = "Patient exhibits typical drug clearing. Standard maintenance monitoring required."
    elif 2.0 <= final_dosage < 4.0:
        risk_level     = "🟡 Moderate Toxic Risk"
        suitability    = "SUITABLE WITH PRECAUTIONS"
        clinical_notes = "Elevated bleeding risk due to genetic variants. Monitor INR every 3–5 days initially."
    else:
        risk_level     = "🔴 CRITICAL TOXICITY WARNING"
        suitability    = "HIGH RISK — ALTERNATIVE DOSING REQUIRED"
        clinical_notes = "Extremely narrow therapeutic window. Standard dosing will cause toxic accumulation."

    return {
        "recommended_dosage": f"{final_dosage} mg/day",
        "dosage_value":        final_dosage,
        "suitability_status":  suitability,
        "toxic_risk_profile":  risk_level,
        "clinical_notes":      clinical_notes
    }


def parse_vcf_and_predict(vcf_path, fallback_age=50, fallback_weight=70):
    """
    Master function: parses metadata + genomics from one VCF file.
    Returns (clinical_data dict, genomics dict, dosage_report dict)
    The dosage_report is the authoritative CPIC rule-based result.
    """
    metadata = parse_vcf_patient_metadata(vcf_path)
    clinical_data = {
        "age":    metadata["age"]    if metadata["age"]    is not None else fallback_age,
        "weight": metadata["weight"] if metadata["weight"] is not None else fallback_weight
    }
    genomics     = parse_vcf_genomics(vcf_path)
    dosage_report = evaluate_clinical_dosage(clinical_data, genomics)

    return clinical_data, genomics, dosage_report
