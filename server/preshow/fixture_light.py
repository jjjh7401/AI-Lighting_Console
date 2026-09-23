"""「401 왜 안 켜져?」 — 한 기구의 점등 조건을 콘솔에서 읽기만으로 점검한다 (t451).

입력은 t450 판정서(``.moai/reports/t450/verdict.md`` §1)의 점검 표와 판독 순서다.
t450 이후 정정 한 가지를 반영했다: 이 쇼의 3D 창에서는 **다른 기구가 켜진다.**
그래서 핵심 단계는 「켜지는 기구와 나란히 읽어 차이를 찾는 것」이고, 네트워크
DMX 출력(``OUT``)은 외부 출력용 참고로만 적는다 — 내장 3D 창의 원인으로 올리지
않는다.

## 이 모듈이 하지 않는 것

- **콘솔 쓰기.** 쓰는 포트를 받지 않고, 쓰기 경로를 import 하지 않는다.
- **읽지 못한 것을 판정하기.** 읽기 실패는 ``unknown`` 이지 ``abnormal`` 이 아니다.
  기구의 **현재** 디머·셔터·색 값은 응답기가 프로그래머 값을 비추지 못해(t442·t450
  §3) 늘 「미확인」이다. 채널 **기본값**은 기구 타입에서 읽히므로 그것으로 조건을
  말한다.
- **감독 눈에만 보이는 것을 지어내기.** 3D 창의 Beam 페이더·GPU 경고·대조군 기구
  번호는 ``app_cannot_check`` 로 「볼 곳」과 함께 돌려준다.

## 상태 여섯

``ok`` 정상 · ``abnormal`` 읽은 값이 점등을 막는다 · ``candidate`` 막을 수 있으나
확정은 못 한다 · ``info`` 참고 · ``unknown`` 못 읽었다 · ``app_cannot_check`` 앱이
읽을 통로가 없다.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from server.prechk.query import read_properties
from server.rig.paging import paged_children

__all__ = [
    "ABSENT_PROBE_PATH",
    "DMX24_PER_STEP",
    "Finding",
    "LightDiagnosis",
    "diagnose_fixture_light",
]

#: 계기 생존 확인용 날조 경로 — 살아 있는 응답기는 반드시 거절한다.
ABSENT_PROBE_PATH = "ShowData/__t451_no_such_object__"

#: 응답기가 주는 채널 값은 24비트다. 이 값으로 나누면 0~255 DMX 가 된다(t442 diag3 실측:
#: open 526344..986895 = DMX 8..15).
DMX24_PER_STEP = 65793

_MASTERS = (
    ("grand_master", "그랜드 마스터", "ShowData/Masters/Grand/Master"),
    ("world_master", "월드 마스터", "ShowData/Masters/Grand/World"),
)
_PROTOCOLS = (
    ("Art-Net", "Root/DeviceConfigurations/DMXProtocols/ArtNet", "ArtNetDataCollect"),
    ("sACN", "Root/DeviceConfigurations/DMXProtocols/sACN", "sACNDataCollect"),
)
_FIXTURE_PROPS = ("FID", "NAME", "PATCH", "FIXTURETYPE", "MODE", "MASTERREACT", "VISIBLE3D")
_STATUSES = frozenset({"ok", "abnormal", "candidate", "info", "unknown", "app_cannot_check"})

_PROGRAMMER_UNREAD = (
    "미확인 — 응답기는 프로그래머에 들어간 값(디머·셔터·색)을 비추지 못한다(t442·t450 §3). "
    "콘솔의 기구 시트(Fixture Sheet)에서 이 기구 줄을 보라."
)


@dataclass(frozen=True)
class Finding:
    key: str
    label: str
    status: str
    path: str = ""
    verb: str = ""
    observed: str = ""
    detail: str = ""
    where_to_look: str = ""

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError(f"unknown finding status {self.status!r}")

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "path": self.path,
            "verb": self.verb,
            "observed": self.observed,
            "detail": self.detail,
            "where_to_look": self.where_to_look,
        }


@dataclass
class LightDiagnosis:
    fid: int
    compare_fid: int | None
    findings: list[Finding] = field(default_factory=list)
    stopped: str | None = None

    @property
    def summary(self) -> str:
        return _summarize(self)

    def to_dict(self) -> dict:
        return {
            "fid": self.fid,
            "compare_fid": self.compare_fid,
            "stopped": self.stopped,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }


@dataclass(frozen=True)
class _Fixture:
    fid: int
    slot: int
    path: str
    props: dict[str, str]
    channels: list[str] | None  # None = 못 읽음
    channels_path: str
    defaults: dict[str, int | None]  # 채널 이름 → DMX 0~255 기본값(못 읽으면 None)


# -- 판독 ---------------------------------------------------------------------


def _read(port, path: str, names: tuple[str, ...]) -> dict[str, str | None]:
    reads = read_properties(port, path, names)
    return {name: (read.value if read.ok else None) for name, read in reads.items()}


def _instrument(state_port) -> Finding | None:
    """계기 생존 — 양성 대조(``ShowData``)가 읽히고 날조 경로가 거절돼야 한다."""
    try:
        state_port.query_state("ShowData")
    except Exception as error:  # noqa: BLE001 — 어떤 실패든 「콘솔 응답 없음」이다
        return Finding(
            "instrument",
            "콘솔 응답",
            "abnormal",
            "ShowData",
            "state",
            observed=str(error),
            detail="콘솔이 응답하지 않는다. 이후 판독을 하지 않았다.",
        )
    try:
        state_port.query_state(ABSENT_PROBE_PATH)
    except Exception as error:  # noqa: BLE001
        if "path segment not found" in str(error):
            return None
        return Finding(
            "instrument",
            "콘솔 응답",
            "abnormal",
            ABSENT_PROBE_PATH,
            "state",
            observed=str(error),
            detail="없는 경로에 대한 거절이 예상과 다른 형태로 왔다. 판독을 믿을 수 없어 멈췄다.",
        )
    return Finding(
        "instrument",
        "콘솔 응답",
        "abnormal",
        ABSENT_PROBE_PATH,
        "state",
        observed="ok",
        detail="없는 경로를 콘솔이 받아들였다. 판독을 믿을 수 없어 멈췄다.",
    )


def _find_slot(state_port, property_port, fixtures_path: str, fid: int) -> tuple[int | None, str]:
    """패치에서 ``FID == fid`` 인 칸을 찾는다. 이름이 번호로 끝나는 칸부터 확인한다."""
    try:
        first = state_port.query_state(fixtures_path)
    except Exception as error:  # noqa: BLE001
        return None, f"기구 목록을 못 읽었다: {error}"
    children, truncated = paged_children(state_port, fixtures_path, first)
    suffix = f" {fid}"
    ordered = sorted(children, key=lambda c: not str(c.get("name", "")).endswith(suffix))
    for child in ordered:
        slot = child.get("i")
        if not isinstance(slot, int) or isinstance(slot, bool):
            continue
        value = _read(property_port, f"{fixtures_path}/{slot}", ("FID",))["FID"]
        if value is not None and value.strip() == str(fid):
            return slot, ""
    note = f"기구 {len(children)}대를 읽었다"
    return None, note + (" (목록이 끝까지 읽히지 않았다)" if truncated else "")


def _channels(state_port, path: str) -> list[tuple[int, str]] | None:
    try:
        first = state_port.query_state(path)
    except Exception:  # noqa: BLE001
        return None
    children, truncated = paged_children(state_port, path, first)
    if truncated:
        return None
    out = []
    for child in children:
        slot, name = child.get("i"), child.get("name")
        if isinstance(slot, int) and not isinstance(slot, bool) and isinstance(name, str):
            out.append((slot, name))
    return out


def _attr(channel_name: str) -> str:
    """``Main Module#2_ColorRGB_R`` → ``ColorRGB_R`` (모듈 접두를 뗀 속성 이름)."""
    if "ColorRGB_" in channel_name:
        return "ColorRGB_" + channel_name.rsplit("ColorRGB_", 1)[1]
    return channel_name.rsplit("_", 1)[-1]


