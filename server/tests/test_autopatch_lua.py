"""M4 — `AddFixtures` Lua 생성기 + 주소 계획.

AC-AUTOPATCH-013 (호출 형태) · AC-AUTOPATCH-014 (`ChangeDestination` 0건) ·
AC-AUTOPATCH-016 (점유폭 간격 · 점유 주소 제외).

**M0가 이 마일스톤에 남긴 제약** (`progress.md` §E.2 M0 1~5차):
- 함정 7 — `DMXChannels` childCount는 DMX 점유폭이 **아니다**(`Robin LEDBeam 350` Mode 2는
  childCount 14 / 실제 stride 16). 따라서 점유폭은 **1단계 도면이 준 값**만 쓰고, 없으면
  **추측하지 않고 제외**한다. `ASSUMPTION-72`가 GO(한정)인 이유가 이것이다.
- 함정 1 — CD 금지는 유효하나 근거가 "CD가 실패 원인"이 아니라 **"CD는 아무 효과가 없다"**다.
  생성 어휘에 애초에 없게 하는 구조 보장은 그대로 요구된다(REQ-AUTOPATCH-017).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from types import MappingProxyType, ModuleType

import lupa.lua54 as lua54
import pytest

from server.tests.test_autopatch_contract import iter_vwx_modules, vwx_module_label
from server.vwx import luagen
from server.vwx.address import to_console_form
from server.vwx.luagen import (
    ADDFIXTURES_FIELD_ORDER,
    FIXTURE_IDTYPE,
    LuaGenerationError,
    LuaPatchEntry,
    render_addfixtures_call,
    render_addfixtures_plugin,
)
from server.vwx.patchplan import (
    AddressPlanEntry,
    PatchCandidate,
    plan_addresses,
)
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_OVERLAP_IN_PLAN,
    FOOTPRINT_UNKNOWN,
    TARGET_EXCLUSION_REASON,
    target_exclusion_label,
)

LUAGEN_PATH = Path("server/vwx/luagen.py")
LUAGEN_SOURCE = LUAGEN_PATH.read_text(encoding="utf-8")

# `CD`/`ChangeDestination` 스캐너. 산출물과 모듈 소스 양쪽에 쓴다.
CD_TOKEN = re.compile(r"ChangeDestination|(?<![A-Za-z])CD(?![A-Za-z])")


def _entry(
    *,
    console_type: str = "Robin LEDBeam 350",
    console_mode: str = "Mode 1",
    fid: int = 101,
    name: str = "LEDBeam 101",
    universe: int = 1,
    address: int = 1,
) -> LuaPatchEntry:
    return LuaPatchEntry(
        console_type=console_type,
        console_mode=console_mode,
        fid=fid,
        name=name,
        universe=universe,
        address=address,
    )


def _candidate(
    *,
    candidate_id: str,
    universe: int,
    address: int,
    fid: int,
    instrument_type: str = "Robin LEDBeam 350",
) -> PatchCandidate:
    return PatchCandidate(
        id=candidate_id,
        unit_number=None,
        instrument_type=instrument_type,
        universe=universe,
        address=address,
        detail="",
        address_basis="universe_address_direct",
        source_index=0,
        assigned_fid=fid,
    )


# --------------------------------------------------------------------------
# AC-AUTOPATCH-013 — `AddFixtures` 호출 형태
# --------------------------------------------------------------------------


def test_mode_handle_uses_bracket_notation_for_names_with_spaces():
    """AC-013① — `mode`가 `Patch().FixtureTypes[...].DMXModes[...]` 형태다."""
    call = render_addfixtures_call(_entry())
    assert 'Patch().FixtureTypes["Robin LEDBeam 350"].DMXModes["Mode 1"]' in call


def test_required_fields_present_with_rulebook_shapes():
    """AC-013② — `amount` · `idtype = "Fixture"` · `fid`(문자열) · `name`이 모두 있다."""
    call = render_addfixtures_call(_entry(fid=101, name="LEDBeam 101"))
    assert "amount = 1" in call
    assert f'idtype = "{FIXTURE_IDTYPE}"' in call
    # fid는 **문자열**이다 — 룰북이 그렇게 요구한다.
    assert 'fid = "101"' in call
    assert 'name = "LEDBeam 101"' in call
    assert 'patch = { "1.1" }' in call


def test_no_key_outside_the_rulebook_field_set():
    """AC-013③ — 룰북 필드 집합 밖의 키가 0건."""
    call = render_addfixtures_call(_entry())
    keys = set(re.findall(r"(\w+) = ", call))
    assert keys == set(ADDFIXTURES_FIELD_ORDER)


def test_extra_key_control_is_caught(monkeypatch):
    """AC-013③ 비공허성 — 여분 키를 심은 사본에서 위 단정이 **실제로 실패**한다."""
    import server.vwx.luagen as luagen

    monkeypatch.setattr(
        luagen, "ADDFIXTURES_FIELD_ORDER", (*luagen.ADDFIXTURES_FIELD_ORDER, "zzextra")
    )
    call = luagen.render_addfixtures_call(_entry())
    keys = set(re.findall(r"(\w+) = ", call))
    # 심은 키는 산출물에 나타나지 않으므로 필드 집합 단정이 깨진다 —
    # 즉 이 단정은 공허하지 않다.
    assert keys != set(luagen.ADDFIXTURES_FIELD_ORDER)


def test_fid_is_rendered_as_string_not_number():
    """AC-013② — `fid`를 숫자로 내면 룰북 형태가 아니다."""
    call = render_addfixtures_call(_entry(fid=7))
    assert 'fid = "7"' in call
    assert re.search(r"fid = 7(?!\")", call) is None


# --------------------------------------------------------------------------
# AC-AUTOPATCH-014 — `ChangeDestination` 0건 (세 기법을 분리한다)
# --------------------------------------------------------------------------


def test_generated_output_has_no_cd_token():
    """AC-014① — 생성된 Lua 소스 전수에서 `ChangeDestination`·`CD` 토큰 0건."""
    source = render_addfixtures_plugin([_entry(), _entry(fid=102, address=17)])
    assert CD_TOKEN.search(source) is None


def test_output_scanner_control_is_caught():
    """AC-014② 비공허성 — CD를 심은 가짜 산출물을 스캐너가 **실제로 잡는다**."""
    planted = render_addfixtures_plugin([_entry()]) + '\n  Cmd("ChangeDestination Root")\n'
    assert CD_TOKEN.search(planted) is not None
    # 짧은 형태(`CD`)도 잡아야 한다.
    assert CD_TOKEN.search('Cmd("CD Root")') is not None


def test_module_source_has_no_cd_string_literal():
    """AC-014③(a) — `luagen.py` **모듈 전체**에 CD를 담은 문자열 리터럴이 0건 (AST 기법)."""
    tree = ast.parse(LUAGEN_SOURCE)
    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        if CD_TOKEN.search(node.value)
    ]
    assert offenders == []


def test_module_source_literal_control_is_caught():
    """AC-014③(a) 비공허성 — CD 리터럴을 심은 **사본**에서 (a)가 실제로 실패한다.

    ②의 산출물 문자열 스캔과 **다른 기법**(AST)이므로 별도 대조군이 필요하다(round9 N47).
    """
    planted = LUAGEN_SOURCE + '\n_PLANTED = "ChangeDestination Root"\n'
    tree = ast.parse(planted)
    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        if CD_TOKEN.search(node.value)
    ]
    assert offenders == ["ChangeDestination Root"]


def test_caller_strings_cannot_escape_the_lua_string_literal():
    """AC-014③(b) — 호출자가 준 자유 문자열이 Lua 본문 조립부에 **그대로 도달하지 않는다**.

    `name`은 설계상 본문에 들어가야 하는 필드이므로 "도달 0건"은 **인코더 통과 강제**로 닫는다 —
    따옴표·역슬래시·줄바꿈으로 문자열 리터럴을 탈출해 **키를 주입하려는 시도가 무력화**된다.
    """
    hostile = 'x" , mode = Root() --'
    call = render_addfixtures_call(_entry(name=hostile))
    # 키가 주입되지 않았다 — 구조적 탈출 실패.
    assert set(re.findall(r"(\w+) = ", call)) == set(ADDFIXTURES_FIELD_ORDER)
    # 따옴표가 인코딩된 형태로만 등장한다.
    assert '\\"' in call
    assert len(call.splitlines()) == 1


# **round17 감사 지적 — 이 표 8행 중 4행이 반증 불가였다.**
# 원래 단정은 "1줄 유지"와 "키 집합"뿐이라, `back\slash` 행은 `_LUA_ESCAPES`에서 백슬래시
# 항목을 지워도 통과했다(치명 #1). `bracket]close` · `brace}close` · `comma,inside` 세 행은
# 그 글자들이 애초에 이스케이프 대상이 아니라 **어떤 뮤테이션에도 반응하지 않는다** —
# 지우지 않고 남기되 성격을 명시한다(통과성 확인 행이지 뮤테이션 탐지 행이 아니다).
# 실효 단정은 아래 왕복 대조로 붙인다. 표의 각 행이 무엇을 죽이는지는 파일 끝
# `round17 luagen 전달물 생성 본체 전수 게이트` 섹션에 전수로 적혀 있다.
_HOSTILE_NAME_FORMS = (
    ('quote"inside', "detects"),  # `"` 항목 제거를 잡는다
    ("back\\slash", "detects"),  # `\` 항목 제거를 잡는다 (round17 치명 #1)
    ("new\nline", "detects"),  # 날 줄바꿈이 리터럴을 깨는지
    ("carriage\rreturn", "detects"),
    ("tab\tchar", "detects"),
    ("bracket]close", "passthrough"),  # 반증 불가 — 이스케이프 대상이 아니다
    ("brace}close", "passthrough"),  # 반증 불가
    ("comma,inside", "passthrough"),  # 반증 불가
)


@pytest.mark.parametrize(
    "hostile",
    [form for form, _ in _HOSTILE_NAME_FORMS],
    ids=[f"{kind}:{form!r}" for form, kind in _HOSTILE_NAME_FORMS],
)
def test_name_encoder_neutralises_every_hostile_form(hostile):
    """AC-014③(b) — 적대적 입력 전수에서 **한 줄짜리 Lua 문자열 리터럴**로 남고 키 주입이 없다."""
    call = render_addfixtures_call(_entry(name=hostile))
    assert len(call.splitlines()) == 1
    assert set(re.findall(r"(\w+) = ", call)) == set(ADDFIXTURES_FIELD_ORDER)
    # round17 실효화 — 값이 **그대로 복원**되어야 한다. 리터럴을 빠져나온 산출물은
    # 여기서 거부된다(`_r17_decode_lua_literal`는 파일 끝 섹션에 있다).
    assert _r17_decode_lua_literal(luagen._lua_string(hostile)) == hostile
    # 그리고 진짜 Lua 5.4가 실행해도 부작용 0건이어야 한다.
    _, calls, side = _r17_run_lua(render_addfixtures_plugin([_entry(name=hostile)]))
    assert side == []
    assert calls[0]["name"] == f"string:{hostile}"


def test_hostile_name_form_table_is_complete():
    """표 행삭제 프로브 — 한 행을 지우면 실패한다.

    `detects` 행 다섯은 `_LUA_ESCAPES`의 다섯 항목과 **일대일**이고, `passthrough` 행 셋은
    반증 불가임을 명시적으로 세어 둔다(무증상 행이 조용히 늘거나 줄지 않게).
    """
    detecting = [form for form, kind in _HOSTILE_NAME_FORMS if kind == "detects"]
    passthrough = [form for form, kind in _HOSTILE_NAME_FORMS if kind == "passthrough"]
    assert len(detecting) == len(luagen._LUA_ESCAPES)
    assert len(passthrough) == 3
    assert set(luagen._LUA_ESCAPES) == {
        char for form in detecting for char in form if char in luagen._LUA_ESCAPES
    }


@pytest.mark.parametrize(
    "hostile", ["ChangeDestination", "CD", "go CD now", "x ChangeDestination y"]
)
def test_generator_refuses_a_name_carrying_the_destination_token(hostile):
    """AC-014① 을 **건전한 게이트로 유지**하기 위해 토큰을 담은 이름은 거부한다.

    조용히 이름을 고치면 `자동 보정 금지`(REQ-AUTOPATCH-024 정신)를 어기고,
    통과시키면 산출물 토큰 스캐너가 거짓 양성을 내 AC-014① 이 강제력을 잃는다.
    그래서 **거부**한다 — 항목을 빼는 결정은 호출자(M5)가 사유와 함께 보고한다.
    """
    with pytest.raises(LuaGenerationError):
        render_addfixtures_call(_entry(name=hostile))


def test_refusal_control_a_clean_name_is_accepted():
    """위 거부가 공허하지 않다 — 정상 이름은 통과한다."""
    assert render_addfixtures_call(_entry(name="LEDBeam 101"))


def test_generator_api_takes_no_free_form_lua_parameter():
    """AC-014③(b) — 생성기 공개 API에 **자유 Lua 삽입 지점이 없다**.

    `LuaPatchEntry`의 필드 집합이 `AddFixtures` 인자에 대응하는 것뿐임을 확인한다 —
    `extra_lua` / `prelude` / `raw` 같은 통로가 하나라도 있으면 실패한다.
    """
    assert set(LuaPatchEntry.__dataclass_fields__) == {
        "console_type",
        "console_mode",
        "fid",
        "name",
        "universe",
        "address",
    }


def test_generator_functions_take_no_extra_string_argument():
    """AC-014③(b) — 공개 함수 시그니처에 문자열 자유 인자가 없다(AST)."""
    tree = ast.parse(LUAGEN_SOURCE)
    public = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert set(public) == {"render_addfixtures_call", "render_addfixtures_plugin"}
    for name, node in public.items():
        args = [a.arg for a in node.args.args]
        assert args in (["entry"], ["entries"]), (name, args)
        assert node.args.vararg is None
        assert node.args.kwarg is None
        assert node.args.kwonlyargs == []


# --------------------------------------------------------------------------
# AC-AUTOPATCH-016 — 점유폭 간격 · 점유 주소 제외
# --------------------------------------------------------------------------


def test_planned_ranges_do_not_overlap_within_a_universe():
    """AC-016① — 같은 유니버스 안에서 점유 구간이 서로 겹치지 않는다."""
    targets = (
        _candidate(candidate_id="a", universe=1, address=1, fid=101),
        _candidate(candidate_id="b", universe=1, address=17, fid=102),
    )
    plan = plan_addresses(targets, footprints={"a": 16, "b": 16}, occupied={})
    assert [entry.candidate_id for entry in plan.entries] == ["a", "b"]
    assert plan.exclusions == ()
    spans = [(entry.address, entry.end_address) for entry in plan.entries]
    assert spans == [(1, 16), (17, 32)]


def test_overlap_control_is_caught():
    """AC-016① 비공허성 — 간격을 좁힌 입력에서 겹침이 **실제로 잡힌다**."""
    targets = (
        _candidate(candidate_id="a", universe=1, address=1, fid=101),
        _candidate(candidate_id="b", universe=1, address=8, fid=102),
    )
    plan = plan_addresses(targets, footprints={"a": 16, "b": 16}, occupied={})
    assert [entry.candidate_id for entry in plan.entries] == ["a"]
    codes = {exclusion.code for exclusion in plan.exclusions}
    assert codes == {ADDRESS_OVERLAP_IN_PLAN}
    assert plan.exclusions[0].candidate_id == "b"


def test_same_address_in_a_different_universe_is_not_an_overlap():
    """AC-016① — 유니버스가 다르면 같은 주소도 겹침이 아니다."""
    targets = (
        _candidate(candidate_id="a", universe=1, address=1, fid=101),
        _candidate(candidate_id="b", universe=2, address=1, fid=102),
    )
    plan = plan_addresses(targets, footprints={"a": 16, "b": 16}, occupied={})
    assert [entry.candidate_id for entry in plan.entries] == ["a", "b"]
    assert plan.exclusions == ()


def test_console_occupied_address_is_excluded_with_reason():
    """AC-016② — 도면 주소가 콘솔에서 이미 점유되어 있으면 제외되고 사유가 보고된다."""
    targets = (_candidate(candidate_id="a", universe=1, address=1, fid=101),)
    plan = plan_addresses(targets, footprints={"a": 16}, occupied={1: ((1, 8),)})
    assert plan.entries == ()
    assert len(plan.exclusions) == 1
    exclusion = plan.exclusions[0]
    assert exclusion.candidate_id == "a"
    assert exclusion.code == ADDRESS_ALREADY_OCCUPIED
    assert exclusion.reason
    assert exclusion.to_dict()["label"] == target_exclusion_label(ADDRESS_ALREADY_OCCUPIED)


def test_occupancy_check_uses_the_whole_footprint_span_not_just_the_start():
    """AC-016② — 시작 주소가 비어 있어도 **점유폭 구간**이 겹치면 제외한다."""
    targets = (_candidate(candidate_id="a", universe=1, address=1, fid=101),)
    # 콘솔이 10~20을 점유 → 1..16 요청은 겹친다(시작 1은 비어 있다).
    plan = plan_addresses(targets, footprints={"a": 16}, occupied={1: ((10, 20),)})
    assert plan.entries == ()
    assert plan.exclusions[0].code == ADDRESS_ALREADY_OCCUPIED


def test_unknown_footprint_is_excluded_rather_than_guessed():
    """점유폭을 모르면 **추측하지 않고 제외**한다 — M0 함정 7의 직접 결과."""
    targets = (_candidate(candidate_id="a", universe=1, address=1, fid=101),)
    plan = plan_addresses(targets, footprints={}, occupied={})
    assert plan.entries == ()
    assert plan.exclusions[0].code == FOOTPRINT_UNKNOWN


def test_no_relocation_path_exists():
    """AC-016③ — 임의의 빈 주소로 재배치하는 경로가 0건.

    점유된 항목은 **제외**되며, 계획된 항목의 주소는 **언제나 도면 주소 그대로**다.
    """
    targets = (
        _candidate(candidate_id="a", universe=1, address=1, fid=101),
        _candidate(candidate_id="b", universe=1, address=200, fid=102),
    )
    plan = plan_addresses(targets, footprints={"a": 16, "b": 16}, occupied={1: ((1, 8),)})
    assert [entry.candidate_id for entry in plan.entries] == ["b"]
    # 살아남은 항목은 도면 주소를 유지한다.
    assert plan.entries[0].address == 200
    # 제외된 항목이 다른 주소로 옮겨 붙지 않았다.
    assert all(entry.candidate_id != "a" for entry in plan.entries)


def test_relocation_control_is_caught():
    """AC-016③ 비공허성 — 재배치 로직을 심은 사본에서 "주소 불변" 단정이 실제로 실패한다."""
    targets = (_candidate(candidate_id="a", universe=1, address=1, fid=101),)
    plan = plan_addresses(targets, footprints={"a": 16}, occupied={})
    assert plan.entries[0].address == 1

    # 재배치를 심은 사본: 계획 결과의 주소를 빈 곳으로 옮긴다.
    relocated = AddressPlanEntry(
        candidate_id="a", universe=1, address=64, footprint=16, end_address=79
    )
    assert relocated.address != targets[0].address  # 단정이 깨지는 것을 확인


def test_planned_addresses_are_always_the_designed_addresses():
    """AC-016③ — 계획된 주소 집합은 도면 주소 집합의 부분집합이다."""
    targets = (
        _candidate(candidate_id="a", universe=1, address=1, fid=101),
        _candidate(candidate_id="b", universe=1, address=17, fid=102),
        _candidate(candidate_id="c", universe=2, address=5, fid=103),
    )
    plan = plan_addresses(targets, footprints={"a": 16, "b": 16, "c": 16}, occupied={})
    designed = {(target.universe, target.address) for target in targets}
    planned = {(entry.universe, entry.address) for entry in plan.entries}
    assert planned <= designed


def test_exclusion_codes_are_registered_vocabulary():
    """새 제외 사유가 닫힌 어휘에 등재되어 있다(`server/vwx/verdicts.py`)."""
    for code in (ADDRESS_ALREADY_OCCUPIED, ADDRESS_OVERLAP_IN_PLAN, FOOTPRINT_UNKNOWN):
        assert code in TARGET_EXCLUSION_REASON
        assert target_exclusion_label(code)


# --------------------------------------------------------------------------
# 생성기 ↔ 주소 계획 결합 — 계획된 항목만 Lua가 된다
# --------------------------------------------------------------------------


def test_plugin_source_renders_one_call_per_planned_entry():
    entries = [_entry(fid=101, address=1), _entry(fid=102, address=17)]
    source = render_addfixtures_plugin(entries)
    assert source.count("AddFixtures") == len(entries)
    assert 'fid = "101"' in source
    assert 'fid = "102"' in source


def test_plugin_source_is_a_single_lua_module_returning_main():
    """룰북 형태: `local function main() ... end return main`."""
    source = render_addfixtures_plugin([_entry()])
    assert source.startswith("local function main()")
    assert source.rstrip().endswith("return main")


def test_empty_entry_list_produces_no_addfixtures_call():
    source = render_addfixtures_plugin([])
    assert "AddFixtures" not in source


# --------------------------------------------------------------------------
# --- round17 luagen 전달물 생성 본체 전수 게이트 (LuagenGates) ---
#
# **round17 치명 #1·#2가 성립한 기제**: 전달물 Lua를 만드는 본체(`luagen.py`)에 대한
# 단정이 전부 **문자열 부분일치**였다. `'patch = { "1.1" }' in call` 한 줄과 `in`/키집합
# 대조만으로는 (a) 이스케이프 표의 항목이 사라져 **문자열 리터럴을 탈출**하는 것도,
# (b) 주소쌍 `{universe}.{address}`가 뒤집히는 것도 보이지 않는다(표본이 u==a==1).
#
# 여기서는 세 층으로 닫는다.
#   L1 **의미론** — 생성된 플러그인을 `lupa`의 **진짜 Lua 5.4**로 컴파일·실행하고,
#      `os.execute`/`io.popen`/`Cmd` 등을 트랩한 샌드박스에서 `AddFixtures`가 **실제로
#      받은 인자값**을 회수해 대조한다. 문자열 대조가 아니라 Lua 파서가 판정한다.
#   L2 **왕복** — 생성된 리터럴을 파이썬 디코더로 되돌려 `decode(encode(x)) == x`.
#      디코더는 Lua 문법을 재구현하지 않고 짧은 리터럴 규칙만 최소로 구현하며,
#      **진짜 Lua와 교차검증**(`test_r17_decoder_agrees_with_real_lua`)한다.
#   L3 **전단사 표** — 이스케이프 의무·필드 렌더·생성 본체 소스 표현·모듈 경계 스캔.
#      기대값은 프로덕션에서 파생하지 않고 **독립 저작**하며, 양방향 일치를 요구한다.
#
# **[HARD 규율 1] 도달 범위 재도출**: 게이트가 모듈 경계에서 멈추지 않도록
# `server/vwx/` **전 모듈**을 AST로 훑어 같은 성질의 자리를 전수 열거한다
# (`_R17_ESCAPE_TABLE_SITES` · `_R17_TOKEN_JOIN_SITES` · `_R17_DELIVERABLE_INT_SITES`).
#
# 프로덕션(`server/vwx/luagen.py`)은 **한 줄도 고치지 않았다** — 현 동작은 옳다.
# 빠져 있던 것은 게이트뿐이다.
# --------------------------------------------------------------------------


_LUAGEN_UNDER_TEST = "server.vwx._luagen_under_test"


def _load_luagen(source: str) -> dict[str, object]:
    """`luagen.py` 소스를 **진짜 모듈로** 적재한다 — `test_autopatch_execute._load` 관례.

    `dataclass`가 `sys.modules` 조회를 하므로 네임스페이스 dict만으로는 적재되지 않는다.
    대조군은 이 사본에 대해 **프로덕션 단정 그 자체**(`_r17_gate_failures`)를 다시 돌린다 —
    테스트 로컬 헬퍼를 검사하는 자기확인이 아니다.
    """
    module = ModuleType(_LUAGEN_UNDER_TEST)
    module.__file__ = str(LUAGEN_PATH)
    saved = sys.modules.get(_LUAGEN_UNDER_TEST)
    sys.modules[_LUAGEN_UNDER_TEST] = module
    try:
        exec(compile(source, str(LUAGEN_PATH), "exec"), module.__dict__)
    finally:
        if saved is None:
            del sys.modules[_LUAGEN_UNDER_TEST]
        else:
            sys.modules[_LUAGEN_UNDER_TEST] = saved
    return module.__dict__


# --------------------------------------------------------------------------
# L2 — Lua 짧은 문자열 리터럴 디코더 (테스트 전용, 최소 구현)
# --------------------------------------------------------------------------


class _R17LuaLiteralError(AssertionError):
    """디코더가 **하나의 완결된** Lua 짧은 문자열 리터럴로 읽지 못했다."""


# Lua 5.4 짧은 리터럴의 글자 이스케이프. 여기 없는 글자가 역슬래시 뒤에 오면 거부한다 —
# 관대하게 넘기면 "잘못 이스케이프된 산출물"이 왕복을 통과해 게이트가 공허해진다.
_R17_LUA_LETTER_UNESCAPES = MappingProxyType(
    {
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
        '"': '"',
        "'": "'",
    }
)


def _r17_decode_lua_literal(text: str) -> str:
    """`text` **전체**가 하나의 큰따옴표 Lua 짧은 리터럴이라고 보고 값을 복원한다.

    탈출을 잡는 핵심은 두 규칙이다.
    - 닫는 따옴표가 **마지막 글자가 아니면** 거부한다 → 리터럴을 빠져나와 그 뒤에 코드를
      붙인 산출물(치명 #1의 실제 형태)이 여기서 걸린다.
    - 알 수 없는 역슬래시 이스케이프를 거부한다 → 역슬래시가 이스케이프되지 않은 산출물
      (`"back\\slash"`)이 걸린다.
    """
    if len(text) < 2 or text[0] != '"':
        raise _R17LuaLiteralError(f"큰따옴표 리터럴로 시작하지 않는다: {text!r}")
    out: list[str] = []
    index = 1
    while index < len(text):
        char = text[index]
        if char == '"':
            if index != len(text) - 1:
                raise _R17LuaLiteralError(
                    f"리터럴이 문자열 끝보다 먼저 닫혔다 — 탈출 성립: {text!r}"
                )
            return "".join(out)
        if char in "\n\r":
            raise _R17LuaLiteralError(f"짧은 리터럴 안에 날 줄바꿈이 있다: {text!r}")
        if char != "\\":
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(text):
            raise _R17LuaLiteralError(f"역슬래시로 끝났다: {text!r}")
        escape = text[index]
        if escape.isdigit():
            digits = ""
            while index < len(text) and text[index].isdigit() and len(digits) < 3:
                digits += text[index]
                index += 1
            code = int(digits)
            if code > 255:
                raise _R17LuaLiteralError(f"십진 이스케이프가 255를 넘는다: {text!r}")
            out.append(chr(code))
            continue
        replacement = _R17_LUA_LETTER_UNESCAPES.get(escape)
        if replacement is None:
            raise _R17LuaLiteralError(f"알 수 없는 이스케이프 \\{escape}: {text!r}")
        out.append(replacement)
        index += 1
    raise _R17LuaLiteralError(f"닫히지 않은 리터럴: {text!r}")


# --------------------------------------------------------------------------
# L1 — 진짜 Lua 5.4 샌드박스
# --------------------------------------------------------------------------

# `AddFixtures`가 **실제로 받은 값**을 타입까지 붙여 회수한다. `tostring`만 쓰면
# `fid = "7351"`(문자열)과 `fid = 7351`(숫자)이 구별되지 않는다.
_R17_LUA_SANDBOX = r"""
__CALLS = {}
__SIDE = {}

local function trap(tag)
  return function(...)
    local parts = {}
    for _, v in ipairs({ ... }) do parts[#parts + 1] = tostring(v) end
    table.insert(__SIDE, tag .. "(" .. table.concat(parts, ",") .. ")")
    return true
  end
end

os = { execute = trap("os.execute"), remove = trap("os.remove"), exit = trap("os.exit") }
io = { open = trap("io.open"), popen = trap("io.popen"), write = trap("io.write") }
Cmd = trap("Cmd")
Printf = trap("Printf")
dofile = trap("dofile")
loadfile = trap("loadfile")
require = trap("require")

local anymt = {}
anymt.__index = function(t, k)
  return setmetatable({ __chain = rawget(t, "__chain") .. "[" .. tostring(k) .. "]" }, anymt)
end
anymt.__call = function(t)
  return setmetatable({ __chain = rawget(t, "__chain") .. "()" }, anymt)
end
function Patch() return setmetatable({ __chain = "Patch()" }, anymt) end
function Root() return setmetatable({ __chain = "Root()" }, anymt) end

local describe
describe = function(v)
  if type(v) == "table" then
    if rawget(v, "__chain") ~= nil then return "object:" .. rawget(v, "__chain") end
    local acc = {}
    for i = 1, #v do acc[i] = describe(v[i]) end
    return "table:[" .. table.concat(acc, ",") .. "]"
  end
  return type(v) .. ":" .. tostring(v)
end

function AddFixtures(t)
  local rec = {}
  for k, v in pairs(t) do rec[tostring(k)] = describe(v) end
  table.insert(__CALLS, rec)
end

function __run(src)
  local f, e = load(src, "plugin")
  if not f then return "COMPILE:" .. tostring(e) end
  local ok, m = pcall(f)
  if not ok then return "CHUNK:" .. tostring(m) end
  if type(m) ~= "function" then return "NOTFN:" .. type(m) end
  local ok2, e2 = pcall(m)
  if not ok2 then return "RUN:" .. tostring(e2) end
  return ""
end
"""


def _r17_run_lua(source: str) -> tuple[str, list[dict[str, str]], list[str]]:
    """생성된 Lua를 **진짜 Lua 5.4**에서 컴파일·실행하고 (오류, 호출기록, 부작용)을 준다."""
    runtime = lua54.LuaRuntime()
    runtime.execute(_R17_LUA_SANDBOX)
    error = runtime.globals().__run(source)
    calls = [dict(rec.items()) for rec in runtime.globals().__CALLS.values()]
    side = list(runtime.globals().__SIDE.values())
    return str(error), calls, side


# --------------------------------------------------------------------------
# L3 표 ① — 이스케이프 의무 (독립 저작 기대값 · 프로덕션 표와 양방향 일치)
# --------------------------------------------------------------------------

# 키 = 이스케이프되어야 하는 글자. 값 = 값 `"A" + 글자 + "B"`에 대해 산출되어야 하는
# **리터럴 전문**. 프로덕션 `_LUA_ESCAPES`를 복사하지 않고 Lua 규격에서 독립적으로
# 적었다 — 그래서 프로덕션 항목을 지우거나 무효화하면 여기서 깨진다.
_R17_ESCAPE_OBLIGATIONS = MappingProxyType(
    {
        "\\": '"A\\\\B"',
        '"': '"A\\"B"',
        "\n": '"A\\nB"',
        "\r": '"A\\rB"',
        "\t": '"A\\tB"',
    }
)

# 왕복 대조에 쓰는 값 모음. 제어문자 전 범위 + 이스케이프 대상 + 적대적 실물.
_R17_INJECTION_PAYLOAD = 'rig\\" }); os.execute([[touch /tmp/PWNED]]) --'
_R17_ROUNDTRIP_CORPUS = (
    *(f"A{chr(code)}B" for code in range(0x00, 0x100)),
    *(f"A{char}B" for char in _R17_ESCAPE_OBLIGATIONS),
    _R17_INJECTION_PAYLOAD,
    'x" , mode = Root() --',
    "back\\slash",
    'plain " and \\ together',
    "한글 이름 350",
    "",
)


# --------------------------------------------------------------------------
# L3 표 ② — 여섯 필드 렌더 전단사 (u ≠ a · 여섯 값 전부 구분 가능)
# --------------------------------------------------------------------------

# round16이 M50("계수 1 표본만 있으면 하드코딩이 안 보인다")을 고치고도 주소 쌍에는
# u == a == 1 표본만 남겨 두었다. 여기서는 **여섯 값을 서로 구분 가능하게** 주고,
# 특히 u(12) ≠ a(349)로 둔다.
_R17_FIELD_PROBE_KWARGS = MappingProxyType(
    {
        "console_type": "TypeAlpha",
        "console_mode": "ModeBravo",
        "fid": 7351,
        "name": "NameCharlie",
        "universe": 12,
        "address": 349,
    }
)

# 각 필드가 렌더되어야 하는 **텍스트 전문**(독립 저작).
_R17_FIELD_SITES = MappingProxyType(
    {
        "mode": 'Patch().FixtureTypes["TypeAlpha"].DMXModes["ModeBravo"]',
        "amount": "1",
        "fid": '"7351"',
        "idtype": '"Fixture"',
        "name": '"NameCharlie"',
        "patch": '{ "12.349" }',
    }
)

# 같은 여섯 필드가 **Lua 런타임에서 실제로 갖는 값**(타입 포함).
_R17_LUA_SEMANTIC_FIELDS = MappingProxyType(
    {
        "mode": "object:Patch()[FixtureTypes][TypeAlpha][DMXModes][ModeBravo]",
        "amount": "number:1",
        "fid": "string:7351",
        "idtype": "string:Fixture",
        "name": "string:NameCharlie",
        "patch": "table:[string:12.349]",
    }
)

# `_lua_int`를 통과해야 하는 정수 필드 — bool 가드가 여기 걸린다(#7의 luagen 몫).
_R17_DELIVERABLE_INT_FIELDS = ("fid", "universe", "address")


# --------------------------------------------------------------------------
# L3 표 ③ — 모듈 경계를 넘는 소스 표현 고정
# --------------------------------------------------------------------------

# `_field_values`의 지역 바인딩과 여섯 필드 값 표현을 **`ast.unparse` 전문**으로 고정한다.
# 값 교환(예: name ↔ idtype)이나 주소쌍 반전은 여기서 곧바로 깨진다.
_R17_FIELD_VALUE_EXPRESSIONS = MappingProxyType(
    {
        "mode": "mode_handle",
        "amount": "'1'",
        "fid": "_lua_string(str(_lua_int(entry.fid)))",
        "idtype": "_lua_string(FIXTURE_IDTYPE)",
        "name": "_lua_string(entry.name)",
        "patch": "'{ ' + patch_address + ' }'",
    }
)

_R17_FIELD_LOCAL_EXPRESSIONS = MappingProxyType(
    {
        "mode_handle": (
            "f'Patch().FixtureTypes[{_lua_string(entry.console_type)}]"
            ".DMXModes[{_lua_string(entry.console_mode)}]'"
        ),
        "patch_address": "_lua_string(f'{_lua_int(entry.universe)}.{_lua_int(entry.address)}')",
    }
)

# `server/vwx/` **전 모듈**에서 "한 글자 키만 담은 매핑 상수"(= 이스케이프 표) 전수.
# 새 이스케이프 표가 어느 모듈에 생기든 이 표가 실패해 게이트를 요구한다.
_R17_ESCAPE_TABLE_SITES = (("luagen.py", "_LUA_ESCAPES"),)

# `server/vwx/` **전 모듈**에서 "스칼라 여럿을 구분자 하나로 이어 하나의 토큰으로 만드는
# f-string" 전수. 피연산자 순서가 뒤집히면 `ast.unparse` 전문이 달라져 실패한다 —
# 치명 #2와 **같은 성질**의 자리를 모듈 경계 밖까지 덮는다.
_R17_TOKEN_JOIN_SITES = (
    ("address.py", "f'{universe}.{address}'"),
    # [round24 후속] 자리 판정이 쓰는 좌표 — `address.py`와 **같은 순서 규약**
    # (유니버스 먼저, 그다음 주소)이다. 뒤집으면 3.001을 1.003으로 읽어 엉뚱한
    # 유니버스의 점유를 보고 "비었다"고 답한다. 앞의 것은 요청을 정규화해 되돌려
    # 주는 자리, 뒤의 것은 배치된 자리 하나를 사람에게 보여 주는 자리다.
    ("addressfit.py", "f'{parsed.universe}.{parsed.address}'"),
    ("addressfit.py", "f'{self.universe}.{self.address}'"),
    # [round24 후속] 인테이크가 자동 배정 결과를 사용자에게 보여 줄 때의 미리보기.
    # 판정이 아니라 **표시**다 — 실제 행의 주소는 `Universe`/`U Address` 칸이 나른다.
    ("intake.py", "f'{u}.{a}'"),
    # [round24 후속] 조달 안내가 보여 주는 설치 경로. 콘솔에 보내는 값이 아니라
    # 사람이 읽고 파일을 놓을 자리다 — 어긋나면 Library 탭에서 못 찾는다.
    ("typesource.py", "f\"{FIXTURE_TYPE_HINT}/{self.suggested_filename or '<이름>.gdtf'}\""),
    ("luagen.py", "f'{_lua_int(entry.universe)}.{_lua_int(entry.address)}'"),
    ("patchplan.py", "f'{FID_FIXTURE_ROOT}/{child_index}'"),
    # --- round19 절단 복구 스윕 (TruncationSweep) — 스윕 프로브의 슬롯 경로.
    # 위 열거 경로와 **같은 규약**이다(루트 + `/` + 슬롯 번호). 여기서 슬롯 번호 대신
    # 열거 리스트의 위치를 넣으면 responder가 `children[wanted_slot]`로 답해 엉뚱한
    # 픽스처의 FID를 기존 FID로 적재한다 — `slots_established` 전제가 막는 사고다.
    ("patchplan.py", "f'{FID_FIXTURE_ROOT}/{slot}'"),
    # [round23 R21-A] FID 점유자의 좌표를 묻는 프로브(`_slot_address`) — 위 두 자리와
    # **같은 규약**(루트 + `/` + 슬롯 번호)이고 같은 슬롯 번호를 쓴다. 여기에 슬롯이 아닌
    # 값(열거 위치 등)이 들어가면 엉뚱한 픽스처의 주소를 그 FID의 소유자 좌표로 읽어,
    # 남의 픽스처를 "내가 만든 것"으로 승격시킨다 — R21-A 승격 규칙의 입력이 오염된다.
    ("patchplan.py", "f'{FID_FIXTURE_ROOT}/{slot}'"),
    # [round18 R18-J] 2단계 고지가 가리키는 도면 좌표 — `address.py`와 **같은 순서 규약**
    # (유니버스 먼저, 그다음 주소)이다. 뒤집으면 조작자가 다른 픽스처를 찾아간다.
    ("patchplan.py", "f'{universe}.{address}'"),
    (
        "typemap.py",
        "f'{FIXTURE_TYPE_LIBRARY_ROOT}/{console_type.index}/{DMX_MODES_SEGMENT}"
        "/{console_mode.index}/{DMX_CHANNELS_SEGMENT}'",
    ),
    # [round21 R20-A ⓑ] 표적 회수 스윕의 프로브 경로 — `recover_requested_types`.
    # 인덱스는 `1..childCount` 유계 루프의 정수라 사용자 문자열이 섞이지 않는다.
    ("typemap.py", "f'{FIXTURE_TYPE_LIBRARY_ROOT}/{index}'"),
    ("typemap.py", "f'{FIXTURE_TYPE_LIBRARY_ROOT}/{index}/{DMX_MODES_SEGMENT}'"),
    ("typemap.py", "f'{modes_path}/{mode_index}'"),
    ("typemap.py", "f'{mode_path}/{DMX_CHANNELS_SEGMENT}'"),
)

# `luagen`에서 `_lua_int`를 통과하는 자리 전수 — 정수가 전달물에 닿는 모든 경로.
_R17_DELIVERABLE_INT_SITES = (
    "_lua_int(entry.universe)",
    "_lua_int(entry.address)",
    "_lua_int(entry.fid)",
)

# 소스 전문 앵커. **부분문자열이 아니라 전문 등장 횟수**로 고정한다(round17 #6의 교훈:
# 부분일치 앵커는 뒤에 덧붙이는 조작을 통과시킨다).
_R17_SOURCE_ANCHORS = MappingProxyType(
    {
        "patch_pair": 'f"{_lua_int(entry.universe)}.{_lua_int(entry.address)}"',
        "bool_guard": "    if isinstance(value, bool) or not isinstance(value, int):",
        "control_boundary": "        elif ord(char) < 0x20 or ord(char) == 0x7F:",
    }
)


def _r17_vwx_modules() -> list[Path]:
    """`server/vwx` 아래 모듈 경로 — 재귀성·제외는 공용 순회 한 자리가 정한다."""
    return list(iter_vwx_modules())


def _r17_scan_escape_tables() -> list[tuple[str, str]]:
    """`server/vwx/` 전 모듈에서 한 글자 키만 담은 매핑 상수를 전수 열거한다."""
    found: list[tuple[str, str]] = []
    for path in _r17_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign | ast.AnnAssign) or node.value is None:
                continue
            value = node.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "MappingProxyType"
                and value.args
            ):
                value = value.args[0]
            if not isinstance(value, ast.Dict) or not value.keys:
                continue
            if not all(
                isinstance(key, ast.Constant) and isinstance(key.value, str) and len(key.value) == 1
                for key in value.keys
            ):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            found.extend((vwx_module_label(path), ast.unparse(target)) for target in targets)
    return sorted(found)


def _r17_scan_token_joins() -> list[tuple[str, str]]:
    """`server/vwx` **전 모듈**에서 `{a}<sep>{b}` 꼴로 **오직 스칼라와 구분자만**으로
    이루어진 f-string을 전수 열거한다(스코프: `server/vwx/**/*.py` 디렉터리 전체)."""
    found: list[tuple[str, str]] = []
    for path in _r17_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr) or len(node.values) < 3:
                continue
            if len(node.values) % 2 == 0:
                continue
            if not all(isinstance(part, ast.FormattedValue) for part in node.values[0::2]):
                continue
            if not all(
                isinstance(part, ast.Constant) and part.value in {".", "/"}
                for part in node.values[1::2]
            ):
                continue
            found.append((vwx_module_label(path), ast.unparse(node)))
    return sorted(found)


def _r17_scan_deliverable_int_sites() -> list[str]:
    tree = ast.parse(LUAGEN_SOURCE)
    return [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_lua_int"
    ]


# --------------------------------------------------------------------------
# 프로덕션 단정 본체 — 원본과 **사보타주 사본에 똑같이** 적용한다
# --------------------------------------------------------------------------


def _r17_gate_failures(namespace) -> list[str]:
    """적재된 `luagen` 네임스페이스에 대해 게이트 전부를 돌리고 **깨진 이름**을 준다.

    원본에 대해서는 `[]`여야 하고, 대조군(사보타주 사본)에 대해서는 정확히 그 뮤테이션이
    건드린 게이트 이름이 나와야 한다. 로컬 헬퍼 자기확인이 아니라 **프로덕션 함수**
    (`_lua_string` · `_field_values` · `render_addfixtures_call/plugin`)를 실행한다.
    """
    failures: list[str] = []
    lua_string = namespace["_lua_string"]
    field_values = namespace["_field_values"]
    render_call = namespace["render_addfixtures_call"]
    render_plugin = namespace["render_addfixtures_plugin"]
    entry_cls = namespace["LuaPatchEntry"]
    error_cls = namespace["LuaGenerationError"]
    probe = entry_cls(**_R17_FIELD_PROBE_KWARGS)

    # ① 이스케이프 의무 — 표의 **모든** 항목.
    for char, expected in _R17_ESCAPE_OBLIGATIONS.items():
        try:
            rendered = lua_string(f"A{char}B")
        except Exception as exc:  # noqa: BLE001 - 어떤 예외든 게이트 실패로 본다
            failures.append(f"escape:{char!r}:raised:{exc!r}")
            continue
        if rendered != expected:
            failures.append(f"escape:{char!r}:{rendered!r}!={expected!r}")

    # ② 왕복 — 인코딩한 리터럴을 되돌려 원래 값이 나와야 한다.
    for value in _R17_ROUNDTRIP_CORPUS:
        try:
            literal = lua_string(value)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"roundtrip:{value!r}:raised:{exc!r}")
            continue
        try:
            decoded = _r17_decode_lua_literal(literal)
        except _R17LuaLiteralError as exc:
            failures.append(f"roundtrip:{value!r}:{exc}")
            continue
        if decoded != value:
            failures.append(f"roundtrip:{value!r}:decoded={decoded!r}")

    # ③ 날 제어문자가 리터럴에 남지 않는다.
    for code in (*range(0x00, 0x20), 0x7F):
        literal = lua_string(f"A{chr(code)}B")
        if chr(code) in literal:
            failures.append(f"rawctl:{code}")

    # ④ 여섯 필드 렌더 전문.
    values = field_values(probe)
    if set(values) != set(_R17_FIELD_SITES):
        failures.append(f"fieldset:{sorted(values)}")
    for key, expected in _R17_FIELD_SITES.items():
        if values.get(key) != expected:
            failures.append(f"field:{key}:{values.get(key)!r}!={expected!r}")

    # ⑤ 주소쌍은 **순서 있는 쌍**이다 — u와 a를 바꾸면 산출이 달라져야 한다.
    swapped = entry_cls(
        **{**_R17_FIELD_PROBE_KWARGS, "universe": 349, "address": 12},
    )
    if field_values(swapped)["patch"] == values["patch"]:
        failures.append("patch_order_insensitive")
    # 타입·모드도 마찬가지다.
    crossed = entry_cls(
        **{**_R17_FIELD_PROBE_KWARGS, "console_type": "ModeBravo", "console_mode": "TypeAlpha"},
    )
    if field_values(crossed)["mode"] == values["mode"]:
        failures.append("mode_order_insensitive")

    # ⑥ bool 가드 — `fid=True`가 전달물에 `"True"`로 실리면 안 된다.
    for field in _R17_DELIVERABLE_INT_FIELDS:
        try:
            render_call(entry_cls(**{**_R17_FIELD_PROBE_KWARGS, field: True}))
        except error_cls:
            continue
        except Exception as exc:  # noqa: BLE001
            failures.append(f"bool:{field}:wrong_error:{exc!r}")
            continue
        failures.append(f"bool:{field}:accepted")

    # ⑦ 진짜 Lua 5.4 — 컴파일·실행·부작용·인자값.
    hostile = entry_cls(
        console_type="TypeAlpha",
        console_mode="ModeBravo",
        fid=9,
        name=_R17_INJECTION_PAYLOAD,
        universe=3,
        address=77,
    )
    source = render_plugin([probe, hostile])
    error, calls, side = _r17_run_lua(source)
    if error:
        failures.append(f"lua:{error}")
    elif side:
        failures.append(f"lua:side_effect:{side}")
    elif len(calls) != 2:
        failures.append(f"lua:call_count:{len(calls)}")
    else:
        if calls[0] != dict(_R17_LUA_SEMANTIC_FIELDS):
            failures.append(f"lua:fields:{calls[0]}")
        if calls[1].get("name") != f"string:{_R17_INJECTION_PAYLOAD}":
            failures.append(f"lua:hostile_name:{calls[1].get('name')!r}")
        if calls[1].get("patch") != "table:[string:3.77]":
            failures.append(f"lua:hostile_patch:{calls[1].get('patch')!r}")
    return failures


# --------------------------------------------------------------------------
# 사보타주 사본 만들기 — git을 쓰지 않고 **소스 문자열만** 변형한다
# --------------------------------------------------------------------------


def _r17_escape_row_lineno(char: str) -> int:
    """`_LUA_ESCAPES`에서 `char` 항목이 적힌 소스 줄 번호(줄바꿈 재배치에 강하다)."""
    tree = ast.parse(LUAGEN_SOURCE)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key in node.keys:
            if isinstance(key, ast.Constant) and key.value == char:
                return key.lineno
    raise AssertionError(f"_LUA_ESCAPES에 {char!r} 항목이 없다")


def _r17_source_without_escape_row(char: str) -> str:
    lines = LUAGEN_SOURCE.splitlines(keepends=True)
    del lines[_r17_escape_row_lineno(char) - 1]
    return "".join(lines)


def _r17_source_with_neutralised_escape(char: str) -> str:
    """항목을 지우지 않고 **사실상 무효화**한다(`"\\\\": "\\\\"` 꼴)."""
    lines = LUAGEN_SOURCE.splitlines(keepends=True)
    index = _r17_escape_row_lineno(char) - 1
    lines[index] = f"        {char!r}: {char!r},\n"
    return "".join(lines)


def _r17_replace_anchor(anchor: str, replacement: str) -> str:
    """앵커를 **전문 등장 1회**로 확인하고 치환한다 — 부분일치 앵커를 쓰지 않는다."""
    original = _R17_SOURCE_ANCHORS[anchor]
    assert LUAGEN_SOURCE.count(original) == 1, f"앵커 전문이 정확히 1회가 아니다: {anchor}"
    return LUAGEN_SOURCE.replace(original, replacement)


# `[round17 수용기준]` 표 — 각 행이 심어야 할 뮤테이션과 **깨져야 할 게이트 이름**이다.
_R17_MUTATIONS = (
    ("escape_drop_backslash", lambda: _r17_source_without_escape_row("\\"), "escape:'\\\\'"),
    ("escape_drop_quote", lambda: _r17_source_without_escape_row('"'), "escape:'\"'"),
    ("escape_drop_newline", lambda: _r17_source_without_escape_row("\n"), "escape:'\\n'"),
    ("escape_drop_return", lambda: _r17_source_without_escape_row("\r"), "escape:'\\r'"),
    ("escape_drop_tab", lambda: _r17_source_without_escape_row("\t"), "escape:'\\t'"),
    (
        "escape_neutralise_backslash",
        lambda: _r17_source_with_neutralised_escape("\\"),
        "escape:'\\\\'",
    ),
    ("escape_neutralise_quote", lambda: _r17_source_with_neutralised_escape('"'), "escape:'\"'"),
    (
        "patch_pair_swapped",
        lambda: _r17_replace_anchor(
            "patch_pair", 'f"{_lua_int(entry.address)}.{_lua_int(entry.universe)}"'
        ),
        "field:patch",
    ),
    (
        "patch_pair_colon",
        lambda: _r17_replace_anchor(
            "patch_pair", 'f"{_lua_int(entry.universe)}:{_lua_int(entry.address)}"'
        ),
        "field:patch",
    ),
    (
        "bool_guard_removed",
        lambda: _r17_replace_anchor("bool_guard", "    if not isinstance(value, int):"),
        "bool:fid",
    ),
    (
        "control_boundary_off_by_one",
        lambda: _r17_replace_anchor(
            "control_boundary", "        elif ord(char) < 0x1F or ord(char) == 0x7F:"
        ),
        "rawctl:31",
    ),
)


# --------------------------------------------------------------------------
# 게이트 본체 — 프로덕션 모듈에 직접 건다
# --------------------------------------------------------------------------


def test_r17_production_luagen_passes_every_gate():
    """[round17 #1·#2·#7] 프로덕션 `luagen.py`가 게이트 전부를 통과한다(기준선)."""
    assert _r17_gate_failures(vars(luagen)) == []


def test_r17_loaded_copy_of_pristine_source_passes_every_gate():
    """대조군 적재 경로가 원본을 왜곡하지 않는다 — 사본 판정의 전제."""
    assert _r17_gate_failures(_load_luagen(LUAGEN_SOURCE)) == []


@pytest.mark.parametrize(
    ("mutation_id", "mutate", "expected_gate"),
    _R17_MUTATIONS,
    ids=[row[0] for row in _R17_MUTATIONS],
)
def test_r17_each_acceptance_mutation_is_killed(mutation_id, mutate, expected_gate):
    """[round17 수용기준] 심어야 할 뮤테이션 전부를 **상시 대조군으로 굳혀 둔다**.

    사본에 뮤테이션을 심고 **같은 프로덕션 단정**을 돌려, 그 뮤테이션이 건드린 게이트가
    실제로 깨지는지 본다. 게이트가 언젠가 공허해지면 이 테스트가 먼저 실패한다.
    """
    mutated = mutate()
    assert mutated != LUAGEN_SOURCE, f"뮤테이션이 소스를 바꾸지 못했다: {mutation_id}"
    failures = _r17_gate_failures(_load_luagen(mutated))
    assert any(name.startswith(expected_gate) for name in failures), (
        mutation_id,
        expected_gate,
        failures,
    )


def test_r17_escape_obligation_table_is_bijective_with_production():
    """[round17 #1] `_LUA_ESCAPES`에서 항목을 **더하거나 빼면** 실패한다.

    기대값은 프로덕션에서 파생하지 않고 독립 저작했으므로 이 일치는 항진식이 아니다.
    """
    assert set(_R17_ESCAPE_OBLIGATIONS) == set(luagen._LUA_ESCAPES)
    assert len(_R17_ESCAPE_OBLIGATIONS) == len(luagen._LUA_ESCAPES)
    assert all(len(char) == 1 for char in luagen._LUA_ESCAPES)


@pytest.mark.parametrize(
    ("char", "expected"),
    sorted(_R17_ESCAPE_OBLIGATIONS.items()),
    ids=[repr(char) for char, _ in sorted(_R17_ESCAPE_OBLIGATIONS.items())],
)
def test_r17_each_escape_obligation_holds_on_the_public_path(char, expected):
    """[round17 #1] `_LUA_ESCAPES`의 어느 항목을 지워도(백슬래시 포함) 실패한다.

    비공개 인코더와 **공개 렌더 경로** 양쪽에서 같은 리터럴이 나와야 한다.
    """
    assert luagen._lua_string(f"A{char}B") == expected
    call = render_addfixtures_call(_entry(name=f"A{char}B"))
    assert f"name = {expected}" in call
    assert len(call.splitlines()) == 1


@pytest.mark.parametrize(
    "value", _R17_ROUNDTRIP_CORPUS, ids=[repr(value) for value in _R17_ROUNDTRIP_CORPUS]
)
def test_r17_encoded_string_round_trips(value):
    """[round17 #1] 탈출 불가 — `decode(encode(x)) == x`.

    리터럴이 문자열 끝보다 먼저 닫히면(=탈출) 디코더가 거부한다.
    """
    assert _r17_decode_lua_literal(luagen._lua_string(value)) == value


@pytest.mark.parametrize(
    ("broken", "why"),
    [
        ('"back\\slash"', "이스케이프되지 않은 역슬래시"),
        ('"rig\\\\" }); os.execute([[x]]) --"', "리터럴을 빠져나온 뒤 코드가 붙었다"),
        ('"a\nb"', "짧은 리터럴 안의 날 줄바꿈"),
        ('"a\\', "역슬래시로 끝났다"),
        ('"unterminated', "닫히지 않았다"),
        ("noquote", "따옴표로 시작하지 않는다"),
    ],
)
def test_r17_decoder_rejects_broken_encodings(broken, why):
    """디코더 비공허성 — 잘못 이스케이프된 리터럴에서 **왕복이 실제로 깨진다**."""
    with pytest.raises(_R17LuaLiteralError):
        _r17_decode_lua_literal(broken)
    assert why


def test_r17_decoder_agrees_with_real_lua():
    """디코더가 Lua 문법을 잘못 재구현하지 않았다 — **진짜 Lua 5.4**와 교차검증한다."""
    runtime = lua54.LuaRuntime()
    runtime.execute(_R17_LUA_SANDBOX)
    probe = runtime.eval("function(src) local f = load('return ' .. src); return f() end")
    for value in _R17_ROUNDTRIP_CORPUS:
        if any(ord(char) > 0x7E for char in value):
            continue  # 바이트 인코딩 왕복은 이 대조의 대상이 아니다.
        literal = luagen._lua_string(value)
        assert _r17_decode_lua_literal(literal) == probe(literal), literal


def test_r17_no_raw_control_character_reaches_the_literal():
    """[round17 수용기준] `ord(char) < 0x20`을 `< 0x1F`로 낮추면 실패한다.

    **재판정**: 감사는 이 변조를 "무해"로 봤으나 무해하지 않다. 전달물은 **사람이 콘솔에
    임포트하는 텍스트 파일**이고, 날 C0 바이트는 편집기·검토자·`Printf` 어디서도 보이지
    않는 채로 이름 값에 실려 나간다. 검토 불가능한 바이트가 전달물에 들어가는 것 자체가
    "본문에 도달하는 모든 문자열은 이 함수를 통과한다"는 규약의 위반이다.
    """
    for code in (*range(0x00, 0x20), 0x7F):
        literal = luagen._lua_string(f"A{chr(code)}B")
        assert chr(code) not in literal, code
        assert _r17_decode_lua_literal(literal) == f"A{chr(code)}B"


# --------------------------------------------------------------------------
# 진짜 Lua 5.4 실행 — 의미론 게이트
# --------------------------------------------------------------------------


def test_r17_lua_sandbox_control_actually_detects_injection():
    """샌드박스 비공허성 — 주입이 **실제로 잡힌다**(하네스가 무기력하지 않다)."""
    error, calls, side = _r17_run_lua(
        "local function main()\n"
        '  AddFixtures({ name = "a" })\n'
        '  os.execute("touch /tmp/PWNED")\n'
        '  AddFixtures({ name = "b" })\n'
        "end\n\nreturn main\n"
    )
    assert error == ""
    assert side == ["os.execute(touch /tmp/PWNED)"]
    assert len(calls) == 2


def test_r17_generated_plugin_runs_in_real_lua_with_zero_side_effects():
    """[round17 #1] 백슬래시 항목을 지우면 **주입이 발화**해 실패한다.

    감사가 실증한 그 재현(`rig\\" }); os.execute([[touch /tmp/PWNED]]) --`)을 그대로
    진짜 Lua 5.4에 태운다. 원본에서는 `AddFixtures` 한 번, 부작용 0건이어야 한다.
    """
    source = render_addfixtures_plugin([_entry(name=_R17_INJECTION_PAYLOAD)])
    error, calls, side = _r17_run_lua(source)
    assert error == ""
    assert side == []
    assert len(calls) == 1
    assert calls[0]["name"] == f"string:{_R17_INJECTION_PAYLOAD}"


@pytest.mark.parametrize(
    ("field", "expected"),
    sorted(_R17_LUA_SEMANTIC_FIELDS.items()),
    ids=sorted(_R17_LUA_SEMANTIC_FIELDS),
)
def test_r17_each_field_reaches_lua_with_the_right_value(field, expected):
    """[round17 #2] `f"{universe}.{address}"`를 뒤집거나 구분자를 바꾸면 실패한다.

    여섯 값을 서로 구분 가능하게 주고(u=12 ≠ a=349), **Lua 런타임이 실제로 받은 값**을
    타입까지 대조한다. 문자열 부분일치가 아니다.
    """
    source = render_addfixtures_plugin([LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS)])
    error, calls, side = _r17_run_lua(source)
    assert error == ""
    assert side == []
    assert len(calls) == 1
    assert calls[0][field] == expected


def test_r17_lua_semantic_field_table_is_bijective_with_the_field_order():
    """표 행삭제 프로브 — 한 행을 지우면 실패한다."""
    assert set(_R17_LUA_SEMANTIC_FIELDS) == set(ADDFIXTURES_FIELD_ORDER)
    assert len(_R17_LUA_SEMANTIC_FIELDS) == len(ADDFIXTURES_FIELD_ORDER)
    source = render_addfixtures_plugin([LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS)])
    _, calls, _ = _r17_run_lua(source)
    assert set(calls[0]) == set(_R17_LUA_SEMANTIC_FIELDS)


# --------------------------------------------------------------------------
# 여섯 필드 렌더 전단사 — 텍스트 층
# --------------------------------------------------------------------------


def test_r17_field_site_table_is_bijective_with_the_field_order():
    """표 행삭제 프로브 — `_R17_FIELD_SITES` 한 행을 지우면 실패한다."""
    assert set(_R17_FIELD_SITES) == set(ADDFIXTURES_FIELD_ORDER)
    assert len(_R17_FIELD_SITES) == len(ADDFIXTURES_FIELD_ORDER) == 6
    assert set(luagen._field_values(LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS))) == set(
        _R17_FIELD_SITES
    )


