"""t357 — 움직임을 콘솔로 보낸다: 룩의 `MovementSpec` → fx 페이저 → 곡 큐 번들.

정본은 `docs/proposals/song-structure-lighting-standard.md` §6.2(세 층) · §6.4(움직임 속도
· 관객 눈 하드룰) · §12 항목 1(고칠 것).

**고치기 전에 실측한 것**(2026-09-11, main `28a0dc1`):
`grep -rn "server.fx" server/looks server/design` → 0건. 무빙 페이저는
`server/fx/library/movement.yaml` 에 실재하고 `Look.movement` 필드도 선언돼 있는데 곡→큐
경로가 fx 계층을 부르지 않으므로, 룩에 움직임을 적으면 **조용히 버려졌다**.

**이 파일이 재지 않는 것**도 적는다.

* **콘솔에서의 효과.** 저장된 페이저 큐는 빈 큐와 구별되지 않고 `Phase`/`Speed` 는 되읽히지
  않는다(`server/fx/instantiate.py` 머리의 @MX:WARN, M0 실측). 그러므로 여기서 재는 것은
  **명령 문면**이고, 무대에서 무엇이 움직이는지는 실기 회차의 몫이다.
* **정적 값과 페이저를 한 캡처에 섞는 것.** 값 라인 뒤에 스텝 런을 두는 순서가 이 카드의
  유일한 미실측 가정이다(`songcue.py` `_section_bundle` 의 주석).
* **출하 라이브러리.** 지금 출하되는 룩 중 movement 를 선언한 것은 **하나도 없다** —
  `test_looks_library.py` 의 `FORBIDDEN_ATTRIBUTE_TOKENS` 가 자산 **원문**에서 `Pan`/`Tilt`
  를 금지하는 spec.md §D 범위 경계이기 때문이다. 그 경계를 옮기는 것은 LOOKLIB 쪽 결정이고
  이 카드에서 하지 않는다. 그래서 여기의 룩은 전부 시험 자료다.
"""

from __future__ import annotations

import pytest

