import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.services.tenant_store import DATABASE_PATH


MODULE_CATALOG = {
    "xmltv_generator": {
        "name": "XMLTV Generator",
        "suite": "XMLTV",
        "source": "professional",
    },
    "xmltv_validator": {
        "name": "XMLTV Validator",
        "suite": "XMLTV",
        "source": "professional",
    },
    "xmltv_repair": {
        "name": "XMLTV Repair",
        "suite": "XMLTV",
        "source": "professional",
    },
    "programming_grid": {
        "name": "Programming Grid",
        "suite": "XMLTV",
        "source": "professional",
    },
    "hls_validator": {
        "name": "HLS Validator",
        "suite": "Streaming QC",
        "source": "professional",
    },
    "prelogs": {
        "name": "Pre Logs",
        "suite": "Traffic Operations",
        "source": "traffic_operations",
    },
    "postlogs": {
        "name": "Post Logs",
        "suite": "Traffic Operations",
        "source": "traffic_operations",
    },
    "hls_monitor": {
        "name": "Monitor Stream",
        "suite": "Streaming QC",
        "source": "stream_monitoring",
    },
    "media_qc": {
        "name": "Media Loudness Compliance",
        "suite": "Streaming QC",
        "source": "stream_monitoring",
        "available": True,
    },
}

ADD_ON_CATALOG = {
    "traffic_operations": {
        "name": "Traffic Operations",
        "modules": ["prelogs", "postlogs"],
    },
    "stream_monitoring": {
        "name": "Stream Monitoring",
        "modules": ["hls_monitor"],
    },
}


class EntitlementStore:
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS organization_addons (
                    organization_id TEXT NOT NULL,
                    addon_code TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (organization_id, addon_code),
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE
                )
            """)

    def set_addon(
        self,
        organization_id: str,
        addon_code: str,
        enabled: bool,
    ) -> None:
        if addon_code not in ADD_ON_CATALOG:
            raise ValueError(f'Unknown add-on: "{addon_code}".')
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO organization_addons (
                    organization_id, addon_code, enabled
                ) VALUES (?, ?, ?)
                ON CONFLICT (organization_id, addon_code)
                DO UPDATE SET enabled = excluded.enabled
                """,
                (organization_id, addon_code, int(enabled)),
            )

    def effective_entitlements(self, organization_id: str) -> dict:
        with self._connection() as connection:
            organization = connection.execute(
                "SELECT plan FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
            if organization is None:
                raise KeyError("Organization not found.")
            rows = connection.execute(
                """
                SELECT addon_code
                FROM organization_addons
                WHERE organization_id = ? AND enabled = 1
                """,
                (organization_id,),
            ).fetchall()
            try:
                subscription = connection.execute(
                    """
                    SELECT status, current_period_end, provider,
                           payment_waived, waiver_expires_at,
                           cancel_at_period_end, grace_period_ends_at
                    FROM subscriptions
                    WHERE organization_id = ?
                    """,
                    (organization_id,),
                ).fetchone()
            except sqlite3.OperationalError:
                subscription = None

        plan = organization["plan"]
        trial_active = False
        trial_ends_at = None
        access_active = True
        access_type = "paid"
        access_ends_at = None
        if subscription and subscription["status"] == "trialing":
            trial_ends_at = subscription["current_period_end"]
            trial_active = (
                datetime.fromisoformat(trial_ends_at)
                > datetime.now(timezone.utc)
            )
            access_active = trial_active
            access_type = "trial"
            access_ends_at = trial_ends_at
        elif subscription:
            grace_end = subscription["grace_period_ends_at"]
            parsed_grace_end = None
            if grace_end:
                parsed_grace_end = datetime.fromisoformat(grace_end)
                if parsed_grace_end.tzinfo is None:
                    parsed_grace_end = parsed_grace_end.replace(
                        tzinfo=timezone.utc
                    )
            in_payment_grace = bool(
                subscription["provider"] == "stripe"
                and subscription["status"] == "past_due"
                and parsed_grace_end
                and parsed_grace_end > datetime.now(timezone.utc)
            )
            access_active = (
                subscription["status"] == "active" or in_payment_grace
            )
            if in_payment_grace:
                access_type = "payment_grace"
                access_ends_at = grace_end
            if subscription["cancel_at_period_end"]:
                access_ends_at = subscription["current_period_end"]
                if (
                    not access_ends_at
                    or datetime.fromisoformat(access_ends_at)
                    <= datetime.now(timezone.utc)
                ):
                    access_active = False
            if subscription["payment_waived"]:
                access_type = "complimentary"
                access_ends_at = subscription["waiver_expires_at"]
                if (
                    not access_ends_at
                    or datetime.fromisoformat(access_ends_at)
                    <= datetime.now(timezone.utc)
                ):
                    access_active = False
        enabled_addons = {row["addon_code"] for row in rows}
        trial_modules = {
            "xmltv_validator",
            "prelogs",
            "hls_validator",
        }
        modules = {}
        for code, definition in MODULE_CATALOG.items():
            source = definition["source"]
            if subscription and subscription["status"] == "trialing":
                enabled = (
                    trial_active
                    and definition.get("available", True)
                    and code in trial_modules
                )
            else:
                enabled = (
                    access_active
                    and definition.get("available", True)
                    and (
                        source == "professional"
                        or plan == "enterprise"
                        or source in enabled_addons
                    )
                )
            modules[code] = {
                **definition,
                "enabled": enabled,
            }
        return {
            "plan": plan,
            "access": {
                "type": access_type,
                "active": access_active,
                "ends_at": access_ends_at,
                "grace_period_ends_at": (
                    subscription["grace_period_ends_at"]
                    if subscription else None
                ),
                "download_formats": (
                    ["pdf"] if subscription and subscription[
                        "status"
                    ] == "trialing" else ["xlsx", "pdf", "json", "html"]
                ),
                "watermark": bool(
                    subscription and subscription["status"] == "trialing"
                ),
            },
            "addons": [
                {
                    "code": code,
                    **ADD_ON_CATALOG[code],
                    "enabled": (
                        access_active
                        and (code in enabled_addons or plan == "enterprise")
                    ),
                }
                for code in ADD_ON_CATALOG
            ],
            "modules": modules,
        }


entitlement_store = EntitlementStore()
entitlement_store.initialize()
