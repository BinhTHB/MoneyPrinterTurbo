"""
Topic Planner for YouTube automation.

Generates fresh, unique video topics using LLM while avoiding history.
"""

import json
import time
from loguru import logger

from app.automation.channel_config import ChannelConfig
from app.automation.topic_history import is_duplicate
from app.services.llm import _generate_response, _strip_code_fence


def _parse_topics_from_response(response: str) -> list[str]:
    """
    Parse topics from LLM response with robust error handling.
    
    Args:
        response: Raw LLM response string
        
    Returns:
        List of topic strings, empty list if parsing fails
    """
    cleaned = _strip_code_fence(response)
    if not cleaned or not cleaned.strip():
        logger.warning("topic_planner: LLM returned empty response")
        return []
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"topic_planner: failed to parse LLM response as JSON: {e}")
        logger.debug(f"topic_planner: raw response was: {response[:500]}")
        return []
    
    topics = data.get("topics", [])
    if not isinstance(topics, list):
        logger.warning(f"topic_planner: 'topics' is not a list, got {type(topics)}")
        return []
    
    # Convert all to strings and filter empty
    result = []
    for topic in topics:
        topic_str = str(topic).strip()
        if topic_str:
            result.append(topic_str)
    
    return result


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

    # Retry logic for topic generation
    max_attempts = 3
    for attempt in range(max_attempts):
        response = _generate_response(prompt)
        if not response:
            logger.warning(f"topic_planner: LLM returned empty response (attempt {attempt + 1}/{max_attempts})")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # 1s, 2s
                continue
            raise ValueError("LLM returned empty response for topic generation")

        topics = _parse_topics_from_response(response)
        
        if not topics:
            logger.warning(f"topic_planner: no valid topics parsed (attempt {attempt + 1}/{max_attempts})")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
                continue
            raise ValueError("Failed to parse valid topics from LLM after retries")

        # Filter out duplicates
        unique_topics: list[str] = []
        for topic in topics:
            # Check duplicate against history and current batch
            if is_duplicate(topic, previous_topics) or is_duplicate(topic, unique_topics):
                logger.debug(f"skipped duplicate topic: {topic}")
                continue
            unique_topics.append(topic)

        if len(unique_topics) >= count:
            # Return exactly the requested count
            selected = unique_topics[:count]
            logger.success(f"generated unique topics: {selected}")
            return selected
        else:
            logger.warning(
                f"Generated {len(unique_topics)} unique topics, but {count} was requested. "
                f"Raw topics: {topics} (attempt {attempt + 1}/{max_attempts})"
            )
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
                continue
            raise ValueError(
                f"Not enough fresh topics generated (got {len(unique_topics)}, requested {count})"
            )

    # Should not reach here, but just in case
    raise ValueError("Topic generation failed after all retries")