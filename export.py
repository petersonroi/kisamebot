import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import database
from config import Config


# ──────────────────────────────────────────────
#  Export Formats
# ──────────────────────────────────────────────
def _build_export_data(user_id: int) -> dict[str, Any]:
    """Build the full export payload for a user."""
    data = database.export_user_data(user_id)
    # Enrich with bot-level metadata
    data["export_metadata"] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "bot_model": Config.AI_MODEL,
        "default_system_prompt": Config.SYSTEM_PROMPT,
        "max_history": Config.MAX_HISTORY,
        "format_version": "1.0",
    }
    return data


def export_to_json(user_id: int) -> tuple[str, int]:
    """Export a user's full data as a JSON string.

    Returns:
        (json_string, total_messages)
    """
    data = _build_export_data(user_id)
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    return json_str, data["total_messages"]


def export_to_file(user_id: int, export_dir: str | None = None) -> tuple[str, int]:
    """Export a user's data to a JSON file.

    Args:
        user_id: The Telegram user ID.
        export_dir: Directory to write the file. Defaults to a temp dir.

    Returns:
        (file_path, total_messages)
    """
    data = _build_export_data(user_id)
    total = data["total_messages"]

    # Determine output directory
    out_dir = export_dir or tempfile.mkdtemp(prefix="tg_export_")
    os.makedirs(out_dir, exist_ok=True)

    # Build filename: export_<user_id>_<timestamp>.json
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"export_{user_id}_{ts}.json"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath, total


def export_messages_only(user_id: int) -> tuple[str, int]:
    """Export only the conversation messages (OpenAI-compatible format).

    Returns a JSON string of message dicts with 'role' and 'content',
    plus a 'timestamp' field. Useful for importing into other tools.

    Returns:
        (json_string, total_messages)
    """
    messages = database.export_user_conversation(user_id)
    # Strip to minimal format
    minimal = [
        {"role": m["role"], "content": m["content"], "timestamp": m["created_at"]}
        for m in messages
    ]
    json_str = json.dumps(minimal, indent=2, ensure_ascii=False)
    return json_str, len(minimal)
