"""Intelligent handlers using LLM for natural language processing."""

import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

from assistant.services import (
    LLMService,
    TodoService,
    CalendarService,
    EmailService
)
from assistant.config import get

logger = logging.getLogger(__name__)


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    api_key = get("gemini.api_key")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        raise ValueError(
            "Gemini API key not configured. "
            "Get one from https://aistudio.google.com/apikey and add it to config.yaml"
        )

    model = get("gemini.model", "gemini-2.5-flash")
    return LLMService(api_key, model)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages by transcribing and processing them."""
    try:
        # Notify user we're processing
        processing_msg = await update.message.reply_text("🎤 Transcribing voice message...")

        # Get voice file
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)

        # Download to temporary file
        temp_dir = "/tmp/personal_assistant"
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = os.path.join(temp_dir, f"voice_{voice.file_id}.ogg")
        await voice_file.download_to_drive(audio_path)

        # Transcribe
        llm = get_llm_service()
        transcribed_text = llm.transcribe_audio(audio_path)

        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)

        if not transcribed_text:
            await processing_msg.edit_text("❌ Failed to transcribe voice message.")
            return

        # Show transcription
        await processing_msg.edit_text(f"📝 Transcribed: \"{transcribed_text}\"\n\nProcessing...")

        # Process the transcribed text as a natural language command
        await process_natural_language(update, context, transcribed_text, processing_msg)

    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await update.message.reply_text(f"❌ Error processing voice message: {str(e)}")


async def handle_intelligent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages using LLM for natural language understanding."""
    try:
        message_text = update.message.text
        await process_natural_language(update, context, message_text)

    except Exception as e:
        logger.error(f"Error handling intelligent message: {e}")
        await update.message.reply_text(f"❌ Error processing message: {str(e)}")


async def process_natural_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    existing_message = None
):
    """Process natural language using LLM and execute appropriate action."""
    try:
        llm = get_llm_service()

        # Parse the message to extract intent and entities
        parsed = llm.parse_command(message)
        intent = parsed.get('intent')
        entities = parsed.get('entities', {})
        confidence = parsed.get('confidence', 0.0)

        logger.info(f"Parsed intent: {intent}, confidence: {confidence}, entities: {entities}")

        # Route to appropriate handler based on intent
        if intent == 'todo_add':
            await handle_todo_add(update, context, entities, message, existing_message)

        elif intent == 'todo_list':
            await handle_todo_list(update, context, entities, existing_message)

        elif intent == 'todo_complete':
            await handle_todo_complete(update, context, entities, message, existing_message)

        elif intent == 'calendar_add':
            await handle_calendar_add(update, context, entities, message, existing_message)

        elif intent == 'calendar_list':
            await handle_calendar_list(update, context, entities, existing_message)

        elif intent == 'reminder_add':
            await handle_reminder_add(update, context, entities, message, existing_message)

        elif intent == 'email_send':
            await handle_email_send(update, context, entities, message, existing_message)

        elif intent == 'general_chat':
            await handle_general_chat(update, context, message, existing_message)

        else:
            # Fallback to general chat for unknown intents
            await handle_general_chat(update, context, message, existing_message)

    except Exception as e:
        logger.error(f"Error processing natural language: {e}")
        error_msg = f"❌ Error: {str(e)}"
        if existing_message:
            await existing_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def handle_todo_add(update, context, entities, original_message, existing_message=None):
    """Handle adding a todo from natural language."""
    from dateutil import parser as date_parser

    todo_service = TodoService()

    title = entities.get('title') or original_message
    description = entities.get('description')
    priority = entities.get('priority', 'medium')
    due_date_str = entities.get('date')

    # Parse date string to datetime object if provided
    due_date = None
    if due_date_str:
        try:
            due_date = date_parser.parse(due_date_str)
        except Exception as e:
            logger.warning(f"Could not parse date '{due_date_str}': {e}")

    todo = todo_service.add(
        title=title,
        description=description,
        priority=priority,
        due_date=due_date
    )

    response = f"✅ Added todo: {todo['title']}"
    if priority and priority != 'medium':
        response += f" ({priority} priority)"
    if due_date:
        response += f"\n📅 Due: {due_date.strftime('%Y-%m-%d')}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_todo_list(update, context, entities, existing_message=None):
    """Handle listing todos."""
    todo_service = TodoService()
    todos = todo_service.list(limit=10)

    if not todos:
        response = "No todos found."
    else:
        response = "*Your Todos:*\n"
        for todo in todos:
            priority_icon = {"urgent": "‼️", "high": "❗", "medium": "➖", "low": "🔽"}
            icon = priority_icon.get(todo["priority"], "➖")
            response += f"{icon} {todo['id']}. {todo['title']}\n"

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")


