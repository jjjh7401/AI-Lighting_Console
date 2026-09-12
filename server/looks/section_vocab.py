"""구간 어휘 — 정본 §2 의 **두 축**과, 그 축이 §6 표의 어느 행을 부르는가.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` 이고, 이 모듈이 닫는 것은
그 문서 §12 항목 4 다: **구간 이름이 어휘에 없으면 큐가 아예 안 나간다.**

**고치기 전에 실측한 것**(2026-09-12, main ``0c0237b``). ``matching.DYNAMICS_TERMS`` 에
``breakdown`` 도 ``브레이크다운`` 도 없다(grep 0건). 결과는 「엉뚱한 룩」이 아니라
**큐 없음**이다 — ``songcue._section_dynamics`` 가 ``None`` 을 답하면
``requires_explicit_dynamics`` 가 참이 되고 ``_map_section_to_look`` 이
``EXPLICIT_DYNAMICS_REQUIRED`` 로 그 구간을 버린다. 실측 6구간 EDM 입력
(Intro·Build-Up·Drop·Breakdown·Drop 2·Outro)에서 **Breakdown 과 Outro 두 장이 안 나갔다.**

같은 실측이 두 번째 결함을 드러냈다 — **하이픈이 어휘를 뚫는다.** ``-`` 는
``matching._WORD`` 가 아니므로 ``Pre-Chorus`` 의 ``Chorus`` 앞뒤가 전부 경계로 읽히고,
``Pre-Chorus`` 와 ``Post-Chorus`` 가 **코러스 대역 (4,5)** 로 해석됐다. 한글은 이 구멍이
없다(``프리코러스`` 안의 ``코러스`` 는 앞 글자가 단어 문자라 안 걸린다) — 영문 하이픈
표기에만 뚫린 구멍이고, 정본 §2·§4 는 라벨을 **하이픈으로** 적는다.

## 왜 이 파일인가 — ``matching.py`` 가 아니라

``server/looks/matching.py`` 는 **선언된 무변경 대상**이고 잠금이 **둘**이다
(``server/tests/test_overlap_preserve.py`` ``_PRESERVE_PATHS`` ·
``server/tests/test_songcue_bundle.py`` ``_PRESERVE_LOOK_FILES``). 그 경계를 열려면
선언 층의 승인이 먼저 있어야 하고(선례: 카드 t348·t356), 그것은 이 카드의 범위가 아니다.

다만 자리를 옮기는 것이 **우회는 아니다** — 소비자가 실제로 다르다.
``DYNAMICS_TERMS`` 는 **운영자 질의**의 어휘다(「코러스로 가자」). 이 파일은 **구간 라벨**의
어휘다. 둘의 판정 규칙이 서로 다르다는 것이 위 하이픈 실측에서 드러났다:

* 질의는 **합집합**이 맞다. 「워십이나 발라드」처럼 둘을 부르는 것이 정상이고, 넓히는
  쪽이 fail-open 이다(``matching.resolve_dynamics`` 독스트링).
* 라벨은 **최장 일치**가 맞다. 라벨 하나는 구간 하나를 이름한다. ``Post-Chorus`` 를
  ``post-chorus`` ∪ ``chorus`` = (3,4,5) 로 읽으면 후렴 대역의 룩이 후주에 붙는다.

그래서 :func:`resolve_section_dynamics` 가 **다른 말의 진부분 문자열인 말을 뺀 뒤**
합집합한다. 어휘 자체는 복제하지 않는다 — :data:`SECTION_TERMS` 는 ``DYNAMICS_TERMS`` 를
**들여와** 합치고, 같은 말이 두 표에서 다른 대역을 가지면 **import 시각에 깨진다**
(:func:`_merged_terms`). 조용히 갈라지는 것이 복제의 실패 방식이므로, 시끄럽게 깨뜨린다.

## 축을 가른 결정과 그 근거 — 합치지 않았다, 다만 오늘 갈림이 없다

정본 §2 는 [HARD] 로 「라벨 집합을 두 벌 들고 곡의 장르로 선택한다」고 적고, 합치면
한쪽이 깨진다는 근거로 논문 수치를 든다 — 팝 어휘 모델을 EDM 에 그대로 쓰면 구간 이름
정확도가 **0.883 → 0.148** 로 무너진다.

그 수치는 **라벨을 만드는** 층의 것이다. 무너지는 이유가 「팝 어휘에 drop·build-up
클래스가 없다」이므로, 그것은 분류기의 **출력 알파벳**이 좁은 문제다. 이 저장소는 라벨을
만들지 않는다 — 운영자나 분석기가 이미 고른 라벨 **문자열을 읽는다.** 소비 표는 두 알파벳을
**동시에 들 수 있고**, 들어도 정확도가 무너질 자리가 없다.

그리고 정본 자신이 **조명 층에서는 두 축을 이미 합쳤다.** §6 표의 행 이름을 그대로 읽어라:

    ``pre-chorus · build`` · ``chorus · drop`` · ``breakdown · bridge``

셋 다 **팝 라벨과 EDM 라벨을 한 행에 묶은** 이름이다. 우리가 구현하는 층이 바로 그 층이다.

그래서 **판정 함수는 하나**로 두고, **선언은 두 벌**로 둔다(:data:`POP_AXIS` ·
:data:`EDM_AXIS`). 두 축이 공유하는 라벨의 배정을 **일부러 두 번 적는** 것이 요점이다 —
한 번만 적으면 :func:`axis_disagreements` 가 구조적으로 빈 답만 낼 수 있는 공허한 검사가
된다. 오늘 실측: 두 축의 교집합은 ``intro`` · ``outro`` · ``silence`` · ``end`` 넷이고
**넷 다 배정이 같다**(불일치 0건). 즉 장르로 축을 고르는 스위치는 오늘 **두 갈래가 같은
스위치**다.

**그래서 장르를 ``parse_sections`` 까지 끌고 가지 않았다.** 갈래가 같은 것이 실측으로
확인된 스위치를 위해 ``server/orchestrator/tools.py`` 의 호출 순서(장르 해석이 구간 파싱
**뒤**에 온다)를 뒤집는 것은 재지 못하는 이득을 위한 서명 변경이다.

**갈림이 생기는 날의 처방**(지금 적어 둔다): :func:`axis_disagreements` 가 비지 않으면
``test_section_vocab.py`` 가 빨개진다. 그때 해야 할 일은 이 표를 고치는 것이 아니라
**장르를 :func:`resolve_section_dynamics` 까지 배선하는 것**이다 —
``tools.py`` 에서 ``select_genre`` 를 ``parse_sections`` **앞**으로 옮기고, 해석된 슬러그를
파서에 넘긴다. 네 장르 중 ``edm`` 이 :data:`EDM_AXIS` 를, ``rock`` · ``ballad`` ·
``worship`` 이 :data:`POP_AXIS` 를 읽는다(:data:`GENRE_AXES`). 다섯 번째 장르는 오늘 이
코드에 **닿지 않는다** — ``busking.select_genre`` 가 라이브러리에 없는 장르를 그 앞에서
오류로 돌려보낸다.

## 세기를 안 준 라벨이 있다 — 못 준 것이 아니라 정본이 안 준 것

``()`` 는 「어휘에 없다」가 아니라 **「정본이 이 라벨에 세기를 주지 않았다」**이다. 둘은
다르고, 뒤엣것은 보고에 적을 수 있는 사실이다. 배정은 정본이 숫자나 대응 문면을 준
자리에서만 온다(각 항의 ``source``). 안 준 자리는 비운다 — **행을 지어내지 않는다**는
``section_intent`` 의 규율 그대로다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from server.looks.matching import (
    DYNAMICS_TERMS,
    _found,  # 구간 어휘를 실제로 대조하는 술어의 단일 출처 (section_intent 와 같은 사유)
    _normalise,
)

__all__ = [
    "EDM_AXIS",
    "GENRE_AXES",
    "POP_AXIS",
    "ROW_TERMS",
    "SECTION_TERMS",
    "SIX_ROW_ONLY",
    "SectionLabel",
    "axis_disagreements",
    "matched_section_terms",
    "resolve_section_dynamics",
]

#: 정본 §6 표의 행 이름. ``section_intent`` 가 여기에 밝기 구간을 붙인다 — 행 이름과
#: 밝기를 한 파일에 두지 않는 것은 소비자가 다르기 때문이다(이 파일은 세기, 저 파일은 밝기).
ROW_INTRO = "intro"
ROW_VERSE = "verse"
ROW_BUILD = "pre-chorus · build"
ROW_CHORUS = "chorus · drop"
ROW_POST_CHORUS = "post-chorus"
ROW_BREAKDOWN = "breakdown · bridge"


@dataclass(frozen=True)
class SectionLabel:
    """한 라벨의 배정 — 부르는 말, 세기 대역, §6 행, 그리고 그 배정의 **출처 문면**.

    ``dynamics`` 가 비면 정본이 이 라벨에 세기를 주지 않은 것이고, ``row`` 가 ``None``
    이면 §6 이 이 라벨에 **기계로 걸 수 있는 밝기 숫자**를 주지 않은 것이다. 둘은 서로
    독립이다 — ``outro`` 는 세기는 있고 행은 없다(§6 outro 행이 퍼센트 대신 「디밍한
    베이스」라고 적혀 있다).
    """

    terms: tuple[str, ...]
    dynamics: tuple[int, ...]
    row: str | None
    source: str


def _label(
    *terms: str,
    dynamics: tuple[int, ...] = (),
    row: str | None = None,
    source: str,
) -> SectionLabel:
    return SectionLabel(terms=terms, dynamics=dynamics, row=row, source=source)


# 정본 §2.1 팝 축 — SALAMI 기능 어휘. **표에 적힌 그대로 21개**다(묶음별 4·2·4·3·3·3·2).
# 절 제목은 「20개」라고 적었고 표는 21행이다. 어느 쪽이 맞는지 정본이 말하지 않으므로
# **표를 따르고 그 차이를 여기 적는다** — 하나를 골라 조용히 지우면 그 선택이 안 보인다.
POP_AXIS: Mapping[str, SectionLabel] = {
    # ── 기본 4
    "intro": _label(
        "인트로", "intro", "도입", dynamics=(1, 2), row=ROW_INTRO, source="§6 intro 행 20~40%"
    ),
    "verse": _label("벌스", "verse", dynamics=(2, 3), row=ROW_VERSE, source="§6 verse 행 25~50%"),
    "chorus": _label(
        "코러스",
        "chorus",
        "후렴",
        dynamics=(4, 5),
        row=ROW_CHORUS,
        source="§6 chorus · drop 행 80~100%",
    ),
    # 밝기 20~35% 는 intro 의 20~40% 안에 그대로 들어가므로 대역도 그쪽이지만, §6 이
    # 같은 행에 「무빙·이펙트 정지」를 함께 적었다. 정지는 D1 하나다 —
    # ``movement._DYNAMICS_BANDS`` 가 이미 그렇게 읽고 있고, 그 주석이 이 행을 이름으로
    # 지목한다(「§6 표의 앰비언트·브레이크다운·솔로가 「무빙·이펙트 정지」다」).
    # D2 를 넣으면 SLOW 대역이 열려 정본이 정지라고 적은 구간이 움직인다.
    "bridge": _label(
        "브릿지",
        "브리지",
        "bridge",
        dynamics=(1,),
        row=ROW_BREAKDOWN,
        source="§6 breakdown · bridge 행 20~35% + 「무빙·이펙트 정지」(정지 = D1)",
    ),
    # ── 기악 2 — §6 solo 행은 밝기 칸에 숫자 대신 「솔로이스트만 강조」를 적었다.
    # 그것은 §6.2 의 역할 문장이지 밝기가 아니고, 오늘 ``SectionIntent`` 가 드는 칸은
    # 밝기 하나다. 세기도 정본이 주지 않는다 — 비운다.
    "instrumental": _label(
        "기악", "instrumental", source="§2.1 기악 묶음 — 정본이 세기·밝기를 주지 않는다"
    ),
    "solo": _label(
        "솔로", "solo", source="§6 solo 행은 밝기 대신 역할을 말한다(「전용 스페셜 + 백라이트」)"
    ),
    # ── 전환 4 — §2.1: 「pre-chorus·pre-verse·interlude·transition 넷의 조명 의도가
    # 같다(§6)」. 넷이 한 행을 부른다는 것이 정본 문면이므로 배정도 하나다.
    "transition": _label(
        "전환",
        "transition",
        dynamics=(3,),
        row=ROW_BUILD,
        source="§2.1 「pre-chorus·pre-verse·interlude·transition 넷의 조명 의도가 같다」",
    ),
    "pre-chorus": _label(
        "프리코러스",
        "prechorus",
        "pre-chorus",
        dynamics=(3,),
        row=ROW_BUILD,
        source="§6 pre-chorus · build 행 40~55%",
    ),
    "pre-verse": _label(
        "pre-verse",
        dynamics=(3,),
        row=ROW_BUILD,
        source="§2.1 전환 넷의 조명 의도가 같다",
    ),
    "interlude": _label(
        "간주",
        "인터루드",
        "interlude",
        dynamics=(3,),
        row=ROW_BUILD,
        source="§2.1 전환 넷의 조명 의도가 같다",
    ),
    # ── 장르 고유 3 — §2.1: 「재즈의 head, 클래식의 main theme 는 팝의 chorus 에
    # 대응한다(논문 명시)」. secondary theme 은 그 문장에 없다 — 대응을 지어내지 않는다.
    "head": _label(
        "head",
        dynamics=(4, 5),
        row=ROW_CHORUS,
        source="§2.1 「재즈의 head … 팝의 chorus 에 대응한다(논문 명시)」",
    ),
    "main theme": _label(
        "main theme",
        dynamics=(4, 5),
        row=ROW_CHORUS,
        source="§2.1 「클래식의 main theme 는 팝의 chorus 에 대응한다(논문 명시)」",
    ),
    "secondary theme": _label("secondary theme", source="§2.1 이 라벨에는 대응 문면이 없다"),
    # ── 형식 고유 3 — 소나타 형식. 정본에 조명 의도가 없다.
    "exposition": _label("exposition", source="§2.1 형식 고유 — 조명 의도 문면 없음"),
    "development": _label("development", source="§2.1 형식 고유 — 조명 의도 문면 없음"),
    "recapitulation": _label("recapitulation", source="§2.1 형식 고유 — 조명 의도 문면 없음"),
    # ── 종결 3 — §6 outro 행은 퍼센트를 주지 않고 「리셋 큐 · 디밍한 베이스 · 느린
    # 페이드 1회」라고 적는다. 「디밍한」과 「느린」은 에너지를 말하므로 대역은 아래
    # 둘이고, 숫자가 없으므로 §6 **행은 없다**. 좁혀서 (2,) 로 적으면 정본이 주지 않은
    # 정밀도를 주장하는 것이다.
    "outro": _label(
        "아웃트로",
        "outro",
        dynamics=(1, 2),
        source="§6 outro 행 「디밍한 베이스 · 느린 페이드 1회」 — 퍼센트 없음",
    ),
    "coda": _label(
        "코다",
        "coda",
        dynamics=(1, 2),
        source="§2.1 종결 동의어군(outro · coda · fadeout)",
    ),
    # fadeout 은 §2.1 이 **겹쳐 붙는 라벨**이라고 명시한다 — 「코러스가 페이드아웃하면
    # 그 구간은 chorus + fadeout 둘을 갖는다」. 독립된 에너지 주장이 아니므로 대역을
    # 주지 않는다. 주면 ``Chorus Fadeout`` 이 (1,2) ∪ (4,5) 로 읽혀 후렴에 D1 룩이 붙는다.
    "fadeout": _label("fadeout", source="§2.1 「겹쳐 붙는 라벨」 — 독립 에너지 주장이 아니다"),
    # ── 특수 2 — 소리가 없는 자리와 파일 끝 표시. 조명 구간이 아니다.
    "silence": _label("silence", source="§2.1 특수 — 조명 구간이 아니다"),
    "end": _label("end", source="§2.1 특수 — 파일 끝 표시이지 조명 구간이 아니다"),
}

# 정본 §2.2 EDM 축 — 7개. 팝 축과 **겹치는 넷(intro · outro · silence · end)의 배정을
# 일부러 다시 적는다.** 한 번만 적으면 ``axis_disagreements`` 가 구조적으로 빈 답만 낼 수
# 있는 공허한 검사가 된다 — 두 벌을 들라는 §2 [HARD] 가 기계로 확인되는 자리가 여기다.
EDM_AXIS: Mapping[str, SectionLabel] = {
    "intro": _label(
        "인트로", "intro", "도입", dynamics=(1, 2), row=ROW_INTRO, source="§6 intro 행 20~40%"
    ),
    "build-up": _label(
        "빌드업",
        "빌드",
        "build",
        "buildup",
        "build-up",
        "라이저",
        "riser",
        dynamics=(3,),
        row=ROW_BUILD,
        source="§6 pre-chorus · build 행 40~55%",
    ),
    "drop": _label(
        "드랍", "drop", dynamics=(4, 5), row=ROW_CHORUS, source="§6 chorus · drop 행 80~100%"
    ),
    "breakdown": _label(
        "브레이크다운",
        "breakdown",
        dynamics=(1,),
        row=ROW_BREAKDOWN,
        source="§6 breakdown · bridge 행 20~35% + 「무빙·이펙트 정지」(정지 = D1)",
    ),
    "outro": _label(
        "아웃트로",
        "outro",
        dynamics=(1, 2),
        source="§6 outro 행 「디밍한 베이스 · 느린 페이드 1회」 — 퍼센트 없음",
    ),
    "silence": _label("silence", source="§2.2 특수 — 조명 구간이 아니다"),
    "end": _label("end", source="§2.2 특수 — 파일 끝 표시이지 조명 구간이 아니다"),
}

#: §6 표에는 행이 있는데 §2 어느 축의 어휘에도 없는 라벨. 셋째 통을 따로 두는 것은
#: **출처가 다르기 때문**이다 — 축 둘의 일치 검사가 이 항목을 세면 안 된다.
SIX_ROW_ONLY: Mapping[str, SectionLabel] = {
    "post-chorus": _label(
        "포스트코러스",
        "post-chorus",
        dynamics=(3, 4),
        row=ROW_POST_CHORUS,
        source="§6 post-chorus 행 60~75% + 「코러스보다 느리게」 · §4 표 406표본",
    ),
}

#: 장르 슬러그 → 그 장르가 읽는 축. 오늘 이 스위치는 **두 갈래가 같다**
#: (``axis_disagreements()`` 가 빈 것이 그 증거). 갈리는 날의 처방은 모듈 독스트링에 있다.
GENRE_AXES: Mapping[str, str] = {
    "edm": "edm",
    "rock": "pop",
    "ballad": "pop",
    "worship": "pop",
}


def axis_disagreements() -> tuple[str, ...]:
    """두 축이 **같은 라벨에 다른 배정**을 준 것들 — 오늘 비어 있다.

    비교하는 것은 세기 대역과 §6 행이다. 부르는 말은 비교하지 않는다 — 한 축이 그 라벨에
    별칭을 하나 더 다는 것은 갈림이 아니라 어휘의 넓이이고, 넓이가 갈리면 합집합이 답이다.

    이 함수가 빈 답을 내는 것이 **합쳐도 된다는 근거**다. 비지 않는 날 합친 표는 한쪽을
    깨뜨리고, 그때 장르를 배선해야 한다(모듈 독스트링 「갈림이 생기는 날의 처방」).
    """
    shared = sorted(set(POP_AXIS) & set(EDM_AXIS))
    return tuple(
        name
        for name in shared
        if (POP_AXIS[name].dynamics, POP_AXIS[name].row)
        != (EDM_AXIS[name].dynamics, EDM_AXIS[name].row)
    )


def _all_labels() -> tuple[SectionLabel, ...]:
    return (*POP_AXIS.values(), *EDM_AXIS.values(), *SIX_ROW_ONLY.values())


def _merged_terms() -> Mapping[str, tuple[int, ...]]:
    """``DYNAMICS_TERMS`` ∪ 이 파일의 축들. 같은 말이 다른 대역이면 **여기서 깨진다.**

    복제한 어휘는 조용히 갈라진다. 갈라지는 순간을 import 시각의 예외로 바꾸면 조용하지
    않다 — ``section_intent`` 가 비공개 이름을 들여오며 적은 것과 같은 선택이다
    (「복제는 조용히 갈라지고, 들여오기는 시끄럽게 깨진다」).
    """
    merged: dict[str, tuple[int, ...]] = dict(DYNAMICS_TERMS)
    for label in _all_labels():
        for term in label.terms:
            existing = merged.get(term)
            if existing is not None and existing != label.dynamics:
                raise RuntimeError(
                    f"section term {term!r} carries two different dynamics bands: "
                    f"{existing} and {label.dynamics}"
                )
            merged[term] = label.dynamics
    return merged


#: 구간 라벨이 대조하는 말 전부 → 그 말의 세기 대역. 빈 튜플은 「정본이 세기를 주지
#: 않았다」이고 「어휘에 없다」와 다르다.
SECTION_TERMS: Mapping[str, tuple[int, ...]] = _merged_terms()


def _row_terms() -> Mapping[str, tuple[str, ...]]:
    """§6 행 → 그 행을 부르는 말 전부. ``section_intent`` 가 밝기를 붙여 쓴다."""
    rows: dict[str, list[str]] = {}
    for label in _all_labels():
        if label.row is None:
            continue
        bucket = rows.setdefault(label.row, [])
        for term in label.terms:
            if term not in bucket:
                bucket.append(term)
    return {row: tuple(terms) for row, terms in rows.items()}


ROW_TERMS: Mapping[str, tuple[str, ...]] = _row_terms()


def _specific(matched: frozenset[str]) -> frozenset[str]:
    """다른 걸린 말의 **진부분 문자열**인 말을 뺀다 — 라벨은 최장 일치다.

    ``Post-Chorus`` 에는 ``post-chorus`` 와 ``chorus`` 가 둘 다 걸린다. ``-`` 가
    ``matching._WORD`` 가 아니라서 경계 판정이 둘 다 통과시키기 때문이다. 라벨 하나는
    구간 하나를 이름하므로 합집합은 틀린 답이다 — 후렴 대역 (4,5) 이 후주에 섞인다.

    **합쳐야 하는 경우는 남는다.** ``Build to Chorus`` 의 ``build`` 와 ``chorus`` 는 서로
    부분 문자열이 아니므로 둘 다 살아남고, 그러면 ``intent_for_label`` 이 행 둘을 보고
    ``None`` 을 답한다 — 「행이 둘 걸리는 이름은 반쯤 제약이 아니라 제약 없음」이라는
    기존 규율이 그대로 산다.

    한글은 이 문제가 없다(``프리코러스`` 안의 ``코러스`` 는 앞 글자가 단어 문자라 애초에
    안 걸린다). 그래도 술어는 문자열로만 판정한다 — 언어를 조건으로 가르면 그 조건이
    다음 언어에서 다시 틀린다.
    """
    return frozenset(
        term for term in matched if not any(term != other and term in other for other in matched)
    )


def matched_section_terms(label: str) -> frozenset[str]:
    """이 라벨이 담고 있는 구간 어휘 — 최장 일치로 걸러낸 것."""
    text = _normalise(label)
    return _specific(frozenset(term for term in SECTION_TERMS if _found(term, text)))


def resolve_section_dynamics(label: str) -> tuple[int, ...] | None:
    """이 구간 라벨의 세기 대역, 없으면 ``None``.

    ``None`` 은 두 갈래를 한 값으로 답한다 — 어휘에 없는 이름(``Nonsense``)과, 어휘에는
    있지만 정본이 세기를 주지 않은 이름(``Solo``)이다. 둘 다 「이 구간의 세기를 기계가
    못 정한다」이고 처방이 같다(운영자가 ``explicit_dynamics`` 로 준다). 갈래를 나누려면
    ``songcue`` 의 사유 어휘를 늘려야 하고, 그것은 이 카드의 범위가 아니다 — 대신 두
    갈래가 다른 사실이라는 것을 :data:`SECTION_TERMS` 의 빈 튜플이 보존한다.
    """
    levels: set[int] = set()
    for term in matched_section_terms(label):
        levels.update(SECTION_TERMS[term])
    return tuple(sorted(levels)) if levels else None
