"""모델이 **사용자에게 되묻는** 통로 — 추측 대신 질문.

없는 픽스처 타입, 좁혀지지 않는 후보, 비어 있는 필수 값. 이런 자리에서 모델이
혼자 판단하면 실물 사고가 난다. 실측 사례: 라이브러리에 없는 타입을 요청받자
모델이 ``Import`` 문법과 GDTF 파일명을 **다섯 번 추측**하고 플러그인까지
배포·실행했으나 장비는 하나도 생기지 않았다(59.6초, ``retries_exhausted``).

이 모듈은 그 자리에 **질문 카드**를 세우고, 답이 올 때까지 부른 쪽을 붙잡아 둔다.

**승인 채널을 쓰지 않는다.** 처음에는 payload를 안 보니 그대로 재사용할 수 있다고
봤는데, 실측에서 도구가 받은 값은 답이 아니라 ``True``였다 —
:class:`~server.web.approval_bridge.ApprovalChannel`\\ 은 **불리언 결정**을 나르도록
만들어졌기 때문이다. 그 결과 ``ask_user``\\ 는 「아직 답을 못 받았다」로 읽었고,
모델은 카드로 답을 받고도 산문으로 같은 것을 다시 물었다. 답이 **글**인 통로는
따로 있어야 한다.

가르는 지점이 하나 더 있다. 승인은 실패하면 **거부**가 안전하다(되돌릴 수 없는
쓰기를 막는다). 질문은 실패해도 거부가 아니다 — 답을 못 받았을 뿐이다. 그래서
연결이 끊기거나 시간이 지나면 :data:`UNANSWERED`\\ 를 내고, 모델은 "사용자가 아직
답하지 않았다"를 사실 그대로 받는다. 없는 답을 지어내지 않게 하는 것이 이 통로의
전부다.
"""

from __future__ import annotations

import itertools
import re
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from server.design.profile import BpmResolution
from server.orchestrator.songcue_timecode import operator_handoff_commands
from server.safety.session_context import DEFAULT_SESSION_KEY, current_session_key

#: 사람이 콘솔 앞에 다녀오는 시간까지 잡아 둔다. 승인(600초)과 같은 눈금.
DEFAULT_QUESTION_TIMEOUT_SECONDS = 600.0

#: 답을 받지 못했을 때의 값 — 거부가 아니라 **미응답**이다.
UNANSWERED = "__unanswered__"

#: 답 대신 사용자가 대화로 잇겠다고 고른 경우.
ANSWER_FREEFORM = "__freeform__"


class _Pending:
    """답 하나를 기다리는 자리."""

    __slots__ = ("event", "answer", "decided")

    def __init__(self) -> None:
        self.event = threading.Event()
        #: 못 받은 채 풀리면 이 값이 그대로 나간다 — 거부가 아니라 미응답.
        self.answer = UNANSWERED
        self.decided = False


@dataclass(frozen=True)
class QuestionOption:
    """고를 수 있는 답 하나."""

    label: str
    #: 이 갈래를 고르면 무슨 일이 일어나는지 — 사용자가 고르기 전에 읽는다.
    description: str = ""
    #: 다중 선택 카드에서 **미리 체크된 채** 뜨는가. 문장이 이미 지목한 항목을
    #: 체크해 두면, 카드는 나머지 선택지도 함께 보여 주면서 "이 문장이 무엇을
    #: 요청했는지"를 그대로 되비춘다. 단일 선택 카드에서는 의미가 없다.
    selected: bool = False


