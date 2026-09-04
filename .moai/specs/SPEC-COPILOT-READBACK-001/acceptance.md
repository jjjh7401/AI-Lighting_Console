# SPEC-COPILOT-READBACK-001 — 인수 기준

> 각 항목은 **이진 판정 가능**해야 한다. 부정 대조군이 없는 항목은 통과해도 계기 고장과 구별되지 않는다.
> 오프라인 명령은 저장소 루트에서, 라이브 명령은 운영자 승인 후 M3 에서만.
>
> **AC 번호는 REQ 번호와 대응하지 않는다.** 대응은 각 AC 제목 끝의 `↔ REQ-READBACK-0xx` 표기와 §H 커버리지 표가 정본이며, 번호 관례에 기대어 매핑을 추측하지 않는다.

## A. 실행 명령

```bash
# 오프라인 — R1 응답기 (실제 .lua 를 lupa 로 실행)
uv run pytest server/tests/test_lua_responder.py server/tests/test_lua_responder_payload_budget.py server/tests/test_responder_protocol.py -q

# 오프라인 — 잠금 규약 (다이제스트 재고정 검증)
uv run pytest server/tests/test_overlap_preserve.py -q

# 오프라인 — R2 매퍼·프리셋 API 고정 (값 판독 전에는 계속 value_match 를 고정한다)
uv run pytest server/tests/test_lxseq_preset_mapper.py server/tests/test_web_presets_api.py -q

# 오프라인 — 조사 노트 표제 검사 (미발견 경로를 닫을 때만 의미가 있다)
grep -c -E '^#{1,6}\s*(시도한 이름|사유|대조군|실행일)\b' <조사노트경로>

# 라이브 검증(읽기 전용) — M3, 운영자 승인 후
# 이 명령은 --skip-exec 로 쓰기를 하지 않는다. 이 SPEC 의 유일한 콘솔 쓰기(응답기
# 재임포트 1회)는 여기에 없으며 plan.md §E M3-1 이 그 절차와 승인 게이트를 소유한다.
.venv/bin/python server/tools/responder_roundtrip.py --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool
```

---

## B. R1 — 응답기 테이블 직렬화

**AC-READBACK-001** — 테이블 값이 JSON 으로 도착하고, 회신 키 집합은 그대로이며, 결과가 결정적이다 ↔ REQ-READBACK-001, REQ-READBACK-004
Given `lua_mock_env.py` 의 `__NODE._props` 에 `{a=1, b="x"}` 형태의 테이블이 심겨 있고
When `props` 로 그 프로퍼티를 읽으면
Then 회신의 `t` 는 `"table"` 이고, `v` 는 `json.loads` 로 파싱되어 `{"a":1,"b":"x"}` 와 같으며, `table: 0x` 문자열은 `v` 어디에도 나타나지 않는다.
그리고 Then 그 회신 항목의 **키 집합이 1.6.3 회신의 키 집합과 동일**하다 — 새 형제 필드가 하나도 늘지 않았다.
그리고 Given 같은 테이블을 두 번 읽으면 When 두 회신의 `v` 를 비교하면 Then **바이트 단위로 동일**하다.

**AC-READBACK-002** [부정 대조군] — `[1]` 키를 가진 해시가 키를 잃지 않는다 ↔ REQ-READBACK-004
Given `{[1]="first", name="kept", flag=true}` 가 심겨 있고
When 그 프로퍼티를 읽으면
Then `v` 를 파싱한 결과에 `name` 과 `flag` 키가 **모두 존재**하며, 배열로 인코딩되어 `["first"]` 만 남는 일이 일어나지 않는다.

