content = open("app/config/config.py", "r", encoding="utf-8").read()
content = content.replace('siliconflow = _cfg.get("siliconflow", {})', 'siliconflow = _cfg.get("siliconflow", {})\nelevenlabs = _cfg.get("elevenlabs", {})')
open("app/config/config.py", "w", encoding="utf-8").write(content)
print("Done")