def test_r17_probe_values_are_pairwise_distinguishable():
    """표본이 구분 가능해야 자리 교환이 보인다 — round16 M50이 주소 쌍에 빠뜨린 규율."""
    scalars = [str(value) for value in _R17_FIELD_PROBE_KWARGS.values()]
    assert len(set(scalars)) == len(scalars)
    assert _R17_FIELD_PROBE_KWARGS["universe"] != _R17_FIELD_PROBE_KWARGS["address"]
    assert len(set(_R17_FIELD_SITES.values())) == len(_R17_FIELD_SITES)


@pytest.mark.parametrize(
    ("field", "expected"),
    sorted(_R17_FIELD_SITES.items()),
    ids=sorted(_R17_FIELD_SITES),
)
def test_r17_each_field_renders_its_exact_text(field, expected):
    """[round17 #2] 값이 다른 자리로 가면 실패한다 — 여섯 값 전부 전문 대조."""
    values = luagen._field_values(LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS))
    assert values[field] == expected
    assert f"{field} = {expected}" in render_addfixtures_call(
        LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS)
    )


def test_r17_patch_pair_is_an_ordered_pair():
    """[round17 #2] `patch`가 (universe, address) **순서 있는 쌍**임을 대칭성으로 못 박는다.

    `assert 'patch = { "1.1" }' in call` 한 줄이 u==a==1 표본이라 원리적으로 못 보던 것.
    """
    forward = luagen._field_values(LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS))["patch"]
    backward = luagen._field_values(
        LuaPatchEntry(**{**_R17_FIELD_PROBE_KWARGS, "universe": 349, "address": 12})
    )["patch"]
    assert forward == '{ "12.349" }'
    assert backward == '{ "349.12" }'
    assert forward != backward