**AC-READBACK-003** [부정 대조군] — 순환과 심층이 응답기를 멈추지 않는다 ↔ REQ-READBACK-003
Given `t.self = t` 인 자기참조 테이블이 심겨 있고
When 그 프로퍼티를 읽으면
Then 테스트는 정해진 타임아웃 안에 끝나고, 회신은 도착하며, `v` 는 파싱 가능하고, 재방문 지점은 값 대신 상한 표식을 담는다.
그리고 Given 상한보다 깊게 중첩된 테이블이 심겨 있으면 When 읽으면 Then `v` 는 파싱 가능하고 상한 깊이 이하로 잘려 있으며, 그 사실이 표식으로 남는다.

**AC-READBACK-004** [부정 대조군] — 절단된 테이블 값도 파싱된다 ↔ REQ-READBACK-005
Given 직렬화 결과가 값 길이 상한을 넘는 테이블이 심겨 있고
When 읽으면
Then 회신은 절단을 고지하고(`truncated` 계열 신호), **`v` 는 여전히 `json.loads` 를 통과한다**. 바이트 중간에서 잘린 JSON 조각은 실패로 간주한다.

**AC-READBACK-005** [부정 대조군] — 메타메소드가 호출되지 않는다 ↔ REQ-READBACK-002
Given `__index`·`__tostring` 이 호출 시 부작용 플래그를 세우는 메타테이블이 붙은 테이블이 심겨 있고
When 읽으면
Then 회신은 정상 도착하고 **부작용 플래그는 세워지지 않는다.**

**AC-READBACK-006** — 페이로드 예산이 유지된다 ↔ REQ-READBACK-006
Given 값 길이 상한이 상향된 상태에서
When `test_lua_responder_payload_budget.py` 를 실행하면
Then 인코딩된 페이로드 + `SendOSC` 래퍼가 2048 이하임이 통과하고, `max_payload` 는 `1900` 그대로다.

**AC-READBACK-007** — 잠금 규약이 이행된다 ↔ REQ-READBACK-007
Given 1.6.4 로 편집된 `copilot_responder.lua` 와 `PROTOCOL.md` 가 있고
When `test_overlap_preserve.py` 를 실행하면
Then 두 다이제스트가 새 값으로 재고정되어 통과하고, 날짜 붙은 승인 블록이 **같은 커밋**에 존재하며, `copilot_responder.lua:82` 의 `VERSION` 과 세 테스트의 버전 리터럴이 모두 `1.6.4` 다.

---

## C. R2 — 프리셋 값 되읽기

**AC-READBACK-008** [양성 대조군] — 스윕이 계기 생존을 보인다 ↔ REQ-READBACK-009
Given 프리셋 객체 1개에 대한 `introspect`+`props` 스윕이 실행되고
When 판독 가능하다고 이미 알려진 프로퍼티(예: 이름)를 같은 스윕에 포함하면
Then 그 프로퍼티는 값을 답한다. **이 양성 대조군이 없으면 다른 모든 `not readable` 은 결론의 근거가 되지 못한다.**

**AC-READBACK-009** [부정 대조군] — 스윕이 부재를 부재로 답한다 ↔ REQ-READBACK-009
Given 존재하지 않는 프로퍼티 이름을 같은 스윕에 포함하고
When 판독을 시도하면
Then 회신은 그 이름에 대해 판독 실패 사유를 답하며, 그 사유 문자열이 조사 노트에 그대로 기록된다. 조사 노트는 그 항목을 「0 건」이 아니라 「재지 못함」으로 분류한다.

**AC-READBACK-010** — 열거가 완전함을 산술로 증명한다 ↔ REQ-READBACK-009, REQ-READBACK-015
Given `introspect` 페이징으로 이름을 모으고
When 열거를 마치면
Then 조사 노트는 콘솔이 보고한 `childCount`, 실제 도착 개수, `truncated` 판독값을 **세 값 모두** 싣는다. 「전부 읽었다」는 이 세 값이 정합할 때만 쓴다.

**AC-READBACK-011** [발견 경로] — 값이 회신에 실린다 ↔ REQ-READBACK-010
Given 스윕이 판독 가능한 값 프로퍼티를 찾았고
When `GET /api/presets/{pool_no}` 를 호출하면
Then 회신은 이름 옆에 값을 싣고, 그 값의 출처가 **콘솔**임이 필드로 구별된다.

