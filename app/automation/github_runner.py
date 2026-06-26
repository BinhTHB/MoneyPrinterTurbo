"""
GitHub Actions automation runner for YouTube video generation.

Orchestrates multi-channel video creation and upload.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from app.automation.channel_config import (
    ChannelConfig,
    load_channels_config,
    parse_count_overrides,
    resolve_channel_count,
)
from app.automation.topic_history import append_history, load_history
from app.automation.topic_planner import generate_topics
from app.automation.youtube_credentials import (
    load_youtube_client_config,
    load_youtube_token,
)
from app.models.schema import VideoParams
from app.services import task as tm
from app.services.youtube_upload import YouTubeUploadService


def run_automation(
    channels_file: str,
    history_dir: str,
    count_overrides: Optional[str] = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """
    Run the YouTube automation pipeline for all configured channels.

    Args:
        channels_file: Path to channels config JSON.
        history_dir: Directory to store topic history files.
        count_overrides: Optional count overrides like "cat=2,tech=1".
        dry_run: If True, skip video generation and upload.

    Returns:
        List of results per channel.
    """
    results: list[dict[str, Any]] = []

    channels = load_channels_config(channels_file)
    overrides = parse_count_overrides(count_overrides or "")

    os.makedirs(history_dir, exist_ok=True)

    for channel in channels:
        try:
            result = _run_channel(
                channel=channel,
                history_dir=history_dir,
                overrides=overrides,
                dry_run=dry_run,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Channel {channel.id} failed: {e}")
            results.append(
                {
                    "channel_id": channel.id,
                    "status": "error",
                    "error": str(e),
                    "videos": [],
                }
            )

    return results


def _run_channel(
    channel: ChannelConfig,
    history_dir: str,
    overrides: dict[str, str],
    dry_run: bool,
) -> dict[str, Any]:
    """
    Run automation for a single channel.
    """
    count = resolve_channel_count(channel, overrides)

    history_file = Path(history_dir) / f"{channel.id}.json"
    previous_topics = load_history(str(history_file))

    topics = generate_topics(channel, count=count, previous_topics=previous_topics)

    videos: list[dict[str, Any]] = []

    for topic in topics:
        try:
            video_result = _run_single_video(
                channel=channel,
                topic=topic,
                dry_run=dry_run,
            )
            videos.append(video_result)

            if video_result.get("status") == "success" and video_result.get("video_id"):
                record = {
                    "topic": topic,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "video_id": video_result.get("video_id"),
                    "url": video_result.get("url"),
                }
                append_history(str(history_file), record)
        except Exception as e:
            logger.error(f"Video generation for topic '{topic}' failed: {e}")
            videos.append(
                {
                    "topic": topic,
                    "status": "error",
                    "error": str(e),
                }
            )

    return {
        "channel_id": channel.id,
        "status": "success" if all(v.get("status") == "success" for v in videos) else "partial",
        "videos": videos,
    }


def _run_single_video(
    channel: ChannelConfig,
    topic: str,
    dry_run: bool,
) -> dict[str, Any]:
    """
    Generate a single video and upload to YouTube.
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would generate video for topic: {topic}")
        return {
            "topic": topic,
            "status": "dry_run",
        }

    client_config = load_youtube_client_config(channel.youtube_client_env)
    token_data = load_youtube_token(channel.youtube_token_env)

    with (
        tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as client_file,
        tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as token_file,
    ):
        try:
            json.dump(client_config, client_file)
            client_file.flush()
            json.dump(token_data, token_file)
            token_file.flush()

            params = VideoParams(
                video_subject=topic,
                video_language=channel.video_language,
                voice_name=channel.voice_name,
            )

            task_id = tm.utils.get_uuid()
            logger.info(f"Starting task {task_id} for topic: {topic}")

            task_result = tm.start(task_id=task_id, params=params, stop_at="video")

            if not task_result:
                return {
                    "topic": topic,
                    "status": "error",
                    "error": "video generation failed",
                }

            video_paths = task_result.get("videos", [])
            if not video_paths:
                return {
                    "topic": topic,
                    "status": "error",
                    "error": "no video paths in task result",
                }

            video_path = video_paths[0]
            video_title = task_result.get("video_title", topic)
            video_script = task_result.get("video_script", "")

            yt_config = {
                "enabled": True,
                "auto_upload": True,
                "privacy": channel.privacy,
                "category_id": channel.category_id,
                "made_for_kids": channel.made_for_kids,
                "shorts": channel.shorts,
                "token_file": token_file.name,
                "oauth_client": client_config,
            }

            yt_service = YouTubeUploadService(yt_config)
            if not yt_service.is_configured():
                return {
                    "topic": topic,
                    "status": "error",
                    "error": "YouTube upload not configured",
                }

            upload_result = yt_service.upload_video(
                video_path=video_path,
                title=video_title,
                description=video_script,
                tags=[],
            )

            if upload_result.get("success"):
                return {
                    "topic": topic,
                    "status": "success",
                    "video_id": upload_result.get("video_id"),
                    "url": upload_result.get("url"),
                }
            else:
                return {
                    "topic": topic,
                    "status": "error",
                    "error": upload_result.get("error", "upload failed"),
                }
        finally:
            try:
                os.unlink(client_file.name)
            except Exception:
                pass
            try:
                os.unlink(token_file.name)
            except Exception:
                pass