def test_r17_type_and_mode_are_an_ordered_pair():
    """`mode` 핸들에서 타입 자리와 모드 자리가 바뀌면 실패한다."""
    handle = luagen._field_values(LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS))["mode"]
    crossed = luagen._field_values(
        LuaPatchEntry(
            **{**_R17_FIELD_PROBE_KWARGS, "console_type": "ModeBravo", "console_mode": "TypeAlpha"}
        )
    )["mode"]
    assert handle.index("TypeAlpha") < handle.index("ModeBravo")
    assert handle != crossed


def test_r17_field_order_is_the_rulebook_order():
    """필드 **순서**는 형태 규약이다 — 순서 교환(B10)은 무해, **값 교환은 치명**이다.

    그래서 순서는 여기서 별도로 고정하고, 값 자리 교환은 위의 전문·의미론 대조가 잡는다.
    """
    call = render_addfixtures_call(LuaPatchEntry(**_R17_FIELD_PROBE_KWARGS))
    assert re.findall(r"(\w+) = ", call) == list(ADDFIXTURES_FIELD_ORDER)


# --------------------------------------------------------------------------
# 생성 본체 소스 표현 고정 + 모듈 경계 전수 스캔 [HARD 규율 1]
# --------------------------------------------------------------------------


def test_r17_field_value_expression_table_is_bijective():
    """[round17 #2] `_field_values` 여섯 값의 **소스 표현 전문**을 고정한다.

    표 행삭제 프로브 — 한 행을 지우면 전단사가 깨진다.
    """
    tree = ast.parse(LUAGEN_SOURCE)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_field_values"
    )
    mapping = next(node for node in ast.walk(function) if isinstance(node, ast.Dict))
    actual = {
        key.value: ast.unparse(value)
        for key, value in zip(mapping.keys, mapping.values, strict=True)
    }
    assert actual == dict(_R17_FIELD_VALUE_EXPRESSIONS)
    assert set(_R17_FIELD_VALUE_EXPRESSIONS) == set(ADDFIXTURES_FIELD_ORDER)


