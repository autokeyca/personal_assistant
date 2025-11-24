"""Scheduler for automated tasks like reminders and notifications."""

from .jobs import setup_scheduler

__all__ = ["setup_scheduler"]
