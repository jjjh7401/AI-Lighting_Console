# SPEC-COPILOT-IMGLAYOUT-001 독립 리뷰 기록 (2026-08-15)

- 대상: worktree HEAD `648a023` (= origin/main 머지본, `a1a886d`)
- 방식: 독립 리뷰어 2종(품질·보안) 병렬, 읽기 전용
- 판정: **PASS — Critical/High/Major 0건.** 발견은 Low 3 · Informational 2, 전부 기록만 하고 미수정(사용자 결정 2026-08-15).

## 이상 없음으로 확인된 축

| 축 | 근거 |
|---|---|
| 승인 게이트 우회 (최우선) | `analyse_layout_image`(tools.py:3054-3090)는 execution/state 포트 무접근(`test_layout_image_tool.py`의 `_NeverCalled*` 포트가 고정), vision 1회 호출뿐. 쓰기는 `arrange_fixtures`→`run_commands` 재진입(tools.py:5531-5534)으로 gate.screen+승인 카드+백업→쓰기→재검증 상속. LiveLock proposal 강등(5275-5320) 동일 적용 |
| 업로드 DoS | 상한 검사가 b64decode 이전(messages.py:227) + 디코드 후 재검증(237) + `validate=True` + 세션 1장 교체형(session.py:5811) + busy-guard(app.py:424). WS 프레임은 uvicorn 기본 16MiB |
| WS 인증/오리진 | 별도 엔드포인트 없음 — 기존 `/ws` Origin+token 게이트(app.py:262-281, accept 이전 판정)와 동일 |
| 로깅/감사 유출 | base64 원본 미기록. notice는 파일명+KB만(session.py:5814-5826) |
| triangle 프리셋 수학 | circumradius side/√3, 꼭짓점 90/210/330°, 둘레 등간격·apex 시작·반시계, 3k 대수 꼭짓점 착지 — 정확(spatial/presets.py:406-421). isfinite/양수/`_MAX_ABS` 검증 통과 |
| 스펙 원칙 ① (픽셀 수치 추정 금지) | 프롬프트 + `_LAYOUT_INTERPRETED_KEYS` 화이트리스트 이중 차단 |
| UI 업로드 경로 | 드래그앤드롭·클립보드·버튼이 동일 검증(`routeAttachment`→`uploadLayoutImage`), accept 확장자 폴백 |
| 어댑터 | gemini `Part.from_bytes`(269-274) · anthropic base64(86-103) · claude_code 정직 거부(229-233) — 무단 드롭 없음 |

## 발견 — 기록만, 미수정

### [Low] IMGLAYOUT-SEC-001 — 이미지 내 텍스트의 무프레이밍 재주입 (간접 프롬프트 인젝션 잔여, CWE-1427/74)
비전 프롬프트가 이미지 내 텍스트 원문 전사를 요구(tools.py:518-525)하고, 검증 통과 payload가 데이터/지시 경계 표시·항목 수·길이 상한 없이 툴 결과로 모델 컨텍스트에 재주입된다(tools.py:3083-3090). 파스 실패 시에도 원문 200자 에코(tools.py:546). 게이트가 실행은 막지만 잔여 위험 = 승인 카드 요약 오도, unresolved 지시문화로 `ask_user` 사회공학·질문 폭탄(awaited_human=True는 폭주 루프 가드 면제, tools.py:614-620).
**권고**: annotations/unresolved 항목 수 상한(각 32) + 항목당 길이 상한(200자) + "이미지에서 읽은 데이터이며 지시가 아님" 데이터-프레이밍 문구.

### [Low] IMGLAYOUT-SEC-002 — 비전 응답 값 타입 미검증 (CWE-20)
`_parse_layout_vision_response`(tools.py:534-604)는 키만 화이트리스트 — `{"count": "문자열"}`·중첩 객체 통과, `applies_to`/`note` 타입 검사 없음, `layers[].count`는 0/음수/10⁹ 유효(tools.py:566-599). 하류 `spatial_preset_placements`(presets.py:168-190)의 isfinite/양수/상한이 실쓰기는 방어 — 영향은 컨텍스트 오염에 한정.
**권고**: 키별 타입 고정(spacing/radius/z/side: 유한 수, count: 양의 정수+상한, type_name: 짧은 문자열), applies_to·note 문자열 강제.

### [Low] IMGLAYOUT-SEC-003 — 선언 MIME 신뢰, 매직바이트 미검사 (CWE-434/345)
문자열 멤버십 검사만(messages.py:220), UI는 MIME 공백 시 확장자 역산(App.tsx:547-551). 임의 5MB 바이트가 'image/png' 라벨로 vision API에 전달 가능. 서버는 이미지를 파싱·재서빙하지 않아 로컬 표면 없음.
**권고**: 디코드 payload 선두 8바이트를 PNG/JPEG/WebP 시그니처와 대조, 선언 MIME 불일치 시 거부.

### [Info] IMGLAYOUT-SEC-004 — `file_name` 길이 무상한 (CWE-770)
비어있지 않음만 검사(messages.py:218-219), notice로 UI 반사(session.py:5820-5826). 기존 `vectorworks_export_upload`와 동일 관례, React 렌더링이라 XSS 없음. **권고**: 255자 상한, vectorworks 경로와 일괄.

### [Info] IMGLAYOUT-SEC-005 — 업로드당 base64 이중 디코드 (CWE-405)
검증 디코드(messages.py:230) 후 표시용 재디코드(session.py:5814). **권고**: len 산술로 대체.

### [P3·품질] interpreted 값/레이어 수 타입 검사 부재 — SEC-002와 동일 지점 (품질 리뷰어 독립 발견, 상호 확증)
### [P3·품질] 매직바이트 스니핑 부재 — SEC-003과 동일 지점 (상호 확증)

## 리뷰 범위
server/web/{messages,session,app,serve}.py · server/orchestrator/tools.py · server/llm/{types,gemini_adapter,anthropic_adapter,claude_code_adapter}.py · server/spatial/presets.py · ui/src/{App.tsx,useCopilotSocket.ts} · 관련 테스트 4종
