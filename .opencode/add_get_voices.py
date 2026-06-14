content = open('app/services/voice.py', 'r', encoding='utf-8').read()
old = '    return [f"mimo:{voice}-{gender}" for voice, gender in voices_with_gender]\n\n\n_AZURE_VOICES_DATA_FILE'
new = '''    return [f"mimo:{voice}-{gender}" for voice, gender in voices_with_gender]


def get_elevenlabs_voices() -> list[str]:
    \"\"\"
    Lay danh sach giong ElevenLabs TTS.
    Neu co API key, se fetch tu API. Neu khong, tra ve danh sach cac giong pho bien.

    Returns:
        Danh sach giong, format "elevenlabs:voice_id-VoiceName-Gender"
    \"\"\"
    api_key = config.app.get("elevenlabs_api_key", "")
    if api_key:
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=api_key)
            response = client.voices.search()
            voices = []
            for v in response.voices:
                gender = getattr(v, "gender", "Unknown") or "Unknown"
                voices.append(f"elevenlabs:{v.voice_id}-{v.name}-{gender}")
            if voices:
                return sorted(voices)
        except Exception as e:
            logger.warning(f"Failed to fetch ElevenLabs voices: {str(e)}")

    # Fallback: danh sach cac giong pho bien
    common_voices = [
        ("JBFqnCBsd6RMkjVDRZzb", "Rachel", "Female"),
        ("21m00Tcm4TlvDq8ikWAM", "Adam", "Male"),
        ("ODq5zmih8GrVes37Dizd", "Patrick", "Male"),
        ("EXAVITQu4vr2nSDke1cM", "Elli", "Female"),
        ("XrExE9yKIg1WjnnlV5kG", "Aria", "Female"),
        ("N2lVS1w4EtoT3dr4rgOW", "Domi", "Female"),
        ("IKne3meq5aSn9XLyUdCD", "Oliver", "Male"),
        ("onwK4e9ZLuTAKqWW03F9", "Daniel", "Male"),
        ("pMsXgVXv3BLzUg7XRGFv", "Bella", "Female"),
        ("LcfcDJNUP1GQjkzn1xUU", "Emily", "Female"),
        ("Yj8o4eOVY0jDn2AdSW1J", "Chris", "Male"),
        ("z9fAnlkpzviPz146aGWa", "Brian", "Male"),
        ("5Q0t7uMcjvn0Fv1VArQX", "Antoni", "Male"),
        ("ThT5KcBeYPX3keUQqHPh", "Dorothy", "Female"),
    ]
    return [
        f"elevenlabs:{voice_id}-{name}-{gender}"
        for voice_id, name, gender in common_voices
    ]


_AZURE_VOICES_DATA_FILE'''

if old in content:
    content = content.replace(old, new)
    open('app/services/voice.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('Pattern not found')
    idx = content.find('return [f"mimo:')
    if idx >= 0:
        print('found mimo at', idx, repr(content[idx:idx+120]))
