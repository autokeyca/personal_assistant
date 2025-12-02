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
    UserService,
    PromptService,
    BehaviorConfigService
)
from assistant.config import get
from assistant.bot.handlers.todo import format_todo_list

logger = logging.getLogger(__name__)

# Bot name
BOT_NAME = "Jarvis"


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

    if user['is_owner']:
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
        # Introduction for other users - different message based on authorization status
        if user['is_authorized']:
            intro = f"""Good day! I'm {BOT_NAME}, a personal assistant.

You are authorized to use my services. I can help you with:
• Managing your todos and tasks
• Setting up reminders
• General conversation and questions

How may I assist you?"""
        else:
            intro = f"""Good day! I'm {BOT_NAME}, a personal assistant.

I'm currently serving my owner. I can pass along messages or requests to them, but I need my owner's authorization to execute tasks on your behalf.

Your introduction has been forwarded to my owner for approval.

How may I assist you?"""

    await update.message.reply_text(intro)

    # If not owner, send comprehensive notification to owner about new contact
    if not user['is_owner']:
        owner_notification = f"""🔔 New User Contact

👤 *User Details:*
Name: {user['full_name']}
User ID: `{user['telegram_id']}`
Username: @{user['username'] if user['username'] else 'N/A'}

*Authorization Commands:*
• `/authorize {user['telegram_id']}` - Grant task execution permissions
• `/block {user['telegram_id']}` - Revoke all permissions

This user can currently send messages but cannot execute tasks until authorized."""

        try:
            await update.get_bot().send_message(
                chat_id=owner_id,
                text=owner_notification,
                parse_mode="Markdown"
            )
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
        user_service.add_conversation(user['telegram_id'], "user", transcribed_text, channel="telegram")

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
        from assistant.bot.handlers.authorization import handle_unauthorized_user

        # Get or create user
        user_service = UserService()
        user, is_new = user_service.get_or_create_user(update.effective_user)

        # Check if user is authorized
        if not user['is_authorized'] and not user['is_owner']:
            # Route to authorization handler
            await handle_unauthorized_user(update, context)
            return

        # Greet new authorized users
        if is_new:
            await send_introduction(update, user)
            return

        message_text = update.message.text

        # Add to conversation history
        user_service.add_conversation(user['telegram_id'], "user", message_text, channel="telegram")

        await process_natural_language(update, context, message_text, None, user)

    except Exception as e:
        logger.error(f"Error handling intelligent message: {e}")
        await update.message.reply_text(f"❌ Error processing message: {str(e)}")


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
        conversation_history = user_service.get_conversation_history(user['telegram_id'], limit=10, hours=24)

        # Parse the message to extract intent and entities
        parsed = llm.parse_command(message, conversation_context=conversation_history)
        intent = parsed.get('intent')
        entities = parsed.get('entities', {})
        confidence = parsed.get('confidence', 0.0)

        logger.info(f"User {user['full_name']} - Parsed intent: {intent}, confidence: {confidence}, entities: {entities}")

        # Owner-only intents (email and calendar are private to the owner)
        owner_only_intents = ['calendar_add', 'calendar_list', 'email_send', 'email_check']

        # Check if non-owner is trying to access owner-only features
        if intent in owner_only_intents and not user['is_owner']:
            response = "⛔ Email and calendar management are only available to my owner. You have access to todo management and reminders."
            if existing_message:
                await existing_message.edit_text(response)
            else:
                await update.message.reply_text(response)
            user_service.add_conversation(user['telegram_id'], "assistant", response)
            return

        # Note: Unauthorized users are handled at entry point (handle_intelligent_message)
        # Only authorized users (owner, employees, contacts) reach this point

        # If non-owner user is asking questions or general chat, they get direct responses
        # No need to forward messages - authorized users can interact directly with Jarvis

        # Route to appropriate handler based on intent
        if intent == 'todo_add':
            await handle_todo_add(update, context, entities, message, existing_message, user)

        elif intent == 'todo_list':
            await handle_todo_list(update, context, entities, existing_message, user)

        elif intent == 'todo_complete':
            await handle_todo_complete(update, context, entities, message, existing_message, user)

        elif intent == 'todo_delete':
            await handle_todo_delete(update, context, entities, message, existing_message, user)

        elif intent == 'todo_focus':
            await handle_todo_focus(update, context, entities, message, existing_message, user)

        elif intent == 'todo_set_reminder':
            await handle_todo_set_reminder(update, context, entities, message, existing_message, user)

        elif intent == 'calendar_add':
            await handle_calendar_add(update, context, entities, message, existing_message, user)

        elif intent == 'calendar_list':
            await handle_calendar_list(update, context, entities, existing_message, user)

        elif intent == 'reminder_add':
            await handle_reminder_add(update, context, entities, message, existing_message, user)

        elif intent == 'email_send':
            await handle_email_send(update, context, entities, message, existing_message, user)

        elif intent == 'telegram_message':
            await handle_telegram_message(update, context, entities, message, existing_message, user)

        elif intent == 'meta_modify_prompt':
            await handle_meta_modify_prompt(update, context, entities, message, existing_message, user)

        elif intent == 'meta_configure':
            await handle_meta_configure(update, context, entities, message, existing_message, user)

        elif intent == 'meta_extend':
            await handle_meta_extend(update, context, entities, message, existing_message, user)

        elif intent == 'web_search':
            await handle_web_search(update, context, entities, message, existing_message, user)

        elif intent == 'web_fetch':
            await handle_web_fetch(update, context, entities, message, existing_message, user)

        elif intent == 'web_ask':
            await handle_web_ask(update, context, entities, message, existing_message, user)

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
    intensity = entities.get('intensity')
    for_user_name = entities.get('for_user')

    # Parse date string to datetime object if provided
    due_date = None
    if due_date_str:
        try:
            due_date = date_parser.parse(due_date_str)
        except Exception as e:
            logger.warning(f"Could not parse date '{due_date_str}': {e}")

    # Determine the target user for this todo
    target_user_id = user['telegram_id']  # Default to self
    target_user_name = user['first_name']

    if for_user_name and user['is_owner']:
        # Owner is adding a task for someone else
        from assistant.db import get_session, User
        with get_session() as session:
            target_user = session.query(User).filter(
                User.first_name.ilike(for_user_name)
            ).first()

            if target_user:
                target_user_id = target_user.telegram_id
                target_user_name = target_user.first_name
            else:
                response = f"❌ User '{for_user_name}' not found. They need to start Jarvis first."
                if existing_message:
                    await existing_message.edit_text(response)
                else:
                    await update.message.reply_text(response)
                return

    todo = todo_service.add(
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        user_id=target_user_id,
        created_by=user['telegram_id'],
        follow_up_intensity=intensity
    )

    # Check if user wants to focus on this new task
    should_focus = 'focus' in original_message.lower() and target_user_id == user['telegram_id']

    if should_focus:
        # Set this as the active task and pin it
        todo_service.set_active_task(todo['id'])

        # Unpin previous focus message if it exists
        from assistant.db import get_session, Setting
        with get_session() as session:
            setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
            if setting and setting.value:
                try:
                    await context.bot.unpin_chat_message(
                        chat_id=update.effective_chat.id,
                        message_id=int(setting.value)
                    )
                except Exception as e:
                    logger.warning(f"Could not unpin previous message: {e}")

        # Format focus message
        priority_icon = {
            "urgent": " ‼️",
            "high": " ❗",
            "medium": "",
            "low": "",
        }.get(priority, "")

        due = ""
        if due_date:
            due = f"\n📅 Due: {due_date.strftime('%B %d, %H:%M')}"

        focus_text = (
            f"🎯 *FOCUSED TASK*\n\n"
            f"`{todo['id']}` {todo['title']}{priority_icon}{due}"
        )
        if description:
            focus_text += f"\n\n_{description}_"

        # Send and pin the message
        focus_message = await update.message.reply_text(focus_text, parse_mode="Markdown")
        await focus_message.pin(disable_notification=True)

        # Store pinned message ID
        with get_session() as session:
            setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
            if setting:
                setting.value = str(focus_message.message_id)
            else:
                setting = Setting(key="pinned_focus_message_id", value=str(focus_message.message_id))
                session.add(setting)

    # Show confirmation
    if for_user_name and target_user_id != user['telegram_id']:
        # Task added for someone else
        response = f"✅ Added to {target_user_name}'s list: {todo['title']}"

        # Notify the target user
        try:
            notify_msg = f"📋 New task from {user['first_name']}:\n\n{todo['title']}"
            if priority and priority != 'medium':
                notify_msg += f"\n🎯 Priority: {priority.capitalize()}"
            if due_date:
                notify_msg += f"\n📅 Due: {due_date.strftime('%Y-%m-%d')}"
            if description:
                notify_msg += f"\n\n{description}"

            await context.bot.send_message(
                chat_id=target_user_id,
                text=notify_msg
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_user_name}: {e}")

        # Show target user's todo list
        todos = todo_service.list(user_id=target_user_id, include_completed=False)
        list_title = f"{target_user_name}'s Todos"
        response += f"\n\n{format_todo_list(todos, title=list_title)}"
    else:
        # Task added for self
        # Owner sees all tasks, regular users see only their own
        if user['is_owner']:
            todos = todo_service.list(all_users=True, include_completed=False)
        else:
            todos = todo_service.list(user_id=target_user_id, include_completed=False)
        response = f"✅ Added: {todo['title']}"
        if priority and priority != 'medium':
            response += f" ({priority} priority)"
        if due_date:
            response += f"\n📅 Due: {due_date.strftime('%Y-%m-%d')}"
        response += f"\n\n{format_todo_list(todos)}"

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_todo_list(update, context, entities, existing_message=None, user=None):
    """Handle listing todos."""
    user_service = UserService()
    todo_service = TodoService()

    user_name = entities.get('user_name')
    target_user_id = user['telegram_id']
    list_title = "Your Todos"
    show_all = False

    # Determine whose todos to show
    if user_name:
        if user_name.lower() == 'all' and user['is_owner']:
            # Show all users' todos
            show_all = True
            list_title = "All Todos"
        elif user['is_owner']:
            # Show specific user's todos
            from assistant.db import get_session, User
            with get_session() as session:
                target_user = session.query(User).filter(
                    User.first_name.ilike(user_name)
                ).first()

                if target_user:
                    target_user_id = target_user.telegram_id
                    list_title = f"{target_user.first_name}'s Todos"
                else:
                    response = f"❌ User '{user_name}' not found."
                    if existing_message:
                        await existing_message.edit_text(response)
                    else:
                        await update.message.reply_text(response)
                    return

    # Get todos
    if show_all:
        todos = todo_service.list(all_users=True, include_completed=False)
    elif user['is_owner'] and not user_name:
        # Owner sees all tasks by default unless asking for specific user
        todos = todo_service.list(all_users=True, include_completed=False)
        list_title = "All Todos"
    else:
        todos = todo_service.list(user_id=target_user_id, include_completed=False)

    response = format_todo_list(todos, title=list_title)

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_todo_complete(update, context, entities, original_message, existing_message=None, user=None):
    """Handle completing a todo."""
    user_service = UserService()
    todo_service = TodoService()

    # Try to extract ID from entities or find by title
    title = entities.get('title') or ''
    if title is None:
        title = ''

    # Strip common articles from the beginning for better matching
    import re
    title = re.sub(r'^(the|a|an)\s+', '', title, flags=re.IGNORECASE).strip()

    # Get all pending tasks for this user
    pending_todos = todo_service.list(user_id=user['telegram_id'], include_completed=False)

    # If ambiguous (short title or no title), need confirmation
    is_ambiguous = len(title) < 3 or title.lower() in ['it', 'that', 'this', 'task', 'todo']

    if is_ambiguous and len(pending_todos) > 1:
        # Multiple tasks and ambiguous request - ask for confirmation
        # Prioritize most recent task created by someone else
        suggested_task = None
        for todo in sorted(pending_todos, key=lambda x: x['created_at'], reverse=True):
            if todo['created_by'] and todo['created_by'] != user['telegram_id']:
                suggested_task = todo
                break

        # If no tasks created by others, use most recent overall
        if not suggested_task and pending_todos:
            suggested_task = sorted(pending_todos, key=lambda x: x['created_at'], reverse=True)[0]

        # Show suggestion and ask for confirmation
        response = f"📋 You have {len(pending_todos)} pending tasks. Did you mean:\n\n"
        response += f"**#{suggested_task['id']}** {suggested_task['title']}"
        if suggested_task.get('priority') and suggested_task['priority'] != 'medium':
            response += f" ({suggested_task['priority']} priority)"
        response += f"\n\nReply with:\n"
        response += f"• 'yes' or 'confirm' to complete this task\n"
        response += f"• A task number (e.g., '{suggested_task['id']}') to complete a specific task\n"
        response += f"• 'list' to see all your tasks"

    elif title.isdigit():
        # User specified a task number directly
        todo_id = int(title)
        todo = todo_service.get(todo_id)

        # Owner can complete anyone's tasks, others can only complete their own
        can_complete = todo and todo['status'] != 'completed' and (
            user['is_owner'] or todo['user_id'] == user['telegram_id']
        )

        if can_complete:
            # Complete the task
            active = todo_service.get_active_task()
            is_focused = active and active['id'] == todo_id

            todo_service.complete(todo_id)

            # Unpin if this was the focused task
            if is_focused:
                from assistant.db import get_session, Setting
                with get_session() as session:
                    setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
                    if setting and setting.value:
                        try:
                            await context.bot.unpin_chat_message(
                                chat_id=update.effective_chat.id,
                                message_id=int(setting.value)
                            )
                            setting.value = None
                        except Exception as e:
                            logger.warning(f"Could not unpin message: {e}")

            remaining_todos = todo_service.list(user_id=user['telegram_id'], include_completed=False)
            response = f"✅ Completed: {todo['title']}\n\n{format_todo_list(remaining_todos)}"
        else:
            response = f"❌ Task #{todo_id} not found or already completed."

    else:
        # Search for matching todo by title
        todos = todo_service.search(title)

        # Filter to pending todos (owner can complete anyone's, others only their own)
        if user['is_owner']:
            user_todos = [t for t in todos if t['status'] != 'completed']
        else:
            user_todos = [t for t in todos if t['user_id'] == user['telegram_id'] and t['status'] != 'completed']

        if user_todos:
            todo_id = user_todos[0]['id']

            # Check if this is the focused task
            active = todo_service.get_active_task()
            is_focused = active and active['id'] == todo_id

            todo_service.complete(todo_id)

            # Unpin if this was the focused task
            if is_focused:
                from assistant.db import get_session, Setting
                with get_session() as session:
                    setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
                    if setting and setting.value:
                        try:
                            await context.bot.unpin_chat_message(
                                chat_id=update.effective_chat.id,
                                message_id=int(setting.value)
                            )
                            setting.value = None
                        except Exception as e:
                            logger.warning(f"Could not unpin message: {e}")

            # Show confirmation and list
            remaining_todos = todo_service.list(user_id=user['telegram_id'], include_completed=False)
            response = f"✅ Completed: {user_todos[0]['title']}\n\n{format_todo_list(remaining_todos)}"
        else:
            response = "❌ Could not find matching todo. Try /todo to see your list."

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_todo_delete(update, context, entities, original_message, existing_message=None, user=None):
    """Handle deleting a todo."""
    user_service = UserService()
    todo_service = TodoService()

    # Try to extract title from entities
    title = entities.get('title') or ''
    if title is None:
        title = ''

    # Strip common articles from the beginning for better matching
    import re
    title = re.sub(r'^(the|a|an)\s+', '', title, flags=re.IGNORECASE).strip()

    # Search for matching todo
    todos = todo_service.search(title)
    if todos:
        todo_id = todos[0]['id']
        todo_service.delete(todo_id)

        # Show confirmation and list
        remaining_todos = todo_service.list(include_completed=False)
        response = f"🗑️ Deleted: {todos[0]['title']}\n\n{format_todo_list(remaining_todos)}"
    else:
        response = "❌ Could not find matching todo. Try /todo to see your list."

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_todo_focus(update, context, entities, original_message, existing_message=None, user=None):
    """Handle focusing on a todo task."""
    user_service = UserService()
    todo_service = TodoService()

    # Try to extract title from entities or use original message
    title = entities.get('title') or original_message or ''

    # Handle None values
    if title is None:
        title = ''

    # Strip common articles from the beginning for better matching
    import re
    title = re.sub(r'^(the|a|an)\s+', '', title, flags=re.IGNORECASE).strip()

    # Try to parse as ID first
    todo_id = None
    if title.isdigit():
        todo_id = int(title)
    else:
        # Search for matching todo
        todos = todo_service.search(title)
        if todos:
            todo_id = todos[0]['id']

    if todo_id:
        result = todo_service.set_active_task(todo_id)
        if result:
            # Unpin previous focus message if it exists
            from assistant.db import get_session, Setting
            with get_session() as session:
                setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
                if setting and setting.value:
                    try:
                        await context.bot.unpin_chat_message(
                            chat_id=update.effective_chat.id,
                            message_id=int(setting.value)
                        )
                    except Exception as e:
                        logger.warning(f"Could not unpin previous message: {e}")

            # Format focus message
            priority_icon = {
                "urgent": " ‼️",
                "high": " ❗",
                "medium": "",
                "low": "",
            }.get(result["priority"], "")

            due = ""
            if result.get("due_date"):
                from dateutil import parser
                dt = parser.parse(result["due_date"])
                due = f"\n📅 Due: {dt.strftime('%B %d, %H:%M')}"

            text = (
                f"🎯 *FOCUSED TASK*\n\n"
                f"`{result['id']}` {result['title']}{priority_icon}{due}"
            )
            if result.get("description"):
                text += f"\n\n_{result['description']}_"

            # Send and pin the message
            if existing_message:
                # Can't pin edited messages, send new one
                message = await update.message.reply_text(text, parse_mode="Markdown")
            else:
                message = await update.message.reply_text(text, parse_mode="Markdown")

            await message.pin(disable_notification=True)

            # Store pinned message ID
            with get_session() as session:
                setting = session.query(Setting).filter(Setting.key == "pinned_focus_message_id").first()
                if setting:
                    setting.value = str(message.message_id)
                else:
                    setting = Setting(key="pinned_focus_message_id", value=str(message.message_id))
                    session.add(setting)

            response = f"🎯 Now focused on: {result['title']}"
        else:
            response = "❌ Could not find that todo."
    else:
        response = "❌ Could not find matching todo. Try /todo to see your list."

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


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
        user_service.add_conversation(user['telegram_id'], "assistant", response)


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
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_todo_set_reminder(update, context, entities, original_message, existing_message=None, user=None):
    """Handle setting a custom reminder frequency for a todo task."""
    from assistant.services import TodoService, UserService, FrequencyParser
    from assistant.db import get_session, Todo
    import json

    user_service = UserService()
    todo_service = TodoService()
    frequency_parser = FrequencyParser()

    # Extract entities
    frequency = entities.get('frequency')
    title = entities.get('title')
    user_name = entities.get('user_name') or entities.get('for_user')

    if not frequency:
        response = "❌ I couldn't understand the reminder frequency. Try: 'remind Luke every 2 hours during business hours'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Parse the frequency expression
    frequency_config = frequency_parser.parse(frequency)
    if not frequency_config:
        response = f"❌ I couldn't parse the frequency '{frequency}'. Try something like 'every 2 hours' or 'every day at 9am'."
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Find the target user
    target_user_id = None
    if user_name:
        target_user = user_service.get_user_by_name(user_name)
        if target_user:
            target_user_id = target_user.telegram_id
        else:
            response = f"❌ User '{user_name}' not found."
            if existing_message:
                await existing_message.edit_text(response)
            else:
                await update.message.reply_text(response)
            if user:
                user_service.add_conversation(user['telegram_id'], "assistant", response)
            return

    # Find the todo task
    todo_id = None
    todo = None

    # If title is provided, search for it
    if title:
        # Check if title is a number (task ID)
        if title.isdigit():
            todo_id = int(title)
            todo_dict = todo_service.get(todo_id)
            if todo_dict and (target_user_id is None or todo_dict['user_id'] == target_user_id):
                todo = todo_dict
        else:
            # Search by title
            search_results = todo_service.search(title, user_id=target_user_id)
            if search_results:
                todo = search_results[0]
                todo_id = todo['id']

    # If no todo found and user_name is specified, get their most recent task
    if not todo and target_user_id:
        todos = todo_service.list(user_id=target_user_id, include_completed=False, limit=1)
        if todos:
            todo = todos[0]
            todo_id = todo['id']

    if not todo:
        response = "❌ I couldn't find which task to set reminders for. Try: 'remind Luke about cleanup task every 2 hours'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Store the reminder config in the database
    with get_session() as session:
        db_todo = session.query(Todo).filter(Todo.id == todo_id).first()
        if db_todo:
            db_todo.reminder_config = json.dumps(frequency_config)
            session.commit()

            # Generate confirmation message
            frequency_description = frequency_parser.describe(frequency_config)
            task_owner = ""
            if db_todo.user_id and db_todo.user_id != user['telegram_id']:
                owner_user = user_service.get_user(db_todo.user_id)
                if owner_user:
                    task_owner = f" for {owner_user.first_name}"

            response = (
                f"✅ Reminder set{task_owner}!\n\n"
                f"📋 Task: {db_todo.title}\n"
                f"⏰ Frequency: {frequency_description}\n\n"
                f"I'll remind about this task according to this schedule."
            )
        else:
            response = f"❌ Task #{todo_id} not found in database."

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


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
            user_service.add_conversation(user['telegram_id'], "assistant", response)
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
        user_service.add_conversation(user['telegram_id'], "assistant", response)


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
            user_service.add_conversation(user['telegram_id'], "assistant", response)
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
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_telegram_message(update, context, entities, original_message, existing_message=None, user=None):
    """Handle sending a Telegram message to another user."""
    user_service = UserService()
    owner_id = get("telegram.authorized_user_id")

    recipient_name = entities.get('recipient')
    message_body = entities.get('body') or entities.get('description') or original_message

    # Validate we have the minimum required info
    if not recipient_name:
        response = "❌ I need a recipient name to send a message.\nTry: 'Send John a message to call me back'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Check if recipient is the owner (by name/aliases)
    owner_aliases = get("telegram.owner_aliases", [])
    recipient_name_lower = recipient_name.lower()
    is_owner_recipient = False

    for alias in owner_aliases:
        if alias and recipient_name_lower == alias.lower():
            is_owner_recipient = True
            break

    # If recipient is owner, use owner's telegram_id
    if is_owner_recipient:
        recipient = {
            'telegram_id': owner_id,
            'first_name': get("telegram.owner_name", "Owner"),
            'full_name': get("telegram.owner_name", "Owner")
        }
    else:
        # Search for the recipient in known users
        all_users = user_service.get_all_users()
        recipient = None

        # Try to find recipient by first name, last name, or username
        for u in all_users:
            if (u['first_name'] and recipient_name_lower in u['first_name'].lower()) or \
               (u['last_name'] and recipient_name_lower in u['last_name'].lower()) or \
               (u['username'] and recipient_name_lower in u['username'].lower()):
                recipient = u
                break

    if not recipient:
        response = f"❌ I don't know anyone named '{recipient_name}'. They need to start a conversation with me first."
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    try:
        # Store the message in recipient's conversation history (incoming message)
        sender_name = user['full_name'] if user else "Someone"
        user_service.add_conversation(
            recipient['telegram_id'],
            "user",
            f"[Message from {sender_name}] {message_body}",
            channel="telegram"
        )

        # Send the Telegram message to the recipient
        message_text = f"📨 Message from {sender_name}:\n\n{message_body}"

        await context.bot.send_message(
            chat_id=recipient['telegram_id'],
            text=message_text
        )

        response = f"✅ Message sent to {recipient['first_name']}"

    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        response = f"❌ Failed to send message: {str(e)}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_general_chat(update, context, message, existing_message=None, user=None, conversation_history=None):
    """Handle general conversational messages."""
    from datetime import datetime
    import pytz
    from assistant.config import get

    user_service = UserService()
    prompt_service = PromptService()
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

    user_name = user['first_name'] if user else "User"

    # Load personality prompt from database
    personality_template = prompt_service.get_personality_prompt()

    # Format the prompt with current context
    system_context = f"""{personality_template}

Current date and time: {current_time}
User's name: {user_name}{history_context}"""

    response = llm.generate_response(message, system_context)

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)

    # Save response to conversation history
    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_meta_modify_prompt(update, context, entities, original_message, existing_message=None, user=None):
    """Handle meta-command to modify system prompts via natural language."""
    user_service = UserService()
    prompt_service = PromptService()
    llm = get_llm_service()

    # Only owner can modify prompts
    if not user['is_owner']:
        response = "⛔ Only the owner can modify system prompts."
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    prompt_type = entities.get('prompt_type', 'personality').lower()
    modification = entities.get('modification') or original_message

    # Validate prompt type
    if prompt_type not in ['personality', 'parser', 'command']:
        prompt_type = 'personality'  # Default

    # Map 'command' to 'parser'
    if prompt_type == 'command':
        prompt_type = 'parser'

    # Get current prompt
    if prompt_type == 'personality':
        current_prompt = prompt_service.get_personality_prompt()
        prompt_name = "Personality"
    else:
        current_prompt = prompt_service.get_parser_prompt()
        prompt_name = "Parser"

    # Use LLM to generate modified prompt
    meta_prompt = f"""You are modifying a system prompt based on user instructions.

Current {prompt_name} Prompt:
```
{current_prompt}
```

User's Modification Request:
{modification}

Generate an updated version of the prompt that incorporates the user's request while maintaining the essential structure and purpose of the original prompt.

Return ONLY the new prompt text, without any explanations or markdown formatting."""

    try:
        new_prompt = llm.process_message(meta_prompt)

        # Remove markdown code blocks if present
        import re
        new_prompt = re.sub(r'^```.*?\n', '', new_prompt, flags=re.MULTILINE)
        new_prompt = re.sub(r'\n```$', '', new_prompt)
        new_prompt = new_prompt.strip()

        # Save the new prompt
        if prompt_type == 'personality':
            success = prompt_service.set_personality_prompt(new_prompt)
        else:
            success = prompt_service.set_parser_prompt(new_prompt)

        if success:
            # Show preview
            preview = new_prompt[:400] + "..." if len(new_prompt) > 400 else new_prompt
            response = f"""✅ {prompt_name} prompt updated!

**Preview:**
```
{preview}
```

**What changed:** {modification}

The changes will take effect immediately. Use `/viewprompt {prompt_type}` to see the full prompt."""
        else:
            response = f"❌ Failed to update {prompt_name.lower()} prompt."

    except Exception as e:
        logger.error(f"Error modifying prompt: {e}")
        response = f"❌ Error modifying prompt: {str(e)}"

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_meta_configure(update, context, entities, original_message, existing_message=None, user=None):
    """Handle meta-command to configure system behavior."""
    user_service = UserService()
    behavior_service = BehaviorConfigService()

    # Only owner can configure behavior
    if not user['is_owner']:
        response = "⛔ Only the owner can configure system behavior."
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    config_key = entities.get('config_key')
    config_value = entities.get('config_value')

    # If no specific key/value extracted, list all configs
    if not config_key:
        configs = behavior_service.list_all()
        if configs:
            response = "**Current Behavior Configurations:**\n\n"
            for config in configs:
                category = f"[{config['category']}] " if config['category'] else ""
                response += f"{category}**{config['key']}** = `{config['value']}`"
                if config.get('description'):
                    response += f"\n  _{config['description']}_"
                response += "\n\n"
            response += "To change a setting, say: 'change [setting] to [value]'"
        else:
            response = "No behavior configurations set.\n\nExample: 'Set reminder check interval to 5 minutes'"

        if existing_message:
            await existing_message.edit_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Try to infer category from key
    category = None
    if 'reminder' in config_key.lower():
        category = 'reminders'
    elif 'follow' in config_key.lower() or 'task' in config_key.lower():
        category = 'tasks'
    elif 'email' in config_key.lower():
        category = 'email'
    elif 'calendar' in config_key.lower():
        category = 'calendar'

    # Set the configuration
    success = behavior_service.set(
        key=config_key,
        value=config_value,
        category=category,
        updated_by=f"{user['first_name']} (via message)"
    )

    if success:
        # Special handling for morning briefing time - reschedule immediately
        if 'morning_briefing_time' in config_key.lower() or 'briefing' in config_key.lower():
            try:
                from assistant.scheduler.jobs import reschedule_morning_briefing
                # Get the application from context
                reschedule_success = reschedule_morning_briefing(context.application, config_value)
                if reschedule_success:
                    response = f"""✅ Morning briefing time updated!

**Morning Briefing** will now run at `{config_value}` (Montreal time)

The schedule has been updated immediately - you'll receive your next briefing at the new time."""
                else:
                    response = f"""⚠️ Configuration saved but rescheduling failed.

**{config_key}** = `{config_value}`

Please restart the bot for changes to take effect."""
            except Exception as e:
                logger.error(f"Error rescheduling morning briefing: {e}")
                response = f"""⚠️ Configuration saved but rescheduling failed: {str(e)}

**{config_key}** = `{config_value}`

Please restart the bot for changes to take effect."""
        else:
            response = f"""✅ Configuration updated!

**{config_key}** = `{config_value}`

This setting will be used by the system immediately where applicable."""
    else:
        response = f"❌ Failed to update configuration: {config_key}"

    if existing_message:
        await existing_message.edit_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_meta_extend(update, context, entities, original_message, existing_message=None, user=None):
    """Handle meta-command to generate new code/features."""
    user_service = UserService()
    llm = get_llm_service()

    # Only owner can extend functionality
    if not user['is_owner']:
        response = "⛔ Only the owner can extend system functionality."
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    feature_name = entities.get('feature_name') or 'new_feature'
    feature_description = entities.get('feature_description') or entities.get('description') or original_message

    # Generate code using LLM
    code_gen_prompt = f"""You are generating a new handler function for a Telegram bot assistant.

**Feature Request:**
{feature_description}

**Architecture Context:**
- Bot uses python-telegram-bot library
- Handlers are async functions with signature: async def handle_X(update, context, entities, original_message, existing_message=None, user=None)
- Services available: TodoService, CalendarService, EmailService, UserService, PromptService, BehaviorConfigService
- Database uses SQLAlchemy ORM
- User info comes from user dict with keys: telegram_id, first_name, is_owner, is_authorized

**Your Task:**
Generate a complete, working handler function for this feature. Include:
1. Imports if needed (relative imports from assistant.services or assistant.db)
2. The handler function with proper error handling
3. User authorization checks if appropriate
4. Conversation history logging
5. Comments explaining the logic

Return ONLY the Python code for the handler function, properly formatted."""

    try:
        generated_code = llm.process_message(code_gen_prompt)

        # Clean up markdown code blocks
        import re
        generated_code = re.sub(r'^```python\n', '', generated_code)
        generated_code = re.sub(r'^```\n', '', generated_code)
        generated_code = re.sub(r'\n```$', '', generated_code)
        generated_code = generated_code.strip()

        # Save to a new file in assistant/bot/handlers/
        file_name = f"meta_{feature_name.lower().replace(' ', '_')}.py"
        file_path = f"/home/ja/projects/personal_assistant/assistant/bot/handlers/{file_name}"

        # Show preview first
        preview = generated_code[:800] + "\n\n... (truncated)" if len(generated_code) > 800 else generated_code

        response = f"""🔧 **Feature Generation Complete**

**Feature:** {feature_name}

**Generated Code Preview:**
```python
{preview}
```

**Next Steps:**
1. Review the code above
2. The full code has been saved to: `{file_path}`
3. To activate:
   - Add the handler to `bot/main.py`
   - Add the intent to the parser prompt
   - Restart the bot: `sudo systemctl restart personal-assistant`

Would you like me to save this code? Reply 'yes' to confirm."""

        if existing_message:
            await existing_message.edit_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

        # Store generated code in user's conversation for potential retrieval
        user_service.add_conversation(
            user['telegram_id'],
            "assistant",
            f"[Generated code for {feature_name}]\n\n{generated_code}"
        )

        # Also save to file immediately (owner can review/delete if unwanted)
        try:
            with open(file_path, 'w') as f:
                f.write(f'"""{feature_description}"""\n\n')
                f.write(generated_code)
            logger.info(f"Saved generated handler to {file_path}")
        except Exception as e:
            logger.error(f"Error saving generated code: {e}")

    except Exception as e:
        logger.error(f"Error generating code: {e}")
        response = f"❌ Error generating code: {str(e)}"

        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)

    if user:
        user_service.add_conversation(user['telegram_id'], "assistant", response)


