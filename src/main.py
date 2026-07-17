"""Backs up all accessible Chatwork rooms (including DMs) to Google Drive.

Incremental state (last seen message id / downloaded file ids per room) is
kept as state.json inside the ChatworkBackup folder on Drive itself - not in
this git repo. This repo is meant to run private, but as defense in depth
against future visibility/collaborator misconfiguration, nothing that could
reveal which rooms exist or how much traffic they see (room ids,
message/file counts, per-room log lines) is written to git or to the
GitHub Actions log; only an aggregate total across all rooms is printed.
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


def backup_room(cw: ChatworkClient, gd: GDriveClient, root_id: str, room: dict, state: dict) -> dict:
    """Mutates state["rooms"][room_id] in place. Returns stats (never contains the room id/name).

    state.json is saved to Drive immediately after each successful upload
    (not just once at the end) so that a crash mid-room can't leave a Drive
    upload without its corresponding state update - which would otherwise
    cause the same message batch or file to be re-uploaded as a duplicate
    on the next run.
    """
    room_id = room["room_id"]
    room_state = state["rooms"].setdefault(str(room_id), {})
    folder_id = gd.get_or_create_folder(room_folder_name(room), parent_id=root_id)
    stats = {
        "new_messages": 0, "new_files": 0, "message_cap_hit": False, "file_cap_hit": False,
        "file_errors": 0, "message_errors": 0,
    }

    # --- messages ---
    # The Chatwork API only exposes the latest 100 messages per room, with
    # no way to page further back. cap_hit only fires when every message in
    # this batch is new (no overlap with what we'd already synced) - that's
    # the actual signal that something beyond the 100-item window may have
    # been missed, rather than just "the room happens to be busy".
    last_message_id = int(room_state.get("last_message_id", 0))
    messages = cw.list_messages(room_id, force=True)
    new_messages = [m for m in messages if int(m["message_id"]) > last_message_id]
    stats["message_cap_hit"] = len(messages) >= 100 and len(new_messages) == len(messages)
    if new_messages:
        try:
            messages_folder_id = gd.get_or_create_folder("messages", parent_id=folder_id)
            # Named after only the lower bound of the batch (the first
            # message past the still-unadvanced cursor), which stays the
            # same across retries even if more messages arrive in the
            # meantime - unlike a range that includes max(ids), which
            # would shift and produce a second, differently-named
            # duplicate. Upserting (not skip-if-exists) means a retry
            # always overwrites with the current full batch, so any
            # messages that arrived during a partial-failure retry are
            # still captured under the same artifact names.
            ids = [int(m["message_id"]) for m in new_messages]
            batch_id = str(min(ids))
            json_name, doc_name = f"messages_{batch_id}.json", f"messages_{batch_id}"
            payload = json.dumps(new_messages, ensure_ascii=False, indent=2).encode("utf-8")
            gd.upsert_bytes(json_name, payload, messages_folder_id, "application/json")
            gd.upsert_text_as_doc(doc_name, render_transcript(new_messages), messages_folder_id)
        except Exception as exc:  # noqa: BLE001 - keep backup running on single-room failure
            stats["message_errors"] = 1
            print(f"message upload failed: {type(exc).__name__}")
        else:
            # Only advance the cursor once every write for this batch
            # succeeded, so a partial failure gets retried next run
            # instead of silently losing the un-uploaded messages.
            room_state["last_message_id"] = str(max(int(m["message_id"]) for m in new_messages))
            save_state(gd, root_id, state)
            stats["new_messages"] = len(new_messages)

    # --- files ---
    # Same caveat as messages: /files has no pagination, so only the latest
    # 100 files are visible per run. Same cap_hit refinement: only a real
    # signal when none of the returned files were already known.
    downloaded = set(room_state.get("downloaded_file_ids", []))
    files = cw.list_files(room_id)
    already_known = sum(1 for f in files if str(f["file_id"]) in downloaded)
    stats["file_cap_hit"] = len(files) >= 100 and already_known == 0
    files_folder_id = None
    for f in files:
        file_id = str(f["file_id"])
        if file_id in downloaded:
            continue
        try:
            url = cw.get_file_download_url(room_id, f["file_id"])
            content = cw.download_file(url)
            if files_folder_id is None:
                files_folder_id = gd.get_or_create_folder("files", parent_id=folder_id)
            gd.upload_bytes(f"{file_id}_{sanitize(f['filename'])}", content, files_folder_id)
        except Exception as exc:  # noqa: BLE001 - keep backup running on single-file failure
            # Only the exception type is logged: the message can embed the
            # file's signed download URL, which must not land in a public log.
            stats["file_errors"] += 1
            print(f"file download failed: {type(exc).__name__}")
            continue
        downloaded.add(file_id)
        room_state["downloaded_file_ids"] = sorted(downloaded)
        save_state(gd, root_id, state)
        stats["new_files"] += 1
        time.sleep(0.5)  # be gentle with rate limits

    return stats


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
    totals = {
        "new_messages": 0, "new_files": 0, "message_cap_hit": 0, "file_cap_hit": 0,
        "file_errors": 0, "message_errors": 0, "room_errors": 0,
    }

    for room in rooms:
        try:
            stats = backup_room(cw, gd, root_id, room, state)  # saves state internally after each upload
        except Exception as exc:  # noqa: BLE001 - one room's failure shouldn't abort the whole run
            totals["room_errors"] += 1
            print(f"room backup failed: {type(exc).__name__}")
            continue

        totals["new_messages"] += stats["new_messages"]
        totals["new_files"] += stats["new_files"]
        totals["file_errors"] += stats["file_errors"]
        totals["message_errors"] += stats["message_errors"]
        totals["message_cap_hit"] += int(stats["message_cap_hit"])
        totals["file_cap_hit"] += int(stats["file_cap_hit"])

    # Deliberately aggregate-only: no room id, room name, or per-room
    # breakdown here - see the module docstring for why.
    print(
        f"backed up {len(rooms)} rooms: +{totals['new_messages']} messages, "
        f"+{totals['new_files']} files, {totals['file_errors']} file errors, "
        f"{totals['message_errors']} message-upload errors, {totals['room_errors']} room errors"
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
