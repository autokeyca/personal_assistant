"""Comprehensive tests for LLM Service - command parsing, date handling, and natural language processing."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
from assistant.services.llm import LLMService


@pytest.fixture
def mock_genai():
    """Mock Google Generative AI module."""
    with patch('assistant.services.llm.genai') as mock:
        # Mock configure
        mock.configure = Mock()

        # Mock GenerativeModel
        mock_model = Mock()
        mock.GenerativeModel.return_value = mock_model

        # Default response for generate_content
        mock_response = Mock()
        mock_response.text = '{"intent": "general_chat", "entities": {}, "confidence": 0.5}'
        mock_model.generate_content.return_value = mock_response

        yield mock


@pytest.fixture
def mock_prompt_service():
    """Mock PromptService for database access."""
    with patch('assistant.services.llm.PromptService') as mock:
        mock_instance = Mock()
        mock_instance.get_parser_prompt.return_value = "Parser prompt template: {context}\n\n{message}"
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def llm_service(mock_genai, mock_prompt_service):
    """Create LLM service with mocked Gemini API and database."""
    return LLMService(api_key="test_key", model_name="gemini-2.5-flash")


class TestLLMServiceInit:
    """Test LLM service initialization."""

    def test_init_with_default_model(self, mock_genai):
        """Test initialization with default model."""
        service = LLMService(api_key="test_key")

        mock_genai.configure.assert_called_once_with(api_key="test_key")
        assert service.model_name == "gemini-2.5-flash"

    def test_init_with_custom_model(self, mock_genai):
        """Test initialization with custom model."""
        service = LLMService(api_key="test_key", model_name="gemini-3.0")

        assert service.model_name == "gemini-3.0"


class TestParseCommand:
    """Test natural language command parsing."""

    def test_parse_todo_add_intent(self, llm_service, mock_genai):
        """Test parsing 'add todo' intent."""
        # Mock response for todo_add intent
        mock_response = Mock()
        mock_response.text = '''{
            "intent": "todo_add",
            "entities": {
                "title": "Buy milk",
                "priority": "medium"
            },
            "confidence": 0.95
        }'''
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Add a todo to buy milk")

        assert result["intent"] == "todo_add"
        assert result["entities"]["title"] == "Buy milk"
        assert result["confidence"] == 0.95
        assert result["original_text"] == "Add a todo to buy milk"

    def test_parse_reminder_add_intent(self, llm_service, mock_genai):
        """Test parsing 'add reminder' intent."""
        mock_response = Mock()
        mock_response.text = '''{
            "intent": "reminder_add",
            "entities": {
                "message": "Check on Raphael",
                "remind_at": "2025-12-04 15:00:00"
            },
            "confidence": 0.92
        }'''
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Remind me at 3pm to check on Raphael")

        assert result["intent"] == "reminder_add"
        assert result["entities"]["message"] == "Check on Raphael"
        assert "15:00" in result["entities"]["remind_at"]

    def test_bug15_date_context_injected(self, llm_service, mock_genai):
        """Bug #15: Test that current date/time is injected into parser context."""
        mock_response = Mock()
        mock_response.text = '{"intent": "reminder_add", "entities": {}, "confidence": 0.9}'
        llm_service.model.generate_content.return_value = mock_response

        # Parse command that references relative time
        result = llm_service.parse_command("remind me at 3pm")

        # Verify generate_content was called with prompt containing date
        call_args = llm_service.model.generate_content.call_args
        prompt_text = call_args[0][0]

        # Should contain today's date in the prompt
        # This is the Bug #15 fix - injecting current date/time context
        assert "Today's date:" in prompt_text
        assert "Current time:" in prompt_text
        assert "2025" in prompt_text  # Should have current year

    def test_parse_general_chat(self, llm_service, mock_genai):
        """Test parsing general conversation."""
        mock_response = Mock()
        mock_response.text = '''{
            "intent": "general_chat",
            "entities": {},
            "confidence": 0.8
        }'''
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("How are you today?")

        assert result["intent"] == "general_chat"
        assert result["entities"] == {}

    def test_parse_with_conversation_context(self, llm_service, mock_genai):
        """Test parsing with conversation history context."""
        mock_response = Mock()
        mock_response.text = '{"intent": "todo_complete", "entities": {"task_id": 5}, "confidence": 0.9}'
        llm_service.model.generate_content.return_value = mock_response

        conversation_context = [
            {"role": "user", "message": "Show me my todos", "channel": "telegram"},
            {"role": "assistant", "message": "#5 - Buy milk\n#6 - Call dentist", "channel": "telegram"}
        ]

        result = llm_service.parse_command("Complete number 5", conversation_context=conversation_context)

        # Verify conversation context was passed in prompt
        call_args = llm_service.model.generate_content.call_args
        prompt_text = call_args[0][0]

        assert "Recent conversation context:" in prompt_text
        assert "Show me my todos" in prompt_text

    def test_parse_command_error_handling(self, llm_service, mock_genai):
        """Test error handling when parsing fails."""
        # Mock an exception
        llm_service.model.generate_content.side_effect = Exception("API Error")

        result = llm_service.parse_command("Some command")

        # Should return safe default instead of crashing
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.0
        assert result["original_text"] == "Some command"

    def test_parse_json_with_markdown_code_block(self, llm_service, mock_genai):
        """Test parsing JSON from markdown code block response."""
        mock_response = Mock()
        mock_response.text = '''```json
{
    "intent": "todo_add",
    "entities": {"title": "Test task"},
    "confidence": 0.9
}
```'''
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Add a test task")

        # Should successfully parse despite markdown wrapper
        assert result["intent"] == "todo_add"
        assert result["entities"]["title"] == "Test task"

    def test_parse_malformed_json_returns_default(self, llm_service, mock_genai):
        """Test handling of malformed JSON response."""
        mock_response = Mock()
        mock_response.text = "This is not valid JSON {broken"
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Some command")

        # Should return safe default
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.0


