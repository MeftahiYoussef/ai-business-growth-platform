from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"postgres(?:ql)?://\S+", re.IGNORECASE),
    re.compile(r"redis://\S+", re.IGNORECASE),
]


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _validate_record(record: dict[str, Any]) -> dict[str, Any]:
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        raise ValueError("Each record must contain at least system, user and assistant messages")
    roles = [message.get("role") for message in messages if isinstance(message, dict)]
    if roles[:3] != ["system", "user", "assistant"]:
        raise ValueError("The first three messages must be system, user and assistant")
    assistant = messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""
    if not str(assistant).strip():
        raise ValueError("Assistant answer cannot be empty")
    serialized = json.dumps(record, ensure_ascii=False)
    if _contains_secret(serialized):
        raise ValueError("Record appears to contain a secret or credential-bearing URL")
    return record


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = _validate_record(json.loads(line))
        key = json.dumps(record["messages"], sort_keys=True, ensure_ascii=False)
        if key in seen:
            raise ValueError(f"Duplicate training example at line {line_number}")
        seen.add(key)
        records.append(record)
    return records


def write_split(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic SFT JSONL train/validation/test splits.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    args = parser.parse_args()

    records = load_jsonl(Path(args.input))
    rng = random.Random(args.seed)
    shuffled = list(records)
    rng.shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * args.test_ratio)) if len(shuffled) >= 10 else 0
    validation_count = max(1, round(len(shuffled) * args.validation_ratio)) if len(shuffled) >= 10 else 0
    test = shuffled[:test_count]
    validation = shuffled[test_count:test_count + validation_count]
    train = shuffled[test_count + validation_count:]

    output_dir = Path(args.output_dir)
    write_split(output_dir / "train.jsonl", train)
    write_split(output_dir / "validation.jsonl", validation)
    write_split(output_dir / "test.jsonl", test)
    print(json.dumps({"train": len(train), "validation": len(validation), "test": len(test)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
