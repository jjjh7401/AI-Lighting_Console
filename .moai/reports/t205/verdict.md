# t205 -- Aura XB 24행 모드 오버라이드 -- preview까지, 1단계 패치 완결 확인

- 워크트리: .claude/worktrees/t205, 브랜치 WT-aura-mode-override
- 이 세션 4장째 카드, 기준: lane-protocol.md 9절 (5장 임계 임박 -- 이번 카드 종료 후 인계)
- preview만 실행. apply 실행 안 함. 콘솔에 쓰지 않았다.

## 0. 한 줄

--mode-overrides 로 Martin MAC Aura XB 를 Extended - Extended 로 지정해
preview를 재실행하니 mode_unresolved 24 -> 0, 새로운 스킵 사유 없음, 총계
86 유지. 그리고 그 24행도 already_patched로 떨어졌다 -- 즉
write_count_planned = 0. 1단계 패치는 지금 콘솔 기준으로 이미 전부
끝나 있다(86/86 already_patched). apply할 것 자체가 없다.

## 1. 순서대로 잰 것

### 1.1 응답기 버전 재확인 (착수 시점)

responder_roundtrip --listen-port 9005 --skip-exec --wait 5 실행:
ping ok, live version=1.6.2 plugin=CopilotResponder, result PASS.

### 1.2 플래그 문법 확인 (추측 안 함)

lxseq_e2e --help 로 확인: --mode-overrides 는 JSON 형태(CSV타입을 키로,
콘솔모드를 값으로)다. 키는 콘솔 모드명이 아니라 CSV 타입명이다
(mapper.py 의 mode_overrides.get(csv_type) or mode_overrides.get(console_type)
확인). CSV 원문에서 타입명 그대로 뽑음: Martin MAC Aura XB.

### 1.3 preview 재실행 (오버라이드 적용)

명령: lxseq_e2e --csv <정본CSV> --action preview --listen-port 9005
--mode-overrides 로 Martin MAC Aura XB -> Extended - Extended 매핑 전달.

결과: skipped 86건 = already_patched 86 (전량), write_count_planned 0,
write_count_applicable 0, runs 0.

### 1.4 FID 집합 교차대조 -- 카드가 요구한 안전성 확인

t204 preview(오버라이드 없음, already_patched 62 / mode_unresolved 24)와
이번 결과(already_patched 86)를 FID 집합으로 대조:

- 이전 already_patched(62)가 이번 already_patched(86)의 부분집합인가: True
- 이번에 새로 already_patched 로 들어온 24개가 이전 mode_unresolved(24)와
  정확히 같은가: True
- 이전 already_patched 중 이번에 사라진 것이 있는가: 없음(공집합)

기존 62행은 오버라이드에 전혀 건드려지지 않았고, 새로 already_patched가
된 24행은 정확히 이전 mode_unresolved 24행과 일치한다. 새로운 실패 사유는
생기지 않았고 총계도 86으로 유지된다 -- 카드가 요구한 안전성 확인 전부 통과.

## 2. 왜 already_patched 인가 -- apply가 필요 없는 이유

Extended - Extended(25ch)로 모드가 풀리자, 그 24대의 콘솔상 현재 자리·타입·
모드가 CSV가 의도한 것과 이미 일치하는 것으로 판정됐다(occupancy 판정 로직,
같은 타입이 같은 자리에 이미 있다 -- 이미 패치됨). 즉 이 24대는 이미
콘솔에 올바르게 패치돼 있었고, 막고 있던 것은 실제 미패치가 아니라 우리
쪽 모드 이름 매칭 실패(CSV가 뒤쪽 겹 모드명을 안 줌)였다 -- t128 진단
그대로였다.

## 3. 판정 규율 -- (A)/(B)/(C)

mode_unresolved 24건은 감독 답(모드명 확정)으로 해소됐다 -- 카드 본문이
이미 이걸 (C)(문서 의도 미확인 -> 감독에게 물어야 함)로 분류해 뒀고,
이번 회차가 그 답을 반영해 닫았다. 새로 분류할 안 된다 는 없다.

## 4. 안 잰 것 (카드가 남긴 것 + 이번 회차가 못 채운 것)

- already_patched 62행이 언제·어떻게 패치됐는지(감독 GUI인지 이전
  apply 런인지) -- 이번 회차도 못 갈랐다. preview 산출만으로는 시점을
  알 수 없다.
- 이 24행이 8/30 리포트의 24행과 같은 FID인지 -- 8/30 리포트는 FID
  목록이 아니라 개수(24)만 남겼다. t204 preview(2026-08-31 기준)의 24개
  FID는 이번 1.4절로 확인했지만, 8/30 당시의 실제 FID 목록 자체가 없어
  그 시점과의 개별 대조는 원리적으로 불가능하다(자료 부재, 수단 없음).
- apply 실행은 안 함 -- write_count_planned가 0이라 실행해도 쓰기가
  안 나갈 것으로 보이지만, 이것도 관측이지 apply를 돌려서 확인한 것은
  아니다(카드 지시: preview까지).

## 5. 결론 -- 리드에게 보고할 것

1단계 패치 스테이지는 86/86 already_patched, 쓸 것 0건으로 콘솔 기준
이미 완결 상태다. apply를 실행할 필요 자체가 없어 보인다(관측이지 실행
확인은 아님). 감독 승인이 있더라도 이 CSV 기준으로는 apply가 아무것도
쓰지 않을 것으로 예상된다.
