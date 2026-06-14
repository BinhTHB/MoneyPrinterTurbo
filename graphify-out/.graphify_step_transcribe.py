import json, os, sys
from pathlib import Path
from graphify.transcribe import transcribe_all

try:
    with open('graphify-out/.graphify_detect.json', 'r', encoding='utf-8-sig') as f:
        detect = json.load(f)
    video_files = detect.get('files', {}).get('video', [])
    prompt = os.environ.get('GRAPHIFY_WHISPER_PROMPT', 'Use proper punctuation and paragraph breaks.')
    print(f'Processing {len(video_files)} video files...', file=sys.stderr)
    transcript_paths = transcribe_all(video_files, initial_prompt=prompt)
    print(json.dumps(transcript_paths, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
