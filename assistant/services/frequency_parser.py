"""Parse natural language frequency expressions for reminders."""

import re
from typing import Dict, Optional, List
from datetime import time


class FrequencyParser:
    """Parse natural language frequency expressions into structured configurations."""

    BUSINESS_HOURS = {"start": "09:00", "end": "17:00"}
    WORK_HOURS = {"start": "08:00", "end": "18:00"}

    WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    WEEKEND = ["saturday", "sunday"]
    ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def __init__(self):
        """Initialize the frequency parser."""
        pass

    def parse(self, frequency_text: str) -> Optional[Dict]:
        """
        Parse a natural language frequency expression.

        Args:
            frequency_text: Natural language frequency like "every 2 hours during business hours"

        Returns:
            Dictionary with frequency configuration, or None if parsing failed.

        Example return:
            {
                "interval_value": 2,
                "interval_unit": "hours",
                "time_range": {"start": "09:00", "end": "17:00"},
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "enabled": True
            }
        """
        if not frequency_text:
            return None

        text = frequency_text.lower().strip()
        config = {
            "interval_value": None,
            "interval_unit": None,
            "time_range": None,
            "days": None,
            "enabled": True
        }

        # Parse interval (e.g., "every 2 hours", "every 30 minutes", "every day")
        interval_match = re.search(
            r'every\s+(\d+)?\s*(hour|hours|minute|minutes|min|day|days|week|weeks)',
            text
        )

        if interval_match:
            value_str, unit_str = interval_match.groups()
            config["interval_value"] = int(value_str) if value_str else 1

            # Normalize unit
            if unit_str in ["hour", "hours"]:
                config["interval_unit"] = "hours"
            elif unit_str in ["minute", "minutes", "min"]:
                config["interval_unit"] = "minutes"
            elif unit_str in ["day", "days"]:
                config["interval_unit"] = "days"
            elif unit_str in ["week", "weeks"]:
                config["interval_unit"] = "weeks"

        # Parse time constraints
        if "business hours" in text or "business hour" in text:
            config["time_range"] = self.BUSINESS_HOURS.copy()
            config["days"] = self.WEEKDAYS.copy()
        elif "work hours" in text or "working hours" in text:
            config["time_range"] = self.WORK_HOURS.copy()
            config["days"] = self.WEEKDAYS.copy()

        # Parse specific time range (e.g., "between 9am and 5pm")
        time_range_match = re.search(
            r'between\s+(\d+)\s*(am|pm)?\s+and\s+(\d+)\s*(am|pm)?',
            text
        )
        if time_range_match:
            start_hour, start_period, end_hour, end_period = time_range_match.groups()
            start_hour = int(start_hour)
            end_hour = int(end_hour)

            # Convert to 24-hour format
            if start_period == "pm" and start_hour != 12:
                start_hour += 12
            elif start_period == "am" and start_hour == 12:
                start_hour = 0

            if end_period == "pm" and end_hour != 12:
                end_hour += 12
            elif end_period == "am" and end_hour == 12:
                end_hour = 0

            config["time_range"] = {
                "start": f"{start_hour:02d}:00",
                "end": f"{end_hour:02d}:00"
            }

        # Parse day constraints
        if "weekday" in text or "weekdays" in text:
            config["days"] = self.WEEKDAYS.copy()
        elif "weekend" in text or "weekends" in text:
            config["days"] = self.WEEKEND.copy()
        elif "every day" in text or "daily" in text:
            config["days"] = self.ALL_DAYS.copy()

        # Parse specific days (e.g., "on Monday and Wednesday", "on Mondays")
        for day in self.ALL_DAYS:
            if day in text or f"{day}s" in text:
                if config["days"] is None:
                    config["days"] = []
                if day not in config["days"]:
                    config["days"].append(day)

        # Validate we got at least an interval
        if config["interval_value"] is None or config["interval_unit"] is None:
            return None

        return config

    def describe(self, config: Dict) -> str:
        """
        Convert a frequency configuration back to human-readable text.

        Args:
            config: Frequency configuration dictionary

        Returns:
            Human-readable description
        """
        if not config or not config.get("enabled"):
            return "No reminders set"

        parts = []

        # Interval
        interval_value = config.get("interval_value", 1)
        interval_unit = config.get("interval_unit", "hours")

        if interval_value == 1:
            parts.append(f"Every {interval_unit.rstrip('s')}")
        else:
            parts.append(f"Every {interval_value} {interval_unit}")

        # Time range
        time_range = config.get("time_range")
        if time_range:
            start = time_range.get("start", "")
            end = time_range.get("end", "")

            # Check if it's business hours
            if start == "09:00" and end == "17:00":
                parts.append("during business hours")
            else:
                # Convert to 12-hour format for display
                start_hour = int(start.split(":")[0])
                end_hour = int(end.split(":")[0])

                start_period = "am" if start_hour < 12 else "pm"
                end_period = "am" if end_hour < 12 else "pm"

                if start_hour > 12:
                    start_hour -= 12
                elif start_hour == 0:
                    start_hour = 12

                if end_hour > 12:
                    end_hour -= 12
                elif end_hour == 0:
                    end_hour = 12

                parts.append(f"between {start_hour}{start_period} and {end_hour}{end_period}")

        # Days
        days = config.get("days")
        if days:
            if set(days) == set(self.WEEKDAYS):
                parts.append("on weekdays")
            elif set(days) == set(self.WEEKEND):
                parts.append("on weekends")
            elif set(days) == set(self.ALL_DAYS):
                pass  # Don't add "every day" if already implied
            else:
                day_names = [d.capitalize() for d in days]
                if len(day_names) == 1:
                    parts.append(f"on {day_names[0]}s")
                else:
                    parts.append(f"on {', '.join(day_names[:-1])} and {day_names[-1]}")

        return " ".join(parts)

    def should_remind_now(self, config: Dict, last_reminder_time=None, timezone_name: str = None) -> bool:
        """
        Check if a reminder should be sent now based on the configuration.

        Args:
            config: Frequency configuration dictionary
            last_reminder_time: datetime of last reminder sent (None if never sent)
            timezone_name: Timezone name (defaults to system timezone from config)

        Returns:
            True if a reminder should be sent now
        """
        from datetime import datetime, timedelta
        import pytz

        if not config or not config.get("enabled"):
            return False

        # Use timezone-aware datetime
        if timezone_name is None:
            from assistant.config import get as get_config
            timezone_name = get_config("timezone", "America/Montreal")

        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)

        # Check day constraint
        days = config.get("days")
        if days:
            current_day = now.strftime("%A").lower()
            if current_day not in days:
                return False

        # Check time range constraint
        time_range = config.get("time_range")
        if time_range:
            current_time = now.time()
            start_time = datetime.strptime(time_range["start"], "%H:%M").time()
            end_time = datetime.strptime(time_range["end"], "%H:%M").time()

            if not (start_time <= current_time <= end_time):
                return False

        # Check interval
        if last_reminder_time:
            interval_value = config.get("interval_value", 1)
            interval_unit = config.get("interval_unit", "hours")

            if interval_unit == "minutes":
                delta = timedelta(minutes=interval_value)
            elif interval_unit == "hours":
                delta = timedelta(hours=interval_value)
            elif interval_unit == "days":
                delta = timedelta(days=interval_value)
            elif interval_unit == "weeks":
                delta = timedelta(weeks=interval_value)
            else:
                return False

            # Make last_reminder_time timezone-aware if it's naive
            if last_reminder_time.tzinfo is None:
                last_reminder_time = tz.localize(last_reminder_time)

            time_since_last = now - last_reminder_time

            # Only remind if enough time has passed
            if time_since_last < delta:
                return False

        return True
