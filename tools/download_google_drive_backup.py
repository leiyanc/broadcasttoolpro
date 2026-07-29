import argparse
import json
from pathlib import Path

from backend.services.google_drive_backup import google_drive_backup


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download, decrypt, and verify the latest complete "
            "Broadcast Tool Pro Google Drive backup."
        )
    )
    parser.add_argument("--destination", required=True, type=Path)
    arguments = parser.parse_args()
    result = google_drive_backup.download_latest(arguments.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
