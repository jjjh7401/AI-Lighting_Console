"""`Store Preset <pool>.<n>` (+ `Label`) 일반형 빌더.

이 파일은 **문형을 아는 유일한 일반형 자리**다. 툴 층도 세션 층도 여기를 부른다.
새 자리에 같은 문형을 적지 마라 — 사본이 늘면 변경이 한 곳에서 끝나지 않는다.
"""

from __future__ import annotations

from server.spatial.pointing import SpatialPointingError

__all__ = ["preset_apply_command", "preset_label_refusal", "preset_store_commands"]


def preset_label_refusal(label: str | None) -> str | None:
    """이 라벨을 `Label Preset` 에 실을 수 없는 이유. 실을 수 있으면 ``None``.

    `preset_store_commands` 가 던지기 **전에** 같은 판정을 물어볼 수 있게 술어를
    밖으로 낸다. 계획을 내는 쪽(`lxseq.preset_mapper`)이 이걸 부르면, 못 보내는
    이름이 「보낼 수 있다」고 계획에 실리는 일이 없다(t97).

    술어를 부르는 쪽에 **다시 적지 마라** — 사본이 늘면 판정기와 발사기가 갈라져,
    한쪽만 바뀐 날에 계획이 통과시킨 이름에서 빌더가 터진다. 이 파일이 문형을 아는
    유일한 자리라는 규율(모듈 docstring)이 술어에도 그대로 걸린다.
    """
    if label is None:
        return None
    text = label.strip()
    if not text:
        return "라벨이 비었다 — 이름 없는 프리셋은 나중에 무엇인지 알 수 없다"
    if "'" in text or '"' in text:
        # 홑따옴표가 `Label Preset <pool>.<n> '<text>'` 의 구분자다. 이름 안의
        # 따옴표는 구분자를 조기에 닫아 문법을 깬다. 겹따옴표도 같이 막는 이유는
        # 콘솔 파서가 어느 쪽을 구분자로 볼지 이 채널로는 확인되지 않아서다.
        return "이름에 따옴표가 있다 — 따옴표가 명령의 구분자라서 문법이 깨진다"
    return None


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
        # 판정은 `preset_label_refusal` 하나가 한다 — 여기에 사본을 두면 계획
        # 단계와 발사 단계의 술어가 갈라진다(t97).
        if preset_label_refusal(label) is not None:
            raise SpatialPointingError(f"preset label {label!r} is empty or carries a quote")
        commands.append(f"Label Preset {pool_no}.{preset_no} '{text}'")
    return tuple(commands)


def preset_apply_command(group_no: int, attribute: str, value: int) -> str:
    """``Group <n> ; Attribute '<attr>' At <v>`` — 저장 **전에** 프로그래머를 채우는
    한 줄.

    ``Store Preset`` 은 그 순간의 프로그래머 상태를 저장한다. 이 줄이 없으면
    저장되는 것은 시트 값이 아니라 그 자리에 우연히 있던 것이다(t108 C1).

    대상을 **그룹 번호**로 잡는 이유: 그룹 멤버십은 이 프로젝트가 시도한 어느
    채널로도 되읽히지 않지만 그룹 **번호**는 멤버십을 몰라도 주소가 된다
    (``server/web/session.py:900-905`` 이 같은 근거로 같은 문형을 쓴다). 콘솔
    픽스처 열거로 대상을 만드는 길은 열거가 절단되기 때문에 이 저장소가 이미
    거절해 뒀다(``server/orchestrator/tools.py`` 의 ``import_lxseq_groups``).

    선택과 값을 ``;`` 로 한 줄에 묶는 것은 ``_color_apply_command`` 의 규율과
    같다 — 두 줄로 나누면 앞줄(맨몸 선택)이 접힘 면제라 뒤 값 줄만 남는 상황이
    생길 수 있다.
    """
    if not isinstance(group_no, int) or isinstance(group_no, bool) or group_no <= 0:
        raise SpatialPointingError(f"group number {group_no!r} must be a positive integer")
    name = attribute.strip()
    if not name or "'" in name or '"' in name:
        raise SpatialPointingError(f"attribute {attribute!r} is empty or carries a quote")
    if not isinstance(value, int) or isinstance(value, bool):
        raise SpatialPointingError(f"attribute value {value!r} must be an int")
    return f"Group {group_no} ; Attribute '{name}' At {value}"
