"""LX-SEQ `mm:ss.f` 시각 판독 — 결과는 값이 아니라 **종류**다.

SPEC-COPILOT-MUSICSYNC-001 M1 (REQ-MUSICSYNC-002·003·006).

이 모듈이 존재하는 이유는 하나다. 「초 또는 없음」으로 판독하면 미확정 세 갈래
(`확인필요` · 빈칸 · 형식 불명)가 하나의 `None` 으로 뭉개지고, 그 `None` 은
언젠가 어딘가에서 `or 0` 을 만난다. 그 순간 그 큐는 **첫 박에 발사된다.**
그래서 판독 결과는 다섯 갈래의 **명시적 값**이며, 미확정은 숫자를 아예 안 든다.

정본 형식은 SMPTE `hh:mm:ss:ff` 가 아니라 `mm:ss.f` 다(LX-SEQ-SPEC-v2.1 §3.1).
PRE-ROLL 은 음수를 허용한다(§3.2, `-00:30.0`).

콘솔 무접촉 · 파일 시스템 무접촉 — 순수 함수만 있다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from server.design.song_plan import TimestampedSection

#: 정상 시각 — 타임라인·`TrigTime` 둘 다 쓴다.
CUE_TIME_OK = "ok"
#: 음수(PRE-ROLL) — `TrigTime` 에만 쓰고 타임라인 투사에서는 뺀다.
CUE_TIME_PREROLL = "preroll"
#: 시트가 스스로 「아직 안 정했다」고 적은 자리.
CUE_TIME_NEEDS_CHECK = "needs_check"
#: 열이 원래 비어 있는 자리.
CUE_TIME_BLANK = "blank"
#: 뭔가 적혀 있는데 `mm:ss.f` 가 아닌 자리 — 「시트를 고쳐라」다.
CUE_TIME_MALFORMED = "malformed"

CUE_TIME_KINDS: tuple[str, ...] = (
    CUE_TIME_OK,
    CUE_TIME_PREROLL,
    CUE_TIME_NEEDS_CHECK,
    CUE_TIME_BLANK,
    CUE_TIME_MALFORMED,
)

#: 🔴 셋은 **서로 다른 사유**다. 사용자가 해야 할 행동이 다르기 때문에 하나로
#: 합치지 않는다 — 「시트를 고쳐라」·「아직 안 정했다」·「이 열은 원래 비었다」.
UNDETERMINED_CUE_TIME_KINDS: tuple[str, ...] = (
    CUE_TIME_NEEDS_CHECK,
    CUE_TIME_BLANK,
    CUE_TIME_MALFORMED,
)

#: 시트가 미확인 시각에 적는 정본 문자열(LX-SEQ-SPEC-v2.1 §3.1).
NEEDS_CHECK_LITERAL = "확인필요"

#: `TC_METHOD` 가 `DERIVED` 일 때 세 곳에 그대로 실리는 문면(REQ-MUSICSYNC-007).
#: 의역하면 AC 의 리터럴 판정이 깨진다 — 문면 그대로 둔다.
DERIVED_NOT_FINAL_LITERAL = "리허설 LTC 대조 전까지 실행 확정본이 아님"

#: CSV 만 준 호출이 적는 정직한 한계(REQ-MUSICSYNC-007). 두 리터럴을 함께 담는다.
NO_SHEET_TIME_REASON = (
    "정본 CUE 시트(xlsx)를 안 줬다 — 시간 정보 없음. 큐는 manual_go 상태로 "
    "남으며 TrigType/TrigTime 줄은 0건이다."
)

_MILLISECONDS_PER_SECOND = 1000
_MILLISECONDS_PER_MINUTE = 60 * _MILLISECONDS_PER_SECOND

#: 분은 60 을 넘어도 된다(정본 RUNTIME 이 `03:56.0` 이지만 긴 곡은 넘는다).
#: 초는 00~59 만 — `00:60.0` 은 오타이지 90 초가 아니다.
#: 소수는 1~3 자리까지만 받는다. 4 자리는 밀리초보다 잘게 적은 값이라
#: 반올림하면 **없는 정밀도를 지어내는** 것이 된다(표준 §3.6 규칙 4).
_PATTERN = re.compile(r"^(?P<sign>-)?(?P<mm>\d{1,3}):(?P<ss>[0-5]\d)(?:\.(?P<frac>\d{1,3}))?$")


@dataclass(frozen=True)
class CueTime:
    """한 칸의 판독 결과. `ms` 는 **판독된 경우에만** 값을 든다.

    🔴 `ms is None` 을 「0」으로 읽지 마라. 미확정 큐는 발사되지 않는 것이
    맞고, 0 은 첫 박이다.
    """

    kind: str
    raw: str
    ms: int | None = None

    @property
    def is_determined(self) -> bool:
        """시각으로 쓸 수 있는가 — `TrigTime` 발화 가능 여부다."""
        return self.kind in (CUE_TIME_OK, CUE_TIME_PREROLL)

    @property
    def is_timeline_eligible(self) -> bool:
        """타임라인 투사에 앉을 수 있는가 — PRE-ROLL 은 여기서 빠진다."""
        return self.kind == CUE_TIME_OK

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "raw": self.raw, "ms": self.ms}


# @MX:ANCHOR: [AUTO] 시트 텍스트가 **콘솔 발사 시각**으로 바뀌는 유일한 관문이다.
# @MX:REASON: REQ-MUSICSYNC-002·003. 이 함수 밖에서 `mm:ss.f` 를 다시 해석하는
#   경로가 생기면 두 벌의 판독이 갈리고, 그중 관대한 쪽이 미확정을 숫자로
#   바꾼다 — 그 숫자는 곧 `TrigTime` 이 되어 큐를 첫 박에 발사한다. 결과가
#   `CueTime` 이라는 **종류**인 것도 같은 이유다: `int | None` 이면 호출자가
#   `or 0` 을 붙일 자리가 생긴다.
# @MX:SPEC: SPEC-COPILOT-MUSICSYNC-001
def parse_cue_time(value: object) -> CueTime:
    """`mm:ss.f` 한 칸을 다섯 갈래 중 하나로 판독한다. 순수 함수."""
    if value is None:
        return CueTime(kind=CUE_TIME_BLANK, raw="")
    if not isinstance(value, str):
        # 숫자·날짜 객체를 초로 넘겨짚지 않는다 — 넘겨짚으면 그 추측이
        # 콘솔의 발사 시각이 된다. 사람이 시트를 고치게 한다.
        return CueTime(kind=CUE_TIME_MALFORMED, raw=str(value))
    raw = value.strip()
    if not raw:
        return CueTime(kind=CUE_TIME_BLANK, raw="")
    if raw == NEEDS_CHECK_LITERAL:
        return CueTime(kind=CUE_TIME_NEEDS_CHECK, raw=raw)
    hit = _PATTERN.match(raw)
    if hit is None:
        return CueTime(kind=CUE_TIME_MALFORMED, raw=raw)
    frac = hit.group("frac") or ""
    magnitude = (
        int(hit.group("mm")) * _MILLISECONDS_PER_MINUTE
        + int(hit.group("ss")) * _MILLISECONDS_PER_SECOND
        + int(frac.ljust(3, "0") or 0)
    )
    ms = -magnitude if hit.group("sign") and magnitude else magnitude
    kind = CUE_TIME_PREROLL if ms < 0 else CUE_TIME_OK
    return CueTime(kind=kind, raw=raw, ms=ms)


@dataclass(frozen=True)
class CueTimelineProjection:
    """임포트 큐 → 타임라인의 **얕은 투사**.

    `TimestampedSection` 의 `start_ms >= 0` 계약은 건드리지 않는다 —
    두 계약이 모두 옳기 때문에 소비자를 나눈다(design §2.3). 그래서 PRE-ROLL 은
    좌표를 0 으로 접는 대신 **빠지고, 빠졌다고 말한다.**
    """

    sections: tuple[TimestampedSection, ...]
    excluded_preroll: tuple[str, ...]
    undetermined: tuple[str, ...]
    warning: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "sections": [section.to_dict() for section in self.sections],
            "excluded_preroll": list(self.excluded_preroll),
            "undetermined": list(self.undetermined),
            "warning": self.warning,
        }


# @MX:NOTE: [AUTO] 여기서 `TimestampedSection` 을 만드는 것은 그 계약을 **안
#   고치기 위해서**다. `start_ms` 의 `minimum=0`(server/design/song_plan.py)과
#   표준의 음수 PRE-ROLL 허용은 둘 다 옳고, 그래서 완화 대신 소비자를 나눴다.
#   좌표를 옮겨 음수를 0 으로 만들면 시트에 적힌 숫자와 화면의 숫자가 갈린다.
def project_cue_timeline(
    entries: Iterable[Sequence[object]],
    *,
    warning: str | None = None,
) -> CueTimelineProjection:
    """`(cue_no, section, tc_in, tc_out)` 순서열을 타임라인으로 투사한다.

    시트 순서를 그대로 지킨다 — 재정렬은 시트를 고치는 행위이고, 이 앱은
    시트의 주인이 아니다(design §2.4).
    """
    sections: list[TimestampedSection] = []
    excluded: list[str] = []
    undetermined: list[str] = []
    for entry in entries:
        cue_no, label, tc_in, tc_out = entry
        cue_no = str(cue_no)
        if tc_in.kind == CUE_TIME_PREROLL:
            excluded.append(cue_no)
            continue
        if not tc_in.is_timeline_eligible:
            undetermined.append(cue_no)
            continue
        end_ms = None
        if tc_out.is_determined and tc_out.ms is not None and tc_out.ms > tc_in.ms:
            end_ms = tc_out.ms
        sections.append(
            TimestampedSection(
                index=len(sections) + 1,
                label=f"{cue_no} {label}".strip() if str(label).strip() else cue_no,
                start_ms=tc_in.ms,
                end_ms=end_ms,
                source="lxseq_cue_sheet",
            )
        )
    return CueTimelineProjection(
        sections=tuple(sections),
        excluded_preroll=tuple(excluded),
        undetermined=tuple(undetermined),
        warning=warning,
    )
