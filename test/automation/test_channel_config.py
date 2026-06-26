import json
import random
from pathlib import Path

import pytest

from app.automation.channel_config import (
    ChannelConfig,
    load_channels_config,
    parse_count_overrides,
    resolve_channel_count,
)


def test_load_channels_config_reads_enabled_channels(tmp_path: Path):
    config_path = tmp_path / "channels.json"
    config_path.write_text(
        json.dumps(
            {
                "channels": [
                    {
                        "id": "cat_shorts",
                        "name": "Cat Shorts",
                        "topic_prompt": "Generate cat topics",
                        "script_prompt": "Write concise scripts",
                        "youtube_client_env": "YOUTUBE_CLIENT_JSON_CAT",
                        "youtube_token_env": "YOUTUBE_TOKEN_JSON_CAT",
                    },
                    {
                        "id": "disabled_channel",
                        "enabled": False,
                        "topic_prompt": "Ignore me",
                        "youtube_client_env": "YOUTUBE_CLIENT_JSON_DISABLED",
                        "youtube_token_env": "YOUTUBE_TOKEN_JSON_DISABLED",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    channels = load_channels_config(str(config_path))

    assert [channel.id for channel in channels] == ["cat_shorts"]
    assert channels[0].name == "Cat Shorts"
    assert channels[0].topic_prompt == "Generate cat topics"
    assert channels[0].count == 1
    assert channels[0].video_language == "en"
    assert channels[0].privacy == "private"
    assert channels[0].shorts is True



def test_load_channels_config_rejects_duplicate_ids(tmp_path: Path):
    config_path = tmp_path / "channels.json"
    config_path.write_text(
        json.dumps(
            {
                "channels": [
                    {
                        "id": "same",
                        "topic_prompt": "A",
                        "youtube_client_env": "CLIENT_A",
                        "youtube_token_env": "TOKEN_A",
                    },
                    {
                        "id": "same",
                        "topic_prompt": "B",
                        "youtube_client_env": "CLIENT_B",
                        "youtube_token_env": "TOKEN_B",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate channel id"):
        load_channels_config(str(config_path))


def test_parse_count_overrides_supports_exact_range_and_all():
    overrides = parse_count_overrides("cat=2,tech=1-3, all = 1")

    assert overrides == {"cat": "2", "tech": "1-3", "all": "1"}


def test_resolve_channel_count_prefers_channel_override():
    channel = ChannelConfig(
        id="cat",
        count=1,
        topic_prompt="Generate cat topics",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )
    rng = random.Random(7)

    assert resolve_channel_count(channel, {"all": "1", "cat": "2-2"}, rng=rng) == 2


def test_resolve_channel_count_uses_all_override_then_channel_default():
    channel = ChannelConfig(
        id="cat",
        count=4,
        topic_prompt="Generate cat topics",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )

    assert resolve_channel_count(channel, {"all": "3"}) == 3
    assert resolve_channel_count(channel, {}) == 4


def test_invalid_count_override_raises_clear_error():
    channel = ChannelConfig(
        id="cat",
        topic_prompt="Generate cat topics",
        youtube_client_env="YOUTUBE_CLIENT_JSON_CAT",
        youtube_token_env="YOUTUBE_TOKEN_JSON_CAT",
    )

    with pytest.raises(ValueError, match="Invalid count override"):
        resolve_channel_count(channel, {"cat": "3-1"})

    with pytest.raises(ValueError, match="Invalid count override"):
        parse_count_overrides("cat=0")
