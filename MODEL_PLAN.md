# MODEL_PLAN.md

## 모델 개발 목표

`ixissage`의 모델 개발 목표는 한국어 문자 메시지 본문을 입력받아 정상 또는 스미싱 확률을 출력하는 것이다.

이 프로젝트는 생성형 AI가 아니라 supervised text classification이다.

- 입력: 문자 메시지 본문
- 출력: 정상/스미싱 라벨
- 앱에서 사용할 값: 정상 확률, 스미싱 확률

중요한 제약:

- 룰 기반 탐지는 금지한다.
- `"택배"`, `"미납"`, `"URL"`, `"환급"`, `"본인인증"` 같은 키워드를 if문으로 검사해 위험 판단하지 않는다.
- 위험 판단은 모델의 softmax probability 또는 sigmoid probability만 사용한다.
- threshold는 모델 확률을 UI 배지로 바꾸기 위한 용도만 허용된다.

## 문제 유형

기본 문제 유형은 binary text classification이다.

예상 라벨:

- `normal`
- `smishing`

모델 출력 예:

```json
{
  "normalProbability": 0.12,
  "smishingProbability": 0.88,
  "predictedLabel": "smishing"
}
```

Android UI는 이 확률을 다음처럼 표시할 수 있다.

- `smishingProbability < 0.40`: `정상`
- `0.40 <= smishingProbability < 0.70`: `주의`
- `smishingProbability >= 0.70`: `스팸 경고`

이 threshold mapping은 모델 확률을 시각화하는 것이므로 허용된다. 하지만 문자 본문 안의 특정 단어를 검사하는 방식은 허용되지 않는다.

## 데이터 라벨 처리

Hugging Face 데이터셋 카드 기준:

- `label 1`: 일상적 문자
- `label 2`: 피싱/스미싱 문자

원본 CSV 확인 결과:

- `class=1`: 5,778개
- `class=2`: 10,531개
- `class=3`: 2,700개

`class=3`은 데이터셋 카드에 의미가 명확히 설명되어 있지 않다. 따라서 모델 학습 전에 EDA에서 반드시 처리 방침을 정한다.

권장 실험 순서:

1. `class=1`과 `class=2`만 사용한 binary baseline
2. `class=3` 샘플을 분석한 뒤 `normal` 병합 여부 결정
3. 필요하면 `1`, `2`, `3` multi-class 모델도 비교

모델 코드에서는 라벨 매핑을 명시적으로 기록해야 한다. 예를 들어 `2 -> smishing`, `1 -> normal` 같은 매핑을 설정 파일이나 리포트에 남긴다.

## 전처리 계획

허용되는 전처리:

- 결측치 제거
- 중복 제거
- 앞뒤 공백 제거
- 너무 긴 메시지 truncation
- tokenizer 적용
- padding
- attention mask 생성
- 모델 입력 형식에 맞는 정규화

주의:

- 전처리는 모델 입력을 안정적으로 만들기 위한 과정이다.
- 전처리가 위험 판단 규칙이 되면 안 된다.
- URL, 금액, 기관명 등을 사람이 만든 위험 점수로 바꾸지 않는다.
- `"URL이 있으면 스미싱"` 같은 feature engineering은 금지한다.

TF-IDF baseline은 허용된다. TF-IDF는 학습 데이터에서 통계적으로 feature를 만들고 분류기가 가중치를 학습하기 때문이다. 사람이 직접 keyword risk score를 만드는 방식과 다르다.

## 데이터 split

Hugging Face에는 train split만 있으므로 프로젝트에서 직접 split한다.

권장:

- train: 70%
- dev: 15%
- test: 15%

조건:

- stratified split 사용
- random seed 고정
- split 결과 저장
- test set은 최종 평가에만 사용
- 중복 메시지가 train/test에 동시에 들어가지 않도록 점검

예상 저장 위치:

- `data/processed/train.csv`
- `data/processed/dev.csv`
- `data/processed/test.csv`

## baseline 모델

baseline의 목적은 빠르게 기준 성능을 만드는 것이다.

후보:

- TF-IDF + Logistic Regression
- TF-IDF + Linear SVM
- TF-IDF + Naive Bayes

권장 첫 baseline:

- TF-IDF + Logistic Regression

이유:

- 구현이 단순하다.
- 확률 출력이 가능하다.
- 결과 해석이 비교적 쉽다.
- Transformer 성능과 비교할 기준점이 된다.

필수 출력:

- accuracy
- precision
- recall
- F1-score
- confusion matrix
- false positive examples
- false negative examples

주의:

- baseline도 AI 모델이다.
- 하지만 baseline 결과를 보고 사람이 키워드 규칙을 앱에 추가하면 안 된다.

## Transformer fine-tuning

Transformer 모델은 한국어 문장 의미와 문맥을 더 잘 반영하기 위한 단계다.

검토한 후보 모델:

- `monologg/koelectra-small-v3-discriminator`
- `distilbert/distilbert-base-multilingual-cased`

선택 기준:

- 한국어 처리 성능
- 수업 프로젝트 시간 내 학습 가능성
- GPU 필요 여부
- 모델 크기
- Android 변환 가능성

권장 모델:

- `monologg/koelectra-small-v3-discriminator`

