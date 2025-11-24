"""Todo command handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from dateutil import parser as date_parser

from assistant.services import TodoService


async def list_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todo and /todos commands."""
    try:
        service = TodoService()

        # Parse optional filters from args
        priority = None
        include_completed = False

        if context.args:
            for arg in context.args:
                if arg in ["low", "medium", "high", "urgent"]:
                    priority = arg
                elif arg == "all":
                    include_completed = True

        todos = service.list(priority=priority, include_completed=include_completed)

        if not todos:
            await update.message.reply_text("No todos found. Add one with /add <task>")
            return

        # Format output
        text = "*Your Todos:*\n\n"
        for todo in todos:
            status_icon = {
                "pending": "",
                "in_progress": "",
                "completed": "",
            }.get(todo["status"], "")

            priority_icon = {
                "urgent": " !!",
                "high": " !",
                "medium": "",
                "low": "",
            }.get(todo["priority"], "")

            due = ""
            if todo["due_date"]:
                from dateutil import parser
                dt = parser.parse(todo["due_date"])
                due = f" (due: {dt.strftime('%m/%d')})"

            text += f"{status_icon} `{todo['id']}` {todo['title']}{priority_icon}{due}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error listing todos: {e}")


async def add_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /add <task> [priority:high] [due:tomorrow]\n\n"
            "Examples:\n"
            "/add Buy groceries\n"
            "/add Call John priority:urgent\n"
            "/add Submit report due:friday"
        )
        return

    try:
        service = TodoService()

        # Parse arguments
        args = " ".join(context.args)
        title = args
        priority = "medium"
        due_date = None
        tags = []

        # Extract priority
        for p in ["urgent", "high", "medium", "low"]:
            if f"priority:{p}" in args:
                priority = p
                title = title.replace(f"priority:{p}", "").strip()

        # Extract due date
        import re
        due_match = re.search(r"due:(\S+)", args)
        if due_match:
            due_str = due_match.group(1)
            title = title.replace(f"due:{due_str}", "").strip()
            try:
                due_date = date_parser.parse(due_str, fuzzy=True)
            except Exception:
                pass

        # Extract tags
        tag_matches = re.findall(r"#(\w+)", args)
        if tag_matches:
            tags = tag_matches
            for tag in tag_matches:
                title = title.replace(f"#{tag}", "").strip()

        todo = service.add(
            title=title.strip(),
            priority=priority,
            due_date=due_date,
            tags=tags if tags else None,
        )

        await update.message.reply_text(
            f"Added todo #{todo['id']}: {todo['title']}"
        )

    except Exception as e:
        await update.message.reply_text(f"Error adding todo: {e}")


async def complete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command."""
    if not context.args:
        await update.message.reply_text("Usage: /done <id>")
        return

    try:
        service = TodoService()
        todo_id = int(context.args[0])

        result = service.complete(todo_id)

        if result:
            await update.message.reply_text(f"Completed: {result['title']}")
        else:
            await update.message.reply_text(f"Todo #{todo_id} not found")

    except ValueError:
        await update.message.reply_text("Invalid todo ID")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def delete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deltodo command."""
    if not context.args:
        await update.message.reply_text("Usage: /deltodo <id>")
        return

    try:
        service = TodoService()
        todo_id = int(context.args[0])

        if service.delete(todo_id):
            await update.message.reply_text(f"Deleted todo #{todo_id}")
        else:
            await update.message.reply_text(f"Todo #{todo_id} not found")

    except ValueError:
        await update.message.reply_text("Invalid todo ID")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def search_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todosearch command."""
    if not context.args:
        await update.message.reply_text("Usage: /todosearch <query>")
        return

    try:
        service = TodoService()
        query = " ".join(context.args)

        todos = service.search(query)

        if not todos:
            await update.message.reply_text(f"No todos matching '{query}'")
            return

        text = f"*Search results for '{query}':*\n\n"
        for todo in todos:
            text += f"`{todo['id']}` {todo['title']} ({todo['status']})\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def focus_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /focus command - set or view active task."""
    try:
        service = TodoService()

        # No args - show current active task
        if not context.args:
            active = service.get_active_task()
            if active:
                priority_icon = {
                    "urgent": " !!",
                    "high": " !",
                    "medium": "",
                    "low": "",
                }.get(active["priority"], "")

                due = ""
                if active["due_date"]:
                    from dateutil import parser
                    dt = parser.parse(active["due_date"])
                    due = f"\nDue: {dt.strftime('%B %d, %H:%M')}"

                text = (
                    f"*Currently focused on:*\n\n"
                    f"`{active['id']}` {active['title']}{priority_icon}{due}"
                )
                if active.get("description"):
                    text += f"\n\n{active['description']}"

                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    "No active task. Set one with /focus <id>\n"
                    "Use /todo to see your tasks."
                )
            return

        # Set active task
        todo_id = int(context.args[0])
        result = service.set_active_task(todo_id)

        if result:
            await update.message.reply_text(
                f"Now focused on: *{result['title']}*\n\n"
                f"Stay on track! Use /focus to see this again.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"Todo #{todo_id} not found")

    except ValueError:
        await update.message.reply_text("Usage: /focus [id]")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def unfocus_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unfocus command - clear active task."""
    try:
        service = TodoService()
        active = service.get_active_task()

        if active:
            service.clear_active_task()
            await update.message.reply_text(
                f"Cleared focus from: {active['title']}"
            )
        else:
            await update.message.reply_text("No active task to clear")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
