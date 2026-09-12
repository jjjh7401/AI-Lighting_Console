"""곡 **사이**의 룩 재사용을 막는 세션 기억 (카드 t358).

정본 ``docs/proposals/song-structure-lighting-standard.md`` §7 의 비대칭 하나가 이
모듈의 존재 이유다 — **곡 안에서는 반복이 미덕이고, 곡 사이에서는 반복이 결함이다.**
두 축은 서로 다른 자리에 산다:

- 곡 안: 한 곡 안의 회차 사다리(:mod:`server.looks.songcue` 의 ``_ladder_start``).
  기억이 필요 없다 — 구간의 세 필드(라벨·회차·변형)가 같은 번들 안에 다 있다.
- 곡 사이: 앞 곡이 무엇을 썼는지 **기억해야** 안다. 그 기억이 이 객체다.

수명은 **세션 하나**다. 더 짧으면 곡을 못 건너고, 더 길면 지난 공연에서 쓴 룩이
오늘의 선택을 좁힌다. ``ExecutionContext`` 에 싣지 않은 이유가 앞쪽이다: 그 객체는
frozen 이고 툴 호출마다 새로 만들어지므로(``server/orchestrator/runner.py:496``
``ExecutionContext(executed_ok=...)``) 곡 하나를 넘길 수 없다. 그래서 세션이 들고
``build_toolset`` 으로 넘기는 ``spatial_memory``·``song_analysis`` 와 같은 자리에 둔다.

이 모듈은 순수 기억이다 — 콘솔도 리그도 라이브러리도 모른다. 무엇을 기억할지는
호출자가 정하고(저장된 큐의 룩만), 기억을 어떻게 쓸지는 룩 선택이 정한다
(``songcue.map_sections_to_looks`` 의 ``used_look_ids``).
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["SongLookMemory"]


class SongLookMemory:
    """이 세션이 이미 무대에 올린 룩 id — 처음 쓴 순서 그대로, 중복 없이.

    집합이 아니라 **순서 있는 목록**인 이유는 보고 하나다: 감독이 「어느 곡이 무엇을
    가져갔나」를 읽을 때 순서가 곧 곡 순서이고, 집합은 그 순서를 버린다.
    """

    def __init__(self, used: Iterable[str] = ()) -> None:
        # dict.fromkeys — 중복을 접으면서 순서는 그대로. 생성자에 값을 받는 것은
        # 테스트가 「앞 곡 둘이 이미 지나간 세션」을 한 줄로 만들 수 있게 하기 위해서다.
        self._used: list[str] = [look_id for look_id in dict.fromkeys(used) if look_id]

    def used(self) -> tuple[str, ...]:
        """지금까지 기억한 룩 id 전량. 호출자가 바꿔도 기억은 안 움직인다."""
        return tuple(self._used)

    def remember(self, look_ids: Iterable[str]) -> tuple[str, ...]:
        """이 곡이 **실제로 저장한** 룩을 기억에 더하고, 새로 더해진 것만 돌려준다.

        저장되지 않은 룩은 여기 오지 않는다 — 호출자가 저장된 큐에서만 뽑아 넘긴다.
        무대에 안 나간 룩이 기억에 들어가면 다음 곡이 **쓰지도 않은 룩을 피하게** 되고,
        그것은 재사용을 막는 것이 아니라 팔레트를 이유 없이 좁히는 것이다.
        """
        added: list[str] = []
        for look_id in look_ids:
            if look_id and look_id not in self._used:
                self._used.append(look_id)
                added.append(look_id)
        return tuple(added)

    def __len__(self) -> int:
        return len(self._used)