from server.fx.instantiate import is_programmer_state
from server.looks.movement import (
    AMPLITUDE_UNDECLARED,
    EYE_DWELL_LIMIT_SECONDS,
    MOVEMENT_FAST,
    MOVEMENT_MID,
    MOVEMENT_SLOW,
    MOVEMENT_STILL,
    SPEED_FLOOR_BPM,
    SPEED_OUT_OF_BAND,
    MovementError,
    band_for_dynamics,
    band_speed_range,
    plan_movement,
)
from server.looks.schema import AttributeValue, Look, MovementSpec
from server.looks.songcue import (
    MOVEMENT_BAND_STILL,
    MOVEMENT_LINE_COLLISION,
    MOVEMENT_TURN_BOUNDARY,
    SongCueBundleError,
    SongCueLookSelection,
    _assembled,
    _guard_bundle_collision,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups


class TestTheBandComesFromSectionIntent:
    """정본 §6.4 — 느림 = 빌드·앰비언스, 중속 = 그루브, 빠름 = **드롭 전용**."""

    def test_each_dynamics_level_routes_to_the_documented_band(self):
        assert [band_for_dynamics(level) for level in (1, 2, 3, 4, 5)] == [
            MOVEMENT_STILL,
            MOVEMENT_SLOW,
            MOVEMENT_SLOW,
            MOVEMENT_MID,
            MOVEMENT_FAST,
        ]

    def test_fast_is_the_drop_alone(self):
        """「빠름 = 드롭 전용」의 대우 — D5 아래 어느 세기도 빠름이 아니다."""
        assert [
            level for level in (1, 2, 3, 4, 5) if band_for_dynamics(level) == MOVEMENT_FAST
        ] == [5]

    def test_the_bands_do_not_overlap_and_rise(self):
        slow, mid, fast = (
            band_speed_range(b) for b in (MOVEMENT_SLOW, MOVEMENT_MID, MOVEMENT_FAST)
        )
        assert slow[1] == mid[0]
        assert mid[1] == fast[0]
        assert slow[0] < mid[0] < fast[0]

    def test_a_drop_band_look_is_faster_than_a_build_band_look(self):
        """카드가 요구한 대조 — 드롭 대역이 빌드 대역보다 빠르다."""
        build = plan_movement(_moving_look("build", dynamics=3), band=MOVEMENT_SLOW)
        drop = plan_movement(_moving_look("drop", dynamics=5), band=MOVEMENT_FAST)

        assert build is not None and drop is not None
        assert build.speed < drop.speed
        assert (build.speed, drop.speed) == (SPEED_FLOOR_BPM, band_speed_range(MOVEMENT_FAST)[0])


class TestMovementReachesTheBundle:
    """대조군 ①(양팔의 양성) — 움직임을 선언한 룩이 콘솔 명령을 낸다."""

    def test_a_moving_look_puts_a_real_phaser_between_the_values_and_the_store(self):
        section = parse_sections((("Drop", "0:00"),))[0]
        look = _moving_look("drop", dynamics=5)
        bundle = _bundle_of((section, look))

        stored = bundle.stored_sections
        assert len(stored) == 1
        assert stored[0].movement is not None
        assert stored[0].movement.band == MOVEMENT_FAST
        # 값 라인(index 2) 뒤, Store 앞. 카드 t377·t378 이 프론트 필·찍는 액센트
        # 그룹을 값 라인과 움직임 사이에 끼워 넣으므로(둘 다 켜지면 각 두 줄), 그
        # 층들이 실제로 몇 줄을 냈는지(``front_fill``/``accent_fixture`` 필드)를
        # 읽어 움직임 줄의 시작 자리를 구한다 — 위치를 하드코드하지 않는다.
        commands = stored[0].commands
        store_index = next(i for i, c in enumerate(commands) if c.startswith("Store Sequence"))
        offset = 3
        if stored[0].front_fill is not None:
            offset += 2
        if stored[0].accent_fixture is not None:
            offset += 2
        emitted = commands[offset:store_index]
        assert emitted == (
            "Attribute 'Pan' At Relative -20",
            "Step 2",
            "Attribute 'Pan' At Relative 20",
            "Attribute 'Pan' At Phase 0 Thru 360",
            "Attribute 'Pan' At Speed 90",
        )

    def test_a_phaser_needs_two_steps_and_this_one_has_them(self):
        """`Step 2` 가 없으면 페이저가 아니다 — 그 줄이 실제로 나가는지가 이 카드의 핵심."""
        section = parse_sections((("Drop", "0:00"),))[0]
        bundle = _bundle_of((section, _moving_look("drop", dynamics=5)))

        assert "Step 2" in bundle.commands

    def test_two_axes_emit_a_diagonal_with_both_axes_in_every_step(self):
        section = parse_sections((("Drop", "0:00"),))[0]
        look = _moving_look("drop", dynamics=5, axes=(("Pan", 20.0), ("Tilt", 12.0)))
        bundle = _bundle_of((section, look))

        movement = bundle.stored_sections[0].movement
        assert movement is not None
        assert movement.pattern == "diagonal"
        assert movement.attributes == ("Pan", "Tilt")
        assert "Attribute 'Tilt' At Relative -12" in bundle.commands
        assert "Attribute 'Tilt' At Relative 12" in bundle.commands

    def test_the_command_text_comes_from_the_fx_layer_not_a_second_grammar(self):
        """문면 생산자는 `server.fx.instantiate.phaser_lines` 하나다.

        룩 계층이 자기 문법을 따로 갖고 있었다면 이 두 줄이 갈라진다.
        """
        look = _moving_look("drop", dynamics=5)
        plan = plan_movement(look, band=MOVEMENT_FAST)
        section = parse_sections((("Drop", "0:00"),))[0]
        bundle = _bundle_of((section, look))

        assert plan is not None
        for line in plan.commands:
            assert line in bundle.commands


class TestOneInstantiationPerInstructionTurn:
    """`run_commands` 중복 제거의 경계 — 한 번들이 페이저를 하나만 낸다."""

    def test_the_strongest_band_carries_it_and_the_rest_are_reported(self):
        build, drop = parse_sections((("Build", "0:00"), ("Drop", "0:40")))
        bundle = _bundle_of(
            (build, _moving_look("build", dynamics=3)),
            (drop, _moving_look("drop", dynamics=5)),
        )

        carriers = bundle.movement_sections
        assert [section.cue_number for section in carriers] == [2]
        assert carriers[0].movement.band == MOVEMENT_FAST
        assert [(w.cue_number, w.reason) for w in bundle.withheld_movement] == [
            (1, MOVEMENT_TURN_BOUNDARY)
        ]
        assert "Step 2" in bundle.commands
        assert bundle.commands.count("Step 2") == 1

    def test_the_earliest_cue_wins_a_tie_on_band(self):
        first, second = parse_sections((("Drop", "0:00"), ("Drop", "0:40")))
        bundle = _bundle_of(
            (first, _moving_look("drop-a", dynamics=5, dimmer=90)),
            (second, _moving_look("drop-b", dynamics=5, dimmer=80)),
        )

        assert [section.cue_number for section in bundle.movement_sections] == [1]
        assert [w.cue_number for w in bundle.withheld_movement] == [2]

    def test_a_literal_drop_wins_a_band_tie_over_an_earlier_cue(self):
        """카드 t367 — 대역이 묶이고 그 중 하나가 **리터럴 드롭**이면 이른 큐가 아니라
        드롭이 캐리어다. 위 시험(``test_the_earliest_cue_wins_a_tie_on_band``)은 리터럴
        드롭끼리 묶인 경우라 이 tie-break 을 가르지 못한다 — 여기는 드롭이 아닌 큐가
        먼저 오는 경우다.
        """
        chorus, drop = parse_sections((("Chorus", "0:00"), ("Drop", "0:40")))
        bundle = _bundle_of(
            (chorus, _moving_look("chorus", dynamics=5, dimmer=90)),
            (drop, _moving_look("drop", dynamics=5, dimmer=80)),
        )

        assert [section.cue_number for section in bundle.movement_sections] == [2]
        assert [w.cue_number for w in bundle.withheld_movement] == [1]

    def test_a_band_tie_with_no_literal_drop_still_favours_the_earliest_cue(self):
        """대조군 — 드롭이 아예 없으면 tie-break 은 고치기 전과 바이트 동일하다.

        ``test_the_earliest_cue_wins_a_tie_on_band`` 는 리터럴 드롭끼리의 묶임이라
        리터럴-드롭 우선이 개입할 자리가 없다. 여기는 라벨 자체가 드롭 어휘를 안 걸어
        (``Build`` 둘), 새 tie-break 의 두 번째 열(``_is_literal_drop``)이 둘 다
        ``False`` 로 같아 세 번째 열(이른 큐)로 그대로 내려간다 — 고치기 전 로직과
        같은 결과다.
        """
        first, second = parse_sections((("Build", "0:00"), ("Build", "0:40")))
        bundle = _bundle_of(
            (first, _moving_look("build-a", dynamics=5, dimmer=90)),
            (second, _moving_look("build-b", dynamics=5, dimmer=80)),
        )

        assert [section.cue_number for section in bundle.movement_sections] == [1]
        assert [w.cue_number for w in bundle.withheld_movement] == [2]

    def test_firing_two_phasers_into_one_bundle_is_refused_not_silently_emitted(self):
        """대조군 ②(음성) — 경계를 넘는 모양을 실제로 쏴서 거절되는 것을 본다.

        `_movement_carrier` 를 우회해 큐 둘에 페이저를 실으면 `Step 2` 가 두 번 나온다.
        내용이 없는 줄이라 큐마다 다르게 만들 방법이 없고, 중복 제거는 두 번째를 접는다 —
        그러면 그 큐는 스텝 하나짜리 「페이저 아닌 것」을 저장하고, 저장된 페이저 큐는 빈
        큐와 구별되지 않으므로 그 실패는 무대에서만 보인다. 그래서 거절한다.
        """
        first, second = parse_sections((("Build", "0:00"), ("Drop", "0:40")))
        looks = (_moving_look("build", dynamics=3), _moving_look("drop", dynamics=5))
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in ((first, looks[0]), (second, looks[1]))
        )
        movements = dict()
        movements[1] = plan_movement(looks[0], band=MOVEMENT_SLOW)
        movements[2] = plan_movement(looks[1], band=MOVEMENT_FAST)

        from server.looks.resolver import resolve_roles

        overreaching = _assembled(
            "Song",
            selections,
            ("Build", "Drop"),
            sequence_number=1,
            sequence_name="Song",
            resolution=resolve_roles(_groups(*FULL_RIG)),
            movements=movements,
        )

        # (가) 위반이 실재한다 — 같은 줄이 두 번 나간다.
        assert overreaching.commands.count("Step 2") == 2
        assert not is_programmer_state("Step 2"), "`Step 2` 가 면제 대상이면 이 시험은 공허하다"

        # (나) 그 모양을 그물에 쏘면 거절된다.
        with pytest.raises(SongCueBundleError) as raised:
            _guard_bundle_collision(overreaching)
        assert MOVEMENT_LINE_COLLISION in str(raised.value)

    def test_the_guard_passes_the_bundle_the_builder_actually_produces(self):
        """대조군 — 그물이 「항상 거절」을 재는 것이 아니라는 증거."""
        build, drop = parse_sections((("Build", "0:00"), ("Drop", "0:40")))
        bundle = _bundle_of(
            (build, _moving_look("build", dynamics=3)),
            (drop, _moving_look("drop", dynamics=5)),
        )

        _guard_bundle_collision(bundle)


