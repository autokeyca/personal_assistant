"""Handlers for notes module."""


async def handle_note_add(update, context, entities, original_message, existing_message=None, user=None):
    """Add a new note."""
    note_text = entities.get('title') or entities.get('description') or original_message

    # In a real implementation, save to database
    response = f"📝 Note saved: {note_text}"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)


async def handle_note_list(update, context, entities, original_message, existing_message=None, user=None):
    """List all notes."""
    # In a real implementation, fetch from database
    response = "📋 Your Notes:\n\n• Buy milk\n• Call Sarah\n• Finish report"

    if existing_message:
        await existing_message.edit_text(response)
    else:
        await update.message.reply_text(response)
