#!/usr/bin/env python3
"""Evaluate the fine-tuned ixissage Transformer classifier."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import torch
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        precision_recall_fscore_support,
    )
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding
except ImportError as exc:
    raise SystemExit(
        "Missing Transformer dependencies. Install them with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


MODEL_DIR = Path("models/smishing_classifier")
TEST_PATH = Path("data/processed/test.csv")
OUTPUTS_DIR = Path("outputs")
REPORT_PATH = OUTPUTS_DIR / "transformer_report.md"
METRICS_PATH = OUTPUTS_DIR / "transformer_metrics.json"
ERRORS_PATH = OUTPUTS_DIR / "transformer_errors.json"
CONFUSION_MATRIX_PATH = OUTPUTS_DIR / "confusion_matrix_transformer.csv"
BASELINE_METRICS_PATH = OUTPUTS_DIR / "baseline_metrics.json"
TRAIN_SUMMARY_PATH = OUTPUTS_DIR / "transformer_train_summary.json"
LABEL_TO_ID = {"normal": 0, "smishing": 1}
ID_TO_LABEL = {0: "normal", 1: "smishing"}
POSITIVE_LABEL = "smishing"
LABEL_ORDER = ["normal", "smishing"]


class SmsDataset(Dataset):
    def __init__(
        self,
        rows: list[dict[str, str]],
        tokenizer: Any,
        max_length: int,
    ) -> None:
        self.rows = rows
        self.encodings = tokenizer(
            [row["content"] for row in rows],
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        self.labels = [LABEL_TO_ID[row["label"]] for row in rows]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = {key: value[index] for key, value in self.encodings.items()}
        item["labels"] = self.labels[index]
        item["row_index"] = index
        return item


def read_split(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Split file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows


def get_device(preferred: str) -> torch.device:
    if preferred != "auto":
        return torch.device(preferred)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


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


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def predict(
    model: Any,
    dataloader: DataLoader,
    rows: list[dict[str, str]],
    device: torch.device,
) -> tuple[list[str], list[str], list[dict[str, float]]]:
    model.eval()
    y_true: list[str] = []
    y_pred: list[str] = []
    probabilities: list[dict[str, float]] = []

    with torch.no_grad():
        for batch in dataloader:
            labels = batch.pop("labels")
            row_indexes = batch.pop("row_index")
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            probs = torch.softmax(outputs.logits, dim=-1).detach().cpu()
            preds = torch.argmax(probs, dim=-1).tolist()

            for local_index, pred_id in enumerate(preds):
                row_index = int(row_indexes[local_index])
                true_label = rows[row_index]["label"]
                y_true.append(true_label)
                y_pred.append(ID_TO_LABEL[pred_id])
                probabilities.append(
                    {
                        "normal": float(probs[local_index][LABEL_TO_ID["normal"]]),
                        "smishing": float(probs[local_index][LABEL_TO_ID["smishing"]]),
                    }
                )

    return y_true, y_pred, probabilities


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


def baseline_comparison_rows(transformer_metrics: dict[str, float], baseline: dict[str, Any]) -> list[str]:
    baseline_metrics = baseline.get("metrics", {})
    rows = [
        "| metric | baseline | transformer | delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in ["accuracy", "precision", "recall", "f1"]:
        baseline_value = baseline_metrics.get(metric)
        transformer_value = transformer_metrics[metric]
        if baseline_value is None:
            rows.append(f"| {metric} | n/a | {transformer_value:.6f} | n/a |")
            continue
        delta = transformer_value - float(baseline_value)
        rows.append(
            f"| {metric} | {float(baseline_value):.6f} | {transformer_value:.6f} | {delta:+.6f} |"
        )
    return rows


def write_report(
    path: Path,
    payload: dict[str, Any],
    baseline: dict[str, Any],
    train_summary: dict[str, Any],
) -> None:
    metrics = payload["metrics"]
    matrix = payload["confusion_matrix"]
    baseline_cm = baseline.get("confusion_matrix", {})

    lines = [
        "# Transformer Report",
        "",
        "## Scope",
        "",
        "This report evaluates a Hugging Face Transformers Korean SMS classifier.",
        "",
        f"- Model: `{payload['model_name']}`",
        "- Input feature: message `content` text only",
        "- Label mapping: `normal -> 0`, `smishing -> 1`",
        "- No rule-based smishing detection",
        "- No keyword if-statements",
        "- No handcrafted URL or risk features",
        "",
        "## Model Choice",
        "",
        "`monologg/koelectra-small-v3-discriminator` is selected over `distilbert/distilbert-base-multilingual-cased` because it is Korean-specific and smaller in key config dimensions, which is more practical for course-project fine-tuning and Android demo preparation.",
        "",
        "Android on-device inference is still not guaranteed; TFLite/LiteRT conversion remains a separate follow-up.",
        "",
        "## Training Summary",
        "",
        f"- Train split: `{train_summary.get('train_split', 'unknown')}`",
        f"- Dev split: `{train_summary.get('dev_split', 'unknown')}`",
        f"- Train rows: `{train_summary.get('train_rows', 'unknown')}`",
        f"- Dev rows: `{train_summary.get('dev_rows', 'unknown')}`",
        f"- Best epoch: `{train_summary.get('best_epoch', 'unknown')}`",
        f"- Best dev F1: `{train_summary.get('best_dev_f1', 'unknown')}`",
        f"- Max length: `{train_summary.get('max_length', 'unknown')}`",
        f"- Device: `{train_summary.get('device', 'unknown')}`",
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
        "## Baseline Comparison",
        "",
        "\n".join(baseline_comparison_rows(metrics, baseline)),
        "",
        "Baseline is TF-IDF + Logistic Regression from `outputs/baseline_report.md`.",
        "",
        "## Transformer Confusion Matrix",
        "",
        "| actual \\ predicted | normal | smishing |",
        "| --- | ---: | ---: |",
        f"| normal | {matrix['normal']['normal']} | {matrix['normal']['smishing']} |",
        f"| smishing | {matrix['smishing']['normal']} | {matrix['smishing']['smishing']} |",
        "",
        "## Baseline Confusion Matrix",
        "",
        "| actual \\ predicted | normal | smishing |",
        "| --- | ---: | ---: |",
        f"| normal | {baseline_cm.get('normal', {}).get('normal', 'n/a')} | {baseline_cm.get('normal', {}).get('smishing', 'n/a')} |",
        f"| smishing | {baseline_cm.get('smishing', {}).get('normal', 'n/a')} | {baseline_cm.get('smishing', {}).get('smishing', 'n/a')} |",
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
        f"- Model directory: `{payload['model_dir']}`",
        f"- Evaluated split: `{payload['split_path']}`",
        f"- Metrics JSON: `{payload['metrics_path']}`",
        f"- Error examples JSON: `{payload['errors_path']}`",
        f"- Confusion matrix CSV: `{payload['confusion_matrix_path']}`",
        "",
        "## Notes",
        "",
        "This model is an educational demo classifier, not a production security product.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned Transformer classifier.")
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--split", type=Path, default=TEST_PATH)
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--baseline-metrics", type=Path, default=BASELINE_METRICS_PATH)
    parser.add_argument("--train-summary", type=Path, default=TRAIN_SUMMARY_PATH)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--error-limit", type=int, default=10)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.model_dir.exists():
        raise FileNotFoundError(
            f"Model directory not found: {args.model_dir}. Run scripts/train_transformer.py first."
        )

    device = get_device(args.device)
    rows = read_split(args.split)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_dir)
    model.to(device)

    dataset = SmsDataset(rows, tokenizer, args.max_length)
    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=DataCollatorWithPadding(tokenizer=tokenizer),
    )

    y_true, y_pred, probabilities = predict(model, dataloader, rows, device)
    metrics = compute_metrics(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER).tolist()

    all_fp_examples = error_examples(rows, y_pred, probabilities, "fp", len(rows))
    all_fn_examples = error_examples(rows, y_pred, probabilities, "fn", len(rows))
    fp_examples = all_fp_examples[: args.error_limit]
    fn_examples = all_fn_examples[: args.error_limit]

    metrics_path = args.outputs_dir / "transformer_metrics.json"
    errors_path = args.outputs_dir / "transformer_errors.json"
    confusion_matrix_path = args.outputs_dir / "confusion_matrix_transformer.csv"
    report_path = args.outputs_dir / "transformer_report.md"
    baseline = load_optional_json(args.baseline_metrics)
    train_summary = load_optional_json(args.train_summary)
    model_name = train_summary.get("model_name", str(args.model_dir))

    payload = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": model_name,
        "model_dir": str(args.model_dir),
        "split_path": str(args.split),
        "metrics_path": str(metrics_path),
        "errors_path": str(errors_path),
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
            "No handcrafted URL or risk features are used.",
        ],
    }
    errors_payload = {
        "false_positive_total": len(all_fp_examples),
        "false_negative_total": len(all_fn_examples),
        "false_positive_examples": all_fp_examples,
        "false_negative_examples": all_fn_examples,
    }

    write_json(metrics_path, payload)
    write_json(errors_path, errors_payload)
    write_confusion_matrix_csv(confusion_matrix_path, cm)
    write_report(report_path, payload, baseline, train_summary)

    print("Transformer evaluation complete.")
    print(f"Model: {args.model_dir}")
    print(f"Split: {args.split} ({len(rows)} rows)")
    print(f"Device: {device}")
    print(f"Metrics: {metrics}")
    print("Confusion matrix:")
    print(f"  actual normal   -> predicted normal={cm[0][0]}, smishing={cm[0][1]}")
    print(f"  actual smishing -> predicted normal={cm[1][0]}, smishing={cm[1][1]}")
    print(f"False positives: {len(all_fp_examples)}")
    print(f"False negatives: {len(all_fn_examples)}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()

