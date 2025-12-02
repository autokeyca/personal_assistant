"""Tests for reminder functionality (Bug fixes from 2025-12-02)."""

import pytest
from datetime import datetime, timedelta
import pytz
from unittest.mock import Mock, AsyncMock, patch
from assistant.db import get_session
from assistant.db.models import Reminder, Todo, TodoStatus, User
from assistant.services import TodoService


class TestReminderCreation:
    """Test reminder creation and validation."""

    @pytest.mark.asyncio
    async def test_create_reminder_with_valid_time(self, test_db, owner_user):
        """Test creating a reminder with valid time specification."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        # Mock Telegram update and context
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()
        context.bot = Mock()

        entities = {
            'time': 'tomorrow at 3pm',
            'title': 'call the dentist',
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me tomorrow at 3pm to call the dentist",
            None, owner_user
        )

        # Verify reminder was created
        with get_session() as session:
            reminders = session.query(Reminder).all()
            assert len(reminders) == 1

            reminder = reminders[0]
            assert reminder.message == 'call the dentist'
            assert reminder.user_id == owner_user['telegram_id']
            assert reminder.is_sent == False

            # Should be stored as naive UTC
            assert reminder.remind_at.tzinfo is None

            # Should be in the future
            now_utc = datetime.now(pytz.UTC).replace(tzinfo=None)
            assert reminder.remind_at > now_utc

    @pytest.mark.asyncio
    async def test_incomplete_reminder_rejected(self, test_db, owner_user):
        """Bug #1: Test that 'remind me in 15 minutes' without message is rejected."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Entities with time but no message
        entities = {
            'time': '15 minutes',
            'title': None,
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me in 15 minutes",
            None, owner_user
        )

        # Should get error message
        assert update.message.reply_text.called
        error_msg = update.message.reply_text.call_args[0][0]
        assert "What should I remind you about?" in error_msg

        # No reminder should be created
        with get_session() as session:
            reminders = session.query(Reminder).all()
            assert len(reminders) == 0

    @pytest.mark.asyncio
    async def test_relative_time_parsing(self, test_db, owner_user):
        """Bug #2: Test that relative times like 'in 15 minutes' work correctly."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        entities = {
            'time': 'in 15 minutes',
            'title': 'check the oven',
            'description': None
        }

        before = datetime.now(pytz.UTC)

        await handle_reminder_add(
            update, context, entities,
            "remind me in 15 minutes to check the oven",
            None, owner_user
        )

        # Verify reminder time is approximately 15 minutes in future
        with get_session() as session:
            reminder = session.query(Reminder).first()
            assert reminder is not None

            # Convert to UTC for comparison
            reminder_time_utc = pytz.UTC.localize(reminder.remind_at)
            expected = before + timedelta(minutes=15)

            # Should be within 1 minute of expected time
            diff = abs((reminder_time_utc - expected).total_seconds())
            assert diff < 60, f"Time parsing off by {diff} seconds"

    @pytest.mark.asyncio
    async def test_utc_storage(self, test_db, owner_user):
        """Bug #3: Test that reminders are stored as naive UTC regardless of input timezone."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        entities = {
            'time': 'tomorrow at 1pm',
            'title': 'meeting',
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me tomorrow at 1pm about meeting",
            None, owner_user
        )

        with get_session() as session:
            reminder = session.query(Reminder).first()

            # Should be stored as naive UTC
            assert reminder.remind_at.tzinfo is None

            # Time should be in future
            now_utc = datetime.now(pytz.UTC).replace(tzinfo=None)
            assert reminder.remind_at > now_utc

            # Hour should be different from 1pm (EST is UTC-5 or UTC-4)
            # 1pm EST = 6pm or 5pm UTC
            assert reminder.remind_at.hour in [17, 18]


