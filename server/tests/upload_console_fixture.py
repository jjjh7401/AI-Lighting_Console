"""카드 t480 — 업로드 길(``prepare_songcue``)을 조립기 길로 태우는 가짜 콘솔.

조립기 길은 그룹·시퀀스·타임코드 풀(업로드 길이 원래 읽던 것)에 더해 리그 패치
(기구 번호·기종 능력)와 프리셋 풀(포지션 라벨·페이저 라벨·흰색 프리셋)을 읽는다.
두 기존 대역을 합쳤다:

* 그룹·시퀀스·타임코드 트리 — ``test_songcue_tool._tree`` 와 같은 모양.
* 기종 라이브러리·기구 트리 — ``test_capability_verdict._FakeConsole`` 과 같은 모양
  (MegaPointe = 팬·틸트·줌).

쓰기는 받지 않는다. 모르는 경로는 ``LookupError`` — 실제 게이트 포트가 모르는 경로에
예외를 던지는 것과 같다(``test_songcue_tool._SongCueStatePort`` 규율).
"""

from __future__ import annotations

from server.design.phaser_catalog import (
    COLOR_PHASER_SEQUENCE,
    COMBO_PHASER_SEQUENCE,
    DIMMER_PHASER_SEQUENCE,
)
from server.prechk.capability_read import CHANNEL_FUNCTION_PROPERTIES
from server.spatial.pointing import BASIC_POSITION_SEQUENCE

TYPES_ROOT = "Patch/FixtureTypes"
FIXTURE_ROOT = "Patch/Stages/1/Fixtures"
GROUPS_PATH = "DataPool/Groups"
SEQUENCES_PATH = "DataPool/Sequences"
TIMECODES_PATH = "DataPool/Timecodes"
PRESET_POOLS = "DataPool/PresetPools"

#: 포지션 풀(2)에 기본 10라벨이 앉는 첫 슬롯. ``preset_start`` 로 이 값을 준다.
POSITION_START = 21

_TYPES = {11: ("Robin MegaPointe", {1: "Pan", 2: "Tilt", 3: "Zoom", 4: "Dimmer"})}
_RANGES = {
    "Pan": ("-270.0", "270.0"),
    "Tilt": ("-125.0", "125.0"),
    "Zoom": ("42.0", "1.8"),
    "Dimmer": ("0.0", "1.0"),
}

#: 업로드 길 기본 그룹 + 블라인더 그룹(조립기 절정 블라인더가 이름으로 찾는다).
GROUPS = (
    (11, "Back Wash"),
    (12, "FOH Wash"),
    (13, "Side L"),
    (14, "Top"),
    (15, "Cyc"),
    (16, "Special"),
    (17, "BLINDER"),
)


def _payload(path: str, children: list[dict]) -> dict:
    return {
        "ok": True,
        "v": 1,
        "kind": "state",
        "path": path,
        "children": children,
        "node": {"childCount": len(children)},
        "truncated": False,
    }


def _pool(slots: dict[int, str]) -> list[dict]:
    return [{"i": slot, "name": name} for slot, name in sorted(slots.items())]


