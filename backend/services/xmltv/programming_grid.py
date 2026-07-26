from collections import defaultdict
from datetime import date, datetime, time, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


NAVY = colors.HexColor("#102A43")
LIGHT_BLUE = colors.HexColor("#EAF2FF")
GRID = colors.HexColor("#B7C8DE")
MUTED = colors.HexColor("#52677F")
GENRE_COLORS = (
    colors.HexColor("#DDEAFE"),
    colors.HexColor("#DCF5E8"),
    colors.HexColor("#F8E1EC"),
    colors.HexColor("#EEE5FF"),
    colors.HexColor("#FFF0CE"),
    colors.HexColor("#DDF3F5"),
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


def _genre_color(genre: str | None) -> colors.Color:
    if not genre:
        return LIGHT_BLUE
    index = sum(ord(character) for character in genre.lower())
    return GENRE_COLORS[index % len(GENRE_COLORS)]


def _draw_page(
    pdf: canvas.Canvas,
    week: date,
    by_day: dict[date, list[dict]],
    channel_name: str,
    timezone_name: str,
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

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(left, page_height - 27, channel_name)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawRightString(
        page_width - right,
        page_height - 23,
        "PROGRAMMING GRID",
    )
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawRightString(
        page_width - right,
        page_height - 34,
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

            pdf.setFillColor(_genre_color(programme.get("genre")))
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
                pdf.setFillColor(NAVY)
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
        _draw_page(pdf, week, by_day, channel_name, timezone_name)

    pdf.save()
    return output.getvalue()
