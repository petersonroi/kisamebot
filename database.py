import sqlite3
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Database file path (relative to project root)
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_data", "conversations.db")


def _ensure_dir() -> None:
    """Make sure the data directory exists."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                role       TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content    TEXT NOT NULL,
                model      TEXT,
                tokens     INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id, created_at);

            CREATE TABLE IF NOT EXISTS bot_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id     INTEGER NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                updated_at  TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            """
        )
        conn.commit()
        logger.info("Database initialized successfully.")
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  User Operations
# ──────────────────────────────────────────────
def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    """Insert or update a user record."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                last_active = datetime('now')
            """,
            (user_id, username, first_name),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Conversation Operations
# ──────────────────────────────────────────────
def save_message(
    user_id: int,
    role: str,
    content: str,
    model: str | None = None,
    tokens: int = 0,
) -> None:
    """Save a single message to the conversation history."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO conversations (user_id, role, content, model, tokens)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, role, content, model, tokens),
        )
        conn.commit()
    finally:
        conn.close()


def load_messages(
    user_id: int, limit: int = 20
) -> list[dict[str, Any]]:
    """Load the most recent messages for a user (newest last)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT role, content
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        # Reverse so oldest-first order is preserved
        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]
    finally:
        conn.close()


def clear_messages(user_id: int) -> None:
    """Delete all conversation messages for a user."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM conversations WHERE user_id = ?", (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_message_count(user_id: int) -> int:
    """Return total number of stored messages for a user."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Bot Settings Operations
# ──────────────────────────────────────────────
def get_setting(key: str, default: str | None = None) -> str | None:
    """Read a setting from the bot_settings table."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    """Write or update a setting in the bot_settings table."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO bot_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Per-User Settings Operations
# ──────────────────────────────────────────────
def get_user_setting(user_id: int, key: str, default: str | None = None) -> str | None:
    """Read a per-user setting from user_settings."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_user_setting(user_id: int, key: str, value: str) -> None:
    """Write or update a per-user setting."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
            """,
            (user_id, key, value),
        )
        conn.commit()
    finally:
        conn.close()


def delete_user_setting(user_id: int, key: str) -> bool:
    """Delete a per-user setting. Returns True if a row was deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM user_settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_all_user_settings(user_id: int) -> dict[str, str]:
    """Return all settings for a user as a dict."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT key, value FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Per-User System Prompt Helpers
# ──────────────────────────────────────────────
USER_PROMPT_KEY = "system_prompt"


def get_user_system_prompt(user_id: int) -> str | None:
    """Get a user's custom system prompt, or None if using the default."""
    return get_user_setting(user_id, USER_PROMPT_KEY)


def set_user_system_prompt(user_id: int, prompt: str) -> None:
    """Set a user's custom system prompt."""
    set_user_setting(user_id, USER_PROMPT_KEY, prompt)


def clear_user_system_prompt(user_id: int) -> bool:
    """Remove a user's custom system prompt (reverts to global default)."""
    return delete_user_setting(user_id, USER_PROMPT_KEY)


# ──────────────────────────────────────────────
#  Export Operations
# ──────────────────────────────────────────────
def export_user_conversation(user_id: int) -> list[dict[str, Any]]:
    """Load ALL messages for a user with full metadata, ordered oldest-first.

    Returns a list of dicts with: id, role, content, model, tokens, created_at.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, role, content, model, tokens, created_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (user_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "model": row["model"],
                "tokens": row["tokens"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def export_user_data(user_id: int) -> dict[str, Any]:
    """Export all data for a user: profile, settings, and full conversation.

    Returns a dict structured for JSON serialization.
    """
    conn = get_connection()
    try:
        # User profile
        user_row = conn.execute(
            "SELECT user_id, username, first_name, created_at, last_active FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        user_info = dict(user_row) if user_row else {"user_id": user_id}

        # User settings
        settings_rows = conn.execute(
            "SELECT key, value, updated_at FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        user_settings = [
            {"key": row["key"], "value": row["value"], "updated_at": row["updated_at"]}
            for row in settings_rows
        ]

        # Full conversation
        conversation = export_user_conversation(user_id)

        return {
            "user": user_info,
            "settings": user_settings,
            "conversation": conversation,
            "total_messages": len(conversation),
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Aggregate Analytics (for admin reports)
# ──────────────────────────────────────────────
def get_global_stats() -> dict[str, Any]:
    """Return high-level aggregate stats across all users."""
    conn = get_connection()
    try:
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        total_messages = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
        total_tokens = conn.execute(
            "SELECT COALESCE(SUM(tokens), 0) as s FROM conversations"
        ).fetchone()["s"]
        total_with_custom_prompt = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM user_settings WHERE key = ?",
            (USER_PROMPT_KEY,),
        ).fetchone()["c"]

        # Date range of activity
        first_msg = conn.execute(
            "SELECT MIN(created_at) as d FROM conversations"
        ).fetchone()["d"]
        last_msg = conn.execute(
            "SELECT MAX(created_at) as d FROM conversations"
        ).fetchone()["d"]

        return {
            "total_users": total_users,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "users_with_custom_prompt": total_with_custom_prompt,
            "first_message": first_msg,
            "last_message": last_msg,
        }
    finally:
        conn.close()


def get_top_users(limit: int = 10) -> list[dict[str, Any]]:
    """Return the top users by message count."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.first_name,
                COUNT(c.id) as message_count,
                COALESCE(SUM(c.tokens), 0) as total_tokens,
                MAX(c.created_at) as last_message_at
            FROM users u
            LEFT JOIN conversations c ON u.user_id = c.user_id
            GROUP BY u.user_id
            ORDER BY message_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "message_count": row["message_count"],
                "total_tokens": row["total_tokens"],
                "last_message_at": row["last_message_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_daily_activity(days: int = 7) -> list[dict[str, Any]]:
    """Return daily message counts for the last N days."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                DATE(created_at) as day,
                COUNT(*) as message_count,
                COUNT(CASE WHEN role = 'user' THEN 1 END) as user_msgs,
                COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_msgs,
                COALESCE(SUM(tokens), 0) as total_tokens
            FROM conversations
            WHERE created_at >= datetime('now', ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            """,
            (str(-days),),
        ).fetchall()
        return [
            {
                "date": row["day"],
                "total_messages": row["message_count"],
                "user_messages": row["user_msgs"],
                "assistant_messages": row["assistant_msgs"],
                "total_tokens": row["total_tokens"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_model_usage() -> list[dict[str, Any]]:
    """Return message and token counts broken down by AI model."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                model,
                COUNT(*) as message_count,
                COALESCE(SUM(tokens), 0) as total_tokens
            FROM conversations
            WHERE model IS NOT NULL
            GROUP BY model
            ORDER BY message_count DESC
            """
        ).fetchall()
        return [
            {
                "model": row["model"],
                "message_count": row["message_count"],
                "total_tokens": row["total_tokens"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_hourly_distribution() -> list[dict[str, Any]]:
    """Return message counts grouped by hour of day (0-23)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                COUNT(*) as message_count
            FROM conversations
            GROUP BY hour
            ORDER BY hour
            """
        ).fetchall()
        return [
            {"hour": row["hour"], "message_count": row["message_count"]}
            for row in rows
        ]
    finally:
        conn.close()
