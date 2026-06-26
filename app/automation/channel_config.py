"""
Channel configuration models for YouTube automation.

Parse and validate multi-channel automation config from JSON/TOML files.
"""

import json
import random
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ChannelConfig(BaseModel):
    """Configuration for a single YouTube automation channel."""

    id: str
    name: str = ""
    enabled: bool = True
    count: int = 1
    count_range: Optional[str] = None
    topic_prompt: str
    script_prompt: str = ""
    video_language: str = "en"
    voice_name: str = ""
    video_source: str = "pexels"
    video_aspect: str = "9:16"
    privacy: str = "private"
    category_id: str = "22"
    made_for_kids: bool = False
    shorts: bool = True
    youtube_client_env: str
    youtube_token_env: str
    history_file: str = ""


def load_channels_config(path: str) -> list[ChannelConfig]:
    """
    Load channel configurations from a JSON file.

    Args:
        path: Path to the channels config JSON file.

    Returns:
        List of enabled ChannelConfig objects.

    Raises:
        ValueError: If duplicate channel IDs are found.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Channels config file not found: {path}")

    content = config_path.read_text(encoding="utf-8")
    data = json.loads(content)

    channels_data = data.get("channels", [])
    seen_ids: set[str] = set()
    channels: list[ChannelConfig] = []

    for item in channels_data:
        channel = ChannelConfig(**item)
        if channel.id in seen_ids:
            raise ValueError(f"Duplicate channel id: {channel.id}")
        seen_ids.add(channel.id)
        if channel.enabled:
            channels.append(channel)

    return channels


def parse_count_overrides(raw: str) -> dict[str, str]:
    """
    Parse count overrides string into a dictionary.

    Args:
        raw: Comma-separated overrides, e.g. "cat=2,tech=1-3,all=1".

    Returns:
        Dictionary mapping channel id or 'all' to count specification.

    Raises:
        ValueError: If a count override is invalid (e.g., "0", negative, malformed).
    """
    if not raw or not raw.strip():
        return {}

    overrides: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid count override format: {part!r}")
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Empty channel id in count override: {part!r}")

        # Validate value: must be positive int or range
        if not re.fullmatch(r"[1-9]\d*|\d+-\d+", value):
            raise ValueError(f"Invalid count override value: {value!r} for channel {key!r}")

        # If range, validate min <= max
        if "-" in value:
            min_str, max_str = value.split("-", 1)
            min_val, max_val = int(min_str), int(max_str)
            if min_val > max_val:
                raise ValueError(f"Invalid count override range: {value!r} (min > max)")
            if min_val < 1:
                raise ValueError(f"Invalid count override range: {value!r} (min < 1)")

        overrides[key] = value

    return overrides


def resolve_channel_count(
    channel: ChannelConfig,
    overrides: dict[str, str],
    rng: random.Random | None = None,
) -> int:
    """
    Resolve the number of videos to generate for a channel.

    Priority:
    1. Channel-specific override (exact or range).
    2. 'all' override.
    3. Channel's default count.
    4. If channel has count_range, sample from range.

    Args:
        channel: ChannelConfig object.
        overrides: Dictionary of count overrides from parse_count_overrides.
        rng: Optional random.Random instance for deterministic testing.

    Returns:
        Number of videos to generate for this channel.

    Raises:
        ValueError: If count override is invalid.
    """
    rng = rng or random.Random()

    # Priority 1: Channel-specific override
    if channel.id in overrides:
        return _parse_count_value(overrides[channel.id], rng)

    # Priority 2: 'all' override
    if "all" in overrides:
        return _parse_count_value(overrides["all"], rng)

    # Priority 3: Channel default count (if no count_range)
    if channel.count_range is None:
        return channel.count

    # Priority 4: Sample from count_range
    return _parse_count_value(channel.count_range, rng)


def _parse_count_value(value: str, rng: random.Random) -> int:
    """
    Parse a count value, which can be an exact integer or a range.

    Args:
        value: Count specification like "2" or "1-3".
        rng: Random instance for range sampling.

    Returns:
        Exact count.
    """
    if "-" in value:
        min_str, max_str = value.split("-", 1)
        min_val, max_val = int(min_str), int(max_str)
        if min_val > max_val:
            raise ValueError(f"Invalid count override range: {value!r} (min > max)")
        return rng.randint(min_val, max_val)
    return int(value)
