"""Tests for CalendarService - event handling and edge cases."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from assistant.services import CalendarService


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar API service."""
    service = Mock()

    # Mock events chain
    events_mock = Mock()
    service.events.return_value = events_mock

    # Mock freebusy chain
    freebusy_mock = Mock()
    service.freebusy.return_value = freebusy_mock

    return service


@pytest.fixture
def calendar_service(mock_calendar_service):
    """Create CalendarService with mocked API."""
    with patch('assistant.services.calendar.get_google_auth') as mock_auth:
        mock_auth.return_value.get_calendar_service.return_value = mock_calendar_service
        service = CalendarService()
        service._service = mock_calendar_service
        return service


class TestEventRetrieval:
    """Test event retrieval and listing."""

    def test_list_upcoming_events(self, calendar_service, mock_calendar_service):
        """Test listing upcoming events."""
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "event001",
                    "summary": "Team Meeting",
                    "start": {"dateTime": "2025-12-03T10:00:00Z"},
                    "end": {"dateTime": "2025-12-03T11:00:00Z"}
                },
                {
                    "id": "event002",
                    "summary": "Lunch with Client",
                    "start": {"dateTime": "2025-12-03T12:00:00Z"},
                    "end": {"dateTime": "2025-12-03T13:00:00Z"}
                }
            ]
        }

        events = calendar_service.list_events(days=7)

        assert len(events) == 2
        assert events[0]["summary"] == "Team Meeting"
        assert events[1]["summary"] == "Lunch with Client"
        assert events[0]["all_day"] is False

    def test_list_events_empty(self, calendar_service, mock_calendar_service):
        """Test listing when no events exist."""
        mock_calendar_service.events().list().execute.return_value = {
            "items": []
        }

        events = calendar_service.list_events(days=7)

        assert events == []

    def test_get_today_events(self, calendar_service, mock_calendar_service):
        """Test getting today's events."""
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "event001",
                    "summary": "Morning Standup",
                    "start": {"dateTime": "2025-12-03T09:00:00Z"},
                    "end": {"dateTime": "2025-12-03T09:30:00Z"}
                }
            ]
        }

        events = calendar_service.get_today_events()

        assert len(events) == 1
        assert events[0]["summary"] == "Morning Standup"

    def test_search_events(self, calendar_service, mock_calendar_service):
        """Test searching events by query."""
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "event001",
                    "summary": "Interview with John",
                    "start": {"dateTime": "2025-12-05T14:00:00Z"},
                    "end": {"dateTime": "2025-12-05T15:00:00Z"}
                }
            ]
        }

        events = calendar_service.search_events("Interview")

        assert len(events) == 1
        assert "Interview" in events[0]["summary"]


