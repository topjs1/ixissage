#!/usr/bin/env python3
"""Export the TF-IDF + Logistic Regression baseline for Android inference.

The exported artifact contains learned TF-IDF statistics and classifier
weights. It is not a keyword rule list: Android uses the same model math as
the Python baseline to produce probabilities from message text.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from joblib import load
except ImportError as exc:
    raise SystemExit(
        "Missing export dependency. Install it with: python3 -m pip install -r requirements.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "baseline_tfidf_logreg.joblib"
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "android"
    / "IxissageApp"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "baseline_tfidf_logreg.json"
)
DEFAULT_TEST_TEXTS = [
    "오늘 저녁에 회의 끝나고 집에 갈게.",
    "[국외발신] 고객님 계정이 해외 IP에서 로그인되었습니다. 본인 확인을 진행해 주세요.",
    "ㅎㅇㅎㅇㅎㅇ 잘지내냐?",
]
WHITESPACE_PATTERN = re.compile(r"\s\s+")


def load_pipeline(path: Path) -> tuple[Any, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Baseline model not found: {path}. Run scripts/train_baseline.py first."
        )

    payload = load(path)
    pipeline = payload["pipeline"] if isinstance(payload, dict) else payload
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    return pipeline, metadata


def export_payload(pipeline: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["logreg"]

    classes = [str(label) for label in classifier.classes_.tolist()]
    if classes != ["normal", "smishing"]:
        raise ValueError(f"Expected classes ['normal', 'smishing'], got {classes}")
    if classifier.coef_.shape[0] != 1:
        raise ValueError(f"Expected binary logistic regression, got coef shape {classifier.coef_.shape}")

    feature_names = vectorizer.get_feature_names_out()
    idf_values = vectorizer.idf_
    coefficients = classifier.coef_[0]

    features = [
        {
            "term": str(term),
            "idf": round(float(idf_values[index]), 8),
            "coef": round(float(coefficients[index]), 8),
        }
        for index, term in enumerate(feature_names)
    ]

    return {
        "formatVersion": 1,
        "modelType": "tfidf_logistic_regression",
        "sourceModel": "models/baseline_tfidf_logreg.joblib",
        "labels": classes,
        "positiveLabel": "smishing",
        "vectorizer": {
            "analyzer": vectorizer.analyzer,
            "ngramRange": list(vectorizer.ngram_range),
            "lowercase": bool(vectorizer.lowercase),
            "stripAccents": vectorizer.strip_accents,
            "norm": vectorizer.norm,
            "useIdf": bool(vectorizer.use_idf),
            "smoothIdf": bool(vectorizer.smooth_idf),
            "sublinearTf": bool(vectorizer.sublinear_tf),
            "featureCount": len(features),
            "sklearnWhitespacePattern": r"\s\s+",
        },
        "classifier": {
            "type": "LogisticRegression",
            "classes": classes,
            "intercept": round(float(classifier.intercept_[0]), 8),
        },
        "features": features,
        "trainingMetadata": metadata,
        "policyNotes": [
            "Android on-device baseline inference uses learned TF-IDF statistics and logistic regression weights.",
            "No keyword if-statements are used for risk decisions.",
            "No URL presence rule or handcrafted risk feature is used.",
            "Message text is transformed by the trained vectorizer, then scored by the trained classifier.",
        ],
    }


def preprocess(text: str, lowercase: bool) -> str:
    processed = text.lower() if lowercase else text
    return WHITESPACE_PATTERN.sub(" ", processed)


def exported_predict(payload: dict[str, Any], text: str) -> dict[str, float | str]:
    vectorizer = payload["vectorizer"]
    min_n, max_n = vectorizer["ngramRange"]
    processed = preprocess(text, lowercase=vectorizer["lowercase"])
    vocabulary = {feature["term"]: index for index, feature in enumerate(payload["features"])}
    idf_values = [float(feature["idf"]) for feature in payload["features"]]
    coefficients = [float(feature["coef"]) for feature in payload["features"]]

    counts: Counter[int] = Counter()
    text_length = len(processed)
    for n in range(min_n, min(max_n, text_length) + 1):
        for start in range(0, text_length - n + 1):
            term = processed[start : start + n]
            feature_index = vocabulary.get(term)
            if feature_index is not None:
                counts[feature_index] += 1

    values: dict[int, float] = {}
    norm_squared = 0.0
    for feature_index, count in counts.items():
        tf = math.log(count) + 1.0 if vectorizer["sublinearTf"] else float(count)
        value = tf * idf_values[feature_index]
        values[feature_index] = value
        norm_squared += value * value

    norm = math.sqrt(norm_squared)
    decision = float(payload["classifier"]["intercept"])
    if norm > 0.0:
        for feature_index, value in values.items():
            decision += (value / norm) * coefficients[feature_index]

    smishing_probability = 1.0 / (1.0 + math.exp(-decision))
    normal_probability = 1.0 - smishing_probability
    return {
        "predictedLabel": "smishing" if smishing_probability >= normal_probability else "normal",
        "normalProbability": normal_probability,
        "phishingProbability": smishing_probability,
    }


def verify_export(pipeline: Any, payload: dict[str, Any], texts: list[str]) -> None:
    max_delta = 0.0
    for text in texts:
        python_probs = pipeline.predict_proba([text])[0]
        exported = exported_predict(payload, text)
        normal_delta = abs(float(python_probs[0]) - float(exported["normalProbability"]))
        smishing_delta = abs(float(python_probs[1]) - float(exported["phishingProbability"]))
        max_delta = max(max_delta, normal_delta, smishing_delta)
        print(
            "verify",
            {
                "text": text[:40],
                "python": [round(float(python_probs[0]), 6), round(float(python_probs[1]), 6)],
                "exported": [
                    round(float(exported["normalProbability"]), 6),
                    round(float(exported["phishingProbability"]), 6),
                ],
            },
        )

    if max_delta > 1e-5:
        raise ValueError(f"Export verification failed: max probability delta {max_delta}")
    print(f"Export verification passed. max_delta={max_delta:.8f}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export baseline TF-IDF + Logistic Regression model to Android JSON asset."
    )
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--skip-verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline, metadata = load_pipeline(args.model_path)
    payload = export_payload(pipeline, metadata)
    if not args.skip_verify:
        verify_export(pipeline, payload, DEFAULT_TEST_TEXTS)
    write_json(args.output, payload)
    print(f"Exported Android baseline model: {args.output}")
    print(f"Feature count: {payload['vectorizer']['featureCount']}")
    print("Policy: exported artifact is a learned ML model, not a rule-based detector.")


if __name__ == "__main__":
    main()
