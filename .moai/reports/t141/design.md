# t141 설계 — 두 어휘의 정본 자리와 매핑 자리

- 카드: t141 · SPEC-COPILOT-LXSEQ-003 · 기준 `08edf8b` · 트리 `.claude/worktrees/t141`
- 선행 측정: `.moai/reports/t141/sheet-token-census.md` (커밋 `1af9a08`)
- **콘솔 접촉 0.** 코드 판독뿐이다.

## 0. 물음 — 「통일」이 아니다

카드가 묻는 것은 **「두 어휘를 각각 어디에 정본으로 세우고, 그 사이 매핑을 어디에 두나」**다.
통일하면 회귀한다는 것은 t135 가 BM.03 로 이미 관측했고, 정본 SPEC 이 그것을 실었다
(`.moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md` §A.4-2b, t146 신설).

## 1. 통일이 불가능한 **기계적** 이유 — 술어의 방향

`server/lxseq/preset_parser.py:209·213`:

    known_names = list(_ACCEPTED_ATTRIBUTES) + list(_PROBE_REJECTED) + list(_OUT_OF_SCOPE)
    if token.lower().startswith(known.lower()) and known not in found:

**목록의 항목은 시트 토큰의 접두사로 쓰인다.** 그래서:

| 목록 항목 | 시트 토큰 | 판정 |
|---|---|---|
| `Prism` | `Prism` (「Prism 3-facet ON」에서 `_WORD` 가 뽑는 것) | `"prism".startswith("prism")` → **참** |
| `Prism1` | `Prism` | `"prism".startswith("prism1")` → **거짓** |
| `Prism` | `Prism1` (시트가 그렇게 적었다면) | `"prism1".startswith("prism")` → **참** |

**짧은 항목이 엄격히 더 관대하다.** 그리고 콘솔이 받는 이름(`Prism1`·`Frost1`·`Focus1`)은
시트 토큰(`Prism`·`Frost`)보다 **길다** — 이 술어에 정확히 반대 방향이다.

결론: **한 목록이 두 일을 동시에 못 한다.** 시트를 걸려면 짧아야 하고, 콘솔에 쏘려면
길어야 한다. 콘솔 어휘를 이 목록에 넣으면 시트가 콘솔 철자를 쓸 때만 걸리므로,
시트가 감독 어휘를 쓰는 한 **영원히 안 걸린다** — 그것이 BM.03 회귀의 원리다.

취향 문제가 아니다.

## 2. 🔴 새 실측 — 폭발 반경이 SPEC 이 적은 것보다 크다

> **[반증 고지 — 2026-08-30, t154 가 덧붙였다. 아래 절은 한 글자도 고치지 않았다.]**
>
> **이 절의 결론은 틀렸다.** SPEC 의 원래 문면(「bm 임포트가 통째로 0건」)이 맞고,
> 아래의 「프리셋 임포트 전체가 0건」이 과장이다.
>
> 소비 루프가 종류를 안 가리는 것은 맞다. 그런데 **그 계획에 다른 종류가 애초에
> 못 들어온다** — `parse_preset_csv` 가 헤더에서 종류 하나를 정하고
> (`server/lxseq/preset_parser.py:380`·`:434`), 그 함수의 프로덕션 호출지는
> `import_lxseq_presets` 안의 한 곳뿐이며(`server/orchestrator/tools.py:4883`)
> 인자는 시트 **한 장**이다. **한 번의 임포트 = 한 시트 = 한 종류.**
>
> 틀린 형태: 소비 루프만 읽고 **생산 지점**(무엇이 `planned` 에 들어오나)을 안 읽었다.
> 원문을 남기는 이유는 그 형태가 기록으로 남아야 하기 때문이다. 정정 경위는
> `.moai/reports/t154/blast-radius.md`.

SPEC §A.4-2b 는 「열면 bm 임포트가 통째로 0건이 된다」고 적었다. 코드를 읽으니
**bm 만이 아니다.**

`server/orchestrator/tools.py:4983-5008` (읽기만 함):

    bundles, untranslatable = [], []
    for placement in result.planned:            # <- 종류를 안 가린다. 계획 전체다
        apply_command = _lxseq_preset_apply_command(placement)
        if apply_command is None:
            untranslatable.append(...); continue
        bundles.append(...)

    if untranslatable:                          # <- 하나라도 있으면
        payload["refusal"] = "apply_untranslatable"
        return ...                              # <- bundles 를 버리고 반환한다

`LXSEQ_PRESET_APPLY_ATTRIBUTE = dict([("preset-dim", "Dimmer")])` (`:1692`) 이고 bm 항목이
없으므로 bm 배정은 `None` 을 낸다. 그리고 `planned` 는 보류를 뺀 저장 가능분만 담는다
(`server/lxseq/preset_mapper.py:357-366` — `to_plan` 에서 만든다).

**그러므로 bm 한 행이 storable 로 열리는 순간, 같은 계획에 있던 dim·col 배정까지 전부
안 나간다.** 「bm 이 0건」이 아니라 **「프리셋 임포트 전체가 0건」**이다.

이것이 설계를 가른다: **매핑에서 보류를 자동으로 파생시키면 지뢰를 심는 것**이다.
콘솔 어휘가 넓어지는 날(t149) bm 행이 저절로 열리고, 그날 프리셋 임포트 전체가 죽는다.

## 3. 설계

### 3.1 정본 자리 — 이미 갈려 있다. 이름을 붙인다

| 어휘 | 정본 | 성격 |
|---|---|---|
| 콘솔에 **쏘는** 문자열 | `server/looks/schema.py` (밴드 1·2·3) | 실기로 잰 것. **PRESERVE 게이트 둘이 잠금 — t149** |
| 감독 **시트에 적힌** 토큰 | `server/lxseq/preset_parser.py` (`_PROBE_REJECTED` · `_OUT_OF_SCOPE`) | 이 리그 시트의 어휘. 전수는 census 참조 |