class TestNothingIsDroppedSilently:
    """선언은 있는데 못 낸 경우 — 조용히 버리지 않고 이름과 함께 내보낸다."""

    def test_a_still_band_section_reports_the_band_instead_of_moving(self):
        section = parse_sections((("Ambient", "0:00"),))[0]
        bundle = _bundle_of((section, _moving_look("ambient", dynamics=1)))

        assert bundle.movement_sections == ()
        assert [(w.cue_number, w.reason) for w in bundle.withheld_movement] == [
            (1, MOVEMENT_BAND_STILL)
        ]
        assert "Step 2" not in bundle.commands

    def test_an_amplitude_less_declaration_is_reported_not_emitted(self):
        """`relative` 가 없으면 스텝을 만들 수 없다 — 수정자 줄만 내면 무대가 가만히 있는다."""
        section = parse_sections((("Drop", "0:00"),))[0]
        look = Look(
            look_id="no-amplitude",
            display_name="no-amplitude",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(AttributeValue("Dimmer", 90),),
            movement=(MovementSpec(attribute="Pan", phase_from=0, phase_to=360),),
        )
        bundle = _bundle_of((section, look))

        assert bundle.movement_sections == ()
        assert [(w.cue_number, w.reason) for w in bundle.withheld_movement] == [
            (1, AMPLITUDE_UNDECLARED)
        ]
        assert not any("Pan" in command for command in bundle.commands)

    def test_a_look_without_movement_is_not_reported_as_withheld(self):
        """대조군 — 선언이 없는 것은 결함이 아니므로 보고에 안 실린다."""
        section = parse_sections((("Drop", "0:00"),))[0]
        bundle = _bundle_of((section, _still_look("drop", dynamics=5)))

        assert bundle.withheld_movement == ()


