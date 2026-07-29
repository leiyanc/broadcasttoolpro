import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import InstalledAppFlow

from backend.services.google_drive_backup import (
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_KEY_PATH,
    DEFAULT_TOKEN_PATH,
    DRIVE_SCOPE,
)


CLIENT_PATH = (
    DEFAULT_CONFIG_DIRECTORY / "google-drive-oauth-client.json"
)


def main() -> None:
    if not CLIENT_PATH.is_file():
        raise FileNotFoundError(
            f"OAuth client file not found at {CLIENT_PATH}."
        )
    DEFAULT_CONFIG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG_DIRECTORY.chmod(0o700)
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_PATH,
        [DRIVE_SCOPE],
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message=(
            "Authorize Broadcast Tool Pro in the browser window."
        ),
        success_message=(
            "Broadcast Tool Pro Google Drive authorization completed. "
            "You may close this window."
        ),
        open_browser=True,
    )
    DEFAULT_TOKEN_PATH.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )
    DEFAULT_TOKEN_PATH.chmod(0o600)
    if not DEFAULT_KEY_PATH.exists():
        DEFAULT_KEY_PATH.write_bytes(Fernet.generate_key())
        DEFAULT_KEY_PATH.chmod(0o600)
    print(json.dumps({
        "authorized": True,
        "scope": DRIVE_SCOPE,
        "token_path": str(DEFAULT_TOKEN_PATH),
        "encryption_key_created": DEFAULT_KEY_PATH.is_file(),
    }, indent=2))


if __name__ == "__main__":
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "0")
    main()
