"""Email command handlers."""

import re
from telegram import Update
from telegram.ext import ContextTypes

from assistant.services import EmailService


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters for Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


async def list_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /email command - list recent emails."""
    try:
        service = EmailService()

        max_results = 10
        if context.args:
            try:
                max_results = int(context.args[0])
            except ValueError:
                pass

        emails = service.list_messages(max_results=max_results)

        if not emails:
            await update.message.reply_text("No emails found")
            return

        text = "Recent Emails:\n\n"
        for email in emails:
            unread = "[NEW] " if email["is_unread"] else ""
            sender = email["from"].split("<")[0].strip()[:20]
            subject = email["subject"][:40]
            text += f"{unread}[{email['id'][:8]}] {sender}\n  {subject}\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def unread_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unread command."""
    try:
        service = EmailService()
        emails = service.get_unread(max_results=20)

        if not emails:
            await update.message.reply_text("No unread emails!")
            return

        text = f"Unread Emails ({len(emails)}):\n\n"
        for email in emails:
            sender = email["from"].split("<")[0].strip()[:25]
            subject = email["subject"][:35]
            text += f"[{email['id'][:8]}] {sender}\n  {subject}\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def read_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /read command - read full email."""
    if not context.args:
        await update.message.reply_text("Usage: /read <email_id>")
        return

    try:
        service = EmailService()
        email_id = context.args[0]

        # Get email with body
        email = service.get_message(email_id)
        body = service.get_message_body(email_id)

        # Mark as read
        service.mark_read(email_id)

        text = f"*From:* {email['from']}\n"
        text += f"*To:* {email['to']}\n"
        text += f"*Date:* {email['date']}\n"
        text += f"*Subject:* {email['subject']}\n\n"
        text += "─" * 20 + "\n\n"

        # Truncate body if too long
        if len(body) > 3000:
            body = body[:3000] + "\n\n... (truncated)"

        text += body

        # Split into multiple messages if needed
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await update.message.reply_text(text[i:i+4000])
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def send_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /send command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /send <to> | <subject> | <body>\n\n"
            "Example:\n"
            "/send john@example.com | Meeting tomorrow | Hi John, can we meet tomorrow at 3pm?"
        )
        return

    try:
        # Parse the arguments
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) < 3:
            await update.message.reply_text(
                "Please provide: /send <to> | <subject> | <body>"
            )
            return

        to, subject, body = parts[0], parts[1], "|".join(parts[2:])

        service = EmailService()
        result = service.send_message(to=to, subject=subject, body=body)

        await update.message.reply_text(
            f"Email sent to {to}\nSubject: {subject}"
        )

    except Exception as e:
        await update.message.reply_text(f"Error sending email: {e}")


async def reply_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reply command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /reply <email_id> | <message>\n\n"
            "Example:\n"
            "/reply abc12345 | Thanks for the update, I'll review it tomorrow."
        )
        return

    try:
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) < 2:
            await update.message.reply_text(
                "Please provide: /reply <email_id> | <message>"
            )
            return

        email_id, body = parts[0], "|".join(parts[1:])

        service = EmailService()
        result = service.reply(message_id=email_id, body=body)

        await update.message.reply_text("Reply sent!")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def archive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /archive command."""
    if not context.args:
        await update.message.reply_text("Usage: /archive <email_id>")
        return

    try:
        service = EmailService()
        email_id = context.args[0]

        service.archive(email_id)
        await update.message.reply_text(f"Archived email {email_id[:8]}...")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def search_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /emailsearch command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /emailsearch <query>\n\n"
            "Examples:\n"
            "/emailsearch from:john@example.com\n"
            "/emailsearch subject:invoice\n"
            "/emailsearch is:unread newer_than:7d"
        )
        return

    try:
        service = EmailService()
        query = " ".join(context.args)

        emails = service.search(query, max_results=15)

        if not emails:
            await update.message.reply_text(f"No emails matching: {query}")
            return

        text = f"*Search results for '{query}':*\n\n"
        for email in emails:
            sender = email["from"].split("<")[0].strip()[:20]
            subject = email["subject"][:35]
            text += f"`{email['id'][:8]}` {sender}\n  {subject}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
