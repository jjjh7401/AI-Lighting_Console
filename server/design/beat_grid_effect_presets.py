"""카드 t593 — 박자 격자의 새 효과 프리셋을 콘솔에 만드는 레시피
(SPEC-LDBEAT-001 REQ-LDBEAT-015(i-4)(i-7)(i-8), plan M13).

값의 출처는 곡 격자 ``preset_fx_recipes["22.n"]``(효과 템플릿 ``fx_id`` + 음악 단위
주기 ``period_unit``·``period_value``)다. 반영 시점에 그 템플릿(``server/fx/library``)을
꺼내 속도를 곡 BPM ÷ 한 주기 박 수로 바꾸고(``server/design/app_movement.py`` 선례),
``build_fx_preset_bundle``(``Store Preset <pool>.<n> '<이름>' /Universal`` → ``Label`` →
``ClearAll``, 실기 선례)로 만든다. 콘솔 이름은 t589 와 같은 ``preset_labels["22.n"]``.

이 모듈은 콘솔에 아무것도 쓰지 않는다 — 순수 함수뿐이다. 후보를 「풀은 읽혔고 slot 이
없다」로 보류된 번호로 좁히는 일(덮어쓰기 0)은 공용 칸 판정
``beat_grid_position_presets.plan_cells``가 한다.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping, Sequence
from functools import lru_cache

from server.design.beat_grid import preset_pool_no
from server.design.beat_grid_edit import (
    _KIND_TO_POOL_KEYS,
    BeatGridEditError,
    _assert_ascii_preset_label,
    speed_master_of,
)
from server.design.beat_grid_position_presets import POSITION_GROUP_UNCONFIRMED
from server.design.beat_grid_presets import app_preset_label
from server.fx.instantiate import FxInstantiationError, build_fx_preset_bundle
from server.fx.loader import FxSchemaError, load_library_from_dir
from server.fx.schema import Fx, FxLibrary

__all__ = [
    "EFFECT_BAND_UNKNOWN",
    "EFFECT_BUILD_REFUSED",
    "EFFECT_CREATE_ON_APPLY",
    "EFFECT_DIMMER_OUT_OF_SCOPE",
    "EFFECT_GROUP_UNCONFIRMED",
    "EFFECT_LABEL_INVALID",
    "EFFECT_LABEL_MISSING",
    "EFFECT_MULTI_GROUP",
    "EFFECT_RECIPE_MISSING",
    "EFFECT_TEMPLATE_KIND_MISMATCH",
    "EFFECT_TEMPLATE_UNKNOWN",
    "EFFECT_TEMPO_MISSING",
    "default_effect_library",
    "effect_grid_blocker",
    "effect_preset_outcomes",
    "effect_preset_recipe",
    "effect_shape_of_cue",
    "effect_template_catalog",
    "effect_template_problem",
    "record_effect_preset_recipe",
    "speed_master_bpm_lines",
]

#: 보류 사유 — 승인 카드·빈 프리셋 표식·시험이 같은 값을 읽는다(t592 문구와 나란히).
EFFECT_RECIPE_MISSING = "효과 프리셋 레시피(템플릿·주기)가 없음"
EFFECT_TEMPLATE_UNKNOWN = "효과 템플릿을 라이브러리에서 찾지 못함"
EFFECT_BAND_UNKNOWN = "효과 번호대(preset_pools.yaml) 밖의 번호"
EFFECT_DIMMER_OUT_OF_SCOPE = "디머 효과 프리셋은 만들기 범위 밖(REQ-LDBEAT-015(i-6))"
EFFECT_TEMPLATE_KIND_MISMATCH = "효과 템플릿 속성이 이 번호대 종류와 맞지 않음"
EFFECT_LABEL_MISSING = "효과 프리셋 콘솔 이름(영문)이 없음"
EFFECT_LABEL_INVALID = "효과 프리셋 콘솔 이름이 영문·숫자 규칙에 맞지 않음"
EFFECT_GROUP_UNCONFIRMED = POSITION_GROUP_UNCONFIRMED
EFFECT_MULTI_GROUP = (
    "여러 그룹이 같은 효과 번호를 씀 — 여러 그룹 선택으로 만드는 꼴은 실기 선례 없음"
)
EFFECT_TEMPO_MISSING = "곡 BPM·박자가 없어 주기를 속도로 바꿀 수 없음"
EFFECT_BUILD_REFUSED = "효과 묶음을 만들 수 없음"
#: 카드 t595 넓힘 — 반영 때 만들어질 빈 효과 번호의 표식 문구.
#: 카드 t605 — t601 이 묶음 안 반복을 전부 보내게 고친 뒤로 "반영당 하나" 제약은
#: 없다(한 반영에 효과 프리셋을 몇 개 만들어도 전부 나간다). BPM 조건만 남는다.
EFFECT_CREATE_ON_APPLY = "빈 효과 프리셋 — 반영 때 템플릿·주기로 만듦(BPM 없으면 보류)"

_EFFECT_FIELD = "effect_preset_no"
_PERIOD_UNITS = ("beat", "bar")


# -- 저장 자리 -----------------------------------------------------------------


def _is_pool_slot(preset_no: object) -> bool:
    return preset_pool_no(preset_no) is not None


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def effect_preset_recipe(grid: Mapping[str, object], preset_no: str) -> dict[str, object] | None:
    """곡 격자 ``preset_fx_recipes[preset_no]``. 없거나 모양이 틀리면 ``None``
    (지어내지 않는다)."""
    recipes = grid.get("preset_fx_recipes")
    raw = recipes.get(preset_no) if isinstance(recipes, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    fx_id = raw.get("fx_id")
    unit = raw.get("period_unit")
    value = raw.get("period_value")
    if not isinstance(fx_id, str) or not fx_id.strip():
        return None
    if unit not in _PERIOD_UNITS or not _positive_int(value):
        return None
    return {"fx_id": fx_id, "period_unit": unit, "period_value": value}


def record_effect_preset_recipe(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    fx_id: str,
    period_unit: str,
    period_value: int,
) -> dict[str, object]:
    """새 효과 프리셋의 레시피를 곡 격자에 남기는 단일 저장 자리. ``grid``의 사본을
    돌려준다(원본은 그대로). 주기는 음악 단위(박·마디)만 받는다 — 초는 받지 않는다."""
    if not _is_pool_slot(preset_no):
        raise ValueError(f"'{preset_no}'은(는) pool.slot 꼴의 프리셋 번호가 아닙니다.")
    if not isinstance(fx_id, str) or not fx_id.strip():
        raise ValueError("효과 템플릿 fx_id 가 비어 있습니다.")
    if period_unit not in _PERIOD_UNITS:
        raise ValueError(f"주기 단위 {period_unit!r}는 'beat' 또는 'bar' 여야 합니다.")
    if not _positive_int(period_value):
        raise ValueError(f"주기 값 {period_value!r}는 양의 정수여야 합니다.")
    updated = dict(grid)
    existing = grid.get("preset_fx_recipes")
    recipes = dict(existing) if isinstance(existing, Mapping) else {}
    recipes[preset_no] = {
        "fx_id": fx_id.strip(),
        "period_unit": period_unit,
        "period_value": period_value,
    }
    updated["preset_fx_recipes"] = recipes
    return updated


# -- 판정 ----------------------------------------------------------------------


@lru_cache(maxsize=1)
def default_effect_library() -> FxLibrary | None:
    """출하 fx 라이브러리. 못 읽으면 ``None`` — 그 경우 모든 번호가
    「템플릿을 찾지 못함」으로 보류된다(지어낸 템플릿 0)."""
    try:
        return load_library_from_dir()
    except FxSchemaError:
        return None


#: 막대 아이콘 모양 어휘 — ``fx.schema.PATTERN_KINDS``(펄스·체이스·웨이브·스윕)와
#: 앱 무빙 모양 중 UI가 그릴 수 있는 것만. 그 밖의 값(원·대각 등)은 생략한다.
EFFECT_SHAPES: tuple[str, ...] = ("pulse", "chase", "wave", "sweep")


def effect_shape_of_cue(
    cue: Mapping[str, object],
    grid: Mapping[str, object],
    library: FxLibrary | None = None,
) -> str | None:
    """칸의 효과 모양(``EFFECT_SHAPES`` 중 하나) — 구조화 데이터에서만 파생한다.

    1. ``app_movement.shape``가 웨이브·스윕이면 그대로.
    2. ``effect_preset_no``의 레시피(``preset_fx_recipes``) → 효과 템플릿
       ``Fx.pattern``이 어휘 안이면 그대로.

    라벨 글자는 읽지 않는다. 근거가 없거나 어휘 밖이면 ``None``(지어내지 않는다)."""
    movement = cue.get("app_movement")
    if isinstance(movement, Mapping):
        shape = movement.get("shape")
        if shape in ("wave", "sweep"):
            return str(shape)
    preset_no = cue.get("effect_preset_no")
    if not isinstance(preset_no, str):
        return None
    recipe = effect_preset_recipe(grid, preset_no)
    if recipe is None:
        return None
    lib = library if library is not None else default_effect_library()
    fx = _find_fx(lib, str(recipe["fx_id"]))
    if fx is None or fx.pattern not in EFFECT_SHAPES:
        return None
    return fx.pattern


def _band_kind(preset_no: str, policy: Mapping[str, object]) -> str | None:
    """번호가 속한 효과 번호대의 종류(``position``/``color``/``dimmer``/``mixed``)."""
    pools = policy.get("pools") if isinstance(policy, Mapping) else None
    if not isinstance(pools, Mapping):
        return None
    pool_no = preset_pool_no(preset_no)
    if pool_no is None:
        return None
    slot = int(preset_no.partition(".")[2])
    for kind, keys in _KIND_TO_POOL_KEYS.items():
        for key in keys:
            band = pools.get(key)
            if not isinstance(band, Mapping):
                continue
            start, end = str(band.get("start")), str(band.get("end"))
            if preset_pool_no(start) != pool_no or preset_pool_no(end) != pool_no:
                continue
            if int(start.partition(".")[2]) <= slot <= int(end.partition(".")[2]):
                return kind
    return None


def _template_fits(kind: str, fx: Fx) -> bool:
    """번호대 종류와 템플릿 속성이 맞는가 — 위치 효과 풀엔 Pan/Tilt 만, 색 효과 풀엔
    Color 속성만, 이 곡 전용 All 풀(mixed)엔 무엇이든."""
    if kind == "mixed":
        return True
    if kind == "position":
        return set(fx.attributes) <= {"Pan", "Tilt"}
    if kind == "color":
        return all(name.startswith("Color") for name in fx.attributes)
    if kind == "wave":
        # 웨이브 번호대(풀 21) — 디머 웨이브(Dimmer)와 컬러 웨이브(Color*)가 맞는다.
        return all(name == "Dimmer" or name.startswith("Color") for name in fx.attributes)
    return False


def _referencing_tracks(grid: Mapping[str, object], preset_no: str) -> list[Mapping[str, object]]:
    """``preset_no``를 효과 번호로 가리키는 칸이 하나라도 있는 트랙 **전부**(이미
    승인된 칸 포함 — t592 리드 지적과 같은 이유)."""
    return [
        track
        for track in grid.get("tracks") or []
        if isinstance(track, Mapping)
        and any(
            isinstance(cue, Mapping) and cue.get(_EFFECT_FIELD) == preset_no
            for cue in track.get("cues") or []
        )
    ]


def _find_fx(library: FxLibrary | None, fx_id: str) -> Fx | None:
    if library is None:
        return None
    return next((fx for fx in library.fx if fx.fx_id == fx_id), None)


def _blocker_and_parts(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    library: FxLibrary | None,
    policy: Mapping[str, object],
) -> tuple[str | None, tuple[Fx, dict[str, object], str, int] | None]:
    recipe = effect_preset_recipe(grid, preset_no)
    if recipe is None:
        return EFFECT_RECIPE_MISSING, None
    fx = _find_fx(library, str(recipe["fx_id"]))
    if fx is None:
        return EFFECT_TEMPLATE_UNKNOWN, None
    kind = _band_kind(preset_no, policy)
    if kind is None:
        return EFFECT_BAND_UNKNOWN, None
    if kind == "dimmer":
        return EFFECT_DIMMER_OUT_OF_SCOPE, None
    if not _template_fits(kind, fx):
        return EFFECT_TEMPLATE_KIND_MISMATCH, None
    label = app_preset_label(grid, preset_no)
    if label is None:
        return EFFECT_LABEL_MISSING, None
    try:
        _assert_ascii_preset_label(label)
    except BeatGridEditError:
        return EFFECT_LABEL_INVALID, None
    tracks = _referencing_tracks(grid, preset_no)
    if any(not track.get("group_no_confirmed") for track in tracks):
        return EFFECT_GROUP_UNCONFIRMED, None
    groups = {track.get("group_no") for track in tracks}
    if len(groups) != 1:
        return EFFECT_MULTI_GROUP, None
    (group,) = groups
    if not _positive_int(group):
        return EFFECT_GROUP_UNCONFIRMED, None
    return None, (fx, recipe, label, int(group))  # type: ignore[arg-type]


#: 카드 t603 — 「＋ 새 프리셋 만들기」 창이 고를 수 있는 번호대 종류(디머는 범위 밖, (i-6)).
_CATALOG_KINDS = ("position", "color", "mixed")


def effect_template_catalog(library: FxLibrary | None = None) -> list[dict[str, object]]:
    """카드 t603 — 창이 고르는 효과 틀 목록. 출하 fx 라이브러리 그대로(콘솔 판독 0).
    ``kinds``는 그 틀을 쓸 수 있는 번호대 종류 — ``_template_fits``와 같은 판정이라
    화면이 고를 수 있는 틀과 반영이 받아 주는 틀이 어긋나지 않는다."""
    library = default_effect_library() if library is None else library
    if library is None:
        return []
    return [
        {
            "fx_id": fx.fx_id,
            "display_name": fx.display_name,
            "attributes": list(fx.attributes),
            "kinds": [kind for kind in _CATALOG_KINDS if _template_fits(kind, fx)],
        }
        for fx in library.fx
    ]


def effect_template_problem(fx_id: str, kind: str, library: FxLibrary | None = None) -> str | None:
    """카드 t603 — 창에서 고른 틀을 그 칸의 효과 종류(번호대)에 쓸 수 있나. 반영 때
    ``_blocker_and_parts``가 내는 것과 같은 사유 문자열을 돌려준다(없으면 ``None``)."""
    library = default_effect_library() if library is None else library
    fx = _find_fx(library, fx_id)
    if fx is None:
        return EFFECT_TEMPLATE_UNKNOWN
    if kind == "dimmer":
        return EFFECT_DIMMER_OUT_OF_SCOPE
    if not _template_fits(kind, fx):
        return EFFECT_TEMPLATE_KIND_MISMATCH
    return None


def effect_grid_blocker(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    library: FxLibrary | None,
    policy: Mapping[str, object],
) -> str | None:
    """콘솔을 읽지 않고 격자만으로 알 수 있는 만들기 걸림돌(레시피·템플릿·번호대·이름·
    그룹). ``None``이면 남은 조건은 반영 때 아는 곡 BPM·박자와 같은 묶음의 다른 효과뿐이다.
    격자의 「빈 프리셋」 표식(카드 t595)이 「반영 때 만듦」을 가를 때 쓴다."""
    blocker, _parts = _blocker_and_parts(grid, preset_no, library=library, policy=policy)
    return blocker


def _one(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    library: FxLibrary | None,
    policy: Mapping[str, object],
    bpm: float | None,
    beats_per_bar: int | None,
) -> tuple[tuple[str, ...] | None, str | None]:
    blocker, parts = _blocker_and_parts(grid, preset_no, library=library, policy=policy)
    if blocker is not None or parts is None:
        return None, blocker
    fx, recipe, label, group = parts
    if bpm is None or not math.isfinite(bpm) or bpm <= 0:
        return None, EFFECT_TEMPO_MISSING
    beats_per_cycle = int(recipe["period_value"])  # type: ignore[call-overload]
    if recipe["period_unit"] == "bar":
        if beats_per_bar is None or beats_per_bar <= 0:
            return None, EFFECT_TEMPO_MISSING
        beats_per_cycle *= beats_per_bar
    master = speed_master_of(policy)
    head: tuple[str, ...] = ()
    if master is None:
        timed = dataclasses.replace(fx, speed=bpm / beats_per_cycle, speed_master=None)
    else:
        # 스피드 마스터에 묶는다(REQ-LDRHYTHM-009): 마스터 BPM = 곡 BPM, 한 바퀴 박 수 = Measure.
        # 실기 근거 — `Master 3.15 At BPM 112.35` OK(t516 live_write), `At Measure 1`·
        # `At SpeedMaster 15`·`Store Preset` OK(t531 live P4), Measure 4 느림·1 빠름(t516 감독).
        timed = dataclasses.replace(
            fx, speed=None, speed_master=master, measure=float(beats_per_cycle)
        )
        head = (f"Master 3.{master} At BPM {bpm:g}",)
    pool, _sep, slot = preset_no.partition(".")
    try:
        bundle = build_fx_preset_bundle(
            timed, group=group, preset_pool=int(pool), preset=int(slot), label=label
        )
    except FxInstantiationError as error:
        return None, f"{EFFECT_BUILD_REFUSED}({error.reason})"
    return head + tuple(bundle.commands), None


def speed_master_bpm_lines(
    grid: Mapping[str, object], *, policy: Mapping[str, object], bpm: float | None
) -> tuple[str, ...]:
    """격자에 효과 프리셋을 쓰는 칸이 있으면 스피드 마스터 BPM 을 곡 BPM 으로 맞추는 줄 하나.

    효과 프리셋은 스피드 마스터에 묶여(``At SpeedMaster``) 콘솔에 남으므로, 다시 쓰는 프리셋은
    만들기 줄이 없다 — 그래도 마스터 BPM 은 반영마다 이 곡 BPM 으로 맞춰야 한다(4차 전체 실행
    D-12: 재사용 반영에 ``Master 3.15 At BPM`` 0건). 이 곡에 스피드 마스터 번호가 없거나 BPM 을
    모르면 빈 묶음이다."""
    if bpm is None or not math.isfinite(bpm) or bpm <= 0:
        return ()
    uses_effect = any(
        _is_pool_slot(cue.get("effect_preset_no"))
        for track in grid.get("tracks") or []  # type: ignore[attr-defined]
        if isinstance(track, Mapping)
        for cue in track.get("cues") or []
        if isinstance(cue, Mapping)
    )
    if not uses_effect:
        # 효과를 쓰지 않는 격자는 스피드 마스터 번호를 정하지 않는다(배정은 필요할 때만).
        return ()
    master = speed_master_of(policy)
    return (f"Master 3.{master} At BPM {bpm:g}",) if master is not None else ()


def effect_preset_outcomes(
    grid: Mapping[str, object],
    numbers: Sequence[str],
    *,
    library: FxLibrary | None,
    policy: Mapping[str, object],
    bpm: float | None,
    beats_per_bar: int | None,
) -> dict[str, tuple[tuple[str, ...] | None, str | None]]:
    """번호마다 만들기 줄 또는 (None, 보류 사유).

    모든 효과 묶음이 같은 스텝 전환 줄(``Step 2``)을 내므로(``server/fx/library/
    movement.yaml`` 머리 주석), 한 반영에 효과 프리셋을 여럿 만들면 그 묶음들이
    서로 줄을 공유한다. 카드 t601 전에는 송신 중복 제거가 같은 묶음 안의 반복
    줄을 건너뛰어 빈 효과가 저장됐으므로(카드 t593 우회), 여기서 번호 순서로
    먼저 받은 묶음과 줄이 겹치는 번호를 다음 반영으로 미뤘다. t601 이 그 중복
    제거를 "앞선 호출에서 실행된 줄만" 건너뛰도록 고친 뒤로는 묶음 안 반복이
    승인된 그대로 전부 나가므로, 이 함수는 번호마다 독립으로 판정한다(카드
    t605)."""
    return {
        number: _one(
            grid, number, library=library, policy=policy, bpm=bpm, beats_per_bar=beats_per_bar
        )
        for number in sorted(numbers)
    }
