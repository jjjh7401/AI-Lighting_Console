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

---

## 추가 2 — 마지막 조(triage-02b) 6장, 리드 검산

`addendum.md` 본문을 커밋한 뒤 조 하나가 더 완주했다. 리포트: `report-02b.md`.
조 생존은 12개 중 **3개**(triage-04a 9장 · triage-02a 6장 · triage-02b 6장)로 정정.

### 닫은 카드 없음 — 판정만 6장

| 카드 | 판정 | 리드 검산 |
|---|---|---|
| t132 | ALIVE (일부 UNMEASURED) | — |
| t133 | **DECISION** (좁은 주장은 DEAD) | 검산함, 아래 |
| t136 | ALIVE | 본편에서 이미 확인 |
| t138 | DECISION | 스키마를 열지 여부 |
| t139 | ALIVE | 검산함, 아래 |
| t143 | ALIVE | 🔴본편에서 **중복으로 닫았다** — 아래 |

### t133 — 결함이 아니라 결정이다 (리드 검산 완료)

조의 판정: 「켈빈→RGB 매핑이 결함이다」는 DEAD — 그런 매핑이 **아예 없어서**
결함일 수가 없다. 남는 것은 「모델을 아직 안 골랐다」는 DECISION.

리드 재측정:
```
grep -n '_KELVIN' server/lxseq/preset_parser.py
→ 392: _KELVIN = re.compile(r"~?\s*(\d{3,5})\s*K\b", re.IGNORECASE)

grep -n 'Warm White' server/web/session.py
→ 2528: ("Warm White", (100, 75, 40))
```
켈빈을 **읽는** 정규식은 있지만 RGB 로 **변환하는** 모델은 없고, `Warm White` 는
켈빈 참조가 없는 생 RGB 삼중항이다. 조의 갈라치기가 옳다 — 이 카드는 「고칠
결함」이 아니라 「모델을 들일지」의 감독 결정이다. 카드 성격이 바뀌므로 착수
시점에 그 프레임으로 읽어야 한다.

### t139 — 접두 매칭이 그대로다 (리드 검산 완료)

```
grep -n 'startswith' server/lxseq/preset_parser.py
→ 256: if token.lower().startswith(known.lower()) and known not in found:
→ 649: if lowered.startswith(known_lower):
→ 72-74: 주석이 비대칭을 직접 적어 두었다
    목록 `Prism`  · 시트 `Prism1` -> "prism1".startswith("prism")  참
    목록 `Prism1` · 시트 `Prism`  -> "prism".startswith("prism1")  거짓
```
카드가 지적한 과다 수용이 코드에 그대로 있고, **주석이 그 비대칭을 이미 알고
있다.** ALIVE 확정.

### 🔴 t143 — 조 판정과 리드 조치가 어긋난 것을 남긴다

조는 t143 을 ALIVE 로 냈고 그 근거(커밋 `ef0103a` 의 diffstat 3파일·548/0)는
정확하다. 그러나 리드는 본편에서 t143 을 **t136 과 중복**이라 닫았다. 둘은
모순이 아니다 — 조가 판정한 것은 「카드가 가리키는 일이 남아 있는가」(남아
있다)이고, 리드가 판정한 것은 「그 일을 가리키는 카드가 둘인가」(둘이다)다.
남긴 카드는 t136 이므로 **일은 장부에 남아 있다.**

조가 스스로 적은 주의가 정확하다: *"커밋의 인용이 정확한 것이 카드의 목표가
달성됐다는 증거는 아니다"* — 지시했던 함정을 조가 지켜 냈다.

또 조는 `.moai/reports/t136/verdict.md` 가 11,285바이트로 **이미 존재한다**고
보고하면서 내용은 읽지 않았다(크기만 확인). 그 파일이 t136 의 완료 조건 일부를
이미 충족하는지는 **미검증**이다 — t136 착수 시 첫 확인 대상이다.

### 누적 정정

- 판정: 47 → **53** (85장 중 62%)
- 닫음: **5장** 그대로 (이 조에서는 닫힌 것 없음)
- 조 생존: 12개 중 **3개**
- 미판정: 38 → **32장**
