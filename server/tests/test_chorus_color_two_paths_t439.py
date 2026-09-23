"""카드 t439 — AC-LDDESIGN-017 방향의 교차 확인: 같은 후렴 반복(코러스 6회
+ Final Chorus)이 두 곡 조립 경로(웹/채팅 경로 `server/web/session.py` ·
LLM 툴 경로 `server/looks/songcue.py`+`server/orchestrator/tools.py`) 양쪽
모두에서 회차 간 색 항등을 만족하는지 실제 실행으로 확인한다.

**두 경로는 같은 입력을 받을 수 없다** — Path A 는 역할(role)·D-레벨·감독이
고른 팔레트(이름 문자열, 예: "블루")를 입력으로 받아 `_ARC_PALETTE` 아크에서
보조색을 고르고, Path B 는 구간 라벨·다이내믹스 요청을 입력으로 받아
버스킹 룩 라이브러리(`server/looks/busking/`)에서 이미 RGB 값이 박힌 Look
을 고른다. 색의 출처 자체가 다르므로(이름 팔레트 vs 라이브러리 룩) **값을
곧이곧대로 비교하는 것은 의미가 없다** — 이 파일은 대신 "가장 가까운
등가물"(같은 구간 어휘, 같은 반복 횟수, 같은 다이내믹스/세기)을 만들어 두
경로 각각이 **자기 색 표현 안에서** REQ-LDDESIGN-004/030 의 불변식(후렴
반복 전체가 동일한 색을 유지한다)을 실제로 지키는지 재고, 그 결과를
표로 남긴다.
"""

from __future__ import annotations

