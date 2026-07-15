# 저장소 구조 (Structure)

> ⚠️ **이 프로젝트는 그린필드(greenfield) 상태다.** 아래 구조는 `/DESIGN.md` §3(시스템 아키텍처), §9(기술 스택)를 근거로 한 **계획(planned) 구조**이며, 현재 실제로 존재하는 디렉터리/파일이 아니다. 실제 생성 시점과 세부 파일 구성은 Phase 0~1 진행 중 확정된다.

## 1. 현재 상태 (Actual)

```
AI-Lighting_Console/
├── CLAUDE.md          # MoAI 오케스트레이터 실행 지침
├── DESIGN.md          # 설계 원본 문서 (SSOT) — 이 구조 문서의 근거
└── .moai/
    └── project/       # product.md, structure.md, tech.md (본 문서)
```

## 2. 계획된 구조 (Planned — Phase 1 MVP 기준)

```
AI-Lighting_Console/
├── DESIGN.md                     # 설계 원본 (SSOT, 루트 유지)
├── server/                       # Python 3.11+ AI 오케스트레이터
│   ├── orchestrator/             # Anthropic SDK tool runner
│   │   ├── tools.py              # run_commands / query_state /
│   │   │                         #   deploy_plugin / get_rig_context /
│   │   │                         #   propose_plan (@beta_tool)
│   │   ├── prompt_cache.py       # 룰북+오브젝트 모델 프리픽스 캐싱
│   │   └── system_prompt/        # 문법 룰북 · 오브젝트 모델 요약
│   ├── bridge/                   # OSC 브리지 (python-osc)
│   │   ├── osc_client.py         # OSC out: /cmd (UDP)
│   │   └── osc_feedback.py       # OSC in: 피드백 수신
│   ├── safety/                   # 안전 게이트
│   │   ├── grammar_validator.py  # ① 문법 밸리데이터
│   │   ├── risk_classifier.py    # ② 위험 명령 분류 (블랙리스트)
│   │   └── live_lock.py          # ④ 라이브 잠금 모드
│   ├── api/                      # FastAPI + WebSocket 서버
│   └── requirements.txt
├── console/                      # grandMA3 콘솔측 상주물
│   └── lua/
│       └── responder.lua         # 상태 스냅샷·실행 결과 회수 (Lua 5.4)
├── parsers/                      # 컨텍스트 파이프라인
│   ├── showfile_xml.py           # showfile XML 파서
│   └── mvr_gdtf.py                # MVR/GDTF(zip+XML) 파서 — Phase 2
├── ui/                            # 한국어 채팅 웹 UI
│   ├── src/                       # React 또는 Svelte (미정 — DESIGN.md §9 "React or Svelte")
│   └── package.json
└── docs/                          # 프로젝트 문서 (본 .moai/project/ 와는 별도, 사용자향 문서)
```

## 3. 디렉터리별 책임

| 디렉터리 | 책임 | 근거 (DESIGN.md) |
|---|---|---|
| `server/orchestrator/` | Claude tool-use 루프, 프롬프트 캐싱, 시스템 프롬프트(문법 룰북) 관리 | §3 아키텍처, §4.2, §4.3 |
| `server/bridge/` | grandMA3와의 OSC 통신 (명령 전송 `/cmd`, 피드백 수신) | §3, §9 |
| `server/safety/` | 문법 검증 → 위험 명령 분류 → 승인 게이트 → 라이브 잠금의 4단계 안전 계층 | §3, §5 |
| `console/lua/` | grandMA3 Lua 5.4 responder 플러그인 — 상태 조회·실행 결과 회수 (콘솔측 상주) | §3, §9 |
| `parsers/` | showfile XML, MVR/GDTF 파서 — 리그 컨텍스트 인식(Phase 2)의 기반 | §3, §6 Phase 2, §9 |
| `ui/` | 한국어 채팅 웹 UI, WebSocket으로 오케스트레이터와 통신 | §3, §9 |
| `docs/` | 미정(TBD) — DESIGN.md에 문서 디렉터리 구조 명시 없음. 관례상 배치 |

## 4. 미정(TBD) 항목

- `ui/`의 프레임워크 확정 (React vs Svelte — DESIGN.md §9 "React or Svelte" 병기, 미확정)
- 테스트 디렉터리 구조 (예: `tests/`, `server/tests/`) — DESIGN.md에 명시 없음
- 배포/CI 구성 (Dockerfile, CI 파이프라인 등) — DESIGN.md에 명시 없음
- `deploy_plugin` 도구가 생성/관리하는 Lua 플러그인 풀의 저장 위치 — DESIGN.md는 "플러그인 풀" 개념만 언급, 파일 구조 미상세
- Phase 3(음악 분석) 관련 모듈 배치 — librosa/essentia 사용은 확정(§9)이나 디렉터리 위치는 미정

## 5. 참고

이 구조는 Phase 0(검증) 완료 후 실제 구현이 시작되는 Phase 1(MVP)에서 최초로 코드가 생성될 때 확정된다. `/moai plan`으로 SPEC을 작성할 때 이 구조를 기준선으로 삼되, 실제 구현 중 발견되는 제약에 따라 조정될 수 있다.
