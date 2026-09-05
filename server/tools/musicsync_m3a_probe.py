"""M3-a 프로브 — 타임코드 재생 문법과 `TrackGroup` 판독을 **격리 슬롯 하나**에서 잰다.

SPEC-COPILOT-MUSICSYNC-001 (REQ-019·020·021·023·025 / AC-020·021·022).
검증 도구다 — 제품 코드가 아니다. `server/tools/t66_destination_probe.py` 의 형태를
승계한다: 실포트 조립(`build_console_stack`), 우회 배선 0, `--approve` 가 없으면
콘솔에 아무것도 닿지 않는다.

## 이 스윕이 재는 셋과 대조군 둘

    ① `state DataPool/Timecodes/<n>/TrackGroup 1` 로 트랙·이벤트가 판독되는가
    ② 재생 명령 후보 4건 이하 — 판정은 `ok:true` 가 아니라 **되읽기 차이**다
    ③ `rig_paths["timecodes"]` 실값 대 M0 문자열
    ④ 양성 대조군 — 준비 뒤 슬롯 노드가 이름 `MSYNCPROBE` 로 답해야 한다
    ⑤ 음성 대조군 — 생성 **전** 같은 경로가 부재를 부재로 답해야 한다

대조군 둘이 같은 스윕 안에 없으면 다른 모든 실패가 「계기 고장」과 구별되지 않는다.

## 예산 (`spec.md §A.4` M3-a 행이 정본)

콘솔 쓰기 **8건 이하** — 슬롯 준비 3줄 + 재생 후보 4건 이하 + 해제 1줄. 조회는
스윕 전체에서 `query_state` **12회 이하**. 어느 한쪽을 넘겨야 답이 나오는 단계는
**보내지 않고** `budget_exceeded` 로 적고 스윕을 **무결론**으로 닫는다. 특히
후보는 되읽기 예산이 남아 있을 때만 쏜다 — 잴 수 없는 쓰기는 증거를 만들지 못하고
되돌릴 수 없는 행위만 남긴다.

`TrackGroup` 페이징이 예산을 먹으면 뒤 단계가 전부 거절된다. 그것이 이 도구의
설계된 거동이다(`plan.md §G` — 답이 안 나온다고 프로브를 늘려 예산 밖에서
판정하지 않는다).

## 슬롯 판정이 모든 쓰기의 관문이다

`slot_verdict` 는 `server/orchestrator/tools.py:2792` `_timecode_slot_verdict` 의
재구현이다 — 그 함수는 툴셋 빌더 안의 **중첩 함수**라 임포트할 수 없다. 세 갈래를
원본과 같은 분기로 답하는지는 `server/tests/test_musicsync_m3a_probe.py` 의 특성
검사가 못박는다. **free 가 아니면 쓰기 0건**이다 — occupied 는 남의 쇼를 덮고,
unknown 은 덮는지 아닌지를 모르는 상태다.

## M0 실측과 그 주의사항

M0(`SPEC-COPILOT-SONGCUE-001/progress.md`)이 GO 로 실측한 것: `Store Timecode <n>`
(풀 childCount 0→1) · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign
Sequence <s> At Timecode <n>`(`TrackGroup 1` 생성) · `Off Timecode <n>`.
`Stop Timecode <n>` 은 `Not implemented`.

🔴 **`Go Timecode <n>` 의 `Illegal object` 는 「그 동사가 없다」의 증거가 아니다.**
M0 원본 로그(`.moai/state/verify/songcue-m0/steps.jsonl`)에서 그 발화는 seq 5 이고
`Store Timecode 999` 는 seq 6 이다 — **슬롯이 생기기 전에 쐈다.** 그러므로 그 답은
「그런 객체가 없다」였을 수 있다. 이 프로브는 같은 명령을 **슬롯이 생긴 뒤에**
다시 쏜다.

🔴 **기본 후보 4종은 가설이지 실측이 아니다.** `Go` · `Go+` · `Pause` · `Toggle` 은
grandMA3 의 다른 오브젝트(시퀀스·익스큐터)에서 쓰이는 동사를 타임코드에 옮겨 본
것이고, 타임코드에 대해서는 **아무도 재지 않았다.** 이 목록이 답을 못 내는 것은
실패가 아니라 관측 결과다.

## 이 도구가 절대 안 하는 것

녹화를 무장시키는 명령은 이 파일 어디에도 문자열로 없다(AC-MUSICSYNC-022).
그 명령은 앱이 아니라 **운영자가** 쏘며, 앱은 `QuestionRequest.commands[]` 로
넘긴다. 슬롯도 지우지 않는다 — 삭제 동사는 §A.4 예산 밖이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, TIMECODE_POOL_PATH
from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

#: M0 이 실측한 타임코드 풀 경로 문자열. ③ 은 이 값과 코드의 실값을 대조한다.
M0_TIMECODE_POOL_PATH = "DataPool/Timecodes"

#: 격리 슬롯에 붙일 이름. ASCII 만 — M0 가 잰 것이 ASCII 이고, 한글은 응답기
#: payload 예산에서 더 일찍 잘린다(t230 실측).
PROBE_SLOT_NAME = "MSYNCPROBE"

#: 슬롯 준비 3줄. M0 GO 실측분이며 순서가 의미를 갖는다 — 이름은 오브젝트가
#: 생긴 뒤에, 시퀀스 결합은 그 뒤에.
PREP_TEMPLATES = (
    "Store Timecode {slot}",
    "Set Timecode {slot} Property 'Name' '{name}'",
    "Assign Sequence {sequence} At Timecode {slot}",
)

#: 해제 1줄. M0 GO 실측분.
RELEASE_TEMPLATE = "Off Timecode {slot}"

#: 재생 명령 후보 기본 목록 — **가설 집합이지 실측이 아니다**(독스트링 참조).
DEFAULT_CANDIDATES = (
    "Go Timecode {slot}",
    "Go+ Timecode {slot}",
    "Pause Timecode {slot}",
    "Toggle Timecode {slot}",
)

#: `spec.md §A.4` M3-a 행의 두 상한.
MAX_WRITES = 8
MAX_QUERIES = 12

#: 후보 허용치는 상한에서 **역산**한다 — 준비 3줄과 해제 1줄은 협상 대상이
#: 아니므로, 후보 수를 따로 박아 두면 두 숫자가 갈릴 자리가 생긴다.
CANDIDATE_ALLOWANCE = MAX_WRITES - len(PREP_TEMPLATES) - 1

#: 프로브 수 상한(본 프로브 3 + 대조군 2). 조회 수와 **단위가 다르다**.
MAX_PROBES = 5


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _canonical(payload) -> str:
    """되읽기 비교용 정규형. 키 순서가 응답마다 흔들려도 같은 상태는 같은 문자열이다."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def slot_verdict(port, path: str, wanted: int) -> tuple[str, str | None]:
    """`Timecode <wanted>` 가 비었는가. `("free"|"occupied"|"unknown", 사유)`.

    `server/orchestrator/tools.py:2792` `_timecode_slot_verdict` 의 재구현이다.
    셋째 갈래(unknown)가 이 함수의 존재 이유다 — 풀이 답을 안 하거나, 열거가
    잘렸거나, `childCount` 가 없거나 자식 수보다 크거나, 0 이면 **비었음과
    못 읽었음이 같은 페이로드**다. 그 자리에서 free 로 읽으면 남의 쇼를 덮는다.
    """
    try:
        payload = port.query_state(path)
    except Exception as error:  # noqa: BLE001 — 어떤 판독 실패도 unknown 이다
        return "unknown", f"{path} 가 답하지 않았다: {error}"
    if not isinstance(payload, dict):
        return "unknown", f"{path} 가 매핑이 아닌 페이로드를 답했다"
    if payload.get("truncated"):
        return "unknown", f"{path} 열거가 잘렸다"
    children = [child for child in (payload.get("children") or ()) if isinstance(child, dict)]
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    if not isinstance(child_count, int) or isinstance(child_count, bool):
        return "unknown", f"{path} 가 childCount 를 안 실었다"
    if child_count > len(children):
        return "unknown", (
            f"{path} 열거가 짧다: childCount {child_count} 인데 자식 {len(children)}개"
        )
    if child_count == 0:
        return "unknown", (
            f"{path} 가 자식 0 을 답했다 — 빈 풀과 실패한 열거가 여기서는 구별되지 않는다"
        )
    for child in children:
        if child.get("i") == wanted:
            name = child.get("name")
            return "occupied", f"슬롯 {wanted} 점유: {name or '이름 없음'}"
    return "free", None


