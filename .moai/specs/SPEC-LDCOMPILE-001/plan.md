# 구현 계획 — SPEC-LDCOMPILE-001

[요구사항](spec.md) · [인수](acceptance.md) · 우산: [계약](../SPEC-LDPLUGIN-001/contract.md) · [설계](../SPEC-LDPLUGIN-001/design.md) · [근거](../SPEC-LDPLUGIN-001/research.md) · 형제: [저장층](../SPEC-LDSTORE-001/spec.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 우산
`SPEC-LDPLUGIN-001/spec.md:23` 과 같은 조건이 승계된다. 승인 없이 구현을 시작하지 않는다.

[HARD] **착수 전에 `spec.md` §6 의 갈등 셋을 먼저 해소해야 한다.** 그중 §6.3(음수 ms)은
우산 수준의 판정이 필요하므로 자식이 임의로 진행하지 않는다. §6.1(축별 emitter 0건)은
Tier 등급 자체를 재산정하게 만든다.

## 2. 마일스톤

착수 순서를 정하는 원리 하나: **거부는 로컬로 닫히고, 승격만 콘솔이 필요하다** (`spec.md`
§5). 그래서 먼저 정직하게 전부 `blocking` 으로 만들고, 실측된 것만 하나씩 연다. 순서를
뒤집으면 — 지원한다고 먼저 선언하고 나중에 실측하면 — 그 사이에 실측되지 않은 표현이
사람 승인 대기열에 오른다.

| 단계 | REQ | 파일 소유 | 완료 산출물 | 콘솔 | 얇은 왕복 |
|---|---|---|---|---|---|
| C1 검증 골격·진단 | 014 | 신규 `server/director/validate/{__init__,pipeline,diagnostics}.py` | `LD-VAL-001` 6단 순서, action별 최소 1진단, leaf JSON Pointer, `before/after`, critical blocking → `compiled.available=false` · `outcome=blocked`. `LDSTORE` 의 `PlanValidator` seam 에 꽂힌다 | 아니오 | **예 — 필수** |
| C2 시간 해석 | 009(계산부) | 신규 `server/director/validate/timing.py` | 원음 첫 sample=0ms, 전곡 분할 검사, 동일 ms → 단일 semantic cue, `beat(t)` 연속성, 반올림(정확한 .5는 +방향), tempo segment 교차 분할, `manual_go`/`trig_time` delta(준비 cue 포함) | 아니오 | **예 — 최소판** |
| C3 tracking·FX·ready | 010, 011 | 신규 `server/director/validate/{simulate,conflict}.py` | 축별·fixture별 simulation, 누락=hold, 첫 full baseline, `instance_id` 1:1 start/stop, `active_fx` terminal 빈 배열, fixture×axis 겹침 검출(동일 값이어도 conflict) | 아니오 | **예 — 최소판** |
| C4 capability 거부 | 008, 013(거부부) | 신규 `server/director/validate/capability.py` | `LD-CAP-001` 을 **blocking 으로** 구현. 요청 field 제거·fallback preset·percent clamp·quantize 금지를 시험으로 고정. 축별 timing 은 실측 전까지 `unsupported` | 아니오 | 아니오 — 유보 |
| C5 dark move·re-entry 거부 | 012 | 신규 `server/director/validate/mib.py` | 증명할 수 없으면 `blocking`. `random_access` 를 미지원인데 true 로 광고하지 않음. authored reveal 시각 불변 | 아니오 | 아니오 — 유보 |
| C6 emitter 프로브·승격 | 008·009(fidelity), 012(실측), 013(승격) | 신규 `server/director/emit.py` + 프로브 기록 | 축별 delay/fade 를 실제로 보존하는 콘솔 문법을 프로브로 찾고, 관측된 것만 capability 를 승격. frozen artifact bytes + manifest | **예** | 아니오 — 유보 |

C1 → C2 → C3 → C4 → C5 → C6. C1 이 뿌리다 — 진단 형태가 정해지지 않으면 나머지가 낼 것이
없다. C6 은 마지막이며 실기 콘솔 없이 시작할 수 없다.

### 2.1 얇은 왕복에서 이 층이 내는 것

감독 결정(2026-09-14): 얇은 왕복은 **출시가 아니라 내부 마일스톤**이다.

이 층이 내는 것은 **C1 전체 + C2·C3 최소판**이다. 그 상태에서 왕복은 이렇게 성립한다:

```
플러그인이 계획 제출 → LDSTORE 가 저장(불변·CAS) → C1 검증기가 판정
  → ValidationReport(outcome=blocked, 진단에 leaf pointer) → 사람이 무엇이 왜 막혔는지 본다
```

`blocked` 는 실패가 아니라 **정직한 왕복의 종점**이다. 축별 emitter 가 0건인 상태에서
`ready_for_review` 가 나오면 그것이 거짓이다.

[HARD] **C4 를 유보하는 것이 "검사를 미룬다"는 뜻이 아니다.** C1 의 `LD-VAL-001` 파이프라인은
capability 단계를 **무조건 blocking 으로** 통과시킨다 — 즉 유보 상태의 기본값이 안전한 쪽이다.
C4 가 하는 일은 그 blocking 의 *사유를 축·op별로 정확하게 만드는 것*이지, blocking 을
켜는 것이 아니다.

### 2.2 검증기 seam — 형제가 이미 열어 두었다

`SPEC-LDSTORE-001` 의 `server/director/service.py` 가 `PlanValidator` Protocol 을 정의하고
기본 구현 `NotInstalledValidator` 가 `blocked` + `reason="validator-not-installed"` 를 답한다.

C1 은 그 Protocol 을 구현한 클래스를 새로 만들어 주입한다. **`service.py` 를 수정하지 않는다** —
seam 이 이미 그 목적으로 있으므로 고칠 것이 없다. 기존 stub 은 지우지 않고 남긴다(검증기
없이 서버를 띄우는 경로가 여전히 유효해야 한다).

## 3. PRESERVE — 건드리지 않는다

| 영역 | 파일 | 이유 |
|---|---|---|
| OSC 송신 (서버 유일 표면) | `server/bridge/osc.py` | 이 층은 import 하지 않는다. artifact 는 bytes 이고 발화가 아니다 |
| 3단 안전 게이트 | `server/safety/*.py` | 승인·실행은 `SPEC-LDRECV-001` |
| 저장층 | `server/director/{models,store,service,digest}.py` | 형제 SPEC 소유. C1 은 읽고 seam 에 꽂을 뿐 |
| 예술 producer 둘 | `server/looks/songcue.py`, `server/web/session.py` `_ARC_*` | cutover 는 `SPEC-LDCUTOVER-001` |
| 기존 LXSEQ 경로 | `server/lxseq/*.py`, `server/design/cue_*.py` | **읽기만 한다.** C6 프로브의 참고 자료이며 수정 대상이 아니다 |
| 앱 표면·데스크톱 | `server/web/{app,messages,handshake}.py`, `ui/src/`, `src-tauri/` | 범위 밖 |

### 3.1 공유 파일 직렬화 — 이 SPEC 은 충돌하지 않는다

우산 `plan.md` §2 가 동시 작성을 금지한 넷 — `server/orchestrator/tools.py`,
`server/web/session.py`, `server/web/app.py`, `server/safety/gate.py`.

**이 SPEC 이 쓰는 것은 하나도 없다.** C6 이 `tools.py` 를 **읽지만**(축별 timing 을 낼 문법을
찾기 위해 현행 `per_row_timing` 조립을 참고한다) 새 emitter 는 `server/director/emit.py` 에
독립으로 만든다. 우산이 *"scalar CueFade 근사 제거(Director 경로)"* 라고 경로를 나눠 적은
이유가 이것이다 — 기존 경로를 고치면 기존 실측이 무효가 된다.

## 4. TDD 순서

### C1 (검증 골격) — 이 SPEC 의 뿌리

1. **RED** `server/tests/test_director_validate_pipeline.py`:
   - 6단 순서가 실제 순서인지. 앞 단계가 blocking 이면 뒤 단계 진단이 **없어야** 하는가,
     아니면 전부 수집하는가 — 계약 §8 `LD-VAL-001` 을 읽고 그대로 고정한다.
   - 요청 action N 개에 진단이 최소 N 개.
   - critical blocking 하나 + 정상 action 여럿 → `outcome=blocked`,
     `compiled.available=false`, 그리고 정상 action 에도 진단이 붙는다 (`AC-LDPLUGIN-014`).
   - 조용한 수용이 `before/after` 둘 다 `present=false` + 사유로 표현되는가.
   - pointer 가 **submitted plan root** 기준이고 `""` 가 전체 plan 인가.
   - **양성 대조**: 계약 §11 의 `examples/validation.json` 이 우리 출력 shape 과 같은가.
     `LDSTORE` 의 `parse_exchange` 로 왕복시켜 스키마를 통과하는지 함께 본다.
2. **GREEN** `pipeline.py` + `diagnostics.py` 최소 구현. capability·fidelity 단계는
   무조건 blocking (§2.1).
3. **REFACTOR** 진단 조립을 한 자리로 모은다.

### C2 (시간) — 순수 함수여서 경계값이 전부다

1. **RED** `server/tests/test_director_validate_timing.py`: 첫 cue=0, section 경계
   `start<=at<end`, 전곡 `[0,duration)` 무겹침·무공백 분할, 동일 ms 묶기, `beat(t)` 인접
   segment 연속성, **정확한 .5 반올림이 +방향**, 반올림으로 생긴 충돌은 거부, tempo segment
   를 가로지르는 FX instance 는 분할 아니면 unsupported, `trig_time` 의 첫 bundle 만
   `manual_go/0` 이고 이후 `relative_ms = at_ms − 직전 최종 bundle at_ms`, 준비 cue 도
   delta 계산에 포함.
2. **GREEN** `timing.py`.

**주의**: 여기서 기본 BPM 을 넣고 싶은 유혹이 생긴다. 넣지 않는다 — `LD-TIME-002` 가
*"tempo 불명인데 120 BPM을 가정하지 않는다"* 고 못박았고, 이 저장소의 `profile.py` 도
같은 이유로 `fx_rate` 역산을 채택 후보에서 뺐다 (`spec.md` §6.2).

### C3 (simulation·충돌)

1. **RED** `server/tests/test_director_validate_conflict.py`: 겹친 두 group 이 같은 fixture
   의 같은 축을 **같은 값으로** 써도 conflict, `transition 끝 == 다음 시작` 은 허용, FX
   `affects_axes` 와 static 겹침은 conflict, FX stop fade 완료 뒤에만 그 축 재사용 가능,
   delay 구간도 예약 구간이다.
2. **RED** `server/tests/test_director_validate_ready.py`: 누락 axis 는 hold(상속 아님),
   첫 cue 가 controlled group 전부의 4축 baseline 을 지정하지 않으면 blocking, stop 없는 FX
   는 blocking, `active_fx` terminal 이 빈 배열이 아니면 blocking, terminal_state 가
   simulation 결과와 정확히 일치.
   **음성 대조**: 조용한 엔딩·동일 후렴 강도 plan 은 **통과해야 한다** — `LD-STATE-002` 가
   유효하다고 명시했으므로, 이것이 실패하면 예술 정책을 주입한 것이다.
3. **GREEN** `simulate.py` + `conflict.py`.

### C4·C5 (거부의 정확도)

각 op·축별로 "왜 unsupported 인가" 를 진단에 담는다. `AC-LDPLUGIN-008` 이 요구하는 **표현
범위별 trace matrix** 를 산출물로 낸다.

### C6 (프로브·승격) — 콘솔 게이트

1. 기존 실측 기록을 먼저 읽는다: `server/design/cue_fade.py` 독스트링(프로브 T11 §2/§4),
   `docs/handoff/2026-08-15-timeline-workflow-handoff.md:19`(`Property 'Fade'` 금지 근거).
2. 축별 delay/fade 문법 후보를 **프로브로** 찾는다. 실측 전에 문법을 코드에 넣지 않는다.
3. 관측된 조합만 capability 를 승격한다. 승격은 `compiler version/build` + `rig fingerprint`
   에 고정한다 (우산 `plan.md` §3 마지막 문단).

[HARD] **안전장치를 발사해서 확인하지 않는다.** 콘솔 쓰기를 포함하는 프로브는 감독 승인
뒤에만 돈다. 확인과 사고가 같은 행위가 되는 검사는 설계하지 않는다.

각 단계마다 `uv run pytest` 전체를 돌려 기준선이 깨지지 않는지 본다.

## 5. 검증 명령

```bash
# 이 SPEC 범위
uv run pytest server/tests/test_director_validate_ -q

# 회귀 (기준선 대조)
uv run pytest -q          # 기대: 12928 + 신규 통과, skipped 31, 실패 0

# 경계: 이 층이 OSC 를 import 하지 않는지 (주석이 아니라 실제 import 를 본다)
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/ || echo "OK - no OSC import"

# 경계: 예술 producer 를 호출하지 않는지
grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ || echo "OK - no artistic producer"

# 경계: 기존 LXSEQ/design 경로를 수정하지 않았는지
git diff --name-only origin/main -- server/lxseq server/design | grep . && echo "FAIL: PRESERVE 위반" || echo "OK"
```

**CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 명령의 출력만 증거로 쓴다.
그리고 §2 표의 「콘솔 = 예」 항목은 위 명령들로 판정할 수 없다 — 관측 기록이 별도 증거다.

## 6. 중단 조건

- **`spec.md` §6.3(음수 ms)의 판정을 받기 전에 C2 를 완결하지 않는다.** 계약과 코드가 정면
  으로 다르므로 자식이 한쪽을 고르면 그 선택이 조용한 규범이 된다.
- 검증 순서·진단 shape 이 우산 `contract.md` §6.3/§8 과 어긋나는 것이 발견되면 **중단하고
  보고한다.** 계약이 단일 원본이다.
- C6 프로브가 축별 timing 문법을 **찾지 못하면** 중단하고 보고한다. 그 경우 계약 §7 의 축별
  독립 timing 은 이 하드웨어 조합에서 영구 `unsupported` 이며, 그것은 우산 `spec.md:41`
  (첫 릴리스 표현 범위)에 대한 판정이 필요한 사안이다 — 자식이 조용히 축소할 수 없다.
- 형제 `SPEC-LDSTORE-001` 의 `PlanValidator` Protocol shape 이 바뀌면 중단하고 조정한다.

## 7. 미검증 (착수 전 남은 것)

- **우산 `contract.md` §4·§10·§11 미독.** C1 착수 시 §6.3·§8 을 다시 읽고 §11 예제로 대조한다.
- **LOC 추정 없음.** `spec.md` §6.1 때문에 Tier L 등급 자체가 재산정 대상이다 — C6 이
  프로브 탐색을 포함하므로 상한을 예측할 근거가 없다.
- **`plan-auditor` 없음.** 이 저장소에서 착수 전 컨텍스트 초과로 죽는다(실측 적재 ≈114K
  토큰). 이 계획의 품질 판단은 orchestrator 자기 검수다.
- **실기 콘솔 관측 0회.** §2 표의 콘솔 항목 전부.
