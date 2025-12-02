"""Prompt management service for storing and retrieving system prompts."""

import logging
from typing import Optional
from assistant.db import get_session, Setting

logger = logging.getLogger(__name__)

# Default system prompts
DEFAULT_PERSONALITY_PROMPT = """You are Jarvis, a polite and helpful personal assistant bot.
You help manage todos, calendar, email, and reminders.
When users ask questions or chat with you, be friendly and professional.
If they're asking about their schedule, todos, or want to manage something, guide them to use natural language.
Keep responses concise and friendly."""

DEFAULT_PARSER_PROMPT = """Parse this message and extract the intent and entities.
{context}
Return ONLY a JSON object with this structure:
{{
    "intent": "one of: todo_add, todo_list, todo_complete, todo_delete, todo_focus, todo_set_reminder, calendar_add, calendar_list, reminder_add, telegram_message, email_send, email_check, web_search, web_fetch, web_ask, help, general_chat, meta_modify_prompt, meta_configure, meta_extend",
    "entities": {{
        "title": "extracted title/subject",
        "description": "extracted description or message content",
        "date": "extracted date in YYYY-MM-DD format",
        "time": "extracted time in HH:MM format",
        "priority": "high/medium/low if mentioned",
        "recipient": "recipient name or identifier",
        "subject": "email subject line if mentioned",
        "body": "message body/content",
        "duration": "event duration if mentioned",
        "for_user": "user name if task is for someone (e.g., 'for Sarah' → 'Sarah')",
        "user_name": "user name when querying someone's todos (e.g., 'Sarah's todos' → 'Sarah')",
        "intensity": "follow-up intensity if mentioned (none/low/medium/high/urgent)",
        "frequency": "for todo_set_reminder: natural language frequency (e.g., 'every 2 hours during business hours')",
        "prompt_type": "for meta_modify_prompt: personality or parser",
        "modification": "for meta_modify_prompt: description of what to change",
        "config_key": "for meta_configure: setting name to change",
        "config_value": "for meta_configure: new value for the setting",
        "feature_name": "for meta_extend: name of feature to add",
        "feature_description": "for meta_extend: detailed requirements",
        "query": "for web_search/web_ask: search query or question",
        "url": "for web_fetch: URL to fetch content from",
        "max_results": "for web_search: number of results (default 5)",
        "summarize": "for web_search/web_fetch: whether to generate summary (true/false)"
    }},
    "confidence": 0.95
}}

Message: {message}

Important:
- Only include entities that are actually present in the message
- Use null for missing entities
- For dates, interpret "tomorrow", "next week", etc. relative to today
- For times, use 24-hour format
- CRITICAL: Pronoun and context resolution:
  - When user says "it", "that", "this" referring to a task, look at the conversation context
  - If the assistant just sent a task notification (e.g., "New task from X: Buy flowers"), extract the task title
  - "I've completed it" after task notification → extract the task title from context
  - "Done with that" → extract task from most recent assistant message
  - "Finished it" → look for task mentioned in last assistant message
  - Extract task titles, IDs, or descriptions from the conversation context when pronouns are used
- CRITICAL: Confirmation responses:
  - When user says "yes", "confirm", "ok", "correct" after assistant asked about completing a task
  - Look for task number (#12 or "12") in the most recent assistant message
  - Extract that number as the title for todo_complete intent
  - Example: Assistant asks "Did you mean: #12 Buy milk?", User says "yes" → intent: todo_complete, title: "12"
- CRITICAL: Multi-user todo commands:
  - "add task for Sarah: finish report" → intent: todo_add, for_user: "Sarah", title: "finish report"
  - "show Sarah's todos" → intent: todo_list, user_name: "Sarah"
  - "what is Mike working on" → intent: todo_list, user_name: "Mike"
  - "show all tasks" → intent: todo_list, user_name: "all"
  - "mark Sarah's task 5 complete" → intent: todo_complete, user_name: "Sarah", title: "5"
- CRITICAL: Use "todo_focus" when user wants to focus on a task (e.g., "focus on 9", "focus 9", "focus on buy milk task")
  - For "focus 9" or "focus on 9", extract "9" as the title
  - For "focus on buy milk", extract "buy milk" as the title
- CRITICAL: Use "todo_set_reminder" when user wants to set a custom reminder schedule for a task
  - Examples: "remind Sarah about her task every 2 hours", "remind Luke every hour during business hours", "set reminder for cleanup task every 30 minutes"
  - Extract the task identifier (user name, task title, or task ID) and the frequency expression
  - If user mentions a recipient/user, extract as "for_user" or "user_name"
  - Extract the full frequency expression as "frequency" (e.g., "every 2 hours during business hours", "every day at 9am", "every 30 minutes on weekdays")
  - If context shows a recent task was added for someone, use that task
- CRITICAL: Use "telegram_message" for sending Telegram messages (e.g., "send X a message", "tell Y that...", "message Z")
- CRITICAL: Use "email_send" ONLY when explicitly mentioning "email" or when recipient is an email address
- CRITICAL: When user says "respond" without specifying channel, look at the conversation context:
  - If last message was via telegram channel → use "telegram_message"
  - If last message was via email channel → use "email_send"
  - Use the sender's name from context as the recipient
- CRITICAL: For "reminder_add" intent, extract BOTH time and the reminder message:
  - "remind me in 15 minutes to call mom" → time: "in 15 minutes", title: "call mom"
  - "remind me tomorrow at 3pm about the meeting" → time: "tomorrow at 3pm", title: "about the meeting"
  - "remind me at 5pm" (no message) → still extract intent, but leave title/description null
  - The reminder message should be extracted to "title" or "description" fields
- CRITICAL: Meta-programming intents (system modification):
  - Use "meta_modify_prompt" when user wants to change how the assistant behaves/talks
    Examples: "be more formal", "change your personality", "stop suggesting priorities"
    Extract: prompt_type (personality/parser), modification (what to change)
  - Use "meta_configure" when user wants to change system settings/parameters
    Examples: "change reminder frequency to 30 minutes", "set default priority to high"
    Extract: config_key (what setting), config_value (new value)
  - Use "meta_extend" when user wants to add new features/commands/capabilities
    Examples: "add expense tracking", "create a habit tracker", "add pomodoro timer"
    Extract: feature_name (what to build), description (detailed requirements)
- CRITICAL: Web research intents:
  - Use "web_search" when user wants to search the web or find information online
    Examples: "search for best restaurants in Montreal", "find information about Python async", "look up AI news"
    Extract: query (the search query), max_results (if specified), summarize (true if they want a summary)
  - Use "web_fetch" when user wants to read/extract content from a specific URL
    Examples: "fetch https://example.com", "read this article: [URL]", "get content from [URL]"
    Extract: url (the URL to fetch), summarize (true if they want a summary)
  - Use "web_ask" when user asks a question that requires current/real-time information
    Examples: "what's the weather in Montreal", "who won the game yesterday", "what are the latest AI developments"
    Extract: query (the question to answer)
- If the message is conversational/chat, use "general_chat" intent"""


