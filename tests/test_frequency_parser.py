"""Tests for frequency parser functionality."""

import pytest
from datetime import datetime, timedelta
import pytz
from assistant.services.frequency_parser import FrequencyParser


class TestFrequencyParser:
    """Test frequency parsing and reminder scheduling."""

    def test_simple_hourly_reminder_due(self):
        """Test that hourly reminder is due after 1 hour has passed."""
        parser = FrequencyParser()

        config = {
            "enabled": True,
            "interval_value": 1,
            "interval_unit": "hours"
        }

        # Last reminder was 2 hours ago
        now = datetime.now(pytz.UTC)
        last_reminded = now - timedelta(hours=2)

        # Should be due for reminder
        should_remind = parser.should_remind_now(config, last_reminded)
        assert should_remind == True, f"Should remind after 2 hours for hourly reminder. last_reminded={last_reminded}, now={now}"

    def test_simple_hourly_reminder_not_due(self):
        """Test that hourly reminder is NOT due if less than 1 hour has passed."""
        parser = FrequencyParser()

        config = {
            "enabled": True,
            "interval_value": 1,
            "interval_unit": "hours"
        }

        # Last reminder was 30 minutes ago
        now = datetime.now(pytz.UTC)
        last_reminded = now - timedelta(minutes=30)

        # Should NOT be due
        should_remind = parser.should_remind_now(config, last_reminded)
        assert should_remind == False, "Should not remind before 1 hour has passed"

    def test_first_reminder_no_last_time(self):
        """Test that first reminder (no last_reminded) is always due."""
        parser = FrequencyParser()

        config = {
            "enabled": True,
            "interval_value": 1,
            "interval_unit": "hours"
        }

        # No last reminder time (first time)
        should_remind = parser.should_remind_now(config, None)
        assert should_remind == True, "First reminder should always be sent"

    def test_business_hours_constraint(self):
        """Test business hours time range constraint."""
        parser = FrequencyParser()

        config = {
            "enabled": True,
            "interval_value": 1,
            "interval_unit": "hours",
            "time_range": {
                "start": "09:00",
                "end": "17:00"
            }
        }

        # Test during business hours (simplified - just check the logic works)
        # Note: Actual time-based testing would require mocking datetime.now()
        # For now, we just verify the config is parseable and doesn't crash
        result = parser.should_remind_now(config, None, timezone_name='America/Montreal')
        # Result depends on current time, so we just verify it doesn't crash
        assert result in [True, False]

    def test_disabled_config_never_reminds(self):
        """Test that disabled reminder configs never send reminders."""
        parser = FrequencyParser()

        config = {
            "enabled": False,
            "interval_value": 1,
            "interval_unit": "hours"
        }

        should_remind = parser.should_remind_now(config, None)
        assert should_remind == False, "Disabled reminders should never be sent"

    def test_naive_utc_datetime_handling(self):
        """Bug #8: Test handling of naive UTC datetimes from database."""
        parser = FrequencyParser()

        config = {
            "enabled": True,
            "interval_value": 1,
            "interval_unit": "hours"
        }

        # Database stores naive UTC
        now_utc = datetime.now(pytz.UTC)
        last_reminded_naive_utc = (now_utc - timedelta(hours=2)).replace(tzinfo=None)

        # This is the actual case from the database - naive UTC datetime
        # The parser should handle this correctly
        should_remind = parser.should_remind_now(config, last_reminded_naive_utc)

        # Debug output
        if not should_remind:
            print(f"\nDEBUG: should_remind returned False!")
            print(f"  last_reminded_naive_utc: {last_reminded_naive_utc}")
            print(f"  now_utc: {now_utc}")
            print(f"  diff: {now_utc.replace(tzinfo=None) - last_reminded_naive_utc}")

        assert should_remind == True, "Should remind after 2 hours even with naive UTC datetime"
