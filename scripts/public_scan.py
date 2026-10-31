#!/usr/bin/env python3
"""Fail if a file in this repo looks unsafe to publish."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "data",
    ".mypy_cache",
}
SKIP_FILES = {"public_scan.py"}

NEEDLES = (
    ("em dash", "\u2014"),
    ("en dash", "\u2013"),
    ("workspace path", "/workspace"),
    ("home path", "/home/"),
    ("tenant example name", "Southern Wholesale"),
)

TOKEN_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk_live_[A-Za-z0-9]+"),
    re.compile(r"sk_test_[A-Za-z0-9]+"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"hooks\.slack\.com/services/"),
)

BENJI_ALONE = re.compile(r"\bBenji\b(?!\s+Pays)")


def main() -> int:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name in SKIP_FILES:
            continue
        rel = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            failures.append(f"{rel}: not utf-8")
            continue
        for label, needle in NEEDLES:
            if needle in text:
                failures.append(f"{rel}: contains {label}")
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                failures.append(f"{rel}: contains a token-shaped string ({pattern.pattern})")
        for line_no, line in enumerate(text.splitlines(), 1):
            if BENJI_ALONE.search(line):
                failures.append(f"{rel}:{line_no}: write Benji Pays, not Benji alone")
    if failures:
        print("Public content scan failed:", file=sys.stderr)
        for item in failures:
            print(f"  {item}", file=sys.stderr)
        return 1
    print("Public content scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
