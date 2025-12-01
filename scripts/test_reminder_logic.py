#!/usr/bin/env python3
"""Test reminder logic for Luke's task."""

import sys
sys.path.insert(0, '/home/ja/projects/personal_assistant')

from assistant.db import init_db, get_session, Todo
from assistant.config import get as get_config
from assistant.services.frequency_parser import FrequencyParser
import json
from datetime import datetime
import pytz

db_path = get_config("database.path", "data/assistant.db")
init_db(db_path)

frequency_parser = FrequencyParser()
tz_name = get_config("timezone", "America/Montreal")
tz = pytz.timezone(tz_name)
now = datetime.now(tz)

print(f"Current time: {now}")
print(f"Timezone: {tz_name}\n")

with get_session() as session:
    todo = session.query(Todo).filter_by(id=16).first()
    if todo:
        print(f"Task ID: {todo.id}")
        print(f"Title: {todo.title}")
        print(f"Status: {todo.status}")
        print(f"User ID: {todo.user_id}")
        print(f"Last Reminder At: {todo.last_reminder_at}")
        print()

        if todo.reminder_config:
            reminder_config = json.loads(todo.reminder_config)
            print(f"Reminder Config: {json.dumps(reminder_config, indent=2)}")
            print()

            # Check if we should remind now
            should_remind = frequency_parser.should_remind_now(
                reminder_config,
                todo.last_reminder_at,
                tz_name
            )

            print(f"Should remind now? {should_remind}")
            print()

            # Check each condition
            print("=== Debugging should_remind_now ===")

            # Check enabled
            print(f"Enabled: {reminder_config.get('enabled')}")

            # Check day constraint
            current_day = now.strftime("%A").lower()
            days = reminder_config.get("days")
            print(f"Current day: {current_day}")
            print(f"Allowed days: {days}")
            if days:
                print(f"Day check passes: {current_day in days}")

            # Check time range
            time_range = reminder_config.get("time_range")
            if time_range:
                current_time = now.time()
                start_time = datetime.strptime(time_range["start"], "%H:%M").time()
                end_time = datetime.strptime(time_range["end"], "%H:%M").time()
                print(f"Current time: {current_time}")
                print(f"Time range: {start_time} - {end_time}")
                print(f"Time check passes: {start_time <= current_time <= end_time}")

            # Check interval
            if todo.last_reminder_at:
                from datetime import timedelta
                interval_value = reminder_config.get("interval_value", 1)
                interval_unit = reminder_config.get("interval_unit", "hours")

                if interval_unit == "hours":
                    delta = timedelta(hours=interval_value)
                elif interval_unit == "minutes":
                    delta = timedelta(minutes=interval_value)
                elif interval_unit == "days":
                    delta = timedelta(days=interval_value)

                # Make last_reminder_at timezone-aware if it's not
                last_reminder = todo.last_reminder_at
                if last_reminder.tzinfo is None:
                    last_reminder = tz.localize(last_reminder)

                time_since_last = now - last_reminder

                print(f"Interval: {interval_value} {interval_unit} = {delta}")
                print(f"Time since last reminder: {time_since_last}")
                print(f"Interval check passes: {time_since_last >= delta}")
        else:
            print("No reminder config set")
    else:
        print("Task not found")
