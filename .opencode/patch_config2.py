content = open("app/config/config.py", "r", encoding="utf-8").read()
content = content.replace('_cfg["siliconflow"] = siliconflow', '_cfg["siliconflow"] = siliconflow\n        _cfg["elevenlabs"] = elevenlabs')
open("app/config/config.py", "w", encoding="utf-8").write(content)
print("Done")
