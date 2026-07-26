# SPEC-COPILOT-LOOKLIB-001 — progress

## Plan-phase log

### v0.1.0 (최초 작성)

- 2026-07-26 — 출처: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-3(연출 어휘 계층 — 룩 라이브러리, 승인된 제안). manager-spec이 spec.md/plan.md/acceptance.md/design.md/research.md(5-file Tier L) + 본 progress.md 스켈레톤을 동시 생성.
- 2026-07-26 — 사용자 사전 확정 3건(재질의 금지, spec.md §A 수록): ① 속성 범위, ② 장르 4종(워십/록/발라드/EDM × 6~10룩), ③ v1 = 데이터 계층 + 인스턴스화 + 자연어 매칭 전부.
- 2026-07-26 — 미해결 결정 6건을 plan.md §A.4에 clarification 마커로 기록.
- ~~"브랜치 `feat/lighting-direction-features`, HEAD `81e2232`. 커밋은 오케스트레이터/사용자 결정 대기(파일은 워킹 트리에만 존재)."~~ — **낡음, v0.2.0에서 정정**(감사 D15). 아래 기준선 참조.
- ~~"design.md §5와 1:1"~~ — **거짓, v0.2.0에서 정정**(감사 D6a). 실제로는 마커 ③④가 슬롯 C 하나로 접혔고 슬롯 F에는 대응 마커가 없었다.

### v0.2.0 (독립 감사 반영 개정 — 2026-07-26)

- **감사 결과**: 독립 plan-audit **FAIL, 종합 0.65** (Tier L PASS 기준 0.85). 감사를 권위로 수용하고 원문을 방어하지 않는 방침으로 6개 아티팩트 전면 개정.
- ~~"정정된 기준선 (감사 D15): … HEAD `fd59163` … `.moai/state/context-usage.json`은 이미 untrack되었으며 재생성하지 않는다."~~ — **기준선은 낡았고, 런타임 상태 파일에 대한 문장은 쓰이는 순간 이미 거짓이었다. v0.3.0에서 정정**(아래 v0.3.0 절 참조).
- **사용자 확정 4건 추가 반영** (재질의 금지, spec.md §A 수록):
  - ④ **빔 축 유지 + M0 라이브 프로브 선행** — 라이브러리 저작 전 실물 콘솔에서 attribute 문법 실측(EXECBODY-001 M1 GO/DESCOPE 패턴). 스트로브 포함 여부는 프로브 결과 + 프리뷰 안전 발견(D5)과 함께 판단.
  - ⑤ **프리셋 슬롯 = 런타임 빈 슬롯 탐색** (고정 대역·설정값 기각).
  - ⑥ **인스턴스화 산출물 = 프리셋만** (데모 시퀀스·익스큐터 바인딩 기각).
  - ⑦ **충돌 처리 = 건너뛰고 "N개 건너뜀" 명시 보고** (덮어쓰기·재슬롯 기각).
- **감사 결함 처리** (~~"18건 중 지적된 전부"~~ — **거짓 주장, v0.3.0 정정**: 아래 표는 18건 중 **16건**만 열거한다. D1·D16 행이 없다):

  | 결함 | 처리 |
  |---|---|
  | D2 (critical) REQ-001/003 상호 충족 불가 | 한 쌍으로 개정. 빔 어휘 리포지토리 0건 재실측 → ASSUMPTION-15 + M0 게이트. REQ-003을 3구간(확정/용도한정/프로브대기)으로 재구성, Pan/Tilt는 무브먼트 내부로 한정. `10_object_model.md:39` zoom=Focus 그룹핑 오류 정정. |
  | D5 (major) preview.py 안전 계층 누락 | research.md §5.5 신설 + §6 프리뷰 절 + §8 표 4행 추가. design.md §3 데이터 흐름에 프리뷰 단계 추가 + "screen 이후 무변경" 주장 정정(감싼다) + §4 위험 #9/#10 추가. 스트로브 v1 제외 확정. |
  | D3+D13 (major) 역할 어휘 사전 근거 부재 | spec.md §A·research.md §3에서 "신규 어휘"로 정정(0건 실측 명시). REQ-006을 명명 관례 *스타일* 준수로 재진술 — PRESERVE 파일 무변경. |
  | D6+D8 (major) 마커 집합 결함 | (a) 1:1 허위 주장 4곳 정정. (b) 마커 ①⑤를 리포지토리·문서 증거로 폐쇄. (c) 다이내믹스 척도를 신규 마커로 승격. |
  | D4 (major) 미커버 REQ 4건 | AC-015/016/017/019 신설 + §C.0 REQ↔AC 역추적표 도입(재발 구조적 봉쇄). REQ-021은 EXECBODY AC-011 형식 계승. |
  | D7 (major) 범위 누출 | REQ-010에서 "(또는 장르 묶음)" 제거. |
  | D9 (major) M1 과적재 + 전제 순서 결함 | M0 프로브 신설 + M1 분해(스키마/어휘/로더 ↔ 라이브러리 저작). 마일스톤 M0~M7. spec.md:93 허위 교차참조 삭제. 라이브 세션 **2회**로 명시. |
  | D10 AC-008 검증 미달 | ①~④로 분해, 실행 호출 경로 grep(③) 신설. |
  | D11 REQ-014 `Where` 오용 | 역량 게이트로 재진술 + AC-016(정적 부재 검증). |
  | D12 AC-014 비토큰 축약 | 완전 토큰으로 정정 + REQ-013 유닛 AC-018 신설. |
  | D14 AC-007 대소문자 | `re.IGNORECASE` assert 규칙 명문화 + design.md AP-13. |
  | D15 낡은 기준선 | 본 절 + spec.md §C 갱신. |
  | D17 Phase 2/3 | spec.md §A에 1문단 추가(Phase 3 산출물로 Phase 2 기준 충족). |
  | D18 빔 출처 | spec.md §A에 P1-2:78 ↔ P1-3:84 치환 기록. |
  | 인용 nit | `tools.py:233-265` → **`231-272`**(`drill_into` 실제 범위). |
  | **D1** | **행 없음** — v0.3.0 조사에서도 내용 복원 불가(아래 v0.3.0 절 "D1·D16 처리"). |
  | **D16** | **행 없음** — 동일. |

- **남은 미해결 마커 3건** (plan.md §A.4b ↔ design.md §5.2 슬롯 R1/R2/R3, **진짜 1:1**) — 각각 구체적 제안 기본값 + 근거 동반. **→ v0.3.0에서 3건 전부 폐쇄, 잔여 0건.**
  1. **역할 어휘 폐쇄 집합** — 제안: 6종(백라이트/프론트/사이드/탑/배경/스페셜) + 한영 별칭 + 매핑 힌트.
  2. **다이내믹스 단계 척도** — 제안: 정수 1~5, 검증식 `1 <= level <= 5`, 스팬 판정 `{1,2}`≥1 ∧ `{4,5}`≥1.
  3. **역할 매핑 확정 UX** — 제안: 자동 휴리스틱 + 적용 전 요약 보고(방어 3겹 근거) / 반대 논거 병기.

### v0.3.0 (재감사 반영 최종 개정 — 2026-07-26)

- **재감사 결과**: 독립 plan-audit **FAIL, 종합 0.80** (Tier L PASS 기준 0.85). v0.2.0의 0.65에서 **+0.15 상승, 회귀 0건**이나 기준 미달. 재감사는 v0.1.0 원문을 `git show 8325b9b`로 대조한 뒤 **v0.2.0의 이의 제기 2건을 모두 인용**했다 — (a) REQ-003 구간 2의 Pan/Tilt 용도 한정 분리, (b) REQ-004의 출처 귀속 정정. D2·D5는 진짜로 해소되었음이 확인되었다. 해당 작업은 그대로 유지한다.
- **재감사의 핵심 진단**: *"새로 만든 통제 장치들이 그것들이 잡으려던 오류와 같은 부류의 오류를 담고 있다 — 13건의 신규 지적 중 5건이 그 자체로는 옳은 편집의 전파 실패다."* 이번 개정의 작업 규율은 여기서 나왔다: **구조를 바꿀 때마다 6개 아티팩트 전부에서 하류 참조를 훑는다.**
- **정정된 기준선 (v0.3.0)**: 브랜치 `feat/lighting-direction-features`, ~~"HEAD **`4f1fb7a`**"~~ · 아티팩트 6종은 전부 git 추적 상태(`8325b9b` 최초 → `6220f45` v0.2.0 → ~~"본 v0.3.0 개정은 미커밋"~~). — **취소선 두 곳 모두 v0.3.1에서 정정**: v0.3.0 개정은 `6c3e626`으로 커밋되었고(그 커밋이 아티팩트 6종 전부를 담는다), 그 순간 "미커밋" 주장과 `4f1fb7a` HEAD 표기가 함께 낡았다. **v0.2.0의 런타임 상태 파일 주장과 정확히 같은 부류의 자기참조 결함**이다 — 아래 v0.3.1 절 참조.
  - **런타임 상태 파일 — v0.2.0 주장이 거짓이었음의 기계적 확인**: v0.2.0 progress.md는 "`.moai/state/context-usage.json`은 이미 untrack되었으며 재생성하지 않는다"고 적었다. 그러나 `git show --stat 6220f45`는 **그 문장을 담은 커밋이 바로 그 파일을 `+11`행으로 다시 추가**했음을 보여준다. 즉 **쓰이는 순간 이미 거짓**이었다(`fd59163`이 untrack → `6220f45`이 재추가 → `4f1fb7a`이 다시 untrack). `4f1fb7a`은 `.gitignore:241`에 `.moai/specs/*/.moai/`를 추가해 재발을 구조적으로 막았다. 파일은 워킹 트리에 남아 있으나 ignore 대상이므로 **삭제하지도, 재생성하지도 않는다** — 이번 개정에서 건드리지 않았다.
- **사용자 확정 3건 추가 반영** (재질의 금지, spec.md §A 수록):
  - ⑧ **빔 유지 + 라이브 세션 2회 수용** — 사용자는 "빔을 v1에 유지하면 실물 콘솔 세션이 2회가 된다"는 대가를 명시적으로 제시받고 유지를 택했다. **표면화된 뒤 수용된 비용**으로 기록한다. 단 논거는 정정했다(아래 참조).
  - ⑨ **역할 어휘 6종 폐쇄 집합** — `백라이트`·`프론트`·`사이드`·`탑`·`배경`·`스페셜`. **6종 전부에 매핑 힌트 문자열을 저작**했다(v0.2.0은 백라이트 1종에만 예시 힌트가 있었고, 그 상태의 "제안 기본값"은 그대로 채택할 수 없었다 — 나머지 다섯은 M0에서 실측할 대상조차 없었다). 시작점이며 M0 실측으로 힌트 조정 가능.
  - ⑩ **역할 매핑 확정 UX = 자동 휴리스틱 + 적용 전 요약 보고** (확인 왕복 없음). 반대 논거는 기각이 아니라 **design.md §4 위험 #1의 수용된 잔여 위험**으로 존치.
- **엔지니어링 판단으로 폐쇄 2건** (사용자 질의 없이):
  - **H. 다이내믹스 척도 = 정수 1~5**. 실수 0.0~1.0은 명시 기각 — 무단계 축은 REQ-005의 "범위 이탈" 검증을 거의 항상 참인 조건으로 만들고 AC-002의 스팬 판정에 **임계값이라는 새 미해결 결정**을 도입한다(마커 하나를 없애고 하나를 만든다).
  - **I. 프리셋 풀 범위 + "N개 건너뜀"의 단위** — 아래 별도 항목.
- **`<pool>` 미결의 해소 (재감사 N3 — major)**: v0.2.0은 여섯 아티팩트 전부에서 프리셋 주소를 `Preset <pool>.<slot>`으로만 적고 `<pool>`을 끝내 정하지 않았다. **마커도 아니고 결정도 아닌 상태**였고 그 미결이 네 곳으로 번졌다(번들 형상 / 스킵 카운트 단위 / ASSUMPTION-14의 실측 대상 / 요약 보고 형상). 결정 I로 폐쇄:
  - **in-scope 풀 = Dimmer · Color** (+ ASSUMPTION-15 GO 시 **Beam · Focus**). Position(정적 pan/tilt 금지로 담을 값 없음) · All(무차별 캡처로 패밀리별 검증 불가 + per-show 값 유입 경로) · Gobo/Control/Shapers/Video(매핑되는 v1 속성 없음) **제외**.
  - **근거**: `10_object_model.md:18-20`(프리셋은 속성 패밀리별 풀로 조직 + `Preset <pool>.<slot>` 주소), `:38-40`(패밀리 경계 — Beam=iris/prism/frost, Focus=zoom/focus), `00_grammar.md:18`(`Preset 4.1` = pool 4 "Color").
  - **풀 번호 하드코딩 금지**: `server/orchestrator/tools.py:39-44`가 preset_pools를 "**the preset TYPES (Dimmer, Position, Gobo, Color, ...)**"로 명시하고 `:185-190`이 실번호 `no`를 이름과 함께 반환하므로 **런타임 해석이 가능**하다. `Preset 4.1 = Color`는 룰북의 예시 산문이지 계약이 아니다(`tools.py:53-55` "추측된 경로는 죽은 채 출하된다").
  - **번들 형상**: 룩 1개 = in-scope 풀 타입마다 `Store Preset` + `Label` 1쌍(기본 2쌍, 최대 4쌍). 역할×풀로 쪼개지 않는다.
  - **"N개 건너뜀"의 단위 = 건너뛴 프리셋 저장 1회**(룩 아님). 근거 (a) REQ-013 (c)가 요구하는 "그 슬롯"을 갖는 것은 룩이 아니라 프리셋이다. (b) 룩 단위로 세면 부분 충돌(Color는 비었는데 Dimmer만 점유)이 표현 불가능해져 룩 전체를 버리거나 0건으로 보고하게 되고, 후자는 부분 성공을 전체 성공으로 위장하는 것이다. 사유 2종(`conflict` / `no_free_slot`)을 항목별로 구분 기록.
