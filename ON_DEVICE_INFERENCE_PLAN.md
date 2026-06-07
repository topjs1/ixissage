# ON_DEVICE_INFERENCE_PLAN.md

## 목적

이 문서는 `ixissage`의 학습된 Transformer 모델을 Android 온디바이스 추론에 넣을 수 있는지 판단하기 위한 검토 문서다.

이번 단계에서는 변환 코드를 작성하지 않는다. 목표는 수업 발표에서 실제로 보여줄 수 있는 방법을 고르고, 변환이 어려운 이유와 대안을 명확히 설명하는 것이다.

프로젝트의 핵심 제약은 그대로 유지한다.

- 룰 기반 탐지는 구현하지 않는다.
- 키워드 `if`문으로 스미싱 위험을 판단하지 않는다.
- URL 포함 여부, 금액 표현, 기관명 같은 handcrafted risk feature를 만들지 않는다.
- Android 앱은 classifier가 반환한 `normalProbability`, `phishingProbability`, `predictedLabel`만 표시한다.
- UI threshold는 모델 확률을 `정상`, `주의`, `스팸 경고`로 보여주기 위한 표시용이다.

## 현재 학습 모델 상태

현재 저장된 모델 위치:

- `models/smishing_classifier/`

확인 명령:

```bash
du -sh models/smishing_classifier
find models/smishing_classifier -maxdepth 1 -type f -exec ls -lh {} \;
```

확인 결과:

| 항목 | 크기 |
| --- | ---: |
| 전체 모델 디렉터리 | 약 55 MB |
| `model.safetensors` | 약 54 MB |
| `tokenizer.json` | 약 796 KB |
| `vocab.txt` | 약 257 KB |
| `config.json` | 약 910 B |

모델 구조:

- `architectures`: `ElectraForSequenceClassification`
- `model_type`: `electra`
- `hidden_size`: 256
- `num_hidden_layers`: 12
- `num_attention_heads`: 4
- `vocab_size`: 35000
- `max_position_embeddings`: 512
- 라벨: `normal`, `smishing`

해석:

- 55MB는 Android 앱에 넣는 것이 불가능한 크기는 아니다.
- 하지만 모델 파일만 55MB이고, 실제 앱에는 런타임 라이브러리, tokenizer 처리 코드, 입력/출력 처리 코드가 추가된다.
- 현재 파일은 Hugging Face/PyTorch 계열 `safetensors` 모델이다. Android에서 바로 실행할 수 있는 `.tflite`, `.onnx`, `.ort` 파일은 아직 없다.

## 후보 1: Precomputed Inference Demo

방식:

1. Python의 `src/inference.py`가 학습된 Transformer 모델로 샘플 문자들을 추론한다.
2. 추론 결과를 `sample_messages.json`에 저장한다.
3. Android 앱은 `PrecomputedSampleClassifier`를 통해 JSON의 확률을 classifier 결과처럼 반환한다.

현재 프로젝트 상태:

- 이미 `outputs/sample_messages.json`이 생성되어 있다.
- Android assets에도 `sample_messages.json`이 들어 있다.
- Android에는 `SmishingClassifier`, `PrecomputedSampleClassifier`, `MockSmishingClassifier`, `ClassifierProvider` 구조가 있다.

장점:

- 수업 발표에서 가장 안정적으로 시연할 수 있다.
- 모델이 실제로 계산한 확률을 Android UI에 보여줄 수 있다.
- Android 모델 변환, tokenizer 이식, 런타임 호환성 문제를 피할 수 있다.
- 외부 서버로 문자 본문을 보내지 않는다.
- 실제 SMS 권한 없이도 AI 분류 흐름을 보여줄 수 있다.

단점:

- Android 기기 안에서 새 문자를 실시간 추론하는 것은 아니다.
- 발표 중 사용자가 임의로 입력한 새 문자를 Android 앱 내부에서 바로 분류하는 기능은 없다.

판단:

