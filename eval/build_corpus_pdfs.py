# eval/build_corpus_pdfs.py
#
# Generates the synthetic insurance-policy corpus (real PDFs, real tables)
# used by the Week 4 Task Set D retrieval exercise. Run once:
#
#   pip install reportlab   # one-off, not an app dependency
#   python eval/build_corpus_pdfs.py
#
# Output: eval/corpus_pdfs/{HO-0304_ed_03-24,HO-0304_ed_01-19,Endorsement_HO-2306}.pdf

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = Path(__file__).parent / "corpus_pdfs"

TABLE_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)


def build_policy_pdf(edition: str, day_threshold: str, out_path: Path) -> None:
    styles = getSampleStyleSheet()
    cell_style = styles["BodyText"].clone("cell")
    cell_style.fontSize = 8
    cell_style.leading = 10

    def cell(text: str) -> Paragraph:
        # Plain strings don't wrap in reportlab's Table and silently overflow
        # into neighboring cells, which pdfplumber then reads back garbled.
        # Wrapping in a Paragraph forces real wrapping + correct row height.
        return Paragraph(text, cell_style)

    story = []

    # Page 1 - Declarations, Coverage A-D, Coverage Limits table
    story.append(Paragraph("HARBORSTONE MUTUAL INSURANCE COMPANY", styles["Title"]))
    story.append(Paragraph(f"Homeowners Policy - Form HO-0304 - Edition {edition}", styles["Heading2"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("DECLARATIONS", styles["Heading3"]))
    story.append(Paragraph(
        "Named Insured: Jordan A. Whitfield. Residence Premises: 214 Alder Creek "
        "Lane, Millbrook. Policy Period: 12 months from the inception date shown "
        "on the Declarations page.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("SECTION I - PROPERTY COVERAGES", styles["Heading3"]))
    story.append(Paragraph(
        "Coverage A - Dwelling. We cover the dwelling on the residence "
        "premises shown in the Declarations, including structures attached to "
        "the dwelling, up to the Coverage A limit of liability.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Coverage B - Other Structures. We cover other structures on the "
        "residence premises separated from the dwelling by clear space.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Coverage C - Personal Property. We cover personal property owned "
        "or used by an insured, up to the Coverage C limit of liability.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Coverage D - Loss of Use. If a covered loss makes the residence "
        "premises uninhabitable, we cover the necessary increase in living "
        "expenses.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Coverage Limits", styles["Heading4"]))
    limits_table = Table(
        [
            ["Coverage", "Limit of Liability"],
            [cell("A - Dwelling"), "$350,000"],
            [cell("B - Other Structures"), "$35,000"],
            [cell("C - Personal Property"), "$175,000"],
            [cell("D - Loss of Use"), "$70,000"],
        ],
        colWidths=[3 * inch, 2 * inch],
    )
    limits_table.setStyle(TABLE_STYLE)
    story.append(limits_table)
    story.append(PageBreak())

    # Page 2 - Perils Insured Against (includes the "sudden discharge" decoy)
    story.append(Paragraph("SECTION I - PERILS INSURED AGAINST", styles["Heading3"]))
    story.append(Paragraph(
        "Coverage C losses are covered only for direct physical loss caused by "
        "a named peril, including fire, lightning, windstorm, theft, "
        "vandalism, and the peril below.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Sudden and Accidental Discharge or Overflow of Water. We cover direct "
        "physical loss caused by the sudden and accidental discharge or "
        "overflow of water or steam from within a plumbing, heating, or air "
        "conditioning system, or from within a household appliance.",
        styles["BodyText"],
    ))
    story.append(PageBreak())

    # Page 3 - Exclusions Schedule (the table that must stay chunk-local with
    # the edition header so retrieval can tell editions apart from chunk text)
    story.append(Paragraph(f"Form HO-0304 - Edition {edition} - Harborstone Mutual", styles["Heading4"]))
    story.append(Paragraph(
        "Section I - Exclusions. We do not cover loss from the causes "
        "below, unless amended by endorsement.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 8))
    excl_table = Table(
        [
            ["Code", "Exclusion", "Description"],
            ["E-01", cell("Flood"), cell("Surface water, waves, tidal water, or overflow of a body of water")],
            ["E-05", cell("Earth Movement"), cell("Earthquake, landslide, mudflow, or sinkhole collapse")],
            ["E-12", cell("Wear and Tear"), cell("Wear, tear, deterioration, or mechanical breakdown")],
            ["E-17", cell("Water Damage, Continuous Seepage"),
             cell(f"Water/steam seeping {day_threshold}+ days, incl. resulting mold or rot. "
                  f"(Form HO-0304, Edition {edition}.)")],
            ["E-20", cell("Nuclear Hazard"), cell("Nuclear reaction, radiation, or radioactive contamination")],
        ],
        colWidths=[0.6 * inch, 1.7 * inch, 3.2 * inch],
    )
    excl_table.setStyle(TABLE_STYLE)
    story.append(excl_table)
    story.append(PageBreak())

    # Page 4 - Conditions
    story.append(Paragraph("SECTION I - CONDITIONS", styles["Heading3"]))
    story.append(Paragraph(
        "Duties After Loss. In case of a loss, you must give prompt notice, "
        "protect the property from further damage, and cooperate with us in "
        "the investigation of the claim.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Appraisal. If you and we fail to agree on the amount of loss, either "
        "party may demand an appraisal.",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        "Loss Settlement. Covered losses to the dwelling are settled at "
        "replacement cost, provided the Coverage A limit is at least 80% of "
        "full replacement cost.",
        styles["BodyText"],
    ))

    SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    ).build(story)


def build_endorsement_pdf(out_path: Path) -> None:
    styles = getSampleStyleSheet()
    story = [
        Paragraph("HARBORSTONE MUTUAL INSURANCE COMPANY", styles["Title"]),
        Paragraph("Endorsement HO-2306 - Amendment of Water Damage Exclusion", styles["Heading2"]),
        Spacer(1, 12),
        Paragraph("Attached to and forming part of Form HO-0304.", styles["BodyText"]),
        Paragraph(
            "This endorsement amends Exclusion E-17 (Water Damage, Continuous "
            "or Repeated Seepage) of Form HO-0304. In return for the "
            "additional premium shown on the Declarations, we will pay for "
            "loss caused by seepage or leakage of water or steam lasting "
            "fewer than 30 days, provided the dwelling was not vacant or "
            "unoccupied for more than 60 consecutive days during the policy "
            "period. All other terms, conditions, and exclusions of Form "
            "HO-0304 remain unchanged.",
            styles["BodyText"],
        ),
    ]
    SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    ).build(story)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_policy_pdf("03-24", "14", OUT_DIR / "HO-0304_ed_03-24.pdf")
    build_policy_pdf("01-19", "10", OUT_DIR / "HO-0304_ed_01-19.pdf")
    build_endorsement_pdf(OUT_DIR / "Endorsement_HO-2306.pdf")
    print(f"Wrote 3 PDFs to {OUT_DIR}")


if __name__ == "__main__":
    main()