class UploadConsole:
    """``query_state`` · ``query_property`` · ``query_properties`` 를 답하는 대역.

    ``fids`` 는 패치된 기구 번호(모두 MegaPointe). ``pools`` 를 거짓으로 주면
    프리셋 풀이 비어 있는 쇼파일을 흉내낸다(라벨 판독이 실패하는 갈래).
    """

    def __init__(
        self,
        *,
        fids: tuple[int, ...] = (101, 102, 103, 104),
        sequences: tuple[int, ...] = (1, 2, 4),
        timecodes: tuple[int, ...] = (1, 3),
        groups: tuple[tuple[int, str], ...] = GROUPS,
        pools: bool = True,
    ) -> None:
        self.fixtures = {slot: fid for slot, fid in enumerate(fids, start=1)}
        self.queried: list[str] = []
        tree = {
            GROUPS_PATH: _payload(GROUPS_PATH, _pool(dict(groups))),
            SEQUENCES_PATH: _payload(
                SEQUENCES_PATH, _pool({n: f"Sequence {n}" for n in sequences})
            ),
            TIMECODES_PATH: _payload(
                TIMECODES_PATH, _pool({n: f"Timecode {n}" for n in timecodes})
            ),
        }
        if pools:
            tree[PRESET_POOLS] = _payload(
                PRESET_POOLS,
                _pool({1: "Dimmer", 2: "Position", 4: "Color", 21: "All 1"}),
            )
            tree[f"{PRESET_POOLS}/2"] = _payload(
                f"{PRESET_POOLS}/2",
                _pool(
                    {
                        POSITION_START + offset: label
                        for offset, label in enumerate(BASIC_POSITION_SEQUENCE)
                    }
                ),
            )
            color = {11 + n: label for n, (label, *_rest) in enumerate(COLOR_PHASER_SEQUENCE)}
            color[7] = "웜 화이트 (=P2)"
            color[8] = "뉴트럴 화이트 (=P3)"
            tree[f"{PRESET_POOLS}/4"] = _payload(f"{PRESET_POOLS}/4", _pool(color))
            tree[f"{PRESET_POOLS}/1"] = _payload(
                f"{PRESET_POOLS}/1",
                _pool({11 + n: label for n, (label, *_r) in enumerate(DIMMER_PHASER_SEQUENCE)}),
            )
            tree[f"{PRESET_POOLS}/21"] = _payload(
                f"{PRESET_POOLS}/21",
                _pool({11 + n: label for n, (label, *_r) in enumerate(COMBO_PHASER_SEQUENCE)}),
            )
        self._tree = tree

    # ── 열거 ────────────────────────────────────────────────────────────
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.queried.append(path)
        if path in self._tree:
            return self._tree[path]
        parts = path.split("/")
        if path == TYPES_ROOT:
            return _payload(path, [{"i": s, "name": n} for s, (n, _c) in _TYPES.items()])
        if path == FIXTURE_ROOT:
            return _payload(path, [{"i": s, "name": f"fixture {s}"} for s in self.fixtures])
        if path.startswith(TYPES_ROOT) and len(parts) >= 4 and parts[3] == "DMXModes":
            channels = _TYPES[int(parts[2])][1]
            if len(parts) == 4:
                return {"ok": True, "children": [{"i": 1, "name": "Mode 1"}]}
            if len(parts) == 6 and parts[5] == "DMXChannels":
                return {
                    "ok": True,
                    "children": [
                        {"i": slot, "name": f"Main Module_{attr}"}
                        for slot, attr in channels.items()
                    ],
                }
            if len(parts) == 7:
                return {"ok": True, "children": [{"i": 1, "name": channels[int(parts[6])]}]}
            if len(parts) == 8:
                return {
                    "ok": True,
                    "children": [{"i": 1, "name": f"{channels[int(parts[6])]} 1"}],
                }
        raise LookupError(f"unknown object path: {path}")

    # ── 단건 프로퍼티: FID + 모드 폭 ─────────────────────────────────────
    def query_property(self, path: str, name: str) -> dict:
        if path.startswith(FIXTURE_ROOT) and name == "FID":
            fid = self.fixtures.get(int(path.split("/")[-1]))
            return {"ok": False} if fid is None else {"ok": True, "value": str(fid)}
        return {"ok": True, "value": "32"}

    # ── 벌크 프로퍼티: 기구 속성 + 채널함수 범위 ─────────────────────────
    def query_properties(self, path: str, property_names) -> dict:
        parts = path.split("/")
        if path.startswith(FIXTURE_ROOT):
            slot = int(parts[-1])
            values = {
                "Patch": f"1.{slot:03d}",
                "FixtureType": "FixtureType 11",
                "Mode": "1 Mode 1",
                "Name": f"fixture {slot}",
            }
            return {
                "ok": True,
                "reads": [{"n": n, "ok": True, "v": values.get(n, "")} for n in property_names],
            }
        attr = _TYPES[int(parts[2])][1][int(parts[6])]
        low, high = _RANGES[attr]
        values = {
            "ATTRIBUTE": attr,
            "DMXFROM": "0",
            "DMXTO": "255",
            "PHYSICALFROM": low,
            "PHYSICALTO": high,
            "DEFAULT": "0",
        }
        return {
            "ok": True,
            "reads": [{"n": k, "ok": True, "v": values[k]} for k in CHANNEL_FUNCTION_PROPERTIES],
        }
