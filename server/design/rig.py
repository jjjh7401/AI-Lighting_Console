"""Rig profile — the layer standard rules are conditioned on
(SPEC-COPILOT-SONGSTD-001 M1, REQ R1b, docs/proposals/song-lighting-design-
standard.md §2c).

Music decides *what* a song's lighting should say; the rig decides *what it
can say at all*. Every rule in the standard is conditioned on a
:class:`RigProfile` built from four axes, read from data that already exists
elsewhere in this codebase — never inferred from a fixture's name string:

* ``inventory`` — per-type fixture counts + declared capabilities, read from
  patch records (never guessed: ``server/spatial/fixture_type.py`` already
  established that GDTF's FixtureType node carries no ``Categories`` field, so
  a "this is a strobe" call from a type name would be a guess dressed as a
  fact — the same discipline applies here: a fixture is capable of something
  only when the caller *declares* it, exactly like ``declared_layers`` below).
* ``layers`` — role -> fid mapping (RG5: operator declaration > group-name
  heuristic > single-layer degradation — never a guess).
* ``geometry`` — centroid, dominant axis and arrangement, derived from
  fixture coordinates (arrangement classification reuses
  ``server.spatial.topology.classify`` rather than reimplementing it).
* ``scale`` — a stage-proportion factor for fixed-metre constants (RG4);
  ``1.0`` and undeclared when the caller supplies none.

RG1 is the reason ``layers`` carries an explicit ``mapped`` flag and a note
when it is ``False``: a rig with no mapped layers must say so rather than
silently answering every layer-conditioned query with an empty set that reads
identically to "there really are zero key fixtures". A false violation report
destroys trust in the rule; an explicit inactive note does not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from server.spatial.schema import spatial_fixtures_from_records
from server.spatial.topology import TopologyKind, classify

#: The standard's closed layer-role vocabulary (docs/proposals/song-lighting-
#: design-standard.md §2c: "role층 → 그룹 매핑 (key/back/effect/audience)").
#: Closed on purpose — a role outside this set is a caller typo, not a new
#: role the standard recognises, and RG5 forbids guessing.
RIG_LAYER_ROLES: tuple[str, ...] = ("key", "back", "effect", "audience")

#: Where a rig's ``layers`` mapping came from (RG5 priority order, highest
#: first). A first-class field rather than something a caller has to infer
#: from "is the mapping non-empty" — the audit trail should say *why*.
RIG_LAYER_SOURCE_DECLARED = "declared"
RIG_LAYER_SOURCE_GROUP_HEURISTIC = "group_name_heuristic"
RIG_LAYER_SOURCE_SINGLE_LAYER = "single_layer_degraded"

#: Group-name aliases per role, matched case-insensitively and EXACTLY
#: (RG5: "추측 실행 금지" — no guessing). A substring match would turn a
#: console group named "Front of House" into a false hit on BOTH "key"
#: (via "front") and "audience" (via "house") from a single label that never
#: declared either — exact match keeps the heuristic conservative.
_LAYER_GROUP_ALIASES: Mapping[str, frozenset[str]] = {
    "key": frozenset({"key", "front", "keylight", "face"}),
    "back": frozenset({"back", "backlight", "rear"}),
    "effect": frozenset({"effect", "fx", "aerial", "beam"}),
    "audience": frozenset({"audience", "house", "foh"}),
}

#: RG6 default budget-scale threshold — the capable-fixture count at which
#: an instant-action / simultaneous-effect budget reaches full scale (1.0).
#: Below this the budget shrinks in proportion to what the rig actually has
#: (docs/proposals/song-lighting-design-standard.md §2c: "4대 리그의 블라인더
#: 예산 ≠ 40대 리그"). Not derived from a measured rig — a starting constant
#: a caller may override per-call via ``full_scale_at``.
RG6_FULL_BUDGET_FIXTURE_COUNT = 8

Axis = Literal["x", "y", "z"]

#: Deterministic dominant-axis tie-break order — x before y before z — the
#: same left-to-right-then-depth-then-height reading order the rest of the
#: spatial layer uses (e.g. ``server/spatial/topology.py``'s
#: ``AXIS_TIE_BREAK_ORDER``).
_AXIS_ORDER: tuple[Axis, ...] = ("x", "y", "z")


class RigProfileError(ValueError):
    """A rig-profile input is malformed or violates a closed contract."""


@dataclass(frozen=True)
class RigFixtureRecord:
    """One patched fixture's type + DECLARED capabilities.

    ``capabilities`` is never inferred from ``type_name`` — see the module
    docstring. An empty set means "not declared", not "known absent".
    """

    fid: int
    type_name: str
    capabilities: frozenset[str] = frozenset()


def rig_fixture_record_from_record(record: Mapping[str, object]) -> RigFixtureRecord:
    """Parse one patch record ``{"fid", "type_name"?, "capabilities"?}``."""
    if not isinstance(record, Mapping):
        raise RigProfileError(f"patch record must be a mapping, got {record!r}")
    fid = record.get("fid")
    if isinstance(fid, bool) or not isinstance(fid, int):
        raise RigProfileError(f"patch record 'fid' must be an int, got {fid!r}")
    type_name = record.get("type_name", "")
    if not isinstance(type_name, str):
        raise RigProfileError(f"fixture {fid} 'type_name' must be a string, got {type_name!r}")
    raw_capabilities = record.get("capabilities", ())
    valid_container = isinstance(raw_capabilities, Sequence | frozenset | set)
    if isinstance(raw_capabilities, str) or not valid_container:
        raise RigProfileError(
            f"fixture {fid} 'capabilities' must be a sequence of strings, got {raw_capabilities!r}"
        )
    capabilities = frozenset(raw_capabilities)
    if not all(isinstance(capability, str) for capability in capabilities):
        raise RigProfileError(f"fixture {fid} 'capabilities' entries must all be strings")
    return RigFixtureRecord(fid=fid, type_name=type_name, capabilities=capabilities)


@dataclass(frozen=True)
class RigInventory:
    """RG2/RG6 read surface: what the rig HAS, never what a name suggests it
    might have."""

    fixture_count: int
    type_counts: Mapping[str, int]
    capability_fids: Mapping[str, frozenset[int]]

    def has_capability(self, capability: str) -> bool:
        """RG2: is an effect vocabulary open at all on this rig?"""
        return bool(self.capability_fids.get(capability))

    def capable_fixture_count(self, capability: str) -> int:
        """RG6: how many fixtures can carry this capability's budget?"""
        return len(self.capability_fids.get(capability, frozenset()))


