"""Reminder command handlers."""

from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from dateutil import parser as date_parser

from assistant.db import get_session, Reminder


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remind command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /remind <time> | <message>\n\n"
            "Examples:\n"
            "/remind tomorrow 9am | Call the bank\n"
            "/remind in 2 hours | Check on deployment\n"
            "/remind friday 5pm | Submit weekly report"
        )
        return

    try:
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) < 2:
            await update.message.reply_text(
                "Please provide: /remind <time> | <message>"
            )
            return

        time_str, message = parts[0], "|".join(parts[1:])

        # Parse the time
        remind_at = date_parser.parse(time_str, fuzzy=True)

        # If time is in the past, it might be for tomorrow
        if remind_at < datetime.now():
            from datetime import timedelta
            remind_at += timedelta(days=1)

        with get_session() as session:
            reminder = Reminder(
                message=message,
                remind_at=remind_at,
            )
            session.add(reminder)
            session.flush()

            await update.message.reply_text(
                f"Reminder set for {remind_at.strftime('%A, %B %d at %H:%M')}\n"
                f"Message: {message}\n"
                f"ID: {reminder.id}"
            )

    except Exception as e:
        await update.message.reply_text(f"Error setting reminder: {e}")


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reminders command."""
    try:
        with get_session() as session:
            reminders = (
                session.query(Reminder)
                .filter(Reminder.is_sent == False)
                .order_by(Reminder.remind_at.asc())
                .all()
            )

            if not reminders:
                await update.message.reply_text("No pending reminders")
                return

            text = "*Pending Reminders:*\n\n"
            for r in reminders:
                time_str = r.remind_at.strftime("%m/%d %H:%M")
                text += f"`{r.id}` {time_str}\n  {r.message}\n\n"

            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delremind command."""
    if not context.args:
        await update.message.reply_text("Usage: /delremind <id>")
        return

    try:
        reminder_id = int(context.args[0])

        with get_session() as session:
            reminder = (
                session.query(Reminder)
                .filter(Reminder.id == reminder_id)
                .first()
            )

            if reminder:
                session.delete(reminder)
                await update.message.reply_text(f"Deleted reminder #{reminder_id}")
            else:
                await update.message.reply_text(f"Reminder #{reminder_id} not found")

    except ValueError:
        await update.message.reply_text("Invalid reminder ID")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
