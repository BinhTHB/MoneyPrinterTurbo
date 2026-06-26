import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.youtube_upload import YouTubeUploadService, append_shorts_metadata


def test_append_shorts_metadata_adds_shorts_once():
    title, description, tags = append_shorts_metadata(
        "My Video",
        "Description",
        ["video"],
    )

    assert title == "My Video #Shorts"
    assert description == "Description\n\n#Shorts"
    assert tags == ["video", "Shorts"]

    title, description, tags = append_shorts_metadata(
        title,
        description,
        tags,
    )

    assert title == "My Video #Shorts"
    assert description == "Description\n\n#Shorts"
    assert tags == ["video", "Shorts"]


def test_service_is_configured_requires_enabled_and_oauth_client():
    service = YouTubeUploadService({})
    assert service.is_configured() is False

    service = YouTubeUploadService({
        "youtube_upload_enabled": True,
        "youtube_oauth_client": {"installed": {"client_id": "id"}},
    })
    assert service.is_configured() is True


def test_get_oauth_client_config_builds_installed_config_from_flat_fields():
    service = YouTubeUploadService({
        "youtube_upload_enabled": True,
        "youtube_oauth_client_id": "client-id",
        "youtube_oauth_client_secret": "client-secret",
        "youtube_oauth_project_id": "project-id",
    })

    assert service.get_oauth_client_config() == {
        "installed": {
            "client_id": "client-id",
            "client_secret": "client-secret",
            "project_id": "project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }


def test_upload_video_inserts_metadata_and_returns_video_url(tmp_path):
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"fake video")

    service = YouTubeUploadService({
        "youtube_upload_enabled": True,
        "youtube_oauth_client": {"installed": {"client_id": "id"}},
        "youtube_upload_privacy": "unlisted",
        "youtube_upload_category_id": "22",
        "youtube_upload_made_for_kids": False,
        "youtube_upload_shorts": True,
    })

    credentials = object()
    request = Mock()
    request.next_chunk.side_effect = [
        (SimpleNamespace(progress=lambda: 0.5), None),
        (None, {"id": "abc123"}),
    ]
    youtube = Mock()
    youtube.videos.return_value.insert.return_value = request

    with patch.object(service, "authenticate", return_value=credentials), \
         patch("app.services.youtube_upload.build", return_value=youtube), \
         patch("app.services.youtube_upload.MediaFileUpload") as media_upload:
        result = service.upload_video(
            str(video_file),
            title="Test Video",
            description="Description",
            tags=["tag1"],
        )

    assert result == {
        "success": True,
        "video_id": "abc123",
        "url": "https://youtu.be/abc123",
    }
    media_upload.assert_called_once_with(str(video_file), chunksize=1024 * 1024, resumable=True)
    _, kwargs = youtube.videos.return_value.insert.call_args
    assert kwargs["part"] == "snippet,status"
    assert kwargs["body"] == {
        "snippet": {
            "title": "Test Video #Shorts",
            "description": "Description\n\n#Shorts",
            "tags": ["tag1", "Shorts"],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "unlisted",
            "selfDeclaredMadeForKids": False,
        },
    }


def test_authenticate_refreshes_existing_token(tmp_path):
    token_file = tmp_path / "youtube_token.json"
    token_file.write_text(json.dumps({"token": "old"}), encoding="utf-8")
    service = YouTubeUploadService({
        "youtube_upload_enabled": True,
        "youtube_upload_token_file": str(token_file),
        "youtube_oauth_client": {"installed": {"client_id": "id"}},
    })

    creds = Mock(valid=False, expired=True, refresh_token="refresh-token")
    creds.to_json.return_value = '{"token":"new"}'

    with patch("app.services.youtube_upload.Credentials.from_authorized_user_file", return_value=creds), \
         patch("app.services.youtube_upload.Request") as request_cls:
        assert service.authenticate() is creds

    creds.refresh.assert_called_once_with(request_cls.return_value)
    assert token_file.read_text(encoding="utf-8") == '{"token":"new"}'