def test_r17_field_local_binding_table_is_bijective():
    """`luagen.py`의 지역 바인딩(`mode_handle` · `patch_address`)을 전수·전문으로 고정한다."""
    tree = ast.parse(LUAGEN_SOURCE)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_field_values"
    )
    actual = {
        ast.unparse(target): ast.unparse(statement.value)
        for statement in function.body
        if isinstance(statement, ast.Assign)
        for target in statement.targets
    }
    assert actual == dict(_R17_FIELD_LOCAL_EXPRESSIONS)


def test_r17_escape_table_sites_are_exhaustive_across_every_vwx_module():
    """[HARD 1] 이스케이프 표가 `server/vwx/` **어느 모듈에 새로 생겨도** 실패한다.

    round17의 교훈은 "게이트가 모듈 경계에서 멈춘다"였다 — 그래서 luagen만이 아니라
    전 모듈을 훑는다. 표 행삭제 프로브: 한 행을 지우면 전수 일치가 깨진다.
    """
    assert _r17_scan_escape_tables() == sorted(_R17_ESCAPE_TABLE_SITES)


def test_r17_token_join_sites_are_exhaustive_across_every_vwx_module():
    """[HARD 1 · round17 #2] 구분자로 이어 붙인 토큰 f-string 전수 — **전 모듈**.

    피연산자 순서가 뒤집히면 `ast.unparse` 전문이 달라져 실패한다. 즉 `luagen.py:89`
    뿐 아니라 `address.py`·`patchplan.py`·`typemap.py`의 같은 성질 자리도 함께 닫힌다.
    새 자리가 생기면 이 표에 한 행 추가해야 하고, 그때 순서 규약을 명시하게 된다.
    """
    assert _r17_scan_token_joins() == sorted(_R17_TOKEN_JOIN_SITES)