class TestTheAudienceEyeRule:
    """정본 §6.4 하드룰 — 기계로 막는 절반과 못 막는 절반."""

    def test_the_speed_floor_is_derived_from_the_five_second_limit(self):
        assert SPEED_FLOOR_BPM == 60.0 / EYE_DWELL_LIMIT_SECONDS
        assert band_speed_range(MOVEMENT_SLOW)[0] == SPEED_FLOOR_BPM

    def test_every_band_floor_completes_a_cycle_inside_the_limit(self):
        for band in (MOVEMENT_SLOW, MOVEMENT_MID, MOVEMENT_FAST):
            low, _high = band_speed_range(band)
            assert 60.0 / low <= EYE_DWELL_LIMIT_SECONDS

    def test_a_speed_below_the_floor_is_refused(self):
        look = _moving_look("too-slow", dynamics=3, speed=10.0)

        with pytest.raises(MovementError) as raised:
            plan_movement(look, band=MOVEMENT_SLOW)
        assert raised.value.reason == SPEED_OUT_OF_BAND

    def test_an_authored_speed_inside_the_band_is_used_verbatim(self):
        """대조군 — 대역 안의 값은 거절되지 않는다. 위 단정이 「항상 거절」이 아니라는 증거."""
        plan = plan_movement(_moving_look("in-band", dynamics=3, speed=18.0), band=MOVEMENT_SLOW)

        assert plan is not None
        assert plan.speed == 18.0

    def test_a_drop_speed_authored_into_the_slow_band_is_refused_too(self):
        """경계는 양방향이다 — 위로 벗어난 값도 조용히 끌어내리지 않는다."""
        with pytest.raises(MovementError) as raised:
            plan_movement(_moving_look("too-fast", dynamics=3, speed=120.0), band=MOVEMENT_SLOW)
        assert raised.value.reason == SPEED_OUT_OF_BAND


