"""t360 — 한 곡 안에서 룩을 이름 알파벳 순으로 고르지 않는다.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` §6(구간별 조명 의도) ·
§6.1(액센트는 한 번에 하나) · §6.3(색은 적게) · §7(곡 안 반복은 미덕) ·
§12 항목 2(고칠 것: 「룩을 이름 알파벳 순으로 고른다」).

**고치기 전에 실측한 것**(2026-09-12, main ``7d78876``). 5구간 EDM 입력
(Intro·Build·Chorus·Drop·Chorus)의 뒤 세 구간이 전부 ``edm-drop-acid`` 하나였다 —
후렴도 드롭도 다음 후렴도 같은 그림이다. 원인은 ``busking.looks_for_genre`` 의
``(dynamics, look_id)`` 전순서와 그 선두를 집는 선택 계층이고, 그래서 같은 세기 안에서는
**룩 id 의 사전순**이 무대를 정했다.

**이 파일이 재는 두 축과, 그 둘이 부딪히지 않는 이유.**

- 라벨이 §6 행을 가리키면 그 행의 밝기 구간이 후보를 가른다(§6).
- 라벨이 **바뀌면** 앞 큐와 가장 대비되는 룩을 고른다(§12 항목 2 · §8).
- 라벨이 **되풀이되면** 1회차의 룩이 되돌아온다(§7 [HARD]). 회차 사이의 변화는 룩
  교체가 아니라 사다리가 만든다(§7.1, 카드 t355).

세 번째 줄이 없으면 두 번째 줄이 t355 를 방향만 바꿔 되돌린다 — 후렴 2회차가 1회차를
피해 다른 룩으로 갈아타고, 「돌아와야 하는 것이 사라진다」.

**이 파일이 재기만 하고 안 고쳤던 것은 카드 t361 이 닫았다.** §6.1 [HARD]「한 큐에 하나만」
은 이제 지켜진다 — 감독이 갈래를 정했고(2026-09-12: 밝기만 누적), 사다리가 액센트를 쌓지
않고 갈아탄다. 아래 :class:`TestTheOneAccentRuleNowHolds` 가 그 자리를 계속 지킨다.
"""

from __future__ import annotations

from fractions import Fraction

from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue, Look
from server.looks.section_intent import (
    SECTION_INTENTS,
    contrast,
    intent_for_label,
    sorted_candidates,
)
from server.looks.section_vocab import SECTION_TERMS

#: 정본 §12 항목 2 가 실측 근거로 인용한 그 입력.
_MEASURED_FIVE_SECTIONS = (
    ("Intro", "0:00"),
    ("Build", "0:30"),
    ("Chorus", "1:00"),
    ("Drop", "1:30"),
    ("Chorus", "2:00"),
)