class PromptService:
    """Service for managing system prompts."""

    PERSONALITY_KEY = "system_prompt_personality"
    PARSER_KEY = "system_prompt_parser"

    def get_personality_prompt(self) -> str:
        """Get the personality/conversational system prompt."""
        with get_session() as session:
            setting = session.query(Setting).filter_by(key=self.PERSONALITY_KEY).first()
            if setting and setting.value:
                return setting.value
            return DEFAULT_PERSONALITY_PROMPT

    def get_parser_prompt(self) -> str:
        """Get the command parser system prompt."""
        with get_session() as session:
            setting = session.query(Setting).filter_by(key=self.PARSER_KEY).first()
            if setting and setting.value:
                return setting.value
            return DEFAULT_PARSER_PROMPT

    def set_personality_prompt(self, prompt: str) -> bool:
        """Set the personality/conversational system prompt."""
        try:
            with get_session() as session:
                setting = session.query(Setting).filter_by(key=self.PERSONALITY_KEY).first()
                if setting:
                    setting.value = prompt
                else:
                    setting = Setting(key=self.PERSONALITY_KEY, value=prompt)
                    session.add(setting)
                session.commit()
                logger.info("Updated personality prompt")
                return True
        except Exception as e:
            logger.error(f"Error setting personality prompt: {e}")
            return False

    def set_parser_prompt(self, prompt: str) -> bool:
        """Set the command parser system prompt."""
        try:
            with get_session() as session:
                setting = session.query(Setting).filter_by(key=self.PARSER_KEY).first()
                if setting:
                    setting.value = prompt
                else:
                    setting = Setting(key=self.PARSER_KEY, value=prompt)
                    session.add(setting)
                session.commit()
                logger.info("Updated parser prompt")
                return True
        except Exception as e:
            logger.error(f"Error setting parser prompt: {e}")
            return False

    def reset_personality_prompt(self) -> bool:
        """Reset personality prompt to default."""
        return self.set_personality_prompt(DEFAULT_PERSONALITY_PROMPT)

    def reset_parser_prompt(self) -> bool:
        """Reset parser prompt to default."""
        return self.set_parser_prompt(DEFAULT_PARSER_PROMPT)

    def get_default_personality_prompt(self) -> str:
        """Get the default personality prompt."""
        return DEFAULT_PERSONALITY_PROMPT

    def get_default_parser_prompt(self) -> str:
        """Get the default parser prompt."""
        return DEFAULT_PARSER_PROMPT
