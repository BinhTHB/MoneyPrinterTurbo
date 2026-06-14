content = open("webui/Main.py", "r", encoding="utf-8").read()

# 1. Add "elevenlabs-tts" to tts_servers
old1 = '("mimo-tts", "Xiaomi MiMo TTS"),'
new1 = '("mimo-tts", "Xiaomi MiMo TTS"),\n            ("elevenlabs-tts", "ElevenLabs TTS"),'
content = content.replace(old1, new1)

# 2. Add elevenlabs voice loading
old2 = 'elif selected_tts_server == "mimo-tts":\n            # \u83b7\u53d6 Xiaomi MiMo TTS \u7684\u9884\u7f6e\u97f3\u8272\u5217\u8868\n            filtered_voices = voice.get_mimo_voices()\n        else:'
new2 = 'elif selected_tts_server == "mimo-tts":\n            # \u83b7\u53d6 Xiaomi MiMo TTS \u7684\u9884\u7f6e\u97f3\u8272\u5217\u8868\n            filtered_voices = voice.get_mimo_voices()\n        elif selected_tts_server == "elevenlabs-tts":\n            # \u83b7\u53d6 ElevenLabs TTS \u7684\u58f0\u97f3\u5217\u8868\n            filtered_voices = voice.get_elevenlabs_voices()\n        else:'
content = content.replace(old2, new2)

# 3. Add ElevenLabs API key input
old3 = '            config.app["mimo_api_key"] = mimo_api_key\n\n        params.voice_volume'
new3 = '            config.app["mimo_api_key"] = mimo_api_key\n\n        # ElevenLabs TTS settings\n        if selected_tts_server == "elevenlabs-tts" or (\n            voice_name and voice.is_elevenlabs_voice(voice_name)\n        ):\n            saved_elevenlabs_api_key = config.app.get("elevenlabs_api_key", "") or config.elevenlabs.get("api_key", "")\n\n            elevenlabs_api_key = st.text_input(\n                tr("ElevenLabs API Key"),\n                value=saved_elevenlabs_api_key,\n                type="password",\n                key="elevenlabs_api_key_input",\n            )\n\n            st.info(\n                tr("ElevenLabs TTS Settings")\n                + ":\\n"\n                + "- "\n                + tr("Supports 29+ languages with multilingual model")\n                + "\\n"\n                + "- "\n                + tr("Voice list is fetched from your ElevenLabs account, or uses predefined voices")\n                + "\\n"\n                + "- "\n                + tr("Get API key at https://elevenlabs.io")\n            )\n\n            config.app["elevenlabs_api_key"] = elevenlabs_api_key\n\n        params.voice_volume'
content = content.replace(old3, new3)

open("webui/Main.py", "w", encoding="utf-8").write(content)
print("Main.py patched")
