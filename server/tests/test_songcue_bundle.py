"""SONGCUE 번들 게이트 — 그리고 그 PRESERVE 검사가 실제로 재는 것.

이 파일에는 원래 모듈 독스트링이 없었다. t348(2026-09-11)이 하나 만든 이유는
여기서 한 번 잘못 읽힌 것을 다음 카드가 처음부터 다시 발견하지 않게 하려는 것뿐이다.

**과대평가 1건 — 「REQ 를 좁혀야 한다」는 오독.** t348 은 이 파일의
``test_preserve_look_files_are_unchanged_from_run_phase_base`` 가 빨개진 것을 보고
「``REQ-SONGCUE-021`` 을 좁혀야 하는 별도 거버넌스 사안」으로 보고했다. 그것은 과대평가였다.
그 REQ 의 주어는 **「본 SPEC」**이다 — 「**본 SPEC이** 그 계층을 재사용하되 고치지 않는다는
형상의 기계적 증거」(``SPEC-COPILOT-SONGCUE-001/spec.md:182-185``). 그것은 **역사적 사실**
이고 t348 이후에도 글자 그대로 참이다: SONGCUE 는 ``server/looks/instantiate.py`` 를
건드리지 않았다.

미래의 누구도 못 건드린다는 **집행되는 경계**를 만든 것은 REQ 가 아니라 이 검사의 diff
**범위**(``_RUN_PHASE_BASE..HEAD``)다 — 그 범위는 이후의 모든 변경을 함께 잰다. 형제 게이트
(``server/tests/test_overlap_preserve.py``) 독스트링이 정확히 이 혼동을 소유하며 이 파일을
형제로 지목한다: 「그 SPEC 은 이 파일들을 안 건드렸다」와 「아무도 이 파일들을 못 건드린다」는
다른 문장이고, 게이트 자신은 ``git diff`` 가 비었는지만 보므로 그 둘을 **구별할 수 없다**.

🔴 **``REQ-SONGCUE-021`` 은 개정되지 않았고 개정할 필요도 없었다 — 지금 문면 그대로 옳다.**
고친 것은 이 검사가 자기 REQ 가 말하는 것을 재도록 만든 것뿐이다: t348 의 변경을
:data:`_T348_ACCOUNTED_DIGEST` 로 **계상**하고, 나머지 다섯 파일과 이 파일의 **추가**
변경에 대해서는 게이트를 그대로 살려 두었다. 목록에서 파일을 빼지 않았다 — 빼면 REQ 의
기계적 증거가 아예 검사되지 않는다.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest

from server.looks.busking import VALUE_LINE_COLLISION
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    EMPTY_SECTIONS,
    ROLE_UNMAPPED,
    SEQUENCE_TRUNCATED,
    SEQUENCE_UNAVAILABLE,
    SongCueBundleError,
    SongCueLookSelection,
    build_songcue_bundle,
    observed_user_cue_count,
    parse_sections,
    render_songcue_report,
    select_sequence_number,
)
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import ToolCall as RegistryToolCall
from server.orchestrator.tools import build_toolset
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import _code_string_constants

_SONGCUE_MODULE = Path("server/looks/songcue.py")
_STORE_RE = re.compile(r"^Store Sequence (?P<sequence>\d+) Cue (?P<cue>\d+) '(?P<name>[^']+)'$")
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_FORBIDDEN_COMMANDS = {
    "overwrite": re.compile(r"/overwrite\b", re.IGNORECASE),
    "remove": re.compile(r"/remove\b", re.IGNORECASE),
    "delete": re.compile(r"\bdelete\b", re.IGNORECASE),
    "trig": re.compile(r"/trig\s*=", re.IGNORECASE),
    "label_cue": re.compile(r"^\s*label\s+cue\b", re.IGNORECASE),
    "goto_cue": re.compile(r"^\s*goto\s+cue\b", re.IGNORECASE),
}
_RUN_PHASE_BASE = "38a6e7e2157a4862721fcd868056e0dbbb09c4c0"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_phase_base_is_reachable() -> bool:
    """이 base 커밋이 이 클론에 있는가.

    스쿼시 머지로 원본 브랜치가 지워져 어느 **브랜치** ref 에서도 도달할 수 없다
    (git for-each-ref --contains 가 태그 하나만 낸다). 지금 이 커밋을 붙잡고 있는
    것은 주석태그 preserve-base-songcue-m0 하나뿐이고, 그 태그는 origin 에 있다.

    CI 의 checkout 은 fetch-depth: 0 일 때만 태그 refspec(+refs/tags/*:refs/tags/*)을
    발행한다(t64 실측). 얕은 클론으로 되돌리면 태그가 안 오고, 이 함수가 False 를 낸다.
    """
    return (
        subprocess.run(
            ["git", "cat-file", "-e", _RUN_PHASE_BASE],
            cwd=_REPO_ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _require_run_phase_base() -> None:
    """기준 커밋이 없으면 **실패한다** — skip 이 아니다.

    한때 이 자리는 skipif 였다. 그 결과 아래 두 검사는 CI 에서 **매 실행 조용히**
    건너뛰어졌고, PRESERVE 불변식을 아무도 안 보는 상태가 오래 갔다(t59 에서 발견).
    침묵은 초록으로 읽힌다 — 그래서 원인과 처방을 말하는 실패로 바꾼다.

    이 실패는 되돌릴 이유가 아니라 신호다. 특히 CI 가 이걸 내면 워크플로의
    fetch-depth 가 얕아졌다는 뜻이고, 그때 같이 죽는 것은 이 두 검사만이 아니다 —
    PRESERVE 의 git diff <고정 SHA>..HEAD 범위도 함께 죽는다.
    """
    if _run_phase_base_is_reachable():
        return
    raise AssertionError(
        "run-phase base 커밋 " + _RUN_PHASE_BASE + " 가 이 클론에 없다 — "
        "PRESERVE 불변식을 검사할 수 없다.\n"
        "이 커밋은 어느 브랜치에서도 도달 불가이고, 주석태그 "
        "preserve-base-songcue-m0 하나가 붙잡고 있다.\n"
        "처방(로컬): git fetch origin "
        "refs/tags/preserve-base-songcue-m0:refs/tags/preserve-base-songcue-m0\n"
        "처방(CI): .github/workflows/test.yml 의 checkout 이 아직 fetch-depth: 0 인지 "
        "확인해라 — 그 설정이 태그 refspec 을 딸고 온다. 얕은 클론이면 태그가 안 온다."
    )


# SONGCUE 가 §C 에서 선언한 무변경 대상 여섯. **범위 선언이지 이 게이트가 만든
# 경계가 아니다** (t162) — 출처는
# `.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:182` (REQ-SONGCUE-021) 이고
# 목록 본문은 같은 문서 `:238` (§C PRESERVE — 무변경 대상) 이다.
#
# 이 목록을 읽는 법 — 「SONGCUE 가 안 건드렸다」(역사적 사실)와 「아무도 못
# 건드린다」(집행되는 경계)의 구별, 그리고 다른 카드가 이 파일을 고쳐야 할 때
# 선언 층으로 가는 이유 — 은 `server/tests/test_overlap_preserve.py` 의
# `_PRESERVE_PATHS` 주석에 **한 번만** 적혀 있다. 여기에 복사하지 마라:
# 술어가 두 곳으로 갈리면 한쪽만 고쳐지고 나머지가 조용히 낡는다.
#
# 이 목록에 `console/lua/**` 가 없는 것은 누락이 아니다 — v0.2.0 이 예외를 단
# 것이 아니라 §C 목록에서 **뺐다**(`spec.md:245-250` · `progress.md` §F 개정 절).
_PRESERVE_LOOK_FILES = (
    "server/looks/matching.py",
    "server/looks/instantiate.py",
    "server/looks/resolver.py",
    "server/looks/schema.py",
    "server/looks/loader.py",
    "server/looks/roles.py",
)

#: 2026-09-11 — 카드 t348 이 `server/looks/instantiate.py` 를 고쳤고, 그 변경은
#: **계상되었다**(accounted for). 목록에서 파일을 빼지 않았다: 빼면 이 파일에 대한
#: 게이트가 통째로 은퇴하고 `REQ-SONGCUE-021` 의 기계적 증거가 아예 검사되지 않는다.
#: 대신 이 파일만 스윕에서 빼고 **아래 다이제스트로 정확히 고정**한다 — 다른 다섯
#: 파일은 여전히 빈 출력이어야 하고, 이 파일의 **추가 변경**도 여전히 거부된다.
#:
#: 왜 REQ 를 고치지 않았는가 (읽고 지나갈 자리가 아니다):
#: `REQ-SONGCUE-021` 의 주어는 **「본 SPEC」**이다 —
#: 「**본 SPEC이** 그 계층을 재사용하되 고치지 않는다는 형상의 기계적 증거」
#: (`SPEC-COPILOT-SONGCUE-001/spec.md:182-185`). 그것은 **역사적 사실**이고 t348
#: 이후에도 글자 그대로 참이다: SONGCUE 는 이 파일을 건드리지 않았다. 미래의 누구도
#: 못 건드린다는 **집행되는 경계**를 만든 것은 REQ 가 아니라 이 검사의 diff **범위**
#: (`_RUN_PHASE_BASE..HEAD`)다 — 그 범위는 이후의 모든 변경을 함께 잰다. 형제 게이트
#: (`server/tests/test_overlap_preserve.py`) 독스트링이 바로 이 혼동을 소유하고 이
#: 파일을 형제로 지목한다: 「그 SPEC 은 이 파일들을 안 건드렸다」(역사적 사실)와
#: 「아무도 이 파일들을 못 건드린다」(집행되는 경계)는 다른 문장이며, 게이트 자신은
#: `git diff` 가 비었는지만 보므로 그 둘을 **구별할 수 없다**.
#: 🔴 그래서 `REQ-SONGCUE-021` 은 **개정되지 않았고 개정할 필요도 없었다.** 고친 것은
#: 이 검사가 자기 REQ 가 말하는 것을 재도록 만든 것뿐이다. (t348 이 1회차에 이 잠금을
#: 「REQ 를 좁혀야 하는 사안」으로 과대평가했고, 그 과대평가를 여기 적어 다음 카드가
#: 처음부터 다시 발견하지 않게 한다.)
#:
#: 감독 승인(2026-09-11)이 덮는 것은 t348 이 이 파일을 고치는 것이다. 승인·사유·
#: 「범위 선언 ≠ 경계」 구별의 전문은 `SPEC-COPILOT-PRECHK-001/plan.md` §A.5 개정 절과
#: 같은 SPEC `progress.md` §F.2 에 있다.
_T348_ACCOUNTED_FILE = "server/looks/instantiate.py"
#: 계상된 변경이 지운 네 줄 — 무엇이 계상됐는지 사람이 읽는 자리(형제 게이트의
#: `_PRECHK_GRANTED_DELETED_ROW_KEYS` 와 같은 역할). 넷 다 치환이고, 나머지는 순수 추가다.
_T348_ACCOUNTED_DELETED_LINES = (
    "    look: Look, label: str, pools: PoolIndex",
    '    """Decide, per family the look has values in, whether a store can happen."""',
    '    """Build the bundle and report for one look against one resolved rig."""',
    "    planned, skipped = _plan_stores(look, label, pools)",
)
#: sha256 of the diff BODY lines (`+`/`-`, headers dropped) joined by "\n", in diff
#: order, from ``git diff --unified=0``. 본문만 담으므로 줄번호가 밀려도 안 깨지고,
#: **한 바이트라도 다르면** 깨진다. 계상되지 않은 두 번째 변경은 여기서 거부된다.
_T348_ACCOUNTED_DIGEST = "c69d8f321d7fdf7bee32bb78b91a2f022d2954f46cccfe055b8df6cd62a7d039"
#: 계상된 변경의 형상 — 14 hunk, 추가 79, 삭제 4. 다이제스트가 이미 내용을 고정하므로
#: 이 숫자는 사람이 규모를 읽는 자리다.
_T348_ACCOUNTED_SHAPE = (14, 79, 4)

#: 2026-09-12 계상 — 카드 t356 이 역할 어휘의 **닫힌 6개**를 열었다(감독 승인).
#: 같은 이유로, 같은 방식으로 계상한다: 목록에서 파일을 빼지 않고(빼면 REQ 의
#: 기계적 증거가 통째로 은퇴한다) 이 두 파일만 스윕에서 빼서 아래 다이제스트로
#: 고정한다. 나머지 넷은 여전히 빈 출력이어야 하고, 이 둘의 **추가** 변경도
#: 여전히 거부된다.
#:
#: 🔴 `REQ-SONGCUE-021` 은 여기서도 개정되지 않았다 — 그 REQ 의 주어는 「본 SPEC」
#: 이고, SONGCUE 가 이 두 파일을 안 건드렸다는 역사적 사실은 t356 이후에도 참이다.
#: 위 t348 절의 「범위 선언 ≠ 집행되는 경계」 구별이 그대로 적용된다.
#:
#: 무엇이 계상됐는가: 위치 역할 6개는 **한 글자도 안 바뀌었고**(룩 자산이 그 이름을
#: 문자열로 든다), 기구 종류 역할 5개가 덧붙었으며, 이름 매칭에 「위치가 종류를
#: 이긴다」 규칙과 쇼 단위 별칭 통로가 생겼다.
_T356_ACCOUNTED_FILES = ("server/looks/roles.py", "server/looks/resolver.py")
#: 지워진 줄 40개를 개행으로 이은 sha256. t348 은 네 줄이라 튜플로 들었지만 40줄은
#: 사람이 읽을 목록이 아니다 — 형제 게이트(`test_overlap_preserve.py`)의
#: `_PRECHK_GRANTED_DELETION_DIGEST` 가 같은 이유로 쓰는 형태를 따른다.
_T356_ACCOUNTED_DELETION_DIGEST = "1cd64d981d67de40305b678465a0312bdf8d5a1ce50b836ccce3874ab0bb2fe7"
#: diff 본문(`+`/`-`, 헤더 제외)을 개행으로 이은 sha256. 한 바이트라도 다르면 깨진다.
_T356_ACCOUNTED_DIGEST = "bef1ef8a2b68ef3c21f74e6f8193426331c3733aab3ce07aa4aa5884d97c51ae"
#: 40 hunk · 추가 277 · 삭제 40. 다이제스트가 내용을 고정하므로 이 숫자는 규모를
#: 사람이 읽는 자리다.
_T356_ACCOUNTED_SHAPE = (40, 277, 40)

#: 스윕에서 빠지는 전체 — 계상된 것들의 합집합. 스윕 명령과 비공허성 검사가
#: 둘 다 이 하나를 읽으므로, 계상을 추가할 때 두 곳이 어긋날 수 없다.
_ACCOUNTED_LOOK_FILES = (_T348_ACCOUNTED_FILE, *_T356_ACCOUNTED_FILES)

_TOOLS_PATH = "server/orchestrator/tools.py"
# Snapshot of every tools.py hunk since SONGCUE's run-phase base. It is a
# TRIPWIRE, not a constant: a later SPEC that legitimately edits tools.py must
# update it deliberately, which is the point — the protected-range assertion
# below is the real invariant and it must keep holding while this list grows.
# PRECHK (SPEC-COPILOT-PRECHK-001, M6) added the three hunks at 463 / 475 / 479
# (the prechk imports, the `property_port` parameter and its docstring) and moved
# the first hunk's old start from 32 to 33 by inserting its import block one line
# lower. None of them touches a protected range.
# Grows by one entry per SPEC that registers a tool. FXLIB M5 added 17 (the fx
# imports) and 436 (the fx argument/rig helpers, inserted above ToolRegistry).
# SCENE (SPEC-COPILOT-SCENE-001, M6) added 15 — the `replace` import the label
# override needs — and widened the existing 17 hunk with the scene imports, the
# two handlers and their tool definitions. Still no protected range touched.
# PRESHOW (SPEC-COPILOT-PRESHOW-001) registered preshow_check the same way:
# one import line, one TOOL_NAMES entry, one handler + ToolDefinition + one
# handlers-dict entry. Its handler insertion sits inside the same large
# build_toolset body the earlier SPECs already touch, so unified=0 splits the
# old single hunk at 951 into five (952 / 971 / 989 / 1007 / 1118) instead of
# adding a wholly new start — none of the five overlaps a protected range.
# T-J (tool-registration branch) registered the four previously-unregistered
# paperwork/layout tools the same way: import lines, four TOOL_NAMES entries,
# four handlers + four ToolDefinitions + four handlers-dict entries — all
# widening hunks the earlier SPECs already opened, except ONE genuinely new
# start at 27 (ruff's isort placing the `server.looks.layout` import between
# the existing `server.looks.instantiate` and `server.looks.schema` imports).
# None of it touches a protected range.
# SPATIAL (SPEC-COPILOT-SPATIAL-001) registered get_spatial_context and
# arrange_fixtures: three genuinely new starts — 12 and 14 (ruff's isort placing
# `import math` and the `server.spatial` import block among the existing
# imports) and 425 (the spatial read/write module-level helpers, inserted above
# ToolRegistry beside the fx ones at 436) — plus widening of hunks the earlier
# SPECs already opened. 15 and 1118 disappear from the list because unified=0
# merged them into neighbouring widened hunks, not because anything there was
# reverted.
# None of it touches a protected range (verified: zero overlap).
# The positional list is bookkeeping; the assertion that carries the PRESERVE
# claim is the protected-range overlap check below.
# SPEC-COPILOT-GROUPGEN-001 M3/M4 — granted exception, re-walked per the SPATIAL
# §E.2.19 precedent that this snapshot exists to force. Two tools were appended
# (`classify_arrangement_topology`, `create_arrangement_groups`; TOOL_NAMES 20 ->
# 22), which opens the 1067..1220 block plus 477.
# Evidence this is additive-only, not a rewrite of anyone else's code:
#   git diff --stat 5ce471f~1..HEAD -- server/orchestrator/tools.py  ->  +538 -0
#   git diff --unified=0 ... | grep -cE '^-[^-]'                     ->  0
# i.e. ZERO pre-existing lines were deleted or modified; every new start below is
# a pure-insertion hunk. 1222 leaves the list because unified=0 merged it into the
# widened 1220 hunk, not because anything there was reverted.
# Protected-range overlap re-verified: ZERO (the assertion below is what actually
# carries the PRESERVE claim; this positional list is bookkeeping).
# SPEC-COPILOT-TRUNCATE-001 (2026-08-05, user-approved) — granted exception,
# re-walked per the same SPATIAL §E.2.19 precedent. The partial-read reply shape
# diverges (`fixtures`/`analysis` withheld, `partial_fixtures`/`missing`/
# `analysis_withheld` in their place), the one in-process consumer
# (`classify_arrangement_topology`) is migrated to the new keys, and
# `create_arrangement_groups` gains the `acknowledged_unread_fids` refusal. That
# opens the 952..1007 block and widens much of 1070..1231.
#
# THIS GRANT IS NOT ADDITIVE-ONLY, and that is the difference from the two above:
#   git diff --unified=0 38a6e7e2..HEAD -- server/orchestrator/tools.py
#     | grep -cE '^-[^-]'                                          ->  203
# So the "ZERO pre-existing lines modified" evidence the GROUPGEN note leans on
# is NOT available here and must not be implied. What IS verified is the thing
# this test actually protects, and it was checked by CONTENT rather than by
# position: both protected ranges are present VERBATIM in HEAD --
#   old 234..238  `_PROGRAMMER_STATE_COMMANDS`  (the "state" half of the name)
#   old 524..569  the in-bundle dedupe loop     (the "dedupe" half)
# Protected-range overlap re-verified mechanically: ZERO across all 43 hunks.
# A positional list that shifts while those two blocks stay byte-identical is
# bookkeeping catching up, not a boundary being crossed — but a future re-walk
# MUST re-check the content, because with 203 modified lines the position check
# alone no longer implies it.
# 2026-08-07 granted exception — the timecode SLOT OCCUPANCY check. Re-walked by
# the same procedure as the three grants above, and it adds TWO hunks:
#   old 104   `SongCueTimingAxes` added to the songcue import block
#   old 1231  `_timecode_slot_verdict` + the `axes=` argument at its call site
#
# WHY IT IS IN SCOPE OF THIS TEST'S NAME. `prepare_songcue` emitted
# `Store Timecode <n>` with a MODEL-SUPPLIED number and no occupancy read, so a
# showfile already using that slot lost its timecode track silently — with no
# approval card and no way back (`backup.py` retains snapshots but there is no
# restore SEND path). Both hunks are songcue REGISTRATION plumbing, which is the
# half of this test's name that is allowed to move; neither is dedupe or state.
#
# ADDITIVITY, measured rather than claimed:
#   git diff --unified=0 8eb5d56..HEAD -- server/orchestrator/tools.py
#     | grep -cE '^-[^-]'                                          ->  1
# The one modified line is the `build_songcue_timing(...)` call itself, gaining
# `axes=`. So this grant is NOT additive-only either, and per the TRUNCATE note
# above the position check alone therefore does not carry the claim. Re-checked
# by CONTENT, mechanically, both blocks byte-identical in HEAD:
#   old 234..238  `_PROGRAMMER_STATE_COMMANDS`  -> present verbatim
#   old 524..569  the in-bundle dedupe loop     -> present verbatim
# Neither new hunk start falls inside either protected range (104, 1231 vs
# 234..238 / 524..569): overlap ZERO.
#
# ⚠️ HOW THIS GATE WAS TRIPPED, recorded because it will happen again: it diffs
# `BASE..HEAD`, so it is BLIND to an uncommitted working tree. A full green
# suite run before `git commit` does not exercise it, and the failure surfaces
# only after the commit — which is how it reached `main` in PR #33. Run the
# suite ONCE MORE after committing, before merging.
# 2026-08-14 re-walk — two catch-ups in one, per the same procedure as the
# grants above:
# ① f4fb366 (P0 페이퍼워크 — build_handover_pack/paperwork registration) added
#   its own three hunks at 1048 / 1061 / 1067 (the paperwork ToolDefinitions
#   region) but updated this pin BLIND, before committing — exactly the ⚠️
#   failure mode recorded just above, tripped a second time.
# ② 2e20dda (도구환각 교정 — rewritten ToolDefinition descriptions/schemas)
#   adds 1035 / 1110 / 1116 / 1210 (find_looks gains `genre` +
#   `sequence_numbers`, patch_fixtures gains `fixture_type_records`, and the
#   surrounding description text is rewritten), moves the 1089 hunk's boundary
#   to 1088, and 1218 leaves the list because unified=0 merged it into the
#   widened 1220 hunk — not because anything there was reverted.
# ADDITIVITY, measured rather than claimed:
#   git diff --unified=0 38a6e7e2..HEAD -- server/orchestrator/tools.py
#     | grep -cE '^-[^-]'                                          ->  215
# (203 at the TRUNCATE grant), so NOT additive-only; per the TRUNCATE note the
# position check alone does not carry the claim. Re-checked by CONTENT,
# mechanically, both blocks byte-identical in HEAD:
#   old 234..238  `_PROGRAMMER_STATE_COMMANDS`  -> present verbatim
#   old 524..569  the in-bundle dedupe loop     -> present verbatim
# Neither new start falls inside either protected range: overlap ZERO across
# all 54 hunks. Every moved hunk is registration/definition plumbing — the
# half of this test's name that is allowed to move; none is dedupe or state.
# 2026-08-15 catch-up — SPEC-COPILOT-IMGLAYOUT-001 (analyse_layout_image
# registration/definition plumbing): 17→18, 971 merged away, 1013/1029 added.
# Protected ranges re-checked by the overlap assert below: zero overlap.
# 2026-08-16 catch-up — spatial rotation opt-in (include_rotation read
# plumbing in get_spatial_context): 54→56 hunks; all in the SPATIAL read
# helper/registration region, none touching dedupe or programmer state.
# 2026-08-16 re-walk — get_spatial_context DESCRIPTION gains a rotation
# paragraph (pure insertion inside the already-widened SPATIAL definition
# hunk): re-measured 56 hunks, starts identical, pin unchanged, overlap ZERO.
# 2026-08-16 re-walk 2 — query_state gains a paging pass-through (offset arg
# validation in the handler at old 591/593 and the optional 'offset' schema
# property, a widening of the definition hunk): 56→58 hunks, new starts 591
# and 593 are the query_state handler region, far from both protected ranges
# (234..238 / 524..569) — overlap ZERO.
# 2026-08-16 re-walk 3 — drill_into gains contents_total (the responder's own
# node.childCount claim, for the dash pool badge; commit 8800168): 58→60
# hunks, new starts 345 (docstring paragraph) and 367 (childCount extraction)
# are pure insertions inside drill_into, far from both protected ranges
# (234..238 / 524..569) — overlap ZERO.
# 2026-08-17 re-walk 4 — rig_object gains int coercion for the responder's
# 'i' slot (SEC-TRUST-001 review fix): 60→64 hunks, new starts 302 (docstring
# paragraph insertion) and 304/306/308 (single-line rewrites inside
# rig_object's body), all far from both protected ranges (234..238 / 524..569)
# — overlap ZERO.
# 2026-08-20 re-walk 5 — SPEC-COPILOT-SPATIALMEM-001 (커밋 ff664a3, PR #66)이
# tools.py에 좌표 기억/재검증을 넣으면서 이 트립와이어를 갱신하지 않았다.
# 실측 델타: 66→65 hunks. 새 시작점 993(build_toolset 안 기억 주입),
# 사라진 시작점 1088·1111 — 삽입이 두 이웃 헝크를 하나로 합쳐 unified=0
# 경계가 이동한 결과이며 삭제가 아니다. 두 보호 구간(234..238 / 524..569)
# 침범은 ZERO — 실제 불변식은 그대로 성립한다.
# LXSEQ (SPEC-COPILOT-LXSEQ-001, M3)가 import_lxseq_patch를 같은 방식으로 등재했다:
# 임포트 2줄 · TOOL_NAMES 1줄 · _LXSEQ_GUIDANCE 상수 · 핸들러 · ToolDefinition ·
# handlers 1줄. 실측 델타: 65→65 hunks(수는 같다). 새 시작점 971·1088·1181,
# 사라진 시작점 1029·1129·1179 — 삽입이 이웃 헝크 경계를 unified=0에서 옮긴 결과이며
# 삭제가 아니다(BASE..HEAD의 tools.py 삭제 줄은 0). 두 보호 구간(234..238 / 524..569)
# 침범은 ZERO — 실제 불변식은 그대로 성립한다.
# t134 (SPEC-COPILOT-LXSEQ-003, col 척도)가 import_lxseq_presets 의 col 분기를
# 배선했다: 임포트 2곳 · _PRESET_POOL_FAMILY 주석 정정 · _lxseq_preset_apply_command
# 의 col 분기. 실측 델타: 72->73 hunks, 새 시작점 **956** 하나, 사라진 시작점 없음.
# 커밋 단위 numstat 은 +19/-6 이고, 삭제 6줄은 전부 그 함수와 주석의 제자리 교체다.
# 두 보호 구간(234..238 / 524..569) 침범은 ZERO — 실제 불변식은 그대로 성립한다.
# t151 (SPEC-COPILOT-LXSEQ-003, rig 섹션 페이징)이 collect_rig_sections 의 섹션 루프를
# 공용 페이징(server/rig/paging.py paged_children)으로 바꿨다: children/objects/entry
# 3줄의 제자리 교체 + 근거 주석. 실측 델타: 73->74 hunks, 새 시작점 **410** 하나,
# 사라진 시작점 없음(순수 삽입). 두 보호 구간(234..238 / 524..569) 침범은 ZERO —
# 234..238 앞뒤로 가장 가까운 헝크가 184 와 302 이고, 524..569 앞뒤가 479 와 591 이다.
# 이 트립와이어는 커밋된 HEAD 를 보므로 커밋 **전에** 돌린 스위트로는 안 잡힌다 —
# t151 은 로컬 전량 초록 뒤 CI 에서 처음 빨갰다. 다음 사람은 커밋 후 한 번 더 돌려라.
# t194 (슬롯 판독 귀속)이 _SlotReadPort 어댑터를 모듈 수준에 넣고 read_existing_fids
# 호출 3자리를 감쌌다. 실측 델타: 74->47 hunks. 사라진 시작점 28개(477 과 956..1124
# 구간의 27개), 새 시작점 **1140** 하나.
# 커밋 단위 numstat 은 +49/-3 이고, 삭제 3줄은 전부 그 호출 3자리의 제자리 교체다
# (실측: git diff origin/main..HEAD 의 - 줄이 그 셋뿐이다). 즉 삭제가 아니라 삽입이
# unified=0 경계를 재정렬한 결과이며, 위 re-walk 5 가 명명한 것과 같은 기제다.
# 두 보호 구간(234..238 / 524..569) 침범은 ZERO — 사라진 477 은 524 아래이고 나머지
# 956 이상은 569 위다. main 을 대조군으로 함께 쟀고 그쪽도 ZERO 다
# (.moai/reports/t194/probes/_t194_preserve.py · preserve-out.txt).
# 🔴 위 t151 의 경고("커밋 후 한 번 더 돌려라")를 t194 도 그대로 밟았다 — 커밋 전
# 전량 10571 초록, 커밋 후 CI 에서 처음 빨갛다. 경고가 문면에 있는데도 두 번째다.
# t209 (SPEC-COPILOT-LXSEQ-004 M3) registered import_lxseq_cues + wired
# preset_slots (ID(sheet) -> Name(sheet) -> slot(console) join, DIM/COL/BM).
# Measured delta: 47->48 hunks, one new start point **1190**, no start point
# disappeared (pure insertion between existing 1183 and 1192).
# Both protected ranges (234..238 / 524..569) untouched -- nearest hunks
# around 234..238 are 184 and 302 (unchanged); around 524..569 are 479 and
# 591 (unchanged).
# t209 (Store Cue command generation) added a single-quote-vs-double-quote
# fix (protocol.py rejects a literal double quote -- MA3 grammar needs the
# transport form single-quoted, ma3.txt's own double quotes are for a
# human pasting into the console, not this wire path -- reproduced live by
# the lead session on the real console before this fix) plus a fail-closed
# guard refusing a single quote inside --sequence-name (would prematurely
# close the single-quoted MA3 string). Measured delta: 48->47 hunks, start
# point **1190** disappeared (the new guard sits right after the
# sequence_name validation at old-line ~1183 and merged with what used to
# be a separate hunk at 1190 into one contiguous hunk), no new start point.
# Both protected ranges (234..238 / 524..569) untouched -- nearest hunks
# around 234..238 are 184 and 302 (unchanged); around 524..569 are 479 and
# 591 (unchanged).
# t220 (POS.xx 산출 + 큐 조인) 은 tools.py 를 세 자리 고쳤다: (1) POS 계열 이름
# 상수 POSITION_POOL_FAMILY 를 _PRESET_POOL_FAMILY 옆에 신설, (2) preset_slots
# 뒤에 Position 풀 되읽기 블록 추가, (3) 명령 조립 루프의 (row.col, row.bm) 에
# row.pos 를 넣었다. Measured delta: 47->48 hunks, 새 시작점 **477**
# (순수 삽입, count 0), 사라진 시작점 없음. 보호 구간 둘(234..238 / 524..569)
# 모두 무접촉 -- 524..569 주변 이웃은 479 와 591 로 그대로이고, 새 477 은
# count 0 이라 524 에 닿지 않는다.
#: 🔴 이 튜플은 **불변식이 아니라 재고 목록**이다. 실질 불변식은 아래
#: `_TOOLS_PROTECTED_OLD_RANGES` 와 겹치지 않는 것이고, 이 목록은 그 시점의
#: hunk 스냅샷일 뿐이라 `tools.py` 를 건드리는 **모든** 브랜치가 갱신해야 한다.
#: `--unified=0` 은 삽입이 기존 hunk 를 쪼개므로 한 줄만 더해도 시작점이 여럿
#: 바뀐다 — 48 -> 65 가 그 형태다(t229 는 tools.py 에 25+/4- 만 더했다).
#:
#: t229 갱신: 보호 구간 겹침이 **0** 임을 이 파일의 `_overlaps` 로 다시 재고
#: 목록만 옮겼다. 겹침이 있었으면 목록을 고치는 것이 아니라 변경을 물렀어야 한다.
#:
#: t270 (SPEC-COPILOT-POOLEMPTY-001 M2, 2026-09-06) 갱신: 툴셋 빌더 안의 중첩
#: 함수 `_timecode_slot_verdict` 를 모듈 수준 `timecode_slot_verdict` 로
#: 들어올려 `def build_toolset` 바로 앞에 두고(REQ-016), 유일 호출자의 이름을
#: 바꾸고, `childCount == 0` 갈래 하나에 응답기 1.6.5 의 `node.enumeration`
#: 조건을 더했다. 실측 델타: 65 -> 68 hunks — 기존 1007 hunk 가 64 -> 48 행으로
#: 줄고 그 옛 범위 안에서 새 시작점 **1061**(count 5) · **1067** · **1070** 이
#: 갈라져 나왔다(옮긴 본문이 base 의 일부 행과 다시 일치해 큰 교체 hunk 하나가
#: 넷으로 쪼개진 형태). 사라진 시작점 없음. 보호 구간 둘(234..238 / 524..569)
#: 모두 무접촉 — 이웃은 184 / 302 와 483(+7 = 489) / 591 로 그대로이고, 겹침은
#: 아래 검사의 `_overlaps` 로 다시 재어 **0** 이다.
#:
#: t273 (SPEC-COPILOT-SONGCONFIRM-001 M2, 2026-09-06) 갱신 — #320(t270) 과 #321(t273) 이
#: 서로 다른 base 에서 tools.py 를 고친 뒤 main 에서 만난 형태. #321 은 build_toolset 에
#: song_analysis 키워드·SongAnalysisPort Protocol·prepare_songcue 기본값 분기를 더했다
#: (97+/2-). 병합 트리 실측 델타: 68 -> 65 hunks — 새 시작점 **475**(count 1) ·
#: **479**(count 0), 사라진 시작점 473 · 481 · 483 · 1061 · 1067(이웃 hunk 가 합쳐지거나
#: 자리를 옮긴 것, 삭제 아님). 보호 구간 둘(234..238 / 524..569) 무접촉 — 이웃은
#: 184 / 302 와 479(count 0) / 591 이고, 겹침은 `_overlaps` 로 다시 재어 **0**. #321 의
#: 자체 게이트는 이 파일을 안 돌려 병합 뒤 CI 에서 잡혔다(리드 실수 — 이 목록을
#: 건드리는 브랜치는 병합 트리에서 이 검사를 먼저 돌려야 한다).
#:
#: t274 (prepare_songcue.section_names, 2026-09-06) 갱신 — 확정 기본값 경로에
#: 운영자 이름을 붙이는 선택 인자를 더했다. 건드린 자리는 `_confirmed_section_input`
#: (시그니처에 `name` 추가) · 그 아래 새 헬퍼 둘 · prepare_songcue 핸들러의 검증
#: 분기 · 결과 페이로드 한 줄 · 도구 스키마 한 블록. 실측 델타: 65 -> **65** hunks
#: (개수 불변). 옮긴 시작점 **하나뿐** — 467 -> **463**. 시그니처 행이 base 좌표에서
#: 종전 hunk 시작보다 네 줄 위라 hunk 가 그만큼 위로 자란 것이고, 사라진 시작점도
#: 새로 생긴 시작점도 없다. 보호 구간 둘(234..238 / 524..569) 무접촉 — 이웃은
#: 184(count 0) / 302(count 0) 과 479(count 0) / 591(count 0) 로 그대로이고,
#: 겹침은 아래 검사의 `_overlaps` 로 다시 재어 **0** 이다.
#:
#: t306 (업로드 경로 큐 밀도, 2026-09-06) 갱신 — `prepare_songcue` 의 업로드/확정
#: 경로에 마디 경계 분할을 배선했다. 건드린 자리는 다섯: songcue 임포트에
#: `split_selections_for_density` 한 줄 · `ConfirmedSectionPort` 에 `end_ms` 필드와
#: docstring · 새 `ConfirmedBpmPort` Protocol · `ConfirmedSongAnalysisPort` 에 `bpm`
#: 필드 · 새 헬퍼 둘(`_confirmed_density_bpm` · `_confirmed_song_end_ms`) ·
#: build_toolset 안 분할 호출 블록. 커밋 단위 numstat 은 +88/-2 이고, 삭제 2줄은
#: 두 Protocol docstring 의 제자리 교체다.
#:
#: 실측 델타: 65 -> **78** hunks. 새 시작점 20개(426 · 434 · 459 · 467 · 473 · 481 ·
#: 483 · 975 · 977 · 984 · 986 · 993 · 995 · 1004 · 1011 · 1013 · 1035 · 1048 ·
#: 1061 · 1067), 사라진 시작점 7개(425 · 453 · 463 · 475 · 479 · 1129 · 1140).
#: 사라진 것은 삭제가 아니라 삽입이 `--unified=0` 경계를 재정렬한 결과이며,
#: 위 re-walk 5 가 명명한 것과 같은 기제다.
#:
#: 이 델타 전부가 t306 것임을 대조군으로 확인했다 — `origin/main` 을 같은 base 로
#: 재니 hunk 65개에 시작점이 아래 옛 튜플과 **바이트 동일**했다(즉 병합이 끌고 온
#: main 쪽 표류는 0). 이 브랜치에서 tools.py 를 건드린 커밋도 t306 하나뿐이다
#: (`git log origin/main..HEAD -- server/orchestrator/tools.py` → 2aee812 단독).
#: 보호 구간 둘(234..238 / 524..569) 무접촉 — 234..238 이웃은 184 / 302 로 그대로,
#: 524..569 이웃은 483(count 39 → 483..521, 524 에 못 닿는다) / 591 이고, 겹침은
#: 아래 검사의 `_overlaps` 로 다시 재어 **0** 이다.
_TOOLS_EXPECTED_HUNK_OLD_STARTS = (
    11,
    12,
    14,
    18,
    27,
    # t350 이 더한 시작점 — 임포트 블록 두 줄(`RIG_GAP_UNREADABLE` 추가 ·
    # `server.looks.rig_axes`)이 기존 27 헝크를 쪼갰다.
    31,
    33,
    49,
    104,
    125,
    160,
    162,
    171,
    184,
    302,
    304,
    306,
    308,
    345,
    367,
    410,
    426,
    434,
    437,
    440,
    444,
    447,
    455,
    459,
    467,
    473,
    477,
    481,
    483,
    591,
    593,
    620,
    # 카드 t319 (2026-09-07): 새 시작점 넷. `instantiate_look`·`prepare_busking`·
    # `precheck_patch`·`_deliver_fx_plan`·`compile_scene`·`arrange_fixtures` 여섯
    # 자리가 번들 위험 선언(`risk=showfile_write_risk(...)`)을 달면서 이 근처에
    # 헝크가 넷 늘었다. 여섯인데 넷인 것은 둘이 기존 헝크에 흡수됐기 때문이다.
    #
    # 이 목록은 **재고 조사**이지 안전 성질이 아니다. 안전 성질을 지키는 것은
    # 아래 `_overlaps` 검사이고, 보호 구간 둘(234..238 / 524..569)은 여기서
    # 800 넘게 떨어져 있어 무접촉이다 — 그 검사로 다시 재어 0 이다. 목록을
    # 안 늘리면 「봉인하지 말라」는 뜻이 되므로, 사유를 적고 늘린다.
    #
    # t350 (룩 저장 축 판정 배선, 2026-09-11) 이 이 근처에 다섯을 더했다: 704 · 775 ·
    # 781 · 789 · 794 는 `instantiate_look` 앞에 들어간 `_look_axis_source` 클로저와
    # `axes=` 인자, 그리고 payload 두 갈래의 `capability` 절이 기존 헝크를 쪼갠
    # 자리다. 804 는 그 아래 첫 경계다.
    704,
    775,
    781,
    789,
    794,
    797,
    800,
    804,
    923,
    928,
    952,
    # t350 갱신 — 도구 설명(`instantiate_look` 의 `skipped` 사유 목록에 `axis_absent`
    # 를 넣고 `capability` 절을 설명하는 문단)이 기존 헝크를 둘로 쪼갰다.
    965,
    971,
    # SPEC-COPILOT-BULKGATE-001 (2026-09-07): 새 시작점 하나. `run_commands`
    # 클로저가 키워드 전용 `risk` 를 얻으면서 이 근처의 헝크 경계가 하나 더
    # 갈라진다. 보호 구간(`_TOOLS_PROTECTED_OLD_RANGES`)은 안 건드린다 —
    # 그 교차 없음은 같은 검사의 둘째 단언이 따로 잰다.
    #
    # SPEC-COPILOT-WRITEGATE-001 / 카드 t317 (2026-09-07) 갱신: 79 -> 78 hunks.
    # 새 시작점 둘(160 · 162), 사라진 시작점 셋(164 · 968 · 971).
    # `ExecutionContext` 가 `risk` 필드와 그 설명을 얻고 `run_commands` 가
    # 컨텍스트 대체 두 줄을 얻으면서 `--unified=0` 경계가 재정렬됐다 —
    # 삭제가 아니라 삽입이 경계를 다시 그은 것으로, 위 t306 항목이 명명한
    # 것과 같은 기제다. 보호 구간 둘(234..238 / 524..569) 무접촉이고,
    # 겹침은 같은 검사의 `_overlaps` 로 다시 재어 **0** 이다 —
    # 483 헝크는 old-count 41 -> **37** 로 오히려 줄어 483..519 에 그친다.
    #
    # 🔴 이 카드가 재고 목록 밖에서 배운 것 — 이 검사는 `ToolRegistry.dispatch`
    # 의 **시그니처 한 줄**에 특히 민감하다. 그 줄은 base 에도 같은 문자열로
    # 있어서 diff 의 닻 노릇을 하는데, 그 줄을 고치면 483 헝크가 old-side 로
    # 두 줄(524 · 525) 더 자라 보호 구간 524..569 를 **한 줄 차이로** 건드린다.
    # 대조군 셋으로 갈랐다(`.moai/state/verify/t317/control*.py`): EOF 에 무관한
    # 한 줄 → 41 유지 · 같은 자리에 무관한 1~8줄 → 41 유지 · 그 시그니처 줄만
    # 교체(본문 무변경) → 42. 즉 크기도 위치도 아니고 그 한 줄이다. t317 은
    # 그래서 `dispatch` 를 안 건드리고 선언을 `ExecutionContext` 로 흘렸다 —
    # 가드를 고쳐서 통과한 것이 아니라, 가드가 지키는 자리를 실제로 비켜 갔다.
    975,
    977,
    984,
    986,
    989,
    993,
    995,
    1004,
    1007,
    1011,
    1013,
    1035,
    1048,
    1061,
    1067,
    1070,
    1072,
    1081,
    1088,
    1096,
    1103,
    1110,
    1113,
    1116,
    1118,
    1122,
    1124,
    # t350 갱신 — 시작점 **1146 이 1129 로 옮겨졌다**(사라진 하나 · 새로 생긴 하나).
    # 삭제가 아니라 삽입이 경계를 다시 그은 것으로, 위 t306 · t317 항목이 명명한 것과
    # 같은 기제다.
    1129,
    1167,
    1175,
    1177,
    1179,
    1181,
    1183,
    1192,
    1196,
    1198,
    1210,
    1213,
    1220,
    # 카드 t323 (모델 도구 봉합, 2026-09-07) 갱신 — `build_toolset` 의 핸들러
    # 등재부 바로 위에 `dispatch_run_commands` 클로저를 넣고 `write_reason`
    # 임포트를 정렬했다. 실측 델타: 82 -> **84** hunks. 새 시작점 둘(1223 ·
    # 1225), 사라진 시작점 **0**. 보호 구간 둘(234..238 / 524..569) 무접촉 —
    # 겹침은 아래 검사의 `_overlaps` 로 다시 재어 **0** 이다.
    1223,
    1225,
    1231,
    # 카드 t350 (룩 저장 축 판정 배선, 2026-09-11) 갱신: 84 -> **93** hunks.
    # 새 시작점 열(31 · 704 · 775 · 781 · 789 · 794 · 804 · 965 · 971 · 1129),
    # 사라진 시작점 하나(1146 -> 1129 로 이동). 보호 구간 둘(234..238 / 524..569)
    # 무접촉 — 겹침은 아래 검사의 `_overlaps` 로 다시 재어 **0** 이고, 형제 게이트의
    # 보호 구간(247..251 / 537..582)도 같은 식으로 재어 **0** 이다
    # (`.moai/reports/t350/measure_hunks.py`, 출력은 나란한 `.out.txt`).
    #
    # 🔴 **이 검사를 커밋 전에 돌리면 공허하게 통과한다 — t350 이 그 함정을 밟았다.**
    # `_tools_hunks_from_run_phase_base()` 는 `git diff <base>..HEAD` 를 쓰므로
    # **작업 트리를 안 본다.** 커밋 전에는 내 변경이 한 줄도 안 들어간 diff 를 재고,
    # 그래서 초록이다. t350 은 커밋 전에 같은 명령으로 손수 재어 「84 -> 84, 새 시작점
    # 0」을 얻고 그것을 「내 변경이 hunk 를 안 옮겼다」로 읽었다 — 실제로는 「내 변경을
    # 안 봤다」였고, 진짜 델타(84 -> 93)는 커밋 뒤 CI 가 잡았다.
    #
    # 그래서 이 재고를 갱신하려면 **먼저 커밋하고 그 다음에 재라.** 커밋 전 측정은
    # 부재의 증거가 아니다. (같은 이유로 형제 검사
    # `test_the_accounted_change_is_exactly_the_one_t348_introduced` 도 커밋 전에는
    # 공허하다.)
)


_TOOLS_PROTECTED_OLD_RANGES = ((234, 238), (524, 569))
_HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")


def test_sequence_one_and_cues_one_to_n_for_six_and_ten_sections():
    for size in (6, 10):
        bundle = _bundle_for_size(size)
        stores = _store_refs(bundle.commands)

        assert len(stores) == size
        assert {sequence for sequence, _cue, _name in stores} == {bundle.sequence_number}
        assert [cue for _sequence, cue, _name in stores] == list(range(1, size + 1))


def test_naive_per_section_next_cue_defect_is_real_but_bundle_uses_a_ledger():
    bundle = _bundle_for_size(4)
    sections = [plan.section for plan in bundle.sections]

    assert _naive_next_cues(sections) == [1, 1, 1, 1]
    assert [plan.cue_number for plan in bundle.sections] == [1, 2, 3, 4]


def test_sequence_number_comes_from_complement_and_rejects_unknown_snapshots():
    assert select_sequence_number(_sequences(1, 2, 4)) == 3
    assert select_sequence_number(_sequences(1, 2, 3)) == 4
    assert select_sequence_number({"children": [{"i": 1, "name": "Sequence 1"}]}) == 2

    with pytest.raises(Exception) as failed:
        select_sequence_number({"reason": "path_not_resolved"})
    assert failed.value.reason == SEQUENCE_UNAVAILABLE

    with pytest.raises(Exception) as truncated:
        select_sequence_number(_sequences(1, 2, truncated=True))
    assert truncated.value.reason == SEQUENCE_TRUNCATED


def test_implicit_system_cues_are_subtracted_and_truncation_is_rejected():
    payload = {"node": {"childCount": 8}, "truncated": False}

    assert observed_user_cue_count(payload) == 6
    with pytest.raises(Exception) as raised:
        observed_user_cue_count({"node": {"childCount": 24}, "truncated": True})
    assert raised.value.reason == SEQUENCE_TRUNCATED


def test_commands_are_ascii_and_report_keeps_korean_in_presentation_only():
    section = parse_sections((("후렴", "0:00"),))[0]
    look = _look("k", dynamics=4)
    bundle = build_songcue_bundle(
        "사랑 노래",
        (SongCueLookSelection(section=section, requested_dynamics=(4,), look=look),),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert bundle.commands
    assert all(command.isascii() for command in bundle.commands)
    assert _has_hangul(render_songcue_report(bundle))
    assert all(field.name.isascii() for field in fields(Look))


def test_repeated_section_names_are_disambiguated_in_store_names():
    sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:30")))
    looks = (_look("a", dynamics=4, value=40), _look("b", dynamics=5, value=50))
    bundle = build_songcue_bundle(
        "Song",
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in zip(sections, looks, strict=True)
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert [name for _sequence, _cue, name in _store_refs(bundle.commands)] == [
        "Chorus 1",
        "Chorus 2",
    ]


def test_forbidden_command_scanner_is_generated_tuple_based_and_nonempty():
    bundle = _bundle_for_size(3)

    assert bundle.commands
    assert _forbidden_hits(bundle.commands) == []
    assert all("/Merge" not in command for command in bundle.commands)


def test_forbidden_command_scanner_catches_injected_forms_case_insensitively():
    planted = (
        "Store Cue 5 /overwrite",
        "Store Cue 6 /Remove",
        "Delete Sequence 7",
        "Cue 1 /trig=Time",
        "Label Cue 1 'X'",
        "Goto Cue 2 Sequence 5",
    )

    hits = _forbidden_hits(planted)

    assert {name for name, _command in hits} == set(_FORBIDDEN_COMMANDS)


def test_destination_is_once_at_head_and_clearall_cycles_survive():
    bundle = _bundle_for_size(4)

    assert bundle.commands[0] == _DESTINATION
    assert bundle.commands.count(_DESTINATION) == 1
    assert bundle.commands.count(_CLEAR) == 8
    assert bundle.commands[1] == _CLEAR
    assert bundle.commands[-1] == _CLEAR


def test_label_sequence_is_after_first_store_once():
    bundle = _bundle_for_size(2)
    store_indexes = [
        index
        for index, command in enumerate(bundle.commands)
        if command.startswith("Store Sequence ")
    ]
    label = f"Label Sequence {bundle.sequence_number} '{bundle.sequence_name}'"

    assert bundle.commands.count(label) == 1
    assert bundle.commands[store_indexes[0] + 1] == label


def test_bundle_goes_through_run_commands_without_dedupe_loss():
    bundle = _bundle_for_size(5)
    port = _RecordingPort()
    registry = build_toolset(execution_port=port, state_port=_StatePort())
    execution = registry.dispatch(
        RegistryToolCall(
            id="songcue", name="run_commands", arguments={"commands": list(bundle.commands)}
        )
    )
    statuses = [outcome.status for outcome in execution.command_outcomes]

    assert statuses
    assert "skipped_already_executed" not in statuses
    assert set(statuses) == {"executed_ok"}
    assert port.executed == list(bundle.commands)


def test_preserve_gate_uses_run_phase_base_to_head_range():
    command = _preserve_diff_command()

    assert command[:4] == ["git", "diff", "--stat", f"{_RUN_PHASE_BASE}..HEAD"]
    assert command[4] == "--"
    # 계상된 파일들만 빠지고 나머지는 그대로 스윕된다. 목록 자체는 여섯이며,
    # 빠진 것들은 아래 다이제스트 검사가 더 좁게 잰다.
    assert tuple(command[5:]) == _unaccounted_look_files()
    assert len(command[5:]) == len(_PRESERVE_LOOK_FILES) - len(_ACCOUNTED_LOOK_FILES)
    for path in _ACCOUNTED_LOOK_FILES:
        assert path not in command
        # 계상은 목록에서 빼는 것이 아니다 — 빼면 게이트가 통째로 은퇴한다.
        assert path in _PRESERVE_LOOK_FILES


def test_preserve_look_files_are_unchanged_from_run_phase_base():
    _require_run_phase_base()

    result = subprocess.run(  # noqa: S603
        _preserve_diff_command(),
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert _PRESERVE_LOOK_FILES
    assert _unaccounted_look_files()  # 비공허성: 스윕 대상이 비면 영구 통과가 된다
    assert result.stdout == ""


def test_every_unaccounted_look_file_exists_on_disk():
    """비공허성 — 존재하지 않는 경로는 `--stat` 에 한 줄도 안 낸다."""
    missing = [path for path in _unaccounted_look_files() if not (_REPO_ROOT / path).exists()]
    assert missing == []


def test_the_accounted_change_is_exactly_the_one_t348_introduced():
    """계상된 변경을 내용으로 고정한다 — 두 번째 변경은 여기서 거부된다."""
    _require_run_phase_base()

    body = _accounted_diff_body()
    additions = [line for line in body if line[0] == "+"]
    deletions = [line for line in body if line[0] == "-"]
    hunks, expected_adds, expected_dels = _T348_ACCOUNTED_SHAPE

    assert len(additions) == expected_adds
    assert len(deletions) == expected_dels
    assert tuple(line[1:] for line in deletions) == _T348_ACCOUNTED_DELETED_LINES
    digest = hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()
    assert digest == _T348_ACCOUNTED_DIGEST
    # hunk 수는 별도 계기로 센다 — 본문 줄 수와 다른 것을 잰다.
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--unified=0", f"{_RUN_PHASE_BASE}..HEAD", "--", _T348_ACCOUNTED_FILE],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert len([1 for line in result.stdout.splitlines() if line.startswith("@@")]) == hunks


def test_the_t356_accounted_change_is_exactly_the_role_vocabulary_opening():
    """t356 의 계상을 내용으로 고정한다 — 이 두 파일의 두 번째 변경은 여기서 거부된다."""
    _require_run_phase_base()

    body = _accounted_diff_body(*_T356_ACCOUNTED_FILES)
    additions = [line for line in body if line[0] == "+"]
    deletions = [line for line in body if line[0] == "-"]
    hunks, expected_adds, expected_dels = _T356_ACCOUNTED_SHAPE

    assert len(additions) == expected_adds
    assert len(deletions) == expected_dels
    deletion_digest = hashlib.sha256(
        "\n".join(line[1:] for line in deletions).encode("utf-8")
    ).hexdigest()
    assert deletion_digest == _T356_ACCOUNTED_DELETION_DIGEST
    digest = hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()
    assert digest == _T356_ACCOUNTED_DIGEST
    # hunk 수는 별도 계기로 센다 — 본문 줄 수와 다른 것을 잰다.
    result = subprocess.run(  # noqa: S603
        [
            "git",
            "diff",
            "--unified=0",
            f"{_RUN_PHASE_BASE}..HEAD",
            "--",
            *_T356_ACCOUNTED_FILES,
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert len([1 for line in result.stdout.splitlines() if line.startswith("@@")]) == hunks


def test_the_t356_position_role_names_did_not_change():
    """계상의 근거 — 「덧붙이기였다」를 문면이 아니라 diff 로 잰다.

    지워진 40줄 안에 위치 역할 여섯의 이름이 **한 번도** 나오지 않아야 한다.
    나오면 그것은 덧붙이기가 아니라 개명이고, `server/looks/library/*.yaml` 의
    룩들이 그 이름을 문자열로 들고 있으므로 자산이 깨진다.
    """
    _require_run_phase_base()

    deletions = "\n".join(
        line[1:] for line in _accounted_diff_body(*_T356_ACCOUNTED_FILES) if line[0] == "-"
    )
    assert deletions  # 비공허성: 지워진 줄이 없으면 이 검사는 아무것도 안 잰다
    for name in ("백라이트", "프론트", "사이드", "탑", "배경", "스페셜"):
        assert f'name="{name}"' not in deletions, name


def test_the_accounted_digest_would_reject_a_second_unaccounted_hunk():
    """비공허성 — 계상은 이 파일을 열어주지 않는다. 내용 민감이고 개수 민감이 아니다."""
    _require_run_phase_base()

    body = _accounted_diff_body()
    smuggled = [*body, "+    # 계상되지 않은 두 번째 변경"]
    digest = hashlib.sha256("\n".join(smuggled).encode("utf-8")).hexdigest()
    assert digest != _T348_ACCOUNTED_DIGEST
    # 한 바이트만 달라도 깨진다 — 줄을 더하지 않고 한 글자만 바꿔도.
    tampered = [body[0] + "x", *body[1:]]
    assert tampered != body  # 비공허성: 변조가 실제로 일어났다
    assert len(tampered) == len(body)  # 개수는 그대로 — 내용 민감임을 증명한다
    assert hashlib.sha256("\n".join(tampered).encode("utf-8")).hexdigest() != _T348_ACCOUNTED_DIGEST


def test_the_accounted_file_is_still_named_by_the_requirement():
    """`REQ-SONGCUE-021` 은 개정되지 않았다 — 계상은 REQ 를 건드리지 않는다.

    REQ 의 주어가 「본 SPEC」이라는 것이 이 계상의 근거이므로, 그 문면이 사라지면
    근거가 사라진다. 그래서 문면을 여기서 잰다.
    """
    text = (_REPO_ROOT / ".moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md").read_text(encoding="utf-8")
    assert "REQ-SONGCUE-021" in text
    assert "server/looks/instantiate.py" in text
    # 주어가 「본 SPEC」이라는 것 — 이 계상 전체가 여기에 걸려 있다.
    assert "본 SPEC이 그 계층을 **재사용하되 고치지 않는다**" in text


def test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state():
    _require_run_phase_base()

    hunks = _tools_hunks_from_run_phase_base()

    assert hunks
    assert tuple(start for start, _count in hunks) == _TOOLS_EXPECTED_HUNK_OLD_STARTS
    assert [
        (start, count)
        for start, count in hunks
        for protected_start, protected_end in _TOOLS_PROTECTED_OLD_RANGES
        if _overlaps(start, count, protected_start, protected_end)
    ] == []


def test_value_line_collision_skips_later_section_without_pulling_next_cue():
    """마지막 수단으로 남은 건너뜀 — 사다리가 오를 칸이 없을 때만(카드 t355).

    룩이 밝기 **천장**(100)에 있고 빔 축을 안 실었으므로 아껴두기 사다리(정본 §7.1)가
    바꿀 값이 없다. 80 이던 시절 이 검사가 재던 것은 「값이 같으면 버린다」였고, 그것이
    정본 §12 항목 3 이 결함으로 지목한 동작이다. 여기서 재는 것은 그것이 아니라 건너뜀이
    일어날 때 **다음 큐를 끌어당기지 않는다**는 성질 하나다.
    """
    chorus_a, chorus_b, verse = parse_sections(
        (("Chorus", "0:00"), ("Chorus", "0:30"), ("Verse", "1:00"))
    )
    chorus_look = _look("chorus", dynamics=4, value=100)
    verse_look = _look("verse", dynamics=2, value=45)
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(section=chorus_a, requested_dynamics=(4, 5), look=chorus_look),
            SongCueLookSelection(section=chorus_b, requested_dynamics=(4, 5), look=chorus_look),
            SongCueLookSelection(section=verse, requested_dynamics=(2, 3), look=verse_look),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    stores = _store_refs(bundle.commands)
    assert [cue for _sequence, cue, _name in stores] == [1, 3]
    assert [plan.cue_number for plan in bundle.sections] == [1, 2, 3]
    assert len(bundle.skipped) == 1
    assert bundle.skipped[0].reason == VALUE_LINE_COLLISION
    assert bundle.skipped[0].collides_with_section_index == chorus_a.index
    assert bundle.skipped[0].collides_with_cue_number == 1


def test_value_line_collision_bundle_still_executes_without_dedupe_loss():
    chorus_a, chorus_b = parse_sections((("Chorus", "0:00"), ("Chorus", "0:30")))
    look = _look("chorus", dynamics=4, value=80)
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(section=chorus_a, requested_dynamics=(4, 5), look=look),
            SongCueLookSelection(section=chorus_b, requested_dynamics=(4, 5), look=look),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    port = _RecordingPort()
    execution = build_toolset(execution_port=port, state_port=_StatePort()).dispatch(
        RegistryToolCall(
            id="songcue", name="run_commands", arguments={"commands": list(bundle.commands)}
        )
    )

    assert bundle.commands
    assert execution.result.is_error is False
    assert "skipped_already_executed" not in [
        outcome.status for outcome in execution.command_outcomes
    ]
    assert port.executed == list(bundle.commands)


def test_distinct_value_lines_do_not_trigger_collision():
    first, second = parse_sections((("Chorus", "0:00"), ("Verse", "0:30")))
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=first, requested_dynamics=(4,), look=_look("a", dynamics=4, value=80)
            ),
            SongCueLookSelection(
                section=second, requested_dynamics=(2,), look=_look("b", dynamics=2, value=45)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert bundle.skipped == ()
    assert [cue for _sequence, cue, _name in _store_refs(bundle.commands)] == [1, 2]


def test_zero_sections_rejects_one_section_succeeds_and_unmapped_roles_are_answer():
    with pytest.raises(SongCueBundleError) as raised:
        build_songcue_bundle(
            "Song", (), sequences_section=_sequences(), groups_section=_groups(*FULL_RIG)
        )
    assert raised.value.reason == EMPTY_SECTIONS

    section = parse_sections((("Intro", "0:00"),))[0]
    normal = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=section, requested_dynamics=(1,), look=_look("intro", dynamics=1)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    assert [cue for _sequence, cue, _name in _store_refs(normal.commands)] == [1]

    unresolved = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=section, requested_dynamics=(1,), look=_look("intro", dynamics=1)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups((99, "Unmatched")),
    )
    assert unresolved.is_error is False
    assert unresolved.commands == ()
    assert unresolved.skipped[0].reason == ROLE_UNMAPPED


def test_static_scans_find_no_command_number_literals_or_numeric_rig_defaults():
    strings = _code_string_constants(_SONGCUE_MODULE)
    assert strings
    numbered_object = re.compile(
        r"\b(Group|Pool|Preset|Sequence|Cue|Fixture|Executor|Page|FID|Slot)\s+\d"
    )
    assert [value for value in strings if numbered_object.search(value)] == []

    tree = ast.parse(_SONGCUE_MODULE.read_text(encoding="utf-8"))
    assert _numeric_fstring_constants(tree) == []
    assert _numeric_rig_defaults(tree) == []


def test_static_scanners_catch_injected_forbidden_shapes():
    numbered_object = re.compile(
        r"\b(Group|Pool|Preset|Sequence|Cue|Fixture|Executor|Page|FID|Slot)\s+\d"
    )
    assert numbered_object.search("Store Sequence 3 Cue 1")

    fstring_tree = ast.parse('def x(slot):\n    return f"Preset {4}.{slot}"\n')
    assert _numeric_fstring_constants(fstring_tree)

    default_tree = ast.parse("def store(look, *, group_number: int = 7) -> None: ...")
    assert _numeric_rig_defaults(default_tree)


def _bundle_for_size(size: int):
    sections = parse_sections(tuple((f"Section {index}", index + 1) for index in range(size)))
    selections = tuple(
        SongCueLookSelection(
            section=section,
            requested_dynamics=(1,),
            look=_look(f"look-{section.index}", dynamics=1, value=20 + section.index),
        )
        for section in sections
    )
    return build_songcue_bundle(
        "테스트 곡",
        selections,
        sequences_section=_sequences(1, 2, 4),
        groups_section=_groups(*FULL_RIG),
    )


def _look(look_id: str, *, dynamics: int, value: float = 50) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="rock",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(AttributeValue("Dimmer", value),),
    )


def _sequences(*numbers: int, truncated: bool = False) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": truncated,
        "total": len(numbers),
    }


def _store_refs(commands: tuple[str, ...]) -> list[tuple[int, int, str]]:
    refs: list[tuple[int, int, str]] = []
    for command in commands:
        match = _STORE_RE.fullmatch(command)
        if match:
            refs.append(
                (int(match.group("sequence")), int(match.group("cue")), match.group("name"))
            )
    return refs


def _forbidden_hits(commands: tuple[str, ...]) -> list[tuple[str, str]]:
    return [
        (name, command)
        for command in commands
        for name, pattern in _FORBIDDEN_COMMANDS.items()
        if pattern.search(command)
    ]


def _naive_next_cues(sections) -> list[int]:
    return [1 for _section in sections]


def _has_hangul(value: str) -> bool:
    return any("가" <= char <= "힣" for char in value)


def _unaccounted_look_files() -> tuple[str, ...]:
    """스윕이 「빈 출력」을 요구하는 파일 — 계상된 것들을 뺀 나머지."""
    return tuple(path for path in _PRESERVE_LOOK_FILES if path not in _ACCOUNTED_LOOK_FILES)


def _preserve_diff_command() -> list[str]:
    return [
        "git",
        "diff",
        "--stat",
        f"{_RUN_PHASE_BASE}..HEAD",
        "--",
        *_unaccounted_look_files(),
    ]


def _accounted_diff_body(*paths: str) -> list[str]:
    """계상된 파일의 diff 본문 줄(`+`/`-`, 헤더 제외). 줄번호를 담지 않는다."""
    result = subprocess.run(  # noqa: S603
        [
            "git",
            "diff",
            "--unified=0",
            f"{_RUN_PHASE_BASE}..HEAD",
            "--",
            *(paths or (_T348_ACCOUNTED_FILE,)),
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        line
        for line in result.stdout.splitlines()
        if line[:1] in {"+", "-"} and not line.startswith(("+++", "---"))
    ]


def _tools_hunks_from_run_phase_base() -> list[tuple[int, int]]:
    result = subprocess.run(
        ["git", "diff", "--unified=0", f"{_RUN_PHASE_BASE}..HEAD", "--", _TOOLS_PATH],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    hunks: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        match = _HUNK_RE.match(line)
        if match is not None:
            hunks.append((int(match.group("old_start")), int(match.group("old_count") or "1")))
    return hunks


def _overlaps(old_start: int, old_count: int, protected_start: int, protected_end: int) -> bool:
    old_end = old_start + max(old_count, 1) - 1
    return old_start <= protected_end and protected_start <= old_end


def _numeric_fstring_constants(tree: ast.AST) -> list[ast.FormattedValue]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FormattedValue)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, int | float)
    ]


def _numeric_rig_defaults(tree: ast.AST) -> list[tuple[str, str]]:
    rig_param = re.compile(r"sequence|cue|group|pool|slot|fid|fixture|executor|page", re.IGNORECASE)
    offenders: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        pairs = list(
            zip(
                node.args.args[len(node.args.args) - len(node.args.defaults) :],
                node.args.defaults,
                strict=True,
            )
        ) + list(zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True))
        for arg, default in pairs:
            if (
                default is not None
                and rig_param.search(arg.arg)
                and isinstance(default, ast.Constant)
                and isinstance(default.value, int | float)
            ):
                offenders.append((node.name, arg.arg))
    return offenders


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _StatePort:
    def query_state(self, path: str) -> dict:
        return {}
