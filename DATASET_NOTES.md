# DATASET_NOTES.md

## 목적

이 문서는 `ixissage`의 첫 번째 학습 후보 데이터셋인 Hugging Face `meal-bbang/Korean_message`를 모델 학습 전에 이해하기 위해 작성했다.

중요한 전제:

- 이 프로젝트는 생성형 AI가 아니라 supervised text classification 프로젝트다.
- 문자 본문 `content`를 입력으로 받고 `class` 라벨을 예측한다.
- 룰 기반 스미싱 탐지는 구현하지 않는다.
- `"택배"`, `"미납"`, `"URL"`, `"환급"`, `"본인인증"` 같은 키워드를 if문으로 검사해서 위험 판단하지 않는다.
- 데이터 분석에서 발견한 패턴은 모델/데이터 이해용이며, Android 또는 inference 코드의 위험 판단 규칙으로 옮기면 안 된다.

## 확인한 페이지

필수 확인 페이지:

- https://huggingface.co/datasets/meal-bbang/Korean_message

라이선스/사용상 주의 확인:

- https://huggingface.co/datasets/meal-bbang/Korean_message/discussions/3

조사일:

- 2026-06-07

## 데이터셋 목적

Hugging Face 데이터셋 카드 기준으로 `meal-bbang/Korean_message`는 한국어 스팸 메시지 탐지를 위한 텍스트 분류 데이터셋이다.

Hugging Face 페이지에서 확인한 메타 정보:

- Task: `Text Classification`
- Modalities: `Tabular`, `Text`
- Format: `csv`
- Size: `10K - 100K`
- Subset: `default`
- Split: `train`
- Viewer 표시: 약 `19k rows`
- 파일: `lgaidataset.csv`
- 파일 크기: 약 `2.84 MB`

현재 Hugging Face viewer에는 `train` split 하나만 표시된다. 따라서 학습 단계에서는 프로젝트 코드에서 직접 train/dev/test split을 만들어야 한다.

## 다운로드 스크립트

생성한 스크립트:

- `scripts/download_dataset.py`

역할:

- Hugging Face CSV를 `data/raw/lgaidataset.csv`로 다운로드한다.
- raw CSV가 이미 존재하면 절대 덮어쓰지 않고 건너뛴다.
- 다운로드한 raw 파일의 byte size와 SHA256을 기록한다.
- `data/raw/lgaidataset.metadata.json`에 원본 URL, 다운로드 시각, SHA256을 저장한다.

실행 결과:

- Raw CSV: `data/raw/lgaidataset.csv`
- Metadata: `data/raw/lgaidataset.metadata.json`
- Bytes: `2,840,339`
- SHA256: `d56a0c0aea67df0ad3bc783fad37dc56cbe2b64c531e3f335a43befce08abe0d`

주의:

- raw data는 절대 overwrite하지 않는다.
- raw 파일을 정제하거나 split한 결과는 `data/processed/` 아래에 저장한다.

## 검사 스크립트

생성한 스크립트:

- `scripts/inspect_dataset.py`

역할:

- 컬럼 확인
- label 1과 label 2 의미 출력
- 전체 행 수 확인
- class balance 확인
- null 확인
- duplicate 확인
- 문자 길이 분포 확인
- 정상 문자 10개와 스미싱 문자 10개 샘플 출력
- label 3 샘플 일부 출력
- 검사 결과를 `data/processed/`에 저장

생성된 processed 산출물:

- `data/processed/dataset_inspection_summary.json`
- `data/processed/dataset_inspection_report.md`

이 스크립트는 모델 학습을 하지 않는다. 또한 키워드 기반 위험 판단 로직을 만들지 않는다. 샘플 출력의 긴 숫자열은 기본적으로 `<NUM>`으로 마스킹한다.

## 컬럼 구조

실제 CSV 컬럼:

| column | type in viewer | 설명 |
| --- | --- | --- |
| `index` | int64 | 원본 인덱스 또는 ID성 값 |
| `content` | string | 문자 메시지 본문, 모델 입력 후보 |
| `class` | int64 | 라벨 |

