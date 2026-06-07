# Inference Examples

Generated at UTC: `2026-06-07T09:08:49.298838+00:00`

These examples use the fine-tuned Transformer model. The model input is message text only.

No rule-based detection, keyword if-statements, or handcrafted risk features are used.

| # | text | predictedLabel | normalProbability | phishingProbability |
| ---: | --- | --- | ---: | ---: |
| 1 | 오늘 저녁 7시에 도서관 앞에서 만나자. 늦으면 문자할게. | normal | 0.951976 | 0.048024 |
| 2 | 수업 과제 제출 확인했습니다. 다음 주 발표 준비해 주세요. | normal | 0.695292 | 0.304708 |
| 3 | 엄마 나 휴대폰이 고장나서 임시로 문자하고 있어. 급하게 송금 좀 부탁해. | smishing | 0.054932 | 0.945068 |
| 4 | [국외발신] 고객님 계정이 해외 IP에서 로그인되었습니다. 본인 확인을 진행해 주세요. | smishing | 0.022169 | 0.977831 |
| 5 | 주문하신 상품이 배송 완료되었습니다. 이용해 주셔서 감사합니다. | normal | 0.734457 | 0.265542 |
