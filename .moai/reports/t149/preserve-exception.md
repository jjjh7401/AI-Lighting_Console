# t149 — 예외를 달 자리가 아니라 **선언이 드리프트한 자리**다

- 카드: t149 · 안전장치 예외 심사 · 기준 `38e09b9` · 브랜치 `WT-preserve-exception`
- **게이트 파일 변경 0 · 코드 변경 0 · 콘솔 접촉 0.** 판정과 설계 초안까지다.

## 0. 판정 — **지금은 달지 않는다.** 권고는 선언 층으로 올리는 것

| 물음 | 답 |
|---|---|
| 예외를 달 근거가 있나 | **있다.** 확립된 형태(FXGEN 선례)가 이 변경에도 적용 가능하다 |
| 지금 달아야 하나 | 🔴 **아니다.** 아래 넷 때문이다 |
| 안 고치고 사는 것이 맞나 | **당분간 맞다.** 피해가 유계이고 이미 문서화돼 있다 |
| 그럼 무엇이 답인가 | **선언 층 결정** — 이 카드 위다. 설계 초안은 §4 에 준비해 뒀다 |

## 1. 🔴 잠금의 **원래 뜻**을 읽었다 — 「영원히 얼음」이 아니었다

카드가 「두 SPEC 이 왜 잠갔는지 먼저 읽어라」고 했다. 읽었더니:

    SPEC-COPILOT-PRECHK-001 plan.md:89
      | server/looks/{schema,loader,roles,resolver,instantiate,matching}.py |
        **PRECHK는 룩 계층 소비자가 아니다. 변경 0건**

    SPEC-COPILOT-SONGCUE-001 spec.md:182
      REQ-SONGCUE-021 [Unwanted] The **본 SPEC** shall not … PRESERVE 목록의 파일을 변경한다

**둘 다 「이 SPEC 이 안 건드린다」는 자기 범위 선언이다.** 「이 파일은 영구히 불변이다」가 아니다.

그런데 게이트는 그것을 **매 스위트 실행마다 영구 불변식으로 재단언**한다. 게이트 자신의
독스트링이 목적을 이렇게 적는다:

    What this file catches is a FUTURE edit crossing a boundary nobody re-checks

🔴 **여기가 드리프트다.** 선언된 경계는 「SPEC X 는 안 건드렸다」 — 그건 **역사적 사실**이라
나중에 누가 무엇을 하든 영원히 참이다. 지금 집행되는 경계는 「아무도 못 건드린다」다.
**게이트는 그 둘을 구별할 수 없다** — `git diff <base>..HEAD` 가 비었는지만 보기 때문이다.

## 2. 만료된 전제 — 다만 **게이트를 없앨 근거가 아니다**

게이트 독스트링의 동기 문장:

    The predecessor SPEC's PRESERVE gate was a ONE-OFF manual procedure, and this
    repository runs no CI. A gate nobody re-runs protects nothing …

**「runs no CI」는 만료됐다.** 내가 직접 쟀다:

    .github/workflows/test.yml  존재 · on: pull_request + push:[main]
    그 파일 머리말: 「이 저장소에는 테스트 CI 가 **없었다**」 (과거형)

그리고 오늘만 PR 열 건에서 그 CI 가 돌았다.

⚠️ **그런데 이것이 게이트를 무를 근거는 아니다.** 같은 독스트링이 스스로 가른다 —
「**NOT regression tests — this whole module is an INVARIANT GATE**」. CI 는 게이트를
**대체하는 것이 아니라 실행한다.** 즉 CI 의 등장은 게이트를 **약화**시킨 게 아니라
**강화**시켰다. 만료된 것은 동기 문장이지 기능이 아니다.

**판정은 이 만료를 알고 하되, 만료를 이유로 무르지 않는다.**

## 3. 왜 지금 달지 않나 — 넷

**① 피해가 유계이고 이미 문서화됐다.** t142·t141 이 **7자리**에 「정본이 아직 옛 사유를
말한다 + t149」 포인터를 박았다. 정본 옆을 지나는 사람은 낡음을 알게 된다. 침묵하는
모순이 아니다.