- **M0 필요성 논거 정정 (재감사 지적)**: v0.2.0은 "전제 검증이 저작보다 먼저"를 **네 프로브 항목 전부에 균일하게** 적용했으나 항목별 차단 대상은 다르다 — **ASSUMPTION-15만 M1(로더)을 진짜로 막고**, ASSUMPTION-14·슬롯 탐색은 **M4(번들 빌더)**, ASSUMPTION-13은 **M3(리졸버)**이며 그나마 차단이 아니라 튜닝 입력이다. 정확한 진술은 **"진짜 순서 제약 1건 + 의도적 배칭 3건"**(plan.md §A.2 표).
  - **사용자 확정 ⑧과의 관계**: 빔이 결정한 것은 **프로브의 위치**(M4 직전 → M1 직전)이지 **세션의 개수**가 아니다. 빔을 뺐더라도 ASSUMPTION-14·슬롯 탐색이 M4를 막으므로 2회는 그대로였다. 사용자 결정은 유효하게 유지되며 정정 대상은 **논거의 정밀도**다.
- **ASSUMPTION-14 부정 분기 완전 명세 (재감사 지적 — M0 weakness)**: v0.2.0은 "GO / 형상 수정 필요"라고만 적어 형상도 소유자도 게이트도 없었다. **GO / FALLBACK / HALT 3분기**로 명세하고 ASSUMPTION-15의 빔 게이트와 같은 수준(명명 게이트 + 스키마 규칙 + AC assert + DoD 절)으로 올렸다.
  - **FALLBACK** = 패밀리별 격리 캡처 사이클로 번들 분해. 이를 **라이브러리 재저작 없이** 흡수하기 위해 **REQ-001에 "속성 페이로드의 패밀리 분할 가능성" 스키마 규칙을 신설**하고 AC-003 구간 5가 검증한다.
  - **HALT** = `Store Preset` 자체 불성립 → run-phase 진행 금지 + 오케스트레이터 블로커 보고.
  - 슬롯 탐색 항목도 **GO / BLOCKER 2분기**로 확장(풀 타입 런타임 해석 실현성 추가 — 결정 I 4항의 전제).

- **기계적 정정 (재감사 N1·N2·N5~N12)**:

  | 지적 | 처리 | 확인 |
  |---|---|---|
  | **N1** (major) §C.0 역추적표의 AC-010↔AC-012 전치 | AC 본문 기준으로 정정(AC-010 = 자연어 매칭 → REQ-015/018, AC-012 = 고정 프리픽스 → REQ-022). 표 위에 정정 사유 명기 | 독립 확인 — AC 본문 대조 |
  | **N2** (major) plan.md §B ↔ acceptance.md §C.0 마일스톤 AC 3곳 불일치 | M4={007,008,016,018} · M5={010,011,012,017} · M6={009,013,019} · M7={014}로 재정합. **§C.0에 마일스톤별 AC 집합 요약행 추가**(001~020이 정확히 한 번씩) | 20개 AC 중복·누락 0 확인 |
  | ↳ 그중 **AC-014(LIVE)가 오프라인 회귀 M6에 배정** | M7로 이동. plan.md 자신의 M7 제목과 모순이었음 | 확인 |
  | **N5** (minor) design.md §2 `:21`·`:22`, §4 `:65` 낡은 슬롯 문자 | `§5 슬롯 D` → **결정 E**(매칭 표면), `§5 슬롯 B/C` → **결정 B/D**. 미결처럼 서술한 표현도 확정형으로 | §3만 갱신되고 §2/§4가 남겨진 전파 실패 |
  | **N6** (minor) research.md `:28`·`:32` 폐쇄된 결정을 마커로 이연 | 결정 A/E 확정 표기로 교체. **같은 문서 §9.1이 이미 폐쇄로 기록**하고 있어 자기모순이었음을 명기 | 확인 |
  | **N7** (minor) research.md `:154` `20_korean_terms.md` = "역할 어휘 클래스 사전" | "**픽스처 타입 클래스** 사전"으로 정정 — §3이 D3 정정으로 뒤집은 프레이밍이 §8에 남아 있었음 | 확인 |
  | **N8** (minor) plan.md `:88` `AC-EXECBODY-013` 오인용 | **AC-EXECBODY-010**(`…/acceptance.md:117-123`, GO/DESCOPE 조건부 인수)으로 정정. 013은 "`Go+ Page N.M` 구문 계속 보류(regression)"로 무관 | EXECBODY acceptance.md 실측 |
  | **N9** (minor) spec.md `:112` `related_specs` 3건 "모두 구현·라이브 검증 완료" | **MVP-001은 `status: in-progress`**(`SPEC-COPILOT-MVP-001/spec.md:5`); DASHUI-001·EXECBODY-001만 `completed`. 의존 기제별로 정확히 재진술 + 킥오프 재확인 의무 추가 | 3개 SPEC frontmatter 실측 |
  | **N10** (minor) 본 표 "18건 중 전부"인데 16 ID | 헤더를 거짓 주장으로 표시 + **D1·D16 행 추가**(아래 별도 항목) | 확인 |
  | **N11** (nit) `§A.4 마커` vs `§A.4b` 표기 혼재 | **마커 0건 폐쇄로 자연 해소** — 모든 참조가 `§A.4a 결정 X`로 바뀜 | 확인 |
  | **N12** (nit) spec.md `:46` "장르당 **약** 6~10룩" | "약" 삭제(REQ-002/AC-002가 하드 범위를 기계 assert). research.md `:15`도 동일 정정 | 확인 |
  | **신규 발견 1** | spec.md §C ASSUMPTION-14가 "**M3** 착수 전에 알아야 한다"고 적고 있었으나 번들 빌더는 **M4**다 — v0.2.0의 마일스톤 번호 밀림(구 M2~M6 → 신 M3~M7)이 이 문장에 전파되지 않은 오기. **M4로 정정** | plan.md §B 대조 |
  | **신규 발견 2** | v0.2.0 커밋 `6220f45`이 "untrack되었다"고 적은 바로 그 런타임 상태 파일을 **같은 커밋에서 재추가**했음 | `git show --stat` 실측 |

- **D1·D16 처리 (N10) — 복원 불가를 정직하게 기록한다**: 두 결함의 **내용은 리포지토리에서 복원할 수 없다.** LOOKLIB의 plan-audit 보고서는 `.moai/reports/plan-audit/`에 저장되지 않았고(그 디렉터리에는 EXECREF-001과 날짜 기반 2건만 존재), 감사 결과가 대화 안에서만 전달됐다. 따라서 D1·D16에 대해 확인할 수 있는 것은 **"v0.2.0의 처리 표에 행이 없다"는 사실뿐**이며, 그 내용을 추정해 채우는 것은 근거 없는 기록이 되므로 하지 않는다.
  - **이것이 뜻하는 것**: v0.2.0의 "18건 중 지적된 전부" 헤더는 **열거하지 않은 2건에 대해 완결성을 주장한 거짓 진술**이었다. 위 표에 D1·D16 행을 "행 없음 / 복원 불가"로 명시해 그 공백이 조용히 사라지지 않게 고정한다.
  - **후속(구조적 재발 방지)**: 이후 plan-audit 결과는 `.moai/reports/plan-audit/SPEC-COPILOT-LOOKLIB-001-<date>.md`로 **파일 영속화**한 뒤 처리 표를 작성한다 — 대화 안에만 존재하는 감사는 처리 누락을 사후 검증할 방법이 없다.

- **마커 최종 상태**: v0.1.0 6건 → v0.2.0 3건 → **v0.3.0 0건.** plan.md §A.4b 삭제, design.md §5.2 해체, research.md §9 "0건". 결정은 plan.md §A.4a에 **11건(A~K)**, design.md §5.1에 **11건**으로 양쪽 1:1.
- **next**: plan-audit 재실행(Tier L PASS 기준 0.85 — 이번엔 감사 보고서를 파일로 영속화) → **M0 라이브 세션 접근 가능성 확인** → Implementation Kickoff Approval → run(M0 프로브부터). **Kickoff 전 결정 해소용 AskUserQuestion은 0건**이며, 남은 사용자 접점 2건은 결정이 아니라 **실물 콘솔 접근 가능성**을 묻는다(plan.md §G).

### v0.3.1 (감사 PASS 이후 정리 개정 — 2026-07-26)

- **감사 결과**: 독립 plan-audit **PASS, 종합 0.92** (Tier L 기준 0.85). v0.3.0의 0.80에서 **+0.12**. **SPEC은 승인되었고 구현이 인가되었다.** 본 개정은 재감사 라운드가 **아니며**, 감사가 기록으로 남긴 경미한 지적 4건(F1~F4)만 처리하는 한정 정리다. **구조는 건드리지 않았다** — 요구 22건 · AC 20건 · 마일스톤 M0~M7 · §A.4a 결정 11건(A~K) · 미해결 마커 0건이 전부 그대로다.
- **마커 상태**: **0건 유지** (v0.1.0 6건 → v0.2.0 3건 → v0.3.0 0건 → v0.3.1 **0건**). 결정 집합도 **11건(A~K) 무변경** — F3은 새 결정 문자를 만들지 않고 기존 §D 무브먼트 제외의 범위를 좁혔다.

| 지적 | 처리 | 확인 |
|---|---|---|
| **F1** — spec.md §A 마지막 문단의 매핑 예시가 `'Wash'`/`'워시'`(픽스처 타입 클래스) | 6종 표의 실제 힌트 문자열(`Back`/`백라이트`, `FOH`/`프론트`, `Cyc`/`샤막`)로 교체 + 정정 사유 각주. **여덟 줄 위의 배제 규칙**(AC-015 ④가 힌트 내 0건을 assert)과 정면으로 어긋나 있었다 | v0.1.0 이후 **손대지 않은 잔존 산문**이라 v0.3.0의 6-아티팩트 훑기를 빠져나갔음 |
| ↳ **F1 sweep 적발** | acceptance.md §B 시나리오 1의 Given이 `'FOH Wash'/'워시'`로 **같은 결함의 하류 사본**이었다 → 동일 정정 | 이번 개정의 훑기가 새로 잡은 건 |
| **F2** — research.md §5.5 함의 2항이 무브먼트 `caution`을 v1에서 도달 가능한 것처럼 서술 | §D의 무브먼트 제외 확정 이후 **v1 룩 번들에서 도달 불가**임을 명시. "요약 보고(REQ-013)가 설명해야 한다"던 요구는 삭제 — REQ-013 (a)~(d) 어디에도 대응 요소가 없어 **어떤 요구와도 연결되지 않은 채 떠 있던 문장**이었다. 폴백 경로에서의 유효성은 분리 존치 | §5.5는 v0.2.0 신설, §D 무브먼트 제외는 v0.3.0 확정 — 후자가 전자에 전파되지 않은 순서 결함 |
| **F3** — REQ-013의 보고 요소 (a)~(d)가 "선언된 무브먼트 축을 v1이 인스턴스화하지 않았다"를 담지 않음 | **두 대안 중 "v1 라이브러리 무브먼트 수록 금지"를 채택**(보고 요소 (e) 신설 기각). REQ-003 신설 절 + **AC-003 구간 6** 신설(무브먼트 0건 **분리 assert** 스키마 필드 왕복 가능) + design.md 위험 #13/AP-18 + plan.md M2·§E·§F + research.md §4/§10 | AC-003 구간 2가 라이브러리 무브먼트를 허용하고 있었으므로 **실재하는 은닉 축소 경로**였음 |
| **F4** — spec.md §C / 본 문서의 "본 v0.3.0 개정은 미커밋" | `pending-backfill` 자리표시자로 교체. HEAD SHA도 문서에 고정 기록하지 않는다 — 실질 위험은 spec.md §C의 **킥오프 기준선 재측정 의무**가 이미 덮는다 | `git show --stat 6c3e626`이 아티팩트 6종 전부를 보여줌 = 주장은 **커밋되는 순간 거짓**이 되었음 |

- **F3의 선택 근거 (판단이 필요했던 유일한 항목)**: 감사는 두 해법을 열어 두었다 — (α) 보고 요소 `movement_not_instantiated` 신설, (β) v1 라이브러리 무브먼트 0건 AC 신설. **β를 택했다.** ① 본 SPEC은 v1이 정직하게 발화할 수 없는 것을 **보고하기보다 제외해 왔다**(Position 풀 "담을 것이 없다", All 풀 "패밀리별 검증을 불가능하게 한다", 스트로브 "경보 피로를 만든다") — β가 그 처리 방향과 같다. ② **발생할 수 없는 누락은 보고할 필요가 없다**; α는 v1이 스스로 만든 뒤 스스로 알리는 결손을 위해 REQ-013 시그니처·번들 빌더·AC-018을 모두 넓힌다. ③ β는 **빔 DESCOPE 분기와 정확히 동형**("스키마 필드 정의 유지 + v1 라이브러리 미사용")이라 새 기제가 0이다. ④ **소비 계약을 깨지 않는다** — research.md §10이 명시하듯 P1-1이 소비하는 것은 다이내믹스 축, P1-2가 소비하는 것은 장르 묶음 API 형상이며 **무브먼트 필드는 둘 중 어느 것도 아니다**; 필드는 정의된 채 남아 후속 SPEC이 스키마 변경 없이 켤 수 있다. ⑤ 검증이 **M2 오프라인 전수 테스트**로 닫혀 라이브 세션 2회와 무관하다(α는 M4 유닛 + 배선이 필요).
  - **기계적 검증 형태**: AC-003 구간 6은 두 assert를 **반드시 분리**한다 — (i) `sum(1 for look in library if look.movement) == 0`, (ii) `parse(dump(look_with_movement)) == look_with_movement`(로더가 무브먼트를 담은 룩을 **거부하지 않음**). (i)만으로는 "필드가 삭제된 것"과 "v1이 쓰지 않는 것"을 구분할 수 없어, 후속 SPEC이 켜려 할 때 필드가 살아 있는지 보증되지 않는다.
  - **구간 2는 존치**: `Pan`/`Tilt`가 무브먼트 지정 내부에서만 등장한다는 규칙은 삭제하지 않았다. 구간 6과 합쳐 v1의 `Pan`/`Tilt` 등장은 0이 되지만, 구간 2는 무브먼트가 켜질 때 그 거처를 고정하는 규칙으로 남는다.
