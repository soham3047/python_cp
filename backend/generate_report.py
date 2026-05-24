"""
GeniDose - Clinical Dosage Report Generator
Matches the exact output of the GeniDose Control Panel / CPIC Engine.

Integrates with backend/app.py — call generate_patient_report(result_dict) 
after Calculate Optimal Dosage returns its JSON.

Usage (standalone):
    python generate_report.py                        # sample data
    python generate_report.py --input result.json    # real output JSON
    python generate_report.py --output report.pdf
"""

import argparse, json, os
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Colours ──────────────────────────────────────────────────────────────────
TEAL       = colors.HexColor("#0EA5C7")
TEAL_DARK  = colors.HexColor("#0D7F9B")
TEAL_BG    = colors.HexColor("#E0F7FB")
DARK       = colors.HexColor("#0F172A")
DARK2      = colors.HexColor("#1E293B")
GRAY       = colors.HexColor("#64748B")
GRAY_LIGHT = colors.HexColor("#F1F5F9")
WHITE      = colors.white
RED        = colors.HexColor("#EF4444")
RED_BG     = colors.HexColor("#FEE2E2")
AMBER      = colors.HexColor("#F59E0B")
AMBER_BG   = colors.HexColor("#FEF3C7")
GREEN      = colors.HexColor("#10B981")
GREEN_BG   = colors.HexColor("#D1FAE5")
PURPLE     = colors.HexColor("#8B5CF6")

# ── Sample data — mirrors exactly what the GeniDose UI shows ─────────────────
SAMPLE_DATA = {
    "patient": {
        "vcf_file":  "patient4.vcf",
        "age":       50,
        "weight_kg": 70,
        "parsed_from_vcf": True
    },
    "medication": {
        "name":     "Warfarin",
        "category": "Blood Thinner",
        "engine":   "CPIC Pharmacogenomic Rule Engine"
    },
    "cpic_result": {
        "recommended_dose_mgday": 1.74,
        "risk_level": "CRITICAL",          # CRITICAL | HIGH | MODERATE | LOW
        "warnings": [
            "CRITICAL TOXICITY WARNING",
            "HIGH RISK — ALTERNATIVE DOSING REQUIRED"
        ],
        "clinical_notes": [
            "Extremely narrow therapeutic window. Standard dosing will cause toxic accumulation."
        ]
    },
    "genotypes": [
        {"gene": "CYP2C9*2", "rsid": "rs3795853", "zygosity": "1/1",
         "phenotype": "Poor Metaboliser",      "impact": "HIGH"},
        {"gene": "CYP2C9*3", "rsid": "rs1057910", "zygosity": "0/0",
         "phenotype": "Normal / Wild Type",    "impact": "NONE"},
        {"gene": "VKORC1",   "rsid": "rs9923231", "zygosity": "1/1",
         "phenotype": "High Sensitivity",      "impact": "HIGH"},
    ],
    "fl_model": {
        "comparison_dose_mgday": 2.79,
        "note": "Improves after running more hospital terminals",
        "fl_round": 12,
        "participating_hospitals": 5,
        "aggregation": "FedAvg",
        "model_version": "GeniDose-FL v2.3.1",
        "accuracy_pct": 91.4,
        "auc_roc": 0.947
    },
    "report_meta": {
        "hospital_id":   "HOSP-MH-042",
        "hospital_name": "Manipal Hospital, Pune",
        "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "privacy_method": "Differential Privacy (ε = 0.5)"
    },
    "upcoming_drugs": [
        {"drug": "Clopidogrel", "gene": "CYP2C19", "status": "In Development"},
        {"drug": "Simvastatin",  "gene": "SLCO1B1", "status": "In Development"},
        {"drug": "Codeine",      "gene": "CYP2D6",  "status": "Planned"},
    ]
}

