"""Configuration management."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict

_config: Dict[str, Any] = {}
_base_path: Path = None


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    global _config, _base_path

    if config_path is None:
        # Try to find config in common locations
        possible_paths = [
            Path("config/config.yaml"),
            Path("config.yaml"),
            Path.home() / ".config" / "personal_assistant" / "config.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break
        else:
            raise FileNotFoundError(
                "No config.yaml found. Copy config/config.example.yaml to config/config.yaml "
                "and fill in your values."
            )

    config_path = Path(config_path)
    _base_path = config_path.parent.parent  # Project root

    with open(config_path) as f:
        _config = yaml.safe_load(f)

    # Resolve relative paths
    _resolve_paths()

    return _config


def _resolve_paths():
    """Resolve relative paths in config to absolute paths."""
    global _config

    if "google" in _config:
        for key in ["credentials_file", "token_file"]:
            if key in _config["google"]:
                path = Path(_config["google"][key])
                if not path.is_absolute():
                    _config["google"][key] = str(_base_path / path)

    if "database" in _config:
        path = Path(_config["database"]["path"])
        if not path.is_absolute():
            _config["database"]["path"] = str(_base_path / path)

    if "logging" in _config:
        path = Path(_config["logging"]["file"])
        if not path.is_absolute():
            _config["logging"]["file"] = str(_base_path / path)


def get_config() -> Dict[str, Any]:
    """Get the loaded configuration."""
    if not _config:
        load_config()
    return _config


def get(key: str, default: Any = None) -> Any:
    """Get a config value by dot-notation key (e.g., 'telegram.bot_token')."""
    if not _config:
        load_config()

    keys = key.split(".")
    value = _config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value
