"""Google Calendar integration service."""

from datetime import datetime, timedelta
from typing import List, Optional
import pytz
from dateutil import parser as date_parser

from .google_auth import get_google_auth


class CalendarService:
    """Manage Google Calendar events."""

    def __init__(self):
        self._service = None

    @property
    def service(self):
        """Get the Calendar API service."""
        if self._service is None:
            self._service = get_google_auth().get_calendar_service()
        return self._service

    def list_events(
        self,
        days: int = 7,
        max_results: int = 20,
        calendar_id: str = "primary",
    ) -> List[dict]:
        """List upcoming events for the specified number of days."""
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days)).isoformat() + "Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        return [self._format_event(e) for e in events]

    def get_today_events(self, calendar_id: str = "primary") -> List[dict]:
        """Get all events for today."""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + "Z",
                timeMax=end_of_day.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        return [self._format_event(e) for e in events]

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime = None,
        description: str = None,
        location: str = None,
        attendees: List[str] = None,
        calendar_id: str = "primary",
        timezone: str = None,
    ) -> dict:
        """Create a new calendar event."""
        if end is None:
            end = start + timedelta(hours=1)

        if timezone is None:
            timezone = "UTC"

        event = {
            "summary": summary,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": timezone,
            },
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        result = (
            self.service.events()
            .insert(calendarId=calendar_id, body=event)
            .execute()
        )

        return self._format_event(result)

    def quick_add(self, text: str, calendar_id: str = "primary") -> dict:
        """Create event using natural language (e.g., 'Dinner with John tomorrow at 7pm')."""
        result = (
            self.service.events()
            .quickAdd(calendarId=calendar_id, text=text)
            .execute()
        )
        return self._format_event(result)

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start: datetime = None,
        end: datetime = None,
        description: str = None,
        location: str = None,
        calendar_id: str = "primary",
    ) -> dict:
        """Update an existing event."""
        event = (
            self.service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )

        if summary:
            event["summary"] = summary
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if start:
            event["start"]["dateTime"] = start.isoformat()
        if end:
            event["end"]["dateTime"] = end.isoformat()

        result = (
            self.service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )

        return self._format_event(result)

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete an event."""
        self.service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        return True

    def search_events(
        self,
        query: str,
        days: int = 30,
        calendar_id: str = "primary",
    ) -> List[dict]:
        """Search for events by text."""
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days)).isoformat() + "Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=query,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        return [self._format_event(e) for e in events]

    def get_free_busy(
        self,
        start: datetime,
        end: datetime,
        calendar_ids: List[str] = None,
    ) -> dict:
        """Check free/busy times."""
        if calendar_ids is None:
            calendar_ids = ["primary"]

        body = {
            "timeMin": start.isoformat() + "Z",
            "timeMax": end.isoformat() + "Z",
            "items": [{"id": cal_id} for cal_id in calendar_ids],
        }

        result = self.service.freebusy().query(body=body).execute()
        return result.get("calendars", {})

    def _format_event(self, event: dict) -> dict:
        """Format a calendar event for display."""
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle all-day events vs timed events
        if "dateTime" in start:
            start_dt = date_parser.parse(start["dateTime"])
            end_dt = date_parser.parse(end["dateTime"])
            all_day = False
        else:
            start_dt = date_parser.parse(start.get("date", ""))
            end_dt = date_parser.parse(end.get("date", ""))
            all_day = True

        return {
            "id": event.get("id"),
            "summary": event.get("summary", "No title"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            "all_day": all_day,
            "link": event.get("htmlLink"),
            "attendees": [
                a.get("email") for a in event.get("attendees", [])
            ],
        }
