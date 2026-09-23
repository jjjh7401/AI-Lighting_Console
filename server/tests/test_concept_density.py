"""3층 큐 밀도 컴파일러 시험 — SPEC-LDDESIGN-001 M4 (REQ-LDDESIGN-036~041,
045~046, 카드 t437).

두 실측 곡(Rain.mp3·Too Cool.mp3, `pilot_baseline.json` 8곡 기준선)의
구간 표를 픽스처로 그대로 옮겨 썼다 — 실행 시점에 파일을 읽지 않는다
(카드 지시 "read-only, outside git ... copied into the test file, not
read at test time"). 초 단위 변환(``mm:ss`` → 초)만 이 파일 안에서
한다.
"""

from __future__ import annotations

import pytest

from server.concept.cue_model import layer_limit_warning
from server.concept.density import (
    GROUP_ROSTER,
    MOVER_GROUPS,
    SectionOccurrence,
    bar_seconds,
    compile_density,
    distribute_motion_steps,
    g13_density_warning,
)
from server.concept.resolver import resolve_sequence
from server.concept.vocab import ONE_SHOTS, TRIGGERS, VocabError


def _mmss(text: str) -> float:
    minutes, seconds = text.split(":")
    return float(int(minutes) * 60 + int(seconds))


def _remap(raw: list[tuple[str, str, str]]) -> list[SectionOccurrence]:
    """``(원시 이름, 시작 mm:ss, 종료 mm:ss)`` 목록을 이미 9종 어휘로
    재매핑된 :class:`SectionOccurrence` 목록으로 바꾼다 — 마지막
    ``"Chorus"`` 만 ``"Final Chorus"`` 로 승급한다(REQ-008 과 같은
    방향, 이 파일 전용 픽스처 헬퍼일 뿐 production 코드가 아니다).
    """
    chorus_positions = [i for i, (name, _, _) in enumerate(raw) if name == "Chorus"]
    last_chorus = chorus_positions[-1] if chorus_positions else None
    occurrence_by_name: dict[str, int] = {}
    sections: list[SectionOccurrence] = []
    for i, (name, start, end) in enumerate(raw):
        label = "Final Chorus" if (name == "Chorus" and i == last_chorus) else name
        occurrence_by_name[label] = occurrence_by_name.get(label, 0) + 1
        sections.append(
            SectionOccurrence(
                section=label,
                occurrence=occurrence_by_name[label],
                start=_mmss(start),
                end=_mmss(end),
            )
        )
    return sections


# --- 픽스처 1: Rain.mp3 (76.0bpm, pilot_baseline.json 실측) ------------------
#
# 절 4개(REQ-021/AC-010 대상)·빌드업 3자리·눈 리셋 1자리(Final Chorus→
# Outro 간격 (209-179)/bar ≈ 9.5마디 ≥3)를 모두 갖춘 중간 밀도 곡이다.

RAIN_RAW: list[tuple[str, str, str]] = [
    ("Intro", "0:00", "0:20"),
    ("Verse", "0:20", "0:33"),
    ("Verse", "0:33", "0:49"),
    ("Chorus", "0:49", "1:06"),
    ("Chorus", "1:06", "1:19"),
    ("Verse", "1:19", "1:46"),
    ("Chorus", "1:46", "2:03"),
    ("Chorus", "2:03", "2:18"),
    ("Chorus", "2:18", "2:46"),
    ("Verse", "2:46", "2:59"),
    ("Chorus", "2:59", "3:29"),
    ("Outro", "3:29", "3:42"),
]
RAIN_BPM = 76.0


# --- 픽스처 2: Too Cool.mp3 (161.5bpm, pilot_baseline.json 실측) -------------
#
# 후렴 13회·브릿지 2개 — REQ-045(4회차 이후 후렴당 최대 1개)와
# REQ-046/047(브릿지 축소 + 구간 단위 비교)을 실제 8곡 실측 밀도로
# 시험한다.

