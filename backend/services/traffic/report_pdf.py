from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.services.traffic.playlist import PlaylistEvent
from backend.services.traffic.prelog_export import LABELS

BRAND_LOGO = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "broadcast-tool-pro-logo.png"
)


def _brand_logo() -> Image:
    return Image(
        str(BRAND_LOGO),
        width=190,
        height=42,
    )


def _logo(logo_content: bytes | None) -> Image | None:
    if not logo_content:
        return None
    try:
        reader = ImageReader(BytesIO(logo_content))
        width, height = reader.getSize()
        scale = min(120 / width, 46 / height, 1)
        return Image(
            BytesIO(logo_content),
            width=width * scale,
            height=height * scale,
        )
    except Exception as exc:
        raise ValueError(
            "The logo must be a valid PNG, JPG, or JPEG image."
        ) from exc


def generate_report_pdf(
    events: list[PlaylistEvent],
    channel_name: str,
    language: str = "en",
    product: str | None = None,
    agency: str | None = None,
    logo_content: bytes | None = None,
    report_type: str = "prelog",
    trial_watermark: bool = False,
) -> bytes:
    if not events:
        raise ValueError("At least one scheduled event is required.")
    if language not in LABELS:
        raise ValueError("Report language must be English or Spanish.")

    labels = LABELS[language]
    title = (
        labels["postlog_title"]
        if report_type == "postlog"
        else labels["title"]
    )
    include_product = bool(product and product.strip())
    include_agency = bool(agency and agency.strip())
    headers = [labels["channel"]]
    if include_product:
        headers.append(labels["product"])
    headers.extend([
        labels["asset"],
        labels["date"],
        labels["time"],
        labels["duration"],
    ])
    if include_agency:
        headers.append(labels["agency"])

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=26,
        title=title,
        author="Broadcast Tool Pro",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=23,
        textColor=colors.HexColor("#102A43"),
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2563EB"),
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
    )

    first_airing = min(event.air_datetime for event in events)
    last_airing = max(event.air_datetime for event in events)
    heading = [
        Paragraph(title, title_style),
        Paragraph(channel_name.strip(), subtitle_style),
        Paragraph(
            f"{first_airing:%B %d, %Y %H:%M} - "
            f"{last_airing:%B %d, %Y %H:%M}",
            meta_style,
        ),
    ]
    logo = _logo(logo_content)
    header_table = Table(
        [[_brand_logo(), heading, logo or ""]],
        colWidths=[200, document.width - 330, 130],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    rows = [headers]
    for event in events:
        values = [channel_name.strip()]
        if include_product:
            values.append(product.strip())
        values.extend([
            event.asset_id,
            event.air_datetime.strftime("%m/%d/%Y"),
            event.air_datetime.strftime("%H:%M:%S"),
            event.duration or "",
        ])
        if include_agency:
            values.append(agency.strip())
        rows.append(values)

    column_count = len(headers)
    available_width = document.width
    widths = [available_width * 0.15]
    if include_product:
        widths.append(available_width * 0.15)
    widths.extend([
        available_width * 0.25,
        available_width * 0.12,
        available_width * 0.11,
        available_width * 0.10,
    ])
    if include_agency:
        widths.append(available_width * 0.16)
    width_scale = available_width / sum(widths)
    widths = [width * width_scale for width in widths]

    report_table = Table(
        rows,
        colWidths=widths[:column_count],
        repeatRows=1,
    )
    asset_column = 2 if include_product else 1
    report_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (asset_column, 0), (asset_column, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F8FAFC"),
        ]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    footer = labels["generated"]
    if report_type == "postlog":
        footer = f"{labels['total_airings']}: {len(events)} · {footer}"
    footer_style = ParagraphStyle(
        "ReportFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#829AB1"),
        alignment=TA_CENTER,
    )
    story = [
        header_table,
        Spacer(1, 14),
        report_table,
        Spacer(1, 12),
        Paragraph(footer, footer_style),
    ]

    def page(canvas, doc):
        if not trial_watermark:
            return
        canvas.saveState()
        canvas.setFillColor(colors.Color(0.08, 0.22, 0.48, alpha=0.12))
        canvas.setFont("Helvetica-Bold", 34)
        canvas.translate(landscape(letter)[0] / 2, landscape(letter)[1] / 2)
        canvas.rotate(28)
        canvas.drawCentredString(
            0,
            0,
            "BROADCAST TOOL PRO - FREE TRIAL",
        )
        canvas.restoreState()

    document.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()