def test_r17_console_address_text_is_also_an_ordered_pair():
    """[HARD 1] 모듈 경계 밖 — `address.to_console_form`도 순서 있는 쌍이다.

    `luagen`만 닫으면 같은 성질의 결함이 옆 모듈에 남는다.
    """
    forward = to_console_form(12, 349)
    backward = to_console_form(349, 12)
    assert (forward.universe, forward.address) == (12, 349)
    assert (backward.universe, backward.address) == (349, 12)
    assert forward.raw != backward.raw


def test_r17_deliverable_int_sites_are_exhaustive():
    """[round17 #7 luagen 몫] `_lua_int` 통과 자리 전수 — 표 행삭제 프로브 포함."""
    assert sorted(_r17_scan_deliverable_int_sites()) == sorted(_R17_DELIVERABLE_INT_SITES)
    assert len(_R17_DELIVERABLE_INT_SITES) == len(_R17_DELIVERABLE_INT_FIELDS)


@pytest.mark.parametrize("field", _R17_DELIVERABLE_INT_FIELDS)
def test_r17_bool_is_refused_in_every_integer_field(field):
    """[round17 #7] `_lua_int`의 bool 가드를 지우면 실패한다.

    `fid=True`는 `fid = "True"`로, `universe=True`는 `patch = { "True.349" }`로 전달물에
    실린다 — 사람이 콘솔에 임포트하는 파일이다.
    """
    with pytest.raises(LuaGenerationError):
        render_addfixtures_call(LuaPatchEntry(**{**_R17_FIELD_PROBE_KWARGS, field: True}))


