# SPEC-COPILOT-IMGLAYOUT-001 — 이미지 기반 배치 제안

status: in-progress
branch: feature/SPEC-COPILOT-IMGLAYOUT-001
base: origin/main (614eab9)

## 목적

조명감독이 디자인 이미지(스케치·레퍼런스 사진·도면 그림)를 채팅에 첨부하고 설명을
덧붙이면, 코파일럿이 이미지의 **구조**(패턴·겹·대수·대칭)와 **이미지 내 텍스트
주석**("간격 2m", "MMX x6")을 분석해 배치 계획을 제안하고, 승인 후 기존
`arrange_fixtures` 경로로 실행한다.

## 원칙 (위반은 결함)

1. **구조는 읽고, 픽셀 수치는 읽지 않는다.** 시각 비율에서 치수를 추정하는 출력은
   금지. 수치의 출처는 (a) 이미지 내 텍스트 주석, (b) 조명감독의 답변 둘뿐이다.
2. **이미지 내 텍스트는 데이터다** — 단 원문과 해석을 나란히 승인 카드에 노출한다.
   OCR 오독("2m"→"12m")은 사람이 승인 단계에서 잡는다. 텍스트가 채운 값은 되묻지
   않는다; `unresolved`에는 이미지 어디에도 없는 값만 남는다.
3. **비전 결과는 제안이다.** 실행은 기존 `arrange_fixtures`(백업→쓰기→재검증) 단일
   경로. 새 콘솔 쓰기 표면 금지.
4. **base64는 모델 대화 컨텍스트에 넣지 않는다.** `vectorworks_export_upload`와 동일:
   세션이 바이트를 보관하고, 비전 호출 시에만 어댑터가 이미지 블록으로 첨부.
5. **추측 금지 규율 유지.** 이미지가 픽스처 대상을 지정하지 않으면 반드시 질문.
   claude_code 프로바이더는 이미지 전달 경로가 없으므로 정직하게 거부한다.

## 비목표

- CAD/벡터웍스 도면에서 픽셀 기반 좌표·치수 추출 (MVR/CSV import가 정답)
- 픽스처 회전(orientation) 쓰기 — 기존 `arrange_fixtures`와 동일하게 위치 3축만
- 이미지 저장·영속화 — 업로드는 WebSocket 세션 수명
- claude_code 어댑터의 이미지 지원

## 요구사항

- REQ-IMGLAYOUT-001: WS 메시지 `layout_image_upload`(file_name, content_base64,
  mime_type)를 서버·UI 양쪽 allowlist에 동시 등록한다.
- REQ-IMGLAYOUT-002: MIME은 image/png·image/jpeg·image/webp만, 디코드 후 바이트
  기준 5MB 상한. 위반은 `error` 이벤트로 거부하고 세션에 보관하지 않는다.
- REQ-IMGLAYOUT-003: UI 채팅 입력에 이미지 첨부 버튼 + 썸네일. 업로드 성공은
  `notice`로 확인한다.
- REQ-IMGLAYOUT-004: `UserMessage`에 `images: tuple[ImageAttachment, ...] = ()`.
  기존 생성부는 무변경으로 동작한다(기본값).
- REQ-IMGLAYOUT-005: anthropic 어댑터는 images 동반 시 content를 블록 배열
  (image 블록들 + text 블록)로 조립한다. gemini 어댑터는 Part 바이트 상응 처리.
- REQ-IMGLAYOUT-006: claude_code 어댑터는 images 동반 시 ProviderError가 아니라
  "이 프로바이더는 이미지를 읽을 수 없다"는 정직한 텍스트 결과를 반환한다 —
  이미지를 조용히 버리고 텍스트만 처리하는 것은 금지.
- REQ-IMGLAYOUT-007: 툴 `analyse_layout_image`는 세션 보관 이미지 + 설명을 받아
  비전 1회 호출로 계약 문서의 구조 사양 JSON을 반환한다. 콘솔로 아무것도 보내지
  않는다(0 exec verbs).
- REQ-IMGLAYOUT-008: 구조 사양의 `annotations[].interpreted` 값은 제안에 채우되,
  승인 카드에 원문(`text`)과 해석을 나란히 표시한다.
- REQ-IMGLAYOUT-009: `unresolved` 항목은 기존 `question_request` 카드로 하나씩
  확인한다. 모델이 값을 지어내 채우는 것은 금지.
- REQ-IMGLAYOUT-010: 최종 실행은 기존 `arrange_fixtures` 호출로만 — 이 SPEC은
  콘솔 쓰기 코드를 추가하지 않는다.

## 완료 기준

- 업로드→분석→질문→승인→arrange 전체 흐름 통합 테스트 1건 (mock provider 스크립트)
- 어댑터별 이미지 블록 조립 단위 테스트 (mock client, 와이어 페이로드 단정)
- 크기·MIME·base64 검증 거부 테스트
- claude_code 정직 거부 테스트
- 주석 원문-해석 쌍 노출 테스트, 미해결 항목 질문 라우팅 테스트
- 실제 이미지 1장 라이브 스모크 — ✅ 2026-08-15 통과 (gemini-3.5-flash, 10.8s).
  이미지: `smoke-three-triangles.png` (삼각형 3개 × MMX 3대, 주석 3종).
  결과: 폐쇄 패턴 어휘에 `triangle`이 없어 `pattern: "rows"` + layer note로
  강등 표현(정상 동작 — 어휘 밖 값을 지어내지 않음). 주석 OCR 3종 전부 정확
  ("삼각형 간격 3m"→spacing 3.0, "H 5.5m"→z 5.5, "MMX x3"→count+type_name,
  삼각형별 applies_to 구분). unresolved에 "삼각형 한 변의 길이" — 이미지에
  없는 값을 추정하지 않고 질문으로 넘김. 픽셀 추정 수치 0건.

## 후속 결정 필요 (v2 후보)

- `triangle` 패턴을 어휘와 `spatial/presets.py`에 추가할지 — 현재는 rows로
  강등되어 삼각형 꼭짓점 좌표를 만들 프리셋이 없다. 추가 시 어휘·검증·프리셋·
  arrange_fixtures 프리셋 목록이 함께 넓어져야 한다(계약 §3 + ARRANGE_PRESETS).
