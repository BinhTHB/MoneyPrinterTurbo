# Add elevenlabs dependency check
content = open("pyproject.toml", "r", encoding="utf-8").read()
if "elevenlabs" in content:
    print("pyproject.toml: OK")
else:
    print("pyproject.toml: FAILED")
