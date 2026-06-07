# ANDROID_ON_DEVICE_BASELINE.md

## 목적

이 문서는 `ixissage` Android 앱에 구현된 온디바이스 baseline classifier를 설명한다.

현재 Android 앱은 Transformer 모델을 직접 실행하지 않는다. 대신 이미 학습한 `TF-IDF + Logistic Regression` baseline 모델을 Android asset으로 export하고, Kotlin 코드에서 직접 TF-IDF 벡터와 logistic regression 확률을 계산한다.

이 방식은 룰 기반 탐지가 아니다.

- 키워드 `if`문을 사용하지 않는다.
- URL 포함 여부로 위험 판단하지 않는다.
- 문자 본문을 사람이 만든 위험 점수로 바꾸지 않는다.
- 학습된 TF-IDF vocabulary, IDF 값, logistic regression weight로 확률을 계산한다.

## 현재 구현 상태

Android asset:

- `android/IxissageApp/app/src/main/assets/baseline_tfidf_logreg.json`

Android classifier:

- `android/IxissageApp/app/src/main/java/com/ixissage/app/classifier/OnDeviceBaselineClassifier.kt`

export script:

- `scripts/export_baseline_android.py`

ViewModel 연결:

- `MessageViewModel`이 `ClassifierProvider.provideOnDeviceBaselineClassifier(application)`을 사용한다.

즉 현재 Android 앱의 분류 흐름은 다음과 같다.

```text
sample_messages.json
    -> MessageRepository가 문자 본문 로드
    -> OnDeviceBaselineClassifier가 Android 내부에서 TF-IDF 계산
    -> Logistic Regression sigmoid probability 계산
    -> ClassificationResult 반환
    -> MessageListScreen / MessageDetailScreen 표시
```

목록 화면 상단의 직접 테스트 아이콘을 누르면 사용자가 문자 본문을 직접 입력할 수도 있다.

```text
사용자 직접 입력
    -> OnDeviceBaselineClassifier가 Android 내부에서 TF-IDF 계산
    -> Logistic Regression sigmoid probability 계산
    -> 직접 테스트 화면에 결과 표시
```

## 모델 asset 크기

확인 결과:

- `baseline_tfidf_logreg.json`: 약 5.2 MB
- debug APK: 약 17-18 MB

이 크기는 수업 발표용 Android 데모 앱에 넣기 현실적인 수준이다.

## 모델 export 방법

baseline 모델이 이미 학습되어 있어야 한다.

필요 파일:

- `models/baseline_tfidf_logreg.joblib`

없으면 먼저 실행한다.

```bash
python3 scripts/download_dataset.py
python3 scripts/train_baseline.py
```

Android asset export:

```bash
python3 scripts/export_baseline_android.py
```

이 명령은 Python baseline 모델과 export된 JSON 계산 결과를 비교한다. 예시 문장들에서 확률 차이가 거의 없으면 asset을 생성한다.

생성 파일:

```text
android/IxissageApp/app/src/main/assets/baseline_tfidf_logreg.json
```

## Android 실행 방법

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export ANDROID_SDK_ROOT=$ANDROID_HOME

cd android/IxissageApp
./gradlew build
```

앱 설치:

```bash
./gradlew installDebug
```

또는 Android Studio에서 `android/IxissageApp` 폴더를 열고 실행한다.

## Kotlin 추론 방식

`OnDeviceBaselineClassifier`는 다음 순서로 계산한다.

1. URL-like 문자열을 공백으로 치환해 URL 표면형을 중립화한다.
2. 문자 본문을 lowercase 처리한다.
3. scikit-learn의 char analyzer와 맞게 반복 whitespace를 단일 space로 정규화한다.
4. 2-5 글자 char n-gram을 생성한다.
5. 학습된 vocabulary에 있는 n-gram만 count한다.
6. sublinear TF와 IDF를 적용한다.
7. L2 normalization을 적용한다.
8. logistic regression weight와 intercept로 decision score를 계산한다.
9. sigmoid로 `phishingProbability`를 계산한다.
10. `normalProbability = 1 - phishingProbability`로 반환한다.

중요:

- n-gram 생성은 모델 입력 전처리다.
- 특정 단어를 검사해 라벨을 정하지 않는다.
- URL-like 문자열 제거는 URL의 안전성을 판단하는 로직이 아니라, URL 존재만으로 스미싱 확률이 과도하게 올라가지 않도록 하는 균일한 전처리다.
- URL 위험도 자체는 이 모델이 판단하지 않는다.

## Transformer와의 차이

현재 프로젝트에는 두 종류의 모델 흐름이 있다.

1. Transformer 모델

   - 위치: `models/smishing_classifier/`
   - 실행 위치: 노트북 Python
   - 장점: 한국어 문맥 처리에 더 강함
   - 단점: Android 온디바이스 변환이 아직 안 됨

2. Android on-device baseline 모델

   - 위치: `android/IxissageApp/app/src/main/assets/baseline_tfidf_logreg.json`
   - 실행 위치: Android 앱 내부 Kotlin 코드
   - 장점: 진짜 온디바이스 추론 가능
   - 단점: Transformer보다 단순하고 문맥 이해가 약함

발표에서 정확한 표현:

> Transformer는 Python 로컬 환경에서 fine-tuning과 평가를 완료했고, Android 앱에는 실시간 온디바이스 데모를 위해 TF-IDF + Logistic Regression baseline 모델을 이식했습니다. Android 앱은 외부 서버 없이 기기 내부에서 baseline 모델 확률을 계산합니다.

## 한계

이 방식은 실제 보안 제품이 아니다.

- 정상 기관 문자에서 false positive가 발생할 수 있다.
- 스미싱 문자를 정상으로 놓치는 false negative도 가능하다.
- URL 평판, 대량 발송 패턴, 사용자 신고 데이터는 개인 앱에서 알 수 없다.
- Transformer보다 문맥 이해력이 낮다.

따라서 앱 문구는 “확정 판정”이 아니라 “AI 기반 참고 지표”로 설명해야 한다.

## 다음 개선 방향

현실적인 후속 작업:

1. 정상 기관 안내 문자 false positive 사례를 별도 manual test set으로 수집
2. baseline threshold calibration
3. URL 전용 ML 모델 또는 평판 DB 검토
4. Transformer ONNX Runtime Mobile 또는 LiteRT 변환 재검토
