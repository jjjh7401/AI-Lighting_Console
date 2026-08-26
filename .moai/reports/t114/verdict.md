# t114 실기 — 옛 것과 새 것을 한 화면에 나란히 세웠다. 판정은 감독 눈이다

판정: 저장 발화 완료 · **값 일치는 미검증**(이 채널로 불가) · 감독 육안 대기

측정 트리: .claude/worktrees/t114
브랜치: WT-dim-value-match
base: origin/main e71802d
콘솔: grandMA3 onPC 2.4.2 · app_gma3 pid **83784** (재시작 후 새 pid, 착수 시점에 다시 쟀다)
응답기: 1.6.2 (재시작을 넘어 살아남음 — 콘솔 회신으로 확인)

## 1. 주장 (Claim)

1. t108 이 심은 **apply → Store → Label → ClearAll** 네 명령이 실기에서 전부
   `executed_ok` 를 받았다. 값 적용 단계(`Attribute 'Dimmer' At 85`)가 **실제로 나갔다**.
2. 슬롯 7 에 프리셋이 생겼다. 풀은 6 → 7.
3. **값이 맞는지는 말할 수 없다.** 그리고 이번엔 그 한계를 실측으로 못박았다 —
   옛 경로 산물(슬롯 2)과 새 경로 산물(슬롯 7)이 **판독으로 구별되지 않는다**.
4. 범위 밖은 안 건드렸다.

## 2. 증거 (Evidence)

### 2-1. 재시작 후 채널을 새로 세웠다

콘솔이 재시작돼 이전 측정이 전부 낡았다. 순서대로 다시 쟀다.

    프로세스        app_gma3 83784 · UDP 9005 점유 (직접 확인, 리드 보고를 그대로 안 썼다)
    날조 대조군     path segment not found: 'FixtureTypesZZZNotAThing'  (이유를 댄 거절)
    응답기 버전     1.6.2  PASS   <- 재시작이 되돌리지 않았다
    딤 풀           childCount 6 · 회신 6 · truncated False · 슬롯 1~6 이름 그대로

⚠️ 재시작이 **무엇을 되돌렸는지**는 안 쟀다. 위 넷이 유지됐다는 것만 관측했다.

### 2-2. 개명 — 첫 콘솔 쓰기, 비파괴

가드가 막는 것은 **이름 충돌**이다(REQ-LXSEQ3-007, `preset_mapper.py:305`).
지우지 않고 이름만 바꿔 조건을 바꿨다. **가드를 우회한 것이 아니다** — 가드는
그대로 돌고 그 판정이 바뀐 것뿐이다.

    발사 전 대상 판독   슬롯 2  NAME=쇼 하이 · NO=2 · PRESETMODE=Universal
    발사               Label Preset 1.2 '쇼 하이 OLD'   (33 바이트)  executed_ok "OK"
    되읽기             슬롯 2 이름이 '쇼 하이 OLD' 로 바뀜. 나머지 다섯과 childCount 6 불변

명령 성공이 아니라 **판독으로** 확인했다.

### 2-3. 모의가 실측과 일치했다

개명 전에 합성 풀로 돌린 모의가 `slot 7 · '쇼 하이' · 85%` 를 냈다. 실측 preview 가
같은 값을 냈다.

    개명 전 preview   read 6 · planned 0 · already_present 6 · held 0 · refusal None
    개명 후 preview   read 6 · planned **1** · already_present 5 · held 0 · refusal None
                      PLANNED -> DIM.SHOW · '쇼 하이' · slot **7** · 85%

모의 때 대조군(새 이름까지 이미 있는 상태 → planned 0)을 같이 쐈다. 없었으면
「무조건 1건 계획」과 구분되지 않았다.

### 2-4. 발사 — t108 경로 네 명령 전부

    발사 전 슬롯 7   path segment not found: '7'   (비어 있음을 이유 있는 거절로 확인)

    approval: granted
    번들: Group 1 ; Attribute 'Dimmer' At 85    executed_ok "OK"   <- 값 적용 단계
          Store Preset 1.7                      executed_ok "OK"
          Label Preset 1.7 '쇼 하이'             executed_ok "OK"
          ClearAll                              executed_ok "OK"
    all_ok: true

    command_bytes [34, 16, 29, 8] · 최장 34   (t72 기록용이지 판정 근거 아님)
    시트 출처 sha256 5afe3faf… · 298 바이트   (정본 시트, 파생 CSV 없음)

이번엔 **승인 통로가 실제로 물었다** — `approval_requests` 에 번들이 찍혔다.
t104 의 `Import Plugin` 은 안 물었던 것과 갈린다.

