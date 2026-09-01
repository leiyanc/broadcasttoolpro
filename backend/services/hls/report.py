from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, String
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
WARNING = colors.HexColor("#B45309")
PALE_SUCCESS = colors.HexColor("#ECFDF3")
PALE_WARNING = colors.HexColor("#FFF7ED")
PALE_DANGER = colors.HexColor("#FEF3F2")
BRAND_LOGO = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "broadcast-tool-pro-logo.png"
)

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


def _scte_summary(payload: dict) -> dict:
    supplied = payload.get("scte35_summary") or {}
    if supplied:
        return supplied
    triggers = list(payload.get("triggers") or [])
    date_range_breaks = [
        trigger for trigger in triggers
        if (
            trigger.get("type") == "SCTE-35 DATERANGE"
            and trigger.get("ad_trigger") is not False
        )
    ]
    cue_out_breaks = [
        trigger for trigger in triggers
        if trigger.get("type") == "CUE-OUT"
    ]
    breaks = date_range_breaks or cue_out_breaks
    durations = []
    for trigger in breaks:
        try:
            duration = float(trigger.get("duration"))
        except (TypeError, ValueError):
            continue
        if duration > 0:
            durations.append(duration)
    return {
        "break_count": max(len(date_range_breaks), len(cue_out_breaks)),
        "continuation_count": sum(
            trigger.get("type") == "CUE-OUT-CONT"
            for trigger in triggers
        ),
        "durations_reported": len(durations),
        "total_planned_duration": round(sum(durations), 3),
    }

