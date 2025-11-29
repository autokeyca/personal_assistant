"""Behavior configuration service for runtime system modification."""

import logging
import json
from typing import Optional, Dict, Any, List
from assistant.db import get_session
from assistant.db.models import BehaviorConfig

logger = logging.getLogger(__name__)


class BehaviorConfigService:
    """Service for managing runtime behavior configuration."""

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value (parsed from stored type)
        """
        with get_session() as session:
            config = session.query(BehaviorConfig).filter_by(key=key).first()
            if not config:
                return default

            # Parse based on value_type
            return self._parse_value(config.value, config.value_type)

    def set(self, key: str, value: Any, description: str = None,
            category: str = None, updated_by: str = None) -> bool:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to set
            description: Human-readable description
            category: Configuration category
            updated_by: Who/what updated it

        Returns:
            True if successful
        """
        try:
            with get_session() as session:
                config = session.query(BehaviorConfig).filter_by(key=key).first()

                # Determine value type
                value_type = self._get_value_type(value)
                value_str = self._serialize_value(value, value_type)

                if config:
                    config.value = value_str
                    config.value_type = value_type
                    if description:
                        config.description = description
                    if category:
                        config.category = category
                    if updated_by:
                        config.updated_by = updated_by
                else:
                    config = BehaviorConfig(
                        key=key,
                        value=value_str,
                        value_type=value_type,
                        description=description,
                        category=category,
                        updated_by=updated_by
                    )
                    session.add(config)

                session.commit()
                logger.info(f"Set behavior config: {key} = {value}")
                return True
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        try:
            with get_session() as session:
                config = session.query(BehaviorConfig).filter_by(key=key).first()
                if config:
                    session.delete(config)
                    session.commit()
                    logger.info(f"Deleted behavior config: {key}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting config {key}: {e}")
            return False

    def list_all(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all configuration values.

        Args:
            category: Optional category filter

        Returns:
            List of configuration dictionaries
        """
        with get_session() as session:
            query = session.query(BehaviorConfig)
            if category:
                query = query.filter_by(category=category)

            configs = query.all()
            return [c.to_dict() for c in configs]

    def list_categories(self) -> List[str]:
        """Get all unique categories."""
        with get_session() as session:
            categories = session.query(BehaviorConfig.category).distinct().all()
            return [c[0] for c in categories if c[0]]

    def _get_value_type(self, value: Any) -> str:
        """Determine value type from Python type."""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (dict, list)):
            return "json"
        else:
            return "string"

    def _serialize_value(self, value: Any, value_type: str) -> str:
        """Serialize value to string for storage."""
        if value_type == "json":
            return json.dumps(value)
        elif value_type == "bool":
            return "true" if value else "false"
        else:
            return str(value)

    def _parse_value(self, value_str: str, value_type: str) -> Any:
        """Parse stored string value to appropriate Python type."""
        if value_type == "bool":
            return value_str.lower() in ("true", "1", "yes", "on")
        elif value_type == "int":
            return int(value_str)
        elif value_type == "float":
            return float(value_str)
        elif value_type == "json":
            return json.loads(value_str)
        else:
            return value_str