@dataclass(frozen=True)
class RigLayers:
    """RG1/RG5 read surface: the role -> fid mapping and where it came from."""

    mapping: Mapping[str, tuple[int, ...]]
    source: str
    mapped: bool

    def has_layer(self, role: str) -> bool:
        return bool(self.mapping.get(role))

    def fids_for(self, role: str) -> tuple[int, ...]:
        return self.mapping.get(role, ())


@dataclass(frozen=True)
class RigGeometry:
    """Placement facts derived from fixture coordinates. ``arrangement``
    reuses ``server.spatial.topology.classify`` rather than a second
    classifier — one arrangement verdict, shared.

    카드 t312 — **이 축은 계산되기만 하고 아무도 읽지 않는다.** 지어낸
    진단이 아니라 실측이다:

    * 생산자는 살아 있다 — `server/web/session.py` 의 유일한
      `build_rig_profile(...)` 호출이 이미 읽어 둔 픽스처 좌표를 넘긴다.
    * 소비자는 없다 — `grep -rn "\\.geometry" server/ ui/src` 가 10건을
      찾고 **전부** `server/tests/test_design_rig.py` 다(2026-09-07 실측).
    * 소비자가 지워진 것이 아니라 **한 번도 붙은 적이 없다** —
      `git log -S"RigGeometry" -- server/design/rig.py` 는 도입 커밋
      `8ecefec` 하나만 답한다.

    그래서 이것은 죽은 코드가 아니라 **미완의 배선**이다. 붙을 자리는
    SPEC-COPILOT-SONGSTD-001 R1c 의 Q4(공간 스토리)이고, 지금 그 자리는
    좌표를 전혀 안 본다:

    * `server/design/interview.py::_q4_candidates` 는 포지션 후보를
      음악 프로파일에서만 유도한다 — 무대가 일자든 아치든 같은 답이 나온다.
    * 같은 파일 `_rig_note` 는 인벤토리 수가 0 일 때 「무대 좌표를 기준으로
      만든 제안이에요」라고 적는다. 좌표는 실제로 한 값도 읽지 않는다 —
      **문면이 근거를 과장하고 있다.**

    무엇을 제안에 반영할지(무게중심 기준 중앙성? 지배축을 따라가는 진행?
    배치 분류별 후보 교체?)는 연출 판단이라 여기서 정하지 않는다. 배선하기
    전에 그 판단이 먼저 필요하다.
    """

    # @MX:TODO: [AUTO] RigGeometry 를 읽는 생산 소비자가 없다 — Q4 공간 스토리
    #   제안(interview._q4_candidates)과 그 근거 문면(interview._rig_note)이
    #   붙을 자리다.
    # @MX:SPEC: SPEC-COPILOT-SONGSTD-001 R1b/R1c
    # @MX:PRIORITY: P3 — 기능 결손이 아니라 미사용 축. 다만 _rig_note 의
    #   「좌표를 기준으로」 문면은 배선 전까지 근거를 과장한다.

    arrangement: TopologyKind
    arrangement_low_confidence: bool
    centroid: tuple[float, float, float] | None
    dominant_axis: Axis | None