class TestTheLabelSteersSelection:
    """정본 §6 — 구간 이름이 세기뿐 아니라 **의도**를 정한다."""

    def test_two_rows_named_at_once_is_no_constraint_rather_than_half_of_one(self):
        """행이 둘 걸리는 이름은 ``None`` — ``resolve_genre`` 가 장르 둘을 접는 규율."""
        assert intent_for_label("Build to Chorus") is None
        assert intent_for_label("Build") is not None
        assert intent_for_label("Chorus") is not None

    def test_every_row_term_comes_from_the_shared_section_vocabulary(self):
        """§6 행의 말은 한 벌뿐이다 — 여기서 새 말을 만들면 어휘가 갈라진다.

        표가 ``matching.DYNAMICS_TERMS`` 에서 ``section_vocab.SECTION_TERMS`` 로 옮겨간
        것은 카드 t362 다. ``SECTION_TERMS`` 는 ``DYNAMICS_TERMS`` 를 **포함**하므로
        이 단언은 넓어진 것이 아니라 같은 자리를 지킨다 — 새 말은 반드시 축 선언
        (``POP_AXIS``/``EDM_AXIS``/``SIX_ROW_ONLY``)을 거쳐야 한다.
        """
        for _row, _brightness, terms in SECTION_INTENTS:
            assert terms
            for term in terms:
                assert term in SECTION_TERMS, term

    def test_the_six_rows_are_exactly_the_standard_rows_that_carry_a_percentage(self):
        """§6 표의 열 행 중 **밝기 숫자를 가진 여섯**만 행이 된다 (카드 t362).

        고치기 전엔 넷이었다. post-chorus(60~75%)와 breakdown · bridge(20~35%)가
        더해져 여섯이고, 나머지 넷은 숫자가 없어서 빠진다 — solo(「솔로이스트만 강조」),
        outro(「리셋 큐 · 디밍한 베이스」), 텐션(자리이지 라벨이 아니다), 마지막 drop
        (「마지막」을 회차로 유도하는 규칙이 정본에 없다).
        """
        assert [row for row, _b, _t in SECTION_INTENTS] == [
            "intro",
            "verse",
            "pre-chorus · build",
            "chorus · drop",
            "post-chorus",
            "breakdown · bridge",
        ]
        assert [b for _r, b, _t in SECTION_INTENTS] == [
            (20, 40),
            (25, 50),
            (40, 55),
            (80, 100),
            (60, 75),
            (20, 35),
        ]

    def test_the_six_row_divergence_from_the_old_order_is_exactly_one(self):
        """전수 실측 — §6 의도가 사전순 선두를 바꾸는 자리를 라이브러리 전체에서 센다.

        「라벨을 걸어도 거의 아무것도 안 바뀐다」와 「다 바뀐다」는 둘 다 주장이다. 네
        장르 × §6 행을 전수로 돌려 실제 개수를 센다. 룩이 늘면 이 수가 움직이고,
        움직이면 그때 다시 읽어야 한다.

        카드 t362 로 행이 넷에서 여섯이 됐고, 이 수는 **그대로 하나**다(재측정).
        새 두 행(post-chorus · breakdown · bridge)은 어느 장르에서도 사전순 선두를
        바꾸지 않는다 — 그 대역의 후보들이 §6 구간 밖이라 `fits` 가 전부 1로 같고,
        같으면 꼬리의 기존 전순서가 그대로 답이기 때문이다.
        """
        library = load_library_from_dir()
        genres = sorted({look.genre for look in library.looks})
        diverged = []
        for genre in genres:
            for row, _brightness, terms in SECTION_INTENTS:
                intent = intent_for_label(terms[0])
                band = SECTION_TERMS[terms[0]]
                matches = tuple(
                    look for look in library.looks if look.genre == genre and look.dynamics in band
                )
                if not matches:
                    continue
                before = sorted_candidates(matches, previous=None, intent=None)[0]
                after = sorted_candidates(matches, previous=None, intent=intent)[0]
                if before.look_id != after.look_id:
                    diverged.append((genre, row, before.look_id, after.look_id))

        assert diverged == [("rock", "verse", "rock-verse-amber-grit", "rock-verse-side")]


class TestTheContrastDefinition:
    """대비는 자료가 실제로 드는 세 축의 합이다 — 색 · 밝기 · 역할."""

    def test_the_three_axes_sum_to_the_reported_contrast(self):
        """실제 라이브러리 값으로 셈을 전개한다. 분수라 자릿수 반올림이 없다."""
        library = load_library_from_dir()
        # 역할 수는 2026-09-12 카드 t359 로 셋 다 하나씩 늘었다 — 움직이는 룩이
        # `무버` 를 함께 들기 때문이다. 색·밝기 축은 그대로이고 역할 축만 움직였다.
        # 2026-09-13 카드 t379 가 리그 커버리지(워시·헤이즈 미매핑)를 메우면서
        # crimson·beams 의 역할 수가 다시 늘었다 — crimson 은 워시 +1(7→8),
        # beams 는 헤이즈 +1(4→5). acid 는 안 바뀐다.
        acid = library.by_id("edm-drop-acid")  # D90 rgb(72,100,0) 역할 5
        crimson = library.by_id("edm-drop-crimson")  # D100 rgb(100,0,15) 역할 8
        beams = library.by_id("edm-drop-beams")  # D100 rgb(70,88,100) 역할 5

        # 색 (|72-100| + |100-0| + |0-15|) / 300 = 143/300
        # 밝기 |90-100| / 100 = 30/300
        # 역할 1 - 5/8 = 3/8   (교집합 5 — acid 의 역할이 전부 crimson 에 있다)
        assert contrast(acid, crimson) == Fraction(143 + 30, 300) + Fraction(3, 8)
        assert contrast(acid, crimson) == Fraction(571, 600)
        # 색 (2 + 12 + 100)/300 · 밝기 30/300 · 역할 1 - 4/6 = 1/3 = 100/300
        assert contrast(acid, beams) == Fraction(114 + 30 + 100, 300) == Fraction(61, 75)
        # 대칭이고, 자기 자신과는 0 이다.
        assert contrast(crimson, acid) == contrast(acid, crimson)
        assert contrast(acid, acid) == Fraction(0)

    def test_an_axis_the_data_does_not_carry_contributes_nothing(self):
        """못 잰 축은 0 — 없는 값을 기본값으로 지어내지 않는다."""
        colourless = Look(
            look_id="colourless",
            display_name="colourless",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(AttributeValue("Dimmer", 100),),
        )
        other = Look(
            look_id="other",
            display_name="other",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(AttributeValue("Dimmer", 40),),
        )
        # 밝기 축만 값을 낸다: |100-40| / 100. 색도 역할도 0.
        assert contrast(colourless, other) == Fraction(60, 100)
