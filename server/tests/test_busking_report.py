"""M3 — 집계 보고 계층 (AC-BUSKWIZ-008).

SPEC-COPILOT-BUSKWIZ-001 REQ-BUSKWIZ-013 / -015.

보고 요소 5종 (a) 생성 · (b) 미매핑 역할 · (c) 건너뜀 · (d) 룩별 판정 ·
(e) 미실행. 집계만 내고 룩별을 생략하는 것은 금지 — 51~87 커맨드 중 어느 룩이
죽었는지 사용자가 알 수 없게 된다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from server.looks.busking import build_genre_bundle, looks_for_genre
from server.looks.instantiate import resolve_pools
from server.looks.loader import load_library_from_dir
from server.looks.report import (
    COMPLETE,
    MATCH_VERDICT,
    NONE,
    PARTIAL,
    SECTION_FAILURE,
    build_report,
    to_korean,
)
from server.looks.resolver import resolve_roles
from server.tests.busking_fixtures import (
    FULL_RIG,
    capped_pools,
    make_bundle,
    make_look,
    pools_without,
)

_REPORT_MODULE = Path("server/looks/report.py")

# plan-phase 실측을 본 테스트가 **직접 재측정**해 기대값으로 쓴다.
#
# 2026-09-06 갱신 — SPEC-COPILOT-D1GRANT-001 이 rock·edm 에 dynamics 1 룩을 하나씩
# 더했다. 두 룩 모두 역할이 **하나뿐**이므로(`rock-wing-embers` = 사이드,
# `edm-haze-shafts` = 백라이트) 쌍 수는 각각 +1 이다: rock 26→27, edm 26→27.
# worship·ballad 는 안 움직인다.
# 자산에서 잰 `(룩, 역할)` 쌍 수. 2026-09-12 카드 t359 가 움직이는 룩 열다섯에
# `무버` 역할을 더하면서 넷 다 늘었다 (worship 25→27 · rock 27→32 · ballad 20→21 ·
# edm 27→34).
# 2026-09-13 갱신 — 카드 t379 가 리그 커버리지 결손(워시·헤이즈 그룹 미매핑)을
# 메우면서 룩마다 역할을 하나씩 더 얹었다: worship +1(워시) 27→28 ·
# rock +2(워시·헤이즈) 32→34 · ballad +1(워시) 21→22 · edm +2(워시·헤이즈) 34→36.
# 이 표는 인용이 아니라 **재측정값**이고, 그래서 아래 검사가 자산에 대고
# 다시 세어 맞춰 본다 — 표만 고치고 자산이 안 바뀌면 그 자리에서 빨개진다.
_PAIR_COUNTS = {"worship": 28, "rock": 34, "ballad": 22, "edm": 36}

# 장르별 distinct 역할 종수. t379 전에는 넷 다 7종(위치 6 + 무버)으로 같았다 —
# t379 가 워시를 네 장르 모두에 붙이고 헤이즈는 "빔을 보이게 하는" 캐논 근거가
# 있는 edm·rock 에만 붙여서, 이제 장르마다 다르다(worship·ballad 는 워시만 +1 →
# 8종, edm·rock 은 워시+헤이즈 +2 → 9종). 그래서 이 표도 `_PAIR_COUNTS` 처럼
# 장르별 dict 로 바꾼다 — 하나의 정수로는 이 비대칭을 표현할 수 없다.
_DISTINCT_ROLES = {"worship": 8, "rock": 9, "ballad": 8, "edm": 9}


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


class _Outcome:
    """`CommandOutcome`의 최소 대역 — status만 본다."""

    def __init__(self, status: str) -> None:
        self.status = status


def _all_ok(bundle) -> list[_Outcome]:
    return [_Outcome("executed_ok") for _ in bundle.commands]


# -- (a) 생성 목록 --------------------------------------------------------------


class TestCreatedListing:
    def test_every_created_preset_is_listed_with_pool_slot_and_label(self):
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("Dimmer", 80), ("ColorRGB_R", 100))),
                make_look("b", "룩 B", attrs=(("Dimmer", 70), ("ColorRGB_R", 90))),
            ]
        )
        report = build_report(bundle, _all_ok(bundle))
        assert len(report.created) == bundle.created_count == 4
        for preset in report.created:
            assert preset.pool is not None
            assert preset.slot is not None
            assert preset.label


# -- (b) 미매핑 역할 ------------------------------------------------------------


class TestUnmappedRoles:
    def test_pairs_are_counted_per_look_not_distinct(self, library):
        """(b)의 집계 단위는 `(룩, 역할)` 쌍이다.

        리그를 1회만 해석하므로 하나의 미매핑 역할이 그것을 선언한 모든 룩에서
        반복된다. distinct 역할 수로 세면 룩별 합계와 어긋나 구간 1이 깨진다.
        """
        for genre, expected in sorted(_PAIR_COUNTS.items()):
            looks = looks_for_genre(library, genre)
            # 이 테스트의 기대값을 자산에서 재측정한다 — 인용하지 않는다.
            assert sum(len(look.roles) for look in looks) == expected
            bundle = make_bundle(looks, groups=((99, "관계 없는 그룹"),))
            report = build_report(bundle, _all_ok(bundle))
            assert report.unmapped_count == expected
            assert len(report.unmapped_roles) == _DISTINCT_ROLES[genre], (
                f"{genre} 의 distinct 는 {_DISTINCT_ROLES[genre]}종이어야 한다"
            )

    def test_a_single_unmapped_role_can_contribute_many_pairs(self, library):
        # 역할 하나만 미매핑이어도 쌍 카운트는 1이 아니다.
        looks = looks_for_genre(library, "rock")
        contributions = {}
        for look in looks:
            for role in look.roles:
                contributions[role] = contributions.get(role, 0) + 1
        # 2026-09-06 — SPEC-COPILOT-D1GRANT-001 의 `rock-wing-embers` 가 `사이드`
        # 를 유일한 역할로 들고 오면서 7→8. 경계 케이스의 성질(단일 역할 하나가
        # 1 이 아니라 여러 쌍을 낸다)은 그대로다.
        assert max(contributions.values()) == 8, "rock `사이드` 8룩 — 경계 케이스"

    def test_match_verdicts_and_section_failures_are_separate_kinds(self, library):
        # 매칭 판정 3종과 섹션 실패 전파는 서로 다른 사실이다 — 합치지 않는다.
        looks = looks_for_genre(library, "ballad")[:2]

        mapped_none = make_bundle(looks, groups=((99, "관계 없는 그룹"),))
        verdicts = build_report(mapped_none, _all_ok(mapped_none))
        assert {u.kind for u in verdicts.unmapped} == {MATCH_VERDICT}

        broken = build_genre_bundle(
            "ballad",
            tuple(looks),
            resolution=resolve_roles({"reason": "path_not_resolved"}),
            pools=resolve_pools({"reason": "path_not_resolved"}),
        )
        section = build_report(broken, [])
        assert {u.kind for u in section.unmapped} == {SECTION_FAILURE}
        assert {u.reason for u in section.unmapped} == {"path_not_resolved"}

    def test_a_section_failure_is_never_reported_as_no_match(self):
        broken = build_genre_bundle(
            "rock",
            (make_look("a", "룩 A"),),
            resolution=resolve_roles({"reason": "console_unreachable"}),
            pools=resolve_pools({"reason": "console_unreachable"}),
        )
        report = build_report(broken, [])
        assert all(u.kind == SECTION_FAILURE for u in report.unmapped)
        assert "no_match" not in {u.reason for u in report.unmapped}


# -- (c) 건너뜀 -----------------------------------------------------------------


class TestSkippedUnit:
    def test_the_unit_is_one_preset_store_not_one_look(self):
        # 한 룩에서 두 풀이 건너뛰어지면 카운트는 1이 아니라 2다.
        bundle = make_bundle(
            [make_look("a", "룩 A", attrs=(("Dimmer", 80), ("ColorRGB_R", 100)))],
            pools=pools_without("Dimmer", "Color"),
        )
        report = build_report(bundle, _all_ok(bundle))
        assert len(report.looks) == 1
        assert report.skipped_count == 2
        assert report.looks[0].skipped == 2


# -- (d) 룩별 판정 --------------------------------------------------------------


class TestPerLookVerdict:
    def test_every_look_appears_exactly_once(self, library):
        looks = looks_for_genre(library, "worship")
        bundle = make_bundle(looks)
        report = build_report(bundle, _all_ok(bundle))
        assert [v.look_id for v in report.looks] == [look.look_id for look in looks]
        assert len(report.looks) == len({v.look_id for v in report.looks}) == len(looks)

    def test_verdicts_are_the_closed_three(self, library):
        bundle = make_bundle(looks_for_genre(library, "edm"))
        report = build_report(bundle, _all_ok(bundle))
        assert {v.verdict for v in report.looks} <= {COMPLETE, PARTIAL, NONE}

    def test_a_clean_look_is_complete(self):
        bundle = make_bundle([make_look("a", "룩 A")])
        report = build_report(bundle, _all_ok(bundle))
        assert report.looks[0].verdict == COMPLETE

    def test_a_look_with_no_store_is_none(self):
        bundle = make_bundle([make_look("a", "룩 A")], groups=((99, "관계 없는 그룹"),))
        report = build_report(bundle, [])
        assert report.looks[0].verdict == NONE
        assert report.looks[0].created == 0

    def test_a_partially_stored_look_is_partial(self):
        bundle = make_bundle(
            [make_look("a", "룩 A", attrs=(("Dimmer", 80), ("ColorRGB_R", 100)))],
            pools=pools_without("Color"),
        )
        report = build_report(bundle, _all_ok(bundle))
        assert report.looks[0].created == 1
        assert report.looks[0].skipped == 1
        assert report.looks[0].verdict == PARTIAL


# -- (e) 미실행 -----------------------------------------------------------------


class TestNotExecutedIsSeparate:
    """(c)와 (e)를 합산하지 않는다 — 원인도 조치도 다르다."""

    def _bundle_and_outcomes(self):
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("Dimmer", 80),)),
                make_look("b", "룩 B", attrs=(("Dimmer", 70),)),
            ]
        )
        # 두 번째 룩 구간의 첫 줄에서 실패 → 그 뒤 전량 not_executed
        second_start = bundle.spans[1][0]
        statuses = ["executed_ok"] * second_start
        statuses.append("failed")
        statuses += ["not_executed"] * (len(bundle.commands) - len(statuses))
        return bundle, [_Outcome(s) for s in statuses]

    def test_not_executed_is_its_own_count(self):
        bundle, outcomes = self._bundle_and_outcomes()
        report = build_report(bundle, outcomes)
        assert report.not_executed > 0
        assert report.skipped_count == 0, "이 픽스처에는 빌드 시점 건너뜀이 없다"

    def test_the_two_numbers_are_never_summed(self):
        bundle, outcomes = self._bundle_and_outcomes()
        report = build_report(bundle, outcomes)
        rendered = to_korean(report)
        # 렌더된 숫자를 **직접 뽑아** 대조한다. "합계 문자열이 없다"는 형태의
        # 단언은 렌더 포맷이 조금만 달라도 아무것도 검사하지 않는다 —
        # 실제로 이 테스트의 첫 판은 그래서 합산 뮤테이션을 놓쳤다.
        skipped_shown = int(re.search(r"건너뜀 (\d+)개", rendered).group(1))
        not_executed_shown = int(re.search(r"미실행 (\d+)개", rendered).group(1))
        assert skipped_shown == report.skipped_count
        assert not_executed_shown == report.not_executed
        assert report.not_executed > 0, "미실행이 0이면 합산 여부를 가릴 수 없다"
        assert skipped_shown != report.skipped_count + report.not_executed, (
            "두 수를 한 칸에 합치면 사용자가 조치를 고를 수 없다"
        )

    def test_the_interrupted_look_is_not_complete(self):
        bundle, outcomes = self._bundle_and_outcomes()
        report = build_report(bundle, outcomes)
        assert report.looks[0].verdict == COMPLETE
        assert report.looks[1].verdict != COMPLETE
        assert report.looks[1].not_executed > 0

    def test_plan_only_report_does_not_claim_execution(self):
        bundle = make_bundle([make_look("a", "룩 A")])
        report = build_report(bundle)
        assert report.executed is False
        assert report.not_executed == 0

    def test_no_automatic_retry_path_exists(self):
        tree = ast.parse(_REPORT_MODULE.read_text(encoding="utf-8"))
        identifiers = (
            {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            | {
                n.name
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            }
            | {
                alias.asname or alias.name
                for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom | ast.Import)
                for alias in n.names
            }
        )
        assert identifiers, "AST에서 식별자를 하나도 모으지 못했다"
        # 비공허성: 정의 이름까지 보는지 확인한다 — 그래야 `def retry(...)`도 잡힌다.
        assert {"build_report", "to_korean"} <= identifiers
        assert {"execute", "run_commands", "retry", "resend"} & identifiers == set()


# -- 산술 정합 ------------------------------------------------------------------


class TestAggregateArithmetic:
    """구간 1 — 집계가 룩별 합계와 어긋나면 실패다."""

    @pytest.mark.parametrize("genre", sorted(_PAIR_COUNTS))
    def test_aggregates_equal_the_per_look_sums(self, library, genre):
        bundle = make_bundle(looks_for_genre(library, genre))
        report = build_report(bundle, _all_ok(bundle))
        assert report.created_count == sum(v.created for v in report.looks)
        assert report.skipped_count == sum(v.skipped for v in report.looks)
        assert report.unmapped_count == sum(v.unmapped for v in report.looks)
        assert report.not_executed == sum(v.not_executed for v in report.looks)

    def test_distinct_role_count_would_break_the_arithmetic(self, library):
        # 이 규칙이 왜 필요한지 고정한다 — distinct로 세면 합계가 어긋난다.
        bundle = make_bundle(looks_for_genre(library, "worship"), groups=((99, "무관"),))
        report = build_report(bundle, _all_ok(bundle))
        assert report.unmapped_count == _PAIR_COUNTS["worship"]
        assert len(report.unmapped_roles) == _DISTINCT_ROLES["worship"]
        assert report.unmapped_count != len(report.unmapped_roles)


# -- 한국어 1급 -----------------------------------------------------------------


class TestKoreanFirstClass:
    def test_the_summary_is_korean(self, library):
        bundle = make_bundle(looks_for_genre(library, "ballad"))
        rendered = to_korean(build_report(bundle, _all_ok(bundle)))
        assert "생성" in rendered
        assert "건너뜀" in rendered
        assert any("\uac00" <= ch <= "\ud7a3" for ch in rendered)

    def test_every_reason_code_has_a_korean_label(self):
        from server.looks.busking import VALUE_LINE_COLLISION
        from server.looks.instantiate import (
            CONFLICT,
            NO_FREE_SLOT,
            POOL_UNADDRESSABLE,
            POOL_UNRESOLVED,
        )
        from server.looks.report import reason_label
        from server.looks.resolver import UNADDRESSABLE
        from server.looks.roles import AMBIGUOUS, NO_MATCH

        for code in (
            CONFLICT,
            NO_FREE_SLOT,
            POOL_UNRESOLVED,
            POOL_UNADDRESSABLE,
            AMBIGUOUS,
            NO_MATCH,
            UNADDRESSABLE,
            VALUE_LINE_COLLISION,
        ):
            label = reason_label(code)
            assert label and label != code, f"{code}에 한국어 라벨이 없다"

    def test_an_unknown_reason_is_passed_through_not_invented(self):
        from server.looks.report import reason_label

        assert reason_label("path_not_resolved_xyz") == "path_not_resolved_xyz"

    def test_the_mapping_lives_in_code_not_in_the_assets(self, library):
        # REQ-BUSKWIZ-015 — 룩 자산·스키마에 한국어 필드를 추가하지 않는다.
        for look in library.looks:
            assert not hasattr(look, "label_ko")
            assert not hasattr(look, "korean")


# -- 상한 신호 전파 -------------------------------------------------------------


class TestDrilldownCappedPropagates:
    def test_the_cap_signal_reaches_the_report(self):
        bundle = make_bundle([make_look("a", "룩 A")], pools=capped_pools())
        report = build_report(bundle, _all_ok(bundle))
        assert report.drilldown_capped is True

    def test_an_uncapped_run_says_so(self):
        bundle = make_bundle([make_look("a", "룩 A")])
        report = build_report(bundle, _all_ok(bundle))
        assert report.drilldown_capped is False


# -- (e) 역할 미부여 그룹 — 미매핑의 반대 방향 (t356) ----------------------------


class TestUnmatchedGroupsReachTheReport:
    """리그에 있는데 아무 역할도 안 부른 그룹은 보고까지 올라와야 한다.

    `unmapped`/`unmapped_roles` 는 「룩이 부른 역할에 그룹이 없다」이고, 이쪽은
    「그룹이 있는데 아무도 안 부른다」다. 조치가 다르므로 접지 않는다 — 전자는
    그룹을 만드는 일, 후자는 어휘를 넓히거나 쇼 별칭을 다는 일이다.
    """

    def test_a_group_no_role_claims_is_carried_into_the_report(self, library):
        looks = looks_for_genre(library, "ballad")[:1]
        bundle = make_bundle(looks, groups=((11, "Back Wash"), (99, "Zorblax Array")))
        report = build_report(bundle, _all_ok(bundle))
        assert report.unmatched_groups == ("Zorblax Array",)
        assert "Zorblax Array" in report.to_dict()["unmatched_groups"]

    def test_the_korean_summary_names_it(self, library):
        looks = looks_for_genre(library, "ballad")[:1]
        bundle = make_bundle(looks, groups=((11, "Back Wash"), (99, "Zorblax Array")))
        text = to_korean(build_report(bundle, _all_ok(bundle)))
        assert "역할 미부여 그룹 1개" in text
        assert "Zorblax Array" in text

    def test_a_fully_named_rig_reports_none_and_prints_no_line(self, library):
        # 비공허성 — 위 두 검사가 항상 참인 문자열을 재는 것이 아님을 보인다.
        looks = looks_for_genre(library, "ballad")[:1]
        bundle = make_bundle(looks, groups=FULL_RIG)
        report = build_report(bundle, _all_ok(bundle))
        assert report.unmatched_groups == ()
        assert "역할 미부여 그룹" not in to_korean(report)
