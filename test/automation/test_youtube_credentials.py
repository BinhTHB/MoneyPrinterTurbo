import json
import os
from unittest.mock import patch

import pytest

from app.automation.youtube_credentials import (
    load_youtube_client_config,
    load_youtube_token,
)


def test_load_youtube_client_config_from_env():
    env_value = json.dumps(
        {
            "installed": {
                "client_id": "abc.apps.googleusercontent.com",
                "client_secret": "SECRET",
                "project_id": "my-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
    )

    with patch.dict(os.environ, {"YOUTUBE_CLIENT_JSON_CAT": env_value}):
        config = load_youtube_client_config("YOUTUBE_CLIENT_JSON_CAT")
        assert config["installed"]["client_id"] == "abc.apps.googleusercontent.com"
        assert config["installed"]["client_secret"] == "SECRET"


def test_load_youtube_client_config_missing_env_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="missing env var"):
            load_youtube_client_config("YOUTUBE_CLIENT_JSON_MISSING")


def test_load_youtube_token_from_env():
    env_value = json.dumps(
        {
            "token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "abc.apps.googleusercontent.com",
            "client_secret": "SECRET",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        }
    )

    with patch.dict(os.environ, {"YOUTUBE_TOKEN_JSON_CAT": env_value}):
        token = load_youtube_token("YOUTUBE_TOKEN_JSON_CAT")
        assert token["refresh_token"] == "refresh-token-456"


def test_load_youtube_token_missing_env_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="missing env var"):
            load_youtube_token("YOUTUBE_TOKEN_JSON_MISSING")