**AC-READBACK-012** [발견 경로] — 일치할 때만 `value_match` 가 빠지고, 그 커밋에 증거가 함께 있다 ↔ REQ-READBACK-011, REQ-READBACK-014
Given 라이브 되읽기 값이 앱이 변환해서 쓴 값과 일치하고
When 임포트 결과를 확인하면
Then 그 프리셋의 `unverified` 에 `"value_match"` 가 없다.
그리고 Given 값이 **불일치**하면 When 같은 확인을 하면 Then `"value_match"` 는 남아 있고 불일치가 보고된다.
그리고 Given `value_match` 고정 테스트 3건이 갱신됐으면 When 그 커밋을 확인하면 Then **같은 커밋**에 라이브 되읽기 증거(조사 노트 갱신 또는 라운드트립 출력)가 함께 들어 있고, 조사 노트가 그 제거보다 **앞선 커밋**에 이미 존재한다.

**AC-READBACK-013** [미발견 경로 · 유효한 PASS] — 부재가 측정된 사실로 닫히고, 그 판정이 grep 으로 이진화된다 ↔ REQ-READBACK-012, REQ-READBACK-014
Given 스윕이 판독 가능한 값 프로퍼티를 하나도 찾지 못했고
When R2 를 닫으면
Then `grep -c -E '^#{1,6}\s*(시도한 이름|사유|대조군|실행일)\b' <조사노트경로>` 가 **4** 를 답한다 — 네 표제가 모두 매치하며, 하나라도 빠지면 4 미만이 되어 실패다.
그리고 Then 각 표제 아래에 실제 내용이 있다: `시도한 이름` 아래에 시도한 이름 전부, `사유` 아래에 사유 문자열, `대조군` 아래에 양성·음성 두 대조군, `실행일` 아래에 ISO 일자.
그리고 Then `_VALUE_MATCH_REASON` 문면이 「이 채널에는 없다(측정 일자·근거 링크)」로 강화되어 있으며, `value_match` 고정 테스트 3건은 **초록으로 남아 있다.**

**AC-READBACK-014** [부정 대조군] — 팔레트가 콘솔 판독으로 위장하지 않는다 ↔ REQ-READBACK-013
Given 앱이 저장한 스와치 팔레트가 존재하고 콘솔은 색을 답하지 않는 상태에서
When 프리셋 회신을 확인하면
Then 콘솔 유래 값 필드는 비어 있거나 부재하며, 팔레트 색은 앱 유래로 구별되는 필드에만 실린다.

---

## D. 횡단 — 쓰기 예산과 증거

**AC-READBACK-015** — 콘솔 쓰기 총계가 1이고, 배포는 `ping` 으로만 확인된다 ↔ REQ-READBACK-008
Given 본 SPEC 의 전 작업이 끝났고
When 세션의 콘솔 명령 로그를 확인하면
Then 쓰기 명령은 응답기 재임포트 1건뿐이며, 그 시각이 머지 시각과 분리돼 있다.
그리고 Given 1.6.4 를 재임포트했으면 When `responder_roundtrip.py --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool` 을 실행하면 Then 버전 확인이 통과한다.
그리고 Given main 이 1.6.4 를 담고 있으나 라이브가 이전 버전이면 When 같은 명령을 실행하면 Then **실패**하며, 그 실패가 배포 미완의 증거로 채택된다.

**AC-READBACK-016** — 완료 보고가 5절 형식을 갖춘다 ↔ REQ-READBACK-015
Given 본 SPEC 의 완료 보고가 작성됐고
When 그 보고를 확인하면
Then 주장·증거(명령과 그 출력)·기준 귀속·**미검증**·잔여 위험 다섯 절이 모두 있고, 미검증 절에 최소한 B3(`SELECTIONDATA`/`DEPENDENCIES` 의 실제 테이블 형상)이 명시돼 있으며, **증거 절 어디에도 `exec: ok` 가 효과의 근거로 인용돼 있지 않다.**

