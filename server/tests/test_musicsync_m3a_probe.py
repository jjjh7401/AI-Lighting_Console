"""M3-a 프로브의 **예산 규율**을 가짜 콘솔에 대고 잰다 (SPEC-COPILOT-MUSICSYNC-001).

이 파일은 실기 콘솔에 한 바이트도 보내지 않는다. 재는 것은 「프로브가 무엇을
알아냈는가」가 아니라 **「프로브가 무엇을 쏘고 무엇을 물어보는가」**다. 그 둘은
다른 질문이고, 앞의 것은 실기 앞에서만 답이 나오며 뒤의 것은 여기서 못박아야
실기 앞에서 예산을 넘기지 않는다.

검사가 못박는 다섯:

1. `--dry-run` 이 쓰기 **정확히 8건**과 조회 계획 **12회 이하**를 인쇄하고
   콘솔 스택을 **바인드하지 않는다**.
2. 슬롯 판정이 occupied·unknown 이면 쓰기 **0건**이고 노트가 **무결론**과
   그 사유를 싣는다.
3. 다섯째 후보와 열셋째 조회가 **거절**된다(발화·질의 자체가 없다).
4. 도구 원본에 녹화 무장 명령 문자열이 **0건**이다 (AC-MUSICSYNC-022).
5. 효과 판정이 `ok:true` 가 아니라 **되읽기 차이**로 갈린다 — 응답이 그대로면
   `ok` 가 참이어도 효과는 거짓이다 (AC-MUSICSYNC-020 · `spec.md §A.5`).

그리고 `slot_verdict` 특성 검사 — 이 술어는 `server/orchestrator/tools.py:2792`
`_timecode_slot_verdict` 의 재구현이다(그 함수는 툴셋 빌더 안의 중첩 함수라
임포트할 수 없다). 세 갈래(free/occupied/unknown)의 페이로드 형태를 원본과
같은 분기로 답하는지 잰다 — 재구현이 조용히 갈라지면 「남의 쇼를 덮지 않는다」는
보장이 사라진다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.tools import musicsync_m3a_probe as probe

POOL = "DataPool/Timecodes"
SLOT = 998
SLOT_PATH = "DataPool/Timecodes/998"
TRACKGROUP_PATH = "DataPool/Timecodes/998/TrackGroup 1"


class FakeStateQueryError(RuntimeError):
    """가짜 조회 실패. 실코드는 `StateQueryError` 를 받지만 넓게 잡으므로 이걸로 충분하다."""


class FakePort:
    """경로별 응답 대본. 리스트면 순서대로 소진하고 **마지막 항목을 반복**한다."""

    def __init__(self, script: dict[str, object]) -> None:
        self.script = {
            key: (list(value) if isinstance(value, list) else [value])
            for key, value in script.items()
        }
        self.asked: list[tuple[str, int | None]] = []

    def query_state(self, path: str, offset: int | None = None):
        self.asked.append((path, offset))
        queue = self.script.get(path)
        if queue is None:
            raise FakeStateQueryError("path segment not found: " + path)
        payload = queue[0] if len(queue) == 1 else queue.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload


class FakeConsole:
    """발화된 명령을 기록하고, 지정한 명령이 오면 되읽기 대본을 **바꾼다**.

    대본을 바꾸는 것이 이 가짜의 요점이다 — 효과는 `ok` 가 아니라 상태 변화이므로,
    변화를 만들지 않는 가짜로는 효과 판정을 재는 검사 자체가 공허해진다.
    """

    def __init__(self, port: FakePort | None = None, *, effects: dict[str, object] | None = None):
        self.port = port
        self.effects = dict(effects or {})
        self.fired: list[str] = []

    def __call__(self, commands: list[str]) -> list[dict]:
        rows = []
        for command in commands:
            self.fired.append(command)
            changed = self.effects.get(command)
            if changed is not None and self.port is not None:
                self.port.script[SLOT_PATH] = [changed]
            rows.append(dict(command=command, ok=True, detail="OK"))
        return rows


def pool_payload(children, *, count=None, truncated=False) -> dict:
    node: dict[str, object] = {"class": "Timecodes"}
    if count is not None:
        node["childCount"] = count
    return {"node": node, "children": list(children), "truncated": truncated}


def slot_payload(name: str) -> dict:
    return {
        "node": {"class": "Timecode", "name": name, "childCount": 1},
        "children": [{"class": "TrackGroup", "i": 1}],
        "truncated": False,
    }


def free_pool() -> dict:
    """슬롯 998 이 없는 풀 — 다른 슬롯 하나가 들어 있어야 `childCount == 0` 무결론을 피한다."""
    return pool_payload([{"class": "Timecode", "i": 1, "name": "SHOW"}], count=1)


def healthy_script(*, trackgroup=None) -> dict[str, object]:
    return {
        POOL: free_pool(),
        SLOT_PATH: [FakeStateQueryError("path segment not found"), slot_payload("MSYNCPROBE")],
        TRACKGROUP_PATH: trackgroup
        if trackgroup is not None
        else pool_payload([], count=0, truncated=False),
    }


class TestDryRunPlan:
    def test_it_plans_exactly_eight_writes_for_four_candidates(self, capsys, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("--dry-run 이 콘솔 스택을 바인드했다")

        monkeypatch.setattr(probe, "build_console_stack", explode)
        code = probe.main(
            ["--listen-port", "9005", "--slot", "998", "--sequence", "1", "--dry-run"]
        )
        assert code == 0
        plan = json.loads(capsys.readouterr().out)
        assert plan["fired"] is False
        assert len(plan["writes"]) == 8, plan["writes"]
        assert plan["writes"][0] == "Store Timecode 998"
        assert plan["writes"][-1] == "Off Timecode 998"
        assert plan["planned_query_count"] <= 12
        assert len(plan["planned_queries"]) == plan["planned_query_count"]

    def test_without_approve_it_prints_the_plan_and_fires_nothing(self, capsys, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("--approve 없이 콘솔 스택을 바인드했다")

        monkeypatch.setattr(probe, "build_console_stack", explode)
        code = probe.main(["--listen-port", "9005", "--slot", "998", "--sequence", "1"])
        assert code == 0
        assert json.loads(capsys.readouterr().out)["fired"] is False


class TestSlotVerdictGatesEveryWrite:
    def test_occupied_slot_fires_nothing_and_closes_inconclusive(self):
        port = FakePort(
            {POOL: pool_payload([{"class": "Timecode", "i": 998, "name": "SHOWTC"}], count=1)}
        )
        console = FakeConsole(port)
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=list(probe.DEFAULT_CANDIDATES),
        )
        assert console.fired == []
        assert result["slot_verdict"]["verdict"] == "occupied"
        assert result["verdict"] == "inconclusive"
        assert result["verdict_reason"]
        note = probe.render_note(result)
        assert "무결론" in note
        assert result["verdict_reason"] in note

    def test_unknown_verdict_fires_nothing(self):
        port = FakePort({POOL: pool_payload([], count=None)})
        console = FakeConsole(port)
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=list(probe.DEFAULT_CANDIDATES),
        )
        assert console.fired == []
        assert result["slot_verdict"]["verdict"] == "unknown"
        assert result["verdict"] == "inconclusive"


class TestBudgetGuard:
    def test_a_fifth_candidate_is_refused_before_it_is_fired(self):
        port = FakePort(healthy_script())
        console = FakeConsole(port)
        candidates = [
            "Go Timecode 998",
            "Go+ Timecode 998",
            "Pause Timecode 998",
            "Toggle Timecode 998",
            "Zzz Timecode 998",
        ]
        result = probe.run_sweep(
            state_port=port, fire=console, slot=998, sequence=1, candidates=candidates
        )
        assert "Zzz Timecode 998" not in console.fired
        assert len(console.fired) == 8
        assert result["budget_exceeded"] is True
        assert result["verdict"] == "inconclusive"
        assert any("Zzz Timecode 998" in entry for entry in result["refused"])

    def test_a_thirteenth_query_is_refused(self):
        """`TrackGroup` 이 끝없이 잘려 오면 페이징이 예산을 먹고 **거기서 멈춘다**."""
        forever = pool_payload([{"class": "Track", "i": 1}], count=99, truncated=True)
        script = healthy_script(trackgroup=forever)
        script[TRACKGROUP_PATH] = [forever]
        port = FakePort(script)
        console = FakeConsole(port)
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=list(probe.DEFAULT_CANDIDATES),
        )
        assert result["queries"]["total"] == 12
        assert len(port.asked) == 12, port.asked
        assert result["budget_exceeded"] is True
        assert result["verdict"] == "inconclusive"


class TestEffectIsReadFromTheReadback:
    def test_a_changed_readback_is_an_effect(self):
        script = healthy_script()
        port = FakePort(script)
        moved = slot_payload("MSYNCPROBE")
        moved["node"]["childCount"] = 2
        console = FakeConsole(port, effects={"Go Timecode 998": moved})
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=["Go Timecode 998"],
        )
        rows = {row["command"]: row for row in result["probe2_candidates"]}
        assert rows["Go Timecode 998"]["effect"] is True

    def test_a_readback_that_differs_only_by_request_id_is_no_effect(self):
        """1회차 실기(2026-09-05) 오판의 회귀 — 응답기는 되읽기마다 새 `id`
        (`gate-12`·`gate-15`…)를 매기므로, 그 필드를 비교에 넣으면 네 후보 전부가
        「효과 있음」이 된다. 상태 본문이 같으면 효과가 아니어야 한다."""
        script = healthy_script()
        port = FakePort(script)
        same_state_new_id = slot_payload("MSYNCPROBE")
        same_state_new_id["id"] = "gate-999"  # 상태는 같고 상관 번호만 새것
        console = FakeConsole(port, effects={"Go Timecode 998": same_state_new_id})
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=["Go Timecode 998"],
        )
        rows = {row["command"]: row for row in result["probe2_candidates"]}
        assert rows["Go Timecode 998"]["effect"] is False

    def test_an_unchanged_readback_is_no_effect_even_when_ok_is_true(self):
        port = FakePort(healthy_script())
        console = FakeConsole(port)  # 효과 대본 없음 — 되읽기가 그대로다
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=["Go Timecode 998"],
        )
        row = result["probe2_candidates"][0]
        assert row["ok"] is True
        assert row["effect"] is False


class TestTheToolNeverNamesTheArmingCommand:
    def test_grep_count_is_zero(self):
        """AC-MUSICSYNC-022 — 앱도 프로브도 녹화를 무장시키지 않는다."""
        source = Path("server/tools/musicsync_m3a_probe.py").read_text(encoding="utf-8")
        needle = "Record" + " Timecode"
        assert source.count(needle) == 0


class TestSlotVerdictCharacterisation:
    """`server/orchestrator/tools.py:2792` 의 3분 판정을 같은 분기로 답하는가."""

    def test_a_free_slot(self):
        port = FakePort({POOL: pool_payload([{"i": 1, "name": "SHOW"}], count=1)})
        assert probe.slot_verdict(port, POOL, 998)[0] == "free"

    def test_an_occupied_slot_names_its_occupant(self):
        port = FakePort({POOL: pool_payload([{"i": 998, "name": "SHOWTC"}], count=1)})
        verdict, detail = probe.slot_verdict(port, POOL, 998)
        assert verdict == "occupied"
        assert "SHOWTC" in detail

    @pytest.mark.parametrize(
        "payload,label",
        [
            (pool_payload([{"i": 1}], count=1, truncated=True), "truncated"),
            (pool_payload([{"i": 1}], count=None), "childCount 부재"),
            (pool_payload([{"i": 1}], count=9), "childCount > 자식 수"),
            (pool_payload([], count=0), "childCount 0"),
            ("not-a-mapping", "비매핑 페이로드"),
        ],
    )
    def test_unknown_shapes(self, payload, label):
        port = FakePort({POOL: payload})
        verdict, detail = probe.slot_verdict(port, POOL, 998)
        assert verdict == "unknown", label
        assert detail

    def test_a_read_failure_is_unknown_not_free(self):
        port = FakePort({POOL: FakeStateQueryError("no answer")})
        verdict, detail = probe.slot_verdict(port, POOL, 998)
        assert verdict == "unknown"
        assert "no answer" in detail


class TestArtifacts:
    def test_the_note_carries_the_per_probe_query_counts_and_the_residue(self, tmp_path):
        port = FakePort(healthy_script())
        console = FakeConsole(port)
        result = probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=list(probe.DEFAULT_CANDIDATES),
        )
        note = probe.render_note(result)
        assert "## 조회 수" in note
        for label in result["queries"]["per_probe"]:
            assert label in note
        assert "잔여물" in note
        assert "Off Timecode 998" in note

    def test_the_step_log_is_one_json_object_per_line(self, tmp_path):
        port = FakePort(healthy_script())
        console = FakeConsole(port)
        log: list[dict] = []
        probe.run_sweep(
            state_port=port,
            fire=console,
            slot=998,
            sequence=1,
            candidates=list(probe.DEFAULT_CANDIDATES),
            log=log,
        )
        out = tmp_path / "steps.jsonl"
        probe.write_step_log(out, log)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines
        for line in lines:
            row = json.loads(line)
            assert set(("label", "seq", "kind", "arg", "ts", "payload")) <= set(row)
        assert [row["kind"] for row in log].count("exec") == 8
