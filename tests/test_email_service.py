"""Tests for EmailService - caching, deduplication, and email operations."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from assistant.services import EmailService
from assistant.db import get_session, EmailCache


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = Mock()

    # Mock users().messages() chain
    messages_mock = Mock()
    users_mock = Mock()
    users_mock.messages.return_value = messages_mock
    service.users.return_value = users_mock

    # Mock labels chain
    labels_mock = Mock()
    users_mock.labels.return_value = labels_mock

    return service


@pytest.fixture
def email_service(mock_gmail_service):
    """Create EmailService with mocked Gmail API."""
    with patch('assistant.services.email.get_google_auth') as mock_auth:
        mock_auth.return_value.get_gmail_service.return_value = mock_gmail_service
        service = EmailService()
        service._service = mock_gmail_service  # Force use of mock
        return service


class TestEmailCaching:
    """Test email caching and notification deduplication."""

    def test_new_message_cached_on_first_check(self, email_service, mock_gmail_service, test_db):
        """Test that new messages are cached when first detected."""
        # Mock API response with one unread message
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Test email",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Date", "value": "Wed, 3 Dec 2025 10:00:00"}
                ]
            }
        }

        # Get new messages
        new_messages = email_service.get_new_messages()

        # Should return the message
        assert len(new_messages) == 1
        assert new_messages[0]["id"] == "msg001"

        # Check that it's cached
        with get_session() as session:
            cached = session.query(EmailCache).filter_by(id="msg001").first()
            assert cached is not None
            assert cached.subject == "Test Subject"
            assert cached.sender == "test@example.com"
            assert cached.notified is True

    def test_cached_message_not_returned_again(self, email_service, mock_gmail_service, test_db):
        """Test that already-notified messages aren't returned again."""
        # Pre-cache a message as notified
        with get_session() as session:
            cache_entry = EmailCache(
                id="msg001",
                subject="Already notified",
                sender="test@example.com",
                received_at=datetime.utcnow(),
                notified=True
            )
            session.add(cache_entry)
            session.commit()

        # Mock API returning the same message
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Test",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Already notified"},
                    {"name": "From", "value": "test@example.com"}
                ]
            }
        }

        # Get new messages
        new_messages = email_service.get_new_messages()

        # Should NOT return the message
        assert len(new_messages) == 0

    def test_promotional_emails_filtered(self, email_service, mock_gmail_service, test_db):
        """Test that promotional emails are not returned as new messages."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "promo001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "promo001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD", "CATEGORY_PROMOTIONS"],
            "snippet": "Buy now!",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Sale!"},
                    {"name": "From", "value": "ads@shop.com"}
                ]
            }
        }

        # Get new messages
        new_messages = email_service.get_new_messages()

        # Should NOT return promotional email
        assert len(new_messages) == 0

    def test_social_emails_filtered(self, email_service, mock_gmail_service, test_db):
        """Test that social category emails are filtered out."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "social001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "social001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD", "CATEGORY_SOCIAL"],
            "snippet": "You have a new friend request",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "New notification"},
                    {"name": "From", "value": "noreply@social.com"}
                ]
            }
        }

        new_messages = email_service.get_new_messages()
        assert len(new_messages) == 0

    def test_multiple_new_messages_all_cached(self, email_service, mock_gmail_service, test_db):
        """Test that multiple new messages are all cached."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}, {"id": "msg002"}, {"id": "msg003"}]
        }

        # Mock get() to return different messages
        def get_message_mock(*args, **kwargs):
            msg_id = kwargs.get('id')
            return Mock(execute=lambda: {
                "id": msg_id,
                "threadId": f"thread_{msg_id}",
                "labelIds": ["INBOX", "UNREAD"],
                "snippet": f"Email {msg_id}",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": f"Subject {msg_id}"},
                        {"name": "From", "value": f"sender{msg_id}@example.com"}
                    ]
                }
            })

        mock_gmail_service.users().messages().get.side_effect = get_message_mock

        new_messages = email_service.get_new_messages()

        # Should return all 3 messages
        assert len(new_messages) == 3

        # Check all are cached
        with get_session() as session:
            cached_count = session.query(EmailCache).count()
            assert cached_count == 3


class TestEmailOperations:
    """Test email operations (mark read/unread, archive, etc.)."""

    def test_mark_read(self, email_service, mock_gmail_service):
        """Test marking email as read."""
        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.mark_read("msg001")

        assert result is True
        mock_gmail_service.users().messages().modify.assert_called_once()
        call_args = mock_gmail_service.users().messages().modify.call_args
        assert call_args[1]["id"] == "msg001"
        assert call_args[1]["body"]["removeLabelIds"] == ["UNREAD"]

    def test_mark_unread(self, email_service, mock_gmail_service):
        """Test marking email as unread."""
        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.mark_unread("msg001")

        assert result is True
        call_args = mock_gmail_service.users().messages().modify.call_args
        assert call_args[1]["body"]["addLabelIds"] == ["UNREAD"]

    def test_archive(self, email_service, mock_gmail_service):
        """Test archiving email (remove from INBOX)."""
        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.archive("msg001")

        assert result is True
        call_args = mock_gmail_service.users().messages().modify.call_args
        assert call_args[1]["body"]["removeLabelIds"] == ["INBOX"]

    def test_trash(self, email_service, mock_gmail_service):
        """Test moving email to trash."""
        mock_trash = Mock()
        mock_trash.execute.return_value = {}
        mock_gmail_service.users().messages().trash.return_value = mock_trash

        result = email_service.trash("msg001")

        assert result is True
        mock_gmail_service.users().messages().trash.assert_called_once()

    def test_delete_permanently(self, email_service, mock_gmail_service):
        """Test permanently deleting email."""
        mock_delete = Mock()
        mock_delete.execute.return_value = {}
        mock_gmail_service.users().messages().delete.return_value = mock_delete

        result = email_service.delete("msg001")

        assert result is True
        mock_gmail_service.users().messages().delete.assert_called_once()


class TestEmailRetrieval:
    """Test email retrieval and formatting."""

    def test_get_unread_count(self, email_service, mock_gmail_service):
        """Test getting unread email count."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "resultSizeEstimate": 5
        }

        count = email_service.get_unread_count()

        assert count == 5

    def test_get_unread_count_zero(self, email_service, mock_gmail_service):
        """Test getting unread count when no unread emails."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "resultSizeEstimate": 0
        }

        count = email_service.get_unread_count()

        assert count == 0

    def test_format_message_with_all_headers(self, email_service):
        """Test message formatting with complete headers."""
        msg = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "This is a test email",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Wed, 3 Dec 2025 10:00:00"}
                ]
            }
        }

        formatted = email_service._format_message(msg)

        assert formatted["id"] == "msg001"
        assert formatted["thread_id"] == "thread001"
        assert formatted["subject"] == "Test Subject"
        assert formatted["from"] == "sender@example.com"
        assert formatted["to"] == "recipient@example.com"
        assert formatted["date"] == "Wed, 3 Dec 2025 10:00:00"
        assert formatted["snippet"] == "This is a test email"
        assert formatted["is_unread"] is True
        assert "INBOX" in formatted["labels"]

    def test_format_message_missing_headers(self, email_service):
        """Test message formatting with missing headers."""
        msg = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX"],
            "snippet": "Test",
            "payload": {
                "headers": []
            }
        }

        formatted = email_service._format_message(msg)

        assert formatted["subject"] == "No subject"
        assert formatted["from"] == "Unknown"
        assert formatted["to"] == ""
        assert formatted["is_unread"] is False


class TestEmailEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_email_list(self, email_service, mock_gmail_service, test_db):
        """Test handling empty email list."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": []
        }

        new_messages = email_service.get_new_messages()

        assert new_messages == []

    def test_cached_message_becomes_unnotified(self, email_service, mock_gmail_service, test_db):
        """Test that cached but unnotified messages are returned and marked notified."""
        # Pre-cache a message as NOT notified
        with get_session() as session:
            cache_entry = EmailCache(
                id="msg001",
                subject="Not yet notified",
                sender="test@example.com",
                received_at=datetime.utcnow(),
                notified=False  # Not yet notified
            )
            session.add(cache_entry)
            session.commit()

        # Mock API returning the same message
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Test",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Not yet notified"},
                    {"name": "From", "value": "test@example.com"}
                ]
            }
        }

        # Get new messages
        new_messages = email_service.get_new_messages()

        # Should return the message
        assert len(new_messages) == 1
        assert new_messages[0]["id"] == "msg001"

        # Check that it's now marked as notified
        with get_session() as session:
            cached = session.query(EmailCache).filter_by(id="msg001").first()
            assert cached.notified is True

    def test_multiple_category_labels_all_filtered(self, email_service, mock_gmail_service, test_db):
        """Test email with multiple excluded category labels."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD", "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES"],
            "snippet": "Spam",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Spam"},
                    {"name": "From", "value": "spam@spam.com"}
                ]
            }
        }

        new_messages = email_service.get_new_messages()

        # Should be filtered out
        assert len(new_messages) == 0

    def test_primary_inbox_message_not_filtered(self, email_service, mock_gmail_service, test_db):
        """Test that primary inbox messages pass through filters."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg001"}]
        }

        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD", "IMPORTANT"],  # No CATEGORY_* labels
            "snippet": "Important email",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Important"},
                    {"name": "From", "value": "boss@company.com"}
                ]
            }
        }

        new_messages = email_service.get_new_messages()

        # Should NOT be filtered
        assert len(new_messages) == 1
        assert new_messages[0]["id"] == "msg001"


