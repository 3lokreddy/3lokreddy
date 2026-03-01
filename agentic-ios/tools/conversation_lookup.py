#!/usr/bin/env python3
"""Lookup utility for agent voice transcripts.

Supports filtering by speaker, tag, and free-text query.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Transcript index must be a JSON list")
    return data


def record_matches(record: dict, speaker: str | None, tag: str | None, query: str | None) -> bool:
    if speaker and record.get("speaker_agent_id") != speaker:
        return False
    if tag and tag not in record.get("tags", []):
        return False
    if query:
        haystack = " ".join(
            [
                str(record.get("text", "")),
                " ".join(record.get("tags", [])),
                " ".join(record.get("linked_items", [])),
            ]
        ).lower()
        if query.lower() not in haystack:
            return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search agent transcript records")
    parser.add_argument("--input", default="agentic-ios/transcripts/sample_transcripts.json")
    parser.add_argument("--speaker", help="Filter by speaker agent ID")
    parser.add_argument("--tag", help="Filter by a transcript tag")
    parser.add_argument("--query", help="Case-insensitive text query")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_records(Path(args.input))
    matches = [r for r in records if record_matches(r, args.speaker, args.tag, args.query)]

    if not matches:
        print("No matches found.")
        return

    for item in matches:
        print(
            f"[{item.get('timestamp_utc')}] {item.get('speaker_agent_id')}: {item.get('text')}"
        )


if __name__ == "__main__":
    main()