class TestNoMovementIsByteIdentical:
    """움직임을 선언하지 않은 룩의 콘솔 명령은 고치기 전과 바이트 동일하다."""

    def test_the_command_bundle_of_a_movement_free_song_is_unchanged(self):
        first, second = parse_sections((("Chorus", "0:00"), ("Verse", "0:40")))
        bundle = _bundle_of(
            (first, _still_look("chorus", dynamics=5, dimmer=90, zoom=18)),
            (second, _still_look("verse", dynamics=2, dimmer=45)),
        )

        # 카드 t363 이 Store 줄에 페이드를 붙였다(정본 §9) — 후렴은 0.2초(극적인 컷),
        # 벌스는 2초(부드러운 전환). **이 검사의 성질은 그대로다**: 재는 것은 「움직임이
        # 없으면 움직임 줄이 하나도 안 나간다」이고, 페이드는 움직임 축이 아니다.
        # 감광은 여기서 안 걸린다 — 드롭 대역 큐가 **뒤에** 없다(후렴이 첫 큐다).
        # 카드 t377 이 프론트 필 두 줄을 큐마다 더했다 — 이 픽스처의 룩이 프론트를
        # 안 실어서다(정본 §6.2 [HARD]). 두 번째 큐가 21 인 것은 첫 큐의 20 과
        # 겹치지 않는 유일한 값으로 오른 것이다.
        assert bundle.commands == (
            "ChangeDestination Root",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 90 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0 ; "
            "Attribute 'Zoom' At 18",
            "Group 12",
            "Attribute 'Dimmer' At 20 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 52",
            "Store Sequence 1 Cue 1 'Chorus' CueFade 0.2",
            "Label Sequence 1 'Song'",
            "ClearAll",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 45 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0",
            "Group 12",
            "Attribute 'Dimmer' At 21 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 52",
            "Store Sequence 1 Cue 2 'Verse' CueFade 2",
            "ClearAll",
        )
        assert bundle.movement_sections == ()
        assert bundle.withheld_movement == ()

    def test_movement_does_not_change_which_cues_are_stored_or_skipped(self):
        """두 번 도는 조립의 전제 — 움직임 줄은 저장/건너뜀 판정에 참여하지 않는다.

        같은 세 구간을 「움직임 있음/없음」으로 두 번 만들어, 저장된 큐 번호와 건너뛴 사유가
        같은지 잰다. 여기서 값 라인이 겹치도록 천장 룩을 써서 건너뜀 갈래까지 태운다.
        """
        first, second, third = parse_sections(
            (("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20"))
        )
        ceiling_still = _still_look("ceiling", dynamics=5, dimmer=100)
        ceiling_moving = _moving_look("ceiling", dynamics=5, dimmer=100)

        without = _bundle_of(*((section, ceiling_still) for section in (first, second, third)))
        with_movement = _bundle_of(
            *((section, ceiling_moving) for section in (first, second, third))
        )

        assert [s.cue_number for s in without.stored_sections] == [
            s.cue_number for s in with_movement.stored_sections
        ]
        assert [s.reason for s in without.skipped] == [s.reason for s in with_movement.skipped]
        # 비공허성: 건너뜀 갈래가 실제로 걸렸다.
        assert without.skipped != ()


def _moving_look(
    look_id: str,
    *,
    dynamics: int,
    dimmer: float = 90,
    axes: tuple[tuple[str, float], ...] = (("Pan", 20.0),),
    speed: float | None = None,
) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
        movement=tuple(
            MovementSpec(
                attribute=name, phase_from=0, phase_to=360, speed=speed, relative=magnitude
            )
            for name, magnitude in axes
        ),
    )


def _still_look(
    look_id: str,
    *,
    dynamics: int,
    dimmer: float = 90,
    zoom: float | None = None,
) -> Look:
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", 72),
        AttributeValue("ColorRGB_G", 100),
        AttributeValue("ColorRGB_B", 0),
    ]
    if zoom is not None:
        attributes.append(AttributeValue("Zoom", zoom))
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=tuple(attributes),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _bundle_of(*pairs, title: str = "Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
