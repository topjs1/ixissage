#!/usr/bin/env python3
"""Run single-message inference with the fine-tuned ixissage model.

The classifier uses only the input text and the model's softmax probabilities.
It does not implement keyword rules, URL rules, or handcrafted risk features.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError as exc:
    raise SystemExit(
        "Missing inference dependencies. Install them with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "smishing_classifier"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "inference_examples.md"
LABEL_NORMAL = "normal"
LABEL_SMISHING = "smishing"
EXAMPLE_MESSAGES = [
    "오늘 저녁 7시에 도서관 앞에서 만나자. 늦으면 문자할게.",
    "수업 과제 제출 확인했습니다. 다음 주 발표 준비해 주세요.",
    "엄마 나 휴대폰이 고장나서 임시로 문자하고 있어. 급하게 송금 좀 부탁해.",
    "[국외발신] 고객님 계정이 해외 IP에서 로그인되었습니다. 본인 확인을 진행해 주세요.",
    "주문하신 상품이 배송 완료되었습니다. 이용해 주셔서 감사합니다.",
]


def get_device(preferred: str) -> torch.device:
    if preferred != "auto":
        return torch.device(preferred)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def ui_badge_from_probability(phishing_probability: float) -> str:
    """Map model probability to a UI badge only; this is not text-risk logic."""
    if phishing_probability >= 0.70:
        return "스팸 경고"
    if phishing_probability >= 0.40:
        return "주의"
    return "정상"


class SmishingClassifier:
    def __init__(
        self,
        model_dir: Path = DEFAULT_MODEL_DIR,
        device: str = "auto",
        max_length: int = 192,
    ) -> None:
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Model directory not found: {model_dir}. "
                "Run scripts/train_transformer.py first."
            )

        self.model_dir = model_dir
        self.device = get_device(device)
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str, include_ui_badge: bool = False) -> dict[str, Any]:
        message = text.strip()
        if not message:
            raise ValueError("Input text must not be empty.")

        encoded = self.tokenizer(
            message,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=False,
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        with torch.no_grad():
            logits = self.model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1)[0].detach().cpu()

        normal_probability = float(probabilities[0])
        phishing_probability = float(probabilities[1])
        predicted_label = (
            LABEL_SMISHING if phishing_probability >= normal_probability else LABEL_NORMAL
        )

        result: dict[str, Any] = {
            "predictedLabel": predicted_label,
            "normalProbability": normal_probability,
            "phishingProbability": phishing_probability,
        }
        if include_ui_badge:
            result["uiBadge"] = ui_badge_from_probability(phishing_probability)
        return result


def predict_text(
    text: str,
    model_dir: Path = DEFAULT_MODEL_DIR,
    device: str = "auto",
    max_length: int = 192,
    include_ui_badge: bool = False,
) -> dict[str, Any]:
    classifier = SmishingClassifier(model_dir=model_dir, device=device, max_length=max_length)
    return classifier.predict(text, include_ui_badge=include_ui_badge)


def write_examples_markdown(
    classifier: SmishingClassifier,
    output_path: Path,
    include_ui_badge: bool,
) -> list[dict[str, Any]]:
    rows = []
    for index, text in enumerate(EXAMPLE_MESSAGES, start=1):
        prediction = classifier.predict(text, include_ui_badge=include_ui_badge)
        rows.append({"index": index, "text": text, **prediction})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Inference Examples",
        "",
        f"Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "These examples use the fine-tuned Transformer model. The model input is message text only.",
        "",
        "No rule-based detection, keyword if-statements, or handcrafted risk features are used.",
        "",
        "| # | text | predictedLabel | normalProbability | phishingProbability |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        text = str(row["text"]).replace("|", "\\|")
        lines.append(
            "| "
            f"{row['index']} | "
            f"{text} | "
            f"{row['predictedLabel']} | "
            f"{row['normalProbability']:.6f} | "
            f"{row['phishingProbability']:.6f} |"
        )

    if include_ui_badge:
        lines.extend(
            [
                "",
                "## UI Badge Mapping",
                "",
                "`uiBadge` is optional UI visualization based only on `phishingProbability`: `<0.40 정상`, `0.40-0.70 주의`, `>=0.70 스팸 경고`.",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify one Korean SMS message with the fine-tuned ixissage model."
    )
    parser.add_argument("--text", help="One message body to classify.")
    parser.add_argument("--examples", action="store_true", help="Run five built-in examples.")
    parser.add_argument(
        "--write-examples",
        action="store_true",
        help="Write built-in example results to outputs/inference_examples.md.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument(
        "--include-ui-badge",
        action="store_true",
        help="Include probability-only UI badge mapping in the output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.text and not args.examples and not args.write_examples:
        raise SystemExit("Provide --text, --examples, or --write-examples.")

    classifier = SmishingClassifier(
        model_dir=args.model_dir,
        device=args.device,
        max_length=args.max_length,
    )

    if args.text:
        print_json(classifier.predict(args.text, include_ui_badge=args.include_ui_badge))

    if args.examples or args.write_examples:
        rows = write_examples_markdown(
            classifier,
            args.output,
            include_ui_badge=args.include_ui_badge,
        )
        if args.examples:
            print_json(rows)
        print(f"Wrote examples: {args.output}")


if __name__ == "__main__":
    main()

