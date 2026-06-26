"""
YouTube credentials loader for automation.

Loads OAuth client config and token from environment variables or files.
"""

import json
import os
from typing import Any


def load_youtube_client_config(env_var: str) -> dict[str, Any]:
    """
    Load Google OAuth client config from an environment variable.

    Args:
        env_var: Name of the environment variable containing JSON.

    Returns:
        OAuth client config dict.

    Raises:
        ValueError: If environment variable is missing or contains invalid JSON.
    """
    val = os.environ.get(env_var)
    if not val:
        raise ValueError(f"missing env var {env_var!r} for YouTube client config")

    try:
        return json.loads(val)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"invalid JSON in env var {env_var!r} for YouTube client config: {e}"
        ) from e


def load_youtube_token(env_var: str) -> dict[str, Any]:
    """
    Load YouTube user/oauth token JSON from an environment variable.

    Args:
        env_var: Name of the environment variable containing JSON.

    Returns:
        Token data dict.

    Raises:
        ValueError: If environment variable is missing or contains invalid JSON.
    """
    val = os.environ.get(env_var)
    if not val:
        raise ValueError(f"missing env var {env_var!r} for YouTube token")

    try:
        return json.loads(val)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in env var {env_var!r} for YouTube token: {e}") from e
