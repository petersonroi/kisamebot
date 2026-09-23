import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration for the AI Telegram Bot.

    Timezone note
    -------------
    All timestamps stored in the SQLite database use UTC
    (`datetime('now')` → UTC).  Export and report modules also use
    `datetime.now(timezone.utc)` for generated_at / exported_at fields.
    The hourly distribution chart in admin reports is in UTC.
    If you need local-time display, convert on the client side.
    """

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # AI backend (OpenAI-compatible HTTP endpoint)
    # Point AI_API_BASE at any provider that speaks the OpenAI
    # /chat/completions protocol (local model server, gateway, etc.).
    AI_API_BASE: str = os.getenv("AI_API_BASE", "http://localhost:11434/v1")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "llama3")
    AI_TIMEOUT: float = float(os.getenv("AI_TIMEOUT", "60"))
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        "You are a helpful, friendly, and knowledgeable AI assistant."
    )
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # Webhook (leave WEBHOOK_URL empty to fall back to polling mode)
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_LISTEN: str = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))
    # URL path Telegram posts updates to; defaults to the bot token for secrecy.
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "")
    # Optional secret token Telegram echoes back in a header for verification.
    WEBHOOK_SECRET_TOKEN: str = os.getenv("WEBHOOK_SECRET_TOKEN", "")

    # Health check (only started in webhook mode). Exposes GET /health.
    HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8081"))

    # Access control
    ALLOWED_USERS: list[int] = [
        int(uid.strip())
        for uid in os.getenv("ALLOWED_USERS", "").split(",")
        if uid.strip().isdigit()
    ]

    # Admin users (first in ALLOWED_USERS is admin by default, or set explicitly)
    ADMIN_USERS: list[int] = [
        int(uid.strip())
        for uid in os.getenv("ADMIN_USERS", "").split(",")
        if uid.strip().isdigit()
    ]

    # Conversation
    MAX_HISTORY: int = 20  # Max messages kept per conversation

    @classmethod
    def validate(cls) -> None:
        """Validate that required config values are set."""
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.AI_API_BASE:
            missing.append("AI_API_BASE")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please set them in your .env file."
            )