def render_commands(slot: int, sequence: int, candidates) -> tuple[list[str], list[str], str]:
    """(준비 3줄, 후보 목록, 해제 1줄). 템플릿의 `{slot}` 을 실제 번호로 채운다."""
    prep = [
        template.format(slot=slot, sequence=sequence, name=PROBE_SLOT_NAME)
        for template in PREP_TEMPLATES
    ]
    filled = [str(item).format(slot=slot, sequence=sequence) for item in candidates]
    return prep, filled, RELEASE_TEMPLATE.format(slot=slot)


def plan(slot: int, sequence: int, candidates) -> dict:
    """쓰기 전문과 조회 계획을 **발화 없이** 세운다. `--dry-run` 과 계획 인쇄가 쓴다."""
    prep, filled, release = render_commands(slot, sequence, candidates)
    accepted = filled[:CANDIDATE_ALLOWANCE]
    refused = filled[CANDIDATE_ALLOWANCE:]
    slot_path = f"{TIMECODE_POOL_PATH}/{slot}"
    queries = [
        ("slot_verdict", TIMECODE_POOL_PATH),
        ("pool_baseline", TIMECODE_POOL_PATH),
        ("control_negative", slot_path),
        ("post_prep_readback", slot_path),
        ("probe1_trackgroup", f"{slot_path}/TrackGroup 1"),
    ]
    queries.extend(("probe2_candidates", slot_path) for _ in accepted)
    queries.append(("probe3_rig_path", TIMECODE_POOL_PATH))
    queries.append(("post_release_readback", slot_path))
    return dict(
        slot=slot,
        sequence=sequence,
        writes=[*prep, *accepted, release],
        refused_candidates=refused,
        planned_queries=[dict(label=label, path=path) for label, path in queries],
        planned_query_count=len(queries),
        max_writes=MAX_WRITES,
        max_queries=MAX_QUERIES,
        max_probes=MAX_PROBES,
        candidate_allowance=CANDIDATE_ALLOWANCE,
    )


