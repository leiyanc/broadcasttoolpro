from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#102A43")
BLUE = colors.HexColor("#2563EB")
PALE_BLUE = colors.HexColor("#EAF2FF")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#D7E1EC")
SUCCESS = colors.HexColor("#087F5B")
DANGER = colors.HexColor("#B42318")

RECOMMENDATIONS = {
    "HLS-001": "Verify that the URL returns an M3U8 playlist beginning with #EXTM3U.",
    "HLS-002": "Add a valid media-playlist URI after every EXT-X-STREAM-INF tag.",
    "HLS-003": "Declare BANDWIDTH for every variant so players can perform adaptive selection.",
    "HLS-004": "Ensure the media playlist publishes playable media segment URIs.",
    "HLS-005": "Provide one EXTINF duration for every referenced media segment.",
    "HLS-006": "Replace the invalid EXTINF value with a valid positive decimal duration.",
    "HLS-007": "Set EXT-X-TARGETDURATION to a whole number in seconds.",
    "HLS-008": "Add EXT-X-TARGETDURATION to every media playlist.",
    "HLS-009": "Increase TARGETDURATION or resegment so no segment exceeds it.",
    "HLS-010": "Verify CDN/origin reachability, authorization, DNS, and playlist availability.",
    "HLS-011": "Ensure the variant URL returns a valid UTF-8 M3U8 media playlist.",
    "HLS-012": "Review ad-marker pairing and remove unmatched CUE-IN markers.",
}

RECOMMENDATIONS_ES = {
    "HLS-001": "Verifique que la URL entregue un playlist M3U8 que comience con #EXTM3U.",
    "HLS-002": "Agregue una URI valida despues de cada tag EXT-X-STREAM-INF.",
    "HLS-003": "Declare BANDWIDTH en cada variante para la seleccion adaptativa.",
    "HLS-004": "Asegure que el media playlist publique segmentos reproducibles.",
    "HLS-005": "Incluya una duracion EXTINF por cada segmento.",
    "HLS-006": "Reemplace el valor EXTINF por una duracion decimal positiva.",
    "HLS-007": "Defina EXT-X-TARGETDURATION como un numero entero.",
    "HLS-008": "Agregue EXT-X-TARGETDURATION a cada media playlist.",
    "HLS-009": "Aumente TARGETDURATION o vuelva a segmentar el contenido.",
    "HLS-010": "Verifique CDN/origen, autorizacion, DNS y disponibilidad.",
    "HLS-011": "Asegure que la variante entregue un M3U8 UTF-8 valido.",
    "HLS-012": "Revise el pareo de marcadores CUE-OUT y CUE-IN.",
}

SPANISH = {
    "platform": "Plataforma de Operaciones Broadcast",
    "title": "Reporte de Validacion HLS y Monitoreo SCTE-35",
    "disclaimer": (
        "Reporte de validacion independiente. Broadcast Tool Pro no modifico, "
        "reparo ni reempaqueto el stream inspeccionado."
    ),
    "status": "Estado",
    "valid": "Valido",
    "attention": "Requiere Atencion",
    "url": "URL del Playlist",
    "type": "Tipo de Playlist",
    "period": "Periodo de Monitoreo",
    "minutes": "minutos",
    "inspections": "Inspecciones",
    "detected": "Detectado",
    "not_detected": "No Detectado",
    "triggers": "Triggers Unicos",
    "generated": "Generado",
    "variants": "Resumen de Variantes",
    "timeline": "Linea de Tiempo SCTE-35 y Triggers",
    "findings": "Hallazgos y Acciones Recomendadas",
    "scope": "Alcance y Limitaciones",
    "footer": "Broadcast Tool Pro - Reporte Confidencial de Validacion",
    "page": "Pagina",
}

FINDINGS_ES = {
    "HLS-001": "El recurso no es un playlist HLS valido.",
    "HLS-002": "Una variante no contiene una URI de media playlist valida.",
    "HLS-003": "Una variante no declara el atributo BANDWIDTH.",
    "HLS-004": "El media playlist no contiene segmentos reproducibles.",
    "HLS-005": "La cantidad de duraciones EXTINF no coincide con los segmentos.",
    "HLS-006": "Se detecto un valor EXTINF invalido.",
    "HLS-007": "EXT-X-TARGETDURATION debe ser un numero entero.",
    "HLS-008": "El media playlist no declara EXT-X-TARGETDURATION.",
    "HLS-009": "Un segmento excede el TARGETDURATION declarado.",
    "HLS-010": "No fue posible acceder al playlist o a una de sus variantes.",
    "HLS-011": "Una variante no entrego un media playlist M3U8 valido.",
    "HLS-012": "Se detecto un marcador CUE-IN sin su CUE-OUT correspondiente.",
}


def _text(value, limit: int = 500) -> str:
    return escape(str(value or "")[:limit])


def _paragraph(value, style):
    return Paragraph(_text(value), style)


