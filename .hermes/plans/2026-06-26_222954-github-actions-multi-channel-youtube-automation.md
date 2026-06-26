# GitHub Actions Multi-Channel YouTube Automation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build an automated GitHub Actions workflow that generates and uploads YouTube videos for multiple channels, where each channel defines `n` videos, prompt guidance for LLM script/topic generation, and a history of completed topics to avoid repetition.

**Architecture:** Keep upstream merge risk low by adding new automation modules under `app/automation/`, a new CLI entrypoint mode in `cli.py`, and one GitHub Actions workflow. Existing video pipeline and `app/services/youtube_upload.py` stay the upload backend. Channel-specific OAuth tokens and prompts are supplied via GitHub Secrets and runtime JSON files.

**Tech Stack:** Python 3.11, MoneyPrinterTurbo CLI, YouTube Data API v3 OAuth tokens, GitHub Actions, TOML/JSON channel configs, pytest.

---

## Current Context / Assumptions

- Direct YouTube upload already works via `app/services/youtube_upload.py`.
- Verified real upload: `https://youtu.be/4PYkgtlK9gg` private test video.
- `youtube_token.json` contains both access token and refresh token.
- `config.toml` is local-only and ignored; do not commit secrets.
- User wants:
  - Multiple YouTube channels.
  - Input prompt per channel: detailed instruction for LLM script/topic style.
  - History of previously completed topics.
  - Automatic topic generation.
  - `n-n` input mapping per channel, interpreted as per-channel count/range, e.g. channel A generates 2 videos, channel B generates 3 videos, or `min-max` random count per channel.
  - Easy upstream merge.

## Proposed Approach

Add a separate automation layer instead of bloating the existing video pipeline:

1. `app/automation/channel_config.py`
   - Parse a JSON/TOML channel config file.
   - Support per-channel settings:
     - `channel_id`
     - `name`
     - `count` or `count_range`
     - `topic_prompt`
     - `script_prompt`
     - `video_language`
     - `voice_name`
     - `youtube_token_env`
     - `youtube_client_env`
     - `privacy`
     - `shorts`
     - optional `history_file`

2. `app/automation/topic_planner.py`
   - Generate fresh topics using LLM.
   - Avoid duplicates from channel history.
   - Persist generated/uploaded topics to history.

3. `app/automation/github_runner.py`
   - Orchestrate per-channel runs.
   - For each topic:
     - Build `VideoParams` or call CLI internally.
     - Generate video.
     - Upload to channel-specific YouTube token.
     - Append result to run summary JSON.

4. `cli.py`
   - Add a new subcommand or flags:
     - `python cli.py auto-youtube --channels-file config/youtube_channels.example.json --counts "main=2,shorts=1"`
   - Prefer subcommand if refactor is acceptable; otherwise add `--automation-mode youtube` to minimize disruption.

5. `.github/workflows/youtube-automation.yml`
   - Manual dispatch (`workflow_dispatch`) first.
   - Inputs:
     - `channels_json`: JSON string or path committed without secrets.
     - `counts`: e.g. `main=1,tech=2` or `main=1-3,tech=2`.
     - `dry_run`: true/false.
     - `privacy`: private/unlisted/public override.
   - GitHub Secrets:
     - `YOUTUBE_CLIENT_JSON_MAIN`
     - `YOUTUBE_TOKEN_JSON_MAIN`
     - `YOUTUBE_CLIENT_JSON_TECH`
     - `YOUTUBE_TOKEN_JSON_TECH`
     - LLM/API keys already used by the app.

6. History persistence options:
   - Dùng GitHub Cache (`actions/cache`) làm giải pháp mặc định để phục hồi và lưu lại lịch sử `automation-history/` giữa các lần chạy.
   - Hỗ trợ auto-commit: Nếu workflow có quyền ghi, tự động commit và push các thay đổi trong `automation-history/` trở lại repo để lưu trữ vĩnh viễn và dễ dàng theo dõi.
   - Local: Lưu trong file JSON như bình thường.

---

## Config Design

Create example file:

`config/youtube_channels.example.json`

