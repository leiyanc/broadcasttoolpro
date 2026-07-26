from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services import report_history


def test_report_history_records_and_retrieves_artifacts():
    original_data_dir = report_history.DATA_DIR
    original_reports_dir = report_history.REPORTS_DIR
    original_database_path = report_history.DATABASE_PATH

    with TemporaryDirectory() as directory:
        data_dir = Path(directory)
        report_history.DATA_DIR = data_dir
        report_history.REPORTS_DIR = data_dir / "reports"
        report_history.DATABASE_PATH = data_dir / "history.db"
        try:
            report_id = report_history.record_report(
                report_type="postlog",
                client_name="Example Client",
                channel_name="Example Channel",
                product=None,
                agency=None,
                asset_ids=["clip_b", "clip_a", "clip_a"],
                start_date="2026-07-25",
                end_date="2026-07-27",
                output_format="pdf",
                filename="certification.pdf",
                media_type="application/pdf",
                content=b"report",
            )

            saved = report_history.get_report(report_id)
            reports = report_history.list_reports()

            assert saved is not None
            assert saved["client_name"] == "Example Client"
            assert saved["asset_ids"] == ["clip_a", "clip_b"]
            assert Path(saved["file_path"]).read_bytes() == b"report"
            assert reports[0]["id"] == report_id
            assert "file_path" not in reports[0]
        finally:
            report_history.DATA_DIR = original_data_dir
            report_history.REPORTS_DIR = original_reports_dir
            report_history.DATABASE_PATH = original_database_path