class _Sweep:
    """예산을 쥔 채로 순서를 진행한다. 예산이 모자라면 **보내지 않고** 적는다."""

    def __init__(self, *, state_port, fire, slot: int, sequence: int, log: list | None):
        self.port = state_port
        self.fire = fire
        self.slot = slot
        self.sequence = sequence
        self.slot_path = f"{TIMECODE_POOL_PATH}/{slot}"
        self.log = log if log is not None else []
        self.queries = 0
        self.writes = 0
        self.per_probe: OrderedDict[str, int] = OrderedDict()
        self.fired: list[dict] = []
        self.refused: list[str] = []
        self.budget_exceeded = False
        self.seq = 0

    # -- 기록 ---------------------------------------------------------------

    def record(self, label: str, kind: str, arg, payload) -> None:
        """단계 로그 한 줄. songcue-m0 `steps.jsonl` 과 같은 필드 집합이다."""
        self.seq += 1
        self.log.append(
            dict(label=label, seq=self.seq, kind=kind, arg=arg, ts=_now(), payload=payload)
        )

    def charge_query(self, label: str) -> None:
        """이미 발생한 조회 1회를 장부에 단다 — 슬롯 판정처럼 밖에서 묻는 자리용."""
        self.queries += 1
        self.per_probe[label] = self.per_probe.get(label, 0) + 1

    # -- 조회 ---------------------------------------------------------------

    def query(self, label: str, path: str, *, offset: int | None = None):
        """한 번 묻는다. 예산이 없으면 **묻지 않고** `(None, 사유)` 를 돌려준다."""
        if self.queries >= MAX_QUERIES:
            self.budget_exceeded = True
            reason = f"조회 예산 {MAX_QUERIES}회 소진 — {label}({path}) 는 묻지 않았다"
            self.refused.append(reason)
            self.record(label, "budget", path, dict(refused=reason))
            return None, reason
        self.charge_query(label)
        try:
            if offset is None:
                payload = self.port.query_state(path)
            else:
                payload = self.port.query_state(path, offset=offset)
        except Exception as error:  # noqa: BLE001 — 사유를 그대로 싣는다
            detail = str(error)
            self.record(label, "query", path, dict(ok=False, error=detail))
            return None, detail
        self.record(label, "query", path, payload)
        return payload, None

    def remaining_queries(self) -> int:
        return MAX_QUERIES - self.queries

    # -- 쓰기 ---------------------------------------------------------------

    def send(self, label: str, commands: list[str]) -> list[dict]:
        """번들 하나를 발화한다. 예산을 넘기면 **한 줄도 안 보낸다**."""
        if self.writes + len(commands) > MAX_WRITES:
            self.budget_exceeded = True
            reason = f"쓰기 예산 {MAX_WRITES}건 초과 — {', '.join(commands)} 는 발화하지 않았다"
            self.refused.append(reason)
            self.record(label, "budget", "; ".join(commands), dict(refused=reason))
            return []
        rows = list(self.fire(list(commands)))
        self.writes += len(commands)
        for row in rows:
            self.fired.append(row)
            self.record(label, "exec", row.get("command"), dict(row))
        return rows

    # -- 페이징 -------------------------------------------------------------

    def page_children(self, label: str, path: str) -> dict:
        """자식을 소진할 때까지 페이징한다 — **매 창이 조회 1회**다.

        멈춤 조건은 t230 `read_children` 와 같다(truncated 해소 · 빈 창 · offset
        반향 불일치). 여기에 넷째가 붙는다 — **예산 소진**. 넷을 구별해서 적는다.
        """
        children: list = []
        offset = 0
        child_count = None
        truncated_last = None
        stop = "complete"
        error = None
        while True:
            payload, error = self.query(label, path, offset=offset)
            if payload is None:
                stop = "budget" if "예산" in (error or "") else "error"
                break
            if not isinstance(payload, dict):
                stop = "non_mapping"
                break
            node = payload.get("node")
            if child_count is None and isinstance(node, dict):
                child_count = node.get("childCount")
            window = [child for child in (payload.get("children") or ()) if isinstance(child, dict)]
            children.extend(window)
            truncated_last = bool(payload.get("truncated"))
            if not truncated_last:
                break
            if not window:
                stop = "empty_window"
                break
            echoed = payload.get("offset")
            if echoed is not None and echoed != offset:
                stop = "offset_echo_mismatch"
                break
            offset += len(window)
        return dict(
            path=path,
            children=children,
            listed=len(children),
            childCount=child_count,
            truncated=truncated_last,
            stop=stop,
            error=error,
        )


