# Graph Report - .  (2026-05-30)

## Corpus Check
- 138 files · ~102,236 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1338 nodes · 1656 edges · 73 communities (51 shown, 22 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_API Keys & Configuration|API Keys & Configuration]]
- [[_COMMUNITY_Video Settings & UI|Video Settings & UI]]
- [[_COMMUNITY_Media Providers|Media Providers]]
- [[_COMMUNITY_Pexels & Pixabay Integration|Pexels & Pixabay Integration]]
- [[_COMMUNITY_Custom Script Config|Custom Script Config]]
- [[_COMMUNITY_Advanced Video Params|Advanced Video Params]]
- [[_COMMUNITY_Background Music & Audio|Background Music & Audio]]
- [[_COMMUNITY_Task Queue Management|Task Queue Management]]
- [[_COMMUNITY_Text-to-Speech & Subtitles|Text-to-Speech & Subtitles]]
- [[_COMMUNITY_Docker Deployment & Infrastructure|Docker Deployment & Infrastructure]]
- [[_COMMUNITY_LLM Provider Testing|LLM Provider Testing]]
- [[_COMMUNITY_FastAPI Web Layer|FastAPI Web Layer]]
- [[_COMMUNITY_State Management|State Management]]
- [[_COMMUNITY_Script Generation|Script Generation]]
- [[_COMMUNITY_Video Processing & FFmpeg|Video Processing & FFmpeg]]
- [[_COMMUNITY_Web UI & i18n|Web UI & i18n]]
- [[_COMMUNITY_Repository Documentation|Repository Documentation]]
- [[_COMMUNITY_Logo & Brand Assets|Logo & Brand Assets]]
- [[_COMMUNITY_Material Search Service|Material Search Service]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]

## God Nodes (most connected - your core abstractions)
1. `Translation` - 131 edges
2. `Translation` - 131 edges
3. `Translation` - 120 edges
4. `Translation` - 118 edges
5. `Translation` - 118 edges
6. `Translation` - 118 edges
7. `Translation` - 101 edges
8. `str` - 29 edges
9. `InMemoryTaskManager` - 22 edges
10. `TestLiteLLMProvider` - 21 edges

## Surprising Connections (you probably didn't know these)
- `MiniMax LLM Provider` --implements--> `MoneyPrinterTurbo`  [INFERRED]
  app/llm/providers/minimax.py → README.md
- `Video Service` --references--> `Background Music`  [EXTRACTED]
  app/services/video.py → README.md
- `video_transition_mode=null bug` --references--> `Video Service`  [EXTRACTED]
  docs/PR_MERGE_RECORD_2026-04-02.md → app/services/video.py
- `Subtitle Provider` --references--> `faster-whisper`  [INFERRED]
  app/services/subtitle.py → README.md
- `PR #850: subtitle position from config` --references--> `Subtitle Provider`  [EXTRACTED]
  docs/PR_MERGE_RECORD_2026-04-02.md → app/services/subtitle.py

## Hyperedges (group relationships)
- **Video Generation Flow** — VideoGenerationPipeline, VideoService, VoiceService, SubtitleProvider, background_music [EXTRACTED 1.00]
- **Docker Deployment Stack** — Docker_CPU, Docker_GPU, Dockerfile_gpu, NVIDIA_CUDA [EXTRACTED 1.00]
- **LLM Provider Integrations** — OpenAI_LLM, DeepSeek_LLM, Moonshot_LLM, Google_Gemini, Ollama_LLM, MiniMax_Provider [EXTRACTED 1.00]
- **PR Merge Batch 2026-04-02** — gemini_fix_PR_837, GPU_faster_whisper_PR_848, upload_post_PR_843, subtitle_position_PR_850, minimax_PR_838 [EXTRACTED 1.00]
- **Successful Smoke Test (Task 2)** — VideoService, SubtitleProvider, VoiceService [EXTRACTED 1.00]

## Communities (73 total, 22 thin omitted)

### Community 0 - "API Keys & Configuration"
Cohesion: 0.02
Nodes (131): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, Advanced Script Settings, API Key, Audio Settings, Auto Detect (+123 more)

### Community 1 - "Video Settings & UI"
Cohesion: 0.02
Nodes (131): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, Advanced Script Settings, API Key, Audio Settings, Auto Detect (+123 more)

### Community 2 - "Media Providers"
Cohesion: 0.02
Nodes (120): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, API Key, Audio Settings, Auto Detect, Background Music (+112 more)