---

## E. 완료 정의 (Definition of Done)

- [ ] §A 오프라인 명령 3줄 전부 초록, 출력 그대로 인용.
- [ ] AC-READBACK-001~007 통과 (부정 대조군 4종 포함).
- [ ] R2 가 발견 경로(011·012) **또는** 미발견 경로(013) 중 하나로 명시적으로 닫힘 — 「나중에」는 종점이 아니다.
- [ ] 미발견 경로로 닫았다면 §A 의 표제 grep 이 `4` 를 답한 출력이 보고서에 인용됨 (AC-READBACK-013).
- [ ] 콘솔 쓰기 1건, `ping` 이 `1.6.4` 응답 (AC-READBACK-015).
- [ ] `docs/runbooks/console-channel-facts.md` §4 갱신.
- [ ] 완료 보고 5절, 미검증 절 비어 있지 않음 (AC-READBACK-016).

---

## F. 커버리지 표 (REQ → AC)

> **개수와 하위 ID 표기**: 이 SPEC 은 REQ **15건**(REQ-READBACK-001~015 연속)과 AC **16건**(AC-READBACK-001~016 연속)을 갖는다. **이 SPEC 의 AC 에는 하위 ID(`003a`/`003b` 형태)가 없다** — 개수 차 1은 하위 ID 때문이 아니라 REQ-READBACK-004(배열/객체 판정 + 결정적 정렬)가 AC 두 건으로 갈려 검증되기 때문이다. 15개 REQ 전부가 최소 1개의 AC 를 갖고, 역방향(AC → REQ)은 각 AC 제목 끝의 `↔` 표기가 답한다.

| REQ | 요지 | 검증 AC |
|---|---|---|
| REQ-READBACK-001 | 테이블 값 → JSON 텍스트 회신 · `t`/`v` 형상 유지 · 형제 필드 신설 없음 | AC-READBACK-001 |
| REQ-READBACK-002 | 메타메소드 미호출 | AC-READBACK-005 |
| REQ-READBACK-003 | 깊이 상한 · 순환 탐지 | AC-READBACK-003 |
| REQ-READBACK-004 | 명시적 배열/객체 판정 · 결정적 키 정렬 | AC-READBACK-001 · 002 |
| REQ-READBACK-005 | 구조적 절단 (파싱 가능성 유지) | AC-READBACK-004 |
| REQ-READBACK-006 | 값 상한 상향은 2048 산술 안에서만 | AC-READBACK-006 |
| REQ-READBACK-007 | `console/lua/` 잠금 규약 이행 (다이제스트 2건 · 승인 블록 · 버전 리터럴) | AC-READBACK-007 |
| REQ-READBACK-008 | 콘솔 쓰기 정확히 1회 (재임포트) · 배포 근거는 `ping` 뿐 | AC-READBACK-015 |
| REQ-READBACK-009 | 구현 전 조사 스윕 + 양성/음성 대조군 + 「0 건」/「재지 못함」 구별 | AC-READBACK-008 · 009 · 010 |
| REQ-READBACK-010 | 발견 시 값과 출처를 회신에 실음 | AC-READBACK-011 |
| REQ-READBACK-011 | 일치할 때만 `value_match` 제거 | AC-READBACK-012 |
| REQ-READBACK-012 | 미발견 시 네 표제(`시도한 이름`·`사유`·`대조군`·`실행일`)로 닫음 | AC-READBACK-013 |
| REQ-READBACK-013 | 팔레트를 콘솔 판독값으로 제시 금지 | AC-READBACK-014 |
| REQ-READBACK-014 | 고정 3건은 증거와 같은 커밋 · 노트가 제거보다 먼저 | AC-READBACK-012 · 013 |
| REQ-READBACK-015 | 완료 보고 5절 형식 · `exec: ok` 를 효과의 증거로 인용 금지 | AC-READBACK-010 · 016 |