def run_sweep(
    *,
    state_port,
    fire,
    slot: int,
    sequence: int,
    candidates,
    log: list | None = None,
) -> dict:
    """스윕 본문. 콘솔 조립은 호출자가 하고, 여기서는 포트와 발화 통로만 받는다.

    이 분리가 오프라인 검사를 가능하게 한다 — 가짜 포트와 가짜 발화 통로를 넣으면
    실기 없이 **예산 규율 전부**를 잴 수 있다. 알아낼 수 없는 것은 재생 문법뿐이고,
    그것은 원래 실기 앞에서만 답이 나온다.
    """
    prep, filled, release = render_commands(slot, sequence, candidates)
    sweep = _Sweep(state_port=state_port, fire=fire, slot=slot, sequence=sequence, log=log)
    result: dict = dict(
        spec="SPEC-COPILOT-MUSICSYNC-001 M3-a",
        ran_at=_now(),
        slot=slot,
        sequence=sequence,
        slot_name=PROBE_SLOT_NAME,
        candidates_requested=list(filled),
        writes=[],
        refused=sweep.refused,
        probe2_candidates=[],
        unverified=[],
    )

    # ①의 앞 관문 — 슬롯 판정. free 가 아니면 여기서 끝난다(쓰기 0건).
    sweep.charge_query("slot_verdict")
    verdict, detail = slot_verdict(state_port, TIMECODE_POOL_PATH, slot)
    sweep.record("slot_verdict", "query", TIMECODE_POOL_PATH, dict(verdict=verdict, detail=detail))
    result["slot_verdict"] = dict(verdict=verdict, detail=detail)
    if verdict != "free":
        result["verdict"] = "inconclusive"
        result["verdict_reason"] = f"슬롯 판정이 {verdict} 다 — {detail}. 콘솔 쓰기 0건으로 닫는다"
        result["budget_exceeded"] = sweep.budget_exceeded
        result["queries"] = dict(total=sweep.queries, per_probe=dict(sweep.per_probe))
        result["unverified"] = ["①", "②", "③", "④"]
        result["residue"] = "없음 — 슬롯을 만들지 않았다"
        return result

    # 준비 전 베이스라인. ④ 양성 대조군의 앞짝이다 — 풀 자체는 답해야 한다.
    baseline, baseline_error = sweep.query("pool_baseline", TIMECODE_POOL_PATH)
    result["control_positive_pool"] = dict(
        path=TIMECODE_POOL_PATH,
        answered=baseline is not None,
        error=baseline_error,
        childCount=(baseline or dict()).get("node", dict()).get("childCount")
        if isinstance(baseline, dict)
        else None,
    )

    # ⑤ 음성 대조군 — 생성 **전** 슬롯 경로. 부재를 부재로 답해야 한다.
    before, before_error = sweep.query("control_negative", sweep.slot_path)
    result["control_negative"] = dict(
        path=sweep.slot_path,
        answered=before is not None,
        error=before_error,
        payload=before,
    )

    # 슬롯 준비 3줄.
    prep_rows = sweep.send("prep", prep)
    result["writes"].extend(row.get("command") for row in prep_rows)
    result["prep"] = prep_rows
    if not prep_rows or any(row.get("fired", True) is False for row in prep_rows):
        result["verdict"] = "inconclusive"
        result["verdict_reason"] = (
            "준비 줄이 콘솔에 닿지 않았다(게이트 차단 또는 예산) — 이 실행의 어떤 "
            "실패도 콘솔에 대한 관측이 아니다"
        )
        result["budget_exceeded"] = sweep.budget_exceeded
        result["queries"] = dict(total=sweep.queries, per_probe=dict(sweep.per_probe))
        result["unverified"] = ["①", "②", "③", "④"]
        result["residue"] = "없음 — 콘솔에 닿지 않았다"
        return result

    # ④ 양성 대조군 — 준비 뒤 슬롯 노드가 이름으로 답해야 한다.
    after_prep, after_prep_error = sweep.query("post_prep_readback", sweep.slot_path)
    node = after_prep.get("node") if isinstance(after_prep, dict) else None
    result["control_positive_slot"] = dict(
        path=sweep.slot_path,
        answered=after_prep is not None,
        error=after_prep_error,
        name=node.get("name") if isinstance(node, dict) else None,
        name_matches=bool(isinstance(node, dict) and node.get("name") == PROBE_SLOT_NAME),
        payload=after_prep,
    )

    # ① TrackGroup 아래 판독.
    result["probe1_trackgroup"] = sweep.page_children(
        "probe1_trackgroup", f"{sweep.slot_path}/TrackGroup 1"
    )

    # ② 재생 명령 후보 — 되읽기 예산이 남아 있을 때만 쏜다.
    reference = after_prep
    for command in filled:
        if len(result["probe2_candidates"]) >= CANDIDATE_ALLOWANCE:
            sweep.budget_exceeded = True
            sweep.refused.append(
                f"후보 허용치 {CANDIDATE_ALLOWANCE}건 초과 — {command} 는 발화하지 않았다"
            )
            continue
        if sweep.remaining_queries() <= 0:
            sweep.budget_exceeded = True
            sweep.refused.append(
                f"되읽기 예산이 없다 — {command} 는 발화하지 않았다(잴 수 없는 쓰기는 안 쏜다)"
            )
            continue
        rows = sweep.send("candidate", [command])
        if not rows:
            continue
        row = rows[0]
        result["writes"].append(row.get("command"))
        readback, readback_error = sweep.query("probe2_candidates", sweep.slot_path)
        effect = None
        if readback is not None and reference is not None:
            effect = _canonical(readback) != _canonical(reference)
        result["probe2_candidates"].append(
            dict(
                command=command,
                ok=bool(row.get("ok")),
                detail=row.get("detail"),
                effect=effect,
                readback=readback,
                readback_error=readback_error,
            )
        )
        if readback is not None:
            reference = readback

    # ③ rig_paths["timecodes"] 실값 대조. 값 비교는 조회가 아니다 — 코드를 읽는다.
    rig_query, rig_error = sweep.query("probe3_rig_path", TIMECODE_POOL_PATH)
    result["probe3_rig_path"] = dict(
        code_value=TIMECODE_POOL_PATH,
        m0_value=M0_TIMECODE_POOL_PATH,
        matches_m0=TIMECODE_POOL_PATH == M0_TIMECODE_POOL_PATH,
        in_default_rig_table="timecodes" in DEFAULT_RIG_CONTEXT_PATHS,
        answers=rig_query is not None,
        error=rig_error,
    )

    # 해제 1줄 + 해제 뒤 되읽기.
    release_rows = sweep.send("release", [release])
    result["writes"].extend(row.get("command") for row in release_rows)
    result["release"] = release_rows
    released, released_error = sweep.query("post_release_readback", sweep.slot_path)
    result["post_release_readback"] = dict(
        path=sweep.slot_path, payload=released, error=released_error
    )

    result["queries"] = dict(total=sweep.queries, per_probe=dict(sweep.per_probe))
    result["write_count"] = sweep.writes
    result["budget_exceeded"] = sweep.budget_exceeded
    result["unverified"] = _unverified(result)
    result["residue"] = (
        f"타임코드 슬롯 {slot}('{PROBE_SLOT_NAME}') 가 콘솔에 남는다 — 해제만 했고 "
        "삭제하지 않았다. 삭제 동사는 spec.md §A.4 M3-a 예산 밖이므로 이 프로브가 "
        "쏘지 않는다. 정리는 운영자 몫이다"
    )
    if sweep.budget_exceeded:
        result["verdict"] = "inconclusive"
        result["verdict_reason"] = "예산을 넘겨야 답이 나오는 단계가 있었다 — " + "; ".join(
            sweep.refused
        )
    else:
        result["verdict"] = "complete"
        result["verdict_reason"] = None
    return result


