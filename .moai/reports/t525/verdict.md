# t525 판정서 — 앱만으로 무대 2D 그리기 확인 (읽기 전용 프로브)

카드 t525 · 2026-10-10 · 브랜치 `WT-stage-from-patch` (base `159f0cb1`)
실기: grandMA3 onPC 2.4.2 (pid 58462) · 응답기 `CopilotResponder` 1.6.5 · 127.0.0.1:8000 → 9005
**콘솔 쓰기 0 · 쇼 저장 0 · 코드 0.** 보낸 동사는 `ping` · `state` · `prop` · `props` · `introspect`뿐이다(프로브 네 개의 소스가 증거 — `exec`/`deploy` 를 부르는 줄이 없다).

산출물: `reports/ldbeat-stage-from-patch-20261010.html` (위에서 본 그림 X·Y + 객석에서 본 그림 X·Z + 리드 시안 무대 칸 캡처 나란히)

## 결론 — 조건부 가능

| 질문 | 판정 | 조건 |
|---|---|---|
| ① 장비 위치를 앱 경로만으로 다 읽나 | **가능 (지금)** | 응답기가 `props`(일괄 읽기, 1.6.1+)를 지원할 때. 86/86, 왕복 154, 10.3초 |
| ① 일괄 읽기 없는 응답기라면 | 불가(부분) | 속성 하나씩 읽는 경로는 60/86 에서 예산 컷 |
| ② 그룹 소속을 앱이 아나 | **콘솔에는 있다 — 지금은 앞 2대만** | 그룹 오브젝트 `SELECTIONDATA` 에 멤버 목록이 있고 읽힌다. 응답기가 값 하나를 240바이트에서 잘라 그룹당 2대만 온다. 전부 읽으려면 응답기 확장(코드 카드) 필요 |
| ③ 위에서/객석에서 그림 | **그렸다** | 좌표 86대 전부 · 그룹 색은 확인된 8대만, 나머지 회색 |

한 줄로: **위치는 지금 앱만으로 된다. 그룹 소속은 응답기에 "긴 값 나눠 읽기" 하나를 붙이면 된다.** 리드가 손으로 알고 그리던 것을 앱이 대신할 수 있다.

## ① 좌표 읽기 — 앱 경로 그대로

명령: `.venv/bin/python .moai/reports/t525/probe_spatial.py bulk` → `r1_spatial_bulk.json`
앱의 `get_spatial_context` 와 같은 함수(`read_spatial_fixtures`)·같은 예산 계산(`_spatial_read_budget`)·`include_rotation=True`.

| 항목 | 값 (r1) |
|---|---|
| 픽스처 총수 (`node.childCount`) | 86 |
| 한 번에 읽힌 수 | 86 — 응답 모양 `fixtures` (partial 아님), `coverage {judged 86, of 86, complete true}` |
| `truncated` / `roundtrip_capped` / `missing` | false / false / 없음 |
| 읽지 못한 장비 (`unreadable`) | 0 |
| 예산 · 왕복 | budget 240 · `state` 68 + `props` 86 = 154 |
| 시간 | 10.27초 |
| 회전 읽힘 | **86/86** (rotx·roty·rotz 전부). 코드 주석 `tools.py:1385` 「NOT yet live-measured」 를 이 측정이 메운다 |

대조 — 속성 하나씩 읽는 경로(`probe_spatial.py pername` → `r2_spatial_pername.json`): budget 420, `prop` 420 + `state` 68 = 488 왕복, 32.53초, 모양 `partial_fixtures`, `coverage {judged 60, of 86}`, `missing {expected 86, received 60, unseen_count 26}`. 카드 본문의 「240 ≈ 60대」 는 **이 경로에서만** 맞다. 1.6.1+ 응답기에서는 일괄 경로라 86대가 한 번에 된다.

`state` 68번의 내역: 응답기 자식 목록 상한 24 라 첫 창 뒤 빠진 슬롯을 하나씩 물어 복원한다(`tools.py` truncated 복원 루프). 86대 리그에서 이 복원이 완결됐다.

### 읽은 배치 (r1 요약, 이름 앞부분별)

