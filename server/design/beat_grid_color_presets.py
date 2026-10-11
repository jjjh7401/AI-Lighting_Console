"""카드 t594 — 박자 격자의 새 색 프리셋을 콘솔에 만드는 레시피
(SPEC-LDBEAT-001 REQ-LDBEAT-015(i-5), t592·t593의 세 번째 형제).

값의 출처는 곡 격자 ``preset_colors["4.n"]``(R·G·B, 0~100%, t589과 같은
저장 모양)다. 반영 시점에 그 값을 선택(그룹)+값 한 줄로 만들고, looks/
instantiate 선례(``server/fx/instantiate.py`` ``build_fx_preset_bundle``)
와 같은 꼴로 ``ClearAll`` → 선택+값 → ``Store Preset`` → ``Label Preset``
→ ``ClearAll`` 5줄을 조립한다. 콘솔 이름은 t589 와 같은
``preset_labels["4.n"]`` 자리에서 읽는다.

선택+값은 **반드시 한 줄**이다(``Group <g> ; Attribute 'ColorRGB_R' At
<r> ; Attribute 'ColorRGB_G' At <g> ; Attribute 'ColorRGB_B' At <b>``,
``aimed_commands``의 Pan+Tilt 한 줄 관행과 같다) — 이 형태는
``server/fx/instantiate.py``의 ``_SELECTED_VALUE_LINE``과 완전히
일치해 송신 중복 제거(``run_commands``)가 **절대 건너뛰지 않는**
「프로그래머 상태」 줄이 된다(``is_programmer_state``). 같은 그룹·같은
RGB를 쓰는 색 프리셋 둘이 한 반영 묶음에 있어도(카드 t601 결함류) 선택을
떼어 값만 남긴 줄이면 두 번째가 조용히 걸러지므로, 선택과 값을 가르지
않는다.

컬러 ATTRIBUTE 이름은 코드 상수가 아니라 콘솔 판독(세션
``_fixture_color_channel_names``)에서 온다 — 모듈 접두(``Main
Module#2_ColorRGB_R``)를 뗀 뒤(``server/preshow/fixture_light.py``
``_attr`` 선례와 같은 뜻) ColorRGB_R/G/B 셋이 다 있는 장비만 받는다
(CMY만 있는 리그는 보류). ColorRGB_W는 건드리지 않는다 — 알려진 한계,
화이트 채널은 이 카드 범위 밖이다.

이 모듈은 콘솔에 아무것도 쓰지 않는다 — 순수 함수뿐이다. 후보를 좁히는
일(「풀은 읽혔고 slot이 없다」로 보류된 번호로만 좁히기)은
``beat_grid_position_presets.plan_cells``가 한다 — 위치(t592)·효과(t593)
가 이미 쓰는 그 입구를 색도 그대로 재사용한다.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from server.design.beat_grid import preset_pool_no
from server.design.beat_grid_edit import BeatGridEditError, _assert_ascii_preset_label
from server.design.beat_grid_position_presets import POSITION_GROUP_UNCONFIRMED
from server.design.beat_grid_presets import app_preset_label

__all__ = [
    "COLOR_ATTRS_MISSING",
    "COLOR_CHANNELS_UNREAD",
    "COLOR_CREATE_ON_APPLY",
    "COLOR_GROUP_UNCONFIRMED",
    "COLOR_LABEL_INVALID",
    "COLOR_LABEL_MISSING",
    "COLOR_MEMBERS_UNREAD",
    "COLOR_MULTI_GROUP",
    "COLOR_RGB_MISSING",
    "color_grid_blocker",
    "color_preset_outcomes",
    "color_preset_rgb",
    "record_color_preset_rgb",
    "referencing_tracks",
]

#: 보류 사유 — 승인 카드·빈 프리셋 표식·시험이 같은 값을 읽는다(t592·t593 문구와 나란히).
COLOR_RGB_MISSING = "색 프리셋 목표 RGB 가 없음"
COLOR_LABEL_MISSING = "색 프리셋 콘솔 이름(영문)이 없음"
COLOR_LABEL_INVALID = "색 프리셋 콘솔 이름이 영문·숫자 규칙에 맞지 않음"
COLOR_GROUP_UNCONFIRMED = POSITION_GROUP_UNCONFIRMED
COLOR_MULTI_GROUP = "여러 그룹이 같은 색 번호를 씀 — 여러 그룹 선택으로 만드는 꼴은 실기 선례 없음"
COLOR_MEMBERS_UNREAD = "트랙 그룹 소속을 다 읽지 못함"
COLOR_CHANNELS_UNREAD = "장비 컬러 채널 이름을 다 읽지 못함"
COLOR_ATTRS_MISSING = "컬러(ColorRGB R/G/B) 속성이 없는 장비가 있음"
#: 카드 t595 넓힘 — 반영 때 만들어질 빈 색 번호의 표식 문구.
COLOR_CREATE_ON_APPLY = (
    "빈 색 프리셋 — 반영 때 그룹·RGB로 만듦(장비 컬러 채널을 다 읽을 때만, 못 읽으면 보류)"
)

_COLOR_FIELD = "color_preset_no"
_REQUIRED_COLOR_ATTRS = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")


# -- 저장 자리 -----------------------------------------------------------------


def _is_pool_slot(preset_no: object) -> bool:
    return preset_pool_no(preset_no) is not None


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _percent(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    if not (0 <= value <= 100):
        return None
    return float(value)


def color_preset_rgb(
    grid: Mapping[str, object], preset_no: str
) -> tuple[float, float, float] | None:
    """곡 격자 ``preset_colors[preset_no]``의 R·G·B(0~100%). 없거나 모양이
    틀리면(수가 아님·범위 밖·결측) ``None``(지어내지 않는다)."""
    colors = grid.get("preset_colors")
    raw = colors.get(preset_no) if isinstance(colors, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    r = _percent(raw.get("r"))
    g = _percent(raw.get("g"))
    b = _percent(raw.get("b"))
    if r is None or g is None or b is None:
        return None
    return (r, g, b)


def record_color_preset_rgb(
    grid: Mapping[str, object], preset_no: str, rgb: Sequence[object]
) -> dict[str, object]:
    """새 색 프리셋의 목표 RGB를 곡 격자에 남기는 단일 저장 자리. ``grid``의
    사본을 돌려준다(원본은 그대로). ``pool.slot`` 꼴이 아니거나 값이
    0~100 범위의 유한한 수 셋이 아니면 거절한다."""
    if not _is_pool_slot(preset_no):
        raise ValueError(f"'{preset_no}'은(는) pool.slot 꼴의 프리셋 번호가 아닙니다.")
    if len(rgb) != 3:
        raise ValueError("색 목표는 R·G·B 세 값이어야 합니다.")
    channels: list[float] = []
    for value in rgb:
        percent = _percent(value)
        if percent is None:
            raise ValueError(f"색 채널 값 {value!r}는 0~100 범위의 유한한 수가 아닙니다.")
        channels.append(percent)
    updated = dict(grid)
    existing = grid.get("preset_colors")
    colors = dict(existing) if isinstance(existing, Mapping) else {}
    colors[preset_no] = {"r": channels[0], "g": channels[1], "b": channels[2]}
    updated["preset_colors"] = colors
    return updated


# -- 판정 ----------------------------------------------------------------------


def referencing_tracks(grid: Mapping[str, object], preset_no: str) -> list[Mapping[str, object]]:
    """``preset_no``를 색 번호로 가리키는 칸이 하나라도 있는 트랙 **전부**(이미
    승인된 칸 포함 — 위치(t592)·효과(t593)와 같은 이유). 호출자(세션)가
    `beat_grid_position_presets.referencing_tracks`(위치 전용 필드)를
    색에 잘못 재사용하지 않도록 이 모듈이 자신의 필드로 공개한다."""
    return [
        track
        for track in grid.get("tracks") or []
        if isinstance(track, Mapping)
        and any(
            isinstance(cue, Mapping) and cue.get(_COLOR_FIELD) == preset_no
            for cue in track.get("cues") or []
        )
    ]


def _attr_name(channel_name: str) -> str:
    """``Main Module#2_ColorRGB_R`` → ``ColorRGB_R`` (모듈 접두를 뗀 속성 이름,
    ``server/preshow/fixture_light.py`` ``_attr`` 선례와 같은 뜻)."""
    if "ColorRGB_" in channel_name:
        return "ColorRGB_" + channel_name.rsplit("ColorRGB_", 1)[1]
    return channel_name.rsplit("_", 1)[-1]


def _member_color_verdict(names: Sequence[str | None] | None) -> str:
    """``"ok"``/``"unread"``/``"missing"`` — 장비 하나의 컬러 속성 판정.
    ``_color_capable_fids``(세션)와 같은 fail-closed 규율: 완전 판독 +
    R·G·B 셋 다 있음만 ``"ok"``, 완전 판독 + 부재는 ``"missing"``, 그 외
    (판독 실패·미해소 절단·무명 자식)는 모두 ``"unread"``(모르는 채널은
    켜지 않는다)."""
    if names is None or any(name is None for name in names):
        return "unread"
    attrs = {_attr_name(name) for name in names}
    return "ok" if set(_REQUIRED_COLOR_ATTRS) <= attrs else "missing"


def _grid_only_blocker_and_parts(
    grid: Mapping[str, object], preset_no: str
) -> tuple[str | None, tuple[tuple[float, float, float], str, int] | None]:
    """콘솔을 읽지 않고 격자만으로 아는 조건(RGB·이름·그룹 확인) — ``color_grid_
    blocker``와 ``_blocker_and_parts``가 공유하는 앞부분."""
    rgb = color_preset_rgb(grid, preset_no)
    if rgb is None:
        return COLOR_RGB_MISSING, None
    label = app_preset_label(grid, preset_no)
    if label is None:
        return COLOR_LABEL_MISSING, None
    try:
        _assert_ascii_preset_label(label)
    except BeatGridEditError:
        return COLOR_LABEL_INVALID, None
    tracks = referencing_tracks(grid, preset_no)
    if any(not track.get("group_no_confirmed") for track in tracks):
        return COLOR_GROUP_UNCONFIRMED, None
    groups = {track.get("group_no") for track in tracks}
    if len(groups) != 1:
        return COLOR_MULTI_GROUP, None
    (group,) = groups
    if not _positive_int(group):
        return COLOR_GROUP_UNCONFIRMED, None
    return None, (rgb, label, int(group))  # type: ignore[arg-type]


def color_grid_blocker(grid: Mapping[str, object], preset_no: str) -> str | None:
    """콘솔을 읽지 않고 격자만으로 알 수 있는 만들기 걸림돌(RGB·영문 이름·그룹
    확인). ``None``이면 남은 조건은 반영 때 읽는 그룹 소속·장비 컬러 채널뿐이다.
    격자의 「빈 프리셋」 표식(카드 t595)이 「반영 때 만듦」을 가를 때 쓴다."""
    blocker, _parts = _grid_only_blocker_and_parts(grid, preset_no)
    return blocker


def _blocker_and_parts(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    members: Mapping[str, Sequence[int]],
    channel_names: Mapping[int, Sequence[str | None] | None],
) -> tuple[str | None, tuple[tuple[float, float, float], str, int, tuple[int, ...]] | None]:
    blocker, parts = _grid_only_blocker_and_parts(grid, preset_no)
    if blocker is not None or parts is None:
        return blocker, None
    rgb, label, group = parts
    tracks = referencing_tracks(grid, preset_no)
    fids: list[int] = []
    for track in tracks:
        track_fids = members.get(str(track.get("group_name")))
        if not track_fids:
            return COLOR_MEMBERS_UNREAD, None
        fids.extend(fid for fid in track_fids if fid not in fids)
    if not fids:
        return COLOR_MEMBERS_UNREAD, None
    unread_fids = sorted(
        fid for fid in fids if _member_color_verdict(channel_names.get(fid)) == "unread"
    )
    if unread_fids:
        return f"{COLOR_CHANNELS_UNREAD}(FID {', '.join(map(str, unread_fids))})", None
    missing_fids = sorted(
        fid for fid in fids if _member_color_verdict(channel_names.get(fid)) == "missing"
    )
    if missing_fids:
        return f"{COLOR_ATTRS_MISSING}(FID {', '.join(map(str, missing_fids))})", None
    return None, (rgb, label, group, tuple(fids))


def _format_value(value: float) -> str:
    """``server/fx/instantiate.py`` ``_format_value``와 같은 뜻(정수면 정수
    문자열) — 그 함수는 비공개(언더스코어)라 교차 모듈 import 대신 짧게
    다시 쓴다(한 줄, 새 규율 아님)."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _build_bundle(
    *, group: int, rgb: tuple[float, float, float], pool: int, slot: int, label: str
) -> tuple[str, ...]:
    """looks/instantiate 선례와 같은 꼴 — ``ClearAll`` → 선택+값(한 줄) →
    ``Store Preset`` → ``Label Preset`` → ``ClearAll``. 선택+값을 한 줄로
    묶는 이유는 모듈 설명(송신 중복 제거 면제) 참조."""
    r, g, b = rgb
    selection = (
        f"Group {group} ; Attribute 'ColorRGB_R' At {_format_value(r)}"
        f" ; Attribute 'ColorRGB_G' At {_format_value(g)}"
        f" ; Attribute 'ColorRGB_B' At {_format_value(b)}"
    )
    text = label.strip()
    return (
        "ClearAll",
        selection,
        f"Store Preset {pool}.{slot}",
        f"Label Preset {pool}.{slot} '{text}'",
        "ClearAll",
    )


