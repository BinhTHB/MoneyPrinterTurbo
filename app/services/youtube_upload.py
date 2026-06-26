"""
YouTube Upload Service for direct upload to YouTube via OAuth 2.0.

Supports:
- OAuth 2.0 authentication with automatic token refresh
- Direct upload via YouTube Data API v3
- YouTube Shorts metadata (auto-add #Shorts)
"""

import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def append_shorts_metadata(
    title: str,
    description: str,
    tags: list,
) -> tuple[str, str, list]:
    """
    Append #Shorts to title, description, and tags if not already present.
    Returns updated (title, description, tags).
    """
    if "#Shorts" not in title:
        title = f"{title} #Shorts"
    if "#Shorts" not in description:
        description = f"{description}\n\n#Shorts"
    if "Shorts" not in tags:
        tags = list(tags) + ["Shorts"]
    return title, description, tags


class YouTubeUploadService:
    """
    YouTube upload service using OAuth 2.0 and YouTube Data API v3.
    """

    def __init__(self, app_config: dict):
        self.enabled = app_config.get("enabled", app_config.get("youtube_upload_enabled", False))
        self.auto_upload = app_config.get("auto_upload", app_config.get("youtube_upload_auto", False))
        self.privacy = app_config.get("privacy", app_config.get("youtube_upload_privacy", "private"))
        self.category_id = app_config.get("category_id", app_config.get("youtube_upload_category_id", "22"))
        self.made_for_kids = app_config.get(
            "made_for_kids",
            app_config.get("youtube_upload_made_for_kids", False),
        )
        self.shorts = app_config.get("shorts", app_config.get("youtube_upload_shorts", False))
        self.token_file = app_config.get(
            "token_file",
            app_config.get("youtube_upload_token_file", "youtube_token.json"),
        )
        self._oauth_client_config = app_config.get("oauth_client", app_config.get("youtube_oauth_client"))

        # Flat fields for OAuth client (alternative to nested config)
        self._oauth_client_id = app_config.get("client_id", app_config.get("youtube_oauth_client_id", ""))
        self._oauth_client_secret = app_config.get("client_secret", app_config.get("youtube_oauth_client_secret", ""))
        self._oauth_project_id = app_config.get("project_id", app_config.get("youtube_oauth_project_id", ""))

    def is_configured(self) -> bool:
        """Check if YouTube upload is properly configured."""
        if not self.enabled:
            return False
        # Need either nested oauth_client config or flat fields
        if self._oauth_client_config:
            return True
        if self._oauth_client_id and self._oauth_client_secret:
            return True
        return False

    def get_oauth_client_config(self) -> dict:
        """
        Build OAuth client config from either nested dict or flat fields.
        Returns config in format expected by InstalledAppFlow.
        """
        if self._oauth_client_config:
            return self._oauth_client_config

        return {
            "installed": {
                "client_id": self._oauth_client_id,
                "client_secret": self._oauth_client_secret,
                "project_id": self._oauth_project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }

    def authenticate(self):
        """
        Authenticate with YouTube OAuth 2.0.
        Returns Credentials object.
        """
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing YouTube OAuth token...")
                creds.refresh(Request())
            else:
                logger.info("Starting YouTube OAuth flow...")
                client_config = self.get_oauth_client_config()
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
            logger.info(f"YouTube OAuth token saved to {self.token_file}")

        return creds

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
    ) -> dict:
        """
        Upload video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags

        Returns:
            dict with success, video_id, url on success
            dict with success=False, error on failure
        """
        if not self.is_configured():
            logger.warning("YouTube upload not configured. Skipping.")
            return {"success": False, "error": "YouTube upload not configured"}

        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": f"Video file not found: {video_path}"}

        try:
            creds = self.authenticate()
            youtube = build("youtube", "v3", credentials=creds)

            # Prepare metadata
            tags = tags or []
            if self.shorts:
                title, description, tags = append_shorts_metadata(title, description, tags)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags,
                    "categoryId": self.category_id,
                },
                "status": {
                    "privacyStatus": self.privacy,
                    "selfDeclaredMadeForKids": self.made_for_kids,
                },
            }

            logger.info(f"Uploading video to YouTube: {title}")

            media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")

            video_id = response.get("id")
            logger.success(f"YouTube upload complete! Video ID: {video_id}")

            return {
                "success": True,
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
            }

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance (initialized with actual config in task.py)
youtube_upload_service: Optional[YouTubeUploadService] = None


def init_youtube_upload_service(app_config: dict):
    """Initialize the singleton YouTube upload service."""
    global youtube_upload_service
    youtube_upload_service = YouTubeUploadService(app_config)


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[list] = None,
) -> dict:
    """Upload video using the singleton service."""
    if youtube_upload_service is None:
        logger.warning("YouTube upload service not initialized")
        return {"success": False, "error": "Service not initialized"}
    return youtube_upload_service.upload_video(video_path, title, description, tags)
