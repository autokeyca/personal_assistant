# Personal Assistant

A local personal assistant that runs in your WSL Ubuntu environment, powered by AI for intelligent natural language understanding.

## Features

- **Todo management** - Track tasks with priorities and due dates
- **Google Calendar integration** - View and create events
- **Gmail management** - Read, send, reply, and organize emails
- **Reminders** - Set and receive reminders via Telegram
- **Daily briefings** - Get a morning summary of your day
- **🤖 AI-Powered Natural Language** - Use conversational text instead of commands
- **🎤 Voice Message Support** - Send voice notes that are automatically transcribed and processed
- **Intelligent Command Parsing** - Powered by Gemini 2.5 Flash

All commands are sent via Telegram for a seamless mobile experience.

## Quick Start

### 1. Run the setup script

```bash
cd /home/ja/projects/personal_assistant
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Create a Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token to `config/config.yaml`

### 3. Get your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID to `config/config.yaml`

### 4. Set up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable these APIs:
   - Google Calendar API
   - Gmail API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Choose "Desktop application"
6. Download the JSON file and save as `config/credentials.json`

### 5. Authenticate with Google

```bash
source venv/bin/activate
python scripts/auth_google.py
```

A browser will open for authentication. Grant the requested permissions.

### 6. Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Add it to `config/config.yaml` under `gemini.api_key`

The free tier provides:
- 250 requests per day
- 10 requests per minute
- More than enough for personal use!

### 7. Run the Assistant

```bash
source venv/bin/activate
python run.py
```

## Running as a Service

To run the assistant in the background:

```bash
# Copy service file
sudo cp scripts/personal-assistant.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable personal-assistant
sudo systemctl start personal-assistant

# Check status
sudo systemctl status personal-assistant

# View logs
journalctl -u personal-assistant -f
```

## Usage

### 🎤 Voice Messages & Natural Language (NEW!)

You can now interact with your assistant using natural language, both with text and voice!

**Text examples:**
- "Add a todo to buy groceries"
- "What's on my calendar tomorrow?"
- "Remind me to call mom at 3pm tomorrow"
- "Show me my todos"
- "Create a high priority task to finish the report by Friday"

**Voice messages:**
Just send a voice message saying what you want:
- "Add a meeting with Sarah tomorrow at 2pm"
- "What do I need to do today?"
- "Set a reminder for project deadline next Friday"

The bot will:
1. Transcribe your voice message
2. Understand your intent
3. Execute the appropriate action
4. Respond with confirmation

### Traditional Telegram Commands

You can still use traditional slash commands for faster access:

#### General
- `/start` - Start the bot
- `/help` - Show all commands
- `/status` - Show assistant status
- `/briefing` - Get your daily briefing

### Todos
- `/todo` - List active todos
- `/add <task>` - Add a new todo
- `/done <id>` - Mark todo as complete
- `/focus [id]` - View or set active/focused task
- `/unfocus` - Clear active task
- `/deltodo <id>` - Delete a todo
- `/todosearch <query>` - Search todos

**Examples:**
```
/add Buy groceries
/add Call John priority:urgent
/add Submit report due:friday
/done 1
/focus 2
/focus
```

The `/focus` command is your ADHD guardrail - when you get distracted, just type `/focus` to see what you were working on. It also shows prominently in `/status` and `/briefing`.

### Calendar
- `/cal` - List upcoming events (7 days)
- `/today` - Show today's events
- `/week` - Show this week's events
- `/newevent <text>` - Quick add event
- `/delevent <id>` - Delete an event

**Examples:**
```
/newevent Lunch with John tomorrow at noon
/newevent Team meeting Friday 3pm
/cal 14
```

### Email
- `/email` - List recent emails
- `/unread` - Show unread emails
- `/read <id>` - Read an email
- `/send <to> | <subject> | <body>` - Send email
- `/reply <id> | <message>` - Reply to email
- `/archive <id>` - Archive email
- `/emailsearch <query>` - Search emails

**Examples:**
```
/send john@example.com | Meeting tomorrow | Hi John, can we meet at 3pm?
/reply abc12345 | Thanks, I'll review it tomorrow.
/emailsearch from:boss subject:urgent
```

### Reminders
- `/remind <time> | <message>` - Set a reminder
- `/reminders` - List pending reminders
- `/delremind <id>` - Delete a reminder

**Examples:**
```
/remind tomorrow 9am | Call the bank
/remind in 2 hours | Check on deployment
/remind friday 5pm | Submit weekly report
```

## Automated Features

The assistant automatically:

- Checks for due reminders every minute
- Checks for new emails every 5 minutes
- Sends event reminders 10-15 minutes before
- Sends a morning briefing at 8:00 AM (configurable)

## Configuration

Edit `config/config.yaml`:

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  authorized_user_id: 123456789

google:
  credentials_file: "config/credentials.json"
  token_file: "config/token.json"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"  # Get from https://aistudio.google.com/apikey
  model: "gemini-2.5-flash"

scheduler:
  reminder_check_interval: 1  # minutes
  email_check_interval: 5     # minutes
  morning_briefing_time: "08:00"

logging:
  level: "INFO"
  file: "logs/assistant.log"
```

## Troubleshooting

### Bot not responding
- Check the bot token is correct
- Ensure your user ID is set in config
- Check logs: `tail -f logs/assistant.log`

### Google authentication fails
- Make sure the APIs are enabled
- Check the credentials.json file is valid
- Delete config/token.json and re-authenticate

### Service won't start
- Check the service file paths are correct
- Ensure the virtual environment exists
- Check systemd logs: `journalctl -u personal-assistant`

## Project Structure

```
personal_assistant/
├── assistant/
│   ├── bot/            # Telegram bot handlers
│   ├── services/       # Calendar, Email, Todo services
│   ├── scheduler/      # Reminder scheduler
│   └── db/             # Database models
├── config/
│   ├── config.yaml     # Your configuration
│   └── credentials.json # Google OAuth credentials
├── data/               # SQLite database
├── logs/               # Log files
├── scripts/            # Setup and service scripts
├── run.py              # Main entry point
└── requirements.txt    # Python dependencies
```

## License

MIT License
