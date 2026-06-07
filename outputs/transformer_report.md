# Transformer Report

## Scope

This report evaluates a Hugging Face Transformers Korean SMS classifier.

- Model: `monologg/koelectra-small-v3-discriminator`
- Input feature: message `content` text only
- Label mapping: `normal -> 0`, `smishing -> 1`
- No rule-based smishing detection
- No keyword if-statements
- No handcrafted URL or risk features

## Model Choice

`monologg/koelectra-small-v3-discriminator` is selected over `distilbert/distilbert-base-multilingual-cased` because it is Korean-specific and smaller in key config dimensions, which is more practical for course-project fine-tuning and Android demo preparation.

Android on-device inference is still not guaranteed; TFLite/LiteRT conversion remains a separate follow-up.

## Training Summary

- Train split: `data/processed/train.csv`
- Dev split: `data/processed/dev.csv`
- Train rows: `9412`
- Dev rows: `2017`
- Best epoch: `1`
- Best dev F1: `0.999565`
- Max length: `192`
- Device: `mps`

## Test Metrics

| metric | value |
| --- | ---: |
| accuracy | 0.998513 |
| precision | 0.999130 |
| recall | 0.998262 |
| F1 | 0.998696 |

Positive class is `smishing`.

## Baseline Comparison

| metric | baseline | transformer | delta |
| --- | ---: | ---: | ---: |
| accuracy | 0.992567 | 0.998513 | +0.005946 |
| precision | 0.997373 | 0.999130 | +0.001757 |
| recall | 0.989574 | 0.998262 | +0.008688 |
| f1 | 0.993458 | 0.998696 | +0.005238 |

Baseline is TF-IDF + Logistic Regression from `outputs/baseline_report.md`.

## Transformer Confusion Matrix

| actual \ predicted | normal | smishing |
| --- | ---: | ---: |
| normal | 866 | 1 |
| smishing | 2 | 1149 |

## Baseline Confusion Matrix

| actual \ predicted | normal | smishing |
| --- | ---: | ---: |
| normal | 864 | 3 |
| smishing | 12 | 1139 |

## False Positive Examples

False positive means true `normal`, predicted `smishing`.
Total false positives in this split: `1`. Showing `1` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-003802 | normal | smishing | 0.0459 | 0.9541 | 아이폰6s 사용자인데 겨울에 추우면 배터리 30% 넘게 남았는데 전원이 꺼집니다!! 구매하실분들 이 증상 너무 심각합니다!! 고객센터에서는 알면서 as도 보상도 안하고 있습니다!! 아이폰6s만 그런게 아닙니다!! |

## False Negative Examples

False negative means true `smishing`, predicted `normal`.
Total false negatives in this split: `2`. Showing `2` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-010331 | smishing | normal | 0.9661 | 0.0339 | 리일~짜앙♡늘 기뻐하고♡ ♡늘많이웃고♡ ♡늘 행복하세요♡zag⑤⑤⑦◘ℂℴℳ |
| 2 | baseline-000027 | smishing | normal | 0.9548 | 0.0452 | 응 나 뭐하나 부탁해도 돼? 지금 편의점가서 구글기프트카드 20만권 3장 사줄수있어? 수수료 벌려고 그래 |

## Artifacts

- Model directory: `models/smishing_classifier`
- Evaluated split: `data/processed/test.csv`
- Metrics JSON: `outputs/transformer_metrics.json`
- Error examples JSON: `outputs/transformer_errors.json`
- Confusion matrix CSV: `outputs/confusion_matrix_transformer.csv`

## Notes

This model is an educational demo classifier, not a production security product.
