#!/usr/bin/env python3
"""Evaluate the TF-IDF + Logistic Regression baseline."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from joblib import load
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        precision_recall_fscore_support,
    )
except ImportError as exc:
    raise SystemExit(
        "Missing baseline dependencies. Install them with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


MODEL_PATH = Path("models/baseline_tfidf_logreg.joblib")
DEFAULT_SPLIT_PATH = Path("data/processed/test.csv")
OUTPUTS_DIR = Path("outputs")
REPORT_PATH = OUTPUTS_DIR / "baseline_report.md"
METRICS_PATH = OUTPUTS_DIR / "baseline_metrics.json"
CONFUSION_MATRIX_PATH = OUTPUTS_DIR / "confusion_matrix_baseline.csv"
POSITIVE_LABEL = "smishing"
LABEL_ORDER = ["normal", "smishing"]


def read_split(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Split file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_pipeline(path: Path) -> tuple[Any, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Model not found: {path}. Run scripts/train_baseline.py first."
        )
    artifact = load(path)
    if isinstance(artifact, dict) and "pipeline" in artifact:
        return artifact["pipeline"], artifact.get("metadata", {})
    return artifact, {}


def probabilities_by_label(pipeline: Any, texts: list[str]) -> list[dict[str, float]]:
    probabilities = pipeline.predict_proba(texts)
    classes = list(getattr(pipeline, "classes_", []))
    if not classes:
        classes = list(pipeline.named_steps["logreg"].classes_)

    result = []
    for row in probabilities:
        result.append({label: float(row[classes.index(label)]) for label in LABEL_ORDER})
    return result


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
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


def redact_for_display(text: str, limit: int = 260) -> str:
    masked = re.sub(r"\d{4,}", "<NUM>", text)
    masked = re.sub(r"\s+", " ", masked).strip()
    if len(masked) > limit:
        return masked[: limit - 3] + "..."
    return masked


def escape_markdown_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def error_examples(
    rows: list[dict[str, str]],
    predictions: list[str],
    probabilities: list[dict[str, float]],
    kind: str,
    limit: int,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for row, prediction, probability in zip(rows, predictions, probabilities):
        true_label = row["label"]
        is_false_positive = true_label == "normal" and prediction == "smishing"
        is_false_negative = true_label == "smishing" and prediction == "normal"

        if kind == "fp" and not is_false_positive:
            continue
        if kind == "fn" and not is_false_negative:
            continue

        examples.append(
            {
                "sample_id": row["sample_id"],
                "true_label": true_label,
                "predicted_label": prediction,
                "normal_probability": probability["normal"],
                "smishing_probability": probability["smishing"],
                "content": redact_for_display(row["content"]),
            }
        )

    sort_key = "smishing_probability" if kind == "fp" else "normal_probability"
    examples.sort(key=lambda item: item[sort_key], reverse=True)
    return examples[:limit]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_confusion_matrix_csv(path: Path, matrix: list[list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["actual\\predicted", "normal", "smishing"])
        writer.writerow(["normal", matrix[0][0], matrix[0][1]])
        writer.writerow(["smishing", matrix[1][0], matrix[1][1]])


def markdown_error_table(examples: list[dict[str, Any]]) -> str:
    if not examples:
        return "No examples."

    lines = [
        "| # | sample_id | true | predicted | normal_prob | smishing_prob | content |",
        "| ---: | --- | --- | --- | ---: | ---: | --- |",
    ]
    for index, example in enumerate(examples, start=1):
        lines.append(
            "| "
            f"{index} | "
            f"{escape_markdown_cell(example['sample_id'])} | "
            f"{example['true_label']} | "
            f"{example['predicted_label']} | "
            f"{example['normal_probability']:.4f} | "
            f"{example['smishing_probability']:.4f} | "
            f"{escape_markdown_cell(example['content'])} |"
        )
    return "\n".join(lines)


def write_report(
    path: Path,
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    matrix = payload["confusion_matrix"]
    metrics = payload["metrics"]
    split_counts = metadata.get("split_counts", {})
    split_label_counts = metadata.get("split_label_counts", {})
    data_stats = metadata.get("data_stats", {})

    lines = [
        "# Baseline Report",
        "",
        "## Scope",
        "",
        "This is the first ixissage baseline model: TF-IDF + Logistic Regression.",
        "",
        "- Input feature: message `content` text only",
        "- Label mapping: `class=1 -> normal`, `class=2 -> smishing`",
        "- Excluded from this first binary baseline: `class=3`",
        "- No rule-based smishing detection",
        "- No keyword if-statements",
        "- No manual URL or handcrafted risk features",
        "",
        "## Data Split",
        "",
        f"- Train rows: `{split_counts.get('train', 'unknown')}`",
        f"- Dev rows: `{split_counts.get('dev', 'unknown')}`",
        f"- Test rows: `{split_counts.get('test', 'unknown')}`",
        f"- Train label counts: `{split_label_counts.get('train', {})}`",
        f"- Dev label counts: `{split_label_counts.get('dev', {})}`",
        f"- Test label counts: `{split_label_counts.get('test', {})}`",
        f"- Binary rows before dedup: `{data_stats.get('binary_rows_before_dedup', 'unknown')}`",
        f"- Binary rows after dedup: `{data_stats.get('binary_rows_after_dedup', 'unknown')}`",
        f"- Same-label duplicate rows removed: `{data_stats.get('duplicate_same_label_rows_removed', 'unknown')}`",
        f"- Conflicting duplicate contents removed: `{data_stats.get('conflicting_duplicate_contents_removed', 'unknown')}`",
        "",
        "Exact duplicate message bodies were removed before splitting to reduce train/test leakage.",
        "",
        "## Test Metrics",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| accuracy | {metrics['accuracy']:.6f} |",
        f"| precision | {metrics['precision']:.6f} |",
        f"| recall | {metrics['recall']:.6f} |",
        f"| F1 | {metrics['f1']:.6f} |",
        "",
        "Positive class is `smishing`.",
        "",
        "## Confusion Matrix",
        "",
        "| actual \\ predicted | normal | smishing |",
        "| --- | ---: | ---: |",
        f"| normal | {matrix['normal']['normal']} | {matrix['normal']['smishing']} |",
        f"| smishing | {matrix['smishing']['normal']} | {matrix['smishing']['smishing']} |",
        "",
        "## False Positive Examples",
        "",
        "False positive means true `normal`, predicted `smishing`.",
        f"Total false positives in this split: `{payload['false_positive_total']}`. "
        f"Showing `{len(payload['false_positive_examples'])}` of up to `{payload['error_example_limit']}`.",
        "",
        markdown_error_table(payload["false_positive_examples"]),
        "",
        "## False Negative Examples",
        "",
        "False negative means true `smishing`, predicted `normal`.",
        f"Total false negatives in this split: `{payload['false_negative_total']}`. "
        f"Showing `{len(payload['false_negative_examples'])}` of up to `{payload['error_example_limit']}`.",
        "",
        markdown_error_table(payload["false_negative_examples"]),
        "",
        "## Artifacts",
        "",
        f"- Model: `{payload['model_path']}`",
        f"- Evaluated split: `{payload['split_path']}`",
        f"- Metrics JSON: `{payload['metrics_path']}`",
        f"- Confusion matrix CSV: `{payload['confusion_matrix_path']}`",
        "",
        "## Notes",
        "",
        "This baseline is useful as a reproducible reference point. It should not be treated as a production security system.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))
        file.write("\n")


def print_examples(title: str, examples: list[dict[str, Any]]) -> None:
    print(f"\n{title}")
    if not examples:
        print("No examples.")
        return

    for index, example in enumerate(examples, start=1):
        print(
            f"{index:02d}. [{example['sample_id']}] "
            f"true={example['true_label']} pred={example['predicted_label']} "
            f"normal={example['normal_probability']:.4f} "
            f"smishing={example['smishing_probability']:.4f} "
            f"{example['content']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate TF-IDF + Logistic Regression baseline."
    )
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--error-limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_split(args.split)
    pipeline, metadata = load_pipeline(args.model_path)

    texts = [row["content"] for row in rows]
    y_true = [row["label"] for row in rows]
    y_pred = pipeline.predict(texts).tolist()
    probabilities = probabilities_by_label(pipeline, texts)

    metrics = compute_metrics(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER).tolist()
    all_fp_examples = error_examples(rows, y_pred, probabilities, "fp", len(rows))
    all_fn_examples = error_examples(rows, y_pred, probabilities, "fn", len(rows))
    fp_examples = all_fp_examples[: args.error_limit]
    fn_examples = all_fn_examples[: args.error_limit]

    metrics_path = args.outputs_dir / "baseline_metrics.json"
    confusion_matrix_path = args.outputs_dir / "confusion_matrix_baseline.csv"
    report_path = args.outputs_dir / "baseline_report.md"

    payload = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_path": str(args.model_path),
        "split_path": str(args.split),
        "metrics_path": str(metrics_path),
        "confusion_matrix_path": str(confusion_matrix_path),
        "positive_label": POSITIVE_LABEL,
        "metrics": metrics,
        "confusion_matrix": {
            "normal": {"normal": cm[0][0], "smishing": cm[0][1]},
            "smishing": {"normal": cm[1][0], "smishing": cm[1][1]},
        },
        "error_example_limit": args.error_limit,
        "false_positive_total": len(all_fp_examples),
        "false_negative_total": len(all_fn_examples),
        "false_positive_examples": fp_examples,
        "false_negative_examples": fn_examples,
        "policy_notes": [
            "Model uses content text only.",
            "No keyword if-statements are used.",
            "No manual URL or handcrafted risk features are used.",
        ],
    }

    write_json(metrics_path, payload)
    write_confusion_matrix_csv(confusion_matrix_path, cm)
    write_report(report_path, payload, metadata)

    print("Baseline evaluation complete.")
    print(f"Split: {args.split} ({len(rows)} rows)")
    print(f"Metrics: {metrics}")
    print("Confusion matrix:")
    print(f"  actual normal   -> predicted normal={cm[0][0]}, smishing={cm[0][1]}")
    print(f"  actual smishing -> predicted normal={cm[1][0]}, smishing={cm[1][1]}")
    print_examples("False Positive Examples", fp_examples)
    print_examples("False Negative Examples", fn_examples)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
