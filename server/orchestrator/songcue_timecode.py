"""M3-b — 운영자 인계와 되읽기 검증 (SPEC-COPILOT-MUSICSYNC-001).

두 가지를 판다.

1. **인계.** 녹화 무장 명령은 앱이 발화하지 않는다. 이 모듈이 그 문자열을 만드는
   **유일한 자리**이고, 만들어진 문자열은 `QuestionRequest.commands[]` 를 타고
   운영자에게 간다(`server/web/question.py`). 번들·`run_commands`·`exec` 어느
   경로에도 들어가지 않는다 — REQ-MUSICSYNC-020 · AC-MUSICSYNC-022.
2. **되읽기 검증.** 운영자가 녹화를 마쳤다고 알리면 앱이 되읽어 본다. 조회는
   **한 번의 검증당 `query_state` 4회 이하**로 코드에서 잠겨 있다
   (:data:`TIMECODE_VERIFY_QUERY_CAP`) — REQ-MUSICSYNC-021 · 025.

**왜 `server/looks/songcue.py` 가 아니라 여기인가.** 검증기는 `StateQueryPort`
를 받는다. `server/looks/**` 는 `test_looks_boundary.py` 가 `server.orchestrator.ports`
를 **금지 모듈 접두사**로 못박아 둔 층이라, 포트를 받는 함수는 그 층에 설 수 없다.
그리고 `tools.py` 는 11,000행이 넘고 형제격인 `_timecode_slot_verdict` 는 팩토리
안의 중첩 함수라 「그 옆」이라 부를 모듈 수준 자리가 없다. 그래서 같은 패키지의
새 모듈이다.

**판정 어휘에 `verified` 는 없다.** 설계서 §5 의 배달본은 **갈래 B** 다 —
M3-a 가 `TrackGroup 1` 아래는 열었으나(`childCount 2`, `MarkerTrack` + `Track`)
재생 명령의 효과는 증명하지 못했고, 이벤트 내용 축은 열리지 않았다. 좁혀진
범위를 성공처럼 적지 않기 위해(REQ-MUSICSYNC-022) 이 모듈이 낼 수 있는 판정은
:data:`VERDICT_UNVERIFIED` · :data:`VERDICT_SKIPPED` · :data:`VERDICT_INCONCLUSIVE`
셋뿐이다.

콘솔 쓰기: **0건.** 이 모듈은 읽기만 한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from server.looks.songcue import SongCueTimingSkip

#: 타임코드 풀의 기본 경로. `tools.py` 의 `TIMECODE_POOL_PATH` 와 같은 값이지만
#: 여기서 다시 적는다 — `tools.py` 가 이 모듈을 import 하므로 반대 방향으로
#: 끌어오면 순환이 된다.
DEFAULT_TIMECODE_POOL_PATH = "DataPool/Timecodes"

#: 검증 **1회당** 허용되는 `query_state` 호출 수. spec.md §A.4 M3-b 행.
TIMECODE_VERIFY_QUERY_CAP = 4

#: 운영자가 손으로 실행할 명령의 서식. 앱은 이것을 **쏘지 않는다.**
_OPERATOR_RECORD_TEMPLATE = "Record Timecode {slot}"

VERDICT_UNVERIFIED = "unverified"
VERDICT_SKIPPED = "SongCueTimingSkip"
VERDICT_INCONCLUSIVE = "inconclusive"

#: 이벤트 내용 축의 이름. 기존 DESCOPE 어휘(`SongCueTimingSkip`)를 그대로 쓴다.
EVENT_CONTENT_AXIS = "timecode_event_content"

_EVENT_CONTENT_SKIP_REASON = (
    "M3-a 2회차는 TrackGroup 1 아래 트랙 목록까지만 열었다 — 트랙 아래 이벤트 "
    "내용은 이 채널로 관측되지 않았으므로(설계서 §5 갈래 B) 이 축은 검증 범위 "
    "밖이며, 좁혀진 사실로 보고한다"
)


class TimecodeQueryBudgetExceeded(RuntimeError):
    """검증 1회의 조회 예산을 넘겨 조회를 **보내지 않고** 멈췄다.

    예산을 넘겨야 답이 나오는 판독은 답이 아니라 무결론이다
    (REQ-MUSICSYNC-025). 그래서 상한은 경고가 아니라 거절이다.
    """


class BudgetedStateReader:
    """조회 장부를 쥔 채 `query_state` 를 중계한다.

    상한에 닿으면 **포트를 부르지 않고** :class:`TimecodeQueryBudgetExceeded` 를
    올린다. 거절된 조회는 장부에 달리지 않는다 — 나가지 않았기 때문이다.
    반대로 포트가 예외를 던진 조회는 **달린다**: 이미 나갔다.
    """

    def __init__(self, port: object, *, cap: int = TIMECODE_VERIFY_QUERY_CAP) -> None:
        self._port = port
        self._cap = int(cap)
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    @property
    def cap(self) -> int:
        return self._cap

    @property
    def remaining(self) -> int:
        return max(0, self._cap - self._count)

    def query(self, path: str) -> object:
        if self._count >= self._cap:
            raise TimecodeQueryBudgetExceeded(
                f"query_state budget of {self._cap} is spent; {path!r} was not sent"
            )
        self._count += 1
        return self._port.query_state(path)  # type: ignore[attr-defined]


# @MX:ANCHOR: [AUTO] 녹화 무장 명령 문자열이 만들어지는 앱 안의 유일한 자리.
# @MX:REASON: REQ-MUSICSYNC-020 / AC-MUSICSYNC-022 — 앱 발화 전수 grep 이 0 이어야
#   하므로, 이 문자열은 인계 경로 하나에서만 생성되고 실행 경로에는 닿지 않는다.
def operator_handoff_commands(timecode_number: int) -> tuple[str, ...]:
    """운영자가 **손으로** 실행할 명령 목록.

    갈래 B 이므로 한 줄뿐이다. M3-a 가 효과를 증명하지 못한 재생 명령은 목록에도
    코드에도 없다(AC-MUSICSYNC-023 둘째 절) — 증명되지 않은 후보를 남기면 다음
    사람이 그것을 근거로 읽는다.
    """
    if isinstance(timecode_number, bool) or not isinstance(timecode_number, int):
        raise TypeError(f"timecode_number must be an int, got {timecode_number!r}")
    if timecode_number < 1:
        raise ValueError(f"timecode_number must be positive, got {timecode_number}")
    return (_OPERATOR_RECORD_TEMPLATE.format(slot=timecode_number),)


@dataclass(frozen=True)
class TimecodeAxisReading:
    """되읽기 한 축 — **값과 함께** 남는다(AC-MUSICSYNC-025).

    ``matched`` 가 ``None`` 인 것은 「대조할 기준을 안 받았다」는 뜻이지
    「일치하지 않았다」가 아니다.
    """

    axis: str
    observed: str
    matched: bool | None = None


@dataclass(frozen=True)
class TimecodeVerification:
    verdict: str
    query_count: int
    axes: tuple[TimecodeAxisReading, ...] = ()
    skipped: tuple[SongCueTimingSkip, ...] = ()
    reason: str = ""
    slot: int | None = None
    handoff_commands: tuple[str, ...] = field(default_factory=tuple)


def _event_content_skip() -> SongCueTimingSkip:
    return SongCueTimingSkip(axis=EVENT_CONTENT_AXIS, reason=_EVENT_CONTENT_SKIP_REASON)


def _children(payload: Mapping[str, object]) -> list[dict]:
    raw = payload.get("children") or ()
    return [child for child in raw if isinstance(child, dict)]  # type: ignore[union-attr]


def _child_count(payload: Mapping[str, object]) -> int | None:
    node = payload.get("node")
    if not isinstance(node, dict):
        return None
    value = node.get("childCount")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


# @MX:ANCHOR: [AUTO] M3-b 되읽기 검증의 단일 진입점.
# @MX:REASON: REQ-MUSICSYNC-021/022/025 — 네 축·조회 상한·좁힘 고지가 한 자리에
#   모여 있어야 「좁힌 것을 성공처럼」 적는 자리가 생기지 않는다.
def verify_songcue_timecode(
    state_port: object,
    timecode_number: int,
    expected_name: str,
    expected_sequence: str,
    *,
    pool_path: str = DEFAULT_TIMECODE_POOL_PATH,
    baseline_pool_child_count: int | None = None,
    event_content_probe_note: str | None = None,
) -> TimecodeVerification:
    """운영자 녹화 뒤의 타임코드 오브젝트를 **조회 4회 이하**로 되읽는다.

    축은 넷이고, 배달본(갈래 B)에서 실제로 도는 것은 셋이다.

    (a) ``pool_presence`` — 풀 ``childCount`` 와 슬롯 존재.
    (b) ``name_match`` — 오브젝트 이름이 준비 단계에서 붙인 이름과 같은가.
    (c) ``trackgroup`` — ``TrackGroup`` 존재와 자식 수·구성.
    (d) ``event_content`` — **M3-a 가 열어 준 경우에만.** 열지 않았으면
        ``event_content_probe_note`` 가 ``None`` 이고, 축은
        :class:`SongCueTimingSkip` 으로 좁혀진 채 보고된다.

    ``truncated: true`` 를 어느 자리에서든 만나면 판정은 성공도 실패도 아닌
    :data:`VERDICT_INCONCLUSIVE` 다 — 잘린 응답의 부재는 부재의 증거가 아니다.
    """
    reader = BudgetedStateReader(state_port)
    slot_path = f"{pool_path}/{timecode_number}"
    axes: list[TimecodeAxisReading] = []
    skipped: list[SongCueTimingSkip] = []
    handoff = operator_handoff_commands(timecode_number)

    def _finish(verdict: str, reason: str = "") -> TimecodeVerification:
        return TimecodeVerification(
            verdict=verdict,
            query_count=reader.count,
            axes=tuple(axes),
            skipped=tuple(skipped),
            reason=reason,
            slot=timecode_number,
            handoff_commands=handoff,
        )

    def _read(path: str) -> tuple[dict | None, str]:
        """``(payload, failure_reason)`` — 실패도 무결론 사유로 돌려준다."""
        try:
            payload = reader.query(path)
        except TimecodeQueryBudgetExceeded as error:
            return None, str(error)
        except Exception as error:  # noqa: BLE001 - 어떤 읽기 실패도 무결론이다
            return None, f"{path} did not answer: {error}"
        if not isinstance(payload, dict):
            return None, f"{path} returned a non-mapping payload"
        if payload.get("truncated"):
            return None, f"{path} enumeration was truncated — the readback is inconclusive"
        return payload, ""

    # -- (a) 풀 --------------------------------------------------------------
    pool, failure = _read(pool_path)
    if pool is None:
        return _finish(VERDICT_INCONCLUSIVE, failure)
    pool_count = _child_count(pool)
    pool_children = _children(pool)
    slot_child = next(
        (child for child in pool_children if child.get("i") == timecode_number), None
    )
    growth = ""
    if isinstance(baseline_pool_child_count, int) and isinstance(pool_count, int):
        growth = f", baseline {baseline_pool_child_count} -> {pool_count}"
    elif pool_count is not None:
        growth = " (baseline not supplied — growth not judged)"
    axes.append(
        TimecodeAxisReading(
            axis="pool_presence",
            observed=(
                f"{pool_path} childCount {pool_count}{growth}; "
                f"slot {timecode_number} "
                + (
                    f"present as {slot_child.get('name')!r}"
                    if slot_child is not None
                    else "absent from the enumeration"
                )
            ),
            matched=slot_child is not None,
        )
    )
    if slot_child is None:
        skipped.append(
            SongCueTimingSkip(
                axis="timecode_readback",
                reason=(
                    f"slot {timecode_number} is not in {pool_path} — the name and "
                    "TrackGroup axes have nothing to read, so they are narrowed out "
                    "rather than reported as failures"
                ),
            )
        )
        skipped.append(_event_content_skip())
        return _finish(
            VERDICT_SKIPPED,
            f"slot {timecode_number} was not found in {pool_path}",
        )

    # -- (b) 이름 ------------------------------------------------------------
    slot_payload, failure = _read(slot_path)
    if slot_payload is None:
        return _finish(VERDICT_INCONCLUSIVE, failure)
    node = slot_payload.get("node")
    observed_name = node.get("name") if isinstance(node, dict) else None
    axes.append(
        TimecodeAxisReading(
            axis="name_match",
            observed=f"node name {observed_name!r} (expected {expected_name!r})",
            matched=observed_name == expected_name,
        )
    )

    # -- (c) TrackGroup ------------------------------------------------------
    group_child = next(
        (child for child in _children(slot_payload) if child.get("class") == "TrackGroup"),
        None,
    )
    if group_child is None:
        axes.append(
            TimecodeAxisReading(
                axis="trackgroup",
                observed=(
                    f"{slot_path} childCount {_child_count(slot_payload)}; "
                    "no TrackGroup child in the enumeration"
                ),
                matched=False,
            )
        )
        skipped.append(_event_content_skip())
        return _finish(VERDICT_UNVERIFIED, "no TrackGroup child to read")

    group_path = f"{slot_path}/TrackGroup {group_child.get('i')}"
    group_payload, failure = _read(group_path)
    if group_payload is None:
        return _finish(VERDICT_INCONCLUSIVE, failure)
    group_children = _children(group_payload)
    listed = ", ".join(f"{c.get('class')} {c.get('name')!r}" for c in group_children)
    track_child = next(
        (
            child
            for child in group_children
            if child.get("class") == "Track" and child.get("name") == expected_sequence
        ),
        None,
    )
    axes.append(
        TimecodeAxisReading(
            axis="trackgroup",
            observed=(
                f"{group_path} childCount {_child_count(group_payload)}; children: {listed}"
                f" (expected a Track named {expected_sequence!r})"
            ),
            matched=track_child is not None,
        )
    )

    # -- (d) 이벤트 내용 — M3-a 가 열어 준 경우에만 --------------------------
    if not event_content_probe_note:
        skipped.append(_event_content_skip())
        return _finish(
            VERDICT_UNVERIFIED,
            "three axes read; the event-content axis is outside the verified scope",
        )

    if track_child is None:
        skipped.append(
            SongCueTimingSkip(
                axis=EVENT_CONTENT_AXIS,
                reason=(
                    "the probe note opens the event axis, but no matching Track was "
                    "enumerated, so there is nothing to read"
                ),
            )
        )
        return _finish(VERDICT_UNVERIFIED, "no matching Track to read events from")

    event_path = f"{group_path}/Track {track_child.get('i')}"
    event_payload, failure = _read(event_path)
    if event_payload is None:
        return _finish(VERDICT_INCONCLUSIVE, failure)
    event_children = _children(event_payload)
    axes.append(
        TimecodeAxisReading(
            axis="event_content",
            observed=(
                f"{event_path} childCount {_child_count(event_payload)}; "
                f"{len(event_children)} event(s) enumerated "
                f"[probe note: {event_content_probe_note}]"
            ),
            matched=None,
        )
    )
    return _finish(
        VERDICT_UNVERIFIED,
        "four axes read; matching the recorded events against the plan is not this "
        "verifier's claim to make",
    )


def render_timecode_verification_report(
    verification: TimecodeVerification,
    *,
    baseline: str,
    residual_risks: Sequence[str] = (),
) -> str:
    """검증 산출물 하나를 **5절 형식**으로 세운다.

    표제 다섯(`주장` · `증거` · `기준 귀속` · `미검증` · `잔여 위험`)은 리터럴로
    존재해야 한다 — AC-MUSICSYNC-024 (a) 가 각각 `grep -c` 로 1 이상을 요구한다.
    판정 필드는 한 줄이고, 그 값은 결코 `verified` 가 아니다.
    """
    slot = verification.slot
    lines: list[str] = [
        f"# 타임코드 되읽기 검증 — Timecode {slot}",
        "",
        f"verdict: {verification.verdict}",
        f"query_count: {verification.query_count} (상한 {TIMECODE_VERIFY_QUERY_CAP})",
        "",
        "## 주장",
        "",
    ]

    if verification.verdict == VERDICT_INCONCLUSIVE:
        lines.append(
            "되읽기가 결론에 닿지 못했다. 성공도 실패도 아닌 **무결론**으로 남긴다."
        )
    elif verification.verdict == VERDICT_SKIPPED:
        lines.append(
            "읽을 대상이 서 있지 않아 검증 범위가 좁혀졌다. 좁혀진 사실을 그대로 적는다."
        )
    else:
        lines.append(
            "타임코드 오브젝트가 존재하고 시퀀스가 매달려 있다는 것까지 관측했다. "
            "여기까지가 이 채널이 말할 수 있는 전부다."
        )
    lines += ["", "## 증거", ""]
    if verification.axes:
        for axis in verification.axes:
            mark = {True: "일치", False: "불일치", None: "대조 기준 없음"}[axis.matched]
            lines.append(f"- `{axis.axis}` [{mark}] — {axis.observed}")
    else:
        lines.append("- 관측된 축이 없다.")
    if verification.reason:
        lines += ["", f"사유: {verification.reason}"]
    if verification.handoff_commands:
        handed = ", ".join(f"`{command}`" for command in verification.handoff_commands)
        lines += [
            "",
            f"운영자 인계분(앱 미발화): {handed}",
        ]

    lines += ["", "## 기준 귀속", "", baseline, "", "## 미검증", ""]
    lines.append(f"- 이 산출물의 판정은 `{verification.verdict}` 이며 `verified` 가 아니다.")
    for skip in verification.skipped:
        lines.append(f"- `SongCueTimingSkip` [{skip.axis}] — {skip.reason}")
    for axis in verification.axes:
        if axis.matched is None:
            lines.append(f"- `{axis.axis}` 는 대조 기준 없이 값만 남았다 — {axis.observed}")

    lines += ["", "## 잔여 위험", ""]
    risks = list(residual_risks)
    if not risks:
        risks = ["별도로 기록된 잔여 위험 없음."]
    for risk in risks:
        lines.append(f"- {risk}")
    lines.append("")
    return "\n".join(lines)
