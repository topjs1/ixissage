# Baseline Report

## Scope

This is the first ixissage baseline model: TF-IDF + Logistic Regression.

- Input feature: message `content` text only
- Label mapping: `class=1 -> normal`, `class=2 -> smishing`
- Excluded from this first binary baseline: `class=3`
- No rule-based smishing detection
- No keyword if-statements
- No manual URL or handcrafted risk features

## Data Split

- Train rows: `9412`
- Dev rows: `2017`
- Test rows: `2018`
- Train label counts: `{'normal': 4043, 'smishing': 5369}`
- Dev label counts: `{'normal': 866, 'smishing': 1151}`
- Test label counts: `{'normal': 867, 'smishing': 1151}`
- Binary rows before dedup: `16309`
- Binary rows after dedup: `13447`
- Same-label duplicate rows removed: `2862`
- Conflicting duplicate contents removed: `0`

Exact duplicate message bodies were removed before splitting to reduce train/test leakage.

## Test Metrics

| metric | value |
| --- | ---: |
| accuracy | 0.992567 |
| precision | 0.997373 |
| recall | 0.989574 |
| F1 | 0.993458 |

Positive class is `smishing`.

## Confusion Matrix

| actual \ predicted | normal | smishing |
| --- | ---: | ---: |
| normal | 864 | 3 |
| smishing | 12 | 1139 |

## False Positive Examples

False positive means true `normal`, predicted `smishing`.
Total false positives in this split: `3`. Showing `3` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-000916 | normal | smishing | 0.1957 | 0.8043 | 안녕하세요 형도니오빠! |
| 2 | baseline-000883 | normal | smishing | 0.4884 | 0.5116 | 댓글 잘읽었습니다. |
| 3 | baseline-000770 | normal | smishing | 0.4942 | 0.5058 | 훈훈 합니다^^.굿 |

## False Negative Examples

False negative means true `smishing`, predicted `normal`.
Total false negatives in this split: `12`. Showing `10` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-000028 | smishing | normal | 0.8137 | 0.1863 | 아빠~ 지금 구글기프트카드가 좀 필요한데 시간 괜찮으면 대신 먼저 구매해줄수 잇어? 지금 인증서오류땜에 안되네ㅠ 실은 내가 지금 부업으로 외국에 있는 애들 상대로 게임 충전카드를 판매하고 있어 이거 수익이 너무 좋아 내가 대신 구매해주는 건데 100만원 당 20만 가까이 수수료 벌거든 |
| 2 | baseline-000052 | smishing | normal | 0.7961 | 0.2039 | 형수님 죄송한대 제가 지금 호주에 와있거든요.. 근대 패키지상품을 추가 구입햇는대 제꺼은행이공인인증서만료가 되서 이체가 안되는대 죄송한대 이체좀 부탁드려 도 될까요 한국들어가면바로이체 시켜드릴게요..ㅜㅜ 92만원이요ㅠㅠ 입금자명은 제 이름으로 부탁좀 드릴게요.. |
| 3 | baseline-013110 | smishing | normal | 0.7498 | 0.2502 | 퇴근은 잘 하셨나요? 대한민국 vs 이란 얼마 남지도 않았네요 같이 치킨먹으면서 응원해요 '*만' 지급 주소창에 성대리 쩜 컴 |
| 4 | baseline-008506 | smishing | normal | 0.7267 | 0.2733 | 모두가 할 수 있지만 누구나 할 수 없는 필승전략 분석 픽 최반장.net |
| 5 | baseline-000027 | smishing | normal | 0.6796 | 0.3204 | 응 나 뭐하나 부탁해도 돼? 지금 편의점가서 구글기프트카드 20만권 3장 사줄수있어? 수수료 벌려고 그래 |
| 6 | baseline-000355 | smishing | normal | 0.6573 | 0.3427 | [Web발신] 아 빠 나지금폰 액정나가서 <NUM> 이번호로 톡/추가 하고 탑줘 통화안되 폰 떨어뜨려서 액정이 나가서 인터넷 문자싸이트로 인증한 1회용 pc톡이야 부탁할거있는데 시간되? 아빠 지금 시간되면 잠깐 편의점 다녀올수있어? 아무 편의점가서 구글기프트카드30만원어치 구매해줘.구매후 개봉하고 카드뒷면에 라벨 긁으면 나오는 코드번호 여기로보내줘 혹시누가 사용하는지 물어보면 아빠가 사용한다고하면 돼 부탁할게 글구 편의점 알바들 그코드번호를 엿보고 도용하는... |
| 7 | baseline-000364 | smishing | normal | 0.6401 | 0.3599 | 엄마 바뻐 ? 나 지금 폰이 고장나서 수리 맡기고 컴으로 카톡 하고있어 어 안대 수리 맡겻어 엄마 머한느데? 낼 오전 쯤에 찾을수 잇을거야 언제 집에가는데/.? 문상필요하다니깐 엄마 사주면 안대? ㅎㅎ 문화상품권 엄마 나 폰 없어서 살수없어서 그래 위메프서 사면 10장 9만원이야 위메프서 사 아니 <NUM>짜리야 위메프서 문화상품권 검색하면 나와 이런거 이거 사면 대 10장 그리고 결제하면 핀번호가 엄마 폰으로 올거야 그걸 나한테 보내줘 엄마 부탁할게 엄마... |
| 8 | baseline-008601 | smishing | normal | 0.6293 | 0.3707 | [돈 벌기 힘들다?]NO NO...방법이 틀려서 그렇다돈버는 노하우 공개클릭▶ 서울정보.com |
| 9 | baseline-000005 | smishing | normal | 0.5656 | 0.4344 | 엄마~ 바빠? 엄마 나 급한 일이 좀 생겨서… 지금 98만원만 입금해 줄 수 있어?+C6 |
| 10 | baseline-000351 | smishing | normal | 0.5440 | 0.4560 | 엄마 뭐해?나 핸드폰 액정이나가서 수리센터에 수리맡기고 전에 내 명의로 가입해놨던 인터넷 문자 사이트로 엄마한테 문자 하는거야 급하게 부탁이 있어! 컴퓨터 문자사이트로 하는거라 문자만 가능해 통화가 안되니깐 확인하면 답장줘~ 엄마 나 급한일이 있어서 그래 문자로 하기 불편하니까 일단 <NUM> 이번호로 카톡 추가해줘 인터넷으로 카톡하나 만들었어 엄마 지금 컬쳐랜드 회사에서 구글기프트카드 재테크 땜에 이벤트진행중인데 편의점 가면은 구글기프트 카드 파는거 있어... |

## Artifacts

- Model: `models/baseline_tfidf_logreg.joblib`
- Evaluated split: `data/processed/test.csv`
- Metrics JSON: `outputs/baseline_metrics.json`
- Confusion matrix CSV: `outputs/confusion_matrix_baseline.csv`

## Notes

This baseline is useful as a reproducible reference point. It should not be treated as a production security system.