- **이번 개정의 훑기 (v0.3.0이 놓친 부류를 겨냥)**: 재감사가 진단한 "전파 실패"의 실제 형태는 **새로 쓴 참조의 오류가 아니라 손대지 않은 산문의 잔존**이었다(F1·F2가 둘 다 그 부류다). 따라서 이번에는 변경한 개념마다 6개 아티팩트를 **전문 검색**했다 — `워시|Wash|스팟|Spot`(F1), `무브먼트|페이저|Phase 0 Thru`(F2·F3), `4f1fb7a|6220f45|8325b9b|미커밋`(F4), `11건|A~K`(결정 수 불변 확인), 그리고 clarification 마커 토큰(0건 확인 — 이 문서는 그 토큰을 리터럴로 적지 않는다. 적는 순간 자기 자신이 카운트에 잡혀 불변식을 깨기 때문이며, 이번 훑기가 실제로 그 자기 오염을 한 번 적발해 제거했다).
- **next**: 변경 없음 — **Implementation Kickoff Approval → M0 라이브 세션 접근 가능성 확인 → run(M0 프로브부터)**. Kickoff 전 결정 해소용 AskUserQuestion은 여전히 **0건**이고, 남은 사용자 접점 2건은 결정이 아니라 **실물 콘솔 접근 가능성**을 묻는다(plan.md §G).

## §E.1 Plan-phase Audit-Ready Signal

_<pending plan-audit>_

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 (2026-07-26, 실물 grandMA3 onPC) — 판정 4건 확정

**형식 계승**: `SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`(AC-EXECBODY-010)의 GO/DESCOPE 조건부 인수 패턴. plan.md §B M0의 산출물 조항("판정 4건 + 실측 원문을 **각주가 아니라 명시적 섹션으로** 기록")에 따라 본 절이 그 명시적 섹션이다. **코드 변경 0건** — M0는 측정 세션이다(plan.md §B M0).

#### 세션 조건 + 측정 채널 (판정 해석의 전제)

| 항목 | 값 |
|---|---|
| 콘솔 | 실물 grandMA3 onPC |
| 응답기 | `CopilotResponder` v1.4.1 |
| OSC | send 8000 / receive 9005 |
| 왕복 사전 확인 | ping + state + exec **전부 PASS, 첫 시도**(소켓 사이클 불요 — `feedback_grandma3_osc_stale_socket_and_send_row` 계열 장애 미발생) |
| 쇼파일 그룹 | 4종 — `Copilot Grp`(1) · `Back`(11) · `Front`(12) · `All`(13) |
| 발화 경로 | `server/tools/responder_roundtrip` 프리미티브. 전 커맨드가 `ChangeDestination Root` 선행 + `ClearAll` 규율 |

> **채널의 성질을 정확히 적는다 (미검증 항목 G2·G4의 근거)**: `server/tools/responder_roundtrip.py:44`는 `server.bridge.osc`를 직접 import하며 `server/safety/gate.py`를 경유하지 않는다(`grep -n "gate\|screen\|audit" server/tools/responder_roundtrip.py` → **0건**). 즉 본 프로브는 **게이트 미경유 직결 채널**이었고, 따라서 게이트 감사 로그 항목이 생성되지 않았다. 이것은 AC-LOOKLIB-020이 ASSUMPTION-15에 대해 적은 "게이트 경유로 발화하고 콘솔 응답·**감사 로그** verbatim 판독"과 어긋난다 — 아래 §미검증 G2에 결함으로 기록한다. 판정 자체는 콘솔 응답 원문으로 성립하나, **증거 매체 1종이 산출되지 않았다.**

#### 판정 요약 (4건 — 각각 명시된 분기 중 하나)

| # | 항목 | 분기 | 차단 대상(plan.md §A.2) | 증거 등급 |
|---|---|---|---|---|
| 1 | ASSUMPTION-15 (빔 attribute 문자열) | **GO** (≥1 수용) | M1 로더 | 직접 관측 |
| 2 | 슬롯 탐색 + 풀 타입 해석 (결정 I·B 실현성) | **GO** (a·b 모두 가능) | M4 번들 빌더 | 직접 관측 |
| 3 | ASSUMPTION-13 (그룹 명명 관례) | **매칭 역할 2/6 기록** (DESCOPE 분기 없음 — 튜닝 입력) | M3 리졸버 | 직접 관측 |
| 4 | ASSUMPTION-14 (`Store Preset` 캡처 의미론) | **GO — 단 추론 근거이며 직접 관측 아님** | M4 번들 빌더 | **구조적 추론(강) + 시각 간접(중)** |

**HALT 미발동 · BLOCKER 미발동** — acceptance.md §F DoD 2항의 두 차단 분기 어느 쪽도 발동하지 않았다. run-phase 진행 차단 사유 없음.

---

#### 측정 1 — ASSUMPTION-15 (빔 계열 attribute 문자열) → **GO**

선택 `Group 13`. 각 후보를 `Attribute '<name>' At 50` 형태로 발화.

| 후보 문자열 | 응답기 결과 |
|---|---|
| `Zoom` | ok=True, result=`OK` |
| `Iris` | ok=True, result=`OK` |
| `Focus` | ok=False, result/error=`Illegal object` |
| `Frost` | ok=False, result/error=`Illegal object` |
| `Prism1` | ok=False, result/error=`Failed` |
| `Shutter` | ok=False, result/error=`Illegal object` |

**판정 GO** (≥1개 수용). 결정 I의 패밀리 라우팅(`10_object_model.md:39` — Beam=iris/prism/frost, Focus=zoom/focus) 적용:

- `Zoom` → **Focus** 패밀리/풀
- `Iris` → **Beam** 패밀리/풀

따라서 **Beam · Focus 두 풀이 v1 in-scope에 진입**하고, **REQ-LOOKLIB-003 구간 3의 허용 목록은 정확히 `{Zoom, Iris}`** 로 확정된다(아래 §M0가 확정한 하류 결정).

**반드시 함께 기록되어야 할 한정 (bounded confidence — 닫힌 열거가 아니다)**: 거부 4건은 **문법 무효가 증명된 것이 아니라 픽스처 의존적 결과**다. `Group 13`은 이름이 `All`이며, 그 그룹의 픽스처가 frost/prism/shutter 속성을 실제로 보유하는지는 확립되지 않았다. `Illegal object`는 (i) "MA3가 모르는 attribute 이름"과 (ii) "선택된 픽스처가 그 속성을 갖지 않음" **양쪽과 모두 정합**한다. 픽스처가 더 풍부한 선택을 대상으로 후속 프로브를 돌리면 더 많은 문자열이 수용될 수 있다. 본 판정은 **"≥1 수용"이라는 GO 조건의 충족**이지 빔 어휘의 전수 확정이 아니다.

- `Prism1`만 `Failed`로 다른 오류 문자열을 반환했다(나머지 3건은 `Illegal object`). 이 차이의 원인은 **관측되지 않았고 추론하지 않는다** — 원문 그대로 보존한다.

#### 측정 2 — 풀 타입 해석 + 슬롯 탐색 (결정 I·B 실현성) → **GO**

`DataPool/PresetPools` 조회 → `childCount=14`. 반환된 이름 전량:

```
1 Dimmer · 2 Position · 3 Gobo · 4 Color · 5 Beam · 6 Focus
7 Control · 8 Shapers · 9 Video
21 All 1 · 22 All 2 · 23 All 3 · 24 All 4 · 25 All 5
```

**(a) 풀 이름 → 패밀리 해석 = GO.** 결정 I 4항("풀 번호를 하드코딩하지 않고 런타임에 타입을 해석")의 전제가 관측으로 확인되었다. `server/orchestrator/tools.py:39-44`가 preset_pools를 "the preset TYPES"로 기술하고 `:185-190`이 실번호 `no`를 이름과 함께 반환한다는 코드측 근거에 **실측이 붙었다.** 이는 최종 감사가 구현으로 이월되는 최대 잔여 위험으로 지목한 항목이며, 본 측정으로 (단일 쇼파일 한정 하에서) 닫힌다.

**(b) 점유 판독 / 빈 슬롯 판별 = GO.** in-scope 4개 풀(1 Dimmer · 4 Color · 5 Beam · 6 Focus) 전부 `childCount=0`. `drilldown_capped` **미관측**.

**잔여 기록 (감사 권고 이행)**: 위 풀 이름은 **MA3 기본값**이며 사용자 편집 가능하다. 본 실측은 **쇼파일 1개**다. 최종 감사가 권고한 "관측된 풀 이름을 verbatim 기록해 rename 위험을 성격 규정하라"는 위 전량 열거로 충족한다. 이름이 변경된 쇼파일에서 해석이 실패할 경로는 제거되지 않았다.

**신규 발견 — 스킵 사유 코드의 공백 (M4 후속)**: 풀 타입을 해석할 수 없는 상태를 표현할 사유 코드가 **없다**. REQ-LOOKLIB-013 / AC-LOOKLIB-018 (c)가 열거하는 것은 `conflict` / `no_free_slot` 2종뿐이며 어느 쪽도 "풀 타입 미해석"을 담지 못한다. 이번 세션에서는 해석이 성공해 발동하지 않았으나, M4가 형상을 고정할 때 다뤄야 한다.

#### 측정 3 — ASSUMPTION-13 (그룹 명명 관례) → **매칭 역할 2/6 기록**

힌트 문자열은 spec.md §A 결정 J 표에서 **verbatim** 취했다. 토큰 경계 매칭, 대소문자 무관.

| 역할 | 매칭된 그룹 |
|---|---|
| 백라이트 | `Back` (11) |
| 프론트 | `Front` (12) |
| 사이드 | 미매핑 |
| 탑 | 미매핑 |
| 배경 | 미매핑 |
| 스페셜 | 미매핑 |

- **(b) 모호 매칭(둘 이상 역할 힌트에 걸린 이름): 0건.**
- **(c) 어떤 힌트에도 걸리지 않은 그룹 이름**: `Copilot Grp`(1) · `All`(13) — 힌트 확장 후보.
  - `All`이 어떤 역할도 건드리지 않은 것은 **의도된 동작의 확인**이다. 부분열 매칭이었다면 `All`은 `백라이트` 힌트 `BL`류와 충돌할 소지가 있으나, spec.md §A "토큰 경계 + 약어 정확 토큰 일치" 규율이 그 오탐을 막았다.

**판정**: plan.md §B M0 및 AC-LOOKLIB-020에 따라 **매칭 역할 수를 기록**한다 — 2/6. 이 항목은 DESCOPE 분기가 없다(차단이 아니라 튜닝 입력). **2/6은 휴리스틱의 실패가 아니다**: 이 쇼파일이 표현할 수 있는 역할은 2종뿐이고, 그 2종이 **정확히** 매칭됐다. 기제 자체는 검증되었고, 미매핑 4종은 데이터 부재이지 알고리즘 결함이 아니다. 힌트 문자열 조정 근거는 이번 실측에서 **발생하지 않았다**(모호 매칭 0건 · 오탐 0건) — 즉 **결정 J의 힌트 집합은 무변경으로 M1에 진입한다**(spec.md §A "집합은 시작점" 조항에 따른 조정 없음).

#### 측정 4 — ASSUMPTION-14 (`Store Preset` 캡처 의미론) → **GO, 단 추론 근거 (직접 관측 아님)**

> **증거 등급을 정직하게 적는다 — 상향하지 않는다.** 4건 중 유일하게 직접 관측에 도달하지 못한 측정이다.

**실행 시퀀스**

| 단계 | 프로그래머 상태 | 커맨드 | 결과 |
|---|---|---|---|
| (i) | 컬러 값만 | `Store Preset 4.1` | `OK` |
| (ii) | 딤머 값만 | `Store Preset 1.1` | `OK` |
| (iii) | **혼합** — `ColorRGB_R At 100` + `Dimmer At 80` | `Store Preset 4.2` | `OK` |

**판독**: 풀 4 = 프리셋 2개, 풀 1 = 1개, 풀 5/6 = 여전히 비어 있음 → **교차 풀 오염 0건.**

**GO 근거 2종 (등급 명시)**

1. **구조적 (강)** — 프리셋 에디터가 스스로를 `Edit FeatureGroup 4 'Color'.Preset 2 'M0 Probe Mixed'`로 제목 표기한다. MA3의 타입 풀 1–9는 **구성상 FeatureGroup 스코프**이고 Dimmer는 FeatureGroup 1이므로, FeatureGroup 4 프리셋이 딤머 데이터를 담을 수 없다.
2. **시각 (중)** — Dimmer 풀 프리셋 타일은 레벨 바를 렌더링한다. Color 풀 타일 2개(혼합 케이스 포함)는 레벨 바 없이 렌더링되며 **서로 시각적으로 동일**하다.

