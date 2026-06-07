#!/usr/bin/env python3
"""Inspect the Korean_message dataset before any model training."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable


DEFAULT_INPUT = Path("data/raw/lgaidataset.csv")
DEFAULT_PROCESSED_DIR = Path("data/processed")
SUMMARY_JSON = "dataset_inspection_summary.json"
SUMMARY_MD = "dataset_inspection_report.md"
REQUIRED_COLUMNS = ("index", "content", "class")
LABEL_MEANINGS = {
    "1": "일상 문자 / ordinary message",
    "2": "피싱 또는 스미싱 문자 / phishing or smishing message",
    "3": "데이터셋 카드에 의미가 명시되지 않음",
}


def normalize_column_name(name: str) -> str:
    return (name or "").replace("\ufeff", "").strip()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")

        columns = [normalize_column_name(name) for name in reader.fieldnames]
        rows = []
        for raw_row in reader:
            row = {
                normalize_column_name(key): value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    return columns, rows


def is_null(value: str | None) -> bool:
    return value is None or value.strip() == ""


def percentile(values: list[int], p: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = math.ceil((p / 100) * len(sorted_values)) - 1
    index = min(max(index, 0), len(sorted_values) - 1)
    return float(sorted_values[index])


def length_stats(lengths: list[int]) -> dict[str, float | int | None]:
    if not lengths:
        return {
            "min": None,
            "p25": None,
            "median": None,
            "mean": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "max": None,
        }

    return {
        "min": min(lengths),
        "p25": percentile(lengths, 25),
        "median": statistics.median(lengths),
        "mean": round(statistics.mean(lengths), 2),
        "p75": percentile(lengths, 75),
        "p90": percentile(lengths, 90),
        "p95": percentile(lengths, 95),
        "p99": percentile(lengths, 99),
        "max": max(lengths),
    }


def redact_for_display(text: str) -> str:
    masked = re.sub(r"\d{4,}", "<NUM>", text)
    masked = re.sub(r"\s+", " ", masked).strip()
    return masked


def collect_samples(
    rows: Iterable[dict[str, str]], label: str, limit: int, redact: bool
) -> list[dict[str, str]]:
    samples = []
    for row in rows:
        if str(row.get("class", "")).strip() != label:
            continue
        content = row.get("content", "") or ""
        if redact:
            content = redact_for_display(content)
        samples.append(
            {
                "index": str(row.get("index", "")).strip(),
                "class": label,
                "content": content,
            }
        )
        if len(samples) >= limit:
            break
    return samples


def inspect_dataset(path: Path, processed_dir: Path, sample_count: int, redact: bool) -> dict:
    columns, rows = read_rows(path)
    missing_required = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")

    total_rows = len(rows)
    null_counts = {
        column: sum(1 for row in rows if is_null(row.get(column)))
        for column in columns
    }
    label_counts = Counter(str(row.get("class", "")).strip() for row in rows)
    label_counts = {label: label_counts[label] for label in sorted(label_counts)}
    class_balance = {
        label: {
            "count": count,
            "percentage": round((count / total_rows) * 100, 2) if total_rows else 0.0,
            "meaning": LABEL_MEANINGS.get(label, "알 수 없음"),
        }
        for label, count in label_counts.items()
    }

    contents = [row.get("content", "") or "" for row in rows]
    content_lengths = [len(content) for content in contents]
    duplicate_content_count = total_rows - len(set(contents))
    duplicated_content_values = sum(
        1 for count in Counter(contents).values() if count > 1
    )
    full_row_values = [
        tuple(str(row.get(column, "")) for column in columns)
        for row in rows
    ]
    duplicate_full_row_count = total_rows - len(set(full_row_values))

    normal_samples = collect_samples(rows, "1", sample_count, redact)
    smishing_samples = collect_samples(rows, "2", sample_count, redact)
    label_3_samples = collect_samples(rows, "3", min(5, sample_count), redact)

    summary = {
        "source_file": str(path),
        "outputs": {
            "summary_json": str(processed_dir / SUMMARY_JSON),
            "summary_markdown": str(processed_dir / SUMMARY_MD),
        },
        "columns": columns,
        "required_columns_present": not missing_required,
        "total_rows": total_rows,
        "label_meanings_from_dataset_card": {
            "1": LABEL_MEANINGS["1"],
            "2": LABEL_MEANINGS["2"],
        },
        "label_3_note": LABEL_MEANINGS["3"],
        "class_balance": class_balance,
        "null_counts": null_counts,
        "duplicates": {
            "duplicate_content_rows": duplicate_content_count,
            "duplicated_content_values": duplicated_content_values,
            "duplicate_full_rows": duplicate_full_row_count,
        },
        "message_length_distribution": length_stats(content_lengths),
        "samples": {
            "normal_label_1": normal_samples,
            "smishing_label_2": smishing_samples,
            "unknown_label_3": label_3_samples,
        },
        "policy_notes": [
            "This script performs dataset inspection only.",
            "No model training is performed.",
            "No rule-based smishing detection is implemented.",
            "Keyword checks must not be used for risk decisions in ixissage.",
        ],
    }

    processed_dir.mkdir(parents=True, exist_ok=True)
    json_path = processed_dir / SUMMARY_JSON
    md_path = processed_dir / SUMMARY_MD
    write_json(summary, json_path)
    write_markdown(summary, md_path)

    return summary


def write_json(summary: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")


def markdown_table(rows: list[dict[str, str]]) -> str:
    lines = ["| index | class | content |", "| --- | --- | --- |"]
    for row in rows:
        content = row["content"].replace("|", "\\|")
        lines.append(f"| {row['index']} | {row['class']} | {content} |")
    return "\n".join(lines)


def write_markdown(summary: dict, path: Path) -> None:
    length = summary["message_length_distribution"]
    class_rows = [
        "| class | count | percentage | meaning |",
        "| --- | ---: | ---: | --- |",
    ]
    for label, info in summary["class_balance"].items():
        class_rows.append(
            f"| {label} | {info['count']} | {info['percentage']}% | {info['meaning']} |"
        )

    lines = [
        "# Dataset Inspection Report",
        "",
        "This report is generated before model training. It does not implement rule-based smishing detection.",
        "",
        "## Source",
        "",
        f"- File: `{summary['source_file']}`",
        "- Dataset: `meal-bbang/Korean_message`",
        "- Raw data must not be overwritten.",
        "",
        "## Columns",
        "",
        ", ".join(f"`{column}`" for column in summary["columns"]),
        "",
        "## Row Count",
        "",
        f"- Total rows: `{summary['total_rows']}`",
        "",
        "## Label Meanings",
        "",
        "- `1`: 일상 문자 / ordinary message",
        "- `2`: 피싱 또는 스미싱 문자 / phishing or smishing message",
        "- `3`: 데이터셋 카드에 의미가 명시되지 않음",
        "",
        "## Class Balance",
        "",
        "\n".join(class_rows),
        "",
        "## Null Counts",
        "",
        *(f"- `{column}`: {count}" for column, count in summary["null_counts"].items()),
        "",
        "## Duplicates",
        "",
        f"- Duplicate content rows: `{summary['duplicates']['duplicate_content_rows']}`",
        f"- Duplicated content values: `{summary['duplicates']['duplicated_content_values']}`",
        f"- Duplicate full rows: `{summary['duplicates']['duplicate_full_rows']}`",
        "",
        "## Message Length Distribution",
        "",
        f"- min: `{length['min']}`",
        f"- p25: `{length['p25']}`",
        f"- median: `{length['median']}`",
        f"- mean: `{length['mean']}`",
        f"- p75: `{length['p75']}`",
        f"- p90: `{length['p90']}`",
        f"- p95: `{length['p95']}`",
        f"- p99: `{length['p99']}`",
        f"- max: `{length['max']}`",
        "",
        "## Sample Normal Messages: label 1",
        "",
        markdown_table(summary["samples"]["normal_label_1"]),
        "",
        "## Sample Smishing Messages: label 2",
        "",
        markdown_table(summary["samples"]["smishing_label_2"]),
        "",
        "## Sample label 3 Messages",
        "",
        markdown_table(summary["samples"]["unknown_label_3"]),
        "",
        "## Policy Notes",
        "",
        "- This project must use AI model probabilities for risk decisions.",
        "- Do not add keyword if-statements for smishing detection.",
        "- Dataset inspection may describe text patterns, but those patterns must not become Android or inference rules.",
    ]

    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))
        file.write("\n")


def print_samples(title: str, rows: list[dict[str, str]]) -> None:
    print(f"\n{title}")
    for number, row in enumerate(rows, start=1):
        print(f"{number:02d}. [index={row['index']}, class={row['class']}] {row['content']}")


def print_summary(summary: dict) -> None:
    print("\n=== Dataset Summary ===")
    print(f"Source file: {summary['source_file']}")
    print(f"Columns: {', '.join(summary['columns'])}")
    print(f"Total rows: {summary['total_rows']}")

    print("\n=== Label Meanings ===")
    print("1: 일상 문자 / ordinary message")
    print("2: 피싱 또는 스미싱 문자 / phishing or smishing message")
    print("3: 데이터셋 카드에 의미가 명시되지 않음")

    print("\n=== Class Balance ===")
    for label, info in summary["class_balance"].items():
        print(f"class {label}: {info['count']} ({info['percentage']}%) - {info['meaning']}")

    print("\n=== Null Counts ===")
    for column, count in summary["null_counts"].items():
        print(f"{column}: {count}")

    print("\n=== Duplicates ===")
    for key, value in summary["duplicates"].items():
        print(f"{key}: {value}")

    print("\n=== Message Length Distribution ===")
    for key, value in summary["message_length_distribution"].items():
        print(f"{key}: {value}")

    print_samples("=== Sample Normal Messages: label 1 ===", summary["samples"]["normal_label_1"])
    print_samples("=== Sample Smishing Messages: label 2 ===", summary["samples"]["smishing_label_2"])
    print_samples("=== Sample label 3 Messages ===", summary["samples"]["unknown_label_3"])

    print(f"\nWrote: {summary['outputs']['summary_json']}")
    print(f"Wrote: {summary['outputs']['summary_markdown']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect meal-bbang/Korean_message before training."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Raw CSV path.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Directory for inspection outputs.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of normal and smishing samples to print.",
    )
    parser.add_argument(
        "--no-redact-samples",
        action="store_true",
        help="Print full sample text instead of masking long digit sequences.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = inspect_dataset(
        path=args.input,
        processed_dir=args.processed_dir,
        sample_count=args.samples,
        redact=not args.no_redact_samples,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