Outcome = tuple[tuple[str, ...] | None, str | None]


def _one(
    grid: Mapping[str, object],
    preset_no: str,
    *,
    members: Mapping[str, Sequence[int]],
    channel_names: Mapping[int, Sequence[str | None] | None],
) -> Outcome:
    blocker, parts = _blocker_and_parts(
        grid, preset_no, members=members, channel_names=channel_names
    )
    if blocker is not None or parts is None:
        return None, blocker
    rgb, label, group, _fids = parts
    pool_no = preset_pool_no(preset_no)
    assert pool_no is not None  # 걸림돌이 없으면 pool.slot 꼴이 이미 확인됐다.
    slot = int(preset_no.partition(".")[2])
    return _build_bundle(group=group, rgb=rgb, pool=pool_no, slot=slot, label=label), None


def color_preset_outcomes(
    grid: Mapping[str, object],
    numbers: Sequence[str],
    *,
    members: Mapping[str, Sequence[int]],
    channel_names: Mapping[int, Sequence[str | None] | None],
) -> dict[str, Outcome]:
    """번호마다 만들기 줄 또는 (None, 보류 사유). 선택+값이 한 줄이라
    (모듈 설명) 색 프리셋끼리는 송신 중복 제거 겹침을 막을 필요가 없다 —
    효과(t593)의 ``EFFECT_BATCH_COLLISION``과 다른 점(``Store``/``Label``
    줄은 번호가 달라 겹치지 않는다)."""
    return {
        number: _one(grid, number, members=members, channel_names=channel_names)
        for number in numbers
    }