**시도했으나 실패한 직접 관측 2건 — 방법론 발견으로 기록한다**

- 프리셋 에디터의 `Sheet` 토글이 사용자 세션에서 **클릭되지 않아** 저장 속성 시트를 판독할 수 없었다.
- **자동 판별 테스트를 설계했다가 폐기했다.** 설계: 빈 프로그래머 → `At Preset 4.2` → `Store Preset 1.3`. **대조군**: 빈 프로그래머, 프리셋 미적용 → `Store Preset 1.4`. **대조군이 테스트를 무효화했다** — MA3가 대조군에도 프리셋을 생성했고(Dimmer 풀이 슬롯 1–4 전부 점유 상태로 종료), 이는 **프리셋의 "존재"가 데이터 캡처 여부를 판별하지 못함**을 증명한다. 모호한 결과를 확증으로 읽는 대신 **테스트 설계 자체를 폐기**했다.

**판정 GO — 추론 기반.** FALLBACK 분기는 **M4가 번들을 실제로 발화해 경험적으로 확인할 때까지 살아 있다.** plan.md §B M0에 따라 FALLBACK 전환 비용은 **커맨드 수 증가뿐이며 라이브러리 재저작을 요구하지 않는다**(REQ-LOOKLIB-001 패밀리 분할 가능성이 흡수). 따라서 이 미확정성은 M1·M2 저작을 막지 않는다.

---

#### 교차 발견 — SPEC이 예상하지 않은 제약

**응답기는 프리셋 내용을 읽을 수 없다.** `DataPool/PresetPools/<pool>/<slot>`은 프리셋의 **존재와 이름**을 `childCount: 0`과 함께 반환하며, **속성 값은 어떤 형태로도 노출하지 않는다.**

**귀결**: 애플리케이션은 **자신이 자기 채널로 생성한 프리셋의 내용을 검증할 수 없다.**

REQ-LOOKLIB-013의 보고 요소(생성 프리셋의 풀/슬롯/이름, 미매핑 역할, 건너뛴 저장, `drilldown_capped`)는 **우연히** 관측 가능한 범위 안에 머문다 — 그러나 그것은 **설계된 제약이 아니었다.** "룩이 실제로 무엇을 저장했는가"를 보고하거나 검증하도록 요구하는 후속 요구는 **현재 구현 불가능**하다. M4의 검증 설계는 이 사실 위에서 이뤄져야 한다(프리셋 내용 assert는 유닛/페이크 층에서만 가능하며 라이브 층으로 승격될 수 없다).

#### 부수 관측

- **프리셋 저장 모드 = `Universal`** (에디터 표시). Universal 프리셋은 픽스처 타입을 가로질러 적용되므로 **이식 가능한 룩 라이브러리에 유리**하다.
- **페이저 필드 전량 `None`** (`X`, `XBlock`, `XGroup`, `Fade From X`, …) — v1 무브먼트 제외(REQ-LOOKLIB-003 v0.3.1 신설 절, AC-LOOKLIB-003 구간 6)와 정합.
- **M2 저작에 직접 영향 — 컬러 스와치 관측**: `Attribute 'ColorRGB_R' At 100` 후 저장한 프리셋의 스와치가 **빨강이 아니라 흰색**으로 렌더링됐다. 이는 store가 변경된 attribute 하나만이 아니라 **컬러 패밀리 전체(R + 기존 값의 G/B)** 를 캡처함과 정합한다(측정 4의 패밀리 스코프 GO를 **간접 보강**하는 관측이기도 하다). **저작 규율**: 의도한 색조를 얻으려면 룩이 **R·G·B를 명시적으로 전부 지정**해야 한다.

#### 정리 기록 (쇼파일 무해성)

- 프로브 프리셋 6개(`4.1`, `4.2`, `1.1`, `1.2`, `1.3`, `1.4`) 전부 `Delete Preset <n>`으로 삭제. 재조회로 풀 1/4/5/6이 **전부 `childCount=0`** 복귀 확인.
- 쇼파일은 프로브 **이전에 사용자가 저장**했다.
- **6건의 쓰기 전부가 사전에 비어 있던 슬롯을 대상**으로 했다 — 덮어쓴 것이 없다.

---

#### 미검증 항목 (Gaps) — 관측하지 **않은** 것

| # | 미검증 내용 | 어긋나는 기대 | 영향 |
|---|---|---|---|
| **G1** | 수용된 빔 문자열의 **값 범위**. 후보당 단일 값(`At 50`)만 발화했다 | AC-LOOKLIB-020 기대 결과: "수용된 문자열 목록·**값 범위** + 각 문자열의 귀속 풀 기록" | M1 로더는 attribute **이름** 소속만 검증하므로(REQ-LOOKLIB-005) M1 차단 아님. M2 저작 시 값 선택 근거가 없다 |
| **G2** | **게이트 감사 로그 미산출** — 프로브가 게이트 미경유 직결 채널(`responder_roundtrip` → `server.bridge.osc`)을 썼다. GUI 관측은 산문으로 기록되었으나 **스크린샷 아티팩트 경로가 제출되지 않았다** | AC-LOOKLIB-020("게이트 경유로 발화하고 … 감사 로그 verbatim 판독") + plan.md §B M0 산출물("콘솔 응답·**감사 로그**·**GUI 스크린샷**") | 판정 4건의 성립에는 영향 없음(콘솔 응답 원문으로 성립). **증거 매체 2종이 빠졌다** — 오케스트레이터 판단 대상 |
| **G3** | ASSUMPTION-14의 **저장 내용 직접 판독** | AC-LOOKLIB-020이 명세한 방법("각각 GUI / `query_state`로 저장 내용 판독")의 **`query_state` 절반은 교차 발견에 의해 구조적으로 불가능**하고, GUI 절반은 이번 세션에서 차단됐다 | GO가 추론 근거에 머문다. FALLBACK 분기 M4까지 존치 |
| **G4** | `drilldown_capped`가 **발생할 수 있는 경로를 타지 않았다** | plan.md §B M0 "`drilldown_capped` 발생 여부 기록" | 아래 별도 항목 |
| **G5** | 단일 쇼파일 · 그룹 4종 · MA3 기본 풀 이름 | 측정 2·3의 일반화 | rename/다른 쇼파일에서의 재현성 미확립 |

**G4 상세 — "미관측"이 "발생하지 않는다"가 아닌 이유 (M4 필수 확인)**

`drilldown_capped`는 `get_rig_context` 계층의 신호다(`server/web/messages.py:385`, `server/orchestrator/tools.py` `drill_into`). 본 프로브가 쓴 `responder_roundtrip` 채널은 `drill_into`를 **호출하지 않으므로 이 신호를 애초에 방출할 수 없다.** 따라서 "미관측"은 **채널의 성질이지 앱 경로의 안전성 근거가 아니다.**

읽어서 확인한 코드 사실 4건으로부터 산술적 우려가 따라온다 — **가설이며, 도구로 확인되기 전까지 결함 주장이 아니다**:

- `RIG_DRILLDOWN_QUERY_CAP = 16` (`tools.py:88`)
- `DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")` (`tools.py:81`)
- `drill_into`는 `no`를 가진 객체당 **쿼리 1건**을 쓰며, 예산은 **한 번의 `get_rig_context` 호출 안에서 모든 드릴 섹션이 공유**한다
- 본 세션 실측: preset_pools `childCount=14`

→ preset_pools 드릴다운만으로 16 중 **14를 소비**하고 `pages`에 **≤2**가 남는다. 실제 cap 발동 여부는 **페이지 수에 달려 있으며 페이지 수는 이번에 측정되지 않았다.** M4는 이 경로를 **실제 `get_rig_context`로** 확인해야 한다 — 본 절의 "미관측"을 안전 신호로 소비하면 안 된다.

#### 잔여 위험 (관측된 것에도 불구하고 남는 것)

1. **측정 4의 GO가 뒤집힐 여지** — 구조적 추론은 강하나 관측이 아니다. M4에서 FALLBACK이 실제로 필요해질 수 있고, 그 비용은 커맨드 수 증가로 한정된다(재저작 없음).
2. **빔 어휘의 열거가 닫히지 않았다** — 픽스처가 풍부한 선택에서 재프로브하면 `{Zoom, Iris}`가 넓어질 수 있다. v1은 이 2종으로 확정하되, 확장은 스키마 변경 없이 가능하다.
3. **풀 이름 rename** — 사용자가 풀을 개명한 쇼파일에서 런타임 해석이 실패하는 경로는 남아 있고, 그 실패를 표현할 사유 코드가 아직 없다(측정 2 신규 발견).
4. **역할 힌트의 실전 적중률** — 2/6은 이 쇼파일의 표현 한계이며, 6종 힌트가 실제 현장 쇼파일에서 얼마나 걸리는지는 M7 종단 세션에서야 더 넓은 표본을 얻는다.

---

#### M0가 확정한 하류 결정 (M1 이후가 전제로 삼는 값)

| 결정 | 확정 값 | 근거 | 소비처 |
|---|---|---|---|
| **REQ-LOOKLIB-003 구간 3 허용 목록** | **`{Zoom, Iris}`** — 이 2종만 라이브러리에 진입한다 | 측정 1 GO | M1 로더 검증, M2 저작 |
| **v1 in-scope 프리셋 풀** | **Dimmer · Color · Beam · Focus (4종)** | 측정 1 GO → 결정 I의 빔 조건부 확장 발동 | M4 번들 형상(룩당 최대 4쌍), AC-LOOKLIB-018 스킵 카운트 |
| 결정 J 힌트 집합 | **무변경** — 조정 근거 미발생 | 측정 3 (모호 0 · 오탐 0) | M1 역할 어휘 모듈, M3 리졸버 |
| 번들 캡처 형상 | **GO 형상**(룩당 1회 캡처 + 풀 타입별 `Store`)으로 진행, FALLBACK 존치 | 측정 4 GO(추론) | M4 |

> 위 2행의 귀결로 acceptance.md §D "동일 지시 반복(더블 인스턴스화)" 엣지 케이스는 **"최대 4건" 분기가 실경로**가 된다(기본 2건 분기 아님). spec.md §A 결정 I의 "최대 4쌍" 상한이 v1에서 실제로 사용된다.

#### 마일스톤 상태

| 마일스톤 | 상태 | 비고 |
|---|---|---|
| **M0** — 라이브 프로브 | **완료** | 판정 4건 확정 · 본 절이 명시적 기록 · 코드 변경 0건 · HALT/BLOCKER 미발동 |
| **M1** — 룩 스키마 + 역할 어휘 + 로더 | **차단 해제** | 유일한 진짜 순서 제약(ASSUMPTION-15 → M1 로더, plan.md §A.2)이 GO로 닫혔고 허용 목록이 `{Zoom, Iris}`로 확정됨 |
| M2~M7 | 미착수 | M2는 M0의 attribute 문법 + 측정 4 컬러 스와치 관측을 저작 입력으로 소비 |

#### M0 시점 AC 상태 스냅샷

(전량 판정은 run-phase 종결 시 최종 매트릭스로 대체한다.)

| AC | 상태 | 근거 |
|---|---|---|
| **AC-LOOKLIB-020** (LIVE, 2건 중 1번째) | **PASS — 조건부(증거 매체 2종 미산출)** | 판정 4건이 각각 명시된 분기로 확정되어 본 §E.2 명시적 섹션에 기록됨. AC 본문이 요구하는 핵심("긍정 결과가 아니라 **실측되고 기록되었다**")은 충족. **단** 기대 결과가 함께 열거한 "감사 로그 jsonl verbatim / GUI 스크린샷"은 산출되지 않았고(G2), ASSUMPTION-14의 명세된 판독 방법도 완주되지 않았다(G3) |
| AC-LOOKLIB-001~019 | PENDING | M1 이후 범위 |

**제약 준수 기록**: 코드 변경 **0건**(M0는 측정 세션 — plan.md §B M0). 워킹 트리 수정은 본 `progress.md` 1파일로 한정 — `spec.md` / `plan.md` / `acceptance.md` / `design.md` / `research.md` 무수정(manager-spec 소유), `server/**` · `console/lua/**` · `ui/src/**` 무수정. 콘솔 잔여물 0건(프로브 프리셋 6개 전량 삭제·재조회 확인). frontmatter `draft → in-progress` 전이는 **수행하지 않았다** — 그 전이는 M1 첫 커밋의 소관이다(spec-frontmatter-schema.md 소유권 매트릭스).

### M1 — 룩 스키마 + 역할 어휘 + 로더 (2026-07-26, cycle_type=tdd) — **완료**

**RED → GREEN 증거.** 테스트 63건을 먼저 작성했고, 모듈 부재로 수집 단계에서 실패함을 확인했다(`ModuleNotFoundError: No module named 'server.looks'`). 이후 3개 모듈을 구현해 전량 GREEN.

**산출 파일 (신규 4건)**

| 파일 | 내용 |
|---|---|
| `server/looks/__init__.py` | 패키지 선언 — 콘솔 무접촉 계약 명시 |
| `server/looks/schema.py` | 룩 스키마 + REQ-003 3구간 어휘 + 풀 패밀리 귀속 + 패밀리 분할(`payload_for_family`) + 왕복(`look_to_dict`) |
| `server/looks/roles.py` | 결정 J 6종 폐쇄 집합(한/영 별칭 + 힌트) + 매칭 규율(`match_role_by_name`) |
| `server/looks/loader.py` | 스키마 검증 + 명시적 에러(REQ-005) + YAML 디렉터리 병합 로더 |

