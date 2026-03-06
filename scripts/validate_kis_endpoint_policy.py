#!/usr/bin/env python3
"""Validate KIS endpoint wrappers to prevent absolute URL regressions.

Policy:
- API wrapper modules must pass relative paths (e.g. "/uapi/...") to KISRestClient.make_request.
- Absolute URL literals in `_BASE_URL`/`path` assignments are disallowed for wrapper modules.

This guardrail prevents mock/real mode drift caused by hardcoded REST domains in endpoint wrappers.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ABSOLUTE_PATH_ASSIGNMENT = re.compile(
    r'^\s*path\s*=\s*(?:[fr]{0,2})["\']https?://',
    re.MULTILINE,
)
ABSOLUTE_BASE_URL_ASSIGNMENT = re.compile(
    r'^\s*_BASE_URL\s*=\s*["\']https?://',
    re.MULTILINE,
)


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    message: str


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _scan_file(path: Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    violations: list[Violation] = []

    for match in ABSOLUTE_BASE_URL_ASSIGNMENT.finditer(source):
        violations.append(
            Violation(
                file=path,
                line=_line_number(source, match.start()),
                message="absolute `_BASE_URL` assignment is forbidden",
            )
        )

    for match in ABSOLUTE_PATH_ASSIGNMENT.finditer(source):
        violations.append(
            Violation(
                file=path,
                line=_line_number(source, match.start()),
                message="absolute endpoint URL in `path` assignment is forbidden",
            )
        )

    return violations


def _iter_target_files(apis_root: Path) -> list[Path]:
    if not apis_root.exists():
        return []

    files: list[Path] = []
    for file in sorted(apis_root.rglob("*.py")):
        relative_parts = file.relative_to(apis_root).parts
        if "oauth" in relative_parts:
            continue
        files.append(file)
    return files


def validate_endpoint_policy(apis_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for file in _iter_target_files(apis_root):
        violations.extend(_scan_file(file))
    return violations


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: inferred from this script location).",
    )
    parser.add_argument(
        "--apis-dir",
        default="stock_manager/adapters/broker/kis/apis",
        help="Path to KIS API wrapper directory, relative to --root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    apis_root = (args.root / args.apis_dir).resolve()

    files = _iter_target_files(apis_root)
    if not files:
        print(f"[endpoint-policy] No wrapper files found under: {apis_root}")
        return 1

    violations = validate_endpoint_policy(apis_root)
    if violations:
        print("[endpoint-policy] Found policy violations:")
        for violation in violations:
            print(f"- {violation.file}:{violation.line}: {violation.message}")
        return 1

    print(f"[endpoint-policy] OK - scanned {len(files)} files under {apis_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
