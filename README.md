# 🤖 AI-Powered Telegram Chatbot

A ready-to-use template for building an AI-powered Telegram chatbot with a provider-agnostic AI backend (any OpenAI-compatible endpoint — local models via Ollama/LM Studio/vLLM, gateways, or the OpenAI cloud API), persistent conversation memory (SQLite), per-user custom personalities, and access control. Supports both **polling** and **webhook** modes.

## ✨ Features

- 🧠 **AI Chat** — Works with any OpenAI-compatible endpoint (local or cloud)
- 💬 **Persistent Memory** — SQLite database stores conversations across bot restarts
- 🎭 **Custom Personalities** — Each user can set their own system prompt/personality
- 📦 **Conversation Export** — Download chat history as JSON via `/export`
- 👤 **User Tracking** — Stores user info and chat statistics
- 🔒 **Access Control** — Restrict bot to specific Telegram user IDs
- 📊 **Admin Reports** — Detailed analytics via `/report` (admin-only)
- 🧹 **Clear History** — Reset conversation with `/clear`
- 📊 **Chat Stats** — View message counts with `/stats`
- ⚙️ **Configurable** — Model, temperature, tokens all adjustable via `.env`
- 📦 **Clean Architecture** — Modular code, easy to extend

## 📂 Project Structure

```
ai_telegram_bot/
├── bot.py              # Main bot logic & handlers
├── ai_client.py        # AI backend wrapper (OpenAI-compatible HTTP)
├── conversation.py     # Conversation manager (DB + per-user prompts)
├── database.py         # SQLite database layer
├── report.py           # Admin analytics report generator
├── export.py           # Conversation export to JSON
├── config.py           # Configuration from .env
├── .env.example        # Template for environment variables
├── .gitignore          # Protects secrets & database
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── bot_data/           # Auto-created at runtime
    └── conversations.db  # SQLite database
```

## 🗄️ Database Schema

The bot automatically creates a SQLite database (`bot_data/conversations.db`) with four tables:

### `users`
Stores user information.
| Column | Type | Description |
|---|---|---|
| user_id | INTEGER (PK) | Telegram user ID |
| username | TEXT | Telegram username |
| first_name | TEXT | Display name |
| created_at | TEXT | First seen timestamp |
| last_active | TEXT | Last activity timestamp |

### `conversations`
Stores all chat messages.
| Column | Type | Description |
|---|---|---|
| id | INTEGER (PK) | Auto-increment ID |
| user_id | INTEGER (FK) | Reference to users table |
| role | TEXT | `user`, `assistant`, or `system` |
| content | TEXT | Message text |
| model | TEXT | AI model used (for assistant msgs) |
| tokens | INTEGER | Token count for AI responses |
| created_at | TEXT | Timestamp |

### `bot_settings`
Global key-value store for bot configuration.
| Column | Type | Description |
|---|---|---|
| key | TEXT (PK) | Setting name |
| value | TEXT | Setting value |

