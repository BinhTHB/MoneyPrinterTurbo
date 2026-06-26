import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.automation.channel_config import ChannelConfig
from app.automation.github_runner import run_automation


@pytest.fixture
def mock_dependencies():
    with (
        patch("app.automation.github_runner.load_channels_config") as mock_load_config,
        patch("app.automation.github_runner.load_history") as mock_load_history,
        patch("app.automation.github_runner.generate_topics") as mock_generate_topics,
        patch("app.automation.github_runner.load_youtube_client_config") as mock_load_client,
        patch("app.automation.github_runner.load_youtube_token") as mock_load_token,
        patch("app.automation.github_runner.YouTubeUploadService") as mock_upload_service,
        patch("app.automation.github_runner.tm.start") as mock_start_task,
        patch("app.automation.github_runner.append_history") as mock_append_history,
    ):
        yield {
            "load_config": mock_load_config,
            "load_history": mock_load_history,
            "generate_topics": mock_generate_topics,
            "load_client": mock_load_client,
            "load_token": mock_load_token,
            "upload_service": mock_upload_service,
            "start_task": mock_start_task,
            "append_history": mock_append_history,
        }


def test_run_automation_orchestrates_correctly(mock_dependencies):
    channel = ChannelConfig(
        id="cat_shorts",
        name="Cat Channel",
        topic_prompt="cat topic",
        youtube_client_env="CLIENT_ENV",
        youtube_token_env="TOKEN_ENV",
        privacy="private",
    )
    mock_dependencies["load_config"].return_value = [channel]
    mock_dependencies["load_history"].return_value = ["old topic"]
    mock_dependencies["generate_topics"].return_value = ["new topic"]

    mock_dependencies["load_client"].return_value = {"client": "data"}
    mock_dependencies["load_token"].return_value = {"token": "data"}

    mock_svc = MagicMock()
    mock_svc.is_configured.return_value = True
    mock_svc.upload_video.return_value = {"success": True, "video_id": "vid123", "url": "url123"}
    mock_dependencies["upload_service"].return_value = mock_svc

    mock_dependencies["start_task"].return_value = {
        "videos": ["/path/to/video.mp4"],
        "video_script": "cat story",
        "video_title": "Cat Title",
    }

    with tempfile.TemporaryDirectory() as tmp:
        history_dir = Path(tmp) / "history"
        results = run_automation(
            channels_file="channels.json",
            history_dir=str(history_dir),
            count_overrides="cat_shorts=1",
            dry_run=False,
        )

        assert len(results) == 1
        res = results[0]
        assert res["channel_id"] == "cat_shorts"
        assert len(res["videos"]) == 1
        assert res["videos"][0]["topic"] == "new topic"
        assert res["videos"][0]["status"] == "success"
        assert res["videos"][0]["video_id"] == "vid123"

        # Verify calls
        mock_dependencies["generate_topics"].assert_called_once_with(
            channel, count=1, previous_topics=["old topic"]
        )
        mock_dependencies["start_task"].assert_called_once()
        mock_dependencies["append_history"].assert_called_once()
