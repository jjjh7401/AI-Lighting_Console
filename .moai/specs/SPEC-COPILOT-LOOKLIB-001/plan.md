# SPEC-COPILOT-LOOKLIB-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-26) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음.

## §A. 접근 요약 (Context)

본 절은 **변경 가능성이 높은 결정을 먼저** 배치한다(가장 되돌리기 어렵거나 후속 결정을 규정하는 순서). 빌드 순서(§B)와 다를 수 있다 — §A.2가 그 편차를 설명한다.

### §A.1 결정 우선순위 (리뷰 순서 — 빌드 순서 아님)

| 순위 | 결정 | 위치 | 왜 먼저 검토해야 하는가 |
|---|---|---|---|
| **1위** | **룩 스키마 형상** — 아이덴티티/장르/다이내믹스/속성/역할 축의 정확한 데이터 모델 | spec.md REQ-001~006, plan.md M1 | P1-1·P1-2가 이 스키마를 공통 기반으로 소비한다(research.md §10). 출하 후 스키마 파괴 변경은 소비자 2개를 함께 깨뜨리므로 **가장 미래-구속적인 결정**이다. |
| 2위 | **저장·통합 아키텍처** — 저장 형식(§A.4 ①)·매칭 표면 형상(§A.4 ⑤)·룰북과의 관계 | design.md §5 슬롯 A/D | 고정 프리픽스 byte-stability와 제공자 캐시 계약에 직결 — 잘못 정하면 매 턴 토큰 회귀 또는 캐시 무효화가 구조화된다. |
| 3위 | **인스턴스화 산출물 + 슬롯/충돌 정책** (§A.4 ②③④) | design.md §5 슬롯 B/C, spec.md REQ-010~013 | 사용자 콘솔에 실제로 남는 오브젝트를 규정 — 사용자 대면·비가역(생성된 프리셋은 쇼파일에 남음) 결정. |
| 4위 | **역할 매핑 확정 UX** (§A.4 ⑥) + 역할 어휘 집합(슬롯 F) | design.md §5 슬롯 E/F, REQ-006~009 | 안전 철학과 왕복 마찰의 트레이드오프 — 단, 방어(미매핑 보고·게이트)는 어느 쪽이든 동일해 상대적으로 가역적. |
| 5위 | 테스트 축·회귀 확장 | plan.md M5 | 기계적 — 상위 결정 확정 후 자연히 따라온다. |

### §A.2 빌드 순서가 리뷰 순서와 거의 같은 이유

본 SPEC은 데이터 계층부터 쌓는 순수-우선 구조라 빌드 순서(M1 스키마 → M2 리졸버 → M3 인스턴스화 → M4 매칭 → M5 회귀 → M6 라이브)가 결정 우선순위와 대체로 일치한다. 유일한 편차: §A.4 마커 6건은 **M1 착수 전(Implementation Kickoff Approval 시점)에 전부 해소**되어야 한다 — M1이 스키마를 굳히기 전에 저장 형식·매칭 표면 방향이 정해져 있어야 재작업이 없다.

### §A.3 정직한 축소 원칙

역할 매핑이 특정 리그에서 전멸(전 역할 미매핑)하더라도 SPEC 실패가 아니다 — 명시적 미매핑 보고 + 폴백(룰북 무드 절)이 정직한 출력이다(REQ-LOOKLIB-009/017). EXECREF/EXECBODY의 "부분 성공을 성공으로 위장하지 않는다" 규율을 계승한다: M6 라이브에서 ASSUMPTION-13(명명 관례 실효성)이 부정으로 실측되면, 그 사실을 progress.md에 기록하고 매핑 휴리스틱 확장을 후속 항목으로 남긴다.

### §A.4 미해결 결정 — Kickoff 전 해소 대상 (design.md §5와 1:1)