**M0 판정의 하류 반영 (재도출하지 않고 그대로 소비)**

- `PROBE_GATED_ATTRIBUTES = ("Zoom", "Iris")` — 측정 1 GO의 허용 목록 `{Zoom, Iris}`를 그대로.
- 패밀리 라우팅 `Zoom → Focus`, `Iris → Beam` (`10_object_model.md:38-40`), `IN_SCOPE_POOL_FAMILIES = (Dimmer, Color, Beam, Focus)` — 측정 1 GO에 따른 4종.
- 결정 J 힌트 집합 **무변경** 진입(측정 3: 모호 0 · 오탐 0). `Back` → 백라이트, `Front` → 프론트, `All` → 미매핑을 테스트로 고정.

**뮤테이션 검증 (완화된 단언 금지 규율).** 63건이 1회차에 전량 통과했으므로 매처를 3종의 약한 구현으로 치환해 어떤 테스트가 실제로 죽는지 측정했다.

| 뮤테이션 | 죽는 테스트 | 판정 |
|---|---|---|
| 부분열 매칭(경계 없음) | `백색` · `Keys` · `Slash Bar` · `Backdrop` | 경계 규율은 실효 |
| 파이썬 `\b` 경계 | `FrontBack Truss` · **밑줄 구분자**(`BL_Truss`) | 명시적 워드 클래스는 실효 |
| strict 패스만(camel 패스 삭제) | `FrontBack Truss` | camel 패스는 실효 |

- 뮤테이션이 드러낸 공백 1건을 테스트로 보강: `BL_Truss` / `Back_Wash` — 파이썬 `\b`는 `_`를 워드 문자로 취급해 조용히 놓친다.
- **판정 정정 1건**: `All` 케이스는 부분열 매처로도 미매핑이 되므로 **토큰 경계 규율을 판별하지 못한다.** §E.2 측정 3이 근거로 든 `All`/`BL` 충돌은 실재하지 않는다(어느 힌트도 `all`의 부분열이 아니다). 측정 3의 **관측(`All` 0건 매칭)은 사실이고 판정도 유효**하며, 정정 대상은 그 관측에 붙은 **설명**이다. 실제 판별 케이스는 `백색`·`Keys`·`Slash Bar`·`Backdrop`이며 테스트 주석에 그대로 기록했다.

**AC 판정 (M1 = {001, 015})**

| AC | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|
| **AC-LOOKLIB-001** (스키마 로딩 + 검증) | **PASS** | `pytest server/tests/test_looks_schema.py -q` | `63 passed` — 정상 로드 + 위반 18건 **개별** 거부(다이내믹스 0/6/실수/bool · 집합 밖 역할 · 미지 attribute · Shutter · Frost · 풀 귀속 불가 · 중복 id · 미지 키 · 필수 필드 누락 · 빈 역할/속성 · schema_version · 비-매핑 · 무브먼트 미지 attribute) |
| **AC-LOOKLIB-015** (역할 어휘 폐쇄 집합) | **PASS** | 동일 | ① 6종 정확 일치 ② 6종 전부 별칭≥1 + 힌트≥1 ④ 타입 클래스 어휘 0건 ⑤ 모호 매칭 `ambiguous` + 약어 정확 토큰. ③(라이브러리 전수)은 **M2 소관** — M1은 로더의 집합 밖 역할 거부로 대응 |
| AC-015 PRESERVE assert | **PASS** | `git diff --stat server/rulebook/assets/` | 빈 출력 |

**자기 검증 (verbatim)**

| 항목 | 커맨드 | 결과 |
|---|---|---|
| 신규 테스트 | `.venv/bin/python -m pytest server/tests/test_looks_schema.py -q` | exit 0 · `63 passed` |
| 아키텍처 경계 | `.venv/bin/python -m pytest server/tests/test_architecture.py -q` | exit 0 · `4 passed` |
| 전체 회귀 | `.venv/bin/python -m pytest -q` | exit 1 · `1 failed, 1909 passed` |
| 기준선(M1 착수 전) | 동일 | exit 1 · `1 failed, 1849 passed` |
| OSC/bridge import | `grep -rn "bridge.osc\|from server.bridge" server/looks/` | 0건 (exit 1) |
| AskUserQuestion | `grep -rn "AskUserQuestion\|mcp__askuser" server/looks/` | 0건 (exit 1) |
| `/Overwrite` (대소문자 무관) | `grep -rniE "/overwrite" server/looks/` | 0건 (exit 1) |
| PRESERVE diff | `git diff --stat server/safety/ server/rulebook/assets/ console/lua/ ui/src/` | 빈 출력 |
| 린트 | `.venv/bin/python -m ruff check server/looks/ server/tests/test_looks_schema.py` | exit 0 · `All checks passed!` |
| 포맷 | `.venv/bin/python -m ruff format --check <동일>` | exit 0 · `5 files already formatted` |
| 커버리지 | `pytest ... --cov=server.looks` | **95%** (loader 92 · roles 100 · schema 98 · 임계 85 충족) |

- **신규 실패 0건**: 전체 회귀의 유일한 실패 `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`는 **M1 착수 전 기준선에서 이미 실패하던 항목**이며 동일 테스트다. 통과 수는 1849 → 1909로 정확히 **+60**(신규 테스트 수와 일치, 이후 3건 추가로 63건).
- **`_ALLOWED_PREFIXES` 미변경 (판단 근거)**: `test_architecture.py:53`의 `_ALLOWED_PREFIXES`는 OSC 표면 import를 **면제**받는 목록이다. 여기에 `server/looks/`를 추가하면 REQ-LOOKLIB-019가 요구하는 경계 검사에서 **제외**되어 정확히 반대 효과가 난다. 추가하지 않았고, 테스트는 그대로 통과한다(면제 없이 통과 = 경계가 실제로 지켜짐).

**@MX 태그 배치 (plan.md §D 대비)**

| 태그 | 위치 | 비고 |
|---|---|---|
| `@MX:NOTE` | `server/looks/schema.py` 모듈 독스트링 | P1-1/P1-2 공통 기반 + per-show 값 금지 불변식(닫힌 필드 집합 + 미지 키 거부가 그 기제임을 명시) — §D 예상대로 |
| `@MX:WARN` + `@MX:REASON` | `server/looks/roles.py` `match_role_by_name` | 이름 관례 휴리스틱 지점. 미매핑 축소가 정상 동작임 + 힌트 확장 시 그룹 발명 금지 경계 — §D 예상대로 |
| `@MX:ANCHOR` | **신설 0건** | §D의 "fan_in 조건 충족 전까지 NOTE로 시작" 준수 |

**범위 준수**: `server/looks/**`(신규 4) + `server/tests/test_looks_schema.py`(신규 1) + `spec.md` frontmatter `status` 1행 + 본 `progress.md`. plan.md §A.5 PRESERVE 전량 무변경. `20_korean_terms.md` 무변경(REQ-006은 스타일 준수만 요구). 라이브러리 저작 **미착수**(M2 소관) — 자산 디렉터리 `server/looks/library/`는 생성하지 않았고, 로더는 부재 시 명시적 에러를 낸다.

**M2로 이월되는 항목 1건 (신규 발견 아님, 경계 확인)**: AC-LOOKLIB-003 구간 6-i("라이브러리 무브먼트 0건")는 라이브러리가 없으므로 M2 소관이다. M1은 그 짝인 6-ii(**스키마 필드 존재 + 왕복 가능**)를 `TestMovementFieldIsDefinedButUnusedInV1`로 이미 고정했다 — 6-i만 있으면 "필드가 삭제된 것"과 구분되지 않는다는 AC의 지적을 M1에서 미리 봉쇄한 것이다.

### M2 — 내장 4장르 라이브러리 저작 (AC-LOOKLIB-002 / 003 / 004)

**산출물**: `server/looks/library/{worship,rock,ballad,edm}.yaml`(신규 4) + `server/tests/test_looks_library.py`(신규 1, 29 테스트).

**저작 내용**: 32룩 — 워십 8 · 록 8 · 발라드 7 · EDM 9. 사용 attribute는 실측 6종(`Dimmer` / `ColorRGB_R` / `_G` / `_B` / `Zoom` / `Iris`)뿐이며, 밴드 2(`Pan`/`Tilt`)와 M0 기각 문자열(`Focus`/`Frost`/`Prism1`/`Shutter`)은 **주석 포함 전 자산에서 0건**이다. 무브먼트 지정 **0건**(v0.3.1 F3).

**전수 census 테스트의 뮤테이션 검증 (17건 / 생존 0건)**: 테스트를 콘텐츠보다 먼저 작성해 RED(23 error — 자산 디렉터리 부재)를 관측한 뒤 저작했고, 저작 직후 census가 **실제 결함 2건을 잡았다** — ① 네 자산 전부의 top-level `version:` 키(`blacklist.yaml` 패턴을 그대로 옮겨온 것 · 로더의 닫힌 스키마가 거부), ② `edm.yaml` 주석의 `SHUTTER` 문자열(**본 에이전트가 쓴 주석**을 자체 스캔이 적발). 이후 17종 뮤테이션(per-show 값 2종 · 정적 `Pan` · 기각 빔 문자열 · 5번째 장르 · 무브먼트 2종 · 부분 컬러 · 다이내믹스 저역/고역 상실 · 룩 수 하한/상한 · 장르 파일 삭제 · 폐쇄집합 밖 역할 · 범위 이탈 · 중복 id · 한국어 표시명 제거)을 주입해 **전량 KILL, 생존 0건**을 확인했다.

**AC 판정**

| AC | 판정 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|
| **AC-LOOKLIB-002** (커버리지) | **PASS** | `pytest server/tests/test_looks_library.py -q` | `29 passed`. 4장르 · 8/8/7/9룩(전부 6~10) · 장르별 `{1,2}`·`{4,5}` 각 ≥1 · 전 레벨 정수 1~5 |
| **AC-LOOKLIB-003** (attribute 어휘) | **PASS** | 동일 | 구간 1·2·3·4·5·6 개별 테스트 전량 PASS. 구간 6은 두 assert 분리 — (i) 무브먼트 0건, (ii) 무브먼트 담은 룩의 스키마 왕복 성립. `Zoom` 무브먼트 격리 뮤테이션으로 (i)이 **단독 발화**함을 확인(토큰 스캔과 무관하게) |
| **AC-LOOKLIB-004** (per-show 값 부재) | **PASS** | 동일 + `grep -rniE "Pan\|Tilt\|Focus\|Frost\|Prism\|Shutter" server/looks/library/` | grep exit=1(매치 0). 구조(스키마에 바인딩 필드 부재) + 파싱된 문자열 필드 + 원문(주석 포함) 3중 스캔 위반 0건 |

**미검증 잔여 (§E.2 기록 대상)**: `Zoom`/`Iris`의 **값 방향은 실측되지 않았다.** M0는 두 문자열의 *수용 여부*만 측정했고 어느 끝이 좁고/열린 상태인지는 측정하지 않았다. 본 마일스톤은 `Zoom` 저=협·고=광, `Iris` 저=폐·고=개를 **가정**했으며 그 가정을 자산 헤더 주석에 명시했다. 방향이 반대라면 해당 룩은 의도보다 넓거나 좁게 렌더링된다(안전 영향 없음, 미관 문제). M7 종단 검증에서 관측 가능하다.

### M3 — 역할→리그 매핑 리졸버 (AC-LOOKLIB-005 / 006)

**산출물**: `server/looks/resolver.py`(신규 1) + `server/tests/test_looks_resolver.py`(신규 1, 63 테스트). 콘솔 무접촉 — 전 픽스처가 인메모리이며, 입력 리그는 생산자 자신의 헬퍼(`rig_object`/`rig_section`)로 조립한다(손으로 만든 dict는 콘솔 형상이 바뀌어도 계속 통과하므로 경계 테스트가 되지 못한다).

**RED → GREEN 증거.** 테스트 60건을 먼저 작성해 수집 단계 실패를 관측했다(`ModuleNotFoundError: No module named 'server.looks.resolver'`). 구현 후 1건이 실패했는데 **결함은 구현이 아니라 테스트의 전제**였다 — 비공허성 단언이 `NO_MATCH`(값이 `roles.py`에 사는 상수)를 resolver.py 소스에서 찾고 있었다. 스캔이 실제로 읽는 것을 단언하도록 정정했다(리졸버가 소비하는 섹션 키 전량: `reason`/`objects`/`truncated`/`no`/`name`).

**공개 계약**

| 이름 | 형상 |
|---|---|
| `resolve_roles(groups_section) -> RoleResolution` | 입력은 groups 섹션 1개 — 해결된 형상(`{"objects": [...], "truncated": ...}`) 또는 실패 형상(`{"reason": ..., ...}`) |
| `GroupCandidate(number: int, name: str)` | 리그가 등재했고 **주소를 가진** 그룹. `number`는 옵셔널이 아니다 — M4가 `Group None`을 만들 수 있는 경로 자체를 없앤다 |
| `UnmappedRole(role, reason, groups)` | 미매핑 역할 + 사유 + 그 사유를 만든 리그 그룹 이름 |
| `AmbiguousGroup(name, roles)` | 둘 이상 역할이 주장한 이름 — 어느 쪽에도 배정되지 않음 |
| `RoleResolution` | `mapped` / `unmapped` / `ambiguous_groups` / `unaddressable_groups` / `unmatched_groups` / `truncated` / `unavailable_reason` + 조회기 `groups_for` · `unmapped_for` · `reason_for` |

