import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for YouTube upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def load_client_config(path: str) -> dict:
    """Load OAuth client configuration JSON file."""
    cfg_path = Path(path)
    if not cfg_path.is_file():
        print(f"[ERROR] Client config file not found: {path}")
        sys.exit(1)
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_token(creds, output_path: str):
    """Save credentials (including refresh token) to a JSON file."""
    token_path = Path(output_path)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"[INFO] Token saved to {token_path.resolve()}")

def main():
    # Expect environment variable or arguments for client config file and output token file
    client_cfg_path = os.getenv("YOUTUBE_CLIENT_CONFIG", "client_secret.json")
    token_output = os.getenv("YOUTUBE_TOKEN_OUTPUT", "youtube_token_new.json")

    print(f"[INFO] Loading client config from: {client_cfg_path}")
    client_cfg = load_client_config(client_cfg_path)

    # Use InstalledAppFlow to perform OAuth consent screen locally
    flow = InstalledAppFlow.from_client_config(client_cfg, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials (includes access_token, refresh_token, expiry, etc.)
    save_token(creds, token_output)

    # Show short summary
    token_data = json.loads(creds.to_json())
    print("[INFO] Refresh token (truncated):", token_data.get("refresh_token", "<none>")[:30] + "...")
    print("[INFO] Access token will be refreshed automatically by the library.")

if __name__ == "__main__":
    main()