### Community 3 - "Pexels & Pixabay Integration"
Cohesion: 0.02
Nodes (118): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, API Key, Audio Settings, Auto Detect, Background Music (+110 more)

### Community 4 - "Custom Script Config"
Cohesion: 0.02
Nodes (118): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, API Key, Audio Settings, Auto Detect, Background Music (+110 more)

### Community 5 - "Advanced Video Params"
Cohesion: 0.02
Nodes (118): Translation, Account ID, Add Pexels API Key, Add Pixabay API Key, API Key, Audio Settings, Auto Detect, Background Music (+110 more)

### Community 6 - "Background Music & Audio"
Cohesion: 0.02
Nodes (101): Translation, Account ID, API Key, Audio Settings, Auto Detect, Background Music, Background Music Volume, Base Url (+93 more)

### Community 7 - "Task Queue Management"
Cohesion: 0.05
Nodes (37): Any, int, int, str, int, Request, str, AudioRequest (+29 more)

### Community 8 - "Text-to-Speech & Subtitles"
Cohesion: 0.15
Nodes (43): Edge TTS, bool, float, int, str, Communicate, azure_tts_v1(), azure_tts_v2() (+35 more)

### Community 9 - "Docker Deployment & Infrastructure"
Cohesion: 0.06
Nodes (41): API (FastAPI), DeepSeek, Docker CPU Deployment, Docker GPU Deployment, Dockerfile.gpu, PR #848: GPU faster-whisper Docker, Google Gemini, MVC Architecture (+33 more)

### Community 10 - "LLM Provider Testing"
Cohesion: 0.09
Nodes (4): TestLiteLLMLiveIntegration, TestLiteLLMProvider, TestRuntimeEnvironmentDetection, str

### Community 11 - "FastAPI Web Layer"
Cohesion: 0.08
Nodes (20): exception_handler(), get_application(), Request, validation_exception_handler(), Request, Request, str, Request (+12 more)

### Community 12 - "State Management"
Cohesion: 0.12
Nodes (12): ABC, int, str, BaseState, _convert_to_original_type(), get_all_tasks(), get_task(), MemoryState (+4 more)

### Community 13 - "Script Generation"
Cohesion: 0.16
Nodes (24): int, str, str, VideoParams, bool, str, build_script_prompt(), _extract_chat_completion_text() (+16 more)

### Community 14 - "Video Processing & FFmpeg"
Cohesion: 0.17
Nodes (23): bool, int, MaterialInfo, str, VideoAspect, VideoConcatMode, VideoParams, close_clip() (+15 more)

### Community 15 - "Web UI & i18n"
Cohesion: 0.15
Nodes (17): Any, bool, float, int, str, font_dir(), get_response(), get_uuid() (+9 more)

### Community 16 - "Repository Documentation"
Cohesion: 0.25
Nodes (14): bool, float, int, MaterialInfo, str, VideoAspect, VideoConcatMode, download_videos() (+6 more)

### Community 18 - "Material Search Service"
Cohesion: 0.18
Nodes (12): Audio Generation API, API Interface Screenshot, BGM Management API, Script Generation API, Subtitle Generation API, Task Management API, Video Terms API, Video Materials API (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.42
Nodes (8): bool, str, _can_resolve_hostname(), _decode_linux_route_gateway(), get_container_default_gateway_ip(), get_default_ollama_base_url(), is_running_in_container(), load_config()

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (4): bool, str, cross_post_video(), UploadPostService

### Community 23 - "Community 23"
Cohesion: 0.50
Nodes (7): float, str, Clip, fadein_transition(), fadeout_transition(), slidein_transition(), slideout_transition()

## Knowledge Gaps
- **903 isolated node(s):** `webui.sh script`, `PYTHONPATH`, `$schema`, `plugin`, `@opencode-ai/plugin` (+898 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TaskQueueFullError` connect `Task Queue Management` to `Script Generation`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `Translation` connect `Pexels & Pixabay Integration` to `Community 32`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `Translation` connect `Video Settings & UI` to `Community 38`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **What connects `webui.sh script`, `PYTHONPATH`, `$schema` to the rest of the system?**
  _903 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Keys & Configuration` be split into smaller, more focused modules?**
  _Cohesion score 0.015267175572519083 - nodes in this community are weakly interconnected._
- **Should `Video Settings & UI` be split into smaller, more focused modules?**
  _Cohesion score 0.015267175572519083 - nodes in this community are weakly interconnected._
- **Should `Media Providers` be split into smaller, more focused modules?**
  _Cohesion score 0.016666666666666666 - nodes in this community are weakly interconnected._