# REPRODUCIBILITY.md

## 목적

이 문서는 친구나 발표 평가자가 `ixissage`를 직접 실행하거나 검증하는 방법을 정리한다.

현재 GitHub 저장소에는 코드, 문서, Android 데모 앱, 안전하게 마스킹된 Android 샘플 데이터가 포함되어 있다.

의도적으로 제외한 항목:

- `data/raw/`: Hugging Face 원본 데이터
- `data/processed/`: train/dev/test split CSV
- `models/`: 학습된 모델 weight
- 큰 JSON/CSV 산출물

이 파일들은 로컬에서 다시 만들 수 있다. 원본 데이터와 모델 weight를 GitHub commit에 직접 넣지 않는 이유는 저장소 크기, 데이터셋 라이선스 불명확성, 모델 공유 범위 때문이다.

## 검증 레벨 1: Android 앱만 실행

친구들이 가장 쉽게 확인할 수 있는 방식이다.

필요한 것:

- GitHub 저장소 clone
- Android Studio 또는 Android SDK/Gradle
- JDK 17

실행:

```bash
git clone https://github.com/topjs1/ixissage.git
cd ixissage/android/IxissageApp
./gradlew build
```

Android Studio에서 실행:

1. Android Studio를 연다.
2. `ixissage/android/IxissageApp` 폴더를 연다.
3. 에뮬레이터 또는 실제 기기를 선택한다.
4. `app`을 실행한다.

확인할 수 있는 것:

- 문자 목록 화면
- AI 판단 배지
- 스미싱 확률
- 문자 상세 화면
- ground truth label
- predicted label
- 정상/스미싱 확률
- 사용자가 직접 입력한 문자 본문에 대한 온디바이스 baseline 추론 결과

이 방식은 Python 모델 파일이 없어도 된다. Android 앱은 `sample_messages.json`에서 문자 본문을 읽고, `baseline_tfidf_logreg.json`에 들어 있는 TF-IDF + Logistic Regression baseline 모델을 기기 내부에서 실행한다.

주의:

- Android 앱의 실시간 온디바이스 모델은 Transformer가 아니라 baseline 모델이다.
- Transformer 모델은 Python 로컬 환경에서 학습/평가/단일 추론에 사용된다.
- `PrecomputedSampleClassifier`는 구조상 남아 있지만 현재 ViewModel은 `OnDeviceBaselineClassifier`를 사용한다.

## 검증 레벨 2: 데이터 다운로드부터 학습까지 재현

친구들이 모델 학습과 평가 과정을 직접 재현하고 싶을 때 사용한다.

Python 환경:

```bash
git clone https://github.com/topjs1/ixissage.git
cd ixissage
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

데이터셋 다운로드:

```bash
python3 scripts/download_dataset.py
```

데이터셋 검사:

```bash
python3 scripts/inspect_dataset.py
```

baseline 학습:

```bash
python3 scripts/train_baseline.py
```

baseline 평가:

```bash
python3 scripts/evaluate_baseline.py
```

Transformer 학습:

```bash
python3 scripts/train_transformer.py
```

Transformer 평가:

```bash
python3 scripts/evaluate_transformer.py
```

주의:

- Transformer 학습은 CPU에서는 느릴 수 있다.
- Mac Apple Silicon에서는 `mps`, NVIDIA GPU에서는 `cuda`가 사용될 수 있다.
- 학습 결과는 `models/smishing_classifier/`에 저장된다.
- 평가 결과는 `outputs/transformer_report.md` 등에 저장된다.

빠른 smoke test가 필요하면 epoch를 줄일 수 있다.

```bash
python3 scripts/train_transformer.py --epochs 1 --batch-size 16
```

이 경우 최종 성능은 README의 성능과 다를 수 있다.

## 검증 레벨 3: 기존 학습 모델로 Python 추론 실행

친구들이 네가 이미 학습한 모델로 바로 `src/inference.py`를 실행하고 싶다면 `models/smishing_classifier/`가 필요하다.

현재 이 모델 weight는 GitHub commit에 포함하지 않았다.

추천 공유 방식:

- GitHub Release asset
- Google Drive
- 학교 LMS 첨부 파일

모델을 ZIP으로 묶기:

```bash
zip -r smishing_classifier.zip models/smishing_classifier
```

친구들이 ZIP을 받은 뒤 프로젝트 루트에서 압축 해제하면 다음 구조가 되어야 한다.

```text
ixissage/
└── models/
    └── smishing_classifier/
        ├── config.json
        ├── model.safetensors
        ├── tokenizer.json
        ├── tokenizer_config.json
        ├── special_tokens_map.json
        └── vocab.txt
```

그 다음 실행:

```bash
python3 src/inference.py --text "오늘 저녁에 회의 끝나고 집에 갈게." --include-ui-badge
```

예상 출력 형태:

```json
{
  "predictedLabel": "normal",
  "normalProbability": 0.9686533808708191,
  "phishingProbability": 0.0313466340303421,
  "uiBadge": "정상"
}
```

## GitHub Release로 모델 공유하기

모델 weight를 git commit에 직접 넣는 것보다 Release asset으로 올리는 편이 낫다.

절차:

1. 로컬에서 모델 ZIP 생성

   ```bash
   zip -r smishing_classifier.zip models/smishing_classifier
   ```

2. GitHub 저장소 접속

   ```text
   https://github.com/topjs1/ixissage
   ```

3. 오른쪽 `Releases` 클릭
4. `Draft a new release` 클릭
5. Tag 입력 예:

   ```text
   model-v1
   ```

6. Release title 입력 예:

   ```text
   ixissage smishing classifier v1
   ```

7. `smishing_classifier.zip` 업로드
8. 설명에 다음 문구 추가

   ```text
   Fine-tuned Transformer model for ixissage class demo.
   Use for educational verification only.
   Dataset license is unclear, so do not use commercially.
   ```

9. `Publish release` 클릭

친구들은 Release에서 ZIP을 다운로드해 `models/smishing_classifier/` 위치에 압축을 풀면 된다.

## GitHub에 올려도 되는 파일과 피하는 파일

올려도 되는 쪽:

- 프로젝트 문서
- Python scripts
- Android source code
- `requirements.txt`
- `outputs/*_report.md`
- `outputs/inference_examples.md`
- 마스킹된 Android asset `sample_messages.json`

피하는 쪽:

- 원본 데이터 CSV
- train/dev/test split CSV
- 학습된 모델 weight
- 개인정보나 실제 URL이 들어갈 수 있는 샘플
- 실제 사용자 SMS

## 발표 검증 포인트

친구들이 코드를 볼 때 확인할 부분:

- Android에 `RuleBasedAnalyzer`, `KeywordDetector`, `URLRiskAnalyzer`가 없는지
- Kotlin 코드가 문자 본문 키워드로 위험 판단하지 않는지
- `PrecomputedSampleClassifier`가 JSON의 모델 확률만 반환하는지
- `src/inference.py`가 softmax probability로 `predictedLabel`을 정하는지
- `phishingProbability` threshold는 UI 배지 표시용인지

금지된 방식:

- `"택배"`가 있으면 스팸
- URL이 있으면 스팸
- 금액 표현이 있으면 스팸
- 직접 만든 keyword risk score

허용된 방식:

- tokenizer 전처리
- 모델 softmax probability
- probability 기반 UI badge mapping
