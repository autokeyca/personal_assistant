"""General bot commands."""

from telegram import Update
from telegram.ext import ContextTypes

from assistant.services import TodoService, CalendarService, EmailService


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Hello! I'm your personal assistant.\n\n"
        "I can help you with:\n"
        "- Todo lists (/todo, /add, /done)\n"
        "- Calendar (/cal, /today, /newevent)\n"
        "- Email (/email, /unread, /send)\n"
        "- Reminders (/remind, /reminders)\n\n"
        "Type /help for all commands or /briefing for your daily summary."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
*Personal Assistant Commands*

*General:*
/start - Start the bot
/help - Show this help
/status - Show assistant status
/briefing - Get your daily briefing
/modules - View loaded plugin modules

*Todos:*
/todo - List active todos
/add <task> - Add a new todo
/done <id> - Mark todo as complete
/focus [id] - View or set active task
/unfocus - Clear active task
/deltodo <id> - Delete a todo
/todosearch <query> - Search todos

*Calendar:*
/cal - List upcoming events
/today - Show today's events
/week - Show this week's events
/newevent <text> - Quick add event (natural language)
/delevent <id> - Delete an event

*Email:*
/email - List recent emails
/unread - Show unread emails
/read <id> - Read an email
/send <to> | <subject> | <body> - Send email
/reply <id> | <message> - Reply to email
/archive <id> - Archive email
/emailsearch <query> - Search emails

*Reminders:*
/remind <time> | <message> - Set a reminder
/reminders - List pending reminders
/delremind <id> - Delete a reminder

Note: For commands with multiple parts, use | as separator.
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    try:
        todo_service = TodoService()
        email_service = EmailService()

        # Get current user's todos only
        user_id = update.effective_user.id
        todos = todo_service.list(user_id=user_id, limit=100)
        pending = len([t for t in todos if t["status"] == "pending"])
        in_progress = len([t for t in todos if t["status"] == "in_progress"])
        active_task = todo_service.get_active_task()

        unread = email_service.get_unread_count()

        status_text = "*Assistant Status*\n\n"

        # Show active task prominently at top
        if active_task:
            status_text += f"*Currently focused on:*\n {active_task['title']}\n\n"
        else:
            status_text += "*No active task* - Use /focus <id> to set one\n\n"

        status_text += (
            f"Todos: {pending} pending, {in_progress} in progress\n"
            f"Unread emails: {unread}\n"
            f"Status: Running"
        )

        await update.message.reply_text(status_text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error getting status: {e}")


async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /briefing command - daily summary."""
    try:
        todo_service = TodoService()
        calendar_service = CalendarService()
        email_service = EmailService()

        # Get today's data - only current user's todos
        user_id = update.effective_user.id
        todos = todo_service.list(user_id=user_id, limit=10)
        due_soon = todo_service.get_due_soon(hours=24)
        events = calendar_service.get_today_events()
        unread = email_service.get_unread(max_results=5)
        active_task = todo_service.get_active_task()

        # Build briefing
        text = "*Your Daily Briefing*\n\n"

        # Show active task first as ADHD guardrail
        if active_task:
            text += f"*Currently focused on:*\n {active_task['title']}\n\n"
        else:
            text += "*No active task set* - Use /focus <id>\n\n"

        # Today's events
        text += "*Today's Events:*\n"
        if events:
            for event in events:
                time_str = ""
                if not event["all_day"]:
                    from dateutil import parser
                    dt = parser.parse(event["start"])
                    time_str = dt.strftime("%H:%M") + " - "
                text += f"  - {time_str}{event['summary']}\n"
        else:
            text += "  No events today\n"

        # Todos due soon
        text += "\n*Due Soon:*\n"
        if due_soon:
            for todo in due_soon[:5]:
                text += f"  - {todo['title']}\n"
        else:
            text += "  No urgent deadlines\n"

        # Active todos
        text += "\n*Active Todos:*\n"
        if todos:
            for todo in todos[:5]:
                priority_icon = {"urgent": "!!", "high": "!", "medium": "", "low": ""}
                icon = priority_icon.get(todo["priority"], "")
                text += f"  - {icon}{todo['title']}\n"
        else:
            text += "  No active todos\n"

        # Unread emails
        text += f"\n*Unread Emails:* {len(unread)}\n"
        if unread:
            for email in unread[:3]:
                sender = email["from"].split("<")[0].strip()
                subject = email["subject"][:40]
                text += f"  - {sender}: {subject}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error generating briefing: {e}")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(
        f"Unknown command: {update.message.text}\n"
        "Type /help to see available commands."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages."""
    text = update.message.text.lower()

    # Simple natural language processing
    if any(word in text for word in ["hi", "hello", "hey"]):
        await update.message.reply_text(
            "Hello! How can I help you today?\n"
            "Type /help to see what I can do."
        )
    elif "todo" in text:
        await update.message.reply_text(
            "For todo management, try:\n"
            "/todo - List todos\n"
            "/add <task> - Add new todo"
        )
    elif "email" in text or "mail" in text:
        await update.message.reply_text(
            "For email management, try:\n"
            "/unread - Show unread emails\n"
            "/email - List recent emails"
        )
    elif "calendar" in text or "event" in text or "meeting" in text:
        await update.message.reply_text(
            "For calendar management, try:\n"
            "/today - Today's events\n"
            "/cal - Upcoming events"
        )
    else:
        await update.message.reply_text(
            "I'm not sure what you mean. Try /help to see available commands."
        )
