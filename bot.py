import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from ai_client import AIClient
from config import Config
from conversation import ConversationManager
import database
import export as export_module
import report as report_module
from health_server import start_health_server

# ──────────────────────────────────────────────
#  Logging Setup
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────
MAX_CUSTOM_PROMPT_LENGTH = 1000  # Max characters for a custom system prompt

# ──────────────────────────────────────────────
#  Global Instances
# ──────────────────────────────────────────────
conversation_manager = ConversationManager()
ai_client = AIClient()


# ──────────────────────────────────────────────
#  Access Control
# ──────────────────────────────────────────────
def is_allowed(user_id: int) -> bool:
    """Check if a user is allowed to interact with the bot."""
    if not Config.ALLOWED_USERS:
        return True
    return user_id in Config.ALLOWED_USERS


def is_admin(user_id: int) -> bool:
    """Check if a user is a bot admin."""
    if not Config.ADMIN_USERS:
        return False
    return user_id in Config.ADMIN_USERS


async def reject_unauthorized(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Send a rejection message if the user isn't allowed. Returns True if rejected."""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Sorry, you are not authorized to use this bot."
        )
        return True
    return False


# ──────────────────────────────────────────────
#  Command Handlers
# ──────────────────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    if await reject_unauthorized(update, context):
        return

    user = update.effective_user
    database.upsert_user(user.id, user.username, user.first_name)

    name = user.first_name or "there"
    msg_count = conversation_manager.get_message_count(user.id)

    history_note = f"\n📝 I remember {msg_count} messages from our past chats!" if msg_count else ""

    await update.message.reply_text(
        f"👋 Hello {name}! I'm your AI assistant.\n\n"
        "💬 Just send me a message and I'll respond.\n"
        "🧹 /clear — Reset our conversation\n"
        "🎭 /prompt — Set your custom personality\n"
        "👀 /myprompt — View your current personality\n"
        "🔄 /resetprompt — Reset to default personality\n"
        "📦 /export — Export your chat history\n"
        "📊 /stats — View your chat statistics\n"
        "ℹ️ /help — Show available commands\n"
        "🧠 /model — Show current AI model\n"
        "⚙️ /settings — Show bot configuration\n"
        "📊 /report — Admin analytics report *(admin only)*"
        f"{history_note}"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list commands."""
    if await reject_unauthorized(update, context):
        return

    await update.message.reply_text(
        "📖 **Available Commands**\n\n"
        "/start — Welcome message\n"
        "/help — Show this help\n"
        "/clear — Clear conversation history\n"
        "/prompt — Set a custom personality for me\n"
        "/myprompt — View your current personality\n"
        "/resetprompt — Reset to default personality\n"
        "/export — Export your chat history as JSON\n"
        "/export full — Full export with profile & settings\n"
        "/stats — View chat statistics\n"
        "/report — Admin analytics report *(admin only)*\n"
        "/report full — Full report with JSON file *(admin only)*\n"
        "/model — Show current AI model\n"
        "/settings — Show bot configuration\n\n"
        "💡 You can also just send me any text and I'll respond!"
    )


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — reset conversation."""
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id
    conversation_manager.clear(user_id)
    await update.message.reply_text("🧹 Conversation history cleared!")


async def prompt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /prompt — set a custom system prompt.

    Usage:
        /prompt You are a sarcastic pirate who speaks in nautical terms
        /prompt You are a friendly coding tutor who explains with examples
    """
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id

    # Check if the user provided a prompt after the command
    if not context.args or not " ".join(context.args).strip():
        # Show current prompt and usage instructions
        current = conversation_manager.get_custom_prompt(user_id)
        if current:
            await update.message.reply_text(
                "🎭 **Your current personality:**\n\n"
                f"> {current}\n\n"
                "To change it, use:\n"
                "`/prompt <your custom instructions>`\n\n"
                "Example:\n"
                '"/prompt You are a witty coding tutor"'
                "\n\n"
                "Use /resetprompt to go back to default."
            )
        else:
            await update.message.reply_text(
                "🎭 **Custom Personality**\n\n"
                "You're using the default personality right now.\n\n"
                "To set a custom one, use:\n"
                "`/prompt <your custom instructions>`\n\n"
                "Examples:\n"
                '"/prompt You are a witty coding tutor"\n'
                '"/prompt You are a sarcastic pirate"\n'
                '"/prompt You are a friendly travel advisor"'
            )
        return

    # Set the new custom prompt (with length validation)
    custom_prompt = " ".join(context.args)
    if len(custom_prompt) > MAX_CUSTOM_PROMPT_LENGTH:
        await update.message.reply_text(
            f"⚠️ Custom personality is too long ({len(custom_prompt)} characters).\n"
            f"Please keep it under {MAX_CUSTOM_PROMPT_LENGTH} characters."
        )
        return
    conversation_manager.set_custom_prompt(user_id, custom_prompt)

    # Clear history so the new prompt takes effect cleanly
    conversation_manager.clear(user_id)

    await update.message.reply_text(
        f"🎭 **Personality set!**\n\n"
        f"> {custom_prompt}\n\n"
        "Conversation history was cleared so the new personality takes effect cleanly.\n"
        "Use /resetprompt to go back to default anytime."
    )


async def myprompt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /myprompt — view current system prompt."""
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id
    custom = conversation_manager.get_custom_prompt(user_id)

    if custom:
        await update.message.reply_text(
            "🎭 **Your custom personality:**\n\n"
            f"> {custom}\n\n"
            "Use /prompt <text> to change it, or /resetprompt to go back to default."
        )
    else:
        await update.message.reply_text(
            "🎭 **Using default personality:**\n\n"
            f"> {Config.SYSTEM_PROMPT}\n\n"
            "Use /prompt <text> to set a custom one!"
        )


async def resetprompt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resetprompt — remove custom system prompt."""
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id
    was_custom = conversation_manager.get_custom_prompt(user_id)

    if was_custom:
        conversation_manager.reset_custom_prompt(user_id)
        # Clear history so the default prompt takes effect cleanly
        conversation_manager.clear(user_id)

        await update.message.reply_text(
            "🔄 **Personality reset to default!**\n\n"
            f"> {Config.SYSTEM_PROMPT}\n\n"
            "Conversation history was cleared for a clean start."
        )
    else:
        await update.message.reply_text(
            "ℹ️ You're already using the default personality.\n"
            "Use /prompt <text> to set a custom one!"
        )


async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export — export conversation history as JSON.

    Usage:
        /export          — Export conversation messages only (compact)
        /export full     — Export everything: profile, settings, messages
    """
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id
    mode = (context.args[0].lower() if context.args else "").strip()

    if mode == "full":
        # Full export: user profile + settings + conversation + metadata
        filepath, total = export_module.export_to_file(user_id)
        caption = f"📦 **Full Export**\n\n• Messages: {total}\n• Includes: profile, settings, conversation, metadata"
    else:
        # Compact export: conversation messages only (OpenAI-compatible)
        json_str, total = export_module.export_messages_only(user_id)
        filepath, _ = export_module.export_to_file(user_id)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
        caption = f"📦 **Chat Export**\n\n• Messages: {total}\n• Format: role, content, timestamp\n• Compatible with OpenAI message format"

    if total == 0:
        await update.message.reply_text(
            "📦 No conversation history to export.\n"
            "Start chatting with me first!"
        )
        return

    try:
        with open(filepath, "rb") as f:                          # FIX: was open() without with — file handle leak
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(filepath),         # FIX: was filepath.split("/")[-1]
                caption=caption,
            )
    except Exception as e:
        logger.error(f"Export failed for user {user_id}: {e}")
        await update.message.reply_text(                        # FIX: hide internal error details
            "⚠️ Export failed. Please try again later."
        )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats — show user's chat statistics."""
    if await reject_unauthorized(update, context):
        return

    user_id = update.effective_user.id
    msg_count = conversation_manager.get_message_count(user_id)
    custom_prompt = conversation_manager.get_custom_prompt(user_id)

    await update.message.reply_text(
        f"📊 **Your Chat Stats**\n\n"
        f"• Total messages stored: {msg_count}\n"
        f"• Custom personality: {'Yes' if custom_prompt else 'No (using default)'}\n"
        f"• Active conversation: {'Yes' if user_id in conversation_manager._cache else 'No'}\n"
        f"• Max history limit: {Config.MAX_HISTORY}"
    )


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /model — show current AI model."""
    if await reject_unauthorized(update, context):
        return

    await update.message.reply_text(
        f"🧠 Current AI model: `{Config.AI_MODEL}`"
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings — show current config."""
    if await reject_unauthorized(update, context):
        return

    await update.message.reply_text(
        f"⚙️ **Bot Settings**\n\n"
        f"• Model: `{Config.AI_MODEL}`\n"
        f"• Temperature: `{Config.TEMPERATURE}`\n"
        f"• Max tokens: `{Config.MAX_TOKENS}`\n"
        f"• Max history: `{Config.MAX_HISTORY} messages`\n"
        f"• Database: `SQLite (persistent)`\n"
        f"• Custom prompts: `Per-user (stored in DB)`\n"
        f"• Access control: `{'Enabled' if Config.ALLOWED_USERS else 'Disabled (open to all)'}`"
    )