def _to_dmx(raw: str | None) -> int | None:
    try:
        return round(int(raw) / DMX24_PER_STEP) if raw is not None else None
    except ValueError:
        return None


def _read_fixture(state_port, property_port, fixtures_path, types_path, fid, slot) -> _Fixture:
    path = f"{fixtures_path}/{slot}"
    props = {k: v for k, v in _read(property_port, path, _FIXTURE_PROPS).items() if v is not None}
    type_match = re.fullmatch(r"FixtureType\s+(\d+)", props.get("FIXTURETYPE", "").strip())
    mode_match = re.match(r"(\d+)(?:\s|$)", props.get("MODE", "").strip())
    channels_path = ""
    channels: list[str] | None = None
    defaults: dict[str, int | None] = {}
    if type_match and mode_match:
        channels_path = (
            f"{types_path}/{type_match.group(1)}/DMXModes/{mode_match.group(1)}/DMXChannels"
        )
        listed = _channels(state_port, channels_path)
        if listed is not None:
            channels = [name for _, name in listed]
            for index, name in listed:
                attr = _attr(name)
                if "ColorRGB_" in name or attr in ("Dimmer",):
                    raw = _read(property_port, f"{channels_path}/{index}/1/1", ("DEFAULT",))[
                        "DEFAULT"
                    ]
                    defaults[attr] = _to_dmx(raw)
    return _Fixture(fid, slot, path, props, channels, channels_path, defaults)


