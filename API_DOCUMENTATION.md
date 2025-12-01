# Jarvis Agent API Documentation

REST API for inter-agent communication with Jarvis personal assistant.

## Overview

The Jarvis Agent API allows external AI agents, automation tools (n8n, Make.com), and custom applications to interact with Jarvis. Agents can send messages to users, create tasks, set reminders, and query Jarvis status.

## Quick Start

### 1. Start the API Server

```bash
python run_api.py
```

The API will be available at `http://127.0.0.1:8000`

### 2. Create an API Key

```bash
python scripts/manage_api_keys.py create "my-agent" --description "My automation agent"
```

Save the API key shown - it won't be displayed again!

### 3. Make Your First Request

```bash
curl -X POST http://127.0.0.1:8000/message \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from my agent!"}'
```

## Authentication

All endpoints (except `/health` and `/`) require authentication using an API key.

**Header:** `X-API-Key: your-api-key-here`

### API Key Management

```bash
# Create new key
python scripts/manage_api_keys.py create "agent-name" --description "Description"

# List all keys
python scripts/manage_api_keys.py list

# Deactivate a key
python scripts/manage_api_keys.py deactivate 1

# Delete a key
python scripts/manage_api_keys.py delete 1
```

## Endpoints

### General

#### GET /
API information and available endpoints.

#### GET /health
Health check endpoint (no authentication required).

```json
{"status": "healthy"}
```

#### GET /status
Get Jarvis status including active task and task counts.

**Permissions Required:** `status:read`

**Response:**
```json
{
  "status": "running",
  "uptime": null,
  "active_task": {
    "id": 5,
    "title": "Important task",
    "status": "in_progress",
    ...
  },
  "pending_tasks": 3,
  "in_progress_tasks": 2
}
```

### Communication

#### POST /message
Send a message to a user via Telegram.

**Permissions Required:** `message:send`

**Request:**
```json
{
  "message": "Hello from my agent!",
  "parse_mode": "Markdown",
  "user_id": 123456789  // Optional, defaults to owner
}
```

**Response:**
```json
{
  "success": true,
  "message_id": 12345,
  "error": null
}
```

### Tasks

#### POST /task
Create a new task for a user.

**Permissions Required:** `task:create`

**Request:**
```json
{
  "title": "Buy groceries",
  "description": "Milk, bread, eggs",
  "priority": "medium",  // low, medium, high, urgent
  "due_date": "2025-12-05T15:00:00",  // ISO format, optional
  "user_name": "Luke",  // Optional - assign to user by name
  "user_id": 123456789,  // Optional - assign to user by ID
  "follow_up_intensity": "medium"  // none, low, medium, high, urgent
}
```

**Response:**
```json
{
  "id": 42,
  "title": "Buy groceries",
  "description": "Milk, bread, eggs",
  "priority": "medium",
  "status": "pending",
  "due_date": "2025-12-05T15:00:00",
  "user_id": 123456789,
  "created_at": "2025-12-01T10:30:00",
  "reminder_config": null
}
```

#### GET /tasks
List tasks for a user.

**Permissions Required:** `task:read`

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `user_name` (optional): Filter by user name
- `include_completed` (optional): Include completed tasks (default: false)
- `limit` (optional): Max number of tasks (default: 10)

**Response:** Array of TaskResponse objects

### Reminders

#### POST /reminder
Create a one-time reminder.

**Permissions Required:** `reminder:create`

**Request:**
```json
{
  "message": "Call mom",
  "remind_at": "2025-12-01T15:00:00",
  "user_id": 123456789  // Optional, defaults to owner
}
```

**Response:**
```json
{
  "id": 5,
  "message": "Call mom",
  "remind_at": "2025-12-01T15:00:00",
  "is_sent": false
}
```

#### POST /task-reminder
Set a custom reminder frequency for a task.

**Permissions Required:** `reminder:create`

**Request:**
```json
{
  "task_id": 42,
  "frequency": "every 2 hours during business hours"
}
```

**Response:**
```json
{
  "success": true,
  "task_id": 42,
  "frequency": "Every 2 hours during business hours on weekdays"
}
```

**Supported frequency patterns:**
- `"every 2 hours"`
- `"every 30 minutes"`
- `"every day at 9am"`
- `"every 2 hours during business hours"`
- `"every hour between 8am and 5pm"`
- `"every day on weekdays"`

## Permissions

API keys can have fine-grained permissions:

- `*` - All permissions (default)
- `message:send` - Send messages to users
- `task:create` - Create tasks
- `task:read` - List and view tasks
- `reminder:create` - Create reminders
- `status:read` - View Jarvis status

Set permissions when creating a key:
```bash
python scripts/manage_api_keys.py create "limited-agent" \
  --permissions "message:send,task:read"
```

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## Example: Python Client

```python
import requests

class JarvisClient:
    def __init__(self, api_key, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def send_message(self, message, user_id=None):
        """Send a message to user."""
        data = {"message": message}
        if user_id:
            data["user_id"] = user_id

        response = requests.post(
            f"{self.base_url}/message",
            headers=self.headers,
            json=data
        )
        return response.json()

    def create_task(self, title, description=None, priority="medium"):
        """Create a new task."""
        data = {
            "title": title,
            "priority": priority
        }
        if description:
            data["description"] = description

        response = requests.post(
            f"{self.base_url}/task",
            headers=self.headers,
            json=data
        )
        return response.json()

    def get_status(self):
        """Get Jarvis status."""
        response = requests.get(
            f"{self.base_url}/status",
            headers=self.headers
        )
        return response.json()

# Usage
client = JarvisClient("your-api-key-here")
client.send_message("🤖 Hello from my agent!")
task = client.create_task("Review PR #123", priority="high")
print(f"Created task #{task['id']}")
```

## Example: n8n Workflow

1. **HTTP Request Node**
   - Method: POST
   - URL: `http://127.0.0.1:8000/message`
   - Headers:
     - `X-API-Key`: `your-key-here`
     - `Content-Type`: `application/json`
   - Body:
     ```json
     {
       "message": "Alert: Server CPU usage is high!"
     }
     ```

2. **Create Task from Webhook**
   - Trigger: Webhook
   - HTTP Request to `/task`:
     ```json
     {
       "title": "{{$json.task_title}}",
       "description": "{{$json.task_description}}",
       "priority": "urgent"
     }
     ```

## Security

- API server listens on `127.0.0.1` (localhost) by default
- API keys are hashed before storage (SHA-256)
- Keys are shown only once during creation
- Keys can be deactivated without deletion
- Usage tracking (last_used, usage_count)

**For production:**
- Use HTTPS with reverse proxy (nginx)
- Enable rate limiting
- Rotate API keys regularly
- Use specific permissions instead of `*`

## Troubleshooting

### API Server Won't Start

Check if port 8000 is already in use:
```bash
lsof -i :8000
```

Change port in `config/config.yaml`:
```yaml
api:
  port: 8001
```

### Authentication Failed

1. Check API key is correct
2. Verify key is active: `python scripts/manage_api_keys.py list`
3. Check permissions for the endpoint

### Bot Not Connected Error

The API needs access to the bot instance to send messages. Make sure Jarvis bot is running.

## Testing

Run the test script:
```bash
python scripts/test_api.py
```

This will test all major endpoints and show example requests/responses.