class TestProcessMessage:
    """Test general message processing."""

    def test_process_message_simple(self, llm_service, mock_genai):
        """Test processing a simple message."""
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you today?"
        llm_service.model.generate_content.return_value = mock_response

        response = llm_service.process_message("Hi there")

        assert "Hello" in response

    def test_process_message_with_context(self, llm_service, mock_genai):
        """Test processing message with context."""
        mock_response = Mock()
        mock_response.text = "Based on the context, here's my response"
        llm_service.model.generate_content.return_value = mock_response

        context = "You are a helpful assistant focused on productivity."
        response = llm_service.process_message("Help me", context=context)

        # Verify context was included in prompt
        call_args = llm_service.model.generate_content.call_args
        prompt_text = call_args[0][0]
        assert "productivity" in prompt_text

    def test_process_message_error_handling(self, llm_service, mock_genai):
        """Test error handling in message processing."""
        llm_service.model.generate_content.side_effect = Exception("API Error")

        response = llm_service.process_message("Test message")

        assert "error" in response.lower()


class TestGenerateResponse:
    """Test conversational response generation."""

    def test_generate_response_simple(self, llm_service, mock_genai):
        """Test generating a simple response."""
        mock_response = Mock()
        mock_response.text = "I'm doing well, thank you!"
        llm_service.model.generate_content.return_value = mock_response

        response = llm_service.generate_response("How are you?")

        assert "doing well" in response

    def test_generate_response_with_system_context(self, llm_service, mock_genai):
        """Test generating response with system context."""
        mock_response = Mock()
        mock_response.text = "As your personal assistant, I'm here to help"
        llm_service.model.generate_content.return_value = mock_response

        system_context = "You are a helpful personal assistant named Jarvis"
        response = llm_service.generate_response("Hello", system_context=system_context)

        # Verify system context was used
        call_args = llm_service.model.generate_content.call_args
        prompt_text = call_args[0][0]
        assert "Jarvis" in prompt_text or "personal assistant" in prompt_text

    def test_generate_response_error_handling(self, llm_service, mock_genai):
        """Test error handling in response generation."""
        llm_service.model.generate_content.side_effect = Exception("Network error")

        response = llm_service.generate_response("Test")

        assert "trouble" in response.lower() or "error" in response.lower()


class TestTranscribeAudio:
    """Test audio transcription."""

    def test_transcribe_audio_success(self, llm_service, mock_genai):
        """Test successful audio transcription."""
        # Mock file upload
        mock_audio_file = Mock()
        mock_audio_file.name = "audio_file_id"
        mock_genai.upload_file.return_value = mock_audio_file

        # Mock transcription response
        mock_response = Mock()
        mock_response.text = "This is the transcribed text from the audio."
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.transcribe_audio("/path/to/audio.ogg")

        assert result == "This is the transcribed text from the audio."
        mock_genai.upload_file.assert_called_once_with(path="/path/to/audio.ogg")
        mock_genai.delete_file.assert_called_once_with("audio_file_id")

    def test_transcribe_audio_error_handling(self, llm_service, mock_genai):
        """Test error handling in audio transcription."""
        mock_genai.upload_file.side_effect = Exception("Upload failed")

        result = llm_service.transcribe_audio("/path/to/audio.ogg")

        assert result is None


