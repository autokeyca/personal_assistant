# Jarvis Testing Strategy

Automated testing plan to catch bugs before they reach production.

---

## 🐛 Recent Bugs (Lessons Learned)

### Bugs Found Today (2025-12-02):
1. ❌ **Incomplete reminder parsing** - "remind me in 15 minutes" created reminder with wrong message
2. ❌ **Broken relative time parsing** - dateutil couldn't handle "in 15 minutes"
3. ❌ **Timezone inconsistency** - Naive vs aware datetime comparisons
4. ❌ **Wrong reminder recipient** - All reminders went to owner, not creator
5. ❌ **Compound commands failed** - "Create todo AND set reminder" only did first part
6. ❌ **Completed tasks getting reminders** - Enum vs string comparison bug

### Root Causes:
- ❌ No automated tests catching edge cases
- ❌ No validation of time parsing logic
- ❌ No multi-user scenario testing
- ❌ No enum comparison tests
- ❌ Manual testing only covers happy paths

---

## 🎯 Testing Strategy

### 1. Unit Tests (Test Individual Functions)
Test isolated components in `assistant/services/` and `assistant/bot/handlers/`

### 2. Integration Tests (Test Components Together)
Test workflows that span multiple services

### 3. End-to-End Tests (Simulate Real Usage)
Simulate actual Telegram messages and API calls

### 4. Regression Tests (Prevent Bug Reoccurrence)
Test every fixed bug to ensure it stays fixed

---

## 📋 Test Plan

### Phase 1: Critical Path Tests (High Priority)

#### A. Time Parsing Tests
**File**: `tests/test_time_parsing.py`

Tests:
- ✅ Relative times: "in 15 minutes", "in 2 hours"
- ✅ Absolute times: "tomorrow at 3pm", "next Monday at 9am"
- ✅ Edge cases: "in 0 minutes", "yesterday" (should reject)
- ✅ Invalid inputs: "in banana minutes" (should fail gracefully)
- ✅ Timezone handling: EST vs UTC conversion
- ✅ Future preference: Ambiguous times prefer future

#### B. Reminder Tests
**File**: `tests/test_reminders.py`

Tests:
- ✅ Create reminder with valid time
- ✅ Incomplete message rejection: "remind me in 15 minutes" (no message)
- ✅ Reminder goes to correct user (multi-user)
- ✅ UTC storage validation
- ✅ Scheduler only processes due reminders
- ✅ Scheduler skips completed todos
- ✅ Enum comparison: completed status filtering

#### C. Todo Tests
**File**: `tests/test_todos.py`

Tests:
- ✅ Create todo for self
- ✅ Create todo for another user (owner only)
- ✅ Complete todo
- ✅ Delete todo
- ✅ Search todos by title
- ✅ List todos filtered by user
- ✅ Compound command: "Create todo. Set reminder"
- ✅ Focus on todo (pin functionality)

#### D. Parser Tests (LLM Intent Recognition)
**File**: `tests/test_parser.py`

Tests:
- ✅ Todo intents: add, list, complete, delete
- ✅ Calendar intents: add, list
- ✅ Reminder intents: one-time, recurring
- ✅ Multi-user commands: "Create todo for Ron"
- ✅ Compound commands: Extract both intent AND frequency
- ✅ Context awareness: "complete it" after creating task
- ✅ Confirmation responses: "yes" after suggestion

#### E. Multi-User Tests
**File**: `tests/test_multiuser.py`

Tests:
- ✅ Owner creates task for employee
- ✅ Employee receives notification
- ✅ Employee completes own task
- ✅ Employee cannot access owner's calendar/email
- ✅ Reminders go to correct user
- ✅ Authorization workflow

### Phase 2: Service Tests (Medium Priority)

#### F. Frequency Parser Tests
**File**: `tests/test_frequency_parser.py`

Tests:
- ✅ "every hour" parsing
- ✅ "every 2 hours during business hours"
- ✅ "daily at 9am"
- ✅ "weekdays at 2pm"
- ✅ Invalid frequencies (should reject)
- ✅ should_remind_now() logic

#### G. Calendar Tests
**File**: `tests/test_calendar.py`

Tests:
- ✅ Add event with natural language
- ✅ List upcoming events
- ✅ Time range filtering
- ✅ Google Calendar API mocking

#### H. Email Tests
**File**: `tests/test_email.py`

Tests:
- ✅ Send email
- ✅ Check for new emails
- ✅ Email cache deduplication
- ✅ Gmail API mocking

### Phase 3: API Tests (Medium Priority)

#### I. REST API Tests
**File**: `tests/test_api.py`

Tests:
- ✅ Authentication: Valid/invalid API keys
- ✅ Permissions: Task creation with/without permission
- ✅ Rate limiting
- ✅ All endpoints: /task, /reminder, /message, etc.
- ✅ Research endpoints: search, fetch, ask
- ✅ Error responses: 400, 401, 403, 500

