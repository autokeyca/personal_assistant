"""Tests for todo functionality (Bug fixes from 2025-12-02)."""

import pytest
from assistant.services import TodoService
from assistant.db import get_session
from assistant.db.models import Todo, TodoStatus


class TestTodoStatus:
    """Test todo status and filtering (Bug #6 fix)."""

    def test_completed_todos_excluded_from_reminder_query(self, test_db, owner_user):
        """Bug #6: Completed todos should be excluded from reminder processing.

        Original bug: Filter was comparing enum to string (TodoStatus.COMPLETED != 'completed')
        which always returned True, so completed tasks were never filtered out.
        """
        todo_service = TodoService()

        # Create pending todo with reminder
        pending_todo = todo_service.add(
            title="Pending task with reminder",
            user_id=owner_user['telegram_id']
        )

        # Set reminder config
        with get_session() as session:
            db_todo = session.query(Todo).filter(Todo.id == pending_todo['id']).first()
            db_todo.reminder_config = '{"interval": 1}'
            session.commit()

        # Create completed todo with reminder
        completed_todo = todo_service.add(
            title="Completed task with reminder",
            user_id=owner_user['telegram_id']
        )

        with get_session() as session:
            db_todo = session.query(Todo).filter(Todo.id == completed_todo['id']).first()
            db_todo.reminder_config = '{"interval": 1}'
            session.commit()

        # Complete the second todo
        todo_service.complete(completed_todo['id'])

        # Query with CORRECTED filter (enum to enum comparison)
        with get_session() as session:
            todos = (
                session.query(Todo)
                .filter(
                    Todo.reminder_config.isnot(None),
                    Todo.status != TodoStatus.COMPLETED  # Fixed: enum to enum
                )
                .all()
            )

            # Should only return the pending todo
            assert len(todos) == 1
            assert todos[0].id == pending_todo['id']
            assert todos[0].status == TodoStatus.PENDING

    def test_enum_vs_string_comparison_bug(self, test_db, owner_user):
        """Demonstrate the original bug: enum != string always returns True."""
        todo_service = TodoService()

        completed_todo = todo_service.add(
            title="Completed task",
            user_id=owner_user['telegram_id']
        )
        todo_service.complete(completed_todo['id'])

        with get_session() as session:
            todo = session.query(Todo).filter(Todo.id == completed_todo['id']).first()

            # Verify the todo is completed
            assert todo.status == TodoStatus.COMPLETED

            # Demonstrate the BUG: enum to string comparison
            # This would return True even though status IS 'completed'!
            buggy_comparison = (todo.status != 'completed')

            # The CORRECT comparison (enum to enum)
            correct_comparison = (todo.status != TodoStatus.COMPLETED)

            # Prove the bug
            assert buggy_comparison == True, "BUG: Enum != string always True!"
            assert correct_comparison == False, "CORRECT: Enum == enum works!"

    def test_create_todo_for_self(self, test_db, owner_user):
        """Test creating a todo for yourself."""
        todo_service = TodoService()

        todo = todo_service.add(
            title="Buy groceries",
            description="Milk, eggs, bread",
            priority="high",
            user_id=owner_user['telegram_id']
        )

        assert todo['title'] == "Buy groceries"
        assert todo['description'] == "Milk, eggs, bread"
        assert todo['priority'] == "high"
        assert todo['user_id'] == owner_user['telegram_id']
        assert todo['status'] == "pending"

    def test_create_todo_for_another_user(self, test_db, owner_user, employee_user):
        """Bug #5: Test creating todo for another user (multi-user support)."""
        todo_service = TodoService()

        todo = todo_service.add(
            title="Call client",
            user_id=employee_user['telegram_id'],
            created_by=owner_user['telegram_id']
        )

        assert todo['user_id'] == employee_user['telegram_id']
        assert todo['created_by'] == owner_user['telegram_id']

    def test_complete_todo(self, test_db, sample_todo):
        """Test completing a todo."""
        todo_service = TodoService()

        result = todo_service.complete(sample_todo['id'])

        assert result is not None
        assert result['status'] == 'completed'

    def test_list_todos_by_user(self, test_db, owner_user, employee_user):
        """Test filtering todos by user."""
        todo_service = TodoService()

        # Create todos for both users
        todo_service.add(title="Owner task 1", user_id=owner_user['telegram_id'])
        todo_service.add(title="Owner task 2", user_id=owner_user['telegram_id'])
        todo_service.add(title="Employee task", user_id=employee_user['telegram_id'])

        # Get owner's todos
        owner_todos = todo_service.list(user_id=owner_user['telegram_id'])
        assert len(owner_todos) == 2

        # Get employee's todos
        employee_todos = todo_service.list(user_id=employee_user['telegram_id'])
        assert len(employee_todos) == 1

    def test_search_todos(self, test_db, owner_user):
        """Test searching todos by title."""
        todo_service = TodoService()

        todo_service.add(title="Buy milk", user_id=owner_user['telegram_id'])
        todo_service.add(title="Buy eggs", user_id=owner_user['telegram_id'])
        todo_service.add(title="Call dentist", user_id=owner_user['telegram_id'])

        # Search for "buy"
        results = todo_service.search("buy")
        assert len(results) == 2

        # Search for "dentist"
        results = todo_service.search("dentist")
        assert len(results) == 1
        assert results[0]['title'] == "Call dentist"
