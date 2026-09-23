import threading
from typing import Any

from config import Config
import database


class ConversationManager:
    """Manages conversation history per user with SQLite persistence.

    • On startup, history is loaded from the database.
    • Every new message is persisted immediately.
    • Clearing history deletes it from the database.
    • Each user can have a custom system prompt stored in the DB.
    • Thread-safe: a lock guards the in-memory cache to prevent
      race conditions when multiple updates arrive concurrently.
    """

    def __init__(self, max_history: int = Config.MAX_HISTORY) -> None:
        self._max_history = max_history
        # In-memory cache: user_id -> list of messages
        self._cache: dict[int, list[dict[str, Any]]] = {}
        # FIX: Concurrency guard — lock protects _cache mutations
        self._lock = threading.Lock()

    def _get_system_prompt(self, user_id: int) -> str:
        """Return the user's custom system prompt, or the global default."""
        custom = database.get_user_system_prompt(user_id)
        return custom if custom else Config.SYSTEM_PROMPT

    def get_messages(self, user_id: int) -> list[dict[str, Any]]:
        """Return the full message list for a user (system prompt + history)."""
        with self._lock:
            if user_id not in self._cache:
                self._cache[user_id] = database.load_messages(user_id, self._max_history)
            messages = list(self._cache[user_id])  # return a copy
        return [
            {"role": "system", "content": self._get_system_prompt(user_id)},
            *messages,
        ]

    def add_user_message(self, user_id: int, text: str) -> None:
        """Add a user message to cache and persist it to the database."""
        with self._lock:
            if user_id not in self._cache:
                self._cache[user_id] = database.load_messages(user_id, self._max_history)

            self._cache[user_id].append({"role": "user", "content": text})
            database.save_message(user_id, "user", text)
            self._trim(user_id)

    def add_assistant_message(
        self, user_id: int, text: str, model: str | None = None, tokens: int = 0
    ) -> None:
        """Add an assistant message to cache and persist it to the database."""
        with self._lock:
            if user_id not in self._cache:
                self._cache[user_id] = database.load_messages(user_id, self._max_history)

            self._cache[user_id].append({"role": "assistant", "content": text})
            database.save_message(user_id, "assistant", text, model=model, tokens=tokens)
            self._trim(user_id)

    def clear(self, user_id: int) -> None:
        """Clear conversation history — both cache and database."""
        with self._lock:
            self._cache.pop(user_id, None)
            database.clear_messages(user_id)

    def get_message_count(self, user_id: int) -> int:
        """Return total stored messages for a user."""
        return database.get_message_count(user_id)

    def get_custom_prompt(self, user_id: int) -> str | None:
        """Return the user's custom system prompt, or None if using default."""
        return database.get_user_system_prompt(user_id)

    def set_custom_prompt(self, user_id: int, prompt: str) -> None:
        """Set a custom system prompt for this user."""
        database.set_user_system_prompt(user_id, prompt)

    def reset_custom_prompt(self, user_id: int) -> bool:
        """Remove the user's custom prompt, reverting to global default."""
        return database.clear_user_system_prompt(user_id)

    def _trim(self, user_id: int) -> None:
        """Trim in-memory cache to max_history (doesn't delete from DB)."""
        # Called under self._lock — no need to re-acquire
        history = self._cache[user_id]
        if len(history) > self._max_history:
            self._cache[user_id] = history[-self._max_history :]