TOO_COOL_RAW: list[tuple[str, str, str]] = [
    ("Intro", "0:00", "0:10"),
    ("Chorus", "0:10", "0:16"),
    ("Chorus", "0:16", "0:22"),
    ("Chorus", "0:22", "0:28"),
    ("Chorus", "0:28", "0:34"),
    ("Chorus", "0:34", "0:40"),
    ("Chorus", "0:40", "0:46"),
    ("Verse", "0:46", "0:57"),
    ("Verse", "0:57", "1:05"),
    ("Verse", "1:05", "1:17"),
    ("Chorus", "1:17", "1:28"),
    ("Chorus", "1:28", "1:34"),
    ("Chorus", "1:34", "1:40"),
    ("Chorus", "1:40", "1:51"),
    ("Verse", "1:51", "2:00"),
    ("Chorus", "2:00", "2:10"),
    ("Chorus", "2:10", "2:16"),
    ("Chorus", "2:16", "2:24"),
    ("Bridge", "2:24", "2:30"),
    ("Bridge", "2:30", "2:38"),
    ("Verse", "2:38", "2:44"),
    ("Verse", "2:44", "2:50"),
    ("Outro", "2:50", "3:01"),
]
TOO_COOL_BPM = 161.5


class TestBarSeconds:
    """REQ-037/038 마디 계산 단위(4/4 가정)."""

    def test_bar_seconds_4_4(self) -> None:
        assert bar_seconds(120.0) == pytest.approx(2.0)
        assert bar_seconds(76.0) == pytest.approx(3.1579, abs=1e-3)


class TestSectionOccurrenceValidation:
    """REQ-005/016 — 9종 어휘 밖의 이름은 생성 시점에 거부된다."""

    def test_rejects_out_of_vocab_section(self) -> None:
        with pytest.raises(VocabError):
            SectionOccurrence(section="Hook", occurrence=1, start=0.0, end=10.0)

    def test_rejects_non_positive_duration(self) -> None:
        with pytest.raises(ValueError):
            SectionOccurrence(section="Intro", occurrence=1, start=10.0, end=10.0)

    def test_rejects_zero_occurrence(self) -> None:
        with pytest.raises(ValueError):
            SectionOccurrence(section="Intro", occurrence=0, start=0.0, end=10.0)


class TestDensityIsTriggerGrounded:
    """REQ-036 — 큐 밀도는 트리거(구간 발생·워크시트 트리거)로 정해지지,
    마디 수 기계 분할로 정해지지 않는다(AC-LDDESIGN-032)."""

    def test_every_row_is_section_occurrence_or_vocab_trigger(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        for row in result.sequence:
            if row["kind"] == "section":
                # 구간 큐의 근거는 "그 구간이 시작했다"는 사건 하나뿐이다 —
                # trigger 필드가 없다(마디 분할 표식이 아니다).
                assert row["trigger"] is None
            else:
                assert row["kind"] == "phrase"
                assert row["trigger"] in TRIGGERS

    def test_section_cue_count_equals_occurrence_count_not_bar_count(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        section_rows = [row for row in result.sequence if row["kind"] == "section"]
        # 마디 분할이었다면 곡 길이/마디 길이에 비례했을 것이다(222.6초/
        # 3.16초 ≈ 70마디) — 실제로는 입력 구간 발생 수(12개)와 정확히
        # 같다.
        assert len(section_rows) == len(sections)


class TestBuildupPhraseCue:
    """REQ-037 — 빌드업 프레이즈 큐 삽입 조건과 위치."""

    def test_inserted_before_general_chorus_when_previous_is_long_enough(self) -> None:
        # 120bpm → 마디 2초. Verse 40초(20마디) ≥ 5마디 조건을 만족한다.
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=10.0),
            SectionOccurrence(section="Verse", occurrence=1, start=10.0, end=50.0),
            SectionOccurrence(section="Chorus", occurrence=1, start=50.0, end=66.0),
            SectionOccurrence(section="Outro", occurrence=1, start=66.0, end=76.0),
        ]
        result = compile_density(sections, 120.0)
        buildups = [row for row in result.sequence if row["trigger"] == "빌드업 시작"]
        assert len(buildups) == 1
        # 일반 후렴 앞은 4마디(=8초) 전 — 50 - 8 = 42.0.
        assert buildups[0]["ts"] == pytest.approx(42.0)
        assert buildups[0]["tracking"] == "cue_only"

    def test_final_chorus_uses_3_bar_threshold_and_2_bar_lead(self) -> None:
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=10.0),
            SectionOccurrence(section="Verse", occurrence=1, start=10.0, end=16.0),  # 6s=3bars
            SectionOccurrence(section="Final Chorus", occurrence=1, start=16.0, end=32.0),
            SectionOccurrence(section="Outro", occurrence=1, start=32.0, end=42.0),
        ]
        result = compile_density(sections, 120.0)
        buildups = [row for row in result.sequence if row["trigger"] == "빌드업 시작"]
        assert len(buildups) == 1
        # Final Chorus 는 2마디(=4초) 전 — 16 - 4 = 12.0.
        assert buildups[0]["ts"] == pytest.approx(12.0)

    def test_not_inserted_when_previous_section_too_short(self) -> None:
        # Verse 4초=2마디 < 5마디 문턱 — 삽입되지 않는다.
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=10.0),
            SectionOccurrence(section="Verse", occurrence=1, start=10.0, end=14.0),
            SectionOccurrence(section="Chorus", occurrence=1, start=14.0, end=30.0),
            SectionOccurrence(section="Outro", occurrence=1, start=30.0, end=40.0),
        ]
        result = compile_density(sections, 120.0)
        assert not [row for row in result.sequence if row["trigger"] == "빌드업 시작"]

    def test_not_inserted_when_previous_is_already_chorus_family(self) -> None:
        # Intro 6초(=3마디, <5마디 문턱) — Chorus1 앞 빌드업도 조건
        # 미달이라 함께 걸러진다. Chorus2 는 직전이 Chorus1(후렴 계열)
        # 이라 길이와 무관하게 걸러진다.
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=6.0),
            SectionOccurrence(section="Chorus", occurrence=1, start=6.0, end=22.0),
            SectionOccurrence(section="Chorus", occurrence=2, start=22.0, end=38.0),
            SectionOccurrence(section="Outro", occurrence=1, start=38.0, end=48.0),
        ]
        result = compile_density(sections, 120.0)
        assert not [row for row in result.sequence if row["trigger"] == "빌드업 시작"]

    def test_rain_three_qualifying_buildup_slots(self) -> None:
        # Rain.mp3 실측(bar≈3.158s) — Verse2(16s≈5.07마디)→Chorus1,
        # Verse3(27s≈8.55마디)→Chorus3(둘 다 일반 후렴 문턱 5마디 이상),
        # Verse4(13s≈4.12마디)→Final Chorus(Final 문턱은 3마디 이상이라
        # 여기서도 만족) — 세 자리 모두 조건을 만족한다. Chorus2·4·5 는
        # 직전이 후렴 계열이라 걸러진다.
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        buildups = [row for row in result.sequence if row["trigger"] == "빌드업 시작"]
        assert len(buildups) == 3