def _truthy(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    return None


def _int(value: str | None) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except ValueError:
        return None


# -- 항목별 판정 --------------------------------------------------------------


def _masters(property_port) -> list[Finding]:
    out = []
    for key, label, path in _MASTERS:
        raw = _read(property_port, path, ("NORMEDVALUE",))["NORMEDVALUE"]
        value = _int(raw)
        if value is None:
            out.append(
                Finding(key, label, "unknown", path, "props NORMEDVALUE", raw or "", "읽지 못했다.")
            )
        elif value <= 0:
            out.append(
                Finding(
                    key,
                    label,
                    "abnormal",
                    path,
                    "props NORMEDVALUE",
                    str(value),
                    f"{label}가 0 이다 — 이 마스터에 묶인 모든 출력이 꺼진다.",
                )
            )
        else:
            out.append(Finding(key, label, "ok", path, "props NORMEDVALUE", str(value)))
    return out


def _output(state_port, property_port, universe: int | None) -> list[Finding]:
    """네트워크 DMX 출력 — 외부 조명기·외부 시각화용 참고. 내장 3D 원인으로 올리지 않는다."""
    outs, lines, unread = [], [], []
    for name, path, collect in _PROTOCOLS:
        out_flag = _truthy(_read(property_port, path, ("OUT",))["OUT"])
        if out_flag is None:
            unread.append(name)
        outs.append(f"{name} OUT={out_flag if out_flag is not None else '?'}")
        try:
            first = state_port.query_state(f"{path}/{collect}")
        except Exception:  # noqa: BLE001
            unread.append(f"{name} 줄")
            continue
        children, _ = paged_children(state_port, f"{path}/{collect}", first)
        for child in children:
            slot = child.get("i")
            vals = _read(
                property_port, f"{path}/{collect}/{slot}", ("ENABLED", "LOCALUNIVERSE", "AMOUNT")
            )
            lines.append(
                (
                    name,
                    out_flag,
                    _truthy(vals["ENABLED"]),
                    _int(vals["LOCALUNIVERSE"]),
                    _int(vals["AMOUNT"]),
                )
            )
    any_out = any("OUT=True" in o for o in outs)
    note = "외부 조명기·외부 시각화로 나가는 출력이다. 콘솔 내장 3D 창의 원인이 아니다."
    findings = [
        Finding(
            "dmx_output",
            "DMX 네트워크 출력",
            "info" if not unread else "unknown",
            "Root/DeviceConfigurations/DMXProtocols/<ArtNet|sACN>",
            "props OUT",
            " · ".join(outs),
            ("켜져 있다. " if any_out else "꺼져 있다. ") + note,
        ),
    ]
    if universe is None:
        findings.append(
            Finding(
                "universe_coverage",
                "출력 줄이 기구 유니버스를 덮나",
                "unknown",
                detail="기구 유니버스를 못 읽었다.",
            )
        )
        return findings
    covering = [
        f"{n}"
        for n, out, en, lu, am in lines
        if out and en and lu is not None and am is not None and lu <= universe < lu + am
    ]
    desc = (
        "; ".join(
            f"{n} ENABLED={en} 유니버스 {lu}~{(lu or 0) + (am or 0) - 1}"
            for n, _o, en, lu, am in lines
        )
        or "줄 없음"
    )
    findings.append(
        Finding(
            "universe_coverage",
            "출력 줄이 기구 유니버스를 덮나",
            "info",
            "…/DMXProtocols/<ArtNet|sACN>/<Collect>/<n>",
            "props ENABLED,LOCALUNIVERSE,AMOUNT",
            f"기구 유니버스 {universe} · {desc}",
            (
                f"{', '.join(covering)} 가 덮는다. "
                if covering
                else f"유니버스 {universe} 를 내보내는 켜진 줄이 없다. "
            )
            + note,
        )
    )
    return findings


def _fixture_findings(fx: _Fixture) -> list[Finding]:
    out = []
    visible = _truthy(fx.props.get("VISIBLE3D"))
    out.append(
        Finding(
            "visible_3d",
            "3D 표시",
            "unknown" if visible is None else ("ok" if visible else "abnormal"),
            fx.path,
            "props VISIBLE3D",
            fx.props.get("VISIBLE3D", ""),
            "" if visible is not False else "이 기구는 3D 창에 표시되지 않게 설정돼 있다.",
        )
    )
    out.append(
        Finding(
            "master_react",
            "마스터 반응",
            "info",
            fx.path,
            "props MASTERREACT",
            fx.props.get("MASTERREACT", ""),
        )
    )
    if fx.channels is None:
        out.append(
            Finding(
                "channels",
                "채널 구성",
                "unknown",
                fx.channels_path,
                "state",
                detail="기구 타입의 채널 목록을 끝까지 읽지 못했다.",
            )
        )
        return out
    attrs = [_attr(n) for n in fx.channels]
    has_dimmer = "Dimmer" in attrs
    out.append(
        Finding(
            "channels",
            "채널 구성",
            "ok" if has_dimmer else "candidate",
            fx.channels_path,
            "state",
            ", ".join(attrs),
            "" if has_dimmer else "디머 채널이 없다 — 밝기는 색 채널 값으로만 정해진다.",
        )
    )
    color = {a: v for a, v in fx.defaults.items() if a.startswith("ColorRGB_")}
    if color:
        if any(v is None for v in color.values()):
            out.append(
                Finding(
                    "color_default",
                    "색 채널 기본값",
                    "unknown",
                    fx.channels_path,
                    "props DEFAULT (<채널>/1/1)",
                    _fmt(color),
                    "일부 기본값을 못 읽었다.",
                )
            )
        elif all(v == 0 for v in color.values()):
            out.append(
                Finding(
                    "color_default",
                    "색 채널 기본값",
                    "candidate",
                    fx.channels_path,
                    "props DEFAULT (<채널>/1/1)",
                    _fmt(color),
                    "색 채널 기본값이 전부 0 이다 — 색을 주지 않으면 "
                    "디머가 100 이어도 빛이 안 난다. "
                    "지금 프로그래머의 색 값은 앱이 확인 못한다.",
                )
            )
        else:
            out.append(
                Finding(
                    "color_default",
                    "색 채널 기본값",
                    "ok",
                    fx.channels_path,
                    "props DEFAULT (<채널>/1/1)",
                    _fmt(color),
                )
            )
    return out


def _fmt(values: dict[str, int | None]) -> str:
    return ", ".join(f"{k} {v if v is not None else '?'}" for k, v in values.items())


def _shutter(state_port, property_port, fx: _Fixture) -> Finding | None:
    if not fx.channels:
        return None
    index = next((i for i, n in enumerate(fx.channels, start=1) if "_Shutter" in n), None)
    if index is None:
        return None
    base = f"{fx.channels_path}/{index}/1/1"
    try:
        first = state_port.query_state(base)
    except Exception:  # noqa: BLE001
        return Finding(
            "shutter_range",
            "셔터",
            "unknown",
            base,
            "state",
            detail="셔터 채널이 있지만 open 범위를 못 읽었다. 셔터가 닫혀 있으면 켜지지 않는다.",
        )
    sets, _ = paged_children(state_port, base, first)
    open_set = next((c for c in sets if str(c.get("name", "")).strip().lower() == "open"), None)
    if open_set is None:
        return Finding(
            "shutter_range",
            "셔터",
            "unknown",
            base,
            "state",
            detail="셔터 채널에 'open' 값 구간이 없다. 셔터가 닫혀 있으면 켜지지 않는다.",
        )
    vals = _read(property_port, f"{base}/{open_set.get('i')}", ("DMXFROM", "DMXTO"))
    lo, hi = _to_dmx(vals["DMXFROM"]), _to_dmx(vals["DMXTO"])
    return Finding(
        "shutter_range",
        "셔터 열림",
        "app_cannot_check",
        f"{base}/{open_set.get('i')}",
        "props DMXFROM,DMXTO",
        f"open = DMX {lo}~{hi}",
        "이 기구는 셔터가 있어 열려 있어야 켜진다. 지금 셔터 값은 앱이 확인 못한다.",
        where_to_look=f"콘솔 기구 시트에서 이 기구의 Shutter 가 open(DMX {lo}~{hi})인지",
    )


def _compare(target: _Fixture, other: _Fixture) -> Finding:
    diffs = []
    for key, label in (("FIXTURETYPE", "타입"), ("MODE", "모드")):
        if target.props.get(key) != other.props.get(key):
            diffs.append(f"{label}: {target.props.get(key)} ↔ {other.props.get(key)}")
    if target.channels is not None and other.channels is not None:
        mine, theirs = {_attr(n) for n in target.channels}, {_attr(n) for n in other.channels}
        if mine - theirs:
            diffs.append(f"{target.fid} 에만 있는 채널: {', '.join(sorted(mine - theirs))}")
        if theirs - mine:
            diffs.append(f"{other.fid} 에만 있는 채널: {', '.join(sorted(theirs - mine))}")
    for attr in sorted(set(target.defaults) | set(other.defaults)):
        a, b = target.defaults.get(attr), other.defaults.get(attr)
        if a is not None and b is not None and a != b:
            diffs.append(f"{attr} 기본값: {a} ↔ {b}")
    for key, label in (("VISIBLE3D", "3D 표시"), ("MASTERREACT", "마스터 반응")):
        if target.props.get(key) != other.props.get(key):
            diffs.append(f"{label}: {target.props.get(key)} ↔ {other.props.get(key)}")
    if not diffs:
        return Finding(
            "compare",
            f"켜지는 기구 {other.fid} 와 대조",
            "info",
            observed="차이 없음",
            detail=(
                "읽을 수 있는 설정에는 차이가 없다. 남은 차이는 프로그래머 값(앱이 확인 못함)이다."
            ),
        )
    return Finding(
        "compare",
        f"켜지는 기구 {other.fid} 와 대조",
        "candidate",
        observed=" · ".join(diffs),
        detail="켜지는 기구와 다른 점이다. 이 차이가 원인 후보다.",
    )


def _app_cannot_check(compare_fid: int | None) -> list[Finding]:
    control = (
        Finding(
            "control_group",
            "켜지는 기구",
            "app_cannot_check",
            detail="3D 창에서 켜지는 기구가 있는지는 앱이 볼 수 없다.",
            where_to_look=(
                "3D 창에서 지금 켜져 있는 기구 하나의 번호를 알려 주면 나란히 읽어 차이를 찾는다."
            ),
        )
        if compare_fid is None
        else None
    )
    rest = [
        Finding(
            "programmer_values",
            "지금 들어간 디머·셔터·색 값",
            "unknown",
            "Programmer",
            "",
            detail=_PROGRAMMER_UNREAD,
        ),
        Finding(
            "beam_fader",
            "3D 창 Beam 페이더",
            "app_cannot_check",
            detail="모든 기구의 빔이 안 보인다면 이것부터 본다.",
            where_to_look="3D 창 MA 로고 → Rendering Settings → Beam 페이더",
        ),
        Finding(
            "gpu_warning",
            "3D 창 GPU 경고",
            "app_cannot_check",
            where_to_look="3D 창에 OpenGL/GPU 드라이버 경고가 떠 있는지",
        ),
    ]
    return ([control] if control else []) + rest


# -- 진입점 --------------------------------------------------------------------


def diagnose_fixture_light(
    fid: int,
    *,
    state_port,
    property_port,
    compare_fid: int | None = None,
    fixtures_path: str = "Patch/Stages/1/Fixtures",
    fixture_types_path: str = "Patch/FixtureTypes",
) -> LightDiagnosis:
    """기구 ``fid`` 가 왜 안 켜지는지 원인 후보를 읽기만으로 모은다.

    ``compare_fid`` 는 감독이 「이건 켜진다」고 알려 준 기구다. 주면 두 기구를
    나란히 읽어 차이를 원인 후보로 올린다 — t450 정정 이후 이 단계가 핵심이다.
    """
    result = LightDiagnosis(fid=fid, compare_fid=compare_fid)
    add: Callable[[Finding], None] = result.findings.append

    dead = _instrument(state_port)
    if dead is not None:
        add(dead)
        result.stopped = dead.detail
        return result
    add(
        Finding(
            "instrument",
            "콘솔 응답",
            "ok",
            "ShowData · " + ABSENT_PROBE_PATH,
            "state",
            "양성 대조 읽힘 · 날조 경로 거절",
        )
    )

    slot, note = _find_slot(state_port, property_port, fixtures_path, fid)
    target = None
    if slot is None:
        add(
            Finding(
                "fixture",
                f"기구 {fid}",
                "abnormal",
                fixtures_path,
                "state + props FID",
                note,
                f"패치에서 기구 {fid} 를 찾지 못했다.",
            )
        )
    else:
        target = _read_fixture(
            state_port, property_port, fixtures_path, fixture_types_path, fid, slot
        )
        add(
            Finding(
                "fixture",
                f"기구 {fid}",
                "ok",
                target.path,
                "props " + ",".join(_FIXTURE_PROPS),
                " · ".join(
                    f"{k} {target.props.get(k, '?')}"
                    for k in ("NAME", "PATCH", "FIXTURETYPE", "MODE")
                ),
            )
        )

    if compare_fid is not None and target is not None:
        other_slot, other_note = _find_slot(state_port, property_port, fixtures_path, compare_fid)
        if other_slot is None:
            add(
                Finding(
                    "compare",
                    f"켜지는 기구 {compare_fid} 와 대조",
                    "unknown",
                    observed=other_note,
                    detail=f"패치에서 기구 {compare_fid} 를 찾지 못했다.",
                )
            )
        else:
            other = _read_fixture(
                state_port,
                property_port,
                fixtures_path,
                fixture_types_path,
                compare_fid,
                other_slot,
            )
            add(_compare(target, other))

    for finding in _masters(property_port):
        add(finding)
    if target is not None:
        for finding in _fixture_findings(target):
            add(finding)
        shutter = _shutter(state_port, property_port, target)
        if shutter is not None:
            add(shutter)

    selection = _read(property_port, "Selection", ("COUNTTOTALSELECTED",))["COUNTTOTALSELECTED"]
    add(
        Finding(
            "selection",
            "지금 선택된 기구 수",
            "info" if selection is not None else "unknown",
            "Selection",
            "props COUNTTOTALSELECTED",
            selection or "",
        )
    )

    patch = target.props.get("PATCH", "") if target else ""
    universe = _int(patch.split(".", 1)[0]) if "." in patch else None
    for finding in _output(state_port, property_port, universe):
        add(finding)
    for finding in _app_cannot_check(compare_fid):
        add(finding)
    return result


# -- 사람이 읽는 요약 ------------------------------------------------------------


def _line(f: Finding) -> str:
    text = f"- {f.label}"
    if f.observed:
        text += f": {f.observed}"
    if f.detail:
        text += f" — {f.detail}"
    if f.where_to_look:
        text += f" (볼 곳: {f.where_to_look})"
    return text


def _summarize(d: LightDiagnosis) -> str:
    if d.stopped:
        return f"기구 {d.fid} 점검을 멈췄다 — {d.stopped}"
    by = {s: [f for f in d.findings if f.status == s] for s in _STATUSES}
    lines = []
    if d.compare_fid is None:
        lines.append(
            "먼저 확인: 3D 창에서 지금 켜져 있는 다른 기구가 있나요? 번호를 알려 주면 "
            f"기구 {d.fid} 와 나란히 읽어 차이를 찾습니다."
        )
    else:
        lines.append(
            f"먼저 확인: 켜지는 기구 {d.compare_fid} 와 기구 {d.fid} 를 나란히 읽었습니다."
        )
    # 켜지는 기구와의 차이를 맨 앞에 — 설정으로 읽히는 가장 강한 판별자다.
    causes = sorted(by["abnormal"] + by["candidate"], key=lambda f: f.key != "compare")
    lines.append("")
    lines.append(f"[원인 후보 — 이상] {len(causes)}건" if causes else "[원인 후보 — 이상] 없음")
    lines += [_line(f) for f in causes]
    lines.append("")
    lines.append("[앱이 확인 못함 — 볼 곳]")
    lines += [_line(f) for f in by["app_cannot_check"] + by["unknown"]]
    info = by["info"]
    output = next((f for f in info if f.key == "dmx_output"), None)
    if output is not None and "OUT=True" not in output.observed:
        lines.append("")
        lines.append(
            "[참고 — 외부 출력용] DMX 네트워크 출력 꺼짐. 콘솔 내장 3D 창의 원인은 아니다."
        )
    if any(f.key == "beam_fader" for f in by["app_cannot_check"]):
        lines.append("")
        lines.append(
            "모든 기구가 3D 창에서 안 보인다면 3D Beam 페이더 확인부터 하세요 "
            "(3D 창 MA 로고 → Rendering Settings → Beam)."
        )
    lines.append("")
    lines.append("[정상]")
    lines += [f"- {f.label}: {f.observed}" for f in by["ok"]]
    return "\n".join(lines)
