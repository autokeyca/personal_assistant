"""Intelligent handlers using LLM for natural language processing."""

import os
import logging
import json
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

from assistant.services import (
    LLMService,
    TodoService,
    CalendarService,
    EmailService,
    UserService
)
from assistant.config import get

logger = logging.getLogger(__name__)

# Bot name
BOT_NAME = "Jeeves"


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


async def send_introduction(update: Update, user):
    """Send introduction message to new users."""
    user_service = UserService()
    owner_id = get("telegram.authorized_user_id")

    if user.is_owner:
        # Introduction for owner
        intro = f"""Good day! I'm {BOT_NAME}, your personal assistant.

I can help you with:
• Managing todos and tasks
• Calendar events and scheduling
• Email management
• Reminders and notifications
• General conversation and questions

You can speak to me naturally or send voice messages, and I'll do my best to assist you."""
    else:
        # Introduction for other users
        intro = f"""Good day! I'm {BOT_NAME}, a personal assistant.

I'm currently serving my owner, but I'm happy to pass along messages or requests to them. Please note that I can only execute tasks with my owner's explicit permission.

How may I assist you?"""

    await update.message.reply_text(intro)

    # If not owner, notify owner about new contact
    if not user.is_owner:
        owner_notification = f"""📬 New contact: {user.full_name}

{user.full_name} has started a conversation with {BOT_NAME}.
User ID: {user.telegram_id}
Username: @{user.username if user.username else 'N/A'}"""

        try:
            await update.get_bot().send_message(chat_id=owner_id, text=owner_notification)
        except Exception as e:
            logger.error(f"Failed to notify owner about new user: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages by transcribing and processing them."""
    try:
        # Get or create user
        user_service = UserService()
        user, is_new = user_service.get_or_create_user(update.effective_user)

        # Greet new users
        if is_new:
            await send_introduction(update, user)
            return

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

        # Add to conversation history
        user_service.add_conversation(user.telegram_id, "user", transcribed_text)

        # Show transcription
        await processing_msg.edit_text(f"📝 Transcribed: \"{transcribed_text}\"\n\nProcessing...")

        # Process the transcribed text as a natural language command
        await process_natural_language(update, context, transcribed_text, processing_msg, user)

    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await update.message.reply_text(f"❌ Error processing voice message: {str(e)}")


async def handle_intelligent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages using LLM for natural language understanding."""
    try:
        # Get or create user
        user_service = UserService()
        user, is_new = user_service.get_or_create_user(update.effective_user)

        # Greet new users
        if is_new:
            await send_introduction(update, user)
            return

        message_text = update.message.text

        # Add to conversation history
        user_service.add_conversation(user.telegram_id, "user", message_text)

        await process_natural_language(update, context, message_text, None, user)

    except Exception as e:
        logger.error(f"Error handling intelligent message: {e}")
        await update.message.reply_text(f"❌ Error processing message: {str(e)}")


async def request_owner_approval(update: Update, context: ContextTypes.DEFAULT_TYPE, user, message: str, intent: str, entities: dict, existing_message=None):
    """Request owner approval for a task from non-authorized user."""
    user_service = UserService()
    owner_id = get("telegram.authorized_user_id")

    # Create pending approval
    approval_id = user_service.create_approval_request(
        requester_id=user.telegram_id,
        request_message=message,
        intent=intent,
        entities=json.dumps(entities) if entities else None
    )

    # Notify requester
    response = f"I've forwarded your request to my owner for approval.\n\nRequest ID: {approval_id}"
    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)

    user_service.add_conversation(user.telegram_id, "assistant", response)

    # Notify owner
    owner_message = f"""🔔 Task Approval Request #{approval_id}

From: {user.full_name} (@{user.username if user.username else 'no username'})
Request: {message}

Intent: {intent}
Entities: {json.dumps(entities, indent=2) if entities else 'None'}

Reply with:
• /approve {approval_id} - to approve and execute
• /reject {approval_id} - to reject"""

    try:
        await context.bot.send_message(chat_id=owner_id, text=owner_message)
    except Exception as e:
        logger.error(f"Failed to send approval request to owner: {e}")


async def forward_message_to_owner(update: Update, user, message: str):
    """Forward a message from non-owner user to the owner."""
    owner_id = get("telegram.authorized_user_id")

    forward_text = f"""📨 Message from {user.full_name}:

{message}

---
User ID: {user.telegram_id}
Username: @{user.username if user.username else 'N/A'}"""

    try:
        await update.get_bot().send_message(chat_id=owner_id, text=forward_text)
    except Exception as e:
        logger.error(f"Failed to forward message to owner: {e}")


async def process_natural_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    existing_message = None,
    user = None
):
    """Process natural language using LLM and execute appropriate action."""
    try:
        user_service = UserService()
        llm = get_llm_service()

        # Get conversation context
        conversation_history = user_service.get_conversation_history(user.telegram_id, limit=10, hours=24)

        # Parse the message to extract intent and entities
        parsed = llm.parse_command(message)
        intent = parsed.get('intent')
        entities = parsed.get('entities', {})
        confidence = parsed.get('confidence', 0.0)

        logger.info(f"User {user.full_name} - Parsed intent: {intent}, confidence: {confidence}, entities: {entities}")

        # Check if this is a task intent that requires authorization
        task_intents = ['todo_add', 'todo_complete', 'todo_delete', 'calendar_add', 'reminder_add', 'email_send']

        if intent in task_intents and not user.is_owner and not user.is_authorized:
            # Non-authorized user trying to execute a task - request approval
            await request_owner_approval(update, context, user, message, intent, entities, existing_message)
            return

        # If not owner but asking a question or having general chat, pass message to owner
        if not user.is_owner and intent not in task_intents and intent != 'general_chat':
            await forward_message_to_owner(update, user, message)
            response = f"I've forwarded your request to my owner. They will respond shortly."
            if existing_message:
                await existing_message.edit_text(response)
            else:
                await update.message.reply_text(response)
            user_service.add_conversation(user.telegram_id, "assistant", response)
            return

        # Route to appropriate handler based on intent
        if intent == 'todo_add':
            await handle_todo_add(update, context, entities, message, existing_message, user)

        elif intent == 'todo_list':
            await handle_todo_list(update, context, entities, existing_message, user)

        elif intent == 'todo_complete':
            await handle_todo_complete(update, context, entities, message, existing_message, user)

        elif intent == 'calendar_add':
            await handle_calendar_add(update, context, entities, message, existing_message, user)

        elif intent == 'calendar_list':
            await handle_calendar_list(update, context, entities, existing_message, user)

        elif intent == 'reminder_add':
            await handle_reminder_add(update, context, entities, message, existing_message, user)

        elif intent == 'email_send':
            await handle_email_send(update, context, entities, message, existing_message, user)

        elif intent == 'general_chat':
            await handle_general_chat(update, context, message, existing_message, user, conversation_history)

        else:
            # Fallback to general chat for unknown intents
            await handle_general_chat(update, context, message, existing_message, user, conversation_history)

    except Exception as e:
        logger.error(f"Error processing natural language: {e}")
        error_msg = f"❌ Error: {str(e)}"
        if existing_message:
            await existing_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def handle_todo_add(update, context, entities, original_message, existing_message=None, user=None):
    """Handle adding a todo from natural language."""
    from dateutil import parser as date_parser

    user_service = UserService()
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_todo_list(update, context, entities, existing_message=None, user=None):
    """Handle listing todos."""
    user_service = UserService()
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_todo_complete(update, context, entities, original_message, existing_message=None, user=None):
    """Handle completing a todo."""
    user_service = UserService()
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_calendar_add(update, context, entities, original_message, existing_message=None, user=None):
    """Handle adding a calendar event."""
    user_service = UserService()
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_calendar_list(update, context, entities, existing_message=None, user=None):
    """Handle listing calendar events."""
    user_service = UserService()
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_reminder_add(update, context, entities, original_message, existing_message=None, user=None):
    """Handle adding a reminder."""
    from assistant.db import get_session
    from assistant.db.models import Reminder

    user_service = UserService()
    time_str = entities.get('time') or entities.get('date')
    message_text = entities.get('title') or entities.get('description') or original_message

    if not time_str:
        response = "❌ Could not extract time from message. Try: 'remind me tomorrow at 3pm to call mom'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user.telegram_id, "assistant", response)
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_email_send(update, context, entities, original_message, existing_message=None, user=None):
    """Handle sending an email from natural language."""
    user_service = UserService()
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
        if user:
            user_service.add_conversation(user.telegram_id, "assistant", response)
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

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def handle_general_chat(update, context, message, existing_message=None, user=None, conversation_history=None):
    """Handle general conversational messages."""
    from datetime import datetime
    import pytz
    from assistant.config import get

    user_service = UserService()
    llm = get_llm_service()

    # Get timezone from config and provide current time context
    tz_name = get("timezone", "America/Montreal")
    tz = pytz.timezone(tz_name)
    current_time = datetime.now(tz).strftime("%A, %B %d, %Y at %I:%M %p %Z")

    # Build context from conversation history
    history_context = ""
    if conversation_history:
        history_context = "\n\nRecent conversation:\n"
        for conv in conversation_history[-5:]:  # Last 5 messages
            role = conv['role'].capitalize()
            history_context += f"{role}: {conv['message']}\n"

    user_name = user.first_name if user else "User"

    system_context = f"""You are {BOT_NAME}, a polite and helpful personal assistant bot.
You help manage todos, calendar, email, and reminders.
When users ask questions or chat with you, be friendly and professional.
If they're asking about their schedule, todos, or want to manage something, guide them to use natural language.
Keep responses concise and friendly.

Current date and time: {current_time}
User's name: {user_name}{history_context}"""

    response = llm.generate_response(message, system_context)

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)

    # Save response to conversation history
    if user:
        user_service.add_conversation(user.telegram_id, "assistant", response)


