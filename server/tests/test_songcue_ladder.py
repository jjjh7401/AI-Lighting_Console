"""t355 — 사라지는 후렴을 되살린다: 구간 세 필드 + 아껴두기 사다리.

정본은 `docs/proposals/song-structure-lighting-standard.md` (origin/main `d9e9fbe`)
§3(라벨·회차·변형) · §7(곡 안 반복은 미덕) · §7.1(아껴두기 사다리) · §12 항목 3(고칠 것).

**고치기 전에 실측한 것**(2026-09-11, main `d9e9fbe`): 5구간 EDM 입력이 큐 3장이 됐다.
후렴이 드롭과 값 라인이 같아 `VALUE_LINE_COLLISION` 으로 **버려졌기** 때문이다. 정본 §7 은
곡 안의 반복을 규범으로 못박는다 — 되돌아와야 하는 룩을 지우는 것이 결함이었다.

**이 파일이 재지 않는 것**도 적는다(고쳐 적음, 카드 t378). 정본 §7.1 표의
「무빙 포지션 전환」은 여전히 이 사다리의 칸이 아니다 — v1 은 이제 movement 를
내지만(카드 t357), 그 통로는 구간마다 하나를 고르는 별도 층(``_movement_carrier``)
이지 반복 회차가 쌓는 사다리가 아니다. 「블라인더/백색 플래시」와 「스트로브」는
**이제 이 사다리의 칸이다** — 카드 t356 이 역할 어휘를 연 뒤 카드 t378 이 실었다.
그 칸들의 실측은 `test_songcue_accent_fixture.py` 가 든다(이 파일은 밝기 히트와
빔(줌·아이리스) 좁힘, 그리고 블라인더가 값 라인에 미치는 무영향만 잰다).
"""

from __future__ import annotations

from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    VARIANT_PRIME,
    parse_sections,
)

_MEASURED_FIVE_SECTIONS = (
    ("Intro", "0:00"),
    ("Build", "0:30"),
    ("Chorus", "1:00"),
    ("Drop", "1:30"),
    ("Chorus", "2:00"),
)


class TestTheThreeFields:
    """정본 §3 — 구간 하나는 라벨 + 회차 + 변형 표시로 적는다."""

    def test_instance_counts_per_label_and_the_prime_marks_a_variant(self):
        sections = parse_sections(
            (
                ("Chorus", "0:00"),
                ("Verse", "0:30"),
                ("Chorus", "1:00"),
                ("Chorus" + VARIANT_PRIME, "1:30"),
            )
        )

        assert [section.label for section in sections] == [
            "Chorus",
            "Verse",
            "Chorus",
            "Chorus",
        ]
        assert [section.instance for section in sections] == [1, 1, 2, 3]
        assert [section.variant for section in sections] == ["", "", "", VARIANT_PRIME]
        # 이름은 입력 그대로 남는다 — 변형 표시를 뗀 것은 라벨뿐이다.
        assert sections[3].name == "Chorus" + VARIANT_PRIME


#: 카드 t366 실측 — 8구간 EDM 입력, 마디 없이 라벨만 배치했다(정본 §2.2 어휘 그대로).
#: 다이내믹스는 배차서가 적은 값(2/2/4/3/4/2/5/1)을 §6 표가 그대로 배정한다.
_MEASURED_EIGHT_SECTIONS = (
    ("Intro", "0:00"),
    ("Verse", "0:20"),
    ("Chorus", "0:50"),
    ("Verse", "1:20"),
    ("Chorus", "1:50"),
    ("Breakdown", "2:20"),
    ("Drop", "2:40"),
    ("Outro", "3:10"),
)


def _look(
    look_id: str,
    *,
    dynamics: int = 5,
    dimmer: float = 90,
    zoom: float | None = None,
    iris: float | None = None,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", 72),
        AttributeValue("ColorRGB_G", 100),
        AttributeValue("ColorRGB_B", 0),
    ]
    if zoom is not None:
        attributes.append(AttributeValue("Zoom", zoom))
    if iris is not None:
        attributes.append(AttributeValue("Iris", iris))
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=roles,
        attributes=tuple(attributes),
    )


def _values_line_of(look: Look) -> str:
    return " ; ".join(
        f"Attribute '{value.name}' At {int(value.value)}" for value in look.attributes
    )


def _value_lines(bundle) -> list[str]:
    return [section.commands[2] for section in bundle.stored_sections]


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }
