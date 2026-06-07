# ixissage

`ixissage`는 인공지능 과목 수업 프로젝트용 Android 데모 앱이다. 목표는 한국어 문자 메시지를 AI 모델로 정상/스미싱 분류하고, Android 화면에서 모델 확률 기반 배지를 보여주는 것이다.

이 프로젝트는 상용 보안 제품이 아니며 Google Play Store 배포를 목표로 하지 않는다.

## 핵심 원칙

- 룰 기반 스미싱 탐지를 구현하지 않는다.
- `"택배"`, `"미납"`, `"URL"`, `"환급"`, `"본인인증"` 같은 키워드를 if문으로 검사해 위험 판단하지 않는다.
- 위험 판단은 AI 모델의 softmax probability 또는 sigmoid probability만 사용한다.
- 데이터 분석에서 발견한 패턴을 Android 또는 inference 코드의 규칙으로 옮기지 않는다.
- 데이터 조사 단계에서는 모델 학습을 하지 않는다.
- raw data는 `data/raw/`에 저장하고 절대 overwrite하지 않는다.
- 처리 결과와 리포트는 `data/processed/`에 저장한다.

## 데이터셋 조사

대상 데이터셋:

- https://huggingface.co/datasets/meal-bbang/Korean_message

현재 단계에서 생성된 스크립트:

- `scripts/download_dataset.py`
- `scripts/inspect_dataset.py`

현재 단계에서 생성된 문서/리포트:

- `DATASET_NOTES.md`
- `data/processed/dataset_inspection_summary.json`
- `data/processed/dataset_inspection_report.md`

## 데이터셋 조사 실행 방법

Python 표준 라이브러리만 사용한다. 별도 패키지 설치 없이 실행할 수 있다.

1. 데이터셋 다운로드:

```bash
python3 scripts/download_dataset.py
```

이 명령은 `data/raw/lgaidataset.csv`를 생성한다. 파일이 이미 있으면 덮어쓰지 않고 건너뛴다.

2. 데이터셋 검사:

```bash
python3 scripts/inspect_dataset.py
```

이 명령은 다음을 확인한다.

- 컬럼 구조
- label 1과 label 2 의미
- 전체 행 수
- class balance
- null count
- duplicate count
- 문자 길이 분포
- 정상 문자 10개 샘플
- 스미싱 문자 10개 샘플
- label 3 확인용 샘플

검사 결과는 `data/processed/dataset_inspection_summary.json`과 `data/processed/dataset_inspection_report.md`에 저장된다.

샘플 출력에서 긴 숫자열은 기본적으로 `<NUM>`으로 마스킹된다. 원문 전체를 확인해야 할 때만 다음 옵션을 사용한다.

```bash
python3 scripts/inspect_dataset.py --no-redact-samples
```

## 현재 확인된 데이터셋 요약

- 총 row 수: `19,009`
- 컬럼: `index`, `content`, `class`
- `class=1`: `5,778`개, 일상 문자
- `class=2`: `10,531`개, 피싱/스미싱 문자
- `class=3`: `2,700`개, 데이터셋 카드에 의미가 명시되지 않음
- `content` 결측치: `0`
- `class` 결측치: `0`
- 중복 본문 row: `3,149`
- 문자 길이: min `4`, median `50`, mean `67.85`, max `1,223`

자세한 내용은 `DATASET_NOTES.md`를 확인한다.

## Baseline 모델

첫 번째 baseline은 TF-IDF + Logistic Regression이다.

- 입력 feature: 문자 본문 `content`만 사용
- 라벨 매핑: `class=1 -> normal`, `class=2 -> smishing`
- `class=3`은 첫 binary baseline에서 제외
- 동일 본문 중복은 split 전에 제거
- 룰 기반 탐지, 키워드 if문, URL 포함 여부 같은 수작업 feature는 사용하지 않음

의존성 설치:

```bash
python3 -m pip install -r requirements.txt
```

학습 실행:

```bash
python3 scripts/train_baseline.py
```

이 명령은 다음 파일을 생성한다.

- `data/processed/train.csv`
- `data/processed/dev.csv`
- `data/processed/test.csv`
- `data/processed/baseline_split_metadata.json`
- `models/baseline_tfidf_logreg.joblib`
- `outputs/baseline_train_summary.json`

평가 실행:

```bash
python3 scripts/evaluate_baseline.py
```

이 명령은 accuracy, precision, recall, F1, confusion matrix, false positive 예시, false negative 예시를 출력하고 다음 파일을 생성한다.