async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authorize a user to execute tasks (owner only)."""
    user_service = UserService()

    # Get user ID from command
    if not context.args:
        await update.message.reply_text("Usage: /authorize <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        return

    # Get user details
    user = user_service.get_user_by_id(user_id)
    if not user:
        await update.message.reply_text(f"❌ User with ID {user_id} not found.")
        return

    # Check if already authorized
    if user['is_authorized']:
        await update.message.reply_text(f"ℹ️ {user['first_name']} is already authorized.")
        return

    # Authorize the user
    success = user_service.authorize_user(user_id)

    if success:
        await update.message.reply_text(
            f"✅ Authorized {user['first_name']} (ID: {user_id})\n\n"
            f"They can now execute tasks through {BOT_NAME}."
        )

        # Notify the user they've been authorized
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 You've been authorized by my owner!\n\n"
                     f"You can now ask me to manage your todos and set up reminders. "
                     f"Try saying things like:\n"
                     f"• 'Add a todo: buy groceries'\n"
                     f"• 'Show my tasks'\n"
                     f"• 'Remind me tomorrow at 3pm to call mom'"
            )
        except Exception as e:
            logger.warning(f"Could not notify user {user_id} about authorization: {e}")
    else:
        await update.message.reply_text(f"❌ Failed to authorize user.")


async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block/revoke authorization for a user (owner only)."""
    user_service = UserService()

    # Get user ID from command
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        return

    # Get user details
    user = user_service.get_user_by_id(user_id)
    if not user:
        await update.message.reply_text(f"❌ User with ID {user_id} not found.")
        return

    # Check if user is owner
    if user['is_owner']:
        await update.message.reply_text("❌ Cannot block the owner.")
        return

    # Check if already blocked
    if not user['is_authorized']:
        await update.message.reply_text(f"ℹ️ {user['first_name']} is already blocked.")
        return

    # Revoke authorization
    success = user_service.revoke_authorization(user_id)

    if success:
        await update.message.reply_text(
            f"🚫 Blocked {user['first_name']} (ID: {user_id})\n\n"
            f"They can no longer execute tasks through {BOT_NAME}."
        )

        # Notify the user they've been blocked
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Your authorization has been revoked.\n\n"
                     f"You can still send messages, but I cannot execute tasks on your behalf anymore."
            )
        except Exception as e:
            logger.warning(f"Could not notify user {user_id} about revocation: {e}")
    else:
        await update.message.reply_text(f"❌ Failed to block user.")


