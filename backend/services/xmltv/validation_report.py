from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND_LOGO = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "broadcast-tool-pro-logo.png"
)


def generate_xmltv_validation_report(
    payload: dict,
) -> bytes:
    validation = payload.get("validation") or {}
    issues = validation.get("issues") or []
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="XMLTV Validation Report",
        author="Broadcast Tool Pro",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#102A43"),
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#243B53"),
    )
    status = "VALID XMLTV" if payload.get("valid") else "NEEDS ATTENTION"
    metrics = Table(
        [[
            f"Score {validation.get('score', 0)}/100",
            f"{validation.get('critical', 0)} Critical",
            f"{validation.get('errors', 0)} Errors",
            f"{validation.get('warnings', 0)} Warnings",
        ]],
        colWidths=[1.7 * inch] * 4,
    )
    metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF2FF")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#102A43")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7E1EC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7E1EC")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    rows = [["Severity", "Rule", "Line", "Field", "Message"]]
    for issue in issues:
        rows.append([
            str(issue.get("severity") or ""),
            str(issue.get("rule_id") or ""),
            str(issue.get("row") or "—"),
            str(issue.get("field") or "—"),
            Paragraph(str(issue.get("message") or ""), body),
        ])
    if len(rows) == 1:
        rows.append(["—", "—", "—", "—", "No issues found."])
    issue_table = Table(
        rows,
        colWidths=[0.65 * inch, 0.7 * inch, 0.45 * inch, 1.0 * inch, 4.1 * inch],
        repeatRows=1,
    )
    issue_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E1EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F7FAFC"),
        ]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story = [
        Image(str(BRAND_LOGO), width=3.1 * inch, height=0.68 * inch),
        Spacer(1, 14),
        Paragraph("XMLTV Validation Report", title),
        Paragraph(
            f"{status} · {payload.get('filename') or 'XMLTV file'}",
            body,
        ),
        Spacer(1, 12),
        metrics,
        Spacer(1, 16),
        issue_table,
    ]

    document.build(story)
    return output.getvalue()
