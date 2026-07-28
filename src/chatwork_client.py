"""Chatwork API client for fetching rooms, messages, and files."""
from __future__ import annotations

import time
from typing import Any

import requests

API_BASE = "https://api.chatwork.com/v2"


def _rate_limit_wait_seconds(headers: dict) -> float:
    """Chatwork signals its rate-limit reset via X-RateLimit-Reset (unix
    epoch seconds), not the generic Retry-After header."""
    reset_at = headers.get("X-RateLimit-Reset")
    if reset_at is not None:
        try:
            return max(0.0, float(reset_at) - time.time())
        except ValueError:
            pass
    return 60.0


class ChatworkClient:
    def __init__(self, api_token: str):
        self._session = requests.Session()
        self._session.headers.update({"X-ChatWorkToken": api_token})

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{API_BASE}{path}"
        for attempt in range(5):
            try:
                resp = self._session.get(url, params=params, timeout=30)
            except requests.exceptions.RequestException:
                if attempt == 4:
                    raise
                time.sleep(2**attempt)
                continue
            if resp.status_code == 429:
                if attempt == 4:
                    break
                time.sleep(_rate_limit_wait_seconds(resp.headers))
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()

    def list_rooms(self) -> list[dict]:
        """Returns all rooms accessible to the token, including DMs (type=='direct')."""
        return self._get("/rooms")

    def list_messages(self, room_id: int, force: bool = True) -> list[dict]:
        """Returns up to the latest 100 messages in the room.

        force=1 always fetches the latest 100 without touching read state.
        force=0 instead returns messages since the last force=0/1 call made
        with this token and, as a side effect, marks them read - which
        would flip the unread badge on the real Chatwork account this
        token belongs to. We deliberately always pass force=1 and rely on
        last_message_id in our own state to dedupe, accepting the 100-item
        cap (see list_files docstring) rather than mutate the user's inbox.
        """
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
        """Downloads from a pre-signed URL returned by get_file_download_url.

        Uses a plain request instead of self._session: the signed URL
        already carries its own auth and is often on a different host
        (e.g. object storage), so it must never be sent the Chatwork API
        token that self._session attaches to every request.
        """
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