- 이 프로젝트가 상용 제품이 아니라 AI 수업 프로젝트라는 점을 고려하면, 가장 현실적인 1순위 방식이다.
- 발표에서는 “모델 학습과 추론은 Python에서 수행했고, Android는 그 결과를 데모 UI로 표시한다”고 설명하면 된다.

## 후보 2: TFLite

방식:

- 모델을 TensorFlow Lite 형식인 `.tflite`로 변환한다.
- Android에서 TensorFlow Lite Interpreter API 또는 Task API로 실행한다.

장점:

- Android 온디바이스 ML에서 오래 사용된 방식이다.
- `.tflite` 파일은 모바일/엣지 환경을 고려한 포맷이다.
- Android에서 Java/Kotlin API를 사용할 수 있다.

어려운 점:

- 현재 모델은 PyTorch/Hugging Face `ElectraForSequenceClassification`이다.
- 전통적인 TFLite 경로는 TensorFlow 모델을 `.tflite`로 변환하는 흐름에 더 가깝다.
- Transformer 계열 모델은 attention, embedding, dynamic sequence length, token type/attention mask 처리가 필요하다.
- 모델 변환만으로 끝나지 않고 Android에서 WordPiece tokenizer를 동일하게 구현해야 한다.
- 변환 후 Python 원본 모델과 Android 결과가 같은지 parity test가 필요하다.
- 양자화까지 적용하면 크기와 속도는 좋아질 수 있지만, 확률 출력이 달라질 수 있어 재평가가 필요하다.

판단:

- 기술적으로 시도할 수는 있지만 이번 발표의 1순위 구현으로는 위험하다.
- 모델 변환과 tokenizer 이식에 시간이 많이 들고, 실패했을 때 발표 가능한 결과물이 늦어질 수 있다.

## 후보 3: LiteRT

방식:

- LiteRT는 Google AI Edge의 최신 온디바이스 런타임 방향이다.
- `.tflite` 또는 LiteRT 계열 포맷으로 변환한 모델을 Android에서 실행한다.
- 최신 문서 기준 Android에서는 `CompiledModel` API와 `Interpreter` API가 제공된다.

장점:

- Google의 최신 Android 온디바이스 ML 방향과 맞다.
- CPU/GPU/NPU 가속을 고려할 수 있다.
- 장기적으로 Android 앱 내부 추론을 구현한다면 검토 가치가 높다.

어려운 점:

- 현재 프로젝트 모델은 이미 학습된 Hugging Face ELECTRA 모델이다.
- LiteRT 문서상 PyTorch/TensorFlow/JAX 모델 변환 흐름은 있지만, Transformer text classifier 전체 변환은 단순한 import 작업이 아니다.
- Android에서 tokenizer와 전처리 파이프라인을 정확히 재현해야 한다.
- `normalProbability`, `phishingProbability`를 얻기 위한 softmax 후처리를 직접 구현해야 한다.
- 발표 일정 안에서 변환, 최적화, 앱 통합, 정확도 검증을 모두 끝내기는 부담이 크다.

판단:

- 장기 목표로는 의미가 있지만, 이번 수업 발표의 기본 시연 방식으로 삼기에는 리스크가 높다.
- 후속 단계에서 “LiteRT 변환 검토” 또는 “작은 모델로 교체 후 변환”을 실험하는 편이 안전하다.

## 후보 4: ONNX Runtime Mobile

방식:

1. Hugging Face Transformer 모델을 ONNX로 export한다.
2. Android 앱에 ONNX Runtime Mobile 또는 `onnxruntime-android`를 추가한다.
3. Android에서 tokenizer 결과를 `input_ids`, `attention_mask`, `token_type_ids` 텐서로 만들어 ONNX 모델에 넣는다.
4. 출력 logits에 softmax를 적용해 확률을 계산한다.

장점:

- Hugging Face/PyTorch 모델은 ONNX export 경로가 비교적 자연스럽다.
- Hugging Face 문서에서 Transformer 모델을 ONNX로 export하는 기능을 제공한다.
- ONNX Runtime은 Android Java/Kotlin 의존성을 제공한다.
- TFLite보다 PyTorch Transformer에서 출발하기 쉬울 가능성이 있다.

