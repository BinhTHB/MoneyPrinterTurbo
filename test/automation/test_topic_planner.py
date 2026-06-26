import json
from unittest.mock import patch

from app.automation.channel_config import ChannelConfig
from app.automation.topic_planner import generate_topics


def test_generate_topics_extracts_json_and_dedupes():
    channel = ChannelConfig(
        id="cat_shorts",
        topic_prompt="Generate cute cat topics for YouTube Shorts",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )
    previous = ["Kitten chases sunlight", "Cat discovers a hat"]
    llm_response = json.dumps(
        {
            "topics": [
                "Kitten chases sunlight",
                "A kitten finds a tiny hat",
                "Cat plays with yarn ball",
            ]
        }
    )

    with patch("app.automation.topic_planner._generate_response", return_value=llm_response):
        topics = generate_topics(channel, count=2, previous_topics=previous)

    assert "Kitten chases sunlight" not in topics
    assert "A kitten finds a tiny hat" in topics or "kitten finds a tiny hat" in topics
    assert "Cat plays with yarn ball" in topics


def test_generate_topics_raises_if_not_enough_fresh():
    channel = ChannelConfig(
        id="cat_shorts",
        topic_prompt="Generate cute cat topics",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )
    previous = ["Kitten chases sunlight"]
    llm_response = json.dumps({"topics": ["Kitten chases sunlight"]})

    with patch("app.automation.topic_planner._generate_response", return_value=llm_response):
        try:
            generate_topics(channel, count=1, previous_topics=previous)
            raise AssertionError("should have raised")
        except ValueError as exc:
            assert "fresh" in str(exc).lower()


def test_generate_topics_handles_code_fence():
    channel = ChannelConfig(
        id="cat_shorts",
        topic_prompt="Generate cat topics",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )
    llm_response = '```json\n{"topics": ["Kitten plays", "Cat sleeps"]}\n```'

    with patch("app.automation.topic_planner._generate_response", return_value=llm_response):
        topics = generate_topics(channel, count=2, previous_topics=[])

    assert len(topics) == 2
    assert "Kitten plays" in topics
    assert "Cat sleeps" in topics
