#!/usr/bin/env python3
"""Fine-tune a Hugging Face Transformer for ixissage.

Chosen default model:
- monologg/koelectra-small-v3-discriminator

Policy:
- input is message content text only
- no rule-based smishing detection
- no keyword if-statements
- no handcrafted URL or risk features
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import torch
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        get_linear_schedule_with_warmup,
    )
except ImportError as exc:
    raise SystemExit(
        "Missing Transformer dependencies. Install them with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


DEFAULT_MODEL_NAME = "monologg/koelectra-small-v3-discriminator"
TRAIN_PATH = Path("data/processed/train.csv")
DEV_PATH = Path("data/processed/dev.csv")
OUTPUT_DIR = Path("models/smishing_classifier")
OUTPUTS_DIR = Path("outputs")
TRAINING_SUMMARY_PATH = OUTPUTS_DIR / "transformer_train_summary.json"
LABEL_TO_ID = {"normal": 0, "smishing": 1}
ID_TO_LABEL = {0: "normal", 1: "smishing"}
POSITIVE_LABEL = "smishing"


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
        return item


def read_split(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Split file not found: {path}. Run scripts/train_baseline.py first."
        )

    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    missing_labels = sorted({row.get("label", "") for row in rows} - set(LABEL_TO_ID))
    if missing_labels:
        raise ValueError(f"Unexpected labels in {path}: {missing_labels}")

    return rows


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device(preferred: str) -> torch.device:
    if preferred != "auto":
        return torch.device(preferred)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def label_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    return dict(Counter(row["label"] for row in rows))


def compute_metrics(y_true_ids: list[int], y_pred_ids: list[int]) -> dict[str, float]:
    y_true = [ID_TO_LABEL[label] for label in y_true_ids]
    y_pred = [ID_TO_LABEL[label] for label in y_pred_ids]
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


def evaluate_dev(
    model: Any,
    dataloader: DataLoader,
    device: torch.device,
) -> tuple[float, dict[str, float]]:
    model.eval()
    losses: list[float] = []
    y_true: list[int] = []
    y_pred: list[int] = []

    with torch.no_grad():
        for batch in dataloader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            losses.append(float(outputs.loss.detach().cpu()))
            predictions = torch.argmax(outputs.logits, dim=-1)
            y_true.extend(batch["labels"].detach().cpu().tolist())
            y_pred.extend(predictions.detach().cpu().tolist())

    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return avg_loss, compute_metrics(y_true, y_pred)


def save_training_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune a Transformer smishing classifier."
    )
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--train", type=Path, default=TRAIN_PATH)
    parser.add_argument("--dev", type=Path, default=DEV_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.epochs < 1:
        raise ValueError("--epochs must be at least 1")

    set_seed(args.seed)
    device = get_device(args.device)

    train_rows = read_split(args.train)
    dev_rows = read_split(args.dev)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2,
        id2label={str(key): value for key, value in ID_TO_LABEL.items()},
        label2id=LABEL_TO_ID,
    )
    model.to(device)

    train_dataset = SmsDataset(train_rows, tokenizer, args.max_length)
    dev_dataset = SmsDataset(dev_rows, tokenizer, args.max_length)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collator,
    )
    dev_loader = DataLoader(
        dev_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collator,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    best_dev_f1 = -1.0
    best_epoch = 0
    history: list[dict[str, Any]] = []

    print("Transformer fine-tuning started.")
    print(f"Model: {args.model_name}")
    print(f"Device: {device}")
    print(f"Train rows: {len(train_rows)} {label_counts(train_rows)}")
    print(f"Dev rows: {len(dev_rows)} {label_counts(dev_rows)}")
    print("Policy: content-only tokenizer input; no keyword rules; no handcrafted risk features.")

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses: list[float] = []

        for step, batch in enumerate(train_loader, start=1):
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            train_losses.append(float(loss.detach().cpu()))

            if step % 50 == 0 or step == len(train_loader):
                print(
                    f"epoch={epoch} step={step}/{len(train_loader)} "
                    f"train_loss={sum(train_losses) / len(train_losses):.4f}"
                )

        dev_loss, dev_metrics = evaluate_dev(model, dev_loader, device)
        epoch_summary = {
            "epoch": epoch,
            "train_loss": round(sum(train_losses) / len(train_losses), 6),
            "dev_loss": round(dev_loss, 6),
            "dev_metrics": dev_metrics,
        }
        history.append(epoch_summary)
        print(f"epoch={epoch} dev_loss={dev_loss:.4f} dev_metrics={dev_metrics}")

        if dev_metrics["f1"] > best_dev_f1:
            best_dev_f1 = dev_metrics["f1"]
            best_epoch = epoch
            args.output_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": args.model_name,
        "recommended_reason": (
            "Korean-specific small ELECTRA model selected for lower training cost "
            "and better fit to Korean SMS than multilingual DistilBERT."
        ),
        "output_dir": str(args.output_dir),
        "train_split": str(args.train),
        "dev_split": str(args.dev),
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_label_counts": label_counts(train_rows),
        "dev_label_counts": label_counts(dev_rows),
        "label_mapping": {"normal": 0, "smishing": 1},
        "max_length": args.max_length,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "warmup_ratio": args.warmup_ratio,
        "device": str(device),
        "best_epoch": best_epoch,
        "best_dev_f1": best_dev_f1,
        "history": history,
        "policy_notes": [
            "No rule-based smishing detection.",
            "No keyword if-statements.",
            "No handcrafted URL or risk features.",
            "Model input is content text only.",
        ],
    }
    summary_path = args.outputs_dir / "transformer_train_summary.json"
    save_training_summary(summary_path, summary)

    print("Transformer fine-tuning complete.")
    print(f"Best epoch: {best_epoch}")
    print(f"Best dev F1: {best_dev_f1:.6f}")
    print(f"Saved model/tokenizer: {args.output_dir}")
    print(f"Training summary: {summary_path}")


if __name__ == "__main__":
    main()

