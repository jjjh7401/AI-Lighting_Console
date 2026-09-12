"""Built-in look library census (M2 — AC-LOOKLIB-002 / AC-LOOKLIB-003 / AC-LOOKLIB-004).

This is an EXHAUSTIVE census, not a sample: every assert below walks the whole
shipped library. A sample-based test would let a single bad look through, and a
bad look here is not a test-fixture problem — it is a bad command sent to a real
console.

The three requirements under test:

* REQ-LOOKLIB-002 — four genres, 6-10 looks each, the dynamics scale covered
  from its lowest band to its highest.
* REQ-LOOKLIB-003 — the attribute vocabulary is limited to the three bands. Band
  6 예전에는 「v1 라이브러리는 움직임을 하나도 싣지 않는다」였고, 2026-09-12 카드
  t359(감독 승인)가 그것을 **뒤집었다**: 이제 자산은 정본 §6.4 가 배정하는 자리에
  움직임을 싣고, 이 파일이 재는 것은 부재가 아니라 **규율**이다
  (:class:`TestMovementIsDeclaredWhereTheStandardRoutesIt`).
* REQ-LOOKLIB-004 — no per-show value anywhere.

Failure modes are separate tests on purpose (design.md §6.2). Nothing here
touches a console: the library is static repo data and the loader is pure.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from server.looks.loader import DEFAULT_LIBRARY_DIR, LookSchemaError, load_library_from_dir
from server.looks.movement import (
    MOVEMENT_SLOW,
    MOVEMENT_STILL,
    band_for_dynamics,
    plan_movement,
)
from server.looks.roles import ROLE_NAMES
from server.looks.schema import (
    CONFIRMED_ATTRIBUTES,
    DYNAMICS_MAX,
    DYNAMICS_MIN,
    IN_SCOPE_POOL_FAMILIES,
    MOVEMENT_ONLY_ATTRIBUTES,
    PROBE_GATED_ATTRIBUTES,
    Look,
    look_to_dict,
    payload_for_family,
    pool_family,
)

# The four genres of 사용자 확정 ② (spec.md §A). The slugs are English because
# the genre is a machine axis paired with the English ``look_id``; Korean is
# first-class where REQ-LOOKLIB-001 puts it — display_name, aliases and mood
# keywords. ``EDM`` would otherwise force a mixed-script enum.
EXPECTED_GENRES = ("worship", "rock", "ballad", "edm")

MIN_LOOKS_PER_GENRE = 6
MAX_LOOKS_PER_GENRE = 10

# The dynamics bands REQ-LOOKLIB-002 requires each genre to reach.
LOW_BAND = frozenset({1, 2})
HIGH_BAND = frozenset({4, 5})

# Band 1 + band 3 — the only names that may carry a static value. Band 2
# (Pan/Tilt) is legal ONLY inside a movement spec. 카드 t359 이후 자산은 실제로
# movement 를 싣지만, **정적 값으로는 여전히 0건**이다 — 정적 Pan/Tilt 는 빔이 정지
# 위치로 쉬는 것이고, 그것이 SPEC 이 금지한 하드 팬/틸트 그대로다.
STATIC_VOCABULARY = frozenset(CONFIRMED_ATTRIBUTES + PROBE_GATED_ATTRIBUTES)

COLOR_CHANNELS = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

# 카드 t356 이 연 기구 종류 역할 중, 팬할 수 있는 기구를 부르는 하나. 문자열을 여기
# 한 번만 적는 것은 `roles.py` 가 이름을 바꾸면 이 파일이 조용히 다른 것을 재기
# 시작하는 것을 막으려는 것이 아니라(이름은 자산이 문자열로 들고 있어 못 바꾼다)
# 이 파일 안에서 뜻이 한 자리에만 있게 하려는 것이다.
MOVER_ROLE = "무버"

# 드롭이 없는 장르. 정본 §6.4 「빠름 = 드롭 전용」이 자산 층에서 집행되는 자리다.
DROPLESS_GENRES = ("ballad", "worship")

# Substring scan, matching the shipped verification grep verbatim. These are API
# tokens, not topic words, so a plain case-insensitive substring is the right
# shape — a word boundary would miss ``ColorRGB_Pan``-style compounds. Focus /
# Frost / Prism1 / Shutter did not enter band 3 at M0, for three causes rather
# than one: Focus / Frost were misspellings of ``Focus1`` / ``Frost1`` (t135
# fired both live at ok=True), Prism is genuinely absent from this rig, Shutter
# is danger-policy excluded and was never fired. What this list keys on is the
# scope boundary, which holds under every branch (spec.md §D) whichever cause
# applies. The canonical docstring at ``server/looks/schema.py:16-18`` still
# states the old single cause — two PRESERVE gates lock that file, so t142 could
# not correct it; the correction follows the t149 exception review.
#
# 🔴 **이 목록은 2026-09-12 에 여섯에서 넷으로 좁혀졌다 — 카드 t359, 감독 승인.**
# 예전 목록은 ``("Pan", "Tilt", "Focus", "Frost", "Prism", "Shutter")`` 여섯을 한
# 덩어리로 금지했고, 그 한 덩어리가 **서로 다른 두 사실**을 실었다:
#
# * ``Focus`` / ``Frost`` / ``Prism`` / ``Shutter`` — **콘솔이 거절했거나 위험 정책으로
#   배제된** 어휘. 그 사실은 안 변했으므로 이 넷은 자산 원문에서 주석·산문까지 포함해
#   여전히 전면 금지다.
# * ``Pan`` / ``Tilt`` — 콘솔이 거절한 적이 **없다**. 금지의 근거는 `spec.md §D` 의 범위
#   경계였고, 그 경계의 실질적 사유는 v1 번들이 movement 를 발화하지 않아 선언한 축이
#   조용히 버려진다는 것이었다(design.md AP-18). **그 사유는 소멸했다** — 카드 t357 이
#   룩의 움직임 선언을 `server/looks/movement.py` → `server/fx/instantiate.py` 경로로
#   실제 페이저 명령까지 옮겼고, 감독이 2026-09-12 자산에 움직임을 싣는 것을 승인했다.
#
# 그래서 ``Pan``/``Tilt`` 는 **지워지지 않고 좁혀진다**: 아래
# :data:`MOVEMENT_DECLARATION` 한 형태로만 자산 원문에 나타날 수 있고, 그 밖의 자리
# (정적 값·표시 이름·별칭·주석)에 나타나면 여전히 빨갛다. 그냥 지웠다면 다음 편집자가
# ``display_name: "Pan 스윕"`` 이나 주석 속 예시 값을 적어도 아무도 못 잡는다.
PROBE_REJECTED_TOKENS = ("Focus", "Frost", "Prism", "Shutter")

# ``Pan``/``Tilt`` 가 자산 원문에 나타나도 되는 **유일한** 형태 — movement 항목의
# attribute 줄. 줄 **전체**를 앵커로 잡는 것이 요점이다: 부분 일치로 두면 같은 줄에
# 무엇이든 덧붙일 수 있고, 그러면 좁힌 것이 아니라 푼 것이 된다.
MOVEMENT_DECLARATION = re.compile(
    r'^\s*-\s+attribute:\s*"(?:' + "|".join(MOVEMENT_ONLY_ATTRIBUTES) + r')"\s*$'
)

# A per-show value can only reach the assets through a string field (the schema
# is closed) or through a comment. Both are scanned. The pattern is keyword +
# number because that is what an actual rig binding looks like; the bare words
# may legitimately appear in prose explaining why they are absent.
PER_SHOW_PATTERN = re.compile(
    r"(?:group|preset|fixture|fid|executor|exec|page|sequence|cue|universe|dmx|채널|그룹|프리셋|익스큐터)"
    r"\s*[.#]?\s*\d",
    re.IGNORECASE,
)

HANGUL = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def library():
    """The real shipped library, loaded exactly the way production loads it."""
    return load_library_from_dir()


@pytest.fixture(scope="module")
def asset_paths() -> tuple[Path, ...]:
    return tuple(sorted(DEFAULT_LIBRARY_DIR.glob("*.yaml")))


@pytest.fixture(scope="module")
def asset_text(asset_paths) -> tuple[tuple[str, str], ...]:
    return tuple((path.name, path.read_text(encoding="utf-8")) for path in asset_paths)


def _by_genre(library) -> dict[str, list[Look]]:
    grouped: dict[str, list[Look]] = {}
    for look in library.looks:
        grouped.setdefault(look.genre, []).append(look)
    return grouped


class TestLibraryLoads:
    """AC-LOOKLIB-002 — the shipped assets are loadable at all."""

    def test_the_shipped_library_loads_without_error(self, library):
        # load_library_from_dir raises LookSchemaError on any violation, so a
        # clean return already means every look passed the M1 loader.
        assert library.looks, "the shipped library is empty"

    def test_every_look_is_individually_reachable_by_id(self, library):
        for look in library.looks:
            assert library.by_id(look.look_id) is look

    def test_look_ids_are_unique_across_the_whole_library(self, library):
        ids = [look.look_id for look in library.looks]
        assert len(ids) == len(set(ids)), "duplicate look id across asset files"

    def test_assets_are_yaml_files_under_the_library_directory(self, asset_paths):
        assert asset_paths, f"no *.yaml assets in {DEFAULT_LIBRARY_DIR}"


class TestGenreCoverage:
    """AC-LOOKLIB-002 — four genres, 6-10 looks each."""

    def test_exactly_the_four_confirmed_genres_are_present(self, library):
        assert set(_by_genre(library)) == set(EXPECTED_GENRES)

    def test_every_genre_carries_between_six_and_ten_looks(self, library):
        for genre, looks in sorted(_by_genre(library).items()):
            assert MIN_LOOKS_PER_GENRE <= len(looks) <= MAX_LOOKS_PER_GENRE, (
                f"{genre} has {len(looks)} looks, "
                f"expected {MIN_LOOKS_PER_GENRE}-{MAX_LOOKS_PER_GENRE}"
            )


class TestDynamicsScale:
    """AC-LOOKLIB-002 — the integer scale and the per-genre coverage rule."""

    def test_every_dynamics_level_is_an_integer_within_range(self, library):
        for look in library.looks:
            assert isinstance(look.dynamics, int) and not isinstance(look.dynamics, bool)
            assert DYNAMICS_MIN <= look.dynamics <= DYNAMICS_MAX, (
                f"{look.look_id} dynamics {look.dynamics} out of range"
            )

    def test_every_genre_reaches_the_low_band(self, library):
        # "Reaches its lowest band" is mechanised as >=1 look at level 1 or 2
        # (acceptance.md AC-LOOKLIB-002). Asserted separately from the high band
        # so a failure names which end of the arc is missing.
        for genre, looks in sorted(_by_genre(library).items()):
            levels = {look.dynamics for look in looks}
            assert levels & LOW_BAND, (
                f"{genre} has no look at dynamics 1 or 2 (levels: {sorted(levels)})"
            )

    def test_every_genre_reaches_the_high_band(self, library):
        for genre, looks in sorted(_by_genre(library).items()):
            levels = {look.dynamics for look in looks}
            assert levels & HIGH_BAND, (
                f"{genre} has no look at dynamics 4 or 5 (levels: {sorted(levels)})"
            )


class TestAttributeVocabulary:
    """AC-LOOKLIB-003 bands 1, 2, 3 — the census over every attribute name."""

    def test_every_static_attribute_is_in_the_confirmed_or_probed_bands(self, library):
        for look in library.looks:
            for value in look.attributes:
                assert value.name in STATIC_VOCABULARY, (
                    f"{look.look_id} uses {value.name!r}, outside {sorted(STATIC_VOCABULARY)}"
                )

    def test_no_movement_only_attribute_appears_as_a_static_value(self, library):
        # Band 2: Pan/Tilt are legal only inside a movement spec. 카드 t359 가 자산에
        # movement 를 실은 지금 이 단언은 처음으로 **실제 일**을 한다 — 예전에는 자산에
        # Pan/Tilt 가 한 글자도 없어 공허하게 통과했다.
        for look in library.looks:
            for value in look.attributes:
                assert value.name not in MOVEMENT_ONLY_ATTRIBUTES, (
                    f"{look.look_id} carries {value.name!r} as a static position value"
                )

    def test_no_probe_rejected_beam_string_appears_in_any_asset(self, asset_text):
        # Raw-text scan, not a parsed scan: the loader would reject these names
        # in an attribute payload, but it never sees a comment or a display
        # name. Focus/Frost/Prism1/Shutter did not enter band 3 at M0; the cause
        # differs per name (see PROBE_REJECTED_TOKENS above), and what this
        # scan enforces is the scope boundary, not any one of those causes.
        for name, text in asset_text:
            for token in PROBE_REJECTED_TOKENS:
                assert token.lower() not in text.lower(), (
                    f"{name} mentions {token!r}; probe-rejected beam vocabulary "
                    "must not appear in the assets at all"
                )

    def test_a_movement_axis_appears_only_as_a_movement_declaration(self, asset_text):
        # t359 가 위 스캔에서 뺀 절반을 여기서 **좁혀서** 받는다. 파싱 스캔
        # (`test_no_movement_only_attribute_appears_as_a_static_value`)은 로더가 읽는
        # 것만 보므로 주석·표시 이름·별칭을 못 본다. 원문 스캔은 그 자리를 덮고,
        # `Pan`/`Tilt` 가 movement 선언 줄 **말고** 어디에 나타나도 빨개진다.
        for name, text in asset_text:
            for number, line in enumerate(text.splitlines(), start=1):
                lowered = line.lower()
                if not any(axis.lower() in lowered for axis in MOVEMENT_ONLY_ATTRIBUTES):
                    continue
                assert MOVEMENT_DECLARATION.match(line), (
                    f"{name}:{number} carries a movement axis outside a movement "
                    f'declaration: {line!r}. 위치 축은 `- attribute: "Pan"` 형태의 '
                    "movement 항목으로만 자산에 들어온다 (카드 t359)"
                )

    def test_the_narrowed_scan_is_not_vacuous(self, asset_text):
        # 좁힌 스캔은 **아무것도 안 잡는 스캔**으로 조용히 퇴화할 수 있다. 두 쪽을
        # 모두 못박는다: 금지 목록이 비어 있지 않고 훑는 원문도 비어 있지 않다는 것,
        # 그리고 위 `Pan`/`Tilt` 규칙이 실제로 **발화하는 줄이 있다**는 것. 자산에서
        # 움직임이 사라지면 여기가 빨개진다 — 「선언이 없어서 통과」를 막는 팔이다.
        assert PROBE_REJECTED_TOKENS
        assert asset_text and all(text.strip() for _name, text in asset_text)
        declarations = [
            line
            for _name, text in asset_text
            for line in text.splitlines()
            if MOVEMENT_DECLARATION.match(line)
        ]
        assert declarations, (
            "자산에 movement 선언이 한 줄도 없다. 그러면 위 스캔은 훑을 것이 없어 "
            "공허하게 통과한다 (카드 t359)"
        )

    def test_every_attribute_attributes_to_exactly_one_in_scope_pool_family(self, library):
        # AC-LOOKLIB-003 band 4 — an allowed name with no pool to store it in
        # would only surface at M4, when the bundle builder has nowhere to put it.
        for look in library.looks:
            for value in look.attributes:
                family = pool_family(value.name)
                assert family in IN_SCOPE_POOL_FAMILIES, (
                    f"{look.look_id}: {value.name!r} attributes to {family!r}, "
                    f"not one of {list(IN_SCOPE_POOL_FAMILIES)}"
                )

    def test_every_payload_splits_by_family_without_loss(self, library):
        # AC-LOOKLIB-003 band 5 — the mechanical evidence that the ASSUMPTION-14
        # FALLBACK branch (per-family isolated capture) can be built from this
        # same data without re-authoring the library.
        for look in library.looks:
            union: list = []
            for family in IN_SCOPE_POOL_FAMILIES:
                union.extend(payload_for_family(look, family))
            assert sorted(union, key=lambda a: a.name) == sorted(
                look.attributes, key=lambda a: a.name
            ), f"{look.look_id} payload does not partition cleanly by family"


class TestColourIsFullySpecified:
    """M0 secondary observation — a partially named colour renders white.

    Storing a preset after setting only one ColorRGB channel captures the whole
    colour family, so a look that names only R arrives on the console as white.
    Naming one channel is therefore not "specifying less colour", it is
    specifying a different colour than the author intended.
    """

    def test_a_look_naming_any_colour_channel_names_all_three(self, library):
        for look in library.looks:
            named = {value.name for value in look.attributes if value.name in COLOR_CHANNELS}
            assert named in (set(), set(COLOR_CHANNELS)), (
                f"{look.look_id} names {sorted(named)} but not all of "
                f"{list(COLOR_CHANNELS)} — it would render white on the console"
            )

    def test_every_look_specifies_a_colour(self, library):
        # Not required by the schema, but a look with no colour is a look whose
        # colour is whatever the programmer left active — the same silent
        # inheritance the rule above guards against.
        for look in library.looks:
            named = {value.name for value in look.attributes if value.name in COLOR_CHANNELS}
            assert named == set(COLOR_CHANNELS), f"{look.look_id} specifies no colour"

    def test_every_look_specifies_an_intensity(self, library):
        names = {"Dimmer"}
        for look in library.looks:
            assert names & {value.name for value in look.attributes}, (
                f"{look.look_id} specifies no Dimmer"
            )


class TestMovementIsDeclaredWhereTheStandardRoutesIt:
    """AC-LOOKLIB-003 band 6 — 카드 t359 이후. 부재가 아니라 **규율**을 잰다.

    예전의 이 자리에는 ``test_no_shipped_look_carries_a_movement_spec`` 이 있었고,
    출하 룩 중 움직임을 선언한 것이 하나도 없어야 통과했다. 그 단언의 사유는 v1
    번들이 movement 필드를 발화하지 않는다는 것이었는데(design.md AP-18), 카드 t357
    이 발화 경로를 놓으면서 사유가 소멸했고 감독이 2026-09-12 자산에 움직임을 싣는
    것을 승인했다. 그래서 단언은 지워지지 않고 **뒤집혀서 좁혀진다** — 아래 넷은
    정본 `docs/proposals/song-structure-lighting-standard.md` §6 표 · §6.2 · §6.4 가
    문면으로 정한 것들이고, 각각 다른 사실이라 합치지 않았다.
    """

    def test_the_shipped_library_actually_carries_movement(self, library):
        # 비공허 팔. 아래 세 규율은 전부 「움직임을 선언한 룩」을 훑으므로, 자산에서
        # 움직임이 사라지면 셋 다 빈 루프로 조용히 통과한다.
        movers = [look.look_id for look in library.looks if look.movement]
        assert movers, (
            "출하 라이브러리에 움직임을 선언한 룩이 하나도 없다. 카드 t359 가 연 것이 "
            "바로 이 자리이고, 비면 아래 규율 검사들이 공허해진다"
        )

    def test_no_still_band_look_declares_movement(self, library):
        # 정본 §6.4 → `_DYNAMICS_BANDS`: D1 은 정지다. §6 표도 인트로·브레이크다운·
        # 솔로를 「무빙·이펙트 정지」로 적는다. 정지 대역 룩이 움직임을 선언하면
        # `_movement_carrier` 가 `movement_band_still` 로 보류하므로, 선언은 무대에
        # 안 나가면서 보고만 어지럽힌다.
        offenders = [
            look.look_id
            for look in library.looks
            if look.movement and band_for_dynamics(look.dynamics) == MOVEMENT_STILL
        ]
        assert offenders == [], (
            f"{offenders} declare movement at a still-band dynamics level; "
            "정본 §6 표가 그 구간을 「무빙·이펙트 정지」로 적는다"
        )

    def test_every_moving_look_carries_a_fixture_role_that_can_pan(self, library):
        # 정본 §6.2 「기구마다 역할을 부여하라」. 위치 역할만으로는 그 기구가 돌 수
        # 있는지 말할 수 없다 — 호리·워시·프론트 필은 팬하지 않는다. 종류 역할
        # `무버`(카드 t356)가 그것을 말하는 유일한 어휘다.
        for look in library.looks:
            if not look.movement:
                continue
            assert MOVER_ROLE in look.roles, (
                f"{look.look_id} declares movement but names no {MOVER_ROLE!r} role; "
                "돌 수 없는 기구에 스윕을 보내게 된다 (정본 §6.2)"
            )

    def test_no_drop_less_genre_reaches_the_mid_or_fast_band(self, library):
        # 정본 §6.4 「빠름 = 드롭 전용」. 대역은 룩이 아니라 다이내믹스가 정하므로
        # (`band_for_dynamics`), 드롭이 없는 장르에서 그 문면을 지키는 유일한 방법은
        # D4·D5 룩에 움직임을 **안 적는 것**이다.
        for look in library.looks:
            if not look.movement or look.genre not in DROPLESS_GENRES:
                continue
            band = band_for_dynamics(look.dynamics)
            assert band == MOVEMENT_SLOW, (
                f"{look.look_id} ({look.genre}) routes to the {band!r} band; "
                "드롭이 없는 장르는 느린 대역에만 움직임을 싣는다 (정본 §6.4)"
            )

    def test_every_declaration_reaches_a_phaser_command(self, library):
        # 이 검사가 이 클래스의 이빨이다. 위 셋은 「어디에 적었는가」를 재고, 이것은
        # 「적은 것이 실제로 명령이 되는가」를 잰다. `plan_movement` 는 진폭 미선언·
        # 축 중복·위상 충돌·대역 밖 속도를 `MovementError` 로 거절하므로, 여기를
        # 통과한다는 것은 자산의 선언이 조용히 버려지지 않는다는 뜻이다.
        for look in library.looks:
            if not look.movement:
                continue
            plan = plan_movement(look, band=band_for_dynamics(look.dynamics))
            assert plan is not None and plan.commands, (
                f"{look.look_id} declares movement but plans no command line"
            )

    def test_the_schema_still_round_trips_a_movement_bearing_look(self):
        # The other half of the pair. Without this, "the library has no
        # movement" and "the field was deleted" are indistinguishable — and the
        # field is a successor-SPEC contract (P1-1 / P1-2).
        from server.looks.loader import load_library
        from server.looks.schema import SCHEMA_VERSION

        with_movement = {
            "look_id": "probe-movement-roundtrip",
            "display_name": "왕복 확인용",
            "genre": "worship",
            "dynamics": 3,
            "roles": ["백라이트"],
            "attributes": {"Dimmer": 60, "ColorRGB_R": 100, "ColorRGB_G": 70, "ColorRGB_B": 20},
            "movement": [
                {"attribute": "Pan", "phase_from": 0, "phase_to": 360, "speed": 60},
            ],
        }
        loaded = load_library({"schema_version": SCHEMA_VERSION, "looks": [with_movement]})
        look = loaded.looks[0]
        assert len(look.movement) == 1
        assert look.movement[0].attribute == "Pan"

        # dump -> parse -> identical object.
        reloaded = load_library({"schema_version": SCHEMA_VERSION, "looks": [look_to_dict(look)]})
        assert reloaded.looks[0] == look


class TestNoPerShowValues:
    """AC-LOOKLIB-004 — structural absence plus a census over the assets."""

    def test_the_schema_carries_no_rig_binding_field(self):
        # Structural half: there is no field to put a per-show value in.
        fields = {field.name for field in dataclasses.fields(Look)}
        forbidden = {
            "group",
            "group_number",
            "preset",
            "preset_slot",
            "slot",
            "fid",
            "fixture",
            "fixture_id",
            "executor",
            "executor_number",
            "page",
            "universe",
            "dmx_address",
        }
        assert not (fields & forbidden), (
            f"schema exposes rig binding field(s): {fields & forbidden}"
        )

    def test_no_look_string_field_carries_a_per_show_binding(self, library):
        # The closed schema means a per-show value can only ride in on a string.
        for look in library.looks:
            for label, text in (
                ("look_id", look.look_id),
                ("display_name", look.display_name),
                ("genre", look.genre),
                *((f"alias {a!r}", a) for a in look.aliases),
                *((f"mood {m!r}", m) for m in look.mood_keywords),
            ):
                match = PER_SHOW_PATTERN.search(text)
                assert match is None, (
                    f"{look.look_id} {label} contains a per-show binding: {match.group(0)!r}"
                )

    def test_no_asset_file_mentions_a_per_show_binding(self, asset_text):
        # Comments are scanned too: an example binding in a comment is the
        # invitation for the next author to write a real one.
        for name, text in asset_text:
            for line_number, line in enumerate(text.splitlines(), start=1):
                match = PER_SHOW_PATTERN.search(line)
                assert match is None, (
                    f"{name}:{line_number} contains a per-show binding: {match.group(0)!r}"
                )

    def test_roles_are_the_only_way_a_look_names_a_stage_position(self, library):
        for look in library.looks:
            assert look.roles, f"{look.look_id} names no role"
            for role in look.roles:
                assert role in ROLE_NAMES, (
                    f"{look.look_id} uses role {role!r} outside the closed set"
                )


class TestKoreanIsFirstClass:
    """REQ-LOOKLIB-001 — Korean aliases and mood keywords, not an afterthought."""

    def test_every_display_name_is_korean(self, library):
        for look in library.looks:
            assert HANGUL.search(look.display_name), (
                f"{look.look_id} display_name {look.display_name!r} has no Hangul"
            )

    def test_every_look_carries_at_least_one_korean_mood_keyword(self, library):
        for look in library.looks:
            korean = [word for word in look.mood_keywords if HANGUL.search(word)]
            assert korean, f"{look.look_id} has no Korean mood keyword"

    def test_every_look_carries_at_least_one_alias(self, library):
        for look in library.looks:
            assert look.aliases, f"{look.look_id} has no alias"


class TestCensusIsExhaustive:
    """Guards on the census itself — a census that walks nothing passes silently."""

    def test_the_library_is_large_enough_to_make_the_census_meaningful(self, library):
        # 4 genres x 6 looks minimum. If a future edit drops the library to a
        # handful of looks, every per-look loop above would still "pass".
        assert len(library.looks) >= len(EXPECTED_GENRES) * MIN_LOOKS_PER_GENRE

    def test_the_census_sees_every_asset_file(self, library, asset_paths):
        # Ties the parsed view to the on-disk view: a file the loader silently
        # skipped would never be censused.
        assert len(asset_paths) == len(EXPECTED_GENRES)
        assert len(library.looks) >= len(asset_paths)

    def test_a_missing_library_directory_is_an_explicit_error(self, tmp_path):
        with pytest.raises(LookSchemaError):
            load_library_from_dir(tmp_path / "does-not-exist")
