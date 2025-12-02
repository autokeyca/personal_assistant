"""Shared test fixtures for Jarvis test suite."""

import pytest
import tempfile
import os
from datetime import datetime
import pytz

# Add parent directory to path so we can import assistant modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.db import init_db, get_session
from assistant.db.models import User, Todo, Reminder, TodoStatus


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # Initialize the database
    init_db(db_path)

    yield db_path

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def owner_user(test_db):
    """Create test owner user in database."""
    with get_session() as session:
        user = User(
            telegram_id=123456789,
            first_name='TestOwner',
            last_name='Smith',
            username='testowner',
            is_owner=True,
            is_authorized=True,
            role='owner'
        )
        session.add(user)
        session.commit()

    return {
        'telegram_id': 123456789,
        'first_name': 'TestOwner',
        'last_name': 'Smith',
        'full_name': 'TestOwner Smith',
        'username': 'testowner',
        'is_owner': True,
        'is_authorized': True,
        'role': 'owner'
    }


@pytest.fixture
def employee_user(test_db):
    """Create test employee user in database."""
    with get_session() as session:
        user = User(
            telegram_id=987654321,
            first_name='TestEmployee',
            last_name='Johnson',
            username='testemployee',
            is_owner=False,
            is_authorized=True,
            role='employee'
        )
        session.add(user)
        session.commit()

    return {
        'telegram_id': 987654321,
        'first_name': 'TestEmployee',
        'last_name': 'Johnson',
        'full_name': 'TestEmployee Johnson',
        'username': 'testemployee',
        'is_owner': False,
        'is_authorized': True,
        'role': 'employee'
    }


@pytest.fixture
def sample_todo(test_db, owner_user):
    """Create a sample todo in the database."""
    from assistant.services import TodoService

    todo_service = TodoService()
    todo = todo_service.add(
        title="Sample todo task",
        description="This is a test todo",
        priority="medium",
        user_id=owner_user['telegram_id']
    )

    return todo


@pytest.fixture
def sample_reminder(test_db, owner_user):
    """Create a sample reminder in the database."""
    with get_session() as session:
        tz = pytz.timezone('America/Montreal')
        future_time = datetime.now(pytz.UTC).replace(tzinfo=None)

        reminder = Reminder(
            message="Test reminder message",
            remind_at=future_time,
            is_sent=False,
            user_id=owner_user['telegram_id']
        )
        session.add(reminder)
        session.commit()
        session.refresh(reminder)

        return {
            'id': reminder.id,
            'message': reminder.message,
            'remind_at': reminder.remind_at,
            'user_id': reminder.user_id
        }