def test_r17_source_anchors_are_whole_line_exact_and_unique():
    """[HARD 규율 4] 앵커는 **부분문자열이 아니라 전문**이며 정확히 1회 등장한다.

    round17 #6이 성립한 기제가 "앵커 뒤에 덧붙이면 통과"였다. 여기서는 전문 등장 횟수를
    센다 — 앞뒤 어디에 무엇을 붙여도 그 줄의 전문 일치가 깨지거나 횟수가 달라진다.
    """
    for name, anchor in _R17_SOURCE_ANCHORS.items():
        assert LUAGEN_SOURCE.count(anchor) == 1, name
    lines = LUAGEN_SOURCE.splitlines()
    assert _R17_SOURCE_ANCHORS["bool_guard"] in lines
    assert _R17_SOURCE_ANCHORS["control_boundary"] in lines


def test_r17_mutation_table_covers_every_escape_row():
    """표 행삭제 프로브 — `_R17_MUTATIONS`에서 이스케이프 제거 행을 하나 지우면 실패한다."""
    dropped = {row[0] for row in _R17_MUTATIONS if row[0].startswith("escape_drop_")}
    assert len(dropped) == len(luagen._LUA_ESCAPES)
    assert len(_R17_MUTATIONS) == 11


@pytest.mark.parametrize(
    ("letter", "expected"),
    sorted(_R17_LUA_LETTER_UNESCAPES.items()),
    ids=[repr(letter) for letter, _ in sorted(_R17_LUA_LETTER_UNESCAPES.items())],
)
def test_r17_decoder_letter_table_matches_real_lua(letter, expected):
    """디코더 표 행삭제 프로브 — 한 행을 지우면 그 이스케이프에서 디코더가 거부해 실패한다.

    기대값을 **진짜 Lua 5.4**가 판정하므로 자기 비교가 아니다.
    """
    literal = f'"{chr(92)}{letter}"'
    runtime = lua54.LuaRuntime()
    runtime.execute(_R17_LUA_SANDBOX)
    lua_value = runtime.eval("function(src) local f = load('return ' .. src); return f() end")(
        literal
    )
    assert _r17_decode_lua_literal(literal) == expected
    assert _r17_decode_lua_literal(literal) == lua_value