def _unverified(result: dict) -> list[str]:
    """무엇을 **못 쟀는지** 목록으로 남긴다. 빈 목록은 강한 주장이다."""
    gaps: list[str] = []
    trackgroup = result.get("probe1_trackgroup") or dict()
    if trackgroup.get("stop") != "complete":
        gaps.append(f"① TrackGroup 판독이 {trackgroup.get('stop')} 로 멈췄다")
    elif trackgroup.get("truncated"):
        gaps.append("① TrackGroup 응답이 truncated — 무결론")
    for row in result.get("probe2_candidates") or ():
        if row.get("effect") is None:
            gaps.append(f"② {row['command']} 의 효과를 되읽지 못했다")
    if not (result.get("control_positive_slot") or dict()).get("name_matches"):
        gaps.append("④ 양성 대조군이 이름으로 답하지 않았다 — 계기 의심")
    if (result.get("control_negative") or dict()).get("answered"):
        gaps.append("⑤ 음성 대조군이 생성 전에 값을 답했다 — 부재 판별 불가")
    return gaps


#: 노트는 사람이 읽는다 — 판정어를 한국어로 적고 기계 값을 괄호에 병기한다.
#: 「무결론」은 성공도 실패도 아닌 셋째 상태이며, 그 낱말이 노트에 없으면
#: 읽는 사람이 이 스윕을 실패로 오독한다.
_VERDICT_KO = {"complete": "완결", "inconclusive": "무결론"}


