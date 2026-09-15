from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone

from backend.services import report_history
from backend.services.tenant_store import TenantStore


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
                organization_id="organization-a",
                created_by="user-a",
            )

            saved = report_history.get_report(report_id, "organization-a")
            reports = report_history.list_reports("organization-a")

            assert saved is not None
            assert saved["client_name"] == "Example Client"
            assert saved["asset_ids"] == ["clip_a", "clip_b"]
            assert Path(saved["file_path"]).read_bytes() == b"report"
            assert reports[0]["id"] == report_id
            assert "file_path" not in reports[0]
            assert (
                report_history.get_report(report_id, "organization-b")
                is None
            )
            assert report_history.list_reports("organization-b") == []
        finally:
            report_history.DATA_DIR = original_data_dir
            report_history.REPORTS_DIR = original_reports_dir
            report_history.DATABASE_PATH = original_database_path


def test_closed_account_reports_are_purged_after_ninety_days_only():
    original_data_dir = report_history.DATA_DIR
    original_reports_dir = report_history.REPORTS_DIR
    original_database_path = report_history.DATABASE_PATH
    with TemporaryDirectory() as directory:
        data_dir = Path(directory)
        database_path = data_dir / "retention.db"
        report_history.DATA_DIR = data_dir
        report_history.REPORTS_DIR = data_dir / "reports"
        report_history.DATABASE_PATH = database_path
        try:
            tenants = TenantStore(database_path)
            tenants.initialize()
            old_org = tenants.create_organization(
                name="Old Closed", slug="old-closed", plan="professional"
            )
            recent_org = tenants.create_organization(
                name="Recent Closed", slug="recent-closed", plan="professional"
            )
            active_org = tenants.create_organization(
                name="Still Active", slug="still-active", plan="professional"
            )
            tenants.close_organization(
                old_org["id"], closed_at="2026-01-01T00:00:00+00:00"
            )
            tenants.close_organization(
                recent_org["id"], closed_at="2026-03-15T00:00:00+00:00"
            )

            ids = {}
            for label, organization in {
                "old": old_org,
                "recent": recent_org,
                "active": active_org,
            }.items():
                ids[label] = report_history.record_report(
                    report_type="prelog",
                    client_name=None,
                    channel_name="Test Channel",
                    product=None,
                    agency=None,
                    asset_ids=[],
                    start_date=None,
                    end_date=None,
                    output_format="pdf",
                    filename=f"{label}.pdf",
                    media_type="application/pdf",
                    content=label.encode(),
                    organization_id=organization["id"],
                )

            result = report_history.purge_reports_for_closed_organizations(
                now=datetime(2026, 4, 2, tzinfo=timezone.utc)
            )

            assert result["removed"] == 1
            assert report_history.get_report(ids["old"], old_org["id"]) is None
            assert report_history.get_report(
                ids["recent"], recent_org["id"]
            ) is not None
            assert report_history.get_report(
                ids["active"], active_org["id"]
            ) is not None
        finally:
            report_history.DATA_DIR = original_data_dir
            report_history.REPORTS_DIR = original_reports_dir
            report_history.DATABASE_PATH = original_database_path