async def view_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View current system prompts (owner only)."""
    prompt_service = PromptService()

    if not context.args:
        # Show both prompts
        personality = prompt_service.get_personality_prompt()
        parser = prompt_service.get_parser_prompt()

        response = f"""**Current System Prompts:**

📝 **Personality Prompt** (use `/viewprompt personality` to see full):
```
{personality[:200]}...
```

🔍 **Parser Prompt** (use `/viewprompt parser` to see full):
```
{parser[:200]}...
```

**Commands:**
• `/viewprompt personality` - View full personality prompt
• `/viewprompt parser` - View full parser prompt
• `/setprompt <type>` - Set a new prompt (interactive)
• `/resetprompt <type>` - Reset to default"""

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    prompt_type = context.args[0].lower()

    if prompt_type in ['personality', 'p']:
        prompt = prompt_service.get_personality_prompt()
        response = f"**Current Personality Prompt:**\n\n```\n{prompt}\n```"
    elif prompt_type in ['parser', 'command', 'c']:
        prompt = prompt_service.get_parser_prompt()
        response = f"**Current Parser Prompt:**\n\n```\n{prompt}\n```"
    else:
        response = "❌ Invalid prompt type. Use 'personality' or 'parser'."

    await update.message.reply_text(response, parse_mode="Markdown")


async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a system prompt (owner only)."""
    prompt_service = PromptService()

    # Get the full message text after /setprompt <type>
    if not context.args:
        response = """**Set System Prompt**

Usage: `/setprompt <type> <new_prompt>`

Types:
• `personality` - Conversational personality prompt
• `parser` - Command parsing prompt

Example:
```
/setprompt personality You are a friendly and helpful assistant named Jarvis.
```

Or send the prompt in a follow-up message after using:
`/setprompt personality`"""
        await update.message.reply_text(response, parse_mode="Markdown")
        return

    prompt_type = context.args[0].lower()

    # Get the new prompt (everything after the type)
    message_parts = update.message.text.split(maxsplit=2)
    if len(message_parts) < 3:
        response = f"""**Ready to set {prompt_type} prompt**

Please send your new prompt text in your next message."""
        await update.message.reply_text(response, parse_mode="Markdown")
        # TODO: Implement state management for multi-message prompt setting
        return

    new_prompt = message_parts[2]

    if prompt_type in ['personality', 'p']:
        success = prompt_service.set_personality_prompt(new_prompt)
        prompt_name = "personality"
    elif prompt_type in ['parser', 'command', 'c']:
        success = prompt_service.set_parser_prompt(new_prompt)
        prompt_name = "parser"
    else:
        await update.message.reply_text("❌ Invalid prompt type. Use 'personality' or 'parser'.")
        return

    if success:
        response = f"""✅ {prompt_name.capitalize()} prompt updated!

New prompt:
```
{new_prompt[:300]}{"..." if len(new_prompt) > 300 else ""}
```

The changes will take effect immediately for new conversations."""
    else:
        response = f"❌ Failed to update {prompt_name} prompt."

    await update.message.reply_text(response, parse_mode="Markdown")


