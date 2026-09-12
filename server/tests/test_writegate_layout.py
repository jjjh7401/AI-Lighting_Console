"""Layout 요소 좌표 쓰기 — 카드 t364 (SPEC-COPILOT-WRITEGATE-001 §D 잔여 하나).

## 이 파일이 고정하는 결함 (고치기 전의 실측)

main `c0aa6ec`, 오프라인, `validate` -> `classify_command` 순수 호출, 룰셋 v8:

    Set Layout 1.1 'PositionX' 5.0     category=safe         risky=False
    Set Fixture 11 Posx '5.0'          category=blacklisted  risky=True
    Set Fixture 11 Rotx '90.0'         category=blacklisted  risky=True

셋 다 쇼파일을 바꾸는 좌표 쓰기인데 픽스처 축만 닫혀 있었다. WRITEGATE SPEC 의
`spec.md` §D 가 이 구멍을 **스스로 적어 두고** 범위 밖에 뒀다 — *"`Set Layout
<l>.<e> 'PositionX' <v>`는 오늘도 `safe`다 … 어떤 툴도 이 형태를 발화하지 않으니
제품이 깨지는 것은 아니지만, `run_commands`는 모델이 손으로 쓴 줄을 받으므로
경로가 열려 있다."* 이 파일이 그 경로를 닫고, 닫혔다는 사실을 못 박는다.

## 고친 자리와 그 이유

고친 것은 `classify.py` 가 아니라 `blacklist.yaml` 이다 (v8 -> v9, 항목
`"Set Layout"`). 픽스처 축을 닫은 것도 코드가 아니라 룰셋 자산의 항목
하나(`"Set Fixture"`, v1 -> v2)였고, `classify.py` 에는 명령별 규칙이 하나도
없다 — 축을 미러링한다는 것은 **그 기제를 미러링한다**는 뜻이다. 폐집합 개정
절차(REQ-MVP-013/026)는 v2 가 세우고 v3~v8 이 여섯 번 이어 쓴 것을 그대로
따랐다: 버전 범프 + REVISION HISTORY 항목 + `_would_be_held` 비용 실측 +
항목 순서 실측.

## 무엇을 덮고 무엇을 안 덮나

`_match_blacklist` 는 동사 `Set` 과 **따옴표 없는 인자 하나**가 키워드
`Layout` 에 맞으면 걸린다(`_keyword_match` 는 3자 이상 접두 축약을 받는다).
그래서 **프로퍼티 차원 전체**가 닫힌다 — `'PositionX'` 하나가 아니라
`'PositionY'`·따옴표 없는 형태·축약 `Set Lay …`·`Set Layout 1.1 Name …` 까지.
프로퍼티 이름을 열거하는 방식이었다면 `'PositionY'` 가 열린 채 남았을 것이고,
그 열거 자체가 `blacklist.yaml` 헤더가 금지하는 open-ended list 다.

안 덮는 것(측정했고, 의도된 경계다): 다른 **동사**(`Edit|Assign|Copy|Store
Layout`), 복수형 `Layouts`(`Layout` 의 접두가 아니다), 오브젝트 키워드가 없는
`Set 'PositionX' 5.0`. `Set Fixture` 가 자기 주석에 적어 둔 미확인 후보들과
같은 종류의 열린 자리이고, 같은 이유로 열려 있다 — `Set` 이 유일한 패치 쓰기
동사라는 것이 작업 가설이며, 뒤집히면 또 한 번의 리비전이 고칠 일이다.
"""

from __future__ import annotations

import dataclasses

import pytest

from server.deploy.scan import scan_lua_source
from server.safety.classify import classify_command
from server.safety.expand import BodyUnavailable, evaluate_reference
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

RULESET = load_ruleset()

#: 이 카드가 넣은 항목. 한 번만 적어 두어 개명이 diff 하나로 보이게 한다.
ENTRY = "Set Layout"

#: 보류되어야 하는 모든 형태. 각 줄의 사유는 「왜 이 형태가 여기 있나」이지
#: 「순열을 채우려고」가 아니다.
HELD_FORMS = (
    ("Set Layout 1.1 'PositionX' 5.0", "이 카드가 재현한 바로 그 줄"),
    ("Set Layout 1.1 'PositionY' 5.0", "프로퍼티 차원 — 리터럴 하나만 잡는 규칙이면 열린다"),
    ("Set Layout 1.1 PositionX 5.0", "따옴표 없는 값 형태"),
    ("Set Layout 1.1 'PositionX' -3.5", "부호 있는 값 — `Set Fixture` 가 라이브로 관측한 형태"),
    ("Set Lay 1.1 'PositionX' 5.0", "오브젝트가 축약된다: `Lay` -> `Layout`"),
    ("Set Layout 1.1 Name 'Cue list'", "좌표가 아닌 레이아웃 쓰기 — 과다매칭, 의도한 방향"),
)