@dataclass(frozen=True)
class QuestionRequest:
    """모델이 사용자에게 던지는 물음 하나.

    ``options``\\ 가 비면 자유 입력 질문이다. 차 있으면 선택지 + 자유 입력이다 —
    선택지가 사용자의 실제 사정을 다 담지 못하는 경우가 실물에서 흔하다.
    """

    #: 무엇을 묻는가. 한국어 한 문장.
    prompt: str
    #: 왜 필요한가. 이유 없는 질문은 사용자를 막는 벽이다.
    why: str = ""
    #: 사용자가 따라 할 수 있는 절차(콘솔 조작 등). 없으면 빈 튜플.
    steps: tuple[str, ...] = ()
    #: 사용자가 콘솔 명령줄에 **그대로 복사해 실행**할 명령들. UI가 복사 버튼과
    #: 함께 렌더한다 — 서버가 대신 실행하면 안 되는 명령(AddFixtures 패치 등)의
    #: 인계 통로다. 없으면 빈 튜플.
    commands: tuple[str, ...] = ()
    options: tuple[QuestionOption, ...] = field(default_factory=tuple)
    #: 여러 개를 **함께** 고를 수 있는 물음인가. 한 문장이 여러 계열을 지정하는
    #: 경우(«포지션, 컬러, 딤머 프리셋을 설정해줘»)가 실물에서 흔한데, 단일
    #: 선택 카드는 그중 하나만 받고 나머지를 조용히 버린다. 참이면 UI가 체크박스
    #: + 「확인」으로 렌더하고, 고른 라벨을 ``", "``\\ 로 이어 하나의 답으로 보낸다
    #: — 답의 **형식**만 다르고 통로는 그대로다(자유 입력도 계속 열려 있다).
    multi: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "why": self.why,
            "steps": list(self.steps),
            "commands": list(self.commands),
            "options": [
                {
                    "label": option.label,
                    "description": option.description,
                    "selected": option.selected,
                }
                for option in self.options
            ],
            "multi": self.multi,
        }


# ---------------------------------------------------------------------------
# 곡 분석 확인 카드 (SPEC-COPILOT-MUSICSYNC-001 M2 · REQ-MUSICSYNC-015)
# ---------------------------------------------------------------------------
#
# 위 :class:`QuestionRequest` 스키마는 **한 글자도 바뀌지 않는다.** 아래는 그
# 스키마로 구간표 카드를 세우는 빌더일 뿐이다 — 구조화 payload 신설은 이 SPEC
# 밖이다(design.md §4.3).
#
# **그리고 이 카드는 모델이 아니라 서버 코드가 세운다.** ``ask_user`` 툴 스키마는
# 「EXACTLY ONE question」이고 ``selected``·``multi``·``commands`` 를 모델에
# 노출하지 않는다. 즉 모델에게 구간표 카드를 부탁하는 경로는 **존재하지 않으며**,
# 존재하는 것처럼 설계하면 런타임에 조용히 축소된 카드가 뜬다.