- `outputs/baseline_report.md`
- `outputs/baseline_metrics.json`
- `outputs/confusion_matrix_baseline.csv`

현재 test split 평가 결과:

- accuracy: `0.992567`
- precision: `0.997373`
- recall: `0.989574`
- F1: `0.993458`
- confusion matrix: normal->normal `864`, normal->smishing `3`, smishing->normal `12`, smishing->smishing `1139`

자세한 내용은 `outputs/baseline_report.md`를 확인한다.

## Transformer 모델

첫 번째 Transformer fine-tuning 모델은 `monologg/koelectra-small-v3-discriminator`이다.

선택 이유:

- 한국어 특화 ELECTRA 계열 모델이다.
- `distilbert-base-multilingual-cased`보다 config상 hidden size, attention head, vocab size가 작아 학습/추론 비용이 낮을 가능성이 높다.
- 수업 프로젝트와 Android 데모용 샘플 추론 결과 생성에 더 현실적이다.

주의:

- 입력은 문자 본문 `content`만 사용한다.
- 룰 기반 탐지, 키워드 if문, handcrafted risk feature는 사용하지 않는다.
- tokenizer, truncation, padding은 모델 입력 형식을 맞추기 위한 전처리다.

학습 실행:

```bash
python3 scripts/train_transformer.py
```

기본 설정:

- model: `monologg/koelectra-small-v3-discriminator`
- train split: `data/processed/train.csv`
- dev split: `data/processed/dev.csv`
- max length: `192`
- epochs: `2`
- best checkpoint 기준: dev F1

이 명령은 다음 파일을 생성한다.

- `models/smishing_classifier/config.json`
- `models/smishing_classifier/model.safetensors`
- `models/smishing_classifier/tokenizer.json`
- `models/smishing_classifier/vocab.txt`
- `outputs/transformer_train_summary.json`

평가 실행:

```bash
python3 scripts/evaluate_transformer.py
```

이 명령은 accuracy, precision, recall, F1, confusion matrix, false positive 예시, false negative 예시를 출력하고 baseline과 비교한다.

생성 파일:

- `outputs/transformer_report.md`
- `outputs/transformer_metrics.json`
- `outputs/transformer_errors.json`
- `outputs/confusion_matrix_transformer.csv`

현재 test split 평가 결과:

- accuracy: `0.998513`
- precision: `0.999130`
- recall: `0.998262`
- F1: `0.998696`
- confusion matrix: normal->normal `866`, normal->smishing `1`, smishing->normal `2`, smishing->smishing `1149`

baseline 대비:

- accuracy: `+0.005946`
- precision: `+0.001757`
- recall: `+0.008688`
- F1: `+0.005238`

자세한 내용은 `outputs/transformer_report.md`를 확인한다.

## 단일 문자 추론

학습된 Transformer 모델로 하나의 문자 메시지를 분류할 수 있다.

출력 필드:

- `predictedLabel`: `normal` 또는 `smishing`
- `normalProbability`: 정상 확률
- `phishingProbability`: 피싱/스미싱 확률

중요:

- 판단은 모델 softmax probability만 사용한다.
- 룰 기반 탐지, 키워드 if문, handcrafted risk feature는 사용하지 않는다.
- threshold 기반 배지는 선택 UI 표시용이며 텍스트 위험 판단 로직이 아니다.

단일 문자 실행:

```bash
python3 src/inference.py --text "오늘 저녁에 회의 끝나고 집에 갈게."
```

출력 예:

```json
{
  "predictedLabel": "normal",
  "normalProbability": 0.9686533808708191,
  "phishingProbability": 0.0313466340303421
}
```

예시 5개 실행 및 Markdown 저장:

```bash
python3 src/inference.py --examples --write-examples
```

생성 파일:

- `outputs/inference_examples.md`

선택적으로 UI 배지까지 같이 확인할 수 있다.

```bash
python3 src/inference.py --text "..." --include-ui-badge
```

## Android 샘플 데이터

Android 프로젝트가 아직 생성되지 않았으므로 데모용 JSON은 `outputs/sample_messages.json`에 생성한다.

생성 실행:

```bash
python3 scripts/create_sample_messages.py
```

이 명령은 `data/processed/test.csv`에서 normal 15개, smishing 15개를 샘플링해 총 30개의 메시지를 만든다.

JSON 필드:

- `id`
- `sender`
- `body`
- `groundTruthLabel`
- `predictedLabel`
- `normalProbability`
- `phishingProbability`

중요:

- 실제 URL처럼 보이는 값은 `https://example.com`으로 치환한다.
- 전화번호, IP 주소, 긴 숫자열, 이름/주소처럼 보이는 값은 마스킹한다.
- 확률은 마스킹된 `body`에 대해 학습된 Transformer 모델이 낸 inference 결과다.
- 룰 기반 판단, 키워드 if문, handcrafted risk feature는 사용하지 않는다.

생성된 파일:

- `outputs/sample_messages.json`

## Android 데모 앱

Android 데모 앱은 Kotlin, Jetpack Compose, MVVM, Gradle Kotlin DSL로 구성되어 있다.

위치:

- `android/IxissageApp/`

기능:

- 실제 SMS 권한 없이 `sample_messages.json` assets를 읽는다.
- `MessageListScreen`에서 발신자, 문자 미리보기, AI 판단 배지, 스미싱 확률을 표시한다.
- 메시지를 누르면 `MessageDetailScreen`에서 전체 본문, ground truth label, predicted label, 정상 확률, 스미싱 확률을 표시한다.
- 배지는 `phishingProbability` threshold만 사용해 UI 표시용으로 계산한다.

배지 기준:

- `phishingProbability < 0.40`: `정상`
- `0.40 <= phishingProbability < 0.70`: `주의`
- `phishingProbability >= 0.70`: `스팸 경고`

중요:

- `RuleBasedAnalyzer`, `KeywordDetector`, `URLRiskAnalyzer` 같은 룰 기반 구조는 없다.
- 키워드 if문으로 위험 판단하지 않는다.
- Android 앱은 JSON에 저장된 모델 inference 결과와 확률만 표시한다.

빌드 환경:

- JDK 17
- Android SDK platform `android-35`
- Gradle wrapper `8.10.2`

이 저장소에서 사용한 로컬 환경 변수 예:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export ANDROID_SDK_ROOT=$ANDROID_HOME
```

빌드:

```bash
cd android/IxissageApp
./gradlew build
```

Debug APK:

```text
android/IxissageApp/app/build/outputs/apk/debug/app-debug.apk
```

기기에 설치:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Android Studio에서는 `android/IxissageApp` 폴더를 열면 된다.

## 발표 데모 시나리오

수업 발표에서는 다음 흐름으로 시연한다.

1. Transformer 모델 평가 결과 설명
2. `src/inference.py`로 단일 문자 추론 결과 확인
3. `sample_messages.json`에 저장된 모델 확률 설명
4. Android 앱에서 문자 목록과 상세 화면 시연
5. 온디바이스 추론은 후속 확장 과제로 설명

자세한 발표 스크립트와 대체 시연 방법은 `PRESENTATION_DEMO_SCENARIO.md`를 확인한다.

## 친구/평가자 검증 방법

친구들이 이 저장소를 직접 실행하거나 검증하고 싶다면 `REPRODUCIBILITY.md`를 확인한다.

검증 방식은 세 단계로 나뉜다.

1. Android 앱만 실행: GitHub 저장소만 clone하면 가능
2. 데이터 다운로드부터 학습까지 재현: `scripts/download_dataset.py`부터 실행
3. 기존 학습 모델로 Python 추론 실행: `models/smishing_classifier/`를 별도 ZIP 또는 GitHub Release로 받아야 함

원본 데이터, processed split CSV, 학습된 모델 weight는 기본 GitHub commit에 포함하지 않는다. 필요한 경우 모델 weight는 GitHub Release asset으로 따로 공유하는 것을 권장한다.

## 라이선스와 사용상 주의

Hugging Face 데이터셋 카드에는 명확한 라이선스가 표시되어 있지 않다. 라이선스 discussion에서 작성자는 일부 소스의 라이선스를 확인하기 어렵고, 법적 문제가 중요한 상업적 이용이라면 사용하지 않는 편이 좋다고 설명했다.

따라서 `ixissage`는 수업 프로젝트 범위에서만 사용하고, 상용 서비스나 실제 보안 제품으로 사용하지 않는다.

## 다음 단계

다음 단계는 Android UI를 실제 기기나 에뮬레이터에서 확인하고, 필요하면 `outputs/sample_messages.json`을 다시 생성해 assets에 갱신하는 것이다. 이때도 키워드 기반 위험 판단 코드는 작성하지 않는다.
