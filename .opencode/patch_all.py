# Add elevenlabs dependency
content = open("pyproject.toml", "r", encoding="utf-8").read()
old = '"pydub==0.25.1",\n    "litellm==1.60.0",'
new = '"pydub==0.25.1",\n    "litellm==1.60.0",\n    "elevenlabs>=2.51.0",'
if old in content:
    content = content.replace(old, new)
    open("pyproject.toml", "w", encoding="utf-8").write(content)
    print("pyproject.toml: OK")
else:
    print("pyproject.toml: pattern not found")
    # debug
    idx = content.find("pydub")
    if idx >= 0:
        print("  found pydub at", idx, repr(content[idx:idx+60]))