async def handle_todo_complete(update, context, entities, original_message, existing_message=None):
    """Handle completing a todo."""
    todo_service = TodoService()

    # Try to extract ID from entities or find by title
    title = entities.get('title', '')

    # Search for matching todo
    todos = todo_service.search(title)
    if todos:
        todo_id = todos[0]['id']
        todo_service.complete(todo_id)
        response = f"✅ Marked as complete: {todos[0]['title']}"
    else:
        response = "❌ Could not find matching todo. Try /todo to see your list."

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_calendar_add(update, context, entities, original_message, existing_message=None):
    """Handle adding a calendar event."""
    calendar_service = CalendarService()

    # Use the original message for quick_add which handles natural language well
    event = calendar_service.quick_add(original_message)

    response = f"📅 Added event: {event['summary']}"
    if 'start' in event:
        start_time = event['start'].get('dateTime', event['start'].get('date'))
        response += f"\n🕐 {start_time}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_calendar_list(update, context, entities, existing_message=None):
    """Handle listing calendar events."""
    calendar_service = CalendarService()

    # Determine the time range based on entities
    days = 1  # Default to today
    if entities.get('date'):
        # If a specific date is mentioned, show that day
        days = 1

    events = calendar_service.list_events(days=days, max_results=10)

    if not events:
        response = "No upcoming events."
    else:
        response = "*Upcoming Events:*\n"
        for event in events:
            # CalendarService returns start as an ISO string already
            start = event.get('start', 'Unknown time')
            summary = event.get('summary', 'No title')
            # Format the datetime nicely
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(start)
                start_formatted = dt.strftime('%Y-%m-%d %H:%M')
            except:
                start_formatted = start
            response += f"• {summary} - {start_formatted}\n"

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")


async def handle_reminder_add(update, context, entities, original_message, existing_message=None):
    """Handle adding a reminder."""
    from assistant.db import get_session
    from assistant.db.models import Reminder

    time_str = entities.get('time') or entities.get('date')
    message_text = entities.get('title') or entities.get('description') or original_message

    if not time_str:
        response = "❌ Could not extract time from message. Try: 'remind me tomorrow at 3pm to call mom'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        return

    # Parse the time (simplified - you might want to enhance this)
    try:
        from dateutil import parser
        reminder_time = parser.parse(time_str)

        with get_session() as session:
            reminder = Reminder(
                message=message_text,
                remind_at=reminder_time,
                is_sent=False
            )
            session.add(reminder)
            session.commit()

            response = f"⏰ Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M')}\n💬 {message_text}"
    except Exception as e:
        response = f"❌ Could not parse time: {time_str}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_email_send(update, context, entities, original_message, existing_message=None):
    """Handle sending an email from natural language."""
    email_service = EmailService()

    recipient = entities.get('recipient')
    subject = entities.get('subject') or entities.get('title')
    body = entities.get('body') or entities.get('description')

    # Validate we have the minimum required info
    if not recipient:
        response = "❌ I need an email address or recipient name to send an email.\nTry: 'Send an email to john@example.com about the meeting'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        return

    if not body:
        # If no body is extracted, use the original message as body
        body = original_message

    if not subject:
        # Generate a subject from the body if not provided
        subject = body[:50] + "..." if len(body) > 50 else body

    try:
        # Send the email
        result = email_service.send_message(
            to=recipient,
            subject=subject,
            body=body
        )

        response = f"✅ Email sent to {recipient}\n📧 Subject: {subject}"

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        response = f"❌ Failed to send email: {str(e)}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_general_chat(update, context, message, existing_message=None):
    """Handle general conversational messages."""
    from datetime import datetime
    import pytz
    from assistant.config import get

    llm = get_llm_service()

    # Get timezone from config and provide current time context
    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)
    current_time = datetime.now(tz).strftime("%A, %B %d, %Y at %I:%M %p %Z")

    system_context = f"""You are a helpful personal assistant bot for managing todos, calendar, email, and reminders.
When users ask questions or chat with you, be friendly and helpful.
If they're asking about their schedule, todos, or want to manage something, guide them to use natural language.
Keep responses concise and friendly.

Current date and time: {current_time}"""

    response = llm.generate_response(message, system_context)

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)
