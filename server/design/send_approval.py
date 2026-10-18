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
- :class:`CellLiveApproval` — 칸 편집(옮기기 · 만들기·지우기)을 콘솔에 바로 반영하는 일의
  **범위**별 허락(SPEC-LDRHYTHM-001 TC5). 미리보기 승인과는 다른 객체이고, 한쪽 승인이 다른 쪽을
  열어 주지 않는다.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

from server.design.beat_grid_cell_live import scope_covers

__all__ = [
    "ApprovalBatch",
    "CellLiveApproval",
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


@dataclass
class CellLiveApproval:
    """칸 편집을 콘솔에 바로 반영해도 좋다는 감독의 허락 — **일의 범위**
    (``SCOPE_MOVE``·``SCOPE_CREATE_DELETE``)를 모아 두는 그릇이다.
    ``approve()`` 가 범위를 더하고(합집합), ``covers()`` 는 이번 일에 필요한 범위를
    지금까지의 허락이 모두 덮는지만 답한다.

    ``PreviewApprovalSession`` 과 다른 객체다(하위 클래스도 아니다). 미리보기를 한 번
    허락했다고 칸 편집이 열리지 않고, 칸 편집을 허락했다고 미리보기가 열리지 않는다.
    아무것도 저장하지 않는다 — 새 객체는 늘 빈 채로 시작하고(만들면서 미리 허락해 둘 길이
    없다), 빈 객체는 아무 범위도 덮지 않는다.

    두 스레드가 동시에 ``approve()`` 하면 한쪽이 더한 범위가 사라질 수 있다. 사라지는
    쪽은 허락이 줄어드는 방향이라(다시 묻는다) 안전하다."""

    _approved: frozenset[str] = field(default_factory=frozenset, init=False)

    def approve(self, scope: frozenset[str]) -> None:
        """감독이 허락한 범위를 더한다 — 이미 허락한 범위에 합친다."""
        self._approved = self._approved | scope

    def covers(self, needed: frozenset[str]) -> bool:
        """이번 일에 필요한 범위(``needed``)를 지금까지의 허락이 모두 덮는가. 필요한
        범위가 비어 있으면 덮은 것이다(허락받을 것이 없다)."""
        return scope_covers(self._approved, needed)
