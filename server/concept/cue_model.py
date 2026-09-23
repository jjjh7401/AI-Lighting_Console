"""큐 모델 v2 타입 — SPEC-LDDESIGN-001 M2 (REQ-LDDESIGN-017~025).

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다(plan.md
M3 "server/concept/ 패키지 신설" 원칙을 M2 도 지킨다). design.md §1 이
스케치한 ``CueV2``/``Timing``/``Headroom``/``MibVerdict`` 타입 개요를
저장소 dataclass 로 옮긴다.

design.md 대비 편차 하나 — ``Headroom.remaining_scale_levels``(정수 1개)를
:class:`RemainingLevels`(모션·딤머 분리)로 바꿨다. G4(REQ-LDDESIGN-048)가
"직전 구간에 남은 **모션** 단계가 1 이상"을 요구해 모션 여력을 딤머
여력과 독립적으로 읽어야 하기 때문이다 — progress.md 에 기록한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from server.concept.vocab import VocabError, validate_operation

__all__ = [
    "LAYERS",
    "TRACKING_MODES",
    "EVIDENCE_GRADES",
    "TIMING_KINDS",
    "MIB_STATUSES",
    "validate_layer",
    "validate_tracking",
    "validate_evidence",
    "validate_timing_kind",
    "layer_limit_warning",
    "Timing",
    "RemainingLevels",
    "Headroom",
    "MibVerdict",
    "CueState",
    "CueV2",
]


# --- REQ-018 — layer 어휘, 5종, 닫힘 -----------------------------------------

LAYERS: tuple[str, ...] = (
    "visibility",
    "environment",
    "architecture",
    "motion",
    "punctuation",
)
_LAYERS_SET = frozenset(LAYERS)


def validate_layer(value: str) -> str:
    """REQ-018 — 5종 밖의 값이면 조립을 거부한다."""
    if value not in _LAYERS_SET:
        raise VocabError(f"layer: 닫힌 어휘(5종) 밖의 값 {value!r}")
    return value


# --- REQ-053 — tracking 어휘, 4종, 닫힘 --------------------------------------

TRACKING_MODES: tuple[str, ...] = ("block", "track", "cue_only", "release")
_TRACKING_MODES_SET = frozenset(TRACKING_MODES)


def validate_tracking(value: str) -> str:
    """REQ-053 — 4종 밖의 값이면 조립을 거부한다."""
    if value not in _TRACKING_MODES_SET:
        raise VocabError(f"tracking: 닫힌 어휘(4종) 밖의 값 {value!r}")
    return value


# --- REQ-022 — evidence 등급, 4종, 닫힘 --------------------------------------

EVIDENCE_GRADES: tuple[str, ...] = (
    "verified",
    "practitioner_pattern",
    "designed_rule",
    "director",
)
_EVIDENCE_GRADES_SET = frozenset(EVIDENCE_GRADES)


def validate_evidence(value: str) -> str:
    """REQ-022 — 4등급 밖의 값이면 조립을 거부한다."""
    if value not in _EVIDENCE_GRADES_SET:
        raise VocabError(f"evidence: 닫힌 어휘(4등급) 밖의 값 {value!r}")
    return value


# --- REQ-058 — timing.kind 어휘, 3종, 닫힘 -----------------------------------

TIMING_KINDS: tuple[str, ...] = ("snap", "short", "long")
_TIMING_KINDS_SET = frozenset(TIMING_KINDS)


def validate_timing_kind(value: str) -> str:
    """REQ-058/024 — 3종 밖의 값이면 조립을 거부한다."""
    if value not in _TIMING_KINDS_SET:
        raise VocabError(f"timing.kind: 닫힌 어휘(3종) 밖의 값 {value!r}")
    return value


# --- REQ-062 — mib.status 어휘, 3종, 닫힘 ------------------------------------

MIB_STATUSES: tuple[str, ...] = ("dark", "mark", "live")
_MIB_STATUSES_SET = frozenset(MIB_STATUSES)


def _validate_mib_status(value: str) -> str:
    if value not in _MIB_STATUSES_SET:
        raise VocabError(f"mib.status: 닫힌 어휘(3종) 밖의 값 {value!r}")
    return value


# --- REQ-018 — 큐 종류별 레이어 상한(린트 경고, 조립을 막지 않는다) ---------
#
# "구간 전환 큐는 레이어 2~3개까지, 프레이즈 전환 큐는 1~2개까지, 비트
# 액센트 큐는 Punctuation 1개만 허용한다(초과 시 린트 경고)" — 하한이
# 아니라 상한만 검사한다(0개는 CueV2.__post_init__ 이 이미 막는다).

CUE_KINDS: tuple[str, ...] = ("section", "phrase", "beat_accent")
_LAYER_UPPER_LIMIT: Mapping[str, int] = {"section": 3, "phrase": 2}


def layer_limit_warning(cue_kind: str, layers: Sequence[str]) -> str | None:
    """REQ-018 — 큐 종류별 레이어 개수 상한을 넘으면 경고 문장을 낸다.

    린트 경고이지 차단이 아니므로(spec.md "초과 시 린트 경고") 이 함수는
    ``VocabError`` 를 던지지 않는다 — 알 수 없는 ``cue_kind`` 는 판정할
    상한이 없다는 뜻으로 보고 경고 없음(``None``)을 낸다.
    """
    layers_set = frozenset(layers)
    if cue_kind == "beat_accent":
        if layers_set != frozenset({"punctuation"}):
            return (
                "비트 액센트 큐는 레이어를 punctuation 1개만 허용하는데 "
                f"{sorted(layers_set)} 를 받음"
            )
        return None
    limit = _LAYER_UPPER_LIMIT.get(cue_kind)
    if limit is None:
        return None
    if len(layers_set) > limit:
        kind_label = {"section": "구간 전환", "phrase": "프레이즈 전환"}[cue_kind]
        return f"{kind_label} 큐는 레이어 {limit}개까지인데 {len(layers_set)}개를 받음"
    return None


# --- REQ-024 — timing 필드 ----------------------------------------------------


@dataclass(frozen=True)
class Timing:
    """REQ-024 — ``kind``/``seconds``/``attr_split``/``stagger`` 4필드.

    ``attr_split`` 은 색·밝기 등 축별 분리 여부다(REQ-060) — 전부
    분리(``True``)/미분리(``False``)이거나, 분리할 축 이름 목록
    (``tuple[str, ...]``)이다.
    """

    kind: str
    seconds: float
    attr_split: bool | tuple[str, ...]
    stagger: str | None

    def __post_init__(self) -> None:
        validate_timing_kind(self.kind)


# --- REQ-025/050 — headroom 필드 ---------------------------------------------


@dataclass(frozen=True)
class RemainingLevels:
    """모션·딤머 상승 여력을 축별로 분리한다.

    design.md §1 은 ``remaining_scale_levels: int`` 하나로 스케치했지만,
    G4(REQ-LDDESIGN-048)는 Final Chorus 직전 구간에 "남은 모션 단계가 1
    이상"인지를 딤머와 독립적으로 요구한다 — 정수 하나로는 둘을 가를 수
    없어 이 SPEC 구현이 2필드로 나눴다(progress.md 편차 기록).
    """

    motion: int
    dimmer: int


@dataclass(frozen=True)
class Headroom:
    """REQ-025/050 — 매 구간 큐마다 담는 4축 헤드룸 계산 결과."""

    unused_groups: int
    reserved_colors: tuple[str, ...]
    reserved_effects: tuple[str, ...]
    remaining: RemainingLevels


# --- REQ-062 — mib 필드 -------------------------------------------------------


@dataclass(frozen=True)
class MibVerdict:
    """REQ-062/063 — 포지션 변화 하나에 대한 MIB(사전 이동) 판정.

    ``mark_insert_at`` 은 판정이 ``mark`` 일 때만 값을 갖는다(REQ-063 —
    Mark 큐를 자동 삽입할 시각).
    """

    status: str
    window_seconds: float
    mark_insert_at: float | None

    def __post_init__(self) -> None:
        _validate_mib_status(self.status)


# --- 큐 상태(해석기 출력) -----------------------------------------------------


@dataclass(frozen=True)
class CueState:
    """큐 하나가 해석된 뒤의 상태 — 3밴드 속성값의 축약형.

    ``color`` 는 팔레트 칸 이름(설계 문서 값 문자열) 그대로다 — RGB 해석은
    이 계층 아래(하류)의 일이다(REQ-017 "3밴드 속성 값 자체... 이 SPEC이
    건드리지 않는다").

    ``secondary`` — 카드 t444(REQ-026/029). 같은 큐가 주색과 함께 띠는
    보조색이다. 입력(운영 경로의 구간 팔레트)이 두 색을 줄 때만 채워지고,
    없으면 ``None`` 이다 — 기존 호출자는 이 칸을 몰라도 그대로 동작한다.
    """

    dim: Mapping[str, int]
    color: str | None
    pos: str
    motion: int
    secondary: str | None = None

    def __post_init__(self) -> None:
        # frozen dataclass 라도 속성 재할당은 object.__setattr__ 로만
        # 가능하다 — dim 을 불변 매핑으로 고정해 호출자의 원본 dict 변경이
        # 이 인스턴스에 새어들지 않게 한다.
        object.__setattr__(self, "dim", MappingProxyType(dict(self.dim)))


# --- 큐 모델 v2 ---------------------------------------------------------------


@dataclass(frozen=True)
class CueV2:
    """REQ-017 — 기존 3밴드 스키마 위에 얹는 7필드 + description + state.

    각 필드는 ``__post_init__`` 에서 검증한다 — 닫힌 어휘 밖의 값은
    :class:`~server.concept.vocab.VocabError` (또는 그 하위 클래스)를
    던진다(REQ-016 과 같은 방향).
    """

    layer: frozenset[str]
    operation: str
    tracking: str
    timing: Timing
    evidence: str
    headroom: Headroom
    mib: MibVerdict | None
    description: str
    state: CueState

    def __post_init__(self) -> None:
        if not self.layer:
            raise VocabError("layer: 최소 1개 이상이어야 한다(REQ-018)")
        for value in self.layer:
            validate_layer(value)
        validate_operation(self.operation)
        validate_tracking(self.tracking)
        validate_evidence(self.evidence)
        if not self.description:
            raise VocabError("description: 빈 문자열일 수 없다(REQ-023)")