#: 사람이 템포를 바꿔 적을 때 쓰는 명시적 토큰. 「답 안의 아무 숫자」를 BPM 으로
#: 읽으면 구간 라벨의 초 단위 숫자(``0:00–0:16``)가 템포가 된다.
_BPM_OVERRIDE_PATTERN = re.compile(r"bpm\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)

#: 사람이 적을 수 있는 템포의 상식적 범위. 밖의 값은 **채택하지 않고** 측정값을
#: 그대로 둔다 — 0 이나 음수를 그대로 실으면 ``MusicProfile`` 이 터지고, 터진
#: 자리에서는 「사람이 오타를 냈다」가 「분석이 실패했다」로 읽힌다.
_BPM_MIN = 20.0
_BPM_MAX = 400.0


@dataclass(frozen=True)
class SongSectionProposal:
    """DSP 가 제안한 구간 하나 — 확정이 아니라 **후보**다.

    ``selected`` 가 기본 참인 이유는 design.md §4.3 이다: 미리 켜 두면 사람이
    **끄는 방식**으로 부분 수정할 수 있고, 카드는 나머지 선택지도 함께 보여
    준다.
    """

    start_ms: int
    end_ms: int
    d_level: int
    selected: bool = True


def _format_clock(millis: int) -> str:
    total_seconds = max(0, millis) // 1000
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


# @MX:ANCHOR: [AUTO] 확인 카드 라벨의 단일 생산자 — 카드 빌더·답 파서·세션 기록이 같은 문자열을 든다
# @MX:REASON: 생산 호출자 3곳(build_song_confirmation_card · parse_confirmed_sections ·
#   session.analyse_song_audio). 형식이 바뀌면 라벨 왕복 대조(REQ-SONGCONFIRM-003)와
#   카드 시험(test_song_confirm_card.py)이 함께 깨진다
# @MX:SPEC: SPEC-COPILOT-SONGCONFIRM-001
def section_label(proposal: SongSectionProposal) -> str:
    """제안 하나의 카드 라벨 — ``m:ss–m:ss · D<n>``.

    카드 빌더와 답 파서(:func:`parse_confirmed_sections`)가 **같은 문자열**을
    써야 왕복 대조가 성립한다. 라벨을 만드는 자리는 여기 하나뿐이다.
    """
    span = f"{_format_clock(proposal.start_ms)}–{_format_clock(proposal.end_ms)}"
    return f"{span} · D{proposal.d_level}"


# ---------------------------------------------------------------------------
# 확정 기록 (SPEC-COPILOT-SONGCONFIRM-001 M1 · REQ-SONGCONFIRM-001)
# ---------------------------------------------------------------------------
#
# 카드가 끝난 뒤 남는 **불변 기록**이다. 세션 안에 살고 프로세스를 넘어 저장되지
# 않는다. BPM 은 ``resolve_bpm`` 의 결과를 **읽기만** 한다 — 세션의 ``song_bpm``
# 프로퍼티가 돌려주는 것과 같은 객체여야 한다(REQ-SONGCONFIRM-006, 두 정본 금지).


@dataclass(frozen=True)
class ConfirmedSongSection:
    """확정 카드의 구간 하나 — 제외된 구간도 **남는다**(``selected=False``)."""

    index: int
    label: str
    start_ms: int
    end_ms: int
    d_level: int
    selected: bool
    #: 같은 라벨을 가진 다른 제안이 있어 판정을 **함께** 받았는가(plan.md §B B1 · §F W1).
    label_shared: bool = False


@dataclass(frozen=True)
class ConfirmedSongAnalysis:
    """사람이 확인한 곡 분석 하나 — 정체성 · BPM 해소 · 구간 목록."""

    source_sha256: str
    source_file_name: str
    #: ISO-8601 UTC. 시험은 값이 아니라 형식만 단언한다(plan.md §F W5).
    confirmed_at: str
    bpm: BpmResolution
    sections: tuple[ConfirmedSongSection, ...]

    @property
    def accepted(self) -> tuple[ConfirmedSongSection, ...]:
        """채택된 구간만, ``index`` 순서대로."""
        return tuple(section for section in self.sections if section.selected)

    @property
    def dropped_count(self) -> int:
        return sum(1 for section in self.sections if not section.selected)


def build_song_confirmation_card(
    *,
    proposals: Sequence[SongSectionProposal],
    measured_bpm: float | None = None,
    bpm_confidence: float | None = None,
    sheet_bpm: float | None = None,
    fallback_reason: str | None = None,
) -> QuestionRequest:
    """구간표 확인 카드 하나를 **오늘 스키마로** 세운다.

    ``multi=True`` + 구간당 옵션 1개다. 갈래 셋 중 이것을 택한 근거는
    design.md §4.3 — 3층 변경(서버 스키마 · 와이어 · 렌더러) 없이 오늘 성립하고,
    ``selected=True`` 로 제안을 미리 켜 두면 부분 수정이 되며, 세부 수정은 자유
    입력(:data:`ANSWER_FREEFORM`)이 받는다.

    ``fallback_reason`` 이 있으면 **같은 카드**가 수동 BPM 입력 카드로 선다
    (plan.md §C 결정 1 폴백). 카드 경로 자체는 어느 쪽에서도 살아 있다.
    """
    if not isinstance(proposals, Sequence) or isinstance(proposals, str | bytes):
        raise TypeError(f"proposals must be a sequence of SongSectionProposal, got {proposals!r}")

    options = tuple(
        QuestionOption(
            label=section_label(item),
            description=(
                f"이 구간을 D{item.d_level} 로 잡습니다. "
                "아니면 체크를 풀고 자유 입력으로 고쳐 주세요."
            ),
            selected=item.selected,
        )
        for item in proposals
    )

    lines: list[str] = []
    if fallback_reason:
        lines.append(fallback_reason)
        lines.append("BPM 을 직접 적어 주세요 — 예: 「BPM 128」.")
    elif measured_bpm is not None:
        confidence = "" if bpm_confidence is None else f" (확신 {bpm_confidence:.2f})"
        lines.append(f"측정된 BPM 은 {measured_bpm:g} 입니다{confidence}.")
        lines.append("다르면 「BPM 130」처럼 적어 주세요. 그대로면 이대로 확정합니다.")
        # 배수 후보를 **함께** 적는다. 실측 2026-09-14 (실제 곡 9개,
        # `.moai/reports/threshold-widen-20260914/`): 감독 판정을 정답지로 대조하니
        # 9곡 중 2곡의 BPM 이 두 배로 헛나갔다(117.5 → 진짜 ≈58.7, 161.5 → ≈80.7).
        # BPM 이 두 배면 마디가 절반이므로 `analyze._MIN_SEGMENT_BARS` 의 4마디 하한이
        # 실제로는 2마디로 작동한다 — 두 곡의 진짜 최소 구간이 각각 2.01마디였다.
        #
        # 자동 판별은 네 번 시도해 네 번 실패했다(온셋 다운비트 대조 · 킥 대역
        # 자기상관 · start_bpm=60 사전확률 · 박 교대). 체감 템포의 배수 모호성은
        # 사람 판정이 기준인 지각적 성질이라, 새 검출기를 짓는 대신 이미 있는
        # 자유 입력 통로(`parse_confirmed_bpm`)로 사람이 고르게 한다.
        #
        # 🔴 확신으로 게이트하지 않는다. 실측 9곡의 확신은 0.949~0.978 이고 두 배로
        # 틀린 두 곡(0.963 · 0.977)이 맞은 곡과 같은 대역에 있다 — 확신은 박 간격의
        # 일관성만 재므로 배수 오류에 대해 무증거다. 낮은 확신에서만 보이면 실측된
        # 두 사례를 둘 다 놓친다.
        lines.append(
            f"자동 검출은 배수를 틀릴 수 있습니다 — 절반({measured_bpm / 2:g})이나 "
            f"두 배({measured_bpm * 2:g})로 세신다면 그렇게 적어 주세요."
        )
    else:
        lines.append("BPM 을 직접 적어 주세요 — 예: 「BPM 128」.")

    if sheet_bpm is not None:
        # 어긋남은 **항상** 말한다(REQ-MUSICSYNC-017). 채택 우선순위는 여기서
        # 정하지 않는다 — ``server.design.profile.resolve_bpm`` 이 정본이다.
        lines.append(f"시트 HEAD.BPM 은 {sheet_bpm:g} 입니다 — 대조용으로 함께 적습니다.")

    prompt = "구간과 BPM 을 확인해 주세요." if options else "BPM 을 확인해 주세요."
    return QuestionRequest(
        prompt=prompt,
        why=" ".join(lines),
        options=options,
        multi=True,
    )


# ---------------------------------------------------------------------------
# 타임코드 녹화 인계 카드 (SPEC-COPILOT-MUSICSYNC-001 M3-b · REQ-MUSICSYNC-020)
# ---------------------------------------------------------------------------
#
# 위 :class:`QuestionRequest` 스키마는 여기서도 **한 글자도 바뀌지 않는다.**
# 인계 통로는 이미 있는 ``commands`` 필드다 — 「서버가 대신 실행하면 안 되는
# 명령」을 위해 존재하는 자리이고, 녹화 무장 명령이 정확히 그 부류다.
#
# 명령 문자열 자체는 여기서 짓지 않고 :func:`operator_handoff_commands` 에서
# 받아 온다. 앱 안에서 그 문자열이 만들어지는 자리를 **하나로** 묶어 두어야
# 「앱이 쏘지 않는다」를 grep 하나로 판정할 수 있다(AC-MUSICSYNC-022).


def build_timecode_handoff_card(
    *,
    timecode_number: int,
    timecode_name: str = "",
    sequence_name: str = "",
) -> QuestionRequest:
    """녹화를 **운영자에게 넘기는** 카드 하나를 오늘 스키마로 세운다.

    앱은 이 명령을 발화하지 않는다(REQ-MUSICSYNC-020). 콘솔을 녹화 무장 상태로
    만드는 명령이고, 해제 경로는 ``Off Timecode`` 실측 1회뿐이기 때문이다.

    갈래 B 이므로 인계 목록은 한 줄뿐이다 — M3-a 가 효과를 증명하지 못한 재생
    명령은 여기에 **없다**(AC-MUSICSYNC-023 둘째 절).
    """
    commands = operator_handoff_commands(timecode_number)
    named = f" ({timecode_name})" if timecode_name else ""
    attached = f" 시퀀스 {sequence_name} 가 매달려 있습니다." if sequence_name else ""
    return QuestionRequest(
        prompt=f"Timecode {timecode_number}{named} 녹화를 콘솔에서 직접 실행해 주세요.",
        why=(
            "이 명령은 콘솔을 녹화 무장 상태로 만들기 때문에 앱이 대신 실행하지 "
            "않습니다. 슬롯 준비는 끝났고" + attached + " 남은 것은 LTC 에 맞춘 "
            "녹화뿐입니다. 끝나면 알려 주세요 — 앱이 되읽어 확인합니다."
        ),
        steps=(
            "콘솔 커맨드라인에 아래 명령을 그대로 실행합니다.",
            "LTC 를 재생해 타임코드를 녹화합니다.",
            "녹화를 멈춘 뒤 이 창에 「녹화를 마쳤습니다」라고 알려 주세요.",
        ),
        commands=commands,
    )


def parse_confirmed_bpm(answer: str, *, measured_bpm: float | None = None) -> float | None:
    """사람의 답 하나에서 **확정된 BPM** 을 읽는다 — 없으면 ``None``.

    규칙은 셋뿐이고 전부 명시적이다.

    * :data:`UNANSWERED` · :data:`ANSWER_FREEFORM` → 확정 없음. 미응답은 거부가
      아니라 답을 못 받은 것이고, 없는 답을 지어내지 않는 것이 이 통로의 전부다.
    * ``BPM <숫자>`` 토큰이 있고 상식 범위 안이면 → 그 값(사람의 덮어쓰기).
    * 그 밖에는 → ``measured_bpm`` 을 **그대로 확정**한다. 카드를 있는 그대로
      받아들인 것이 곧 확정이다.

    숫자를 토큰으로 잠그는 이유는 구간 라벨 때문이다 — ``0:00–0:16 · D1`` 에는
    숫자가 셋 들어 있고, 「답 안의 아무 숫자」 규칙이면 그중 하나가 템포가 된다.
    """
    if not isinstance(answer, str) or answer in (UNANSWERED, ANSWER_FREEFORM):
        return None
    match = _BPM_OVERRIDE_PATTERN.search(answer)
    if match is not None:
        typed = float(match.group(1))
        if _BPM_MIN <= typed <= _BPM_MAX:
            return typed
    return measured_bpm


#: UI ``joinChosenLabels`` 가 체크된 라벨을 잇는 구분자(``QuestionCard.tsx``).
_LABEL_JOINER = ", "


def parse_confirmed_sections(
    answer: object, *, proposals: Sequence[SongSectionProposal]
) -> tuple[bool, ...] | None:
    """사람의 답 하나에서 **구간 채택 여부**를 제안마다 읽는다 — 판정 없음이면 ``None``.

    답의 문법은 새로 만들지 않는다. 카드가 나갈 때의 라벨이 체크된 채로 ``", "``
    로 이어져 그대로 돌아오므로(``QuestionCard.tsx`` ``joinChosenLabels``), 판독은
    **라벨 왕복 대조**다(plan.md §C D1). 규칙은 셋이고 :func:`parse_confirmed_bpm`
    과 같은 원칙이다.

    * :data:`UNANSWERED` · :data:`ANSWER_FREEFORM` · 문자열 아님 → 판정 없음.
    * 답에 카드 라벨이 **하나 이상** 들어 있으면 → 들어 있는 라벨의 구간만 채택.
    * 답에 카드 라벨이 **하나도** 없으면 → 전부 채택. 산문(「두 번째는 빼 줘」)도
      BPM 덮어쓰기(「BPM 130」)도 여기다 — 카드를 있는 그대로 받아들인 것이다.

    대조는 답을 ``", "`` 로 나눈 **항목 각각과 라벨의 완전 일치**(양끝 공백 제거 뒤
    ``==``)다. 부분문자열 포함은 대조가 아니다 — ``_format_clock`` 이 분을 0 으로
    채우지 않아 ``1:00–1:15 · D1`` 이 ``11:00–11:15 · D1`` 의 접두가 되기 때문이다.
    같은 라벨을 가진 제안들은 같은 판정을 받는다(가를 수 없다 — plan.md §B B1).
    """
    if not isinstance(answer, str) or answer in (UNANSWERED, ANSWER_FREEFORM):
        return None
    items = {item.strip() for item in answer.split(_LABEL_JOINER)}
    labels = [section_label(proposal) for proposal in proposals]
    if not any(label in items for label in labels):
        return tuple(True for _ in labels)
    return tuple(label in items for label in labels)


class QuestionChannel:
    """물음을 UI로 보내고 **답이 올 때까지 부른 쪽을 붙잡는다.**

    배선은 승인 브리지와 같은 모양이다(``bind``/``unbind``/``resolve``). 다른 것은
    **나르는 값**뿐 — 여기서는 사용자가 고르거나 적은 글이 그대로 온다.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float | None = DEFAULT_QUESTION_TIMEOUT_SECONDS,
        id_prefix: str = "question",
    ) -> None:
        self._timeout = timeout_seconds
        self._id_prefix = id_prefix
        self._counter = itertools.count(1)
        self._notify: dict[object, Callable[[str, QuestionRequest], None]] = {}
        self._pending: dict[str, tuple[object, _Pending]] = {}
        #: 아직 답을 못 받은 물음의 **원본 카드**. 새 연결이 붙을 때 그대로 다시
        #: 보내기 위한 것이고, 답이 정해지는 순간 :meth:`ask` 의 ``finally`` 에서
        #: ``_pending`` 과 함께 지워진다 — 물음 하나에 대한 진실이 두 군데로
        #: 갈라지지 않게 같은 자리에서 나고 같은 자리에서 죽는다.
        self._requests: dict[str, QuestionRequest] = {}
        #: 연결은 끊겼는데 물음이 걸려 있어 보내는 자리를 세워 둔 세션들.
        self._detached: set[object] = set()
        self._lock = threading.Lock()

    # -- UI 쪽 (이벤트 루프) -------------------------------------------------

    def bind(
        self,
        notify: Callable[[str, QuestionRequest], None],
        *,
        session_key: object = DEFAULT_SESSION_KEY,
    ) -> None:
        """UI 하나를 붙이고, **아직 답을 못 받은 물음을 그대로 다시 보낸다.**

        되살림이 여기 있는 이유: 새로고침은 UI만 갈아 끼울 뿐 기다리는 쪽을 없애지
        않는다. 카드가 화면에서만 사라지면 감독은 「서버가 답을 기다리는 물음」을
        화면에서는 볼 수 없는 상태로 남는다 — 세션이 통째로 막힌다.

        다시 보내는 대상은 **아직 결정되지 않은** 물음뿐이다. 다른 탭에서 이미
        답한 물음은 :attr:`_Pending.decided` 가 서 있어 여기서 걸러지므로, 끝난
        것을 다시 묻는 일은 일어나지 않는다.
        """
        with self._lock:
            self._notify[session_key] = notify
            self._detached.discard(session_key)
            self._sweep_detached()
            # 사전 순서 = 물어본 순서. 카드가 여럿 걸려 있어도 순서가 뒤집히지 않는다.
            replay = [
                (request_id, self._requests[request_id])
                for request_id, (key, pending) in self._pending.items()
                if key != session_key and not pending.decided and request_id in self._requests
            ]
        for request_id, request in replay:
            # 락 밖에서 보낸다 — 보내는 쪽이 막히거나 던져도 통로 전체가 굳지 않는다.
            try:
                notify(request_id, request)
            except Exception:
                continue

    def unbind(self, *, session_key: object = DEFAULT_SESSION_KEY) -> None:
        """연결이 끊긴다 — 걸려 있는 물음은 **미응답으로 풀지 않고 세워 둔다.**

        예전에는 여기서 곧바로 :data:`UNANSWERED` 를 냈다. 그러면 새로고침 한
        번에 감독이 답하려던 물음이 「사용자가 답하지 않았다」로 확정되고, 그
        확정은 되돌릴 수 없다. 새로고침은 거절이 아니다.

        기다림이 무한해지지는 않는다 — :meth:`ask` 의 상한(기본 600초)이 그대로
        걸려 있고, 다시 붙는 UI 가 없으면 그 상한에서 :data:`UNANSWERED` 로 끝난다.
        바뀐 것은 「즉시 미응답」이 「상한까지는 답할 수 있음」이 된 것뿐이다.

        보내는 자리(``notify``)도 지우지 않는다. 세워 둔 작업 스레드는 다음 카드를
        같은 자리로 계속 내보내야 하고, 그 자리는 app.py 가 살아 있는 연결로
        되돌려 준다(``_live_target``).
        """
        with self._lock:
            parked = any(
                key == session_key and not pending.decided
                for key, pending in self._pending.values()
            )
            if parked:
                self._detached.add(session_key)
            else:
                self._detached.discard(session_key)
                self._notify.pop(session_key, None)
            self._sweep_detached()

    def _sweep_detached(self) -> None:
        """세워 뒀지만 이제 걸린 물음이 없는 세션의 보내는 자리를 거둔다.

        ``ask`` 가 끝나는 자리에서 거두지 않는 이유: 인터뷰는 카드를 **한 장씩**
        묻는다. Q1 이 끝난 순간 거두면 Q2 가 갈 곳을 잃는다(실측으로 그렇게
        끊겼다). 그래서 거두는 시점을 **연결이 바뀌는 순간**으로 미룬다 — 그때는
        일이 끝났는지 여부가 「걸린 물음이 하나도 없다」로 판정 가능하다.

        호출자가 :attr:`_lock` 을 들고 있어야 한다.
        """
        for key in [
            key
            for key in self._detached
            if not any(
                other_key == key and not pending.decided
                for other_key, pending in self._pending.values()
            )
        ]:
            self._detached.discard(key)
            self._notify.pop(key, None)

    def has_pending(self, *, session_key: object = DEFAULT_SESSION_KEY) -> bool:
        """이 세션에 아직 답을 못 받은 물음이 남아 있는가."""
        with self._lock:
            return any(
                key == session_key and not pending.decided
                for key, pending in self._pending.values()
            )

    def resolve(self, request_id: str, *, answer: str) -> bool:
        """사람의 답 하나를 전한다 — 모르는 id이거나 이미 끝난 물음이면 False."""
        with self._lock:
            entry = self._pending.get(request_id)
            if entry is None:
                return False
            _session_key, pending = entry
            if pending.decided:
                return False
            pending.decided = True
            pending.answer = answer
            pending.event.set()
        return True

    # -- 부르는 쪽 (작업 스레드) ---------------------------------------------

    def ask(
        self,
        request: QuestionRequest,
        *,
        session_key: object | None = None,
    ) -> str:
        """물음을 띄우고 답을 기다린다 — 못 받으면 :data:`UNANSWERED`.

        세션 키를 안 주면 **지금 턴의 세션**에서 가져온다. 승인 브리지와 같은
        규약이다 — 기본값을 상수로 박아 두면 실제로 붙어 있는 UI를 못 찾아 카드가
        아예 안 뜬다(실측에서 그렇게 조용히 미응답이 났다).
        """
        if session_key is None:
            session_key = current_session_key()
        pending = _Pending()
        with self._lock:
            notify = self._notify.get(session_key)
            if notify is None:
                # 볼 사람이 없는 물음은 물음이 아니다. 기다리지 않는다.
                return UNANSWERED
            request_id = f"{self._id_prefix}-{next(self._counter)}"
            self._pending[request_id] = (session_key, pending)
            self._requests[request_id] = request
        try:
            notify(request_id, request)
        except Exception:
            # UI로 못 보냈으면 기다릴 이유가 없다 — 조용히 붙잡고 있으면
            # 대화가 통째로 멈춘 것처럼 보인다.
            with self._lock:
                self._pending.pop(request_id, None)
                self._requests.pop(request_id, None)
            return UNANSWERED
        try:
            pending.event.wait(self._timeout)
            return pending.answer
        finally:
            with self._lock:
                self._pending.pop(request_id, None)
                self._requests.pop(request_id, None)
