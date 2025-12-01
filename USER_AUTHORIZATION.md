# User Authorization System

Jarvis now has a unified role-based authorization system for managing who can access the assistant.

## How It Works

### When Someone New Contacts Jarvis

**Scenario**: A person you haven't authorized sends a message to Jarvis

**What happens:**

1. **User receives a waiting message:**
   ```
   👋 Hello! I'm Jarvis.

   Your request has been forwarded to my owner for approval.
   Please wait while they review your access request.

   You'll be notified once your access is approved.
   ```

2. **You receive an authorization request:**
   ```
   🔔 New Authorization Request

   Name: John Doe
   Username: @johndoe
   User ID: 123456789

   Message: Hey, can you help me with something?
   ```

3. **You see three inline buttons:**
   - ✅ **Approve as Employee**
   - 👤 **Approve as Contact**
   - ❌ **Deny**

### User Roles

#### 🏆 Owner (You)
- **Full access** to all Jarvis features
- Can authorize/deauthorize other users
- Manage calendar, email, todos, reminders
- All API and configuration access
- Set automatically from `telegram.authorized_user_id` in config

#### 👔 Employee
Best for: Team members, assistants, people you work with

**Can do:**
- Create and manage their own todos
- Be assigned tasks by you
- Receive task reminders
- Set their own reminders
- Use natural language commands
- Send and receive messages via Jarvis
- All basic Jarvis features

**Cannot do:**
- Access your calendar
- Access your email
- Change system configuration
- Authorize other users

#### 👤 Contact
Best for: Friends, family, casual contacts

**Can do:**
- Send messages to you through Jarvis
- Use basic Jarvis features
- Have conversations with Jarvis
- Be assigned simple tasks

**Cannot do:**
- Create their own tasks (only you can assign them)
- Access calendar or email
- Advanced features

### Approval Flow

#### Approving a User

1. Receive authorization request
2. Click either:
   - **"Approve as Employee"** - for team members
   - **"Approve as Contact"** - for casual contacts

3. User is immediately authorized and receives:
   ```
   ✅ Access Approved!

   You have been granted access to Jarvis as an Employee.

   You can now:
   - Be assigned tasks
   - Receive reminders
   - Send messages
   - Use all Jarvis features

   Type /help to see available commands.
   ```

4. You receive confirmation:
   ```
   ✅ Access Approved

   You authorized John Doe (@johndoe) as:
   👔 Employee

   They can now interact with Jarvis.
   ```

#### Denying a User

1. Receive authorization request
2. Click **"Deny"**
3. User receives:
   ```
   ❌ Your access request has been denied.

   If you believe this is an error, please contact the owner directly.
   ```

### Managing Authorized Users

#### View All Users

```bash
sqlite3 data/assistant.db "SELECT telegram_id, first_name, role, is_authorized, authorized_at FROM users WHERE is_authorized = 1"
```

#### Manually Authorize a User (via Python)

```python
from assistant.db import get_session, User
from datetime import datetime

with get_session() as session:
    user = session.query(User).filter_by(telegram_id=123456789).first()
    if user:
        user.is_authorized = True
        user.role = 'employee'  # or 'contact'
        user.authorized_at = datetime.utcnow()
        user.authorized_by = 858441656  # Your telegram ID
        session.commit()
```

#### Revoke Access

Use the `/block` command (if implemented) or manually:

```python
with get_session() as session:
    user = session.query(User).filter_by(telegram_id=123456789).first()
    if user:
        user.is_authorized = False
        user.role = None
        session.commit()
```

## Database Schema

### User Table Columns

```sql
CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    first_name VARCHAR(200),
    last_name VARCHAR(200),
    username VARCHAR(200),
    is_owner BOOLEAN DEFAULT FALSE,
    is_authorized BOOLEAN DEFAULT FALSE,
    role VARCHAR(20),  -- 'owner', 'employee', 'contact'
    authorized_at DATETIME,  -- When they were authorized
    authorized_by BIGINT,  -- Telegram ID of who authorized them
    first_seen DATETIME,
    last_seen DATETIME,
    default_followup_intensity VARCHAR(20),
    followup_enabled BOOLEAN
);
```

## Migration

If upgrading from an older version:

