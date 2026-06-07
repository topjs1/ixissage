#!/usr/bin/env python3
"""Train the first ixissage baseline model.

Baseline:
- TF-IDF over message text only
- Logistic Regression binary classifier
- label 1 -> normal
- label 2 -> smishing

This script intentionally does not create keyword rules or manual URL features.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from joblib import dump
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
except ImportError as exc:
    raise SystemExit(
        "Missing baseline dependencies. Install them with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ixissage_ml.text_normalization import (  # noqa: E402
    NORMALIZATION_METADATA,
    normalize_for_intent_model,
)


RAW_DATA_PATH = Path("data/raw/lgaidataset.csv")
PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models")
OUTPUTS_DIR = Path("outputs")
MODEL_PATH = MODELS_DIR / "baseline_tfidf_logreg.joblib"
TRAIN_PATH = PROCESSED_DIR / "train.csv"
DEV_PATH = PROCESSED_DIR / "dev.csv"
TEST_PATH = PROCESSED_DIR / "test.csv"
SPLIT_METADATA_PATH = PROCESSED_DIR / "baseline_split_metadata.json"
TRAIN_SUMMARY_PATH = OUTPUTS_DIR / "baseline_train_summary.json"
LABEL_MAP = {"1": "normal", "2": "smishing"}
POSITIVE_LABEL = "smishing"
CSV_FIELDS = ["sample_id", "original_index", "content", "original_class", "label", "split"]


def normalize_column_name(name: str) -> str:
    return (name or "").replace("\ufeff", "").strip()


def load_binary_records(path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {path}. Run scripts/download_dataset.py first."
        )

    raw_class_counts: Counter[str] = Counter()
    content_to_record: dict[str, dict[str, str]] = {}
    duplicate_same_label = 0
    conflicting_contents: set[str] = set()
    empty_content_rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")

        reader.fieldnames = [normalize_column_name(field) for field in reader.fieldnames]

        for row in reader:
            row = {normalize_column_name(key): value for key, value in row.items()}
            raw_class = str(row.get("class", "")).strip()
            raw_class_counts[raw_class] += 1

            if raw_class not in LABEL_MAP:
                continue

            content = (row.get("content") or "").strip()
            if not content:
                empty_content_rows += 1
                continue

            label = LABEL_MAP[raw_class]
            existing = content_to_record.get(content)
            if existing is None:
                content_to_record[content] = {
                    "original_index": str(row.get("index", "")).strip(),
                    "content": content,
                    "original_class": raw_class,
                    "label": label,
                }
                continue

            if existing["label"] == label:
                duplicate_same_label += 1
            else:
                conflicting_contents.add(content)

    for content in conflicting_contents:
        content_to_record.pop(content, None)

    records = list(content_to_record.values())
    for index, record in enumerate(records, start=1):
        record["sample_id"] = f"baseline-{index:06d}"

    stats = {
        "raw_class_counts": dict(sorted(raw_class_counts.items())),
        "binary_rows_before_dedup": sum(raw_class_counts[label] for label in LABEL_MAP),
        "excluded_class_3_rows": raw_class_counts.get("3", 0),
        "empty_content_rows_removed": empty_content_rows,
        "duplicate_same_label_rows_removed": duplicate_same_label,
        "conflicting_duplicate_contents_removed": len(conflicting_contents),
        "binary_rows_after_dedup": len(records),
        "label_counts_after_dedup": dict(Counter(record["label"] for record in records)),
        "policy": {
            "input_feature": "content only",
            "label_mapping": LABEL_MAP,
            "excluded_labels": {"3": "not used in first binary baseline"},
            "manual_keyword_rules": False,
            "manual_url_features": False,
        },
    }
    return records, stats


def split_records(
    records: list[dict[str, str]], seed: int
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    labels = [record["label"] for record in records]
    train_records, temp_records = train_test_split(
        records,
        test_size=0.30,
        random_state=seed,
        stratify=labels,
    )
    temp_labels = [record["label"] for record in temp_records]
    dev_records, test_records = train_test_split(
        temp_records,
        test_size=0.50,
        random_state=seed,
        stratify=temp_labels,
    )
    return train_records, dev_records, test_records


def write_split(path: Path, records: list[dict[str, str]], split_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "sample_id": record["sample_id"],
                    "original_index": record["original_index"],
                    "content": record["content"],
                    "original_class": record["original_class"],
                    "label": record["label"],
                    "split": split_name,
                }
            )


def read_split(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def label_counts(records: list[dict[str, str]]) -> dict[str, int]:
    return dict(Counter(record["label"] for record in records))


def compute_binary_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        pos_label=POSITIVE_LABEL,
        zero_division=0,
    )
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 6),
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(f1), 6),
    }


def train_model(train_records: list[dict[str, str]], seed: int) -> Pipeline:
    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(2, 5),
                    min_df=2,
                    max_features=100_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "logreg",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )
    pipeline.fit(
        [normalize_for_intent_model(record["content"]) for record in train_records],
        [record["label"] for record in train_records],
    )
    return pipeline


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train TF-IDF + Logistic Regression baseline for ixissage."
    )
    parser.add_argument("--raw-data", type=Path, default=RAW_DATA_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    processed_dir = args.processed_dir
    train_path = processed_dir / "train.csv"
    dev_path = processed_dir / "dev.csv"
    test_path = processed_dir / "test.csv"
    split_metadata_path = processed_dir / "baseline_split_metadata.json"
    train_summary_path = args.outputs_dir / "baseline_train_summary.json"

    records, data_stats = load_binary_records(args.raw_data)
    train_records, dev_records, test_records = split_records(records, seed=args.seed)

    write_split(train_path, train_records, "train")
    write_split(dev_path, dev_records, "dev")
    write_split(test_path, test_records, "test")

    pipeline = train_model(train_records, seed=args.seed)
    dev_predictions = pipeline.predict(
        [normalize_for_intent_model(record["content"]) for record in dev_records]
    ).tolist()
    dev_metrics = compute_binary_metrics(
        [record["label"] for record in dev_records],
        dev_predictions,
    )

    model_metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": "tfidf_logistic_regression_baseline",
        "model_path": str(args.model_path),
        "raw_data_path": str(args.raw_data),
        "splits": {
            "train": str(train_path),
            "dev": str(dev_path),
            "test": str(test_path),
        },
        "split_counts": {
            "train": len(train_records),
            "dev": len(dev_records),
            "test": len(test_records),
        },
        "split_label_counts": {
            "train": label_counts(train_records),
            "dev": label_counts(dev_records),
            "test": label_counts(test_records),
        },
        "data_stats": data_stats,
        "vectorizer": {
            "type": "TfidfVectorizer",
            "input": "content text only after uniform URL-surface neutralization",
            "analyzer": "char",
            "ngram_range": [2, 5],
            "min_df": 2,
            "max_features": 100000,
            "sublinear_tf": True,
        },
        "text_normalization": NORMALIZATION_METADATA,
        "classifier": {
            "type": "LogisticRegression",
            "class_weight": "balanced",
            "solver": "liblinear",
            "max_iter": 1000,
        },
        "dev_metrics": dev_metrics,
        "policy_notes": [
            "No rule-based smishing detection.",
            "No keyword if-statements.",
            "No manual URL or handcrafted risk features.",
            "URL-like spans are stripped before vectorization so URL syntax alone is not treated as risk.",
            "Only the content text is transformed by TF-IDF.",
        ],
    }

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    dump({"pipeline": pipeline, "metadata": model_metadata}, args.model_path)
    write_json(split_metadata_path, model_metadata)
    write_json(train_summary_path, model_metadata)

    print("Baseline training complete.")
    print(f"Train split: {train_path} ({len(train_records)} rows)")
    print(f"Dev split: {dev_path} ({len(dev_records)} rows)")
    print(f"Test split: {test_path} ({len(test_records)} rows)")
    print(f"Model: {args.model_path}")
    print(f"Dev metrics: {dev_metrics}")
    print("Policy: content-only TF-IDF; URL surface neutralized; no keyword rules; no manual URL risk features.")


if __name__ == "__main__":
    main()