1. **[NEEDS CLARIFICATION: 룩 저장 형식·위치 — YAML repo 자산 vs JSON vs Python 모듈]** — 제약: repo-shipped 정적 템플릿이 단일 진실원(REQ-004); PyYAML은 기존 의존(ruleset.py:16, blacklist.yaml 선례 — 주석 가능); JSON은 PinStore/stdlib 선례; frozen 번들은 `resource_base()` 경유 필요(assembly.py:30-37). 권고 기본값: YAML repo 자산.
2. **[NEEDS CLARIFICATION: 프리셋 풀 슬롯 할당 전략 — 고정 예약 대역 vs 빈 슬롯 런타임 탐색 vs 설정값]** — 제약: 풀 번호·점유는 쇼파일 종속(런타임 실측 필수); 드릴다운 캡 16쿼리(tools.py:88)가 전수 탐색 비용을 제한; 고정 대역은 그 자체가 관례 가정(EXECBODY 역주소 교훈 — 관례는 검증 전 하드코딩 금지).
3. **[NEEDS CLARIFICATION: 인스턴스화 산출물 범위 — 프리셋만 vs 프리셋+데모 시퀀스 vs +익스큐터 바인딩]** — 제약: 산출물↑ = blast radius·승인 마찰↑; 데모 시퀀스는 룩을 "눌러볼 수 있게" 하는 UX 가치; 익스큐터 바인딩은 빈 익스큐터 탐색 문제를 추가로 연다(EXECREF/EXECBODY가 남긴 익스큐터 주소 체계 주의).
4. **[NEEDS CLARIFICATION: 기존 사용자 프리셋과의 충돌 처리 — 스킵 vs 재슬롯 vs 명시 승인 경유 덮어쓰기]** — 제약: `Store /overwrite`는 블랙리스트(blacklist.yaml:18)로 승인 보류 유발 — 기본 경로 불가(REQ-012); 실패 방향은 안전(스킵/보류)이어야 함.
5. **[NEEDS CLARIFICATION: 매칭 표면 형상 — 신규 조회 툴 vs 얇은 룰북 안내 축+툴 하이브리드 vs 세션 컨텍스트 주입]** — 제약: 고정 프리픽스 byte-stability(REQ-022)·매 턴 토큰 비용·제공자 중립(REQ-016); 기존 31 무드 절과의 서술 관계 정리 필요. 권고 기본값: 하이브리드(research.md §2 결론).
6. **[NEEDS CLARIFICATION: 역할 매핑 확정 UX — 자동 휴리스틱+결과 보고 vs 적용 전 사용자 확인 단계]** — 제약: "사람이 확정" 철학(product.md §6) vs 지시→실행 왕복 마찰; 게이트/승인 카드가 최종 방어라는 사실이 자동안(案)의 안전 논거.

### §A.5 PRESERVE 목록 (무변경 대상)

`server/safety/**`(소비만 — gate/classify/blacklist/lock 무수정), `server/bridge/**`, `console/lua/**`, `ui/src/**`, `server/web/panel.py`, `server/rulebook/assembly.py`(자산 추가는 허용 후보, 조립 로직은 무변경), 기존 룰북 자산 4파일(00/10/20/30 — 31은 §A.4 ⑤ 결정에 따라 무드 절 교차 참조 1곳 추가 가능성만).

## §B. 마일스톤 (M1..M6)

### M1 — 룩 스키마 + 내장 4장르 라이브러리 (cycle_type=tdd)

- §A.4 ①(저장 형식)·⑤(매칭 표면 방향) 해소 결과를 전제로 스키마 확정: 아이덴티티/장르/다이내믹스(순서 축)/속성(검증 어휘 한정)/역할(폐쇄 어휘, 슬롯 F 확정 포함)/무드 키워드·별칭(한국어 1급).
- 내장 라이브러리 작성: 워십/록/발라드/EDM × 6~10룩, 잔잔함→클라이맥스 스팬. 값은 룰북 31 무드 표(31:195-202)와 검증된 attribute 문법에 근거.
- 로더 + 스키마 검증(명시적 에러, REQ-005). 전부 순수 함수.
- 파일: `server/looks/`(신규 — schema/library/loader), `server/tests/test_looks_schema.py`, `test_looks_library.py`.

### M2 — 역할→리그 매핑 리졸버 (cycle_type=tdd)

- `rig_object`/`rig_section` 형상(tools.py:185-230)의 groups 데이터를 입력으로, 역할별 후보 그룹을 이름 휴리스틱(20_korean_terms showfile 어휘 클래스 기반 한/영 관례)으로 결정. 실존 그룹만, 미매핑은 명시 보고(REQ-007~009).
- `truncated`/`path_not_resolved`/`console_unreachable` 전파.
- 파일: `server/looks/resolver.py`(가칭), `server/tests/test_looks_resolver.py`. 콘솔 무접촉(fake rig).

### M3 — 인스턴스화 번들 빌더 + 게이트 배선 (cycle_type=tdd)

- §A.4 ②③④ 해소 결과를 정책으로 반영: 슬롯 할당·산출물 범위·충돌 처리.
- 번들 규율 기계화: `ChangeDestination Root` 선두, Store 전후 ClearAll, Label, `/Overwrite` 부재(REQ-011/012). 결과 요약 보고 형상(REQ-013).
- 기존 `run_commands` 경로로만 실행되도록 배선 — 신규 실행 표면 0(REQ-010/019).
- 파일: `server/looks/instantiate.py`(가칭), `server/tests/test_looks_instantiate.py`, (배선) `server/web/session.py`.

