# ANDROID_PLAN.md

## Android 앱 목표

`ixissage` Android 앱은 AI 모델의 문자 분류 결과를 보여주는 데모 앱이다.

앱의 핵심 기능은 다음과 같다.

- 샘플 문자 목록 표시
- 각 문자에 대한 AI 모델 확률 표시
- `정상`, `주의`, `스팸 경고` 배지 표시
- 문자 상세 화면 표시

초기 버전은 실제 SMS 권한을 사용하지 않는다. `sample_messages.json`을 사용해 앱을 먼저 완성한다.

## 가장 중요한 Android 원칙

Android 앱은 스미싱 위험을 직접 판단하지 않는다.

금지:

- 문자 본문에 `"택배"`가 있으면 위험 배지 표시
- 문자 본문에 `"미납"`이 있으면 위험 배지 표시
- 문자 본문에 URL이 있으면 위험 배지 표시
- 문자 본문에 `"환급"`, `"본인인증"` 같은 단어가 있으면 위험 배지 표시
- Kotlin 코드에 keyword list를 넣고 점수 계산

허용:

- AI 모델이 계산한 `smishingProbability` 표시
- 모델 확률을 UI 배지로 변환
- 샘플 JSON에 들어 있는 모델 추론 결과 표시
- mock classifier로 UI 상태 테스트

즉, Android는 AI 결과를 보여주는 프론트엔드다. 위험 판단의 출처는 모델 확률이어야 한다.

## 기술 스택

권장 기술:

- Kotlin
- Jetpack Compose
- Material 3
- Gradle
- Android Studio

초기 구조:

- `android/IxissageApp/`
- Compose single-activity app
- sample JSON asset
- repository/viewmodel 구조
- message list screen
- message detail screen

## 초기 데이터 모드

처음에는 sample dataset mode만 구현한다.

데이터 출처:

- `outputs/sample_messages.json`
- Hugging Face 데이터셋 일부
- Python inference 결과

예상 JSON 구조:

```json
[
  {
    "id": "sample-001",
    "sender": "Sample",
    "body": "문자 본문",
    "normalProbability": 0.12,
    "smishingProbability": 0.88,
    "predictedLabel": "smishing",
    "badge": "스팸 경고"
  }
]
```

주의:

- 샘플 JSON에 실제 개인정보가 포함되지 않도록 마스킹한다.
- Android 앱은 샘플 JSON을 읽고 표시한다.
- 샘플 JSON의 확률은 모델 또는 실험용 mock 결과에서 나온다.

## 화면 계획

### 메시지 목록 화면

표시할 정보:

- 발신자 또는 샘플 이름
- 문자 본문 미리보기
- 스미싱 확률
- 배지
- 날짜 또는 샘플 ID

UX 목표:

- 한눈에 위험도가 보이게 한다.
- 배지는 모델 확률의 시각화임을 유지한다.
- 사용자가 각 메시지를 눌러 상세 화면으로 이동할 수 있게 한다.

### 메시지 상세 화면

표시할 정보:

- 전체 문자 본문
- 정상 확률
- 스미싱 확률
- 예측 라벨
- 배지
- 모델 기반 데모임을 알리는 짧은 표시

주의:

- “이 앱이 실제 보안을 보장한다”는 식의 표현을 피한다.
- 수업 프로젝트용 AI 데모라는 성격을 유지한다.

## 배지 정책

배지는 모델 확률을 사람이 이해하기 쉽게 보여주는 UI 요소다.

예시:

- `smishingProbability < 0.40`: `정상`
- `0.40 <= smishingProbability < 0.70`: `주의`
- `smishingProbability >= 0.70`: `스팸 경고`

이 기준은 허용된다. 이유는 텍스트 내용을 검사하지 않고 모델 확률만 사용하기 때문이다.

금지 예:

```kotlin
if (body.contains("택배")) {
    badge = "스팸 경고"
}
```

허용 예:

```kotlin
badge = when {
    smishingProbability >= 0.70 -> "스팸 경고"
    smishingProbability >= 0.40 -> "주의"
    else -> "정상"
}
```

## Mock classifier 계획

실제 모델을 Android에 연결하기 전에는 mock classifier를 사용한다.

허용되는 mock 방식:

- JSON에 저장된 확률을 그대로 반환
- UI 테스트용 고정 확률 반환
- 샘플 ID별로 미리 정한 확률 반환

금지되는 mock 방식:

- 본문 키워드 기반 위험 판단
- URL 포함 여부 기반 위험 판단
- 금액 표현 기반 위험 판단

mock classifier는 UI 연결을 위한 임시 장치다. 실제 위험 판단처럼 보이는 룰 엔진이 되어서는 안 된다.

## 실제 모델 연결 방향

1차 연결:

- Python에서 `inference.py`를 실행한다.
- 각 샘플 메시지의 모델 확률을 계산한다.
- 결과를 `sample_messages.json`에 저장한다.
- Android는 이 JSON을 표시한다.

장점:

- 구현이 단순하다.
- Android 권한과 모델 변환 문제를 피할 수 있다.
- 수업 데모에 적합하다.

2차 연결:

- TFLite/LiteRT 변환을 검토한다.
- Android 앱 내부에서 로컬 추론을 시도한다.

주의:

- Transformer tokenizer를 Android에서 처리해야 할 수 있다.
- 모델 크기와 속도 문제가 생길 수 있다.
- 수업 일정상 필수 단계는 아니다.

## READ_SMS 기능 계획

실제 SMS 읽기는 후반부 선택 기능이다.

이유:

- Android SMS 권한은 민감하다.
- 권한 요청 UX가 복잡하다.
- 기기/버전/정책에 따라 막힐 수 있다.
- AI 모델 학습과 데모 앱 완성이 먼저다.

추가한다면 다음 원칙을 지킨다.

- 권한 요청 전 사용자에게 목적 설명
- 권한 거부 시 sample dataset mode 유지
- SMS 본문 외부 전송 금지
- SMS 본문 Logcat 출력 금지
- 실제 SMS 데이터 저장 최소화

## 개인정보와 보안

이 앱은 문자 본문을 외부 서버로 보내지 않는다.

금지:

- 외부 AI API 호출
- SMS 본문 서버 업로드
- SMS 본문 analytics 전송
- SMS 본문 Logcat 출력
- 실제 사용자 SMS를 Git에 커밋

허용:

- 샘플 데이터 표시
- 로컬 모델 추론
- 마스킹된 샘플 저장

## Android 완료 기준

초기 완료 기준:

- Android 프로젝트 생성
- sample JSON 로딩
- 메시지 목록 화면
- 메시지 상세 화면
- 확률 기반 배지 표시
- mock classifier 연결
- 실제 SMS 권한 없이 데모 가능

추가 완료 기준:

- Python 모델 결과를 JSON으로 반영
- Android 앱에서 실제 모델 추론 결과처럼 표시
- 가능하면 TFLite/LiteRT 변환 검토 문서 작성

최종적으로 Android 앱은 AI 모델 결과를 설명하는 데모여야 한다. 룰 기반 탐지 앱이 되어서는 안 된다.

