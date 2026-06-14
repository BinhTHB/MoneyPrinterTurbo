import re

with open("config.example.toml", "r", encoding="utf-8") as f:
    content = f.read()

# Find [siliconflow] section and insert [elevenlabs] after it
pattern = r"(\[siliconflow\].*?api_key = \"\"\n)"
replacement = r"\1\n[elevenlabs]\n# ElevenLabs API Key\n# Sign up at https://elevenlabs.io to get your API key.\napi_key = \"\"\n# Default voice ID. Browse voices at https://elevenlabs.io/voice-lab\ndefault_voice_id = \"JBFqnCBsd6RMkjVDRZzb\"\n# Model ID: \"eleven_multilingual_v2\" (29 languages), \"eleven_flash_v2_5\" (low-latency),\n# \"eleven_turbo_v2_5\" (balanced), \"eleven_v3\" (dramatic delivery, 70+ languages)\nmodel_id = \"eleven_multilingual_v2\"\n"

if re.search(pattern, content, re.DOTALL):
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    with open("config.example.toml", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Success")
else:
    print("Pattern not found")
    si = content.find("[siliconflow]")
    if si >= 0:
        print(repr(content[si:si+100]))
