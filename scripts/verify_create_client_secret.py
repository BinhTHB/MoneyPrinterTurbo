import json
import os
from pathlib import Path

def extract_youtube_client_from_config(config_path="config.toml", output_path="client_secret.json"):
    """
    Trích xuất thông tin client YouTube từ config.toml và tạo client_secret.json.
    Nếu client_secret.json đã tồn tại, hãy hỏi người dùng muốn xử lý thế nào.
    """
    config_path = Path(config_path)
    if not config_path.is_file():
        print(f"[LỖI] config.toml không tồn tại!")
        return False

    config_content = config_path.read_text(encoding="utf-8")

    client_id = None
    client_secret = None
    project_id = None

    for line in config_content.splitlines():
        line = line.strip()
        if line.startswith("client_id") and "=" in line:
            client_id = line.split("=", 1)[1].strip().strip('\"')
        elif line.startswith("client_secret") and "=" in line:
            client_secret = line.split("=", 1)[1].strip().strip('\"')
        elif line.startswith("project_id") and "=" in line:
            project_id = line.split("=", 1)[1].strip().strip('\"')

    if not all([client_id, client_secret, project_id]):
        print(f"[LỖI] Không tìm thấy đầy đủ client_id, client_secret hoặc project_id trong config.toml")
        return False

    # Tạo cấu trúc client_secret.json
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }

    client_secret_path = Path(output_path)
    if client_secret_path.is_file():
        print(f"[CẢNH BÁO] client_secret.json đã tồn tại: {client_secret_path}")
        user_choice = input("Bạn muốn (1) Ghi đè (2) Giữ nguyên (3) Thoát? [1/2/3]: ").strip()
        if user_choice == "1":
            pass  # Ghi đè
        elif user_choice == "2":
            print(f"[THÔNG BÁO] Giữ nguyên. Bỏ qua hoạt động.")
            return True
        else:
            print(f"[THÔNG BÁO] Thoát.")
            return False

    client_secret_path.write_text(json.dumps(client_config, indent=2), encoding="utf-8")
    print(f"[THÀNH CÔNG] client_secret.json đã được tạo tại {client_secret_path.resolve()}")
    return True

if __name__ == "__main__":
    success = extract_youtube_client_from_config()
    if not success:
        exit(1)
    
    # Kiểm tra bằng cách đọc lại file
    client_secret_path = Path("client_secret.json")
    if client_secret_path.is_file():
        data = json.loads(client_secret_path.read_text())
        print(f"[VERIFICATION] client_id: {data['installed']['client_id']}")
        print(f"[VERIFICATION] client_secret: {data['installed']['client_secret'][:20]}...")
        print(f"[VERIFICATION] project_id: {data['installed']['project_id']}")
        
        # Kiểm tra cấu trúc
        required_keys = ["client_id", "client_secret", "project_id", "auth_uri", "token_uri", "redirect_uris"]
        if all(key in data["installed"] for key in required_keys):
            print(f"[VERIFICATION] Cấu trúc hợp lệ")
        else:
            print(f"[VERIFICATION] Cấu trúc không hợp lệ - thiếu các trường bắt buộc")
    else:
        print(f"[VERIFICATION] client_secret.json không tồn tại")
        exit(1)
