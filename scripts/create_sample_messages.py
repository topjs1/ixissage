#!/usr/bin/env python3
"""Create sanitized Android demo sample messages with model probabilities.

This script samples from the test split, sanitizes display text, then runs the
fine-tuned model on the sanitized text. Sanitization is only for privacy and
sample safety; it is not used as a risk rule.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference import DEFAULT_MODEL_DIR, SmishingClassifier  # noqa: E402


TEST_SPLIT = PROJECT_ROOT / "data" / "processed" / "test.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "sample_messages.json"
LABELS = ("normal", "smishing")


URL_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s]+|"
    r"\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\."
    r"(?:com|net|org|kr|co\.kr|go\.kr|or\.kr|ne\.kr|io|me|ly|live|site|xyz)\b[^\s]*"
)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}\b")
IP_PATTERN = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
DOMAIN_LIKE_PATTERN = re.compile(
    r"(?i)[^\s]{0,40}(?:"
    r"\.\s*(?:com|net|org|kr|co\.kr|go\.kr|or\.kr|ne\.kr|io|me|ly|live|site|xyz)\w*"
    r"|(?:쩜|점)\s*컴"
    r"|닷\s*컴"
    r")[^\s]{0,20}"
)
LONG_NUMBER_PATTERN = re.compile(r"\d{4,}")
NAME_CUSTOMER_PATTERN = re.compile(r"(?<![가-힣])([가-힣]{2,4})(\s*고객님)")
NAME_TITLE_PATTERN = re.compile(
    r"(?<![가-힣])([가-힣]{1,4})(대리|과장|팀장|부장|실장|님)(?![가-힣])"
)
ADDRESS_PATTERN = re.compile(
    r"([가-힣]{2,}(?:시|도)\s*[가-힣0-9\s-]{0,30}(?:구|군|시)\s*"
    r"[가-힣0-9\s-]{0,40}(?:로|길)\s*\d*)"
)
WHITESPACE_PATTERN = re.compile(r"\s+")


def read_split(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Test split not found: {path}. Run scripts/train_baseline.py first."
        )
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def sanitize_body(text: str) -> str:
    """Remove sample-unsafe values without producing a risk score."""
    sanitized = EMAIL_PATTERN.sub("user@example.com", text)
    sanitized = URL_PATTERN.sub("https://example.com", sanitized)
    sanitized = DOMAIN_LIKE_PATTERN.sub("https://example.com", sanitized)
    sanitized = PHONE_PATTERN.sub("010-****-****", sanitized)
    sanitized = IP_PATTERN.sub("<IP_ADDRESS>", sanitized)
    sanitized = ADDRESS_PATTERN.sub("<ADDRESS>", sanitized)
    sanitized = NAME_CUSTOMER_PATTERN.sub("<NAME>\\2", sanitized)
    sanitized = NAME_TITLE_PATTERN.sub("<NAME>\\2", sanitized)
    sanitized = LONG_NUMBER_PATTERN.sub("<NUM>", sanitized)
    sanitized = WHITESPACE_PATTERN.sub(" ", sanitized).strip()
    return sanitized


def choose_samples(
    rows: list[dict[str, str]],
    per_label: int,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    selected: list[dict[str, str]] = []

    for label in LABELS:
        label_rows = [row for row in rows if row.get("label") == label]
        if len(label_rows) < per_label:
            raise ValueError(f"Not enough {label} rows: requested {per_label}, found {len(label_rows)}")
        selected.extend(rng.sample(label_rows, per_label))

    rng.shuffle(selected)
    return selected


def sender_for(index: int, ground_truth_label: str) -> str:
    prefix = "NORMAL" if ground_truth_label == "normal" else "SMISH"
    return f"IXISSAGE-{prefix}-{index:03d}"


def build_sample_messages(
    rows: list[dict[str, str]],
    classifier: SmishingClassifier,
) -> list[dict[str, Any]]:
    messages = []
    for index, row in enumerate(rows, start=1):
        body = sanitize_body(row["content"])
        prediction = classifier.predict(body)
        messages.append(
            {
                "id": f"sample-{index:03d}",
                "sender": sender_for(index, row["label"]),
                "body": body,
                "groundTruthLabel": row["label"],
                "predictedLabel": prediction["predictedLabel"],
                "normalProbability": round(float(prediction["normalProbability"]), 6),
                "phishingProbability": round(float(prediction["phishingProbability"]), 6),
            }
        )
    return messages


def write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create sanitized Android demo sample_messages.json."
    )
    parser.add_argument("--test-split", type=Path, default=TEST_SPLIT)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--per-label", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    parser.add_argument("--max-length", type=int, default=192)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_split(args.test_split)
    selected_rows = choose_samples(rows, per_label=args.per_label, seed=args.seed)
    classifier = SmishingClassifier(
        model_dir=args.model_dir,
        device=args.device,
        max_length=args.max_length,
    )
    messages = build_sample_messages(selected_rows, classifier)
    write_json(args.output, messages)

    label_counts = {label: sum(1 for item in messages if item["groundTruthLabel"] == label) for label in LABELS}
    prediction_counts = {label: sum(1 for item in messages if item["predictedLabel"] == label) for label in LABELS}
    print(f"Wrote {len(messages)} sample messages: {args.output}")
    print(f"Ground truth counts: {label_counts}")
    print(f"Prediction counts: {prediction_counts}")
    print("Policy: probabilities are model inference results; no rule-based risk judgment.")


if __name__ == "__main__":
    main()
