"""`Store Preset <pool>.<n>` (+ `Label`) 일반형 빌더.

이 파일은 **문형을 아는 유일한 일반형 자리**다. 툴 층도 세션 층도 여기를 부른다.
새 자리에 같은 문형을 적지 마라 — 사본이 늘면 변경이 한 곳에서 끝나지 않는다.
"""

from __future__ import annotations

from server.spatial.pointing import SpatialPointingError

__all__ = ["preset_store_commands"]


def preset_store_commands(
    pool_no: int, preset_no: int, label: str | None = None
) -> tuple[str, ...]:
    """``Store Preset <pool>.<n>`` (+ ``Label``) — 풀 일반형 저장 명령 빌더.

    ``pointing.position_preset_store_commands``의 문면·규칙(양수 번호, 빈
    라벨·따옴표 거부)을 임의 풀 번호에 적용한다. ``pool_no=2``의 출력은
    포지션 빌더와 **문자 단위로 동일**하다.
    """
    if not isinstance(pool_no, int) or isinstance(pool_no, bool) or pool_no <= 0:
        # 대칭 검증 — preset_no만 지키고 pool_no(응답기 풀 목록 유래)를
        # 방치하면 'Store Preset -3.31' 같은 기형 표적이 조립될 수 있다.
        raise SpatialPointingError(f"pool number {pool_no!r} must be a positive integer")
    if preset_no <= 0:
        raise SpatialPointingError(f"preset number {preset_no!r} must be positive")
    commands = [f"Store Preset {pool_no}.{preset_no}"]
    if label is not None:
        text = label.strip()
        if not text or "'" in text or '"' in text:
            raise SpatialPointingError(f"preset label {label!r} is empty or carries a quote")
        commands.append(f"Label Preset {pool_no}.{preset_no} '{text}'")
    return tuple(commands)