async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending task request from another user (owner only)."""
    user_service = UserService()

    # Get approval ID from command
    if not context.args:
        await update.message.reply_text("Usage: /approve <request_id>")
        return

    try:
        approval_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid request ID. Must be a number.")
        return

    # Approve the request
    request_details = user_service.approve_request(approval_id)

    if not request_details:
        await update.message.reply_text(f"❌ Request #{approval_id} not found.")
        return

    # Notify owner
    await update.message.reply_text(f"✅ Request #{approval_id} approved.")

    # Get requester info
    requester = user_service.get_user_by_id(request_details['requester_id'])
    if not requester:
        await update.message.reply_text("❌ Could not find requester information.")
        return

    # Execute the task
    try:
        # Parse entities back from JSON
        entities = json.loads(request_details['entities']) if request_details['entities'] else {}
        intent = request_details['intent']
        message_text = request_details['request_message']

        # Create a mock update object for the requester
        # Note: This is a simplified approach. In production, you'd want to handle this more robustly.
        response_text = f"✅ Your request has been approved by {update.effective_user.first_name}.\n\nExecuting: {message_text}"

        # Notify requester
        await context.bot.send_message(
            chat_id=request_details['requester_id'],
            text=response_text
        )

        # For now, just notify - actual execution would require more complex handling
        # TODO: Implement actual task execution from approved requests

    except Exception as e:
        logger.error(f"Error executing approved request: {e}")
        await update.message.reply_text(f"❌ Error executing request: {str(e)}")


async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending task request from another user (owner only)."""
    user_service = UserService()

    # Get approval ID from command
    if not context.args:
        await update.message.reply_text("Usage: /reject <request_id>")
        return

    try:
        approval_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid request ID. Must be a number.")
        return

    # Reject the request
    success = user_service.reject_request(approval_id)

    if not success:
        await update.message.reply_text(f"❌ Request #{approval_id} not found.")
        return

    # Notify owner
    await update.message.reply_text(f"❌ Request #{approval_id} rejected.")

    # Get request details to notify requester
    try:
        from assistant.db import get_session, PendingApproval

        with get_session() as session:
            request = session.query(PendingApproval).filter_by(id=approval_id).first()
            if request:
                await context.bot.send_message(
                    chat_id=request.requester_id,
                    text=f"Your request has been declined.\n\nOriginal request: {request.request_message}"
                )
    except Exception as e:
        logger.error(f"Error notifying requester of rejection: {e}")
