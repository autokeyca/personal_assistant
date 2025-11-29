"""Main Telegram bot setup and runner."""

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from assistant.config import get
from assistant.db import init_db
from assistant.scheduler import setup_scheduler

from .handlers import todo, calendar, email, reminders, general, intelligent

logger = logging.getLogger(__name__)


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    token = get("telegram.bot_token")
    if not token or token == "YOUR_BOT_TOKEN_FROM_BOTFATHER":
        raise ValueError(
            "Telegram bot token not configured. "
            "Get one from @BotFather and add it to config.yaml"
        )

    # Initialize database
    db_path = get("database.path")
    init_db(db_path)

    # Create application
    app = Application.builder().token(token).build()

    # Get authorized user ID
    authorized_user = get("telegram.authorized_user_id")

    # Add security filter to all handlers
    user_filter = filters.User(user_id=authorized_user) if authorized_user else filters.ALL

    # General commands
    app.add_handler(CommandHandler("start", general.start, filters=user_filter))
    app.add_handler(CommandHandler("help", general.help_command, filters=user_filter))
    app.add_handler(CommandHandler("status", general.status, filters=user_filter))
    app.add_handler(CommandHandler("briefing", general.briefing, filters=user_filter))

    # Todo commands
    app.add_handler(CommandHandler("todo", todo.list_todos, filters=user_filter))
    app.add_handler(CommandHandler("todos", todo.list_todos, filters=user_filter))
    app.add_handler(CommandHandler("add", todo.add_todo, filters=user_filter))
    app.add_handler(CommandHandler("done", todo.complete_todo, filters=user_filter))
    app.add_handler(CommandHandler("deltodo", todo.delete_todo, filters=user_filter))
    app.add_handler(CommandHandler("todosearch", todo.search_todos, filters=user_filter))
    app.add_handler(CommandHandler("focus", todo.focus_task, filters=user_filter))
    app.add_handler(CommandHandler("unfocus", todo.unfocus_task, filters=user_filter))

    # Calendar commands
    app.add_handler(CommandHandler("cal", calendar.list_events, filters=user_filter))
    app.add_handler(CommandHandler("today", calendar.today_events, filters=user_filter))
    app.add_handler(CommandHandler("week", calendar.week_events, filters=user_filter))
    app.add_handler(CommandHandler("newevent", calendar.quick_add, filters=user_filter))
    app.add_handler(CommandHandler("delevent", calendar.delete_event, filters=user_filter))

    # Email commands
    app.add_handler(CommandHandler("email", email.list_emails, filters=user_filter))
    app.add_handler(CommandHandler("unread", email.unread_emails, filters=user_filter))
    app.add_handler(CommandHandler("read", email.read_email, filters=user_filter))
    app.add_handler(CommandHandler("send", email.send_email, filters=user_filter))
    app.add_handler(CommandHandler("reply", email.reply_email, filters=user_filter))
    app.add_handler(CommandHandler("archive", email.archive_email, filters=user_filter))
    app.add_handler(CommandHandler("emailsearch", email.search_emails, filters=user_filter))

    # Reminder commands
    app.add_handler(CommandHandler("remind", reminders.add_reminder, filters=user_filter))
    app.add_handler(CommandHandler("reminders", reminders.list_reminders, filters=user_filter))
    app.add_handler(CommandHandler("delremind", reminders.delete_reminder, filters=user_filter))

    # Approval commands (owner only)
    app.add_handler(CommandHandler("approve", intelligent.approve_request, filters=user_filter))
    app.add_handler(CommandHandler("reject", intelligent.reject_request, filters=user_filter))

    # User authorization commands (owner only)
    app.add_handler(CommandHandler("authorize", intelligent.authorize_user, filters=user_filter))
    app.add_handler(CommandHandler("block", intelligent.block_user, filters=user_filter))

    # Prompt management commands (owner only)
    app.add_handler(CommandHandler("viewprompt", intelligent.view_prompt, filters=user_filter))
    app.add_handler(CommandHandler("setprompt", intelligent.set_prompt, filters=user_filter))
    app.add_handler(CommandHandler("resetprompt", intelligent.reset_prompt, filters=user_filter))

    # Handle voice messages (from anyone - authorization checked in handler)
    app.add_handler(MessageHandler(
        filters.VOICE,
        intelligent.handle_voice
    ))

    # Handle unknown commands
    app.add_handler(MessageHandler(
        filters.COMMAND & user_filter,
        general.unknown_command
    ))

    # Handle regular text messages (from anyone - authorization checked in handler)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        intelligent.handle_intelligent_message
    ))

    # Error handler
    app.add_error_handler(error_handler)

    # Setup scheduler for reminders and notifications
    setup_scheduler(app)

    return app


async def error_handler(update, context):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error: {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"An error occurred: {str(context.error)}"
        )


def run_bot():
    """Run the bot."""
    import logging.handlers
    from pathlib import Path

    # Setup logging
    log_file = get("logging.file")
    log_level = get("logging.level", "INFO")

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Time-based rotating file handler (keep logs for 24 hours)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',  # Rotate at midnight
        interval=1,       # Every 1 day
        backupCount=1     # Keep only 1 backup (24 hours worth)
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler(),
        ],
    )

    logger.info("Starting Personal Assistant bot...")

    app = create_bot()

    # Run the bot (allow message updates including voice)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    run_bot()
