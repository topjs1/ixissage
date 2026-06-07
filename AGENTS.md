# AGENTS.md

## Project Identity

This repository is for `ixissage`, an educational AI course project.

ixissage is inspired by AI security features in telecom apps such as ixi-O, but this project is not intended for production release or Google Play Store distribution.

The goal is to demonstrate how an AI model can classify Korean SMS messages as normal or smishing/phishing and show the model result in an Android demo app.

## Core Principle

This is an AI-first project.

Do not implement rule-based smishing detection.

Forbidden examples:
- Do not classify a message as dangerous just because it contains "택배".
- Do not classify a message as dangerous just because it contains a URL.
- Do not classify a message as dangerous using hardcoded keyword if-statements.
- Do not create a RuleBasedAnalyzer, RuleEngine, KeywordDetector, or URLRiskRuleEngine.

Allowed:
- Text preprocessing for model input.
- Tokenization.
- Padding/truncation.
- Normalization that is required for model inference.
- Mapping model probability to UI labels.

## AI Classification Policy

The model should take message text as input and output probabilities such as:

- normalProbability
- phishingProbability

The app may map probabilities to UI labels:

- phishingProbability < 0.40: 정상
- 0.40 <= phishingProbability < 0.70: 주의
- phishingProbability >= 0.70: 스팸 경고

This threshold mapping is allowed because it only visualizes model confidence. It must not include keyword rules.

## Dataset

Use the Hugging Face dataset:

https://huggingface.co/datasets/meal-bbang/Korean_message

Before training, inspect:
- columns
- label meanings
- number of examples
- class balance
- missing values
- duplicates
- message length distribution
- license or usage notes
- dataset risks and limitations

## Machine Learning Requirements

This is a supervised text classification task.

Required evaluation:
- train/dev/test split
- accuracy
- precision
- recall
- F1-score
- confusion matrix
- false positive examples
- false negative examples

Prefer reproducible scripts over ad-hoc notebook-only code.

Recommended folders:
- data/raw/
- data/processed/
- notebooks/
- src/
- models/
- outputs/
- android/

Never overwrite raw data.

## Android Requirements

The Android app is a demo UI for AI classification results.

Start with:
- sample_messages.json
- mock classifier
- message list screen
- message detail screen
- model probability display

Do not start with SMS permissions.

READ_SMS integration is optional and should be implemented later only after the AI pipeline and demo UI work.

If READ_SMS fails due to Android permissions, fall back to sample dataset mode.

## Privacy

Do not send SMS body text to external servers.

Do not log SMS body text to console, Logcat, or analytics.

This is a local educational demo.

## Working Style

Before major implementation, write a short plan.

Keep tasks small and verifiable.

After changes, run the most relevant validation command:
- Python: pytest, python scripts, or notebook execution checks
- Android: ./gradlew build or relevant unit tests

At the end of each task, report:
- files changed
- what was implemented
- how it was verified
- next recommended step