### 2-5. 되읽기 — 슬롯은 찼다. 범위 밖은 그대로다

    딤 풀            childCount 6 -> **7** · truncated False
                     slot 1 풀 · 2 쇼 하이 OLD · 3 미드 · 4 로우 · 5 잔광 · 6 아웃 · **7 쇼 하이**
    슬롯 7 독립 재조회 (별도 프로세스)   class Preset · name '쇼 하이' · truncated False
    범위 밖  fixtures childCount 86 (truncated True) · groups 18 (truncated False)   불변

## 3. 기준선 귀속 (Baseline-attribution)

    read              6      (정본 dim 시트 6행)
    planned           1      DIM.SHOW -> 슬롯 7
    already_present   5      전부 classes: name_taken (풀·미드·로우·잔광·아웃)
    held              0
    rejected_rows     []
    refusal           None
    unverified        ['value_match']   <- 툴이 스스로 신고한다

**「1건 성공」이 아니다.** 「6행 읽음 · 1건 계획 · 5건 이름중복 보류 · 저장 발화 1건 ·
값 일치 미검증」이다.

## 4. 미검증 (Gaps)

- 🔴 **값이 맞는지 안 쟀다. 잴 수 없다.** t104 가 확정한 한계다.
- **옛 것과 새 것이 판독으로 구별되지 않는다** — 아래 §5 가 이 카드의 핵심 발견이다.
- 재시작이 무엇을 되돌렸는지 안 쟀다.
- 나머지 5행(풀·미드·로우·잔광·아웃)은 **안 쐈다.** 이름 충돌 그대로다.
- `ClearAll` 이 실제로 프로그래머를 비웠는지 안 쟀다 — `executed_ok` 만 봤다.

## 5. 🔴 이 카드의 발견 — 판독 채널은 두 경로를 구별하지 못한다

같은 네 프로퍼티를 두 슬롯에 물었다.

    슬롯   이름          PRESETMODE   PRESETDATA   COUNT   어느 경로 산물
      2    쇼 하이 OLD   Universal    (빈 문자열)    0      **옛 M4 (2026-08-25, t108 이전)**
      7    쇼 하이       Universal    (빈 문자열)    0      **새 t108 (오늘, apply 단계 포함)**

**네 값이 전부 같다.** 슬롯 7 은 값 적용 명령(`At 85`)이 확실히 나간 뒤 저장된
것이고 슬롯 2 는 그 단계가 없던 경로의 산물인데, **판독은 둘을 구별하지 못한다.**

그러므로 이 채널의 빈값·0 은 **프리셋의 상태가 아니라 채널의 한계**다. t95 가
같은 형태를 이미 잡았고(내용 있는 Group 도 COUNT 0), t104 가 프리셋에서 재현했고,
이번에 **경로가 다른 두 산물로** 확정됐다.

## 6. 감독 육안 대조 — 무엇을 어디서 보시는가

콘솔 **Preset Pool 1 (Dimmer)**. 두 슬롯이 나란히 있고 **둘 다 85% 여야 한다**.

    슬롯   이름          기대값   출처                     이게 답하는 질문
      2    쇼 하이 OLD   85%      옛 경로 (M4, t108 이전)   질문 A — 옛 경로가 값을 날랐나
      7    쇼 하이       85%      새 경로 (t108, 오늘)      질문 B — **t114 의 본 질문**

읽는 법:

    슬롯 7 이 85%   → t108 경로가 값을 나른다. **t114 통과**
    슬롯 7 이 비었거나 0%  → 네 명령이 executed_ok 를 받고도 값이 안 남았다.
                            그러면 apply 단계가 무효이고 별도 카드가 필요하다
    슬롯 2 는 별개 질문이다 — 여기가 85% 면 옛 경로도 값을 날랐다는 뜻이고,
    그건 오히려 이상하다(t108 이 없던 단계를 추가했는데 값이 이미 있었다면
    프로그래머에 누가 값을 채워 뒀다는 뜻이다). **두 슬롯의 답을 섞지 마라.**

나머지 다섯(풀 100 · 미드 60 · 로우 30 · 잔광 15 · 아웃 0)은 **전부 옛 경로
산물**이므로 질문 A 에만 속한다.

## 7. 원복

개명은 되돌릴 수 있다 — `Label Preset 1.2 '쇼 하이'`. 다만 그러면 슬롯 2 와 7 이
같은 이름이 되어 대조가 흐려지므로, **감독 육안이 끝난 뒤에** 하는 것이 맞다.
슬롯 7 자체의 제거는 이 카드가 하지 않는다 — 프리셋 삭제는 복구 수단이 없다.
