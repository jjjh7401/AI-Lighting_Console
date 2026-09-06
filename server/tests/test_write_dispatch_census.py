"""SPEC-COPILOT-BULKGATE-001 — 콘솔 디스패치 자리를 전수로 분류한다.

왜 이 파일이 있는가. 이 저장소의 승인 봉합은 전부 **각자 따로** 만들어졌다 —
`import_lxseq_presets` · `import_lxseq_cues` · `create_arrangement_groups` ·
`_cue_sheet_draft_apply`, 그리고 이 SPEC 이 더한 `prepare_songcue`. 다섯 개가
같은 이유로 다섯 번 만들어졌다는 사실이 문제를 말한다: **나중에 추가되는 쓰기
경로는 아무것도 물려받지 않는다.** 곡→콘솔 경로만 닫으면 여섯 번째가 또
조용히 열린다.

그래서 이 검사는 봉합을 달지 않는다. 디스패치 자리를 **전수로 열거**하고,
각 자리가 아래 세 표 중 **정확히 하나**에 등재돼 있기를 요구한다. 새 호출자를
추가한 사람은 「이 자리가 쇼파일을 고치는가」를 분류하기 전에는 초록을 못 본다.

| 표 | 뜻 |
|---|---|
| `SHOWFILE_WRITE_DISPATCHES` | 쇼파일을 고치고, 감싸는 함수에 봉합이 있다 |
| `WRITE_WITHOUT_SEAM_DISPATCHES` | 쇼파일을 고치는데 봉합이 **없다** — 각자 후속 카드 |
| `REVIEWED_NON_WRITE_DISPATCHES` | 사람이 읽고 쇼파일 쓰기가 아니라고 판정했다 |

둘째 표는 이 SPEC 이 **정직하려고** 두는 자리다. 봉합을 다는 일은 이 SPEC 의
범위 밖이고(§4), 그렇다고 쓰기를 비-쓰기 표에 숨기면 계측기가 거짓말을 한다.
등재된 자리들은 오늘 분류 층(`blacklist.yaml`)이 잡거나 못 잡는데, 어느 쪽인지는
이 검사가 답하지 않는다 — 그 축은 각 후속 카드의 몫이다.

**한계 (REQ-BULKGATE-013).** 이것은 `test_architecture.py` 와 같은 계열의
**정적 텍스트 주사**다. `name="run_commands"` 라는 리터럴을 찾을 뿐이라:

- 도구 이름을 변수에 담아 간접 호출하는 형태(`name=TOOL`)는 **못 잡는다**.
- 런타임에 만들어지는 디스패치도 **못 잡는다**.
- 등재된 자리가 실제로 안전한지도 **말하지 않는다** — 분류를 강제할 뿐이다.

잡지 못하는 것을 잡는다고 적지 않는다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

#: 주사 대상. 프로덕션 디스패치가 사는 두 파일.
SCANNED_FILES = (
    "server/orchestrator/tools.py",
    "server/web/session.py",
)

#: 정적 주사가 찾는 리터럴 — plan 단계 실측이 쓴 것과 같은 패턴이다
#: (`grep -c 'name="run_commands"'` → tools.py 12 · session.py 16).
DISPATCH_LITERAL = re.compile(r'name="run_commands"')

#: 봉합으로 인정하는 어휘. 셋 중 하나가 감싸는 함수 본문에 있으면 봉합이 있다.
SEAM_TOKENS = ("risk=", "request_approval(", "_accept_")

#: 자리의 정체는 (파일, 감싸는 함수, 그 함수 안 몇 번째 자리)다.
#: 행 번호를 정체로 쓰면 무관한 편집 한 줄에도 표가 깨진다 — 행 번호는
#: **실패 문면에만** 싣는다(REQ-BULKGATE-011).

#: ① 쇼파일을 고치고 봉합이 붙어 있는 자리.
SHOWFILE_WRITE_DISPATCHES: dict[tuple[str, str, int], str] = {
    ("server/orchestrator/tools.py", "prepare_songcue", 0): (
        "곡 하나가 Sequence 와 Timecode 슬롯을 통째로 만든다 — "
        "SPEC-COPILOT-BULKGATE-001 의 번들 위험 선언(risk=)이 붙었다"
    ),
    ("server/orchestrator/tools.py", "import_lxseq_presets", 0): (
        "Store Preset / Label Preset — 프리셋 쓰기. 자체 request_approval"
    ),
    ("server/orchestrator/tools.py", "import_lxseq_cues", 0): (
        "Store Sequence Cue / Label — 큐 쓰기. 자체 request_approval"
    ),
    ("server/orchestrator/tools.py", "create_arrangement_groups", 0): (
        "Store Group / Label Group — 그룹 쓰기. 자체 request_approval "
        "(분류상 safe 라 승인 단계를 아예 못 본다는 주석이 그 자리에 있다)"
    ),
    ("server/web/session.py", "_cue_sheet_draft_apply", 0): (
        "Store Sequence Cue /Merge — 초안 반영. 카드 t292 의 _accept_draft_apply_batch"
    ),
    ("server/web/session.py", "_song_finalize", 0): (
        "감독의 곡 흐름(업로드→분석→확인→인터뷰)이 실제로 나가는 자리 — "
        "_reviewed_song_commands 의 Store Sequence Cue + Store Timecode 다발. "
        "SPEC-COPILOT-WRITEGATE-001 의 번들 위험 선언(risk=)이 붙었다 "
        "(카드 t317: 2026-09-07 실측이 잰 것은 prepare_songcue 가 아니라 이 자리였다)"
    ),
}

#: ② 쇼파일을 고치는데 봉합이 없는 자리 — 각자 후속 카드다.
#:
#: 이 표에 있다는 것은 「분류했다」는 뜻이지 「안전하다」는 뜻이 **아니다**.
#: 이 SPEC 이 봉합을 다는 자리는 곡→콘솔 하나뿐이고(§4 범위 제외), 나머지는
#: 각자 자기 카드를 갖는다. 여기 있는 자리에 봉합이 붙으면 이 검사가
#: 실패하고, 그때 ① 표로 옮기면 된다 — 표는 양방향으로 정직하다.
WRITE_WITHOUT_SEAM_DISPATCHES: dict[tuple[str, str, int], str] = {
    ("server/orchestrator/tools.py", "instantiate_look", 0): (
        "looks/instantiate.py 가 Store Preset 을 낸다 — 오늘은 blacklist 의 "
        "'Store Preset' 항목이 분류 층에서 잡는다"
    ),
    ("server/orchestrator/tools.py", "prepare_busking", 0): (
        "build_genre_bundle → looks/instantiate 의 Store Preset 다발"
    ),
    ("server/orchestrator/tools.py", "precheck_patch", 0): (
        "prechk/macro.py 가 Store Macro <slot> 을 낸다 — 매크로 풀 쓰기"
    ),
    ("server/orchestrator/tools.py", "_deliver_fx_plan", 0): (
        "fx/instantiate.py 가 Store Sequence <n> Cue 1 / Store Preset 을 낸다"
    ),
    ("server/orchestrator/tools.py", "compile_scene", 0): (
        "씬 컴파일이 Store 계열을 낸다 — 씬을 콘솔 오브젝트로 굳힌다"
    ),
    ("server/orchestrator/tools.py", "arrange_fixtures", 0): (
        "Set Fixture <fid> Posx/Posy/Posz — 패치의 3D 좌표를 고친다. "
        "'Set Fixture' 는 blacklist 에 있어 분류 층이 잡는다"
    ),
    ("server/web/session.py", "run_look_bundle", 0): ("LookInstantiation.commands → Store Preset"),
    ("server/web/session.py", "_look_pan_tilt", 0): (
        "position_preset_store_commands 가 붙는 갈래에서 Store Preset 2.<n>"
    ),
    ("server/web/session.py", "_position_fx_sequence", 0): ("FX 포지션 시퀀스를 Store 로 굳힌다"),
    ("server/web/session.py", "_offer_fx_executor_assignment", 0): (
        "Assign Sequence <n> At Executor <t> — 익스큐터 배정은 쇼파일에 남는다"
    ),
    ("server/web/session.py", "_phaser_recall_sequence", 0): (
        "페이저 회수분을 Store 로 시퀀스에 굳힌다"
    ),
    ("server/web/session.py", "_store_position_preset_looks", 0): (
        "Store Preset + Label — 포지션 프리셋 룩 저장"
    ),
    ("server/web/session.py", "_position_cue_store", 0): (
        "position_cue_store_commands → Store Sequence <n> Cue <m>"
    ),
    ("server/web/session.py", "_position_cue_sheet", 0): (
        "sheet.bundles → position_cue_bundle 의 Store Sequence <n> Cue <m> 다발"
    ),
    ("server/web/session.py", "_merge_timeline_cue_position", 0): (
        "타임라인 큐에 포지션을 Store 로 병합한다"
    ),
    ("server/web/session.py", "_setlist_mode", 0): (
        "Copy Sequence / Assign Sequence … At Executor — 셋리스트 배분. "
        "plan 단계가 '미확인 후보'로 남겼던 자리이며, run 단계에서 "
        "쓰기로 확인했다"
    ),
}

#: ③ 사람이 읽고 쇼파일 쓰기가 **아니라고** 판정한 자리. 사유가 필수다.
REVIEWED_NON_WRITE_DISPATCHES: dict[tuple[str, str, int], str] = {
    ("server/orchestrator/tools.py", "_fire", 0): (
        "Plugin '<name>' 한 줄 — 패치 조회 플러그인을 돌린다. 오브젝트를 만들지도 덮지도 않는다"
    ),
    ("server/orchestrator/tools.py", "build_toolset", 0): (
        '디스패치가 아니라 ToolDefinition(name="run_commands", …) — 도구 '
        "**정의**다. 같은 리터럴이라 주사에 걸리지만 명령을 보내지 않는다"
    ),
    ("server/web/session.py", "_point_fixtures_at_target", 0): (
        "Fixture <fid> Attribute 'Pan'/'Tilt' At <값> — 프로그래머 값이다. "
        "Store 가 없으면 쇼파일에 안 남는다"
    ),
    ("server/web/session.py", "_position_mood_suggestion", 0): (
        "aimed_commands 의 Attribute At 줄뿐 — 프로그래머 값이다"
    ),
    ("server/web/session.py", "_phaser_recall", 0): (
        "프리셋 회수/해제 한 줄 — 저장된 값을 프로그래머로 불러올 뿐이다"
    ),
    ("server/web/session.py", "_song_finalize", 1): (
        "ClearAll 한 줄 — 프로그래머를 비운다. 쇼파일 오브젝트는 안 건드린다"
    ),
}


def _scan(path: str) -> list[tuple[tuple[str, str, int], int]]:
    """(정체, 행 번호) 목록. 정체 = (파일, 감싸는 함수, 함수 안 순번)."""
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    funcs = [
        (node.lineno, node.end_lineno, node.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    seen: dict[str, int] = {}
    found: list[tuple[tuple[str, str, int], int]] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if not DISPATCH_LITERAL.search(line):
            continue
        # 가장 안쪽으로 감싸는 함수가 그 자리의 주인이다.
        enclosing = sorted(
            (f for f in funcs if f[0] <= lineno <= f[1]),
            key=lambda f: f[1] - f[0],
        )
        name = enclosing[0][2] if enclosing else "<module>"
        index = seen.get(name, 0)
        seen[name] = index + 1
        found.append(((path, name, index), lineno))
    return found


def _function_body(path: str, function: str) -> str:
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == function
    )
    return "\n".join(source.splitlines()[node.lineno - 1 : node.end_lineno])


def _all_sites() -> dict[tuple[str, str, int], int]:
    sites: dict[tuple[str, str, int], int] = {}
    for path in SCANNED_FILES:
        for key, lineno in _scan(path):
            sites[key] = lineno
    return sites


class TestEverySiteIsClassified:
    def test_the_three_tables_are_a_partition_not_a_union(self):
        # 한 자리가 두 표에 동시에 있으면 분류가 아니라 중복이다.
        pairs = (
            (
                "SHOWFILE_WRITE",
                SHOWFILE_WRITE_DISPATCHES,
                "WRITE_WITHOUT_SEAM",
                WRITE_WITHOUT_SEAM_DISPATCHES,
            ),
            (
                "SHOWFILE_WRITE",
                SHOWFILE_WRITE_DISPATCHES,
                "REVIEWED_NON_WRITE",
                REVIEWED_NON_WRITE_DISPATCHES,
            ),
            (
                "WRITE_WITHOUT_SEAM",
                WRITE_WITHOUT_SEAM_DISPATCHES,
                "REVIEWED_NON_WRITE",
                REVIEWED_NON_WRITE_DISPATCHES,
            ),
        )
        for left_name, left, right_name, right in pairs:
            overlap = set(left) & set(right)
            assert not overlap, (
                f"{left_name} 과 {right_name} 에 동시에 등재된 자리: {sorted(overlap)}"
            )

    def test_no_dispatch_site_is_unregistered(self):
        # 여섯 번째 경로를 잡는 자리. 새 호출자를 추가한 사람은 「쇼파일을
        # 고치는가」를 분류하기 전에는 초록을 못 본다.
        sites = _all_sites()
        registered = (
            set(SHOWFILE_WRITE_DISPATCHES)
            | set(WRITE_WITHOUT_SEAM_DISPATCHES)
            | set(REVIEWED_NON_WRITE_DISPATCHES)
        )
        unregistered = sorted(
            (path, function, index, sites[(path, function, index)])
            for (path, function, index) in sites
            if (path, function, index) not in registered
        )
        assert not unregistered, (
            "등재되지 않은 run_commands 디스패치 자리가 있습니다 — "
            "쇼파일을 고치는지 분류해 세 표 중 하나에 넣어 주세요:\n"
            + "\n".join(
                f"  {path}:{line}  (함수 {function}, 그 함수 안 {index}번째 자리)"
                for path, function, index, line in unregistered
            )
        )

    def test_no_table_entry_points_at_a_vanished_site(self):
        # 표만 남고 자리가 사라지면 계측기가 실제와 어긋난다.
        sites = set(_all_sites())
        registered = (
            set(SHOWFILE_WRITE_DISPATCHES)
            | set(WRITE_WITHOUT_SEAM_DISPATCHES)
            | set(REVIEWED_NON_WRITE_DISPATCHES)
        )
        stale = sorted(registered - sites)
        assert not stale, f"표에는 있는데 코드에 없는 자리: {stale}"

    def test_the_scanned_count_matches_the_tables(self):
        # 분모를 함께 적는 규율. plan 단계 실측은 tools.py 12 + session.py 16 = 28.
        sites = _all_sites()
        total = (
            len(SHOWFILE_WRITE_DISPATCHES)
            + len(WRITE_WITHOUT_SEAM_DISPATCHES)
            + len(REVIEWED_NON_WRITE_DISPATCHES)
        )
        assert len(sites) == total, f"주사 {len(sites)}자리 대 표 합계 {total}"

    def test_every_reviewed_non_write_entry_carries_a_reason(self):
        for key, reason in REVIEWED_NON_WRITE_DISPATCHES.items():
            assert reason.strip(), key

    def test_every_write_without_seam_entry_carries_a_reason(self):
        for key, reason in WRITE_WITHOUT_SEAM_DISPATCHES.items():
            assert reason.strip(), key


class TestSeamPresence:
    def test_each_showfile_write_site_has_a_seam_in_its_function(self):
        # REQ-BULKGATE-012 — 봉합의 존재를 정적으로 단언한다.
        for path, function, _index in SHOWFILE_WRITE_DISPATCHES:
            body = _function_body(path, function)
            present = [token for token in SEAM_TOKENS if token in body]
            assert present, f"{path} 의 {function} 에 봉합이 없습니다 (찾은 어휘: {SEAM_TOKENS})"

    def test_each_write_without_seam_site_really_has_no_seam(self):
        # 표가 양방향으로 정직하려면 이쪽도 재야 한다. 봉합이 붙으면 이
        # 검사가 실패하고, 그때 SHOWFILE_WRITE_DISPATCHES 로 옮긴다.
        for path, function, _index in WRITE_WITHOUT_SEAM_DISPATCHES:
            body = _function_body(path, function)
            present = [token for token in SEAM_TOKENS if token in body]
            assert not present, (
                f"{path} 의 {function} 에 봉합 {present} 이 생겼습니다 — "
                "SHOWFILE_WRITE_DISPATCHES 로 옮겨 주세요"
            )


class TestTheCensusStatesItsLimits:
    def test_the_module_docstring_names_what_it_cannot_catch(self):
        doc = __doc__ or ""
        assert "정적" in doc
        assert "간접" in doc
