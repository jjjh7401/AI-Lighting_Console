"""t215 — 그룹별 I/P/C/B Fade·Delay 를 큐 **파트** 속성으로 내보낸다.

**이 파일은 측정 뒤에 쓰였다.** 파이프라인은 개별 타이밍을 `[MANUAL]` 주석으로
남기고 있었다. 그것이 자동화 불가라서였는지 아무도 재지 않았고, 이 카드가 쟀다.

    2026-09-01 · onPC · 응답기 1.6.2 · 스크래치 Sequence 9 (Sequences 1·2·3 무접촉)

    Set Cue 1 Sequence 9 Property 'Preset1Fade' 3   -> PRESET1FADE  "CueTiming" -> 3.0
    Set Cue 1 Sequence 9 Property 'Preset1Delay' .5 -> PRESET1DELAY "CueTiming" -> 0.5
    Set Cue 5 Part 1 Sequence 9 Property 'Preset1Fade' 6
                                                    -> Part 1 6.0 / Part 0 "CueTiming"
    대조군 'Preset1Frobnicate'                       -> 거절 "Illegal property"

프리셋 타입 번호도 콘솔에서 읽었다(DataPool/PresetPools/1..6 의 name):
1 Dimmer · 2 Position · 3 Gobo · 4 Color · 5 Beam · 6 Focus.

한 파트는 타입당 값을 하나만 갖는다. 그래서 같은 큐에서 값이 충돌하는 그룹은
파트를 갈라야 한다 — 이 저장소의 시트에서 18큐 중 3큐가 그렇다.

증거 전문: `.moai/reports/t215/verdict.md`.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "src" / "Lighting_Designer" / "90_빌드파이프라인"
SCRIPT = SCRIPTS / "make_ma3.py"
STEM = "LXSEQ_SAMPLE_01_Sugar_r3"

# 시트 열 -> 콘솔 속성. 모듈의 표를 다시 쓴 것이다 — 베끼면 대조군이 아니다.
AXIS = (
    (10, "Preset1Fade"),
    (11, "Preset1Delay"),
    (12, "Preset2Fade"),
    (13, "Preset4Fade"),
    (14, "Preset5Fade"),
)
MEASURED_PROPERTIES = frozenset(name for _, name in AXIS)

SET_RE = re.compile(r"^Set Cue (\d+) (?:Part (\d+) )?Sequence 1 Property '([A-Za-z0-9]+)' (\S+)$")
STORE_RE = re.compile(r"^Store Cue (\d+)(?: Part (\d+))? ")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """생성기를 임시 출력 디렉터리로 한 번 돌리고, 모듈과 스크립트 본문을 함께 준다."""
    out = tmp_path_factory.mktemp("t215-ma3")
    saved = os.environ.get("LXSEQ_MA3_OUT")
    saved_path = list(sys.path)
    os.environ["LXSEQ_MA3_OUT"] = str(out)
    try:
        spec = importlib.util.spec_from_file_location("t215_make_ma3", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
        if saved is None:
            os.environ.pop("LXSEQ_MA3_OUT", None)
        else:
            os.environ["LXSEQ_MA3_OUT"] = saved
    text = (out / (STEM + ".ma3.txt")).read_text(encoding="utf-8")
    return module, text


def _sheet_timings(module):
    """시트에서 큐별 (속성, 값) 집합을 독립적으로 뽑는다 — LED-W 는 조명 큐가 아니다."""
    wanted = defaultdict(set)
    for row in module.CUE_EX:
        if row[1] == "LED-W":
            continue
        cueno = int(row[0][1:])
        for idx, prop in AXIS:
            if row[idx] not in ("", None):
                wanted[cueno].add((prop, str(row[idx])))
    return wanted


def _emitted(text):
    emitted = defaultdict(set)
    for line in text.splitlines():
        m = SET_RE.match(line)
        if m:
            emitted[int(m.group(1))].add((m.group(3), m.group(4)))
    return emitted


class TestTheSplitFollowsValueConflict:
    """파트를 가르는 것은 그룹의 수가 아니라 **값의 충돌**이다."""

    def _row(self, grp, i_f="", i_d="", p_f="", c_f="", b_f=""):
        return ["Q000", grp, "", "", "", "", "", "", "", "", i_f, i_d, p_f, c_f, b_f, "", ""]

    def test_compatible_groups_share_one_part(self, built):
        """겹치는 축의 값이 같고 나머지가 비어 있으면 한 파트로 충분하다."""
        module, _ = built
        rows = [self._row("A", i_f="2.0"), self._row("B", i_f="2.0", c_f="1.0")]
        parts = module.split_parts(rows)
        assert len(parts) == 1
        assert parts[0][1] == dict(Preset1Fade="2.0", Preset4Fade="1.0")

    def test_a_conflicting_value_opens_a_new_part(self, built):
        """같은 축에 다른 값이 오면 파트가 갈린다 — 위 검사의 반대 팔이다."""
        module, _ = built
        rows = [self._row("A", i_f="2.0"), self._row("B", i_f="0.5")]
        parts = module.split_parts(rows)
        assert [sorted(r[1] for r in prows) for prows, _ in parts] == [["A"], ["B"]]
        assert [timing["Preset1Fade"] for _, timing in parts] == ["2.0", "0.5"]

    def test_a_group_without_timings_never_joins_a_timed_part(self, built):
        """타이밍 없는 그룹은 큐 타이밍을 따라야 한다 — 남의 파트에 얹히면 값이 바뀐다."""
        module, _ = built
        rows = [self._row("TIMED", i_f="2.0"), self._row("PLAIN")]
        parts = module.split_parts(rows)
        plain = [prows for prows, timing in parts if not timing]
        assert len(plain) == 1
        assert [r[1] for r in plain[0]] == ["PLAIN"]

    def test_the_plain_part_comes_first(self, built):
        """Part 0 은 라벨과 CueFade 를 지는 자리다 — 순서가 뒤집히면 큐가 잘못 이름 붙는다."""
        module, _ = built
        parts = module.split_parts([self._row("TIMED", i_f="2.0"), self._row("PLAIN")])
        assert not parts[0][1]


class TestTheScriptCarriesEveryTiming:
    """`[MANUAL]` 이 사라진 것과 값이 실린 것은 다른 행이다."""

    def test_no_manual_individual_timing_remark_survives(self, built):
        _, text = built
        assert "개별 타이밍(Cue 에디터" not in text

    def test_every_sheet_timing_appears_as_a_set_command(self, built):
        """개수가 아니라 (속성, 값) 짝으로 대조한다 — 개수는 뒤바뀐 값을 통과시킨다."""
        module, text = built
        assert _emitted(text) == _sheet_timings(module)

    def test_the_sheet_actually_has_timings_to_carry(self, built):
        """빈 기대값과 빈 산출물은 위 검사를 공허하게 통과시킨다."""
        module, _ = built
        wanted = _sheet_timings(module)
        assert len(wanted) == 18
        assert sum(len(v) for v in wanted.values()) >= 40

    def test_every_set_command_targets_a_stored_part(self, built):
        """저장된 적 없는 파트에 쓰면 콘솔에서 조용히 아무 일도 안 난다."""
        _, text = built
        stored = set()
        for line in text.splitlines():
            m = STORE_RE.match(line)
            if m:
                stored.add((int(m.group(1)), int(m.group(2) or 0)))
        for line in text.splitlines():
            m = SET_RE.match(line)
            if m:
                assert (int(m.group(1)), int(m.group(2) or 0)) in stored, line

    def test_only_the_measured_property_names_are_emitted(self, built):
        """콘솔이 받은 이름만 쓴다. 안 재 본 이름은 'ok' 를 받고도 아무 일 안 한다."""
        _, text = built
        for line in text.splitlines():
            m = SET_RE.match(line)
            if m:
                assert m.group(3) in MEASURED_PROPERTIES, line

    def test_the_three_divergent_cues_are_the_ones_that_split(self, built):
        """개수만 세면 엉뚱한 큐가 갈려도 통과한다 — 어느 큐인지 적어 둔다."""
        _, text = built
        matches = [STORE_RE.match(line) for line in text.splitlines()]
        split = sorted(set(int(m.group(1)) for m in matches if m and m.group(2)))
        assert split == [40, 110, 160]

    def test_the_conflicting_colour_values_land_on_different_parts(self, built):
        """Q040 은 KEY 가 C8.0, MOVER-U 가 C4.0 이다. 파트를 안 나누면 둘 중 하나가 사라진다.

        위의 집합 대조는 (큐, 파트)를 안 본다 — 모든 Set 을 Part 0 에 몰아 써도
        같은 짝이 나와 통과한다. 이 행이 그 구멍을 막는다.
        """
        _, text = built
        per_part = defaultdict(set)
        for line in text.splitlines():
            m = SET_RE.match(line)
            if m:
                per_part[(int(m.group(1)), int(m.group(2) or 0))].add((m.group(3), m.group(4)))
        assert ("Preset4Fade", "4.0") in per_part[(40, 0)]
        assert ("Preset4Fade", "8.0") in per_part[(40, 1)]
        assert ("Preset4Fade", "8.0") not in per_part[(40, 0)]