class TestEventCreation:
    """Test event creation."""

    def test_create_event_minimal(self, calendar_service, mock_calendar_service):
        """Test creating event with minimal required fields."""
        mock_calendar_service.events().insert().execute.return_value = {
            "id": "new_event_001",
            "summary": "New Meeting",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        start = datetime(2025, 12, 5, 10, 0, 0)
        event = calendar_service.create_event(
            summary="New Meeting",
            start=start
        )

        assert event["id"] == "new_event_001"
        assert event["summary"] == "New Meeting"

    def test_create_event_with_all_fields(self, calendar_service, mock_calendar_service):
        """Test creating event with all optional fields."""
        mock_calendar_service.events().insert().execute.return_value = {
            "id": "full_event_001",
            "summary": "Client Presentation",
            "description": "Q4 results",
            "location": "Conference Room A",
            "start": {"dateTime": "2025-12-05T14:00:00Z"},
            "end": {"dateTime": "2025-12-05T15:00:00Z"},
            "attendees": [
                {"email": "client@example.com"}
            ]
        }

        start = datetime(2025, 12, 5, 14, 0, 0)
        end = datetime(2025, 12, 5, 15, 0, 0)

        event = calendar_service.create_event(
            summary="Client Presentation",
            start=start,
            end=end,
            description="Q4 results",
            location="Conference Room A",
            attendees=["client@example.com"]
        )

        assert event["summary"] == "Client Presentation"
        assert event["description"] == "Q4 results"
        assert event["location"] == "Conference Room A"
        assert "client@example.com" in event["attendees"]

    def test_create_event_default_end_time(self, calendar_service, mock_calendar_service):
        """Test that event defaults to 1 hour duration if end not specified."""
        def capture_insert(*args, **kwargs):
            body = kwargs.get('body')
            # Verify end is 1 hour after start
            start_dt = datetime.fromisoformat(body['start']['dateTime'])
            end_dt = datetime.fromisoformat(body['end']['dateTime'])
            assert (end_dt - start_dt) == timedelta(hours=1)

            return Mock(execute=lambda: {
                "id": "event001",
                "summary": body["summary"],
                "start": body["start"],
                "end": body["end"]
            })

        mock_calendar_service.events().insert.side_effect = capture_insert

        start = datetime(2025, 12, 5, 10, 0, 0)
        event = calendar_service.create_event(summary="Test", start=start)

        assert event["id"] == "event001"

    def test_quick_add_natural_language(self, calendar_service, mock_calendar_service):
        """Test quick add with natural language."""
        mock_calendar_service.events().quickAdd().execute.return_value = {
            "id": "quick_001",
            "summary": "Dinner with Sarah tomorrow at 7pm",
            "start": {"dateTime": "2025-12-04T19:00:00Z"},
            "end": {"dateTime": "2025-12-04T20:00:00Z"}
        }

        event = calendar_service.quick_add("Dinner with Sarah tomorrow at 7pm")

        assert event["id"] == "quick_001"
        assert "Dinner" in event["summary"]


class TestEventModification:
    """Test event updates and deletion."""

    def test_update_event_summary(self, calendar_service, mock_calendar_service):
        """Test updating event summary."""
        # Mock get (retrieve current event)
        mock_calendar_service.events().get().execute.return_value = {
            "id": "event001",
            "summary": "Old Title",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        # Mock update
        mock_calendar_service.events().update().execute.return_value = {
            "id": "event001",
            "summary": "New Title",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        event = calendar_service.update_event(
            event_id="event001",
            summary="New Title"
        )

        assert event["summary"] == "New Title"

    def test_update_event_time(self, calendar_service, mock_calendar_service):
        """Test updating event start and end times."""
        mock_calendar_service.events().get().execute.return_value = {
            "id": "event001",
            "summary": "Meeting",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        new_start = datetime(2025, 12, 5, 14, 0, 0)
        new_end = datetime(2025, 12, 5, 15, 0, 0)

        mock_calendar_service.events().update().execute.return_value = {
            "id": "event001",
            "summary": "Meeting",
            "start": {"dateTime": new_start.isoformat()},
            "end": {"dateTime": new_end.isoformat()}
        }

        event = calendar_service.update_event(
            event_id="event001",
            start=new_start,
            end=new_end
        )

        assert event["id"] == "event001"

    def test_delete_event(self, calendar_service, mock_calendar_service):
        """Test deleting an event."""
        mock_delete = Mock()
        mock_delete.execute.return_value = None
        mock_calendar_service.events().delete.return_value = mock_delete

        result = calendar_service.delete_event("event001")

        assert result is True
        # Verify delete was called with correct parameters
        call_args = mock_calendar_service.events().delete.call_args
        assert call_args[1]["eventId"] == "event001"
        assert call_args[1]["calendarId"] == "primary"


class TestAllDayEvents:
    """Test all-day event handling."""

    def test_all_day_event_detection(self, calendar_service):
        """Test that all-day events are correctly identified."""
        event = {
            "id": "allday001",
            "summary": "Holiday",
            "start": {"date": "2025-12-25"},
            "end": {"date": "2025-12-26"}
        }

        formatted = calendar_service._format_event(event)

        assert formatted["all_day"] is True
        assert formatted["summary"] == "Holiday"

    def test_timed_event_detection(self, calendar_service):
        """Test that timed events are correctly identified."""
        event = {
            "id": "timed001",
            "summary": "Meeting",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        formatted = calendar_service._format_event(event)

        assert formatted["all_day"] is False
        assert formatted["summary"] == "Meeting"


class TestEventFormatting:
    """Test event formatting edge cases."""

    def test_format_event_with_all_fields(self, calendar_service):
        """Test formatting event with all optional fields present."""
        event = {
            "id": "complete_event",
            "summary": "Complete Event",
            "description": "Event description",
            "location": "Office",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"},
            "htmlLink": "https://calendar.google.com/event?eid=...",
            "attendees": [
                {"email": "person1@example.com"},
                {"email": "person2@example.com"}
            ]
        }

        formatted = calendar_service._format_event(event)

        assert formatted["summary"] == "Complete Event"
        assert formatted["description"] == "Event description"
        assert formatted["location"] == "Office"
        assert formatted["link"] == "https://calendar.google.com/event?eid=..."
        assert len(formatted["attendees"]) == 2
        assert "person1@example.com" in formatted["attendees"]

    def test_format_event_missing_optional_fields(self, calendar_service):
        """Test formatting event with missing optional fields."""
        event = {
            "id": "minimal_event",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        formatted = calendar_service._format_event(event)

        assert formatted["summary"] == "No title"
        assert formatted["description"] is None
        assert formatted["location"] is None
        assert formatted["link"] is None
        assert formatted["attendees"] == []

    def test_format_event_with_no_attendees(self, calendar_service):
        """Test formatting event with no attendees."""
        event = {
            "id": "no_attendees",
            "summary": "Solo Work",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        formatted = calendar_service._format_event(event)

        assert formatted["attendees"] == []


class TestFreeBusy:
    """Test free/busy time checking."""

    def test_check_free_busy(self, calendar_service, mock_calendar_service):
        """Test checking free/busy times."""
        mock_calendar_service.freebusy().query().execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": "2025-12-05T10:00:00Z",
                            "end": "2025-12-05T11:00:00Z"
                        }
                    ]
                }
            }
        }

        start = datetime(2025, 12, 5, 9, 0, 0)
        end = datetime(2025, 12, 5, 17, 0, 0)

        result = calendar_service.get_free_busy(start, end)

        assert "primary" in result
        assert "busy" in result["primary"]

    def test_free_busy_multiple_calendars(self, calendar_service, mock_calendar_service):
        """Test free/busy with multiple calendars."""
        mock_calendar_service.freebusy().query().execute.return_value = {
            "calendars": {
                "primary": {"busy": []},
                "work": {"busy": [{"start": "2025-12-05T10:00:00Z", "end": "2025-12-05T11:00:00Z"}]}
            }
        }

        start = datetime(2025, 12, 5, 9, 0, 0)
        end = datetime(2025, 12, 5, 17, 0, 0)

        result = calendar_service.get_free_busy(
            start,
            end,
            calendar_ids=["primary", "work"]
        )

        assert "primary" in result
        assert "work" in result


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_event_with_empty_summary(self, calendar_service):
        """Test handling event with empty summary."""
        event = {
            "id": "no_summary",
            "summary": "",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        formatted = calendar_service._format_event(event)

        # Empty summary should not be replaced with "No title"
        # (only missing summary gets default)
        assert formatted["summary"] == ""

    def test_event_with_special_characters(self, calendar_service):
        """Test event with special characters in fields."""
        event = {
            "id": "special_chars",
            "summary": "Meeting & Discussion: Q&A Session (重要)",
            "description": "Special chars: <>&\"'",
            "location": "Room #42 @ Building-A",
            "start": {"dateTime": "2025-12-05T10:00:00Z"},
            "end": {"dateTime": "2025-12-05T11:00:00Z"}
        }

        formatted = calendar_service._format_event(event)

        assert formatted["summary"] == "Meeting & Discussion: Q&A Session (重要)"
        assert formatted["description"] == "Special chars: <>&\"'"
        assert formatted["location"] == "Room #42 @ Building-A"

    def test_list_events_with_custom_calendar(self, calendar_service, mock_calendar_service):
        """Test listing events from non-primary calendar."""
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "work_event",
                    "summary": "Work Meeting",
                    "start": {"dateTime": "2025-12-05T10:00:00Z"},
                    "end": {"dateTime": "2025-12-05T11:00:00Z"}
                }
            ]
        }

        events = calendar_service.list_events(calendar_id="work@example.com")

        assert len(events) == 1
        # Verify the calendar_id was passed correctly
        call_args = mock_calendar_service.events().list.call_args
        assert call_args[1]["calendarId"] == "work@example.com"

    def test_create_event_with_timezone(self, calendar_service, mock_calendar_service):
        """Test creating event with specific timezone."""
        def capture_insert(*args, **kwargs):
            body = kwargs.get('body')
            assert body['start']['timeZone'] == 'America/New_York'
            assert body['end']['timeZone'] == 'America/New_York'

            return Mock(execute=lambda: {
                "id": "tz_event",
                "summary": body["summary"],
                "start": body["start"],
                "end": body["end"]
            })

        mock_calendar_service.events().insert.side_effect = capture_insert

        start = datetime(2025, 12, 5, 10, 0, 0)
        event = calendar_service.create_event(
            summary="Meeting",
            start=start,
            timezone="America/New_York"
        )

        assert event["id"] == "tz_event"
