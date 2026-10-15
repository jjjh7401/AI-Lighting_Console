"""박자 격자 2D 무대 판독 — 장비 좌표 + 그룹→소속 장비 (카드 t565, SPEC-LDBEAT-001 REQ-022).

콘솔 **읽기만** 한다. 실행 포트는 받지도 않는다 — 인자로 오는 포트는
``query_state``·``query_property``·``query_properties`` 세 읽기뿐이다.

새 판독을 짓지 않는다. 세 조각 모두 이미 있는 것을 옮겨 쓴다:

- **좌표** — ``server.orchestrator.tools.read_spatial_fixtures`` (생산 지점 그대로,
  paperwork 와 같은 예산 ``SPATIAL_PROPERTY_QUERY_CAP``). ``slot_sink`` 로 fid→패치
  슬롯 주소를 함께 받는다.
- **그룹 목록** — ``server.rig.paging.paged_children`` (무진전 방어 포함).
- **그룹 소속** — 응답기 1.6.6 의 ``props <id> SELECTIONDATA <그룹> offset=<n>``
  (``console/lua/PROTOCOL.md`` §4.8). t525 프로브(``.moai/reports/t525/
  probe_groups.py``)가 앞 2칸까지 실측했고 t531 이 응답기에 나눠 읽기를 넣었다.
  여기서는 그 프로브를 서버로 올린다.
- **sf_index → fid** — 장비마다 ``SUBFIXTUREINDEX`` (t525 ``probe_patch_tree.py``
  실측, 그룹은 서브픽스처가 아니라 본체 번호를 담는다 — 8/8 일치). 본체에 대응하지
  않는 번호는 지어내지 않고 ``complete=False`` + 이유로 남긴다.

어떤 그룹을 읽는가: 박자 격자 트랙 이름과 **정확히 같은**(대소문자만 무시) 콘솔
그룹만. 이름 앞부분 추정(``MOVER`` → ``MOVER-ALL``)은 하지 않는다 — 소속을 지어내는
가장 쉬운 길이 그것이다(레인 리뷰 05ad9ec4).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from server.orchestrator.tools import SPATIAL_PROPERTY_QUERY_CAP, read_spatial_fixtures
from server.rig.paging import paged_children

__all__ = [
    "GroupSelectionRead",
    "read_beat_grid_stage",
    "read_group_selection",
]

SELECTION_PROPERTY = "SELECTIONDATA"
SUBFIXTURE_INDEX_PROPERTY = "SUBFIXTUREINDEX"
#: 한 그룹의 SELECTIONDATA 창 수 상한 — 무한 루프 방어(응답 한도 1900바이트에
#: 항목 약 80바이트면 창 하나에 20개 남짓, 64창이면 1000대를 넘는다).
SELECTION_PAGE_CAP = 64


class StageReadPort(Protocol):
    def query_state(self, path: str, *, offset: int = 0) -> dict: ...

    def query_property(self, path: str, property_name: str) -> dict: ...

    def query_properties(
        self, path: str, property_names: Sequence[str], *, offset: int | None = None
    ) -> dict: ...


@dataclass(frozen=True)
class GroupSelectionRead:
    sf_indexes: tuple[int, ...]
    complete: bool
    reason: str | None


def _selection_item(payload: object) -> Mapping[str, object] | None:
    reads = payload.get("reads") if isinstance(payload, Mapping) else None
    if not isinstance(reads, list):
        return None
    for read in reads:
        if isinstance(read, Mapping) and read.get("n") == SELECTION_PROPERTY:
            return read
    return None


def _sf_index(entry: object) -> int | None:
    value = entry.get("sf_index") if isinstance(entry, Mapping) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def read_group_selection(port: StageReadPort, group_path: str) -> GroupSelectionRead:
    """그룹 하나의 ``SELECTIONDATA`` 를 §4.8 창으로 끝까지 읽는다.

    전진의 증거는 ``offset`` 반향이다(``server.rig.paging`` 과 같은 규율) — 반향이
    없거나 요청한 값과 다르거나, 창이 비었는데 ``truncated`` 면 멈추고 받은 만큼만
    ``complete=False`` 로 돌려준다. 실패는 예외로 올리지 않고 이유로 담는다.
    """
    entries: list[object] = []
    total: int | None = None
    offset = 0
    for _page in range(SELECTION_PAGE_CAP):
        try:
            payload = port.query_properties(group_path, (SELECTION_PROPERTY,), offset=offset)
        except Exception as error:  # noqa: BLE001 — 이유를 그대로 화면에 보인다
            return _finish(
                entries,
                total,
                f"{group_path} {SELECTION_PROPERTY} 판독 실패"
                f"(응답기 1.6.6 나눠 읽기 필요): {error}",
            )
        read = _selection_item(payload)
        if read is None or read.get("ok") is not True:
            reason = (
                read.get("e") if isinstance(read, Mapping) else "응답에 SELECTIONDATA 항목이 없음"
            )
            return _finish(entries, total, f"{group_path} {SELECTION_PROPERTY} 판독 실패: {reason}")
        echo = read.get("offset")
        page_total = read.get("total")
        if (
            isinstance(echo, bool)
            or echo != offset
            or isinstance(page_total, bool)
            or not isinstance(page_total, int)
        ):
            return _finish(
                entries,
                total,
                f"{group_path} 나눠 읽기 반향이 없음 — 응답기가 1.6.6 offset 페이징을 하지 않았다",
            )
        total = page_total
        try:
            window = json.loads(str(read.get("v", "")))
        except ValueError:
            return _finish(entries, total, f"{group_path} {SELECTION_PROPERTY} 값이 JSON 이 아님")
        if not isinstance(window, list):
            return _finish(entries, total, f"{group_path} {SELECTION_PROPERTY} 값이 목록이 아님")
        if not read.get("truncated"):
            entries.extend(window)
            return _finish(entries, total, None)
        if not window:
            return _finish(
                entries, total, f"{group_path} 나눠 읽기가 진전 없이 멈춤(offset {offset})"
            )
        entries.extend(window)
        offset = len(entries)
    return _finish(entries, total, f"{group_path} 나눠 읽기 창 상한 {SELECTION_PAGE_CAP} 도달")


def _finish(entries: list[object], total: int | None, reason: str | None) -> GroupSelectionRead:
    indexes = [_sf_index(entry) for entry in entries]
    parsed = tuple(index for index in indexes if index is not None)
    if reason is None and len(parsed) != len(entries):
        reason = f"sf_index 없는 항목 {len(entries) - len(parsed)}개"
    if reason is None and total is not None and len(entries) != total:
        reason = f"받은 항목 {len(entries)}개 ≠ 전체 {total}개"
    return GroupSelectionRead(sf_indexes=parsed, complete=reason is None, reason=reason)


def _read_subfixture_indexes(
    port: StageReadPort, fixtures_path: str, slots: Mapping[int, int]
) -> tuple[dict[int, int], list[str]]:
    """fid → SUBFIXTUREINDEX. 못 읽은 장비는 이유 목록에 남긴다."""
    by_sf: dict[int, int] = {}
    failures: list[str] = []
    for fid, slot in slots.items():
        try:
            payload = port.query_properties(f"{fixtures_path}/{slot}", (SUBFIXTURE_INDEX_PROPERTY,))
        except Exception as error:  # noqa: BLE001
            failures.append(f"fid {fid} {SUBFIXTURE_INDEX_PROPERTY} 판독 실패: {error}")
            continue
        reads = payload.get("reads") if isinstance(payload, Mapping) else None
        read = next(
            (
                r
                for r in reads or []
                if isinstance(r, Mapping) and r.get("n") == SUBFIXTURE_INDEX_PROPERTY
            ),
            None,
        )
        try:
            value = int(str(read.get("v")).strip()) if read and read.get("ok") is True else None
        except ValueError:
            value = None
        if value is None:
            failures.append(f"fid {fid} {SUBFIXTURE_INDEX_PROPERTY} 값 없음")
            continue
        by_sf[value] = fid
    return by_sf, failures


def _fixture_records(reply: Mapping[str, object]) -> tuple[list[dict], str | None]:
    complete = "fixtures" in reply
    records = reply.get("fixtures") if complete else reply.get("partial_fixtures")
    out: list[dict] = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        fid = record.get("fid")
        if isinstance(fid, bool) or not isinstance(fid, int):
            continue
        try:
            out.append(
                {
                    "fid": fid,
                    "name": str(record.get("name", "")),
                    "x": float(record["x"]),  # type: ignore[arg-type]
                    "y": float(record["y"]),  # type: ignore[arg-type]
                    "z": float(record["z"]),  # type: ignore[arg-type]
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    reason = None if complete else f"장비 좌표 일부만 읽힘({len(out)}대)"
    return out, reason


def fixture_pan_tilt(capability: object) -> bool | None:
    """리그 능력 판독으로 본 「팬/틸트 기종인가」 — 모르면 ``None`` (이름으로 짐작하지 않는다).

    Pan 또는 Tilt 속성이 읽혔으면 참. 없다는 결론(거짓)은 판독이 전수(``whole``)일 때만 —
    부분 판독에서 속성이 안 보이는 것은 「없다」가 아니라 「못 읽었다」다."""
    has = getattr(capability, "has_attribute", None)
    if has is None:
        return None
    if has("Pan") or has("Tilt"):
        return True
    return False if getattr(capability, "whole", False) is True else None


def read_beat_grid_stage(
    port: StageReadPort,
    *,
    fixtures_path: str,
    groups_path: str,
    track_names: Iterable[str],
) -> dict[str, object]:
    """무대 칸 한 번 그릴 만큼을 읽는다 — ``{fixtures, groups, unread}``.

    어느 단계가 실패해도 예외를 올리지 않는다: 읽은 만큼 싣고 못 읽은 이유를
    ``unread`` 에 그대로 적는다(앱은 그 이유를 무대 칸 안내로 보인다).
    """
    unread: list[str] = []
    slots: dict[int, int] = {}
    try:
        reply = read_spatial_fixtures(
            port, port, fixtures_path, SPATIAL_PROPERTY_QUERY_CAP, slot_sink=slots
        )
    except Exception as error:  # noqa: BLE001
        return {"fixtures": [], "groups": [], "unread": [f"장비 좌표 판독 실패: {error}"]}
    fixtures, partial = _fixture_records(reply)
    if partial:
        unread.append(partial)

    wanted = {}
    for name in track_names:
        wanted.setdefault(name.upper(), name)
    try:
        first = port.query_state(groups_path)
        children, truncated = paged_children(port, groups_path, first)
    except Exception as error:  # noqa: BLE001
        unread.append(f"콘솔 그룹 목록 판독 실패: {error}")
        return {"fixtures": fixtures, "groups": [], "unread": unread}
    if truncated:
        unread.append("콘솔 그룹 목록이 잘려 일부 그룹을 못 봤을 수 있음")

    found: list[tuple[int, str]] = []
    for child in children:
        name = child.get("name")
        slot = child.get("i")
        if not isinstance(name, str) or isinstance(slot, bool) or not isinstance(slot, int):
            continue
        if name.upper() in wanted:
            found.append((slot, name))
    found_keys = {name.upper() for _, name in found}
    for key, original in wanted.items():
        if key not in found_keys:
            unread.append(f"콘솔에 '{original}' 그룹이 없음 — 소속을 지어내지 않음")
    if not found:
        return {"fixtures": fixtures, "groups": [], "unread": unread}

    by_sf, sf_failures = _read_subfixture_indexes(port, fixtures_path, slots)
    unread.extend(sf_failures)

    groups: list[dict[str, object]] = []
    for slot, name in found:
        selection = read_group_selection(port, f"{groups_path}/{slot}")
        member_fids: list[int] = []
        unmatched: list[int] = []
        for sf in selection.sf_indexes:
            fid = by_sf.get(sf)
            if fid is None:
                unmatched.append(sf)
            elif fid not in member_fids:
                member_fids.append(fid)
        complete = selection.complete and not unmatched and not sf_failures
        if selection.reason:
            unread.append(f"'{name}' 소속 일부만: {selection.reason}")
        if unmatched:
            unread.append(
                f"'{name}' sf_index {', '.join(map(str, unmatched))} 가 본체 장비에 대응 안 됨"
            )
        groups.append(
            {"group_no": slot, "group_name": name, "member_fids": member_fids, "complete": complete}
        )
    return {"fixtures": fixtures, "groups": groups, "unread": unread}