```json
{
  "channels": [
    {
      "id": "cat_shorts",
      "name": "Cat Shorts Channel",
      "enabled": true,
      "count": 1,
      "topic_prompt": "Generate wholesome, viral, family-safe YouTube Shorts topics about cute cats. Avoid topics already done. Prefer visual, simple scenes that stock footage can represent.",
      "script_prompt": "Write a concise 35-55 second English YouTube Shorts narration. Hook in first 3 seconds. Warm, playful tone. No copyrighted character names.",
      "video_language": "en",
      "voice_name": "en-US-JennyNeural-Female",
      "video_source": "pexels",
      "video_aspect": "9:16",
      "privacy": "private",
      "shorts": true,
      "youtube_client_env": "YOUTUBE_CLIENT_JSON_CAT_SHORTS",
      "youtube_token_env": "YOUTUBE_TOKEN_JSON_CAT_SHORTS",
      "history_file": "automation-history/cat_shorts.json"
    }
  ]
}
```

Runtime count override examples:

- `cat_shorts=1`
- `cat_shorts=2-4` means random count from 2 to 4 for that run.
- `all=1` default for every enabled channel.

---

## Task 1: Add Channel Config Models

**Objective:** Parse and validate multi-channel automation config without touching existing pipeline logic.

**Files:**
- Create: `app/automation/__init__.py`
- Create: `app/automation/channel_config.py`
- Test: `test/automation/test_channel_config.py`

**Implementation Notes:**

Use Pydantic if already available via project; otherwise dataclasses. Pydantic is already in this project.

Core model fields:

```python
class ChannelConfig(BaseModel):
    id: str
    name: str = ""
    enabled: bool = True
    count: int = 1
    count_range: str | None = None
    topic_prompt: str
    script_prompt: str = ""
    video_language: str = "en"
    voice_name: str = ""
    video_source: str = "pexels"
    video_aspect: str = "9:16"
    privacy: str = "private"
    shorts: bool = True
    youtube_client_env: str
    youtube_token_env: str
    history_file: str = ""
```

Add helpers:

- `load_channels_config(path: str) -> list[ChannelConfig]`
- `parse_count_overrides(raw: str) -> dict[str, str]`
- `resolve_channel_count(channel, overrides, rng=random) -> int`

**Tests:**

- Loads valid JSON.
- Rejects duplicate channel IDs.
- Parses `main=2,tech=1-3,all=1`.
- Resolves count range deterministically with mocked RNG.

**Commands:**

```bash
python -m pytest test/automation/test_channel_config.py -v
```

Expected: all tests pass.

---

## Task 2: Add Topic History Store

**Objective:** Track topics already used per channel to reduce duplicates.

**Files:**
- Create: `app/automation/topic_history.py`
- Test: `test/automation/test_topic_history.py`

**Implementation Notes:**

Define schema:

```json
{
  "channel_id": "cat_shorts",
  "topics": [
    {
      "topic": "A kitten discovers a mirror",
      "created_at": "2026-06-26T12:00:00Z",
      "task_id": "...",
      "video_id": "...",
      "url": "https://youtu.be/..."
    }
  ]
}
```

Functions:

- `load_history(path: str) -> list[str]`
- `append_history(path: str, record: dict) -> None`
- `normalize_topic(topic: str) -> str`
- `is_duplicate(topic: str, previous_topics: list[str]) -> bool`

Keep fuzzy matching simple in Phase 1:
- lowercase
- strip punctuation
- collapse whitespace
- exact normalized match

Avoid adding heavy deps.

**Tests:**

- Empty file returns empty history.
- Append creates parent dirs.
- Duplicate detection catches punctuation/case variants.

---

## Task 3: Add Topic Planner

**Objective:** Generate fresh video topics using LLM with channel prompt and history context.

**Files:**
- Create: `app/automation/topic_planner.py`
- Test: `test/automation/test_topic_planner.py`

**Implementation Notes:**

Function:

```python
def generate_topics(channel: ChannelConfig, count: int, previous_topics: list[str]) -> list[str]:
    ...
```

Prompt template:

