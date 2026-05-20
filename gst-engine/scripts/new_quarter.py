#!/usr/bin/env python3
"""
Scaffold a new GST rules quarter.

Usage:
    python scripts/new_quarter.py 2025-Q2
    python scripts/new_quarter.py 2025 Q2      # same thing

Creates rules/YYYY-QN/ by copying the previous quarter's JSON files,
updating the _effective date in each file to the new quarter's start date.
Run `pytest tests/` after to verify the new bundle loads correctly.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

RULES_ROOT = Path(__file__).parent.parent / "rules"
QUARTER_MONTHS = {1: 1, 2: 4, 3: 7, 4: 10}
JSON_FILES = ["rates.json", "thresholds.json", "states.json", "blocked.json", "rcm.json"]


def parse_quarter(arg: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})[- _]?Q([1-4])", arg, re.IGNORECASE)
    if not m:
        raise SystemExit(f"Bad quarter format: {arg!r}  (expected e.g. 2025-Q2)")
    return int(m.group(1)), int(m.group(2))


def quarter_start(year: int, q: int) -> date:
    return date(year, QUARTER_MONTHS[q], 1)


def prev_quarter(year: int, q: int) -> tuple[int, int]:
    if q == 1:
        return year - 1, 4
    return year, q - 1


def find_source_folder(year: int, q: int) -> Path:
    """Walk back up to 8 quarters to find the most recent existing folder."""
    y, qu = year, q
    for _ in range(8):
        y, qu = prev_quarter(y, qu)
        folder = RULES_ROOT / f"{y}-Q{qu}"
        if folder.is_dir():
            return folder
    raise SystemExit("No existing rules folder found to copy from.")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)

    raw = " ".join(args)
    year, q = parse_quarter(raw)
    new_name = f"{year}-Q{q}"
    new_dir = RULES_ROOT / new_name

    if new_dir.exists():
        raise SystemExit(f"Already exists: {new_dir}")

    src = find_source_folder(year, q)
    effective = quarter_start(year, q).isoformat()

    print(f"Source : {src.name}")
    print(f"Target : {new_name}  (effective {effective})")

    new_dir.mkdir()
    (new_dir / "__init__.py").touch()

    for fname in JSON_FILES:
        src_file = src / fname
        if not src_file.exists():
            print(f"  WARNING: {fname} not found in source — skipping")
            continue
        data = json.loads(src_file.read_text())
        if "_effective" in data:
            data["_effective"] = effective
        dst_file = new_dir / fname
        dst_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"  wrote {fname}")

    print()
    print("Next steps:")
    print(f"  1. Edit rules/{new_name}/*.json — update any changed rates, thresholds, or RCM entries")
    print(f"  2. Run: cd gst-engine && pytest tests/ -v")
    print(f"  3. Commit: git add gst-engine/rules/{new_name} && git commit -m 'rules: add {new_name}'")


if __name__ == "__main__":
    main()