어려운 점:

- ONNX 모델도 문자 본문을 직접 받지 않는다. Android에서 tokenizer를 별도로 구현해야 한다.
- ONNX export가 성공해도 Android Runtime에서 필요한 operator가 모두 잘 동작하는지 확인해야 한다.
- ONNX Runtime AAR와 모델 파일을 포함하면 APK 크기가 증가한다.
- 속도와 메모리 사용량은 실제 기기에서 측정해야 한다.
- 모델 최적화, 양자화, ORT format 변환까지 가면 작업량이 커진다.

판단:

- 실제 Android 온디바이스 추론을 꼭 보여줘야 한다면 TFLite/LiteRT보다 먼저 검토할 만한 대안이다.
- 하지만 이번 프로젝트의 발표 안정성을 기준으로는 1순위가 아니다.

## 모델 변환이 어려운 핵심 이유

현재 모델을 Android에 바로 넣기 어려운 이유는 모델 크기 하나만의 문제가 아니다.

1. 모델 포맷 문제

   현재 모델은 `model.safetensors`로 저장된 Hugging Face/PyTorch 모델이다. Android 런타임에서 바로 실행하려면 `.onnx`, `.ort`, `.tflite` 같은 모바일 런타임 포맷으로 변환해야 한다.

2. tokenizer 문제

   모델은 raw string을 입력받지 않는다. Python에서는 Hugging Face tokenizer가 문자 본문을 `input_ids`, `attention_mask`, `token_type_ids`로 바꾼다. Android에서도 같은 tokenizer 결과를 만들어야 Python과 같은 확률을 기대할 수 있다.

3. Transformer operator 문제

   ELECTRA는 embedding, self-attention, layer normalization, GELU, classification head 등을 포함한다. 변환된 모델이 모바일 런타임의 지원 operator와 정확히 맞는지 확인해야 한다.

4. 정확도 검증 문제

   변환 모델은 Python 원본 모델과 같은 입력에 대해 거의 같은 확률을 내야 한다. 이 검증 없이 Android 결과를 발표하면 모델 품질을 신뢰하기 어렵다.

5. 최적화 문제

   55MB 모델은 데모 앱에 넣을 수 있지만, 수업 발표 기기의 성능에 따라 로딩 시간, 추론 속도, 메모리 사용량이 문제가 될 수 있다. 양자화를 적용하면 크기와 속도는 좋아질 수 있으나 정확도 재평가가 필요하다.

## 추천 방식

추천 1순위:

- **Precomputed inference demo**

추천 이유:

- 이번 프로젝트의 목적은 보안 제품 출시가 아니라 AI 분류 흐름을 보여주는 것이다.
- 이미 학습된 Transformer 모델의 실제 확률을 `sample_messages.json`에 저장할 수 있다.
- Android 앱은 classifier 인터페이스를 통해 결과를 받아 UI에 표시하므로 구조적으로도 향후 온디바이스 모델 교체가 가능하다.
- 발표 리스크가 가장 낮다.
- 룰 기반 탐지 없이 AI 모델 중심 프로젝트라는 제약을 명확히 지킬 수 있다.

발표 설명 문장:

> Android 앱은 문자 본문을 직접 규칙으로 판단하지 않습니다. Python에서 학습된 Transformer 모델이 계산한 정상/스미싱 확률을 JSON에 저장하고, 앱은 classifier 인터페이스를 통해 그 확률을 표시합니다. 실제 온디바이스 추론은 후속 확장 과제로 LiteRT 또는 ONNX Runtime Mobile을 검토했습니다.

## 구현 업데이트: Android On-device Baseline

이 문서 작성 이후, 발표 안정성과 실제 온디바이스 동작을 모두 만족시키기 위해 `TF-IDF + Logistic Regression` baseline 모델을 Android에 이식했다.

구현 파일:

