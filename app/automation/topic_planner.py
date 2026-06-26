"""
Topic Planner for YouTube automation.

Generates fresh, unique video topics using LLM while avoiding history.
"""

import json
from loguru import logger

from app.automation.channel_config import ChannelConfig
from app.automation.topic_history import is_duplicate
from app.services.llm import _generate_response, _strip_code_fence


def generate_topics(
    channel: ChannelConfig, count: int, previous_topics: list[str]
) -> list[str]:
    """
    Generate unique video topics for a channel.

    Avoids duplicates by comparing against the previous topics.

    Args:
        channel: ChannelConfig object.
        count: Number of unique topics to generate.
        previous_topics: List of previously completed topics.

    Returns:
        List of generated unique topics.

    Raises:
        ValueError: If LLM fails to return valid JSON or enough unique topics.
    """
    if count < 1:
        return []

    history_bullets = ""
    if previous_topics:
        history_bullets = "\n".join(f"- {topic}" for topic in previous_topics)
    else:
        history_bullets = "(No previous topics. This is the first run.)"

    prompt = f"""
# Role: YouTube Topic Planner

## Goal:
Generate {count * 2} (extra for filtering) new distinct, visual video topics for channel: {channel.name}.
We need at least {count} completely unique topics after filtering.

## Channel Guidance / Prompt:
{channel.topic_prompt}

## Already Completed Topics (DO NOT REPEAT):
{history_bullets}

## Constrains:
1. return JSON format only: {{"topics": ["topic 1", "topic 2", ...]}}
2. do not repeat or paraphrase any of the already completed topics.
3. topics must be visual and feasible for stock footage search.
4. do not output any markdown code blocks, explanation or preamble except the JSON itself.
5. always write topics in English.
""".strip()

    logger.info(f"generating topics for channel {channel.id}: request_count={count}")
    response = _generate_response(prompt)
    if not response:
        raise ValueError("LLM returned empty response for topic generation")

    cleaned = _strip_code_fence(response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"failed to parse LLM topic response: {response}")
        raise ValueError(f"Invalid JSON from topic planner LLM: {e}") from e

    topics = data.get("topics", [])
    if not isinstance(topics, list):
        raise ValueError(f"Invalid response format: 'topics' must be a list, got {type(topics)}")

    # Filter out duplicates
    unique_topics: list[str] = []
    for topic in topics:
        topic_str = str(topic).strip()
        if not topic_str:
            continue
        # Check duplicate against history and current batch
        if is_duplicate(topic_str, previous_topics) or is_duplicate(topic_str, unique_topics):
            logger.debug(f"skipped duplicate topic: {topic_str}")
            continue
        unique_topics.append(topic_str)

    if len(unique_topics) < count:
        logger.error(
            f"Generated {len(unique_topics)} unique topics, but {count} was requested. "
            f"Raw: {topics}"
        )
        raise ValueError(
            f"Not enough fresh topics generated (got {len(unique_topics)}, requested {count})"
        )

    # Return exactly the requested count
    selected = unique_topics[:count]
    logger.success(f"generated unique topics: {selected}")
    return selected
