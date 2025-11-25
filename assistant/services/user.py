"""User management service for Jeeves."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import User as TelegramUser

from assistant.db import get_session, User, ConversationHistory, PendingApproval
from assistant.config import get

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and their interactions with Jeeves."""

    def __init__(self):
        self.owner_id = get("telegram.authorized_user_id")

    def get_or_create_user(self, telegram_user: TelegramUser) -> User:
        """
        Get existing user or create new one from Telegram user object.

        Args:
            telegram_user: Telegram User object from update

        Returns:
            User database object
        """
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_user.id).first()

            is_new = False
            if not user:
                is_new = True
                is_owner = telegram_user.id == self.owner_id
                user = User(
                    telegram_id=telegram_user.id,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    username=telegram_user.username,
                    is_owner=is_owner,
                    is_authorized=is_owner,  # Owner is always authorized
                )
                session.add(user)
                logger.info(f"Created new user: {user.full_name} (ID: {telegram_user.id})")
            else:
                # Update user info in case it changed
                user.first_name = telegram_user.first_name
                user.last_name = telegram_user.last_name
                user.username = telegram_user.username
                user.last_seen = datetime.utcnow()

            session.commit()
            session.refresh(user)

            return user, is_new

    def is_owner(self, telegram_id: int) -> bool:
        """Check if user is the owner."""
        return telegram_id == self.owner_id

    def is_authorized(self, telegram_id: int) -> bool:
        """
        Check if user is authorized to execute tasks.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if user is authorized (owner or explicitly authorized)
        """
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return False
            return user.is_authorized

    def authorize_user(self, telegram_id: int) -> bool:
        """
        Authorize a user to execute tasks.

        Args:
            telegram_id: Telegram user ID to authorize

        Returns:
            True if successful
        """
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return False

            user.is_authorized = True
            session.commit()
            logger.info(f"Authorized user: {user.full_name} (ID: {telegram_id})")
            return True

    def revoke_authorization(self, telegram_id: int) -> bool:
        """
        Revoke user's authorization to execute tasks.

        Args:
            telegram_id: Telegram user ID to revoke

        Returns:
            True if successful
        """
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user or user.is_owner:
                return False  # Can't revoke owner's authorization

            user.is_authorized = False
            session.commit()
            logger.info(f"Revoked authorization: {user.full_name} (ID: {telegram_id})")
            return True

    def add_conversation(self, telegram_id: int, role: str, message: str):
        """
        Add a message to conversation history.

        Args:
            telegram_id: Telegram user ID
            role: 'user' or 'assistant'
            message: The message content
        """
        with get_session() as session:
            conversation = ConversationHistory(
                user_id=telegram_id,
                role=role,
                message=message
            )
            session.add(conversation)
            session.commit()

    def get_conversation_history(
        self,
        telegram_id: int,
        limit: int = 10,
        hours: Optional[int] = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for a user.

        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of messages to return
            hours: Only include messages from last N hours (None for all)

        Returns:
            List of conversation messages
        """
        with get_session() as session:
            query = session.query(ConversationHistory).filter_by(user_id=telegram_id)

            if hours:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                query = query.filter(ConversationHistory.timestamp >= cutoff)

            conversations = query.order_by(
                ConversationHistory.timestamp.desc()
            ).limit(limit).all()

            # Reverse to get chronological order
            return [conv.to_dict() for conv in reversed(conversations)]

    def create_approval_request(
        self,
        requester_id: int,
        request_message: str,
        intent: Optional[str] = None,
        entities: Optional[str] = None
    ) -> int:
        """
        Create a pending approval request.

        Args:
            requester_id: Telegram ID of user making request
            request_message: Original message from user
            intent: Parsed intent from LLM
            entities: JSON-encoded entities

        Returns:
            ID of created approval request
        """
        with get_session() as session:
            approval = PendingApproval(
                requester_id=requester_id,
                request_message=request_message,
                intent=intent,
                entities=entities
            )
            session.add(approval)
            session.commit()
            session.refresh(approval)
            return approval.id

    def approve_request(self, approval_id: int) -> Optional[Dict[str, Any]]:
        """
        Approve a pending request.

        Args:
            approval_id: ID of approval request

        Returns:
            Request details if found, None otherwise
        """
        with get_session() as session:
            approval = session.query(PendingApproval).filter_by(id=approval_id).first()
            if not approval:
                return None

            approval.status = "approved"
            approval.resolved_at = datetime.utcnow()
            session.commit()

            return {
                "id": approval.id,
                "requester_id": approval.requester_id,
                "request_message": approval.request_message,
                "intent": approval.intent,
                "entities": approval.entities
            }

    def reject_request(self, approval_id: int) -> bool:
        """
        Reject a pending request.

        Args:
            approval_id: ID of approval request

        Returns:
            True if successful
        """
        with get_session() as session:
            approval = session.query(PendingApproval).filter_by(id=approval_id).first()
            if not approval:
                return False

            approval.status = "rejected"
            approval.resolved_at = datetime.utcnow()
            session.commit()
            return True

    def get_user_by_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by Telegram ID."""
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            return user.to_dict() if user else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users who have interacted with Jeeves."""
        with get_session() as session:
            users = session.query(User).order_by(User.last_seen.desc()).all()
            return [user.to_dict() for user in users]
