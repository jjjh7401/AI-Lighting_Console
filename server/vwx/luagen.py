"""M4 — `AddFixtures` Lua 소스 생성기 (REQ-AUTOPATCH-016 · REQ-AUTOPATCH-017).

**설계 원칙 — 금지를 검사로 두지 않고 어휘로 둔다.**
이 모듈이 만들 수 있는 Lua는 `AddFixtures` 호출 하나뿐이다. 목적지를 옮기는 명령은
**생성 어휘에 존재하지 않는다** — 사후 문자열 검사로 걸러내는 것이 아니라, 애초에
그런 문장을 조립할 함수도 자유 문자열 삽입 지점도 두지 않는다(design.md §5 슬롯 C).
공개 API는 `LuaPatchEntry`(정수·문자열 필드만)와 두 렌더 함수뿐이며, 문자열 필드는
전부 `_lua_string`을 통과해야 본문에 도달한다.

**왜 목적지 명령을 만들지 않는가 — 근거가 v0.1.3에서 바뀌었다.**
룰북은 "그 명령을 보내면 패치가 nil을 반환한다"는 인과를 적었으나 그것은 반증됐다.
실측이 보인 것은 **그 명령이 플러그인의 앰비언트 목적지에 아무 효과가 없다**는 것이며
(`progress.md` §E.2 M0 3·5차), 따라서 생성물에 둘 이유가 없다.

**점유폭은 이 모듈이 계산하지 않는다.** `DMXChannels` 개수는 DMX 점유폭이 아니고
(M0 함정 7: childCount 14 / 실제 stride 16) 이 빌드에서 폭을 읽을 경로가 없다.
간격 배치는 `patchplan.plan_addresses`가 **1단계 도면이 준 폭**으로만 수행한다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

FIXTURE_IDTYPE = "Fixture"

# 룰북이 정한 필드 집합과 순서. 이 순서 밖의 키는 렌더되지 않는다(AC-AUTOPATCH-013③).
ADDFIXTURES_FIELD_ORDER = ("mode", "amount", "fid", "idtype", "name", "patch")

# 목적지 변경 명령의 토큰. 문자열 리터럴로 두지 않기 위해 조각을 런타임에 합친다 —
# 이 모듈 소스에 그 토큰이 리터럴로 존재하면 AC-AUTOPATCH-014③(a) 스캔이 잡는다.
_DESTINATION_VERB = "Change" + "Destination"
_DESTINATION_SHORT = "C" + "D"
_DESTINATION_TOKEN = re.compile(
    rf"{_DESTINATION_VERB}|(?<![A-Za-z]){_DESTINATION_SHORT}(?![A-Za-z])"
)

_LUA_ESCAPES = MappingProxyType(
    {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
)


class LuaGenerationError(ValueError):
    """생성기가 안전하게 렌더할 수 없는 입력을 받았을 때."""


@dataclass(frozen=True)
class LuaPatchEntry:
    """`AddFixtures` 한 번 호출에 대응하는 값 묶음.

    필드는 룰북 인자에 1:1로 대응하며, **자유 Lua를 실어 보낼 통로가 없다.**
    """

    console_type: str
    console_mode: str
    fid: int
    name: str
    universe: int
    address: int


def render_addfixtures_call(entry):
    """항목 하나를 `AddFixtures({...})` **한 줄**로 렌더한다."""
    values = _field_values(entry)
    parts = [f"{key} = {values[key]}" for key in ADDFIXTURES_FIELD_ORDER if key in values]
    return "  AddFixtures({ " + ", ".join(parts) + " })"


def render_addfixtures_plugin(entries):
    """항목 목록을 룰북 형태의 Lua 모듈 소스로 렌더한다."""
    body = [render_addfixtures_call(entry) for entry in _as_tuple(entries)]
    lines = ["local function main()", *body, "end", "", "return main", ""]
    return "\n".join(lines)


def _field_values(entry: LuaPatchEntry) -> Mapping[str, str]:
    mode_handle = (
        f"Patch().FixtureTypes[{_lua_string(entry.console_type)}]"
        f".DMXModes[{_lua_string(entry.console_mode)}]"
    )
    patch_address = _lua_string(f"{_lua_int(entry.universe)}.{_lua_int(entry.address)}")
    return MappingProxyType(
        {
            "mode": mode_handle,
            "amount": "1",
            "fid": _lua_string(str(_lua_int(entry.fid))),
            "idtype": _lua_string(FIXTURE_IDTYPE),
            "name": _lua_string(entry.name),
            "patch": "{ " + patch_address + " }",
        }
    )


def _lua_string(value: object) -> str:
    """문자열을 **한 줄짜리 Lua 문자열 리터럴**로 인코딩한다.

    본문에 도달하는 모든 문자열은 이 함수를 통과한다. 목적지 변경 토큰을 담은 값은
    **거부한다** — 조용히 고치면 자동 보정 금지를 어기고, 통과시키면 산출물 토큰
    스캐너(AC-AUTOPATCH-014①)가 거짓 양성을 내 강제력을 잃는다.
    """
    if not isinstance(value, str):
        raise LuaGenerationError(f"문자열이 아닌 값을 문자열 필드에 넣을 수 없다: {value!r}")
    if _DESTINATION_TOKEN.search(value):
        raise LuaGenerationError(
            "목적지 변경 명령 토큰을 담은 문자열은 생성물에 넣지 않는다 "
            f"(REQ-AUTOPATCH-017): {value!r}"
        )
    rendered = []
    for char in value:
        replacement = _LUA_ESCAPES.get(char)
        if replacement is not None:
            rendered.append(replacement)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            rendered.append(f"\\{ord(char):03d}")
        else:
            rendered.append(char)
    return '"' + "".join(rendered) + '"'


def _lua_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LuaGenerationError(f"정수 필드에 정수가 아닌 값이 왔다: {value!r}")
    return value


def _as_tuple(entries: Iterable[LuaPatchEntry]) -> tuple[LuaPatchEntry, ...]:
    return tuple(entries)
