"""줄을 타임코드 여러 개에 나눠 담는다 — 줄 수에 고정 상한을 두지 않는다(카드 WT-track-model PR2).

감독 지시(2026-10-18): 무대마다 장비 종류가 수십 가지, 수량이 수백 대가 될 수 있다. 한 타임코드에
붙는 트랙 수는 실기로 잰 값(``MEASURED_MAX_TIMECODE_TRACKS``, 데이터 파일)까지만 믿고, 그보다 줄이
많으면 다음 타임코드에 이어 담는다. 기준은 **줄(콘솔 그룹) 수**다 — 장비 대수가 아니다.

이 파일은 순수 함수다. 콘솔을 읽지 않는다(호출자가 읽은 「쓰인 번호」를 넘긴다). 쓰지 않을 번호는
``beat_grid_data/measured_console.yaml`` 의 ``reserved_timecodes`` 에서 온다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import yaml

__all__ = [
    "RESERVED_TIMECODES",
    "pick_extra_timecode_numbers",
    "split_rows_by_timecode",
    "transport_commands",
]

_DATA = Path(__file__).resolve().parent / "beat_grid_data" / "measured_console.yaml"


def _load_reserved() -> frozenset[int]:
    with _DATA.open("r", encoding="utf-8") as handle:
        values = yaml.safe_load(handle).get("reserved_timecodes") or []
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in values):
        raise ValueError(f"reserved_timecodes 는 양의 정수 목록이어야 합니다: {values!r}")
    return frozenset(values)


#: 나눠 담을 때 고르지 않는 타임코드 번호(감독 쇼의 것). 근거는 데이터 파일.
RESERVED_TIMECODES = _load_reserved()


def split_rows_by_timecode(names: Sequence[str], *, per_timecode: int) -> list[list[str]]:
    """격자 순서 그대로 ``per_timecode`` 줄씩 끊는다. 빈 목록이면 빈 목록."""
    if per_timecode < 1:
        raise ValueError("per_timecode 는 1 이상이어야 합니다")
    return [list(names[i : i + per_timecode]) for i in range(0, len(names), per_timecode)]


def pick_extra_timecode_numbers(
    first: int,
    *,
    needed: int,
    used: Iterable[int],
    recorded: Sequence[int] = (),
    reserved: Iterable[int] = RESERVED_TIMECODES,
) -> tuple[list[int], str | None]:
    """첫 타임코드 ``first`` 다음에 쓸 번호 ``needed`` 개. ``(번호들, 못 고른 사유)``.

    - ``recorded``(이 곡이 전에 만든 추가 타임코드 — 호출자가 앱 소유로 확인)를 먼저 다시 쓴다.
    - 나머지는 ``first`` 보다 큰 번호 중 콘솔에서 비어 있고(``used`` 에 없음) 쓰지 않을 번호가 아닌
      것을 작은 순서로 고른다. 번호를 지어내 남의 객체를 덮지 않는다.
    """
    taken = set(used) | set(reserved) | {first}
    chosen: list[int] = []
    for number in recorded:
        if len(chosen) == needed:
            break
        if number != first and number not in reserved and number not in chosen:
            chosen.append(number)
    candidate = first + 1
    # 타임코드 풀 번호는 유한하다 — 실기 콘솔의 풀 크기를 모르므로 넉넉한 탐색 한도만 둔다.
    limit = first + 10_000
    while len(chosen) < needed and candidate <= limit:
        if candidate not in taken and candidate not in chosen:
            chosen.append(candidate)
        candidate += 1
    if len(chosen) < needed:
        return chosen, f"줄을 나눠 담을 빈 타임코드 번호를 {needed}개 찾지 못했습니다"
    return chosen, None


def transport_commands(numbers: Sequence[int], verbs: Sequence[str]) -> tuple[str, ...]:
    """곡의 타임코드 전부에 같은 동작을 보낸다 — 동작마다 모든 번호(``Top A``·``Top B``·
    ``Go A``·``Go B``). 되감기(Top)를 다 끝낸 뒤 재생(Go)을 몰아 보내 타임코드끼리 시작이
    벌어지지 않게 한다."""
    return tuple(f"{verb} Timecode {number}" for verb in verbs for number in numbers)
