"""승인 단위 — 콘솔 **쓰기**는 배치당 1개, **미리보기**는 세션당 1회
(SPEC-LDBEAT-001 M4, 카드 t549, REQ-LDBEAT-012, AC-LDBEAT-002(b),
AC-LDBEAT-015).

이 모듈은 콘솔에 아무것도 쓰지 않는다 — 순수 상태 객체·순수 함수뿐이다.

- :func:`build_write_approval_batch` — N≥2개의 격자 칸을 배치로 묶어도
  승인 아티팩트는 정확히 1개다(칸마다 별도 승인 N개를 만들지 않는다,
  REQ-LDBEAT-012(a)). 기존 구간 단위 1회 승인 절차(`SPEC-LDRHYTHM-001`
  REQ-LDRHYTHM-001)와 같은 모양이다.
- :class:`PreviewApprovalSession` — 미리보기(Goto Cue/Off Sequence)는
  세션 시작 때 1회만 승인받고, 그 세션 동안의 후속 호출은 재승인 없이
  통과한다(결정⑤, REQ-LDBEAT-012(b)). 이 승인은 **쓰기** 승인
  (`build_write_approval_batch`가 만드는 아티팩트에 대한 감독 승인)을
  대신하지 않는다 — 두 승인 경로는 완전히 독립이다.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

__all__ = [
    "ApprovalBatch",
    "PreviewApprovalSession",
    "build_write_approval_batch",
]


@dataclass(frozen=True)
class ApprovalBatch:
    """구간(또는 묶음) 단위 승인 아티팩트 하나 — 칸이 몇 개든 파일 하나,
    아티팩트 하나(AC-LDBEAT-015)."""

    commands: tuple[str, ...]
    sha256: str
    cell_count: int


def build_write_approval_batch(cells: Sequence[Sequence[str]]) -> ApprovalBatch:
    """``cells``(칸마다의 커맨드 줄 리스트, 순서 보존)를 전부 이어 붙여
    **하나의** 승인 아티팩트로 만든다 — 부분 승인(칸마다 별도 아티팩트)은
    0건이다(REQ-LDBEAT-012(a)). 빈 칸(커맨드 0줄)이 섞여 있어도 ``cell_count``
    는 그 칸을 셈에 포함한다 — "보낼 것이 없다"와 "승인 대상이 아니다"는
    다른 사실이기 때문이다."""
    commands = tuple(line for cell in cells for line in cell)
    text = "".join(f"{line}\n" for line in commands)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ApprovalBatch(commands=commands, sha256=digest, cell_count=len(cells))


@dataclass
class PreviewApprovalSession:
    """REQ-LDBEAT-012(b), AC-LDBEAT-002(b) — 미리보기 승인의 세션-1회-반복
    상태. ``approve()``가 세션 시작 1회 승인을 기록하고, 그 뒤
    ``authorize_preview()``는 그 세션 동안 몇 번을 불러도 ``True``다.

    이 클래스에는 "쓰기 승인됨" 개념이 아예 없다 — 쓰기 승인은
    :func:`build_write_approval_batch`가 만든 아티팩트를 감독이 매번
    확인하는 별도 절차이고(REQ-LDBEAT-012(a)), 이 세션 상태와 섞이면
    "미리보기 1회 승인이 쓰기까지 뚫어준다"는 안전 위반이 생긴다."""

    _approved: bool = field(default=False)

    def approve(self) -> None:
        """세션 시작 때 미리보기 승인 1회를 기록한다."""
        self._approved = True

    @property
    def is_approved(self) -> bool:
        return self._approved

    def authorize_preview(self) -> bool:
        """미리보기(Goto Cue/Off Sequence) 호출 1회를 승인 상태로 통과
        시킬지 — 이미 ``approve()``를 받았으면 ``True``(재승인 프롬프트
        없이 통과), 아직이면 ``False``(승인 필요)."""
        return self._approved
