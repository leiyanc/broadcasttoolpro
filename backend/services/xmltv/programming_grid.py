from collections import defaultdict
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from io import BytesIO
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


NAVY = colors.HexColor("#102A43")
GRID = colors.HexColor("#B7C8DE")
MUTED = colors.HexColor("#52677F")
LIVE_BACKGROUND = colors.HexColor("#7F1D1D")
LIVE_COLORS = (
    colors.HexColor("#7F1D1D"),
    colors.HexColor("#78350F"),
    colors.HexColor("#1E3A8A"),
    colors.HexColor("#4C1D95"),
    colors.HexColor("#064E3B"),
    colors.HexColor("#831843"),
    colors.HexColor("#164E63"),
    colors.HexColor("#3F3F46"),
    colors.HexColor("#713F12"),
    colors.HexColor("#312E81"),
)
SHOW_COLORS = (
    colors.HexColor("#DDEAFE"),
    colors.HexColor("#DCF5E8"),
    colors.HexColor("#F8E1EC"),
    colors.HexColor("#EEE5FF"),
    colors.HexColor("#FFF0CE"),
    colors.HexColor("#DDF3F5"),
    colors.HexColor("#FDE7D8"),
    colors.HexColor("#E9EED0"),
    colors.HexColor("#E5E7FA"),
    colors.HexColor("#F6E6C8"),
)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _local_datetime(value: str, timezone_name: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(ZoneInfo(timezone_name))


def _programme_dates(
    programmes: list[dict],
    timezone_name: str,
) -> dict[date, list[dict]]:
    by_day: dict[date, list[dict]] = defaultdict(list)
    for programme in programmes:
        start = _local_datetime(programme["start_utc"], timezone_name)
        stop = _local_datetime(programme["stop_utc"], timezone_name)
        by_day[start.date()].append({
            **programme,
            "_local_start": start,
            "_local_stop": stop,
        })
    return by_day


def _fit_text(
    value: str,
    max_width: float,
    font_name: str = "Helvetica-Bold",
    font_size: float = 5.5,
) -> str:
    if stringWidth(value, font_name, font_size) <= max_width:
        return value
    ellipsis = "..."
    text = value
    while text and stringWidth(
        text + ellipsis,
        font_name,
        font_size,
    ) > max_width:
        text = text[:-1]
    return text.rstrip() + ellipsis


def _show_color(title: str) -> colors.Color:
    normalized = " ".join(title.casefold().split())
    digest = sha256(normalized.encode("utf-8")).digest()
    return SHOW_COLORS[int.from_bytes(digest[:2], "big") % len(SHOW_COLORS)]


def _live_color(title: str) -> colors.Color:
    normalized = " ".join(title.casefold().split())
    digest = sha256(normalized.encode("utf-8")).digest()
    return LIVE_COLORS[int.from_bytes(digest[:2], "big") % len(LIVE_COLORS)]


def _draw_logo(
    pdf: canvas.Canvas,
    logo_content: bytes | None,
    left: float,
    page_height: float,
) -> None:
    if not logo_content:
        return

    try:
        image = ImageReader(BytesIO(logo_content))
        width, height = image.getSize()
    except Exception as exc:
        raise ValueError(
            "The channel logo must be a valid PNG, JPG, or JPEG image."
        ) from exc

    max_width, max_height = 110, 34
    scale = min(max_width / width, max_height / height)
    draw_width = width * scale
    draw_height = height * scale
    pdf.drawImage(
        image,
        left,
        page_height - 38,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )


def _draw_page(
    pdf: canvas.Canvas,
    week: date,
    by_day: dict[date, list[dict]],
    channel_name: str,
    timezone_name: str,
    logo_content: bytes | None,
) -> None:
    page_width, page_height = landscape(letter)
    left, right, top, bottom = 30, 24, 52, 24
    time_width, header_height = 45, 22
    grid_width = page_width - left - right
    day_width = (grid_width - time_width) / 7
    grid_top = page_height - top - header_height
    grid_bottom = bottom + 18
    grid_height = grid_top - grid_bottom
    half_hour_height = grid_height / 48

    _draw_logo(pdf, logo_content, left, page_height)
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawRightString(
        page_width - right,
        page_height - 19,
        "PROGRAMMING GRID",
    )
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawRightString(
        page_width - right,
        page_height - 30,
        channel_name,
    )
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawRightString(
        page_width - right,
        page_height - 40,
        f"Week of {week.strftime('%B %d, %Y')}  |  {timezone_name}",
    )

    pdf.setFillColor(NAVY)
    pdf.rect(left, grid_top, grid_width, header_height, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawCentredString(left + time_width / 2, grid_top + 8, "TIME")

    for day_index in range(7):
        day = week + timedelta(days=day_index)
        x = left + time_width + day_index * day_width
        pdf.drawCentredString(
            x + day_width / 2,
            grid_top + 8,
            day.strftime("%a %m/%d"),
        )

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(0.35)
    for slot in range(49):
        y = grid_top - slot * half_hour_height
        pdf.line(left, y, left + grid_width, y)
    verticals = [left, left + time_width]
    verticals.extend(
        left + time_width + index * day_width
        for index in range(1, 8)
    )
    for x in verticals:
        pdf.line(x, grid_bottom, x, grid_top + header_height)

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 5.5)
    for slot in range(48):
        slot_time = (
            datetime.combine(date.min, time.min)
            + timedelta(minutes=slot * 30)
        )
        y = grid_top - (slot + 0.68) * half_hour_height
        pdf.drawCentredString(
            left + time_width / 2,
            y,
            slot_time.strftime("%I:%M %p").lstrip("0"),
        )

    for day_index in range(7):
        day = week + timedelta(days=day_index)
        x = left + time_width + day_index * day_width
        for programme in by_day.get(day, []):
            start = programme["_local_start"]
            stop = programme["_local_stop"]
            start_minutes = start.hour * 60 + start.minute + start.second / 60
            duration_minutes = max((stop - start).total_seconds() / 60, 8)
            display_minutes = min(duration_minutes, 1440 - start_minutes)
            block_top = grid_top - (start_minutes / 1440) * grid_height
            block_height = max(
                (display_minutes / 1440) * grid_height,
                4,
            )
            block_bottom = max(grid_bottom, block_top - block_height)

            is_live = bool(programme.get("live"))
            pdf.setFillColor(
                _live_color(programme["program_title"])
                if is_live
                else _show_color(programme["program_title"])
            )
            pdf.setStrokeColor(colors.white)
            pdf.rect(
                x + 0.5,
                block_bottom,
                day_width - 1,
                block_top - block_bottom,
                fill=1,
                stroke=1,
            )
            if block_top - block_bottom >= 5:
                pdf.setFillColor(colors.white if is_live else NAVY)
                pdf.setFont("Helvetica-Bold", 5.5)
                title = _fit_text(
                    programme["program_title"],
                    day_width - 5,
                )
                pdf.drawString(x + 2.5, block_top - 5.5, title)

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 5.5)
    pdf.drawString(
        left,
        13,
        "Generated by Broadcast Tool Pro from the validated EPG schedule.",
    )
    pdf.drawRightString(
        page_width - right,
        13,
        f"{week.isoformat()} - {(week + timedelta(days=6)).isoformat()}",
    )


def generate_programming_grid(
    programmes: list[dict],
    channel_name: str,
    timezone_name: str,
    logo_content: bytes | None = None,
) -> bytes:
    if not programmes:
        raise ValueError("The schedule does not contain any programmes.")

    by_day = _programme_dates(programmes, timezone_name)
    weeks = sorted({_week_start(day) for day in by_day})
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=landscape(letter))
    pdf.setTitle(f"{channel_name} Programming Grid")
    pdf.setAuthor("Broadcast Tool Pro")

    for index, week in enumerate(weeks):
        if index:
            pdf.showPage()
        _draw_page(
            pdf,
            week,
            by_day,
            channel_name,
            timezone_name,
            logo_content,
        )

    pdf.save()
    return output.getvalue()
