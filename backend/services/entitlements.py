import sqlite3
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
        "name": "Media QC Engine",
        "suite": "Streaming QC",
        "source": "enterprise",
        "available": False,
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

        plan = organization["plan"]
        enabled_addons = {row["addon_code"] for row in rows}
        modules = {}
        for code, definition in MODULE_CATALOG.items():
            source = definition["source"]
            enabled = (
                definition.get("available", True)
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
            "addons": [
                {
                    "code": code,
                    **ADD_ON_CATALOG[code],
                    "enabled": code in enabled_addons or plan == "enterprise",
                }
                for code in ADD_ON_CATALOG
            ],
            "modules": modules,
        }


entitlement_store = EntitlementStore()
entitlement_store.initialize()
