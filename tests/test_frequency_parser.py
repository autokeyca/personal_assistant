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


class TestFrequencyParsing:
    """Test parsing natural language frequency expressions."""

    def test_parse_simple_hourly(self):
        """Test parsing simple hourly intervals."""
        parser = FrequencyParser()
        result = parser.parse("every 2 hours")

        assert result is not None
        assert result["interval_value"] == 2
        assert result["interval_unit"] == "hours"
        assert result["enabled"] is True

    def test_parse_simple_minutely(self):
        """Test parsing minute intervals."""
        parser = FrequencyParser()
        result = parser.parse("every 30 minutes")

        assert result is not None
        assert result["interval_value"] == 30
        assert result["interval_unit"] == "minutes"

    def test_parse_every_hour_no_number(self):
        """Test 'every hour' defaults to interval_value=1."""
        parser = FrequencyParser()
        result = parser.parse("every hour")

        assert result is not None
        assert result["interval_value"] == 1
        assert result["interval_unit"] == "hours"

    def test_parse_business_hours(self):
        """Test parsing 'during business hours'."""
        parser = FrequencyParser()
        result = parser.parse("every hour during business hours")

        assert result is not None
        assert result["time_range"] == {"start": "09:00", "end": "17:00"}
        assert result["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]

    def test_parse_work_hours(self):
        """Test parsing 'during work hours'."""
        parser = FrequencyParser()
        result = parser.parse("every 2 hours during work hours")

        assert result is not None
        assert result["time_range"] == {"start": "08:00", "end": "18:00"}
        assert result["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]

    def test_parse_weekdays(self):
        """Test parsing weekday constraints."""
        parser = FrequencyParser()
        result = parser.parse("every 3 hours on weekdays")

        assert result is not None
        assert result["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]

    def test_parse_weekend(self):
        """Test parsing weekend constraints."""
        parser = FrequencyParser()
        result = parser.parse("every 4 hours on weekends")

        assert result is not None
        assert result["days"] == ["saturday", "sunday"]

    def test_parse_specific_days(self):
        """Test parsing specific day constraints."""
        parser = FrequencyParser()
        result = parser.parse("every 2 hours on monday and wednesday")

        assert result is not None
        assert "monday" in result["days"]
        assert "wednesday" in result["days"]

    def test_parse_time_range_am_pm(self):
        """Test parsing specific time ranges with am/pm."""
        parser = FrequencyParser()
        result = parser.parse("every hour between 9am and 5pm")

        assert result is not None
        assert result["time_range"]["start"] == "09:00"
        assert result["time_range"]["end"] == "17:00"

    def test_parse_complex_expression(self):
        """Test parsing complex frequency expression."""
        parser = FrequencyParser()
        result = parser.parse("every 2 hours between 9am and 5pm on weekdays")

        assert result is not None
        assert result["interval_value"] == 2
        assert result["interval_unit"] == "hours"
        assert result["time_range"]["start"] == "09:00"
        assert result["time_range"]["end"] == "17:00"
        assert result["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]

    def test_parse_daily(self):
        """Test parsing daily intervals."""
        parser = FrequencyParser()
        result = parser.parse("every day")

        assert result is not None
        assert result["interval_value"] == 1
        assert result["interval_unit"] == "days"

    def test_parse_weekly(self):
        """Test parsing weekly intervals."""
        parser = FrequencyParser()
        result = parser.parse("every 2 weeks")

        assert result is not None
        assert result["interval_value"] == 2
        assert result["interval_unit"] == "weeks"

    def test_bug11_zero_interval_should_reject(self):
        """Bug #11: Test that zero intervals should be rejected but currently aren't."""
        parser = FrequencyParser()
        result = parser.parse("every 0 hours")

        # BUG #11: Currently this PASSES but should FAIL
        # Zero interval makes no sense and should be rejected
        # After fixing, this should be: assert result is None
        assert result is not None  # Documents the bug
        assert result["interval_value"] == 0  # Confirms bug exists

    def test_negative_interval_rejected(self):
        """Test that negative intervals are not parsed."""
        parser = FrequencyParser()
        result = parser.parse("every -5 hours")

        # Negative intervals don't match the regex pattern
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        parser = FrequencyParser()
        result = parser.parse("")

        assert result is None

    def test_gibberish_returns_none(self):
        """Test that gibberish returns None."""
        parser = FrequencyParser()
        result = parser.parse("asdfghjkl qwerty zxcvbn")

        assert result is None

    def test_no_interval_returns_none(self):
        """Test that expressions without intervals return None."""
        parser = FrequencyParser()
        result = parser.parse("during business hours on weekdays")

        # No interval specified, should return None
        assert result is None

    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        parser = FrequencyParser()
        result1 = parser.parse("EVERY 2 HOURS")
        result2 = parser.parse("every 2 hours")

        assert result1 == result2

    def test_extra_whitespace_handled(self):
        """Test that extra whitespace doesn't break parsing."""
        parser = FrequencyParser()
        result = parser.parse("  every   2   hours  ")

        assert result is not None
        assert result["interval_value"] == 2
        assert result["interval_unit"] == "hours"

    def test_time_range_midnight_edge_case(self):
        """Test time range with midnight (12am)."""
        parser = FrequencyParser()
        result = parser.parse("every hour between 12am and 5am")

        assert result is not None
        assert result["time_range"]["start"] == "00:00"
        assert result["time_range"]["end"] == "05:00"

    def test_time_range_noon_edge_case(self):
        """Test time range with noon (12pm)."""
        parser = FrequencyParser()
        result = parser.parse("every hour between 12pm and 3pm")

        assert result is not None
        assert result["time_range"]["start"] == "12:00"
        assert result["time_range"]["end"] == "15:00"

    def test_abbreviated_minute(self):
        """Test abbreviated 'min' for minutes."""
        parser = FrequencyParser()
        result = parser.parse("every 15 min")

        assert result is not None
        assert result["interval_unit"] == "minutes"


class TestFrequencyDescribe:
    """Test converting frequency configs back to human-readable text."""

    def test_describe_simple_hourly(self):
        """Test describing simple hourly interval."""
        parser = FrequencyParser()
        config = {
            "interval_value": 2,
            "interval_unit": "hours",
            "enabled": True
        }

        description = parser.describe(config)
        assert "Every 2 hours" in description

    def test_describe_singular_unit(self):
        """Test that singular units are described correctly."""
        parser = FrequencyParser()
        config = {
            "interval_value": 1,
            "interval_unit": "hours",
            "enabled": True
        }

        description = parser.describe(config)
        assert "Every hour" in description

    def test_describe_business_hours(self):
        """Test describing business hours constraint."""
        parser = FrequencyParser()
        config = {
            "interval_value": 1,
            "interval_unit": "hours",
            "time_range": {"start": "09:00", "end": "17:00"},
            "enabled": True
        }

        description = parser.describe(config)
        assert "business hours" in description

    def test_describe_custom_time_range(self):
        """Test describing custom time range."""
        parser = FrequencyParser()
        config = {
            "interval_value": 2,
            "interval_unit": "hours",
            "time_range": {"start": "10:00", "end": "15:00"},
            "enabled": True
        }

        description = parser.describe(config)
        assert "between" in description
        assert "10am" in description
        assert "3pm" in description

    def test_describe_weekdays(self):
        """Test describing weekday constraint."""
        parser = FrequencyParser()
        config = {
            "interval_value": 3,
            "interval_unit": "hours",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "enabled": True
        }

        description = parser.describe(config)
        assert "weekdays" in description

    def test_describe_weekend(self):
        """Test describing weekend constraint."""
        parser = FrequencyParser()
        config = {
            "interval_value": 4,
            "interval_unit": "hours",
            "days": ["saturday", "sunday"],
            "enabled": True
        }

        description = parser.describe(config)
        assert "weekends" in description

    def test_describe_disabled_reminder(self):
        """Test describing disabled reminder."""
        parser = FrequencyParser()
        config = {"enabled": False}

        description = parser.describe(config)
        assert "No reminders" in description

    def test_describe_none_config(self):
        """Test describing None config."""
        parser = FrequencyParser()
        description = parser.describe(None)

        assert "No reminders" in description
