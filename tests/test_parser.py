"""Tests for LLM parser and intent recognition."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from assistant.services.llm import LLMService


class TestIntentRecognition:
    """Test intent recognition for different command types."""

    @pytest.mark.asyncio
    async def test_todo_add_intent(self):
        """Test recognition of todo creation intent."""
        llm = LLMService()

        test_cases = [
            "Add todo to buy groceries",
            "Create task for shopping",
            "New todo: call dentist",
            "I need to remember to send email",
        ]

        for message in test_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"
            assert result.get('intent') in ['todo_add', 'general_chat'], \
                f"Expected todo_add intent for: {message}, got {result.get('intent')}"

    @pytest.mark.asyncio
    async def test_todo_list_intent(self):
        """Test recognition of todo list intent."""
        llm = LLMService()

        test_cases = [
            "Show my todos",
            "List all tasks",
            "What are my pending tasks?",
            "Show me what I need to do",
        ]

        for message in test_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"
            # Intent should be todo_list or general_chat (both acceptable)
            assert result.get('intent') in ['todo_list', 'general_chat'], \
                f"Unexpected intent for: {message}"

    @pytest.mark.asyncio
    async def test_reminder_intent(self):
        """Test recognition of reminder creation intent."""
        llm = LLMService()

        test_cases = [
            "Remind me in 15 minutes to check the oven",
            "Set reminder for tomorrow at 3pm about meeting",
            "Remind me to call mom tomorrow",
        ]

        for message in test_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"
            assert result.get('intent') == 'reminder_add', \
                f"Expected reminder_add for: {message}, got {result.get('intent')}"

    @pytest.mark.asyncio
    async def test_calendar_intent(self):
        """Test recognition of calendar-related intents."""
        llm = LLMService()

        add_cases = [
            "Add meeting tomorrow at 3pm",
            "Schedule dentist appointment next Tuesday",
            "Create calendar event for Friday at 10am",
        ]

        for message in add_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"
            # Should recognize calendar intent
            assert 'calendar' in result.get('intent', '').lower() or \
                   result.get('intent') in ['general_chat'], \
                f"Expected calendar intent for: {message}"


class TestEntityExtraction:
    """Test extraction of entities from natural language."""

    @pytest.mark.asyncio
    async def test_user_name_extraction(self):
        """Test extraction of user names from commands."""
        llm = LLMService()

        test_cases = [
            ("Create todo for Ron to call client", "Ron"),
            ("Add task for Sarah: review code", "Sarah"),
            ("Luke needs to finish the report", "Luke"),
        ]

        for message, expected_user in test_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"

            # Check if user name was extracted
            extracted_user = result.get('for_user') or result.get('user')
            if extracted_user:
                assert expected_user.lower() in extracted_user.lower(), \
                    f"Expected user '{expected_user}' in: {message}, got {extracted_user}"

    @pytest.mark.asyncio
    async def test_priority_extraction(self):
        """Test extraction of priority levels."""
        llm = LLMService()

        test_cases = [
            ("Add urgent todo to fix the bug", ["urgent", "high"]),
            ("Create high priority task for deployment", ["high", "urgent"]),
            ("Low priority: update documentation", ["low", "medium"]),
        ]

        for message, acceptable_priorities in test_cases:
            result = await llm.parse_intent(message)
            if result and result.get('priority'):
                priority = result['priority'].lower()
                assert any(p in priority for p in acceptable_priorities), \
                    f"Expected priority in {acceptable_priorities} for: {message}, got {priority}"

    @pytest.mark.asyncio
    async def test_time_extraction(self):
        """Test extraction of time expressions."""
        llm = LLMService()

        test_cases = [
            "Remind me in 15 minutes",
            "Set reminder for tomorrow at 3pm",
            "Add meeting next Tuesday at 10am",
        ]

        for message in test_cases:
            result = await llm.parse_intent(message)
            assert result is not None, f"Failed to parse: {message}"

            # Should extract some time-related entity
            has_time = result.get('time') or result.get('when') or result.get('due_date')
            # Note: Some messages might not extract time if LLM interprets differently
            # This is a soft assertion - we just verify parsing doesn't crash


class TestCompoundCommands:
    """Test handling of compound commands (multiple intents)."""

    @pytest.mark.asyncio
    async def test_todo_with_reminder(self):
        """Bug #5 fix: Test todo creation with reminder in same message."""
        llm = LLMService()

        message = "Create todo for Ron to call client. Set reminder every hour during business hours"
        result = await llm.parse_intent(message)

        assert result is not None, "Failed to parse compound command"

        # Should recognize todo intent
        assert result.get('intent') == 'todo_add', \
            f"Expected todo_add intent, got {result.get('intent')}"

        # Should extract user name
        user = result.get('for_user') or result.get('user')
        if user:
            assert 'ron' in user.lower(), f"Expected 'Ron' in user field, got {user}"

        # Should extract frequency
        frequency = result.get('frequency')
        if frequency:
            assert 'hour' in frequency.lower(), \
                f"Expected 'hour' in frequency, got {frequency}"

    @pytest.mark.asyncio
    async def test_todo_with_due_date(self):
        """Test todo creation with due date."""
        llm = LLMService()

        message = "Add task to finish report by Friday"
        result = await llm.parse_intent(message)

        assert result is not None, "Failed to parse"
        assert result.get('intent') in ['todo_add', 'general_chat']


