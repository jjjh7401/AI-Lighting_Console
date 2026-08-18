# 12. 응답기 1.6.1(props·introspect) 재배포·라이브 재검증 프로브 — SPEC-COPILOT-INTROSPECT-001 T15

`SPEC-COPILOT-INTROSPECT-001`(PR #23)을 main의 1.6.0 페이징 세대 위에 재이식(T14,
`jjjh7401/introspect-reland`, 커밋 `5b4a307`)한 응답기 1.6.1을 **실기 콘솔**에 배포하고,
props·introspect 신동사·기존 동사 하위호환·1.6.0 페이징 공존·M7 발견(재생 상태 필드)을
전부 실측했다. PR #23 문면의 "라이브 검증 완료" 주장은 **구버전(1.5.0/paging-이전) 응답기
기준**이었으므로 여기 기록이 1.6.1 기준 최초의 진짜 검증이다. `verification-claim-integrity`
원칙에 따라 관측된 그대로만 적고, 추정은 GAP으로 명시한다.

- 실기: onPC 2.4.2, `console_port=8000`/`receive_port=9005`(`settings.toml`의 site config,
  `osc_slot=2`)
- 배포 전 라이브 버전: **1.6.0**(파일은 1.6.1로 이미 최신이었으나 콘솔 메모리는 구버전)
- 배포 후 라이브 버전: **1.6.1** (§2)

## 0. 포트 전쟁 (기록)

세션 시작 시 우리 앱(`server.web`)이 이미 8765/9005를 쥐고 있었다(`WON pid=98865`류).
`/tmp/probe_window.sh <command>`로 매 프로브 직전 자동 kill→실행→`/tmp/port_war.sh` 재선점
패턴을 그대로 썼다. 배포 중간 단계(아래 §1.3)에서 `port_war.sh`가 "LOST after 15 attempts"를
반복 출력한 순간이 있었는데, 이는 **거짓 경보**였다 — `lsof`로 직접 확인하면 우리 프로세스가
실제로는 포트를 정상 보유하고 있었다(백그라운드 job 리핑 지연으로 이전 라운드의 `Killed: 9`
메시지가 뒤늦게 출력된 것으로 추정, GAP — 확정 안 함). 이후 모든 프로브는 `lsof`로 실제
홀더를 직접 재확인하는 방식으로 진행해 문제없이 완료했다.

## 1. [최우선] 배포 함정 — 응답기가 자기 자신을 못 지운다

### 1.1 증상

`server/safety/console.py::_run_file_import`의 표준 재배포 경로(같은 이름의 기존 플러그인을
`Delete`한 뒤 새 슬롯에 `Import`)가 **전부 실패**했다:

```
Delete Plugin 1                      → (상태 미확인, 코드가 결과를 버림)
Import Plugin 1 'CopilotResponder'   → {"ok": false, "error": "User Canceled Command"}
Import Plugin 18 'CopilotResponder'  → {"ok": false, "error": "User Canceled Command"}  (완전히 빈 슬롯인데도 동일)
```

`ReloadAllPlugins`(exec)는 `ok:true`로 응답했지만 디스크 재읽기를 하지 않아 라이브 버전은
그대로 1.6.0에 머물렀다(재확인 필요 사실로만 기록 — 이 명령이 실제로 무엇을 리로드하는지는
GAP).

### 1.2 근본 원인 — 자기참조 자기삭제

`ConsoleLink.execute()`는 모든 exec 명령을 `Plugin "CopilotResponder" "exec <id> <cmd>"`로
감싼다 — 즉 **`Delete Plugin 1`을 실행하는 코드 자체가 슬롯1(CopilotResponder) 안에서
돌고 있다**. 자기 자신이 실행 중인 오브젝트를 자기 명령으로 삭제하려 하면 MA3가 확인
대화상자를 띄우고, OSC/exec 경로에는 그 대화상자에 답할 채널이 없어 `User Canceled
Command`로 거부된다. 빈 슬롯(18)에 **같은 이름**으로 새로 Import하는 것도 거부됐다 —
자기삭제가 아니라 **"동일 이름 오브젝트가 풀 어딘가에 이미 존재하면 Import 자체가 확인을
요구한다"**는 더 넓은 규칙으로 보인다(코디네이터 실측 사례와 일치: "Delete Sequence 401"도
동일 패턴으로 거부됨).

