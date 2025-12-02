# Jarvis Interaction Guide

Complete guide to interacting with your Jarvis personal assistant.

---

## 📱 1. Telegram Bot (Primary Interface)

### Natural Language Messaging
The most powerful way to interact. Just talk to Jarvis naturally!

#### Todo Management
```
"Add todo to buy groceries"
"Create task for Ron to call back client. Set reminder every hour"
"Show my todos"
"Show Ron's tasks"
"Complete task 5"
"Mark buy groceries as done"
"Delete the shopping task"
"Focus on task 10"
```

#### Calendar & Scheduling
```
"Add meeting with John tomorrow at 3pm"
"Schedule dentist appointment next Tuesday at 10am"
"Show my calendar"
"What's on my schedule today?"
```

#### Reminders
```
"Remind me in 15 minutes to check the oven"
"Remind me tomorrow at 9am to call mom"
"Set reminder for Monday at 2pm about the presentation"
```

#### Email
```
"Send email to john@example.com about the meeting"
"Check my emails"
```

#### Web Research (NEW!)
```
"Search for best restaurants in Montreal"
"What's the weather in Montreal today?"
"Fetch https://example.com/article"
"Find information about Python async patterns"
```

#### General Chat
```
"What time is it?"
"How are you?"
"Tell me a joke"
```

#### System Configuration (Owner Only)
```
"Change morning briefing time to 7:30am"
"Be more formal in your responses"
"Show current settings"
```

### Voice Messages
Send voice messages to Jarvis - he'll transcribe and process them just like text!

### Slash Commands
Quick access to specific functions:

```
/start          - Initialize conversation with Jarvis
/help           - Get help and available commands
/todo           - List all your todos
/calendar       - Show upcoming calendar events
/authorize 123  - Authorize user (owner only)
/block 123      - Block user (owner only)
/viewprompt     - View system prompts (owner only)
/setprompt      - Modify system prompts (owner only)
/resetprompt    - Reset prompts to default (owner only)
```

---

## 🌐 2. REST API (Programmatic Access)

Base URL: `http://localhost:8000`
Authentication: `X-API-Key: your-api-key`

### General Endpoints

**API Information**
```bash
GET /
```

**Health Check**
```bash
GET /health
```

**Jarvis Status**
```bash
GET /status
# Requires permission: status:read
```

### Communication

**Send Message to User**
```bash
POST /message
{
  "user_id": 123456789,
  "message": "Hello from external agent!",
  "parse_mode": "Markdown"
}
# Requires permission: message:send
```

### Task Management

**Create Task**
```bash
POST /task
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "priority": "high",
  "due_date": "2025-12-05",
  "user_name": "Ron",
  "follow_up_intensity": "medium"
}
# Requires permission: task:create
```

**List Tasks**
```bash
GET /tasks?user_name=Ron&include_completed=false&limit=10
# Requires permission: task:read
```

### Reminders

**Create One-Time Reminder**
```bash
POST /reminder
{
  "message": "Call the dentist",
  "remind_at": "2025-12-03T15:00:00"
}
# Requires permission: reminder:create
```

**Set Task Reminder Frequency**
```bash
POST /task-reminder
{
  "task_id": 20,
  "frequency": "every 2 hours during business hours"
}
# Requires permission: reminder:create
```

### Web Research

**Web Search**
```bash
POST /research/search
{
  "query": "best Python frameworks 2025",
  "max_results": 5,
  "summarize": true
}
# Requires permission: research:search
```

**Fetch URL Content**
```bash
POST /research/fetch
{
  "url": "https://example.com/article",
  "extract": "text",
  "summarize": true
}
# Requires permission: research:fetch
```

**Research Question**
```bash
POST /research/ask
{
  "question": "What's the weather in Montreal?",
  "sources": ["web"],
  "return_citations": true
}
# Requires permission: research:ask
```

### API Documentation
Interactive API docs available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🔑 3. API Key Management

### Creating API Keys

```bash
# Full access
python scripts/manage_api_keys.py create "main-agent" --permissions "*"

# Task management only
python scripts/manage_api_keys.py create "todo-bot" \
  --permissions "task:create,task:read,task:update"

# Research only
python scripts/manage_api_keys.py create "research-agent" \
  --permissions "research:search,research:fetch,research:ask"
```

### Permission Types

- `*` - All permissions (full access)
- `message:send` - Send Telegram messages
- `task:create` - Create tasks
- `task:read` - Read tasks
- `task:update` - Update tasks
- `reminder:create` - Create reminders
- `research:search` - Web search
- `research:fetch` - Fetch URLs
- `research:ask` - Research questions
- `status:read` - Read Jarvis status

---

## 👥 4. Multi-User Support

### User Roles

**Owner** (You)
- Full access to all features
- Can manage calendar, email, todos
- Can authorize/block other users
- Can configure system settings

**Employee**
- Can manage their own todos
- Can set their own reminders
- Can use general chat and research
- Cannot access owner's calendar/email

