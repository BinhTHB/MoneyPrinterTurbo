#!/usr/bin/env python3
"""
Tạo client_secret.json từ thông tin client trong config.toml.
Script này an toàn cho môi trường kiểm chứng (không yêu cầu input từ bàn phím).
Ghi đè client_secret.json cũ nếu cần.
"""
import json
import sys
from pathlib import Path

def extract_client_config(config_path="config.toml", output_path="client_secret.json"):
    cfg_path = Path(config_path)
    if not cfg_path.is_file():
        print(f"[ERROR] config.toml không tồn tại: {config_path}", file=sys.stderr)
        sys.exit(1)
    text = cfg_path.read_text(encoding="utf-8")
    client_id = client_secret = project_id = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("client_id") and "=" in line:
            client_id = line.split("=", 1)[1].strip().strip('\"')
        elif line.startswith("client_secret") and "=" in line:
            client_secret = line.split("=", 1)[1].strip().strip('\"')
        elif line.startswith("project_id") and "=" in line:
            project_id = line.split("=", 1)[1].strip().strip('\"')
    if not all([client_id, client_secret, project_id]):
        print(f"[ERROR] Thiếu thông tin client trong config.toml", file=sys.stderr)
        print(f"  client_id: {client_id}", file=sys.stderr)
        print(f"  client_secret: {'***' if client_secret else None}...", file=sys.stderr)
        print(f"  project_id: {project_id}", file=sys.stderr)
        sys.exit(1)
    return client_id, client_secret, project_id

def create_client_secret_json(output_path: Path, client_id: str, client_secret: str, project_id: str):
    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }
    if output_path.is_file():
        print(f"[WARN] client_secret.json đã tồn tại, ghi đè.")
    output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"[OK] client_secret.json đã được tạo tại {output_path.resolve()}")

def main():
    # Lấy thông tin từ config.toml (đảm bảo tính nhất quán)
    cli_id, cli_secret, proj_id = extract_client_config()
    out_path = Path("client_secret.json")
    create_client_secret_json(out_path, cli_id, cli_secret, proj_id)

if __name__ == "__main__":
    main()
