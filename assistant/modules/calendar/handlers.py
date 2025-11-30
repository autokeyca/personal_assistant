"""Calendar command handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from dateutil import parser as date_parser

from assistant.services import CalendarService


async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cal command - list upcoming events."""
    try:
        service = CalendarService()

        # Parse days from args
        days = 7
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                pass

        events = service.list_events(days=days)

        if not events:
            await update.message.reply_text(f"No events in the next {days} days")
            return

        text = f"*Upcoming Events ({days} days):*\n\n"

        current_date = None
        for event in events:
            dt = date_parser.parse(event["start"])
            event_date = dt.strftime("%A, %B %d")

            if event_date != current_date:
                current_date = event_date
                text += f"\n*{event_date}*\n"

            if event["all_day"]:
                time_str = "All day"
            else:
                time_str = dt.strftime("%H:%M")

            text += f"  {time_str} - {event['summary']}\n"
            if event.get("location"):
                text += f"    {event['location']}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error listing events: {e}")


async def today_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command."""
    try:
        service = CalendarService()
        events = service.get_today_events()

        if not events:
            await update.message.reply_text("No events today")
            return

        text = "*Today's Events:*\n\n"
        for event in events:
            if event["all_day"]:
                time_str = "All day"
            else:
                dt = date_parser.parse(event["start"])
                end_dt = date_parser.parse(event["end"])
                time_str = f"{dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"

            text += f"*{event['summary']}*\n"
            text += f"  {time_str}\n"
            if event.get("location"):
                text += f"  {event['location']}\n"
            if event.get("description"):
                desc = event["description"][:100]
                text += f"  {desc}...\n" if len(event["description"]) > 100 else f"  {desc}\n"
            text += "\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def week_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /week command."""
    try:
        service = CalendarService()
        events = service.list_events(days=7)

        if not events:
            await update.message.reply_text("No events this week")
            return

        text = "*This Week's Events:*\n\n"

        current_date = None
        for event in events:
            dt = date_parser.parse(event["start"])
            event_date = dt.strftime("%A, %b %d")

            if event_date != current_date:
                current_date = event_date
                text += f"\n*{event_date}*\n"

            if event["all_day"]:
                time_str = "All day"
            else:
                time_str = dt.strftime("%H:%M")

            text += f"  {time_str} - {event['summary']}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newevent command - natural language event creation."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /newevent <natural language description>\n\n"
            "Examples:\n"
            "/newevent Lunch with John tomorrow at noon\n"
            "/newevent Team meeting Friday 3pm\n"
            "/newevent Doctor appointment next Monday 10am"
        )
        return

    try:
        service = CalendarService()
        text = " ".join(context.args)

        event = service.quick_add(text)

        dt = date_parser.parse(event["start"])
        time_str = dt.strftime("%A, %B %d at %H:%M")

        await update.message.reply_text(
            f"Created: *{event['summary']}*\n"
            f"{time_str}\n\n"
            f"Event ID: `{event['id'][:20]}...`",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"Error creating event: {e}")


async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delevent command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /delevent <event_id>\n\n"
            "Get event IDs from /cal or /today commands"
        )
        return

    try:
        service = CalendarService()
        event_id = context.args[0]

        service.delete_event(event_id)
        await update.message.reply_text(f"Deleted event {event_id[:20]}...")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