- **불변식**: `set(mapped) | {u.role} == ROLE_NAMES`이며 교집합은 공집합 — 6종 전부가 매핑이거나 명시적 미매핑이다(기계 assert).
- **미매핑 사유 5종**: `no_match` · `ambiguous` · `unaddressable`(신설, 아래) · 그리고 섹션이 오지 않은 경우 `path_not_resolved` / `console_unreachable`가 **역할 단위로도** 그대로 실린다. "어느 그룹도 매칭되지 않았다"는 보지도 못한 리그에 대한 주장이므로 쓰지 않는다.
- **두 실패 사유는 열거하지 않고 verbatim 통과시킨다.** 리졸버는 `REASON_UNRESOLVED`/`REASON_UNREACHABLE`를 import하지도 상수로 갖지도 않는다 — 섹션이 말한 문자열을 그대로 싣는다. 병합이 **구조적으로 불가능**해지고(합칠 대상이 코드에 없다), M5가 `tools.py`에 룩 툴을 등록할 때 생길 순환 import도 함께 없어진다(`tools.py` → `looks.matching` → `looks.resolver` → `tools.py`). 테스트 쪽은 `tools.py`에서 두 상수를 import해 SSOT에 묶여 있다.

**SPEC 열거를 넘어선 결정 1건 — `unaddressable` 사유 신설.** 응답기가 슬롯을 확립하지 못한 그룹(`no` 키 부재)이 어떤 역할에 **정확히** 매칭될 때, 그 역할을 `no_match`로 보고하면 "이 리그엔 백라이트가 없다"가 되어 리그가 실제로 말한 "있는데 번호를 못 붙였다"를 지운다. 두 상태는 고치는 방법이 다르므로(후자는 그 그룹에 슬롯을 주면 끝난다) 사유를 갈랐다. REQ-LOOKLIB-009는 `ambiguous`의 구분만 요구하고 사유 집합을 닫지 않았으므로 위반이 아니라 정보 추가이며, REQ-LOOKLIB-008의 "번호를 발명하지 않는다"를 형상 수준에서 강제하는 장치이기도 하다(`GroupCandidate.number`가 옵셔널이 아니게 된 근거). **M4가 이 사유를 소비해야 한다** — 매핑됐다고 보고된 역할은 전부 주소를 가진다는 것이 리졸버의 계약이다.

**우선순위 결정 1건**: 한 역할에 모호 주장과 미번호 정확 매칭이 동시에 걸리면 **미번호 쪽을 보고**한다 — 운영자가 조치 가능한 쪽(슬롯 부여)이기 때문이다. 모호성은 `ambiguous_groups`에 그대로 남는다.

**M0 실측을 통째로 회귀 테스트로 고정** (`TestM0LiveShowfile`, 6건). `Copilot Grp`(1)·`Back`(11)·`Front`(12)·`All`(13) → 백라이트=`Back`, 프론트=`Front`, 나머지 4역할 `no_match`, 모호 **0건**, `Copilot Grp`/`All`은 `unmatched_groups`. 프로젝트가 가진 유일한 실물 리그 데이터 포인트다.

- **§E.2 측정 3의 설명 정정 1건 (M1이 시작한 정정의 이행)**: `All`이 아무 역할도 건드리지 않은 것은 **토큰 경계 규율을 입증하지 않는다** — 어떤 힌트도 `all`의 부분열이 아니므로 순진한 부분열 매처도 같은 결과를 낸다. 관측은 사실이고 판정도 유효하며, 정정 대상은 그 관측에 붙어 있던 설명이다. 경계 규율을 실제로 판별하는 이름은 `백색`·`Backdrop`·`FrontBack Truss`·`BL_Truss`이며 `TestConsumesTheM1MatchingContract`가 그 역할을 맡는다. 테스트 주석에 이 정정을 명시했다(같은 오해가 다시 쓰이지 않도록).

**뮤테이션 검증 (10건 / 생존 0건)**. 커밋할 소스 그대로에 대해 측정했다.

| # | 뮤테이션 | 죽인 테스트(대표) |
|---|---|---|
| 1 | 두 실패 사유를 `unavailable` 하나로 병합 | `TestTheTwoUnavailableReasonsStaySplit` 2건 + 사유별 verbatim 4건 |
| 2 | 모호 이름을 첫 주장 역할에 배정 | `TestAmbiguous` 4건 + 우선순위 1건 |
| 3 | 미매핑 역할에 그룹을 발명 | 15건 (`TestNeverInventsAGroup` 5 파라미터 포함) |
| 4 | `no` 부재 허용 제거(`entry["no"]`) | `TestUnaddressableGroup` 5건 + 회계/불발명 4건 |
| 5 | 미번호 그룹에 번호를 붙임 | `TestUnaddressableGroup` 5건 + 불발명 1건 |
| 6 | `truncated` 전파 제거 | `test_the_truncation_signal_is_propagated` (+ 비공허성 스캔이 부수적으로 동반 사망) |
| 7 | 매칭을 부분열 스캔으로 재구현 | `백색` · `Backdrop` · 관례 없는 리그 |
| 8 | 미매칭 그룹 이름을 삼킴 | `test_copilot_grp_and_all_match_nothing` 외 1 |
| 9 | 우선순위 뒤집기(ambiguous 먼저) | `test_an_unnumbered_exact_match_outranks_an_ambiguous_claim` |
| 10 | 비-매핑 엔트리 가드 제거 | `TestMalformedEntry` 2건 |

