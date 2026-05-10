from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def build_drive_service() -> Any:
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_json:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=SCOPES,
        )
    elif credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )
    else:
        raise RuntimeError(
            "Set GOOGLE_SERVICE_ACCOUNT_INFO or GOOGLE_APPLICATION_CREDENTIALS for Google Drive upload."
        )

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _query_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def file_exists(service: Any, folder_id: str, filename: str) -> bool:
    query = (
        f"name = {_query_literal(filename)} and "
        f"{_query_literal(folder_id)} in parents and trashed = false"
    )
    response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=1,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    return bool(response.get("files"))


def upload_markdown(service: Any, folder_id: str, path: Path) -> str:
    metadata = {
        "name": path.name,
        "parents": [folder_id],
        "mimeType": "text/markdown",
    }
    media = MediaFileUpload(str(path), mimetype="text/markdown", resumable=False)
    uploaded = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    return str(uploaded.get("webViewLink") or uploaded.get("id"))

