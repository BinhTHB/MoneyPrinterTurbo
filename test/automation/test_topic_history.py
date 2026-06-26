import json
from pathlib import Path

from app.automation.topic_history import (
    load_history,
    append_history,
    normalize_topic,
    is_duplicate,
)


def test_normalize_topic_lowercases_and_strips_punctuation():
    assert normalize_topic("  A Kitten Discovers a Mirror! ") == "kitten discovers a mirror"


def test_normalize_topic_collapses_whitespace():
    assert normalize_topic("A  kitten   plays") == "kitten plays"


def test_is_duplicate_exact_match():
    assert is_duplicate("A kitten plays", ["a kitten plays"])
    assert is_duplicate("A Kitten Plays!", ["a kitten plays"])
    assert not is_duplicate("A kitten sleeps", ["a kitten plays"])


def test_load_history_returns_empty_list_if_no_file(tmp_path: Path):
    history = load_history(str(tmp_path / "nonexistent.json"))
    assert history == []


def test_load_history_reads_existing_topics(tmp_path: Path):
    file_path = tmp_path / "history.json"
    file_path.write_text(
        json.dumps(
            {
                "channel_id": "cat_shorts",
                "topics": [
                    {"topic": "Kitten chases sunlight", "created_at": "2026-06-26T12:00:00Z"},
                    {"topic": "Cat discovers a hat", "created_at": "2026-06-26T12:05:00Z"},
                ],
            }
        ),
        encoding="utf-8",
    )
    history = load_history(str(file_path))
    assert history == ["Kitten chases sunlight", "Cat discovers a hat"]


def test_append_history_creates_parent_dirs(tmp_path: Path):
    file_path = tmp_path / "subdir" / "history.json"
    record = {"topic": "New topic", "created_at": "now", "video_id": "abc123"}
    append_history(str(file_path), record)
    assert file_path.exists()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert len(data["topics"]) == 1
    assert data["topics"][0]["topic"] == "New topic"


def test_append_history_appends_to_existing_file(tmp_path: Path):
    file_path = tmp_path / "history.json"
    file_path.write_text(
        json.dumps({"channel_id": "cat_shorts", "topics": [{"topic": "Old"}], "video_id": "xyz"}),
        encoding="utf-8",
    )
    append_history(str(file_path), {"topic": "New", "created_at": "now"})
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert len(data["topics"]) == 2
    assert data["topics"][-1]["topic"] == "New"


def test_duplicate_vs_history_uses_normalized_matching(tmp_path: Path):
    file_path = tmp_path / "history.json"
    file_path.write_text(
        json.dumps(
            {
                "channel_id": "cat_shorts",
                "topics": [{"topic": "A Kitten Discovers a Mirror!"}],
            }
        ),
        encoding="utf-8",
    )
    history = load_history(str(file_path))
    assert is_duplicate("a kitten discovers a mirror", history)
    assert is_duplicate("Kitten Discovers a Mirror!", history)
    assert not is_duplicate("A kitten plays with yarn", history)
