# 16 — 빈 타임코드 풀의 슬롯 판정 실기 회차 (SPEC-COPILOT-POOLEMPTY-001 M3)

일시: 2026-09-06 12:0x · 기준 트리: main `5e24357` · 실기 grandMA3 onPC · **콘솔 쓰기 0건**

## 무엇을 재려 했나

응답기 1.6.5 가 `state` 회신의 `node.enumeration` 에 열거 성공 여부를 싣는다. 앱은 그 표식이 `"ok"` 일 때에만 `childCount 0` 을 「비었음」으로 읽는다(REQ-POOLEMPTY-007). 그 사슬이 **실기에서** 작동하는지 — 그리고 계기가 공허하지 않은지(음성 대조군) — 를 잰다. AC-POOLEMPTY-013 · 014.

## 감독이 한 일

1. 워크트리의 `console/lua/copilot_responder.lua`(1.6.5)를 `~/MALightingTechnology/gma3_library/datapools/plugins/` 로 복사 — `.moai/state/verify/t270/deploy_165.sh` 가 수행(백업 `copilot_responder.lua.bak-20260906-110523`).
2. 콘솔에서 CopilotResponder 플러그인 슬롯 삭제 → `copilot_responder.xml` 재임포트.
3. `Delete Timecode 1` 시도 → 콘솔이 **`Illegal object`** 로 거절. **풀이 이미 비어 있었다** — 지울 대상이 없었던 것이며, 이 회차가 원하던 조건 그 자체다.

## 배치 심판

```
$ .venv/bin/python -m server.tools.responder_roundtrip --listen-port 9005 --skip-exec --expect-version 1.6.5
  [PASS] ping: ok
         live version=1.6.5 plugin=CopilotResponder
  [PASS] state: ok
result: PASS
```

## 측정 (읽기 전용)

```
$ .venv/bin/python .moai/state/verify/t270-m3/verdict_probe.py --listen-port 9005
```

raw `state` 회신 — 1.6.5 가 실은 표식이 그대로 보인다:

```json
{"children": [], "node": {"childCount": 0, "class": "Timecodes",
 "enumeration": "ok", "name": "Timecodes"},
 "offset": 0, "ok": true, "path": "DataPool/Timecodes", "truncated": false, "v": 1}
```

| 팔 | 경로 | 판정 | 사유 |
|---|---|---|---|
| **양성** | `DataPool/Timecodes` (빈 풀) | **free** — 점유자 `None`, `timecode_go True` | — |
| **음성 대조군** | `DataPool/NoSuchPool` | **unknown** — `timecode_go False` | 「…did not answer: path segment not found: 'NoSuchPool'… — the timecode write is withheld rather than sent unchecked」 |

두 팔이 갈렸다. 양성만이면 「계기가 고장 나 늘 free 를 답한다」와 구별되지 않는다.

전체 출력: `.moai/state/verify/t270-m3/verdict.json` · 프로브: 같은 폴더 `verdict_probe.py`.

## 대조군의 성격 (정직한 한계)

음성 대조군은 **판독-예외 갈래**(`did not answer`)이지 `enumeration: "failed"` 갈래가 아니다. 실기에서 「살아 있으나 `Children()` 이 실패하는 핸들」을 만들 방법이 이 회차에는 없었다 — 그 갈래는 오프라인 lupa 검사(`test_lua_responder.py`, 둘 다 `error()` 를 던지는 목 노드)가 덮는다. AC-013 이 요구한 「①만 있고 ②가 없으면 미통과」는 충족했고, 대조군의 종류는 이 문단이 명시한다.

## 콘솔 예산

발화한 쓰기 명령 **0건**. 이 회차의 콘솔 접촉은 `ping` 1 · `state` 조회 3(양성 raw 1 + 판정 2)뿐이다. 감독의 플러그인 재임포트는 앱의 발화가 아니다. AC-POOLEMPTY-014 충족.

## 결론

`childCount 0` 이던 새 쇼에서 앱이 첫 타임코드를 만들 수 없던 구멍이 **실기에서 닫혔다.** 앞선 회차(`14-musicsync-m3a-timecode-probe.md`)가 무결론으로 닫았던 그 자리다.
