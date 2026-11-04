#!/usr/bin/env python3
"""Pre-submission compliance audit for Kiroween (standard library only, Python 3.9+).

Checks the objective, repository-level requirements. It cannot judge Kiro-usage quality,
and it never inspects the Devpost form. Exit code 1 if any check fails.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "generic API key assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]"
    ),
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".pdf", ".woff", ".woff2", ".ico", ".lock"}


def git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def tracked_files(cwd: Path = ROOT) -> list[str]:
    result = git("ls-files", cwd=cwd)
    return [line for line in result.stdout.splitlines() if line]


def check_license(root: Path) -> tuple[bool, str]:
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
        path = root / name
        if path.is_file() and path.stat().st_size > 200:
            head = path.read_text(errors="replace")[:400]
            return True, f"{name}: {head.splitlines()[0].strip() if head else 'present'}"
    return False, "no substantial LICENSE file at repository root"


def check_kiro_tracked(root: Path) -> tuple[bool, str]:
    files = [f for f in tracked_files(root) if f.startswith(".kiro/")]
    if not files:
        return False, ".kiro has no tracked files"
    ignored = git("check-ignore", "-q", ".kiro", ".kiro/specs", ".kiro/steering", ".kiro/hooks", cwd=root)
    # exit 0 means at least one path is ignored
    if ignored.returncode == 0:
        return False, ".kiro or a sub-folder is matched by .gitignore"
    return True, f"{len(files)} tracked files under .kiro/"


def check_kiro_specs_are_real(root: Path) -> tuple[bool, str]:
    """Each spec directory must hold requirements.md, design.md and tasks.md, not only a README."""
    specs = root / ".kiro" / "specs"
    incomplete = []
    complete = []
    for directory in sorted(p for p in specs.iterdir() if p.is_dir()) if specs.is_dir() else []:
        have = {n for n in ("requirements.md", "design.md", "tasks.md") if (directory / n).is_file()}
        (complete if len(have) == 3 else incomplete).append(directory.name)
    if incomplete:
        return False, f"placeholder specs without requirements/design/tasks: {incomplete}"
    return bool(complete), f"complete specs: {complete}"


def check_hooks_and_agents(root: Path) -> tuple[bool, str]:
    hooks = [p for p in (root / ".kiro" / "hooks").glob("*") if p.is_file() and p.name != "README.md"]
    agents = [p for p in (root / ".kiro" / "agents").glob("*.json") if p.is_file()]
    steering = list((root / ".kiro" / "steering").glob("*.md"))
    ok = bool(hooks) and bool(agents)
    return ok, f"hooks={len(hooks)} agents={len(agents)} steering={len(steering)}"


def check_evidence_logged(root: Path) -> tuple[bool, str]:
    sessions = sorted((root / ".kiro" / "evidence").glob("*.json"))
    return len(sessions) >= 3, f"{len(sessions)} recorded Kiro session metadata files"


def check_secrets(root: Path) -> tuple[bool, str]:
    hits = []
    for rel in tracked_files(root):
        path = root / rel
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file() or path.stat().st_size > 1_500_000:
            continue
        if rel.endswith(("package-lock.json", "uv.lock")):
            continue
        text = path.read_text(errors="ignore")
        is_test = "/tests/" in f"/{rel}"
        for label, pattern in SECRET_PATTERNS.items():
            if label.startswith("generic") and is_test:
                continue  # test fixtures use obvious dummy values
            if pattern.search(text):
                hits.append(f"{rel}: {label}")
    return not hits, "; ".join(hits[:5]) if hits else "no secret patterns in tracked files"


def check_env_not_tracked(root: Path) -> tuple[bool, str]:
    bad = [f for f in tracked_files(root) if re.search(r"(^|/)\.env(\.|$)", f) and not f.endswith(".example")]
    return not bad, f"tracked env files: {bad}" if bad else "no real .env files tracked"


def check_readme(root: Path) -> tuple[bool, str]:
    readme = (root / "README.md").read_text(errors="replace") if (root / "README.md").is_file() else ""
    needed = ["install", "test", "license"]
    missing = [w for w in needed if w not in readme.lower()]
    placeholders = re.findall(r"(?i)(TODO|TBD|example\.com|lorem ipsum)", readme)
    problems = [f"missing mention of {missing}"] if missing else []
    if placeholders:
        problems.append(f"placeholder text: {sorted(set(map(str.lower, placeholders)))}")
    return not problems, "; ".join(problems) or "README has setup/test/license content"


def check_clean_tree(root: Path) -> tuple[bool, str]:
    status = git("status", "--porcelain", cwd=root).stdout.strip()
    return not status, "working tree clean" if not status else f"{len(status.splitlines())} uncommitted paths"


def check_remote_public(root: Path) -> tuple[bool, str]:
    remote = git("remote", "get-url", "origin", cwd=root).stdout.strip()
    return remote.startswith(("https://github.com/", "git@github.com:")), remote or "no origin remote"


def check_submission_links(root: Path) -> tuple[bool, str]:
    path = root / "docs" / "submission-links.json"
    if not path.is_file():
        return False, "docs/submission-links.json missing (app_url, video_url filled after publishing)"
    data = json.loads(path.read_text())
    missing = [k for k in ("app_url", "video_url", "repo_url") if not str(data.get(k, "")).startswith("https://")]
    return not missing, f"unfilled or non-https: {missing}" if missing else "all submission links set"


CHECKS = [
    ("LICENSE present", check_license),
    (".kiro tracked and not ignored", check_kiro_tracked),
    ("Kiro specs are complete (not placeholders)", check_kiro_specs_are_real),
    ("Kiro hooks and custom agents exist", check_hooks_and_agents),
    ("Kiro session evidence recorded", check_evidence_logged),
    ("no secret patterns in tracked files", check_secrets),
    ("no real .env tracked", check_env_not_tracked),
    ("README basics", check_readme),
    ("GitHub origin remote", check_remote_public),
    ("working tree clean", check_clean_tree),
    ("public links recorded", check_submission_links),
]


def main() -> int:
    failures = 0
    for name, check in CHECKS:
        ok, detail = check(ROOT)
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
        failures += not ok
    print(
        f"\n{failures} failing check(s). This audit covers repository requirements only;"
        " verify the video, deployed app and Devpost form by hand."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