def test_r17_decoder_letter_table_is_bijective_with_real_lua():
    """표 행삭제 프로브 — `_R17_LUA_LETTER_UNESCAPES`에서 한 행을 지우면 실패한다.

    기준 집합을 **진짜 Lua 5.4에 물어서** 만든다: ASCII 출력 가능 문자 중 `"\\<c>"`가
    컴파일되고 길이 1 문자열을 내는 것이 곧 "글자 이스케이프"다(`\\z`는 길이 0,
    `\\x`·`\\u`는 컴파일 실패, 숫자는 `\\ddd` 십진 이스케이프라 제외). 표를 파생 대상과
    비교하는 항진식이 아니라 **독립 판정자와의 전단사**다.
    """
    runtime = lua54.LuaRuntime()
    runtime.execute(_R17_LUA_SANDBOX)
    evaluate = runtime.eval(
        "function(src)"
        " local f = load('return ' .. src)"
        " if f == nil then return nil end"
        " local ok, v = pcall(f)"
        " if not ok then return nil end"
        " return v"
        " end"
    )
    letter_escapes = {}
    for code in range(0x21, 0x7F):
        char = chr(code)
        if char.isdigit():
            continue
        value = evaluate('"' + chr(92) + char + '"')
        if isinstance(value, str) and len(value) == 1:
            letter_escapes[char] = value
    assert dict(_R17_LUA_LETTER_UNESCAPES) == letter_escapes


