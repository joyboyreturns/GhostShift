#!/usr/bin/env python3
"""Run one Kiro CLI session from a brief file and record honest evidence (Python 3.9+, stdlib only).

Usage: python3 scripts/kiro_session.py <slug> <brief.md> [--interactive] [--effort high]

Writes .kiro/evidence/<date>-<slug>.log (verbatim output) and .json (measured metadata only:
times, exit code, tool version, git HEAD, brief hash, files changed). It records no credit figures
unless the CLI prints them and never edits the log. Run it yourself: sessions spend Kiro credits.
Review the diff afterwards; attribution of every change goes in docs/kiro-evidence.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".kiro" / "evidence"


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def changed_files() -> list[str]:
    return [line[3:] for line in run("git", "status", "--porcelain").splitlines()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", help="short kebab-case name, e.g. ghost-scan-spec")
    parser.add_argument("brief", type=Path)
    parser.add_argument("--interactive", action="store_true", help="keep a TTY; output is then not logged")
    parser.add_argument("--effort", default="high")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", args.slug):
        print("slug must be kebab-case", file=sys.stderr)
        return 2
    brief = args.brief if args.brief.is_absolute() else ROOT / args.brief
    if not brief.is_file():
        print(f"brief not found: {brief}", file=sys.stderr)
        return 2
    if changed_files():
        print("Working tree is not clean; commit or stash first so the session's diff is attributable.", file=sys.stderr)
        return 2

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc)
    base = EVIDENCE / f"{stamp:%Y-%m-%d}-{args.slug}"
    if base.with_suffix(".json").exists():
        print(f"{base.name}.json exists; choose a new slug", file=sys.stderr)
        return 2

    text = brief.read_text()
    command = ["kiro-cli", "chat", "--trust-workspace", "--effort", args.effort]
    if not args.interactive:
        command += ["--no-interactive", "--trust-all-tools"]
    command.append(text)

    meta = {
        "slug": args.slug,
        "started_at": stamp.isoformat(),
        "tool": run("kiro-cli", "--version"),
        "brief_file": str(brief.relative_to(ROOT)),
        "brief_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "git_head_before": run("git", "rev-parse", "HEAD"),
        "launcher": "user via scripts/kiro_session.py",
        "mode": "interactive (not logged)" if args.interactive else "non-interactive, output logged verbatim",
    }
    print(f"Starting Kiro session '{args.slug}'. This spends Kiro credits.")
    if args.interactive:
        code = subprocess.run(command, cwd=ROOT, check=False).returncode
    else:
        with base.with_suffix(".log").open("w") as log:
            process = subprocess.Popen(
                command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            assert process.stdout is not None
            for line in process.stdout:
                sys.stdout.write(line)
                log.write(line)
            code = process.wait()
    meta.update(
        {
            "ended_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "exit_code": code,
            "files_changed_by_session": changed_files(),
            "credit_usage": "not measured",
            "local_review": "pending: record author, tests run and corrections in docs/kiro-evidence.md",
        }
    )
    base.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"\nEvidence written to {base.relative_to(ROOT)}.json. Review the diff before committing.")
    return code


if __name__ == "__main__":
    sys.exit(main())