### 1.3 해법 — `/nc`(no-confirm) 플래그 + 비자기참조 위임

코디네이터가 오늘 세션에서 이미 실측 확인한 우회를 그대로 적용했다:

```
Import Plugin 18 '<stem>' /nc              → ok:true  (빈 슬롯에 중복 이름 강제 Import 성공)
```

MA3가 중복 이름을 **자동으로 `#2` 접미사**를 붙여 등록했다 — `CopilotResponder#2`(슬롯18).
`Plugin "CopilotResponder#2" "ping ..."`로 직접 호출하면 **1.6.1이 응답**한다(정상 로드
확인). 이제 슬롯18은 슬롯1과 **다른 오브젝트**이므로, 슬롯18을 실행 주체로 삼아 슬롯1을
지우는 것은 자기삭제가 아니다:

```
(via slot18) exec: Delete Plugin 1         → ok:true   (비자기참조 삭제 — 성공)
(via slot18) exec: Import Plugin 1 'CopilotResponder' → ok:true  (빈 슬롯1에 정식 이름으로 재등록)
(via slot1, 이제 1.6.1) ping                → version=1.6.1 확인
(via slot1) exec: Delete Plugin 18          → ok:true   (남은 #2 중복본 정리 — 이번엔 슬롯1이
                                                          실행 주체이고 대상은 슬롯18이라 역시
                                                          비자기참조)
```

최종 풀 상태: `DataPool/Plugins` 17개 오브젝트, 중복 없음, 슬롯1 = `CopilotResponder`
(1.6.1) 단일본. `Rename Plugin <n> '<name>'`은 시도했으나 `{"error": "Not implemented"}`로
거부됨 — MA3 2.4.2의 Plugin 클래스는 Cmd 경로로 이름 변경을 지원하지 않는다(참고용 GAP).

### 1.4 코드 관점 교훈 — 구조적 함정, 이번 SPEC이 만든 게 아니다