# ── Styles ────────────────────────────────────────────────────────────────────
def build_styles():
    S = {}
    S["cover_h1"]   = ParagraphStyle("cover_h1",   fontSize=30, textColor=WHITE,
                        fontName="Helvetica-Bold", alignment=TA_CENTER, leading=36)
    S["cover_sub"]  = ParagraphStyle("cover_sub",  fontSize=13, textColor=TEAL,
                        fontName="Helvetica",      alignment=TA_CENTER, leading=20)
    S["cover_meta"] = ParagraphStyle("cover_meta", fontSize=10, textColor=colors.HexColor("#CBD5E1"),
                        fontName="Helvetica",      alignment=TA_CENTER, leading=16)
    S["section"]    = ParagraphStyle("section",    fontSize=13, textColor=TEAL_DARK,
                        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=5)
    S["subsec"]     = ParagraphStyle("subsec",     fontSize=10.5, textColor=DARK,
                        fontName="Helvetica-Bold", spaceBefore=8,  spaceAfter=4)
    S["body"]       = ParagraphStyle("body",       fontSize=9.5, textColor=DARK,
                        fontName="Helvetica",      leading=14, spaceAfter=4)
    S["small"]      = ParagraphStyle("small",      fontSize=8,  textColor=GRAY,
                        fontName="Helvetica",      leading=12)
    S["dose_big"]   = ParagraphStyle("dose_big",   fontSize=36, textColor=RED,
                        fontName="Helvetica-Bold", alignment=TA_CENTER)
    S["dose_ok"]    = ParagraphStyle("dose_ok",    fontSize=36, textColor=GREEN,
                        fontName="Helvetica-Bold", alignment=TA_CENTER)
    S["warn_label"] = ParagraphStyle("warn_label", fontSize=8.5, textColor=WHITE,
                        fontName="Helvetica-Bold", alignment=TA_CENTER)
    S["note_text"]  = ParagraphStyle("note_text",  fontSize=9, textColor=colors.HexColor("#92400E"),
                        fontName="Helvetica",      leading=13,
                        backColor=AMBER_BG, borderPad=4)
    return S


# ── Table helpers ─────────────────────────────────────────────────────────────
def kv_table(rows, col_widths=None):
    base = getSampleStyleSheet()["Normal"]
    data = [[Paragraph(f"<b>{k}</b>", base), Paragraph(str(v), base)] for k, v in rows]
    t = Table(data, colWidths=col_widths or [7*cm, 9.5*cm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [TEAL_BG, GRAY_LIGHT]),
        ("FONTSIZE",  (0,0),(-1,-1), 9),
        ("GRID",      (0,0),(-1,-1), 0.3, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    return t


def col_table(headers, rows, col_widths=None):
    base = getSampleStyleSheet()["Normal"]
    h_row = [Paragraph(f"<b>{h}</b>", base) for h in headers]
    body  = [[Paragraph(str(c), base) for c in row] for row in rows]
    t = Table([h_row]+body, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), TEAL_DARK),
        ("TEXTCOLOR",   (0,0),(-1,0), WHITE),
        ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GRAY_LIGHT]),
        ("GRID",        (0,0),(-1,-1), 0.3, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING",  (0,0),(-1,-1), 7),
        ("RIGHTPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    return t


def badge_cell(text, bg_color, text_color=WHITE):
    """Single coloured badge cell."""
    style = ParagraphStyle("b", fontSize=8, fontName="Helvetica-Bold",
                           textColor=text_color, alignment=TA_CENTER)
    t = Table([[Paragraph(text, style)]], colWidths=[4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), bg_color),
        ("ROUNDEDCORNERS",[3,3,3,3]),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    return t


def dose_summary_box(dose, risk_level):
    """Big coloured dose box matching the GeniDose UI panel."""
    is_critical = risk_level in ("CRITICAL", "HIGH")
    bg     = RED_BG   if is_critical else GREEN_BG
    fg     = RED      if is_critical else GREEN
    label  = "⚠  CPIC Pharmacogenomic Rule Engine" if is_critical else "✓  CPIC Pharmacogenomic Rule Engine"

    title_style = ParagraphStyle("dt", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=GRAY, alignment=TA_CENTER)
    # dose_style  = ParagraphStyle("ds", fontSize=40, fontName="Helvetica-Bold",
    #                              textColor=fg,   alignment=TA_CENTER)
    # unit_style  = ParagraphStyle("du", fontSize=12, fontName="Helvetica",
    #                              textColor=GRAY, alignment=TA_CENTER)
    dose_style = ParagraphStyle(
    "ds",
    fontSize=36,
    leading=42,   # important fix
    fontName="Helvetica-Bold",
    textColor=fg,
    alignment=TA_CENTER,
    spaceAfter=12  # adds spacing below dosage
)

    unit_style = ParagraphStyle(
    "du",
    fontSize=12,
    leading=16,
    fontName="Helvetica",
    textColor=GRAY,
    alignment=TA_CENTER
)

    inner = Table([
        [Paragraph(label,            title_style)],
        [Paragraph(f"{dose} mg/day", dose_style)],
        [Paragraph("Recommended Daily Dose", unit_style)],
    ], colWidths=[14*cm])
    inner.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), bg),
        ("TOPPADDING",   (0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
        ("BOX",          (0,0),(-1,-1), 1.5, fg),
    ]))
    return inner


