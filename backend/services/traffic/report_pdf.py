from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
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


class TrialWatermarkCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_pages)
        for page_number, page_state in enumerate(self._saved_pages, start=1):
            self.__dict__.update(page_state)
            self.saveState()
            page_width, page_height = landscape(letter)
            self.setFillColor(
                colors.Color(0.08, 0.22, 0.48, alpha=0.16)
            )
            self.setFont("Helvetica-Bold", 30)
            self.translate(page_width / 2, page_height / 2)
            self.rotate(28)
            self.drawCentredString(
                0,
                0,
                "BROADCAST TOOL PRO - FREE TRIAL",
            )
            self.restoreState()
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(
                page_width - 24,
                12,
                f"Free Trial · Page {page_number} of {page_count}",
            )
            Canvas.showPage(self)
        Canvas.save(self)


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
    client_name: str | None = None,
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
    if client_name and client_name.strip():
        heading.append(Paragraph(
            f"{labels['client']}: {client_name.strip()}",
            meta_style,
        ))
    logo = _logo(logo_content)
    header_table = Table(
        [[heading, logo or ""]],
        colWidths=[document.width - 130, 130],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
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

    def draw_footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#829AB1"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(doc.leftMargin, 12, footer)
        canvas.drawImage(
            str(BRAND_LOGO),
            landscape(letter)[0] - doc.rightMargin - 86,
            7,
            width=86,
            height=19,
            preserveAspectRatio=True,
            mask="auto",
        )
        canvas.restoreState()

    story = [
        header_table,
        Spacer(1, 14),
        report_table,
    ]

    canvasmaker = TrialWatermarkCanvas if trial_watermark else Canvas
    document.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
        canvasmaker=canvasmaker,
    )
    return output.getvalue()
