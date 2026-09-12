"""구간이 정하는 페이드 시간 — 정본 §9(페이드) 와 §6 표의 「빔·움직임」 칸.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` 이고, 이 모듈이 닫는 것은
그 문서 §12 항목 7 의 앞 절반이다: **큐 값에 페이드가 없다.**

**고치기 전에 실측한 것**(2026-09-12, main ``980a1db``):
``grep -rn "CueFade" server/looks/songcue.py`` 가 **0건**. 곡→큐 경로가 내는 모든 큐가
하드 스냅이었다 — 아웃트로도, 드롭도, 벌스도 전부 같은 0초.

## 정본이 실제로 준 숫자는 둘뿐이다

§9 는 페이드에 대해 딱 두 값을 적는다 — **부드러운 전환 2~4초**, **극적인 컷 0.2초**.
§6 표는 행마다 페이드 숫자를 주지 않고 말로 적는다(「짧게」·「짧은 버스트」·「느린 페이드
1회」). 그래서 이 표는 **세 값**을 넘지 않는다:

* :data:`FADE_CUT` — §9 의 극적인 컷. §6 「chorus · drop」 행이 「80~100%를 **짧게**」와
  「**짧은** 버스트」로 같은 말을 한다.
* :data:`FADE_SLOW` — §9 대역 2~4초의 **느린 끝**. 정본이 「느린」이라고 **이름 붙인**
  구간은 outro 하나다(§6 outro 행 「느린 페이드 1회」).
* :data:`FADE_SMOOTH` — 그 대역의 **가까운 끝**. §6 이 페이드 숫자도 「느린」이라는
  말도 주지 않은 나머지 행들이 여기로 온다.

**2 와 4 사이를 행마다 다르게 고르지 않는다.** 정본이 행별 값을 주지 않았으므로 그것은
지어내는 일이다. 갈래는 정본이 말로 가른 자리(「짧게」 · 「느린」)에서만 갈린다.

## outro 는 §6 **행**이 아니다 — 그런데 페이드는 있다

``section_intent`` 의 ``SectionIntent`` 는 §6 표의 **밝기 퍼센트**를 든 행만 갖는다.
outro 행은 밝기 칸에 퍼센트 대신 「디밍한 베이스」라고 적혀 있어 거기 없다. 그러나 같은
행의 스트로브 칸 옆에 「느린 페이드 1회」가 **적혀 있다** — 페이드는 정본이 그 행에 준
것이다. 그래서 이 표의 키는 §6 행 여섯 + outro 한 줄이고, outro 의 어휘는
``section_vocab`` 에서 **읽어 온다**(적지 않는다 — 적으면 어휘가 두 벌이 된다).

## 행이 둘 걸리면 아무 말도 안 한다

``intent_for_label`` 과 **같은 규율**이다. 「Build to Chorus」처럼 두 줄이 걸리는 이름은
반쯤 제약이 아니라 제약 없음이고, 그때 페이드는 ``None`` 이다. ``None`` 은 곧
**페이드 없음 = 고치기 전의 하드 스냅**이고, 그 갈래의 콘솔 명령은 바이트 동일하다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.looks.section_vocab import (
    EDM_AXIS,
    POP_AXIS,
    ROW_BREAKDOWN,
    ROW_BUILD,
    ROW_CHORUS,
    ROW_INTRO,
    ROW_POST_CHORUS,
    ROW_TERMS,
    ROW_VERSE,
    matched_section_terms,
)

__all__ = [
    "FADE_CUT",
    "FADE_SLOW",
    "FADE_SMOOTH",
    "LINE_OUTRO",
    "SECTION_FADES",
    "SectionFade",
    "fade_for_label",
]

#: §9 「극적인 컷 **0.2초**」.
FADE_CUT = 0.2
#: §9 「부드러운 전환 **2~4초**」의 가까운 끝.
FADE_SMOOTH = 2.0
#: 같은 대역의 느린 끝 — 정본이 「느린」이라고 이름 붙인 자리에만 쓴다.
FADE_SLOW = 4.0

#: §6 표의 outro 행. §6 **행**이면서 :class:`~server.looks.section_intent.SectionIntent`
#: 의 행은 **아니다** — 밝기 퍼센트가 없어서 그쪽 표에 못 들어간다. 이름을 따로 두는
#: 것은 그 비대칭을 숨기지 않기 위해서다.
LINE_OUTRO = "outro"


@dataclass(frozen=True)
class SectionFade:
    """이 구간이 정하는 페이드 — 초, 그것을 부른 §6/§9 줄, 그리고 **출처 문면**.

    ``source`` 를 값과 함께 드는 것은 이 저장소의 규율이다: 숫자 하나가 정본의 어느
    문장에서 왔는지가 값 옆에 없으면, 다음 사람은 그 숫자를 고쳐도 되는지 알 수 없다.
    """

    line: str
    seconds: float
    source: str


#: §6 행 → (초, 출처). 행을 부르는 **말**은 여기 없다 — ``section_vocab.ROW_TERMS`` 가
#: 든다(``section_intent`` 가 밝기에 대해 하는 것과 같은 분업).
#:
#: 매핑 리터럴이 아니라 튜플인 것은 ``section_intent._ROW_BRIGHTNESS`` 와 같은 규율이고,
#: 순서도 거기와 같다 — **정본 §6 표의 읽기 순서**다.
_ROW_FADE: tuple[tuple[str, float, str], ...] = (
    (ROW_INTRO, FADE_SMOOTH, "§9 「부드러운 전환 2~4초」 — §6 intro 행은 페이드를 안 적는다"),
    (ROW_VERSE, FADE_SMOOTH, "§9 「부드러운 전환 2~4초」 — §6 verse 행은 페이드를 안 적는다"),
    (ROW_BUILD, FADE_SMOOTH, "§9 「부드러운 전환 2~4초」 — §6 build 행은 페이드를 안 적는다"),
    (ROW_CHORUS, FADE_CUT, "§9 「극적인 컷 0.2초」 + §6 chorus · drop 행 「짧게」·「짧은 버스트」"),
    (ROW_POST_CHORUS, FADE_SMOOTH, "§9 「부드러운 전환 2~4초」 — §6 post-chorus 행은 안 적는다"),
    (ROW_BREAKDOWN, FADE_SMOOTH, "§9 「부드러운 전환 2~4초」 — §6 breakdown 행은 안 적는다"),
)


def _outro_terms() -> tuple[str, ...]:
    """outro 를 부르는 말 — ``section_vocab`` 의 두 축에서 **읽어 온다.**

    ``coda`` 를 함께 읽는 것은 정본 §2.1 이 종결 동의어군(outro · coda · fadeout)을
    한 묶음으로 적고 ``section_vocab`` 이 그 배정을 그대로 옮겼기 때문이다. ``fadeout``
    은 뺀다 — §2.1 이 **겹쳐 붙는 라벨**이라고 명시하므로(「코러스가 페이드아웃하면 그
    구간은 chorus + fadeout 둘을 갖는다」) 독립된 페이드 주장이 아니다. 넣으면
    ``Chorus Fadeout`` 이 줄 둘을 걸어 페이드가 통째로 사라진다.
    """
    return tuple(
        dict.fromkeys(
            term
            for key in ("outro", "coda")
            for axis in (POP_AXIS, EDM_AXIS)
            if key in axis
            for term in axis[key].terms
        )
    )


#: 페이드를 정하는 줄 전부 → (초, 그 줄을 부르는 말, 출처).
SECTION_FADES: tuple[tuple[str, float, tuple[str, ...], str], ...] = (
    *((row, seconds, ROW_TERMS[row], source) for row, seconds, source in _ROW_FADE),
    (
        LINE_OUTRO,
        FADE_SLOW,
        _outro_terms(),
        "§6 outro 행 「느린 페이드 1회」 — §9 대역 2~4초의 느린 끝",
    ),
)


def fade_for_label(label: str) -> SectionFade | None:
    """이 라벨이 정하는 페이드, 없거나 줄이 둘 이상 걸리면 ``None``.

    어휘 대조는 ``section_vocab.matched_section_terms`` **하나**를 쓴다 — 정규화·조사
    처리·경계 판정·최장 일치가 전부 그 안에 있고, 여기서 다시 쓰면 같은 말이 두 곳에
    살게 된다(``section_intent._matched_terms`` 와 같은 사유).

    ``None`` 이 「페이드 없음」인 것은 우연이 아니라 선택이다: 정본이 이 라벨에 페이드를
    주지 않았으면 지어내지 않고, 그 큐는 고치기 전과 같은 하드 스냅으로 나간다.
    """
    terms = matched_section_terms(label)
    lines = tuple(
        SectionFade(line=line, seconds=seconds, source=source)
        for line, seconds, words, source in SECTION_FADES
        if terms.intersection(words)
    )
    return lines[0] if len(lines) == 1 else None