@dataclass(frozen=True)
class RigScale:
    """RG4: fixed-metre constants scale by this factor when the caller
    declares one; otherwise the current constants hold and that fact is
    explicit (``declared=False``), never silently assumed."""

    declared: bool
    factor: float


def _build_inventory(patch: Sequence[Mapping[str, object]]) -> RigInventory:
    records = tuple(rig_fixture_record_from_record(record) for record in patch)
    type_counts: dict[str, int] = {}
    capability_fids: dict[str, set[int]] = {}
    for record in records:
        if record.type_name:
            type_counts[record.type_name] = type_counts.get(record.type_name, 0) + 1
        for capability in record.capabilities:
            capability_fids.setdefault(capability, set()).add(record.fid)
    return RigInventory(
        fixture_count=len(records),
        type_counts=dict(sorted(type_counts.items())),
        capability_fids={
            capability: frozenset(fids) for capability, fids in sorted(capability_fids.items())
        },
    )


def _build_layers(
    groups: Mapping[str, Sequence[int]],
    declared_layers: Mapping[str, Sequence[int]] | None,
) -> tuple[RigLayers, tuple[str, ...]]:
    if declared_layers:
        mapping: dict[str, tuple[int, ...]] = {}
        for role, fids in declared_layers.items():
            if role not in RIG_LAYER_ROLES:
                raise RigProfileError(
                    f"declared layer role {role!r} is not one of {RIG_LAYER_ROLES}"
                )
            if fids:
                mapping[role] = tuple(sorted(fids))
        if mapping:
            return RigLayers(mapping=mapping, source=RIG_LAYER_SOURCE_DECLARED, mapped=True), ()

    heuristic: dict[str, set[int]] = {}
    for group_name, fids in groups.items():
        key = group_name.strip().casefold()
        for role, aliases in _LAYER_GROUP_ALIASES.items():
            if key in aliases:
                heuristic.setdefault(role, set()).update(fids)
    if heuristic:
        mapping = {role: tuple(sorted(fids)) for role, fids in heuristic.items()}
        return (
            RigLayers(mapping=mapping, source=RIG_LAYER_SOURCE_GROUP_HEURISTIC, mapped=True),
            (),
        )

    notes = (
        "RG1: no layer mapping declared or inferred from group names — this "
        "rig degrades to single-layer. Layer-conditioned rules (I1-I3) and "
        "lint L6/L7 are inactive; report this explicitly rather than a "
        "false violation.",
    )
    return RigLayers(mapping={}, source=RIG_LAYER_SOURCE_SINGLE_LAYER, mapped=False), notes