def generate_hls_report(payload: dict) -> bytes:
    spanish = payload.get("report_language") == "es"
    copy = SPANISH if spanish else {}

    def translated(key: str, english: str) -> str:
        return copy.get(key, english)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.62 * inch,
        title=translated(
            "title",
            "HLS Validation and SCTE-35 Monitoring Report",
        ),
        author="Broadcast Tool Pro",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=NAVY,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=7.2,
        leading=9,
        textColor=MUTED,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=8,
    )
    title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=24,
        alignment=TA_LEFT,
        textColor=NAVY,
        spaceAfter=4,
    )
    label = ParagraphStyle(
        "Label",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=NAVY,
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []
    brand = Table(
        [[
            Paragraph(
                '<font color="white"><b>B</b></font>',
                ParagraphStyle(
                    "BrandMark",
                    alignment=TA_CENTER,
                    fontSize=18,
                    leading=22,
                ),
            ),
            Paragraph(
                "<b>Broadcast Tool Pro</b><br/>"
                '<font size="8" color="#64748B">'
                f'{translated("platform", "Broadcast Operations Platform")}'
                "</font>",
                body,
            ),
        ]],
        colWidths=[0.48 * inch, 6.42 * inch],
    )
    brand.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        brand,
        Spacer(1, 0.25 * inch),
        Paragraph(
            translated(
                "title",
                "HLS Validation and SCTE-35 Monitoring Report",
            ),
            title,
        ),
        Paragraph(
            translated(
                "disclaimer",
                "Independent validation report. Broadcast Tool Pro did not "
                "modify, repair, or repackage the inspected stream.",
            ),
            small,
        ),
        Spacer(1, 0.16 * inch),
    ])

    valid = bool(payload.get("valid"))
    status_color = SUCCESS if valid else DANGER
    summary = [
        [
            translated("status", "Status"),
            translated("valid", "Valid")
            if valid
            else translated("attention", "Needs Attention"),
        ],
        [translated("url", "Playlist URL"), str(payload.get("url") or "")[:1000]],
        [
            translated("type", "Playlist Type"),
            str(payload.get("playlist_type") or "Unknown").title(),
        ],
        [
            translated("period", "Monitoring Period"),
            (
                f'{payload.get("monitoring_minutes", 0)} '
                f'{translated("minutes", "minutes")}'
            ),
        ],
        [translated("inspections", "Inspections"), str(payload.get("inspections", 1))],
        [
            "SCTE-35",
            translated("detected", "Detected")
            if payload.get("scte35_detected")
            else translated("not_detected", "Not Detected"),
        ],
        [translated("triggers", "Unique Triggers"), str(payload.get("trigger_count", 0))],
        [translated("generated", "Generated"), str(payload.get("generated_at") or "")],
    ]
    summary_table = Table(
        [[_paragraph(key, label), _paragraph(value, body)] for key, value in summary],
        colWidths=[1.45 * inch, 5.45 * inch],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (1, 0), (1, 0), status_color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary_table, Spacer(1, 0.12 * inch)])

    variants = list(payload.get("variants") or [])[:50]
    story.append(Paragraph(
        translated("variants", "Variant Overview"),
        heading,
    ))
    if variants:
        rows = [[
            "Ancho de Banda" if spanish else "Bandwidth",
            "Resolucion" if spanish else "Resolution",
            "Cuadros/seg." if spanish else "Frame Rate",
            "Codecs",
            "Segmentos" if spanish else "Segments",
            "Triggers",
            translated("status", "Status"),
        ]]
        for variant in variants:
            rows.append([
                f'{round((variant.get("bandwidth") or 0) / 1000)} kbps',
                _text(variant.get("resolution") or "-"),
                _text(variant.get("frame_rate") or "-"),
                _text(variant.get("codecs") or "-", 100),
                str(variant.get("segments") or 0),
                str(variant.get("trigger_count") or 0),
                translated("valid", "Valid")
                if variant.get("valid", True)
                else translated("attention", "Attention"),
            ])
        table = Table(
            [
                [
                    _paragraph(
                        cell,
                        table_header if row_index == 0 else small,
                    )
                    for cell in row
                ]
                for row_index, row in enumerate(rows)
            ],
            repeatRows=1,
            colWidths=[0.72*inch, 0.72*inch, 0.58*inch, 2.2*inch, 0.55*inch, 0.55*inch, 0.72*inch],
        )
        table.setStyle(_table_style())
        story.append(table)
    else:
        story.append(Paragraph(
            "No se declararon variantes del stream."
            if spanish
            else "No variant streams were declared.",
            body,
        ))

    triggers = list(payload.get("triggers") or [])[:500]
    story.append(Paragraph(
        translated("timeline", "SCTE-35 and Trigger Timeline"),
        heading,
    ))
    if triggers:
        rows = [[
            translated("detected", "Detected"),
            "Tipo" if spanish else "Type",
            "ID",
            "Inicio" if spanish else "Start",
            "Duracion" if spanish else "Duration",
            "Fuente" if spanish else "Source",
        ]]
        for trigger in triggers:
            rows.append([
                _text(trigger.get("detected_at") or "-"),
                _text(trigger.get("type") or "-"),
                _text(trigger.get("id") or "-"),
                _text(trigger.get("start_date") or "-"),
                f'{trigger.get("duration")}s'
                if trigger.get("duration") is not None else "-",
                _text(trigger.get("source_url") or payload.get("url"), 250),
            ])
        table = Table(
            [
                [
                    _paragraph(
                        cell,
                        table_header if row_index == 0 else small,
                    )
                    for cell in row
                ]
                for row_index, row in enumerate(rows)
            ],
            repeatRows=1,
            colWidths=[0.88*inch, 1.15*inch, 0.92*inch, 1.12*inch, 0.55*inch, 2.28*inch],
        )
        table.setStyle(_table_style())
        story.append(table)
    else:
        story.append(Paragraph(
            (
                "No se observaron marcadores SCTE-35 ni otros triggers HLS "
                "compatibles durante el periodo de inspeccion."
                if spanish
                else
                "No SCTE-35 or supported HLS trigger tags were observed during "
                "the inspection period."
            ),
            body,
        ))

    issues = list(payload.get("issues") or [])[:500]
    story.append(Paragraph(
        translated("findings", "Findings and Recommended Actions"),
        heading,
    ))
    if issues:
        rows = [[
            "Severidad" if spanish else "Severity",
            "Regla" if spanish else "Rule",
            "Hallazgo" if spanish else "Finding",
            "Accion Recomendada" if spanish else "Recommended Action",
        ]]
        for issue in issues:
            rule_id = str(issue.get("rule_id") or "HLS")
            recommendation_source = (
                RECOMMENDATIONS_ES if spanish else RECOMMENDATIONS
            )
            finding = (
                FINDINGS_ES.get(
                    rule_id,
                    "Se detecto una condicion que requiere revision.",
                )
                if spanish
                else issue.get("message")
            )
            rows.append([
                _text(
                    _spanish_severity(issue.get("severity"))
                    if spanish
                    else (issue.get("severity") or "info").title()
                ),
                _text(rule_id),
                _text(finding, 800),
                _text(
                    (
                        None
                        if spanish
                        else issue.get("recommendation")
                    )
                    or recommendation_source.get(
                        rule_id,
                        (
                            "Revise el manifiesto y la configuracion de origen "
                            "con el proveedor del stream."
                            if spanish
                            else
                            "Review the manifest and origin configuration "
                            "with the stream provider."
                        ),
                    ),
                    800,
                ),
            ])
        table = Table(
            [
                [
                    _paragraph(
                        cell,
                        table_header if row_index == 0 else small,
                    )
                    for cell in row
                ]
                for row_index, row in enumerate(rows)
            ],
            repeatRows=1,
            colWidths=[0.62*inch, 0.62*inch, 2.65*inch, 3.01*inch],
        )
        table.setStyle(_table_style())
        story.append(table)
    else:
        story.append(Paragraph(
            (
                "No se identificaron hallazgos criticos ni advertencias. "
                "Continue el monitoreo periodico, especialmente durante las "
                "pausas publicitarias programadas."
                if spanish
                else
                "No blocking or warning findings were identified. Continue "
                "routine monitoring, especially during scheduled ad breaks."
            ),
            body,
        ))

    story.extend([
        Spacer(1, 0.18 * inch),
        KeepTogether([
            Paragraph(translated("scope", "Scope and Limitations"), heading),
            Paragraph(
                (
                    "Este reporte valida la estructura del manifiesto HLS y "
                    "la senalizacion SCTE-35/marcadores publicitarios compatible "
                    "a nivel de manifiesto. No altera el stream de origen. Las "
                    "senales SCTE-35 presentes solamente dentro de los segmentos "
                    "requieren inspeccion del elementary stream y estan fuera "
                    "del alcance actual de este reporte."
                    if spanish
                    else
                    "This report validates HLS manifest structure and supported "
                    "manifest-level SCTE-35/ad-marker signaling. It does not "
                    "alter the source stream. SCTE-35 carried only inside media "
                    "segments requires elementary-stream inspection and is "
                    "outside this report's current scope."
                ),
                body,
            ),
        ]),
    ])

    def page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(
            doc.leftMargin,
            0.43 * inch,
            letter[0] - doc.rightMargin,
            0.43 * inch,
        )
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            doc.leftMargin,
            0.25 * inch,
            translated(
                "footer",
                "Broadcast Tool Pro - Confidential Validation Report",
            ),
        )
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            0.25 * inch,
            f'{translated("page", "Page")} {doc.page}',
        )
        canvas.restoreState()

    document.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()


def _spanish_severity(value) -> str:
    return {
        "critical": "Critico",
        "error": "Error",
        "warning": "Advertencia",
        "info": "Informativo",
    }.get(str(value or "info").lower(), "Informativo")


def _table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