### Phase 4: Edge Cases & Stress Tests (Low Priority)

#### J. Edge Case Tests
**File**: `tests/test_edge_cases.py`

Tests:
- ✅ Empty inputs
- ✅ Very long inputs (>1000 chars)
- ✅ Special characters in titles
- ✅ Concurrent operations
- ✅ Database locks
- ✅ Network failures (API calls)

---

## 🛠️ Implementation Plan

### Test Framework: pytest
**Why pytest?**
- Easy to write tests
- Excellent fixtures support
- Good error reporting
- Parallel test execution
- Plugin ecosystem

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_time_parsing.py     # Phase 1A
├── test_reminders.py        # Phase 1B
├── test_todos.py            # Phase 1C
├── test_parser.py           # Phase 1D
├── test_multiuser.py        # Phase 1E
├── test_frequency_parser.py # Phase 2F
├── test_calendar.py         # Phase 2G
├── test_email.py            # Phase 2H
├── test_api.py              # Phase 3I
├── test_edge_cases.py       # Phase 4J
├── fixtures/
│   ├── sample_todos.json
│   ├── sample_users.json
│   └── sample_reminders.json
└── mocks/
    ├── mock_telegram.py
    ├── mock_google_calendar.py
    └── mock_gmail.py
```

### Key Testing Utilities

#### conftest.py (Shared Fixtures)
```python
import pytest
from assistant.db import init_db, get_session

@pytest.fixture
def test_db():
    """Create a temporary test database."""
    db_path = ":memory:"  # In-memory SQLite
    init_db(db_path)
    yield
    # Cleanup happens automatically with in-memory DB

@pytest.fixture
def owner_user():
    """Create test owner user."""
    return {
        'telegram_id': 123456789,
        'first_name': 'Test Owner',
        'is_owner': True,
        'is_authorized': True,
        'role': 'owner'
    }

@pytest.fixture
def employee_user():
    """Create test employee user."""
    return {
        'telegram_id': 987654321,
        'first_name': 'Test Employee',
        'is_owner': False,
        'is_authorized': True,
        'role': 'employee'
    }
```

---

## 🚀 Running Tests

### Basic Test Run
```bash
# Install pytest
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_reminders.py

# Run specific test
pytest tests/test_reminders.py::test_incomplete_reminder_rejected

# Run with coverage report
pytest --cov=assistant tests/

# Run in parallel (faster)
pytest -n auto tests/
```

### Test Output
```
tests/test_reminders.py::test_create_reminder ✓
tests/test_reminders.py::test_incomplete_reminder_rejected ✓
tests/test_reminders.py::test_correct_user_receives_reminder ✓
tests/test_reminders.py::test_utc_storage ✓
tests/test_reminders.py::test_completed_todos_no_reminders ✓

========== 5 passed in 0.23s ==========
```

---

## 📊 Continuous Testing

### Pre-Commit Hook
Run critical tests before every commit:

**`.git/hooks/pre-commit`**
```bash
#!/bin/bash
echo "Running critical tests..."
pytest tests/test_reminders.py tests/test_todos.py -v
if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

### Daily Automated Tests
Add to crontab:
```bash
# Run full test suite daily at 3am
0 3 * * * cd /home/ja/projects/personal_assistant && source venv/bin/activate && pytest tests/ --cov=assistant > /tmp/test_results.log 2>&1
```

### GitHub Actions (Optional)
**`.github/workflows/tests.yml`**
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest tests/ --cov=assistant
```

---

## 🎯 Testing Priorities

### Phase 1: Critical (Week 1)
- [ ] Time parsing tests
- [ ] Reminder tests (all 6 recent bugs)
- [ ] Todo tests (CRUD + compound commands)
- [ ] Parser tests (intent recognition)

### Phase 2: Important (Week 2)
- [ ] Multi-user tests
- [ ] Frequency parser tests
- [ ] API tests (auth, permissions, endpoints)

### Phase 3: Nice-to-Have (Week 3)
- [ ] Calendar tests
- [ ] Email tests
- [ ] Edge case tests

---

## 📈 Success Metrics

### Coverage Goals
- **Unit tests**: >80% code coverage
- **Integration tests**: Cover all critical workflows
- **Regression tests**: 100% of fixed bugs have tests

### Quality Gates
Before deployment:
- ✅ All tests pass
- ✅ Code coverage >80%
- ✅ No critical bugs in test report
- ✅ All new features have tests

---

## 🔧 Example Test Implementation

### Example 1: Test Incomplete Reminder Rejection
```python
# tests/test_reminders.py
import pytest
from assistant.bot.handlers.intelligent import handle_reminder_add