def render_note(result: dict) -> str:
    """프로브 노트. 판정이 아니라 **관측과 그 한계**를 적는다."""
    lines: list[str] = []
    add = lines.append
    add(f"# M3-a 프로브 노트 — 슬롯 {result['slot']} / 시퀀스 {result['sequence']}")
    add("")
    add("SPEC-COPILOT-MUSICSYNC-001 · REQ-019·021·023·025 · AC-020·021·022")
    add("")
    add("## 실행 일자")
    add("")
    add(f"- {result.get('ran_at')}")
    machine_verdict = result.get("verdict")
    add(f"- 판정: **{_VERDICT_KO.get(machine_verdict, machine_verdict)}** (`{machine_verdict}`)")
    if result.get("verdict_reason"):
        add(f"- 사유: {result['verdict_reason']}")
    add("")
    add("## 슬롯 판정")
    add("")
    verdict = result.get("slot_verdict") or dict()
    add(f"- `_timecode_slot_verdict` 재구현 판정: **{verdict.get('verdict')}**")
    if verdict.get("detail"):
        add(f"- 사유: {verdict['detail']}")
    add("")
    add("## 조회 수")
    add("")
    queries = result.get("queries") or dict(total=0, per_probe=dict())
    add(f"- 합계 {queries.get('total')} / 상한 {MAX_QUERIES}")
    # 프로브 수와 조회 수는 **단위가 다르다**(`plan.md` B8 — 0.1.1 까지 이 둘을
    # 섞어 물어 판정선이 안 섰다). 그래서 한 줄에 나란히 적되 상한을 따로 단다.
    add(f"- 프로브 5건(① ② ③ ④ ⑤) / 상한 {MAX_PROBES} — 조회 수와 단위가 다르다")
    for label, count in (queries.get("per_probe") or dict()).items():
        add(f"- `{label}`: {count}")
    add("")
    add("## 쓰기 명령 전문")
    add("")
    writes = result.get("writes") or []
    if not writes:
        add("- 없음 (0건)")
    for command in writes:
        add(f"- `{command}`")
    add(f"- 합계 {len(writes)} / 상한 {MAX_WRITES}")
    for entry in result.get("refused") or ():
        add(f"- 거절: {entry}")
    add("")
    add("## ① TrackGroup 판독")
    add("")
    trackgroup = result.get("probe1_trackgroup") or dict()
    add(f"- 경로: `{trackgroup.get('path')}`")
    add(f"- 자식 {trackgroup.get('listed')}개 · childCount {trackgroup.get('childCount')}")
    add(f"- truncated: {trackgroup.get('truncated')} · 멈춤: {trackgroup.get('stop')}")
    if trackgroup.get("error"):
        add(f"- 사유: {trackgroup['error']}")
    add("")
    add("## ② 재생 명령 후보 (가설 집합 — 실측 아님)")
    add("")
    rows = result.get("probe2_candidates") or []
    if not rows:
        add("- 발화 0건")
    for row in rows:
        add(
            f"- `{row['command']}` — ok={row['ok']} · **효과={row['effect']}** · "
            f"응답: {row.get('detail')}"
        )
    add("")
    add('## ③ rig_paths["timecodes"] 실값')
    add("")
    rig = result.get("probe3_rig_path") or dict()
    add(f"- 코드 실값: `{rig.get('code_value')}`")
    add(f"- M0 문자열: `{rig.get('m0_value')}` · 일치: {rig.get('matches_m0')}")
    add(f"- `DEFAULT_RIG_CONTEXT_PATHS` 등재 여부: {rig.get('in_default_rig_table')}")
    add(f"- 그 경로가 답하는가: {rig.get('answers')}")
    add("")
    add("## ④ ⑤ 대조군 원문")
    add("")
    positive_pool = result.get("control_positive_pool") or dict()
    positive_slot = result.get("control_positive_slot") or dict()
    negative = result.get("control_negative") or dict()
    add(f"- ④ 풀 응답: {positive_pool.get('answered')} · 사유: {positive_pool.get('error')}")
    add(
        f"- ④ 준비 뒤 슬롯 이름: {positive_slot.get('name')} · "
        f"일치: {positive_slot.get('name_matches')}"
    )
    add(f"- ⑤ 생성 전 슬롯 응답: {negative.get('answered')} · 원문: {negative.get('error')}")
    add("")
    add("## 미검증")
    add("")
    gaps = result.get("unverified") or []
    if not gaps:
        add("- (없음) — 위 다섯이 모두 관측됐다")
    for gap in gaps:
        add(f"- {gap}")
    add("")
    add("## 잔여물")
    add("")
    add(f"- {result.get('residue')}")
    add("")
    return "\n".join(lines)