async def reset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset a system prompt to default (owner only)."""
    prompt_service = PromptService()

    if not context.args:
        response = """**Reset System Prompt**

Usage: `/resetprompt <type>`

Types:
• `personality` - Reset personality prompt to default
• `parser` - Reset parser prompt to default
• `all` - Reset both prompts to defaults"""
        await update.message.reply_text(response, parse_mode="Markdown")
        return

    prompt_type = context.args[0].lower()

    if prompt_type in ['personality', 'p']:
        success = prompt_service.reset_personality_prompt()
        prompt_name = "personality"
    elif prompt_type in ['parser', 'command', 'c']:
        success = prompt_service.reset_parser_prompt()
        prompt_name = "parser"
    elif prompt_type == 'all':
        success1 = prompt_service.reset_personality_prompt()
        success2 = prompt_service.reset_parser_prompt()
        success = success1 and success2
        prompt_name = "all"
    else:
        await update.message.reply_text("❌ Invalid prompt type. Use 'personality', 'parser', or 'all'.")
        return

    if success:
        response = f"✅ {prompt_name.capitalize()} prompt(s) reset to default!"
    else:
        response = f"❌ Failed to reset {prompt_name} prompt(s)."

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_web_search(update, context, entities, original_message, existing_message=None, user=None):
    """Handle web search requests."""
    from assistant.services import ResearchService, UserService
    
    user_service = UserService()
    query = entities.get('query')
    max_results = entities.get('max_results', 5)
    summarize = entities.get('summarize', True)  # Default to True for better UX

    if not query:
        response = "❌ Please provide a search query.\n\nExample: 'Search for best Python frameworks 2025'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Show searching message
    search_msg = f"🔍 Searching the web for: *{query}*..."
    if existing_message:
        await existing_message.edit_text(search_msg, parse_mode="Markdown")
    else:
        existing_message = await update.message.reply_text(search_msg, parse_mode="Markdown")

    try:
        # Get research service with LLM
        llm = get_llm_service()
        research = ResearchService(llm_service=llm)

        # Perform search
        result = research.search(query=query, max_results=max_results, summarize=summarize)

        if result.get('error'):
            response = f"❌ Search error: {result['error']}"
        elif not result.get('results'):
            response = f"🔍 No results found for: *{query}*"
        else:
            # Format response
            response = f"🔍 **Search Results for:** {query}\n\n"

            # Add summary if available
            if result.get('summary'):
                response += f"**Summary:**\n{result['summary']}\n\n"
                response += "---\n\n"

            # Add top results
            response += f"**Top {len(result['results'])} Results:**\n\n"
            for i, res in enumerate(result['results'][:5], 1):
                response += f"{i}. **{res['title']}**\n"
                if res.get('snippet'):
                    response += f"   _{res['snippet'][:150]}..._\n"
                response += f"   🔗 {res['url']}\n\n"

        await existing_message.edit_text(response, parse_mode="Markdown")
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)

    except Exception as e:
        logger.error(f"Web search error: {e}")
        response = f"❌ Error performing search: {str(e)}"
        await existing_message.edit_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_web_fetch(update, context, entities, original_message, existing_message=None, user=None):
    """Handle URL fetching requests."""
    from assistant.services import ResearchService, UserService
    
    user_service = UserService()
    url = entities.get('url')
    summarize = entities.get('summarize', True)

    if not url:
        response = "❌ Please provide a URL to fetch.\n\nExample: 'Fetch https://example.com/article'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Show fetching message
    fetch_msg = f"📄 Fetching content from URL..."
    if existing_message:
        await existing_message.edit_text(fetch_msg)
    else:
        existing_message = await update.message.reply_text(fetch_msg)

    try:
        # Get research service with LLM
        llm = get_llm_service()
        research = ResearchService(llm_service=llm)

        # Fetch URL
        result = research.fetch(url=url, extract="text", summarize=summarize)

        if result.get('error'):
            response = f"❌ Fetch error: {result['error']}"
        else:
            response = f"📄 **{result.get('title', 'Fetched Content')}**\n\n"
            response += f"🔗 {url}\n\n"

            if result.get('summary'):
                response += f"**Summary:**\n{result['summary']}\n\n"
            elif result.get('content'):
                # Show first 500 chars if no summary
                content_preview = result['content'][:500]
                response += f"**Content:**\n{content_preview}...\n\n"
                response += f"_({result.get('content_length', 0)} characters total)_"

        await existing_message.edit_text(response, parse_mode="Markdown")
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)

    except Exception as e:
        logger.error(f"Web fetch error: {e}")
        response = f"❌ Error fetching URL: {str(e)}"
        await existing_message.edit_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)


async def handle_web_ask(update, context, entities, original_message, existing_message=None, user=None):
    """Handle research-based questions."""
    from assistant.services import ResearchService, UserService
    
    user_service = UserService()
    question = entities.get('query')

    if not question:
        response = "❌ Please provide a question.\n\nExample: 'What's the weather in Montreal today?'"
        if existing_message:
            await existing_message.edit_text(response)
        else:
            await update.message.reply_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
        return

    # Show researching message
    research_msg = f"🔬 Researching: *{question}*..."
    if existing_message:
        await existing_message.edit_text(research_msg, parse_mode="Markdown")
    else:
        existing_message = await update.message.reply_text(research_msg, parse_mode="Markdown")

    try:
        # Get research service with LLM
        llm = get_llm_service()
        research = ResearchService(llm_service=llm)

        # Research and answer
        result = research.ask(question=question, sources=["web"], return_citations=True)

        if result.get('error'):
            response = f"❌ Research error: {result['error']}"
        else:
            response = f"**Question:** {question}\n\n"
            response += f"**Answer:**\n{result.get('answer', 'No answer found.')}\n\n"

            # Add citations if available
            if result.get('citations'):
                response += "**Sources:**\n"
                for i, citation in enumerate(result['citations'][:3], 1):
                    response += f"{i}. [{citation['title']}]({citation['url']})\n"

        await existing_message.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)

    except Exception as e:
        logger.error(f"Web ask error: {e}")
        response = f"❌ Error researching question: {str(e)}"
        await existing_message.edit_text(response)
        if user:
            user_service.add_conversation(user['telegram_id'], "assistant", response)