SPANISH = {
    "platform": "Plataforma de Operaciones Broadcast",
    "title": "Reporte de Validacion de Stream HLS y Monitoreo SCTE-35",
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
    "track_present": "Pista Presente; Ningun Cue Observado",
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


def _number(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _loudness_interpretation(loudness: dict, spanish: bool) -> dict:
    integrated = _number(loudness.get("integrated_lkfs"))
    true_peak = _number(loudness.get("true_peak_dbtp"))
    target = _number(loudness.get("target_lkfs"), -24.0)
    tolerance = _number(loudness.get("tolerance_lu"), 2.0)
    peak_limit = _number(loudness.get("true_peak_limit_dbtp"), -2.0)
    loudness_range = loudness.get("loudness_range_lu")
    measured_seconds = _number(loudness.get("measured_seconds"))
    delta = integrated - target
    headroom = peak_limit - true_peak
    within_target = abs(delta) <= tolerance
    peak_safe = true_peak <= peak_limit
    partial = bool(loudness.get("partial"))
    status = str(loudness.get("status") or "warning").lower()

    if loudness_range is None:
        range_label = "No disponible" if spanish else "Not available"
    else:
        range_value = _number(loudness_range)
        if range_value <= 7:
            range_label = (
                "Variacion controlada (informativo)"
                if spanish else "Controlled variation (informational)"
            )
        elif range_value <= 15:
            range_label = (
                "Variacion moderada (informativo)"
                if spanish else "Moderate variation (informational)"
            )
        else:
            range_label = (
                "Variacion amplia; revisar (informativo)"
                if spanish else "Wide variation; review (informational)"
            )

    status_label = {
        "pass": "APROBADO" if spanish else "PASS",
        "warning": "REVISAR" if spanish else "REVIEW",
        "fail": "FALLIDO" if spanish else "FAIL",
    }.get(status, "REVISAR" if spanish else "REVIEW")
    coverage = (
        "Cobertura parcial - resultado preliminar"
        if spanish else "Partial coverage - preliminary result"
    ) if partial else (
        "Sesion solicitada completada"
        if spanish else "Requested session completed"
    )
    integrated_label = (
        f"Dentro del objetivo ({abs(delta):.1f} LU de diferencia)"
        if spanish else f"Within target ({abs(delta):.1f} LU difference)"
    ) if within_target else (
        f"Fuera del objetivo ({abs(delta):.1f} LU de diferencia)"
        if spanish else f"Outside target ({abs(delta):.1f} LU difference)"
    )
    peak_label = (
        f"Seguro ({headroom:.1f} dB por debajo del limite)"
        if spanish else f"Safe ({headroom:.1f} dB below limit)"
    ) if peak_safe else (
        f"Supera el limite por {abs(headroom):.1f} dB"
        if spanish else f"Exceeds limit by {abs(headroom):.1f} dB"
    )
    if spanish:
        executive = (
            f"El loudness integrado esta a {abs(delta):.1f} LU "
            f"del objetivo y el true peak conserva {max(headroom, 0):.1f} dB "
            f"de margen frente al limite configurado. {coverage}. La medicion "
            f"cubre {measured_seconds:.1f} segundos de audio."
        )
    else:
        executive = (
            f"Integrated loudness is {abs(delta):.1f} LU from "
            f"target and true peak retains {max(headroom, 0):.1f} dB of "
            f"headroom below the configured limit. {coverage}. The measurement "
            f"covers {measured_seconds:.1f} seconds of audio."
        )
    return {
        "status": status,
        "status_label": status_label,
        "executive": executive,
        "coverage": coverage,
        "integrated": integrated_label,
        "true_peak": peak_label,
        "loudness_range": range_label,
    }


def _paragraph(value, style):
    return Paragraph(_text(value), style)


def _timestamp_label(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError):
        return str(value)[:24]


def _bandwidth_chart(
    samples: list[dict],
    spanish: bool,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> Drawing:
    width = 6.9 * inch
    height = 2.45 * inch
    left = 48
    right = width - 16
    top = height - 18
    bottom = 30
    values = [
        max(0.0, float(sample.get("bandwidth_kbps") or 0))
        for sample in samples
    ]
    upper = max(values) if values else 1
    lower = min(values) if values else 0
    padding = max((upper - lower) * 0.15, upper * 0.05, 50)
    y_min = max(0, lower - padding)
    y_max = upper + padding
    drawing = Drawing(width, height)

    for step in range(5):
        y = bottom + (top - bottom) * step / 4
        value = y_min + (y_max - y_min) * step / 4
        drawing.add(Line(
            left,
            y,
            right,
            y,
            strokeColor=LINE,
            strokeWidth=0.5,
        ))
        drawing.add(String(
            left - 5,
            y - 2,
            f"{value:.0f}",
            textAnchor="end",
            fontName="Helvetica",
            fontSize=6.5,
            fillColor=MUTED,
        ))

    points = []
    divisor = max(1, len(values) - 1)
    for index, value in enumerate(values):
        x = left + (right - left) * index / divisor
        y = bottom + (top - bottom) * (
            (value - y_min) / max(1, y_max - y_min)
        )
        points.extend([x, y])
    if len(points) >= 4:
        drawing.add(PolyLine(
            points,
            strokeColor=BLUE,
            strokeWidth=2,
        ))
    for index in {0, len(values) - 1}:
        if index < 0 or not values:
            continue
        drawing.add(Circle(
            points[index * 2],
            points[index * 2 + 1],
            2.4,
            fillColor=BLUE,
            strokeColor=colors.white,
            strokeWidth=0.6,
        ))

    drawing.add(Line(left, bottom, right, bottom, strokeColor=NAVY))
    drawing.add(Line(left, bottom, left, top, strokeColor=NAVY))
    drawing.add(String(
        8,
        top + 2,
        "kbps",
        fontName="Helvetica-Bold",
        fontSize=7,
        fillColor=NAVY,
    ))
    start_label = _timestamp_label(
        started_at or (samples[0].get("detected_at") if samples else None)
    )
    end_label = _timestamp_label(
        ended_at or (samples[-1].get("detected_at") if samples else None)
    )
    drawing.add(String(
        left,
        12,
        start_label or ("Inicio" if spanish else "Start"),
        fontName="Helvetica",
        fontSize=6.3,
        fillColor=MUTED,
    ))
    drawing.add(String(
        right,
        12,
        end_label or ("Fin" if spanish else "End"),
        textAnchor="end",
        fontName="Helvetica",
        fontSize=6.3,
        fillColor=MUTED,
    ))
    return drawing


def generate_hls_report(
    payload: dict,
) -> bytes:
    spanish = payload.get("report_language") == "es"
    copy = SPANISH if spanish else {}

    def translated(key: str, english: str) -> str:
        return copy.get(key, english)

    loudness = payload.get("loudness") or {}
    english_title = (
        "HLS Validation, SCTE-35 & Loudness Assessment Report"
        if loudness
        else "HLS Stream Validation & SCTE-35 Monitoring Report"
    )
    spanish_title = (
        "Reporte de Validacion HLS, SCTE-35 y Evaluacion de Loudness"
        if loudness
        else copy.get("title")
    )
    report_title = spanish_title if spanish else english_title
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.62 * inch,
        title=report_title,
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

    story = [
        Paragraph(report_title, title),
        Paragraph(
            translated(
                "disclaimer",
                "Independent validation report. Broadcast Tool Pro did not "
                "modify, repair, or repackage the inspected stream.",
            ),
            small,
        ),
        Spacer(1, 0.16 * inch),
    ]

    valid = bool(payload.get("valid"))
    status_color = SUCCESS if valid else DANGER
    scte_summary = _scte_summary(payload)
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
            "Periodo Solicitado" if spanish else "Requested Monitoring Period",
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
            else (
                translated(
                    "track_present",
                    "Track Present; No Cue Observed",
                )
                if payload.get("scte35_track_detected")
                else translated("not_detected", "Not Detected")
            ),
        ],
        [translated("triggers", "Unique Triggers"), str(payload.get("trigger_count", 0))],
        [
            "Pausas Publicitarias" if spanish else "Ad Breaks",
            str(scte_summary.get("break_count", 0)),
        ],
        [
            "Duracion Planificada Total" if spanish else "Total Planned Duration",
            f'{scte_summary.get("total_planned_duration", 0)}s',
        ],
        [
            "Marcadores de Continuacion" if spanish else "Continuation Markers",
            str(scte_summary.get("continuation_count", 0)),
        ],
        [translated("generated", "Generated"), str(payload.get("generated_at") or "")],
    ]
    optional_rows = [
        ("Canal / Servicio" if spanish else "Channel / Service", payload.get("channel_name")),
        ("ID del Canal" if spanish else "Channel ID", payload.get("channel_id")),
        ("Cliente / Organizacion" if spanish else "Client / Organization", payload.get("client_name")),
        ("Referencia de Prueba" if spanish else "Test Reference", payload.get("test_reference")),
        ("Operador" if spanish else "Operator", payload.get("operator_name")),
        ("Proposito" if spanish else "Purpose", payload.get("monitoring_purpose")),
        (
            "Hora Esperada del Cue" if spanish else "Expected Cue Time",
            (
                f'{payload.get("expected_cue_at")} '
                f'({payload.get("report_timezone")})'
                if payload.get("expected_cue_at") and payload.get("report_timezone")
                else payload.get("expected_cue_at")
            ),
        ),
        (
            "Duracion Esperada del Break" if spanish else "Expected Break Duration",
            (
                f'{payload.get("expected_break_duration")}s'
                if payload.get("expected_break_duration") else None
            ),
        ),
    ]
    summary[1:1] = [
        [label_text, str(value)]
        for label_text, value in optional_rows
        if value not in (None, "")
    ]
    if payload.get("monitoring_started_at") or payload.get("monitoring_ended_at"):
        started_at = payload.get("monitoring_started_at")
        ended_at = payload.get("monitoring_ended_at")
        summary.insert(4 + sum(bool(value) for _, value in optional_rows), [
            "Ventana Analizada" if spanish else "Analyzed Window",
            (
                f"{_timestamp_label(started_at)} - "
                f"{_timestamp_label(ended_at)}"
            ).strip(" -"),
        ])
        try:
            start_dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
            observed_seconds = max(0, int((end_dt - start_dt).total_seconds()))
            summary.insert(5 + sum(bool(value) for _, value in optional_rows), [
                "Duracion Observada" if spanish else "Observed Duration",
                f"{observed_seconds // 60}m {observed_seconds % 60}s",
            ])
            timezone_name = str(payload.get("report_timezone") or "")
            if timezone_name:
                local_zone = ZoneInfo(timezone_name)
                local_format = "%Y-%m-%d %H:%M:%S %Z"
                summary.insert(6 + sum(bool(value) for _, value in optional_rows), [
                    "Ventana Local" if spanish else "Local Window",
                    (
                        f"{start_dt.astimezone(local_zone).strftime(local_format)} - "
                        f"{end_dt.astimezone(local_zone).strftime(local_format)}"
                    ),
                ])
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            pass
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

    if loudness:
        interpretation = _loudness_interpretation(loudness, spanish)
        status_label = {
            "pass": "Aprobado" if spanish else "Pass",
            "warning": "Revisar" if spanish else "Warning",
            "fail": "Fallido" if spanish else "Fail",
        }.get(str(loudness.get("status") or "").lower(), "-")
        loudness_rows = [
            [
                "Perfil" if spanish else "Profile",
                loudness.get("profile"),
                "Perfil tecnico de referencia" if spanish else "Technical reference profile",
            ],
            [
                "Estado" if spanish else "Status",
                status_label,
                "Evaluacion general" if spanish else "Overall assessment",
            ],
            [
                "Tipo de medicion" if spanish else "Measurement Type",
                (
                    "Parcial" if spanish else "Partial"
                ) if loudness.get("partial") else (
                    "Completa" if spanish else "Complete"
                ),
                interpretation["coverage"],
            ],
            [
                "Loudness integrado" if spanish else "Integrated Loudness",
                f'{loudness.get("integrated_lkfs")} LKFS',
                interpretation["integrated"],
            ],
            [
                "True Peak",
                f'{loudness.get("true_peak_dbtp")} dBTP',
                interpretation["true_peak"],
            ],
            [
                "Rango de loudness" if spanish else "Loudness Range",
                (
                    f'{loudness.get("loudness_range_lu")} LU'
                    if loudness.get("loudness_range_lu") is not None
                    else "-"
                ),
                interpretation["loudness_range"],
            ],
            [
                "Duracion analizada" if spanish else "Analyzed Duration",
                (
                    f'{float(loudness.get("measured_seconds")):.1f} s'
                    if loudness.get("measured_seconds") is not None
                    else "-"
                ),
                interpretation["coverage"],
            ],
            [
                "Objetivo" if spanish else "Target",
                (
                    f'{loudness.get("target_lkfs")} LKFS '
                    f'±{loudness.get("tolerance_lu")} LU'
                ),
                "Rango de referencia" if spanish else "Reference range",
            ],
        ]
        loudness_table = Table(
            [
                [
                    _paragraph("Metrica" if spanish else "Metric", table_header),
                    _paragraph("Resultado" if spanish else "Result", table_header),
                    _paragraph("Interpretacion" if spanish else "Interpretation", table_header),
                ],
                *[
                    [
                        _paragraph(key, label),
                        _paragraph(value, body),
                        _paragraph(assessment, small),
                    ]
                    for key, value, assessment in loudness_rows
                ],
            ],
            colWidths=[1.35 * inch, 1.45 * inch, 4.1 * inch],
        )
        loudness_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (0, -1), PALE_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        assessment_background = {
            "pass": PALE_SUCCESS,
            "warning": PALE_WARNING,
            "fail": PALE_DANGER,
        }.get(interpretation["status"], PALE_WARNING)
        assessment_color = {
            "pass": SUCCESS,
            "warning": WARNING,
            "fail": DANGER,
        }.get(interpretation["status"], WARNING)
        executive_box = Table(
            [[Paragraph(
                f'<b>{_text(interpretation["status_label"])}</b><br/>'
                f'{_text(interpretation["executive"], 1200)}',
                body,
            )]],
            colWidths=[6.9 * inch],
        )
        executive_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), assessment_background),
            ("BOX", (0, 0), (-1, -1), 1, assessment_color),
            ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        loudness_story = [
            Paragraph(
                "Cumplimiento Tecnico de Loudness"
                if spanish else "Media Loudness Compliance",
                heading,
            ),
            executive_box,
            Spacer(1, 0.1 * inch),
            loudness_table,
        ]
        for finding in list(loudness.get("findings") or [])[:20]:
            finding_message = _text(finding.get("message"), 800)
            if spanish:
                finding_message = {
                    "LOUD-001": (
                        "El loudness integrado esta fuera del rango tecnico "
                        "configurado para ATSC A/85."
                    ),
                    "LOUD-002": (
                        "El true peak supera el limite tecnico configurado."
                    ),
                    "LOUD-003": (
                        "El audio medido esta dentro de los limites configurados, "
                        "pero suficientemente cerca de un limite para requerir "
                        "revision."
                    ),
                }.get(_text(finding.get("rule_id")), finding_message)
            loudness_story.append(Paragraph(
                f'<b>{_text(finding.get("rule_id"))}</b>: '
                f'{finding_message}',
                small,
            ))
        loudness_story.extend([
            Spacer(1, 0.05 * inch),
            Paragraph(
                (
                    "Esta evaluacion tecnica no constituye una certificacion "
                    "legal ni una determinacion de cumplimiento con SB 576 u "
                    "otra ley."
                    if spanish else
                    "This technical assessment is not a legal certification "
                    "or a determination of compliance with SB 576 or any "
                    "other law."
                ),
                small,
            ),
        ])
        story.append(KeepTogether(loudness_story))

    bandwidth_samples = list(payload.get("bandwidth_samples") or [])[:1000]
    if bandwidth_samples:
        values = [
            float(sample.get("bandwidth_kbps") or 0)
            for sample in bandwidth_samples
        ]
        bandwidth_section = [Paragraph(
            "Comportamiento del Bandwidth"
            if spanish
            else "Bandwidth Behavior",
            heading,
        )]
        bandwidth_section.append(Paragraph(
            (
                "Bitrate observado por segmento durante el periodo de "
                "monitoreo."
                if spanish
                else
                "Observed segment bitrate throughout the monitoring period."
            ),
            small,
        ))
        bandwidth_section.append(Spacer(1, 0.05 * inch))
        bandwidth_section.append(_bandwidth_chart(
            bandwidth_samples,
            spanish,
            payload.get("monitoring_started_at"),
            payload.get("monitoring_ended_at"),
        ))
        bandwidth_summary = [
            [
                "Minimo" if spanish else "Minimum",
                "Promedio" if spanish else "Average",
                "Maximo" if spanish else "Maximum",
                "Muestras" if spanish else "Samples",
            ],
            [
                f"{min(values):.0f} kbps",
                f"{sum(values) / len(values):.0f} kbps",
                f"{max(values):.0f} kbps",
                str(len(values)),
            ],
        ]
        bandwidth_table = Table(
            [
                [
                    _paragraph(
                        cell,
                        table_header if row_index == 0 else body,
                    )
                    for cell in row
                ]
                for row_index, row in enumerate(bandwidth_summary)
            ],
            colWidths=[1.725 * inch] * 4,
        )
        bandwidth_table.setStyle(_table_style())
        bandwidth_section.extend([
            bandwidth_table,
            Paragraph(
                (
                    "Las muestras corresponden a segmentos nuevos con bitrate "
                    "medible; por eso pueden ser menos que las inspecciones."
                    if spanish else
                    "Samples represent new segments with measurable bitrate, "
                    "so the count may be lower than the number of inspections."
                ),
                small,
            ),
            Spacer(1, 0.08 * inch),
        ])
        story.append(KeepTogether(bandwidth_section))

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
                    "a nivel de manifiesto y en las muestras MPEG-TS inspeccionadas. "
                    "No altera el stream de origen. Los eventos fuera del periodo "
                    "seleccionado o fuera de las porciones muestreadas no forman "
                    "parte de este reporte."
                    if spanish
                    else
                    "This report validates HLS manifest structure and supported "
                    "SCTE-35/ad-marker signaling in manifests and inspected "
                    "MPEG-TS samples. It does not alter the source stream. Events "
                    "outside the selected period or sampled segment portions are "
                    "not included in this report."
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
        canvas.drawCentredString(
            letter[0] / 2,
            0.25 * inch,
            f'{translated("page", "Page")} {doc.page}',
        )
        canvas.drawImage(
            str(BRAND_LOGO),
            letter[0] - doc.rightMargin - 86,
            7,
            width=86,
            height=19,
            preserveAspectRatio=True,
            mask="auto",
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