- **1회차에 생존 1건(#9)이 있었고 테스트를 보강해 닫았다.** 우선순위는 코드 주석이 명시한 동작인데 그것을 고정하는 테스트가 없었다 — 문서화된 동작에 테스트가 없으면 그것은 결정이 아니라 우연이다.
- **하니스 결함 1건을 발견해 고쳤다 (측정 신뢰도 문제)**: #9는 **순수 블록 교환이라 파일 크기가 원본과 같다.** CPython의 pyc 무효화는 (mtime 초, 크기) 쌍이므로, 같은 초 안에 원본을 복원하면 뮤턴트의 `.pyc`가 그대로 재사용된다. 실제로 이 오염 때문에 새 테스트가 **원본 코드에서도 실패**하는 것처럼 보였다. 하니스에 `__pycache__` 삭제 + `PYTHONDONTWRITEBYTECODE=1`을 넣고 전량 재측정했으며, 위 표는 재측정 결과다. 이 함정은 뮤테이션이 파일 크기를 바꾸지 않을 때만 발동하므로 M1·M2 결과는 영향받지 않는다(전부 크기 변경 뮤테이션).

**AC 판정 (M3 = {005, 006})**

| AC | 판정 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|
| **AC-LOOKLIB-005** (역할 매핑 리졸버) | **PASS** | `pytest server/tests/test_looks_resolver.py -q` | `63 passed`. 한/영 관례 매핑 · 미매핑 · 신호 전파 3계열이 개별 테스트로 존재하며, 실패 모드 8종(미매칭/모호/truncated/path_not_resolved/console_unreachable/미번호/빈 섹션/비-매핑 엔트리)이 **병합 없이** 각각 고정됨(design.md §6.2) |
| **AC-LOOKLIB-006** (슬롯≠FID + 그룹 발명 금지) | **PASS** | 동일 + `grep -rn "fixtures" server/looks/resolver.py` | ① 정적: 리졸버 소스의 **비-독스트링 문자열 상수 전량**을 AST로 뽑아 `fixture`/`thru`/`attribute`/`pan`/`tilt`/`group ` 토큰 0건 확인(비공허성 동반 단언). fixtures 섹션 소비 경로 부재. ② 산출물: 7종 리그에 대해 모든 후보 `(number, name)`이 입력 리그 등재분에 속함을 파라미터 assert |

- **정적 스캔을 주제 어휘가 아니라 금지 API에 건다**: 리졸버 독스트링은 "왜 fixtures를 읽지 않는가"를 설명해야 하므로 원문 grep은 자기 산문에 걸린다(M2가 자기 주석의 `SHUTTER`에 걸린 것과 같은 함정). AST로 독스트링을 제외하고 **코드 문자열 상수만** 스캔해 이 문제를 없앴다.

**자기 검증 (verbatim)**

| 항목 | 커맨드 | 결과 |
|---|---|---|
| 신규 테스트 | `.venv/bin/python -m pytest server/tests/test_looks_resolver.py -q` | exit 0 · `63 passed` |
| M1·M2·아키텍처 | `... test_looks_schema.py test_looks_library.py test_architecture.py -q` | exit 0 · `96 passed` |
| 전체 회귀 | `.venv/bin/python -m pytest -q` | exit 1 · `1 failed, 2004 passed` |
| 기준선(M3 착수 직전, HEAD 344485e) | 동일 | exit 1 · `1 failed, 1941 passed` |
| OSC/bridge import | `grep -rn "bridge.osc\|from server.bridge" server/looks/` | 0건 (exit 1) |
| AskUserQuestion | `grep -rn "AskUserQuestion\|mcp__askuser" server/looks/` | 0건 (exit 1) |
| PRESERVE diff | `git diff --stat server/safety/ server/rulebook/assets/ ui/ console/` | 빈 출력 |
| 린트 | `.venv/bin/python -m ruff check server/looks/ server/tests/test_looks_resolver.py` | exit 0 · `All checks passed!` |
| 포맷 | `.venv/bin/python -m ruff format --check <동일>` | exit 0 · `6 files already formatted` |
| 커버리지 | `pytest ... --cov=server.looks.resolver` | **100%** (87 stmts / 0 miss) |
| 패키지 커버리지 | `pytest <looks 3종> --cov=server.looks` | **97%** (resolver 100 · roles 100 · schema 98 · loader 93) |

- **신규 실패 0건**: 유일한 실패 `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`는 착수 전 기준선에서 이미 실패하던 동일 테스트다. 통과 수 1941 → 2004 = **+63**(신규 테스트 수와 정확히 일치).
- **§E.3 baseline 불일치 해소 기록**: M1(1909) ↔ M2(1912)의 3건 차이는 규명되지 않은 채 남아 있었다. M3는 착수 직전 HEAD `344485e`에서 **직접** 1941을 실측했고 종료 시 2004를 실측했다 — 두 수 모두 본 마일스톤이 관측한 것이며 이월 인용이 아니다. M1/M2 사이의 3건 차이는 여전히 규명되지 않았다(본 마일스톤은 그 원인을 조사하지 않았다).

**@MX 태그 배치**

| 태그 | 위치 | 비고 |
|---|---|---|
| `@MX:NOTE` | `resolver.py` 모듈 독스트링 | 역할 계층이 **그룹**으로만 해석되고 fixtures를 읽지 않는 이유(슬롯≠FID, `tools.py:33-36`) |
| `@MX:WARN` + `@MX:REASON` | `resolve_roles` | plan.md §D가 예상한 휴리스틱 위험 지대의 **구체적 발현 지점** — 후보 목록이 만들어지는 유일한 자리. M1이 `match_role_by_name`에 건 WARN(힌트 확장 시 발명 금지)과 내용이 다르다: 이쪽은 **후보 합성** 금지(모호 첫 히트 채택 · 미매핑 역할 대체 · 미번호 그룹에 위치 번호 부여) |
| `@MX:ANCHOR` | 신설 0건 | fan_in 미충족 — §D 규율 유지 |

**M6로 이월되는 발견 1건 (본 마일스톤 소관 아님, 보고만 한다)**: AC-LOOKLIB-008 ③이 명시한 `grep -rnE "gate\.screen|execution_port|ConsoleLink" server/looks/` → 0건은 **현재 이미 성립하지 않는다.** `server/looks/__init__.py:6`(M1 산출물)의 독스트링이 실행 경로를 설명하며 `gate.screen()`을 문장 안에서 언급하기 때문이다. `resolver.py`는 0건이며 어느 룩 모듈도 그 API를 **호출**하지 않으므로 REQ-LOOKLIB-010의 실질은 지켜지고 있다 — 어긋난 것은 AC가 적은 검증 수단이다. 정정 방향은 둘(독스트링 표현 변경 / 주석·독스트링 제외 스캔으로 전환)이며 **어느 쪽도 M3가 단독으로 정하지 않는다**: `__init__.py`는 M1 소유이고 AC-008은 M6 소관이다. 위 정적 스캔이 AST 방식을 택한 것은 이 문제의 리졸버 판(版)을 미리 막은 것이다.

**범위 준수**: 신규 2파일(`server/looks/resolver.py` · `server/tests/test_looks_resolver.py`) + 본 `progress.md`. `git status --short server/`가 이 2건만 보고한다. spec.md/plan.md/acceptance.md/design.md/research.md 무수정, PRESERVE 전량 무수정, M1·M2 산출물 무수정(`roles.py`의 매칭 계약은 소비만 했고 재구현하지 않았다). frontmatter 전이 없음 — `status: in-progress`는 M1이 이미 수행했다.

### M4 — 인스턴스화 번들 빌더 + 게이트 배선 (AC-LOOKLIB-007 / 008 / 016 / 018)

**산출물**: `server/looks/instantiate.py`(신규 1) + `server/tests/test_looks_instantiate.py`(신규 1, 98 테스트) + `server/tests/test_looks_boundary.py`(신규 1, 9 테스트) + `server/web/session.py`(배선 1). 콘솔 무접촉 — 리그 형상은 M3와 같이 **생산자 자신의 헬퍼**(`rig_object`/`rig_section`/`drill_into`)로 조립하며, 풀 드릴다운은 실제 `drill_into`에 페이크 state port를 물려 만든다(손으로 쓴 `contents` dict는 `drilldown_capped`·`contents_unavailable` 분기를 재현하지 못한다).

**RED 증거**: 두 테스트 파일을 먼저 작성해 수집 실패를 관측했다 — `ModuleNotFoundError: No module named 'server.looks.instantiate'`. 경계 테스트는 단독 실행 시 8 passed / 1 failed였는데, 그 1건이 `instantiate.py` 부재를 짚는 비공허성 단언이고 나머지 8건은 기존 트리에 대한 회귀 가드다(정직한 RED — 전량 실패가 아니다).

**기준선은 이월하지 않고 직접 실측했다.** 착수 직전 HEAD `c29e543`에서 `1 failed, 2004 passed`. **프롬프트가 지정한 HEAD `ad131b1`은 브랜치에 없다** — 같은 부모(`4cba792`)·같은 subject·**트리 동일**(`git rev-parse ad131b1^{tree} == c29e543^{tree}`)한 고아 커밋이다. 즉 측정 대상 트리는 지시된 트리와 바이트 동일하다.

**번들 형상 (worked example — `ballad-single-key` "단독 키", 6역할 리그)**

```
ChangeDestination Root
ClearAll
Group 16
Attribute 'Dimmer' At 40 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 82 ; Attribute 'ColorRGB_B' At 60 ; Attribute 'Iris' At 32 ; Attribute 'Zoom' At 12
Store Preset 1.1
Label Preset 1.1 '단독 키'
Store Preset 4.1
Label Preset 4.1 '단독 키'
Store Preset 5.1
Label Preset 5.1 '단독 키'
Store Preset 6.1
Label Preset 6.1 '단독 키'
ClearAll
```

M0 ASSUMPTION-14 GO 형상(룩당 1회 캡처 + 풀 타입별 Store)이 기본값이고, FALLBACK(패밀리별 격리 캡처)은 **같은 룩 데이터에서 생성 가능**하다(`shape=` 키워드 1개 — 재작성 아님). 두 형상이 같은 `created`/`skipped`를 내는 것을 기계 assert한다(REQ-001 패밀리 분할 가능성의 증거).

**REQ-011 문언과 GO 형상의 충돌 — 재해석하지 않고 기록한다.** "각 `Store` 후 `ClearAll`"을 GO 형상에서 문자 그대로 지키면 첫 Store 뒤 프로그래머가 비어 2번째 이후 Store가 **빈 프리셋을 만든다**(M0 측정 4의 폐기된 대조군이 "빈 프로그래머에서도 MA3가 프리셋을 만든다"를 이미 증명했다 — 조용한 오작동). 따라서 GO 형상은 `ClearAll`을 **캡처 사이클 경계**(캡처 전 + 사이클 마지막 Store 후)에 둔다. **문언을 문자 그대로 만족시키는 것은 FALLBACK 형상뿐이며**, 이는 SPEC이 예상하지 않은 대칭이다.

**신규 발견 1건 (M4 범위 밖 · 결정 필요) — `run_commands`의 중복 제거가 번들 규율을 침식한다.** `server/orchestrator/tools.py:376-391`은 한 번들 안의 **동일 문자열 커맨드를 재실행하지 않는다**(`skipped_already_executed`). `Store`에는 옳고 `ClearAll`에는 그르다 — 두 번째 `ClearAll`은 효과를 반복하려는 것이 아니라 **다른 시점에** 실행되려는 것이기 때문이다. 실측 결과:

- **GO 형상**: 말미 `ClearAll` 1건이 와이어에서 사라진다(`console.executed == commands[:-1]`, 기계 고정됨). `run_look_bundle`이 `ExecutionContext` 없이 dispatch하므로 다음 번들의 선두 `ClearAll`은 새 dedupe 집합에서 살아남아 실행된다 — 손실은 이중 안전장치 쪽이지만 **손실이다**.
- **FALLBACK 형상**: 사이클 2..N이 `ClearAll`과 `Group` 재선택을 **둘 다** 잃어 이전 사이클의 프로그래머를 그대로 저장한다 — 이 형상이 막으려던 교차 패밀리 과캡처가 정확히 발생한다. **즉 M0가 살려 둔 FALLBACK 분기는 현재 실행 경로로는 발화할 수 없다.**
- **채택한 정의된 동작**: `run_look_bundle`은 `CAPTURE_SHARED`가 아닌 형상을 **거부**한다(`refused` 사유 반환, 콘솔 송신 0건). 조용히 잘못된 프리셋을 쓰는 것보다 크게 거부하는 쪽이다. 해제하려면 dedupe 규칙을 바꿔야 하고 그것은 룩 계층 밖(`tools.py` = M5 소관)이다.

**M0가 M4 후속으로 넘긴 공백 2건 — 정의된 동작을 넣고 사유 코드를 신설했다.**

| 공백 (M0) | M4의 정의된 동작 | 신설 사유 코드 |
|---|---|---|
| 풀 타입을 해석할 수 없는 상태를 표현할 사유 코드가 없다 (측정 2 신규 발견) | 풀 이름 → 패밀리는 **전체 이름 일치**(대소문자 무관)로만 해석. 개명·부재 시 그 풀의 Store만 건너뛰고 이웃 풀은 그대로 진행 | **`pool_unresolved`** |
| (동상) 이름은 맞는데 응답기가 번호를 못 붙인 풀 | `no_match`/`unaddressable` 분화와 같은 근거로 **분리**. 사실이 다르고 조치가 다르다(슬롯 부여로 해소) | **`pool_unaddressable`** |
| `drilldown_capped`를 관측하지 못했고 산술은 빠듯하다 (G4) | 캡은 **살아 있는 가능성**으로 다룬다: 열리지 않은 풀은 `occupied=None`(관측 안 됨) → **비었다고 가정하지 않고** `no_free_slot`으로 건너뛰며, `drilldown_capped`는 보고 (d)로 전파. 캡 이전에 열린 풀은 정상 생성된다 | (기존 `no_free_slot` 재사용 — 요구 문언이 "빈 슬롯 **미관측**"이므로 관측 불가 케이스를 이미 포함한다) |

- `no_free_slot`은 "모든 슬롯이 점유됨"과 "점유를 관측하지 못함"을 **모두** 덮지만 `detail`로 구분한다. 슬롯 탐색 자체는 **쿼리를 1건도 쓰지 않는다**(이미 `get_rig_context`가 캡 16 안에서 지불한 드릴다운을 소비할 뿐) — 기계 assert됨.
- **관측 불가의 세 경로를 하나로 다룬다**: 열리지 않은 풀 / 드릴 실패(`contents_unavailable`) / **슬롯 번호 없는 프리셋이 하나라도 있는 풀**. 세 번째는 "무언가가 점유했는데 어느 슬롯인지 모른다"이므로 어떤 슬롯도 비었다고 주장할 수 없다.

**AC-008 ③ 수단 정정을 커밋된 테스트로 착지시켰다** (`server/tests/test_looks_boundary.py`). `ast.parse`로 실행 위치 식별자(`Attribute.attr` / `Name.id` / import 모듈·별칭명)만 모아 금지 심볼 6종·금지 모듈 프리픽스 4종과 **교집합 0**을 assert한다. 비공허성 2중(모듈당 식별자 수 > 20 + 알려진 심볼 존재), 뮤테이션 2종(호출 1줄·import 1줄 주입)으로 **떨어질 수 있음**을 확인했다. `server/looks/__init__.py:6`의 경계 독스트링은 **보존**되며 스캔을 통과함을 별도 테스트가 고정한다(AP-19).

**같은 부류의 결함을 하나 더 만나 같은 방향으로 고쳤다.** §E 자기 검증의 `grep -rniE "/overwrite" server/looks/` → 0건은 **본 마일스톤에서 1건을 반환한다** — `instantiate.py`의 `@MX:REASON` 주석이 "슬롯이 점유됐을 때 `/Overwrite`로 손이 가는 것"을 금지 이유로 적기 때문이다. AC-008 ③과 정확히 같은 형태(금지 대상을 설명한 산문이 금지 대상으로 계수됨)이므로 **주석을 지우지 않고 스캔을 정밀화**했다: M3의 `_code_string_constants`(독스트링 제외 문자열 상수)를 재사용해 **발화 가능한 문자열 상수**에만 `/overwrite`(대소문자 무관) 부재를 assert하고, 대·소문자 양쪽 주입으로 뮤테이션 확인했다. 주석은 AST 노드가 아니므로 구조적으로 제외된다.

**뮤테이션 검증 (26건 / 최종 생존 0건 · 하니스 결함 0건)**. 커밋할 소스 그대로에 대해 측정했다.

| # | 뮤테이션 | 죽인 테스트(대표) |
|---|---|---|
| 01 | 말미 `ClearAll` 제거 | `test_the_bundle_ends_with_clearall` 외 5 |
| 02 | 선두 `ClearAll` 제거 | `test_every_capture_cycle_opens_with_clearall` 외 5 |
| 03 | 모든 Store에 소문자 `/overwrite` 부착 | 규율 7건 (대소문자 무관 assert 포함) |
| 04 | `Label` 라인 제거 | `test_every_store_is_immediately_followed_by_its_own_label` |
| 05 / 05b / 05c | 관측 불가 점유를 빈 풀로 취급(드릴 실패 / 미개방 / 번호 없는 프리셋) | `TestPoolIndex` 각 1~4건 |
| 06 | **룩 단위 스킵**(첫 스킵에서 룩 전체 포기) | `test_a_partial_conflict_creates_one_and_skips_one` 외 7 |
| 07 / 07b | 라벨 충돌 무시 / 대소문자 고정 비교 | `TestConflict` 7건 / 1건 |
| 08 | **룰북 풀 번호 하드코딩**(`{Dimmer:1, Color:4, ...}`) | `test_the_stored_pool_number_comes_from_the_rig_not_from_a_literal` |
| 09 | 미매핑 역할에 다른 그룹 대입 | `TestUnmappedRoles` 4건 |
| 10 | `pool_unaddressable`를 `pool_unresolved`로 병합 | `TestPoolIndex` 3건 |
| 11 | 풀 이름 부분열 매칭 | `test_a_pool_name_that_merely_contains_a_family_word_does_not_resolve` |
| 12 | 패밀리별 사이클이 전체 페이로드 발화 | `test_a_per_family_cycle_carries_only_that_family_values` |
| 13 | `drilldown_capped` 전파 제거 | `test_the_cap_signal_is_carried_onto_the_report` |
| 14 | 패밀리별 사이클마다 목적지 재발화 | `test_the_per_family_shape_satisfies_clearall_after_every_store_literally` |
| 15 | 매핑 0건인데도 번들 발화 | 6건 |
| 16 | 따옴표 담긴 표시명 허용 | `test_a_label_that_would_break_the_quoting_is_rejected_not_escaped` |
| 17 | 정수값을 float로 발화 | 2건 |
| 18 | 선택 순서를 역할 순으로 | `test_multiple_roles_contribute_their_groups_in_ascending_number_order` 외 1 |
| 19 | 최고 점유 슬롯 +1로 배정(빈 틈 무시) | `test_a_gap_below_the_occupied_slots_is_used` |
| 20 | 값이 없는 패밀리까지 스킵으로 보고 | 15건 |
| 21 / 22 | 발화 가능 문자열 상수에 `/Overwrite` / `/overwrite` 삽입 | `test_no_look_module_carries_overwrite_in_an_emittable_string` |
| 23 / 24 | 비-매핑 풀 엔트리 / 프리셋 엔트리 가드 제거 | `TestPoolIndex` 각 1건 |
| B1 / B2 | 룩 모듈에 `gate.screen()` 호출 / 금지 import 주입 | `test_no_look_module_names_an_execution_path_symbol` |

- **1회차에 생존 3건**이 있었고 전부 닫았다. **그중 2건은 진짜 테스트 공백이었다** — #08(풀 번호 하드코딩)은 `resolve_pools` 층만 검증하고 **번들 층의 AP-16을 고정하지 않았다**(AC-018 (a)가 명시적으로 요구하는 항목이다), #18(선택 순서)은 픽스처가 역할 순서와 오름차순이 **일치하는** 리그를 써서 판별력이 없었다. 나머지 #06은 뮤테이션 자체가 죽은 변수만 추가한 설계 불량이라 재작성했다(하니스 결함으로 계수, 이후 KILL).
- **하니스 신뢰도**: M3가 발견한 stale-`.pyc` 함정을 구조적으로 제거했다 — 드라이버가 매 뮤테이션 전후로 `__pycache__`를 삭제하고 `PYTHONDONTWRITEBYTECODE=1`로 실행한다. 실측 확인: 해당 환경에서 실행 후 `server/` 아래 `__pycache__` 디렉터리 **0개**(대조군 일반 실행은 9개). 동일 크기 뮤테이션(`slot = 1` → `slot = 2`, 17911 바이트 불변)도 재측정했다 — 본 세션에서는 mtime 초가 넘어가 무-purge 조건에서도 KILL되어 **함정 자체는 재현되지 않았다**(따라서 이 실행은 함정의 존부에 대한 증거가 아니다). 방어는 재현 여부와 무관하게 전 뮤테이션에 적용되었다.

**AC 판정 (M4 = {007, 008, 016, 018})**

| AC | 판정 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|
| **AC-LOOKLIB-007** (번들 규율) | **PASS** | `pytest server/tests/test_looks_instantiate.py -q` | `98 passed`. 5 불변식 전량 + 대소문자 무관 케이스: 목적지 선두 1회 · 캡처 사이클 `ClearAll` 개시 · 말미 `ClearAll` · Store 직후 Label · `re.IGNORECASE` `/overwrite` 부재(매처 자체를 대조군으로 검증) · 미등재 그룹 0건 · `Fixture`/`Thru` 0건. 추가 assert(점유 슬롯 재슬롯 아닌 건너뜀): 점유 1·2·3 대상 `Store` 번들 0건 |
| **AC-LOOKLIB-008** (단일 실행 경로) | **PASS** | ① `pytest server/tests/test_architecture.py -q` ② `grep -rn "bridge.osc\|from server.bridge" server/looks/` ③ `pytest server/tests/test_looks_boundary.py -q` ④ `git diff --stat server/safety/` | ① `15 passed` ② exit 1(0건) ③ `9 passed` — AST 식별자 스캔 offender 0건 + 비공허성 2중 + 뮤테이션 2종 확인 ④ 빈 출력. `looks`가 `_ALLOWED_PREFIXES`/`_NAMED_TOOL_EXEMPTIONS` 어디에도 없음을 별도 테스트가 고정 |
| **AC-LOOKLIB-016** (생성형 Lua 우회 부재) | **PASS** | `grep -rnE "build_plugin_xml\|deploy/pack\|lupa\|pcall\|deploy_pipeline\|deploy_plugin" server/looks/` + `git diff --stat server/deploy/` | grep exit 1(0건) · deploy diff 빈 출력. 공허한 참이 아니다 — 스캔이 실제 코드에 도달함을 경계 테스트의 비공허성 단언이 함께 고정한다 |
| **AC-LOOKLIB-018** (요약 보고 형상) | **PASS** | `pytest server/tests/test_looks_instantiate.py -q` | 주입 시나리오 **6개 이상** 각각 개별 assert: (a) 풀·슬롯·라벨 + **풀 번호가 픽스처 유래**(31/32/33/34 리그) · (b) `no_match`/`ambiguous`/`unaddressable` **병합 없이** 한 보고 안에 공존 · (c) 부분 충돌 = 생성 1 + 건너뜀 1, N = 프리셋 저장 수 · (d) `drilldown_capped` |

**@MX 태그 배치**

| 태그 | 위치 | 비고 |
|---|---|---|
| `@MX:NOTE` | `instantiate.py` 모듈 독스트링 | 목적지/`ClearAll` 규율이 **기계화**임 — 트래킹 오염과 빈-프로그래머 Store가 **둘 다 조용한** 오작동이라는 근거 포함 |
| `@MX:WARN` + `@MX:REASON` | 번들 문자열을 만드는 지점 | 커맨드 라인에 오르는 **모든 숫자**가 리그 유래여야 함. 유혹 4종 명시(미매핑 역할 대체 · 미개방 풀을 빈 것으로 가정 · 룰북 산문의 `Preset 4.x` 하드코딩 · 점유 시 `/Overwrite`) |
| `@MX:NOTE` | `session.py` `run_look_bundle` | 이것이 **호출자**이지 제2 실행 경로가 아님 |
| `@MX:ANCHOR` | 신설 0건 | fan_in 미충족 — §D 규율 유지 |

**미검증 잔여 / 라이브 이월 (M7)**

1. **다중 그룹 선택 문법 `Group 11 + 12`는 문법서 유래이지 실측이 아니다.** `00_grammar.md`의 "Additive selection uses `+`"는 객체 참조 일반 규칙으로 적혀 있으나 룰북이 라이브 검증한 사례는 `Fixture 11 + 12 + 13`이고 `Group`은 단일형 `Group 11`뿐이다. 단일 역할 룩은 검증된 형태만 발화한다. M7 필수 관측 항목.
2. **`run_commands` dedupe 상호작용**(위 신규 발견) — GO 형상의 말미 `ClearAll` 실종을 실물에서 확인하고, FALLBACK 형상의 실행 가능성 복구 여부를 결정해야 한다.
3. **프리셋 내용 검증 불가**(M0 교차 발견) — 응답기가 프리셋 속성 값을 노출하지 않으므로 "룩이 실제로 무엇을 저장했는가"는 유닛/페이크 층에서만 assert 가능하다. M4의 어떤 테스트도 라이브 층으로 승격될 수 없다.
4. **풀 contents의 truncation 신호 부재** — `drill_into`는 자식 목록의 `truncated`를 보존하지 않으므로(`child_payload.get("children", [])`), 프리셋이 매우 많은 풀에서 잘린 목록을 완전한 것으로 읽어 점유 슬롯을 비었다고 판단할 경로가 남아 있다. 본 마일스톤은 이를 **제거하지 못했고** 가정하지도 않았다 — 관측되지 않은 위험으로 기록한다.

**범위 준수**: 신규 3파일 + `server/web/session.py` 배선 1건 + 본 `progress.md`. `git status --short`가 이 4건만 보고한다. spec.md/plan.md/acceptance.md/design.md/research.md 무수정, PRESERVE 전량 무수정(`git diff --stat server/safety/ server/rulebook/assets/ ui/ console/` 빈 출력), M1~M3 공개 계약 무수정(소비만). frontmatter 전이 없음 — `status: in-progress`는 M1이 이미 수행했다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: in-progress          # M1·M2·M3·M4 완료 · M5~M7 미착수
milestones_complete: [M0, M1, M2, M3, M4]
m1_commit_sha: c1c1382
m1_complete_at: 2026-07-26
m2_commit_sha: 9b76fce
m2_complete_at: 2026-07-26
m3_commit_sha: 121e52b
m3_complete_at: 2026-07-26
m4_commit_sha: f398d6b
m4_complete_at: 2026-07-26
ac_pass_count: 11                # 001, 015(M1) + 002, 003, 004(M2) + 005, 006(M3) + 007, 008, 016, 018(M4)
ac_fail_count: 0
ac_pending_count: 8              # 009~014, 017, 019 — M5 이후 범위
preserve_list_post_run_count: 0  # PRESERVE 목록 위반 0건
new_warnings_or_lints_introduced: 0   # ruff check/format: 신규 파일 clean
                                      # (리포지토리 사전 baseline 3 E501 + 25 format은 무관·무수정)
baseline_full_suite: "1 failed, 2004 passed"   # M4 착수 직전 직접 실측 (HEAD c29e543)
post_m4_full_suite: "1 failed, 2111 passed"    # +107 = 신규 M4 테스트 전량
new_failures: 0                  # 동일한 사전 실패 1건(test_every_candidate_socket_is_released), 신규 0건
coverage_server_looks: "98%"     # instantiate 100 / resolver 100 / roles 100 / schema 98 / loader 93
coverage_instantiate: "100%"     # 184 stmts / 0 miss
cross_platform_build: n/a        # 순수 파이썬 · 컴파일 산출물 없음
total_run_phase_files: 16        # M1 5 + M2 5 + M3 2 + M4 4 (신규 3 + 배선 1)
library_look_count: 32           # 워십 8 · 록 8 · 발라드 7 · EDM 9
library_movement_spec_count: 0   # v0.3.1 F3
mutation_kill_rate: "53/53"      # M1·M2 17 + M3 10 + M4 26 · 최종 생존 0건
                                 # M4 1회차 생존 3건 → 2건은 진짜 테스트 공백(AP-16 번들층·선택 순서)으로
                                 # 테스트 신설, 1건은 뮤테이션 설계 불량으로 재작성 후 KILL
resolver_unmapped_reasons: 5     # no_match · ambiguous · unaddressable(신설) · 두 unavailable 사유
skip_reasons: 4                  # conflict · no_free_slot + M4 신설 pool_unresolved · pool_unaddressable
capture_shape_default: shared_capture   # M0 ASSUMPTION-14 GO · FALLBACK도 같은 데이터에서 생성 가능
push_performed: false            # 지시에 따라 푸시하지 않음

# --- M4 후속: dedupe 예외 (M4가 발견하고 M4 파일 범위 밖에서 고친 결함) ---
m4_followup_scope: "run_commands dedupe 예외 — 프로그래머 상태 커맨드"
m4_followup_commit_sha: pending-backfill-m4-followup
m4_followup_complete_at: 2026-07-26
m4_followup_files: 4             # tools.py(수정) + session.py(거부 해제) + 테스트 2
m4_followup_baseline: "1 failed, 2111 passed"   # 착수 직전 직접 실측 (HEAD f0f6e76)
m4_followup_post_suite: "1 failed, 2120 passed" # +9 = 신규 테스트 전량 · 신규 실패 0건
m4_followup_mutation: "7/7"      # 생존 0건 · 대소문자 · 선두토큰 · 전량면제 · 전량비면제 · Fixture · Thru · +/-
fallback_shape_executable: true  # 거부 해제 · 21줄 번들 정확 왕복 (4 격리 사이클 보존)
```

> **M4 후속 — 위 블로커성 발견 해소 (2026-07-26)**: `run_commands`의 dedupe가 **프로그래머 상태 커맨드**를 면제하도록 좁혀졌다(`server/orchestrator/tools.py` `_is_programmer_state`). 원칙: dedupe는 **영속 산출물**의 중복을 막는 장치이고, 프로그래머 상태를 세우는 커맨드는 중복시킬 산출물이 없다 — 효과는 멱등이지만 **의미는 위치 의존적**이다. `ClearAll`이 두 번 나온 것은 같은 명령 두 번이 아니라, 서로 다른 두 순간에 실행되어야 하는 하나의 명령이다. 면제 집합은 열거형이며 커맨드의 **선두 토큰**에 고정된다(`ClearAll`, 그리고 `Fixture`/`Group`의 **맨 선택형**만 — `Store Group 7` · `Label Group 7 '...'` · `Delete Group 3` · `Group 3 Full` · `Fixture 1 Thru 10 At 80`은 전부 dedupe 유지). 피연산자 문법(`+` · `-` · `Thru` · 열린 범위)은 `00_grammar.md:17-22`에서 객체 참조 일반 규칙으로 확인했다(룰북 자신의 비-Fixture 예시 `Cue 3 Thru 7`). 대소문자 무시 — 콘솔이 그렇다(D14). 넓은 선택의 차단은 여전히 **게이트** 소관이며(`server/safety/classify.py`가 상류에서 선별), 본 예외는 실행 가능 범위를 넓히지 않는다.
>
> **거부 해제**: 결함이 사라졌으므로 `run_look_bundle`의 per-family 거부는 지킬 것이 없어졌다. 해제 전 프로브로 21줄 FALLBACK 번들이 `console.executed == plan.commands`로 **정확히** 왕복함을 확인했고(4개 격리 사이클 · `ClearAll` 5회 · `Group 11` 4회 전부 보존, `is_error: False`), 그 뒤에 해제했다. M4가 defect를 고정하던 테스트 2건(`..._drops_the_trailing_clearall_...`, `..._per_family_shape_is_refused_...`)과 그 control 1건은 고쳐진 동작을 고정하도록 재작성했다. `test_tools.py`의 기존 dedupe 고정 테스트 2건(`test_already_executed_commands_are_skipped`, `test_in_bundle_duplicate_command_is_not_re_executed`)은 **무수정 통과** — 둘 다 일반 문자열(`"A"`, `"cmd1"`)을 쓰므로 면제 술어에 걸리지 않는다.
>
> **미검증 잔여**: `Fixture` 면제는 **선행적**이다 — 현재 이 코드베이스에서 `Fixture` 선택 라인을 발화하는 프로덕션 경로는 없다(룩 층은 `Group`만 쓴다). 유닛 층에서만 검증되었고 라이브 관측은 없다. 위 §E.2 "미검증 잔여 1번"(`Group 11 + 12`가 문법서 유래이지 실측이 아님)은 **그대로 열려 있다** — 본 후속은 dedupe만 고쳤을 뿐 그 형태를 실측하지 않았다. `ruff format --check`는 두 파일에서 여전히 실패하나 그 4개 지점은 전부 HEAD `f0f6e76`에서 이미 비-clean이던 **기존** 라인이며(직접 확인), 무관한 재포맷을 피하려 손대지 않았다.

> **M4 블로커성 발견 (오케스트레이터 결정 필요, 본 마일스톤 범위 밖)**: `run_commands`의 번들 내 중복-커맨드 제거(`server/orchestrator/tools.py:376-391`)가 `ClearAll` 규율을 침식한다. GO 형상은 말미 `ClearAll` 1건을 잃고(다음 번들의 선두 `ClearAll`이 덮는다), **FALLBACK 형상은 격리가 완전히 붕괴한다** — 따라서 `run_look_bundle`은 FALLBACK 형상을 실행하지 않고 거부한다. M0가 ASSUMPTION-14의 안전망으로 살려 둔 분기가 **현재 실행 경로로는 발화 불가**라는 뜻이므로, dedupe 규칙 개정(=`tools.py`, M5 소관) 여부는 M4가 단독으로 정하지 않는다.

> **M1/M2 baseline 불일치**: M3가 규명 실패로 남긴 3건 차이는 M4에서도 조사하지 않았다. 본 §E.3의 델타는 M4가 착수 직전 `c29e543`에서 **직접 실측한 2004**와 종료 시 **직접 실측한 2111**에만 귀속된다 — 이월 인용 0건.

> **M1/M2 baseline 불일치 (미해소로 유지)**: M1의 `1909`와 M2가 같은 HEAD에서 실측한 `1912`의 3건 차이는 여전히 규명되지 않았다. M3는 이 숫자를 이월하지 않고 착수 직전(`344485e`)에 **직접** `1941`을 실측했으므로 위 델타 판정은 본 마일스톤이 관측한 두 수에만 귀속된다.

> **baseline 주의**: M1이 기록한 `post_m1_full_suite: "1 failed, 1909 passed"`와 본 마일스톤이 동일 HEAD(`c1c1382`)에서 실측한 `1 failed, 1912 passed`가 3건 어긋난다. 원인은 규명하지 못했다(작업 트리의 추적 대상 변경은 `.moai/` 문서뿐이다). 본 §E.3의 델타 판정은 **본 마일스톤이 직접 실측한 1912**에 귀속시켰다 — 이월된 숫자를 baseline으로 쓰는 것은 측정이 아니라 인용이기 때문이다.

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