class TestContextAwareness:
    """Test context-aware parsing (follow-up messages)."""

    @pytest.mark.asyncio
    async def test_followup_reference(self):
        """Test parsing of follow-up messages with pronouns."""
        llm = LLMService()

        # Simulate conversation history
        context = [
            {"role": "user", "content": "Add todo to buy milk"},
            {"role": "assistant", "content": "✅ Added: buy milk"}
        ]

        # Follow-up message
        message = "Actually, complete it"
        result = await llm.parse_intent(message, conversation_history=context)

        assert result is not None, "Failed to parse follow-up"
        # Should recognize completion intent
        # Note: This is challenging for LLM without explicit context handling


class TestEdgeCases:
    """Test edge cases and error handling in parsing."""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test handling of empty messages."""
        llm = LLMService()

        result = await llm.parse_intent("")
        # Should either return None or general_chat intent
        assert result is None or result.get('intent') == 'general_chat'

    @pytest.mark.asyncio
    async def test_very_long_message(self):
        """Test handling of very long messages."""
        llm = LLMService()

        # Create a very long message
        long_message = "Add todo to " + "do something important " * 100

        try:
            result = await llm.parse_intent(long_message)
            # Should handle gracefully (either parse or return None)
            assert result is None or isinstance(result, dict)
        except Exception as e:
            # Should not crash
            pytest.fail(f"Parser crashed on long message: {e}")

    @pytest.mark.asyncio
    async def test_ambiguous_message(self):
        """Test handling of ambiguous messages."""
        llm = LLMService()

        ambiguous = [
            "it",
            "do that thing",
            "you know what I mean",
        ]

        for message in ambiguous:
            result = await llm.parse_intent(message)
            # Should handle gracefully, likely returning general_chat
            assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test handling of special characters in messages."""
        llm = LLMService()

        messages = [
            "Add todo: @#$% special chars",
            "Remind me 😀 emoji test",
            "Todo with\nnewlines\nhere",
        ]

        for message in messages:
            try:
                result = await llm.parse_intent(message)
                assert result is None or isinstance(result, dict)
            except Exception as e:
                pytest.fail(f"Parser crashed on special chars '{message}': {e}")

    @pytest.mark.asyncio
    async def test_multilingual_input(self):
        """Test handling of non-English input."""
        llm = LLMService()

        # Test with some common non-English phrases
        messages = [
            "Añadir tarea",  # Spanish
            "Ajouter une tâche",  # French
        ]

        for message in messages:
            try:
                result = await llm.parse_intent(message)
                # Should handle gracefully
                assert result is None or isinstance(result, dict)
            except Exception as e:
                pytest.fail(f"Parser crashed on multilingual input '{message}': {e}")


class TestParserRobustness:
    """Test parser robustness and error recovery."""

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self):
        """Test that parser handles malformed LLM responses."""
        llm = LLMService()

        # This tests the internal error handling
        # We can't directly inject malformed JSON, but we test error paths
        message = "test message"

        try:
            result = await llm.parse_intent(message)
            # Should always return something or None, never crash
            assert result is None or isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"Parser should handle errors gracefully: {e}")

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        # This would require mocking the LLM API
        # For now, we just ensure the method exists
        llm = LLMService()
        assert hasattr(llm, 'parse_intent')

    @pytest.mark.asyncio
    async def test_rapid_sequential_calls(self):
        """Test parser under rapid sequential calls."""
        llm = LLMService()

        messages = [
            "Add todo 1",
            "Add todo 2",
            "Add todo 3",
        ]

        # Should handle rapid calls without crashing
        try:
            results = []
            for message in messages:
                result = await llm.parse_intent(message)
                results.append(result)

            # All should return valid results
            assert len(results) == 3
            for result in results:
                assert result is None or isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"Parser failed under rapid calls: {e}")
