"""PRESERVE always-on gate (M7 — AC-OVERLAP-019).

The predecessor SPEC's PRESERVE gate was a ONE-OFF manual procedure, and this
repository runs no CI. A gate nobody re-runs protects nothing, so the boundaries
it named are re-asserted here on every suite run.

**This file owns the PRECHK base and nothing else owns it.** The precedent gate in
``test_songcue_bundle.py`` is anchored to a DIFFERENT base, and its protected
ranges are relative to that one. Mixing the two in one module makes a gate guard
the wrong lines while still passing: at the PRECHK base the precedent's
``(234, 238)`` covers the middle of a comment explaining the dedupe exception,
and ``(524, 569)`` starts thirteen lines ahead of the dedupe execution loop and
closes before its final ``failed = True``. The two constants differ by exactly
thirteen because ``tools.py`` grew by thirteen lines between the bases. Hence a
new file rather than an extension of the old one.

Every assertion here is paired with a non-vacuity guard. ``git diff --stat``
contributes NOTHING for a path that does not exist, so a single typo in the path
list would make this gate pass forever.

**NOT regression tests — this whole module is an INVARIANT GATE**
(``AC-OVERLAP-021`` ⑥). The reverse run confirms it: all of these pass against the
pre-change tree, because the boundaries they assert already held. Catching a fix
is a different job, done by the mutation batteries recorded per milestone. What
this file catches is a FUTURE edit crossing a boundary nobody re-checks, which is
the failure mode a one-off manual gate leaves open.

**이 게이트가 지키는 목록은 범위 선언이다 — 이 게이트가 만든 경계가 아니다.** (t162)

``_PRESERVE_PATHS`` 와 선례 게이트의 ``_PRESERVE_LOOK_FILES`` 는 각 SPEC 이 자기
범위를 선언한 자리에서 왔고, 이 파일이 하는 일은 그 선언을 매 스위트 실행마다
다시 확인하는 것뿐이다. 좌표(둘 다 되읽어 확인했고
:class:`TestPreserveScopeCitations` 가 트립와이어로 잡는다):

* ``.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:89`` — §A.5 PRESERVE 재확인 표의
  첫 행. ``server/looks/*.py`` 여섯과 ``server/looks/library/`` 를 「PRECHK 는 룩
  계층 소비자가 아니다. 변경 0건」으로 선언한다. 이어지는 행들이 나머지 항목이다.
* ``.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:182`` — REQ-SONGCUE-021,
  「The **본 SPEC** shall not …」. 선례 게이트
  (``server/tests/test_songcue_bundle.py``)의 여섯 파일이 여기서 온다.

**읽는 법 — 두 문장은 다르고, 이 게이트는 앞의 것만 잰다.**

「그 SPEC 은 이 파일들을 안 건드렸다」는 **역사적 사실**이다. 그 SPEC 이 닫힌
뒤에도 영원히 참이고, 매 실행 재확인해도 값이 안 변한다. 「아무도 이 파일들을 못
건드린다」는 **집행되는 경계**이고 미래를 구속한다. 이 게이트가 재확인하는 것은
앞의 것이다. ``git diff`` 가 비었는지만 보므로 게이트 자신은 그 둘을 **구별할 수
없다** — 구별은 여기 문면에만 있다. 뒤의 것으로 읽으면 이미 끝난 SPEC 의 범위
선언이 저장소 전체의 동결 규칙으로 조용히 승격되고, 그 승격은 아무도 승인한 적이
없다.

**다른 카드가 이 파일 중 하나를 고쳐야 하면, 처방은 이 게이트가 아니다.**

여기에 예외를 다는 것(아래 룰북·console/lua 예외처럼)은 마지막 수단이다. 먼저
가는 곳은 **선언 층** — 그 항목을 목록에 올린 SPEC 문서다. 선례가 있다:
SONGCUE v0.2.0 은 ``console/lua/**`` 에 예외를 단 것이 아니라 §C PRESERVE 목록에서
**뺐다**(사유 ``SPEC-COPILOT-SONGCUE-001/spec.md:245-250`` · 승인 기록 같은 SPEC 의
``progress.md`` §F 개정 절).

⚠️ 그때는 그 SPEC 이 **살아 있었다.** 닫힌 SPEC 의 선언을 사후에 고치는 경우는 이
선례가 덮지 않는다 — 그 판단은 이 게이트 밖이다.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The PRECHK run-phase base. NOT this SPEC's base: a diff taken from this SPEC's
#: own base is empty the moment the work is committed, which would disable the
#: gate entirely while leaving it green.
_PRECHK_BASE = "95687a0e0eba90b325daf76efbd0ac197e69e2fc"

#: This SPEC's base. Used for exactly ONE assertion -- see
#: :func:`test_the_predecessor_progress_log_is_untouched` for why it is the only
#: valid reference point there.
_OVERLAP_BASE = "85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a"

#: t115 — 게이트가 조용히 못 보던 디렉터리. 경로가 한글이라 `git diff`
#: 기본값이 따옴표로 감싸 버렸다.
_T115_PIPELINE_DIR = "src/Lighting_Designer/90_빌드파이프라인"

#: The ten paths the predecessor SPEC locked, inherited unchanged. Files and
#: directories are NOT separated into two lists: the split is derived
#: mechanically below, so revising this list cannot desynchronise a hand-written
#: count.
#:
#: **이 목록은 범위 선언이다 — 이 게이트가 만든 경계가 아니다.** 출처 좌표와
#: 「안 건드렸다」/「못 건드린다」의 구별, 그리고 다른 카드가 이 파일을 고쳐야
#: 할 때 선언 층으로 가는 이유는 **이 모듈의 독스트링**에 있다 (t162).
_PRESERVE_PATHS = (
    "server/looks/schema.py",
    "server/looks/loader.py",
    "server/looks/roles.py",
    "server/looks/resolver.py",
    "server/looks/instantiate.py",
    "server/looks/matching.py",
    "server/looks/library/",
    "server/web/preview.py",
    "console/lua/",
    "server/rulebook/assets/v2.4.2/",
)

#: 2026-08-03 granted exception — SPEC-COPILOT-SPATIAL-001 M3 adds ONE rulebook
#: asset, ``32_spatial_design.md`` (user-approved). The rulebook prefix is a
#: deliberately EXTENSIBLE asset set (00 -> 10 -> 20 -> 30 -> 31 -> 32), so a
#: whole-directory lock would freeze every future rulebook milestone while
#: reading as a preserved boundary. The boundary that actually matters is that
#: the five EXISTING assets stay byte-identical, and that is what is now
#: asserted — by naming them, so a modification to any one of them still fails.
#:
#: Additions are not blanket-permitted either: ``test_the_rulebook_additions_are_
#: only_the_granted_asset`` below pins the added path by name and requires zero
#: deletions across the directory. Another new file, or one byte removed from an
#: old one, still fails the gate. ``server/rulebook/assets/v2.4.2/`` therefore
#: stays in the tuple above as the documented boundary and is swapped for its
#: named members in the diff, the same way ``server/looks/library/`` is.
_RULEBOOK_DIR = "server/rulebook/assets/v2.4.2/"
_RULEBOOK_LOCKED_ASSETS = (
    "server/rulebook/assets/v2.4.2/00_grammar.md",
    "server/rulebook/assets/v2.4.2/10_object_model.md",
    "server/rulebook/assets/v2.4.2/20_korean_terms.md",
    "server/rulebook/assets/v2.4.2/30_plugin_patterns.md",
)
_RULEBOOK_GRANTED_ADDITIONS = (
    "server/rulebook/assets/v2.4.2/32_spatial_design.md",
    # SPEC-COPILOT-FXGEN-001 REQ-FXGEN-016 — the effect-editor routing asset.
    "server/rulebook/assets/v2.4.2/33_effect_editors.md",
)
#: 2026-08-15 granted exception — SPEC-COPILOT-FXGEN-001 REQ-FXGEN-017 (b):
#: the 2026-08-15 live-measurement record (V1~V7 "OBSERVED EFFECT" section +
#: the operator confirmations that closed the session's three open
#: observations) is REQUIRED to land in ``31_choreography_patterns.md`` — the
#: anchor the fx code already cites. The grant is APPEND-ONLY and pinned below:
#: zero deleted lines (every existing line-number citation into this file —
#: :29, :75, :80, :85-89, :100, :111, :115, :236-241 — stays valid because
#: nothing above the old EOF may move) and the added block must carry the
#: OBSERVED EFFECT heading. Any other edit to the file still fails the gate.
_RULEBOOK_GRANTED_APPEND = "server/rulebook/assets/v2.4.2/31_choreography_patterns.md"
_RULEBOOK_APPEND_HEADING = "### OBSERVED EFFECT — live validation V1~V7 + operator confirmations"

#: 2026-08-12 granted exception — SPEC-COPILOT-DEPLOY-001's OSC zero-touch
#: bootstrap section (``console/lua/README.md`` § 1.-1) documents a
#: live-verified onPC 2.4.2 platform limitation (the OSC ``Interface`` field
#: has no command-line or file-import path — ``Set 'ShowData'.'OSCBase'
#: 'Interface' "lo0"`` returns ``Illegal value``) and the template-showfile
#: workaround discovered in that same live session. ``console/lua/`` stays a
#: locked boundary for the responder's SOURCE and WIRE CONTRACT — those three
#: files are named here and still fail the gate on any byte of drift — but
#: README.md is operator-facing prose, not code or protocol, and freezing it
#: forever would make it actively misleading as the app's setup requirements
#: keep being discovered live. Swapped out of the directory sweep the same
#: way ``server/looks/library/`` and the rulebook directory are.
_CONSOLE_LUA_DIR = "console/lua/"
_CONSOLE_LUA_LOCKED_ASSETS = ("console/lua/copilot_responder.xml",)
#: 2026-08-16 granted revision — preset-pool PAGING (responder 1.5.0 → 1.6.0):
#: the state query gains an optional trailing ``offset=<n>`` token and the
#: reply an integer ``offset`` echo, with PROTOCOL.md §4.2 rewritten from
#: "there is no paging" to the paging + legacy-fallback contract. The wire
#: CONTRACT changed deliberately (user-approved 2026-08-16 "진행해줘",
#: live-verified: responder_roundtrip 1.6.0 PASS + a 31-preset pool read
#: completely across two windows). The two revised files leave the byte-lock
#: and are pinned by CONTENT DIGEST instead — one byte of further drift still
#: fails the gate, and the next legitimate revision must re-pin here.
#:
#: 2026-08-18 granted revision (re-pin) — SPEC-COPILOT-INTROSPECT-001 reland
#: (PR #23 reland, T14): responder 1.6.0 → 1.6.1. ADDITIVE `props` +
#: `introspect` read-only discovery verbs (§2/§4.7/§4.8) planted onto the
#: current 1.6.0-paging generation, NOT merged from the drifted-behind
#: original branch. The wire CONTRACT changed deliberately (user-directed
#: reland task); it has NOT been live-verified against this reland's
#: responder (see the PROTOCOL.md 2026-08-18 reland note) — that gap is
#: recorded honestly rather than smoothed over, and is tracked as T15.
#: 2026-08-26 granted revision (re-pin) — t104: responder 1.6.1 → 1.6.2.
#: ADDITIVE `offset=<n>` paging on `introspect`, mirroring the token `state`
#: has carried since 1.6.0, plus the matching PROTOCOL.md §4.7 contract.
#:
#: The grant is motivated by a MEASUREMENT, not a preference: t95 read a
#: preset object that answered 138 properties, of which 27 fit one reply.
#: `introspect` had no cursor, so the other 111 NAMES were unreachable on this
#: channel — the single mechanism that left t95 undecided. A request without
#: the token is byte-for-byte unchanged; its reply changes only by the additive
#: `offset:0` echo, and `truncated` keeps its old meaning on the first window.
#:
#: NOT live-verified against a deployed 1.6.2 responder — the same honest gap
#: the 2026-08-18 reland recorded above. Deploying the plugin is a console
#: write and needs operator approval; the live pass (138 names enumerated
#: across windows, then read with a fabricated control probe) is t104's own
#: closing condition and is where this grant gets its confirmation.
#:
#: 2026-09-02 granted revision (re-pin) — t235/t242: responder 1.6.2 → 1.6.3.
#: ADDITIVE `ROOT_ALIASES` entries `programmer` / `programmerpart` /
#: `selection`. Operator-approved 2026-09-02, after the console `HelpLua`
#: exposure check, and explicitly scoped by that approval to "patch only,
#: deployment separate" — the deploy is NOT covered here.
#:
#: The grant is motivated by a MEASUREMENT, not a preference: three lanes read
#: `path segment not found: 'Programmer'` as a structural limit of the MA3
#: API. It was not. Path resolution walks `safe_children`, which returns
#: `Children()` in full (the 24-child cap binds the reply snapshot only), and
#: `find_child` compares both sides lowercased — so neither truncation nor
#: case explains the failure. What remained was the ABSENCE OF AN ALIAS: the
#: first segment fell through to a `Root()` child-name match. MA Lighting's
#: Object-Free API lists `Programmer()` / `ProgrammerPart()` / `Selection()`
#: beside `Root()` / `DataPool()` / `Patch()`.
#:
#: The WIRE CONTRACT does NOT change — no new verb, no new token, no new reply
#: field. `PROTOCOL.md` is untouched by this revision and keeps its existing
#: digest; only the set of first segments the responder can address grows.
#: Every alias is a guarded global call (`X and X()`), so a console lacking
#: the global yields nil, the caller falls through to the `Root()` walk, and
#: the path fails exactly as in 1.6.2 — `patch` has shipped in that same shape
#: since before this change, which is where the safety argument comes from.
#:
#: NOT live-verified: this rig has not been shown to expose those globals to
#: the responder, nor that the returned handle answers `Children()` the way
#: the reply builders need. Deploying the plugin is a console write and is
#: OUTSIDE this grant. Deployment is confirmed BY VERSION — `ping` must answer
#: 1.6.3; a rig answering 1.6.2 does not carry the aliases whatever main
#: contains (this repo has the live-1.6.1 / main-1.6.2 precedent). That is the
#: reason the version is bumped at all.
#: 2026-09-04 granted revision (re-pin) — SPEC-COPILOT-READBACK-001 M0:
#: responder 1.6.3 → 1.6.4. Table-valued property reads answer JSON TEXT
#: instead of the `table: 0x…` ADDRESS, and `PROTOCOL.md` §4.6/§4.8 gain the
#: sentences that state that contract. Operator-approved through the SPEC's
#: plan-audit PASS + Implementation Kickoff Approval (plan.md §C decision C-2,
#: 2026-09-03); the DEPLOY is explicitly NOT covered here — plan.md §E M3-1
#: owns the single console write and its own approval gate.
#:
#: The grant is motivated by a MEASUREMENT, not a preference: `M.safe_property`
#: put `tostring(value)` on every value, so a table answered its address while
#: the same reply already said `t="table"` — the responder was not lying, it
#: was declining to unpack something it had in hand
#: (`docs/runbooks/console-channel-facts.md:93-101` classifies this as a
#: removable non-implementation, and Part-level `SELECTIONDATA`/`DEPENDENCIES`
#: are the observed instances).
#:
#: The WIRE CONTRACT's SHAPE does not change — no new verb, no new token, no
#: new reply field. `t` stays `"table"`, `v` stays a string; only the CONTENT
#: of `v` changes for table values, so `server/bridge/protocol.py` and every
#: existing consumer are untouched. What §4.6/§4.8 gain is the statement of
#: that content, which is why `PROTOCOL.md` leaves its old digest this time
#: (the 1.6.3 revision left it untouched and kept its digest; this one does
#: not, because the contract text genuinely changes).
#:
#: Three defects the encoder carried since v1 are closed in the same edit,
#: because each of them is reachable ONLY once a table value is actually
#: encoded: no depth cap and no cycle detection (a self-referential table
#: would have recursed forever — the responder would simply never reply), and
#: an array/object heuristic (`value[1] ~= nil`) that silently dropped every
#: other key of a hash carrying `[1]`. Truncation of a table value is
#: STRUCTURAL rather than byte-wise: `safe_truncate` would leave an unparseable
#: JSON fragment, so the truncation announcement would be true and useless.
#:
#: NOT live-verified: no console was touched by this revision, and this rig has
#: not been shown to expose ANY table-valued property on a preset object — that
#: measurement is this SPEC's own M2 and is deliberately not assumed here. The
#: `SELECTIONDATA`/`DEPENDENCIES` shapes remain unobserved
#: (`console-channel-facts.md:121`), so the offline tests pin the encoder's
#: behaviour on shapes NOBODY HAS SEEN on this console. Deployment is confirmed
#: BY VERSION — `ping` must answer 1.6.4; a rig answering 1.6.3 does not carry
#: this change whatever main contains (live-1.6.1 / main-1.6.2 precedent).
#: 2026-09-06 granted revision (re-pin) — SPEC-COPILOT-POOLEMPTY-001 M1:
#: responder 1.6.4 → 1.6.5. Every successful `state` reply's `node` gains ONE
#: ADDITIVE field, `enumeration` ("ok" | "failed"), and `PROTOCOL.md` §4.2
#: gains the bullet that states its contract. Approved through the SPEC's
#: plan-audit PASS (0.86) + Implementation Kickoff Approval (card t270); the
#: DEPLOY is explicitly NOT covered here — plan.md §E M3 is an operator gate.
#:
#: The grant is motivated by a MEASUREMENT, not a preference: MUSICSYNC-001
#: M3-a run 1 (2026-09-05, `docs/research/ma3-effects/14-musicsync-m3a-
#: timecode-probe.md:9`) read `childCount 0` from `DataPool/Timecodes` on a
#: show with no timecodes and closed UNKNOWN — `M.safe_children` returned `{}`
#: for "empty" and for "both accessors raised" alike, so the server could not
#: tell them apart and the first timecode of a new show could never be
#: written. The distinction already existed INSIDE `safe_children`; this
#: revision exports it as a second return value and lets `build_snapshot`
#: put it on the wire.
#:
#: The WIRE CONTRACT changes ADDITIVELY only: no new verb, no new token, no
#: top-level field, nothing on `prop`/`props`/`introspect`/`pong`, no new
#: ASSUMPTION, protocol version stays 1. Backward compatibility is strict in
#: the safe direction — the server relaxes "zero children == unreadable" ONLY
#: when the marker says "ok"; a reply without the field (any responder
#: < 1.6.5) is judged byte-identically to before. The one measurable side
#: effect is the UDP budget: the zero-children `state` floor rises 295 → 326
#: bytes, so the paging window narrows by that much (plan.md B-5).
#:
#: NOT live-verified: no console was touched by this revision; the empty-pool
#: → free reading and its negative control (unknown) are the SPEC's own M3.
#: Deployment is confirmed BY VERSION — `ping` must answer 1.6.5; a rig
#: answering 1.6.4 does not carry the marker whatever main contains.
_CONSOLE_LUA_GRANTED_REVISION_DIGESTS = {
    "console/lua/copilot_responder.lua": "615fdf314d913cf208af479e7cc7116f5de5a224",
    "console/lua/PROTOCOL.md": "3e97fcda808a1c8e57837240cb557b69acfb5ae4",
}

#: 2026-08-02 granted exception — the upstream vocabulary extension
#: (docs/proposals/2026-08-02-upstream-vocabulary-extension-proposal.md §6,
#: user-approved, lightweight track). ``server/looks/library/`` stays a locked
#: boundary, but this ONE measured diff is sanctioned: 파란 mirrored beside 푸른
#: in exactly these alias/mood lines. The grant is pinned by EXACT line text
#: (the ``_SAFETY_ALLOWED_DELETED_LINES`` precedent): anything beyond these
#: pairs — another file, another line, another wording — still fails the gate.
_LOOKS_LIBRARY_DIR = "server/looks/library/"
_LOOKS_GRANTED_LINE_PAIRS = {
    "server/looks/library/ballad.yaml": (
        (
            '    aliases: ["달빛", "moonlight", "푸른 밤"]',
            '    aliases: ["달빛", "moonlight", "푸른 밤", "파란 밤"]',
        ),
        (
            '    mood_keywords: ["쓸쓸한", "푸른", "밤", "달빛", "차분한", "moonlit", "night"]',
            '    mood_keywords: ["쓸쓸한", "푸른", "파란", "밤", "달빛", "차분한", "moonlit", "night"]',  # noqa: E501
        ),
    ),
    "server/looks/library/edm.yaml": (
        (
            '    mood_keywords: ["깊은", "푸른", "숨고르는", "브레이크다운", "deep", "breakdown"]',
            '    mood_keywords: ["깊은", "푸른", "파란", "숨고르는", "브레이크다운", "deep", "breakdown"]',  # noqa: E501
        ),
    ),
    "server/looks/library/worship.yaml": (
        (
            '    aliases: ["푸른 벌스", "blue verse", "새벽"]',
            '    aliases: ["푸른 벌스", "파란 벌스", "blue verse", "새벽"]',
        ),
        (
            '    mood_keywords: ["서늘한", "고요한", "새벽", "푸른", "벌스", "cool", "calm"]',
            '    mood_keywords: ["서늘한", "고요한", "새벽", "푸른", "파란", "벌스", "cool", "calm"]',  # noqa: E501
        ),
    ),
}

#: 2026-09-06 granted addition — SPEC-COPILOT-D1GRANT-001 (REQ-D1GRANT-007):
#: ONE dynamics-1 look appended to EACH of ``edm.yaml`` and ``rock.yaml``, and
#: nothing else. Approved through that SPEC's plan-audit + Implementation
#: Kickoff Approval (card t282 follow-up); the grant is APPEND-ONLY and pinned
#: below by EXACT LINE TEXT, the same regime as the 2026-08-02 파란 mirror above.
#:
#: The grant is motivated by a MEASUREMENT, not a preference: card t277 watched
#: a live grandMA3 session store THREE cues for FOUR director-confirmed
#: sections. The missing one was the quietest section, and it failed silently.
#: Card t278 established the cause and fixed what could be fixed in code —
#: ``_select_bindable`` now picks the first look that actually BINDS on this rig
#: instead of the first look at the requested dynamics — which recovered
#: worship. It could not recover edm or rock, because those two genres had
#: exactly ONE dynamics-1 look each and its only role was ``배경``: on a rig with
#: no cyc/backdrop group there was nothing to choose. t278 recorded that residue
#: honestly in ``test_songcue_rig_aware_look.TestWhatThisFixCannotReach``. What
#: remained was LIBRARY CONTENT, not selection logic, and this is that content.
#:
#: Why the boundary is not weakened by this. ``server/looks/library/`` stays a
#: locked boundary and every OTHER file in it still fails on one changed byte.
#: Three properties bound the grant mechanically, each with its own assertion in
#: :class:`TestLooksLibraryGrantedExtension`: the changed-file set is the UNION
#: of the two grants and nothing more; the added lines must equal
#: ``[파란 pair] + [this block]`` EXACTLY (an ``==``, never a subset — a subset
#: predicate would let arbitrary library edits through and is the named
#: anti-pattern in that SPEC's plan.md §B-2); and each addition must be ONE pure
#: insertion hunk at the old EOF carrying ``- look_id:`` exactly ONCE, which is
#: what pins the grant's WIDTH to one look per file.
#:
#: The old-EOF placement is a GATE property, not a functional one.
#: ``looks_for_genre`` sorts by ``(dynamics, look_id)`` and never reads file
#: order, so where the block sits does not affect selection. What it buys is
#: determinism: a pure insertion shifts no line above it, so the 파란 hunk keeps
#: its position (old line 74) and the added-line ORDER is fixed, which is what
#: makes the exact-equality assertion above possible at all. The cyc-rig
#: no-regression property rests on ``look_id`` collation instead
#: (``edm-ambient-hold`` < ``edm-haze-shafts``, ``rock-empty-stage`` <
#: ``rock-wing-embers``) and is pinned by its own test rather than left to the
#: file layout — see ``test_songcue_d1_cycless.TestTheCycRigDoesNotMove``.
#:
#: NOT live-verified: no console was touched by this addition. The two looks'
#: colour and intensity values are DESIGN values back-derived from neighbouring
#: looks in the same files, never fired on a real rig, so their stage
#: suitability is a director's judgement this grant does not claim to have made.
#: ``edm`` reaches exactly ``MAX_LOOKS_PER_GENRE`` (10) with this addition —
#: a further edm look requires raising that constant, which is a separate
#: decision and NOT covered here.
_LOOKS_GRANTED_D1_APPENDS = {
    "server/looks/library/edm.yaml": (
        "",
        "  # --- dynamics 1, 뒤늦게 붙인 칸: 배경막 없는 리그를 위한 것 -----------------",
        "  # 파일이 다이내믹스 오름차순으로 읽히는 흐름에서 여기만 어긋난다. 정렬은",
        "  # `looks_for_genre` 가 `(dynamics, look_id)` 로 하므로 파일 위치는 선택에",
        "  # 영향을 주지 않고, 이 자리에 붙이는 이유는 승인 게이트 쪽이다(옛 EOF 뒤의",
        "  # 순수 삽입이라 위쪽 줄이 한 줄도 밀리지 않는다).",
        "  #",
        "  # `edm-ambient-hold` 는 역할이 `배경` 하나뿐이라, 호리·cyc 계열이 없는 리그에서는",
        "  # 어느 무리에도 안 묶이고 그 구간이 통째로 침묵했다. 배경막이 없을 때 깊이를",
        "  # 만드는 빛은 뒤에서 오는 것뿐이므로 역할은 `백라이트` 다 — 헤더 규칙이 `프론트` 를",
        "  # 배제하고, `탑` 은 실기 리그에서 안 묶인다.",
        '  - look_id: "edm-haze-shafts"',
        '    display_name: "헤이즈 샤프트"',
        '    genre: "edm"',
        "    dynamics: 1",
        '    roles: ["백라이트"]',
        '    aliases: ["헤이즈 샤프트", "haze shafts", "빈 하늘"]',
        '    mood_keywords: ["어두운", "깊은", "푸른", "파란", "잠긴", "haze", "shafts"]',
        "    attributes:",
        "      Dimmer: 18",
        "      ColorRGB_R: 0",
        "      ColorRGB_G: 40",
        "      ColorRGB_B: 78",
    ),
    "server/looks/library/rock.yaml": (
        "",
        "  # --- dynamics 1, 뒤늦게 붙인 칸: 배경막 없는 리그를 위한 것 -----------------",
        "  # edm.yaml 의 같은 자리와 이유가 같다 — 정렬 축은 `look_id` 사전순이지 파일",
        "  # 위치가 아니고, 옛 EOF 뒤에 붙이는 것은 승인 게이트를 위한 선택이다.",
        "  #",
        "  # `rock-empty-stage` 는 역할이 `배경` 하나뿐이라 배경막 없는 리그에서 침묵했다.",
        "  # 헤더 규칙이 벌스에서 `프론트` 를 배제하므로 남는 것은 `사이드` 와 `백라이트`",
        "  # 인데, `백라이트` 는 바로 다음 칸 `rock-verse-side` 가 이미 쓴다 — D1 에서",
        "  # 미리 쓰면 벌스로 넘어갈 때의 대비가 사라진다. 그래서 `사이드` 다.",
        '  - look_id: "rock-wing-embers"',
        '    display_name: "윙 엠버"',
        '    genre: "rock"',
        "    dynamics: 1",
        '    roles: ["사이드"]',
        '    aliases: ["윙 엠버", "wing embers", "잔불"]',
        '    mood_keywords: ["어두운", "탁한", "붉은", "식어가는", "embers", "smoulder"]',
        "    attributes:",
        "      Dimmer: 22",
        "      ColorRGB_R: 65",
        "      ColorRGB_G: 10",
        "      ColorRGB_B: 22",
    ),
}

#: 2026-09-06 granted line pair — SPEC-COPILOT-D1GRANT-001 (REQ-D1GRANT-019),
#: the count-prose correction that the append above FORCES.
#:
#: This one is worth reading slowly, because it is where two of that SPEC's own
#: requirements pull against each other. REQ-D1GRANT-004 says the SPEC "shall
#: not change any FIELD of an existing look", and then states a MECHANICAL
#: PROXY for that intent: zero deleted lines beyond the 2026-08-02 파란 pairs.
#: REQ-D1GRANT-019 separately REQUIRES that ``edm.yaml``'s header stop saying
#: "Nine looks", because the append makes that sentence false. A comment is not
#: a look's field, so the two requirements agree on INTENT — but a one-line
#: comment edit is a delete plus an add, so it trips the proxy. The proxy
#: over-reaches its own intent; that is the conflict, and it is recorded here
#: rather than resolved silently.
#:
#: Resolved by PINNING rather than by relaxing: the corrected line is named
#: below by exact text on both sides, so the gate is exactly as strong as it was
#: (nothing unpinned passes, and the intent REQ-D1GRANT-004 actually protects —
#: no existing LOOK is touched — is verifiable by reading this pair). The
#: alternative was to ship a library asset whose header states a count that its
#: own contents contradict, which is the defect class REQ-D1GRANT-019 exists to
#: prevent.
#:
#: Only the count word changes. The "weighted toward the top of the scale"
#: clause and the "three at dynamics 4-5" clause are left exactly as the
#: original author wrote them: the second is still true (three looks remain at
#: dynamics 4-5), and the first is a pre-existing characterisation this SPEC
#: neither introduced nor is required to re-litigate. Widening the edit past
#: the one word REQ-D1GRANT-019 names would widen the grant for nothing.
_LOOKS_GRANTED_COUNT_PROSE_PAIRS = {
    "server/looks/library/edm.yaml": (
        (
            "# different room than the build did. Nine looks, weighted toward the top of the",
            "# different room than the build did. Ten looks, weighted toward the top of the",
        ),
    ),
}

#: The look-library files carrying a granted change of ANY kind. Derived, not
#: written down: a hand-kept list would desynchronise from the grants the
#: moment any one of them is revised.
_LOOKS_GRANTED_FILES = (
    frozenset(_LOOKS_GRANTED_LINE_PAIRS)
    | frozenset(_LOOKS_GRANTED_D1_APPENDS)
    | frozenset(_LOOKS_GRANTED_COUNT_PROSE_PAIRS)
)

_TOOLS_PATH = "server/orchestrator/tools.py"

#: Protected regions of ``tools.py``, PRECHK-base relative: the programmer-state
#: command tuple and the dedupe execution loop. Position blockade, NOT a
#: deletion count -- ``tools.py`` legitimately deletes one line since this base
#: (an import replaced by a block), so a "zero deletions" rule would fail on
#: arrival and teach the next reader to weaken the gate.
_TOOLS_PROTECTED_OLD_RANGES = ((247, 251), (537, 582))

_SAFETY_DIR = "server/safety/"

#: The OVERLAP SPEC's own merge commit into main (PR #8) -- a FIXED historical
#: endpoint, unlike HEAD. "OVERLAP itself opened nothing new" is a fact about a
#: SPEC that finished long ago; measuring it against the ever-moving HEAD makes
#: it fail the moment any LATER, legitimate SPEC touches the chokepoint again
#: (exactly the "sibling gate breaks by merge order" failure mode documented at
#: `TestPrecedentGateFileIsNotExtended` above). Bounding both ends fixes it.
_OVERLAP_MERGE_COMMIT = "156a3e1aaf6ef78788394d65cf724bacaec7b567"

#: The safety chokepoint's measured state, PRECHK-base relative. Grown four
#: times: the predecessor's (OVERLAP's) property-read addition (console.py,
#: gate.py), then SPEC-COPILOT-BACKUP-001 T-B/T-B2's snapshot-retention +
#: audit-linkage extension (backup.py, gate.py again), then the T-I audit-log
#: crash fix -- audit.py joins the set (SCOPE CORRECTION below), then the
#: closed-set revision below. Every deletion's TEXT is pinned in
#: `_SAFETY_ALLOWED_DELETED_LINES` below, because a bare count lets a
#: meaningful removal hide under the allowance.
#:
#: 2026-08-05 granted exception -- SPEC-COPILOT-WRITEGATE-001 revises the
#: closed-set SSOT `blacklist.yaml` from version 1 to 2, adding exactly ONE
#: entry ("Set Fixture"). User-approved after the alternatives were searched
#: and rejected, which is the part worth recording: a design touching only
#: `gate.py` would have cost ZERO entries here (gate.py is already an allowed
#: row and the addition deletes nothing), but it would have forked the
#: closed-set interpretation that `classify.py`'s @MX:ANCHOR forbids and,
#: concretely, missed a patch write smuggled through a quoted `Property
#: 'Command'` value -- the recursion that catches those calls
#: `classify_command`, not the gate. So the cheaper boundary was declined for
#: the correct layer, and the cost is this one row.
#:
#: Why it could not be avoided at all: `SafetyGate.screen()` takes a command
#: sequence and nothing else, so no caller can declare a bundle risky
#: (SPATIAL-001 progress.md:294-296). Every possible design edits at least one
#: file under `server/safety/`. The FIRST attempt at this change was reverted
#: precisely here (SPATIAL progress.md:302-306) -- it was blocked by ownership,
#: not by being wrong, and WRITEGATE-001 owns `server/safety/`.
#:
#: The grant is one FILE with one PINNED deletion, and it widens nothing else.
#: Another file under the chokepoint, a second deleted line in this one, or any
#: text other than `version: 1` still fails the gate.
#:
#: 2026-09-04 granted exception -- SPEC-COPILOT-READBACK-002 M0 makes the
#: execution-screen gate READ the responder version that every heartbeat
#: already carries (REQ-READBACK2-001/003). `ConsoleLink.ping` decoded the full
#: `pong` payload and returned a bare `bool`, discarding `version`, so a
#: live-vs-main responder mismatch was undetectable -- and this repository has
#: the mismatch on record (live 1.6.1 against main 1.6.2, the digest dictionary
#: below). Two files join the set and console.py's count moves 57 -> 59.
#:
#: Why it could not be avoided: all five new deletions belong to ONE function.
#: `HealthMonitor.note_ping_success` encoded "a heartbeat answered -> ONLINE",
#: and REQ-READBACK2-003 splits that into "a heartbeat answered -> ONLINE OR
#: version-mismatch". Its three lines in monitor.py plus its two call sites --
#: two lines in console.py, two in gate.py -- are the whole delta: seven lines,
#: three files, one function. Any design satisfying the requirement edits the
#: health monitor, so the chokepoint is touched BY CONSTRUCTION --
#: the same "every possible design edits at least one file under
#: `server/safety/`" reasoning the WRITEGATE-001 grant above records. The new
#: `responder_version.py` is the single-source expected-version constant, pinned
#: to `console/lua/copilot_responder.lua:82`; it deletes nothing and is listed
#: at 0 so that a future deletion there has to come back through this gate.
#:
#: Ownership, MEASURED rather than assumed: the WRITEGATE-001 grant above states
#: that SPEC "owns `server/safety/`", and that sentence was checked before this
#: grant was taken rather than read as a standing exclusive lock. It is not one.
#: SPEC-COPILOT-WRITEGATE-001 carries `updated: 2026-08-05` and has been static
#: since; two later SPECs edited `server/safety/` in the meantime (86fee6c,
#: SPEC-COPILOT-UNREQ-001, 2026-08-25; 0c0adfa, t104, 2026-08-26) and 053553f
#: (2026-08-16) adjusted gate grants directly. The sentence is the rationale for
#: THAT grant, not a lock enforced since -- recorded here so the next reader does
#: not re-litigate it from the sentence alone.
#:
#: This grant widens nothing beyond the seven pinned lines and the two rows.
#: A third new file under the chokepoint, an eighth deleted line, or any text
#: other than the seven pinned below still fails the gate.
_SAFETY_EXPECTED_DELETIONS = {
    "server/safety/audit.py": 10,
    "server/safety/backup.py": 2,
    "server/safety/blacklist.yaml": 1,
    "server/safety/console.py": 59,
    "server/safety/gate.py": 8,
    "server/safety/monitor.py": 3,
    "server/safety/responder_version.py": 0,
    # t272 (2026-09-06): `bootstrap.py` reopened with an ADD-ONLY 4-line
    # `else:` branch — when the session-start backup is deliberately skipped,
    # the periodic timer starts at boot instead of firing SaveShow at boot.
    # 0 deletions: nothing pinned below is touched.
    "server/safety/bootstrap.py": 0,
}
_SAFETY_ALLOWED_DELETED_LINES = {
    # SCOPE CORRECTION (T-I audit-log crash fix): AuditLog.record() used a
    # bare `json.dumps(enriched, ensure_ascii=False)` with no fallback for
    # non-serializable values -- a value like a CommandDecision object landing
    # in an event dict raised TypeError mid-write, so the single durable
    # audit write point (@MX:ANCHOR) silently lost the event instead of
    # recording it. The one-line write is replaced by a `default=str`
    # variant that degrades an unserializable value to its str() form rather
    # than dropping the whole event; this legitimately reopens audit.py under
    # the chokepoint for the first time, the same maintenance shape as the
    # `gate.py` extension above.
    # SECOND audit.py reopening (probe-traffic split, handoff 2026-08-15
    # item 2): the gate's read probes (state_query/property_query/heartbeat)
    # measured 99.9 % of the audit volume (~200 MB/day) and now route to a
    # capped, short-retention `probe-` file family; record()/purge/iterators
    # were reshaped around the two families. Same @MX:ANCHOR discipline — one
    # durable write point, deploy sub-sends (deploy_of) keep 90-day retention.
    # The nine deletions are the single-family write/purge/iterate lines the
    # two-family versions replaced (the T-I `default=str` line among them).
    # TENTH line (probe-split follow-up, 46d9002/363133f): the OSC-send
    # docstring '"""One console send (every OSC send maps 1:1 …)"""' was
    # replaced by the two-family version stating the bounded probe exception
    # — the doc had to change WITH the behavior it documents.
    "server/safety/audit.py": (
        '        """Append one audit event (AuditSink-compatible); adds a UTC timestamp."""',
        '        path = self._directory / f"{_FILE_PREFIX}{now:%Y%m%d}{_FILE_SUFFIX}"',
        r'            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")',
        "        cutoff = (now - timedelta(days=self._retention_days)).date()",
        '        for path in self._directory.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}"):',
        "                continue  # foreign file — never delete what we did not write",
        "            if file_date < cutoff:",
        "                path.unlink()",
        '        for path in sorted(self._directory.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}")):',
        '        """One console send (every OSC send maps 1:1 to an executed event)."""',
    ),
    "server/safety/backup.py": (
        "Three rules: ① once at session start, ② periodic (default 10 minutes,",
        '    """Drives the 3-rule backup policy against an injected backup action."""',
    ),
    # The version bump IS the revision: `version: 1` is replaced by
    # `version: 2`, which is the one deletion granted above. The entry addition
    # and the REVISION HISTORY block that justifies it are pure additions, so
    # they need no allowance -- and `test_safety_ruleset.py` pins the new
    # content exactly, so this grant cannot be used to smuggle a second entry.
    "server/safety/blacklist.yaml": ("version: 1",),
    # 2026-08-16 granted extension — preset-pool PAGING (PROTOCOL §4.2):
    # `query_state` gains a keyword-only `offset` (default 0 — historical
    # bytes preserved; the PRECHK signature pin machine-checks that shape).
    # console.py's fifteen deletions are the paging revision of query_state
    # (signature, one-line docstring, and the fixed-wire `_round_trip` call
    # replaced by an offset-aware wire choice) PLUS five ruff-format rewrap
    # pairs: entering the touched set made TestTouchedFilesPassLint demand
    # format-cleanliness on the whole file, so the historical non-clean
    # wrappings had to align WITH the edit that touched the file.
    # 2026-08-19 granted extension — the responder ALIAS SWAP (PR #56,
    # docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md §1.2/§1.3):
    # `ConsoleLink.execute` wraps every command as
    # `Plugin "CopilotResponder" "exec …"`, so re-deploying the responder made
    # `Delete Plugin <own slot>` a SELF-delete, which MA3 answers with a
    # confirmation dialog that OSC cannot reach ("User Canceled Command").
    # `_run_file_import` is therefore rewritten around a temporary console-named
    # alias, `_deploy_execute` gains `via=` so a step can run from a DIFFERENT
    # plugin, and `execute` delegates to `_execute(..., plugin_name=…)`. The
    # deletions below are exactly that rewrite (the old single-path import body,
    # the old `_deploy_execute` signature and its docstring, the one wire line
    # `execute` no longer builds itself) PLUS the fifteen paging-revision lines
    # granted on 2026-08-16, which the count above now folds in.
    # 2026-09-04 granted extension — the version-gate read (SPEC-COPILOT-
    # READBACK-002 M0). `ping` no longer answers a bare `bool` from a decoded
    # payload it throws away: it preserves `version` as a link attribute and
    # hands the classification to the health monitor. The two deletions are that
    # one-line docstring and the `note_ping_success()` call the new
    # version-aware notify replaces. `ConsolePort.ping()`'s signature is
    # UNCHANGED — the port contract is not part of this grant.
    "server/safety/console.py": (
        "            wire = build_exec_request(request_id, command)",
        '        """Responder heartbeat; updates the health monitor when attached."""',
        "            self._monitor.note_ping_success()",
        "        Idempotent: an existing plugin of the same Name is deleted first so a",
        "        re-deploy updates in place instead of creating a duplicate.",
        "    def _deploy_execute(self, command: str, sends: list[DeploySend]) -> ExecOutcome:",
        '        """One exec round-trip inside a deploy — recorded with its outcome."""',
        "        outcome = self.execute(command)",
        "                detail=outcome.detail,",
        "    def _run_file_import(",
        "        self, name: str, lua_source: str, sends: list[DeploySend]",
        "    ) -> ExecOutcome:",
        '            return ExecOutcome(status="failed", detail=f"cannot write plugin file {target}: {error}")',  # noqa: E501
        "        existing_slot: int | None = None",
        "        occupied: set[int] = set()",
        "        unnumbered = 0",
        '            pool = self._deploy_query_state("DataPool/Plugins", sends)',
        '            for child in pool.get("children", []):',
        "                if not isinstance(child, dict):",
        "                    continue",
        '                index = child.get("i")',
        "                if isinstance(index, int):",
        "                    occupied.add(index)",
        "                else:",
        "                    unnumbered += 1",
        '                if child.get("name") == name:',
        "                    existing_slot = index if isinstance(index, int) else None",
        "            pass  # non-fatal — proceed with the slot-1 fallback below",
        "        # A listed plugin whose real slot the responder could NOT establish",
        '        # (it omits "i" rather than substituting a listing position —',
        "        # PROTOCOL.md §4.2) makes the arithmetic below a guess: that plugin may",
        '        # sit in exactly the slot picked as "free", and `Import Plugin <slot>`',
        "        # would overwrite it. Refuse rather than gamble with the user's pool.",
        "        if unnumbered:",
        '                status="failed",',
        '                    f"cannot choose a free plugin slot: {unnumbered} plugin(s) in "',
        '                    "DataPool/Plugins reported no pool slot (the console exposes no "',
        '                    "usable child-index accessor), so importing could overwrite one"',
        "        if isinstance(existing_slot, int):",
        '            self._deploy_execute(f"Delete Plugin {existing_slot}", sends)',
        "            occupied.discard(existing_slot)",
        "        slot = 1",
        "        while slot in occupied:",
        "            slot += 1",
        '            pool = self._deploy_query_state("DataPool/Plugins", sends)',
        '            return ExecOutcome(status="unconfirmed", detail=f"imported but pool unreadable: {error}")',  # noqa: E501
        '        names = [c.get("name") for c in pool.get("children", []) if isinstance(c, dict)]',  # noqa: E501
        "        if name in names:",
        '            status="failed", detail=f"import did not create plugin {name!r} (pool: {names})"',  # noqa: E501
        "    def query_state(self, path: str) -> dict:",
        '        """Object-tree snapshot query (REQ-MVP-003); raises on failure/timeout."""',
        "        payload = self._round_trip(",
        "            build_state_query(request_id, path), request_id, self._timeouts.state_query_seconds",  # noqa: E501
        "            raise BodyUnavailable(",
        '                f"identity query failed for {reference!r}: {error}"',
        "            ) from error",
        "    def _fetch_body_at_path(",
        "        self, reference: str, path: str, *, allow_empty: bool",
        "    ) -> Sequence[str]:",
    ),
    # gate.py's three NEW deletions (2026-08-16 paging) are the two
    # `query_state` signatures gaining the same keyword-only offset and the
    # fixed `self._console.query_state(path)` call replaced by the
    # offset-conditional pair — the audited chokepoint rides through
    # unchanged (`_query_state` still audits every send, 1:1).
    "server/safety/gate.py": (
        "from server.safety.backup import BackupError, BackupManager",
        '    """StateQueryPort implementation riding the gate-audited console link."""',
        "    def query_state(self, path: str) -> dict:",
        # 2026-09-04 granted extension — the same version-gate read
        # (SPEC-COPILOT-READBACK-002 M0). `_check_health`'s probe returned a
        # health state derived from reachability alone; it now derives it from
        # reachability AND the preserved responder version, so the one-line
        # docstring and the unconditional `note_ping_success()` call are
        # replaced. Same function, same requirement, third file.
        '        """Probe the responder once; audited; returns the resulting health state."""',
        "            self.monitor.note_ping_success()",
        '        """Attach a BackupManager whose action saves the showfile via this gate."""',
        "    def _query_state(self, path: str) -> dict:",
        "            payload = self._console.query_state(path)",
    ),
    # 2026-09-04 granted exception — monitor.py joins the chokepoint for the
    # first time (SPEC-COPILOT-READBACK-002 M0). The three deletions are the
    # WHOLE of `note_ping_success`: its signature, its one-line docstring, and
    # the single `self._state = self.ONLINE` assignment. That function said "a
    # heartbeat answered -> ONLINE" unconditionally, which is exactly the claim
    # REQ-READBACK2-003 has to qualify — a heartbeat from a version-mismatched
    # responder answered, and the path is NOT healthy. The replacement is
    # version-aware, so the unconditional form had to go rather than be extended.
    "server/safety/monitor.py": (
        "    def note_ping_success(self) -> None:",
        '        """A responder heartbeat answered — the full path is healthy."""',
        "        self._state = self.ONLINE",
    ),
    # 2026-09-04 — the expected-version constant's own file, pinned at ZERO
    # deletions rather than omitted. It is a pure addition today; listing it
    # empty means the first deletion inside it has to come back through this
    # gate instead of arriving unnoticed under a file nobody pinned.
    "server/safety/responder_version.py": (),
}

_HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")

_DESCOPE_LINE = "DESCOPE: ASSUMPTION-27"
_PRECHK_SPEC_DIR = ".moai/specs/SPEC-COPILOT-PRECHK-001/"
_PRECHK_PROGRESS = f"{_PRECHK_SPEC_DIR}progress.md"

#: 2026-08-07 granted exception — the spec-feasibility correction pass
#: (PR #29, commit ``2d04125``, user-mandated: "완결 SPEC의 과거 판정은 사실이다.
#: 뒤집혔으면 원문 보존 + 소급 정정 각주. 고쳐 쓰는 것은 미래를 가리키는 문장뿐이다").
#:
#: The pass rewrote TEN rows across the predecessor's two FORWARD-POINTING
#: candidate tables (§E.3a "다음 후보" and the "후속 후보 순위" table) because five
#: of them named work that had since SHIPPED and two named a wrong blocker. A
#: stale "막혀 있다" row is not inert: it stops the next reader from starting work
#: that is already possible. NOTHING measured was erased — no ASSUMPTION verdict,
#: no evidence row, no DESCOPE line (that one keeps its own gate below).
#:
#: Pinned two ways, following ``_SAFETY_ALLOWED_DELETED_LINES``: the row keys are
#: listed so a reader sees WHAT was granted, and the digest fixes the exact text
#: of all ten so a reader cannot grow the grant. Deleting an eleventh line — or
#: one different byte of these ten — still fails the gate. A future correction to
#: this file needs its own grant; that re-review is the point.
_PRECHK_GRANTED_DOC = _PRECHK_PROGRESS
_PRECHK_GRANTED_DELETED_ROW_KEYS = (
    "**FID 축**",
    "**구간 겹침 재개**",
    "**페이지·익스큐터 저작**",
    "**프리셋 읽기**",
    "SONGCUE 잔여 · P2-4 자동 페이퍼워크 · P2-5 볼런티어 런북",
    "**1**",
    "3",
    "4",
    "5",
    "6",
)
#: sha256 of the ten deleted lines joined by "\n", in diff order.
_PRECHK_GRANTED_DELETION_DIGEST = "3c0748d55a049581e2b9592762299177a02e227963072ddb44c013489a56b88a"


def _git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *arguments],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _deleted_lines(base: str, path: str) -> list[str]:
    """The `-` body lines of a diff, with the marker stripped and headers dropped."""
    body = _git("diff", f"{base}..HEAD", "--", path).splitlines()
    return [line[1:] for line in body if line.startswith("-") and not line.startswith("---")]


def _preserve_diff_command() -> list[str]:
    # Three granted extensions are checked by their own narrower gates below:
    # the looks-library one by exact line text, the rulebook and console-lua
    # ones by named locked assets (added path / untouched assets
    # respectively). Every OTHER preserved path must still diff empty, and
    # each grant's named assets are listed here so they keep doing so.
    paths = tuple(
        path
        for path in _PRESERVE_PATHS
        if path not in (_LOOKS_LIBRARY_DIR, _RULEBOOK_DIR, _CONSOLE_LUA_DIR)
    )
    return [
        "git",
        "diff",
        "--stat",
        f"{_PRECHK_BASE}..HEAD",
        "--",
        *paths,
        *_RULEBOOK_LOCKED_ASSETS,
        *_CONSOLE_LUA_LOCKED_ASSETS,
    ]


def _numstat(base: str, *paths: str) -> dict[str, tuple[int, int]]:
    rows = {}
    for line in _git("diff", "--numstat", f"{base}..HEAD", "--", *paths).splitlines():
        added, deleted, path = line.split("\t", 2)
        rows[path] = (int(added), int(deleted))
    return rows


def _hunks(base: str, path: str) -> list[tuple[int, int]]:
    found = []
    for line in _git("diff", "--unified=0", f"{base}..HEAD", "--", path).splitlines():
        match = _HUNK_RE.match(line)
        if match is not None:
            count = match.group("old_count")
            found.append((int(match.group("old_start")), 1 if count is None else int(count)))
    return found


def _overlaps(old_start: int, old_count: int, protected_start: int, protected_end: int) -> bool:
    old_end = old_start + max(old_count, 1) - 1
    return old_start <= protected_end and protected_start <= old_end


class TestPreserveList:
    """AC-OVERLAP-019 ③ — the list is real before it is used."""

    def test_the_list_has_ten_entries(self):
        assert len(_PRESERVE_PATHS) == 10
        assert len(set(_PRESERVE_PATHS)) == 10

    def test_every_entry_exists_on_disk(self):
        missing = [path for path in _PRESERVE_PATHS if not (_REPO_ROOT / path).exists()]
        # A path that does not exist contributes no rows to `--stat`, so one typo
        # turns the gate below into a permanent pass.
        assert missing == []

    def test_the_file_and_directory_split_is_derived_not_written_down(self):
        directories = [path for path in _PRESERVE_PATHS if (_REPO_ROOT / path).is_dir()]
        files = [path for path in _PRESERVE_PATHS if (_REPO_ROOT / path).is_file()]
        # Derived from the list itself: a hand-kept count was wrong once already
        # (the plan-phase audit found "4 directories and 6 files" for a 3/7 split).
        assert len(directories) + len(files) == len(_PRESERVE_PATHS)
        assert len(directories) == 3
        assert len(files) == 7
        # And every directory entry ends with a separator, so `--` treats it as a
        # prefix rather than as a missing file.
        assert all(path.endswith("/") for path in directories)


class TestPreserveScopeCitations:
    """t162·t177 — 독스트링이 가리키는 선언이 아직 그 자리에 그 내용으로 있는가.

    주석은 실행되지 않으므로 가리킨 문서가 움직여도 조용히 어긋난다. 이 저장소는
    그 형태를 이미 한 번 겪었다 — 가리킨 §F 헤딩이 목적지에 아예 없던 「끊어진
    참조」(``SPEC-COPILOT-SONGCUE-001/progress.md:146``).

    🔴 **t177 에서 줄번호를 버리고 내용으로 걸도록 바꿨다.** t162 는 ``plan.md:89``
    를 줄번호로 읽었는데, 실측해 보니 그 형태가 두 값을 치렀다:

    * **커버리지가 우발적이었다.** 선언 네 행 중 의도적으로 덮인 것은 89 하나뿐이고,
      91 은 비공허성 대조군이 ``+2`` 를 읽으면서 **우연히** 덮었다(그 대조군을 손대면
      조용히 사라진다). 90 과 92 는 선언을 통째로 지워도 **초록이었다.**
    * **삽입에 거짓 경보를 냈다.** 표 위에 빈 줄 하나만 끼면 선언이 멀쩡한데도 두 건이
      빨개졌다.

    재배열을 못 잡아서가 **아니다** — 줄번호 검사도 재배열은 잡는다(실측). 문제는
    커버리지와 거짓 경보였다. 그래서 좌표를 **구역 + 내용 동거**로 바꾼다: §A.5 표
    구역 안에서 경로 조각과 방침 문구가 **같은 줄에** 있는지를 본다. 줄이 밀리거나
    행이 재배열돼도 안 깨지고, **선언이 사라지거나 문구가 바뀌는 것**은 잡는다.

    그리고 검사가 :data:`_PRESERVE_PATHS` 를 **돌면서** 확인하므로, 목록에 열한 번째
    경로가 추가되면 그 경로의 선언도 함께 요구된다. 이것은 처방이 아니라 **새 능력**이다.
    """

    _PRECHK_PLAN = ".moai/specs/SPEC-COPILOT-PRECHK-001/plan.md"
    #: §A.5 표 구역을 여는 내용 앵커. 줄번호가 아니다.
    _PRECHK_TABLE_HEADING = "### §A.5 PRESERVE 재확인"
    _SONGCUE_SPEC = ".moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md"
    _SONGCUE_REQ_ID = "REQ-SONGCUE-021"

    #: (목록 항목, 그 항목을 든 표 행의 경로 조각, 같은 줄에 있어야 하는 방침 문구).
    #: 표는 경로를 중괄호 묶음과 ``**`` 글롭으로 적으므로 목록 문자열과 글자가 다르다 —
    #: 그래서 조각을 손으로 든다. 아래 첫 검사가 이 표의 첫 칸 집합이
    #: ``_PRESERVE_PATHS`` 와 정확히 같은지를 강제하므로, 손으로 든 것이 목록과
    #: 어긋날 수는 없다.
    _DECLARATIONS = (
        ("server/looks/schema.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/loader.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/roles.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/resolver.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/instantiate.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/matching.py", "server/looks/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/looks/library/", "server/looks/library/", "PRECHK는 룩 계층 소비자가 아니다"),
        ("server/web/preview.py", "server/web/preview.py", "웹 미리보기 산출물 없음"),
        ("console/lua/", "console/lua/", "응답기 변경 0건"),
        (
            "server/rulebook/assets/v2.4.2/",
            "server/rulebook/assets/v2.4.2/",
            "룰북을 편집하지 않는다",
        ),
    )

    @staticmethod
    def _read(path: str) -> str:
        return (_REPO_ROOT / path).read_text(encoding="utf-8")

    @classmethod
    def _prechk_table(cls) -> list[str]:
        """§A.5 표 구역의 행들. 구역은 헤딩부터 다음 ``---`` 까지다."""
        lines = cls._read(cls._PRECHK_PLAN).splitlines()
        start = next(i for i, line in enumerate(lines) if cls._PRECHK_TABLE_HEADING in line)
        rest = lines[start + 1 :]
        end = next(i for i, line in enumerate(rest) if line.startswith("---"))
        return [line for line in rest[:end] if line.startswith("|")]

    @staticmethod
    def _declared(rows: list[str], fragment: str, policy: str) -> bool:
        """경로 조각과 방침 문구가 **같은 줄에** 있는가.

        술어를 여기 한 번만 두는 것이 [HARD] 다. 아래 대조군이 같은 함수를 쓰므로,
        「같은 줄」 조건을 「표 어딘가에」로 무르면 대조군이 빨개진다. t177 1회차에는
        대조군이 술어를 **복사**하고 있었고, 그래서 구현을 무르는 뮤테이션이 살아남았다 —
        대조군이 자기가 지키려던 조건을 안 지키고 있었다.
        """
        return any(fragment in row and policy in row for row in rows)

    def test_the_declaration_table_is_readable_and_not_empty(self):
        """비공허성 — 구역을 못 찾으면 아래 전부가 헛돈다."""
        rows = self._prechk_table()
        assert len(rows) >= 5, rows
        # 머리 두 줄(제목 · 구분)을 뺀 실제 선언 행이 있어야 한다.
        assert any("변경 0건" in row for row in rows)

    def test_every_preserved_path_has_a_declaration(self):
        """🔴 t177 의 본체 — 목록을 **돌면서** 확인하므로 새 항목이 선언을 강제받는다.

        t162 는 네 선언 행 중 하나만 의도적으로 덮었다. 90(``preview.py``)과
        92(룰북)는 선언을 통째로 지워도 초록이었고, 91 은 대조군이 우연히 덮고
        있었다. 여기서 넷 다 의도적으로 덮는다.
        """
        assert set(entry for entry, _, _ in self._DECLARATIONS) == set(_PRESERVE_PATHS)
        rows = self._prechk_table()
        for entry, fragment, policy in self._DECLARATIONS:
            assert self._declared(rows, fragment, policy), entry

    def test_a_declaration_is_not_satisfied_by_the_wrong_row(self):
        """비공허성 — 조각과 문구가 **같은 줄에** 있어야 한다.

        둘을 따로 찾으면 표 어딘가에 각각 있기만 해도 통과한다. 실제로
        ``server/web/preview.py`` 와 ``응답기 변경 0건`` 은 표에 **둘 다 있지만
        서로 다른 행**이므로, 짝으로는 성립하면 안 된다.

        🔴 이 검사는 구현과 **같은 함수**(:meth:`_declared`)를 부른다. 술어를 복사해
        두면 구현만 무르는 변경에 이 대조군이 안 반응한다 — t177 1회차에 실제로
        그 뮤테이션이 살아남았다.
        """
        rows = self._prechk_table()
        assert any("server/web/preview.py" in row for row in rows)
        assert any("응답기 변경 0건" in row for row in rows)
        assert not self._declared(rows, "server/web/preview.py", "응답기 변경 0건")

    def test_the_songcue_requirement_still_binds_the_preserve_list(self):
        """선례 게이트의 여섯 파일이 오는 자리. 여기도 줄번호가 아니라 내용이다."""
        lines = [
            line
            for line in self._read(self._SONGCUE_SPEC).splitlines()
            if self._SONGCUE_REQ_ID in line
        ]
        assert lines, self._SONGCUE_REQ_ID
        assert any("PRESERVE" in line and "shall not" in line for line in lines)

    def test_the_scope_declaration_block_is_still_written_down(self):
        """문구 단언 — 위 성질 검사들과 **다른 행**이고 서로를 못 대신한다.

        선언이 다 제자리여도 독스트링이 지워지면 읽는 법이 사라지고, 독스트링이
        멀쩡해도 선언이 사라지면 가리키는 곳이 빈다.

        🔴 우주는 파일이 아니라 **모듈 독스트링**(``__doc__``)이다. 파일 전체에 대고
        찾으면 이 메서드가 든 리터럴 자신이 매치돼 공허해진다(t162 실측).
        """
        assert __doc__ is not None
        assert len(__doc__) > 500
        assert "범위 선언이다" in __doc__
        assert "집행되는 경계" in __doc__
        assert self._PRECHK_PLAN in __doc__
        assert self._SONGCUE_SPEC in __doc__

    def test_the_list_carries_a_pointer_to_the_docstring(self):
        """목록 옆에 착지한 독자를 위로 보내는 포인터가 아직 있는가."""
        source = Path(__file__).read_text(encoding="utf-8")
        header = source[: source.index("_PRESERVE_PATHS = (")]
        assert "이 모듈의 독스트링" in header
        pointer_zone = header[header.index("#: The ten paths") :]
        assert "뒤의 것으로 읽으면" not in pointer_zone

    def test_the_precedent_gate_points_here_instead_of_copying(self):
        """선례 게이트는 같은 설명을 복사하지 않고 이 파일을 가리킨다."""
        precedent = (_REPO_ROOT / "server/tests/test_songcue_bundle.py").read_text(encoding="utf-8")
        assert "범위 선언이지 이 게이트가 만든" in precedent
        assert "server/tests/test_overlap_preserve.py" in precedent
        assert "집행되는 경계)의 구별" in precedent
        assert "뒤의 것으로 읽으면" not in precedent


class TestPreserveDiffIsEmpty:
    """AC-OVERLAP-019 ①② — the range is pinned, then the diff must be empty."""

    def test_the_gate_uses_the_predecessor_base_to_head_range(self):
        command = _preserve_diff_command()
        assert command[:4] == ["git", "diff", "--stat", f"{_PRECHK_BASE}..HEAD"]
        assert command[4] == "--"
        # Three granted extensions are swapped out of the directory sweep and
        # re-entered as the narrower thing that IS still locked: the looks
        # library by its own exact-text gate, the rulebook by its five named
        # existing assets, console/lua by its three named source/protocol
        # assets.
        assert tuple(command[5:]) == (
            *(
                path
                for path in _PRESERVE_PATHS
                if path not in (_LOOKS_LIBRARY_DIR, _RULEBOOK_DIR, _CONSOLE_LUA_DIR)
            ),
            *_RULEBOOK_LOCKED_ASSETS,
            *_CONSOLE_LUA_LOCKED_ASSETS,
        )
        # The swap must not silently drop the rulebook/console-lua boundary
        # from the gate entirely.
        assert _RULEBOOK_DIR not in command
        assert _CONSOLE_LUA_DIR not in command
        assert all(asset in command for asset in _RULEBOOK_LOCKED_ASSETS)
        assert all(asset in command for asset in _CONSOLE_LUA_LOCKED_ASSETS)
        # Explicitly NOT this SPEC's base: that range is empty right after the
        # work is committed, which disables the gate while keeping it green.
        assert _PRECHK_BASE != _OVERLAP_BASE
        assert f"{_OVERLAP_BASE}..HEAD" not in command

    def test_the_preserved_paths_are_unchanged(self):
        assert _PRESERVE_PATHS
        assert _git(*_preserve_diff_command()[1:]) == ""

    def test_the_same_command_detects_a_change_elsewhere(self):
        # Non-vacuity for the emptiness above: the command shape CAN report.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", "server/prechk/") != ""


class TestRulebookGrantedAddition:
    """The 2026-08-03 grant — exactly one added asset, and nothing removed.

    Not a weakening: the five existing assets are named in
    :func:`_preserve_diff_command`, so modifying any of them still fails the
    emptiness gate above. This class is the other half — it bounds what the
    grant permits, so "one new rulebook file" cannot quietly become two, or
    become a rewrite of an old one.
    """

    def test_the_four_fully_locked_assets_are_the_locked_set(self):
        # Non-vacuity: a typo'd path contributes nothing to a git diff, so the
        # locked list is checked against the real directory listing. The fifth
        # pre-existing asset, 31_choreography_patterns.md, moved to the
        # narrower APPEND-ONLY grant below (REQ-FXGEN-017 (b)).
        on_disk = sorted(
            path.name for path in (_REPO_ROOT / _RULEBOOK_DIR).iterdir() if path.suffix == ".md"
        )
        locked = sorted(Path(path).name for path in _RULEBOOK_LOCKED_ASSETS)
        granted = {Path(path).name for path in _RULEBOOK_GRANTED_ADDITIONS}
        granted.add(Path(_RULEBOOK_GRANTED_APPEND).name)
        assert locked == sorted(set(on_disk) - granted)
        assert len(_RULEBOOK_LOCKED_ASSETS) == 4

    def test_the_only_rulebook_changes_are_the_granted_ones(self):
        rows = _numstat(_PRECHK_BASE, _RULEBOOK_DIR)
        assert set(rows) == set(_RULEBOOK_GRANTED_ADDITIONS) | {_RULEBOOK_GRANTED_APPEND}

    def test_the_grant_removes_nothing(self):
        # A rulebook asset is a fixed system-prompt prefix; a deletion inside
        # this directory changes what every model call is told, whichever file
        # it lands in.
        rows = _numstat(_PRECHK_BASE, _RULEBOOK_DIR)
        for path, (_added, deleted) in rows.items():
            assert deleted == 0, path

    def test_the_locked_assets_are_byte_identical(self):
        # Stated directly as well as via the emptiness gate: this is the claim
        # the whole grant rests on, and it should be readable on its own.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", *_RULEBOOK_LOCKED_ASSETS) == ""


class TestChoreographyObservedEffectGrantedAppend:
    """The 2026-08-15 grant (REQ-FXGEN-017 (b)) — an APPEND-ONLY addition.

    The fx code cites ``31_choreography_patterns.md`` by LINE NUMBER (:75,
    :78-79, :80, :85-89, :236-241 …), so the grant's load-bearing property is
    that nothing above the old EOF moved: zero deleted lines means zero
    shifted lines, and every citation stays valid.
    """

    def test_the_append_deletes_nothing(self):
        assert _deleted_lines(_PRECHK_BASE, _RULEBOOK_GRANTED_APPEND) == []

    def test_the_addition_is_one_appended_hunk_at_the_old_eof(self):
        hunks = _hunks(_PRECHK_BASE, _RULEBOOK_GRANTED_APPEND)
        assert len(hunks) == 1
        old_start, old_count = hunks[0]
        assert old_count == 0, "an insertion hunk touches no old lines"
        # git names a pure insertion by the line it follows — the old EOF.
        text = _git("show", f"{_PRECHK_BASE}:{_RULEBOOK_GRANTED_APPEND}")
        assert old_start == len(text.splitlines())

    def test_the_appended_block_is_the_observed_effect_record(self):
        # Non-vacuity: the file really did change, and the change is the
        # measurement record the grant names, not arbitrary prose.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", _RULEBOOK_GRANTED_APPEND) != ""
        added = [
            line[1:]
            for line in _git(
                "diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", _RULEBOOK_GRANTED_APPEND
            ).splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        assert _RULEBOOK_APPEND_HEADING in added


class TestConsoleLuaReadmeGrantedException:
    """The 2026-08-12 README grant + the 2026-08-16 paging revision grant.

    Not a weakening: the plugin wrapper stays byte-locked and named in
    :func:`_preserve_diff_command`, while the two 2026-08-16-revised files
    (responder source + wire protocol) are pinned by CONTENT DIGEST — one
    byte of drift past the granted revision still fails, and the next
    legitimate revision must re-pin the digests deliberately. This class
    bounds the directory's change set to exactly those grants.
    """

    def test_the_locked_console_lua_assets_are_byte_identical(self):
        # Stated directly as well as via the emptiness gate: this is the claim
        # the whole grant rests on, and it should be readable on its own.
        assert (
            _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", *_CONSOLE_LUA_LOCKED_ASSETS) == ""
        )

    def test_the_revised_assets_match_the_granted_digests_exactly(self):
        for path, digest in _CONSOLE_LUA_GRANTED_REVISION_DIGESTS.items():
            assert _git("hash-object", path).strip() == digest, path

    def test_the_only_console_lua_changes_are_the_granted_ones(self):
        rows = _numstat(_PRECHK_BASE, _CONSOLE_LUA_DIR)
        assert set(rows) == {"console/lua/README.md"} | set(_CONSOLE_LUA_GRANTED_REVISION_DIGESTS)

    def test_the_grant_is_not_an_empty_exemption(self):
        # Non-vacuity, this module's own standard: both assertions above are
        # satisfied by an untouched directory too, since `console/lua/` is
        # filtered out of `_preserve_diff_command()`. Pin that the directory
        # really did change.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", _CONSOLE_LUA_DIR) != ""


class TestLooksLibraryGrantedExtension:
    """Two grants — the 2026-08-02 파란 mirror and the 2026-09-06 D1 append.

    Not a weakening: the boundary stays locked, and this class IS the lock's
    shape. Every deleted line must reappear as its paired insertion with 파란
    added; every added line must be either one of those pairs' new lines or a
    line of a granted append block; an extra file, an extra hunk, or a
    different wording fails.

    **The two grants are checked TOGETHER, per file, by exact equality.** They
    overlap on ``edm.yaml`` — it carries a 파란 pair AND an appended look — so
    checking either grant alone would read the other's lines as unsanctioned.
    Concatenating them is sound only because the append lands at the old EOF
    and is therefore the LAST hunk, which
    :func:`test_each_granted_addition_is_one_appended_hunk_at_the_old_eof`
    asserts rather than assumes.
    """

    @staticmethod
    def _diff_lines(path: str) -> tuple[list[str], list[str]]:
        deleted, added = [], []
        for line in _git("diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", path).splitlines():
            if line.startswith("-") and not line.startswith("---"):
                deleted.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
        return deleted, added

    def test_the_grant_is_not_an_empty_exemption(self):
        # Non-vacuity, the standard this module sets for itself. The
        # assertions below are satisfied by EMPTY grants — `set() == set()`
        # and loops that never run — while `server/looks/library/` stays
        # filtered out of `_preserve_diff_command()`. That combination is a
        # gate that is off AND green, so pin every half: BOTH grants have
        # entries, and the directory they exempt really did change.
        assert _LOOKS_GRANTED_LINE_PAIRS
        assert _LOOKS_GRANTED_D1_APPENDS
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", _LOOKS_LIBRARY_DIR) != ""

    def test_exactly_the_four_granted_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _LOOKS_LIBRARY_DIR)
        # The UNION of the two grants, not either one alone. `edm.yaml` is in
        # both, `rock.yaml` only in the append grant, `ballad`/`worship` only
        # in the pair grant. A fifth file still fails.
        assert set(rows) == set(_LOOKS_GRANTED_FILES)
        assert len(_LOOKS_GRANTED_FILES) == 4

    def test_every_change_is_a_granted_line_pair_and_every_pair_is_present(self):
        for path in sorted(_LOOKS_GRANTED_FILES):
            prose = _LOOKS_GRANTED_COUNT_PROSE_PAIRS.get(path, ())
            pairs = _LOOKS_GRANTED_LINE_PAIRS.get(path, ())
            appended = _LOOKS_GRANTED_D1_APPENDS.get(path, ())
            deleted, added = self._diff_lines(path)
            # Exact equality on BOTH sides, deliberately. Relaxing either to a
            # subset test is the cheapest way to make an unsanctioned edit pass
            # and would void the whole gate — see the grant comments above.
            #
            # The concatenation ORDER is diff order, which is file-position
            # order: the count-prose line (old 7) precedes the 파란 line
            # (old 74), which precedes the old EOF. That claim is not assumed
            # here — `test_the_granted_hunks_appear_in_the_order_this_class_
            # concatenates_them` measures it.
            assert deleted == [old for old, _new in prose] + [old for old, _new in pairs], path
            assert added == [new for _old, new in prose] + [new for _old, new in pairs] + list(
                appended
            ), path

    def test_the_granted_hunks_appear_in_the_order_this_class_concatenates_them(self):
        # The assertion above concatenates three grants in a fixed order. If the
        # diff ever produced them in a different order the equality would fail
        # confusingly, so pin the ordering claim itself, measured from the diff.
        for path in sorted(_LOOKS_GRANTED_FILES):
            starts = [old_start for old_start, _old_count in _hunks(_PRECHK_BASE, path)]
            assert starts == sorted(starts), path
            prose_count = len(_LOOKS_GRANTED_COUNT_PROSE_PAIRS.get(path, ()))
            if prose_count and path in _LOOKS_GRANTED_LINE_PAIRS:
                # The prose correction sits in the file header, above every
                # look — so above every 파란 line by construction.
                assert starts[0] < starts[prose_count], path

    def test_each_granted_addition_is_one_appended_hunk_at_the_old_eof(self):
        # Shape, following `TestChoreographyObservedEffectGrantedAppend`: a
        # pure insertion (`old_count == 0`) named by the line it follows. That
        # the insertion is the LAST hunk is what makes the concatenation order
        # in the assertion above sound rather than lucky.
        for path in _LOOKS_GRANTED_D1_APPENDS:
            hunks = _hunks(_PRECHK_BASE, path)
            insertions = [hunk for hunk in hunks if hunk[1] == 0]
            assert len(insertions) == 1, path
            text = _git("show", f"{_PRECHK_BASE}:{path}")
            assert hunks[-1] == (len(text.splitlines()), 0), path

    def test_each_appended_block_defines_exactly_one_look(self):
        # This is where the grant's WIDTH is pinned mechanically. "One look per
        # file" is the whole scope of the 2026-09-06 addition; without this,
        # the exact-line-text assertion would still pass for a re-pinned block
        # carrying two looks.
        for path, block in _LOOKS_GRANTED_D1_APPENDS.items():
            assert block, path
            starts = [line for line in block if line.lstrip().startswith("- look_id:")]
            assert len(starts) == 1, path

    def test_the_grant_really_is_the_blue_mirror_and_nothing_broader(self):
        # Non-vacuity + shape: each pair differs ONLY by inserting 파란 tokens.
        for pairs in _LOOKS_GRANTED_LINE_PAIRS.values():
            for old, new in pairs:
                assert old != new
                assert "파란" not in old
                assert "파란" in new
                # Removing the 파란 tokens from the new line restores the old
                # one exactly — the grant cannot smuggle an unrelated edit.
                stripped = new.replace(', "파란 밤"', "").replace(', "파란 벌스"', "")
                stripped = stripped.replace('"파란", ', "")
                assert stripped == old


class TestToolsProtectedRegions:
    """AC-OVERLAP-019 ④ — position blockade on the predecessor's base."""

    def test_no_hunk_crosses_a_protected_region(self):
        hunks = _hunks(_PRECHK_BASE, _TOOLS_PATH)
        assert hunks, "hunk을 하나도 읽지 못하면 교차 0건 판정이 공허하다"
        crossings = [
            (start, count, protected)
            for start, count in hunks
            for protected in _TOOLS_PROTECTED_OLD_RANGES
            if _overlaps(start, count, *protected)
        ]
        assert crossings == []

    def test_the_blockade_would_catch_a_planted_hunk(self):
        # Non-vacuity: the overlap predicate is not simply always false.
        for protected_start, protected_end in _TOOLS_PROTECTED_OLD_RANGES:
            assert _overlaps(protected_start, 1, protected_start, protected_end)
            assert _overlaps(protected_end, 1, protected_start, protected_end)
            assert not _overlaps(protected_end + 1, 1, protected_start, protected_end)

    def test_the_ranges_are_the_predecessor_base_values_not_the_precedent_file_s(self):
        """The two bases differ by thirteen lines; copying is the trap.

        The precedent file's ranges are ``(234, 238)`` and ``(524, 569)``. Using
        those numbers against THIS base guards a comment and stops thirteen lines
        short of the loop's final statement.
        """
        assert _TOOLS_PROTECTED_OLD_RANGES == ((247, 251), (537, 582))
        assert [start for start, _end in _TOOLS_PROTECTED_OLD_RANGES] == [234 + 13, 524 + 13]

    def test_a_deletion_count_rule_would_be_the_wrong_shape_here(self):
        """Why this is a POSITION blockade and not "zero deletions".

        ``tools.py`` deletes one line relative to this base -- an import statement
        replaced by a block. A deletion-count rule would fail on arrival, and the
        next reader would weaken the gate to make it pass.
        """
        added, deleted = _numstat(_PRECHK_BASE, _TOOLS_PATH)[_TOOLS_PATH]
        assert added >= 1
        assert deleted >= 1


