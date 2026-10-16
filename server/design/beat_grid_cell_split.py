"""격자 칸 하나의 왼쪽·오른쪽 따로 색 — 데이터 모양 · 검증 · 화면용 값 (순수 함수).

격자 칸(``beat_grid.tracks[].cues[]``)은 선택 키 ``split`` 을 가질 수 있다::

    split:
      left:  {color: <표준 팔레트 색 이름 또는 null>}
      right: {color: <표준 팔레트 색 이름 또는 null>}

``split`` 이 없는 칸은 지금과 똑같이 동작한다 — 이 모듈은 ``split`` 키가 있는 칸에만 닿는다.
색 이름은 :func:`server.design.color_names.resolve_color_name` 으로만 RGB 가 된다(0~100%). 이름을
못 풀면 RGB 를 지어내지 않고 ``None`` 으로 둔다.

- 검증(:func:`validate_cell_split`): 모양이 틀리면 조용히 버리지 않고 ``ValueError`` 를 올린다.
  메시지는 그룹 이름과 마디를 말한다. 저장 모양은 ``{"left": {"color": ...}, "right": {...}}``
  뿐이다 — 화면용 ``color_rgb`` 는 저장하지 않는다.
- 화면용 값(:func:`attach_cell_split_to_cues`): 서빙 경계에서 칸 사본에 쪽마다
  ``color_rgb: [r, g, b]`` 를 단다. ``split`` 이 없는 칸은 키를 만들지 않는다(``null`` 도 아니다).

콘솔에 아무것도 쓰지 않는다. 곡·리그 고유값을 하나도 담지 않는다 — 색 이름·그룹 이름은 전부
입력(격자 데이터)에서 온다.
"""

from __future__ import annotations

from collections.abc import Mapping

from server.design.color_names import resolve_color_name

__all__ = [
    "CELL_SPLIT_SIDES",
    "attach_cell_split_to_cues",
    "cell_split_side_rgb",
    "validate_cell_split",
]

#: 한 칸의 두 쪽 — 이 두 키만 있어야 한다(순서가 화면 줄 순서와 저장 순서다).
CELL_SPLIT_SIDES: tuple[str, str] = ("left", "right")

#: 한 쪽이 가질 수 있는 키는 ``color`` 하나뿐이다.
_SIDE_KEYS = frozenset({"color"})


def validate_cell_split(
    raw: object, *, group_name: object, bar: object
) -> dict[str, dict[str, str | None]] | None:
    """칸의 ``split`` 값을 검증하고 저장 모양(``left``·``right`` 각각 ``{"color"}``)으로 돌려준다.

    ``raw`` 가 ``None`` 이면 「나눔 없음」이라 ``None`` 을 돌려준다(깨진 데이터가 아니다). 그 밖에
    사전이 아니거나, 두 쪽이 정확히 ``left``·``right`` 가 아니거나, 쪽이 사전이 아니거나, 쪽에
    ``color`` 밖의 키가 있거나, ``color`` 가 문자열도 ``None`` 도 아니면 ``ValueError`` — 메시지가
    ``group_name``·``bar`` 를 말한다. 쪽에 ``color`` 키가 없으면 색 미정(``None``)으로 읽는다."""
    if raw is None:
        return None
    where = f"{group_name} {bar}마디 칸의 split"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{where} 은 left·right 를 가진 사전이어야 합니다: {raw!r}")
    missing = [side for side in CELL_SPLIT_SIDES if side not in raw]
    unknown = [key for key in raw if key not in CELL_SPLIT_SIDES]
    if missing or unknown:
        raise ValueError(
            f"{where} 은 left·right 두 쪽만 가져야 합니다 "
            f"(없는 쪽: {missing or '없음'}, 모르는 키: {unknown or '없음'})"
        )
    clean: dict[str, dict[str, str | None]] = {}
    for side in CELL_SPLIT_SIDES:
        body = raw[side]
        if not isinstance(body, Mapping):
            raise ValueError(f"{where}.{side} 는 color 를 가진 사전이어야 합니다: {body!r}")
        extra = [key for key in body if key not in _SIDE_KEYS]
        if extra:
            raise ValueError(f"{where}.{side} 에 모르는 키가 있습니다(color 만 가능): {extra}")
        color = body.get("color")
        if color is not None and not isinstance(color, str):
            raise ValueError(
                f"{where}.{side}.color 는 색 이름(문자열)이거나 null 이어야 합니다: {color!r}"
            )
        clean[side] = {"color": color}
    return clean


def cell_split_side_rgb(color: str | None) -> list[int] | None:
    """한 쪽의 색 이름 → ``[r, g, b]``(각 0~100%). 이름이 없거나 표에 없으면 ``None``."""
    if color is None:
        return None
    rgb = resolve_color_name(color)
    return list(rgb) if rgb is not None else None


def _payload_split(split: Mapping[str, Mapping[str, str | None]]) -> dict[str, object]:
    """저장 모양 → 화면용 모양 — 쪽마다 ``color`` 와 ``color_rgb``(못 풀면 ``None``)."""
    payload: dict[str, object] = {}
    for side in CELL_SPLIT_SIDES:
        color = split[side]["color"]
        payload[side] = {"color": color, "color_rgb": cell_split_side_rgb(color)}
    return payload


def attach_cell_split_to_cues(grid: Mapping[str, object]) -> dict[str, object]:
    """격자 사본의 칸(``tracks[].cues[]``)마다 ``split`` 을 화면용 모양으로 바꾼다(원본 불변).

    ``split`` 키가 없는 칸은 그 자리 그대로다. 값이 ``None`` 이면 키를 뺀다 — 출력에는 ``null`` 이
    남지 않는다. 모양이 틀린 ``split`` 은 ``ValueError`` 로 알린다(:func:`validate_cell_split`)."""
    tracks = grid.get("tracks")
    if not isinstance(tracks, list):
        return dict(grid)
    new_tracks: list[object] = []
    for track in tracks:
        cues = track.get("cues") if isinstance(track, Mapping) else None
        if not isinstance(cues, list):
            new_tracks.append(track)
            continue
        group_name = track.get("group_name")
        new_cues: list[object] = []
        for cue in cues:
            if isinstance(cue, Mapping) and "split" in cue:
                split = validate_cell_split(cue["split"], group_name=group_name, bar=cue.get("bar"))
                if split is None:
                    cue = {key: value for key, value in cue.items() if key != "split"}
                else:
                    cue = {**cue, "split": _payload_split(split)}
            new_cues.append(cue)
        new_tracks.append({**track, "cues": new_cues})
    return {**grid, "tracks": new_tracks}