**② 값이 주석 한 문단이다.** 필요한 변경은 `server/looks/schema.py:16-18` 독스트링
정정(t142 실측 **17 삽입 · 3 삭제**). 동작 변경 0, 밴드 3 은 `(Zoom, Iris)` 그대로다.

**③ 비용이 비대칭이다 — 게이트 둘, 그중 하나는 기구가 없다.**

| 게이트 | 예외 기구 | 이 변경에 맞는 형태 |
|---|---|---|
| `test_overlap_preserve.py` | **있다**(FXGEN·SPATIAL·looks-library 선례) | 정확 행 쌍 핀(`_LOOKS_GRANTED_LINE_PAIRS` 형) |
| `test_songcue_bundle.py` `_PRESERVE_LOOK_FILES` | **없다** — 평평한 튜플 | **새로 설계해야 한다** |

게다가 이 변경은 **삭제 3줄이 있어 APPEND-ONLY 형이 안 맞는다** — 가장 싼 승인 형태가
배제된다.

**④ 🔴 그리고 결정적인 것: 예외를 달면 드리프트한 독법이 굳는다.**
§1 대로 선언은 「본 SPEC 이 안 건드린다」였다. 여기에 「t149 만 예외」를 붙이면
**「원래 영구 불변인데 하나 봐준다」는 독법을 사실로 만든다.** 더 싸고 정직한 수정은
**선언 층**에 있다 — 「이 목록은 그 SPEC 의 범위 선언이며, 완료 후 다른 카드의 변경은
이 게이트가 판정할 사안이 아니다」를 어디에 적을 것인가. **그건 이 카드 위다.**

### 3.1 선례가 그 방향을 가리킨다

`SONGCUE-001` 은 자기 PRESERVE 에서 **`console/lua/**` 한 항목을 뺀 적이 있다**(v0.2.0):

    그것을 관측할 유일한 수단(응답기의 프로퍼티 읽기)이 바로 이 PRESERVE 항목에 막혀 있었다.
    두 문서 중 하나는 반드시 어긋나며, **오케스트레이터가 측정을 택했다**(승인 기록 §F).
    개정 범위는 한 항목뿐이고 나머지는 그대로다 — 실측으로 확인했다.

**막힌 것이 필요한 일이면 예외를 다는 게 아니라 목록을 개정했다.** 다만 그때는 그 SPEC 이
살아 있었고 개정이 그 SPEC 의 승인 기록으로 남았다. 지금은 둘 다 `completed` 라
**같은 경로가 없다** — 그것이 이 카드가 선언 층 결정을 요청하는 이유다.

## 4. 설계 초안 (달기로 결정되면 이대로)

🔴 **두 게이트를 합치지 않는다.** 독스트링이 이유를 적어 뒀고 수치까지 있다 —
base 가 달라 `(234,238)`·`(524,569)` 가 **정확히 13줄** 어긋난다(`tools.py` 가 두 base
사이에 13줄 자랐다). 합치면 **엉뚱한 줄을 지키며 통과한다.**

### 4.1 `test_overlap_preserve.py` — 확립된 형태 그대로

FXGEN·looks-library 선례를 따른다:

1. `server/looks/schema.py` 를 `_preserve_diff_command()` 의 스윕에서 **뺀다**
2. 대신 **정확 행 쌍**으로 핀한다(`_LOOKS_GRANTED_LINE_PAIRS` 형) — 삭제 3줄·추가 17줄의
   원문을 그대로 적는다. 한 글자라도 다르면 실패
3. **비공허성 두 팔**을 함께 단다(그 파일의 기존 관례):
   - 승인 목록이 비어 있지 않다
   - `git diff --stat <base>..HEAD -- server/looks/schema.py` 가 **비어 있지 않다**
     (승인만 있고 실제 변경이 없으면 게이트가 꺼진 채 초록이다)
4. 넓은 경로는 **문서화된 경계로 튜플에 남기고** diff 명령에서만 치환한다

