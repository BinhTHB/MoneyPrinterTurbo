"""
Topic history management for YouTube automation.

Track topics already used per channel to reduce duplicates.
"""

import json
import re
from pathlib import Path
from typing import Any


def normalize_topic(topic: str) -> str:
    """
    Normalize a topic string for deduplication.

    - Lowercase
    - Strip leading/trailing whitespace
    - Remove punctuation
    - Collapse multiple spaces into one

    Args:
        topic: Raw topic string.

    Returns:
        Normalized topic string.
    """
    topic = topic.lower().strip()
    topic = re.sub(r"[^\w\s]", "", topic)
    topic = re.sub(r"\s+", " ", topic).strip()
    topic = re.sub(r"^(a|an|the)\s+", "", topic)
    return topic


def is_duplicate(topic: str, previous_topics: list[str]) -> bool:
    """
    Check if a topic is a duplicate of any in the previous topics list.

    Uses normalized matching for comparison.

    Args:
        topic: Topic to check.
        previous_topics: List of previous topics (raw strings).

    Returns:
        True if topic matches any previous topic (normalized).
    """
    normalized = normalize_topic(topic)
    for prev in previous_topics:
        if normalize_topic(prev) == normalized:
            return True
    return False


def load_history(path: str) -> list[str]:
    """
    Load topic history from a JSON file.

    Args:
        path: Path to the history JSON file.

    Returns:
        List of topic strings (raw, as stored). Empty list if file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)

    topics = data.get("topics", [])
    return [item.get("topic", "") for item in topics if item.get("topic")]


def append_history(path: str, record: dict[str, Any]) -> None:
    """
    Append a record to the topic history file.

    Creates the file and parent directories if they do not exist.

    Args:
        path: Path to the history JSON file.
        record: Dict with keys like 'topic', 'created_at', 'task_id', 'video_id', 'url'.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
    else:
        data = {"channel_id": "", "topics": []}

    topics = data.get("topics", [])
    topics.append(record)
    data["topics"] = topics

    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