class TestSafetyChokepointFileSet:
    """AC-OVERLAP-019 ⑤ — which files, and which deletions."""

    def test_exactly_the_expected_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        assert set(rows) == set(_SAFETY_EXPECTED_DELETIONS)

    def test_the_deletion_counts_match(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        for path, expected in _SAFETY_EXPECTED_DELETIONS.items():
            assert rows[path][1] == expected, path

    def test_the_deletions_are_exactly_the_pinned_lines(self):
        """A bare count lets a meaningful removal hide -- the deleted TEXT is
        pinned per file, not just the total.

        SCOPE CORRECTION (SPEC-COPILOT-BACKUP-001 T-B/T-B2 integration,
        mirroring the ``tools.py`` correction at
        :class:`TestPrecedentGateFileIsNotExtended`): the predecessor's grant
        removed exactly one docstring line in gate.py. This SPEC legitimately
        extends the chokepoint further -- BackupManager gains snapshot
        retention + a gate-level eviction hook, no restore SEND path (see
        server/safety/backup.py's module docstring) -- so its own edits
        delete an import line and two more docstrings alongside the
        predecessor's line. Not every deletion is a docstring any more (the
        import line is real code), so the old blanket "is-a-docstring" shape
        check is retired in favor of the stricter, general invariant it was
        always standing in for: exact text, per file.
        """
        for path, allowed in _SAFETY_ALLOWED_DELETED_LINES.items():
            deleted = [
                line[1:]
                for line in _git(
                    "diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", path
                ).splitlines()
                if line.startswith("-") and not line.startswith("---")
            ]
            assert deleted == list(allowed), path

    def test_overlap_s_own_scope_changed_nothing_under_the_chokepoint(self):
        """SCOPE CORRECTION (SPEC-COPILOT-BACKUP-001 T-B/T-B2 integration).

        This used to read ``_git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD",
        ...) == ""`` -- "this SPEC changed nothing under the chokepoint". That
        was true and MEASURABLE while OVERLAP's own merge was still HEAD. It
        stops being measurable the moment a later SPEC legitimately reopens
        the chokepoint (exactly the ``tools.py`` failure mode documented at
        :class:`TestPrecedentGateFileIsNotExtended`): the range then spans the
        later SPEC's commits too, and the gate fails while the fact it names
        -- OVERLAP itself opened nothing new -- is still true.

        What survives is bounding BOTH ends instead of leaving one open at
        HEAD: ``_OVERLAP_BASE.._OVERLAP_MERGE_COMMIT`` is OVERLAP's own,
        now-immutable commit range, so this fact is checked exactly where it
        was made rather than at an ever-moving present.
        """
        assert (
            _git("diff", "--stat", f"{_OVERLAP_BASE}..{_OVERLAP_MERGE_COMMIT}", "--", _SAFETY_DIR)
            == ""
        )

    def test_this_spec_s_base_can_still_observe_a_change(self):
        """AC-OVERLAP-002 ④ — 비공허성: 같은 명령이 변화를 볼 수 있는가.

        위 ③은 ``_OVERLAP_BASE.._OVERLAP_MERGE_COMMIT`` 범위에서 chokepoint가
        비어 있다고 주장한다. 같은 명령 형태를 이 SPEC이 실제로 건드린
        ``server/prechk/``에 겨누면 비어 있지 않아야 한다. 여기가 비면 명령이
        변화를 관측하지 못하게 된 것이고, ③의 빈 출력은 아무 의미도 없어진다.

        이 구멍은 좁다: ``_OVERLAP_BASE``를 무력화하는 드리프트는
        :func:`test_the_touched_set_is_not_empty`가 이미 잡는다. 그럼에도 ③이
        이름 붙인 BASE에 대한 대조군은 그 자리에 있어야 한다.
        """
        assert _git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD", "--", "server/prechk/") != ""


class TestPrecedentGateFileIsNotExtended:
    """AC-OVERLAP-019 ⑥ — one base per module."""

    def test_the_precedent_file_still_pins_its_own_protected_ranges(self):
        # SCOPE CORRECTION (SPEC-COPILOT-FXLIB-001 integration, 2026-08-01).
        #
        # This assertion used to read `_numstat(_OVERLAP_BASE, precedent) == {}`
        # -- "this SPEC did not extend the precedent file". That was true and
        # measurable while OVERLAP was the only unmerged work on its base. It
        # stopped being MEASURABLE the moment a sibling SPEC landed on the same
        # base: the range `_OVERLAP_BASE..HEAD` then spans the sibling's commits
        # too, so the diff reports the SIBLING's edits and the gate fails while
        # the property it names is still true. FXLIB legitimately extended the
        # precedent's positional list because it touched `tools.py` -- that is
        # the tripwire's designed maintenance, not a violation.
        #
        # What survives the merge is the invariant the zero-rows form was a
        # proxy FOR: the precedent's tripwire must still pin protected ranges on
        # its own base. That is asserted here, and the precedent asserts the
        # ranges themselves in its own module (one base per module, AC-OVERLAP-019 ⑥).
        precedent = (_REPO_ROOT / "server/tests/test_songcue_bundle.py").read_text(encoding="utf-8")
        assert "_TOOLS_EXPECTED_HUNK_OLD_STARTS" in precedent
        assert "_TOOLS_PROTECTED_RANGES" in precedent or "protected" in precedent
        # Non-vacuity: a file that lost its tripwire would still contain the
        # word "protected" in prose, so the positional list is the real anchor
        # and it is checked by identity above, not by substring in a comment.
        assert re.search(r"_TOOLS_EXPECTED_HUNK_OLD_STARTS\s*=\s*\(", precedent)

    def test_this_file_owns_the_predecessor_base_alone(self):
        """Neither module may hold the other's base.

        The precedent's SHA is READ from its own source rather than retyped here:
        retyping it would both invite drift and put the string this test forbids
        into the very file it is checking.
        """
        precedent = (_REPO_ROOT / "server/tests/test_songcue_bundle.py").read_text(encoding="utf-8")
        assert _PRECHK_BASE not in precedent
        found = re.search(r'_RUN_PHASE_BASE = "([0-9a-f]{40})"', precedent)
        # Non-vacuity: the precedent file really does pin a base -- a different one.
        assert found is not None
        precedent_base = found.group(1)
        assert precedent_base != _PRECHK_BASE
        assert precedent_base != _OVERLAP_BASE
        module_strings = [
            value
            for name, value in globals().items()
            if isinstance(value, str) and not name.startswith("__")
        ]
        assert module_strings, "모듈 상수를 모으지 못하면 이 단정이 공허하다"
        assert precedent_base not in module_strings


class TestPredecessorSpecDocuments:
    """AC-OVERLAP-019 ⑧ — the one assertion that uses THIS SPEC's base."""

    def test_every_predecessor_document_but_the_granted_one_is_untouched(self):
        others = _git(
            "diff",
            "--stat",
            f"{_OVERLAP_BASE}..HEAD",
            "--",
            _PRECHK_SPEC_DIR,
            f":(exclude){_PRECHK_GRANTED_DOC}",
        )
        assert others == ""

    def test_the_exclusion_above_is_not_swallowing_the_whole_directory(self):
        """Non-vacuity: `:(exclude)` on a mistyped path would empty the diff."""
        assert _git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD", "--", _PRECHK_SPEC_DIR) != ""

    def test_the_granted_document_deleted_exactly_the_ten_granted_rows(self):
        deleted = _deleted_lines(_OVERLAP_BASE, _PRECHK_GRANTED_DOC)
        assert len(deleted) == len(_PRECHK_GRANTED_DELETED_ROW_KEYS)
        keys = tuple(line.split("|")[1].strip() for line in deleted)
        assert keys == _PRECHK_GRANTED_DELETED_ROW_KEYS
        digest = hashlib.sha256("\n".join(deleted).encode("utf-8")).hexdigest()
        assert digest == _PRECHK_GRANTED_DELETION_DIGEST

    def test_the_digest_would_reject_an_eleventh_deletion(self):
        """Non-vacuity: the pin is content-sensitive, not just count-sensitive."""
        deleted = _deleted_lines(_OVERLAP_BASE, _PRECHK_GRANTED_DOC)
        smuggled = [*deleted, "| 7 | 몰래 지운 행 | |"]
        digest = hashlib.sha256("\n".join(smuggled).encode("utf-8")).hexdigest()
        assert digest != _PRECHK_GRANTED_DELETION_DIGEST

    def test_the_predecessor_base_would_be_the_wrong_reference_here(self):
        """Why this single item uses a different base from the rest of the file.

        The predecessor's six SPEC documents were WRITTEN AFTER the base the
        PRESERVE gate uses, so a diff from there carries their entire initial
        authoring and can never be empty. This SPEC's base is the predecessor's
        last documentation commit, so changes after it are exactly what this SPEC
        touched.
        """
        from_predecessor_base = _git(
            "diff", "--numstat", f"{_PRECHK_BASE}..HEAD", "--", _PRECHK_SPEC_DIR
        )
        assert from_predecessor_base != ""
        assert len(from_predecessor_base.splitlines()) >= 2

    def test_the_descope_line_is_still_exactly_one(self):
        text = (_REPO_ROOT / _PRECHK_PROGRESS).read_text(encoding="utf-8")
        hits = [line for line in text.splitlines() if line.startswith(_DESCOPE_LINE)]
        assert len(hits) == 1


class TestTouchedFilesPassLint:
    """AC-OVERLAP-019 ⑨ — on the files this SPEC touched, derived not listed."""

    def _touched(self) -> list[str]:
        """이 SPEC 이 손댄 .py 목록. `core.quotePath=false` 가 [HARD] 다.

        기본값이면 git 이 **비ASCII 경로를 따옴표로 감싸고 바이트를 8진 이스케이프**해
        돌려준다(`"src/Lighting_Designer/90_\353\271\214…"`). 그 문자열은 디스크의
        어떤 파일과도 안 맞으므로 아래 `is_file()` 이 **조용히 전부 떨어뜨린다** —
        게이트는 초록인데 그 파일들은 한 번도 검사되지 않는다(t115: 380 중 369 만
        검사됐고, 빠진 11개가 전부 한글 경로였다).

        구멍을 되읽어 확인한다: 이 플래그를 빼면 `test_the_touched_set_covers_non_ascii_paths`
        가 빨개진다.
        """
        return [
            path
            for path in _git(
                "-c",
                "core.quotePath=false",
                "diff",
                "--name-only",
                f"{_OVERLAP_BASE}..HEAD",
                "--",
                "*.py",
            )
            .strip()
            .splitlines()
            if (_REPO_ROOT / path).is_file()
        ]

    def test_the_touched_set_is_not_empty(self):
        touched = self._touched()
        assert touched, "손댄 파일이 0건이면 아래 두 검사가 공허하다"
        assert all(path.endswith(".py") for path in touched)

    def test_the_touched_set_covers_non_ascii_paths(self):
        """t115 — 구멍을 직접 겨눈다. 「도는가」가 아니라 「몇 개를 덮는가」다.

        `core.quotePath=false` 가 빠지면 한글 경로가 따옴표에 싸여 돌아오고
        `is_file()` 이 전부 떨어뜨려 이 단언이 빨개진다. 게이트가 초록인 채로
        검사 범위만 줄어드는 것이 t115 가 잡은 결함이므로, **범위 자체**를 잰다.
        """
        touched = self._touched()
        non_ascii = [path for path in touched if any(ord(ch) > 127 for ch in path)]
        assert non_ascii, (
            "비ASCII 경로가 손댄 목록에 하나도 없다 — quotePath 가 다시 기본값이거나, "
            "이 SPEC 이 그런 파일을 더는 안 건드린다. 후자라면 이 검사를 지워라"
        )
        # 계기 검산 — git 이 몇 개를 보고했는지와 게이트가 몇 개를 보는지를 나란히
        # 둔다. 두 수가 갈리면 그 차이가 곧 조용히 빠진 파일 수다.
        reported = (
            _git(
                "-c",
                "core.quotePath=false",
                "diff",
                "--name-only",
                f"{_OVERLAP_BASE}..HEAD",
                "--",
                "*.py",
            )
            .strip()
            .splitlines()
        )
        assert len(touched) == len(reported), (
            f"git 은 {len(reported)}개를 보고했는데 게이트는 {len(touched)}개만 본다 — "
            f"빠진 것: {sorted(set(reported) - set(touched))}"
        )

    def test_ruff_check_passes_on_them(self):
        finished = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "check", *self._touched()],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr

    def test_ruff_format_reports_no_change(self):
        finished = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "format", "--check", *self._touched()],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr


class TestLintDeferralsDidNotGrow:
    """t115 — 유예가 조용히 자라면 그건 `exclude` 다.

    B 안(게이트를 고쳐 **보이게** 만들고 기존 위반은 명시 유예)의 유일한 정당화는
    **줄어드는 것이 눈에 보인다**는 점이다. 그 가시성을 사람 눈에 맡기면 유예는
    자란다 — 그래서 기계가 지킨다. `test_prechk_inventory.py` 의
    `test_operator_utility_exemptions_did_not_grow` 와 같은 형태다.
    """

    #: 유예 대상 11개. 후속 카드가 규칙을 실제로 고치며 이 목록을 **줄인다**.
    #: 늘리는 변경은 이 검사가 막는다.
    _DEFERRED_FILES = frozenset(
        f"{_T115_PIPELINE_DIR}/{name}"
        for name in (
            "exec_data.py",
            "make_exec.py",
            "make_ma3.py",
            "make_rig.py",
            "make_timeline.py",
            "make_xlsx.py",
            "rig_data.py",
            "seq_data.py",
            "validate.py",
            "validate_ma3.py",
            "validate_rig.py",
        )
    )

    #: t115 착수 시점의 (파일, 규칙) 쌍 수. 상한이지 목표가 아니다.
    _PAIR_CEILING = 85

    @staticmethod
    def _config() -> dict:
        with (_REPO_ROOT / "pyproject.toml").open("rb") as handle:
            return tomllib.load(handle)

    def _per_file_ignores(self) -> dict:
        return self._config()["tool"]["ruff"]["lint"]["per-file-ignores"]

    def test_the_ignore_list_is_not_vacuous(self):
        """공허 방지 먼저 — 목록이 비면 아래 「안 늘었다」가 거저 참이 된다."""
        ignores = self._per_file_ignores()
        assert ignores, "per-file-ignores 가 비었다 — 아래 검사들이 공허하다"
        assert all(codes for codes in ignores.values()), "규칙이 빈 항목이 있다"

    def test_no_file_joined_the_ignore_list(self):
        """[HARD] 새 파일이 유예에 들어오면 빨개진다.

        이것이 이 검사의 본체다. 쌍 수만 세면 한 파일에서 규칙을 빼고 다른 파일을
        통째로 넣는 교환이 통과한다 — 파일 집합을 따로 못박는 이유다.
        """
        assert set(self._per_file_ignores()) == set(self._DEFERRED_FILES)

    def test_the_pair_count_did_not_grow(self):
        pairs = sum(len(codes) for codes in self._per_file_ignores().values())
        assert pairs <= self._PAIR_CEILING, (
            f"유예 쌍이 {pairs}개로 늘었다(상한 {self._PAIR_CEILING}). "
            "유예는 줄어들기만 해야 한다 — 늘려야 한다면 그건 별도 판단이다"
        )

    def test_no_directory_glob_is_used(self):
        """[HARD] 글롭이면 이 폴더의 **새 파일이 첫날부터 유예**가 된다.

        그것이 t115 가 고치고 있는 결함(조용한 무검사)의 재생산이다. 파일 단위면
        새 파일은 처음부터 전량 린트를 받는다.
        """
        globbed = [key for key in self._per_file_ignores() if "*" in key or "?" in key]
        assert globbed == [], f"디렉터리 글롭이 섞였다: {globbed}"

    def test_the_format_exclusion_matches_the_same_files(self):
        """린트 유예와 포맷 유예가 갈리면 한쪽만 줄어도 아무도 모른다.

        포맷 쪽은 저장소가 이미 쓰던 기제(`[tool.ruff.format].exclude` +
        `force-exclude`)를 그대로 늘렸다 — 두 번째 기제를 만들지 않는다.
        """
        excluded = set(self._config()["tool"]["ruff"]["format"]["exclude"])
        pinned = {"server/web/preview.py"}  # PRESERVE 핀 — t115 와 무관, 그대로 둔다
        assert excluded - pinned == set(self._DEFERRED_FILES)
