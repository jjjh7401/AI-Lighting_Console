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

from server.spatial.rows import SPATIAL_ROW_NOISE_SPAN
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
    # 카드 t395 — "foh" 는 `audience` 에서 여기로 옮겼다. FOH(Front of House)는
    # 객석 **뒤편에 매단 위치**를 뜻하고 비추는 대상은 무대와 연주자다 — 객석을
    # 향해 쏘는 것은 블라인더 쪽이다. 정본 §6.2 는 그 층을 **프론트 필**이라
    # 부르며(카드 t377 이 `server/looks/songcue.py` 에 구현) `key` 의 감독용
    # 라벨이 이미 "Key/Front" 이므로, 여기 두면 감독이 읽는 문장이 정본의
    # 어휘와 맞는다.
    #
    # 실측(2026-09-15, origin/main 794a161)으로 좁혀진 피해 범위: `audience`
    # 역할을 읽는 연출 규칙은 **없다** — `RigLayers` 를 읽는 프로덕션 술어 중
    # `has_layer(role)` 의 인수는 전부 `"back"` 이고(`song_cue_composer.py:635`
    # ·`:640`), `layer_rules_active()` 는 역할 무관 `mapped` 불리언이며
    # `fids_for()` 는 프로덕션 호출 0건이다. 프론트 필도 이 표를 안 쓴다(위치
    # 역할 `"프론트"` → `server/looks/roles.py` 의 별칭 `("front", "FOH")`).
    # 그래서 이 이동이 바꾸는 것은 `_confirm_song_layer_mapping` 이 감독에게
    # 보여주고 승인받는 **라벨 한 줄**이고, 그것이 이 카드의 목적이다 —
    # 발화하는 규칙이 없어도 감독이 「객석」으로 이해한 채 승인하면 그 이해가
    # 이후 판단의 전제가 된다.
    #
    # 위 주석이 경고한 "Front of House" 이중 매칭은 여전히 정확 일치가 막는다:
    # `foh` 는 `key` 의 정확 일치 토큰일 뿐이고, "Front of House" 라는 이름은
    # 어느 역할에도 걸리지 않는다.
    "key": frozenset({"key", "front", "keylight", "face", "foh"}),
    "back": frozenset({"back", "backlight", "rear"}),
    # 카드 t385 — 실측(t379): 이 리그 그룹은 KEY FOH BACK SIDE-L SIDE-R
    # SIDE-ALL MOVER-U MOVER-D MOVER-ALL WASH-U WASH-D WASH-ALL BLIND
    # STROBE HAZE ALL ODD EVEN. "strobe"/"haze" 는 정확히 일치하는 그룹
    # 이름이 있고 역할 판정에 모호함이 없어(스트로브·헤이즈는 어느 표준으로
    # 읽어도 이펙트) 추가한다 — RG5(추측 금지)가 막는 것은 부분 문자열
    # 매칭이지, 새 정확 일치 어휘가 아니다. "BLIND"(블라인더)는 일부러
    # 뺐다 — 블라인더는 관객을 향해 쏘는 장비라 "effect" 대신 "audience"
    # 역할일 수 있고, 이 표준·이 리그만으로는 어느 쪽인지 판정할 근거가
    # 없다(감독 확인 필요, 별도 카드). MOVER-U/D/ALL·WASH-U/D/ALL 은
    # 접미사가 붙어 있어 여전히 정확 일치하지 않는다 — 그 확장은
    # 접두사/부분 일치 정책 결정이 먼저 필요해 이 카드 밖(별도 카드)으로
    # 남긴다.
    "effect": frozenset({"effect", "fx", "aerial", "beam", "strobe", "haze"}),
    # 카드 t395 — "foh" 가 `key` 로 나갔다(위 주석). 이 리그에서는 `audience` 를
    # 받는 그룹이 남지 않는데, 그것이 의도한 결과다: 자격이 있는 후보(BLIND,
    # 블라인더)는 감독 확인 대기이고, 없는 역할을 있는 것처럼 세우지 않는다.
    "audience": frozenset({"audience", "house"}),
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

    카드 t312 가 「계산되기만 하고 아무도 읽지 않는다」로 적었던 축이다.
    카드 t314 에서 **소비자가 붙었다**: `server/design/interview.py` 의
    `_readable_arrangement` → `_q4_candidates` / `_q4_rig_note` 가
    SPEC-COPILOT-SONGSTD-001 R1c 의 Q4(공간 스토리)에서 이 값을 읽는다.

    무엇이 쓰이고 무엇이 안 쓰이는지:

    * `arrangement` + `arrangement_low_confidence` — **쓴다.** 판독된 배치가
      Q4 포지션 진행 후보의 **순서**를 정한다(후보 자체는 여전히 곡
      프로파일이 만든다). 확정된 컨셉은 기하보다 앞선다.
    * `spans` + `depth_width_ratio` — **쓴다.** 카드 t315 가 실었다.
      `_build_geometry` 가 이미 계산해 두고 버리던 축별 span 그대로다(다시
      재지 않는다). `interview._q4_preferred_progression` 이 깊이/폭 비를
      읽어, `arrangement` 라벨이 같아도 **실제로 폭으로 퍼진 리그**와 **깊이로
      쌓인 리그**를 가른다. 소비자 쪽에서 지어낼 수 없는 값이라 생산 지점이
      실어야 했다.
    * `centroid` · `dominant_axis` — **안 쓴다.** `dominant_axis` 는 전
      장비가 한 점에 모인 리그에서도 동률 타이브레이크로 `"x"` 를 답해
      판독 불가와 좌우 배치를 못 가른다(t314 실측). 크기가 필요한 자리는
      `spans` 가 답하므로, 이 축을 새로 읽기 시작할 이유도 없다.

    두 값 모두 **없으면 없다고 답한다.** `spans` 는 좌표가 없으면 `None`
    이고 0 으로 채우지 않는다 — 「크기가 0 인 리그」와 「재지 못한 리그」는
    다른 상태이고, 같은 값으로 답하면 소비자가 그 둘을 가를 수 없다. 같은
    이유로 `depth_width_ratio` 는 폭 span 이 잡음 수준
    (:data:`SPATIAL_ROW_NOISE_SPAN`) 이하일 때 `None` 을 답한다: 나눗셈이
    정의되지 않는 리그(전 장비 원점 포함)에 확신 있는 비를 쥐여 주지 않는다.
    """

    # @MX:ANCHOR: [AUTO] Q4 공간 스토리 제안이 이 값을 읽는다 —
    #   interview._readable_arrangement / _q4_candidates / _q4_rig_note.
    # @MX:REASON: arrangement 판독이 감독 화면의 제안 순서와 근거 문면을
    #   동시에 정한다. 판독 불가(전 장비 원점 포함)는 음악 전용 순서와 t312
    #   의 정직한 문면으로 되돌아가는 1급 경로다.
    # @MX:SPEC: SPEC-COPILOT-SONGSTD-001 R1b/R1c

    arrangement: TopologyKind
    arrangement_low_confidence: bool
    centroid: tuple[float, float, float] | None
    dominant_axis: Axis | None
    spans: Mapping[Axis, float] | None = None

    @property
    def depth_width_ratio(self) -> float | None:
        """깊이(y) span ÷ 폭(x) span, 못 낼 때는 ``None``.

        좌표계는 `server/spatial/pointing.py` 와 같다 — x 가 좌우(폭), y 가
        객석→업스테이지(깊이). 폭 span 이 :data:`SPATIAL_ROW_NOISE_SPAN`
        이하면 `None`: 나눗셈이 폭발하는 것을 막으려는 것이 아니라, 폭이
        잡음 수준인 리그에는 **답할 비가 없기** 때문이다. 전 장비가 한 점에
        모인 리그(t314 가 실기에서 읽은 모양)가 이 경로로 들어온다.
        """
        if self.spans is None:
            return None
        width = self.spans["x"]
        if width <= SPATIAL_ROW_NOISE_SPAN:
            return None
        return self.spans["y"] / width


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
            spans=None,
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
        # 카드 t315 — 이미 계산해 둔 값을 그대로 싣는다. 지배축을 고르는
        # 방식은 건드리지 않았다(위 `max` 그대로).
        spans=spans,
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
