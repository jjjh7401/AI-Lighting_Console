"""카드 t406 — t402 팔레트 회전이 실제로는 A-B-A-B 두 상태뿐이고, 회전이
언어만 다른 같은 색(한국어 원색 "블루" vs 영어 아크 색 "blue")을 겹쳐
찍는 결함을 고친다.

재현 1 (AB-AB): `_arc_palette` 를 코러스 역할로 회차 1~6 에 걸쳐 부르면
occurrence 1·3·5 가 서로 바이트 동일하고 2·4·6 도 서로 바이트 동일했다
(회전 주기 2). 코러스가 6회를 넘게 반복돼도 상태는 둘뿐이었다.

재현 2 (언어 중복): verse 아크는 ("blue", "cyan") 인데 감독 원색이
"블루"(한국어)면, 회전이 짝수 회차에서 arc[-1]="blue" 를 골라
("블루", "blue") 를 낸다 — 같은 색이 언어만 바뀌어 두 번 찍힌다.
"""

from __future__ import annotations

from server.web.session import _arc_palette


class TestArcPaletteBreaksTheTwoStateCycle:
    def test_chorus_does_not_collapse_to_two_states_across_six_occurrences(self):
        base = ("블루",)
        seen = {_arc_palette(base, "chorus", occurrence=n) for n in range(1, 7)}
        assert len(seen) > 2, f"6회차인데 상태가 {len(seen)}종뿐이다 — A-B-A-B 재발 (t406)"

    def test_verse_never_duplicates_the_directors_colour_under_another_language(self):
        base = ("블루",)
        for occurrence in range(1, 9):
            colors = _arc_palette(base, "verse", occurrence=occurrence)
            assert "blue" not in colors, (
                f"회차 {occurrence}: {colors} — '블루' 와 'blue' 가 같은 색인데 둘 다 찍혔다 (t406)"
            )

    def test_main_colour_is_always_present_verbatim(self):
        base = ("블루",)
        for occurrence in range(1, 9):
            for role in ("intro", "verse", "chorus", "bridge", "finale"):
                colors = _arc_palette(base, role, occurrence=occurrence)
                assert "블루" in colors, f"{role} 회차 {occurrence} 에서 메인 컬러가 사라졌다"

    def test_occurrence_one_stays_byte_identical_to_pre_t406_where_no_collision_existed(self):
        """회귀 없음 — 언어 충돌이 없던 조합은 t402 시절과 바이트 동일해야 한다."""
        base = ("블루",)
        assert _arc_palette(base, "chorus", occurrence=1) == ("warm white", "magenta", "블루")
        assert _arc_palette(base, "verse", occurrence=1) == ("블루", "cyan")

    def test_intro_occurrence_one_also_had_the_language_collision_and_is_now_fixed(self):
        """intro 아크의 첫 색("deep blue")이 "블루" 와 이미 같은 색이었다 —
        intro 는 회차가 항상 1(싱글턴)이라 이 결함은 회전을 기다릴 필요도
        없이 감독이 파랑 계열을 메인으로 고를 때마다 매번 났다."""
        base = ("블루",)
        colors = _arc_palette(base, "intro", occurrence=1)
        assert colors == ("warm special", "블루")
        assert "blue" not in colors
