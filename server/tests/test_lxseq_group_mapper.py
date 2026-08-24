"""SPEC-COPILOT-LXSEQ-002 M2 — GROUP 매퍼 (RED 먼저).

AC-LXSEQ2-005  닫힌 어휘 밖 이름은 unknown_group_name 으로 건너뛴다.
AC-LXSEQ2-006  기본 12종의 멤버는 패치 라벨 표에서 온다.
AC-LXSEQ2-007  파생 6종의 멤버는 코드의 닫힌 규칙에서 온다.
AC-LXSEQ2-008  Members 개수는 교차검증에만 쓴다.
AC-LXSEQ2-009  콘솔에 없는 FID 는 안 넣는다. 실측이 전수 아니면 0배치.
AC-LXSEQ2-010  측정 슬롯이 시트 GroupNo 와 어긋나면 0배치 + 대조표.
AC-LXSEQ2-011  배치는 기본 12 먼저, 파생 6 나중.
AC-LXSEQ2-012  발화 전 줄 단위 바이트 예산.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from server.lxseq.group_mapper import (
    DERIVED_GROUP_NAMES,
    build_label_fid_table,
    map_groups,
    measure_command_bytes,
)
from server.lxseq.group_parser import parse_group_csv

GROUP_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")
PATCH_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")


def _patch_rows() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(PATCH_CSV.read_text(encoding="utf-8-sig"))))


def _group_records():
    return parse_group_csv(GROUP_CSV.read_text(encoding="utf-8")).records


def _all_fids() -> list[int]:
    return sorted(int(row["FID"]) for row in _patch_rows())


def _empty_pool() -> dict[str, object]:
    """그룹 0개인 풀 단면 — 오늘 실측된 상태(childCount 0)."""
    return dict(objects=[], truncated=False)


def _pool_with(*slots: int) -> dict[str, object]:
    return dict(objects=[dict(no=n, name="기존" + str(n)) for n in slots], truncated=False)


def _map(**overrides):
    kwargs = dict(
        group_records=_group_records(),
        patch_rows=_patch_rows(),
        console_fids=_all_fids(),
        console_fids_complete=True,
        groups_section=_empty_pool(),
    )
    kwargs.update(overrides)
    return map_groups(**kwargs)


class TestLabelTable:
    """AC-LXSEQ2-006 — 기본 12종의 멤버는 패치 라벨 표에서 온다."""

    EXPECTED = dict(
        BACK=12,
        BLIND=6,
        FOH=8,
        HAZE=2,
        KEY=6,
        MOVER_D=8,
        MOVER_U=8,
        SIDE_L=6,
        SIDE_R=6,
        STROBE=4,
        WASH_D=10,
        WASH_U=10,
    )

    def test_table_counts_match_the_canonical_patch(self):
        table = build_label_fid_table(_patch_rows())
        counts = dict()
        for label, fids in table.items():
            counts[label.replace("-", "_")] = len(fids)
        assert counts == self.EXPECTED
        assert sum(counts.values()) == 86

    def test_no_fid_belongs_to_two_base_labels(self):
        table = build_label_fid_table(_patch_rows())
        seen: set[int] = set()
        for fids in table.values():
            overlap = seen.intersection(fids)
            assert overlap == set(), f"두 라벨에 걸친 FID: {sorted(overlap)}"
            seen.update(fids)
        assert len(seen) == 86

    def test_fids_are_sorted_within_a_label(self):
        """선택 줄의 순서가 곧 방향이다 — 재정렬하면 안 되므로 표에서 정렬해 낸다."""
        table = build_label_fid_table(_patch_rows())
        for label, fids in table.items():
            assert list(fids) == sorted(fids), label

    def test_a_gapped_fid_block_separates_the_table_from_arithmetic(self):
        """멤버십의 **출처**를 가르는 검사.

        정본 쇼파일에서는 FID_BASE 산술과 라벨 표가 **같은 값**을 내므로
        정본만으로는 출처를 못 가른다(뮤테이션 ⑨가 안 갈렸다). 실제로
        가르려면 둘이 어긋나는 입력이 필요하다 — 번호가 끊긴 블록이다.

        산술은 시작 번호에 순번을 더하므로 101..106 을 내고, 라벨 표는
        패치가 실제로 적은 101,102,104,105,106,107 을 낸다.
        """
        gapped = [dict(FID=str(f), Group="KEY") for f in (101, 102, 104, 105, 106, 107)]
        table = build_label_fid_table(gapped)
        assert table["KEY"] == (101, 102, 104, 105, 106, 107)
        assert table["KEY"] != tuple(range(101, 107)), "산술이면 이 값이 나온다"

    def test_base_buckets_use_the_table_not_arithmetic(self):
        """FID_BASE 산술과 라벨 표가 이 쇼파일에서 같은 값을 낸다 —
        그래서 이 검사만으로는 출처를 못 가른다. 출처는 뮤테이션 ⑨가 가른다.
        여기서는 결과값만 못박는다."""
        result = _map()
        by_name = dict((b.name, b.fids) for batch in result.batches for b in batch.buckets)
        assert by_name["KEY"] == (101, 102, 103, 104, 105, 106)
        assert by_name["HAZE"] == (621, 622)


class TestDerivedRules:
    """AC-LXSEQ2-007 — 파생 6종은 코드의 닫힌 규칙에서 온다."""

    def test_the_closed_vocabulary_is_exactly_six(self):
        assert sorted(DERIVED_GROUP_NAMES) == [
            "ALL",
            "EVEN",
            "MOVER-ALL",
            "ODD",
            "SIDE-ALL",
            "WASH-ALL",
        ]

    def test_derived_membership_is_exact(self):
        result = _map()
        by_name = dict((b.name, b.fids) for batch in result.batches for b in batch.buckets)

        assert len(by_name["ALL"]) == 86
        assert by_name["SIDE-ALL"] == tuple(range(301, 307)) + tuple(range(311, 317))
        assert len(by_name["WASH-ALL"]) == 20
        assert by_name["MOVER-ALL"] == tuple(range(501, 509)) + tuple(range(521, 529))
        assert by_name["ODD"] == (501, 503, 505, 507, 521, 523, 525, 527)
        assert by_name["EVEN"] == (502, 504, 506, 508, 522, 524, 526, 528)

    def test_odd_and_even_partition_mover_all(self):
        result = _map()
        by_name = dict((b.name, b.fids) for batch in result.batches for b in batch.buckets)
        odd, even, both = set(by_name["ODD"]), set(by_name["EVEN"]), set(by_name["MOVER-ALL"])
        assert odd | even == both
        assert odd & even == set()

    def test_all_carries_no_follow_fixture(self):
        """FOLLOW 는 패치 CSV 에 없다 — 별도 제외 논리가 아니라 입력의 성질이다."""
        result = _map()
        by_name = dict((b.name, b.fids) for batch in result.batches for b in batch.buckets)
        assert 631 not in by_name["ALL"]
        assert set(by_name["ALL"]) == set(_all_fids())


class TestSkips:
    """AC-LXSEQ2-005 · 008 · 009 — 건너뛰기 세 부류."""

    def test_unknown_group_name_is_skipped_not_guessed(self):
        records = list(_group_records())
        from dataclasses import replace

        records.append(replace(records[0], group_no=19, name="SPECIAL-X"))
        result = _map(group_records=tuple(records))
        kinds = [s.kind for s in result.skipped]
        assert kinds == ["unknown_group_name"]
        assert result.skipped[0].name == "SPECIAL-X"
        names = [b.name for batch in result.batches for b in batch.buckets]
        assert "SPECIAL-X" not in names
        assert len(names) == 18, "나머지 18개는 살아야 한다 (비공허성)"

    def test_member_count_mismatch_is_skipped(self):
        from dataclasses import replace

        records = list(_group_records())
        idx = next(i for i, r in enumerate(records) if r.name == "KEY")
        records[idx] = replace(records[idx], members_raw="KEY 7대")
        result = _map(group_records=tuple(records))
        assert [s.kind for s in result.skipped] == ["member_count_mismatch"]
        assert "6" in result.skipped[0].detail and "7" in result.skipped[0].detail

    def test_rows_without_a_count_are_not_cross_checked(self):
        """SIDE-ALL 의 Members 에는 개수가 없다 — 대조 대상이 아니다."""
        result = _map()
        assert [s.kind for s in result.skipped] == []
        names = [b.name for batch in result.batches for b in batch.buckets]
        assert "SIDE-ALL" in names

    def test_fid_absent_from_console_is_filtered_out(self):
        """개수 대조를 안 받는 행으로 격리해서 FID 여과만 잰다.

        Members 를 비우면 그 행은 교차검증 대상이 아니므로(위 검사),
        FID 여과의 효과만 관측된다.
        """
        from dataclasses import replace

        records = tuple(replace(r, members_raw="") for r in _group_records())
        console = [f for f in _all_fids() if f != 205]
        result = _map(group_records=records, console_fids=console)
        by_name = dict((b.name, b.fids) for batch in result.batches for b in batch.buckets)
        assert 205 not in by_name["BACK"]
        assert 205 not in by_name["ALL"]
        assert len(by_name["BACK"]) == 11
        assert len(by_name["ALL"]) == 85

    def test_a_missing_fid_trips_the_count_cross_check(self):
        """격리하지 않으면 개수 대조가 먼저 잡는다 — 그게 그 대조의 값어치다."""
        console = [f for f in _all_fids() if f != 205]
        result = _map(console_fids=console)
        kinds = [s.kind for s in result.skipped]
        assert "member_count_mismatch" in kinds
        assert any(s.name == "BACK" for s in result.skipped)

    def test_incomplete_console_read_yields_zero_batches(self):
        result = _map(console_fids_complete=False)
        assert result.batches == ()
        assert result.console_read_incomplete is True
        # 비공허성 — 같은 입력이 complete=True 면 배치가 나온다.
        assert _map().batches != ()


class TestSlotDivergence:
    """AC-LXSEQ2-010 — 결정 T. 어긋나면 0배치 + 대조표."""

    def test_empty_pool_agrees_with_the_sheet(self):
        result = _map(groups_section=_empty_pool())
        assert result.slot_divergence is None
        assert len(result.batches) == 2

    def test_occupied_slot_diverges_and_yields_zero_batches(self):
        """오늘 풀이 비어 있어 이 경로는 실기로는 안 밟힌다.
        점유 단면을 넣어 **실제로 발동시킨다** — 발동을 못 보고 통과한 것은
        그 요구를 검증한 것이 아니다."""
        result = _map(groups_section=_pool_with(3))
        assert result.batches == ()
        assert result.slot_divergence is not None
        assert result.slot_divergence.sheet_slots[:4] == (1, 2, 3, 4)
        assert result.slot_divergence.measured_slots[:4] == (1, 2, 4, 5)

    def test_no_group_is_renumbered_on_divergence(self):
        result = _map(groups_section=_pool_with(3))
        assert result.batches == ()
        assert [b for batch in result.batches for b in batch.buckets] == []


class TestBatching:
    """AC-LXSEQ2-011 — 기본 12 먼저, 파생 6 나중. 상한 16 이하."""

    def test_batches_follow_groupno_order_not_base_first(self):
        """엔진이 빈 슬롯을 **준 순서대로** 짝지으므로 GroupNo 순서여야 한다.

        「기본 먼저」로 넘기면 18개 전부 번호가 밀린다 — plan-phase 가 그렇게
        적었는데 REQ-009 와 양립하지 않아 구현에서 고쳤다.
        """
        result = _map()
        assert len(result.batches) == 2
        first = [b.group_no for b in result.batches[0].buckets]
        second = [b.group_no for b in result.batches[1].buckets]
        assert first == list(range(1, 17)), "1부터 16까지, 상한이 16이다"
        assert second == [17, 18]
        assert first + second == sorted(first + second)

    def test_a_base_first_order_would_renumber_every_group(self):
        """비공허성 — 왜 GroupNo 순서여야 하는지를 실제로 보인다.

        기본 먼저로 정렬한 순열을 엔진의 빈 슬롯과 짝지으면 시트 번호와
        어긋나는 자리가 나온다. 이 검사가 통과해야 위 검사가 뜻을 갖는다.
        """
        result = _map()
        buckets = [b for batch in result.batches for b in batch.buckets]
        base_first = [b for b in buckets if b.name not in DERIVED_GROUP_NAMES]
        base_first += [b for b in buckets if b.name in DERIVED_GROUP_NAMES]
        assigned = list(range(1, len(base_first) + 1))
        mismatched = [
            b.name for b, slot in zip(base_first, assigned, strict=True) if b.group_no != slot
        ]
        assert mismatched, "기본 먼저가 무해했다면 이 SPEC 의 순서 규칙은 불필요하다"

    def test_no_batch_exceeds_the_engine_cap(self):
        from server.groupgen.write import DEFAULT_GROUP_PLAN_CAP

        result = _map()
        for batch in result.batches:
            assert len(batch.buckets) <= DEFAULT_GROUP_PLAN_CAP

    def test_a_single_combined_batch_would_be_refused_by_the_engine(self):
        """분할이 필요하다는 근거의 비공허성 — 합치면 엔진이 실제로 거부한다."""
        from server.groupgen.write import (
            DEFAULT_GROUP_PLAN_CAP,
            GROUP_PLAN_TOO_LARGE,
            GroupSlotError,
            guard_plan_size,
        )

        result = _map()
        total = sum(len(b.buckets) for b in result.batches)
        assert total == 18
        with pytest.raises(GroupSlotError) as caught:
            guard_plan_size(total, cap=DEFAULT_GROUP_PLAN_CAP)
        assert caught.value.code == GROUP_PLAN_TOO_LARGE
        # 경계 — 16은 통과한다.
        guard_plan_size(DEFAULT_GROUP_PLAN_CAP, cap=DEFAULT_GROUP_PLAN_CAP)


class TestLineByteBudget:
    """AC-LXSEQ2-012 — 결정 N. 발화 전 줄 단위 측정."""

    def test_the_declared_budget_survives_the_real_framing(self):
        """매퍼는 전송층을 임포트할 수 없다 — 그래서 등가성을 **여기서** 잰다.

        `server/lxseq/` 는 `server.bridge` 를 임포트하면 안 된다(001이 세운
        경계, test_lxseq_mapper.py 의 _FORBIDDEN_IMPORTS). 그래서 매퍼는
        프레이밍 여유를 뺀 예산을 **선언**만 하고, 그 선언이 실제 상한·
        프레이밍과 맞는지는 양쪽을 임포트할 수 있는 테스트가 잰다.
        """
        from server.bridge.protocol import MAX_PLUGIN_CALL_BYTES, build_exec_request
        from server.lxseq.group_mapper import DEFAULT_LINE_BYTE_BUDGET
        from server.spatial.choreography import build_spatial_selection_chain

        chain = build_spatial_selection_chain(_all_fids())
        framing = len(build_exec_request("req-0001", chain).encode("utf-8")) - len(
            chain.encode("utf-8")
        )
        assert framing == 42, "프레이밍이 바뀌면 선언된 예산의 여유를 다시 잡아야 한다"
        assert DEFAULT_LINE_BYTE_BUDGET + framing <= MAX_PLUGIN_CALL_BYTES, (
            "예산에 프레이밍을 더한 값이 전송 상한을 넘으면 게이트를 통과한 줄이 조용히 버려진다"
        )

    def test_measure_counts_the_chain_without_framing(self):
        from server.spatial.choreography import build_spatial_selection_chain

        chain = build_spatial_selection_chain(_all_fids())
        assert measure_command_bytes(chain) == len(chain.encode("utf-8"))
        assert measure_command_bytes(chain) == 1201

    def test_all_group_line_is_measured_and_reported(self):
        result = _map()
        by_name = dict((b.name, b) for batch in result.batches for b in batch.buckets)
        assert by_name["ALL"].longest_line_bytes == 1201
        assert all(b.longest_line_bytes > 0 for b in by_name.values())

    def test_the_measured_line_fits_the_transport_ceiling(self):
        from server.bridge.protocol import MAX_PLUGIN_CALL_BYTES

        result = _map()
        widest = max(b.longest_line_bytes for batch in result.batches for b in batch.buckets)
        assert widest == 1201
        assert widest + 42 < MAX_PLUGIN_CALL_BYTES, "프레이밍을 더해도 상한 안이다"

    def test_a_group_over_budget_is_skipped(self):
        """예산을 ALL 아래로 낮추면 ALL 이 빠진다."""
        result = _map(line_byte_budget=1150)
        kinds = [s.kind for s in result.skipped]
        assert kinds == ["line_over_budget"]
        assert result.skipped[0].name == "ALL"
        assert "1201" in result.skipped[0].detail

    def test_skipping_slot_one_breaks_the_prefix_and_yields_zero_batches(self):
        """ALL 은 슬롯 1이다. 빠지면 남은 순열이 2..18 인데 엔진은 1..17 을
        낸다 — 어긋남이 발동하고 아무것도 만들지 않는다.

        이것이 결정 T 의 의도다. 17개를 **틀린 번호로** 쓰느니 0개를 쓴다.
        """
        result = _map(line_byte_budget=1150)
        assert result.batches == ()
        assert result.slot_divergence is not None
        assert result.slot_divergence.sheet_slots[0] == 2
        assert result.slot_divergence.measured_slots[0] == 1

    def test_skipping_the_last_slot_keeps_the_prefix_intact(self):
        """대조 — 꼬리가 빠지면 순열이 안 깨지고 17개가 계획된다.

        「어떤 빠짐이든 0배치」가 아니라 **앞쪽 연속이 깨질 때만** 0배치다.
        이 검사가 없으면 위 검사가 무엇을 재는지 알 수 없다.
        """
        from dataclasses import replace

        records = tuple(
            replace(r, members_raw="EVEN 99대") if r.name == "EVEN" else r for r in _group_records()
        )
        result = _map(group_records=records)
        assert [s.kind for s in result.skipped] == ["member_count_mismatch"]
        assert result.slot_divergence is None
        planned = [b.group_no for batch in result.batches for b in batch.buckets]
        assert planned == list(range(1, 18)), "1부터 17까지 연속이라 어긋나지 않는다"

    def test_default_budget_is_not_larger_than_the_transport_ceiling(self):
        from server.bridge.protocol import MAX_PLUGIN_CALL_BYTES
        from server.lxseq.group_mapper import DEFAULT_LINE_BYTE_BUDGET

        assert DEFAULT_LINE_BYTE_BUDGET <= MAX_PLUGIN_CALL_BYTES


class TestPurityBoundary:
    def test_my_forbidden_set_is_not_weaker_than_the_repo_guard(self):
        """내 스캐너가 저장소가 이미 막던 것을 놓치지 않는지 잰다.

        M2 전량에서 이게 실제로 났다 — 내 순수성 검사는 통과했는데
        `server/tests/test_lxseq_mapper.py` 의 경계 가드가
        `server.bridge.protocol` 임포트를 잡았다. 내 목록이 이름만 보고
        **임포트 경로를 안 봤다.** 저장소 목록을 정본으로 삼아 대조한다.
        """
        from server.tests.test_lxseq_mapper import _FORBIDDEN_IMPORTS, _FORBIDDEN_NAMES

        source = Path("server/lxseq/group_mapper.py").read_text(encoding="utf-8")
        import ast

        offenders: list[str] = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(pre) for pre in _FORBIDDEN_IMPORTS):
                        offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(module.startswith(pre) for pre in _FORBIDDEN_IMPORTS):
                    offenders.append(module)
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
                offenders.append(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_NAMES:
                offenders.append(node.attr)
        assert offenders == []
        # 비공허성 — 저장소 목록이 비어 있으면 위 0건은 아무 뜻이 없다.
        assert len(_FORBIDDEN_IMPORTS) >= 3
        assert "server.bridge" in _FORBIDDEN_IMPORTS

    def test_mapper_names_no_write_surface(self):
        import ast

        FORBIDDEN = ("run_commands", "deploy_pipeline", "execution_port", "state_port", "socket")
        source = Path("server/lxseq/group_mapper.py").read_text(encoding="utf-8")
        names: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.alias):
                names.add(node.name.split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
        # 날조 대조군 먼저 — 스캐너가 실제로 찾는지 증명한 뒤에 0건을 증거로 쓴다.
        planted = "\n".join(
            [
                "from server.bridge import run_commands",
                "def go(port):",
                "    run_commands([])",
                "    port.deploy_pipeline.deploy()",
                "    port.execution_port.fire()",
                "    port.state_port.read()",
                "    import socket",
            ]
        )
        planted_names: set[str] = set()
        for node in ast.walk(ast.parse(planted)):
            if isinstance(node, ast.Name):
                planted_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                planted_names.add(node.attr)
            elif isinstance(node, ast.alias):
                planted_names.add(node.name.split(".")[0])
        assert [f for f in FORBIDDEN if f not in planted_names] == []

        assert [f for f in FORBIDDEN if f in names] == []
        assert "map_groups" in names


class TestSlotMeasurementEquivalence:
    """매퍼의 빈 슬롯 규칙이 엔진의 것과 같은가.

    매퍼는 `server/groupgen/write.py` 의 `measure_empty_slots` 를 부르지
    않는다 — 그 함수는 풀 판독 실패에 예외를 던지고, 이 층은 어긋남을
    **보고**해야지 던지면 안 되기 때문이다. 그래서 같은 규칙을 따로 적었다.

    **둘이 갈리면 아무도 안 본다.** 매퍼가 계획한 슬롯과 엔진이 배정한
    슬롯이 달라지는데, REQ-009 의 대조는 매퍼 안에서만 일어나므로 그
    어긋남을 잡지 못한다. 그래서 등가성을 여기서 잰다.

    **뮤테이션 예고**: 매퍼의 시작 후보를 1이 아니라 0으로 바꾸면 이
    검사가 죽는다고 본다.
    """

    CASES = (
        (),
        (1,),
        (3,),
        (1, 2, 3),
        (2, 4, 6),
        (5, 1, 9),
        tuple(range(1, 17)),
    )

    @pytest.mark.parametrize("occupied", CASES)
    @pytest.mark.parametrize("count", [1, 3, 12, 18])
    def test_both_rules_pick_the_same_empty_slots(self, occupied, count):
        from server.groupgen.write import measure_empty_slots as engine_rule
        from server.lxseq.group_mapper import _measure_empty_slots as mapper_rule

        section = dict(objects=[dict(no=n) for n in occupied], truncated=False)
        assert mapper_rule(section, count) == engine_rule(section, count=count)

    def test_the_two_rules_are_not_the_same_object(self):
        """비공허성 — 같은 함수를 두 이름으로 부르면 위 대조는 자동 참이다."""
        from server.groupgen.write import measure_empty_slots as engine_rule
        from server.lxseq.group_mapper import _measure_empty_slots as mapper_rule

        assert engine_rule is not mapper_rule

    def test_the_engine_raises_where_the_mapper_reports(self):
        """왜 그 함수를 안 부르는지 — 실패 처리가 다르다.

        엔진은 판독 실패에 예외를 던진다. 이 층은 던지면 안 된다.
        """
        from server.groupgen.write import GroupSlotError
        from server.groupgen.write import measure_empty_slots as engine_rule
        from server.lxseq.group_mapper import _measure_empty_slots as mapper_rule

        unreadable = dict(objects=[], truncated=True)
        with pytest.raises(GroupSlotError):
            engine_rule(unreadable, count=1)
        assert mapper_rule(unreadable, 1) == (1,)