### M4 — 자연어 매칭 표면 + 채팅 통합 (cycle_type=tdd)

- §A.4 ⑤ 확정 형상으로 매칭 축 구현: 무드 키워드/별칭/장르/다이내믹스 매칭 + 신뢰 실패 시 폴백 신호(REQ-015~018).
- 툴 등록(`build_toolset` 확장) 또는 컨텍스트 주입 배선 + (채택 시) 얇은 룰북 안내 축 — 프리픽스 byte-diff가 정적 텍스트 1회 변경으로 수렴함을 확인(REQ-022).
- 파일: `server/looks/matching.py`(가칭), `server/orchestrator/tools.py`, `server/tests/test_looks_matching.py`.

### M5 — 회귀 + 경계 전체 그린

- pytest 전체 + vitest 전체: run-phase 킥오프 기준선 대비 신규 실패 0건.
- `test_architecture.py` 그린 + `server/looks/**`의 OSC/bridge import grep 0건 + `server/safety/**` diff 없음.
- 룰북 프리픽스 byte 검증(AC-MVP-014 계열)이 §A.4 ⑤ 결정과 정합함을 확인.

### M6 — 라이브 검증 (실물 onPC, AC-LOOKLIB-014)

- 실물 콘솔에서 종단 1회: 채팅 추상 지시("웅장한 금색 코러스" 류) → 매칭 → 역할 매핑 → 인스턴스화 → 게이트 감사 로그 확인 → 생성 오브젝트 GUI 확인.
- ASSUMPTION-13(명명 관례 실효성)·ASSUMPTION-14(Store Preset 캡처 의미론) 실측. 부정 실측 시 §A.3 정직한 축소 절차.
- 배포 왕복 불요(콘솔측 무변경) — 라이브 세션은 콘솔 실행 + 쇼파일에 이름 있는 그룹 준비(GUI 사용자 작업)만 선행 조건.

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 기존 stdlib + PyYAML(기존 의존) + 기존 Python 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**: `server/safety/gate.py:260-265`(스크리닝 경로 하나), `server/safety/classify.py:169`(분류 의미론 하나), `server/rulebook/assembly.py:69-72`(프리픽스 조립 하나).
3. **fail-safe는 협상 대상이 아니다.** 미매핑·충돌·리그 불능의 실패 방향은 항상 축소/보류이지 추측 보완이 아니다.
4. **per-show 값의 정적 데이터 진입 금지**(REQ-004/022) — 룩 자산과 룰북 어디에도 구체 그룹/슬롯/FID 없음.
5. **범위 경계**: P1-1/P1-2 미번들(§D), UI 무변경, 콘솔측 Lua 무변경.
6. **라이브 왕복 비용**: M6만 실물 콘솔을 요구한다. 접근이 확보되지 않으면 M5까지 완료 후 progress.md에 상태를 기록하고 세션을 마무리한다(EXECBODY-001 M3 회복 절차 선례).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase에서 확정)

| 태그 | 대상 | 내용 |
|---|---|---|
| `@MX:NOTE` | `server/looks/` 스키마 모듈 | 스키마가 P1-1/P1-2 공통 기반임 + per-show 값 금지 불변식 표시 |
| `@MX:NOTE` | 번들 빌더 | ClearAll/목적지 규율이 트래킹 오염 방지 기계화임을 표시 |
| `@MX:WARN` + `@MX:REASON` | 역할 매핑 휴리스틱 지점 | 이름 관례 기반 — 관례 없는 리그에서 미매핑 축소가 정상 동작임을 명시(위험 지대: 휴리스틱 확장 시 그룹 발명 금지 경계) |
| `@MX:ANCHOR` 신설 없음 | — | 기존 3앵커(§C.2)를 소비만 한다. 룩 모듈은 fan_in 조건 충족 전까지 NOTE로 시작 |

## §E. 테스트 스캐폴딩 계획

