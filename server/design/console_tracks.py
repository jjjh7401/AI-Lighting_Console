"""콘솔 그룹으로 배치 줄을 정한다 — 소속 장비 기준 (카드 WT-all-fixtures, SPEC-LDRHYTHM-001).

감독 지시(2026-10-18): 「조명장비가 있는데 마디 배치에 넣지 않는게 말이 돼? … 다음 프로젝트나
음악을 넣었을 때 같은 오류가 생기지 않도록」. 예전에는 배치할 줄이 곡별 기본 격자 파일
(``beat_grid_data/love_attack.yaml``)에서만 왔다. 그 파일에 없는 KEY·HAZE 는 곡 내내 꺼졌고,
파일이 없는 곡은 줄이 0개라 자동 배치가 거절됐다.

이 파일은 순수 함수 하나다. 콘솔을 읽지 않는다(호출자가 읽은 그룹·소속·장비 목록을 넘긴다).
그룹 이름·번호를 하나도 모른다 — 판단은 **소속 장비**로만 한다.

- 이미 있는 줄은 그대로 둔다. 그 줄의 그룹이 덮는 장비를 「덮임」으로 센다.
- 나머지 그룹을 소속 장비 수가 적은 순서(같으면 그룹 번호 순)로 본다. 덮인 장비와 하나도
  안 겹치면 새 줄로 넣는다. 묶음 그룹(전체·홀짝·「-ALL」 류)은 작은 그룹이 먼저 들어간 뒤라
  자연히 겹쳐서 빠진다 — 이름으로 가르지 않는다.
- 소속 장비가 전부 연기 장비(채널 속성으로 판정)인 그룹은 일부러 뺀다 — 감독 2026-10-18
  「이 장비는 무시해도 돼 … 연기를 만드는 장비야」. 목록에는 「일부러 뺌」으로 남긴다.
- 연기 장비는 아닌데 밝기(Dimmer) 채널이 없는 그룹도 박자 배치에 넣지 않고, 이유를 보인다.
- 끝까지 어느 줄에도 안 들어간 장비는 이유와 함께 ``uncovered`` 에 남긴다. 조용히 빠지지 않게
  하는 것이 이 파일의 목적이다.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from server.design.rig import resolve_layer_role

__all__ = [
    "REASON_INCOMPLETE",
    "REASON_NO_DIMMER",
    "REASON_NO_GROUP",
    "REASON_OVERLAP",
    "REASON_SMOKE",
    "ConsoleTrackPlan",
    "coverage_payload",
    "is_smoke_fixture",
    "plan_console_tracks",
]

REASON_INCOMPLETE = "콘솔에서 그룹 소속을 다 못 읽어 줄을 만들지 않았습니다"
REASON_SMOKE = "일부러 뺌: 연기 장비(연출 대상 아님)"
REASON_NO_DIMMER = "밝기(Dimmer) 채널이 없는 장비라 박자 배치에 넣지 않았습니다"

#: 연기 장비 채널 계열 — grandMA3 속성 이름(끝 번호를 뗀 것). 장비·그룹 이름이 아니라 **채널
#: 속성**으로 가른다(감독 2026-10-18: 「헤이즈 즉 연기를 만드는 장비」, 리드: Haze·Fan 계열).
#: 실측: 이 리그의 HAZE 기종은 Haze1·Blower1 두 채널뿐이다(`song_cue_render.py` HAZE 절).
_SMOKE_ATTRIBUTE_FAMILIES = frozenset({"haze", "fog", "smoke", "fan", "blower"})


def is_smoke_fixture(attributes: Iterable[str]) -> bool:
    """밝기(Dimmer) 채널이 없고, 채널이 전부 연기 계열(Haze·Fog·Smoke·Fan·Blower)인 장비인가."""
    families = {str(a).strip().rstrip("0123456789").casefold() for a in attributes}
    if not families or "dimmer" in families:
        return False
    return families <= _SMOKE_ATTRIBUTE_FAMILIES


REASON_OVERLAP = "이 장비가 든 그룹이 모두 다른 줄과 장비가 겹쳐 줄을 만들지 않았습니다"
REASON_NO_GROUP = "어느 콘솔 그룹에도 들어 있지 않아 줄을 만들 수 없습니다"


@dataclass(frozen=True)
class ConsoleTrackPlan:
    #: 새로 붙일 줄 — 박자 격자 트랙 모양(칸은 비어 있다), 그룹 번호 순.
    added: tuple[dict, ...]
    #: 줄로 쓰지 않은 그룹 — ``{group_no, group_name, reason}``.
    excluded: tuple[dict, ...]
    #: 어느 줄에도 안 들어간 장비 — ``{fid, group_names, reason}``, 장비 번호 순.
    uncovered: tuple[dict, ...]
    #: 판단을 막은 판독 공백(사람이 읽는 문장).
    unread: tuple[str, ...] = ()


def _key(name: object) -> str:
    return str(name or "").strip().upper()


def plan_console_tracks(
    *,
    groups: Sequence[Mapping[str, object]],
    fixture_fids: Iterable[int],
    existing_names: Iterable[str],
    dimmerless_fids: Iterable[int] = (),
    smoke_fids: Iterable[int] = (),
) -> ConsoleTrackPlan:
    """콘솔 그룹(``{group_no, group_name, member_fids, complete}``)과 패치된 장비 번호로
    새로 붙일 줄과 빠진 장비를 정한다. ``existing_names`` 는 이미 격자에 있는 줄 이름이다.
    ``smoke_fids`` 는 연기 장비(:func:`is_smoke_fixture`) — 일부러 빼고 그렇게 적는다."""
    by_key = {_key(group.get("group_name")): group for group in groups}
    existing = [_key(name) for name in existing_names]
    covered: set[int] = set()
    unread: list[str] = []
    for key in existing:
        group = by_key.get(key)
        if group is None:
            continue
        if group.get("complete") is not True:
            unread.append(
                f"줄 '{group.get('group_name')}' 의 소속 장비를 다 못 읽어 "
                "빠진 장비를 판정하지 않았습니다"
            )
            continue
        covered.update(int(fid) for fid in group.get("member_fids") or ())
    if unread:
        return ConsoleTrackPlan(added=(), excluded=(), uncovered=(), unread=tuple(unread))

    smoke = set(smoke_fids)
    no_dimmer = set(dimmerless_fids) | smoke
    candidates = [
        group
        for key, group in by_key.items()
        if key not in existing and group.get("group_no") is not None
    ]
    candidates.sort(key=lambda g: (len(g.get("member_fids") or ()), int(g["group_no"])))  # type: ignore[arg-type]

    added: list[dict] = []
    excluded: list[dict] = []
    reason_by_group: dict[str, str] = {}
    for group in candidates:
        name = str(group.get("group_name"))
        members = {int(fid) for fid in group.get("member_fids") or ()}
        reason: str | None = None
        if group.get("complete") is not True:
            reason = REASON_INCOMPLETE
        elif not members:
            continue
        elif members <= smoke:
            reason = REASON_SMOKE
        elif members <= no_dimmer:
            reason = REASON_NO_DIMMER
        elif members & covered:
            reason = REASON_OVERLAP
        if reason is not None:
            excluded.append({"group_no": group["group_no"], "group_name": name, "reason": reason})
            reason_by_group[name] = reason
            continue
        covered.update(members)
        added.append(
            {
                "group_no": group["group_no"],
                "group_no_confirmed": True,
                "group_name": name,
                "layer_role": resolve_layer_role(name),
                "cues": [],
            }
        )
    added.sort(key=lambda track: int(track["group_no"]))

    uncovered: list[dict] = []
    for fid in sorted(set(fixture_fids) - covered):
        holders = [
            group for group in candidates if fid in {int(f) for f in group.get("member_fids") or ()}
        ]
        names = [str(group.get("group_name")) for group in holders]
        reasons = [reason_by_group[n] for n in names if n in reason_by_group]
        # 더 구체적인 이유가 앞선다 — 「겹침」은 다른 이유가 없을 때만.
        reason = next((r for r in reasons if r != REASON_OVERLAP), reasons[0] if reasons else None)
        if reason is None:
            uncovered.append(
                {"fid": fid, "group_names": [], "reason": REASON_NO_GROUP, "intentional": False}
            )
            continue
        # 그 이유를 만든 그룹만 적는다(묶음 그룹까지 늘어놓으면 원인이 흐려진다).
        names = [n for n in names if reason_by_group.get(n) == reason]
        uncovered.append(
            {
                "fid": fid,
                "group_names": names,
                "reason": reason,
                "intentional": reason == REASON_SMOKE,
            }
        )
    return ConsoleTrackPlan(
        added=tuple(added), excluded=tuple(excluded), uncovered=tuple(uncovered)
    )


def coverage_payload(plan: ConsoleTrackPlan | None, *, unread: Sequence[str] = ()) -> dict:
    """화면에 실을 모양 — 빠진 장비와 이유, 새로 붙인 줄 이름, 판독 공백."""
    if plan is None:
        return {"added": [], "uncovered": [], "unread": list(unread)}
    return {
        "added": [track["group_name"] for track in plan.added],
        "uncovered": [dict(entry) for entry in plan.uncovered],
        "unread": [*plan.unread, *unread],
    }
