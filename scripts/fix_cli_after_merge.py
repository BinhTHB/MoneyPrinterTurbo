#!/usr/bin/env python3
"""
Auto-fix cli.py after upstream merge to restore auto-youtube subcommand.
Run after: git merge upstream/main (if cli.py had conflicts)
"""

import sys
from pathlib import Path

CLI_PATH = Path("cli.py")

REQUIRED_SNIPPETS = [
    ("parse_args dispatch", 'if argv and len(argv) > 0 and argv[0] == "auto-youtube":'),
    ("parse_auto_youtube_args function", "def parse_auto_youtube_args"),
    ("run_auto_youtube function", "def run_auto_youtube"),
    ("github_runner import", "from app.automation.github_runner import run_automation"),
]


def check_cli():
    src = CLI_PATH.read_text(encoding="utf-8")
    missing = [name for name, snippet in REQUIRED_SNIPPETS if snippet not in src]
    return missing


def fix_cli():
    src = CLI_PATH.read_text(encoding="utf-8")
    changed = False

    # 1. Ensure parse_args dispatches auto-youtube
    if 'argv and len(argv) > 0 and argv[0] == "auto-youtube"' not in src:
        # Find parse_args function and insert after def line
        idx = src.find("def parse_args(")
        if idx != -1:
            # Find the next line after def
            next_line = src.find("\n", idx)
            insert_pos = next_line + 1
            patch = '''    if argv and len(argv) > 0 and argv[0] == "auto-youtube":
        return parse_auto_youtube_args(argv)

'''
            src = src[:insert_pos] + patch + src[insert_pos:]
            changed = True
            print("  Added auto-youtube dispatch to parse_args()")

    # 2. Ensure parse_auto_youtube_args exists
    if "def parse_auto_youtube_args" not in src:
        # Add before run_auto_youtube
        idx = src.find("def run_auto_youtube")
        if idx != -1:
            patch = '''def parse_auto_youtube_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MoneyPrinterTurbo YouTube automation CLI"
    )
    parser.add_argument("auto-youtube", help="Run YouTube automation pipeline")
    parser.add_argument("--channels-file", required=True, help="Path to channels config JSON")
    parser.add_argument(
        "--history-dir", default="automation-history", help="Directory for topic history"
    )
    parser.add_argument(
        "--counts", default="all=1", help="Count overrides, e.g. channel_1=2,all=1"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run without upload")
    parser.add_argument(
        "--commit-history", action="store_true", help="Commit history to repo"
    )
    return parser.parse_args(argv)


'''
            src = src[:idx] + patch + src[idx:]
            changed = True
            print("  Added parse_auto_youtube_args() function")

    # 3. Ensure run_auto_youtube exists and calls run_automation
    if "def run_auto_youtube" not in src:
        idx = src.find("def run_cli")
        if idx != -1:
            patch = '''def run_auto_youtube(argv: Sequence[str] | None = None) -> int:
    from app.automation.github_runner import run_automation

    args = parse_auto_youtube_args(argv)
    logger.info(f"Running YouTube automation: channels_file={args.channels_file}")

    results = run_automation(
        channels_file=args.channels_file,
        history_dir=args.history_dir,
        count_overrides=args.counts,
        dry_run=args.dry_run,
    )

    if args.commit_history and not args.dry_run:
        import subprocess
        subprocess.run(["git", "add", "automation-history"], check=False)
        subprocess.run(["git", "commit", "-m", "Update automation history"], check=False)
        subprocess.run(["git", "push"], check=False)

    return 0


'''
            src = src[:idx] + patch + src[idx:]
            changed = True
            print("  Added run_auto_youtube() function")

    # 4. Ensure run_cli dispatches auto-youtube
    if "run_auto_youtube" not in src and "def run_cli" in src:
        idx = src.find("def run_cli")
        if idx != -1:
            # Find the body of run_cli
            body_start = src.find(":", idx)
            if body_start != -1:
                next_line = src.find("\n", body_start)
                insert_pos = next_line + 1
                patch = '''    import sys
    args_list = argv if argv is not None else sys.argv[1:]
    if args_list and args_list[0] == "auto-youtube":
        return run_auto_youtube(argv)

'''
                src = src[:insert_pos] + patch + src[insert_pos:]
                changed = True
                print("  Added auto-youtube dispatch to run_cli()")

    if changed:
        CLI_PATH.write_text(src, encoding="utf-8")
        print("cli.py patched successfully")
    else:
        print("cli.py already up to date")

    return changed


if __name__ == "__main__":
    missing = check_cli()
    if missing:
        print(f"Missing in cli.py: {', '.join(missing)}")
        fix_cli()
        missing_after = check_cli()
        if missing_after:
            print(f"ERROR: Still missing: {', '.join(missing_after)}")
            sys.exit(1)
        else:
            print("SUCCESS: All auto-youtube components restored")
    else:
        print("cli.py already has all auto-youtube components")