"""Google Drive client using OAuth2 (drive.file scope only).

drive.file scope limits the app to files/folders it creates itself, which is
the minimum privilege needed here and keeps a leaked token from exposing the
user's entire Drive.
"""
from __future__ import annotations

import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME = "application/vnd.google-apps.folder"


class GDriveClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        self._service = build("drive", "v3", credentials=creds)
        self._folder_cache: dict[tuple[str, str | None], str] = {}

    def get_or_create_folder(self, name: str, parent_id: str | None = None) -> str:
        cache_key = (name, parent_id)
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        query = f"mimeType='{FOLDER_MIME}' and name='{_escape(name)}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"

        result = self._service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = result.get("files", [])
        if files:
            folder_id = files[0]["id"]
        else:
            metadata = {"name": name, "mimeType": FOLDER_MIME}
            if parent_id:
                metadata["parents"] = [parent_id]
            folder = self._service.files().create(body=metadata, fields="id").execute()
            folder_id = folder["id"]

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def upload_bytes(self, name: str, data: bytes, parent_id: str, mime_type: str = "application/octet-stream") -> str:
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        metadata = {"name": name, "parents": [parent_id]}
        result = self._service.files().create(body=metadata, media_body=media, fields="id").execute()
        return result["id"]

    def upload_text_as_doc(self, name: str, text: str, parent_id: str) -> str:
        """Uploads plain text and has Drive convert it into a native Google Doc."""
        media = MediaIoBaseUpload(io.BytesIO(text.encode("utf-8")), mimetype="text/plain", resumable=False)
        metadata = {"name": name, "parents": [parent_id], "mimeType": "application/vnd.google-apps.document"}
        result = self._service.files().create(body=metadata, media_body=media, fields="id").execute()
        return result["id"]

    def find_file(self, name: str, parent_id: str) -> str | None:
        query = f"name='{_escape(name)}' and '{parent_id}' in parents and trashed=false"
        result = self._service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def download_bytes(self, file_id: str) -> bytes:
        return self._service.files().get_media(fileId=file_id).execute()

    def upsert_bytes(self, name: str, data: bytes, parent_id: str, mime_type: str = "application/octet-stream") -> str:
        """Creates the file if it doesn't exist yet, otherwise overwrites its content in place."""
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        existing_id = self.find_file(name, parent_id)
        if existing_id:
            self._service.files().update(fileId=existing_id, media_body=media).execute()
            return existing_id
        metadata = {"name": name, "parents": [parent_id]}
        result = self._service.files().create(body=metadata, media_body=media, fields="id").execute()
        return result["id"]


def _escape(value: str) -> str:
    return value.replace("'", "\\'")
