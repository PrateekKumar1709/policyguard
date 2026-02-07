"""Shared utilities for PolicyGuard MCP server."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}


def get_shared_config() -> dict[str, Any]:
    """Get shared configuration that tools can access.

    Returns:
        Shared configuration dictionary
    """
    config = load_config("manifest.yaml")
    tools_config = config.get("tools", {})
    if isinstance(tools_config, dict):
        return tools_config
    return {}


def get_tool_config(tool_name: str) -> dict[str, Any]:
    """Get configuration for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool-specific configuration
    """
    shared_config = get_shared_config()
    tool_config = shared_config.get(tool_name, {})
    if isinstance(tool_config, dict):
        return tool_config
    return {}


def get_env_var(key: str, default: str = "") -> str:
    """Get environment variable with fallback.

    Args:
        key: Environment variable key
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    return os.environ.get(key, default)


def generate_id(prefix: str = "grd") -> str:
    """Generate a unique ID with a prefix.

    Args:
        prefix: ID prefix (e.g., 'aud' for audit, 'pol' for policy)

    Returns:
        Unique ID string
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# JSON File Storage (Simple persistence for hackathon demo)
# ============================================================================

# Allow DATA_DIR to be configured via environment variable
_data_dir_str = os.environ.get("POLICYGUARD_DATA_DIR", "data")
DATA_DIR = Path(_data_dir_str)


def set_data_dir(path: str) -> None:
    """Set the data directory path (used for testing)."""
    global DATA_DIR
    DATA_DIR = Path(path)


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)


def load_json_file(filename: str, default: Any = None) -> Any:
    """Load data from a JSON file.

    Args:
        filename: Name of the file in the data directory
        default: Default value if file doesn't exist

    Returns:
        Loaded data or default
    """
    ensure_data_dir()
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        return default if default is not None else {}
    
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default if default is not None else {}


def save_json_file(filename: str, data: Any) -> bool:
    """Save data to a JSON file.

    Args:
        filename: Name of the file in the data directory
        data: Data to save

    Returns:
        True if successful, False otherwise
    """
    ensure_data_dir()
    filepath = DATA_DIR / filename
    
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False


def append_to_json_list(filename: str, item: Any, max_items: int = 1000) -> bool:
    """Append an item to a JSON list file, maintaining max size.

    Args:
        filename: Name of the file in the data directory
        item: Item to append
        max_items: Maximum number of items to keep

    Returns:
        True if successful, False otherwise
    """
    data = load_json_file(filename, default=[])
    if not isinstance(data, list):
        data = []
    
    data.append(item)
    
    # Keep only the last max_items
    if len(data) > max_items:
        data = data[-max_items:]
    
    return save_json_file(filename, data)