```text
You are planning YouTube Shorts topics for channel: {channel.name}.
Channel guidance:
{channel.topic_prompt}

Already completed topics:
{history_bullets}

Generate {count} new distinct topics.
Rules:
- Return JSON only: {"topics": ["..."]}
- Do not repeat or paraphrase completed topics.
- Topics must be visual and feasible for stock footage.
- No copyrighted character names.
```

Use existing `app.services.llm._generate_response` only if stable enough; safer is to add public helper in `llm.py` if needed:

- `generate_automation_topics(prompt: str) -> list[str]`

But to reduce conflict, keep topic planner using existing public-ish functions if available; inspect `llm.py` first during implementation.

**Tests:**

Mock LLM response:

```json
{"topics": ["A kitten chases sunlight", "A kitten finds a tiny hat"]}
```

Validate:
- JSON extraction.
- Dedup against history.
- Raises clear error if not enough fresh topics.

---

## Task 4: Add Channel-Specific YouTube Credentials Loader

**Objective:** Support multiple YouTube channels in one run using per-channel env secrets.

**Files:**
- Modify: `app/services/youtube_upload.py`
- Create: `app/automation/youtube_credentials.py`
- Test: `test/automation/test_youtube_credentials.py`

**Implementation Notes:**

Do not require `config.toml` for CI channel secrets.

Add helper:

```python
def build_youtube_config_from_env(channel: ChannelConfig, workdir: str) -> dict:
    client_json = os.environ[channel.youtube_client_env]
    token_json = os.environ[channel.youtube_token_env]
    token_file = Path(workdir) / f"youtube_token_{channel.id}.json"
    token_file.write_text(token_json, encoding="utf-8")
    return {
        "enabled": True,
        "auto_upload": True,
        "privacy": channel.privacy,
        "shorts": channel.shorts,
        "oauth_client": json.loads(client_json),
        "token_file": str(token_file),
    }
```

Important:
- Never print token/client JSON.
- Ensure token file path is inside temp workspace.
- Add generated token files to `.gitignore` pattern if needed:
  - `/youtube_token*.json`

**Tests:**

- Env vars produce config.
- Missing env var raises clear message with env name only.
- Token file is written to temp path.

---

## Task 5: Add Automation Runner

**Objective:** Orchestrate channel/topic/video/upload loop.

**Files:**
- Create: `app/automation/github_runner.py`
- Test: `test/automation/test_github_runner.py`

**Implementation Notes:**

Core function:

```python
def run_youtube_automation(
    channels_file: str,
    counts: str = "",
    dry_run: bool = False,
    output_file: str = "automation-results.json",
) -> dict:
    ...
```

For each enabled channel:

1. Resolve count.
2. Load history.
3. Generate topics.
4. If `dry_run`, write planned topics and skip video generation/upload.
5. For each topic:
   - Build `VideoParams`:
     - `video_subject=topic`
     - `video_language=channel.video_language`
     - `video_script_prompt=channel.script_prompt`
     - `voice_name=channel.voice_name`
     - `video_source=channel.video_source`
     - `video_aspect=channel.video_aspect`
     - `video_count=1`
   - Call `task.start(task_id=..., params=params, stop_at="video")`.
   - Upload using `YouTubeUploadService(channel_youtube_config)`.
   - Append history only after successful video generation; append upload URL if upload succeeds.

Result schema:

```json
{
  "channels": [
    {
      "id": "cat_shorts",
      "planned_count": 1,
      "topics": [
        {
          "topic": "...",
          "task_id": "...",
          "video_path": "...",
          "upload": {"success": true, "video_id": "...", "url": "..."}
        }
      ]
    }
  ]
}
```

**Tests:**

Mock:
- topic generation
- `task.start`
- `YouTubeUploadService.upload_video`

Verify:
- multiple channels run.
- dry run skips generation/upload.
- history is updated after success.
- failed upload does not stop other channels unless `fail_fast=True` is added later.

---

## Task 6: Add CLI Automation Entry

**Objective:** Expose automation runner from `cli.py` with minimal conflict risk.

**Files:**
- Modify: `cli.py`
- Test: `test/services/test_cli.py` or new `test/automation/test_cli_automation.py`

**Preferred CLI:**