### `user_settings`
Per-user key-value store (includes custom system prompts).
| Column | Type | Description |
|---|---|---|
| user_id | INTEGER (FK) | Reference to users table |
| key | TEXT | Setting name (e.g. `system_prompt`) |
| value | TEXT | Setting value |
| updated_at | TEXT | Last modified timestamp |
| *(PK)* | | `(user_id, key)` |

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An AI backend that exposes an OpenAI-compatible `/chat/completions` endpoint
  (e.g. [Ollama](https://ollama.com), LM Studio, vLLM, or the OpenAI cloud API)

### 2. Setup

```bash
# Clone or download this template
cd ai_telegram_bot

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your tokens
```

### 3. Configure `.env`

Open the `.env` file and set:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Your bot token from BotFather |
| `AI_API_BASE` | ✅ | OpenAI-compatible base URL (e.g. `http://localhost:11434/v1`) |
| `AI_API_KEY` | ❌ | API key for the backend (empty for local servers) |
| `AI_MODEL` | ❌ | Model name (e.g. `llama3`, `gpt-4o-mini`) |
| `AI_TIMEOUT` | ❌ | Request timeout in seconds (default: 60) |
| `SYSTEM_PROMPT` | ❌ | Default bot personality prompt |
| `MAX_TOKENS` | ❌ | Max response length (default: 1024) |
| `TEMPERATURE` | ❌ | Creativity 0.0–1.0 (default: 0.7) |
| `ALLOWED_USERS` | ❌ | Comma-separated user IDs (empty = open to all) |
| `ADMIN_USERS` | ❌ | Comma-separated admin IDs for /report access |
| `WEBHOOK_URL` | ❌ | Public HTTPS base URL — set it to enable webhook mode (empty = polling) |
| `WEBHOOK_LISTEN` | ❌ | Local bind address (default: `0.0.0.0`) |
| `WEBHOOK_PORT` | ❌ | Local port for the webhook server (default: `8443`) |
| `WEBHOOK_PATH` | ❌ | URL path Telegram posts to (defaults to the bot token) |
| `WEBHOOK_SECRET_TOKEN` | ❌ | Optional secret token for request verification |
| `HEALTH_PORT` | ❌ | Port for the `/health` check server in webhook mode (default: `8081`) |

### 4. Run the Bot

```bash
python bot.py
```

The database is **auto-created** on first run — no manual setup needed.

## 📋 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + message count |
| `/help` | List available commands |
| `/clear` | Clear conversation history |
| `/prompt` | Set a custom personality (see below) |
| `/myprompt` | View your current personality |
| `/resetprompt` | Reset to default personality |
| `/stats` | View chat statistics |
| `/export` | Export conversation messages as JSON |
| `/export full` | Full export: profile, settings, conversation, metadata |
| `/report` | Admin analytics summary *(admin-only)* |
| `/report full` | Admin analytics summary + JSON file *(admin-only)* |
| `/model` | Show current AI model |
| `/settings` | Show bot configuration |

## 🎭 Custom Personalities (Per-User System Prompts)

Each user can set their own system prompt — the bot will behave differently for each person!

### Set a custom personality
```
/prompt You are a sarcastic pirate who speaks in nautical terms
```

### View your current personality
```
/myprompt
```

### Reset to default
```
/resetprompt
```

### Example personalities
| Prompt | Behavior |
|---|---|
| `/prompt You are a witty coding tutor who explains with examples` | Helpful programming teacher |
| `/prompt You are a sarcastic pirate` | Fun, themed personality |
| `/prompt You are a friendly travel advisor who gives budget tips` | Travel planning assistant |
| `/prompt You are a concise executive assistant. Keep answers under 50 words.` | Brief, professional replies |
| `/prompt You always respond in haiku format` | Creative writing bot |

> **Note:** When you set or reset a personality, your conversation history is cleared so the new personality takes effect cleanly.

## 📦 Conversation Export

Users can download their entire chat history as a JSON file directly in Telegram.

### Export messages only (compact, OpenAI-compatible)
```
/export
```
Returns a JSON file with message objects in this format:
```json
[
  {"role": "user", "content": "Hello!", "timestamp": "2025-03-15 10:30:00"},
  {"role": "assistant", "content": "Hi there! How can I help?", "timestamp": "2025-03-15 10:30:02"}
]
```

### Full export (profile + settings + conversation + metadata)
```
/export full
```
Returns a JSON file with complete data:
```json
{
  "user": {"user_id": 123, "username": "alice", "first_name": "Alice", ...},
  "settings": [{"key": "system_prompt", "value": "You are a pirate", ...}],
  "conversation": [{"id": 1, "role": "user", "content": "...", "model": null, "tokens": 0, "created_at": "..."}, ...],
  "total_messages": 42,
  "export_metadata": {
    "exported_at": "2025-03-15T10:30:00+00:00",
    "bot_model": "gpt-4o-mini",
    "default_system_prompt": "You are a helpful assistant.",
    "max_history": 20,
    "format_version": "1.0"
  }
}
```

> The file is sent as a Telegram document attachment — easy to save, share, or re-import.

## 🔒 Restricting Access

To limit the bot to specific users:

1. Get your Telegram user ID (send `/start` to [@userinfobot](https://t.me/userinfobot))
2. Add it to `.env`:
   ```
   ALLOWED_USERS=123456789,987654321
   ```
3. Leave empty to allow everyone

## 📊 Admin Reports

The `/report` command provides bot-wide analytics (admin-only). This is useful for monitoring usage, identifying power users, and understanding traffic patterns.

### Set up admin access

1. Get your Telegram user ID (same as above)
2. Add it to `.env`:
   ```
   ADMIN_USERS=123456789
   ```
3. You can have multiple admins: `ADMIN_USERS=123456789,987654321`
4. Only admins can use `/report` — regular users get a rejection message

### View the text summary
```
/report
```
Returns an in-chat summary with:
- 🌐 Global overview (total users, messages, tokens)
- 👥 Top 10 users by message count
- 📅 Daily activity for the last 7 days
- 🧠 Model usage breakdown
- ⏰ Hourly distribution chart (UTC)

### Get the full report with JSON file
```
/report full
```
Returns the same text summary **plus** a downloadable JSON file containing all analytics data — perfect for further analysis, dashboards, or archiving.

### Sample JSON structure
```json
{
  "generated_at": "2025-03-15T10:30:00+00:00",
  "global": {
    "total_users": 42,
    "total_messages": 1234,
    "total_tokens": 567890,
    "users_with_custom_prompt": 5,
    "first_message": "2025-01-01 08:00:00",
    "last_message": "2025-03-15 10:30:00"
  },
  "top_users": [...],
  "daily_activity": [...],
  "model_usage": [...],
  "hourly_distribution": [...]
}
```

> **Tip:** Admin users should also be in `ALLOWED_USERS` if access control is enabled.

## 🗄️ Database Management

### Browse the database
```bash
sqlite3 bot_data/conversations.db

# Useful queries
SELECT * FROM users;
SELECT * FROM user_settings;
SELECT * FROM conversations WHERE user_id = 123456 ORDER BY created_at DESC LIMIT 10;
SELECT COUNT(*) FROM conversations;
```

### Backup the database
```bash
cp bot_data/conversations.db bot_data/conversations_backup.db
```

### Reset all data
```bash
rm bot_data/conversations.db
# The bot will recreate it on next start
```

## 🛠 Customization Ideas

- **Add more per-user settings** — Use the `user_settings` table for language preference, response tone, name, etc.
- **Switch models** — Set `AI_MODEL=gpt-4o` for more capable responses
- **Add image support** — Extend `chat_handler` to handle photos via OpenAI Vision API
- **Add rate limiting** — Track message counts in the DB to prevent abuse
- **Upgrade to PostgreSQL** — Swap `database.py` for an async PostgreSQL client for large-scale deployments
- **Export conversations** — Add a `/export` command to download chat history as JSON/CSV
- **Preset personalities** — Add `/persona pirate`, `/persona tutor` shortcuts for quick switching
- **Scheduled reports** — Use a task scheduler to auto-generate and send daily/weekly reports to admins

## 📝 Getting a Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name and username for your bot
4. Copy the token you receive

## ⚠️ Notes

- The bot supports both **polling** and **webhook** modes. Leave `WEBHOOK_URL`
  empty for polling; set it to your public HTTPS URL to run in webhook mode.
  Telegram requires webhooks to be served over **HTTPS** — typically via a
  reverse proxy (nginx/Caddy) terminating TLS in front of the bot.
- In webhook mode the bot also exposes a health-check endpoint at
  `GET /health` on `HEALTH_PORT` (default `8081`), returning
  `{"status": "ok", "mode": "webhook"}` with HTTP 200 — handy for load
  balancers, container orchestrators, and uptime monitors.
- Never commit your `.env` file — keep your tokens secret!
- If you use a paid cloud AI backend, monitor your usage costs.
- The `bot_data/` directory is auto-created and should be included in `.gitignore`.

### Timezone behavior

All timestamps in the database are stored in **UTC** (`datetime('now')` in SQLite).
Export files (`/export`) and admin reports (`/report`) also use UTC for `generated_at` / `exported_at` fields.
The hourly-distribution chart in `/report` is in UTC. If you need local-time display,
convert timestamps on the client side.

### Custom prompt length

The `/prompt` command limits custom personalities to **1 000 characters**.
If the input exceeds this limit, the bot will reject it and ask you to shorten it.