- `scripts/export_baseline_android.py`
- `android/IxissageApp/app/src/main/assets/baseline_tfidf_logreg.json`
- `android/IxissageApp/app/src/main/java/com/ixissage/app/classifier/OnDeviceBaselineClassifier.kt`

현재 Android 앱은 `baseline_tfidf_logreg.json`에 저장된 학습된 vocabulary, IDF, logistic regression weight를 읽고, Kotlin에서 직접 TF-IDF와 sigmoid probability를 계산한다.

이 방식은 다음 점에서 온디바이스 AI 데모로 더 적합하다.

- Android 앱 내부에서 직접 확률을 계산한다.
- 외부 서버 호출이 없다.
- 룰 기반 탐지가 아니다.
- 키워드 `if`문이나 URL 존재 여부 rule을 쓰지 않는다.
- Transformer보다 단순하지만, 수업 발표에서 “기기 내부 ML 추론”을 보여주기에 현실적이다.

정확한 발표 표현:

> Transformer 모델은 Python 로컬 환경에서 fine-tuning과 평가를 완료했습니다. Android 앱에는 실제 온디바이스 동작을 보여주기 위해 TF-IDF + Logistic Regression baseline 모델을 이식했고, 앱 내부 Kotlin 코드가 직접 확률을 계산합니다.

## 대안 1

대안 1:

- **ONNX Runtime Mobile**

적합한 경우:

- 발표 이후 Android에서 실제 새 문자 입력을 온디바이스로 분류하고 싶을 때
- PyTorch/Hugging Face 모델을 유지하면서 모바일 런타임으로 옮기고 싶을 때

필요 작업:

- Hugging Face 모델 ONNX export
- Android ONNX Runtime 의존성 추가
- Android tokenizer 구현 또는 호환 라이브러리 검토
- logits softmax 후처리 구현
- Python 결과와 Android 결과 parity test
- APK 크기, 추론 시간, 메모리 측정

## 대안 2

대안 2:

- **LiteRT/TFLite 변환**

적합한 경우:

- Google Android 온디바이스 ML 생태계에 맞춰 장기적으로 최적화하고 싶을 때
- 모델을 더 작게 만들거나 mobile-friendly architecture로 바꿀 시간이 있을 때

필요 작업:

- PyTorch/Hugging Face ELECTRA 모델을 LiteRT/TFLite 호환 포맷으로 변환
- operator 호환성 확인
- tokenizer와 전처리 Android 구현
- softmax 후처리 구현
- 양자화 전후 성능 비교
- 실제 기기 추론 속도 측정

## 발표용 권장 구현 범위

이번 발표에서는 다음 범위가 가장 현실적이다.

1. Python 학습/평가 결과를 보여준다.
2. `src/inference.py`로 단일 문자 추론이 가능함을 보여준다.
3. `sample_messages.json`에 저장된 모델 확률을 Android 앱에서 표시한다.
4. Android 앱 코드에서는 `SmishingClassifier` 인터페이스를 통해 classifier 결과만 UI에 연결한다.
5. 온디바이스 추론은 후속 확장으로 ONNX Runtime Mobile과 LiteRT/TFLite를 비교해 설명한다.

이 방식은 “AI 모델이 어떤 역할을 하는지 보여주는 수업 프로젝트”라는 목적에 맞고, 룰 기반 탐지 금지 제약도 지킨다.

## 참고 자료

- LiteRT for Android: https://developers.google.com/edge/litert/android
- LiteRT overview: https://developers.google.com/edge/litert/overview
- TensorFlow Lite guide: https://android.googlesource.com/platform/external/tensorflow/+/HEAD/tensorflow/lite/g3doc/guide/index.md
- TensorFlow Lite for Android: https://android.googlesource.com/platform/external/tensorflow/+/main/tensorflow/lite/g3doc/android/index.md
- ONNX Runtime Mobile: https://onnxruntime.ai/docs/get-started/with-mobile.html
- ONNX Runtime install for Android: https://onnxruntime.ai/docs/install/
- Hugging Face Transformers ONNX export: https://huggingface.co/docs/transformers/master/main_classes/onnx

확인일: 2026-06-07