```bash
python cli.py auto-youtube \
  --channels-file config/youtube_channels.json \
  --counts "cat_shorts=1,tech_shorts=2" \
  --output-file automation-results.json
```

But current `cli.py` uses simple argparse with required `--video-subject`. To minimize refactor risk, implement a pre-parse branch at top of `run_cli()`:

```python
if argv and len(argv) > 0 and argv[0] == "auto-youtube":
    return run_auto_youtube_cli(argv[1:])
```

Add:

```python
def parse_auto_youtube_args(argv): ...
def run_auto_youtube_cli(argv): ...
```

This avoids disrupting existing CLI tests.

**Tests:**

- Existing CLI tests still pass.
- `auto-youtube --dry-run` dispatches `run_youtube_automation`.

---

## Task 7: Add GitHub Actions Workflow

**Objective:** Enable manual automation runs in CI.

**Files:**
- Create: `.github/workflows/youtube-automation.yml`
- Create: `config/youtube_channels.example.json`
- Create: `docs/youtube-automation.md`

**Workflow Draft:**

```yaml
name: YouTube Automation

on:
  workflow_dispatch:
    inputs:
      counts:
        description: 'Channel counts, e.g. cat_shorts=1,tech_shorts=2 or all=1'
        required: true
        default: 'all=1'
      dry_run:
        description: 'Plan topics only, no video/upload'
        required: true
        type: boolean
        default: true
      privacy:
        description: 'Override privacy: private/unlisted/public'
        required: false
        default: 'private'

jobs:
  generate-and-upload:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    env:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
      YOUTUBE_CLIENT_JSON_CAT_SHORTS: ${{ secrets.YOUTUBE_CLIENT_JSON_CAT_SHORTS }}
      YOUTUBE_TOKEN_JSON_CAT_SHORTS: ${{ secrets.YOUTUBE_TOKEN_JSON_CAT_SHORTS }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Install dependencies
        run: uv sync
      - name: Install ffmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - name: Restore history cache
        uses: actions/cache/restore@v4
        with:
          path: automation-history
          key: youtube-automation-history-${{ github.run_id }}
          restore-keys: |
            youtube-automation-history-

      - name: Run YouTube automation
        run: |
          uv run python cli.py auto-youtube \
            --channels-file config/youtube_channels.example.json \
            --counts "${{ inputs.counts }}" \
            ${{ inputs.dry_run && '--dry-run' || '' }} \
            --output-file automation-results.json

      - name: Commit history updates
        if: ${{ !inputs.dry_run }}
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add automation-history/*.json || true
          git commit -m "chore: update YouTube automation history [skip ci]" || true
          git push || true

      - name: Save history cache
        if: ${{ always() && !inputs.dry_run }}
        uses: actions/cache/save@v4
        with:
          path: automation-history
          key: youtube-automation-history-${{ github.run_id }}

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: youtube-automation-results
          path: |
            automation-results.json
            storage/tasks/**/final-*.mp4
```

Need validate GitHub Actions expression for conditional CLI flag; if brittle, use shell `if`.

**Docs:**

Include:
- How to create OAuth token locally.
- How to copy `youtube_token.json` into GitHub Secret.
- How to add multiple channels.
- Recommended first run: `dry_run=true`, `privacy=private`.

---

## Task 8: Add CI-Safe Token Refresh Handling

**Objective:** Preserve refreshed YouTube token after CI run.

**Problem:** Google client refreshes access token and may update token file, but GitHub Secrets are immutable at runtime.

**Phase 1 Solution:** Upload refreshed token file as encrypted artifact is not enough for security; avoid this by accepting that refresh token remains valid and access token can be refreshed from original secret each run.

**Implementation:**

- At each CI run, write token JSON secret to temp file.
- Google library refreshes access token in temp file.
- Do not try to update GitHub Secret automatically.
- As long as `refresh_token` is valid, next run can refresh again from original token JSON.

**Docs Warning:**

- If Google revokes refresh token, rerun local OAuth and update GitHub Secret.
- Keep app OAuth publishing status configured correctly to avoid 7-day test-user token expiry.

