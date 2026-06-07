# ROADMAP.md

## 개발 로드맵

이 로드맵은 `ixissage`를 AI 수업 프로젝트로 완성하기 위한 단계별 계획이다.

가장 중요한 방향은 변하지 않는다. 이 프로젝트는 룰 기반 스미싱 탐지기가 아니라 AI 모델 중심의 supervised text classification 프로젝트다. 문자에 `"택배"`, `"미납"`, `"URL"`, `"환급"`, `"본인인증"` 같은 단어가 있는지 if문으로 검사해서 위험 판단을 내리면 안 된다.

## 1단계: 프로젝트 문서화

목표는 프로젝트의 범위와 금지 사항을 명확히 하는 것이다.

산출물:

- `PROJECT_BRIEF.md`
- `ROADMAP.md`
- `DATASET_NOTES.md`
- `MODEL_PLAN.md`
- `ANDROID_PLAN.md`
- `RISKS_AND_LIMITATIONS.md`

확인할 내용:

- AI 모델 중심 프로젝트라는 점
- 룰 기반 탐지 금지
- sample dataset mode 우선
- 실제 SMS 권한은 후반부 선택 기능
- 문자 본문 외부 전송 금지

상태:

- 현재 단계에서 가장 먼저 완료해야 한다.

## 2단계: Hugging Face 데이터셋 조사 및 다운로드

목표는 `meal-bbang/Korean_message` 데이터셋을 정확히 이해하는 것이다.

해야 할 일:

- Hugging Face 데이터셋 페이지 확인
- 원본 CSV 파일 다운로드
- 컬럼 구조 확인
- 라벨 의미 확인
- 데이터 개수 확인
- class balance 확인
- 결측치 확인
- 중복 메시지 확인
- 메시지 길이 분포 확인

예정 산출물:

- `scripts/download_dataset.py`
- `scripts/inspect_dataset.py`
- `data/raw/lgaidataset.csv`
- `outputs/dataset_summary.md`

주의:

- raw data는 덮어쓰지 않는다.
- 라벨 `3`은 데이터셋 카드에 의미가 명확히 설명되어 있지 않으므로 EDA에서 별도로 확인한다.
- 라벨 처리 방침을 코드에 숨기지 말고 문서와 리포트에 기록한다.

## 3단계: 데이터 EDA

목표는 모델 학습 전에 데이터 품질과 문제 구조를 이해하는 것이다.

확인할 내용:

- 라벨별 데이터 수
- 라벨별 메시지 길이 분포
- 결측치
- 중복 문장
- 너무 짧거나 너무 긴 문장
- 라벨 `3`의 실제 성격
- train/dev/test split 가능성

중요한 제약:

- EDA에서 키워드 빈도를 볼 수는 있다.
- 하지만 키워드를 위험 판단 규칙으로 사용하면 안 된다.
- 예를 들어 `"URL이 많으므로 URL이 있으면 스미싱"` 같은 규칙을 앱이나 inference 코드에 넣지 않는다.

예정 산출물:

- `notebooks/train_smishing_classifier.ipynb`
- `outputs/eda_summary.md`

## 4단계: baseline 모델 학습

목표는 간단하고 재현 가능한 기준 성능을 만든다.

후보 모델:

- TF-IDF + Logistic Regression
- TF-IDF + Linear SVM
- TF-IDF + Naive Bayes

이 baseline은 AI 모델이다. 다만 사람이 직접 만든 키워드 규칙은 아니다. TF-IDF 모델이 데이터에서 통계적으로 학습한 feature weight를 사용하는 것은 허용된다.

해야 할 일:

- stratified train/dev/test split
- baseline 학습
- accuracy, precision, recall, F1-score 출력
- confusion matrix 생성
- false positive 예시 분석
- false negative 예시 분석

예정 산출물:

- `scripts/train_baseline.py`
- `outputs/baseline_report.md`
- `outputs/confusion_matrix_baseline.png`

## 5단계: Transformer 기반 모델 fine-tuning

목표는 한국어 문장 분류에 적합한 사전학습 모델을 fine-tuning하는 것이다.

후보 모델:

- `klue/bert-base`
- `monologg/kobert`
- `beomi/KcELECTRA-base`
- 경량화를 고려한 작은 한국어 모델

선택 기준:

- 한국어 SMS 문장 처리 가능성
- 수업 프로젝트 시간 내 학습 가능성
- 추론 코드 작성 난이도
- Android 변환 가능성

해야 할 일:

- tokenizer 적용
- train/dev/test split 유지
- fine-tuning
- 확률 출력 확인
- threshold별 성능 비교
- 잘못 분류한 예시 분석