`_run_file_import`가 자기이름 슬롯을 찾아 `Delete`부터 시도하는 설계는 **1.5.0→1.6.0
전환 때도 동일하게 존재**했을 구조다(코드 자체가 이번 재이식으로 바뀐 부분이 아님 — T14는
이 함수에 순수 추가만 했고 삭제/수정 없음). 과거 배포 기록(메모리 `project_copilot_...`
계열)이 "라이브 배포 성공"을 보고한 사례들은 (a) 최초 배포라 슬롯이 비어 있었거나(자기삭제
불필요), (b) 사용자가 GUI로 1회 수동 Delete를 했거나(M7 발견 문서 §M7.6의 "신규 플러그인은
최초 1회 사용자 GUI 저장이 필수 전제"와 정합), (c) 이번처럼 우연히 자기삭제를 안 겪은
케이스였을 가능성이 높다 — 이번 프로브가 처음으로 재현·근본원인·우회를 모두 실측한
사례다. **후속 SPEC 권고**: `deploy_plugin`이 기존 슬롯과 이름이 같을 때 자기삭제 대신
"임시 별칭으로 Import → 비자기참조로 구버전 삭제 → 원래 이름으로 재Import → 임시본 삭제"
4단계를 표준 경로로 삼는 방향을 검토할 것(현재는 사람이 매번 손으로 우회해야 함). 이번
프로브는 코드 수정 없이 우회만 했다(지시 준수).

---

## 2. 왕복 검증 — 1.6.1 확인 + 기존 동사 하위호환

```
responder_roundtrip --expect-version 1.6.1 --exec-command List
  [PASS] ping: ok            live version=1.6.1 plugin=CopilotResponder
  [PASS] state: ok           node={'childCount': 37, 'class': 'Sequences', ...} children=18
  [PASS] exec: ok
  result: PASS

responder_roundtrip --prop-path "DataPool/Sequences/Sequence 101" --prop-name CURRENTCUE
  [PASS] prop: ok   value='Sequence 101.1'   (신버전에서도 prop 동사 정상)
```

`state`/`prop`/`exec` 전부 1.6.0 때와 동일한 형태로 응답 — 하위호환 확인.

## 3. 신동사 실측 — props / introspect

### 3.1 props — 일괄 판독

```
introspect_probe --path "DataPool/Sequences/Sequence 101" --names CURRENTCUE,FADER,INDEX,NAME
{
  "reads": [
    {"n": "CURRENTCUE", "ok": true,  "t": "userdata", "v": "Sequence 101.1"},
    {"n": "FADER",      "ok": false, "e": "property not readable: FADER"},
    {"n": "INDEX",      "ok": true,  "t": "number", "v": "101"},
    {"n": "NAME",       "ok": true,  "t": "string", "v": "Sequence 101"}
  ],
  "truncated": false
}
```

`CURRENTCUE`의 `props` 값(`Sequence 101.1`)이 §2의 `prop` 단일 판독 값과 **정확히 일치** —
두 동사가 같은 판독 경로를 공유함을 실측으로 확인. `FADER`는 Sequence 핸들에 없는 속성이라
항목 단위 실패(`ok:false`)로 처리됐고 전체 요청은 여전히 `ok:true`(설계대로 — 부분 실패가
전체를 막지 않음).

### 3.2 introspect — 자기진단 + AC-004 정합성 게이트

```
introspect_probe --path "DataPool/Sequences/Sequence 101"
{
  "ok": true, "class": "Sequence", "source": "property_accessors",
  "fields": [27개 나열: IGNORENETWORK ... USER],
  "total": 65, "truncated": true
}
```

`ok:true`로 응답 — **AC-004(대조군 정합성 게이트: property_accessors가 독립 판독 가능한
`INDEX`/`FADER`/`NAME`/`NO`/`CURRENTCUE`를 전부 포함해야 통과) 실기 통과**. 전체 65개 필드
중 27개만 반환되고 `truncated:true` — `CONFIG.max_payload`(1900바이트) 예산 초과로 잘림,
`total`은 잘리기 전 값이 보존됨(설계대로).

## 4. 페이징 공존 — 24캡 너머 + payload 바이트캡 상호작용 실측

`DataPool/PresetPools/Color`(37개, 한글 라벨 다수 포함)를 전량 페이징으로 회수:

```
offset=0  got=16  truncated=True
offset=16 got=19  truncated=True
offset=35 got=2   truncated=False
합계 37개, 중복 0, 누락 0 — 순서대로 재구성 성공
```

**중요 실측 정정**: 처음에 `offset=24`(설계상 `max_children` 캡)로 다음 페이지를 요청했더니
`Blue#2`부터 시작해 `Warm White#2 ~ Cyan#2`(8개)가 **누락**됐다 — 이는 **내 프로브 스크립트의
오프셋 계산 실수**였다(1.6.0/1.6.1 응답기 자체의 결함 아님). 올바른 프로토콜은 "이번 창이
실제로 반환한 개수만큼 offset을 전진"하는 것이지, `max_children` 상수(24)를 고정 전진폭으로
쓰면 안 된다 — 첫 창이 payload 바이트캡에 먼저 걸려 16개로 잘렸기 때문에(한글 라벨이 많아
`max_children=24`보다 먼저 1900바이트를 채움), 다음 offset은 16이어야 했다. 이 정정으로
**문서 11번(§6 GAP #4) "Color 풀 첫 페이지가 16개에서 절단된 이유"가 해소**된다 — 정답은
"바이트 크기 캡이 먼저 걸린다"였고, 이번 프로브가 그 추정을 실측으로 확정했다. 페이징
자체(1.6.0 기능)는 1.6.1(props/introspect 추가)에서도 **회귀 없이 정상 동작**함을 확인.

## 5. M7 발견 재현 — Sequence 핸들의 재생 상태 필드

```
introspect_probe --path "DataPool/Sequences/Sequence 101" \
  --names CURRENTCUE,CUENO,CUENAME,TRIGGER,LOADEDCUE
{
  "reads": [
    {"n": "CURRENTCUE", "ok": true, "t": "userdata", "v": "Sequence 101.1"},
    {"n": "CUENO",      "ok": true, "t": "string",   "v": "1"},
    {"n": "CUENAME",    "ok": true, "t": "string",   "v": ""},
    {"n": "TRIGGER",    "ok": true, "t": "string",   "v": ""},
    {"n": "LOADEDCUE",  "ok": false, "e": "property not readable: LOADEDCUE"}
  ]
}
```

**재현 성공.** M7 원 발견("재생 상태에 해당하는 필드는 Executor가 아니라 Sequence
핸들에 있다")이 재이식된 1.6.1에서도 그대로 유지된다 — `CURRENTCUE`/`CUENO`/`TRIGGER`는
읽히고, `LOADEDCUE`는 원 문서 권고대로 판독 불가로 재확인됐다(`props`의 항목 단위 실패로
깔끔하게 표현됨 — 전체 요청은 안 죽음). `CUENAME`/`TRIGGER`가 빈 문자열인 것은 이 특정
큐(101.1)에 이름·트리거 문구가 비어 있어서로 보인다(콘솔 데이터 상태, 코드 결함 아님).
**페이저 recall ASSUMPTION 해소 관점**: 이 실측 자체는 문서 11번 §1의 "recall이 페이저를
통째로 싣는가"(Programmer/Selection 판독 불가)와는 다른 질문(이미 저장된 시퀀스의 현재
재생 위치)이라 그 GAP을 직접 닫지는 못한다 — 다만 "재생 중 어느 큐에 있는지"는 이제
`props`로 안정적으로 얻을 수 있으므로, 후속 SPEC(큐 모니터/실행 상태 UI, M7 §M7.7 권고
2번)의 데이터 소스로 그대로 쓸 수 있음을 확인했다.

---

## 6. GAP — 이번 프로브가 채우지 못한 것

1. **`ReloadAllPlugins`이 실제로 무엇을 하는지** — `ok:true`였지만 디스크 재읽기는
   일으키지 않았다. MA3 문서/코드 확인 없이는 정확한 동작 범위 unknown.
2. **`Rename Plugin`이 `Not implemented`인 이유** — Cmd 문법이 다른지, 이 클래스가
   아예 미지원인지 미확인.
3. **§0의 "LOST after 15 attempts" 거짓 경보 원인** — job 리핑 지연 추정, 확정 안 함.
4. **`CUENAME`/`TRIGGER`가 다른 큐에서도 항상 채워지는지** — 이번엔 큐 101.1 하나만
   봤다. 여러 큐 순회 검증은 범위 밖(§5는 M7 재현이 목적이지 전수 조사가 아님).

## 7. 정리(cleanup) 검증

배포 자체가 "지우고 새로 심기"라 원복 대상이 없다 — 최종 상태가 곧 목표 상태(1.6.1 단일
플러그인)다. 풀 정리 확인:

```
DataPool/Plugins  17개 오브젝트, 중복 없음(#2 접미사 잔존 없음), 슬롯1=CopilotResponder(1.6.1)
```

`Color`/`Sequences` 등 조회 전용 프로브는 아무것도 변경하지 않았다(Store/Delete 없음).
프로브용 임시 스크립트(`/tmp/*.py`)는 세션 범위 밖 임시 파일이라 리포지토리에 없다.