def write_step_log(path: str | Path, log) -> None:
    """단계 로그를 jsonl 로 쓴다 — songcue-m0 `steps.jsonl` 과 같은 필드 집합."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in log:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def make_console_fire(gate):
    """게이트 심사를 먼저 거치고 통과한 줄만 발화하는 통로.

    심사 결과와 발화 결과를 **따로** 싣는다(t66 이 세운 형태) — 둘을 합치면
    게이트가 막은 것과 콘솔이 거절한 것이 같은 「실패」로 뭉개지고, 그 뭉갬이
    「콘솔에 닿은 적 없는 실패」를 관측으로 오독하게 만든다.
    """

    def fire(commands: list[str]) -> list[dict]:
        decision = gate.screen(list(commands))
        if not decision.cleared:
            return [
                dict(
                    command=row.command,
                    ok=False,
                    fired=False,
                    detail="게이트 차단: " + "; ".join(row.reasons),
                )
                for row in decision.commands
            ]
        rows = []
        for command in commands:
            try:
                outcome = gate._execute_cleared(command)
            except Exception as error:  # noqa: BLE001 — 거절 사유를 그대로 싣는다
                rows.append(
                    dict(
                        command=command,
                        ok=False,
                        fired=True,
                        detail=f"{type(error).__name__}: {error}",
                    )
                )
                continue
            rows.append(
                dict(command=command, ok=bool(outcome.ok), fired=True, detail=outcome.detail)
            )
        return rows

    return fire


class _AlwaysApprove:
    """번들 승인 통로. 사람이 계획을 읽고 `--approve` 로 부른다."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _split_candidates(raw: str | None) -> list[str]:
    if raw is None:
        return list(DEFAULT_CANDIDATES)
    return [item.strip() for item in raw.split(";") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3-a 타임코드 재생 문법 프로브")
    parser.add_argument("--host", default="127.0.0.1", help="콘솔 OSC 입력 호스트")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument("--slot", type=int, required=True, help="격리 타임코드 슬롯 번호")
    parser.add_argument("--sequence", type=int, required=True, help="결합할 시퀀스 번호")
    parser.add_argument(
        "--candidates",
        default=None,
        help=(
            "재생 명령 후보를 `;` 로 나눠 준다. `{slot}` 을 슬롯 번호로 채운다. "
            f"{CANDIDATE_ALLOWANCE}건을 넘는 분은 발화하지 않고 거절로 적는다. "
            "기본 목록은 **가설 집합**이다"
        ),
    )
    parser.add_argument("--out", default=None, help="단계 로그 jsonl 경로")
    parser.add_argument("--note", default=None, help="프로브 노트 md 경로")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="쓰기 전문과 조회 계획만 인쇄하고 콘솔을 바인드하지 않는다",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="없으면 계획만 인쇄하고 아무것도 쏘지 않는다",
    )
    args = parser.parse_args(argv)

    candidates = _split_candidates(args.candidates)
    sketch = plan(args.slot, args.sequence, candidates)

    if args.dry_run or not args.approve:
        sketch["fired"] = False
        sketch["dry_run"] = bool(args.dry_run)
        print(json.dumps(sketch, ensure_ascii=False, indent=2))
        return 0

    approval = _AlwaysApprove()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_host="127.0.0.1",
        receive_port=args.listen_port,
        approval_port=approval,
        audit_dir=Path(".moai/state/verify/musicsync-m3a"),
        timeouts=LinkTimeouts(state_query_seconds=6.0),
        attempt_session_backup=False,
    )
    log: list[dict] = []
    try:
        gate = stack.gate
        health = preflight(
            gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
        if health.get("verdict") != "responder_ok":
            print(json.dumps(dict(fired=False, preflight=health), ensure_ascii=False, indent=2))
            return 1
        result = run_sweep(
            state_port=gate.state_port,
            fire=make_console_fire(gate),
            slot=args.slot,
            sequence=args.sequence,
            candidates=candidates,
            log=log,
        )
        result["preflight"] = health
    finally:
        stack.stop()

    result["fired"] = True
    result["approval_requests"] = [list(bundle) for bundle in approval.asked]
    if args.out:
        write_step_log(args.out, log)
        result["step_log"] = str(args.out)
    if args.note:
        note_path = Path(args.note)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(render_note(result), encoding="utf-8")
        result["note"] = str(note_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
