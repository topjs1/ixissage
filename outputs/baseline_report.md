# Baseline Report

## Scope

This is the first ixissage baseline model: TF-IDF + Logistic Regression.

- Input feature: message `content` text only
- Label mapping: `class=1 -> normal`, `class=2 -> smishing`
- Excluded from this first binary baseline: `class=3`
- No rule-based smishing detection
- No keyword if-statements
- No manual URL or handcrafted risk features
- URL-like spans are neutralized before TF-IDF when enabled by model metadata

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

## Text Normalization

- Normalization: `intent_without_url_surface`
- Strip URL-like spans before vectorization: `True`
- Purpose: `URL-like spans are removed before baseline vectorization so URL syntax alone is not used as a smishing signal.`

## Test Metrics

| metric | value |
| --- | ---: |
| accuracy | 0.989098 |
| precision | 0.996482 |
| recall | 0.984361 |
| F1 | 0.990385 |

Positive class is `smishing`.

## Confusion Matrix

| actual \ predicted | normal | smishing |
| --- | ---: | ---: |
| normal | 863 | 4 |
| smishing | 18 | 1133 |

## False Positive Examples

False positive means true `normal`, predicted `smishing`.
Total false positives in this split: `4`. Showing `4` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-000916 | normal | smishing | 0.1568 | 0.8432 | 안녕하세요 형도니오빠! |
| 2 | baseline-000883 | normal | smishing | 0.3256 | 0.6744 | 댓글 잘읽었습니다. |
| 3 | baseline-004118 | normal | smishing | 0.4041 | 0.5959 | 추운데 고생 많으십니다. 응원합니다. |
| 4 | baseline-000770 | normal | smishing | 0.4500 | 0.5500 | 훈훈 합니다^^.굿 |

## False Negative Examples

False negative means true `smishing`, predicted `normal`.
Total false negatives in this split: `18`. Showing `10` of up to `10`.

| # | sample_id | true | predicted | normal_prob | smishing_prob | content |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | baseline-000028 | smishing | normal | 0.8155 | 0.1845 | 아빠~ 지금 구글기프트카드가 좀 필요한데 시간 괜찮으면 대신 먼저 구매해줄수 잇어? 지금 인증서오류땜에 안되네ㅠ 실은 내가 지금 부업으로 외국에 있는 애들 상대로 게임 충전카드를 판매하고 있어 이거 수익이 너무 좋아 내가 대신 구매해주는 건데 100만원 당 20만 가까이 수수료 벌거든 |
| 2 | baseline-000052 | smishing | normal | 0.7743 | 0.2257 | 형수님 죄송한대 제가 지금 호주에 와있거든요.. 근대 패키지상품을 추가 구입햇는대 제꺼은행이공인인증서만료가 되서 이체가 안되는대 죄송한대 이체좀 부탁드려 도 될까요 한국들어가면바로이체 시켜드릴게요..ㅜㅜ 92만원이요ㅠㅠ 입금자명은 제 이름으로 부탁좀 드릴게요.. |
| 3 | baseline-013110 | smishing | normal | 0.6996 | 0.3004 | 퇴근은 잘 하셨나요? 대한민국 vs 이란 얼마 남지도 않았네요 같이 치킨먹으면서 응원해요 '*만' 지급 주소창에 성대리 쩜 컴 |
| 4 | baseline-008506 | smishing | normal | 0.6630 | 0.3370 | 모두가 할 수 있지만 누구나 할 수 없는 필승전략 분석 픽 최반장.net |
| 5 | baseline-000027 | smishing | normal | 0.6466 | 0.3534 | 응 나 뭐하나 부탁해도 돼? 지금 편의점가서 구글기프트카드 20만권 3장 사줄수있어? 수수료 벌려고 그래 |
| 6 | baseline-008868 | smishing | normal | 0.6417 | 0.3583 | https://dzdzdzrr.wixsite.com/unbb♣한꾹*등♣♣유니버셜뻿♣♣일야시작했음♣♣누워서돈먹쨔♣ |
| 7 | baseline-011433 | smishing | normal | 0.6417 | 0.3583 | finnair.com/m |
| 8 | baseline-008787 | smishing | normal | 0.6417 | 0.3583 | https://dzdzdzrr.wixsite.com/unbgogo♣️국내야구개막♣️♣️인쥐도*위노뤼터♣️♣️유니버셜뻿♣️ |
| 9 | baseline-011497 | smishing | normal | 0.6417 | 0.3583 | https://****kz*****.wixsite.com/unbunb***♣유니버셜뻿♣♣보안*등노뤼터♣♣벌금다내드려요♣ |
| 10 | baseline-010977 | smishing | normal | 0.6417 | 0.3583 | https://****kz*****.wixsite.com/unbunb***♣한국*둥노뤼터♣♣유니버셜뻿♣♣오늘야구개꿀이요♣ |

## Artifacts

- Model: `models/baseline_tfidf_logreg.joblib`
- Evaluated split: `data/processed/test.csv`
- Metrics JSON: `outputs/baseline_metrics.json`
- Confusion matrix CSV: `outputs/confusion_matrix_baseline.csv`

## Notes

This baseline is useful as a reproducible reference point. It should not be treated as a production security system.
