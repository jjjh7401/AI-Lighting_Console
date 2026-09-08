# t266 추가분 — 마지막 두 조의 산출과 리드 검산

회차 본편은 `verdicts.md`. 이 파일은 본편을 커밋한 뒤 도착한 조 둘의 결과와,
그것을 리드가 검산한 기록이다.

- 측정: 2026-09-08, base `a91c4f8` (본편 머지 후, 코드 동일)
- 콘솔 쓰기 0건

## 추가로 닫은 2장 — 조 판정과 리드 재측정이 일치

### t284 — 폐기 (전제 소멸)

카드: 큐시트 항목 `mood`·`note`·`total_duration_ms`·`tc_source`·`tc_origin`·
`palette_legend`·XFADE 구분·다중 `fixture_groups` 에 **자리가 없다**(생산자 없음).

리드 재측정:
```
grep -n 'total_duration_ms\|tc_source\|tc_origin\|palette_legend' server/design/song_plan.py
→ 891: "total_duration_ms"   894: "tc_source"   895: "tc_origin"   898: "palette_legend"
→ 996: total_duration_ms: int | None = None    999: tc_source: str | None = None

grep -n '"mood"\|"note"\|"trans"' server/design/sugar_timeline.py
→ 81: "mood": "화사, 등장"   88: "trans": "SNAP"   90: "note": "[MANUAL] …"
  98: "mood": "경쾌, 근접"  105: "trans": "XFADE"

grep -c 'TRANS_VALUES' server/design/cue_sheet_edit.py → 4
```

카드가 「자리 없음」이라 주장한 필드 전부에 **실제 생산자가 있다.** `trans` 값에
`SNAP` 과 `XFADE` 가 둘 다 나오므로 XFADE 구분도 성립한다.

### t292 — 폐기 (재현되지 않음)

카드: `"이 시퀀스 조도 올려줘"` 가 시퀀스+올려로 2점을 얻어 적용(반영)으로
오라우팅된다.

리드 재측정:
```
grep -n '_DRAFT_APPLY_DESTINATION' server/web/session.py
→ 1129: _DRAFT_APPLY_DESTINATION = re.compile(r"콘솔|데스크|초안|시퀀스\s*\d+")
→ 1193: if _DRAFT_APPLY_DESTINATION.search(stripped) is None:
```

패턴이 `시퀀스\s*\d+` 로 **숫자가 붙은 시퀀스만** 매치한다. 카드 예시 문장에는
번호가 없어 destination 축이 애초에 매치되지 않는다(직접 실행: `False`). 번호를
붙인 변형은 destination 은 매치하지만 `_DRAFT_APPLY_EDIT_OBJECT` 가 조도 편집으로
판별해 반영 라우팅을 막는다 — 그 주석이 이 문장을 배제 사례로 명시한다.

## 판정만 받고 닫지 않은 것

| 카드 | 판정 | 왜 닫지 않았나 |
|---|---|---|
| t264 · t265 · t266 · t267 · t293 | ALIVE | 전제 그대로 |
| t120 · t122 · t123 · t125 | ALIVE | 전제 그대로 |
| t268 | DECISION | 등재 여부가 감독 판단 |
| t283 | UNMEASURED | 조가 명령을 지목하고 죽었다 |
| t124 | UNMEASURED | 같음 |

### 🔴 t121 — 조 판정을 리드가 **뒤집었다** (본편 §6 에 이미 기록)

조는 DEAD 로 냈다. 두 겹의 오류다:
1. 유예 파일 **11개 중 4개만** 쟀다("the 4 files actually named in per-file-ignores"
   라고 적었으나 실제 목록은 11개다).
2. 「오늘 숫자가 카드의 숫자와 다르다」를 「부채가 없다」로 읽었다. 카드의 일은
   **유예를 걷어내는 것**이고 유예는 85쌍 그대로다.

조가 잰 오늘 값(4개 파일 기준: E501 51 · E402 9 · B007 2 · B905 3 · E741 0 ·
SIM115 0 = 65)은 **카드 갱신에 쓸 수 있는 값**이라 여기 남긴다. 다만 11개 파일
전수 값은 여전히 미측정이다.

## 이 회차 누적

- 판정: 32 → **47** (87장 중 54%)
- 닫음: 3 → **5** (t63 · t143 · t180 · t284 · t292)
- 열린 카드: 89 → **85**
- 서브에이전트 판정 오류 누적: **3건**(t88 · t18 · t121), 전부 리드 재측정에서 잡힘
- 조 생존율: 12개 띄워 **2개 완주**(triage-04a 9장, triage-02a 6장), 나머지는
  컨텍스트 고갈로 사망 — 원인은 본편 §6

## 여전히 미검증

- 38장 미판정.
- t283 · t124 는 조가 필요한 명령을 지목했으나 실행 전에 죽었다 — 명령은 각 조
  리포트에 남아 있다.
- t121 의 11개 파일 전수 값.
- 목표(40장 이하)에 대한 판단은 본편 §5 그대로다: 닫힘 비율이 47장 중 5장 ≈
  11% 이므로 85장에 적용하면 약 9장이 닫히고 76장이 남는다. 목표는 측정으로
  도달하지 않는다.