**Contact**
- Limited access (similar to employee)
- For external collaborators

### Authorization Flow

1. New user sends message to Jarvis
2. Owner receives authorization request with inline buttons
3. Owner clicks: "Approve as Employee" / "Approve as Contact" / "Deny"
4. User gets notified of their authorization status

### Multi-User Commands

```
"Create todo for Ron to call client"
"Show Sarah's tasks"
"Add task for Ben: review the code"
"Remind Luke about his task every hour"
```

---

## 🎯 5. Natural Language Understanding

### Intent Recognition

Jarvis uses Gemini 2.5 Flash to understand your intent:

- **todo_add**: Create new tasks
- **todo_list**: Show todos
- **todo_complete**: Mark tasks done
- **todo_delete**: Remove tasks
- **todo_focus**: Pin a task
- **todo_set_reminder**: Set task reminders
- **calendar_add**: Add calendar events
- **calendar_list**: Show calendar
- **reminder_add**: Create one-time reminders
- **email_send**: Send emails
- **telegram_message**: Message other users
- **web_search**: Search the web
- **web_fetch**: Fetch URL content
- **web_ask**: Answer questions with research
- **general_chat**: Conversation
- **meta_modify_prompt**: Change personality (owner)
- **meta_configure**: Change settings (owner)

### Context Awareness

Jarvis remembers recent conversation:
```
You: "Add todo to buy milk"
Jarvis: "✅ Added: buy milk"
You: "Actually, complete it"  ← Jarvis knows "it" = buy milk
Jarvis: "✅ Completed: buy milk"
```

### Compound Commands

Single message with multiple actions:
```
"Create todo for Ron to call client. Set reminder every 2 hours during business hours"
```
Result: Creates todo AND sets up recurring reminder!

---

## 📊 6. Automated Features

### Morning Briefing
Daily summary at 8:00 AM (configurable):
- Pending todos
- Today's calendar events
- Unread emails
- Weather (if configured)

### Task Reminders
Automatic reminders based on:
- Follow-up intensity (low/medium/high/urgent)
- Custom reminder schedules ("every 2 hours during business hours")

### Email Monitoring
Checks Gmail every 5 minutes for new emails and notifies you

### Calendar Alerts
Notifies 10-15 minutes before events

---

## 🔧 7. Integration Examples

### Python Script
```python
import requests

def create_task(title, api_key):
    response = requests.post(
        "http://localhost:8000/task",
        headers={"X-API-Key": api_key},
        json={"title": title, "priority": "medium"}
    )
    return response.json()

# Usage
task = create_task("Call dentist", "your-api-key")
print(f"Created task #{task['id']}")
```

### n8n Workflow
Use HTTP Request node:
- URL: `http://localhost:8000/task`
- Method: POST
- Headers: `X-API-Key: {{$credentials.api_key}}`
- Body: Task details as JSON

### Make.com
HTTP module with same structure as n8n

### Zapier
Webhooks by Zapier → POST to Jarvis API

---

## 📚 8. Documentation

- **README.md** - Getting started guide
- **API_INTEGRATION.md** - API integration details
- **USER_AUTHORIZATION.md** - Multi-user authorization
- **WEB_RESEARCH.md** - Web research capabilities
- **INTERACTION_GUIDE.md** - This file

---

## 🆘 9. Getting Help

### Via Telegram
```
/help
"How do I set a reminder?"
"What can you do?"
```

### Check Logs
```bash
# Bot logs
tail -100 logs/assistant.log

# API logs
tail -100 logs/api.log

# Service status
sudo systemctl status personal-assistant
```

### Debug Mode
```bash
# Run bot in foreground with debug output
source venv/bin/activate
python run.py
```

---

## 🎉 10. Tips & Best Practices

### Natural Language Tips
1. **Be specific**: "Remind me tomorrow at 3pm" > "Remind me later"
2. **Use names**: "Create task for Ron" (not just "task for employee")
3. **Combine actions**: "Create todo and set reminder every hour"
4. **Ask questions**: "What's my schedule today?"

### API Tips
1. **Cache results**: Don't re-query the same data repeatedly
2. **Handle errors**: Network issues happen, implement retries
3. **Use permissions**: Create API keys with minimal required permissions
4. **Monitor rate limits**: Respect the 60 requests/minute default

### Multi-User Tips
1. **Authorize promptly**: New users can't do anything until authorized
2. **Use roles wisely**: Employee vs Contact based on trust level
3. **Review periodically**: Check `/users` to see who has access

---

## 🔐 Security Features

- ✅ API key authentication required
- ✅ Permission-based access control
- ✅ Rate limiting (60 req/min default)
- ✅ Localhost-only by default
- ✅ Owner-only system configuration
- ✅ User authorization workflow
- ✅ Role-based capabilities

---

*Generated on 2025-12-02 for Jarvis Personal Assistant v1.0*
