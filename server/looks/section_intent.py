"""같은 세기 안에서 **어느** 룩인가 — 정본 §6 의 구간별 의도와 앞 큐와의 대비.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` 이고, 이 모듈이 닫는 것은
그 문서 §12 항목 2 다: **룩을 이름 알파벳 순으로 고른다.**

**고치기 전에 실측한 것**(2026-09-12, main ``7d78876``). ``busking.looks_for_genre`` 가
장르의 룩을 ``(dynamics, look_id)`` 로 줄 세우고 선택 계층이 그 앞을 집으므로, 같은 세기
안에서는 **룩 id 의 사전순**이 무대 그림을 정했다. 실측 5구간 EDM 입력
(Intro·Build·Chorus·Drop·Chorus)에서 뒤 세 구간이 전부 ``edm-drop-acid`` 하나였다 —
후렴도 드롭도 다음 후렴도 같은 그림이다.

축이 셋이고, **셋의 순서가 계약이다**(:func:`ordering_key`).

1. **같은 라벨이 되풀이되면 1회차의 룩이 되돌아온다**(§7 [HARD]: 「코러스 1에 쓴 색과
   발리후는 이후 코러스에서 되돌아와야 한다」). 가장 바깥이다 — 회차 사이의 변화는 룩
   교체가 아니라 사다리가 만든다(§7.1, 카드 t355).
2. **라벨이 의도를 정한다**(§6). 구간 이름이 §6 표의 어느 행인지 알면 그 행의 밝기
   구간이 후보를 가른다. 세기(다이내믹스)만으로는 못 하는 일이다 — 한 세기 안에 밝기가
   벌어진 룩들이 함께 산다(실측: rock 의 vocal 대역이 D52 와 D48 로 갈린다).
3. **라벨이 바뀌면 앞 큐가 나머지를 정한다.** 의도가 같은 값을 주는 후보들 사이에서는
   **앞 큐와 가장 대비되는** 룩을 고른다. 정본 §8 「피크와 밸리로 생각하라」와 edm
   라이브러리 머리말의 「드롭은 빌드와 다른 방으로 느껴져야 한다」가 같은 축이다.

1번과 3번이 부딪히지 않는 것은 **적용 지점이 다르기** 때문이다 — 반복은 같은 라벨,
대비는 다른 라벨. 3번을 1번 위에 두면 t355 가 되살린 반복 후렴이 방향만 바꿔 다시
사라진다(곡 B 의 후렴 2회차가 1회차를 피해 갈아탄다).

**거르지 않고 줄 세운다.** 두 축 모두 후보를 목록에서 빼지 않고 뒤로 보낸다 —
``matching`` 머리의 규율(「좁은 필터는 좋은 룩을 조용히 버린다」)과
``songcue._ranked_against_history`` 의 형상이 같다. 그래야 §6 행에 맞는 룩이 이 리그에
하나도 안 묶여도 큐가 사라지지 않는다.

**§6 표에서 오늘 걸 수 있는 칸은 밝기 하나다.** 나머지 세 칸을 왜 안 거는지 적어 둔다 —
안 한 것을 못 한 것처럼 적지 않기 위해서다.

- **색**: §6 의 색 칸은 숫자가 아니라 계열 이름이다(「청·자 계열」·「웜 계열도 가능」).
  도(度) 구간으로 옮기려면 정본에 없는 숫자를 지어내야 한다. §6.3 의 「동시에 최대 2색」
  은 **한 큐가 동시에 내는 색 수**의 상한인데, 룩 하나는 RGB 삼원색 한 벌만 들고 있어
  원리적으로 이 상한을 어길 수 없다 — 걸 자리가 룩 선택이 아니다.
- **빔·움직임**: 대역은 이미 ``movement.band_for_dynamics`` 가 다이내믹스에서 뽑는다.
  여기서 라벨로 다시 정하면 어휘가 두 벌이 된다. 그리고 v1 라이브러리는 움직임 선언이
  **0건**이므로(실측: 네 장르 34룩 전부 ``movement: ()``) 오늘 걸어도 재지 못한다.
- **스트로브**: 역할 어휘에 스트로브가 없다(정본 §12 항목 6, 감독 결정 선행 — 카드 t356).

**§6 행이 없는 라벨은 여전히 남는다 — 다만 줄었다**(카드 t362). 어휘가
``section_vocab`` 으로 넓어지면서 post-chorus · breakdown · bridge 가 행을 갖게 됐고,
행은 **넷에서 여섯**이 됐다. 남은 셋은 §6 이 그 행의 밝기 칸에 **퍼센트를 안 적어서**
남는 것이다:

- **solo**: 밝기 칸이 「솔로이스트만 강조」다 — §6.2 의 역할 문장이지 숫자가 아니다.
- **outro**: 「리셋 큐」 · 「디밍한 베이스」 — 세기는 읽히지만(``section_vocab`` 이 (1,2)
  로 배정한다) 밝기 구간이 없다.
- **텐션 · 마지막 drop**: 텐션은 「드롭 직전 마지막 마디」라는 **자리**이지 §2 어휘의
  라벨이 아니고, 「마지막」을 회차로 유도하는 것은 정본에 없는 규칙을 만드는 일이다.

그런 라벨은 :func:`intent_for_label` 이 ``None`` 을 답하고, 선택은 대비 축과 기존
전순서로만 간다 — **행을 지어내지 않는다.**
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from server.looks.schema import Look
from server.looks.section_vocab import (
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
    "SECTION_INTENTS",
    "SectionIntent",
    "brightness_fits",
    "contrast",
    "intent_for_label",
    "ordering_key",
    "sorted_candidates",
]

_DIMMER = "Dimmer"
_COLOUR_CHANNELS: tuple[str, ...] = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

#: 이 저장소의 속성 값은 퍼센트다(라이브러리 저작 규칙). 대비의 각 축을 0~1 로 맞추는
#: 나눗셈의 분모이고, 상수가 아니라 그 규칙에서 나온 값이다.
_PERCENT_SPAN = 100


@dataclass(frozen=True)
class SectionIntent:
    """정본 §6 표의 한 **행** — 오늘 기계로 걸 수 있는 칸만 값으로 들었다.

    ``row`` 는 그 행의 이름이고 보고와 시험이 인용한다. ``brightness`` 는 §6 이 그
    행에 직접 준 퍼센트 구간이며 **닫힌 구간**이다(표의 「20~40%」는 양끝을 포함한다).
    """

    row: str
    brightness: tuple[int, int]


#: 정본 §6 표의 행 → 그 행이 주는 밝기 구간. **이 파일이 드는 것은 밝기뿐이고**, 그 행을
#: 부르는 말은 ``section_vocab.ROW_TERMS`` 가 든다 — 소비자가 다르기 때문이다(세기는
#: ``songcue`` 가, 밝기는 이 파일이 읽는다). 여기서 말을 다시 적으면 어휘가 두 벌이 된다.
#:
#: 매핑 리터럴이 아니라 튜플인 것은 ``movement._BAND_RANGES`` 와 같은 규율이고, 여기서는
#: 순서에도 뜻이 있다 — **정본 §6 표의 읽기 순서 그대로**다. 한때 이 자리에 「약→강」도
#: 함께 적혀 있었는데, 행이 넷일 때는 두 순서가 우연히 같았을 뿐이다. post-chorus(60~75)
#: 와 breakdown(20~35)이 들어오면서 갈라졌고, 갈라진 쪽에서 정본을 따른다.
#: (판정에는 순서가 안 쓰인다 — :func:`intent_for_label` 은 행이 **정확히 하나** 걸릴
#: 때만 답하므로 앞뒤가 결과를 바꾸지 않는다. 순서는 읽는 사람을 위한 것이다.)
#:
#: **(4,5) 대역의 말을 전부 싣지 않았다.** ``엔딩``·``피날레``·``클라이맥스``·``절정``·
#: ``최고조``·``고조`` 는 세기로는 코러스·드롭과 같은 대역이지만 §6 은 「chorus · drop」
#: 행과 「마지막 drop」 행을 **따로** 두고, 어느 말이 어느 행인지 정본이 정해 주지
#: 않는다. 「마지막」을 회차로 유도하는 것은 정본에 없는 규칙을 만드는 일이므로 하지
#: 않는다 — 그 말들은 §6 행이 없는 라벨로 남고, 대비 축이 그 구간을 고른다.
_ROW_BRIGHTNESS: tuple[tuple[str, tuple[int, int]], ...] = (
    (ROW_INTRO, (20, 40)),
    (ROW_VERSE, (25, 50)),
    (ROW_BUILD, (40, 55)),
    (ROW_CHORUS, (80, 100)),
    (ROW_POST_CHORUS, (60, 75)),
    (ROW_BREAKDOWN, (20, 35)),
)

#: 행 → (밝기, 그 행을 부르는 말). 말은 ``section_vocab`` 에서만 온다.
SECTION_INTENTS: tuple[tuple[str, tuple[int, int], tuple[str, ...]], ...] = tuple(
    (row, brightness, ROW_TERMS[row]) for row, brightness in _ROW_BRIGHTNESS
)


def _matched_terms(label: str) -> frozenset[str]:
    """이 라벨이 담고 있는 구간 어휘 — ``section_vocab`` 의 판정 하나를 그대로 쓴다.

    **어휘도 술어도 새로 만들지 않는다.** 표는 ``section_vocab.SECTION_TERMS`` 하나이고,
    대조는 ``section_vocab.matched_section_terms`` 하나다(정규화·조사 처리·경계 판정에
    더해 **최장 일치**까지 전부 그 안에 있다). 여기서 다시 쓰면 같은 말이 두 곳에 살고,
    그 순간 둘은 갈라지기 시작한다 — ``busking.py`` 가 dedupe 문자열을 만들지 않고
    ``instantiate._values_line`` 를 그대로 들여오는 것과 같은 규율이다.

    한때 이 함수가 ``matching`` 의 비공개 이름을 직접 들여왔다. 그 자리가
    ``section_vocab`` 으로 옮겨간 것은 어휘가 넓어져서가 아니라 **판정 규칙이 갈렸기**
    때문이다: 운영자 질의는 합집합, 구간 라벨은 최장 일치다(``section_vocab`` 독스트링
    「왜 이 파일인가」). 들여오기 자체는 그대로 한 겹 아래로 내려갔을 뿐이다.
    """
    return matched_section_terms(label)


def intent_for_label(label: str) -> SectionIntent | None:
    """이 라벨이 가리키는 §6 행, 없거나 둘 이상이면 ``None``.

    행이 둘 이상 걸리는 이름(「Build to Chorus」)은 **반쯤 제약이 아니라 제약 없음**이다 —
    ``matching.resolve_genre`` 가 장르 두 개를 ``None`` 으로 접는 것과 같은 규율이다.
    모호한 축은 아무 말도 하지 않고, 판정은 다른 축이 한다.
    """
    terms = _matched_terms(label)
    rows = tuple(
        SectionIntent(row=row, brightness=brightness)
        for row, brightness, words in SECTION_INTENTS
        if terms.intersection(words)
    )
    return rows[0] if len(rows) == 1 else None


def brightness_fits(intent: SectionIntent, look: Look) -> bool:
    """이 룩의 밝기가 그 행의 §6 구간 안에 있는가. 밝기 값이 없으면 ``False``.

    없는 값을 「일단 맞다」로 읽지 않는다 — 못 잰 것을 통과시키면 그 룩이 의도와
    무관하게 앞으로 온다. 라이브러리 34룩은 전부 ``Dimmer`` 를 싣고 있으므로(실측)
    이 갈래는 오늘 안 걸리지만, 안 걸리는 것과 없는 것은 다르다.
    """
    dimmer = _attribute(look, _DIMMER)
    if dimmer is None:
        return False
    low, high = intent.brightness
    return low <= dimmer <= high


def contrast(previous: Look, candidate: Look) -> Fraction:
    """두 룩이 무대에서 얼마나 다른 그림인가 — 0(같다) ~ 3(모든 축이 정반대).

    **정의는 자료가 실제로 들고 있는 것에서만 만든다.** 룩이 드는 것은 속성 값과 역할
    뿐이고(``server/looks/schema.py`` ``Look``), 그중 정본 §6 이 무대 그림의 축으로
    이름 붙인 것이 셋이다 — 색(§6 색 칸) · 밝기(§6 밝기 칸) · 어느 자리가 켜지는가
    (§6.2 「기구마다 역할을 부여하라, 전부가 전부를 하는 것이 아니다」). 그래서 축도
    셋이고, 각각 0~1 이다.

    - **색**: RGB 세 채널의 절대차 합 ÷ 300. 채널이 하나라도 빠진 쪽이 있으면 0 이다.
    - **밝기**: ``Dimmer`` 절대차 ÷ 100. 한쪽이라도 없으면 0 이다.
    - **역할**: 자카드 거리 ``1 - |A∩B| / |A∪B|``. 둘 다 역할이 없으면 0 이다.

    **가중치를 두지 않는다.** 정본은 세 칸을 나란히 두고 어느 칸이 더 중하다고 적지
    않았다 — 없는 숫자를 만드는 대신 셋을 같은 무게로 더한다. 축을 달리 재고 싶으면
    그 근거를 정본에서 먼저 찾아야 한다.

    **못 잰 축은 0 이다**(대비 없음이 아니라 근거 없음). 없는 값을 기본값으로 지어내면
    그 룩이 근거 없이 앞으로 오는데, 그 방향의 실패가 이 저장소가 계속 거절하는 것이다.

    :class:`~fractions.Fraction` 로 셈하는 것은 정확한 전순서 때문이다. 부동소수 합은
    같아야 할 두 값을 1e-16 만큼 갈라 놓을 수 있고, 그러면 「대비가 같으면 사전순」이라는
    타이브레이크가 조용히 안 걸린다.
    """
    return (
        _colour_distance(previous, candidate)
        + _brightness_distance(previous, candidate)
        + _role_distance(previous, candidate)
    )


# @MX:ANCHOR: [AUTO] 같은 세기 안에서 어느 룩을 고르는지의 **유일한** 판정 자리.
#   축의 순서가 계약이다 — 되돌아옴 → 의도 → 대비 → 기존 전순서.
# @MX:REASON: 카드 셋이 이 한 줄 위에 겹쳐 산다. 되돌아옴을 내리면 t355 가 되살린 반복
#   후렴이 다시 갈아치워지고, 꼬리의 `(dynamics, look_id)` 를 빼면 t358 의 무기억 바이트
#   동일 성질이 깨진다. 축을 더하거나 재배열하려면 세 카드의 실측 단정을 함께 읽어야 한다
#   (`server/tests/test_songcue_section_intent.py` · `test_songcue_ladder.py` ·
#   `test_songcue_cross_song.py`).
def ordering_key(
    look: Look,
    *,
    previous: Look | None,
    intent: SectionIntent | None,
    returning: Look | None = None,
) -> tuple[int, int, Fraction, int, str]:
    """한 후보의 정렬 키 — 되돌아옴 → 의도 → 대비 → 기존 전순서.

    **되돌아옴이 가장 앞이다**(정본 §7, [HARD]): 「코러스 1에 쓴 색과 발리후는 이후
    코러스에서 되돌아와야 한다.」 그러므로 같은 라벨의 2회차 이후는 대비의 대상이
    아니다 — 대비로 갈아치우면 t355 가 고친 결함(돌아와야 하는 것이 사라진다)이 방향만
    바꿔 되돌아온다. 회차 사이의 변화는 룩 교체가 아니라 사다리가 만든다(§7.1
    ``songcue._ladder_start``).

    **대비는 라벨이 바뀔 때의 축이다.** 정본 §12 항목 2 의 「앞 큐와 가장 대비되는
    룩」과 §8 「피크와 밸리로 생각하라」는 서로 다른 구간 사이의 말이고, edm 라이브러리
    머리말의 「드롭은 빌드와 다른 방으로 느껴져야 한다」도 같다. 곡 안 반복이 미덕이라는
    §7 과 충돌하지 않는 것은 **적용 지점이 다르기** 때문이다: 반복은 같은 라벨,
    대비는 다른 라벨.

    의도가 대비보다 **앞**인 것도 문면이다(§12 항목 2: 「§6 의 구간별 의도를 명시
    사상으로 걸고, **같은 세기 안에서는** 앞 큐와 가장 대비되는 룩을 고른다」). 의도는
    그 구간이 무엇이어야 하는가이고, 대비는 그 안에서의 선택이다.

    꼬리의 ``(dynamics, look_id)`` 는 ``busking.looks_for_genre`` 의 전순서 그대로다 —
    앞의 세 축이 아무 말도 안 하는 입력(되돌아올 룩 없음 + §6 행 없음 + 앞 큐 없음)에서
    이 키는 그 순서로 **퇴화**하고, 그때 나가는 명령은 고치기 전과 바이트 동일하다.
    """
    comes_back = 0 if returning is not None and returning.look_id == look.look_id else 1
    fits = 0 if intent is not None and brightness_fits(intent, look) else 1
    gap = contrast(previous, look) if previous is not None else Fraction(0)
    return (comes_back, fits, -gap, look.dynamics, look.look_id)


def _colour_distance(previous: Look, candidate: Look) -> Fraction:
    span = _PERCENT_SPAN * len(_COLOUR_CHANNELS)
    total = 0
    for channel in _COLOUR_CHANNELS:
        before = _attribute(previous, channel)
        after = _attribute(candidate, channel)
        if before is None or after is None:
            return Fraction(0)
        total += abs(before - after)
    return Fraction(total) / span


def _brightness_distance(previous: Look, candidate: Look) -> Fraction:
    before = _attribute(previous, _DIMMER)
    after = _attribute(candidate, _DIMMER)
    if before is None or after is None:
        return Fraction(0)
    return Fraction(abs(before - after)) / _PERCENT_SPAN


def _role_distance(previous: Look, candidate: Look) -> Fraction:
    before = frozenset(previous.roles)
    after = frozenset(candidate.roles)
    union = before | after
    if not union:
        return Fraction(0)
    return Fraction(1) - Fraction(len(before & after), len(union))


def _attribute(look: Look, name: str) -> Fraction | None:
    """이 룩의 그 속성 값, 없으면 ``None``. 문자열을 거쳐 정확한 분수로 옮긴다.

    ``Fraction(0.1)`` 은 이진 근사를 그대로 가져오지만 ``Fraction("0.1")`` 은 1/10 이다.
    라이브러리 값은 대부분 정수이고, 소수가 섞여도 적힌 대로 셈하는 쪽이 옳다.
    """
    for value in look.attributes:
        if value.name == name:
            return Fraction(str(value.value))
    return None


def sorted_candidates(
    candidates: Sequence[Look],
    *,
    previous: Look | None,
    intent: SectionIntent | None,
    returning: Look | None = None,
) -> tuple[Look, ...]:
    """후보를 되돌아옴 → 의도 → 대비 → 전순서로 줄 세운다. **하나도 빼지 않는다.**"""
    return tuple(
        sorted(
            candidates,
            key=lambda look: ordering_key(
                look, previous=previous, intent=intent, returning=returning
            ),
        )
    )