def test_r17_roundtrip_corpus_covers_the_required_shapes():
    """표 행삭제 프로브 — 왕복 표본에서 한 행을 지우면 실패한다."""
    corpus = set(_R17_ROUNDTRIP_CORPUS)
    assert {f"A{chr(code)}B" for code in range(0x100)} <= corpus
    assert {f"A{char}B" for char in luagen._LUA_ESCAPES} <= corpus
    assert _R17_INJECTION_PAYLOAD in corpus
    assert 'x" , mode = Root() --' in corpus
    assert "back\\slash" in corpus
    assert 'plain " and \\ together' in corpus
    assert "한글 이름 350" in corpus
    assert "" in corpus
    assert len(_R17_ROUNDTRIP_CORPUS) == 0x100 + len(luagen._LUA_ESCAPES) + 6


def test_r17_source_anchor_table_is_complete():
    """표 행삭제 프로브 — `_R17_SOURCE_ANCHORS` 한 행을 지우면 뮤테이션 표가 KeyError로 깨진다."""
    assert len(_R17_SOURCE_ANCHORS) == 3
    assert set(_R17_SOURCE_ANCHORS) == {"patch_pair", "bool_guard", "control_boundary"}
    for _, mutate, _ in _R17_MUTATIONS:
        assert mutate() != LUAGEN_SOURCE