class TestEyeResetPhraseCue:
    """REQ-038 — 눈 리셋 프레이즈 큐 삽입 조건과 위치."""

    def test_inserted_when_final_chorus_precedes_outro_by_3_bars_or_more(self) -> None:
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=10.0),
            SectionOccurrence(section="Chorus", occurrence=1, start=10.0, end=26.0),
            SectionOccurrence(section="Final Chorus", occurrence=1, start=26.0, end=50.0),
            SectionOccurrence(section="Outro", occurrence=1, start=50.0, end=60.0),
        ]
        result = compile_density(sections, 120.0)
        resets = [row for row in result.sequence if row["trigger"] == "드롭 직전의 정적"]
        assert len(resets) == 1
        assert resets[0]["section"] == "Final Chorus"
        # Outro 진입 1마디(=2초) 전 — 50 - 2 = 48.0.
        assert resets[0]["ts"] == pytest.approx(48.0)
        assert resets[0]["tracking"] == "cue_only"

    def test_not_inserted_when_gap_below_3_bars(self) -> None:
        sections = [
            SectionOccurrence(section="Intro", occurrence=1, start=0.0, end=10.0),
            SectionOccurrence(section="Final Chorus", occurrence=1, start=10.0, end=13.0),
            SectionOccurrence(section="Outro", occurrence=1, start=13.0, end=23.0),
        ]
        result = compile_density(sections, 120.0)
        assert not [row for row in result.sequence if row["trigger"] == "드롭 직전의 정적"]

    def test_not_inserted_when_outro_not_preceded_by_final_chorus(self) -> None:
        # Too Cool 실측 — Outro(2:50) 직전은 Verse6(2:44~2:50) 이다(n/a).
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        assert not [row for row in result.sequence if row["trigger"] == "드롭 직전의 정적"]