### 4.2 `test_songcue_bundle.py` — 기구를 새로 만들되 두 단언을 안 깬다

현재 두 자리가 목록을 조용히 못 좁히게 한다:

    :486  assert tuple(command[5:]) == _PRESERVE_LOOK_FILES
    :505  assert _PRESERVE_LOOK_FILES

**설계**: `overlap_preserve` 가 쓰는 것과 **같은 모양**으로 간다 —

    _PRESERVE_LOOK_FILES        (6개, 그대로 둔다 — 문서화된 경계)
    _LOOK_GRANTED_FILE          "server/looks/schema.py"
    _LOOK_GRANTED_LINE_PAIRS    (삭제 원문, 추가 원문) 쌍

- `_preserve_diff_command()` 는 `_PRESERVE_LOOK_FILES` 에서 승인 파일을 **뺀 것**을 넘긴다
- `:486` 은 그 **치환된 형태**를 단언하도록 같이 고친다
  (`overlap_preserve:531-544` 가 정확히 그 모양이다 — 「swap 이 경계를 통째로 빼먹지
  않았음」까지 단언한다)
- `:505` 비공허성은 **그대로 산다**(목록이 여전히 비어 있지 않다)
- **추가**: 승인 파일의 diff 가 비어 있지 않다는 두 번째 팔을 단다

즉 **새 개념을 만들지 않는다** — 형제 파일의 확립된 형태를 옮긴다. 이 저장소가
「이미 갖고 있는 것을 다시 짓지 마라」로 열 번 확인한 그 규율이다.

### 4.3 정확 행 쌍 핀의 **왼쪽(before)** — 이 카드가 확정해 둔다

`server/looks/schema.py:15-18`, 현재 트리(`38e09b9`) 원문 그대로:

    3. Probe-gated beam vocabulary — resolved by the M0 live probe to ``Zoom`` and
       ``Iris``. ``Focus`` / ``Frost`` / ``Prism1`` / ``Shutter`` were rejected by
       the console and never entered. Strobe and shutter are out of scope
       regardless: ``server/web/preview.py:131-139`` classifies them ``danger``.

「콘솔이 거절했다」가 그 문장이다 — t141·t154 가 확정한 대로 `Focus`·`Frost` 는
**철자**였고, `Prism1` 만 진짜 부재이며, `Shutter` 는 미확정이다.

오른쪽(after)은 t142 가 저작했다가 되돌렸으므로 **저장소에 없다**(§5-4).

## 5. 안 잰 것

1. **다른 네 개 looks 파일** — 이 판정은 `schema.py` 한 자리만 본다. 나머지
   (`loader`·`roles`·`resolver`·`instantiate`·`matching`)에 같은 필요가 있는지는 안 쟀다.
2. **선언 층 수정의 형태** — 「PRESERVE 목록은 그 SPEC 범위 선언이다」를 **어디에**
   적을지(규칙? SPEC 본문? 게이트 독스트링?) 안 정했다. 소유자가 다르다.
3. **설계 초안을 실제로 짜 보지 않았다** — 게이트 파일을 안 건드리는 것이 카드 조건이라
   코드로 검증하지 않았다. §4 는 **읽어서 만든 초안**이고, 짜 보면 `:486` 치환 형태에서
   막힐 수 있다.
4. **t142 편집분의 「after」 원문** — 이 카드에서 **왼쪽(before)만 확정했다**(§4.3).
   오른쪽은 t142 가 되돌렸으므로 저장소에 없다. 정확 행 쌍 핀을 쓰려면 그 카드가
   다시 저작해야 한다. **수치(17삽입/3삭제)는 t142 보고서에서 옮긴 값이고 이 카드가
   재현하지 않았다** — 그 자체가 재저작 후 다시 재야 할 값이다.
5. **게이트가 잠근 나머지 경로들** — `console/lua/`·`rulebook/assets/`·`web/preview.py` 등도
   같은 드리프트를 갖는지 안 봤다. §1 의 관찰이 그것들에도 적용되는지는 별개 물음이다.