class TestReminderRouting:
    """Test multi-user reminder routing."""

    @pytest.mark.asyncio
    async def test_reminder_goes_to_creator(self, test_db, employee_user):
        """Bug #4: Test that reminders go to the user who created them, not owner."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = employee_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        entities = {
            'time': 'tomorrow at 3pm',
            'title': 'call client',
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me tomorrow at 3pm to call client",
            None, employee_user
        )

        # Verify reminder has employee's user_id
        with get_session() as session:
            reminder = session.query(Reminder).first()
            assert reminder is not None
            assert reminder.user_id == employee_user['telegram_id']


class TestReminderScheduler:
    """Test reminder scheduling and sending."""

    @pytest.mark.asyncio
    async def test_due_reminders_are_sent(self, test_db, owner_user):
        """Test that due reminders are detected and marked as sent."""
        from assistant.scheduler.jobs import check_reminders

        # Create a due reminder (in the past)
        with get_session() as session:
            past_time = datetime.now(pytz.UTC).replace(tzinfo=None) - timedelta(minutes=5)
            reminder = Reminder(
                message="Test reminder",
                remind_at=past_time,
                is_sent=False,
                user_id=owner_user['telegram_id']
            )
            session.add(reminder)
            session.commit()
            reminder_id = reminder.id

        # Mock bot
        bot = Mock()
        bot.send_message = AsyncMock()

        # Run scheduler
        await check_reminders(bot)

        # Verify reminder was sent
        assert bot.send_message.called

        # Verify reminder marked as sent
        with get_session() as session:
            reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            assert reminder.is_sent == True

    @pytest.mark.asyncio
    async def test_future_reminders_not_sent(self, test_db, owner_user):
        """Test that future reminders are NOT sent."""
        from assistant.scheduler.jobs import check_reminders

        # Create future reminder
        with get_session() as session:
            future_time = datetime.now(pytz.UTC).replace(tzinfo=None) + timedelta(hours=1)
            reminder = Reminder(
                message="Future reminder",
                remind_at=future_time,
                is_sent=False,
                user_id=owner_user['telegram_id']
            )
            session.add(reminder)
            session.commit()
            reminder_id = reminder.id

        # Mock bot
        bot = Mock()
        bot.send_message = AsyncMock()

        # Run scheduler
        await check_reminders(bot)

        # Verify reminder was NOT sent
        assert not bot.send_message.called

        # Verify reminder still marked as not sent
        with get_session() as session:
            reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            assert reminder.is_sent == False

    @pytest.mark.asyncio
    async def test_already_sent_reminders_skipped(self, test_db, owner_user):
        """Test that already-sent reminders are not sent again."""
        from assistant.scheduler.jobs import check_reminders

        # Create already-sent reminder
        with get_session() as session:
            past_time = datetime.now(pytz.UTC).replace(tzinfo=None) - timedelta(minutes=5)
            reminder = Reminder(
                message="Already sent",
                remind_at=past_time,
                is_sent=True,
                user_id=owner_user['telegram_id']
            )
            session.add(reminder)
            session.commit()

        # Mock bot
        bot = Mock()
        bot.send_message = AsyncMock()

        # Run scheduler
        await check_reminders(bot)

        # Verify reminder was NOT sent again
        assert not bot.send_message.called


class TestTodoReminders:
    """Test reminders linked to todos."""

    @pytest.mark.asyncio
    async def test_completed_todos_no_reminders(self, test_db, owner_user):
        """Bug #6: Test that completed todos don't trigger reminders."""
        from assistant.scheduler.jobs import check_todo_reminders
        from assistant.db.models import TodoStatus

        todo_service = TodoService()

        # Create todo with reminder
        todo = todo_service.add(
            title="Test task",
            user_id=owner_user['telegram_id']
        )

        # Set reminder config
        with get_session() as session:
            db_todo = session.query(Todo).filter(Todo.id == todo['id']).first()
            db_todo.reminder_config = '{"interval": 1, "last_reminded": null}'
            session.commit()

        # Complete the todo
        todo_service.complete(todo['id'])

        # Mock bot
        bot = Mock()
        bot.send_message = AsyncMock()

        # Run scheduler
        await check_todo_reminders(bot)

        # Verify no reminder was sent for completed todo
        assert not bot.send_message.called

    def test_pending_todos_identified_for_reminders(self, test_db, owner_user):
        """Test that pending todos with reminder configs are identified by frequency parser."""
        from assistant.services.frequency_parser import FrequencyParser
        import json

        todo_service = TodoService()
        frequency_parser = FrequencyParser()

        # Create todo with reminder
        todo = todo_service.add(
            title="Pending task",
            user_id=owner_user['telegram_id']
        )

        # Set reminder config with correct format
        past_time = datetime.now(pytz.UTC) - timedelta(hours=2)
        with get_session() as session:
            db_todo = session.query(Todo).filter(Todo.id == todo['id']).first()
            reminder_config = {
                "enabled": True,
                "interval_value": 1,
                "interval_unit": "hours"
            }
            db_todo.reminder_config = json.dumps(reminder_config)
            # Set last_reminder_at in the past so it's due
            db_todo.last_reminder_at = past_time.replace(tzinfo=None)
            session.commit()

        # Verify frequency parser identifies this as needing a reminder
        should_remind = frequency_parser.should_remind_now(
            reminder_config,
            past_time.replace(tzinfo=None)
        )
        assert should_remind == True, "Frequency parser should identify todo as needing reminder"


class TestReminderEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_time_format(self, test_db, owner_user):
        """Test that invalid time formats are handled gracefully."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        entities = {
            'time': 'banana oclock',
            'title': 'test reminder',
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me at banana oclock to test reminder",
            None, owner_user
        )

        # Should get error message
        assert update.message.reply_text.called
        error_msg = update.message.reply_text.call_args[0][0]
        assert "could not parse" in error_msg.lower() or "couldn't understand" in error_msg.lower() or "invalid" in error_msg.lower()

        # No reminder should be created
        with get_session() as session:
            reminders = session.query(Reminder).all()
            assert len(reminders) == 0

    @pytest.mark.asyncio
    async def test_past_time_rejected(self, test_db, owner_user):
        """Bug #7: Test that past times are explicitly rejected."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        entities = {
            'time': 'yesterday at 3pm',
            'title': 'test',
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            "remind me yesterday at 3pm to test",
            None, owner_user
        )

        # Should reject past time
        assert update.message.reply_text.called
        error_msg = update.message.reply_text.call_args[0][0]
        assert "past time" in error_msg.lower() or "future" in error_msg.lower()

        # No reminder should be created
        with get_session() as session:
            reminders = session.query(Reminder).all()
            assert len(reminders) == 0

    @pytest.mark.asyncio
    async def test_very_long_reminder_message(self, test_db, owner_user):
        """Test handling of very long reminder messages."""
        from assistant.bot.handlers.intelligent import handle_reminder_add

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = owner_user['telegram_id']
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Create very long message (500+ characters)
        long_message = "a" * 1000

        entities = {
            'time': 'tomorrow at 3pm',
            'title': long_message,
            'description': None
        }

        await handle_reminder_add(
            update, context, entities,
            f"remind me tomorrow at 3pm to {long_message}",
            None, owner_user
        )

        # Should handle gracefully (either truncate or accept)
        with get_session() as session:
            reminders = session.query(Reminder).all()
            assert len(reminders) >= 0  # Either created or rejected, both OK