#: 분류가 움직이면 안 되는 형태. 이 튜플이 이 리비전의 **범위**다.
#: `test_writegate.py::UNCHANGED_SAFE` 와 겹치는 줄을 일부러 다시 싣는다 —
#: 저 파일은 `Set Fixture` 의 범위를 지키고, 이 파일은 `Set Layout` 의 범위를
#: 지킨다. 같은 줄이 두 이유로 안전해야 한다.
UNCHANGED_SAFE = (
    ("Edit Layout 1.1 'PositionX' 5.0", "동사가 다르다 — 항목은 `Set` 에 묶여 있다"),
    ("Assign Layout 1.1 At Page 2", "동사가 다르다"),
    ("Copy Layout 1 At Layout 4", "동사가 다르다"),
    ("Store Layout 3", "동사가 다르다 — `Store` 확대는 2026-08-05 결정이 거절했다"),
    ("Layout 1", "선택이지 쓰기가 아니다"),
    ("Set Layouts 1.1 'PositionX' 5.0", "복수형은 `Layout` 의 접두가 아니다"),
    ("Set Selection MAtricks 'PhaseFromX' 0", "프로그래머 상태 — `Layout` 을 쓴 인자가 없다"),
    ("Store Page 3", "descoped: 측정 코퍼스 대표"),
    ("Store Macro 21", "descoped: 측정 코퍼스 대표"),
    ("Copy Page 1 At Page 4", "descoped: v8 은 `Copy Sequence` 를 넣었지 `Copy` 동사가 아니다"),
    ("Assign Preset 4.1 At Executor 101", "descoped: v8 은 `Assign Sequence` 다"),
    ("Label Group 3 'Vocals'", "라벨링은 패치 쓰기가 아니다"),
    ("Group 4", "선택이지 쓰기가 아니다"),
    ("At 100", "프로그래머 상태이지 쓰기가 아니다"),
)


def _classify(command: str):
    grammar = validate(command)
    assert grammar.ok, f"픽스처가 유효한 명령줄이 아니다: {command!r} — {grammar.reason}"
    return classify_command(grammar.parsed, RULESET)


class TestLayoutWritesAreRisky:
    """양성 대조군 — 재현한 줄이 이제 승인을 거친다."""

    @pytest.mark.parametrize(("command", "why"), HELD_FORMS)
    def test_the_form_is_classified_risky(self, command, why):
        finding = _classify(command)
        assert finding.risky is True, why
        assert finding.matched_entry == ENTRY

    def test_the_reproduced_line_is_no_longer_safe(self):
        """고치기 전 실측을 그대로 남긴 회귀 단정.

        **고치기 전(룰셋 v8, main `c0aa6ec`)의 관측**::

            Set Layout 1.1 'PositionX' 5.0   category=safe  risky=False  entry=None

        아래는 그 관측이 뒤집혔다는 단정이다. 이 검사가 빨개진다면 항목이
        폐집합에서 빠졌다는 뜻이고, 그때 열리는 것은 **승인 없는 쇼파일 쓰기**다.
        """
        finding = _classify("Set Layout 1.1 'PositionX' 5.0")
        assert finding.category == "blacklisted"
        assert finding.risky is True
        assert finding.matched_entry == ENTRY

    def test_the_card_states_a_reason(self):
        finding = _classify("Set Layout 1.1 'PositionX' 5.0")
        assert finding.reasons, "사유 없는 위험 판정은 빈 승인 카드다"
        assert ENTRY in " ".join(finding.reasons)

    def test_the_entry_is_ratified_in_the_closed_set(self):
        assert ENTRY in RULESET.blacklist
        assert RULESET.version >= 9