Important Google OAuth note:
- If OAuth consent screen is in Testing mode, refresh tokens may expire after 7 days.
- For long-term automation, publish app to Production or ensure policy-compliant OAuth setup.

---

## Task 9: Validation Matrix

**Unit Tests:**

```bash
python -m pytest test/automation test/services/test_youtube_upload.py test/services/test_cli.py -q
```

Expected: all pass.

**Dry Run Local:**

```bash
python cli.py auto-youtube \
  --channels-file config/youtube_channels.example.json \
  --counts "all=1" \
  --dry-run \
  --output-file automation-results.json
```

Expected:
- No video generation.
- No YouTube upload.
- `automation-results.json` contains planned topics.

**Single Channel Private Upload Local:**

```bash
python cli.py auto-youtube \
  --channels-file config/youtube_channels.local.json \
  --counts "cat_shorts=1" \
  --output-file automation-results.json
```

Expected:
- One video generated.
- One private YouTube upload success.
- History updated.

**GitHub Actions Dry Run:**

- Trigger manually with `dry_run=true`, `counts=all=1`.
- Verify artifact contains results JSON.

**GitHub Actions Private Upload:**

- Trigger manually with `dry_run=false`, `counts=cat_shorts=1`.
- Verify private YouTube URL exists in artifact summary.

---

## Risks / Tradeoffs

1. **GitHub Actions compute limits**
   - Video generation with downloads and ffmpeg may be slow.
   - Mitigation: start with 1 short video, `privacy=private`, cache dependencies.

2. **OAuth refresh token expiry**
   - Testing-mode OAuth apps can expire refresh tokens after 7 days.
   - Mitigation: move OAuth consent to Production if possible.

3. **Multiple channels need separate OAuth tokens**
   - Each channel must authorize upload scope.
   - Mitigation: env naming convention per channel.

4. **Topic duplication**
   - Simple exact normalized matching misses semantic duplicates.
   - Phase 2 can add LLM duplicate check or embeddings.

5. **History persistence in CI**
   - Artifacts are not ideal long-term state.
   - Phase 2 can commit history to repo, use GitHub cache, or a tiny external store.

6. **Upstream merge conflict risk**
   - `cli.py` changes are the riskiest.
   - Keep automation behind a first-arg branch and new modules.

---

## Open Questions

1. Count syntax: Should `n-n` mean random range (`2-5`) or per-channel mapping (`channelA=2,channelB=5`)? Recommended: support both `channel=2` and `channel=2-5`.
2. Should history be committed back to repo automatically, or only stored as artifact initially?
3. Should failed upload stop the whole workflow or continue to next topic/channel? Recommended: continue, summarize failures.
4. Should topic generation be one batch per channel or one-by-one after each upload? Recommended: batch per channel for fewer LLM calls.
5. Should `privacy` be globally overridden by workflow input? Recommended: yes, default `private`.

---

## Suggested Implementation Order

1. Task 1: Channel config models.
2. Task 2: Topic history store.
3. Task 3: Topic planner.
4. Task 4: YouTube credentials env loader.
5. Task 5: Automation runner dry-run only.
6. Task 6: CLI `auto-youtube` dry-run.
7. Task 7: Real generation/upload path.
8. Task 8: GitHub Actions workflow.
9. Task 9: Docs and validation.

Commit after each completed task with English messages:

```bash
git commit -m "Add YouTube automation channel config"
git commit -m "Add topic history store for YouTube automation"
git commit -m "Add LLM topic planner for YouTube automation"
git commit -m "Load per-channel YouTube credentials from environment"
git commit -m "Add multi-channel YouTube automation runner"
git commit -m "Expose YouTube automation through CLI"
git commit -m "Add GitHub Actions workflow for YouTube automation"
git commit -m "Document YouTube automation setup"
```

---

## Phase 2 Ideas

- Add scheduled runs (`cron`) after manual workflow is stable.
- Add per-channel templates for title/description/tags.
- Add semantic duplicate detection using LLM or embeddings.
- Add YouTube playlist assignment.
- Add upload scheduling/publish time.
- Add Slack/Telegram notification after workflow.
- Add support for TikTok/Instagram later via separate upload services, not Upload-Post.