예정 산출물:

- `scripts/train_transformer.py`
- `scripts/evaluate_transformer.py`
- `models/smishing_classifier/`
- `outputs/transformer_report.md`
- `outputs/confusion_matrix.png`

## 6단계: inference.py 작성

목표는 학습된 모델을 하나의 메시지 본문에 적용할 수 있게 만드는 것이다.

입력:

- 문자 메시지 본문 문자열

출력:

- `normalProbability`
- `smishingProbability`
- `label`
- `badge`

주의:

- `inference.py`는 키워드 if문으로 위험 판단을 해서는 안 된다.
- 배지는 모델 확률을 UI용으로 변환하는 역할만 한다.
- 예를 들어 `smishingProbability >= 0.70`이면 `스팸 경고`로 표시하는 것은 허용된다.
- 하지만 `"택배"`라는 단어가 있으면 `스팸 경고`로 표시하는 것은 금지다.

예정 산출물:

- `src/inference.py`
- `src/ixissage_ml/`

## 7단계: Android용 sample_messages.json 생성

목표는 실제 SMS 권한 없이 Android 데모를 가능하게 만드는 것이다.

해야 할 일:

- 데이터셋 일부를 샘플 메시지로 변환
- 정상, 주의, 스팸 경고 예시가 고르게 보이도록 구성
- 실제 개인정보가 들어갈 가능성이 있는 값은 마스킹
- 모델 확률 필드를 포함할지, 앱에서 mock classifier가 계산할지 결정

예정 산출물:

- `outputs/sample_messages.json`
- Android assets로 복사할 샘플 JSON

주의:

- 샘플 메시지 생성도 룰 기반 탐지가 아니다.
- 위험 배지는 모델 또는 mock classifier의 확률 값을 표시하는 방식으로 연결한다.

## 8단계: Android Kotlin/Jetpack Compose 데모 앱 생성

목표는 AI 분류 결과를 보기 쉽게 보여주는 앱을 만든다.

초기 화면:

- 메시지 목록
- 발신자
- 본문 미리보기
- 확률 기반 배지
- 필터 또는 정렬은 선택 기능

상세 화면:

- 전체 메시지
- 정상 확률
- 스미싱 확률
- 예측 라벨
- 주의 문구

예정 산출물:

- `android/IxissageApp/`

## 9단계: Mock classifier로 UI 연결

목표는 실제 모델 연결 전에 UI 흐름을 완성하는 것이다.

Mock classifier는 임시 확률을 반환할 수 있다.

하지만 mock classifier에도 금지 사항이 있다.

- 문자 본문에 특정 키워드가 있으면 위험하다고 판단하면 안 된다.
- 샘플 JSON에 미리 들어 있는 `smishingProbability`를 읽어 표시하는 방식은 허용된다.
- 랜덤 또는 고정 확률로 UI 상태를 테스트하는 것도 허용된다.

## 10단계: 실제 모델 추론 연결 준비

목표는 Python 모델 결과를 Android 앱과 연결할 전략을 세운다.

가능한 방향:

- Android 앱은 샘플 JSON에 저장된 추론 결과만 표시
- Python `inference.py`로 샘플 메시지 확률 생성 후 Android assets에 넣기
- TFLite 또는 LiteRT 변환 후 앱 내부에서 로컬 추론

수업 프로젝트에서는 먼저 샘플 JSON 방식으로 데모를 완성한다. 그 다음 시간이 남으면 로컬 온디바이스 추론을 검토한다.

## 11단계: TFLite/LiteRT 변환 검토

목표는 Transformer 모델을 Android에서 직접 실행할 수 있는지 확인한다.

검토할 내용:

- 모델 크기
- tokenizer 처리 방식
- 변환 가능성
- 추론 속도
- Android 메모리 사용량
- 수업 프로젝트 시간 내 구현 가능성

이 단계는 필수 완성 조건이 아니다. 모델 학습, 평가, Android 데모가 먼저다.

## 12단계: READ_SMS 기능 선택 구현

목표는 시간이 남을 때 실제 기기 SMS를 읽어오는 기능을 검토하는 것이다.

주의:

- 실제 SMS 권한은 민감하다.
- Play Store 배포 목표가 없더라도 개인정보를 조심해야 한다.
- 권한 요청 실패 시 sample dataset mode로 돌아간다.
- SMS 본문은 외부 서버로 전송하지 않는다.

이 단계는 선택 기능이다. 프로젝트 완성의 핵심은 AI 모델과 데모 앱이다.