| 줄 | 대수 | fid | X (m) | Y (m) | Z (m) | 회전 |
|---|---|---|---|---|---|---|
| KEY | 6 | 101–106 | −5 ~ 5 | −9.0 | 7.5 | 0/0/0 |
| FOH | 8 | 111–118 | −6 ~ 6 | −6.5 | 7.0 | 0/0/0 |
| BLIND | 6 | 601–606 | −4.5 ~ 4.5 | −3.2 | 6.5 | 0/0/0 |
| MOVER-D | 8 | 521–528 | −5.5 ~ 5.5 | −2.5 | 6.8 | 0/0/0 |
| WASH-D | 10 | 421–430 | −5 ~ 5 | −1.0 | 0.0 | 180/0/0 |
| HAZE | 2 | 621–622 | −7.5, 7.5 | 0.5 | 0.2 | 0/0/0 |
| SIDE-L | 6 | 301–306 | −7.0 | 0.5 ~ 3.0 | 1.2 ~ 4.0 | 0/0/0 |
| SIDE-R | 6 | 311–316 | 7.0 | 0.5 ~ 3.0 | 1.2 ~ 4.0 | 0/0/0 |
| STROBE | 4 | 611–614 | −5.5 ~ −2.5 | 2.5 | 6.8 | 0/0/0 |
| MOVER-U | 8 | 501–508 | −1.5 ~ 5.5 | 2.5 | 6.8 | 0/0/0 |
| BACK | 12 | 201–212 | −6 ~ 6 | 4.5 | 6.2 | 0/0/0 |
| WASH-U | 10 | 401–410 | −5 ~ 5 | 5.2 | 0.0 | 180/0/0 |

Y 의 방향(− 가 객석)은 **이름으로 추정**했다 — FOH·KEY 가 Y −, BACK(역광) 이 Y + 에 있다. 콘솔에서 무대 앞뒤를 따로 읽지는 않았다.

### 리드 시안(손그림)과 다른 점

| 시안 | 실제 패치 |
|---|---|
| KEY · STROBE · HAZE 가 없다 | KEY 6 (객석 맨 뒤 Y −9) · STROBE 4 · HAZE 2 가 있다 |
| BLIND 가 BACK 바로 아래, 무대 안쪽 | BLIND 는 **객석 쪽** Y −3.2 — MOVER-D 보다 앞 |
| WASH 두 줄이 무대 앞뒤 끝 | WASH-U 는 BACK **뒤** 바닥(Y 5.2), WASH-D 는 무대 가운데 바닥(Y −1.0). 둘 다 Z 0, 회전 180(위로 향함) |
| MOVER-U 8대가 좌우 대칭 | MOVER-U 는 X −1.5 ~ 5.5 로 오른쪽에 치우침 — 같은 트러스 왼쪽(X −5.5 ~ −2.5)에 STROBE 4 |
| SIDE 가 무대 깊이 전체 | SIDE 는 무대 안쪽 절반(Y 0.5 ~ 3.0)에 세로로 쌓인 붐(Z 1.2 ~ 4.0) |

## ② 그룹 소속 — 콘솔에 있다

### 근거 1 — 그룹 오브젝트 필드 101개 전량

명령: `.venv/bin/python .moai/reports/t525/probe_groups.py 13 4 5 14` → `r3_group_fields.json`
`introspect` 를 offset 으로 넘겨(0 → 27 → 55 → 81) 그룹 4개(MOVER-ALL·BACK·SIDE-L·BLIND) 모두 **101/101** 받았다. t520(`groups_readonly.txt:38`)은 첫 창 27/101 만 받고 끝났었다.

맨 끝 필드가 `SELECTIONDATA` (`Custom`) 다. 값을 읽으면:

```
Groups/13 MOVER-ALL  SELECTIONDATA  ok:true t:"table" truncated:true
[{"grid":{"inv":0,"x":0,...},"sf_index":30},{"grid":{"inv":0,"x":1,...},"sf_index":31}]
```

| 그룹 | sf_index (잘린 값) |
|---|---|
| 13 MOVER-ALL | 30, 31 |
| 4 BACK | 70, 72 |
| 5 SIDE-L | 94, 96 |
| 14 BLIND | 14, 15 |

네 그룹 모두 값 길이 163바이트, `truncated: true`. 원인은 응답기 `console/lua/copilot_responder.lua:43` `max_prop_value = 240` — 표 값은 뒤 항목을 통째로 버려 다시 닫는다(`json_encode_bounded`, `:283`). 항목 하나가 약 80바이트라 2개만 남는다.

`COUNT` 는 네 그룹 모두 0 이고 `state` childCount 도 0 — 둘 다 소속을 세지 않는다(이전 판정과 같음).

### 근거 2 — sf_index → fid 대응

명령: `.venv/bin/python .moai/reports/t525/probe_patch_tree.py` → `r4_patch_tree.json`
픽스처마다 `SUBFIXTUREINDEX` 가 읽힌다(86대, 0 ~ 137). 서브픽스처를 가진 장비는 자식도 번호를 하나씩 차지해 칸이 벌어진다 — 예: BACK 201 은 70, 그 자식 `[Instance2#2]` 가 71, BACK 202 가 72. MOVER-D 521 은 자식 3개.

| 그룹 | sf_index | → fid |
|---|---|---|
| MOVER-ALL | 30, 31 | 501, 502 (MOVER-U) |
| BACK | 70, 72 | 201, 202 |
| SIDE-L | 94, 96 | 301, 302 |
| BLIND | 14, 15 | 601, 602 |

