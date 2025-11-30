"""Gmail integration service for full email management."""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
import html2text
from bs4 import BeautifulSoup

from assistant.db import get_session
from assistant.db.models import EmailCache
from .google_auth import get_google_auth


class EmailService:
    """Manage Gmail emails."""

    def __init__(self):
        self._service = None
        self._html_converter = html2text.HTML2Text()
        self._html_converter.ignore_links = False
        self._html_converter.ignore_images = True

    @property
    def service(self):
        """Get the Gmail API service."""
        if self._service is None:
            self._service = get_google_auth().get_gmail_service()
        return self._service

    def list_messages(
        self,
        query: str = "",
        max_results: int = 20,
        label_ids: List[str] = None,
    ) -> List[dict]:
        """List messages matching a query.

        Common queries:
        - 'is:unread' - Unread messages
        - 'from:someone@example.com' - From specific sender
        - 'subject:important' - Subject contains word
        - 'newer_than:1d' - Last 24 hours
        - 'in:inbox' - Inbox messages
        """
        if label_ids is None:
            label_ids = ["INBOX"]

        results = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                labelIds=label_ids,
                maxResults=max_results,
            )
            .execute()
        )

        messages = results.get("messages", [])
        return [self.get_message(msg["id"]) for msg in messages]

    def get_message(self, message_id: str, format: str = "metadata") -> dict:
        """Get a specific message.

        Format options:
        - 'minimal': Just IDs
        - 'metadata': Headers and metadata
        - 'full': Complete message with body
        """
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
            .execute()
        )

        return self._format_message(msg)

    def get_message_body(self, message_id: str) -> str:
        """Get the full body of a message as plain text."""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        return self._extract_body(msg)

    def get_unread(self, max_results: int = 10) -> List[dict]:
        """Get unread messages."""
        return self.list_messages(query="is:unread", max_results=max_results)

    def get_unread_count(self) -> int:
        """Get count of unread messages."""
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q="is:unread", labelIds=["INBOX"])
            .execute()
        )
        return results.get("resultSizeEstimate", 0)

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False,
    ) -> dict:
        """Send an email."""
        if html:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "html"))
        else:
            message = MIMEText(body)

        message["to"] = to
        message["subject"] = subject

        if cc:
            message["cc"] = ", ".join(cc)
        if bcc:
            message["bcc"] = ", ".join(bcc)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        return {"id": result["id"], "status": "sent"}

    def reply(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> dict:
        """Reply to a message."""
        # Get original message
        original = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata")
            .execute()
        )

        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}

        # Build reply
        message = MIMEText(body)
        message["to"] = headers.get("From", "")
        message["subject"] = "Re: " + headers.get("Subject", "")
        message["In-Reply-To"] = headers.get("Message-ID", "")
        message["References"] = headers.get("Message-ID", "")

        if reply_all and "Cc" in headers:
            message["cc"] = headers["Cc"]

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = (
            self.service.users()
            .messages()
            .send(
                userId="me",
                body={
                    "raw": raw,
                    "threadId": original.get("threadId"),
                },
            )
            .execute()
        )

        return {"id": result["id"], "status": "sent"}

    def forward(self, message_id: str, to: str, comment: str = "") -> dict:
        """Forward a message."""
        # Get original message
        body = self.get_message_body(message_id)
        original = self.get_message(message_id)

        forward_body = f"{comment}\n\n---------- Forwarded message ----------\n"
        forward_body += f"From: {original['from']}\n"
        forward_body += f"Date: {original['date']}\n"
        forward_body += f"Subject: {original['subject']}\n\n"
        forward_body += body

        return self.send_message(
            to=to,
            subject=f"Fwd: {original['subject']}",
            body=forward_body,
        )

    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True

    def mark_unread(self, message_id: str) -> bool:
        """Mark a message as unread."""
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["UNREAD"]},
        ).execute()
        return True

    def archive(self, message_id: str) -> bool:
        """Archive a message (remove from inbox)."""
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["INBOX"]},
        ).execute()
        return True

    def trash(self, message_id: str) -> bool:
        """Move message to trash."""
        self.service.users().messages().trash(
            userId="me", id=message_id
        ).execute()
        return True

    def delete(self, message_id: str) -> bool:
        """Permanently delete a message."""
        self.service.users().messages().delete(
            userId="me", id=message_id
        ).execute()
        return True

    def add_label(self, message_id: str, label_name: str) -> bool:
        """Add a label to a message."""
        # Get or create label
        label_id = self._get_or_create_label(label_name)

        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()
        return True

    def remove_label(self, message_id: str, label_name: str) -> bool:
        """Remove a label from a message."""
        labels = self.service.users().labels().list(userId="me").execute()
        label_id = None
        for label in labels.get("labels", []):
            if label["name"].lower() == label_name.lower():
                label_id = label["id"]
                break

        if label_id:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": [label_id]},
            ).execute()
        return True

    def list_labels(self) -> List[dict]:
        """List all labels."""
        results = self.service.users().labels().list(userId="me").execute()
        return [
            {"id": l["id"], "name": l["name"], "type": l["type"]}
            for l in results.get("labels", [])
        ]

    def search(self, query: str, max_results: int = 20) -> List[dict]:
        """Search emails with Gmail query syntax."""
        return self.list_messages(query=query, max_results=max_results)

    def get_new_messages(self, since_last_check: bool = True) -> List[dict]:
        """Get new messages since last check (for notifications)."""
        # Labels to exclude from notifications (promotional, social, etc.)
        excluded_categories = {
            "CATEGORY_PROMOTIONS",
            "CATEGORY_SOCIAL",
            "CATEGORY_UPDATES",
            "CATEGORY_FORUMS",
        }

        with get_session() as session:
            messages = self.get_unread(max_results=20)
            new_messages = []

            for msg in messages:
                # Skip promotional and other non-primary emails
                msg_labels = set(msg.get("labels", []))
                if msg_labels & excluded_categories:
                    continue

                # Check if already cached
                cached = (
                    session.query(EmailCache)
                    .filter(EmailCache.id == msg["id"])
                    .first()
                )

                if not cached:
                    # New message, cache it
                    cache_entry = EmailCache(
                        id=msg["id"],
                        subject=msg["subject"],
                        sender=msg["from"],
                        received_at=datetime.utcnow(),
                        notified=True,
                    )
                    session.add(cache_entry)
                    new_messages.append(msg)
                elif not cached.notified:
                    cached.notified = True
                    new_messages.append(msg)

            return new_messages

    def _get_or_create_label(self, label_name: str) -> str:
        """Get a label ID, creating it if necessary."""
        labels = self.service.users().labels().list(userId="me").execute()
        for label in labels.get("labels", []):
            if label["name"].lower() == label_name.lower():
                return label["id"]

        # Create label
        result = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        return result["id"]

    def _format_message(self, msg: dict) -> dict:
        """Format a message for display."""
        headers = {}
        if "payload" in msg and "headers" in msg["payload"]:
            headers = {
                h["name"]: h["value"]
                for h in msg["payload"]["headers"]
            }

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "subject": headers.get("Subject", "No subject"),
            "from": headers.get("From", "Unknown"),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "labels": msg.get("labelIds", []),
            "is_unread": "UNREAD" in msg.get("labelIds", []),
        }

    def _extract_body(self, msg: dict) -> str:
        """Extract plain text body from a message."""
        payload = msg.get("payload", {})

        # Simple text message
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8")

        # Multipart message
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8")

        # Fall back to HTML converted to text
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                html = base64.urlsafe_b64decode(data).decode("utf-8")
                return self._html_converter.handle(html)

        return msg.get("snippet", "")