class TestPhraseLayerLimit:
    """REQ-039 — 프레이즈 큐는 레이어 1~2개만 바꾼다(REQ-018 상한 검사를
    통해 확인한다)."""

    def test_compiled_rows_never_warn(self) -> None:
        for raw, bpm in ((RAIN_RAW, RAIN_BPM), (TOO_COOL_RAW, TOO_COOL_BPM)):
            result = compile_density(_remap(raw), bpm)
            assert result.warnings == ()

    def test_phrase_rows_touch_at_most_two_layers(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        for row in result.sequence:
            if row["kind"] == "phrase":
                assert layer_limit_warning("phrase", row["layers"]) is None
                assert 1 <= len(row["layers"]) <= 2

    def test_layer_limit_warning_fires_on_a_deliberately_oversized_phrase(self) -> None:
        # cue_model.layer_limit_warning 자체가 상한만 검사한다는 계약을
        # 이 모듈이 실제로 쓰고 있음을 직접 확인한다 — 5개 레이어는
        # 프레이즈 큐 상한(2)을 넘는다.
        oversized = frozenset(
            {"visibility", "environment", "architecture", "motion", "punctuation"}
        )
        warning = layer_limit_warning("phrase", oversized)
        assert warning is not None


class TestOneShotLane:
    """REQ-040 — 원샷은 시퀀스 큐 목록과 분리된 별도 레인이다."""

    def test_one_shots_are_valid_vocabulary_and_separate_from_sequence(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        assert result.one_shots
        one_shot_names = {row["shot"] for row in result.one_shots}
        assert one_shot_names <= set(ONE_SHOTS)
        # 시퀀스 큐 어디에도 원샷 이름이 trigger 로 나타나지 않는다 —
        # 원샷은 별도 레인이다(evidence/headroom 계산 대상 밖).
        sequence_triggers = {row["trigger"] for row in result.sequence}
        assert not (one_shot_names & sequence_triggers)

    def test_one_shots_excluded_from_g13_count(self) -> None:
        # Too Cool 은 시퀀스 큐만으로 10~45 범위 안이지만, 원샷(13개)을
        # 잘못 더하면 45 를 넘어 경고가 난다 — "제외됐다"를 카운트로
        # 직접 증명한다(공허한 단언 방지).
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        sequence_only = g13_density_warning(len(result.sequence))
        miscounted = g13_density_warning(len(result.sequence) + len(result.one_shots))
        assert sequence_only is None
        assert miscounted is not None


class TestG13DensityWarning:
    """REQ-041/G13 — 시퀀스 큐 10~45 범위, 경고만(조립을 막지 않는다)."""

    @pytest.mark.parametrize(
        ("count", "expect_warning"),
        [(9, True), (10, False), (45, False), (46, True), (0, True)],
    )
    def test_boundary(self, count: int, expect_warning: bool) -> None:
        warning = g13_density_warning(count)
        assert (warning is not None) == expect_warning

    def test_rain_and_too_cool_sequence_counts(self) -> None:
        for raw, bpm in ((RAIN_RAW, RAIN_BPM), (TOO_COOL_RAW, TOO_COOL_BPM)):
            result = compile_density(_remap(raw), bpm)
            # 둘 다 실측 8곡 분포(13~44) 안에 있어야 정상이다 — 벗어나면
            # 이 시험이 먼저 잡아야 한다.
            assert 10 <= len(result.sequence) <= 45


class TestDistributeMotionSteps:
    """REQ-044 — 모션 단계는 후렴 총수에 비례하고, 마지막 회차 이전에
    최대치에 도달하지 않는다."""

    def test_empty_when_no_chorus(self) -> None:
        assert distribute_motion_steps(0) == ()

    def test_single_chorus_gets_max(self) -> None:
        assert distribute_motion_steps(1) == (3,)

    @pytest.mark.parametrize("total", [2, 3, 4, 5, 6, 7, 13])
    def test_last_is_max_and_never_reached_before_last(self, total: int) -> None:
        steps = distribute_motion_steps(total)
        assert len(steps) == total
        assert steps[-1] == 3
        assert all(step < 3 for step in steps[:-1])

    def test_monotonic_non_decreasing(self) -> None:
        steps = distribute_motion_steps(13)
        assert all(a <= b for a, b in zip(steps, steps[1:], strict=False))


class TestChorusPhraseCap:
    """REQ-045 — 4회차 이후 후렴당 프레이즈 큐 최대 1개
    (AC-LDDESIGN-033)."""

    def test_too_cool_13_choruses_capped_from_round_4(self) -> None:
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        states = resolve_sequence(result.sequence)
        from server.concept.escalation import build_chorus_snapshots

        snapshots = build_chorus_snapshots(result.sequence, states, total_groups=len(GROUP_ROSTER))
        assert len(snapshots) == 13
        for snapshot in snapshots:
            if snapshot.round_number >= 4:
                assert snapshot.phrase_density <= 1
        # 상한이 실제로 4회차부터만 걸린다는 것도 함께 보인다(공허한
        # 단언이 아님) — 2·3회차 중 적어도 하나는 1개를 넘는다.
        assert any(s.phrase_density > 1 for s in snapshots if s.round_number < 4)


class TestBridgeCue:
    """REQ-046 — Bridge 큐는 KEY·BACK 을 제외한 그룹을 전부 끄고, 남은
    그룹은 30% 로 축소한다."""

    def test_bridge_removes_everything_but_key_and_back(self) -> None:
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        states = resolve_sequence(result.sequence)
        for row, state in zip(result.sequence, states, strict=True):
            if row["section"] == "Bridge" and row["kind"] == "section":
                on = {role for role, value in state.dim.items() if value > 0}
                assert on == {"KEY", "BACK"}
                assert state.dim["KEY"] == 30
                assert state.dim["BACK"] == 30

    def test_bridge_cue_ops_shape(self) -> None:
        # ops 자체가 remove(비-KEY/BACK) + expand(KEY/BACK, 30) 임을
        # 직접 확인한다 — 상태만 보면 "우연히 30" 인지 구분이 안 된다.
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        bridge_rows = [
            r for r in result.sequence if r["section"] == "Bridge" and r["kind"] == "section"
        ]
        assert bridge_rows
        for row in bridge_rows:
            remove_ops = [op for op in row["ops"] if op["op"] == "remove"]
            expand_ops = [op for op in row["ops"] if op["op"] == "expand"]
            assert remove_ops and set(remove_ops[0]["roles"]) == set(GROUP_ROSTER) - {"KEY", "BACK"}
            assert expand_ops and set(expand_ops[0]["roles"]) == {"KEY", "BACK"}
            assert expand_ops[0]["dimmer"] == 30


class TestVerseBrightnessShape:
    """AC-LDDESIGN-010 — 절 2회차 이후는 같은 최대 밝기를 갖는다(REQ-021
    의 "구간 자신의 1회차 값" 기준 참조를 density.py 가 올바르게
    씁니다 — 직전 트래킹 값 기준이었다면 절마다 값이 달라졌을 것이다).
    """

    def test_rain_verses_2_plus_share_top_brightness(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        states = resolve_sequence(result.sequence)
        verse_tops = [
            max(state.dim.values(), default=0)
            for row, state in zip(result.sequence, states, strict=True)
            if row["section"] == "Verse" and row["kind"] == "section"
        ]
        assert len(verse_tops) == 4
        first, rest = verse_tops[0], verse_tops[1:]
        assert len(set(rest)) == 1
        assert rest[0] != first

    def test_verse_first_occurrence_clears_prior_mover_and_wash_state(self) -> None:
        # 회귀 방지 — Verse occurrence==1 이 remove 를 빠뜨리면 직전
        # 후렴의 WASH/MOVER 디머가 그대로 새어 들어와 밝기가 45 가 아니라
        # 훨씬 큰 값으로 나온다.
        sections = _remap(TOO_COOL_RAW)
        result = compile_density(sections, TOO_COOL_BPM)
        states = resolve_sequence(result.sequence)
        for row, state in zip(result.sequence, states, strict=True):
            if row["section"] == "Verse" and row["occurrence"] == 1 and row["kind"] == "section":
                assert max(state.dim.values(), default=0) == 45
                assert not (frozenset(MOVER_GROUPS) & {r for r, v in state.dim.items() if v > 0})


class TestColorForCallback:
    """REQ-017/030 — 색은 M3 스코프다. 콜백이 없으면 색 동작을 내지
    않고, 콜백이 있으면 그 값을 그대로 반영한다."""

    def test_default_emits_no_color_op(self) -> None:
        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM)
        for row in result.sequence:
            assert not [op for op in row["ops"] if op["op"] == "replace"]

    def test_callback_result_is_used_verbatim(self) -> None:
        calls: list[tuple[str, int]] = []

        def color_for(section: str, occurrence: int) -> str | None:
            calls.append((section, occurrence))
            if section == "Intro":
                return "파랑"
            return None

        sections = _remap(RAIN_RAW)
        result = compile_density(sections, RAIN_BPM, color_for=color_for)
        intro_row = next(row for row in result.sequence if row["section"] == "Intro")
        replace_ops = [op for op in intro_row["ops"] if op["op"] == "replace"]
        assert replace_ops == [{"op": "replace", "color": "파랑"}]
        assert ("Intro", 1) in calls
