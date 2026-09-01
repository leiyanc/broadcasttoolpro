from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from backend.api.xmltv import (
    EXCEL_TEMPLATE,
    download_csv_template,
    download_excel_template,
)
from backend.services.xmltv.parser import EXPECTED_COLUMNS


def test_excel_template_has_expected_structure():
    workbook = load_workbook(
        BytesIO(EXCEL_TEMPLATE.read_bytes()),
        read_only=True,
        data_only=True,
    )

    assert workbook.sheetnames == [
        "Programming",
        "Instructions",
        "Field Reference",
        "Example",
    ]
    worksheet = workbook["Programming"]
    headers = [cell.value for cell in worksheet[4]]
    assert headers == EXPECTED_COLUMNS


def test_excel_template_endpoint_returns_download():
    response = download_excel_template()

    assert Path(response.path) == EXCEL_TEMPLATE
    assert response.filename == "Broadcast_Tool_Pro_XMLTV_Template.xlsx"
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_csv_template_endpoint_returns_expected_headers():
    response = download_csv_template()
    content = response.body.decode()

    assert content.splitlines()[0].split(",") == EXPECTED_COLUMNS
    assert "Broadcast_Tool_Pro_XMLTV_Template.csv" in response.headers[
        "content-disposition"
    ]
    assert response.headers["cache-control"] == "no-store, max-age=0"
