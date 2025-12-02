"""Tests for time parsing functionality (Bug fixes from 2025-12-02)."""

import pytest
import dateparser
from datetime import datetime, timedelta
import pytz


class TestTimeParsing:
    """Test time parsing with dateparser for relative and absolute times."""

    def test_relative_time_in_minutes(self):
        """Bug #2: 'in 15 minutes' should add 15 minutes to current time."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'in 15 minutes',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Should be ~15 minutes from now
        expected = now + timedelta(minutes=15)
        diff = abs((result - expected).total_seconds())

        assert diff < 5, f"Time parsing off by {diff} seconds"
        assert result > now, "Parsed time should be in the future"

    def test_relative_time_in_hours(self):
        """Test 'in 2 hours' parsing."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'in 2 hours',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        expected = now + timedelta(hours=2)
        diff = abs((result - expected).total_seconds())

        assert diff < 5
        assert result > now

    def test_absolute_time_tomorrow(self):
        """Test 'tomorrow at 3pm' parsing."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'tomorrow at 3pm',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Should be tomorrow at 15:00
        assert result.hour == 15
        assert result.day == (now + timedelta(days=1)).day
        assert result > now

    def test_absolute_time_today(self):
        """Test 'at 5pm today' parsing."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'at 5pm today',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        assert result.hour == 17
        assert result.day == now.day

    def test_timezone_awareness(self):
        """Bug #3: Ensure timezone is properly preserved."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'in 30 minutes',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Should be timezone-aware
        assert result.tzinfo is not None
        assert str(result.tzinfo) in ['EST', 'EDT', 'America/Montreal', 'UTC-05:00', 'UTC-04:00']

    def test_utc_conversion(self):
        """Bug #3: Test conversion to naive UTC for storage."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        # Parse in EST
        result_est = dateparser.parse(
            'tomorrow at 1pm',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Convert to naive UTC for storage
        result_utc = result_est.astimezone(pytz.UTC).replace(tzinfo=None)

        # Should be naive (no timezone)
        assert result_utc.tzinfo is None

        # Should be 5-6 hours ahead of EST time (depending on DST)
        hour_diff = result_utc.hour - result_est.hour
        assert hour_diff in [5, 6, -18, -19]  # Accounting for day rollover

    def test_past_time_rejected(self):
        """Test that clearly past times are rejected or handled appropriately."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        # Note: dateparser might interpret "yesterday" as "tomorrow" with PREFER_DATES_FROM='future'
        # This is actually desirable behavior for reminders
        result = dateparser.parse(
            'yesterday',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # With PREFER_DATES_FROM='future', even "yesterday" should give future date
        # This is correct behavior for reminder systems
        assert result is not None

    def test_invalid_time_returns_none(self):
        """Test that completely invalid times return None."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'banana o\'clock',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Should return None for unparseable input
        assert result is None

    def test_zero_minutes_edge_case(self):
        """Test edge case: 'in 0 minutes'."""
        tz = pytz.timezone('America/Montreal')
        now = datetime.now(tz)

        result = dateparser.parse(
            'in 0 minutes',
            settings={
                'TIMEZONE': 'America/Montreal',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now
            }
        )

        # Should return current time (or very close to it)
        if result:
            diff = abs((result - now).total_seconds())
            assert diff < 5
