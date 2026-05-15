"""Google Drive service account client helpers."""

import json
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service(settings: Settings) -> Any:
    """Create and return an authenticated Google Drive API service client."""

    try:
        sa_info = json.loads(settings.google_sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=SCOPES,
        )
        return build("drive", "v3", credentials=credentials)
    except Exception as exc:  # pragma: no cover - external credential parsing path
        raise RuntimeError(f"Failed to initialise Drive service: {exc}") from exc


def list_files(service: Any, folder_id: str, q: str = "", page_size: int = 20) -> list[dict]:
    """List files from a Drive folder with an optional extra query filter."""

    base = f"'{folder_id}' in parents and trashed = false"
    final_q = f"{base} and {q}" if q else base

    try:
        result = (
            service.files()
            .list(
                q=final_q,
                pageSize=page_size,
                fields="files(id, name, mimeType, modifiedTime, webViewLink, parents)",
                supportsAllDrives=False,
                includeItemsFromAllDrives=False,
            )
            .execute()
        )
        return result.get("files", [])
    except HttpError as exc:  # pragma: no cover - depends on external API failure path
        raise RuntimeError(f"Drive API error: {exc}") from exc