```bash
source venv/bin/activate
python scripts/migrate_user_authorization.py
sudo systemctl restart personal-assistant
```

This migration:
- ✅ Adds role, authorized_at, authorized_by columns
- ✅ Sets you (owner) as authorized with 'owner' role
- ✅ Removes old PendingApproval table
- ✅ Preserves all existing user data

## Security Notes

### Authorization Checks

1. **Entry Point Check**: All messages pass through `handle_intelligent_message`
2. **Unauthorized Route**: Non-authorized users → `handle_unauthorized_user`
3. **Authorized Route**: Authorized users → normal processing
4. **Owner Privilege**: Owner bypasses all restrictions

### What Happens Without Authorization

- **Messages**: Trigger authorization request, don't get processed
- **Commands**: Silently ignored (filtered by `user_filter`)
- **Voice Messages**: Can be received but trigger authorization flow
- **API Access**: Requires separate API key (different system)

### Best Practices

1. **Review Requests Promptly**: Users are waiting for access
2. **Choose Role Carefully**:
   - Employee = trusted team members
   - Contact = everyone else
3. **Deny Unknown Users**: If you don't recognize them, deny
4. **Monitor Access**: Check logs occasionally for suspicious activity
5. **Revoke When Needed**: Remove access for former employees/contacts

## Troubleshooting

### User Says They're Not Authorized

1. Check database:
   ```bash
   sqlite3 data/assistant.db "SELECT telegram_id, first_name, is_authorized, role FROM users WHERE first_name LIKE '%Name%'"
   ```

2. If they exist but not authorized, manually authorize or ask them to message Jarvis again

3. If they don't exist, they need to send a message to Jarvis first

### Authorization Request Not Received

1. Check bot is running:
   ```bash
   sudo systemctl status personal-assistant
   ```

2. Check logs for errors:
   ```bash
   tail -50 logs/assistant.log | grep -i "authorization\|error"
   ```

3. Verify your Telegram ID in config matches database:
   ```bash
   grep authorized_user_id config/config.yaml
   sqlite3 data/assistant.db "SELECT telegram_id FROM users WHERE is_owner = 1"
   ```

### Buttons Not Working

1. Verify authorization handlers are registered (should be automatic)
2. Check logs when clicking button
3. Restart bot service
4. Check callback query patterns match in code

## Example Scenarios

### Scenario 1: New Employee Joins Team

**Luke** starts working with you and needs access to Jarvis for task management.

1. Luke sends: "Hi Jarvis, can you help me?"
2. Luke receives: "Your request has been forwarded..."
3. You receive authorization request
4. You click: "✅ Approve as Employee"
5. Luke receives: "Access Approved! You can now..."
6. Luke can now use: todos, reminders, task assignments

### Scenario 2: Friend Wants to Send a Message

**Sarah** (a friend) wants to ask you a question through Jarvis.

1. Sarah sends: "Can you ask Jerry if he's free for lunch?"
2. Sarah receives: "Your request has been forwarded..."
3. You receive authorization request
4. You click: "👤 Approve as Contact"
5. Sarah receives: "Access Approved as Contact..."
6. Sarah can send messages and casual requests

### Scenario 3: Unknown User

**Stranger** contacts Jarvis randomly.

1. Stranger sends: "Hey bot"
2. Stranger receives: "Your request has been forwarded..."
3. You receive authorization request showing: "User: Stranger, Message: Hey bot"
4. You click: "❌ Deny"
5. Stranger receives: "Your access request has been denied"
6. Stranger cannot contact Jarvis again

## Differences from Old System

### Before
- ❌ Separate PendingApproval table
- ❌ /approve and /reject commands
- ❌ Task approval workflow
- ❌ Message forwarding for all non-owners
- ❌ No role differentiation

### After
- ✅ Single unified users table
- ✅ Inline button approvals
- ✅ Role-based access (owner/employee/contact)
- ✅ Direct interaction for authorized users
- ✅ Cleaner authorization flow
- ✅ Better user experience

## API Access

**Note**: This authorization system is separate from API access. The API has its own key-based authentication system. See `API_SECURITY.md` for details.

To allow an AI agent to access Jarvis:
1. User authorization (for Telegram access)
2. API key (for programmatic access)

These are independent systems serving different purposes.