class TestScopeIsHeldExactly:
    """음성 대조군 — 이 확대가 다른 것에 안 닿는다."""

    @pytest.mark.parametrize(("command", "why"), UNCHANGED_SAFE)
    def test_the_form_stays_non_risky(self, command, why):
        finding = _classify(command)
        assert finding.risky is False, why

    def test_the_fixture_axis_is_untouched(self):
        """`Set Fixture` 의 귀속이 바이트 그대로다.

        동사(`Set`)를 공유하는 항목을 하나 더 넣는 리비전이므로, 기존 축의
        **카드 사유**가 움직이지 않았음을 따로 잰다. `_match_blacklist` 는 첫
        일치를 돌려주고 이 항목은 목록 끝에 있다.
        """
        for command in (
            "Set Fixture 11 Posx '5.0'",
            "Set Fixture 11 Rotx '90.0'",
            "Set Fix 11 Posx '1.0'",
            "Set Fixture 1 Thru 18 Posz '5.0'",
            "Set Fixture 11 Name 'Spot 11'",
        ):
            finding = _classify(command)
            assert finding.risky is True, command
            assert finding.matched_entry == "Set Fixture", command

    def test_the_entry_order_only_moves_attribution_never_the_verdict(self):
        """**순서가 의미를 갖는다 — v7 과 같은 조건, v8 과 다른 조건.**

        새 항목의 동사 `Set` 은 기존 항목 `Set Fixture` 와 겹친다. 실측
        (`reports/writegate-t364/03_entry_order.txt`): 항목을 목록 맨 앞으로
        옮기면 **두 줄**의 귀속이 움직인다 — `Set Fixture 11 Layout 3` 과
        `Set Layout 1.1 Fixture 11`, 즉 두 오브젝트 키워드를 한 줄에 담은
        교차 형태뿐이다. 판정(`blacklisted`)은 어느 순서에서도 같다.

        그래서 항목은 목록 **끝**에 둔다 — 그러면 기존 `Set Fixture` 귀속이
        바이트 그대로 남는다. 이 검사가 그 배치를 지킨다: 앞으로 옮기면 아래
        단정이 빨개진다.
        """
        head = dataclasses.replace(
            RULESET,
            blacklist=(ENTRY,) + tuple(e for e in RULESET.blacklist if e != ENTRY),
        )

        def attribution(command, ruleset):
            grammar = validate(command)
            assert grammar.ok, command
            return classify_command(grammar.parsed, ruleset).matched_entry

        crossed = "Set Fixture 11 Layout 3"
        assert attribution(crossed, RULESET) == "Set Fixture"
        assert attribution(crossed, head) == ENTRY, (
            "순서가 귀속을 바꾸지 않는다면 이 검사는 공허하다 — "
            "`_match_blacklist` 의 첫-일치 성질이 사라졌는지 확인하라"
        )
        # 판정 자체는 어느 순서에서도 같다: 귀속만 움직이고 위험도는 안 움직인다.
        for ruleset in (RULESET, head):
            grammar = validate(crossed)
            assert classify_command(grammar.parsed, ruleset).risky is True


class TestIndirectRoutes:
    """간접 경로 둘 — 매크로 본문과 배포 Lua. 기존 `category` 값을 재사용하므로
    두 파일 모두 **무수정**으로 덮인다(`test_writegate.py::TestIndirectRoutes`
    가 `Set Fixture` 에 대해 고정한 것과 같은 성질)."""

    def test_a_macro_body_carrying_a_layout_write_is_held(self):
        class Fetcher:
            def fetch_body(self, reference):
                return ("Set Layout 1.1 'PositionX' 5.0",)

        result = evaluate_reference(
            "Macro 9", ruleset=RULESET, fetcher=Fetcher(), plugin_registry=None
        )
        assert result.hold is True
        assert any("blacklisted" in reason for reason in result.reasons)

    def test_a_deployable_lua_source_carrying_a_layout_write_is_refused(self):
        source = (
            "local function main()\n    Cmd(\"Set Layout 1.1 'PositionX' 5.0\")\nend\nreturn main\n"
        )
        report = scan_lua_source(source, RULESET)
        assert report.destructive is True
        assert [f.kind for f in report.findings] == ["blacklisted"]
        assert report.findings[0].matched_entry == ENTRY

    def test_the_deploy_scan_still_passes_a_genuinely_safe_source(self):
        # 비공허성: 이 확대가 너무 넓었다면 이 소스가 destructive 로 뒤집힌다.
        source = 'local function main()\n    Cmd("Group 4")\nend\nreturn main\n'
        report = scan_lua_source(source, RULESET)
        assert report.destructive is False
        assert list(report.findings) == []

    def test_a_layout_write_smuggled_in_a_quoted_property_value_is_held(self):
        """M6c-2 Finding 1 우회 형태를 이 항목에 대해 다시 잰다."""
        finding = _classify("Set Macro 1.1 Property 'Command' \"Set Layout 1.1 'PositionX' 5.0\"")
        assert finding.risky is True
        assert finding.matched_entry == ENTRY