주의:

- CSV를 잘못 읽으면 첫 컬럼명이 BOM 때문에 `\ufeffindex`처럼 보일 수 있다.
- `scripts/inspect_dataset.py`는 `utf-8-sig`로 읽어서 BOM을 제거한다.
- `index`는 결측치가 있고 학습 feature가 아니므로 모델 입력에 사용하지 않는다.

## label 1과 label 2의 의미

Hugging Face 데이터셋 카드 기준:

| label | 의미 |
| --- | --- |
| `1` | 일상 문자 / ordinary message |
| `2` | 피싱 또는 스미싱 문자 / phishing or smishing message |

`ixissage`의 첫 binary classification 실험에서는 기본적으로 다음 매핑을 사용한다.

- `class=1` -> `normal`
- `class=2` -> `smishing`

단, 실제 CSV에는 `class=3`도 있으므로 최종 학습 데이터 구성은 EDA 이후 명시적으로 결정해야 한다.

## 전체 행 수

`scripts/inspect_dataset.py` 실행 결과:

- 전체 row 수: `19,009`

Hugging Face viewer의 약 `19k rows` 표시와 일치한다.

## class balance

실제 CSV 기준 라벨 분포:

| class | count | percentage | 현재 이해 |
| --- | ---: | ---: | --- |
| `1` | 5,778 | 30.40% | 일상 문자 |
| `2` | 10,531 | 55.40% | 피싱/스미싱 문자 |
| `3` | 2,700 | 14.20% | 데이터셋 카드에 의미가 명시되지 않음 |

해석:

- `class=2`가 가장 많다.
- binary 실험에서 `class=1`과 `class=2`만 쓰면 총 `16,309`개를 사용할 수 있다.
- `class=3`은 의미가 불명확하므로 조용히 normal로 합치지 않는다.

## null 확인

실행 결과:

| column | null count |
| --- | ---: |
| `index` | 2,700 |
| `content` | 0 |
| `class` | 0 |

해석:

- 모델 입력인 `content`에는 결측치가 없다.
- 라벨인 `class`에도 결측치가 없다.
- `index` 결측치는 대부분 `class=3` 샘플과 연결되어 보인다.
- `index`는 학습 feature로 쓰지 않을 예정이므로 치명적인 문제는 아니다.

## duplicate 확인

실행 결과:

| 항목 | count |
| --- | ---: |
| duplicate content rows | 3,149 |
| duplicated content values | 2,690 |
| duplicate full rows | 292 |

의미:

- `duplicate_content_rows`는 중복 본문 때문에 추가로 존재하는 row 수다.
- `duplicated_content_values`는 두 번 이상 등장한 고유 본문 수다.
- `duplicate_full_rows`는 모든 컬럼 값이 완전히 같은 중복 row 수다.

학습 전 주의:

- train/dev/test split 전에 중복 처리 방침을 정해야 한다.
- 같은 본문이 train과 test에 동시에 들어가면 평가 성능이 부풀 수 있다.
- 중복 제거 여부는 baseline 리포트에 기록한다.

## 문자 길이 분포

`content` 문자열 길이 기준:

| statistic | value |
| --- | ---: |
| min | 4 |
| p25 | 32 |
| median | 50 |
| mean | 67.85 |
| p75 | 63 |
| p90 | 140 |
| p95 | 186 |
| p99 | 432 |
| max | 1,223 |

해석:

- 대부분의 메시지는 짧다.
- 일부 긴 메시지가 존재하므로 Transformer 학습 시 `max_length`를 정해야 한다.
- 긴 문장을 자르는 truncation은 허용되는 전처리다.
- 단, 길이나 특정 단어를 이용해 수동 위험 점수를 만들면 안 된다.

## 샘플 출력

`scripts/inspect_dataset.py`는 다음 샘플을 터미널과 `data/processed/dataset_inspection_report.md`에 출력한다.