class TestJSONParsing:
    """Test JSON parsing helper."""

    def test_parse_json_plain(self, llm_service):
        """Test parsing plain JSON."""
        json_text = '{"intent": "test", "value": 123}'
        result = llm_service._parse_json_response(json_text)

        assert result["intent"] == "test"
        assert result["value"] == 123

    def test_parse_json_markdown_block(self, llm_service):
        """Test parsing JSON from markdown code block."""
        json_text = '''```json
{
    "intent": "test",
    "value": 456
}
```'''
        result = llm_service._parse_json_response(json_text)

        assert result["intent"] == "test"
        assert result["value"] == 456

    def test_parse_json_markdown_no_language(self, llm_service):
        """Test parsing JSON from generic code block."""
        json_text = '''```
{
    "intent": "test",
    "value": 789
}
```'''
        result = llm_service._parse_json_response(json_text)

        assert result["intent"] == "test"
        assert result["value"] == 789

    def test_parse_invalid_json(self, llm_service):
        """Test handling invalid JSON."""
        json_text = "Not valid JSON at all {{"
        result = llm_service._parse_json_response(json_text)

        # Should return safe default
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.0

    def test_parse_json_with_whitespace(self, llm_service):
        """Test parsing JSON with extra whitespace."""
        json_text = '''

        {"intent": "test", "value": 999}

        '''
        result = llm_service._parse_json_response(json_text)

        assert result["intent"] == "test"
        assert result["value"] == 999


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_parse_very_long_message(self, llm_service, mock_genai):
        """Test parsing very long messages."""
        mock_response = Mock()
        mock_response.text = '{"intent": "general_chat", "entities": {}, "confidence": 0.7}'
        llm_service.model.generate_content.return_value = mock_response

        # Very long message (10000 characters)
        long_message = "A" * 10000
        result = llm_service.parse_command(long_message)

        # Should handle without crashing
        assert result["intent"] == "general_chat"
        assert result["original_text"] == long_message

    def test_parse_empty_string(self, llm_service, mock_genai):
        """Test parsing empty string."""
        mock_response = Mock()
        mock_response.text = '{"intent": "general_chat", "entities": {}, "confidence": 0.0}'
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("")

        assert result["original_text"] == ""

    def test_parse_unicode_characters(self, llm_service, mock_genai):
        """Test parsing messages with Unicode characters."""
        mock_response = Mock()
        mock_response.text = '{"intent": "todo_add", "entities": {"title": "買い物 🛒"}, "confidence": 0.9}'
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Add todo: 買い物 🛒")

        assert result["entities"]["title"] == "買い物 🛒"

    def test_parse_special_characters(self, llm_service, mock_genai):
        """Test parsing messages with special characters."""
        mock_response = Mock()
        mock_response.text = '{"intent": "todo_add", "entities": {"title": "Test <>&\\"\'"}, "confidence": 0.9}'
        llm_service.model.generate_content.return_value = mock_response

        result = llm_service.parse_command("Add todo: Test <>&\"'")

        # Should handle special characters safely
        assert "Test" in result["entities"]["title"]

    def test_conversation_context_truncation(self, llm_service, mock_genai):
        """Test that conversation context is limited to last 5 messages."""
        mock_response = Mock()
        mock_response.text = '{"intent": "general_chat", "entities": {}, "confidence": 0.8}'
        llm_service.model.generate_content.return_value = mock_response

        # Create 10 messages of conversation context
        conversation_context = [
            {"role": "user", "message": f"Message {i}", "channel": "telegram"}
            for i in range(10)
        ]

        result = llm_service.parse_command("Test", conversation_context=conversation_context)

        # Verify only last 5 are included in prompt
        call_args = llm_service.model.generate_content.call_args
        prompt_text = call_args[0][0]

        # Should contain messages 5-9 (last 5)
        assert "Message 9" in prompt_text
        assert "Message 5" in prompt_text
        # Should NOT contain message 0-4 (older messages)
        assert "Message 0" not in prompt_text
        assert "Message 1" not in prompt_text
