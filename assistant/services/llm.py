"""
LLM Service using Google Gemini 2.5 Flash for natural language processing.
"""
import google.generativeai as genai
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Gemini LLM."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the LLM service.

        Args:
            api_key: Gemini API key
            model_name: Model to use (default: gemini-2.5-flash)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        logger.info(f"LLM service initialized with model: {model_name}")

    def process_message(self, message: str, context: Optional[str] = None) -> str:
        """
        Process a text message and return a response.

        Args:
            message: User message to process
            context: Optional context for the conversation

        Returns:
            LLM response as string
        """
        try:
            prompt = message
            if context:
                prompt = f"{context}\n\n{message}"

            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def parse_command(self, message: str) -> Dict[str, Any]:
        """
        Parse a natural language message into a structured command.

        Args:
            message: Natural language message from user

        Returns:
            Dictionary with parsed command information:
            {
                'intent': str,  # todo_add, calendar_add, reminder_add, email_send, etc.
                'entities': dict,  # extracted parameters
                'confidence': float,  # confidence score
                'original_text': str  # original message
            }
        """
        try:
            prompt = f"""Parse this message and extract the intent and entities.
Return ONLY a JSON object with this structure:
{{
    "intent": "one of: todo_add, todo_list, todo_complete, todo_delete, calendar_add, calendar_list, reminder_add, email_send, email_check, help, general_chat",
    "entities": {{
        "title": "extracted title/subject",
        "description": "extracted description or email body",
        "date": "extracted date in YYYY-MM-DD format",
        "time": "extracted time in HH:MM format",
        "priority": "high/medium/low if mentioned",
        "recipient": "email recipient address or name",
        "subject": "email subject line if mentioned",
        "body": "email body/message content",
        "duration": "event duration if mentioned"
    }},
    "confidence": 0.95
}}

Message: {message}

Important:
- Only include entities that are actually present in the message
- Use null for missing entities
- For dates, interpret "tomorrow", "next week", etc. relative to today
- For times, use 24-hour format
- For email_send: extract recipient (email or name), subject, and body
- If the message is conversational/chat, use "general_chat" intent
"""

            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            result['original_text'] = message
            return result
        except Exception as e:
            logger.error(f"Error parsing command: {e}")
            return {
                'intent': 'general_chat',
                'entities': {},
                'confidence': 0.0,
                'original_text': message
            }

    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio to text using Gemini's audio capabilities.

        Args:
            audio_file_path: Path to audio file

        Returns:
            Transcribed text or None if failed
        """
        try:
            # Upload the audio file
            audio_file = genai.upload_file(path=audio_file_path)

            # Generate transcription
            prompt = "Transcribe this audio message accurately. Return only the transcribed text."
            response = self.model.generate_content([prompt, audio_file])

            # Clean up uploaded file
            genai.delete_file(audio_file.name)

            return response.text.strip()
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None

    def generate_response(self, message: str, system_context: Optional[str] = None) -> str:
        """
        Generate a conversational response to a message.

        Args:
            message: User message
            system_context: System context (e.g., "You are a helpful personal assistant")

        Returns:
            Generated response
        """
        try:
            if system_context:
                prompt = f"{system_context}\n\nUser: {message}\nAssistant:"
            else:
                prompt = message

            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm having trouble processing that right now. Please try again."

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed JSON dictionary
        """
        import json
        import re

        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # Extract content between ``` markers
            match = re.search(r'```(?:json)?\n?(.*?)\n?```', response_text, re.DOTALL)
            if match:
                response_text = match.group(1)

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nResponse: {response_text}")
            return {
                'intent': 'general_chat',
                'entities': {},
                'confidence': 0.0
            }