# ──────────────────────────────────────────────
#  Admin Report Command
# ──────────────────────────────────────────────
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report — admin analytics report.

    Usage:
        /report        — Show text summary in chat
        /report full   — Text summary + JSON file attachment
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ This command is reserved for bot administrators."
        )
        return

    mode = (context.args[0].lower() if context.args else "").strip()

    # Generate and send text summary
    try:
        text_report = report_module.generate_text_report()
        await update.message.reply_text(text_report)
    except Exception as e:
        logger.error(f"Report text generation failed: {e}")
        await update.message.reply_text(                    # FIX: hide internal error details
            "⚠️ Failed to generate report. Please try again later."
        )
        return

    # If "full", also send the JSON file
    if mode == "full":
        try:
            filepath = report_module.generate_report_file()
            with open(filepath, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),   # FIX: was filepath.split("/")[-1]
                    caption="📊 Full analytics report (JSON)",
                )
        except Exception as e:
            logger.error(f"Report JSON export failed: {e}")
            await update.message.reply_text(                # FIX: hide internal error details
                "⚠️ Text report shown above. JSON export failed. Please try again later."
            )


# ──────────────────────────────────────────────
#  Message Handler (AI Chat)
# ──────────────────────────────────────────────
async def chat_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle all text messages — send to AI and reply."""
    if await reject_unauthorized(update, context):
        return

    user = update.effective_user
    user_id = user.id
    user_text = update.message.text

    # Persist user info
    database.upsert_user(user.id, user.username, user.first_name)

    # Show "typing..." indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Add user message to conversation
    conversation_manager.add_user_message(user_id, user_text)

    # Get AI response (uses user's custom system prompt if set)
    messages = conversation_manager.get_messages(user_id)
    ai_response, tokens_used = await ai_client.chat(messages)

    # Add AI response to conversation (with model & token info)
    conversation_manager.add_assistant_message(
        user_id, ai_response, model=Config.AI_MODEL, tokens=tokens_used
    )

    # Send response
    await update.message.reply_text(ai_response)


# ──────────────────────────────────────────────
#  Error Handler
# ──────────────────────────────────────────────
async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log errors that occur during updates."""
    logger.error(f"Exception while handling an update: {context.error}")


