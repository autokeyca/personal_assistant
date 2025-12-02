"""Scheduled jobs for reminders, email checks, and briefings."""

import logging
from datetime import datetime, timedelta
import pytz
from telegram import Bot
from telegram.error import TelegramError

from assistant.config import get
from assistant.db import get_session, Reminder, Todo
from assistant.services import EmailService, CalendarService, TodoService, FrequencyParser

logger = logging.getLogger(__name__)


async def check_reminders(bot: Bot):
    """Check for due reminders and send them."""
    user_id = get("telegram.authorized_user_id")
    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)

    with get_session() as session:
        # Database stores naive UTC, so compare with naive UTC
        now_utc = datetime.now(pytz.UTC).replace(tzinfo=None)

        due_reminders = (
            session.query(Reminder)
            .filter(
                Reminder.remind_at <= now_utc,
                Reminder.is_sent == False,
            )
            .all()
        )

        for reminder in due_reminders:
            try:
                # Send to the user who created the reminder, or owner if not specified
                target_user_id = reminder.user_id if reminder.user_id else user_id
                await bot.send_message(
                    chat_id=target_user_id,
                    text=f" *Reminder*\n\n{reminder.message}",
                    parse_mode="Markdown",
                )
                reminder.is_sent = True
                logger.info(f"Sent reminder {reminder.id} to user {target_user_id}")

            except TelegramError as e:
                logger.error(f"Failed to send reminder {reminder.id}: {e}")


async def check_todo_reminders(bot: Bot):
    """Check for todos with custom reminder schedules and send reminders."""
    from assistant.services import UserService
    import json

    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)
    frequency_parser = FrequencyParser()
    user_service = UserService()

    with get_session() as session:
        now = datetime.now(tz)

        # Get all todos with reminder configs that are not completed
        todos_with_reminders = (
            session.query(Todo)
            .filter(
                Todo.reminder_config.isnot(None),
                Todo.status != 'completed',
            )
            .all()
        )

        for todo in todos_with_reminders:
            try:
                # Parse the reminder config
                reminder_config = json.loads(todo.reminder_config)

                # Check if we should send a reminder now
                should_remind = frequency_parser.should_remind_now(
                    reminder_config,
                    todo.last_reminder_at
                )

                if should_remind:
                    # Get the task owner
                    owner = user_service.get_user(todo.user_id) if todo.user_id else None
                    owner_name = owner.first_name if owner else "You"
                    owner_chat_id = owner.telegram_id if owner else get("telegram.authorized_user_id")

                    # Format reminder message
                    frequency_desc = frequency_parser.describe(reminder_config)
                    priority_icon = {
                        "urgent": " ‼️",
                        "high": " ❗",
                        "medium": "",
                        "low": "",
                    }.get(todo.priority.value, "")

                    text = (
                        f"🔔 *Task Reminder*\n\n"
                        f"`#{todo.id}` {todo.title}{priority_icon}\n"
                    )

                    if todo.description:
                        text += f"\n_{todo.description}_\n"

                    text += f"\n⏰ {frequency_desc}"

                    # Send reminder
                    await bot.send_message(
                        chat_id=owner_chat_id,
                        text=text,
                        parse_mode="Markdown",
                    )

                    # Update last reminder timestamp
                    todo.last_reminder_at = now
                    session.commit()

                    logger.info(f"Sent custom reminder for todo #{todo.id} to {owner_name}")

            except Exception as e:
                logger.error(f"Error processing reminder for todo #{todo.id}: {e}")


async def check_emails(bot: Bot):
    """Check for new emails and notify."""
    user_id = get("telegram.authorized_user_id")

    try:
        service = EmailService()
        new_emails = service.get_new_messages()

        if new_emails:
            text = f"*{len(new_emails)} New Email(s):*\n\n"

            for email in new_emails[:5]:  # Limit to 5
                sender = email["from"].split("<")[0].strip()[:25]
                subject = email["subject"][:40]
                text += f"*{sender}*\n{subject}\n\n"

            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
            )
            logger.info(f"Notified about {len(new_emails)} new emails")

    except Exception as e:
        logger.error(f"Error checking emails: {e}")


async def send_morning_briefing(bot: Bot):
    """Send the daily morning briefing."""
    user_id = get("telegram.authorized_user_id")

    try:
        todo_service = TodoService()
        calendar_service = CalendarService()
        email_service = EmailService()

        # Get today's data
        todos = todo_service.list(limit=10)
        due_soon = todo_service.get_due_soon(hours=24)
        events = calendar_service.get_today_events()
        unread_count = email_service.get_unread_count()

        # Build briefing
        text = " *Good Morning! Here's your briefing:*\n\n"

        # Today's events
        text += "*Today's Events:*\n"
        if events:
            for event in events[:5]:
                if event["all_day"]:
                    time_str = "All day"
                else:
                    from dateutil import parser
                    dt = parser.parse(event["start"])
                    time_str = dt.strftime("%H:%M")
                text += f"  {time_str} - {event['summary']}\n"
        else:
            text += "  No events today\n"

        # Todos
        text += f"\n*Active Todos:* {len(todos)}\n"
        if due_soon:
            text += f"*Due Today:* {len(due_soon)}\n"
            for todo in due_soon[:3]:
                text += f"  - {todo['title']}\n"

        # Emails
        text += f"\n*Unread Emails:* {unread_count}\n"

        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="Markdown",
        )
        logger.info("Sent morning briefing")

    except Exception as e:
        logger.error(f"Error sending morning briefing: {e}")