class TestLabelManagement:
    """Test email label operations."""

    def test_add_label_existing(self, email_service, mock_gmail_service):
        """Test adding an existing label to a message."""
        # Mock label list
        mock_gmail_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_1", "name": "Work", "type": "user"}
            ]
        }

        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.add_label("msg001", "Work")

        assert result is True
        call_args = mock_gmail_service.users().messages().modify.call_args
        assert "Label_1" in call_args[1]["body"]["addLabelIds"]

    def test_add_label_create_new(self, email_service, mock_gmail_service):
        """Test creating and adding a new label."""
        # Mock empty label list
        mock_gmail_service.users().labels().list().execute.return_value = {
            "labels": []
        }

        # Mock label creation
        mock_create = Mock()
        mock_create.execute.return_value = {"id": "Label_2", "name": "NewLabel"}
        mock_gmail_service.users().labels().create.return_value = mock_create

        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.add_label("msg001", "NewLabel")

        assert result is True
        # Should have created the label
        mock_gmail_service.users().labels().create.assert_called_once()

    def test_remove_label(self, email_service, mock_gmail_service):
        """Test removing a label from a message."""
        mock_gmail_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_1", "name": "Work", "type": "user"}
            ]
        }

        mock_modify = Mock()
        mock_modify.execute.return_value = {}
        mock_gmail_service.users().messages().modify.return_value = mock_modify

        result = email_service.remove_label("msg001", "Work")

        assert result is True
        call_args = mock_gmail_service.users().messages().modify.call_args
        assert "Label_1" in call_args[1]["body"]["removeLabelIds"]
