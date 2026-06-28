## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).


## Main Branch Workflow

This is a personal fork. The `main` branch is the active development
branch containing both upstream changes and personal customizations.

Upstream URL: https://github.com/harry0703/MoneyPrinterTurbo (remote: upstream)
Fork URL: https://github.com/BinhTHB/MoneyPrinterTurbo (remote: origin)

Rules:
- Never create pull requests to the upstream unless explicitly asked.
- When upstream has new changes, merge them into main, resolving
  conflicts to prioritize upstream changes. If personal customizations conflict with upstream
  and cannot be adapted, remove them:
  ```
  git fetch upstream
  git merge upstream/main
  # resolve conflicts, prioritizing upstream changes
  git push origin main
  ```
- Do not add Co-authored-by lines to any commit messages.

## Upstream Merge & Pipeline Integrity Plan

**Goal**: Safely merge upstream changes without breaking the YouTube Automation pipeline.

### Trigger Conditions
- Run when upstream has new commits (`git fetch upstream && git log --oneline HEAD..upstream/main`).
- Run before any major release or weekly if upstream active.

### Step-by-Step Procedure

1. **Create test branch**
   ```bash
   git checkout -b merge-test-$(date +%s) main
   ```

2. **Fetch & merge upstream**
   ```bash
   git fetch upstream
   git merge upstream/main
   ```
   - Expect conflicts in: `config.toml`, `cli.py`, `.github/workflows/*`, `app/automation/*`.
   - **Resolution priority**: Keep upstream changes for core logic; re-apply personal customizations manually.

3. **Run local validation**
   ```bash
   uv sync
   python -m pytest test/automation test/services/test_cli.py test/services/test_youtube_upload.py -q
   ```
   - All tests must pass (currently 40+ tests).
   - Verify `test_github_runner.py` passes (key `video_paths`/`videos` logic).

4. **Check critical files for breaking changes**
   | File | What to verify |
   |------|----------------|
   | `config.toml` | New fields? Missing fields pipeline needs? |
   | `cli.py` | `auto-youtube` command intact? Argument parsing changed? |
   | `app/services/task.py` | Return dict keys (`videos` vs `video_paths`)? |
   | `app/services/youtube_upload.py` | `YouTubeUploadService` interface? |
   | `app/models/schema.py` | `VideoParams` fields? `bgm_type`, `voice_name`? |
   | `app/services/video.py` | `get_bgm_file`, `combine_videos` signatures? |
   | `.github/workflows/youtube-automation.yml` | Upstream added new workflow? |

5. **Dry-run workflow on GitHub Actions**
   - Push test branch: `git push origin merge-test-xxx`
   - Run workflow via UI or `gh workflow run` with `dry_run=true`.
   - Verify: 42+ tests pass, video generation steps run without error.

6. **If dry-run passes**
   - Switch back to main: `git checkout main`
   - Merge test branch: `git merge merge-test-xxx`
   - Push: `git push origin main`
   - Delete test branch: `git branch -d merge-test-xxx && git push origin --delete merge-test-xxx`

7. **If dry-run fails**
   - Fix issues on test branch, repeat step 5.
   - If unfixable (upstream removed feature we need): decide to maintain forked copy of that file or adapt pipeline.

### Files to NEVER Auto-Merge (Manual Review Required)
- `app/automation/channel_config.py`
- `app/automation/github_runner.py`
- `app/automation/topic_planner.py`
- `app/automation/youtube_credentials.py`
- `app/automation/topic_history.py`
- `config/youtube_channels.channel_1.json`
- `.github/workflows/youtube-automation.yml`
- `cli.py` (auto-youtube command)

### Auto-Fix for `cli.py` Conflicts
If upstream modifies `cli.py` and causes merge conflicts, re-apply the `auto-youtube` subcommand automatically:

```bash
# After git merge upstream/main (with or without conflicts)
python scripts/fix_cli_after_merge.py
# Verify
python -c "from cli import run_auto_youtube, parse_auto_youtube_args; print('OK')"
```

The script in `scripts/fix_cli_after_merge.py` checks and restores:
1. `parse_args()` dispatch: routes `argv[0] == "auto-youtube"` to `parse_auto_youtube_args()`
2. `parse_auto_youtube_args()` function with `--channels-file`, `--history-dir`, `--counts`, `--dry-run`, `--commit-history`
3. `run_auto_youtube()` function calling `run_automation()` from `github_runner`
4. `run_cli()` dispatch: routes `"auto-youtube"` first argument

### Post-Merge Verification
- Run full test suite locally.
- Trigger real workflow (`dry_run=false`) for 1 video to confirm end-to-end.

### Rollback Plan
If pipeline breaks after merge:
```bash
git revert <merge-commit-sha>
git push origin main
# Or hard reset if needed
git reset --hard origin/main
git push --force origin main
```

## Language

Always respond in Vietnamese (tiếng Việt) unless the user explicitly requests another language.
Always respond in Vietnamese (tiếng Việt) unless the user explicitly requests another language.