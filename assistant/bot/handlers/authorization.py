"""User authorization handlers."""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from assistant.db import get_session, User
from assistant.config import get as get_config

logger = logging.getLogger(__name__)


async def handle_unauthorized_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages from unauthorized users."""
    user = update.effective_user
    owner_id = get_config("telegram.authorized_user_id")

    if not user:
        return

    # Check if user is already authorized
    with get_session() as session:
        db_user = session.query(User).filter_by(telegram_id=user.id).first()

        if db_user and db_user.is_authorized:
            # User is authorized, this shouldn't happen
            return

        # Create or update user record
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                is_authorized=False,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            session.add(db_user)
            session.commit()
            logger.info(f"New user contacted Jarvis: {user.first_name} (@{user.username}, ID: {user.id})")
        else:
            # Update last seen
            db_user.last_seen = datetime.utcnow()
            session.commit()

    # Send waiting message to unauthorized user
    await update.message.reply_text(
        "👋 Hello! I'm Jarvis.\n\n"
        "Your request has been forwarded to my owner for approval.\n"
        "Please wait while they review your access request.\n\n"
        "You'll be notified once your access is approved."
    )

    # Send authorization request to owner
    user_info = (
        f"🔔 *New Authorization Request*\n\n"
        f"**Name:** {user.first_name}"
    )

    if user.last_name:
        user_info += f" {user.last_name}"

    user_info += f"\n**Username:** @{user.username}" if user.username else "\n**Username:** _(none)_"
    user_info += f"\n**User ID:** `{user.id}`"
    user_info += f"\n\n**Message:** {update.message.text[:200]}"

    # Create inline keyboard for approval
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve as Employee", callback_data=f"auth_approve_employee_{user.id}"),
        ],
        [
            InlineKeyboardButton("👤 Approve as Contact", callback_data=f"auth_approve_contact_{user.id}"),
        ],
        [
            InlineKeyboardButton("❌ Deny", callback_data=f"auth_deny_{user.id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=owner_id,
            text=user_info,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending authorization request to owner: {e}")


async def handle_authorization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle authorization approval/denial callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    owner_id = get_config("telegram.authorized_user_id")

    # Verify this is the owner
    if query.from_user.id != owner_id:
        await query.edit_message_text("❌ You are not authorized to perform this action.")
        return

    # Parse callback data
    parts = data.split("_")
    action = parts[1]  # approve or deny
    user_id = int(parts[-1])  # User ID being authorized/denied

    with get_session() as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if not user:
            await query.edit_message_text("❌ User not found in database.")
            return

        if action == "deny":
            # Deny authorization
            await query.edit_message_text(
                f"❌ *Access Denied*\n\n"
                f"You denied access for {user.first_name} (@{user.username or 'no username'}).\n"
                f"They will not be able to interact with Jarvis.",
                parse_mode="Markdown"
            )

            # Notify the denied user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Your access request has been denied.\n\n"
                         "If you believe this is an error, please contact the owner directly."
                )
            except Exception as e:
                logger.error(f"Error notifying denied user {user_id}: {e}")

        elif action == "approve":
            # Get role from callback data
            role = parts[2]  # employee or contact

            # Authorize user
            user.is_authorized = True
            user.role = role
            user.authorized_at = datetime.utcnow()
            user.authorized_by = owner_id
            session.commit()

            logger.info(f"User {user.first_name} (ID: {user_id}) authorized as {role} by owner")

            # Update message to show approval
            role_emoji = "👔" if role == "employee" else "👤"
            await query.edit_message_text(
                f"✅ *Access Approved*\n\n"
                f"You authorized {user.first_name} (@{user.username or 'no username'}) as:\n"
                f"{role_emoji} **{role.capitalize()}**\n\n"
                f"They can now interact with Jarvis.",
                parse_mode="Markdown"
            )

            # Notify the approved user
            role_description = {
                "employee": "You can now:\n- Be assigned tasks\n- Receive reminders\n- Send messages\n- Use all Jarvis features",
                "contact": "You can now:\n- Send messages to the owner\n- Use basic Jarvis features"
            }

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ *Access Approved!*\n\n"
                         f"You have been granted access to Jarvis as a **{role.capitalize()}**.\n\n"
                         f"{role_description.get(role, 'You can now use Jarvis.')}\n\n"
                         f"Type /help to see available commands.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error notifying approved user {user_id}: {e}")


def get_authorization_handlers():
    """Get list of authorization handlers to register."""
    return [
        CallbackQueryHandler(handle_authorization_callback, pattern="^auth_(approve|deny)_"),
    ]