- `class=1` 정상 문자 10개
- `class=2` 스미싱 문자 10개
- `class=3` 확인용 샘플 최대 5개

샘플은 데이터 이해용이다. 샘플에서 보이는 단어나 표현을 기반으로 if문 탐지 규칙을 만들면 안 된다.

## label 3 문제

실제 CSV에는 `class=3`이 `2,700`개 존재한다.

문제:

- Hugging Face 데이터셋 카드에는 `label 3` 의미가 명시되어 있지 않다.
- `class=3` 샘플에는 우체국 배송 완료처럼 정상 알림성 문자로 보이는 내용이 포함되어 있다.
- 하지만 공식 라벨 설명이 없으므로 바로 `normal`로 병합하면 재현성과 설명력이 떨어진다.

권장 처리 순서:

1. 첫 baseline은 `class=1`과 `class=2`만 사용한다.
2. `class=3` 샘플을 별도 분석한다.
3. 필요하면 `class=1 + class=3`을 normal로 병합한 실험을 별도 리포트로 비교한다.
4. 또는 `1/2/3` multi-class 모델을 학습한 뒤 앱에서는 `class=2` 확률만 스미싱 확률로 사용할 수 있다.

## split 가능성

현재 Hugging Face viewer에는 `train` split만 있다.

권장 split:

- train: 70%
- dev: 15%
- test: 15%

또는:

- train: 80%
- dev: 10%
- test: 10%

필수 조건:

- stratified split 사용
- random seed 고정
- split 결과는 `data/processed/`에 저장
- raw CSV는 수정하지 않음
- 중복 본문이 split을 가로질러 누수되지 않도록 확인

## 라이선스와 사용상 주의

Hugging Face 데이터셋 카드에는 명확한 라이선스가 표시되어 있지 않다.

라이선스 discussion에서 데이터셋 작성자는 다음 취지로 답했다.

- 데이터는 생성형 AI로 만든 택배 문자, 스팸 문자, 일상 문자와 여러 소스의 데이터를 보완해 구성했다.
- 일부 소스는 사이트가 없어졌거나 라이선스가 명시되어 있지 않아 작성자가 확인 가능한 범위가 제한적이다.
- 법적 문제가 중요한 상업적 이용이라면 사용하지 않는 편이 가장 좋다.

`ixissage` 대응:

- 이 프로젝트는 상용 출시용이 아니라 수업 프로젝트다.
- Google Play Store 배포를 목표로 하지 않는다.
- README와 발표 자료에 데이터셋 출처와 라이선스 불명확성을 명시한다.
- 상용 서비스나 실제 보안 제품처럼 사용하지 않는다.

## Android 샘플 데이터 사용 주의

Android 데모는 실제 SMS 권한 없이 sample dataset mode로 시작한다.

주의:

- `sample_messages.json`은 `data/processed/` 또는 `outputs/`에서 생성한다.
- 실제 개인정보처럼 보이는 전화번호, 계좌번호, 긴 숫자열은 가능한 마스킹한다.
- Android 앱은 모델 확률 또는 샘플 JSON의 확률을 표시한다.
- Android에서 메시지 본문 키워드를 검사해 위험 배지를 결정하면 안 된다.

## 현재 결론

`meal-bbang/Korean_message`는 `ixissage`의 첫 데이터셋으로 사용할 수 있다.

현재 확인된 핵심 사실:

- 총 `19,009` rows
- 컬럼은 `index`, `content`, `class`
- `label 1`은 일상 문자
- `label 2`는 피싱/스미싱 문자
- `label 3`은 의미가 명시되지 않음
- `content`와 `class`에는 결측치가 없음
- 중복 본문이 있으므로 split 전에 처리 방침 필요
- train split만 있으므로 직접 train/dev/test split 필요
- 라이선스가 명확하지 않으므로 상용 사용은 피해야 함

다음 구현 단계는 모델 학습이 아니라 `data/processed/`에 재현 가능한 split/정제 후보를 만드는 것이다. 그때도 룰 기반 탐지 코드는 만들지 않는다.