class _NoBodyAvailable:
    """게이트 자신의 기본 fetcher (`gate.py`): 아무것도 검증 가능하지 않다."""

    def fetch_body(self, reference: str):
        raise BodyUnavailable("no body fetcher configured — reference bodies unverifiable")


def _would_be_held(command: str) -> bool:
    """게이트가 이 명령줄을 사람 승인으로 **보류**하면 True.

    `test_writegate.py::_would_be_held` 와 같은 술어다(그 파일의 docstring 이
    왜 `.risky` 에서 멈추면 안 되는지 적고 있다).
    """
    grammar = validate(command)
    if not grammar.ok:
        return False
    verdict = classify_command(grammar.parsed, RULESET)
    if verdict.risky:
        return True
    if verdict.category == "invoking":
        return evaluate_reference(
            verdict.reference, ruleset=RULESET, fetcher=_NoBodyAvailable(), plugin_registry=None
        ).hold
    return False


class TestDenyAllReachesTheConsoleZeroTimes:
    """게이트 전체를 통과시켜 **콘솔 송신 0건**을 직접 잰다.

    분류가 `blacklisted` 라는 것과 「콘솔에 안 간다」는 것은 다른 주장이다. 앞의
    검사들은 분류 층을 재고, 이 검사는 `SafetyGate.screen` 이 `DenyAllApprovalPort`
    아래에서 실제로 아무것도 안 보내는지를 잰다. 콘솔은 기록용 가짜이고 OSC 는
    어디에도 없다(`test_safety_corpus.py` 와 같은 형태).
    """

    def test_no_command_reaches_the_console_when_approval_is_denied(self, tmp_path):
        from server.safety.approval import DenyAllApprovalPort
        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate

        from .test_safety_gate import FakeConsole

        console = FakeConsole()
        gate = SafetyGate(
            console=console,
            audit=AuditLog(tmp_path / "audit"),
            approval_port=DenyAllApprovalPort(),
        )
        command = "Set Layout 1.1 'PositionX' 5.0"
        decision = gate.screen([command])
        assert decision.cleared is False
        assert console.executed == [], "승인이 거부됐는데 콘솔에 닿았다 (FN!)"
        # 심층 방어: 스크리닝을 건너뛴 직접 포트 호출도 못 뚫는다.
        result = gate.execution_port.execute(command)
        assert result.ok is False
        assert console.executed == [], "실행 포트가 무승인 명령을 콘솔로 보냈다 (FN!)"

    def test_a_safe_bundle_still_reaches_the_console(self, tmp_path):
        # 비공허성: 게이트가 전부 막는 것이 아니라 이 명령만 막는다는 대조군.
        from server.safety.approval import DenyAllApprovalPort
        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate

        from .test_safety_gate import FakeConsole

        console = FakeConsole()
        gate = SafetyGate(
            console=console,
            audit=AuditLog(tmp_path / "audit"),
            approval_port=DenyAllApprovalPort(),
        )
        decision = gate.screen(["Group 4"])
        assert decision.cleared is True
        gate.execution_port.execute("Group 4")
        assert console.executed == ["Group 4"]


class TestMeasuredCostOfThisRevision:
    """이 리비전의 비용 — 실측값을 검사로 고정한다.

    `reports/writegate-t364/02_corpus_delta.txt`: 코퍼스 21 시나리오 / 35 줄
    기준으로 **새로 보류되는 줄 0건, 시나리오 0건**. v3(`LoadShow`/`NewShow`)와
    같은 모양이다 — 저장소에 MA3 `Layout` 명령줄이 애초에 하나도 없다.
    """

    def test_the_measurement_corpus_gains_no_new_collision(self):
        from server.measurement.corpus import load_corpus

        layout_lines = [
            (scenario.id, command)
            for scenario in load_corpus()
            for command in scenario.mock.commands
            if "layout" in command.lower()
        ]
        assert layout_lines == [], (
            "코퍼스에 `Layout` 줄이 생겼다. 이 항목이 그 시나리오를 무인 운전 "
            f"밖으로 내보내는지 다시 재고 헤더에 적어라 — {layout_lines}"
        )

    def test_the_held_predicate_can_actually_fail(self):
        # 비공허성 두 팔: 새 항목이 실제로 보류를 만들고, 폐집합 밖 명령은 안 만든다.
        assert _would_be_held("Set Layout 1.1 'PositionX' 5.0") is True
        assert _would_be_held("Store Page 3") is False