async def check_upcoming_events(bot: Bot):
    """Notify about events starting soon."""
    user_id = get("telegram.authorized_user_id")
    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)

    try:
        calendar_service = CalendarService()

        # Get events in the next 15 minutes
        from datetime import datetime
        now = datetime.now(tz)
        events = calendar_service.list_events(days=1, max_results=50)

        for event in events:
            if event["all_day"]:
                continue

            from dateutil import parser
            start = parser.parse(event["start"])

            # Ensure both times are timezone-aware for comparison
            if start.tzinfo is None:
                start = tz.localize(start)
            else:
                start = start.astimezone(tz)

            # Check if event starts in 10-15 minutes
            minutes_until = (start - now).total_seconds() / 60

            if 10 <= minutes_until <= 15:
                text = (
                    f" *Upcoming Event in {int(minutes_until)} minutes:*\n\n"
                    f"*{event['summary']}*\n"
                )
                if event.get("location"):
                    text += f"{event['location']}\n"

                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="Markdown",
                )
                logger.info(f"Sent upcoming event notification: {event['summary']}")

    except Exception as e:
        logger.error(f"Error checking upcoming events: {e}")


def setup_scheduler(app):
    """Set up scheduled jobs for the bot."""
    from telegram.ext import Application

    job_queue = app.job_queue

    # Check reminders every minute
    reminder_interval = get("scheduler.reminder_check_interval", 1)
    job_queue.run_repeating(
        lambda context: check_reminders(context.bot),
        interval=reminder_interval * 60,
        first=10,  # Start after 10 seconds
        name="check_reminders",
    )

    # Check todo custom reminders every minute
    job_queue.run_repeating(
        lambda context: check_todo_reminders(context.bot),
        interval=60,  # Every minute
        first=15,  # Start after 15 seconds
        name="check_todo_reminders",
    )

    # Check emails every 5 minutes
    email_interval = get("scheduler.email_check_interval", 5)
    job_queue.run_repeating(
        lambda context: check_emails(context.bot),
        interval=email_interval * 60,
        first=30,
        name="check_emails",
    )

    # Check upcoming events every 5 minutes
    job_queue.run_repeating(
        lambda context: check_upcoming_events(context.bot),
        interval=5 * 60,
        first=60,
        name="check_upcoming_events",
    )

    # Morning briefing - with timezone awareness
    from assistant.services import BehaviorConfigService
    behavior_service = BehaviorConfigService()

    # Check for dynamic briefing time in database, fallback to config
    briefing_time_config = behavior_service.get("morning_briefing_time")
    if briefing_time_config:
        briefing_time = briefing_time_config['value']
    else:
        briefing_time = get("scheduler.morning_briefing_time", "08:00")

    hour, minute = map(int, briefing_time.split(":"))

    from datetime import time
    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)

    job_queue.run_daily(
        lambda context: send_morning_briefing(context.bot),
        time=time(hour=hour, minute=minute, tzinfo=tz),
        name="morning_briefing",
    )

    logger.info(f"Morning briefing scheduled for {briefing_time} {tz_name}")
    logger.info("Scheduler setup complete")


def reschedule_morning_briefing(application, new_time: str):
    """
    Reschedule the morning briefing to a new time.

    Args:
        application: The Telegram application instance
        new_time: New time in HH:MM format (e.g., "07:30")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from datetime import time

        # Parse the new time
        hour, minute = map(int, new_time.split(":"))

        # Get timezone
        tz_name = get("timezone", "America/Montreal")
        tz = pytz.timezone(tz_name)

        # Remove existing morning briefing job
        job_queue = application.job_queue
        current_jobs = job_queue.get_jobs_by_name("morning_briefing")
        for job in current_jobs:
            job.schedule_removal()

        logger.info(f"Removed {len(current_jobs)} existing morning briefing job(s)")

        # Schedule new job
        job_queue.run_daily(
            lambda context: send_morning_briefing(context.bot),
            time=time(hour=hour, minute=minute, tzinfo=tz),
            name="morning_briefing",
        )

        logger.info(f"Morning briefing rescheduled to {new_time} {tz_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to reschedule morning briefing: {e}")
        return False