- **순수 함수 우선**: 로더/리졸버/빌더/매칭 전부 인메모리 — 스크리닝 경로에 OSC 0(design.md §6.1).
- **실패 모드 개별 테스트**(병합 금지): 미매핑/불능/미해석/truncated/충돌/폴백 각각(design.md §6.2).
- **번들 문자열 불변식 assert**(design.md §6.3): 목적지 선두·ClearAll 쌍·Label·`/Overwrite` 부재·미등재 그룹 부재.
- **run-phase 자기 검증 커맨드(예상, run-phase에서 확정)**:
  - `.venv/bin/python -m pytest server/tests/test_looks_schema.py server/tests/test_looks_library.py server/tests/test_looks_resolver.py server/tests/test_looks_instantiate.py server/tests/test_looks_matching.py -q`
  - `.venv/bin/python -m pytest server/tests/test_architecture.py server/tests/test_safety_gate.py server/tests/test_safety_classify.py -q`
  - `.venv/bin/python -m pytest -q` (전체, 킥오프 기준선 대비 신규 실패 0건)
  - `grep -rn "bridge.osc\|from server.bridge" server/looks/` → 0건
  - `grep -rn "AskUserQuestion\|mcp__askuser" server/looks/` → 0건
  - 라이브 검증(M6): 감사 로그 jsonl 판독 + GUI 스크린샷(EXECBODY-001 AC-010 인수 형식 계승)

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| v1 속성 범위 | 컬러/강도/빔 구체값 + 포지션 역할 추상(하드 pan/tilt 금지, 인스턴스화 시점 그룹 매핑) — 사용자 확정 ① | spec.md §A, REQ-001/006 |
| v1 장르 세트 | 워십/록/발라드/EDM 4종 × 6~10룩, 잔잔함→클라이맥스 스팬 — 사용자 확정 ② | spec.md §A, REQ-002 |
| v1 완결 범위 | 데이터 계층 + MA3 인스턴스화 + 자연어 매칭 전부 v1(완결 사용자 기능) — 사용자 확정 ③ | spec.md §A, B.3/B.4 |
| 룩 데이터의 거처 | 서버측 구조화 데이터 계층이 단일 진실원 — 룰북 고정 프리픽스에 구조화 데이터 내장 기각(research.md §7 (a)) | spec.md REQ-016/022 |
| 매칭 인프라 | 임베딩/벡터 검색 기각 — 구조화 데이터 제시 + LLM 판단/키워드 축(research.md §7 (b)) | spec.md §D |
| 콘솔측 | Lua 응답기 무변경 — 인스턴스화는 검증된 커맨드라인 패턴(research.md §7 (c)) | spec.md §C/§D |
| P1-1/P1-2 | 번들하지 않음 — 스키마 소비 형상만 예약(research.md §10) | spec.md §D, REQ-001 |
| frontmatter 참조 | `related_specs`(비차단) — MVP-001/DASHUI-001/EXECBODY-001; 엄격 충족 전제의 pre-flight 차단 회피 선례 계승 | spec.md frontmatter |
| Tier 판단 | L — 신규 데이터 계층 + 리졸버 + 인스턴스화 + 매칭 + 툴 배선 + 라이브 AC가 결합, 예상 파일 15+ | spec.md frontmatter `tier: L` |

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> 구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다(첫 run-phase `Agent()` 스폰 전 작성). 본 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다.

### 입력 파라미터

- **tier**: L (5-artifact 세트 + progress.md)
- **scope (file count)**: 예상 12~18 파일(신규 looks 패키지 5~7 + 자산 + 테스트 5 + 배선 2~3 + 룰북 축 0~1)
- **domain count**: 2 (Python 서버 도메인 + 룩/연출 데이터 도메인) — 콘솔 Lua·UI 무변경으로 도메인 확장 없음
- **file language mix**: Python + 정적 데이터(YAML/JSON) + markdown. 코딩 중심
- **concurrency benefit**: **LOW** — M1 스키마가 M2~M4 전부를 규정하는 순차 의존(스키마 → 리졸버 → 빌더 → 매칭)
- **Agent Teams prereqs**: 해당 없음 (Mode 3 RETIRED)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 패키지 + 배선 + 라이브 AC — 단일 라인 변경 아님 |
| 2 | background | 미선택 | 쓰기 작업 포함 |
| 3 | agent-team | 미선택 | RETIRED (tombstone) |
| 4 | parallel | 미선택 | 도메인 2(<3), M1이 후속 전부를 규정하는 순차 의존 — 병렬화 이득 없음 |
| 5 | **sub-agent** | **선택** | 순차 의존 체인 + 코딩 중심 + Tier L Section A-E 위임 템플릿 적용 |
| 6 | workflow | 미선택 | 12~18 파일(30 미만), 균일 기계 변환 아님(설계 결정 다수) |

### Decision: sub-agent

### 정당화

M1(스키마)이 M2~M4의 데이터 계약을 규정하는 순차 게이트이므로 병렬화 이득이 없고, 코딩 중심 작업은 Anthropic coding-task parallelism caveat상 순차 sub-agent가 안전한 기본값이다. Tier L이므로 `manager-develop` 위임에 Section A-E 전체 템플릿을 적용한다. M6은 실물 콘솔 접근을 요구하므로, 오케스트레이터는 M5 완료 시점에 접근 가능성을 사용자에게 확인해야 한다(AskUserQuestion — run-phase 킥오프 또는 M5 완료 직후). §A.4 마커 6건은 Implementation Kickoff Approval 전 AskUserQuestion 라운드로 해소한다.
