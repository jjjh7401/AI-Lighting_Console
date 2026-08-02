"""Show-control panel server state (SHOWUI M2/M3 — REQ-SHOWUI-001..013/022..026).

Four things live here, and deliberately nothing else:

1. :func:`build_catalog` — the rig-enumerated tile list, read through the SAME
   gate-audited ``state_port`` seam ``get_rig_context`` uses, reusing that
   tool's shape helpers so the real-`no` rule, the truncation signal and the
   unopened-vs-verified-empty distinction have exactly one implementation.
2. :class:`PinStore` — the chat-pinned tiles, persisted atomically to a JSON
   file under the per-user data dir so they survive a restart.
3. :class:`PanelStore` — the two halves composed, plus the membership predicate
   M3 checks a client-supplied target against before any bundle is built.
4. :class:`PanelRuntime` (M3) — one connection's firing surface: membership →
   bundle → ``gate.screen()`` → the gate's own execution port, and the tile
   events that report what actually happened.

Chokepoint discipline (REQ-SHOWUI-007, AC-SHOWUI-006): this module holds NO
execution surface of its own. It never imports the OSC send surface, and it
never will. The ONLY way a panel press reaches the console is
``gate.screen()`` followed by ``gate.execution_port`` — the same single
screening path the chat turn uses, entered from one method
(:meth:`PanelRuntime.fire`) and nowhere else. Reads ride the injected state
port; pins go to a local file. Neither can reach the console at all.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from server.deploy.settings import user_data_dir
from server.llm.config import _CREDENTIAL_KEYS
from server.orchestrator.last_created import LastCreated
from server.orchestrator.ports import StateQueryPort
from server.orchestrator.tools import (
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    drill_into,
    rig_object,
    rig_section,
)
from server.safety.gate import SafetyGate
from server.safety.session_context import SessionKey, bind_session_key, reset_session_key
from server.web.messages import (
    PANEL_TARGET_KINDS,
    _is_object_number,
    error_event,
    panel_busy_event,
    panel_catalog_event,
    panel_item,
    panel_item_state_event,
    panel_section,
    proposal_event,
)

PIN_FILE_NAME = "panel_pins.json"

# The on-disk schema version. Bumped only on a BREAKING record change; an
# unreadable or unrecognised file degrades to an empty panel (see PinStore),
# never to a startup failure — a show must not be blocked by a pin file.
PIN_FILE_VERSION = 1

# The persisted fields of one pin. ``id`` is derived from the pair below and
# ``source`` is always "pin", so neither is stored: a stored ``id`` could drift
# out of agreement with the pair it is supposed to name.
_PIN_RECORD_FIELDS = ("kind", "target_kind", "target", "name", "appearance")

# Ceiling on second-level (page drill-down) queries per catalog build — the
# same reasoning as ``RIG_DRILLDOWN_QUERY_CAP``: each one is a UDP round trip
# through the gate + audit, so an unbounded walk would make a panel refresh
# cost scale with the size of the showfile.
PANEL_DRILLDOWN_QUERY_CAP = 16

# Every catalog tile's type badge. The rig snapshot carries a name and a number
# and nothing that separates a static look from a phaser, so the honest badge is
# the one that describes what the object IS (design.md §4 SEQ) rather than a
# guessed LOOK/FX. A wrong badge is cosmetic; a guessed one trains the operator
# to distrust all of them.
_CATALOG_ITEM_KIND = "sequence"

# Korean, because it is shown to the operator (PROTOCOL.md language rule).
PIN_SEED_UNAVAILABLE_MESSAGE = "패널에 추가할 연출이 없습니다 — 채팅에서 연출을 먼저 만들어 주세요."


class PinSeedUnavailable(RuntimeError):
    """A pin was requested but the chat has not created a look yet.

    Explicit BY DESIGN (REQ-SHOWUI-004, acceptance.md §D edge case 7): silently
    ignoring the press leaves the operator pressing a button that does nothing
    and no way to learn why.
    """

    def __init__(self, message: str = PIN_SEED_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)


class PinStoreError(ValueError):
    """A pin record was rejected before it could be written."""


@dataclass(frozen=True)
class SectionSpec:
    """One catalog source: where to read it and what it addresses."""

    name: str
    path: str
    target_kind: str
    drilldown: bool = False


# @MX:ANCHOR: [AUTO] the closed set of catalog sources. Consumed by the catalog
# builder, by the membership predicate through it, and (from M3) by every bundle
# the panel builds.
# @MX:REASON: REQ-SHOWUI-003 — "fixtures" is ABSENT here structurally, not
# filtered later: a fixture's `no` is its patch slot, not its fixture id, so a
# fixture tile would address the wrong thing on stage. A section can only become
# a tile source by being added to this tuple, and every `target_kind` here must
# be one the console actually fires (PANEL_TARGET_KINDS).
PANEL_CATALOG_SECTIONS = (
    SectionSpec(name="sequences", path="DataPool/Sequences", target_kind="sequence"),
    # A page's CHILDREN are the executors — the only surface that actually fires
    # a stored look — so this section's tiles come from the drill-down, not from
    # the pages themselves.
    SectionSpec(name="pages", path="DataPool/Pages", target_kind="executor", drilldown=True),
    # SPEC-COPILOT-DASHUI-001 REQ-DASHUI-012/plan.md M2 — macro press joins the
    # closed set of fireable classes (additive: PANEL_TARGET_KINDS was already
    # widened at M1). Every macro the console has becomes a catalog tile the
    # same way a sequence does — the ANCHOR's invariant ("every target_kind is
    # something the console actually fires") is EXTENDED here, not weakened.
    SectionSpec(name="macros", path="DataPool/Macros", target_kind="macro"),
)


@dataclass(frozen=True)
class PanelCatalog:
    """One rig enumeration: the tiles, plus each section's own completeness.

    A refresh REPLACES this whole value rather than merging into the previous
    one (PROTOCOL.md "A refresh REPLACES the list"): merging would keep tiles
    for objects the showfile no longer has, and a tile that fires nothing is
    indistinguishable from a console that failed to answer.
    """

    items: tuple[dict, ...] = ()
    sections: tuple[dict, ...] = ()


def _reject_credential_keys(payload: object, *, context: str) -> None:
    """Refuse any credential-like key, at any depth, in a pin payload.

    Reuses the MVP provider loader's key list verbatim (``server.llm.config``)
    for the same reason the settings loader does: two lists would be two
    policies, and the weaker one would be the hole. Unlike that loader this one
    also walks LISTS, because the pin file's payload is a list of records.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in _CREDENTIAL_KEYS:
                raise PinStoreError(
                    f"credential-like key {key!r} found in {context} — the pin file "
                    "never carries credentials"
                )
            _reject_credential_keys(value, context=f"{context}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _reject_credential_keys(value, context=f"{context}[{index}]")


def pin_store_path(file_name: str = PIN_FILE_NAME) -> Path:
    """The default pin file: ``<user-data-dir>/panel_pins.json``.

    The per-user DATA dir, not the config dir and not the bundle: a packaged app
    is read-only, and pins are runtime state the operator creates, not settings
    they configure.
    """
    return user_data_dir() / file_name


class PinStore:
    """Chat-pinned tiles, persisted atomically and read fail-open.

    Ordering is append-only and never sorted (REQ-SHOWUI-005/017): a tile that
    moves under the operator's finger mid-show is a misfire waiting to happen.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else pin_store_path()
        self._pins: list[dict] = self._load()

    @property
    def path(self) -> Path:
        return self._path

    def items(self) -> list[dict]:
        """The pinned tiles, in pin order."""
        return [dict(pin) for pin in self._pins]

    def contains(self, target_kind: str, target: int) -> bool:
        return any(
            pin["target_kind"] == target_kind and pin["target"] == target for pin in self._pins
        )

    def add(self, item: dict) -> bool:
        """Append one tile and persist. Returns ``False`` if already pinned.

        The incoming dict is credential-checked BEFORE it is normalised, so an
        unexpected ``api_key`` is refused rather than quietly dropped: a caller
        that put one there has a defect worth surfacing.
        """
        _reject_credential_keys(item, context="pin item")
        pin = self._normalize(item)
        if self.contains(pin["target_kind"], pin["target"]):
            return False
        pins = [*self._pins, pin]
        self._save(pins)
        self._pins = pins  # committed only after the file swap succeeded
        return True

    def remove(self, target_kind: str, target: int) -> bool:
        """Unpin one tile and persist the removal (REQ-SHOWUI-023)."""
        pins = [
            pin
            for pin in self._pins
            if not (pin["target_kind"] == target_kind and pin["target"] == target)
        ]
        if len(pins) == len(self._pins):
            return False
        self._save(pins)
        self._pins = pins
        return True

    # -- internals ---------------------------------------------------------------

    @staticmethod
    def _normalize(item: dict) -> dict:
        """Rebuild the tile through the frozen item constructor.

        Every enum is re-validated here, so a record that cannot be addressed
        correctly is never stored and never restored.
        """
        name = item.get("name", "")
        appearance = item.get("appearance")
        if not isinstance(name, str):
            raise PinStoreError(f"pin name must be a string, got {name!r}")
        if appearance is not None and not isinstance(appearance, str):
            raise PinStoreError(
                f"pin appearance must be a colour string or null, got {appearance!r}"
            )
        try:
            return panel_item(
                kind=item.get("kind"),
                target_kind=item.get("target_kind"),
                target=item.get("target"),
                name=name,
                appearance=appearance,
                source="pin",
            )
        except ValueError as error:
            raise PinStoreError(str(error)) from error

    def _load(self) -> list[dict]:
        """Read the pin file, degrading to an empty panel on ANY defect.

        Fail-OPEN on read (acceptance.md §D edge case 9): a corrupt, truncated
        or hand-edited file must not stop the app from starting a show. The next
        write regenerates a valid file. Fail-open is safe here precisely because
        a pin grants no capability — every tile is still screened by the gate
        before anything reaches the console.

        Partial trust is refused on purpose: one unreadable record makes the
        WHOLE file suspect, and a silently half-restored panel would leave the
        operator reaching for a tile that is not there.
        """
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return []
        try:
            data = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(data, dict):
            return []
        records = data.get("pins")
        if not isinstance(records, list):
            return []
        if not all(isinstance(record, dict) for record in records):
            return []
        try:
            _reject_credential_keys(data, context=str(self._path))
            return [self._normalize(record) for record in records]
        except PinStoreError:
            return []

    def _save(self, pins: list[dict]) -> None:
        """Write the pin file atomically (temp in the SAME dir + ``os.replace``).

        Mirrors ``server/deploy/settings.py::save_user_settings``: a crash
        mid-write leaves the previous file untouched instead of a half-written
        one that the fail-open read would then silently discard.
        """
        payload = json.dumps(
            {
                "version": PIN_FILE_VERSION,
                "pins": [{field: pin[field] for field in _PIN_RECORD_FIELDS} for pin in pins],
            },
            ensure_ascii=False,
            indent=2,
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".panel-pins-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise


# The tile's type badge per target_kind (plan.md M2 D4 / REQ-DASHUI-012): a
# macro is NOT a stored look, so it must not inherit _CATALOG_ITEM_KIND's
# "sequence" default — the exact mis-badge risk plan.md D4 names ("M2의
# SectionSpec 경로가 매크로 타일에 _CATALOG_ITEM_KIND = 'sequence' 오배지를
# 찍는다"). Sequences and executors keep the existing "sequence" badge (an
# executor is still an assigned-sequence display, per the module-level
# rationale above).
_ITEM_KIND_BY_TARGET_KIND = {"macro": "macro"}


def _tiles(objects: list[dict], target_kind: str) -> list[dict]:
    """Turn resolved rig objects into tiles, skipping the unaddressable ones.

    An object the responder could not number arrives without ``no`` (see
    ``rig_object``). That absence is meaningful: there is no address, so there
    is no tile. Inventing one from the list position is the exact defect
    REQ-SHOWUI-003 exists to prevent.
    """
    kind = _ITEM_KIND_BY_TARGET_KIND.get(target_kind, _CATALOG_ITEM_KIND)
    tiles = []
    for obj in objects:
        number = obj.get("no")
        if number is None:
            continue
        tiles.append(
            panel_item(
                kind=kind,
                target_kind=target_kind,
                target=number,
                name=str(obj.get("name", "")),
                source="auto",
            )
        )
    return tiles


def build_catalog(
    state_port: StateQueryPort,
    *,
    paths: dict[str, str] | None = None,
    query_cap: int = PANEL_DRILLDOWN_QUERY_CAP,
) -> PanelCatalog:
    """Enumerate the console's fireable objects into panel tiles.

    ``paths`` overrides a section's object-tree path by name, for the same
    reason ``rig_paths`` exists: a showfile that keeps its pools elsewhere must
    be configurable rather than silently empty.

    Failure classification is the rig-context one and stays SPLIT
    (REQ-SHOWUI-002): if any sibling section answered, the console is
    demonstrably reachable and a failing path is a configuration defect
    (``path_not_resolved``); if nothing answered, no path can be blamed
    (``console_unreachable``). Merging the two is how two dead default rig paths
    survived a whole stage unnoticed.
    """
    overrides = dict(paths or {})
    items: list[dict] = []
    sections: list[dict | None] = []
    failed: list[tuple[int, str]] = []
    resolved = 0
    budget = query_cap

    for spec in PANEL_CATALOG_SECTIONS:
        path = overrides.get(spec.name, spec.path)
        try:
            payload = state_port.query_state(path)
        except Exception:
            # Position held; classified below, once every section's outcome is
            # known — the reason depends on whether ANY sibling answered.
            failed.append((len(sections), spec.name))
            sections.append(None)
            continue
        resolved += 1
        children = payload.get("children", [])
        objects = [rig_object(child) for child in children if isinstance(child, dict)]
        entry = rig_section(objects, payload)
        contents_unavailable = False
        if spec.drilldown:
            budget = drill_into(state_port, objects, path, entry, budget)
            contents_unavailable = any(obj.get("contents_unavailable") for obj in objects)
            for obj in objects:
                items.extend(_tiles(obj.get("contents", []), spec.target_kind))
        else:
            items.extend(_tiles(objects, spec.target_kind))
        sections.append(
            panel_section(
                name=spec.name,
                status="ok",
                truncated=bool(entry.get("truncated")),
                drilldown_capped=bool(entry.get("drilldown_capped")),
                contents_unavailable=contents_unavailable,
            )
        )

    status = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE
    for index, name in failed:
        sections[index] = panel_section(name=name, status=status)
    return PanelCatalog(items=tuple(items), sections=tuple(s for s in sections if s is not None))


class PanelStore:
    """The panel's server-side truth: pinned tiles + the last rig enumeration."""

    def __init__(
        self,
        *,
        state_port: StateQueryPort,
        pins: PinStore,
        catalog_paths: dict[str, str] | None = None,
    ) -> None:
        self.state_port = state_port
        self.pins = pins
        self._catalog_paths = catalog_paths
        # No catalog until one is actually read. An empty panel is honest; a
        # guessed one is not.
        self._catalog = PanelCatalog()
        self._enumerated = False
        # SPEC-COPILOT-DASHUI-001 M6 — console-VERIFIED executor numbers from
        # the dash catalog's resolution report. The SHOWUI page drill reports
        # POOL SLOTS, which the console does not address (live-measured:
        # page 1 slot 1 is "Executor 101"), so the dash tiles fire these
        # verified numbers instead — membership must recognise them.
        self._dash_executors: set[int] = set()
        # T-H5 — executor_no -> (sequence_no, {cue numbers the sequence
        # actually carries}), populated from the SAME cue_monitor snapshot the
        # UI's cue sheet renders (see ``register_executor_cues``). This is
        # what lets a ``Goto`` request be refused BEFORE a bundle is built
        # when the requested cue does not exist — never guessed at, never
        # forwarded to the gate on faith.
        self._executor_cues: dict[int, tuple[int, frozenset[int]]] = {}

    @property
    def catalog(self) -> PanelCatalog:
        return self._catalog

    def refresh_catalog(self) -> PanelCatalog:
        """Re-read the rig. REPLACES the previous enumeration, never merges."""
        self._catalog = build_catalog(self.state_port, paths=self._catalog_paths)
        self._enumerated = True
        return self._catalog

    def items(self) -> list[dict]:
        """Every tile, in grid order: pins first, then the rig enumeration.

        Pins lead because their positions must be the most stable thing on the
        grid (REQ-SHOWUI-017). They are the operator's own deliberate choices,
        while the auto half is replaced wholesale on every refresh — if the auto
        tiles came first, adding one sequence to the showfile would shift every
        pinned tile out from under the operator's finger.
        """
        return [*self.pins.items(), *self._catalog.items]

    def sections(self) -> list[dict]:
        return list(self._catalog.sections) if self._enumerated else []

    # @MX:ANCHOR: [AUTO] the membership half of REQ-SHOWUI-022. Built and tested
    # in M2; M3 calls it on every panel_execute / panel_stop / panel_unpin before
    # a bundle exists.
    # @MX:REASON: the target is client-controlled. Parse-time validation proves
    # it is a positive integer, not that it names a real object — without this
    # check a well-formed "Executor 9999" would reach gate.screen() as a
    # perfectly plausible command and fire at nothing (or at something).
    def contains(self, target_kind: str, target: int) -> bool:
        """True when this (class, number) pair is a tile the panel actually has."""
        if target_kind not in PANEL_TARGET_KINDS:
            return False
        if target_kind == "executor" and target in self._dash_executors:
            return True
        if self.pins.contains(target_kind, target):
            return True
        return any(
            item["target_kind"] == target_kind and item["target"] == target
            for item in self._catalog.items
        )

    def register_dash_executors(self, console_nos: list[int]) -> None:
        """REPLACE the dash-verified executor membership (never merge).

        Called on every dash catalog build with that build's
        ``resolved_executor_nos`` — the same replace-not-merge discipline the
        catalog itself follows (REQ-DASHUI-006), so a number that stopped
        confirming on refresh stops being fireable with it.
        """
        self._dash_executors = {no for no in console_nos if isinstance(no, int)}

    # @MX:ANCHOR: [AUTO] the Goto membership half (T-H5) — the SAME discipline
    # as ``contains``/``register_dash_executors`` above, applied one level
    # deeper: not just "does this executor exist" but "does its sequence
    # actually carry this cue". ``PanelRuntime.fire`` checks this BEFORE
    # ``playback_command`` is ever called for a ``Goto``.
    # @MX:REASON: without this, a stale/tampered client-supplied cue number
    # would reach ``gate.screen()`` as a plausible-looking ``Goto`` bundle —
    # the exact hazard ``contains`` already closes for the target itself.
    def register_executor_cues(self, executors: list[dict]) -> None:
        """REPLACE (never merge) each executor's known sequence + cue numbers.

        ``executors`` is ``server/web/cue_monitor.py``'s own per-executor
        entry list (``build_cue_progress``'s return shape) — the SAME data
        the UI's cue sheet renders, so a Goto's membership check sees exactly
        the cue list the operator saw when they clicked a row. Only
        ``status == "ok"`` entries carry a resolved sequence — anything else
        contributes nothing (an executor absent from this map fails the
        Goto membership check rather than being guessed at).
        """
        cue_membership: dict[int, tuple[int, frozenset[int]]] = {}
        for entry in executors:
            if not isinstance(entry, dict) or entry.get("status") != "ok":
                continue
            executor_no = entry.get("executor_no")
            sequence_no = entry.get("sequence_no")
            if not isinstance(executor_no, int) or not isinstance(sequence_no, int):
                continue
            cue_nos = {
                cue["cue_no"]
                for cue in entry.get("cues", [])
                if isinstance(cue, dict) and isinstance(cue.get("cue_no"), int)
            }
            cue_membership[executor_no] = (sequence_no, frozenset(cue_nos))
        self._executor_cues = cue_membership

    def sequence_for_executor(self, executor_no: int) -> int | None:
        """The sequence number ``executor_no`` is currently assigned to, or
        ``None`` when unknown — the Goto resolution step (T-H5)."""
        entry = self._executor_cues.get(executor_no)
        return entry[0] if entry is not None else None

    def executor_has_cue(self, executor_no: int, cue_no: int) -> bool:
        """Whether ``executor_no``'s sequence actually carries ``cue_no``."""
        entry = self._executor_cues.get(executor_no)
        return entry is not None and cue_no in entry[1]

    def pin_from_seed(self, seed: LastCreated | None) -> dict:
        """Pin the chat's last-created look (REQ-SHOWUI-004).

        The executor is preferred as the ADDRESS when the look was assigned to
        one — that is the surface which actually fires it — while the name keeps
        naming the sequence, which is the look's identity. With no seed at all
        this raises rather than returning ``None``: see :class:`PinSeedUnavailable`.
        """
        if seed is None or seed.sequence is None:
            raise PinSeedUnavailable()
        if seed.executor is not None:
            target_kind, target = "executor", seed.executor
        else:
            target_kind, target = "sequence", seed.sequence
        item = panel_item(
            kind=_CATALOG_ITEM_KIND,
            target_kind=target_kind,
            target=target,
            name=f"Sequence {seed.sequence}",
            source="pin",
        )
        self.pins.add(item)
        return item

    def unpin(self, target_kind: str, target: int) -> bool:
        """Remove one pinned tile; the removal is persisted (REQ-SHOWUI-023)."""
        return self.pins.remove(target_kind, target)


# -- the firing half (SHOWUI M3 — REQ-SHOWUI-006..013/022/025/026) ----------------


# The console's own playback verbs (rulebook 31_choreography_patterns.md
# "Playback (validated)"). Console vocabulary, never a media-player metaphor
# (REQ-SHOWUI-020).
#
# T-H5 (coordinator directive, 2026-08-02) widens this from a pair to a
# CLOSED QUADRUPLE — step back/forward, jump-to-cue, and stop are the FOUR
# rulebook-validated Playback forms (31_choreography_patterns.md:100-101):
# ``Go+ Executor <n>`` (next cue), ``Go- Executor <n>`` (previous cue),
# ``Goto Cue <c> Sequence <s>`` (jump), ``Off Executor <n>`` (release). All
# four belong to the SAME validated family — none is a media-player
# metaphor, none is invented — and the set stays CLOSED: a panel press can
# express exactly these four intentions, so a fifth verb reaching
# ``playback_command`` (typo, copy-paste, a future feature added carelessly)
# must fail loudly rather than build a plausible-looking but unverified
# command. ``TestPlaybackCommand.test_the_verb_set_is_frozen_at_exactly_four``
# (test_web_panel_execute.py) pins the tuple's exact contents so a silent
# fifth entry breaks the build.
PANEL_GO_VERB = "Go+"
PANEL_BACK_VERB = "Go-"
PANEL_GOTO_VERB = "Goto"
PANEL_OFF_VERB = "Off"
PANEL_VERBS = (PANEL_GO_VERB, PANEL_BACK_VERB, PANEL_GOTO_VERB, PANEL_OFF_VERB)

# The console keyword each addressable class is spoken with.
_TARGET_WORD = {"executor": "Executor", "sequence": "Sequence"}

# Korean, because every one of these is shown to the operator.
PANEL_UNKNOWN_TARGET_MESSAGE = (
    "패널에 없는 대상입니다 — 카탈로그를 새로고침한 뒤 다시 시도해 주세요."
)
# T-H5 — distinct from PANEL_UNKNOWN_TARGET_MESSAGE: the EXECUTOR is a known
# panel member, but the requested cue number is not one this executor's
# sequence actually carries (or the executor's sequence isn't known at all).
# Kept as its own message rather than reusing the target one so the operator
# is told the RIGHT thing failed — the executor, not the cue.
PANEL_UNKNOWN_CUE_MESSAGE = "존재하지 않는 큐입니다 — 큐 시트를 새로고침한 뒤 다시 시도해 주세요."
PANEL_BUSY_MESSAGE = "패널 실행이 진행 중입니다 — 완료된 뒤 다시 시도해 주세요."
PANEL_UNCONFIRMED_MESSAGE = "실행 미확인 — 콘솔에서 실제 상태를 확인해 주세요 (자동 재전송 안 함)."
PANEL_REFUSED_MESSAGE = "패널 명령이 실행되지 않았습니다."

# One Korean line per gate bundle verdict. Mirrors the chat surface's
# ``_DECISION_SUMMARY`` in wording and in principle: gate TRUTH is reported,
# and a non-execution is never rendered as a success (REQ-SHOWUI-010).
_PANEL_DECISION_MESSAGES = {
    "blocked_console_offline": "콘솔 오프라인 상태입니다 — 패널 실행이 차단되었습니다.",
    "blocked_responder_degraded": (
        "콘솔 응답기가 저하 상태입니다 — 결과 확인이 불가능하여 패널 실행을 시작하지 않았습니다."
    ),
    "blocked_backup_failed": "쇼파일 백업 실패로 패널 실행이 차단되었습니다 (안전 장치).",
    "blocked_grammar": "명령 문법 검증에 실패하여 패널 실행이 차단되었습니다.",
    "locked": "라이브 잠금 활성 — 콘솔로 전송하지 않고 제안만 생성했습니다.",
    "rejected": "승인이 거부되어 패널 명령이 실행되지 않았습니다.",
}

# ``ExecutionResult.detail`` markers the gate stamps on a non-send. Matched
# rather than re-derived so a wording change fails here instead of quietly
# turning an unconfirmed send into a reported success (mirrors
# ``server.web.session.UNCONFIRMED_MARKER``).
_UNCONFIRMED_MARKER = "execution unconfirmed"


# @MX:ANCHOR: [AUTO] the ONLY place a panel command string is built. Consumed by
# PanelRuntime.fire (execute + stop), and through it by every panel press —
# including the All Off gesture, which is N ordinary stops and not a special path.
# @MX:REASON: REQ-SHOWUI-026 — a wide target (`Thru`, `*`, `Everything`) trips the
# risk classifier's open-ended-target hold, which would raise an approval card
# mid-blackout. Forcing every command through one builder that accepts only a
# closed verb pair and a single positive integer makes a wide target
# UNCONSTRUCTIBLE rather than merely unwritten (REQ-SHOWUI-025 bounded
# enumeration is then a property of the type, not of the caller's discipline).
def playback_command(verb: str, target_kind: str, target: int, *, cue: int | None = None) -> str:
    """``"Go+ Executor 191"`` / ``"Goto Cue 2 Sequence 11"`` / ``"Macro 3"`` —
    one verb, one class, one number (plus, for ``Goto`` only, a second
    positive integer naming the cue).

    Raises on anything else. The parser already validated a client-supplied
    target (``server.web.messages``), so this second check exists for the
    callers the parser never sees: it is what stops a future internal caller
    from composing a range, a wildcard, or an unaddressable class.

    ``Goto`` (T-H5) is rulebook-validated ONLY in the shape
    ``Goto Cue <c> Sequence <s>`` (31_choreography_patterns.md:100) — it
    addresses a SEQUENCE, never an executor, so ``target_kind`` MUST be
    ``"sequence"`` here even when the press originated on an executor tile;
    resolving an executor number to its sequence number is the CALLER's job
    (``PanelRuntime.fire``), not this builder's — a builder that guessed at
    that resolution itself would be a second, undocumented membership check.

    The macro form (SPEC-COPILOT-DASHUI-001 REQ-DASHUI-012) is the
    rulebook-verified ``Macro <no>`` (00_grammar.md:60) — the run form carries
    NO playback verb word. A macro press is one-shot by decision (plan.md §F
    D1): no verified stop form exists, so ``Off`` on a macro is
    UNCONSTRUCTIBLE here rather than guessed.
    """
    if verb not in PANEL_VERBS:
        raise ValueError(f"panel verb must be one of {PANEL_VERBS}, got {verb!r}")
    if verb == PANEL_GOTO_VERB:
        if target_kind != "sequence":
            raise ValueError(
                "Goto is rulebook-validated ONLY as 'Goto Cue <c> Sequence <s>' "
                "(31_choreography_patterns.md:100) — target_kind must be "
                f"'sequence', got {target_kind!r}"
            )
        if not _is_object_number(target):
            raise ValueError(
                f"panel target must be a positive integer object number, got {target!r}"
            )
        if not _is_object_number(cue):
            raise ValueError(f"Goto requires a positive integer cue number, got {cue!r}")
        return f"Goto Cue {cue} Sequence {target}"
    if cue is not None:
        raise ValueError(f"cue is only meaningful for {PANEL_GOTO_VERB!r}, got verb={verb!r}")
    if not _is_object_number(target):
        raise ValueError(f"panel target must be a positive integer object number, got {target!r}")
    if target_kind == "macro":
        if verb != PANEL_GO_VERB:
            raise ValueError(
                "a macro press is one-shot — no rulebook-verified stop form exists "
                "(the run form is 'Macro <no>', 00_grammar.md:60)"
            )
        return f"Macro {target}"
    word = _TARGET_WORD.get(target_kind)
    if word is None:
        raise ValueError(
            f"panel target_kind must be one of {PANEL_TARGET_KINDS}, got {target_kind!r}"
        )
    return f"{verb} {word} {target}"


@dataclass(frozen=True)
class PanelOutcome:
    """What one press actually did — the value the tests and the lanes read.

    ``screened``/``sent`` are recorded separately on purpose: "the gate was
    asked" and "the console was reached" are different claims, and the whole
    milestone rests on never confusing them.
    """

    status: str  # unknown_target | executed | unconfirmed | failed | blocked | rejected | proposal
    command: str = ""
    screened: bool = False
    sent: bool = False
    detail: str = ""


class PanelRuntime:
    """One WebSocket connection's panel surface (M3).

    Owns the panel's own session identity, which is deliberately NOT the chat
    session's: the gate keys clearances per session, so sharing a key would let
    a chat turn's screening invalidate a panel clearance and vice versa
    (REQ-SHOWUI-013 — the two paths serialize independently).

    Within the panel's OWN key the reset is kept, and that is the point: an
    ``Off`` screened while an execute is still in flight invalidates the
    execute's unconsumed clearance, so the execute is over-blocked rather than
    firing after the operator already asked for stop (REQ-SHOWUI-012 —
    stop-preempts-execute, failing safe by construction).
    """

    def __init__(
        self,
        *,
        gate: SafetyGate,
        store: PanelStore,
        send_event: Callable[[dict], None],
        session_key: SessionKey,
    ) -> None:
        self._gate = gate
        self._store = store
        self._send = send_event
        self._session_key = session_key
        # Derived, volatile, per-connection: what the panel has OBSERVED itself
        # start. Never a claim about the console's own state — a playback
        # started at the desk is invisible here, which is exactly the All Off
        # limitation spec.md §A names (REQ-SHOWUI-025).
        self._running: set[tuple[str, int]] = set()

    def contains(self, target_kind: str, target: int) -> bool:
        """Membership half of REQ-SHOWUI-022 — asked BEFORE a bundle exists."""
        return self._store.contains(target_kind, target)

    def register_dash_executors(self, console_nos: list[int]) -> None:
        """Delegate the dash-verified executor membership to the store."""
        self._store.register_dash_executors(console_nos)

    def register_executor_cues(self, executors: list[dict]) -> None:
        """Delegate the Goto cue-membership map to the store (T-H5)."""
        self._store.register_executor_cues(executors)

    # @MX:ANCHOR: [AUTO] the panel's ONE route to the console. panel_execute,
    # panel_back, panel_goto, and panel_stop ALL enter here; there is no second
    # entry, and the All Off gesture is N calls to this same method.
    # @MX:REASON: REQ-SHOWUI-006/007 (gate.py:260-264) — exactly one screening path
    # may exist. Every send below is preceded by gate.screen() in the same call,
    # so a bypass would require editing this method rather than adding a caller.
    def fire(
        self, verb: str, target_kind: str, target: int, *, cue: int | None = None
    ) -> PanelOutcome:
        """Screen one panel command, then execute it. Synchronous (worker thread).

        Order is load-bearing (REQ-SHOWUI-022): membership is checked FIRST, so
        an unknown target produces an explicit error with no bundle built and
        ``gate.screen()`` never called.

        T-H5 — a ``Goto`` press is keyed on the EXECUTOR (the same identity
        every other press uses), but the rulebook-validated command form
        addresses the executor's SEQUENCE (``playback_command``'s own
        docstring). This method does that resolution — never the builder,
        never the caller — and additionally refuses when ``cue`` is not one
        this executor's sequence actually carries, BEFORE any command string
        is built.
        """
        if not self._store.contains(target_kind, target):
            self._send(error_event(message=PANEL_UNKNOWN_TARGET_MESSAGE, kind="panel"))
            return PanelOutcome(status="unknown_target")
        if verb == PANEL_GOTO_VERB:
            sequence_no = self._store.sequence_for_executor(target)
            if (
                target_kind != "executor"
                or sequence_no is None
                or cue is None
                or not self._store.executor_has_cue(target, cue)
            ):
                self._send(error_event(message=PANEL_UNKNOWN_CUE_MESSAGE, kind="panel"))
                return PanelOutcome(status="unknown_target")
            command = playback_command(verb, "sequence", sequence_no, cue=cue)
        else:
            command = playback_command(verb, target_kind, target)
        token = bind_session_key(self._session_key)
        try:
            decision = self._gate.screen([command])
            if not decision.cleared:
                return self._report_not_cleared(decision, command, target_kind, target)
            # Adjacent to the screen call ON PURPOSE. The clearance Counter is
            # session-keyed and every screen() RESETS it, so the window in which
            # a concurrently-completing screen could invalidate this clearance is
            # exactly the gap between these two statements — keep it at zero
            # statements' worth of work.
            result = self._gate.execution_port.execute(command)
        finally:
            reset_session_key(token)
        return self._report_executed(result, verb, command, target_kind, target)

    def send_catalog(self) -> dict:
        """Re-read the rig and answer with the tile list (REQ-SHOWUI-002).

        Synchronous: the read is a bounded set of console round trips through
        the gate-audited state port, so callers run it off the event loop.
        """
        self._store.refresh_catalog()
        return self._emit_catalog()

    def pin(self, seed: LastCreated | None) -> dict | None:
        """Pin the chat's last-created look (REQ-SHOWUI-004).

        A missing seed is surfaced as an explicit Korean error rather than a
        silent no-op: the operator pressed a button, and a button that does
        nothing without saying why is worse than one that refuses
        (acceptance.md §D edge case 7).
        """
        try:
            self._store.pin_from_seed(seed)
        except (PinSeedUnavailable, PinStoreError) as error:
            self._send(error_event(message=str(error), kind="panel"))
            return None
        return self._emit_catalog()

    def unpin(self, target_kind: str, target: int) -> dict | None:
        """Remove one pinned tile (REQ-SHOWUI-023)."""
        if not self._store.pins.contains(target_kind, target):
            self._send(error_event(message=PANEL_UNKNOWN_TARGET_MESSAGE, kind="panel"))
            return None
        self._store.unpin(target_kind, target)
        self._running.discard((target_kind, target))
        return self._emit_catalog()

    def busy(self, target_kind: str, target: int) -> None:
        """Refuse one press because an execution is already in flight.

        Names the refused tile: the UI latches a tile the moment it is pressed
        (REQ-SHOWUI-011), so an anonymous refusal would leave it latched.
        """
        self._send(
            panel_busy_event(target_kind=target_kind, target=target, message=PANEL_BUSY_MESSAGE)
        )

    # -- internals -------------------------------------------------------------

    def _emit_catalog(self) -> dict:
        event = panel_catalog_event(items=self._store.items(), sections=self._store.sections())
        self._send(event)
        return event

    def _emit_state(self, target_kind: str, target: int) -> None:
        """Report the tile's TRACKED state — never a guess about the console."""
        self._send(
            panel_item_state_event(
                target_kind=target_kind,
                target=target,
                running=(target_kind, target) in self._running,
            )
        )

    def _report_not_cleared(
        self, decision, command: str, target_kind: str, target: int
    ) -> PanelOutcome:
        if decision.proposal is not None:
            self._send(
                proposal_event(
                    commands=list(decision.proposal.commands),
                    reasons=list(decision.proposal.reasons),
                )
            )
        message = _PANEL_DECISION_MESSAGES.get(decision.status) or (
            decision.notice or PANEL_REFUSED_MESSAGE
        )
        self._send(error_event(message=message, kind="panel"))
        # The tile is released to the truth: nothing new is running.
        self._emit_state(target_kind, target)
        status = "proposal" if decision.status == "locked" else decision.status
        return PanelOutcome(
            status=status, command=command, screened=True, sent=False, detail=decision.notice
        )

    def _report_executed(
        self, result, verb: str, command: str, target_kind: str, target: int
    ) -> PanelOutcome:
        key = (target_kind, target)
        if result.ok:
            # A macro is ONE-SHOT — no Off form exists (playback_command
            # raises on it), so entering the running set would latch the tile
            # lit-as-running forever with no affordance that could clear it
            # (live defect, 2026-07-24). Only kinds with a stop affordance
            # track running.
            #
            # T-H5: Go- (step back) and Goto (jump) are grouped with Go+ here
            # — all three leave the executor positioned on a cue and offer
            # the SAME Off affordance next, so all three enter the running
            # set the identical way Go+ always has. Only Off clears it.
            if verb in (PANEL_GO_VERB, PANEL_BACK_VERB, PANEL_GOTO_VERB) and target_kind != "macro":
                self._running.add(key)
            else:
                self._running.discard(key)
            self._emit_state(target_kind, target)
            return PanelOutcome(
                status="executed", command=command, screened=True, sent=True, detail=result.detail
            )
        detail = result.detail or ""
        if _UNCONFIRMED_MARKER in detail:
            # The command may or may not have run. Leave the tracked state
            # untouched and SAY so — REQ-MVP-032 forbids an automatic resend,
            # and a confident render either way would be a lie.
            self._send(error_event(message=PANEL_UNCONFIRMED_MESSAGE, kind="panel"))
            self._emit_state(target_kind, target)
            return PanelOutcome(
                status="unconfirmed", command=command, screened=True, sent=True, detail=detail
            )
        self._send(error_event(message=PANEL_REFUSED_MESSAGE, kind="panel"))
        self._emit_state(target_kind, target)
        status = "blocked" if detail.startswith("blocked:") else "failed"
        return PanelOutcome(
            status=status,
            command=command,
            screened=True,
            sent=not detail.startswith("blocked:"),
            detail=detail,
        )