from pathlib import Path

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue
from server.looks.songcue import (
    _look_color,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.spatial.position_cuesheet import PositionSheetSection
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_ladder import _sequences
from server.web.session import _build_unified_song_plan

_REPORT_PATH = Path(".moai/reports/t439/chorus_color_two_paths.md")

_CHORUS_OCCURRENCES = 6


def _path_a_chorus_colors() -> list[tuple[str, tuple[str, ...]]]:
    """Path A — 확정 구간(role 명시) 경로. intro 1 + chorus 6회 + finale 1."""
    sections = [
        PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro"),
    ]
    start_ms = 4000
    for _ in range(_CHORUS_OCCURRENCES):
        sections.append(
            PositionSheetSection(
                name="Chorus", start_ms=start_ms, mood="", d_level=5, role="chorus"
            )
        )
        start_ms += 4000
    sections.append(
        PositionSheetSection(
            name="Final Chorus", start_ms=start_ms, mood="", d_level=5, role="finale"
        )
    )
    profile = MusicProfile(palette=("블루",))
    plan = _build_unified_song_plan(
        sections=sections,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=(),
        timing=TimingPlan.manual_go(),
        sequence_no=139,
    )
    rows: list[tuple[str, tuple[str, ...]]] = []
    n = 0
    for decision in plan.sections:
        if decision.role == "chorus":
            n += 1
            rows.append((f"Chorus {n}", tuple(decision.palette.colors)))
        elif decision.role == "finale":
            rows.append(("Final Chorus", tuple(decision.palette.colors)))
    return rows


def _path_b_chorus_colors() -> list[tuple[str, tuple[AttributeValue, ...], str]]:
    """Path B — LLM 툴 경로. 같은 반복 횟수의 "Chorus" 라벨을 EDM 장르로
    돌린다(§6 어휘가 다이내믹스를 스스로 정하므로 explicit_dynamics 불필요,
    `test_songcue_section_intent.py` 의 `_chosen` 과 같은 패턴)."""
    library = load_library_from_dir()
    raw_sections = [("Intro", "0:00")]
    t = 4
    for _ in range(_CHORUS_OCCURRENCES):
        raw_sections.append(("Chorus", f"0:{t:02d}"))
        t += 4
    # Final Chorus 어휘가 §6 표에 없으므로(9종 닫힌 어휘는 SPEC-LDDESIGN-001
    # M1 대상, Path B 라이브러리는 아직 옛 5종 어휘다) 마지막 반복을 그대로
    # "Chorus" 로 둔다 — Path A 처럼 별도 finale 역할을 걸 수 없는 것 자체가
    # "두 경로가 같은 입력을 받을 수 없다"의 실측 사례다(아래 리포트에 기록).
    sections = parse_sections(raw_sections)
    selections = map_sections_to_looks(sections, library, "edm")
    bundle = build_songcue_bundle(
        "t439 cross-path",
        selections,
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    rows: list[tuple[str, tuple[AttributeValue, ...], str]] = []
    n = 0
    for section_bundle in bundle.stored_sections:
        if section_bundle.section.label != "Chorus":
            continue
        n += 1
        look = section_bundle.selection.look
        colors = _look_color(look) if look is not None else ()
        rows.append((f"Chorus {n}", colors, look.look_id if look is not None else "(none)"))
    return rows


class TestBothPathsSatisfyChorusColorIdentityInTheirOwnRepresentation:
    def test_path_a_all_chorus_occurrences_share_one_palette_final_excluded(self):
        rows = _path_a_chorus_colors()
        chorus_rows = [colors for label, colors in rows if label != "Final Chorus"]
        assert len(chorus_rows) == _CHORUS_OCCURRENCES
        assert len(set(chorus_rows)) == 1, f"Path A 후렴 색이 갈렸다: {rows}"

    def test_path_b_all_chorus_occurrences_share_one_look(self):
        rows = _path_b_chorus_colors()
        assert len(rows) == _CHORUS_OCCURRENCES, (
            f"기대한 {_CHORUS_OCCURRENCES}회가 아니라 {len(rows)}회 저장됐다 — 입력 확인"
        )
        look_ids = {look_id for _label, _colors, look_id in rows}
        assert len(look_ids) == 1, f"Path B 후렴 룩이 갈렸다: {rows}"
        color_tuples = {colors for _label, colors, _look_id in rows}
        assert len(color_tuples) == 1, f"Path B 후렴 ColorRGB 가 갈렸다: {rows}"

    def test_write_the_cross_path_report(self):
        """두 경로를 실제로 돌려 표로 남긴다 — 값 비교가 아니라 **불변식**
        비교(각 경로가 자기 표현 안에서 항등인가)가 목적임을 표 자체에
        명시한다."""
        path_a_rows = _path_a_chorus_colors()
        path_b_rows = _path_b_chorus_colors()

        lines = [
            "# t439 — 후렴 회차 색, 두 조립 경로 대조",
            "",
            "명령: `uv run pytest "
            "server/tests/test_chorus_color_two_paths_t439.py::"
            "TestBothPathsSatisfyChorusColorIdentityInTheirOwnRepresentation::"
            "test_write_the_cross_path_report -q`",
            "",
            "두 경로는 같은 입력을 받을 수 없다(Path A: 역할+D레벨+이름 팔레트, "
            "Path B: 구간 라벨+다이내믹스 → 버스킹 룩 라이브러리의 RGB). "
            "그래서 이 표는 값을 직접 비교하지 않는다 — 각 경로가 **자기 색 "
            "표현 안에서** REQ-LDDESIGN-004/030(후렴 반복 전체가 동일한 색을 "
            "유지한다)을 지키는지만 본다.",
            "",
            "## Path A — server/web/session.py (`_build_unified_song_plan`)",
            "",
            "| 구간 | palette (primary, accent) |",
            "|---|---|",
        ]
        for label, colors in path_a_rows:
            lines.append(f"| {label} | {colors} |")
        path_a_chorus_only = {c for label, c in path_a_rows if label != "Final Chorus"}
        path_a_verdict = "PASS" if len(path_a_chorus_only) == 1 else "FAIL"
        lines += [
            "",
            f"항등 확인 — Final Chorus 제외 {_CHORUS_OCCURRENCES}회 전부 팔레트 1종: "
            f"{path_a_verdict}",
            "",
            "## Path B — server/looks/songcue.py (`build_songcue_bundle`, genre=edm)",
            "",
            "| 구간 | look_id | ColorRGB |",
            "|---|---|---|",
        ]
        for label, colors, look_id in path_b_rows:
            color_repr = ", ".join(f"{c.name}={c.value}" for c in colors) or "(no color channel)"
            lines.append(f"| {label} | {look_id} | {color_repr} |")
        lines += [
            "",
            f"항등 확인 — {_CHORUS_OCCURRENCES}회 전부 같은 look_id/ColorRGB: "
            f"{'PASS' if len({lid for _l, _c, lid in path_b_rows}) == 1 else 'FAIL'}",
            "",
            "## 두 경로가 다른 지점 (실측)",
            "",
            "- Path A 는 이 SPEC(M1, REQ-005~010)의 9종 닫힌 구간 어휘를 쓴다 "
            "(`intro`/`chorus`/`finale` 등 role 필드) — Final Chorus 가 chorus 와는 "
            "별도인 `finale` role 이라 REQ-030 의 클라이맥스 예외를 구조적으로 "
            "표현할 자리가 있다.",
            "- Path B(`server/looks/songcue.py`)는 아직 옛 §6 5종 어휘(Intro/Build/"
            "Chorus/Drop/Breakdown 계열)를 쓴다 — `Final Chorus` 라는 별도 어휘가 "
            "없어 이 카드에서는 마지막 반복도 그냥 `Chorus`로 돌렸다. 두 경로가 "
            "완전히 같은 입력을 받을 수 없다는 것 자체가 REQ-LDDESIGN-003(두 경로가 "
            "단일 컴포저로 수렴해야 한다, M6/AC-017)의 잔여 격차이고, 이 카드(REQ-004) "
            "가 아니라 그 REQ 의 범위다.",
            "- Path A 의 색은 감독이 고른 이름(팔레트 문자열)이고 Path B 의 색은 "
            "버스킹 룩 라이브러리에 미리 박힌 RGB 값이다 — 같은 곡이라도 두 경로의 "
            "색 문자열/값이 우연히조차 일치할 이유가 없다(서로 다른 어휘 공간).",
        ]
        _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert _REPORT_PATH.exists()


class TestPathBFabricatedControl:
    """날조 대조군 — Path B 의 항등(위 테스트)이 공허하지 않다는 것을
    보인다. Path B 는 이 카드가 고친 코드가 아니라(§7 [HARD] "되돌아옴"
    이 SPEC-LDRETURN-001 에서 이미 landed) `test_songcue_section_intent.py`
    의 `test_restoring_the_alphabetical_pick_brings_the_measured_defect_back`
    과 같은 기법으로, "되돌아옴" 정렬 축을 빼면 실제로 색이 갈린다는 것을
    보여 위 GREEN 이 우연이 아님을 확인한다."""

    def test_removing_the_returning_sort_axis_breaks_chorus_color_identity(self, monkeypatch):
        """`sorted_candidates`(§7.1)의 정렬 키는 되돌아옴 → 의도 → 대비 →
        전순서 순이다(`ordering_key`, `server/looks/section_intent.py`).
        완전 알파벳순으로 갈아치우면 대비 축까지 함께 사라져 이 대조군이
        공허해진다(대비가 없으면 애초에 매 회차가 정적으로 같은 후보를
        고른다 — 실측: 단순 알파벳 대체는 여전히 1종). 그래서 **되돌아옴
        칸만** 지우고 의도·대비·전순서는 그대로 둔 대체 함수로 패치한다
        — 그래야 "돌아오지 않으면 대비가 이긴다"는 §7.1 의 실제 계약을
        무력화한 것이 된다."""
        import server.looks.section_intent as section_intent_module

        def _ordering_key_without_return_bias(look, *, previous, intent, returning=None):
            fits_intent = intent is not None and section_intent_module.brightness_fits(
                intent, look
            )
            fits = 0 if fits_intent else 1
            gap = (
                section_intent_module.contrast(previous, look)
                if previous is not None
                else section_intent_module.Fraction(0)
            )
            return (fits, -gap, look.dynamics, look.look_id)

        monkeypatch.setattr(
            section_intent_module, "ordering_key", _ordering_key_without_return_bias
        )
        rows = _path_b_chorus_colors()

        look_ids = {look_id for _label, _colors, look_id in rows}
        assert len(look_ids) > 1, (
            "날조 대조군이 공허하다 — '되돌아옴' 축을 없앴는데도 룩이 하나뿐이다: "
            f"{rows}"
        )
