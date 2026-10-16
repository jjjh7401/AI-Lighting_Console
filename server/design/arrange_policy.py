"""곡별 배치 규칙 설정 — SPEC-LDARRANGE-001 REQ-LDARRANGE-004.

규칙 값(구간 길이 4마디, 리듬층 둘·드롭 셋)은 전역 상수가 아니라 곡마다 든다. 기본값은
배치 규칙서(``reports/effect-arrangement-rules-20261007.md`` §1 규칙 3·4)의 값이다. 이
객체는 불변이라 한 곡의 설정을 바꿔도 다른 곡의 설정에 닿지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from server.design.color_names import COLOR_PALETTE_SEQUENCE

__all__ = [
    "ARRANGEMENT_COLOR_NAMES",
    "MOVER_POSITION_LADDER",
    "ArrangementPalette",
    "ArrangementPolicy",
]

_Rgb = tuple[int, int, int]

#: 무빙 기본 위치 사다리 — 낮은 곳에서 높은 곳 순서. 이름은 기본 위치 10종
#: (``server/spatial/pointing.py`` ``BASIC_POSITION_SEQUENCE``)의 이름이고, 리그에서 조준값을 그대로
#: 읽는다(지어낸 좌표가 없다). 상대 이동(「한 칸 올림」「새 자리」)은 사다리에서 한 칸씩만 옮긴다.
MOVER_POSITION_LADDER: tuple[str, ...] = ("Home", "Center", "Ring In", "Audience")


#: 배치 팔레트가 낼 수 있는 모든 RGB 의 콘솔 영문 이름(대문자·ASCII) — 이름의 단일 출처다.
#: 표준 팔레트 10색은 ``COLOR_PALETTE_SEQUENCE`` 의 이름을 그대로 쓰고(값을 새로 짓지 않는다),
#: 표준 팔레트에 없는 두 색은 곡 주석(``preset_annotations/love_attack.yaml``)의 콘솔 이름과
#: 같다. 팔레트 색을 바꾸면 이 표에도 이름을 더해야 한다(시험이 팔레트 전체가 이름을 가졌는지
#: 본다). 표 밖의 RGB(주석 색 등)는 ``cell_direction.assign_color_names`` 가 가장 가까운 이름에
#: 번호를 붙여 정한다.
ARRANGEMENT_COLOR_NAMES: dict[tuple[int, int, int], str] = {
    **{rgb: name.upper() for name, rgb in COLOR_PALETTE_SEQUENCE},
    (100, 50, 75): "PINK",
    (40, 65, 95): "SKY",
}


def _check_rgb(name: str, rgb: object) -> None:
    """세 채널이 모두 0~100 사이의 정수(콘솔 퍼센트)인지 본다. bool 은 정수로 치지 않는다."""
    if (
        not isinstance(rgb, tuple)
        or len(rgb) != 3
        or not all(
            isinstance(channel, int) and not isinstance(channel, bool) and 0 <= channel <= 100
            for channel in rgb
        )
    ):
        raise ValueError(f"{name} 색은 0~100 사이 정수 세 개(RGB)여야 합니다: {rgb!r}")


@dataclass(frozen=True)
class ArrangementPalette:
    """구간 종류별 계획 색(콘솔 퍼센트 RGB, 채널마다 0~100). 감독이 고칠 값이다.

    계획 색은 콘솔 값이 아니라 화면에 보이는 표식이다. 기본값은 표준 팔레트와 LOVE ATTACK 계획
    주석(``preset_annotations``)의 값에서 왔다.

    - ``verse``: 벌스 보라(표준 Lavender).
    - ``chorus``: 후렴 핑크(LOVE ATTACK 주석의 핑크).
    - ``drop``: 드롭 주황(표준 Amber).
    - ``bridge``: 브릿지(마디 지도 ``break`` 구간)의 차분한 색(표준 Cool White).
    - ``backlight``: 역광(BACK) 칸 색. 구간과 상관없이 늘 차가운 하늘색(주석의 SKY).
    - ``last_chorus``: 마지막 드롭 뒤 구간을 돌며 쓰는 색 목록. 비어 있으면 안 된다.
    """

    verse: _Rgb = (55, 35, 100)
    chorus: _Rgb = (100, 50, 75)
    drop: _Rgb = (100, 55, 5)
    bridge: _Rgb = (85, 95, 100)
    backlight: _Rgb = (40, 65, 95)
    last_chorus: tuple[_Rgb, ...] = ((100, 50, 75), (55, 35, 100), (100, 55, 5))

    def __post_init__(self) -> None:
        for name in ("verse", "chorus", "drop", "bridge", "backlight"):
            _check_rgb(name, getattr(self, name))
        if not isinstance(self.last_chorus, tuple) or not self.last_chorus:
            raise ValueError("마지막 후렴 색 목록은 비어 있으면 안 됩니다.")
        for rgb in self.last_chorus:
            _check_rgb("last_chorus", rgb)


# @MX:NOTE: [AUTO] 곡별 규칙 설정 — 전역 상수가 아니라 곡마다 따로 든다(REQ-LDARRANGE-004).
@dataclass(frozen=True)
class ArrangementPolicy:
    """이 곡에 적용할 배치 규칙 값.

    - ``slow_song``: 「느린 곡」 플래그. 켜면 스트로브를 한 칸도 제안하지 않는다
      (REQ-LDARRANGE-007). 기준 자체는 spec.md §5 항목 3의 기본안(곡 메타데이터의
      명시 플래그)이고, 기본값은 꺼짐이다.
    - ``window_bars``: 주인공 교대와 리듬층 세기를 재는 구간 길이(규칙 4: 4마디).
    - ``base_layer_cap``: 보통 구간의 리듬층 상한(규칙 3: 둘).
    - ``drop_layer_cap``: 드롭 구간의 리듬층 상한(규칙 3: 셋). 마지막 코러스 라벨은
      마디 지도에 없어서 드롭 구간에만 적용한다(spec.md §5 항목 1 공백 (나)).
    - ``rest_percent``: 쉬는 칸의 밝기(명시적 쉼은 꺼 둔다). 0~100.
    - ``lit_percent``: 켜는 칸의 기본 밝기. 0~100. 감독이 칸마다 고친다.
    - ``downbeat_trigger``: 펄스·강조가 맞는 박(1 = 마디의 첫 박, 규칙 9).
    - ``motion_period_bars``: 무빙 칸의 팬 웨이브 주기(규칙값 2마디).
    - ``palette``: 구간 종류별 계획 색. 콘솔에 보내지 않는 표시용 값이다.
    - ``chorus_energy_cut``: 킥 진입이 없는 구간의 후렴 기준(0~1). 곡 안에서 가장 조용한 구간을
      0, 가장 큰 구간을 1로 둔 그 구간의 위치가 이 값보다 크면 후렴으로 본다(같으면 벌스).
      절대 에너지 값으로 가르면 전 구간이 크게 나오는 곡에서 벌스가 사라져서 곡 안 상대 위치로
      본다. 마디 지도에 구간 이름이 없어서 정한 어림값이라 감독이 고친다.
    """

    slow_song: bool = False
    window_bars: int = 4
    base_layer_cap: int = 2
    drop_layer_cap: int = 3
    rest_percent: int = 0
    lit_percent: int = 100
    downbeat_trigger: int = 1
    motion_period_bars: int = 2
    palette: ArrangementPalette = field(default_factory=ArrangementPalette)
    chorus_energy_cut: float = 0.5

    def __post_init__(self) -> None:
        if self.window_bars < 1:
            raise ValueError("구간 길이는 1마디 이상이어야 합니다.")
        if not 1 <= self.base_layer_cap <= self.drop_layer_cap:
            raise ValueError("리듬층 상한은 1 이상이고, 드롭 상한은 보통 상한 이상이어야 합니다.")
        if not (0 <= self.rest_percent <= 100 and 0 <= self.lit_percent <= 100):
            raise ValueError("밝기는 0~100 사이여야 합니다.")
        if self.downbeat_trigger < 1:
            raise ValueError("트리거 박은 1 이상이어야 합니다.")
        if self.motion_period_bars < 1:
            raise ValueError("움직임 주기는 1마디 이상이어야 합니다.")
        if isinstance(self.chorus_energy_cut, bool) or not 0 <= self.chorus_energy_cut <= 1:
            raise ValueError("후렴 에너지 기준(곡 안 상대 위치)은 0~1 사이여야 합니다.")
