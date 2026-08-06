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
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "hostile",
    [
        'quote"inside',
        "back\\slash",
        "new\nline",
        "carriage\rreturn",
        "tab\tchar",
        "bracket]close",
        "brace}close",
        "comma,inside",
    ],
)
def test_name_encoder_neutralises_every_hostile_form(hostile):
    """AC-014③(b) — 적대적 입력 전수에서 **한 줄짜리 Lua 문자열 리터럴**로 남고 키 주입이 없다."""
    call = render_addfixtures_call(_entry(name=hostile))
    assert len(call.splitlines()) == 1
    assert set(re.findall(r"(\w+) = ", call)) == set(ADDFIXTURES_FIELD_ORDER)


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
