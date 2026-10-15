"""프리셋 값(색 RGB·디머·팬/틸트) 콘솔 판독 — 응답기 1.7.0 ``presetdata`` 동사.

프리셋 값은 객체 속성으로 안 읽힌다(``PRESETDATA`` ``""``, ``SELECTIONDATA`` ``{}``,
``docs/research/ma3-effects/10-preset-property-readback-sweep.md``). 읽는 길은
grandMA3 Lua 의 Object-Free 함수 ``GetPresetData(handle, false, false)`` 하나이고,
응답기는 그 테이블을 JSON 으로 창(window) 나눠 회신한다(``console/lua/PROTOCOL.md``
§4.9). 이 모듈은 (1) 창을 끝까지 읽어 테이블로 다시 맞추고, (2) 그 테이블에서
값을 **방어적으로** 뽑고, (3) 세션 안에서 결과를 기억한다. 콘솔에는 읽기만 한다.

**실기 확인 전 가정(🔴 미실측).** ``GetPresetData`` 가 onPC 2.4.2 에서 돌려주는
테이블의 정확한 모양은 이 저장소에서 아직 관측되지 않았다. 그래서 파서는 모양을
가정하지 않고 재귀로 훑어 **속성 이름**(``ColorRGB_R/G/B`` ·``ColorAdd_R/G/B`` ·
``Dimmer`` · ``Pan`` · ``Tilt``)이 붙은 숫자만 줍는다. 같은 컨테이너(딕셔너리, 또는
``{name,value}`` 쌍의 목록) 안에 R·G·B 셋이 다 있어야 색 하나로 치고, 범위(0~100)를
벗어나거나 한 채널이라도 없으면 그 색은 버린다 — 알 수 없는 모양은 빈 결과이고,
값을 지어내거나 다른 단위로 환산하지 않는다.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "PresetDataPort",
    "PresetValueCache",
    "PresetValues",
    "PositionValue",
    "parse_preset_data",
    "preset_path",
    "read_preset_table",
    "read_preset_values",
]

#: 한 프리셋을 읽을 때 따라갈 창 수의 상한 — 무한 루프 방어(창 하나가 응답 한도
#: 1900바이트라 64창이면 충분히 큰 표까지 덮는다).
PRESET_PAGE_CAP = 64

#: 한 번의 서랍 갱신에서 새로 읽을 프리셋 수의 상한(왕복 폭주 방어).
PRESET_READS_PER_REFRESH = 40

_COLOR_RGB = ("colorrgb_r", "colorrgb_g", "colorrgb_b")
_COLOR_ADD = ("coloradd_r", "coloradd_g", "coloradd_b")
_COLOR_RGB_TRIPLE = "colorrgb_rgb"
_DIMMER = "dimmer"
_PAN = "pan"
_TILT = "tilt"
_KNOWN = frozenset((*_COLOR_RGB, *_COLOR_ADD, _COLOR_RGB_TRIPLE, _DIMMER, _PAN, _TILT))
_NAME_KEYS = ("name", "attribute", "attr", "n")
_VALUE_KEYS = ("value", "val", "v")
_MAX_DEPTH = 12


@dataclass(frozen=True)
class PositionValue:
    """위치 프리셋 한 덩어리. 한쪽만 읽혔으면 다른 쪽은 ``None``(지어내지 않는다)."""

    pan: float | None
    tilt: float | None


@dataclass(frozen=True)
class PresetValues:
    """한 프리셋에서 읽은 값. 못 읽은 종류는 빈 튜플이다."""

    color_rgbs: tuple[tuple[float, float, float], ...] = ()
    dimmers: tuple[float, ...] = ()
    positions: tuple[PositionValue, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.color_rgbs or self.dimmers or self.positions)


# -- 파서 ----------------------------------------------------------------------


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def _attr_name(key: object) -> str | None:
    """``"Main Module#2_ColorRGB_R"`` → ``"colorrgb_r"`` (모듈 접두를 뗀 알려진 이름)."""
    text = str(key).strip().lower()
    for known in _KNOWN:
        if text == known or text.endswith(("_" + known, "." + known, " " + known)):
            return known
    return None


def _scalar(value: object) -> object:
    """숫자 하나로 읽히는 값(또는 ``{"value": 숫자}`` 한 겹) → 그 값. 아니면 ``None``.
    ``ColorRGB_RGB`` 용으로 숫자 셋 리스트는 그대로 돌려준다."""
    if isinstance(value, Mapping):
        for vk in _VALUE_KEYS:
            if vk in value:
                return _scalar(value[vk])
        return None
    if isinstance(value, (list, tuple)):
        numbers = [_number(item) for item in value]
        if len(numbers) == 3 and all(n is not None for n in numbers):
            return numbers
        return None
    return _number(value)


def _is_pair(node: object) -> bool:
    """``{"name": "Dimmer", "value": 50}`` 꼴 쌍인가."""
    if not isinstance(node, Mapping):
        return False
    name_key = next((k for k in _NAME_KEYS if k in node), None)
    value_key = next((k for k in _VALUE_KEYS if k in node), None)
    return name_key is not None and value_key is not None and _attr_name(node[name_key]) is not None


def _attr_map(node: object) -> dict[str, object]:
    """컨테이너 한 겹에서 {알려진 속성 이름: 숫자(또는 숫자 셋)}. 같은 이름이 둘이면
    첫 값만 쓴다(순서가 곧 우선순위)."""
    found: dict[str, object] = {}

    def take(name: str, raw: object) -> None:
        if name in found:
            return
        value = _scalar(raw)
        if value is not None:
            found[name] = value

    if isinstance(node, Mapping):
        if _is_pair(node):
            name_key = next(k for k in _NAME_KEYS if k in node)
            value_key = next(k for k in _VALUE_KEYS if k in node)
            name = _attr_name(node[name_key])
            if name is not None:
                take(name, node[value_key])
            return found
        for key, raw in node.items():
            name = _attr_name(key)
            if name is not None:
                take(name, raw)
    elif isinstance(node, (list, tuple)):
        for item in node:
            if _is_pair(item):
                assert isinstance(item, Mapping)
                name_key = next(k for k in _NAME_KEYS if k in item)
                value_key = next(k for k in _VALUE_KEYS if k in item)
                name = _attr_name(item[name_key])
                if name is not None:
                    take(name, item[value_key])
    return found


def _color_from(attrs: Mapping[str, object]) -> tuple[float, float, float] | None:
    for channels in (_COLOR_RGB, _COLOR_ADD):
        values = [attrs.get(name) for name in channels]
        if all(isinstance(v, float) for v in values):
            rgb = tuple(float(v) for v in values)  # type: ignore[arg-type]
            if all(0.0 <= v <= 100.0 for v in rgb):
                return (rgb[0], rgb[1], rgb[2])
            return None  # 읽혔지만 퍼센트가 아닌 값 — 환산하지 않고 버린다
    triple = attrs.get(_COLOR_RGB_TRIPLE)
    if isinstance(triple, list) and all(0.0 <= v <= 100.0 for v in triple):
        return (triple[0], triple[1], triple[2])
    return None


def _distinct(items: Iterable, key: Callable | None = None) -> list:
    seen: set = set()
    out: list = []
    for item in items:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def parse_preset_data(table: object) -> PresetValues:
    """``GetPresetData`` 테이블 → 값. 알 수 없는 모양은 빈 ``PresetValues``."""
    colors: list[tuple[float, float, float]] = []
    dimmers: list[float] = []
    positions: list[PositionValue] = []

    def walk(node: object, depth: int) -> None:
        if depth > _MAX_DEPTH or not isinstance(node, (Mapping, list, tuple)):
            return
        attrs = _attr_map(node)
        if attrs:
            color = _color_from(attrs)
            if color is not None:
                colors.append(color)
            dim = attrs.get(_DIMMER)
            if isinstance(dim, float) and 0.0 <= dim <= 100.0:
                dimmers.append(dim)
            pan, tilt = attrs.get(_PAN), attrs.get(_TILT)
            pan_v = pan if isinstance(pan, float) else None
            tilt_v = tilt if isinstance(tilt, float) else None
            if pan_v is not None or tilt_v is not None:
                positions.append(PositionValue(pan_v, tilt_v))
        children = node.values() if isinstance(node, Mapping) else node
        if isinstance(node, Mapping) and _is_pair(node):
            return  # 쌍은 위에서 이미 소비했다 — 값 쪽으로 더 내려가지 않는다
        for child in children:
            if isinstance(child, (Mapping, list, tuple)) and not _is_pair(child):
                walk(child, depth + 1)

    walk(table, 0)
    return PresetValues(
        color_rgbs=tuple(_distinct(colors, key=lambda c: tuple(round(v, 4) for v in c))),
        dimmers=tuple(_distinct(dimmers, key=lambda v: round(v, 4))),
        positions=tuple(_distinct(positions, key=lambda p: (p.pan, p.tilt))),
    )


# -- 읽기 ----------------------------------------------------------------------


class PresetDataPort(Protocol):
    def query_preset_data(self, path: str, *, offset: int = 0) -> dict: ...


def preset_path(preset_pools_root: str, preset_no: str) -> str | None:
    """``("DataPool/PresetPools", "4.22")`` → ``".../4/22"``. ``pool.slot`` 꼴이 아니면 ``None``."""
    pool, sep, slot = str(preset_no).partition(".")
    if not sep or not pool.isdigit() or not slot.isdigit():
        return None
    return f"{preset_pools_root.rstrip('/')}/{int(pool)}/{int(slot)}"


def read_preset_table(port: PresetDataPort, path: str) -> object | None:
    """``presetdata`` 창을 끝까지 따라가 테이블을 다시 맞춘다.

    전진의 증거는 ``offset`` 반향이다 — 반향이 없거나 어긋나거나, 창이 비었는데
    ``truncated`` 면 **전체를 못 읽은 것**이라 ``None`` 을 돌려준다(일부 창만으로
    색 목록을 만들면 스와치가 거짓이 된다). 예외는 호출자에게 그대로 올라간다.
    """
    merged: object | None = None
    offset = 0
    for _ in range(PRESET_PAGE_CAP):
        payload = port.query_preset_data(path, offset=offset)
        if not isinstance(payload, Mapping) or payload.get("ok") is not True:
            return None
        echo = payload.get("offset")
        if isinstance(echo, bool) or echo != offset:
            return None
        try:
            window = json.loads(str(payload.get("data", "")))
        except ValueError:
            return None
        if isinstance(window, list):
            if merged is None:
                merged = []
            if not isinstance(merged, list):
                return None
            merged.extend(window)
            received = len(window)
        elif isinstance(window, dict):
            if merged is None:
                merged = {}
            if not isinstance(merged, dict):
                return None
            merged.update(window)
            received = len(window)
        else:
            return None
        if not payload.get("truncated"):
            return merged
        if received == 0:
            return None
        offset += received
    return None


def read_preset_values(
    port: PresetDataPort, preset_pools_root: str, preset_no: str
) -> PresetValues | None:
    """프리셋 하나의 값을 읽는다. 전체를 못 읽었으면 ``None``, 읽었는데 알아볼 값이
    없으면 빈 ``PresetValues``. 콘솔 오류(타임아웃·낡은 응답기)는 예외로 올라간다."""
    path = preset_path(preset_pools_root, preset_no)
    if path is None:
        return None
    table = read_preset_table(port, path)
    if table is None:
        return None
    return parse_preset_data(table)


# -- 세션 기억 -----------------------------------------------------------------


class PresetValueCache:
    """세션 안에서 프리셋 번호 → 읽은 값을 기억한다(읽기 결과만 — 쓰기와 무관).

    「읽혔고 알아볼 값이 없다」(빈 ``PresetValues``)도 기억해 같은 프리셋을 되풀이해
    묻지 않는다. 예외로 끝난 읽기와 「전체를 못 읽음」(``None``)은 기억하지 않는다
    (다음 갱신에서 다시 시도한다). 프리셋을 다시 저장하면 값이 바뀌므로
    ``invalidate`` 로 지운다.
    """

    def __init__(self) -> None:
        self._values: dict[str, PresetValues] = {}

    def get(self, preset_no: object) -> PresetValues | None:
        return self._values.get(str(preset_no))

    def colors(self, preset_no: object) -> tuple[tuple[float, float, float], ...] | None:
        """기억된 색 목록. 모르거나 색이 없으면 ``None``."""
        values = self.get(preset_no)
        return values.color_rgbs if values is not None and values.color_rgbs else None

    def put(self, preset_no: object, values: PresetValues) -> None:
        self._values[str(preset_no)] = values

    def invalidate(self, preset_no: object | None = None) -> None:
        if preset_no is None:
            self._values.clear()
        else:
            self._values.pop(str(preset_no), None)

    def refresh(
        self,
        port: PresetDataPort,
        preset_pools_root: str,
        preset_nos: Sequence[object],
        *,
        limit: int = PRESET_READS_PER_REFRESH,
    ) -> None:
        """아직 모르는 프리셋만 읽어 채운다. 콘솔 오류가 나면 거기서 멈춘다(낡은 응답기가
        모든 프리셋마다 타임아웃을 물리지 않도록) — 이미 채운 것은 남는다."""
        reads = 0
        for preset_no in preset_nos:
            key = str(preset_no)
            if key in self._values:
                continue
            if reads >= limit:
                return
            reads += 1
            try:
                values = read_preset_values(port, preset_pools_root, key)
            except Exception:  # noqa: BLE001 — 읽기 전용 보조 정보, 실패는 「모름」
                return
            if values is not None:
                self._values[key] = values
