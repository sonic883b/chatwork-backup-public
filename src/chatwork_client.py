"""Chatwork API client for fetching rooms, messages, and files."""
from __future__ import annotations

import time
from typing import Any

import requests

API_BASE = "https://api.chatwork.com/v2"


class ChatworkClient:
    def __init__(self, api_token: str):
        self._session = requests.Session()
        self._session.headers.update({"X-ChatWorkToken": api_token})

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{API_BASE}{path}"
        for attempt in range(5):
            resp = self._session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()

    def list_rooms(self) -> list[dict]:
        """Returns all rooms accessible to the token, including DMs (type=='direct')."""
        return self._get("/rooms")

    def list_messages(self, room_id: int, force: bool = True) -> list[dict]:
        """Returns up to the latest 100 messages in the room."""
        params = {"force": 1 if force else 0}
        result = self._get(f"/rooms/{room_id}/messages", params=params)
        return result or []

    def list_files(self, room_id: int) -> list[dict]:
        """Returns up to the latest 100 files in the room.

        The Chatwork API's /files endpoint only accepts an optional
        account_id filter — there is no offset/page parameter, so results
        beyond the newest 100 are not retrievable via this endpoint.
        """
        return self._get(f"/rooms/{room_id}/files") or []

    def get_file_download_url(self, room_id: int, file_id: int) -> str:
        result = self._get(f"/rooms/{room_id}/files/{file_id}", params={"create_download_url": 1})
        return result["download_url"]

    def download_file(self, url: str) -> bytes:
        resp = self._session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
