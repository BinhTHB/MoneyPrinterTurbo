content = open("app/services/voice.py", "r", encoding="utf-8").read()

old = "    return None\n\n\ndef _format_text(text: str) -> str:"
new = """    return None


def elevenlabs_tts(
    text: str,
    voice_id: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
) -> Union[SubMaker, None]:
    \"\"\"
    Use ElevenLabs TTS API to generate speech.

    Uses the official elevenlabs Python SDK.
    Falls back to populate_legacy_submaker_with_full_text() for subtitle
    timestamps since the basic convert() does not return word-level boundaries.

    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID
        voice_rate: Speech rate (ElevenLabs range ~0.7-1.2)
        voice_file: Output audio file path (.mp3)
        voice_volume: Audio volume (currently handled by provider defaults)

    Returns:
        SubMaker object or None on failure
    \"\"\"
    from elevenlabs.client import ElevenLabs
    from pydub import AudioSegment
    _configure_pydub_ffmpeg(AudioSegment)

    text = (text or "").strip()
    if not text:
        logger.error("ElevenLabs TTS text is empty")
        return None

    api_key = config.app.get("elevenlabs_api_key", "") or config.elevenlabs.get("api_key", "")
    if not api_key:
        logger.error("ElevenLabs API key is not set, configure [elevenlabs] api_key in config.toml")
        return None

    model_id = config.elevenlabs.get("model_id", "eleven_multilingual_v2")
    if not voice_id:
        voice_id = config.elevenlabs.get("default_voice_id", "JBFqnCBsd6RMkjVDRZzb")

    for i in range(3):
        try:
            logger.info(
                f"start elevenlabs tts, voice: {voice_id}, model: {model_id}, try: {i + 1}"
            )
            ensure_file_path_exists(voice_file)

            client = ElevenLabs(api_key=api_key)
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format="mp3_44100_128",
            )

            audio_bytes = b"".join(audio) if hasattr(audio, "__iter__") else audio
            if isinstance(audio_bytes, str):
                audio_bytes = audio_bytes.encode()

            with open(voice_file, "wb") as f:
                f.write(audio_bytes)

            try:
                audio_segment = AudioSegment.from_mp3(voice_file)
                audio_duration = len(audio_segment) / 1000.0
            except Exception as e:
                logger.warning(f"failed to get audio duration: {str(e)}")
                audio_duration = 0.0

            sub_maker = ensure_legacy_submaker_fields(SubMaker())
            logger.success(f"elevenlabs tts succeeded: {voice_file}")
            return populate_legacy_submaker_with_full_text(
                sub_maker=sub_maker,
                text=text,
                audio_duration_seconds=audio_duration,
            )
        except ImportError as e:
            logger.error(f"Missing package for ElevenLabs TTS: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"elevenlabs tts failed: {str(e)}")

    return None


def _format_text(text: str) -> str:"""

content = content.replace(old, new)
open("app/services/voice.py", "w", encoding="utf-8").write(content)
print("elevenlabs_tts added")