두 자리는 이미 물리적으로 갈려 있다. 없는 것은 정본이 아니라 **연결**이다.

### 3.2 매핑 자리 — 지금은 **없다**. 산문과 검사 하나가 대신하고 있다

지금 두 어휘의 관계를 담는 것은:

- `preset_parser.py:59-86` 의 주석 블록 (산문)
- `test_lxseq_preset_beam_vocabulary.py::test_the_two_vocabularies_differ_in_exactly_one_name`
  — 「둘이 정확히 한 이름만 다르다」를 고정한다

**둘 다 관계를 *서술*하지 매핑을 *담지* 않는다.** `Frost` 의 콘솔 이름이 `Frost1` 이라는
사실은 코드 어디에도 데이터로 없다 — t135 보고서와 SPEC 산문에만 있다.

제안: **매핑을 `preset_parser.py` 에 데이터로 둔다.**

    #: 감독 시트 토큰 -> 콘솔에 쏘는 어트리뷰트 이름. 두 어휘의 **유일한 연결 지점**이다.
    #: 방향이 비대칭이라(§1) 한 목록으로 못 합친다: 매칭은 키(짧은 총칭)로만 걸리고
    #: 발사는 값(정확 채널명)으로만 된다.
    _SHEET_TO_CONSOLE_ATTRIBUTE = dict([
        ("Focus", "Focus1"),
        ("Frost", "Frost1"),
        ("Prism", "Prism1"),
        ("Shutter", "Shutter1"),
    ])
    _PROBE_REJECTED = tuple(_SHEET_TO_CONSOLE_ATTRIBUTE)   # 매칭 정의역은 키 쪽이다

**왜 여기인가**: (a) 소비자가 이 파서다, (b) 콘솔 쪽 정본은 잠겨 있어 못 쓴다,
(c) 매핑은 콘솔 어휘의 성질이 아니라 **이 리그 시트와 콘솔 사이의** 성질이다 — 다른
시트가 오면 매핑이 바뀌지 콘솔 어휘가 바뀌지 않는다.

**오늘 동작은 안 바뀐다**: 키 순서가 현재 튜플과 같아 `_PROBE_REJECTED` 는 바이트 동일하다.

⚠️ 값 넷 중 셋(`Focus1`·`Frost1`·`Shutter1`)은 t135 가 DMX 채널 목록에서 **읽은** 이름이고,
`Prism1` 은 **쏴 본** 이름이다(그리고 `Failed` 를 냈다). 즉 이 표는 「콘솔이 받는 이름」이
아니라 **「콘솔에 쏘는/쏜 이름」**이다. 그 구분을 주석에 적는다.

### 3.3 보류는 **파생시키지 않는다** — 대신 어긋남을 검사가 잡는다

「콘솔 이름이 수용되면 시트 토큰의 보류를 자동으로 푼다」는 매력적이지만 §2 의 지뢰다.
그래서 파생 대신 **트립와이어**를 놓는다:

    콘솔 어휘가 넓어져 `_SHEET_TO_CONSOLE_ATTRIBUTE` 의 값 하나가 수용 목록에 들어가면,
    그 키가 아직 `_PROBE_REJECTED` 에 있는 한 보류 사유 문면이 **거짓**이 된다
    ("라이브 프로브가 거절한 속성").  그 순간 검사가 빨개지고,
    실패 메시지가 **적용 경로도 함께 열어야 한다**고 지목한다.

이러면 세 가지가 동시에 성립한다:
- 오늘 동작 불변 (수용 목록에 `Frost1` 이 없으므로 트립와이어는 조용하다)
- 낡음이 **조용히** 남지 않는다 (지금은 아무도 안 잡는다)
- 자동으로 열려 임포트를 죽이지 않는다 (§2)

## 4. 범위 — 이 카드가 건드리는 것

- `server/lxseq/preset_parser.py` — 매핑 신설 + `_PROBE_REJECTED` 를 키에서 파생 +
  주석 블록을 정본 SPEC(§A.4-2b) 인용으로 다시 씀
- `server/tests/test_lxseq_preset_beam_vocabulary.py` — 방향 불변식 · 트립와이어 · 비공허성

**안 건드리는 것**: `server/looks/schema.py`(PRESERVE 잠금, t149) ·
`server/orchestrator/tools.py`(적용 경로 축은 별개 카드) · `_OUT_OF_SCOPE`(풀 계열 축이라
어휘 매핑 축이 아니다 — census 결과 이 리그에서 `Gobo` 하나만 발동한다)

## 5. 안 잰 것

1. **`_OUT_OF_SCOPE` 쪽 매핑** — 안 만들었다. 풀 계열 이름(`Position`·`Control`…)은 어트리뷰트
   이름이 아니라 **풀 이름**이라 콘솔 쪽 대응이 어트리뷰트가 아니다. 같은 표에 넣으면
   두 종류를 섞는다.
2. **다른 RIG 팩의 시트 어휘** — census §5-1. 이 리그 시트만 봤다.
3. **적용 경로를 여는 설계** — 이 카드가 안 한다. §2 는 그 축이 **존재한다**는 것을 잰
   것이지 그것을 여는 방법이 아니다.
4. **`_ACCEPTED_ATTRIBUTES` 쪽도 같은 비대칭을 갖는가** — `Zoom` 은 시트에도 콘솔에도
   `Zoom` 이라 지금은 안 갈린다. 콘솔에 `Zoom1` 류가 있는지는 안 쟀다.