@pytest.mark.asyncio
async def test_incomplete_reminder_rejected(test_db, owner_user):
    """Test that 'remind me in 15 minutes' without message is rejected."""

    # Simulate entities from LLM parser
    entities = {
        'time': '15 minutes',
        'title': None,  # No message!
        'description': None
    }

    original_message = "remind me in 15 minutes"

    # Mock Telegram update and context
    update = MockUpdate()
    context = MockContext()

    # Call handler
    await handle_reminder_add(
        update, context, entities,
        original_message, None, owner_user
    )

    # Assert: Should get error message
    assert "What should I remind you about?" in update.last_message

    # Assert: No reminder created in database
    with get_session() as session:
        reminders = session.query(Reminder).all()
        assert len(reminders) == 0
```

### Example 2: Test Enum Comparison Bug
```python
# tests/test_todos.py
import pytest
from assistant.scheduler.jobs import check_todo_reminders
from assistant.db.models import TodoStatus

def test_completed_todos_excluded_from_reminders(test_db):
    """Test that completed todos don't get reminders."""

    # Create two todos: one pending, one completed
    todo_service = TodoService()

    todo1 = todo_service.add(
        title="Pending task",
        user_id=123456789,
        reminder_config='{"interval": 1}'
    )

    todo2 = todo_service.add(
        title="Completed task",
        user_id=123456789,
        reminder_config='{"interval": 1}'
    )
    todo_service.complete(todo2['id'])

    # Query with the filter from check_todo_reminders
    with get_session() as session:
        todos = (
            session.query(Todo)
            .filter(
                Todo.reminder_config.isnot(None),
                Todo.status != TodoStatus.COMPLETED  # Fixed enum comparison
            )
            .all()
        )

    # Assert: Only pending todo should be included
    assert len(todos) == 1
    assert todos[0].id == todo1['id']
    assert todos[0].status == TodoStatus.PENDING
```

### Example 3: Test Multi-User Reminder Routing
```python
# tests/test_multiuser.py
import pytest

@pytest.mark.asyncio
async def test_reminder_goes_to_creator(test_db, employee_user):
    """Test that reminders go to the user who created them, not owner."""

    # Employee creates a reminder
    entities = {
        'time': 'tomorrow at 3pm',
        'title': 'Call client'
    }

    update = MockUpdate()
    context = MockContext()

    await handle_reminder_add(
        update, context, entities,
        "remind me tomorrow at 3pm to call client",
        None, employee_user
    )

    # Check reminder in database
    with get_session() as session:
        reminder = session.query(Reminder).first()

        # Assert: Reminder should have employee's user_id
        assert reminder.user_id == employee_user['telegram_id']

    # Simulate scheduler checking reminders
    bot = MockBot()
    await check_reminders(bot)

    # Assert: Message sent to employee, not owner
    assert bot.last_sent_to == employee_user['telegram_id']
```

---

## 🎓 Best Practices

### 1. Test Naming Convention
```python
def test_<feature>_<scenario>_<expected_result>():
    """Clear test name describes what's being tested."""
    pass

# Good examples:
def test_reminder_incomplete_message_rejected()
def test_todo_created_for_another_user_successfully()
def test_completed_task_excluded_from_reminder_query()
```

### 2. Arrange-Act-Assert Pattern
```python
def test_something():
    # Arrange: Set up test data
    user = create_test_user()

    # Act: Perform the action
    result = do_something(user)

    # Assert: Verify the result
    assert result == expected_value
```

### 3. Test Independence
- Each test should run independently
- Use fixtures for shared setup
- Clean up after tests (or use in-memory DB)
- Don't rely on test execution order

### 4. Mock External Services
- Mock Telegram API (don't send real messages)
- Mock Google Calendar/Gmail APIs
- Mock LLM calls (use fixed responses)
- Use test fixtures for data

---

## 📝 Next Steps

### Immediate (This Week):
1. ✅ Create testing strategy document (this file)
2. [ ] Set up pytest framework and conftest.py
3. [ ] Implement Phase 1A: Time parsing tests
4. [ ] Implement Phase 1B: Reminder tests (cover all 6 bugs)
5. [ ] Run tests and achieve green state

### Short-term (Next 2 Weeks):
1. [ ] Complete Phase 1 (Critical tests)
2. [ ] Set up pre-commit hook
3. [ ] Add test coverage reporting
4. [ ] Document how to run tests in README

### Long-term (Next Month):
1. [ ] Complete Phase 2 & 3 tests
2. [ ] Achieve >80% code coverage
3. [ ] Set up CI/CD pipeline (optional)
4. [ ] Create test data fixtures

---

## 💡 Prevention Strategy

### For New Features:
1. **Write tests FIRST** (TDD approach)
2. Test happy path + edge cases
3. Test multi-user scenarios
4. Test error handling
5. Review bugs to add regression tests

### For Bug Fixes:
1. **Write failing test** that reproduces bug
2. Fix the bug
3. Verify test now passes
4. Add test to regression suite
5. Document bug in test comments

---

*This strategy ensures bugs get caught early and stay fixed!*
