# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal assistant Telegram bot running locally in WSL Ubuntu. Manages todos, Google Calendar, Gmail, and reminders via Telegram commands.

## Commands

### Setup & Run
```bash
./scripts/setup.sh              # Initial setup (venv, dependencies)
source venv/bin/activate        # Activate virtual environment
python run.py                   # Run the bot
python scripts/auth_google.py   # Authenticate with Google APIs
```

### Service Management
```bash
sudo systemctl start personal-assistant
sudo systemctl status personal-assistant
journalctl -u personal-assistant -f
```

## Architecture

### Core Flow
`run.py` → loads config → initializes database → creates Telegram bot with handlers → sets up scheduler → runs polling loop

### Key Components

**Bot Layer** (`assistant/bot/`)
- `main.py`: Bot initialization, handler registration, scheduler setup
- `handlers/`: Command handlers for each feature domain (todo, calendar, email, reminders, general)
- All handlers use a user filter for authorization (single authorized user from config)

**Services Layer** (`assistant/services/`)
- `TodoService`: CRUD operations on local SQLite todos
- `CalendarService`: Google Calendar API wrapper
- `EmailService`: Gmail API wrapper with caching for notification deduplication
- `google_auth.py`: OAuth2 flow, token management, service builders

**Scheduler** (`assistant/scheduler/jobs.py`)
- Background jobs run via python-telegram-bot's job queue
- `check_reminders`: Sends due reminders
- `check_emails`: Notifies about new emails
- `check_upcoming_events`: 10-15 minute event alerts
- `send_morning_briefing`: Daily summary

**Database** (`assistant/db/`)
- SQLite with SQLAlchemy ORM
- Models: `Todo`, `Reminder`, `Setting`, `EmailCache`
- Session management via context manager in `session.py`

**Configuration** (`assistant/config.py`)
- YAML config with dot-notation access: `get("telegram.bot_token")`
- Resolves relative paths to absolute based on project root

### Data Flow for Commands
1. Telegram update received → filtered by authorized user
2. Handler in `bot/handlers/` processes command
3. Handler calls appropriate service method
4. Service interacts with database or Google APIs
5. Response sent back to Telegram

### Scheduler Integration
The scheduler is set up in `bot/main.py:create_bot()` after handlers are registered. Jobs use `context.bot` to send messages directly to the authorized user.