def _build_geometry(coords: Sequence[Mapping[str, object]]) -> RigGeometry:
    if not coords:
        return RigGeometry(
            arrangement=None,
            arrangement_low_confidence=True,
            centroid=None,
            dominant_axis=None,
        )
    fixtures = spatial_fixtures_from_records(coords)
    xs = [fixture.x for fixture in fixtures]
    ys = [fixture.y for fixture in fixtures]
    zs = [fixture.z for fixture in fixtures]
    centroid = (sum(xs) / len(fixtures), sum(ys) / len(fixtures), sum(zs) / len(fixtures))
    spans: dict[Axis, float] = {
        "x": max(xs) - min(xs),
        "y": max(ys) - min(ys),
        "z": max(zs) - min(zs),
    }
    dominant_axis = max(_AXIS_ORDER, key=lambda axis: (spans[axis], -_AXIS_ORDER.index(axis)))
    classification = classify(fixtures)
    return RigGeometry(
        arrangement=classification.selected.kind,
        arrangement_low_confidence=classification.selected.low_confidence,
        centroid=centroid,
        dominant_axis=dominant_axis,
    )


def _build_scale(scale_factor: float | None) -> RigScale:
    if scale_factor is None:
        return RigScale(declared=False, factor=1.0)
    if isinstance(scale_factor, bool) or not isinstance(scale_factor, int | float):
        raise RigProfileError(f"scale_factor must be a number, got {scale_factor!r}")
    if scale_factor <= 0:
        raise RigProfileError(f"scale_factor must be positive, got {scale_factor!r}")
    return RigScale(declared=True, factor=float(scale_factor))


@dataclass(frozen=True)
class RigProfile:
    """``RigProfile(inventory, layers, geometry, scale)`` — the standard's
    equipment-and-design layer (spec.md R1b). Every rule the standard defines
    is conditioned on one of these four axes; nothing downstream should read
    a fixture's console name to decide what it can do."""

    inventory: RigInventory
    layers: RigLayers
    geometry: RigGeometry
    scale: RigScale
    notes: tuple[str, ...] = ()

    # -- RG1: layer rules are conditioned on whether layers are mapped -----

    def layer_rules_active(self) -> bool:
        return self.layers.mapped

    def has_layer(self, role: str) -> bool:
        return self.layers.has_layer(role)

    # -- RG2: effect vocabulary is conditioned on inventory capability -----

    def has_capability(self, capability: str) -> bool:
        return self.inventory.has_capability(capability)

    # -- RG6: instant-action / simultaneous-effect budgets scale with the --
    # -- count of fixtures that actually carry the capability --------------

    def capable_fixture_count(self, capability: str) -> int:
        return self.inventory.capable_fixture_count(capability)

    def budget_scale_factor(
        self, capability: str, *, full_scale_at: int = RG6_FULL_BUDGET_FIXTURE_COUNT
    ) -> float:
        """A ``[0, 1]`` scale for a capability-gated budget (X1/F3).

        ``capable_fixture_count(capability) / full_scale_at``, capped at
        ``1.0``. A rig with zero capable fixtures scores ``0.0`` — RG2 already
        gates the vocabulary shut in that case, and a caller that reaches this
        helper anyway should not be handed a nonzero budget for a capability
        the rig doesn't have.
        """
        if full_scale_at <= 0:
            raise RigProfileError(f"full_scale_at must be positive, got {full_scale_at!r}")
        return min(1.0, self.capable_fixture_count(capability) / full_scale_at)


def build_rig_profile(
    patch: Sequence[Mapping[str, object]],
    groups: Mapping[str, Sequence[int]],
    coords: Sequence[Mapping[str, object]],
    declared_layers: Mapping[str, Sequence[int]] | None = None,
    *,
    scale_factor: float | None = None,
) -> RigProfile:
    """Construct a :class:`RigProfile` from already-read rig data.

    Pure function — no console handle, no port, no transport import
    (matching the rest of the spatial/design layers). ``patch`` supplies
    inventory, ``groups`` + ``declared_layers`` supply layers (RG5 order:
    declaration > group-name heuristic > single-layer degradation),
    ``coords`` supplies geometry, and ``scale_factor`` supplies RG4 scale.
    """
    layers, notes = _build_layers(groups, declared_layers)
    return RigProfile(
        inventory=_build_inventory(patch),
        layers=layers,
        geometry=_build_geometry(coords),
        scale=_build_scale(scale_factor),
        notes=notes,
    )