# ── Page decorators ───────────────────────────────────────────────────────────
def on_cover(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(DARK2)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # teal accent bar top
    canvas.setFillColor(TEAL)
    canvas.rect(0, h-0.6*cm, w, 0.6*cm, fill=1, stroke=0)
    # teal accent bar bottom
    canvas.rect(0, 0, w, 0.6*cm, fill=1, stroke=0)
    # subtle circle decoration
    canvas.setFillColor(TEAL)
    canvas.setFillAlpha(0.07)
    canvas.circle(w+2*cm, -2*cm, 16*cm, fill=1, stroke=0)
    canvas.setFillAlpha(1)
    canvas.restoreState()


def on_page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(DARK2)
    canvas.rect(0, 0, w, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, 0.38*cm,
                      "GeniDose Platform  |  CONFIDENTIAL — For Authorised Clinical Use Only")
    canvas.drawRightString(w-1.5*cm, 0.38*cm,
                           f"Page {doc.page}  |  {datetime.now().strftime('%Y-%m-%d')}")
    canvas.restoreState()


# ── Main report builder ───────────────────────────────────────────────────────
def build_report(data: dict, output_path: str) -> str:
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm,    bottomMargin=1.8*cm,
        title="GeniDose Clinical Dosage Report",
        author="GeniDose Platform"
    )

    S    = build_styles()
    base = getSampleStyleSheet()["Normal"]
    story = []

    pt   = data["patient"]
    med  = data["medication"]
    cpic = data["cpic_result"]
    geno = data["genotypes"]
    fl   = data["fl_model"]
    meta = data["report_meta"]

    risk  = cpic["risk_level"]
    dose  = cpic["recommended_dose_mgday"]

    # ── COVER ──────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 3.8*cm),
        Paragraph("GeniDose", S["cover_h1"]),
        Paragraph("Clinical Pharmacogenomics Report", S["cover_sub"]),
        Spacer(1, 1*cm),
        HRFlowable(width="55%", thickness=1, color=TEAL, hAlign="CENTER"),
        Spacer(1, 1*cm),
        Paragraph(f"Patient VCF: <b>{pt['vcf_file']}</b>", S["cover_meta"]),
        Paragraph(f"Age: {pt['age']} yrs  ·  Weight: {pt['weight_kg']} kg", S["cover_meta"]),
        Paragraph(f"Medication: <b>{med['name']} ({med['category']})</b>", S["cover_meta"]),
        Paragraph(f"Hospital: {meta['hospital_name']}", S["cover_meta"]),
        Paragraph(f"Generated: {meta['generated_at']}", S["cover_meta"]),
        Spacer(1, 2.5*cm),
        Paragraph("Secure Non-IID Genomic Federated Learning Engine", S["cover_sub"]),
        PageBreak()
    ]

    # ── 1. PATIENT & MEDICATION OVERVIEW ──────────────────────────────────────
    story.append(Paragraph("1.  Patient & Medication Overview", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(kv_table([
        ("VCF File",         pt["vcf_file"]),
        ("Parsed from VCF",  "Yes — age, weight & mutations extracted automatically" if pt["parsed_from_vcf"] else "Manual entry"),
        ("Patient Age",      f"{pt['age']} years"),
        ("Patient Weight",   f"{pt['weight_kg']} kg"),
        ("Target Medication",f"{med['name']} ({med['category']})"),
        ("Pharmacogenomics Engine", med["engine"]),
        ("Hospital",         meta["hospital_name"]),
        ("Hospital ID",      meta["hospital_id"]),
    ]))
    story.append(Spacer(1, 0.7*cm))

    # ── 2. CPIC DOSAGE RECOMMENDATION ─────────────────────────────────────────
    story.append(Paragraph("2.  CPIC Dosage Recommendation", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.4*cm))

    # Big dose box (mirrors UI panel)
    story.append(KeepTogether([
        Table([[dose_summary_box(dose, risk)]], colWidths=[16.4*cm]),
        Spacer(1, 0.4*cm),
    ]))

    # Warning badges
    badge_data = []
    for w in cpic["warnings"]:
        bg = RED if "CRITICAL" in w else AMBER
        badge_data.append(badge_cell(w, bg))
    if badge_data:
        row_table = Table([badge_data], colWidths=[4.2*cm]*len(badge_data))
        row_table.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),4)]))
        story.append(row_table)
        story.append(Spacer(1, 0.3*cm))

    # Clinical notes
    for note in cpic.get("clinical_notes", []):
        story.append(Paragraph(f"⚕  {note}", S["note_text"]))
    story.append(Spacer(1, 0.7*cm))

    # ── 3. AUTO-DETECTED GENOTYPES ────────────────────────────────────────────
    story.append(Paragraph("3.  Auto-Detected Genotypes (from VCF)", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "The following variants were automatically parsed from the uploaded VCF file "
        "using the GeniDose VCF Processing Engine, then cross-referenced against the CPIC guideline database.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    # Colour-code impact column
    geno_rows = []
    for g in geno:
        impact_color = {"HIGH": "red", "MODERATE": "orange", "NONE": "green"}.get(g["impact"], "black")
        geno_rows.append([
            g["gene"],
            g["rsid"],
            g["zygosity"],
            g["phenotype"],
            f'<font color="{impact_color}"><b>{g["impact"]}</b></font>'
        ])

    story.append(col_table(
    ["Gene / Allele", "rsID", "Zygosity", "Phenotype", "Impact"],
    [
        [
            g["gene"],
            g["rsid"],
            g["zygosity"],
            g["phenotype"],
            g["impact"]
        ]
        for g in geno
    ],
    col_widths=[3*cm, 3.5*cm, 2.5*cm, 4.5*cm, 2.9*cm]
))
    # story.append(col_table(
    #     ["Gene / Allele", "rsID", "Zygosity", "Phenotype", "Impact"],
    #     [[Paragraph(str(c) if not c.startswith("<") else c, base) for c in row] for row in
    #      [[g["gene"], g["rsid"], g["zygosity"], g["phenotype"],
    #        f'<font color="{"red" if g["impact"]=="HIGH" else "green"}">{g["impact"]}</font>']
    #       for g in geno]],
    #     col_widths=[3*cm, 3.5*cm, 2.5*cm, 4.5*cm, 2.9*cm]
    # ))
    # story.append(Spacer(1, 0.7*cm))

    # ── 4. FEDERATED ML MODEL COMPARISON ─────────────────────────────────────
    story.append(Paragraph("4.  Federated ML Model — Comparison Dose", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"The federated model (trained across {fl['participating_hospitals']} hospital nodes) "
        f"suggests <b>{fl['comparison_dose_mgday']} mg/day</b>. "
        f"{fl['note']}. "
        "The CPIC rule-based dose is used as the primary clinical recommendation; "
        "the FL model dose is provided for comparison and improves with each training round.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(kv_table([
        ("FL Comparison Dose",     f"{fl['comparison_dose_mgday']} mg/day"),
        ("CPIC Rule-Based Dose",   f"{dose} mg/day"),
        ("Delta",                  f"{abs(fl['comparison_dose_mgday'] - dose):.2f} mg/day"),
        ("FL Round",               fl["fl_round"]),
        ("Participating Hospitals",fl["participating_hospitals"]),
        ("Aggregation Method",     fl["aggregation"]),
        ("Model Version",          fl["model_version"]),
        ("Global Accuracy",        f"{fl['accuracy_pct']}%"),
        ("AUC-ROC",                fl["auc_roc"]),
    ]))
    story.append(Spacer(1, 0.7*cm))

    # ── 5. PIPELINE — UPCOMING DRUGS ──────────────────────────────────────────
    story.append(Paragraph("5.  Pipeline — Future Drug Modules", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(col_table(
        ["Drug", "Key Pharmacogene", "Development Status"],
        [[d["drug"], d["gene"], d["status"]] for d in data["upcoming_drugs"]],
        col_widths=[5.5*cm, 5.5*cm, 5.4*cm]
    ))
    story.append(Spacer(1, 0.7*cm))

    # ── 6. PRIVACY & FEDERATED SETUP ──────────────────────────────────────────
    story.append(Paragraph("6.  Privacy & Federated Learning Setup", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(kv_table([
        ("Privacy Method",    meta["privacy_method"]),
        ("Data Shared",       "Model gradients only — no raw patient records or VCF data transmitted"),
        ("VCF Processing",    "Local only — vcf_processing_engine.py runs on-hospital"),
        ("FL Framework",      "Flower (flwr) — Virtual Processes"),
        ("Backend Modules",   "federated_engine.py · hospital_client.py · model.py"),
    ]))
    story.append(Spacer(1, 0.7*cm))

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Clinical Disclaimer:</b> This report is generated by the GeniDose AI-based "
        "pharmacogenomics platform and is intended to support — not replace — clinical judgment. "
        "All dosage recommendations must be validated by a licensed physician or clinical "
        "pharmacist before administration. GeniDose does not assume liability for clinical "
        "decisions made solely on the basis of this output.",
        S["small"]
    ))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    print(f"[✓] Report saved → {output_path}")
    return output_path


# ── Public API — call this from backend/app.py ─────────────────────────────
def generate_patient_report(result_dict: dict, output_path: str = None) -> str:
    """
    Drop-in function for backend/app.py.

    Example in app.py:
        from generate_report import generate_patient_report

        @app.route("/download_report", methods=["POST"])
        def download_report():
            result = request.json          # same dict returned by /calculate_dosage
            pdf_path = generate_patient_report(result)
            return send_file(pdf_path, as_attachment=True,
                             download_name="genidose_report.pdf",
                             mimetype="application/pdf")
    """
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"genidose_report_{ts}.pdf"
    return build_report(result_dict, output_path)


# ADD this new function at the bottom of generate_report.py
import io

def generate_patient_report_bytes(result_dict: dict) -> bytes:
    """Returns PDF as bytes — no disk write, works on Windows."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm,    bottomMargin=1.8*cm,
        title="GeniDose Clinical Dosage Report",
        author="GeniDose Platform"
    )

    # reuse the exact same story-building logic
    from copy import deepcopy
    data = deepcopy(result_dict)

    S    = build_styles()
    base = getSampleStyleSheet()["Normal"]
    story = []

    pt   = data["patient"]
    med  = data["medication"]
    cpic = data["cpic_result"]
    geno = data["genotypes"]
    fl   = data["fl_model"]
    meta = data["report_meta"]
    risk = cpic["risk_level"]
    dose = cpic["recommended_dose_mgday"]

    story += [
        Spacer(1, 3.8*cm),
        Paragraph("GeniDose", S["cover_h1"]),
        Paragraph("Clinical Pharmacogenomics Report", S["cover_sub"]),
        Spacer(1, 1*cm),
        HRFlowable(width="55%", thickness=1, color=TEAL, hAlign="CENTER"),
        Spacer(1, 1*cm),
        Paragraph(f"Patient VCF: <b>{pt['vcf_file']}</b>",          S["cover_meta"]),
        Paragraph(f"Age: {pt['age']} yrs  ·  Weight: {pt['weight_kg']} kg", S["cover_meta"]),
        Paragraph(f"Medication: <b>{med['name']} ({med['category']})</b>",   S["cover_meta"]),
        Paragraph(f"Hospital: {meta['hospital_name']}",              S["cover_meta"]),
        Paragraph(f"Generated: {meta['generated_at']}",              S["cover_meta"]),
        Spacer(1, 2.5*cm),
        Paragraph("Secure Non-IID Genomic Federated Learning Engine", S["cover_sub"]),
        PageBreak()
    ]

    story.append(Paragraph("1.  Patient & Medication Overview", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(kv_table([
        ("VCF File",          pt["vcf_file"]),
        ("Parsed from VCF",   "Yes — age, weight & mutations extracted automatically"),
        ("Patient Age",       f"{pt['age']} years"),
        ("Patient Weight",    f"{pt['weight_kg']} kg"),
        ("Target Medication", f"{med['name']} ({med['category']})"),
        ("Engine",            med["engine"]),
        ("Hospital",          meta["hospital_name"]),
    ]))
    story.append(Spacer(1, 0.7*cm))

    story.append(Paragraph("2.  CPIC Dosage Recommendation", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.4*cm))
    story.append(KeepTogether([
        Table([[dose_summary_box(dose, risk)]], colWidths=[16.4*cm]),
        Spacer(1, 0.4*cm),
    ]))

    badge_data = []
    for w in cpic["warnings"]:
        if w:
            bg = RED if "CRITICAL" in w.upper() else AMBER
            badge_data.append(badge_cell(w, bg))
    if badge_data:
        row_table = Table([badge_data], colWidths=[5*cm]*len(badge_data))
        story.append(row_table)
        story.append(Spacer(1, 0.3*cm))

    for note in cpic.get("clinical_notes", []):
        if note:
            story.append(Paragraph(f"⚕  {note}", S["note_text"]))
    story.append(Spacer(1, 0.7*cm))

    story.append(Paragraph("3.  Federated ML Model — Comparison Dose", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(kv_table([
        ("FL Comparison Dose",      f"{fl['comparison_dose_mgday']} mg/day"),
        ("CPIC Rule-Based Dose",    f"{dose} mg/day"),
        ("FL Round",                fl["fl_round"]),
        ("Participating Hospitals", fl["participating_hospitals"]),
        ("Aggregation Method",      fl["aggregation"]),
        ("Model Version",           fl["model_version"]),
        ("Global Accuracy",         f"{fl['accuracy_pct']}%"),
        ("AUC-ROC",                 fl["auc_roc"]),
    ]))
    story.append(Spacer(1, 0.7*cm))

    story.append(Paragraph("4.  Pipeline — Future Drug Modules", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.3*cm))
    story.append(col_table(
        ["Drug", "Key Pharmacogene", "Status"],
        [[d["drug"], d["gene"], d["status"]] for d in data["upcoming_drugs"]],
        col_widths=[5.5*cm, 5.5*cm, 5.4*cm]
    ))
    story.append(Spacer(1, 0.7*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Clinical Disclaimer:</b> This report is generated by the GeniDose AI-based "
        "pharmacogenomics platform and is intended to support — not replace — clinical judgment. "
        "All dosage recommendations must be validated by a licensed physician before administration.",
        S["small"]
    ))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    buffer.seek(0)
    return buffer.read()

# ── CLI entry point ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="GeniDose Report Generator")
    parser.add_argument("--input",  default=None, help="JSON file with model output")
    parser.add_argument("--output", default=None, help="Output PDF path")
    args = parser.parse_args()

    if args.input and os.path.exists(args.input):
        with open(args.input) as f:
            data = json.load(f)
        print(f"[✓] Loaded: {args.input}")
    else:
        print("[i] Using sample data — pass --input result.json for real output.")
        data = SAMPLE_DATA

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output or f"genidose_report_{ts}.pdf"
    build_report(data, out)



if __name__ == "__main__":
    main()