추천 이유:

- 한국어 특화 ELECTRA 계열 모델이므로 한국어 문자 메시지 분류에 더 직접적으로 맞다.
- Hugging Face config 기준 `hidden_size=256`, `num_attention_heads=4`, `vocab_size=35000`으로, `distilbert-base-multilingual-cased`의 `dim=768`, `n_heads=12`, `vocab_size=119547`보다 학습과 추론 비용이 작을 가능성이 높다.
- 수업 프로젝트에서 빠르게 fine-tuning하고 Android 데모용 샘플 추론 결과를 만들기에 더 현실적이다.
- Android 온디바이스 변환은 여전히 별도 검토가 필요하지만, 작은 한국어 모델을 우선 선택하는 편이 TFLite/LiteRT 검토에도 유리하다.

`distilbert-base-multilingual-cased`의 장점:

- Apache 2.0 라이선스가 명확하다.
- 다국어 모델로 일반성이 높고 Hugging Face 생태계 예제가 많다.

하지만 이번 프로젝트는 한국어 SMS만 다루고 학습 비용과 데모 속도가 중요하므로 첫 Transformer 실험은 `monologg/koelectra-small-v3-discriminator`로 진행한다.

주의:

- Transformer 모델도 룰 기반 탐지기가 아니다.
- 입력은 문자 본문 `content`만 사용한다.
- URL 포함 여부, 특정 키워드, 금액 표현 같은 handcrafted risk feature를 만들지 않는다.
- tokenizer, truncation, padding은 모델 입력 형식을 맞추기 위한 전처리로만 사용한다.

학습 방식:

- Hugging Face Transformers 사용
- tokenizer로 `content` 인코딩
- classification head fine-tuning
- dev set 기준으로 best checkpoint 선택
- test set에서 최종 평가
- baseline report의 TF-IDF + Logistic Regression 성능과 비교

저장 위치:

- `models/smishing_classifier/`

## 평가 지표

필수 지표:

- accuracy
- precision
- recall
- F1-score
- confusion matrix

스미싱 탐지에서는 특히 다음을 구분해 설명한다.

- False Positive: 정상 문자를 스미싱으로 잘못 판단
- False Negative: 스미싱 문자를 정상으로 잘못 판단

False Negative는 사용자가 실제 위험 문자를 놓칠 수 있으므로 중요하다. 하지만 False Positive가 너무 많으면 앱 신뢰도가 떨어진다. 따라서 threshold별 precision/recall trade-off를 확인한다.

## 오류 분석

모델 평가 후 잘못 분류한 예시를 분석한다.

확인할 내용:

- 짧은 문장에서 오분류가 많은가
- 긴 문장에서 truncation 문제가 있는가
- 정상 택배 알림과 스미싱 택배 사칭이 헷갈리는가
- 일상 대화와 가족 사칭 스미싱이 헷갈리는가
- `label 3` 포함 여부가 성능에 어떤 영향을 주는가

주의:

- 오류 분석에서 발견한 키워드를 규칙으로 추가하지 않는다.
- 오류 분석은 모델 개선, 데이터 정제, threshold 조정의 근거로 사용한다.

## inference.py 계획

`src/inference.py`는 학습된 모델을 불러와 하나의 문자 본문에 대해 확률을 반환한다.

역할:

- 모델 로드
- tokenizer 로드
- 메시지 전처리
- 모델 추론
- 확률 계산
- UI용 badge 계산

출력 예:

```json
{
  "messageId": "sample-001",
  "normalProbability": 0.18,
  "smishingProbability": 0.82,
  "predictedLabel": "smishing",
  "badge": "스팸 경고"
}
```

금지:

- 메시지 본문에 `"택배"`가 있는지 검사해 badge 결정
- URL 포함 여부로 badge 결정
- 금액 표현 포함 여부로 badge 결정
- 기관명 포함 여부로 badge 결정

허용:

- 모델 확률이 `0.70` 이상이면 `스팸 경고` 표시
- 모델 확률이 `0.40` 이상이면 `주의` 표시

## Android 연결 전략

1차 데모:

- Python에서 모델 추론 결과를 `sample_messages.json`으로 만든다.
- Android 앱은 JSON의 확률과 배지를 표시한다.

2차 데모:

- Android 앱에 mock classifier를 연결한다.
- mock classifier는 샘플 JSON에 저장된 확률을 반환한다.

3차 검토:

- TFLite/LiteRT 변환 가능성을 조사한다.
- 가능하면 Android 내부에서 로컬 추론한다.

중요:

- 문자 본문을 외부 서버로 보내지 않는다.
- 외부 AI API를 호출하지 않는다.
- 로컬 데모가 기본이다.

## 완료 기준

모델 파트 완료 기준:

- 데이터셋 다운로드 가능
- EDA 리포트 작성
- train/dev/test split 생성
- baseline 모델 평가 완료
- Transformer 모델 평가 완료
- confusion matrix 생성
- false positive/false negative 예시 분석
- `inference.py`에서 확률 출력 가능
- Android용 `sample_messages.json` 생성 가능

완료 후에도 이 프로젝트는 보안 제품이 아니다. 수업 프로젝트로서 AI 분류 흐름을 보여주는 것이 목적이다.