# ──────────────────────────────────────────────
#  Main Entry Point
# ──────────────────────────────────────────────
def main() -> None:
    """Build and run the bot."""
    try:
        Config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Initialize database
    database.init_db()
    logger.info("Database initialized.")

    logger.info(f"Starting AI Telegram Bot (model: {Config.AI_MODEL})")

    app = (
        ApplicationBuilder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("prompt", prompt_cmd))
    app.add_handler(CommandHandler("myprompt", myprompt_cmd))
    app.add_handler(CommandHandler("resetprompt", resetprompt_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("export", export_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("report", report_cmd))

    # Register message handler for all text messages
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler)
    )

    # Register error handler
    app.add_error_handler(error_handler)

    # Start the bot — webhook mode if WEBHOOK_URL is set, else polling.
    if Config.WEBHOOK_URL:
        # The path Telegram POSTs updates to. Defaults to the bot token so the
        # public endpoint is hard to guess.
        url_path = Config.WEBHOOK_PATH or Config.TELEGRAM_BOT_TOKEN
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{url_path.lstrip('/')}"

        # Start the health-check server (GET /health) on a separate port.
        start_health_server()

        logger.info(
            f"Bot is running in WEBHOOK mode on "
            f"{Config.WEBHOOK_LISTEN}:{Config.WEBHOOK_PORT} "
            f"(public URL: {Config.WEBHOOK_URL})"
        )
        app.run_webhook(
            listen=Config.WEBHOOK_LISTEN,
            port=Config.WEBHOOK_PORT,
            url_path=url_path,
            webhook_url=webhook_url,
            secret_token=Config.WEBHOOK_SECRET_TOKEN or None,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        logger.info("Bot is running in POLLING mode! Press Ctrl+C to stop.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
