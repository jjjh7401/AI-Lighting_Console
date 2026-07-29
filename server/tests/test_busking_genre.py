"""M1 — 장르 조회 계층 (AC-BUSKWIZ-001, AC-BUSKWIZ-002).

SPEC-COPILOT-BUSKWIZ-001 REQ-BUSKWIZ-001 / -002 / -003.

이 층은 콘솔·리그·게이트 어느 것도 건드리지 않는다. 출하된 라이브러리를
읽기 전용으로 순회할 뿐이므로 전량 인메모리로 검증된다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from server.looks.busking import (
    EMPTY_QUERY,
    UNRESOLVED_GENRE,
    GenreSelection,
    looks_for_genre,
    select_genre,
)
from server.looks.loader import load_library_from_dir

_BUSKING_MODULE = Path("server/looks/busking.py")

# 출하 자산 실측(plan-phase 계수, 2026-07-27). 이 수는 라이브러리 자산의
# 사실이며, 여기 박아 두는 이유는 AC-BUSKWIZ-001 ①이 요구하는 "EDM 9룩이
# 9건 그대로"를 기대값 있는 테스트로 만들기 위해서다.
_EXPECTED_COUNTS = {"worship": 8, "rock": 8, "ballad": 7, "edm": 9}


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


class TestGenreLookupIsComplete:
    """AC-BUSKWIZ-001 — 절단 없는 결정론적 조회."""

    @pytest.mark.parametrize(("genre", "expected"), sorted(_EXPECTED_COUNTS.items()))
    def test_every_genre_returns_its_whole_set(self, library, genre, expected):
        assert len(looks_for_genre(library, genre)) == expected

    def test_edm_nine_looks_survive(self, library):
        # AC-BUSKWIZ-001 ① — 이 한 케이스가 절단 경로 미접촉의 증명이다.
        # matching.MAX_TOOL_MATCHES == 8 이므로 그 경로를 탔다면 9번째가 사라진다.
        from server.looks.matching import MAX_TOOL_MATCHES

        edm = looks_for_genre(library, "edm")
        assert len(edm) == 9
        assert len(edm) > MAX_TOOL_MATCHES

    def test_return_shape_carries_no_truncation_signal(self, library):
        # AC-BUSKWIZ-001 ② — truncated/total 신호가 있다는 것 자체가
        # 절단 가능한 경로를 탔다는 증거다.
        selection = select_genre(library, "워십")
        assert not hasattr(selection, "truncated")
        assert not hasattr(selection, "total")
        assert "truncated" not in vars(selection)

    def test_two_calls_are_equal_including_order(self, library):
        # AC-BUSKWIZ-001 ③
        assert looks_for_genre(library, "rock") == looks_for_genre(library, "rock")

    def test_unknown_genre_slug_returns_empty_not_error(self, library):
        assert looks_for_genre(library, "jazz") == ()

    def test_the_library_is_not_mutated(self, library):
        # REQ-BUSKWIZ-003 — 읽기 전용 순회.
        before = library.looks
        looks_for_genre(library, "edm")
        select_genre(library, "발라드")
        assert library.looks is before


class TestDeterministicTotalOrder:
    """REQ-BUSKWIZ-001 — 다이내믹스 오름차순 → 동률 시 look_id 사전순."""

    @pytest.mark.parametrize("genre", sorted(_EXPECTED_COUNTS))
    def test_order_is_dynamics_then_look_id(self, library, genre):
        looks = looks_for_genre(library, genre)
        keys = [(look.dynamics, look.look_id) for look in looks]
        assert keys == sorted(keys)

    def test_ties_break_on_look_id(self, library):
        # 동률이 실제로 존재해야 이 규칙이 공허하지 않다.
        looks = looks_for_genre(library, "edm")
        levels = [look.dynamics for look in looks]
        assert len(levels) != len(set(levels)), "동률 없는 장르로는 타이브레이크를 검증할 수 없다"
        for earlier, later in zip(looks, looks[1:], strict=False):
            if earlier.dynamics == later.dynamics:
                assert earlier.look_id < later.look_id


class TestGenreResolution:
    """AC-BUSKWIZ-002 — 한/영 별칭 해석과 정직한 실패."""

    @pytest.mark.parametrize(
        ("query", "genre"),
        [
            ("워십", "worship"),
            ("예배 준비해줘", "worship"),
            ("찬양", "worship"),
            ("록", "rock"),
            ("락 버스킹", "rock"),
            ("발라드", "ballad"),
            ("이디엠", "edm"),
            ("worship", "worship"),
            ("rock", "rock"),
            ("ballad", "ballad"),
            ("edm", "edm"),
        ],
    )
    def test_korean_and_slug_fold_to_the_same_genre(self, library, query, genre):
        selection = select_genre(library, query)
        assert selection.genre == genre
        assert selection.reason is None
        assert len(selection.looks) == _EXPECTED_COUNTS[genre]

    def test_unresolved_query_fails_honestly_with_candidates(self, library):
        # AC-BUSKWIZ-002 ① — 예외가 아니라 후보를 담은 실패 결과.
        selection = select_genre(library, "재즈")
        assert isinstance(selection, GenreSelection)
        assert selection.reason == UNRESOLVED_GENRE
        assert set(selection.candidates) == set(_EXPECTED_COUNTS)

    def test_unresolved_query_is_not_promoted(self, library):
        # AC-BUSKWIZ-002 ② — 가장 비슷한 장르로 승격하지 않는다.
        selection = select_genre(library, "재즈")
        assert selection.genre is None
        assert selection.looks == ()

    def test_two_genres_named_is_not_half_a_constraint(self, library):
        # resolve_genre의 규율 계승: 두 장르가 언급되면 축이 침묵한다.
        selection = select_genre(library, "워십이랑 록 둘 다")
        assert selection.genre is None
        assert selection.reason == UNRESOLVED_GENRE

    def test_empty_query_is_its_own_reason(self, library):
        # "아무것도 안 물었다"와 "모르는 걸 물었다"는 다른 사실이고
        # 사용자가 취할 조치도 다르다 — 한 사유로 합치지 않는다.
        selection = select_genre(library, "   ")
        assert selection.reason == EMPTY_QUERY
        assert selection.genre is None
        assert set(selection.candidates) == set(_EXPECTED_COUNTS)

    def test_candidates_come_from_the_library_not_a_literal(self, library):
        # 후보 목록이 자산에서 파생되어야 라이브러리가 늘어날 때 함께 는다.
        assert set(select_genre(library, "재즈").candidates) == {
            look.genre for look in library.looks
        }


class TestNoGenreVocabularyDuplication:
    """AC-BUSKWIZ-002 ③ — 별칭 표를 재정의하지 않고 import로만 닿는다."""

    @staticmethod
    def _tree() -> ast.Module:
        return ast.parse(_BUSKING_MODULE.read_text(encoding="utf-8"))

    def test_the_scan_actually_parses_this_module(self):
        # 비공허성: 아무것도 못 본 스캔은 틀린 이유로 통과한다.
        names = {node.id for node in ast.walk(self._tree()) if isinstance(node, ast.Name)} | {
            node.attr for node in ast.walk(self._tree()) if isinstance(node, ast.Attribute)
        }
        assert names, "AST에서 식별자를 하나도 모으지 못했다"

    def test_no_dict_or_set_literal_holds_a_genre_name(self, library):
        genre_names = {look.genre for look in library.looks} | {"워십", "록", "발라드", "이디엠"}
        offenders = []
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Dict):
                parts = [k for k in node.keys if k is not None] + list(node.values)
            elif isinstance(node, ast.Set):
                parts = list(node.elts)
            else:
                continue
            for part in parts:
                if isinstance(part, ast.Constant) and part.value in genre_names:
                    offenders.append(ast.dump(node)[:80])
        assert offenders == []

    def test_alias_table_is_reached_only_by_import(self):
        imported = {
            alias.asname or alias.name
            for node in ast.walk(self._tree())
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert {"GENRE_ALIASES", "resolve_genre"} & imported, "별칭 해석을 import하지 않았다"
        assigned = {
            target.id
            for node in ast.walk(self._tree())
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        assert "GENRE_ALIASES" not in assigned, "별칭 표를 재정의했다"

    def test_the_truncating_path_is_not_referenced(self):
        """plan.md M1 — 절단 경로 미접촉을 **구조로** 보장한다.

        raw 텍스트 스캔은 쓰지 않는다. `LOOKLIB v0.3.2`가 같은 이유로 수단을
        교체했고(텍스트는 "호출"과 "호출을 설명하는 산문"을 구분하지 못한다),
        본 모듈의 `@MX:NOTE`가 정확히 그 산문이다 — 왜 그 경로를 쓰지 않는지
        설명하려면 이름을 적어야 하고, 그 설명이 위반으로 잡히면 경계를
        문서화할 방법이 사라진다. 식별자만 본다.
        """
        tree = self._tree()
        identifiers = (
            {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
            | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
            | {
                alias.asname or alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom | ast.Import)
                for alias in node.names
            }
        )
        # 비공허성 2중: 스캔이 식별자를 모았고, 실제로 쓰는 이름을 본다.
        assert identifiers, "AST에서 식별자를 하나도 모으지 못했다"
        assert {"resolve_genre", "EMPTY_QUERY"} <= identifiers
        assert {"MAX_TOOL_MATCHES", "match_looks"} & identifiers == set()
