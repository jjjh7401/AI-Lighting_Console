# t204 -- 픽스처 타입 54종 재측정: "없음"이 아니라 "못 읽음"이었다

- 워크트리: .claude/worktrees/t90 (읽기 전용, 새 워크트리 불필요 -- 카드 지시)
- 이 세션 3장째 카드 (t199 -> t202(취소) -> t90/t204 연속), 기준: lane-protocol.md 9절
- 콘솔 안 씀(preview만). 처방 실행 안 함. 새 카드 안 만듦.

## 0. 한 줄

**type_unresolved 는 지금 0건이다** (8/30 리포트의 54건에서). 원인은 그때 응답기가
1.6.1(풀 캐싱)을 물고 있어 라이브러리 판독이 절단됐고, `library_unreadable`
기본값이 리포트에서 `absent`로 단정된 것으로 보인다 -- 코드 자신이 "없다고
단정하지 않는다"고 말하는 상태를 리포트가 단정했다(감독 지적이 맞았다).

## 1. 순서대로 잰 것

### 1.1 응답기 버전 -- ping 회신으로 (executed_ok 아님)

```
$ uv run python -m server.tools.responder_roundtrip --listen-port 9005 --skip-exec --wait 5
[PASS] ping: ok
       live version=1.6.2 plugin=CopilotResponder
[PASS] state: ok
result: PASS
```

**1.6.2 확인.** exec 결과가 아니라 ping 자체로 확인했다(8/30 리포트가 executed_ok로
판정해서 캐싱을 놓쳤던 실수를 반복하지 않기 위해).

### 1.2 `lxseq_e2e --action preview` 재실행 (읽기 전용)

정본 CSV: `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`
(86행 전량, `--listen-port 9005`)

```
console_read.complete_enough_to_judge_absence: True
types.resolved: 8종 전부
types.unresolved: 0종
fid_map: 86 (전량 판독)
```

### 1.3 상태별 행 분리

| kind | 행 수 |
|---|---:|
| already_patched | 62 |
| mode_unresolved | 24 |
| (합계) | 86 |

**`type_unresolved` 계열(absent/ambiguous/library_unreadable) 자체가 이번
회차에 0행이다.** 카드가 요구한 "상태별 행별 표"는 그래서 만들 대상이 없다 --
이것 자체가 답이다. `ambiguous`는 8/30 리포트에도 등장한 적이 없어 이 저장소
에서 실측된 적이 있는 상태인지 자체가 미확인이다(§4).

코드 확인(`server/lxseq/mapper.py:497-534`): 타입 해석(`type_unresolved` 판정)이
`already_patched`/`mode_unresolved` 판정보다 **먼저** 실행된다(`_occupancy_skip`은
`console_type`을 인자로 받아 타입이 이미 풀린 뒤에만 호출됨). 그래서 지금의
62건 `already_patched`는 타입 미해결을 숨기고 있는 게 아니라 **타입이 실제로
풀린 뒤** 자리 점유로 걸린 것이다.

## 2. 54(8/30) 와 나란히 놓기 -- 왜 줄었는가

| 시점 | 응답기 ping | type_unresolved | mode_unresolved | address_occupied/already_patched |
|---|---|---:|---:|---:|
| 2026-08-30 | **1.6.1**(캐싱, 디스크는 1.6.2) | 54 | 24 | 7 |
| 2026-08-31(이번) | **1.6.2**(ping 확인) | **0** | 24 | 62(already_patched) |

- **mode_unresolved 24는 완전히 동일하다** -- 이 축은 응답기 버전과 무관하고
  안 변했다(t128, PR #182 로 이미 닫힌 사안과 무관하게 다시 나타나는 게 아니라
  같은 24건이 계속 그 자리에 있는 것으로 보인다 -- 개별 FID 재대조는 안 함, §4).
- **54(type_unresolved) + 7(address_occupied) = 61 ≈ 62(already_patched, 오차 1)**.
  이전에 "타입이 없다"거나 "자리가 이미 찼다"로 갈라 적혔던 행 대부분이 지금은
  "타입도 풀리고 그 타입이 이미 그 자리에 패치돼 있다"는 **단일하고 더 강한 정보**로
  합쳐졌다.
- **줄어든 이유**: 8/30 시점엔 응답기가 캐싱된 1.6.1을 답하고 있었고, 그 리포트
  자신이 "풀 childCount 20인데 19개만 회신"(절단)이라고 적어 뒀다. 라이브러리
  판독이 절단되면 `type_resolutions`에 항목이 없는 타입은 코드 기본값
  (`mapper.py:505,520`)에 따라 `library_unreadable`로 떨어지는데, 리포트는 이를
  `absent`로 단정했다. 재임포트 후 1.6.2가 확인되고 라이브러리 판독이 절단 없이
  완료되면서(§1.2 `complete_enough_to_judge_absence: True`), 그 54건의 타입
  해석이 정상적으로 이뤄진 것으로 보인다.
- **"54가 줄었다"를 그 자체로 성과로 쓰지 않는다** -- 위 인과(캐싱->절단->
  기본값 오분류->재임포트로 해소)가 이 감소의 이유라고 판단하는 근거이고, 이
  인과 자체는 8/30 리포트와 이번 측정 두 시점의 대조로 재구성한 것이지 그
  절단-당시 라이브러리 내용을 직접 관측한 것은 아니다(§4).

## 3. 판정 규율 적용 -- (A)/(B)/(C)

- **type_unresolved 0건**: 막힌 것 자체가 없다. 분류할 "안 된다"가 없다.
- **mode_unresolved 24건**: 8/30 리포트가 이미 "우리 코드/문서 매칭 문제"(처방:
  `--mode-overrides`, PR #182로 t128이 이미 일부 닫음)로 분류해 뒀다 -- 이번
  회차에서 재검증하지 않았고 t128 처분을 그대로 존중한다.
- 새로 분류할 것이 없어 (A)/(B)/(C) 표는 이번 카드에서 만들 대상이 없다.

## 4. 안 잰 것

- **8/30 당시 절단된 라이브러리의 실제 내용**은 재현 불가(그 순간의 캐시 상태는
  지나갔다) -- §2의 인과는 재구성이지 직접 관측이 아니다.
- **mode_unresolved 24건이 8/30의 24건과 같은 FID인지** 개별 대조 안 함 -- 숫자만
  같고 구성이 같은지는 미확인.
- **`ambiguous` 상태가 이 저장소에서 실측된 적이 있는지** -- 8/30 리포트에도
  이번 측정에도 한 번도 안 나왔다. 코드 어휘에는 있지만(mapper.py:30) 실측
  사례가 아직 없다는 뜻일 수도, 이 CSV/이 콘솔 조합에서 원리적으로 안 나오는
  상태일 수도 있다 -- 갈리지 않았다.
- **62건 already_patched가 실제로 의도한 패치와 완전히 일치하는지**(타입뿐 아니라
  모드·주소까지)는 이번 preview 판정을 그대로 신뢰했고 재확인 안 함.

## 5. 후속 후보 (카드로 안 만듦)

1. mode_unresolved 24건 개별 FID 대조(8/30 대비 구성 동일 여부).
2. ambiguous 상태를 실제로 유발하는 콘솔/CSV 조합이 있는지 별도 확인(코드
   어휘가 있는데 실측 사례가 없는 상태라 공허한 분기인지 궁금증만 남김).
