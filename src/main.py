"""Backs up all accessible Chatwork rooms (including DMs) to Google Drive.

Incremental state (last seen message id / downloaded file ids per room) is
kept as state.json inside the ChatworkBackup folder on Drive itself - not in
this git repo. This repo is public, so nothing that could reveal which
rooms exist or how much traffic they see (room ids, message/file counts,
per-room log lines) is written to git or to the GitHub Actions log; only an
aggregate total across all rooms is printed.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

from chatwork_client import ChatworkClient
from gdrive_client import GDriveClient

ROOT_FOLDER_NAME = os.environ.get("GDRIVE_ROOT_FOLDER_NAME", "ChatworkBackup")
STATE_FILE_NAME = "state.json"
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


def load_state(gd: GDriveClient, root_id: str) -> dict:
    file_id = gd.find_file(STATE_FILE_NAME, root_id)
    if not file_id:
        return {"rooms": {}}
    return json.loads(gd.download_bytes(file_id).decode("utf-8"))


def save_state(gd: GDriveClient, root_id: str, state: dict) -> None:
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    gd.upsert_bytes(STATE_FILE_NAME, payload, root_id, "application/json")


def room_folder_name(room: dict) -> str:
    label = room.get("name") or room.get("type")
    return sanitize(f"{label}_{room['type']}_{room['room_id']}")


def backup_room(cw: ChatworkClient, gd: GDriveClient, root_id: str, room: dict, room_state: dict) -> tuple[dict, dict]:
    """Returns (updated_room_state, stats). stats never contains the room id/name."""
    room_id = room["room_id"]
    folder_id = gd.get_or_create_folder(room_folder_name(room), parent_id=root_id)
    stats = {"new_messages": 0, "new_files": 0, "message_cap_hit": False, "file_cap_hit": False, "file_errors": 0}

    # --- messages ---
    # The Chatwork API only exposes the latest 100 messages per room, with
    # no way to page further back. If more than 100 arrive between two
    # backup runs (or a room has more than 100 messages of history on its
    # first run), the excess older ones are unrecoverable via this API.
    last_message_id = int(room_state.get("last_message_id", 0))
    messages = cw.list_messages(room_id, force=True)
    new_messages = [m for m in messages if int(m["message_id"]) > last_message_id]
    stats["message_cap_hit"] = len(messages) >= 100
    if new_messages:
        messages_folder_id = gd.get_or_create_folder("messages", parent_id=folder_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = json.dumps(new_messages, ensure_ascii=False, indent=2).encode("utf-8")
        gd.upload_bytes(f"messages_{ts}.json", payload, messages_folder_id, "application/json")
        gd.upload_text_as_doc(f"messages_{ts}", render_transcript(new_messages), messages_folder_id)
        room_state["last_message_id"] = str(max(int(m["message_id"]) for m in new_messages))
        stats["new_messages"] = len(new_messages)

    # --- files ---
    # Same caveat as messages: /files has no pagination, so only the latest
    # 100 files are visible per run.
    downloaded = set(room_state.get("downloaded_file_ids", []))
    files = cw.list_files(room_id)
    stats["file_cap_hit"] = len(files) >= 100
    new_downloads = []
    for f in files:
        file_id = str(f["file_id"])
        if file_id in downloaded:
            continue
        try:
            url = cw.get_file_download_url(room_id, f["file_id"])
            content = cw.download_file(url)
        except Exception as exc:  # noqa: BLE001 - keep backup running on single-file failure
            # Only the exception type is logged: the message can embed the
            # file's signed download URL, which must not land in a public log.
            stats["file_errors"] += 1
            print(f"file download failed: {type(exc).__name__}")
            continue
        files_folder_id = gd.get_or_create_folder("files", parent_id=folder_id)
        gd.upload_bytes(f"{file_id}_{sanitize(f['filename'])}", content, files_folder_id)
        downloaded.add(file_id)
        new_downloads.append(file_id)
        time.sleep(0.5)  # be gentle with rate limits
    if new_downloads:
        room_state["downloaded_file_ids"] = sorted(downloaded)
        stats["new_files"] = len(new_downloads)

    return room_state, stats


def main() -> None:
    api_token = os.environ["CHATWORK_API_TOKEN"]
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    refresh_token = os.environ["GOOGLE_REFRESH_TOKEN"]

    cw = ChatworkClient(api_token)
    gd = GDriveClient(client_id, client_secret, refresh_token)

    root_id = gd.get_or_create_folder(ROOT_FOLDER_NAME)
    state = load_state(gd, root_id)

    rooms = cw.list_rooms()
    totals = {"new_messages": 0, "new_files": 0, "message_cap_hit": 0, "file_cap_hit": 0, "file_errors": 0}

    for room in rooms:
        room_id = str(room["room_id"])
        room_state = state["rooms"].get(room_id, {})
        state["rooms"][room_id], stats = backup_room(cw, gd, root_id, room, room_state)
        save_state(gd, root_id, state)  # persist incrementally so a mid-run failure doesn't lose progress

        totals["new_messages"] += stats["new_messages"]
        totals["new_files"] += stats["new_files"]
        totals["file_errors"] += stats["file_errors"]
        totals["message_cap_hit"] += int(stats["message_cap_hit"])
        totals["file_cap_hit"] += int(stats["file_cap_hit"])

    # Deliberately aggregate-only: this log is public (public repo => public
    # Actions logs), so no room id, room name, or per-room breakdown here.
    print(
        f"backed up {len(rooms)} rooms: +{totals['new_messages']} messages, "
        f"+{totals['new_files']} files, {totals['file_errors']} file errors"
    )
    if totals["message_cap_hit"]:
        print(
            f"WARNING: {totals['message_cap_hit']} room(s) hit the 100-message API cap; "
            "some older messages may have been skipped. Run backups more often."
        )
    if totals["file_cap_hit"]:
        print(
            f"WARNING: {totals['file_cap_hit']} room(s) hit the 100-file API cap; "
            "some older files may have been skipped. Run backups more often."
        )


if __name__ == "__main__":
    main()
