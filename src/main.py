"""Backs up all accessible Chatwork rooms (including DMs) to Google Drive.

Incremental state (last seen message id / downloaded file ids per room) is
kept in data/state.json, which the CI workflow commits back to the repo.
Message bodies and files are never written into the git repo itself, only
uploaded to Drive.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chatwork_client import ChatworkClient
from gdrive_client import GDriveClient

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"
ROOT_FOLDER_NAME = os.environ.get("GDRIVE_ROOT_FOLDER_NAME", "ChatworkBackup")
JST = timezone(timedelta(hours=9))


def sanitize(name: str) -> str:
    name = name.strip() or "unnamed"
    return re.sub(r"[\\/:*?\"<>|]", "_", name)[:100]


def render_transcript(messages: list[dict]) -> str:
    """Renders messages as a human-readable "name: body (time)" transcript."""
    lines = []
    for m in sorted(messages, key=lambda m: int(m["message_id"])):
        ts = datetime.fromtimestamp(m["send_time"], tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
        name = m.get("account", {}).get("name", "unknown")
        lines.append(f"[{ts}] {name}: {m['body']}")
    return "\n".join(lines)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"rooms": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))


def room_folder_name(room: dict) -> str:
    label = room.get("name") or room.get("type")
    return sanitize(f"{label}_{room['type']}_{room['room_id']}")


def backup_room(cw: ChatworkClient, gd: GDriveClient, root_id: str, room: dict, room_state: dict) -> dict:
    room_id = room["room_id"]
    folder_id = gd.get_or_create_folder(room_folder_name(room), parent_id=root_id)

    # --- messages ---
    # The Chatwork API only exposes the latest 100 messages per room, with
    # no way to page further back. If more than 100 arrive between two
    # backup runs, the excess older ones are unrecoverable via this API -
    # warn loudly rather than silently advancing past them.
    last_message_id = int(room_state.get("last_message_id", 0))
    messages = cw.list_messages(room_id, force=True)
    new_messages = [m for m in messages if int(m["message_id"]) > last_message_id]
    if len(messages) >= 100:
        print(
            f"  [{room_id}] WARNING: API returned the max 100 messages; "
            "older unseen messages may have been skipped (including on this "
            "first run, if the room has more history than that). Run backups more often.",
            file=sys.stderr,
        )
    if new_messages:
        messages_folder_id = gd.get_or_create_folder("messages", parent_id=folder_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = json.dumps(new_messages, ensure_ascii=False, indent=2).encode("utf-8")
        gd.upload_bytes(f"messages_{ts}.json", payload, messages_folder_id, "application/json")
        gd.upload_text_as_doc(f"messages_{ts}", render_transcript(new_messages), messages_folder_id)
        room_state["last_message_id"] = str(max(int(m["message_id"]) for m in new_messages))
        print(f"  [{room_id}] +{len(new_messages)} messages")

    # --- files ---
    # Same caveat as messages: /files has no pagination, so only the latest
    # 100 files are visible per run.
    downloaded = set(room_state.get("downloaded_file_ids", []))
    files = cw.list_files(room_id)
    if len(files) >= 100:
        print(
            f"  [{room_id}] WARNING: API returned the max 100 files; "
            "older unseen files may have been skipped (including on this "
            "first run, if the room has more files than that). Run backups more often.",
            file=sys.stderr,
        )
    new_downloads = []
    for f in files:
        file_id = str(f["file_id"])
        if file_id in downloaded:
            continue
        try:
            url = cw.get_file_download_url(room_id, f["file_id"])
            content = cw.download_file(url)
        except Exception as exc:  # noqa: BLE001 - keep backup running on single-file failure
            print(f"  [{room_id}] failed to download file {file_id}: {exc}", file=sys.stderr)
            continue
        files_folder_id = gd.get_or_create_folder("files", parent_id=folder_id)
        gd.upload_bytes(f"{file_id}_{sanitize(f['filename'])}", content, files_folder_id)
        downloaded.add(file_id)
        new_downloads.append(file_id)
        time.sleep(0.5)  # be gentle with rate limits
    if new_downloads:
        room_state["downloaded_file_ids"] = sorted(downloaded)
        print(f"  [{room_id}] +{len(new_downloads)} files")

    return room_state


def main() -> None:
    api_token = os.environ["CHATWORK_API_TOKEN"]
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    refresh_token = os.environ["GOOGLE_REFRESH_TOKEN"]

    cw = ChatworkClient(api_token)
    gd = GDriveClient(client_id, client_secret, refresh_token)

    state = load_state()
    root_id = gd.get_or_create_folder(ROOT_FOLDER_NAME)

    rooms = cw.list_rooms()
    print(f"found {len(rooms)} accessible rooms (including DMs)")

    for room in rooms:
        room_id = str(room["room_id"])
        room_state = state["rooms"].get(room_id, {})
        state["rooms"][room_id] = backup_room(cw, gd, root_id, room, room_state)
        save_state(state)  # persist incrementally so a mid-run failure doesn't lose progress


if __name__ == "__main__":
    main()