8칸 모두 그룹 이름과 맞는 장비로 떨어진다 — 대응 규칙이 맞다는 증거다. 그룹이 서브픽스처가 아니라 본체 번호(70, 72)를 담는다는 것도 함께 확인됐다.

### 대안 비교

| 경로 | 근거 | 평가 |
|---|---|---|
| **콘솔 `SELECTIONDATA`** | 위 측정 | 콘솔이 정본. 응답기에 긴 표 값 나눠 읽기(예: `props` 값에 offset)만 더하면 된다 — 응답기 변경이라 별도 카드 |
| LX-SEQ 그룹 시트 (`import_lxseq_groups`) | `tools.py:5710` · `group_parser.py` 머리말 | 멤버는 패치 시트 Group 라벨에서 온다. 파일 기반이라 콘솔에서 손으로 고친 그룹은 못 따라간다 |
| 앱이 만든 그룹 기록 | GROUPGEN | 앱이 만든 그룹만 안다. 이 쇼의 18개 그룹은 앱이 만든 게 아니다 |
| 이름 앞부분으로 추정 | `design/rig.py` `resolve_layer_role` | 역할은 맞히지만 소속이 아니다(MOVER-ALL 은 U·D 를 다 담을 수 있다) — 그림에서는 「패치 이름(참고)」 보기로만 둔다 |

## ③ 그림

`.venv/bin/python .moai/reports/t525/render_stage.py reports/ldbeat-stage-from-patch-20261010.html` (측정 JSON 세 개 + 시안 캡처에서 다시 만든다)

- 위에서 본 그림(X·Y, 1칸 = 1 m, 아래가 객석) 옆에 리드 시안 무대 칸 캡처(`lead_stage_crop.png`, 시안 HTML 을 headless Chrome 으로 찍어 잘라냄)
- 객석에서 본 그림(X·Z)
- 색: 기본은 **그룹 소속(확인된 것만)** — 8대만 색 + 노란 테두리, 나머지 회색. 단추로 **패치 이름(참고)** 색으로 바꿀 수 있다
- 점에 마우스를 올리면 이름·fid·좌표·회전·소속 확인 여부

화면 확인: headless Chrome 캡처로 범례 전환과 겹침(같은 자리 SIDE 붐에서 소속 장비가 덮이던 것)을 고친 뒤 다시 찍어 봤다.

## 미검증 (안 잰 것)

- 그룹 18개 중 **4개만** 읽었다(13·4·5·14). 나머지 14개는 안 쟀다.
- `SELECTIONDATA` 는 그룹당 **앞 2칸만** 봤다. 3번째 이후가 같은 꼴인지·전체 개수는 모른다. 8/8 일치는 대응 규칙의 증거일 뿐 나머지 멤버의 증거가 아니다.
- `grid` 의 `x/y/z` 뜻(그룹 격자 위치로 보이지만) 은 안 쟀다.
- 무대 크기·경계, Y 방향의 정본은 콘솔에서 읽지 않았다(이름으로 추정).
- 서브픽스처(예: MOVER-D 자식 3개)는 본체 좌표 하나로만 그렸다.
- 프로브는 앱의 게이트(감사 로그)를 거치지 않고 `ConsoleLink` 를 직접 썼다. 쓰기 0 의 근거는 프로브 소스(읽기 동사만)다.

## 잔여 위험

- `props` 일괄 읽기가 안 되는 응답기(1.6.1 미만)로 바뀌면 ①은 60대에서 다시 잘린다.
- 응답기 값 한도를 크게 올려도 응답 전체 한도 `max_payload = 1900` 에 걸린다 — ALL 그룹(86대)은 한 번에 못 담는다. 확장은 「값 한도 올리기」가 아니라 **나눠 읽기**여야 한다.

## 다음 카드 제안 (만들지 않음 — 리드 판단)

1. 응답기: 표 값 속성의 나눠 읽기(예: `props <path> SELECTIONDATA offset=<n>`) + 앱에 `sf_index → fid` 대응. 이것이 ②를 닫는다.
2. 런북 무대 칸(t522 SPEC)이 손그림 대신 이 좌표 그림을 쓰도록 — 위 「다른 점」 표가 손그림의 위험을 보여 준다.

## 증거 파일

| 파일 | 무엇 |
|---|---|
| `probe_spatial.py` · `r1_spatial_bulk.json` · `r2_spatial_pername.json` | ① 좌표 (일괄 / 하나씩) |
| `probe_groups.py` · `r3_group_fields.json` | ② 그룹 필드 101개 + 값 |
| `probe_patch_tree.py` · `r4_patch_tree.json` | ② sf_index ↔ fid |
| `render_stage.py` · `lead_stage_crop.png` | ③ 그림 생성 + 시안 캡처 |
| `r*_*.stderr.txt` | 네 실행 모두 0바이트(오류 없음). 2026-10-08 첫 시도(onPC 꺼짐)의 ConsoleSilentError 는 이번 재실행이 덮어 남아 있지 않다 |
