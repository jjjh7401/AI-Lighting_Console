"""Chat session — one Korean instruction turn through gate + orchestrator (M5).

Builds the M3 orchestrator on top of the REAL M4 gate ports and reports gate
TRUTH to the chat surface in Korean (REQ-MVP-020/022): blocked / held /
unconfirmed / partial states are never rendered as success. Provider failures
are translated through the Korean error catalog; the raw SDK detail goes to the
diagnostic (audit) log ONLY (REQ-MVP-044).

Measurement (acceptance "왕복 시간 측정 방법"): the session marks turn start at
instruction receipt, the measured execution port marks each console-result
receipt (§2 end event), the approval channel brackets human waits (§3), and the
recorder feeds judged turns to the fallback detector. The orchestrator is built
WITHOUT its own detector wiring so the recorder is the single feed point.

Threading: ``run_instruction`` is synchronous and runs on a worker thread
(``asyncio.to_thread`` in the app layer); ``send_event`` must therefore be
thread-safe (the app wraps the WebSocket send accordingly).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from pathlib import Path

from server.deploy.review import ReviewRequest
from server.design.interview import (
    Q1_CONCEPT,
    Q2_PALETTE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
    STEP_ORDER,
    DirectorInterview,
    UnresolvedAnswer,
)
from server.design.profile import (
    SOURCE_GLOBAL_DEFAULT,
    DirectorOverride,
    MusicProfile,
    SectionMoodResolution,
    UnresolvedMood,
    resolve_section,
)
from server.design.rig import _LAYER_GROUP_ALIASES, build_rig_profile
from server.design.song_cue_composer import (
    SongCueCompositionResult,
    compose_song_cue_bundle,
)
from server.design.song_plan import (
    D_AXIS,
    FX_AXIS,
    PALETTE_AXIS,
    POSITION_AXIS,
    TEXTURE_AXIS,
    AccentDecision,
    ApprovalState,
    DirectorDecision,
    DisabledNote,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
)
from server.llm.types import LLMProvider, ModelTurn, ToolCall, Usage, UserMessage
from server.looks.instantiate import LookInstantiation
from server.looks.songcue import (
    SongCueBundle as TimingSongCueBundle,
)
from server.looks.songcue import (
    SongCueLookSelection,
    SongCueSection,
    SongCueSectionBundle,
    SongCueTimingAxes,
    build_songcue_timing,
    normalise_start_ms,
)
from server.orchestrator.last_created import LastCreated, parse_last_created
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    TIMECODE_POOL_PATH,
    CommandOutcome,
    DeployPipelinePort,
    build_toolset,
)
from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate, ScreenDecision
from server.safety.monitor import HealthMonitor
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key
from server.spatial.mib import PositionCuePlan, position_cue_bundle, premove_follow_command
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    basic_position_presets,
    fan_chain,
    fan_pan_tilt,
    pointing_commands,
    position_cue_store_commands,
    position_preset_store_commands,
    preset_recall_command,
    radial_pan_tilt,
)
from server.spatial.position_cuesheet import PositionSheetSection, build_position_cue_sheet
from server.spatial.position_moods import match_position_mood
from server.spatial.vocabulary import (
    layout_terms_guidance,
    match_explicit_layout,
    parse_ring_layout,
)
from server.web.approval_bridge import ApprovalChannel
from server.web.korean_errors import classify_exception
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    CONSOLE_INPUT_LISTENING,
    CONSOLE_INPUT_UNDETERMINED,
    approval_request_event,
    chat_response_event,
    error_event,
    execution_preview_event,
    notice_event,
    proposal_event,
    question_request_event,
    review_request_event,
    song_timeline_event,
    status_event,
)
from server.web.preview import build_execution_preview
from server.web.question import UNANSWERED, QuestionChannel, QuestionOption, QuestionRequest
from server.web.reply_discovery import ReplyPortMismatch
from server.web.timeline_library import SongTimelineLibrary

# The gate's unconfirmed-execution marker (REQ-MVP-032). String contract pinned
# by tests here AND by the gate's own tests — a wording change fails both.
UNCONFIRMED_MARKER = "execution unconfirmed"

# Rolling conversation memory: how many prior transcript messages (user +
# assistant, so an EVEN cap keeps exchanges paired) travel with each new turn.
# Bounded so token cost per turn stays finite while the model still sees enough
# recent context to keep an in-progress task in mind across follow-ups.
HISTORY_MAX_MESSAGES = 16

# Korean labels for every per-command status the chat surface can show.
STATUS_LABELS: dict[str, str] = {
    "executed_ok": "실행 완료",
    "failed": "실행 실패",
    "not_executed": "미실행 (선행 명령 실패로 중단)",
    "skipped_already_executed": "건너뜀 (중복 실행 방지)",
    "blocked": "차단됨",
    "rejected": "거부됨",
    "proposal": "제안 (라이브 잠금 — 전송되지 않음)",
    "held": "승인 대기",
    "unconfirmed": "실행 미확인 (자동 재전송 안 함)",
}

# Korean summary lines derived from gate bundle decisions (gate truth).
_DECISION_SUMMARY: dict[str, str] = {
    "blocked_console_offline": "콘솔 오프라인 상태입니다 — 신규 명령 실행이 차단되었습니다.",
    "blocked_responder_degraded": (
        "콘솔 응답기가 저하 상태입니다 — 결과 확인이 불가능하여 "
        "부수효과 명령을 시작하지 않았습니다."
    ),
    "blocked_backup_failed": "쇼파일 백업 실패로 실행이 차단되었습니다 (안전 장치).",
    "locked": "라이브 잠금 활성 — 콘솔로 전송하지 않고 제안 카드만 생성했습니다.",
    "rejected": "승인 거부로 번들 전체가 실행되지 않았습니다.",
    "blocked_grammar": "문법 검증에 실패한 명령이 있었습니다.",
}

_TURN_STATUS_SUMMARY: dict[str, str] = {
    "retries_exhausted": "자가 수정 3회 한도에 도달하여 실행에 실패했습니다.",
    "loop_limit": "모델 호출 한도를 초과하여 중단했습니다.",
    "readback_failed": (
        "readback 검증에 실패했습니다 — 콘솔 상태와 요청한 타이밍이 일치하지 않습니다."
    ),
}

_ALL_FIXTURES_ELEVATION = re.compile(
    r"(?:3d|레이아웃|공간).*(?:모든|전체).*(?:장비|픽스처|fixture)"
    r".*(?:5\s*(?:m|미터)|5m).*(?:높이|올려|이동)"
    r"|(?:모든|전체).*(?:장비|픽스처|fixture)"
    r".*(?:5\s*(?:m|미터)|5m).*(?:높이|올려|이동)"
    r"|(?:모든|전체|전부).*(?:장비|픽스처|fixture|조명)"
    r".*(?:바닥(?:으로부터)?|무대(?:\s*바닥)?).*(?:위|기준).*(?:5\s*(?:m|미터)|5m)",
    re.IGNORECASE,
)

# Aim every moving head's beam at one stage point (measured pan/tilt model —
# server/spatial/pointing.py). Trigger: an aiming verb plus either a centre
# word or an explicit coordinate triple.
_POINT_AT_TARGET = re.compile(
    r"(?:바라보|바라볼|비추|비춰|비출|향하|향해|향할|조준|겨냥|point|aim)",
    re.IGNORECASE,
)
_POINT_TARGET_CENTRE = re.compile(r"중앙|센터|가운데|정?중앙|원점|center|centre", re.IGNORECASE)
_POINT_TARGET_TRIPLE = re.compile(
    r"\(?\s*(?P<x>-?\d+(?:\.\d+)?)\s*,\s*(?P<y>-?\d+(?:\.\d+)?)\s*,\s*(?P<z>-?\d+(?:\.\d+)?)\s*\)?"
)
_POINT_DIMMER_ON = re.compile(r"불(?:을|도)?\s*(?:다\s*)?켜|점등|풀\s*디머|dimmer", re.IGNORECASE)

_TYPED_TWO_ROW_REQUEST = re.compile(
    r"(?:mmx).*(?:350m|350\s*m).*(?:1[.,]?5\s*(?:m|미터))"
    r"|(?:350m|350\s*m).*(?:mmx).*(?:1[.,]?5\s*(?:m|미터))",
    re.IGNORECASE,
)

# LOOK-family (design-relation) pan/tilt handlers: fan over an ordered chain,
# or an inward/outward ring around the rig centroid. See
# docs/proposals/pan-tilt-position-preset-strategy.md.
_LOOK_FAN = re.compile(r"부채살|부채꼴|부채|팬\s*(?:아웃|인)|\bfan\b", re.IGNORECASE)
_LOOK_FAN_IN = re.compile(r"모아|모으|모이|converge|팬\s*인|안쪽으로\s*모", re.IGNORECASE)
_LOOK_FAN_CROSS = re.compile(r"교차|크로스|엇갈|cross", re.IGNORECASE)
_LOOK_RING = re.compile(
    r"(?P<dir>안쪽|바깥쪽|바깥|밖)(?:을|으로|를)?\s*(?:다\s*)?(?:바라보|바라볼|향하|향해|비추|비추도록|비출)",
    re.IGNORECASE,
)
_LOOK_SPREAD = re.compile(r"(?:팬\s*)?(?P<value>\d+(?:\.\d+)?)\s*도")
# The second fan axis (Align <> on Tilt): "틸트 15도" names the end-fixture
# tilt offset; "틸트도/팬틸트 모두/입체" without a number takes the default V.
_LOOK_TILT_SPREAD = re.compile(r"틸트\s*(?P<value>-?\d+(?:\.\d+)?)\s*도")
_LOOK_TILT_FAN = re.compile(
    r"틸트\s*(?:도|까지|랑|과|와)|팬\s*[/·]?\s*틸트|pan\s*/?\s*tilt|입체", re.IGNORECASE
)
_LOOK_PRESET_STORE = re.compile(
    r"프리셋\s*(?P<no>\d+)\s*(?:번)?\s*(?:으?로|에)?\s*저장|저장.*?프리셋\s*(?P<no2>\d+)"
)
# Position-cue store (T1, SPEC-COPILOT-CUETIME-001): "프리셋 N(포지션)을
# 시퀀스 S 큐 C로 저장, 페이드 F초". The cue is stored from a PRESET RECALL
# state so it holds a reference (32_spatial_design.md) — regenerating the
# preset re-focuses every cue built on it. The sequence number is the
# operator's call when absent (Store can land on an existing cue).
_CUE_STORE_INTENT = re.compile(r"(?=.*큐)(?=.*저장)", re.DOTALL)
_CUE_PRESET_REF = re.compile(r"프리셋\s*(?:2\s*\.\s*)?(?P<no>\d+)\s*(?:번)?")
_CUE_SEQUENCE_NO = re.compile(r"시퀀스\s*(?P<no>\d+)")
_CUE_NO = re.compile(r"큐\s*(?P<no>\d+(?:\.\d+)?)")
_CUE_FADE = re.compile(
    r"페이드\s*(?P<sec>\d+(?:\.\d+)?)\s*초?|(?P<sec2>\d+(?:\.\d+)?)\s*초\s*페이드"
)
# Song-structure position cue sheet (T3, SPEC-COPILOT-CUETIME-001):
# "포지션 큐 시트 … 시퀀스 S, 프리셋 P번부터[, 페이드 F초]: 이름 시각 무드, …".
# Sections ride "이름 m:ss 무드" (or "이름 N초 무드") comma-separated; the
# preset base is the operator-stated 'Home' slot of the stored basic ten.
_POSITION_SHEET_REQUEST = re.compile(r"포지션\s*큐\s*시트")
_SHEET_SECTION = re.compile(
    r"(?P<name>[가-힣A-Za-z0-9]+)\s+(?P<start>\d+:\d{2}(?:\.\d{1,3})?|\d+(?:\.\d+)?\s*초)"
    r"\s+(?P<mood>.+)$"
)
_SHEET_PRESET_START = re.compile(r"프리셋\s*(?P<no>\d+)\s*(?:번)?\s*부터")
# 무드→포지션 제안 게이트: 포지션 의도 단어가 있어야만 발화한다 — 무드 어휘만
# 있는 문장(색·룩 요청일 수 있음)은 모델 경로(find_looks 등)에 남긴다.
_POSITION_INTENT = re.compile(r"포지션|포커스|방향|바라보|비추|조준|잡아|연출")

# Design-standard cue sheet (M2, SPEC-COPILOT-SONGSTD-001 R1c/R4): a 5-card
# director interview (Q1 컨셉 ~ Q5 질감) precedes the standard profile+rig
# sheet. It remains deliberately distinct from the ordinary-language idea
# helper below: this path has enough production details to create cue writes.
_SONG_DESIGN_REQUEST = re.compile(
    r"디자인\s*(?:큐\s*시트|인터뷰)|연출\s*인터뷰|(?:곡|노래)\s*(?:조명\s*)?설계"
)
# A conversational status check is never an instruction to create, change, or
# replay show data. It must stop before the model fallback, where a previous
# sequence in session context could otherwise be mistaken for a modification
# target.
_STATUS_INQUIRY = re.compile(
    r"^\s*(?:(?:지금|현재)\s*)?(?:진행하고\s*있(?:는(?:거야)?|나요)|진행\s*중(?:이야|인가요)?|"
    r"진행\s*상태|어디까지\s*(?:됐|되었)|실행(?:\s*중)?(?:이야|인가요)?)\s*[?!？]?\s*$",
    re.IGNORECASE,
)

# Someone should be able to begin with an opinion, not console vocabulary.
# This path only prepares a human-readable proposal; it never dispatches
# commands, so it cannot turn a casual opinion into an accidental show change.
_PLAIN_LANGUAGE_DESIGN_REQUEST = re.compile(
    r"(?=.*(?:조명|무대|공연))(?=.*(?:분위기|느낌|아이디어|어떻게|꾸며|만들어|연출|바꿔))",
    re.IGNORECASE,
)

# M2 UI-repro fix: the design-interview path also accepts a 2-token section
# form with no separate mood word — "0:00 도입" (time first) or "도입 0:00"
# (name first) — since a live browser submission in this shape hit the
# "곡 구간을 읽지 못해" refusal (_SHEET_SECTION above requires all three
# tokens). Tried ONLY as a fallback after _SHEET_SECTION in
# ``_song_design_interview`` below, so the existing 3-token "이름 시각 무드"
# behavior (and T3's ``_position_cue_sheet``, which never sees these two
# patterns) is unchanged.
_DESIGN_SHEET_SECTION_TIME_FIRST = re.compile(
    r"(?P<start>\d+:\d{2}(?:\.\d{1,3})?|\d+(?:\.\d+)?\s*초)\s+(?P<name>[가-힣A-Za-z0-9]+)\s*$"
)
_DESIGN_SHEET_SECTION_NAME_FIRST = re.compile(
    r"(?P<name>[가-힣A-Za-z0-9]+)\s+(?P<start>\d+:\d{2}(?:\.\d{1,3})?|\d+(?:\.\d+)?\s*초)\s*$"
)
# Natural-language song briefs often put time before a Korean section label:
# ``0:48 후렴에서 마젠타와 화이트로 터뜨리고``.  This parser belongs only
# to the dedicated song-design route; it does not alter the position cue-sheet
# grammar or silently infer a section from bare timing data.
_DESIGN_SHEET_SECTION_NATURAL_TIME_FIRST = re.compile(
    r"(?P<start>\d+:\d{2}(?:\.\d{1,3})?|\d+(?:\.\d+)?\s*초)\s*"
    r"(?:(?:첫|첫번째)\s*)?(?P<name>인트로|도입|벌스|후렴|브리지|아웃트로|마지막|intro|verse|chorus|bridge|outro|final)"
    r"\s*(?:는|은|에서|에)?\s*(?P<mood>[^,\n]+)",
    re.IGNORECASE,
)


def _is_natural_song_brief(text: str) -> bool:
    """Recognise a user-led song brief without requiring console vocabulary.

    A single timestamp is too ambiguous: it could describe a cue edit or a
    timing question. Two named song sections are enough evidence of a
    full-song design request and remain scoped to this dedicated route.
    """
    return sum(1 for _ in _DESIGN_SHEET_SECTION_NATURAL_TIME_FIRST.finditer(text)) >= 2


_SONG_BPM = re.compile(r"bpm\s*(?P<bpm>\d+(?:\.\d+)?)", re.IGNORECASE)
_SONG_GENRE = re.compile(
    r"장르\s*(?:는|은)?\s*[:\-]?\s*(?P<genre>메탈|록|edm|발라드|팝)", re.IGNORECASE
)
# Skip-if-pre-specified (R1c "지시문에 이미 답이 명시된 문항은 카드 생략"),
# same idiom as _CUE_SEQUENCE_NO/_SHEET_PRESET_START above — only Q1/Q2 have
# a reliable free-form keyword to detect ahead of the interview; Q3-Q5 always
# ride their own card.
_SONG_CONCEPT_HINT = re.compile(r"컨셉\s*(?:은|는)?\s*[:\-]?\s*(?P<concept>[^,:]+)")
_SONG_PALETTE_HINT = re.compile(r"팔레트\s*(?:는|은)?\s*[:\-]?\s*(?P<palette>[^,:]+)")
# DI5 "QN만 다시" 부분 재인터뷰: an interview-card answer carrying "Q<N> 다시"
# is never fed to the current step's parser (it would corrupt a free-text
# step like Q1/Q5) — it restarts from Q<N> instead, keeping every earlier
# answer intact (DirectorInterview.restart_from).
_SONG_RESTART = re.compile(r"[Qq]\s*(?P<no>[1-5])\s*(?:만)?\s*다시")
_SONG_TIMECODE_NO = re.compile(r"(?:타임\s*코드|타임코드|timecode)\s*(?P<no>\d+)", re.IGNORECASE)
_SONG_TIMING_TIMECODE = re.compile(r"타임\s*코드|타임코드|timecode", re.IGNORECASE)
_SONG_TIMING_TRIG_TIME = re.compile(
    r"trig\s*time|트리그\s*타임|트리거\s*타임|자동\s*진행|시간\s*트리거",
    re.IGNORECASE,
)
_SONG_TIMING_MANUAL = re.compile(r"manual|수동|고\s*버튼|go\s*버튼|버튼\s*고", re.IGNORECASE)
_SONG_APPROVAL_APPROVE = re.compile(
    r"^(?:승인|승인합니다|좋아요|진행|진행해|실행|실행해|approve|approved|ok|yes)\s*[.!。]?$",
    re.IGNORECASE,
)
_SONG_CLIMAX_SECTION = re.compile(
    r"후렴|드롭|클라이맥스|피크|chorus|drop|climax|peak", re.IGNORECASE
)
_SAFE_SONG_CUE_NAME = re.compile(r"[A-Za-z0-9 _-]+")

_DI_RECORD_AXES = {
    Q1_CONCEPT: PALETTE_AXIS,
    Q2_PALETTE: PALETTE_AXIS,
    Q3_CLIMAX: D_AXIS,
    Q4_SPATIAL_STORY: POSITION_AXIS,
    Q5_TEXTURE: TEXTURE_AXIS,
}

_DI_STEP_LABELS: dict[str, str] = {
    Q1_CONCEPT: "Q1 컨셉",
    Q2_PALETTE: "Q2 팔레트",
    Q3_CLIMAX: "Q3 클라이맥스",
    Q4_SPATIAL_STORY: "Q4 공간 스토리",
    Q5_TEXTURE: "Q5 질감",
}


def _describe_di_value(value: object) -> str:
    """One audit line's value half — DirectorOverride (Q3/Q4) or the plain
    string every other step's value already is (DI6)."""
    if isinstance(value, DirectorOverride):
        parts: list[str] = []
        if value.d_level is not None:
            parts.append(f"D{value.d_level}")
        if value.color_tendency is not None:
            parts.append(value.color_tendency)
        if value.position_candidates is not None:
            parts.append(" → ".join(value.position_candidates))
        return ", ".join(parts) if parts else "(오버라이드 없음)"
    return str(value)


def _is_explicit_song_approval(answer: str | None) -> bool:
    if not answer:
        return False
    return _SONG_APPROVAL_APPROVE.fullmatch(answer.strip()) is not None


def _timing_mode_from_text(text: str) -> str | None:
    if _SONG_TIMING_TIMECODE.search(text):
        return "timecode"
    if _SONG_TIMING_TRIG_TIME.search(text):
        return "trig_time"
    if _SONG_TIMING_MANUAL.search(text):
        return "manual_go"
    return None


def _timecode_number_from_text(text: str) -> int | None:
    match = _SONG_TIMECODE_NO.search(text)
    return int(match.group("no")) if match is not None else None


def _palette_colors(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return value or ("white",)
    text = str(value)
    colors = tuple(
        chunk.strip()
        for chunk in re.split(r"[/,+、=·\s]+", text)
        if chunk.strip() and chunk.strip() not in ("색", "조합")
    )
    return colors or ("white",)


def _safe_song_cue_name(label: str, cue_number: float) -> str:
    kept = "".join(_SAFE_SONG_CUE_NAME.findall(label)).strip()
    if not kept or kept.isdigit():
        return f"Section {cue_number:g}"
    return kept


def _director_decisions(records: Sequence[object]) -> tuple[DirectorDecision, ...]:
    decisions: list[DirectorDecision] = []
    for record in records:
        step = getattr(record, "step", "")
        axis = _DI_RECORD_AXES.get(step)
        if axis is None:
            continue
        decisions.append(DirectorDecision.from_audit_record(record, axis=axis))
    return tuple(decisions)


def _projection(records: Sequence[object], step: str):
    for record in records:
        if getattr(record, "step", None) == step:
            return getattr(record, "director_decision", None)
    return None


def _record_value(records: Sequence[object], step: str, fallback: object = None) -> object:
    for record in records:
        if getattr(record, "step", None) == step:
            return getattr(record, "value", fallback)
    return fallback


def _record_source(records: Sequence[object], step: str, fallback: str = "standard") -> str:
    for record in records:
        if getattr(record, "step", None) == step:
            source = getattr(record, "source", fallback)
            return source if isinstance(source, str) and source else fallback
    return fallback


def _climax_section_index(sections: Sequence[PositionSheetSection]) -> int:
    for index, section in enumerate(sections, start=1):
        if _SONG_CLIMAX_SECTION.search(f"{section.name} {section.mood}"):
            return index
    return len(sections)


def _distributed_position(
    positions: tuple[str, ...], section_index: int, section_count: int
) -> str | None:
    if not positions:
        return None
    if section_count <= 1 or len(positions) == 1:
        return positions[0]
    slot = round((section_index - 1) * (len(positions) - 1) / (section_count - 1))
    return positions[slot]


def _section_director_override(
    *,
    section_index: int,
    section_count: int,
    records: Sequence[object],
    climax_index: int,
) -> DirectorOverride | None:
    d_level: int | None = None
    color: str | None = None
    positions: tuple[str, ...] | None = None

    q4 = _projection(records, Q4_SPATIAL_STORY)
    spatial_story = getattr(q4, "spatial_story", None)
    if spatial_story is not None:
        position = _distributed_position(
            tuple(getattr(spatial_story, "positions", ()) or ()),
            section_index,
            section_count,
        )
        if position is not None:
            positions = (position,)

    q3 = _projection(records, Q3_CLIMAX)
    climax = getattr(q3, "climax", None)
    if section_index == climax_index and climax is not None:
        projected_d = getattr(climax, "d_level", None)
        if isinstance(projected_d, int):
            d_level = projected_d
        projected_color = getattr(climax, "accent_color", None)
        if isinstance(projected_color, str) and projected_color.strip():
            color = projected_color
        peak_positions = tuple(getattr(climax, "peak_positions", ()) or ())
        if peak_positions:
            positions = peak_positions

    if d_level is None and color is None and positions is None:
        return None
    return DirectorOverride(d_level=d_level, color_tendency=color, position_candidates=positions)


def _texture_decision(records: Sequence[object]) -> TextureDecision:
    texture = _record_value(records, Q5_TEXTURE, "중간")
    return TextureDecision(label=str(texture), source=_record_source(records, Q5_TEXTURE))


def _fx_decision(records: Sequence[object]) -> FxDecision:
    q5 = _projection(records, Q5_TEXTURE)
    texture = getattr(q5, "texture", None)
    density = getattr(texture, "fx_density", "medium")
    if density == "high":
        return FxDecision(
            allowed=("dimmer chase", "pan sweep"),
            source="director_texture",
            density=2,
        )
    if density == "medium":
        return FxDecision(allowed=("dimmer chase",), source="director_texture", density=1)
    return FxDecision(allowed=(), source="director_texture", density=0)


def _accent_decision(
    records: Sequence[object], *, section_index: int, climax_index: int
) -> AccentDecision:
    if section_index != climax_index:
        return AccentDecision()
    q3 = _projection(records, Q3_CLIMAX)
    climax = getattr(q3, "climax", None)
    color = getattr(climax, "accent_color", None)
    if isinstance(color, str) and color.strip():
        return AccentDecision(accents=(f"climax accent {color}",), source="director_climax")
    return AccentDecision(accents=("climax accent",), source="director_climax")


# ── Section look-arc (연출 아크, handoff 결함 3/4) ─────────────────────────
# Role classification drives per-section Texture / FX / Palette / D-level so
# the five-section pop arc (도입→벌스→후렴→브리지→피날레) never collapses to
# one global look. Direct natural-language section intent outranks the Q4
# whole-song spatial story (결함 4 priority: 구간 자연어 > 감독 구간 선택 >
# Q4 > 장르 > fallback).
_SECTION_ROLE_INTRO = re.compile(r"도입|인트로|오프닝|intro", re.IGNORECASE)
_SECTION_ROLE_BRIDGE = re.compile(r"브리지|간주|인터루드|bridge", re.IGNORECASE)
_SECTION_ROLE_VERSE = re.compile(r"벌스|verse", re.IGNORECASE)
_SECTION_ROLE_FINALE = re.compile(r"마지막|피날레|엔딩|아웃트로|outro|finale|ending", re.IGNORECASE)

_ARC_D_LEVEL: dict[str, int] = {"intro": 2, "verse": 3, "chorus": 5, "bridge": 2, "finale": 5}
_ARC_TEXTURE: dict[str, str] = {
    "intro": "긴 페이드 · 정적",
    "verse": "점진 빌드",
    "chorus": "샤프 히트",
    "bridge": "스파스 · 고립",
    "finale": "서스테인 히트",
}
_ARC_FX: dict[str, tuple[tuple[str, ...], int]] = {
    "intro": ((), 0),
    "verse": (("slow pan",), 1),
    "chorus": (("dimmer chase", "pan sweep"), 2),
    "bridge": (("slow tilt",), 1),
    "finale": (("dimmer chase", "accent sweep"), 2),
}
_ARC_PALETTE: dict[str, tuple[str, ...]] = {
    "intro": ("deep blue", "warm special"),
    "verse": ("blue", "cyan"),
    "chorus": ("warm white", "magenta"),
    "bridge": ("cold blue",),
    "finale": ("warm white", "gold"),
}

# Direct positional intent inside one section's own wording. Ordered: an
# audience mention wins over a generic "퍼지/넓혀" in the same sentence.
_DIRECT_POSITION_INTENTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"보컬|vocal|솔로|한\s*명|시선.*모", re.IGNORECASE), ("Vocal DSC",)),
    (re.compile(r"객석|관객|audience|블라인더", re.IGNORECASE), ("Audience",)),
    (re.compile(r"넓혀|넓어지|넓게|확장|폭.*넓|퍼지", re.IGNORECASE), ("Fan Out",)),
    (re.compile(r"비워|비운|비어|고립|미니멀", re.IGNORECASE), ("Wall",)),
)

_COLOR_WORDS = re.compile(
    r"레드|빨강|빨간|블루|파랑|파란|그린|초록|녹색|옐로우|엘로우|노랑|노란|골드|금색"
    r"|마젠타|시안|청록|화이트|흰색|하양|앰버|퍼플|보라|핑크|오렌지|주황"
    r"|red|blue|green|yellow|gold|magenta|cyan|white|amber|purple|pink|orange",
    re.IGNORECASE,
)


def _extract_color_words(text: object) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_COLOR_WORDS.findall(str(text or ""))))


def _section_role(section: PositionSheetSection, *, section_index: int, section_count: int) -> str:
    text = f"{section.name} {section.mood}"
    is_chorus = _SONG_CLIMAX_SECTION.search(text) is not None
    if section_index == section_count and (
        is_chorus or _SECTION_ROLE_FINALE.search(text) is not None
    ):
        return "finale"
    if _SECTION_ROLE_INTRO.search(text):
        return "intro"
    if _SECTION_ROLE_BRIDGE.search(text):
        return "bridge"
    if is_chorus:
        return "chorus"
    if _SECTION_ROLE_VERSE.search(text):
        return "verse"
    return "other"


def _direct_position_intent(text: str) -> tuple[str, ...] | None:
    for pattern, positions in _DIRECT_POSITION_INTENTS:
        if pattern.search(text):
            return positions
    return None


def _section_texture_decision(
    *,
    section: PositionSheetSection,
    section_index: int,
    climax_index: int,
    section_count: int,
    records: Sequence[object],
) -> TextureDecision:
    base = _texture_decision(records)
    role = _section_role(section, section_index=section_index, section_count=section_count)
    label = _ARC_TEXTURE.get(role)
    if label is None:
        return base
    return TextureDecision(
        label=label, source="section_arc", notes=(f"감독 질감 기준: {base.label}",)
    )


def _section_fx_decision(
    *,
    section: PositionSheetSection,
    section_index: int,
    climax_index: int,
    section_count: int,
    records: Sequence[object],
) -> FxDecision:
    base = _fx_decision(records)
    role = _section_role(section, section_index=section_index, section_count=section_count)
    arc = _ARC_FX.get(role)
    if arc is None:
        return base
    allowed, density = arc
    if base.density <= 0:
        # Director asked for a calm texture — the arc never re-enables FX.
        return FxDecision(allowed=(), source="section_arc", disabled=allowed, density=0)
    if base.density == 1 and density > 1:
        allowed, density = allowed[:1], 1
    return FxDecision(allowed=allowed, source="section_arc", density=density)


def _arc_palette(base: tuple[str, ...], role: str) -> tuple[str, ...]:
    arc = _ARC_PALETTE.get(role)
    if arc is None:
        return base or ("white",)
    if not base:
        return arc
    primary = base[0]
    if role in ("intro", "bridge"):
        combined: tuple[str, ...] = (arc[0], primary)
    elif role == "verse":
        combined = (primary, arc[-1])
    else:
        combined = (*arc, primary)
    return tuple(dict.fromkeys(combined))


def _requery_position_from_answer(answer: str) -> str | None:
    """The LAST basic-position name in a requery answer — 'Center → Fan Out'
    lands on Fan Out (the look the section arrives at)."""
    folded = answer.casefold()
    found: list[tuple[int, str]] = []
    for name in BASIC_POSITION_SEQUENCE:
        index = folded.rfind(name.casefold())
        if index >= 0:
            found.append((index, name))
    if not found:
        return None
    return max(found)[1]


def _requery_override(
    answer: str, *, section: PositionSheetSection, section_index: int, section_count: int
) -> DirectorOverride | None:
    """A COMPLETE per-section override from a requery answer, so
    ``resolve_section`` never re-trips on the still-unmatched mood word.
    D/color fill from the section's arc role when the answer names only a
    position."""
    position = _requery_position_from_answer(answer)
    if position is None:
        return None
    role = _section_role(section, section_index=section_index, section_count=section_count)
    colors = _extract_color_words(answer) or _ARC_PALETTE.get(role, ("white",))
    d_match = re.search(r"[Dd]\s*([1-5])", answer)
    d_level = int(d_match.group(1)) if d_match else _ARC_D_LEVEL.get(role, 3)
    if "저조도" in answer or "어둡" in answer:
        d_level = min(d_level, 2)
    return DirectorOverride(
        d_level=d_level,
        color_tendency=colors[0],
        position_candidates=(position,),
    )


def _unresolved_prompt(section: PositionSheetSection, reason: str) -> str:
    return (
        f"{section.name} 구간({section.start_ms / 1000:g}s)의 무드/포지션을 "
        f"해석하지 못했습니다({reason}). 이 구간의 무드를 다시 지정해 주세요."
    )


# Requery cards ride mood-derived option sets per section role (handoff UX:
# "벌스 → [Center → Fan Out] …", "브리지 → [Wall 저조도] …"); every label
# names a basic position so `_requery_position_from_answer` can merge it.
_REQUERY_OPTION_SETS: dict[str, tuple[str, ...]] = {
    "intro": ("Vocal DSC 스페셜", "Home 유지", "Wall 저조도"),
    "verse": ("Center → Fan Out", "Center → Audience", "Fan Out 유지"),
    "chorus": ("Fan Out → Audience", "Ring In 히트", "Audience 블라인더"),
    "bridge": ("Wall 저조도", "Center 스페셜", "Cross 역광"),
    "finale": ("Fan Out → Audience", "Ring In 히트", "Audience 블라인더"),
}
_REQUERY_OPTIONS_DEFAULT: tuple[str, ...] = (
    "Center → Fan Out",
    "Fan Out → Audience",
    "Wall 저조도",
    "Vocal DSC 스페셜",
)

_SONG_REQUERY_CANCEL = re.compile(r"^\s*(취소|중단|그만|cancel)\s*$", re.IGNORECASE)

# Korean role labels for the one-time rig-layer confirmation card (결함 6).
_LAYER_ROLE_LABELS: dict[str, str] = {
    "key": "Key/Front",
    "back": "Back",
    "effect": "Effect/Beam",
    "audience": "Audience",
}

_SINGLE_LAYER_WARNING = (
    "단일 레이어 계획입니다. Front/Back/Beam/Audience 분리 연출은 검증되지 않았습니다."
)

#: The placeholder title `_build_unified_song_plan` stamps on a fresh design —
#: auto-snapshots fall back to the sequence name instead of versioning it.
_DESIGN_INTERVIEW_TITLE = "Design Interview"


def _requery_card_options(
    section: PositionSheetSection, *, section_index: int, section_count: int
) -> tuple[QuestionOption, ...]:
    role = _section_role(section, section_index=section_index, section_count=section_count)
    labels = _REQUERY_OPTION_SETS.get(role, _REQUERY_OPTIONS_DEFAULT)
    return tuple(QuestionOption(label=label) for label in labels)


def _layer_mapping_from_group_children(payload: object) -> list[dict[str, object]]:
    """Role → group-number mapping inferred from console group NAMES, using
    the same exact-match alias table as ``server.design.rig`` (RG5: no
    substring guessing). Group MEMBERSHIP is not readable from the console
    (the drilldown wall), so this records which group carries a role — it
    never claims to know the member fixtures."""
    if not isinstance(payload, Mapping):
        return []
    children = payload.get("children")
    if not isinstance(children, list):
        return []
    mapping: list[dict[str, object]] = []
    for child in children:
        if not isinstance(child, Mapping):
            continue
        name = str(child.get("name") or "")
        number = child.get("i") if isinstance(child.get("i"), int) else child.get("no")
        if not name or not isinstance(number, int):
            continue
        key = name.strip().casefold()
        for role, aliases in _LAYER_GROUP_ALIASES.items():
            if key in aliases:
                mapping.append({"role": role, "group_no": number, "group_name": name})
    return mapping


# Timeline cue edit (user finding, 2026-08-15): "타임라인 큐 3를 무대 중앙으로
# 수정해줘" must target the DISPLAYED director timeline's own sequence and
# update the projection — the model fallback once edited an unrelated sequence
# by name and the timeline never changed. Gated on 타임라인 + 큐 N + a
# recognizable target position; anything else falls through untouched.
_TIMELINE_EDIT_REQUEST = re.compile(r"타임\s*라인")
_TIMELINE_EDIT_CUE = re.compile(r"큐\s*(?P<cue>\d+)")
_TIMELINE_EDIT_POSITIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"무대\s*중앙|중앙|센터|center", re.IGNORECASE), "Center"),
    (re.compile(r"객석|관객|audience|블라인더", re.IGNORECASE), "Audience"),
    (re.compile(r"보컬|vocal", re.IGNORECASE), "Vocal DSC"),
    (re.compile(r"벽|wall", re.IGNORECASE), "Wall"),
    (re.compile(r"팬\s*아웃|부채|fan\s*out", re.IGNORECASE), "Fan Out"),
    (re.compile(r"팬\s*인|fan\s*in", re.IGNORECASE), "Fan In"),
    (re.compile(r"크로스|교차|cross", re.IGNORECASE), "Cross"),
    (re.compile(r"링\s*아웃|ring\s*out", re.IGNORECASE), "Ring Out"),
    (re.compile(r"링\s*인|ring\s*in", re.IGNORECASE), "Ring In"),
    (re.compile(r"홈\s*포지션|home", re.IGNORECASE), "Home"),
)


def _timeline_edit_target_position(text: str) -> str | None:
    """The LAST position word wins — "객석이 아니라 무대 중앙으로" names the
    DESTINATION last, exactly like `_requery_position_from_answer`."""
    best: str | None = None
    best_end = -1
    for pattern, name in _TIMELINE_EDIT_POSITIONS:
        for match in pattern.finditer(text):
            if match.end() > best_end:
                best, best_end = name, match.end()
    return best


# PLAN-stage edit grammar (handoff 2026-08-15 priority 1): while a composed
# plan is pending director approval, "큐 N …" turns edit the PLAN — never the
# console. Delete/insert restructure the section list; a position/color word
# retargets one cue via the same override/mood machinery the requery path uses.
_PLAN_EDIT_DELETE = re.compile(r"큐\s*(?P<cue>\d+)\s*(?:번)?\s*(?:을|를)?\s*(?:삭제|제거|빼)")
_PLAN_EDIT_INSERT_BETWEEN = re.compile(
    r"큐\s*(?P<a>\d+)\s*(?:번)?\s*(?:와|과|이랑|하고)\s*(?:큐\s*)?(?P<b>\d+)\s*(?:번)?\s*사이에\s*"
    r"(?P<name>.+?)\s*(?:구간)?\s*(?:을|를)?\s*추가"
)
_PLAN_EDIT_INSERT_ADJACENT = re.compile(
    r"큐\s*(?P<cue>\d+)\s*(?:번)?\s*(?P<where>뒤|다음|앞)에\s*"
    r"(?P<name>.+?)\s*(?:구간)?\s*(?:을|를)?\s*추가"
)
_PLAN_EDIT_CUE = re.compile(r"큐\s*(?P<cue>\d+)")
# Priority-2 edit vocabulary: dimmer (D1~5 or brighter/darker words), FX
# on/off, and a time move ("큐 2를 0:30으로 이동"). Fade reuses `_CUE_FADE`.
_PLAN_EDIT_D = re.compile(r"[Dd]\s*(?P<d>[1-5])(?!\d)")
_PLAN_EDIT_DARKER = re.compile(r"어둡게|저조도|은은하게")
_PLAN_EDIT_BRIGHTER = re.compile(r"밝게|환하게")
_PLAN_EDIT_FX_OFF = re.compile(r"fx\s*(?:를|은|는)?\s*(?:꺼|끄|없이|오프|off)", re.IGNORECASE)
_PLAN_EDIT_FX_ON = re.compile(r"fx\s*(?:를|은|는)?\s*(?:켜|살려|온|on)", re.IGNORECASE)
_PLAN_EDIT_TIME_MOVE = re.compile(
    r"(?P<time>\d+:\d{2}(?:\.\d{1,3})?|\d+\s*분(?:\s*\d+\s*초)?|\d+(?:\.\d+)?\s*초)\s*"
    r"(?:지점)?\s*(?:로|으로|에)\s*(?:이동|옮|시작)"
)

# 셋리스트 모드 (handoff 2026-08-15 priority 4): allocate the library's songs
# to consecutive setlist sequences (210, 220, …) and page-1 executors (101~).
_SETLIST_REQUEST = re.compile(r"셋\s*리스트|set\s*list", re.IGNORECASE)
_SETLIST_SEQ_START = re.compile(r"시퀀스\s*(?P<no>\d+)\s*(?:번)?\s*부터")
_SETLIST_EXEC_START = re.compile(
    r"(?:executor|익스큐터|이그제큐터|실행기)\s*(?P<no>\d+)\s*(?:번)?\s*부터", re.IGNORECASE
)
#: The library's auto-snapshot stamp — stripped so every version of a song
#: collapses to ONE setlist slot (the newest entry wins).
_SETLIST_AUTO_SUFFIX = re.compile(r"\s*\(자동 v\d+\)\s*$")
_SETLIST_DEFAULT_SEQ_START = 210
_SETLIST_SEQ_STEP = 10
_SETLIST_DEFAULT_EXEC_START = 101


def _setlist_base_name(name: object) -> str:
    return _SETLIST_AUTO_SUFFIX.sub("", str(name or "")).strip()


def _setlist_requested_names(text: str) -> list[str]:
    """Song names after the first ':' (comma-separated), with the numeric
    start directives filtered out. Empty = every library song."""
    _head, _colon, tail = text.partition(":")
    names: list[str] = []
    for part in tail.split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        if _SETLIST_SEQ_START.search(cleaned) or _SETLIST_EXEC_START.search(cleaned):
            continue
        names.append(cleaned)
    return names


def _setlist_node_exists(payload: object) -> bool:
    """True when a ``query_state`` payload names a real console object —
    the responder returns ``{}``/``ok: false``/``node: null`` for holes."""
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return False
    return isinstance(payload.get("node"), dict)


def _setlist_executor_sequence_no(payload: object) -> int | None:
    """The assigned sequence number off an ``Executor <n>`` identity probe —
    the same ``node.sequenceNo`` shape ``cue_monitor``/``dash`` read."""
    if not isinstance(payload, dict):
        return None
    node = payload.get("node")
    if not isinstance(node, dict):
        return None
    value = node.get("sequenceNo")
    if value is None and isinstance(node.get("properties"), dict):
        value = node["properties"].get("sequenceNo")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _plan_edit_fx(decision: FxDecision, override: bool | None) -> FxDecision:
    """Apply a director's PLAN-stage FX on/off: off empties the allowed set
    (audited as disabled); on/None keeps the standard arc decision."""
    if override is False and decision.allowed:
        return FxDecision(allowed=(), source="director_edit", disabled=decision.allowed, density=0)
    return decision


def _plan_edit_d_level(text: str) -> int | None:
    """The PLAN-edit dimmer target: an explicit D1~D5 wins; otherwise the
    darker/brighter words map to the quiet (D2) / bright (D4) tiers."""
    match = _PLAN_EDIT_D.search(text)
    if match is not None:
        return int(match.group("d"))
    if _PLAN_EDIT_DARKER.search(text) is not None:
        return 2
    if _PLAN_EDIT_BRIGHTER.search(text) is not None:
        return 4
    return None


def _plan_edit_remap_overrides(state, key_map) -> None:
    """Re-key every per-cue override dict after a structural edit. ``key_map``
    returns the new 1-based index, or None to drop the entry."""
    for attr in ("requery_overrides", "fade_overrides", "fx_overrides"):
        remapped = {}
        for index, value in getattr(state, attr).items():
            new_index = key_map(index)
            if new_index is not None:
                remapped[new_index] = value
        setattr(state, attr, remapped)


def _plan_edit_time_ms(token: str) -> int | None:
    """Parse the move-target token to milliseconds — 'm:ss', 'N분 M초', 'N초'."""
    token = token.strip()
    minute_match = re.fullmatch(r"(?P<m>\d+)\s*분(?:\s*(?P<s>\d+)\s*초)?", token)
    if minute_match is not None:
        return int(minute_match.group("m")) * 60_000 + int(minute_match.group("s") or 0) * 1_000
    try:
        return normalise_start_ms(token.replace("초", "").strip())
    except Exception:
        return None


def _plan_insert_start_ms(sections: Sequence[PositionSheetSection], insert_slot: int) -> int:
    """A start time strictly inside the neighbouring gap: midpoint between
    neighbours, +30s past the current last section, or half of the first
    section's start when inserting at the head."""
    prev_ms = sections[insert_slot - 1].start_ms if insert_slot > 0 else None
    next_ms = sections[insert_slot].start_ms if insert_slot < len(sections) else None
    if prev_ms is not None and next_ms is not None:
        return (prev_ms + next_ms) // 2
    if prev_ms is not None:
        return prev_ms + 30_000
    return (next_ms or 0) // 2


def _build_unified_song_plan(
    *,
    sections: Sequence[PositionSheetSection],
    profile: MusicProfile,
    rig: object,
    records: Sequence[object],
    timing: TimingPlan,
    sequence_no: int,
    requery_overrides: Mapping[int, DirectorOverride] | None = None,
    palette_mode: str = "palette",
    concept_colors: tuple[str, ...] = (),
    fade_overrides: Mapping[int, float] | None = None,
    fx_overrides: Mapping[int, bool] | None = None,
) -> UnifiedSongLightingPlan:
    climax_index = _climax_section_index(sections)
    section_count = len(sections)
    decisions: list[SectionDecision] = []
    unresolved: list[UnresolvedNote] = []
    roles: list[str] = []
    for index, section in enumerate(sections, start=1):
        role = _section_role(section, section_index=index, section_count=section_count)
        roles.append(role)
        override = _section_director_override(
            section_index=index,
            section_count=section_count,
            records=records,
            climax_index=climax_index,
        )
        # Priority (결함 4): 구간 재질의 답변 > 구간 직접 자연어 의도 > Q3/Q4.
        merged = (requery_overrides or {}).get(index)
        if merged is not None:
            override = merged
        else:
            direct_positions = _direct_position_intent(f"{section.name} {section.mood}")
            if direct_positions is not None:
                override = (
                    replace(override, position_candidates=direct_positions)
                    if override is not None
                    else DirectorOverride(position_candidates=direct_positions)
                )
        resolved = resolve_section(section.mood, profile, director_intent=override)
        if isinstance(resolved, UnresolvedMood):
            unresolved.append(
                UnresolvedNote(
                    axis=POSITION_AXIS,
                    section_index=index,
                    reason=resolved.reason,
                    prompt=_unresolved_prompt(section, resolved.reason),
                )
            )
            fallback = resolve_section(None, profile, director_intent=override)
            if not isinstance(fallback, SectionMoodResolution):
                fallback = SectionMoodResolution(
                    d_level=3,
                    color_tendency="white",
                    position_candidates=("Home",),
                    d_source="fallback",
                    color_source="fallback",
                    position_source="fallback",
                )
            resolved = fallback
        position = resolved.position_candidates[0] if resolved.position_candidates else "Home"
        # D-level: arc replaces only undecided defaults — a mood-word or
        # director tier keeps its value.
        d_level, d_source = resolved.d_level, resolved.d_source
        arc_d = _ARC_D_LEVEL.get(role)
        if arc_d is not None and d_source in (SOURCE_GLOBAL_DEFAULT, "fallback"):
            d_level, d_source = arc_d, "section_arc"
        # Palette: section's own color words > palette-conflict choice > Q2
        # palette blended with the role arc.
        direct_colors = _extract_color_words(section.mood)
        if direct_colors:
            palette_colors, palette_source = direct_colors, "section_text"
        else:
            if palette_mode == "concept" and concept_colors:
                base: tuple[str, ...] = concept_colors
            elif palette_mode == "mixed" and concept_colors and role in ("chorus", "finale"):
                base = concept_colors
            else:
                base = _palette_colors(profile.palette or resolved.color_tendency)
            palette_colors, palette_source = _arc_palette(base, role), "section_arc"
        decisions.append(
            SectionDecision(
                section=TimestampedSection(
                    index=index,
                    label=section.name,
                    start_ms=section.start_ms,
                    source="song_design_interview",
                ),
                d=DLevelDecision(level=d_level, source=d_source),
                palette=PaletteDecision(colors=palette_colors, source=palette_source),
                position=PositionDecision(
                    preset=position,
                    source=resolved.position_source,
                    candidates=resolved.position_candidates,
                ),
                texture=_section_texture_decision(
                    section=section,
                    section_index=index,
                    climax_index=climax_index,
                    section_count=section_count,
                    records=records,
                ),
                fx=_plan_edit_fx(
                    _section_fx_decision(
                        section=section,
                        section_index=index,
                        climax_index=climax_index,
                        section_count=section_count,
                        records=records,
                    ),
                    (fx_overrides or {}).get(index),
                ),
                accent=_accent_decision(records, section_index=index, climax_index=climax_index),
                cue_number=index,
                fade_override=(fade_overrides or {}).get(index),
            )
        )
    # Invariant (결함 3): the finale never lands below the first chorus.
    chorus_levels = [
        decision.d.level
        for decision, role in zip(decisions, roles, strict=True)
        if role == "chorus"
    ]
    if chorus_levels:
        floor = max(chorus_levels)
        for slot, (decision, role) in enumerate(zip(decisions, roles, strict=True)):
            if role == "finale" and decision.d.level < floor:
                decisions[slot] = replace(
                    decision, d=DLevelDecision(level=floor, source="section_arc_invariant")
                )
    disabled = tuple(DisabledNote(axis=FX_AXIS, reason=note) for note in getattr(rig, "notes", ()))
    return UnifiedSongLightingPlan(
        song_title=_DESIGN_INTERVIEW_TITLE,
        sequence_name=f"Sequence {sequence_no}",
        sections=tuple(decisions),
        timing=timing,
        music_profile=profile,
        rig_profile=rig,
        approval=ApprovalState.pending(reviewer="director"),
        director_decisions=_director_decisions(records),
        unresolved=tuple(unresolved),
        disabled=disabled,
    )


def _review_text(plan: UnifiedSongLightingPlan, composition: SongCueCompositionResult) -> str:
    cue_lines: list[str] = []
    if composition.bundle is not None:
        for cue in composition.bundle.cues:
            cue_lines.append(
                f"{cue.cue_number:g} {cue.cue_name}: D{cue.d_level}, "
                f"{cue.position.stored or 'position-tracked'}, "
                f"{'/'.join(cue.color.palette) or 'no-color'}, {cue.timing.trigger}"
            )
    lint = (
        "린트 위반 없음"
        if not composition.lint_findings
        else "린트 {}건: {}".format(
            len(composition.lint_findings),
            "; ".join(
                f"{finding.rule_id}@{finding.cue_number:g} {finding.description}"
                for finding in composition.lint_findings
            ),
        )
    )
    disabled_notes = [
        f"{note.rule_id}: {note.reason}" for note in composition.disabled_rule_notes
    ] + [note.reason for note in composition.disabled_plan_notes]
    disabled = "비활성 규칙 없음" if not disabled_notes else "비활성: " + "; ".join(disabled_notes)
    unresolved = (
        "미해결 없음"
        if not composition.requery_requirements
        else "재질의 필요: "
        + "; ".join(requirement.prompt for requirement in composition.requery_requirements)
    )
    timing = plan.timing.to_dict()
    timeline = " / ".join(cue_lines) if cue_lines else "저장 가능한 큐 없음"
    return (
        f"전곡 리뷰 번들 — {plan.sequence_name}, 타이밍 {timing['mode']}"
        f"{' #' + str(timing['timecode_number']) if timing['timecode_number'] else ''}. "
        f"타임라인: {timeline}. {lint}. {unresolved}. {disabled}."
    )


_SECTION_STATUS_BY_LIFECYCLE: dict[str, str] = {
    "requires_requery": "draft",
    "pending_approval": "draft",
    "approved": "approved",
    "readback_failed": "stored",
    "verified": "verified",
}


def _plan_warnings(plan: UnifiedSongLightingPlan, extra: Sequence[str]) -> list[str]:
    warnings = list(extra)
    if len(plan.sections) > 1:
        looks = {
            (
                tuple(decision.palette.colors),
                decision.texture.label,
                tuple(decision.fx.allowed),
            )
            for decision in plan.sections
        }
        if len(looks) == 1:
            warnings.append("전 구간이 동일한 Palette/Texture/FX입니다 — 연출 아크를 확인하세요.")
    return warnings


def _song_timeline_payload(
    plan: UnifiedSongLightingPlan,
    composition: SongCueCompositionResult,
    *,
    lifecycle: str,
    sequence_no: int,
    readback_verified: bool | None = None,
    readback_message: str | None = None,
    warnings: Sequence[str] = (),
    layer_mapping: Sequence[Mapping[str, object]] = (),
    preset_start: int | None = None,
) -> dict[str, object]:
    """Project the reviewed plan for the runbook UI without exposing commands."""
    bundle = composition.bundle
    mib_section_indexes = (
        {
            cue.section_index
            for cue in bundle.cues
            if cue.kind == "mib_premove" and cue.section_index is not None
        }
        if bundle is not None
        else set()
    )
    # PLAN vs console truth (결함 1): a section is only "stored"/"verified"
    # after the console write + readback; unresolved sections stay flagged.
    unresolved_indexes = {
        note.section_index for note in plan.unresolved if note.section_index is not None
    }
    fade_by_section = (
        {
            cue.section_index: cue.fade_seconds
            for cue in bundle.cues
            if cue.kind == "section" and cue.section_index is not None
        }
        if bundle is not None
        else {}
    )
    default_status = _SECTION_STATUS_BY_LIFECYCLE.get(lifecycle, "draft")
    console_stored = lifecycle in ("readback_failed", "verified")
    return {
        "song_title": plan.song_title,
        "sequence_name": plan.sequence_name,
        "sequence_number": sequence_no,
        "timing_mode": plan.timing.mode,
        "timecode_number": plan.timing.timecode_number,
        "lifecycle": lifecycle,
        "approval": plan.approval.status,
        "director_decisions": [
            {
                "step": decision.step,
                "axis": decision.axis,
                "value": decision.to_dict()["value"],
                "confirmed": decision.confirmed,
                "source": decision.source,
            }
            for decision in plan.director_decisions
        ],
        "sections": [
            {
                "index": decision.section.index,
                "label": decision.section.label,
                "start_ms": decision.section.start_ms,
                "cue_number": decision.cue_number or decision.section.index,
                "plan_status": (
                    "requires_requery"
                    if not console_stored and decision.section.index in unresolved_indexes
                    else default_status
                ),
                "d_level": decision.d.level,
                "palette": list(decision.palette.colors),
                "position": decision.position.preset,
                "texture": decision.texture.label,
                "fx": list(decision.fx.allowed),
                "fade_seconds": fade_by_section.get(decision.section.index),
                "accents": list(decision.accent.accents),
                "mib": decision.section.index in mib_section_indexes,
                "trig_time_seconds": (
                    decision.section.start_seconds if plan.timing.uses_trig_time else None
                ),
            }
            for decision in plan.sections
        ],
        "lint": [
            {
                "rule_id": finding.rule_id,
                "cue_number": finding.cue_number,
                "description": finding.description,
            }
            for finding in composition.lint_findings
        ],
        "unresolved": [
            {
                "axis": note.axis,
                "section_index": note.section_index,
                "reason": note.reason,
            }
            for note in plan.unresolved
        ],
        "disabled": [
            {
                "axis": note.axis,
                "section_index": note.section_index,
                "reason": note.reason,
            }
            for note in plan.disabled
        ],
        "readback": {"verified": readback_verified, "message": readback_message},
        "console_stored": console_stored,
        "warnings": _plan_warnings(plan, warnings),
        "layer_mapping": [dict(entry) for entry in layer_mapping],
        # The basic-position preset base the plan was built on — kept so a
        # later "타임라인 큐 N 수정" edit can rebuild preset references.
        "preset_start": preset_start,
    }


def _song_trig_time_token(start_ms: int) -> str:
    seconds, millis = divmod(start_ms, 1000)
    if millis == 0:
        return str(seconds)
    return f"{seconds}.{millis:03d}".rstrip("0")


def _song_timed_cue_expectations(
    bundle, timing: TimingPlan
) -> tuple[_SongTimedCueExpectation, ...]:
    if not timing.uses_trig_time:
        return ()
    expectations: list[_SongTimedCueExpectation] = []
    for cue in bundle.section_cues:
        start_ms = cue.timing.start_ms
        if start_ms is None:
            continue
        expectations.append(
            _SongTimedCueExpectation(
                cue_no=float(cue.cue_number),
                trig_time=_song_trig_time_token(start_ms),
            )
        )
    return tuple(expectations)


def _song_cue_label(cue_no: float) -> str:
    return str(int(cue_no)) if cue_no.is_integer() else f"{cue_no:g}"


def _readback_key(value: object) -> str:
    return str(value).replace("_", "").replace(" ", "").lower()


def _readback_property(mapping: Mapping[str, object], name: str) -> object | None:
    target = _readback_key(name)
    for key, value in mapping.items():
        if _readback_key(key) == target:
            return value
    for container_name in ("properties", "property", "props"):
        nested = mapping.get(container_name)
        if isinstance(nested, Mapping):
            value = _readback_property(nested, name)
            if value is not None:
                return value
    return None


def _readback_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().strip("'\"")
    try:
        return float(text)
    except ValueError:
        return None


def _readback_seconds(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().strip("'\"")
    clock = re.fullmatch(
        r"(?:(?P<hours>\d+):)?(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)",
        text,
    )
    if clock is not None:
        hours = int(clock.group("hours") or 0)
        minutes = int(clock.group("minutes"))
        seconds = float(clock.group("seconds"))
        return hours * 3600 + minutes * 60 + seconds
    try:
        return float(text)
    except ValueError:
        return None


def _same_trig_time(observed: object, expected: str) -> bool:
    observed_seconds = _readback_seconds(observed)
    expected_seconds = _readback_seconds(expected)
    if observed_seconds is not None and expected_seconds is not None:
        return abs(observed_seconds - expected_seconds) < 0.001
    return str(observed).strip().strip("'\"") == expected


def _song_readback_object_present(payload: object) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if payload.get("ok") is False:
        return False
    if isinstance(payload.get("node"), Mapping):
        return True
    if isinstance(payload.get("children"), list):
        return True
    return any(key in payload for key in ("name", "class", "i", "no", "No", "cueNo"))


def _find_readback_cue(
    children: Sequence[object],
    cue_no: float,
) -> Mapping[str, object] | None:
    for child in children:
        if not isinstance(child, Mapping):
            continue
        for key in ("cueNo", "cue_no", "no", "No"):
            observed = _readback_number(child.get(key))
            if observed is not None and abs(observed - cue_no) < 0.001:
                return child
    return None


def _validate_song_sequence_readback(
    payload: object,
    expectations: Sequence[_SongTimedCueExpectation],
) -> str | None:
    if not _song_readback_object_present(payload):
        return "Sequence readback 응답에 시퀀스 객체가 없습니다."
    if not isinstance(payload, Mapping):
        return "Sequence readback 응답이 객체가 아닙니다."
    children = payload.get("children")
    if expectations and not isinstance(children, list):
        return "Sequence readback 응답에 cue children 목록이 없습니다."
    for expected in expectations:
        cue = _find_readback_cue(children or (), expected.cue_no)
        cue_label = _song_cue_label(expected.cue_no)
        if cue is None:
            return f"Sequence readback에서 timed cue {cue_label}를 찾지 못했습니다."
        trig_type = _readback_property(cue, "TrigType")
        if str(trig_type).strip().strip("'\"").lower() != "time":
            return (
                f"Sequence readback timed cue {cue_label}의 TrigType이 "
                f"Time이 아닙니다: {trig_type!r}"
            )
        trig_time = _readback_property(cue, "TrigTime")
        if not _same_trig_time(trig_time, expected.trig_time):
            return (
                f"Sequence readback timed cue {cue_label}의 TrigTime이 "
                f"{expected.trig_time}이 아닙니다: {trig_time!r}"
            )
    return None


def _validate_song_timecode_readback(payload: object, timecode_number: int) -> str | None:
    if not _song_readback_object_present(payload):
        return f"Timecode readback 응답에 Timecode {timecode_number} 객체가 없습니다."
    return None


# The ten-basic-positions request: build the canonical position sequence for
# THIS rig and store it as consecutive Position presets, asking for the first
# preset number when the instruction does not carry one.
_BASIC_POSITIONS_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?(?:포지션|프리셋|position).*?(?:저장|만들|잡아|생성)",
    re.IGNORECASE | re.DOTALL,
)
_BASIC_POSITIONS_START = re.compile(r"(?P<no>\d+)\s*(?:번)?\s*(?:부터|에서(?:부터)?|번대)")

_REPEATING_TYPE_COLUMNS_REQUEST = re.compile(
    r"(?:\d+\s*열\s*:\s*)?.*mmx.*(?:\d+\s*열\s*:\s*)?.*350\s*m?.*반복",
    re.IGNORECASE,
)
_COLUMN_GAP = re.compile(
    r"(?:열\s*간|열간)\s*간격(?:은|은)?\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)",
    re.IGNORECASE,
)
_FIXTURE_GAP = re.compile(
    r"(?:장비\s*간|장비간)\s*(?:의\s*)?(?:좌우\s*)?간격(?:은|은)?\s*"
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)",
    re.IGNORECASE,
)
_METRE_VALUE = re.compile(r"(\d+(?:[.,]\d+)?)")


def _first_metres(text: str | None) -> float | None:
    """The first number in a free-form spacing answer (e.g. '1.5m' -> 1.5)."""
    if not text:
        return None
    match = _METRE_VALUE.search(text)
    return float(match.group(1).replace(",", ".")) if match else None


@dataclass
class _UploadedVectorworksExport:
    """Ephemeral source/report pair for one WebSocket conversation."""

    content_base64: str | None = None
    file_name: str | None = None
    report: dict[str, object] | None = None

    def replace(self, file_name: str, content_base64: str) -> None:
        self.content_base64 = content_base64
        self.file_name = file_name
        self.report = None

    def clear(self) -> None:
        self.content_base64 = None
        self.file_name = None
        self.report = None


@dataclass
class _PendingRepeatingColumns:
    """The still-incomplete MMX/MMX/350 layout for this chat connection."""

    instruction: str
    row_spacing: float | None = None
    column_spacing: float | None = None


@dataclass
class _SongDesignState:
    """Everything a partially-answered song design needs to resume on a later
    turn: the parsed sections, the (possibly re-openable) interview, and the
    already-collected requery merges. Console writes stay unreachable until
    every requirement in the CURRENT recomposition is resolved."""

    sections: list[PositionSheetSection]
    interview: DirectorInterview
    records: tuple[object, ...]
    rig: object
    fids: list[int]
    timing: TimingPlan
    sequence_no: int
    preset_start: int
    palette_mode: str
    concept_colors: tuple[str, ...]
    plan_warnings: list[str]
    layer_mapping: list[dict[str, object]]
    requery_overrides: dict[int, DirectorOverride]
    fade_overrides: dict[int, float] = dataclass_field(default_factory=dict)
    fx_overrides: dict[int, bool] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class _SongTimedCueExpectation:
    cue_no: float
    trig_time: str


@dataclass(frozen=True)
class _SongReadbackResult:
    paths: tuple[str, ...]
    failure: str | None = None


_VECTORWORKS_UPLOAD_INSTRUCTION = (
    "Vectorworks Instrument Data export를 업로드했습니다. "
    "vectorworks_autopatch로 먼저 도면과 현재 콘솔을 대조하고, 자동 패치 가능한 항목을 "
    "정리해 주세요. 반드시 대조 결과에 없는 값은 추측하지 말고 필요한 값만 질문 카드로 "
    "물어보세요."
)


def outcome_view(outcome: CommandOutcome) -> dict:
    """One per-command chat-surface row with an honest Korean label."""
    status = outcome.status
    if status == "failed" and UNCONFIRMED_MARKER in outcome.detail:
        status = "unconfirmed"  # REQ-MVP-032: unconfirmed is NOT a failure claim
    return {
        "command": outcome.command,
        "status": status,
        "label": STATUS_LABELS.get(status, status),
        "detail": outcome.detail,
    }


def summarize_outcomes(status: str, views: Sequence[dict]) -> str:
    """Compose the outcome-derived Korean summary (gate-truth honesty)."""
    statuses = [view["status"] for view in views]
    parts: list[str] = []
    if status in _TURN_STATUS_SUMMARY:
        parts.append(_TURN_STATUS_SUMMARY[status])
    if "unconfirmed" in statuses:
        parts.append(
            "실행 미확인 명령이 있습니다 — 콘솔에서 실제 실행 여부를 확인해 주세요 "
            "(자동 재전송 안 함)."
        )
    executed = sum(1 for s in statuses if s == "executed_ok")
    incomplete = sum(1 for s in statuses if s in ("failed", "not_executed"))
    if executed and incomplete:
        parts.append("일부 명령만 실행되었습니다 (부분 실행).")
    if (
        status == "ok"
        and statuses
        and all(s in ("executed_ok", "skipped_already_executed") for s in statuses)
    ):
        parts.append("요청한 명령을 모두 실행했습니다.")
    return " ".join(parts)


class SongTimelineStore:
    """Process-wide LAST director-timeline payload (runbook UI). Song-timeline
    events are otherwise push-only within one WebSocket session — the app
    replays ``latest`` to every NEW connection so a page refresh keeps the
    timeline. With a ``path`` (wired by serve.py to the user data dir) the
    payload also survives SERVER restarts: atomic JSON write on every update,
    fail-open read (a corrupt file degrades to "no timeline yet", never a
    startup failure). Path-less stores (tests, bare WebDeps) stay memory-only.
    The payload is a read-only projection — restoring it grants no console
    capability; every write still rides the approval gate."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else None
        self._latest: dict | None = self._load()

    @property
    def latest(self) -> dict | None:
        return self._latest

    @latest.setter
    def latest(self, payload: dict | None) -> None:
        self._latest = payload
        if payload is not None:
            self._save(payload)

    def _load(self) -> dict | None:
        if self._path is None:
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        timeline = data.get("timeline")
        return timeline if isinstance(timeline, dict) else None

    def _save(self, payload: dict) -> None:
        if self._path is None:
            return
        # Atomic same-dir temp + os.replace, mirroring PinStore._save — a crash
        # mid-write must leave the previous file intact.
        try:
            body = json.dumps({"version": 1, "timeline": payload}, ensure_ascii=False)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self._path.parent), prefix=".song-timeline-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(body)
                os.replace(tmp_name, self._path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
                raise
        except (OSError, TypeError, ValueError):
            # Persistence is best-effort: the in-memory replay (page refresh)
            # must keep working even on a read-only disk.
            pass


class _MeasuredExecutionPort:
    """Wraps the gate executor; marks each RECEIVED console result (§2 end)."""

    def __init__(self, inner, recorder: RoundTripRecorder | None) -> None:
        self._inner = inner
        self._recorder = recorder

    def execute(self, command: str) -> ExecutionResult:
        result = self._inner.execute(command)
        if self._recorder is not None and self._is_console_result(result):
            self._recorder.note_console_result()
        return result

    @staticmethod
    def _is_console_result(result: ExecutionResult) -> bool:
        detail = result.detail or ""
        if detail.startswith("blocked:"):
            return False  # gate block — nothing was sent, nothing was received
        # Unconfirmed = timeout: no console result was received (§2 end event).
        return UNCONFIRMED_MARKER not in detail


class _GateLivenessPort:
    """Adapts ``SafetyGate.heartbeat()`` to the preshow ``LivenessPort`` shape.

    SPEC-COPILOT-PRESHOW-001 T-G2: the pre-show OSC checks need a
    ``ping() -> bool``, but the gate exposes ``heartbeat() -> str`` (the
    ``HealthMonitor`` state after probing the console once). The adapter
    lives HERE, in the consuming web layer, rather than in
    ``server/preshow/osc_check.py`` — the preshow package must not import
    ``server.safety`` (that import would blur the package boundary the
    architecture test enforces).

    ``heartbeat()``'s only two branches (``server/safety/gate.py``) are: on a
    successful ping, ``HealthMonitor.note_ping_success`` sets the state to
    ``HealthMonitor.ONLINE`` UNCONDITIONALLY; on a failed/timed-out ping,
    ``note_ping_timeout`` sets it to ``CONSOLE_OFFLINE`` or
    ``RESPONDER_DEGRADED`` — never ``ONLINE``. So comparing the returned
    state against ``HealthMonitor.ONLINE`` exactly recovers THIS ping's own
    success/failure, not some stale prior state.
    """

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate

    def ping(self) -> bool:
        return self._gate.heartbeat() == HealthMonitor.ONLINE


class _ObservingBundleGate:
    """BundleGate wrapper surfacing every screening decision to the session."""

    def __init__(
        self,
        gate: SafetyGate,
        on_preview: Callable[[Sequence[str]], None],
        on_decision: Callable[[ScreenDecision], None],
    ) -> None:
        self._gate = gate
        self._on_preview = on_preview
        self._on_decision = on_decision

    def screen(self, commands: Sequence[str]) -> ScreenDecision:
        self._on_preview(commands)
        decision = self._gate.screen(commands)
        self._on_decision(decision)
        return decision


class ChatSession:
    """One WebSocket client's chat session over the shared gate + provider."""

    def __init__(
        self,
        *,
        gate: SafetyGate,
        provider: LLMProvider,
        system_prefix: str,
        audit: AuditLog,
        send_event: Callable[[dict], None],
        approval_channel: ApprovalChannel,
        recorder: RoundTripRecorder | None = None,
        rig_paths: dict[str, str] | None = None,
        review_channel: ApprovalChannel | None = None,
        question_channel: QuestionChannel | None = None,
        deploy_pipeline: DeployPipelinePort | None = None,
        console_input_probe: Callable[[], str] | None = None,
        reply_port_probe: Callable[[], ReplyPortMismatch | None] | None = None,
        preshow_receive_port: int | None = None,
        preshow_osc_slot: int | None = None,
        timeline_store: SongTimelineStore | None = None,
        timeline_library: SongTimelineLibrary | None = None,
    ) -> None:
        self._gate = gate
        # Injected so the status surface owns the I/O and the health state
        # machine stays a pure, clock-driven object on the gate's hot path.
        self._console_input_probe = console_input_probe
        self._reply_port_probe = reply_port_probe
        self._audit = audit
        self._send = send_event
        # Fixture IDs are immutable patch identities. Once a complete spatial
        # read has established them, a later elevation can reuse the set:
        # arrange_fixtures still resolves every ID to its current slot and
        # backs up/read-backs the write, so this removes only a redundant
        # 4-property-per-fixture discovery pass.
        self._spatial_fids: tuple[int, ...] | None = None
        self._pending_repeating_columns: _PendingRepeatingColumns | None = None
        # A song design whose requery cards went unanswered (결함 2 follow-up):
        # kept so the NEXT turn can answer "벌스는 Center → Fan Out" and resume
        # the same plan instead of restarting the interview.
        self._pending_song_requery: _SongDesignState | None = None
        # PLAN-stage editing (handoff 2026-08-15 priority 1): the LAST fully
        # composed but not-yet-approved design, kept so a later turn can
        # delete/insert/retarget cues console-free and re-request approval.
        self._pending_song_plan: _SongDesignState | None = None
        # 결함 6: role → group-number mapping inferred from console group names
        # and confirmed by the director ONCE per session. None = not yet asked;
        # [] = declined or nothing inferable (single-layer, disclosed).
        self._song_layer_mapping: list[dict[str, object]] | None = None
        self._timeline_store = timeline_store
        # Priority 3 (handoff 2026-08-15): approved console stores auto-save a
        # library version ("이름 (자동 vN)"). None (tests, bare deps) = no-op.
        self._timeline_library = timeline_library
        # Layout parameters the operator has already established this session
        # (column gap, fixture gap in metres). Persisted ACROSS turns and NOT
        # cleared after a placement, so a follow-up ("나머지도 배치해줘") reuses
        # them instead of the copilot re-asking for spacing it was already told.
        self._last_layout_spacing: tuple[float, float] | None = None
        # Rolling transcript of prior turns (user instruction + assistant reply),
        # replayed to the model so context survives across turns for EVERY
        # conversation, not just the layout special-cases. Bounded to the last
        # HISTORY_MAX_MESSAGES entries; reset only when this connection ends.
        self._history: list[UserMessage | ModelTurn] = []
        self._channel = approval_channel
        self._review_channel = review_channel
        self._question_channel = question_channel
        self._recorder = recorder
        self._turn_decisions: list[ScreenDecision] = []
        self._preview_counter = 0
        self._rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
        # REQ-DEPLOY-030 (#4): the single most-recent created look, persisted
        # ACROSS turns (unlike _turn_decisions, this is NOT reset per turn) so a
        # bare follow-up modification can anchor to the real target.
        self._last_created: LastCreated | None = None
        self._vectorworks_upload = _UploadedVectorworksExport()
        # M6c-1 Finding 1/2: a unique identity for THIS connection, scoping the
        # shared approval_channel/review_channel/gate's per-session state so a
        # sibling ChatSession's disconnect or screening never leaks in.
        self._session_key = new_session_key()
        approval_channel.bind(self._notify_approval, session_key=self._session_key)
        if review_channel is not None:
            review_channel.bind(self._notify_review, session_key=self._session_key)
        if question_channel is not None:
            question_channel.bind(self._notify_question, session_key=self._session_key)
        registry = build_toolset(
            execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
            state_port=gate.state_port,
            bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision),
            rig_paths=self._rig_paths,
            deploy_pipeline=deploy_pipeline,
            question_port=question_channel,
            vectorworks_upload=self._vectorworks_upload,
            # SPEC-COPILOT-PRESHOW-001 T-G2: reuse the gate's own audited
            # heartbeat as the pre-show OSC checks' liveness probe — no
            # second console link, no new socket. Gated on preshow_receive_port
            # being supplied (wired from server/web/app.py WebDeps ->
            # server/web/serve.py ConsoleStack.receive_port): without a real
            # bound port to report/compare, receive_port_binding has nothing
            # meaningful to check, and the whole OSC family stays the
            # pre-T-G2 skip default — never partially wired.
            preshow_liveness_port=(
                _GateLivenessPort(gate) if preshow_receive_port is not None else None
            ),
            preshow_receive_port=preshow_receive_port,
            # SPEC-COPILOT-PRESHOW-001 T-G3: the site's real osc_slot setting
            # (wired from server/web/app.py WebDeps -> server/web/serve.py
            # apply_effective_settings). None (unwired) is passed through
            # unchanged — run_preshow_checklist itself discloses the
            # unconfirmed-default fallback rather than this layer guessing.
            preshow_osc_slot=preshow_osc_slot,
        )
        # Held so a look bundle re-enters the SAME run_commands tool the model
        # uses, rather than growing a second way to reach the console.
        self._registry = registry
        self._orchestrator = Orchestrator(
            provider=provider, registry=registry, system_prefix=system_prefix
        )

    def close(self) -> None:
        """Disconnect: unbind both channels for THIS session ONLY — denies
        this session's own pending requests, never another session's."""
        self._channel.unbind(session_key=self._session_key)
        if self._review_channel is not None:
            self._review_channel.unbind(session_key=self._session_key)
        if self._question_channel is not None:
            self._question_channel.unbind(session_key=self._session_key)
        self._vectorworks_upload.clear()

    # -- event plumbing ----------------------------------------------------------

    def _notify_approval(self, request_id: str, request: ApprovalRequest) -> None:
        self._send(approval_request_event(request_id=request_id, request=request))

    def _notify_review(self, request_id: str, request: ReviewRequest) -> None:
        self._send(review_request_event(request_id=request_id, request=request))

    def _notify_question(self, request_id: str, request: QuestionRequest) -> None:
        self._send(question_request_event(request_id=request_id, request=request))

    def _on_preview(self, commands: Sequence[str]) -> None:
        if not commands:
            return
        self._preview_counter += 1
        preview = build_execution_preview(
            preview_id=f"preview-{self._preview_counter}",
            commands=commands,
        )
        self._send(execution_preview_event(preview=preview))

    def _on_decision(self, decision: ScreenDecision) -> None:
        self._turn_decisions.append(decision)
        if decision.status == "locked" and decision.proposal is not None:
            self._send(
                proposal_event(
                    commands=list(decision.proposal.commands),
                    reasons=list(decision.proposal.reasons),
                )
            )
        elif decision.status == "blocked_backup_failed":
            self._send(
                notice_event(
                    "쇼파일 백업에 실패하여 실행이 차단되었습니다 (안전 장치). "
                    "저장 공간과 콘솔 상태를 확인해 주세요."
                )
            )
        elif decision.status in ("blocked_console_offline", "blocked_responder_degraded"):
            self._send(self.status_snapshot())

    # -- public surface ------------------------------------------------------------

    # @MX:NOTE: [AUTO] the panel's pin seed (REQ-SHOWUI-004). Read-only exposure
    #   of the EXISTING cross-turn memory — the panel gets no second source of
    #   truth for "what did the chat just create", and cannot write to this one.
    @property
    def last_created(self) -> LastCreated | None:
        """The look this session most recently created, or ``None``.

        ``None`` is the seed-absent case the panel turns into an explicit error
        rather than a silent no-op (``server.web.panel.PinSeedUnavailable``,
        acceptance.md §D edge case 7).
        """
        return self._last_created

    # @MX:NOTE: [AUTO] the look layer's only route to a console (REQ-LOOKLIB-010
    #   / 019). This is a CALLER of the single execution path, not a second one:
    #   the bundle re-enters the same run_commands tool a model-issued call
    #   uses, so it inherits the execution preview, gate.screen() and the audit
    #   log without any of them being duplicated for looks.
    def run_look_bundle(self, plan: LookInstantiation) -> dict:
        """Screen and run one look instantiation bundle; return it with its report.

        An empty bundle sends nothing — that is the shape a look takes when the
        rig addressed none of its roles, and the report says why.

        BOTH capture shapes run. The per-family shape used to be refused here:
        it is built from repeated ``ClearAll`` / ``Group`` lines, and
        run_commands deduplicated every repeat, so cycles 2..N would have lost
        their clear and their re-selection and stored the previous cycle's
        programmer. That defect is fixed at its source — programmer-state
        commands are now exempt from the dedupe
        (``server.orchestrator.tools._is_programmer_state``) — so the isolated
        cycles reach the console intact and the refusal has nothing left to
        protect.
        """
        report = plan.to_dict()
        if not plan.commands:
            return {"executed": False, "report": report, "commands": []}
        execution = self._registry.dispatch(
            ToolCall(
                id=f"look-{plan.look_id}",
                name="run_commands",
                arguments={"commands": list(plan.commands)},
            )
        )
        return {
            "executed": not execution.result.is_error,
            "report": report,
            "commands": [outcome_view(o) for o in execution.command_outcomes],
        }

    def status_snapshot(self) -> dict:
        """Gate-truth status event (REQ-MVP-030/031 UI half)."""
        gate_status = self._gate.status
        health = gate_status["health"]
        console_input = self._console_input(health)
        mismatch = self._reply_port(console_input)
        return status_event(
            health=health,
            live_lock=gate_status["live_lock"],
            executions_blocked=self._gate.monitor.executions_blocked,
            console_input=console_input,
            reply_port=mismatch.observed if mismatch is not None else None,
            receive_port=mismatch.configured if mismatch is not None else None,
        )

    def _console_input(self, health: str) -> str:
        """Diagnose WHY the console is silent — never WHETHER it is (REQ-DEPLOY-018).

        Only ``console_offline`` is ambiguous: the monitor reaches it both when
        onPC is genuinely down and when onPC is up but the responder plugin —
        the only thing that ever sends — has stopped. A bind probe on the
        console's OSC input port separates the two, so the UI can name the real
        cause instead of sending the operator to inspect two healthy subsystems.

        Every other state is left unprobed: ``online`` and ``responder_degraded``
        already imply console traffic was seen, so there is nothing to
        disambiguate and no reason to pay for a socket on every heartbeat tick.
        A probe failure degrades to ``undetermined`` — a diagnosis aid must never
        be able to break the status surface it decorates.
        """
        if health != HealthMonitor.CONSOLE_OFFLINE or self._console_input_probe is None:
            return CONSOLE_INPUT_UNDETERMINED
        try:
            return self._console_input_probe()
        except Exception:
            return CONSOLE_INPUT_UNDETERMINED

    def _reply_port(self, console_input: str) -> ReplyPortMismatch | None:
        """The third ``console_offline`` cause: the console replies elsewhere.

        Gated on ``console_input == listening`` and nothing weaker. That verdict
        already means "the console's OSC input is live but nothing is reaching
        us", which is precisely the shape a reply-port drift makes — and it is
        also the only shape where a reply could exist to be found. A silent
        input means onPC itself is down, so there is nothing to discover; a
        healthy link means the configured port already works and discovery must
        not run at all.

        The probe is non-blocking by contract (see
        :class:`server.web.reply_discovery.ReplyPortDiagnostic`) because this
        method runs on the asyncio event loop. A failure degrades to "no
        mismatch": the operator then sees the responder message, which is still
        the better of the two pre-existing answers.
        """
        if console_input != CONSOLE_INPUT_LISTENING or self._reply_port_probe is None:
            return None
        try:
            return self._reply_port_probe()
        except Exception:
            return None

    def set_lock(self, active: bool) -> dict:
        """Toggle the live lock (REQ-MVP-016 UI half); emits a status event."""
        if active:
            self._gate.lock.activate()
        else:
            self._gate.lock.deactivate()
        event = self.status_snapshot()
        self._send(event)
        return event

    def _all_fixtures_elevation(self, text: str) -> InstructionResult | None:
        """Raise every fixture with a console-confirmed 3D position to 5 m.

        A partial general-layout read can still name a safe elevation target:
        fixtures omitted because they have no usable 3D coordinates are not
        placed in the layout. Console truncation and our own query ceiling are
        different: neither can establish that an omitted fixture is unplaced,
        so both remain a hard stop.
        """
        if _ALL_FIXTURES_ELEVATION.search(text) is None:
            return None
        if self._spatial_fids is not None:
            fids = list(self._spatial_fids)
            target_label = "전체 배치 장비"
        else:
            spatial = self._registry.dispatch(
                ToolCall(id="spatial-read", name="get_spatial_context", arguments={})
            )
            if spatial.result.is_error:
                return InstructionResult(
                    status="ok",
                    text=(
                        "3D 좌표를 읽지 못해 높이 변경을 시작하지 않았습니다. "
                        "콘솔 연결을 확인해 주세요."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            try:
                payload = json.loads(spatial.result.content)
                coverage = payload["coverage"]
                complete = coverage["complete"]
                fixtures = payload.get("fixtures")
                if complete is True and isinstance(fixtures, list):
                    target_label = "전체 배치 장비"
                else:
                    fixtures = payload["partial_fixtures"]
                    if payload.get("truncated") or payload.get("roundtrip_capped"):
                        raise ValueError("coordinate read is incomplete")
                    target_label = "좌표가 확인된 배치 장비"
                fids = [
                    fixture["fid"]
                    for fixture in fixtures
                    if isinstance(fixture, dict)
                    and isinstance(fixture.get("fid"), int)
                    and not isinstance(fixture.get("fid"), bool)
                ]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                return InstructionResult(
                    status="ok",
                    text=(
                        "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 높이 변경을 "
                        "시작하지 않았습니다."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
        if not fids or len(set(fids)) != len(fids):
            return InstructionResult(
                status="ok",
                text=(
                    "확인된 3D 좌표에서 유효한 FID 목록을 만들지 못해 "
                    "높이 변경을 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        if self._spatial_fids is None and complete is True:
            self._spatial_fids = tuple(fids)
        arranged = self._registry.dispatch(
            ToolCall(
                id="spatial-elevation",
                name="arrange_fixtures",
                arguments={"preset": "elevation", "fids": fids, "height": 5.0},
            )
        )
        return InstructionResult(
            status="ok",
            text=(
                f"{target_label} {len(fids)}대의 x/y는 유지하고, 바닥 기준 z=5m로 "
                "변경을 요청했습니다. 승인 또는 라이브 잠금 상태에 따른 결과를 아래 "
                "명령 상태에서 확인해 주세요."
            ),
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    @staticmethod
    def _pointing_refusal(text: str) -> InstructionResult:
        """A no-op turn result carrying WHY no aim command was sent."""
        return InstructionResult(
            status="ok",
            text=text,
            command_outcomes=(),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _read_pointing_coordinates(
        self, call_id: str
    ) -> list[tuple[int, tuple[float, float, float]]] | InstructionResult:
        """Every coordinate-confirmed ``(fid, (x, y, z))`` — or the refusal.

        Shared by the FOCUS (point-at) and LOOK (fan/ring) handlers: both
        compute per-fixture pan/tilt from the console's own patch read, and
        both must refuse on a partial read rather than aim half a rig.
        """
        spatial = self._registry.dispatch(
            ToolCall(id=call_id, name="get_spatial_context", arguments={})
        )
        if spatial.result.is_error:
            return self._pointing_refusal(
                "3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다. "
                "콘솔 연결을 확인해 주세요."
            )
        try:
            payload = json.loads(spatial.result.content)
            records = payload["fixtures"] if "fixtures" in payload else payload["partial_fixtures"]
            if "fixtures" not in payload and (
                payload.get("truncated") or payload.get("roundtrip_capped")
            ):
                raise ValueError("coordinate read is incomplete")
            return [
                (record["fid"], (float(record["x"]), float(record["y"]), float(record["z"])))
                for record in records
                if isinstance(record, dict)
                and isinstance(record.get("fid"), int)
                and not isinstance(record.get("fid"), bool)
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._pointing_refusal(
                "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 조명 방향 "
                "변경을 시작하지 않았습니다."
            )

    def _point_fixtures_at_target(self, text: str) -> InstructionResult | None:
        """Aim every coordinate-confirmed fixture's beam at one stage point.

        Runs on the MEASURED pan/tilt model (``server/spatial/pointing.py``):
        positions come off the console's own patch read, the pan/tilt degrees
        are computed per fixture, and the writes ride ``run_commands`` through
        the ordinary approval gate. A fixture standing ON the target or beyond
        the tilt ceiling is skipped and reported, never clamped.
        """
        if _POINT_AT_TARGET.search(text) is None:
            return None
        triple = _POINT_TARGET_TRIPLE.search(text)
        if triple is not None:
            target = PointingTarget(
                float(triple.group("x")), float(triple.group("y")), float(triple.group("z"))
            )
        elif _POINT_TARGET_CENTRE.search(text) is not None:
            target = PointingTarget(0.0, 0.0, 0.0)
        else:
            return None  # aiming verb without a target — let the model ask
        fixtures = self._read_pointing_coordinates("pointing-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        pointable: list[tuple[int, tuple[float, float, float]]] = []
        skipped: list[int] = []
        for fid, position in fixtures:
            try:
                aim_pan_tilt(position, target.as_tuple())
            except SpatialPointingError:
                skipped.append(fid)
            else:
                pointable.append((fid, position))
        if not pointable:
            return InstructionResult(
                status="ok",
                text="목표 지점을 향할 수 있는 장비가 없어 조명 방향 변경을 시작하지 않았습니다.",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        commands = pointing_commands(pointable, target, dimmer=dimmer)
        executed = self._registry.dispatch(
            ToolCall(
                id="pointing-write",
                name="run_commands",
                arguments={"commands": list(commands)},
            )
        )
        skipped_note = (
            f" 목표 지점과 겹치거나 틸트 한계를 넘는 {len(skipped)}대(FID "
            f"{', '.join(str(fid) for fid in skipped)})는 제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}좌표가 확인된 장비 {len(pointable)}대의 헤드가 "
                f"({target.x:g}, {target.y:g}, {target.z:g}) 지점을 향하도록 "
                f"Pan/Tilt를 요청했습니다.{skipped_note} 승인 또는 라이브 잠금 "
                "상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _look_pan_tilt(self, text: str) -> InstructionResult | None:
        """Aim the rig into a DESIGN look — fan (out/in/cross) or ring (in/out).

        The LOOK family of docs/proposals/pan-tilt-position-preset-strategy.md:
        values are a function of the fixtures' RELATION (chain order, or the
        radial around the rig centroid), not of one target point. Optionally
        stores the programmer as a Position preset when the instruction names
        an explicit preset number (never a guessed slot).
        """
        ring = _LOOK_RING.search(text)
        fan = _LOOK_FAN.search(text)
        if ring is None and fan is None:
            return None
        fixtures = self._read_pointing_coordinates("look-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 룩 포지션을 시작하지 않았습니다."
            )
        skipped: list[int] = []
        if ring is not None:
            mode = "in" if ring.group("dir") == "안쪽" else "out"
            cx = sum(position[0] for _fid, position in fixtures) / len(fixtures)
            cy = sum(position[1] for _fid, position in fixtures) / len(fixtures)
            aims: list[tuple[int, float, float]] = []
            for fid, position in fixtures:
                try:
                    aims.extend(radial_pan_tilt([(fid, position)], center=(cx, cy), mode=mode))
                except SpatialPointingError:
                    skipped.append(fid)
            look_label = f"RING {mode.upper()}"
            look_korean = "링 " + ("안쪽" if mode == "in" else "바깥쪽") + " 조준"
        else:
            if _LOOK_FAN_CROSS.search(text) is not None:
                mode = "cross"
            elif _LOOK_FAN_IN.search(text) is not None:
                mode = "in"
            else:
                mode = "out"
            spread_match = _LOOK_SPREAD.search(_LOOK_TILT_SPREAD.sub("", text))
            spread = float(spread_match.group("value")) if spread_match else 30.0
            tilt_match = _LOOK_TILT_SPREAD.search(text)
            if tilt_match is not None:
                tilt_spread = float(tilt_match.group("value"))
            elif _LOOK_TILT_FAN.search(text) is not None:
                tilt_spread = 15.0
            else:
                tilt_spread = 0.0
            try:
                aims = list(
                    fan_pan_tilt(
                        list(fan_chain(fixtures)),
                        spread=spread,
                        mode=mode,
                        tilt_spread=tilt_spread,
                    )
                )
            except SpatialPointingError as error:
                return self._pointing_refusal(f"부채살 포지션을 만들 수 없습니다: {error}")
            look_label = f"FAN {mode.upper()}"
            tilt_note = f", 틸트 ±{tilt_spread:g}도" if tilt_spread else ""
            look_korean = {
                "out": f"부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
                "in": f"모으는 부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
                "cross": f"교차 부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
            }[mode]
        if not aims:
            return self._pointing_refusal(
                "룩 포지션을 계산할 수 있는 장비가 없어 시작하지 않았습니다."
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        commands = list(aimed_commands(aims, dimmer=dimmer))
        preset_match = _LOOK_PRESET_STORE.search(text)
        preset_note = ""
        if preset_match is not None:
            preset_no = int(preset_match.group("no") or preset_match.group("no2"))
            try:
                commands.extend(position_preset_store_commands(preset_no, look_label))
            except SpatialPointingError as error:
                return self._pointing_refusal(f"프리셋 저장 명령을 만들 수 없습니다: {error}")
            preset_note = (
                f" 이어서 Position 프리셋 2.{preset_no}에 '{look_label}'로 저장을 요청했습니다."
            )
        executed = self._registry.dispatch(
            ToolCall(id="look-write", name="run_commands", arguments={"commands": commands})
        )
        skipped_note = (
            f" 중심과 겹치거나 틸트 한계를 넘는 {len(skipped)}대(FID "
            f"{', '.join(str(fid) for fid in skipped)})는 제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}좌표가 확인된 장비 {len(aims)}대를 {look_korean} "
                f"포지션으로 요청했습니다.{skipped_note}{preset_note} 승인 또는 "
                "라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_mood_suggestion(self, text: str) -> InstructionResult | None:
        """연출 의도(무드) → 포지션 추천 카드 → 선택된 룩만 적용.

        docs/proposals의 무드→포지션 매핑(`server/spatial/position_moods.py`)
        기반. 실행이 아니라 제안이 기본이다: 키워드가 맞아도 카드로 확인을
        받고, 무응답·거절이면 아무것도 보내지 않는다 — 키워드 하나로 단정해
        실행하던 반사적 처리의 재도입을 막는 경계.
        """
        if _POSITION_INTENT.search(text) is None:
            return None
        suggestion = match_position_mood(text)
        if suggestion is None:
            return None
        fixtures = self._read_pointing_coordinates("mood-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 제안을 시작하지 않았습니다."
            )
        entry = suggestion.entry
        options = [QuestionOption(label=entry.label, description=entry.reason)]
        by_label = {
            label: (aims, skipped) for label, aims, skipped in basic_position_presets(fixtures)
        }
        for alt in entry.alternatives:
            options.append(QuestionOption(label=alt))
        options.append(QuestionOption(label="적용 안 함"))
        matched = ", ".join(suggestion.matched)
        answer = self._ask_one(
            f"'{matched}' 느낌에는 {entry.korean}({entry.label}) 포지션을 추천합니다. 적용할까요?",
            options=tuple(options),
            why=entry.reason,
        )
        if answer is None or "안 함" in answer or "안함" in answer:
            return self._pointing_refusal(
                f"포지션을 적용하지 않았습니다. (추천이었던 룩: {entry.label})"
            )
        chosen = next(
            (label for label in by_label if label.casefold() == answer.strip().casefold()),
            None,
        )
        if chosen is None:
            return self._pointing_refusal(
                f"'{answer}'는 기본 포지션 이름이 아니어서 적용하지 않았습니다. "
                f"(가능: {', '.join(by_label)})"
            )
        aims, skipped = by_label[chosen]
        if not aims:
            return self._pointing_refusal(
                f"{chosen} 포지션을 계산할 수 있는 장비가 없어 적용하지 않았습니다."
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        executed = self._registry.dispatch(
            ToolCall(
                id="mood-write",
                name="run_commands",
                arguments={"commands": list(aimed_commands(aims, dimmer=dimmer))},
            )
        )
        skipped_note = (
            f" 조준 불가 {len(skipped)}대(FID {', '.join(str(fid) for fid in skipped)})는 "
            "제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}'{matched}' 의도에 맞춰 {chosen} 포지션을 장비 "
                f"{len(aims)}대에 요청했습니다.{skipped_note} 승인 또는 라이브 잠금 "
                "상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _basic_position_presets(self, text: str) -> InstructionResult | None:
        """Build the ten canonical positions for THIS rig and store them.

        Preset 1 of the run is ALWAYS 'Home'; the rest follow
        ``BASIC_POSITION_SEQUENCE`` from most basic to most varied. The first
        preset number comes from the instruction ("N번부터") or from ONE
        question card — never from a guessed free slot: ``Store Preset``
        silently overwrites, so the number is the operator's call.
        Each look is applied, stored, labelled and cleared as its own bundle,
        so one refused look never voids the other nine.
        """
        if _BASIC_POSITIONS_REQUEST.search(text) is None:
            return None
        fixtures = self._read_pointing_coordinates("basic-presets-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 기본 포지션 프리셋을 시작하지 않았습니다."
            )
        start_match = _BASIC_POSITIONS_START.search(text)
        if start_match is not None:
            start_no = int(start_match.group("no"))
        else:
            count = len(BASIC_POSITION_SEQUENCE)
            answer = self._ask_one(
                f"기본 포지션 {count}개를 Position 프리셋 몇 번부터 저장할까요? "
                f"(예: 1 → Preset 2.1~2.{count}) 이미 있는 번호는 덮어씁니다.",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "Store Preset은 기존 슬롯을 경고 없이 덮어쓰므로 "
                    "시작 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                start_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시작 프리셋 번호를 받지 못해 저장을 시작하지 않았습니다. "
                    "예: '기본 포지션 10개를 프리셋 21번부터 저장해줘'"
                )
        if start_no <= 0:
            return self._pointing_refusal("시작 프리셋 번호는 1 이상이어야 합니다.")
        try:
            looks = basic_position_presets(fixtures)
        except SpatialPointingError as error:
            return self._pointing_refusal(f"기본 포지션을 계산할 수 없습니다: {error}")
        outcomes: list[CommandOutcome] = []
        stored: list[str] = []
        skipped_notes: list[str] = []
        for offset, (label, aims, skipped) in enumerate(looks):
            preset_no = start_no + offset
            if not aims:
                skipped_notes.append(f"{label}(2.{preset_no}): 조준 가능한 장비 없음 — 건너뜀")
                continue
            commands = [
                *aimed_commands(aims),
                *position_preset_store_commands(preset_no, label),
                "ClearAll",
            ]
            executed = self._registry.dispatch(
                ToolCall(
                    id=f"basic-preset-{preset_no}",
                    name="run_commands",
                    arguments={"commands": commands},
                )
            )
            outcomes.extend(executed.command_outcomes)
            stored.append(f"2.{preset_no} '{label}'")
            if skipped:
                skipped_notes.append(f"{label}: FID {', '.join(str(fid) for fid in skipped)} 제외")
        if not stored:
            return self._pointing_refusal(
                "어느 포지션도 계산되지 않아 프리셋을 저장하지 않았습니다."
            )
        notes = f" 참고: {'; '.join(skipped_notes)}." if skipped_notes else ""
        return InstructionResult(
            status="ok",
            text=(
                f"리그 배치에서 유도한 기본 포지션 {len(stored)}개를 "
                f"Position 프리셋에 저장 요청했습니다: {', '.join(stored)}.{notes} "
                "각 프리셋은 적용→저장→ClearAll 순서로 처리했으며, 승인 또는 라이브 "
                "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_cue_store(self, text: str) -> InstructionResult | None:
        """Store a Position preset as a cue with an optional position fade (T1).

        The bundle is ``recall → Store Sequence S Cue C 'Pos 2.N' CueFade F →
        ClearAll``: the cue keeps a preset REFERENCE, and the fade is what
        makes the beams glide instead of snap. The sequence number comes from
        the instruction or ONE question card — ``Store`` on an occupied cue
        changes a show object, so the number is the operator's call. No
        ``/Merge``/``/Overwrite`` ever (phaser-flattening + blacklist).
        """
        if _CUE_STORE_INTENT.search(text) is None:
            return None
        preset_ref = _CUE_PRESET_REF.search(text)
        if preset_ref is None:
            return None
        preset_no = int(preset_ref.group("no"))
        fixtures = self._read_pointing_coordinates("cue-store-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 큐 저장을 시작하지 않았습니다."
            )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                f"Position 프리셋 2.{preset_no}을(를) 어느 시퀀스에 큐로 저장할까요? "
                "(예: 101) 이미 큐가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="101"),
                    QuestionOption(label="110"),
                    QuestionOption(label="200"),
                ),
                why=(
                    "Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 "
                    "시퀀스 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 큐 저장을 시작하지 않았습니다. "
                    "예: '프리셋 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초'"
                )
        cue_match = _CUE_NO.search(text)
        cue_no = float(cue_match.group("no")) if cue_match is not None else 1.0
        fade_match = _CUE_FADE.search(text)
        fade_seconds = (
            float(fade_match.group("sec") or fade_match.group("sec2"))
            if fade_match is not None
            else None
        )
        fids = [fid for fid, _position in fixtures]
        try:
            commands = [
                preset_recall_command(fids, preset_no),
                *position_cue_store_commands(
                    sequence_no,
                    cue_no,
                    fade_seconds=fade_seconds,
                    name=f"Pos 2.{preset_no}",
                ),
                "ClearAll",
            ]
        except SpatialPointingError as error:
            return self._pointing_refusal(f"큐 저장 명령을 만들 수 없습니다: {error}")
        executed = self._registry.dispatch(
            ToolCall(
                id="cue-store-write",
                name="run_commands",
                arguments={"commands": commands},
            )
        )
        fade_note = f" 페이드 {fade_seconds:g}초로" if fade_seconds is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"Position 프리셋 2.{preset_no} 리콜 상태를 시퀀스 {sequence_no} "
                f"큐 {cue_match.group('no') if cue_match else '1'}에{fade_note} 저장 "
                "요청했습니다 (프리셋 참조 유지, 저장 후 ClearAll). 승인 또는 라이브 "
                "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_cue_sheet(self, text: str) -> InstructionResult | None:
        """Song-structure position cue sheet draft (T3) — mood → preset cues.

        Sections ("이름 시각 무드", comma-separated) resolve through the mood
        table to the stored basic Position presets; blackout sections store
        dimmer 0 and the MIB rule inserts dark pre-move cues (measured, M2).
        The sequence number AND the preset base come from the instruction or
        one question card each — recalling a guessed preset slot would aim
        the show at whatever lives there. Each cue is its own bundle, so one
        refused cue never voids the rest of the sheet.
        """
        if _POSITION_SHEET_REQUEST.search(text) is None:
            return None
        sections: list[PositionSheetSection] = []
        for part in text.split(","):
            matched = _SHEET_SECTION.search(part.strip())
            if matched is None:
                continue
            start_token = matched.group("start").replace("초", "").strip()
            try:
                start_ms = normalise_start_ms(start_token)
            except Exception:
                continue
            sections.append(
                PositionSheetSection(
                    name=matched.group("name"),
                    start_ms=start_ms,
                    mood=matched.group("mood").strip(),
                )
            )
        if not sections:
            return self._pointing_refusal(
                "곡 구간을 읽지 못해 포지션 큐 시트를 만들지 않았습니다. 형식: "
                "'포지션 큐 시트, 시퀀스 110, 프리셋 21번부터: 인트로 0:00 잔잔하게, "
                "후렴 0:40 클럽 드롭'"
            )
        fixtures = self._read_pointing_coordinates("sheet-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 큐 시트를 시작하지 않았습니다."
            )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                "포지션 큐 시트를 어느 시퀀스에 저장할까요? (예: 110) "
                "이미 큐가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="110"),
                    QuestionOption(label="120"),
                    QuestionOption(label="200"),
                ),
                why="Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 운영자 결정입니다.",
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 큐 시트를 만들지 않았습니다."
                )
        preset_match = _SHEET_PRESET_START.search(text)
        if preset_match is not None:
            preset_start = int(preset_match.group("no"))
        else:
            answer = self._ask_one(
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                "저장돼 있나요? (예: 21 → 2.21~2.30)",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "큐는 프리셋 참조로 빌드됩니다 — 잘못된 슬롯을 리콜하면 "
                    "그 자리에 있는 다른 포지션이 무대에 나갑니다."
                ),
            )
            try:
                preset_start = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "프리셋 시작 번호를 받지 못해 큐 시트를 만들지 않았습니다."
                )
        fade_match = _CUE_FADE.search(text)
        fade_seconds = (
            float(fade_match.group("sec") or fade_match.group("sec2"))
            if fade_match is not None
            else 3.0
        )
        fids = [fid for fid, _position in fixtures]
        try:
            sheet = build_position_cue_sheet(
                sections,
                sequence_no=sequence_no,
                preset_start=preset_start,
                fids=fids,
                fade_seconds=fade_seconds,
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"포지션 큐 시트를 만들 수 없습니다: {error}")
        outcomes: list[CommandOutcome] = []
        for plan, bundle in zip(sheet.plans, sheet.bundles, strict=True):
            executed = self._registry.dispatch(
                ToolCall(
                    id=f"song-sheet-cue-{plan.cue_no:g}",
                    name="run_commands",
                    arguments={"commands": list(bundle)},
                )
            )
            outcomes.extend(executed.command_outcomes)
        lines: list[str] = []
        for res in sheet.resolutions:
            minute, second = divmod(res.section.start_ms // 1000, 60)
            stamp = f"{minute}:{second:02d}"
            if res.blackout:
                lines.append(f"큐 {res.cue_no} {res.section.name}({stamp}): 암전")
            elif res.skipped_reason is not None:
                lines.append(
                    f"큐 {res.cue_no} {res.section.name}({stamp}): 건너뜀 — {res.skipped_reason}"
                )
            else:
                varied = f", {res.varied_from} 대안" if res.varied_from else ""
                lines.append(
                    f"큐 {res.cue_no} {res.section.name}({stamp}): {res.look_label} "
                    f"(Preset 2.{res.preset_no}{varied})"
                )
        mib_notes = [
            f"큐 {plan.cue_no:g} '{plan.name}' (다크 선이동)"
            for plan in sheet.plans
            if plan.name.endswith(" Move")
        ]
        mib_note = f" MIB 삽입: {', '.join(mib_notes)}." if mib_notes else ""
        return InstructionResult(
            status="ok",
            text=(
                f"시퀀스 {sequence_no}에 포지션 큐 시트 {len(sheet.plans)}큐를 저장 "
                f"요청했습니다 (페이드 {fade_seconds:g}초, 전 큐 프리셋 참조). "
                f"{' / '.join(lines)}.{mib_note} 승인 또는 라이브 잠금 상태에 따른 "
                "결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _song_timing_choice(self, text: str) -> TimingPlan | None:
        mode = _timing_mode_from_text(text)
        if mode is None:
            answer = self._ask_one(
                "이 곡 큐의 타이밍 방식을 선택해 주세요.",
                options=(
                    QuestionOption(label="타임코드"),
                    QuestionOption(label="TrigTime"),
                    QuestionOption(label="수동 Go"),
                ),
                why=(
                    "Cue 저장 전에 수동 Go, TrigTime, Timecode 중 하나가 "
                    "명시적으로 확정돼야 합니다."
                ),
            )
            if answer is None:
                return None
            mode = _timing_mode_from_text(answer) or {
                "타임코드": "timecode",
                "TrigTime": "trig_time",
                "수동 Go": "manual_go",
            }.get(answer.strip())
        if mode == "manual_go":
            return TimingPlan.manual_go(source="director")
        if mode == "trig_time":
            return TimingPlan.trig_time(source="director")
        if mode != "timecode":
            return None
        timecode_number = _timecode_number_from_text(text)
        if timecode_number is None:
            answer = self._ask_one(
                "Timecode 몇 번에 연결할까요?",
                options=(
                    QuestionOption(label="7"),
                    QuestionOption(label="77"),
                    QuestionOption(label="101"),
                ),
                why="Timecode 저장은 기존 트랙을 덮을 수 있어 번호가 명시적으로 필요합니다.",
            )
            try:
                timecode_number = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return None
        return TimingPlan.timecode(timecode_number, source="director")

    def _reviewed_song_commands(
        self,
        composition: SongCueCompositionResult,
        *,
        sequence_no: int,
        preset_start: int,
        fids: Sequence[int],
        timing: TimingPlan,
    ) -> tuple[str, ...]:
        bundle = composition.bundle
        if bundle is None:
            return ()
        commands: list[str] = ["ChangeDestination Root"]
        for cue in bundle.cues:
            preset_no = None
            if cue.position.stored is not None:
                try:
                    preset_no = preset_start + BASIC_POSITION_SEQUENCE.index(cue.position.stored)
                except ValueError as error:
                    raise SpatialPointingError(
                        f"unknown reviewed position {cue.position.stored!r}"
                    ) from error
            dimmer = cue.dimmer.key_pct
            if preset_no is None and dimmer is None:
                continue
            plan = PositionCuePlan(
                cue_no=cue.cue_number,
                name=_safe_song_cue_name(cue.cue_name, cue.cue_number),
                preset_no=preset_no,
                dimmer=dimmer,
                fade_seconds=cue.fade_seconds,
                premove=cue.kind == "mib_premove",
            )
            commands.extend(position_cue_bundle(sequence_no, plan, fids))
            if plan.premove:
                commands.append(premove_follow_command(sequence_no, plan))
        commands.extend(self._reviewed_song_timing_commands(bundle, sequence_no, timing))
        return tuple(commands)

    def _reviewed_song_timing_commands(
        self,
        bundle,
        sequence_no: int,
        timing: TimingPlan,
    ) -> tuple[str, ...]:
        if timing.mode == "manual_go":
            return ()
        sections: list[SongCueSectionBundle] = []
        for cue in bundle.section_cues:
            if cue.timing.start_ms is None:
                continue
            section = SongCueSection(
                name=cue.cue_name,
                start_ms=cue.timing.start_ms,
                index=cue.section_index - 1,
                dynamics=(cue.d_level,),
                requires_explicit_dynamics=False,
            )
            selection = SongCueLookSelection(section=section, requested_dynamics=(cue.d_level,))
            sections.append(
                SongCueSectionBundle(
                    section=section,
                    cue_number=int(cue.cue_number),
                    cue_name=_safe_song_cue_name(cue.cue_name, cue.cue_number),
                    selection=selection,
                    commands=("reviewed",),
                )
            )
        timing_bundle = TimingSongCueBundle(
            song_title=bundle.song_title,
            sequence_number=sequence_no,
            sequence_name=bundle.sequence_name or f"Sequence {sequence_no}",
            commands=("reviewed",),
            sections=tuple(sections),
        )
        if timing.mode == "trig_time":
            return build_songcue_timing(
                timing_bundle,
                timecode_number=1,
                axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=True),
            ).commands
        if timing.timecode_number is None:
            return ()
        return build_songcue_timing(
            timing_bundle,
            timecode_number=timing.timecode_number,
        ).commands

    def _song_readback_requests(
        self,
        *,
        sequence_no: int,
        timing: TimingPlan,
        timed_cues: Sequence[_SongTimedCueExpectation],
    ) -> _SongReadbackResult:
        sequence_path = f"{self._rig_paths['sequences']}/{sequence_no}"
        paths = [sequence_path]
        if timing.timecode_number is not None:
            timecode_path = self._rig_paths.get("timecodes", TIMECODE_POOL_PATH)
            paths.append(f"{timecode_path}/{timing.timecode_number}")
        payloads: dict[str, object] = {}
        for index, path in enumerate(paths, start=1):
            execution = self._registry.dispatch(
                ToolCall(
                    id=f"song-design-readback-{index}",
                    name="query_state",
                    arguments={"path": path},
                )
            )
            if execution.result.is_error:
                return _SongReadbackResult(
                    paths=tuple(paths),
                    failure=f"{path} query_state 실패: {execution.result.content}",
                )
            try:
                payloads[path] = json.loads(execution.result.content)
            except json.JSONDecodeError as error:
                return _SongReadbackResult(
                    paths=tuple(paths),
                    failure=f"{path} query_state JSON 해석 실패: {error}",
                )
        sequence_failure = _validate_song_sequence_readback(payloads.get(sequence_path), timed_cues)
        if sequence_failure is not None:
            return _SongReadbackResult(paths=tuple(paths), failure=sequence_failure)
        if timing.timecode_number is not None:
            timecode_failure = _validate_song_timecode_readback(
                payloads.get(paths[-1]),
                timing.timecode_number,
            )
            if timecode_failure is not None:
                return _SongReadbackResult(paths=tuple(paths), failure=timecode_failure)
        return _SongReadbackResult(paths=tuple(paths))

    def _song_design_interview(self, text: str) -> InstructionResult | None:
        """M2 R1c/R4: the 5-card director interview → standard profile+rig sheet.

        Narrowly gated on the "디자인 큐 시트"/"디자인 인터뷰"/"연출 인터뷰"
        vocabulary (``_SONG_DESIGN_REQUEST``) so the existing "포지션 큐 시트"
        request (T3, ``_position_cue_sheet``) is untouched — the two paths
        never both fire on the same instruction. Sections/sequence/preset
        parsing reuses the same ask-or-parse idiom as ``_position_cue_sheet``;
        the five interview cards ride the same ``_ask_one`` blocking channel
        every other handler in this file already uses, one card at a time
        (DI2). Only once all five steps carry an answer — confirmed via an
        option/free text, pre-specified from the instruction, or auto-drafted
        unconfirmed (DI4, never a block) — does this call the standard
        profile+rig ``build_position_cue_sheet`` path (R4), carrying Q1/Q2's
        confirmed concept/palette via ``interview.working_profile`` and every
        step's audit entry (DI6) into the response text.
        """
        if _SONG_DESIGN_REQUEST.search(text) is None and not _is_natural_song_brief(text):
            return None
        sections: list[PositionSheetSection] = []
        for part in text.split(","):
            stripped = part.strip()
            matched = _SHEET_SECTION.search(stripped)
            if matched is not None:
                start_token = matched.group("start").replace("초", "").strip()
                try:
                    start_ms = normalise_start_ms(start_token)
                except Exception:
                    continue
                sections.append(
                    PositionSheetSection(
                        name=matched.group("name"),
                        start_ms=start_ms,
                        mood=matched.group("mood").strip(),
                    )
                )
                continue
            # 2-token fallback (no mood word) — the label doubles as both
            # name and mood so the downstream mood lookup
            # (server.spatial.position_moods.match_position_mood) still runs
            # unmodified; a section whose label matches no mood keyword is
            # skipped later (established behavior), never an error here.
            two_token = _DESIGN_SHEET_SECTION_TIME_FIRST.search(
                stripped
            ) or _DESIGN_SHEET_SECTION_NAME_FIRST.search(stripped)
            if two_token is None:
                continue
            start_token = two_token.group("start").replace("초", "").strip()
            try:
                start_ms = normalise_start_ms(start_token)
            except Exception:
                continue
            label = two_token.group("name").strip()
            sections.append(PositionSheetSection(name=label, start_ms=start_ms, mood=label))
        # The compact cue-sheet grammar above is preferred.  When it found no
        # sections, accept explicit time-first natural-language brief lines
        # without broadening any other request router.
        if not sections:
            for matched in _DESIGN_SHEET_SECTION_NATURAL_TIME_FIRST.finditer(text):
                start_token = matched.group("start").replace("초", "").strip()
                try:
                    start_ms = normalise_start_ms(start_token)
                except Exception:
                    continue
                sections.append(
                    PositionSheetSection(
                        name=matched.group("name").strip(),
                        start_ms=start_ms,
                        mood=matched.group("mood").strip(),
                    )
                )
        if not sections:
            return self._pointing_refusal(
                "곡 구간을 읽지 못해 연출 인터뷰를 시작하지 않았습니다. 형식: "
                "'디자인 큐 시트, 시퀀스 110, 프리셋 21번부터: 인트로 0:00 잔잔하게, "
                "후렴 0:40 클럽 드롭'"
            )
        fixtures = self._read_pointing_coordinates("song-design-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 연출 인터뷰를 시작하지 않았습니다."
            )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                "디자인 큐 시트를 어느 시퀀스에 저장할까요? (예: 110) "
                "이미 큐가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="110"),
                    QuestionOption(label="120"),
                    QuestionOption(label="200"),
                ),
                why="Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 운영자 결정입니다.",
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 연출 인터뷰를 시작하지 않았습니다."
                )
        preset_match = _SHEET_PRESET_START.search(text)
        if preset_match is not None:
            preset_start = int(preset_match.group("no"))
        else:
            answer = self._ask_one(
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                "저장돼 있나요? (예: 21 → 2.21~2.30)",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "큐는 프리셋 참조로 빌드됩니다 — 잘못된 슬롯을 리콜하면 "
                    "그 자리에 있는 다른 포지션이 무대에 나갑니다."
                ),
            )
            try:
                preset_start = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "프리셋 시작 번호를 받지 못해 연출 인터뷰를 시작하지 않았습니다."
                )
        timing = self._song_timing_choice(text)
        if timing is None:
            return InstructionResult(
                status="ok",
                text=(
                    "타이밍 모드가 확정되지 않아 큐를 쓰지 않았습니다. "
                    "수동 Go, TrigTime, Timecode 중 하나를 선택해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        bpm_match = _SONG_BPM.search(text)
        genre_match = _SONG_GENRE.search(text)
        profile = MusicProfile(
            bpm=float(bpm_match.group("bpm")) if bpm_match is not None else None,
            genre=genre_match.group("genre") if genre_match is not None else None,
        )
        # RG5: no console patch/group query established for this path — the
        # rig degrades to single-layer (an explicit, disclosed note per RG1),
        # geometry is the only axis built from the already-read fixture
        # coordinates above (established path, never a new console query).
        coords = [
            {"fid": fid, "x": position[0], "y": position[1], "z": position[2]}
            for fid, position in fixtures
        ]
        rig = build_rig_profile(patch=[], groups={}, coords=coords)
        pre_specified: dict[str, str] = {}
        concept_match = _SONG_CONCEPT_HINT.search(text)
        if concept_match is not None:
            pre_specified[Q1_CONCEPT] = concept_match.group("concept").strip()
        palette_match = _SONG_PALETTE_HINT.search(text)
        if palette_match is not None:
            pre_specified[Q2_PALETTE] = palette_match.group("palette").strip()
        self._pending_song_requery = None  # a fresh design supersedes a stale one
        self._pending_song_plan = None
        interview = DirectorInterview(profile, rig, pre_specified=pre_specified)
        failure = self._song_run_interview(interview)
        if failure is not None:
            return failure
        records = interview.audit_trail()
        # 결함 5: Q1 concept colors vs Q2 palette — surface the conflict as a
        # director card instead of silently repeating the Q2 palette.
        plan_warnings: list[str] = []
        palette_mode = "palette"
        concept_colors = _extract_color_words(_record_value(records, Q1_CONCEPT, ""))
        palette_value = interview.working_profile.palette
        palette_words = _extract_color_words(palette_value)
        if (
            concept_colors
            and palette_words
            and not (
                {color.casefold() for color in concept_colors}
                & {color.casefold() for color in palette_words}
            )
        ):
            conflict_answer = self._ask_one(
                "색감 결정이 충돌합니다.\n"
                f"전체 컨셉: {' / '.join(concept_colors)}\n"
                f"팔레트: {' / '.join(_palette_colors(palette_value))}\n"
                "어느 방향으로 설계할까요?",
                options=(
                    QuestionOption(label="팔레트 중심"),
                    QuestionOption(label="컨셉 색 중심"),
                    QuestionOption(label="구간 분배 (조용한 구간 팔레트, 후렴 컨셉 색)"),
                ),
                why="결정 전에는 전역 팔레트를 조용히 덮어쓰지 않습니다.",
            )
            if conflict_answer and ("분배" in conflict_answer or "혼합" in conflict_answer):
                palette_mode = "mixed"
            elif conflict_answer and "컨셉" in conflict_answer:
                palette_mode = "concept"
            elif conflict_answer is None:
                plan_warnings.append("색감 충돌 미해결 — 감독 결정 전까지 Q2 팔레트를 유지합니다.")
        # 결함 6: role → group-number layer mapping, read from console group
        # names and confirmed once per session; single-layer stays disclosed.
        layer_mapping = self._confirm_song_layer_mapping()
        if not layer_mapping:
            plan_warnings.append(_SINGLE_LAYER_WARNING)
        state = _SongDesignState(
            sections=list(sections),
            interview=interview,
            records=records,
            rig=rig,
            fids=[fid for fid, _position in fixtures],
            timing=timing,
            sequence_no=sequence_no,
            preset_start=preset_start,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            plan_warnings=plan_warnings,
            layer_mapping=layer_mapping,
            requery_overrides={},
        )
        plan, composition = self._song_compose(state)
        self._song_send_timeline(state, plan, composition)
        # 1단계 (결함 2): EVERY requery requirement gets its own card; answers
        # merge back into the SAME plan (never a new natural-language turn),
        # the whole song recomposes, and the timeline event is re-sent. No
        # console write can happen while any requirement is open.
        plan, composition, failure = self._song_requery_rounds(state, plan, composition)
        if failure is not None:
            return failure
        return self._song_finalize(state, plan, composition)

    def _song_run_interview(self, interview: DirectorInterview) -> InstructionResult | None:
        """Run the 5-card loop until complete — also reused for DI5 partial
        re-interviews after ``restart_from``. Returns the DI3 refusal when a
        card's answer stays unparseable three times, else ``None``."""
        while not interview.is_complete():
            card = interview.build_current_card()
            options = tuple(
                QuestionOption(label=option.label, description=option.description)
                for option in card.options
            )
            attempts = 0
            while True:
                raw_answer = self._ask_one(card.prompt, options=options, why=card.why)
                restart_match = _SONG_RESTART.search(raw_answer) if raw_answer else None
                if restart_match is not None:
                    interview.restart_from(STEP_ORDER[int(restart_match.group("no")) - 1])
                    break
                result = interview.submit_answer(raw_answer)
                if isinstance(result, UnresolvedAnswer):
                    # DI3: no guess on an unparseable free-text answer — the
                    # SAME card is re-presented, capped like every other
                    # bounded retry in this codebase (3 attempts) so a live
                    # UI that keeps sending garbage cannot spin forever.
                    attempts += 1
                    if attempts >= 3:
                        return InstructionResult(
                            status="ok",
                            text=(
                                "연출 답변을 해석하지 못해 큐를 쓰지 않았습니다. "
                                f"재질의 카드: {card.prompt}"
                            ),
                            command_outcomes=(),
                            retries_used=0,
                            model_calls=0,
                            duration_seconds=0.0,
                        )
                    continue
                break
        return None

    def _confirm_song_layer_mapping(self) -> list[dict[str, object]]:
        """결함 6: infer role → group-number from console group NAMES (exact
        alias match, RG5 — membership is unreadable so fids are never
        claimed), then confirm ONCE per session with the director. Declined
        or nothing inferable → single-layer, disclosed by the caller."""
        if self._song_layer_mapping is not None:
            return self._song_layer_mapping
        mapping: list[dict[str, object]] = []
        execution = self._registry.dispatch(
            ToolCall(
                id="song-layer-groups-read",
                name="query_state",
                arguments={"path": "DataPool/Groups"},
            )
        )
        if not execution.result.is_error:
            try:
                payload = json.loads(execution.result.content)
            except (TypeError, ValueError):
                payload = None
            inferred = _layer_mapping_from_group_children(payload)
            if inferred:
                lines = ", ".join(
                    f"Group {entry['group_no']} '{entry['group_name']}' = "
                    f"{_LAYER_ROLE_LABELS[str(entry['role'])]}"
                    for entry in inferred
                )
                answer = self._ask_one(
                    f"콘솔 그룹 이름에서 레이어 역할을 추정했습니다: {lines}. "
                    "이 매핑을 기록할까요? (그룹 멤버십은 콘솔에서 읽을 수 없어 "
                    "역할 라벨로만 기록합니다.)",
                    options=(
                        QuestionOption(label="이 매핑 사용"),
                        QuestionOption(label="단일 레이어로 진행"),
                    ),
                    why=(
                        "레이어 매핑이 없으면 Front/Back/Beam/Audience 분리 연출은 "
                        "검증되지 않은 단일 레이어 계획으로 표시됩니다."
                    ),
                )
                if answer and "사용" in answer:
                    mapping = inferred
        self._song_layer_mapping = mapping
        return mapping

    def _song_compose(
        self, state: _SongDesignState
    ) -> tuple[UnifiedSongLightingPlan, SongCueCompositionResult]:
        built = _build_unified_song_plan(
            sections=state.sections,
            profile=state.interview.working_profile,
            rig=state.rig,
            records=state.records,
            timing=state.timing,
            sequence_no=state.sequence_no,
            requery_overrides=state.requery_overrides,
            fade_overrides=state.fade_overrides,
            fx_overrides=state.fx_overrides,
            palette_mode=state.palette_mode,
            concept_colors=state.concept_colors,
        )
        return built, compose_song_cue_bundle(built)

    def _song_send_timeline(
        self,
        state: _SongDesignState,
        plan: UnifiedSongLightingPlan,
        composition: SongCueCompositionResult,
        *,
        lifecycle: str | None = None,
        readback_verified: bool | None = None,
        readback_message: str | None = None,
    ) -> None:
        if lifecycle is None:
            lifecycle = (
                "requires_requery" if composition.requery_requirements else "pending_approval"
            )
        payload = _song_timeline_payload(
            plan,
            composition,
            lifecycle=lifecycle,
            sequence_no=state.sequence_no,
            readback_verified=readback_verified,
            readback_message=readback_message,
            warnings=state.plan_warnings,
            layer_mapping=state.layer_mapping,
            preset_start=state.preset_start,
        )
        # Keep the LAST projection process-wide so a refreshed browser (new
        # WebSocket) is replayed the current timeline instead of a blank pane.
        if self._timeline_store is not None:
            self._timeline_store.latest = payload
        self._send(song_timeline_event(timeline=payload))

    def _song_merge_requery_answer(
        self, state: _SongDesignState, section_index: int, answer: str
    ) -> bool:
        slot = section_index - 1
        if not 0 <= slot < len(state.sections):
            return False
        override = _requery_override(
            answer,
            section=state.sections[slot],
            section_index=section_index,
            section_count=len(state.sections),
        )
        if override is not None:
            state.requery_overrides[section_index] = override
        else:
            # No position named — treat the answer as the section's corrected
            # mood text and re-resolve it.
            state.sections[slot] = replace(state.sections[slot], mood=answer)
        return True

    def _song_requery_rounds(
        self,
        state: _SongDesignState,
        plan: UnifiedSongLightingPlan,
        composition: SongCueCompositionResult,
    ) -> tuple[UnifiedSongLightingPlan, SongCueCompositionResult, InstructionResult | None]:
        rounds = 0
        while composition.requery_requirements and rounds < 3:
            rounds += 1
            progressed = False
            exhausted = False
            for requirement in composition.requery_requirements:
                if requirement.step is not None:
                    # 미확정 인터뷰 답변 → 해당 카드부터 부분 재인터뷰(DI5).
                    # An exhausted channel would only auto-draft again (and
                    # would DROP later confirmed answers) — snapshot and
                    # restore so an unanswered re-interview changes nothing.
                    snapshot = dict(state.interview.answers)
                    state.interview.restart_from(requirement.step)
                    failure = self._song_run_interview(state.interview)
                    if failure is not None:
                        return plan, composition, failure
                    record = state.interview.answers.get(requirement.step)
                    if record is None or not record.confirmed:
                        state.interview.answers.clear()
                        state.interview.answers.update(snapshot)
                        exhausted = True
                        break
                    state.records = state.interview.audit_trail()
                    progressed = True
                    # A re-interview may have (re)confirmed several later
                    # steps at once — the remaining requirement rows are
                    # stale; recompose before touching another one.
                    break
                if requirement.section_index is None:
                    continue
                slot = requirement.section_index - 1
                if not 0 <= slot < len(state.sections):
                    continue
                answer = self._ask_one(
                    requirement.prompt,
                    options=_requery_card_options(
                        state.sections[slot],
                        section_index=requirement.section_index,
                        section_count=len(state.sections),
                    ),
                    why=(
                        f"{requirement.axis} 입력을 확정할 수 없습니다: {requirement.reason}. "
                        "이 답변 없이는 리뷰 번들을 콘솔에 쓸 수 없습니다."
                    ),
                )
                if answer is None:
                    exhausted = True
                    break
                progressed = (
                    self._song_merge_requery_answer(state, requirement.section_index, answer)
                    or progressed
                )
            if progressed:
                plan, composition = self._song_compose(state)
                self._song_send_timeline(state, plan, composition)
            if exhausted or not progressed:
                break
        return plan, composition, None

    def _song_plan_edit(self, text: str) -> InstructionResult | None:
        """PLAN-stage editing (handoff 2026-08-15 priority 1): while a composed
        song design awaits approval, "큐 N …" turns mutate the PLAN — delete a
        cue, insert a section between cues, or retarget one cue's position/
        color — with ZERO console commands, then recompose and re-ask
        approval. Approved/stored timelines keep riding `_timeline_cue_edit`
        (diff-only /Merge); this route exists so pre-approval edits never
        touch the console at all."""
        state = self._pending_song_plan
        if state is None:
            return None
        if _SONG_DESIGN_REQUEST.search(text) is not None or _is_natural_song_brief(text):
            return None  # a fresh design supersedes; that path clears pending
        if _SONG_REQUERY_CANCEL.match(text) is not None:
            self._pending_song_plan = None
            self._pending_song_requery = None
            return InstructionResult(
                status="ok",
                text=(
                    "보류 중이던 곡 설계 계획을 취소했습니다. 콘솔에는 아무것도 쓰지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        delete = _PLAN_EDIT_DELETE.search(text)
        between = _PLAN_EDIT_INSERT_BETWEEN.search(text)
        adjacent = _PLAN_EDIT_INSERT_ADJACENT.search(text)
        count = len(state.sections)
        if delete is not None:
            cue = int(delete.group("cue"))
            if not 1 <= cue <= count:
                return self._pointing_refusal(
                    f"계획에 큐 {cue}가 없어 삭제하지 않았습니다. (보유 큐: 1~{count})"
                )
            if count == 1:
                return self._pointing_refusal(
                    "마지막 남은 큐는 삭제할 수 없습니다. "
                    "계획 전체를 중단하려면 '취소'라고 답해 주세요."
                )
            removed = state.sections.pop(cue - 1)
            _plan_edit_remap_overrides(
                state, lambda index: None if index == cue else (index - 1 if index > cue else index)
            )
            note = f"큐 {cue}({removed.name}) 삭제"
        elif between is not None or adjacent is not None:
            if between is not None:
                first = int(between.group("a"))
                second = int(between.group("b"))
                name = between.group("name").strip()
                if second != first + 1 or not 1 <= first < count:
                    return self._pointing_refusal(
                        f"큐 {first}와 {second} 사이에는 추가할 수 없습니다. "
                        f"이웃한 큐 번호를 지정해 주세요. (보유 큐: 1~{count})"
                    )
                insert_slot = first
            else:
                assert adjacent is not None
                cue = int(adjacent.group("cue"))
                name = adjacent.group("name").strip()
                if not 1 <= cue <= count:
                    return self._pointing_refusal(
                        f"계획에 큐 {cue}가 없어 추가하지 않았습니다. (보유 큐: 1~{count})"
                    )
                insert_slot = cue if adjacent.group("where") in ("뒤", "다음") else cue - 1
            if not name:
                return self._pointing_refusal(
                    "추가할 구간의 이름/무드가 필요합니다. 예: '큐 2와 3 사이에 브레이크 추가'."
                )
            start_ms = _plan_insert_start_ms(state.sections, insert_slot)
            state.sections.insert(
                insert_slot, PositionSheetSection(name=name, start_ms=start_ms, mood=name)
            )
            inserted_index = insert_slot + 1
            _plan_edit_remap_overrides(
                state, lambda index: index + 1 if index >= inserted_index else index
            )
            note = f"큐 {inserted_index}({name}) 추가"
        else:
            cue_match = _PLAN_EDIT_CUE.search(text)
            if cue_match is None:
                return None
            position = _requery_position_from_answer(text) or _timeline_edit_target_position(text)
            colors = _extract_color_words(text)
            d_level = _plan_edit_d_level(text)
            fade_match = _CUE_FADE.search(text)
            fx_off = _PLAN_EDIT_FX_OFF.search(text) is not None
            fx_on = not fx_off and _PLAN_EDIT_FX_ON.search(text) is not None
            time_match = _PLAN_EDIT_TIME_MOVE.search(text)
            if (
                position is None
                and not colors
                and d_level is None
                and fade_match is None
                and not fx_off
                and not fx_on
                and time_match is None
            ):
                return None  # not an edit vocabulary we own — fall through
            cue = int(cue_match.group("cue"))
            if not 1 <= cue <= count:
                return self._pointing_refusal(
                    f"계획에 큐 {cue}가 없어 수정하지 않았습니다. (보유 큐: 1~{count})"
                )
            slot = cue - 1
            changes: list[str] = []
            if colors:
                # Palette flows from the section's OWN color words — replace
                # any earlier ones so edits retarget instead of accumulating.
                section = state.sections[slot]
                stripped = _COLOR_WORDS.sub("", section.mood).strip()
                state.sections[slot] = replace(
                    section, mood=f"{stripped} {' '.join(colors)}".strip()
                )
                changes.append(f"컬러 {'/'.join(colors)}")
            if position is not None:
                self._song_merge_requery_answer(state, cue, f"{position} {' '.join(colors)}")
                changes.append(f"포지션 {position}")
            if d_level is not None:
                existing = state.requery_overrides.get(cue)
                if existing is None:
                    # Preserve the section's own direct position intent — a
                    # bare override would otherwise drop it (결함 4 priority).
                    section = state.sections[slot]
                    direct = _direct_position_intent(f"{section.name} {section.mood}")
                    existing = DirectorOverride(position_candidates=direct)
                state.requery_overrides[cue] = replace(existing, d_level=d_level)
                changes.append(f"디머 D{d_level}")
            if fade_match is not None:
                fade_seconds = float(fade_match.group("sec") or fade_match.group("sec2"))
                state.fade_overrides[cue] = fade_seconds
                changes.append(f"페이드 {fade_seconds:g}초")
            if fx_off:
                state.fx_overrides[cue] = False
                changes.append("FX 끔")
            elif fx_on:
                state.fx_overrides.pop(cue, None)
                changes.append("FX 표준 복원")
            if time_match is not None:
                moved_ms = _plan_edit_time_ms(time_match.group("time"))
                if moved_ms is None:
                    return self._pointing_refusal(
                        "이동할 시각을 읽지 못했습니다. 예: '큐 2를 0:30으로 이동'."
                    )
                section = state.sections[slot]
                state.sections[slot] = replace(section, start_ms=moved_ms)
                minute, second = divmod(moved_ms // 1000, 60)
                changes.append(f"시작 {minute}:{second:02d}")
                if [s.start_ms for s in state.sections] != sorted(
                    s.start_ms for s in state.sections
                ):
                    # The move crossed a neighbour — re-sort and remap every
                    # per-index override to the section's new cue number.
                    order = sorted(
                        range(len(state.sections)), key=lambda i: state.sections[i].start_ms
                    )
                    new_index = {old + 1: new + 1 for new, old in enumerate(order)}
                    state.sections = [state.sections[i] for i in order]
                    _plan_edit_remap_overrides(state, lambda index: new_index.get(index, index))
                    changes.append(f"큐 순서 재정렬 (큐 {new_index[cue]}로 이동)")
            note = f"큐 {cue} {' · '.join(changes)}"
        plan, composition = self._song_compose(state)
        self._song_send_timeline(state, plan, composition)
        plan, composition, failure = self._song_requery_rounds(state, plan, composition)
        if failure is not None:
            return failure
        result = self._song_finalize(state, plan, composition)
        return replace(result, text=f"계획 수정(콘솔 무접촉): {note}. {result.text}")

    def _timeline_cue_edit(self, text: str) -> InstructionResult | None:
        """Edit ONE cue of the DISPLAYED director timeline (user finding,
        2026-08-15: the model fallback once edited an unrelated sequence by
        name and the timeline never updated). This route (a) always targets
        the timeline's own sequence number, (b) merges only the changed
        position into the existing cue (``/Merge`` — a full re-store would
        drop the cue's dimmer/color), and (c) updates the projection + replay
        store so the runbook reflects the edit immediately."""
        if _TIMELINE_EDIT_REQUEST.search(text) is None:
            return None
        cue_match = _TIMELINE_EDIT_CUE.search(text)
        if cue_match is None:
            return None
        target = _timeline_edit_target_position(text)
        if target is None:
            return None
        store = self._timeline_store
        timeline = store.latest if store is not None else None
        if not isinstance(timeline, dict):
            return self._pointing_refusal(
                "수정할 감독 타임라인이 없습니다. 곡 설계를 완료하거나 "
                "라이브러리에서 타임라인을 먼저 불러와 주세요."
            )
        sections = timeline.get("sections")
        sections = sections if isinstance(sections, list) else []
        cue_no = int(cue_match.group("cue"))
        slot = next(
            (
                index
                for index, section in enumerate(sections)
                if isinstance(section, dict) and section.get("cue_number") == cue_no
            ),
            None,
        )
        if slot is None:
            known = ", ".join(
                str(section.get("cue_number")) for section in sections if isinstance(section, dict)
            )
            return self._pointing_refusal(
                f"감독 타임라인에 큐 {cue_no}가 없습니다. (보유 큐: {known or '없음'})"
            )
        sequence_no = timeline.get("sequence_number")
        if not isinstance(sequence_no, int):
            return self._pointing_refusal(
                "타임라인의 시퀀스 번호를 확인할 수 없어 수정하지 않았습니다."
            )
        preset_start = timeline.get("preset_start")
        if not isinstance(preset_start, int):
            answer = self._ask_one(
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                "저장돼 있나요? (예: 21 → 2.21~2.30)",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "이 타임라인 저장본에는 프리셋 시작 번호가 없어, 잘못된 "
                    "슬롯을 리콜하면 다른 포지션이 무대에 나갑니다."
                ),
            )
            try:
                preset_start = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "프리셋 시작 번호를 받지 못해 큐를 수정하지 않았습니다."
                )
        fixtures = self._read_pointing_coordinates("timeline-edit-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal("좌표가 확인된 장비가 없어 큐를 수정하지 않았습니다.")
        fids = [fid for fid, _position in fixtures]
        preset_no = preset_start + BASIC_POSITION_SEQUENCE.index(target)
        commands = (
            "ChangeDestination Root",
            "ClearAll",
            preset_recall_command(fids, preset_no),
            f"Store Sequence {sequence_no} Cue {cue_no} /Merge",
            "ClearAll",
        )
        executed = self._registry.dispatch(
            ToolCall(
                id="timeline-cue-edit",
                name="run_commands",
                arguments={"commands": list(commands)},
            )
        )
        failed = [
            outcome
            for outcome in executed.command_outcomes
            if outcome.status in ("failed", "blocked", "rejected", "not_executed")
        ]
        if executed.result.is_error or failed:
            return InstructionResult(
                status="ok",
                text=(
                    f"감독 타임라인 큐 {cue_no} 수정 명령이 완료되지 않아 "
                    "타임라인을 갱신하지 않았습니다."
                ),
                command_outcomes=tuple(executed.command_outcomes),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        updated_section = dict(sections[slot])
        updated_section["position"] = target
        updated_sections = list(sections)
        updated_sections[slot] = updated_section
        updated = dict(timeline)
        updated["sections"] = updated_sections
        updated["readback"] = {
            "verified": (timeline.get("readback") or {}).get("verified"),
            "message": f"큐 {cue_no} 포지션을 {target}(으)로 수정 (Preset 2.{preset_no} 병합)",
        }
        if store is not None:
            store.latest = updated
        self._send(song_timeline_event(timeline=updated))
        return InstructionResult(
            status="ok",
            text=(
                f"감독 타임라인 큐 {cue_no}의 포지션을 {target}(으)로 수정했습니다 — "
                f"Sequence {sequence_no} Cue {cue_no}에 Preset 2.{preset_no}을 병합하고 "
                "타임라인에 즉시 반영했습니다."
            ),
            command_outcomes=tuple(executed.command_outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _setlist_mode(self, text: str) -> InstructionResult | None:
        """셋리스트 모드 (priority 4): allocate library songs to consecutive
        setlist sequences (기본 210, 220, …) and page-1 executors (기본 101~).

        Per song (newest library version per base name): ``Copy Sequence
        <원본> At <슬롯>`` — the stored song is duplicated into its setlist
        slot, never moved — then ``Assign Sequence <슬롯> At Executor <n>``.
        Safety: every target slot is PRE-CHECKED empty (기존 시퀀스를 덮어쓰지
        않음), the whole plan rides ONE explicit approval card, the bundle is
        dispatched atomically, and each executor assignment is readback-
        verified via the ``Executor <n>`` identity probe (``node.sequenceNo``
        — the same shape cue_monitor/dash read)."""
        if _SETLIST_REQUEST.search(text) is None:
            return None
        library = self._timeline_library
        entries = library.items() if library is not None else []
        if not entries:
            return self._pointing_refusal(
                "셋리스트를 만들 라이브러리 곡이 없습니다. 곡 설계를 승인/저장하거나 "
                "타임라인을 라이브러리에 먼저 저장해 주세요."
            )
        # Newest first — the FIRST entry per base name is that song's latest.
        latest: dict[str, dict] = {}
        order: list[str] = []
        for entry in entries:
            base = _setlist_base_name(entry.get("name"))
            if base and base not in latest:
                latest[base] = entry
                order.append(base)
        requested = _setlist_requested_names(text)
        if requested:
            chosen: list[str] = []
            for name in requested:
                base = _setlist_base_name(name)
                match = next(
                    (known for known in order if known.casefold() == base.casefold()), None
                )
                if match is None:
                    return self._pointing_refusal(
                        f"라이브러리에 '{base}' 곡이 없습니다. (보유 곡: {', '.join(order)})"
                    )
                if match not in chosen:
                    chosen.append(match)
        else:
            chosen = list(order)
        seq_match = _SETLIST_SEQ_START.search(text)
        exec_match = _SETLIST_EXEC_START.search(text)
        seq_start = int(seq_match.group("no")) if seq_match else _SETLIST_DEFAULT_SEQ_START
        exec_start = int(exec_match.group("no")) if exec_match else _SETLIST_DEFAULT_EXEC_START
        # Executor console form is page*100+slot (dash/cue_monitor measured):
        # the run must stay inside one page's 1~99 slot window.
        slots_left = 99 - (exec_start % 100) + 1
        if exec_start % 100 == 0 or len(chosen) > slots_left:
            return self._pointing_refusal(
                f"Executor {exec_start}부터 {len(chosen)}곡을 배정하면 페이지 슬롯 범위"
                "(x01~x99)를 벗어납니다. 시작 번호를 조정해 주세요."
            )
        plan_rows: list[tuple[str, int, int, int]] = []  # (곡, 원본, 슬롯, executor)
        skipped: list[str] = []
        for base in chosen:
            timeline = latest[base].get("timeline") or {}
            source = timeline.get("sequence_number")
            if not isinstance(source, int) or not timeline.get("console_stored"):
                skipped.append(f"{base}(콘솔 미저장 — 승인/저장 후 다시)")
                continue
            slot_index = len(plan_rows)
            plan_rows.append(
                (base, source, seq_start + _SETLIST_SEQ_STEP * slot_index, exec_start + slot_index)
            )
        if not plan_rows:
            reasons = "; ".join(skipped) if skipped else "곡 없음"
            return self._pointing_refusal(f"셋리스트에 넣을 수 있는 곡이 없습니다: {reasons}.")
        # PRE-CHECK: every target slot must be empty (a live rig may already
        # hold sequences there — the 2026-08-15 safety rule: 새 번호 사용 또는
        # 기존 상태 확인). A source-equals-slot row skips the copy, not the check.
        occupied: list[str] = []
        for base, source, slot, _exec_no in plan_rows:
            if slot == source:
                continue
            probe = self._registry.dispatch(
                ToolCall(
                    id=f"setlist-slot-check-{slot}",
                    name="query_state",
                    arguments={"path": f"{self._rig_paths['sequences']}/{slot}"},
                )
            )
            try:
                payload = json.loads(probe.result.content)
            except (json.JSONDecodeError, TypeError):
                payload = None
            if _setlist_node_exists(payload):
                occupied.append(f"Sequence {slot} ({base} 슬롯)")
        if occupied:
            return self._pointing_refusal(
                f"셋리스트 슬롯이 이미 사용 중입니다: {', '.join(occupied)}. "
                "기존 시퀀스는 덮어쓰지 않습니다 — '시퀀스 N부터'로 빈 구간을 지정해 주세요."
            )
        plan_lines = [
            f"{index}. {base}: Sequence {source} → {slot} / Executor {exec_no}"
            for index, (base, source, slot, exec_no) in enumerate(plan_rows, start=1)
        ]
        skipped_note = f" 제외: {'; '.join(skipped)}." if skipped else ""
        approval = self._ask_one(
            "셋리스트 배분 계획:\n"
            + "\n".join(plan_lines)
            + f"\n{skipped_note}\n원본 시퀀스는 유지(복사)되고, 지정 Executor의 기존 배정은 "
            "덮어씁니다. 실행할까요?",
            options=(
                QuestionOption(label="승인"),
                QuestionOption(label="취소"),
            ),
            why="셋리스트 배분은 콘솔 쇼 객체(시퀀스 복사·Executor 배정)를 변경합니다.",
        )
        if not _is_explicit_song_approval(approval):
            return InstructionResult(
                status="ok",
                text=(
                    "셋리스트 계획을 보여드렸고, 승인 전이므로 콘솔에 쓰지 않았습니다. "
                    + " / ".join(plan_lines)
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        commands: list[str] = []
        for _base, source, slot, exec_no in plan_rows:
            if slot != source:
                commands.append(f"Copy Sequence {source} At {slot}")
            commands.append(f"Assign Sequence {slot} At Executor {exec_no}")
        executed = self._registry.dispatch(
            ToolCall(
                id="setlist-assign-bundle",
                name="run_commands",
                arguments={"commands": commands},
            )
        )
        failed = [
            outcome
            for outcome in executed.command_outcomes
            if outcome.status in ("failed", "blocked", "rejected", "not_executed")
        ]
        if executed.result.is_error or failed:
            return InstructionResult(
                status="ok",
                text=(
                    "셋리스트 배분 명령이 완료되지 않았습니다 — 아래 명령 상태를 확인해 "
                    "주세요. " + " / ".join(plan_lines)
                ),
                command_outcomes=tuple(executed.command_outcomes),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        verified: list[str] = []
        mismatched: list[str] = []
        for base, _source, slot, exec_no in plan_rows:
            probe = self._registry.dispatch(
                ToolCall(
                    id=f"setlist-readback-{exec_no}",
                    name="query_state",
                    arguments={"path": f"Executor {exec_no}"},
                )
            )
            try:
                payload = json.loads(probe.result.content)
            except (json.JSONDecodeError, TypeError):
                payload = None
            assigned = _setlist_executor_sequence_no(payload)
            if assigned == slot:
                verified.append(f"Executor {exec_no}→Seq {slot}({base})")
            else:
                mismatched.append(
                    f"Executor {exec_no}: 기대 Seq {slot}, 확인값 {assigned!r}({base})"
                )
        status = "ok" if not mismatched else "readback_failed"
        readback_note = (
            f"readback 검증 완료: {', '.join(verified)}."
            if not mismatched
            else f"readback 불일치: {'; '.join(mismatched)}."
        )
        return InstructionResult(
            status=status,
            text=(
                f"셋리스트 배분을 실행했습니다 — {' / '.join(plan_lines)}.{skipped_note} "
                f"{readback_note}"
            ),
            command_outcomes=tuple(executed.command_outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _song_requery_resume(self, text: str) -> InstructionResult | None:
        """A later turn answering an open requery card ("벌스는 Center → Fan
        Out") resumes the SAME pending plan — never a new natural-language
        design request. Narrowly gated: only a basic-position answer or an
        explicit cancel is consumed; everything else falls through."""
        state = self._pending_song_requery
        if state is None:
            return None
        if _SONG_DESIGN_REQUEST.search(text) is not None or _is_natural_song_brief(text):
            return None  # a fresh design supersedes; that path clears pending
        if _SONG_REQUERY_CANCEL.match(text) is not None:
            self._pending_song_requery = None
            return InstructionResult(
                status="ok",
                text=(
                    "보류 중이던 곡 설계 재질의를 취소했습니다. 콘솔에는 아무것도 쓰지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        if _requery_position_from_answer(text) is None:
            return None
        plan, composition = self._song_compose(state)
        open_sections = [
            requirement.section_index
            for requirement in composition.requery_requirements
            if requirement.section_index is not None
        ]
        if not open_sections:
            return None
        target = next(
            (
                index
                for index in open_sections
                if state.sections[index - 1].name and state.sections[index - 1].name in text
            ),
            open_sections[0],
        )
        self._song_merge_requery_answer(state, target, text)
        plan, composition = self._song_compose(state)
        self._song_send_timeline(state, plan, composition)
        plan, composition, failure = self._song_requery_rounds(state, plan, composition)
        if failure is not None:
            return failure
        return self._song_finalize(state, plan, composition)

    def _song_finalize(
        self,
        state: _SongDesignState,
        plan: UnifiedSongLightingPlan,
        composition: SongCueCompositionResult,
    ) -> InstructionResult:
        review_text = _review_text(plan, composition)
        audit_lines = [
            f"{_DI_STEP_LABELS[record.step]}: {_describe_di_value(record.value)} "
            f"({'확정' if record.confirmed else '감독 미확정'})"
            for record in state.records
        ]
        if composition.requery_requirements:
            # 미응답 요구를 세션에 보존 — 다음 턴의 포지션 답변이 이어서 병합된다.
            self._pending_song_requery = state
            self._pending_song_plan = state
            open_prompts = "; ".join(
                requirement.prompt for requirement in composition.requery_requirements
            )
            return InstructionResult(
                status="ok",
                text=(
                    f"연출 인터뷰 결과 — {' / '.join(audit_lines)}. "
                    "검토 번들을 만들었지만 미확정/미해결 입력이 있어 콘솔에 쓰지 않았습니다. "
                    f"남은 재질의: {open_prompts}. "
                    "다음 턴에 포지션으로 답하면 같은 계획에 이어서 반영합니다"
                    "(중단: '취소'). "
                    f"{review_text}"
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        self._pending_song_requery = None
        self._pending_song_plan = state
        sequence_no = state.sequence_no
        approval = self._ask_one(
            f"{review_text}\n\n이 전체 리뷰 번들을 시퀀스 {sequence_no}에 원자적으로 저장할까요?",
            options=(
                QuestionOption(label="승인"),
                QuestionOption(label="수정"),
                QuestionOption(label="취소"),
            ),
            why=(
                "인터뷰/타임라인 미리보기는 콘솔에 쓰지 않습니다. "
                "이 별도 승인 뒤에만 한 번 실행합니다."
            ),
        )
        if not _is_explicit_song_approval(approval):
            return InstructionResult(
                status="ok",
                text=(
                    f"연출 인터뷰 결과 — {' / '.join(audit_lines)}. "
                    "전체 리뷰 번들을 보여드렸고, 감독 승인 전이므로 콘솔에 쓰지 않았습니다. "
                    "승인 전 계획은 콘솔 무접촉으로 계속 수정할 수 있습니다 — "
                    "예: '큐 3을 Center로', '큐 3 컬러를 골드로', '큐 2 D4', "
                    "'큐 3 페이드 2초', '큐 2 FX 꺼', '큐 2를 0:30으로 이동', "
                    "'큐 2와 3 사이에 브레이크 추가', '큐 4 삭제' (중단: '취소'). "
                    f"{review_text}"
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        self._pending_song_plan = None
        approved_plan = replace(plan, approval=ApprovalState.approved(reviewer="director"))
        approved_composition = compose_song_cue_bundle(approved_plan)
        self._song_send_timeline(state, approved_plan, approved_composition, lifecycle="approved")
        try:
            commands = self._reviewed_song_commands(
                approved_composition,
                sequence_no=sequence_no,
                preset_start=state.preset_start,
                fids=state.fids,
                timing=state.timing,
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"리뷰 번들을 실행 명령으로 만들 수 없습니다: {error}")
        executed = self._registry.dispatch(
            ToolCall(
                id="song-design-reviewed-bundle",
                name="run_commands",
                arguments={"commands": list(commands)},
            )
        )
        timed_cues = (
            _song_timed_cue_expectations(approved_composition.bundle, state.timing)
            if approved_composition.bundle is not None
            else ()
        )
        readback = self._song_readback_requests(
            sequence_no=sequence_no,
            timing=state.timing,
            timed_cues=timed_cues,
        )
        if readback.failure is not None:
            self._song_send_timeline(
                state,
                approved_plan,
                approved_composition,
                lifecycle="readback_failed",
                readback_verified=False,
                readback_message=readback.failure,
            )
            snapshot_note = self._song_auto_snapshot()
            return InstructionResult(
                status="readback_failed",
                text=(
                    f"연출 인터뷰 결과 — {' / '.join(audit_lines)}. "
                    f"감독 승인 후 시퀀스 {sequence_no}에 리뷰 번들 1건을 원자 실행 요청했지만 "
                    f"readback 검증에 실패했습니다: {readback.failure}. "
                    f"{review_text} readback 요청: {', '.join(readback.paths)}.{snapshot_note}"
                ),
                command_outcomes=tuple(executed.command_outcomes),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        self._song_send_timeline(
            state,
            approved_plan,
            approved_composition,
            lifecycle="verified",
            readback_verified=True,
            readback_message="Sequence 및 타이밍 readback 검증 완료",
        )
        snapshot_note = self._song_auto_snapshot()
        return InstructionResult(
            status="ok",
            text=(
                f"연출 인터뷰 결과 — {' / '.join(audit_lines)}. "
                f"감독 승인 후 시퀀스 {sequence_no}에 리뷰 번들 1건을 원자 실행 요청했습니다. "
                f"{review_text} readback 검증 완료: {', '.join(readback.paths)}.{snapshot_note}"
            ),
            command_outcomes=tuple(executed.command_outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _song_auto_snapshot(self) -> str:
        """Auto version snapshot (priority 3): after an approved console store
        (verified OR readback_failed — the bundle was dispatched either way),
        save the just-sent timeline projection to the library as
        ``<이름> (자동 vN)``. Read-only bookkeeping: a failure never blocks the
        store result, and a saved entry grants no console capability."""
        library = self._timeline_library
        store = self._timeline_store
        payload = store.latest if store is not None else None
        if library is None or not isinstance(payload, dict):
            return ""
        title = str(payload.get("song_title") or "").strip()
        if not title or title == _DESIGN_INTERVIEW_TITLE:
            sequence_no = payload.get("sequence_number")
            title = f"Sequence {sequence_no}" if sequence_no is not None else "타임라인"
        try:
            entry = library.auto_save(title, payload)
        except Exception:
            return " (라이브러리 자동 저장 실패 — 콘솔 저장 결과에는 영향 없음)"
        return f" 라이브러리에 '{entry['name']}' 자동 저장."

    def _repeating_type_columns_layout(self, text: str) -> InstructionResult | None:
        """Arrange repeating MMX/MMX/350 columns with independent grid pitches."""
        pattern_present = _REPEATING_TYPE_COLUMNS_REQUEST.search(text) is not None
        if pattern_present:
            self._pending_repeating_columns = _PendingRepeatingColumns(instruction=text)
        pending = self._pending_repeating_columns
        if pending is None:
            return None

        column_gap = _COLUMN_GAP.search(text)
        fixture_gap = _FIXTURE_GAP.search(text)
        if (
            not pattern_present
            and column_gap is None
            and fixture_gap is None
            and re.search(r"(?:뭘|무엇|뭐).*(?:알려|필요)|(?:필요|알려).*?(?:뭘|무엇|뭐)", text)
        ):
            missing_labels = [
                label
                for value, label in (
                    (pending.row_spacing, "열간 간격"),
                    (pending.column_spacing, "장비간 좌우 간격"),
                )
                if value is None
            ]
            detail = (
                f"현재 필요한 정보는 {', '.join(missing_labels)}입니다."
                if missing_labels
                else (
                    "열간·장비간 간격은 모두 확인했습니다. 전체 3D 패치에서 "
                    "MMX·350 수량만 확인하면 됩니다."
                )
            )
            return InstructionResult(
                status="ok",
                text=f"MMX 10대 → MMX 10대 → 350 10대 반복 배치를 계속 준비 중입니다. {detail}",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        try:
            if column_gap is not None:
                pending.row_spacing = float(column_gap.group("value").replace(",", "."))
            if fixture_gap is not None:
                pending.column_spacing = float(fixture_gap.group("value").replace(",", "."))
            if (
                pending.row_spacing is not None
                and pending.row_spacing <= 0.0
                or pending.column_spacing is not None
                and pending.column_spacing <= 0.0
            ):
                raise ValueError("non-positive spacing")
        except ValueError:
            return InstructionResult(
                status="ok",
                text="열간·장비간 간격은 0보다 큰 미터 값이어야 합니다.",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        missing = [
            label
            for value, label in (
                (pending.row_spacing, "열간 간격"),
                (pending.column_spacing, "장비간 좌우 간격"),
            )
            if value is None
        ]
        if missing:
            # Collect each missing gap through its OWN card, one at a time —
            # clickable presets plus a free-text box — instead of a prose wall
            # the operator has to parse and answer in one breath.
            gap_options = (
                QuestionOption(label="1m"),
                QuestionOption(label="1.5m"),
                QuestionOption(label="2m"),
            )
            for attr, prompt in (
                ("row_spacing", "열 사이(열간) 간격은 몇 미터인가요?"),
                ("column_spacing", "같은 열 안 장비 사이(좌우) 간격은 몇 미터인가요?"),
            ):
                if getattr(pending, attr) is not None:
                    continue
                answer = self._ask_one(
                    prompt,
                    why="열 배치를 계산하려면 열간·장비간 간격이 각각 필요합니다.",
                    options=gap_options,
                )
                value = _first_metres(answer)
                if value is not None and value > 0.0:
                    setattr(pending, attr, value)
            still_missing = [
                label
                for value, label in (
                    (pending.row_spacing, "열간 간격"),
                    (pending.column_spacing, "장비간 좌우 간격"),
                )
                if value is None
            ]
            if still_missing:
                return InstructionResult(
                    status="ok",
                    text=(
                        "MMX 10대 → MMX 10대 → 350 10대 반복 배치를 기억했습니다. "
                        f"계속하려면 {', '.join(still_missing)}을 미터 단위로 알려주세요."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
        row_spacing = pending.row_spacing
        column_spacing = pending.column_spacing
        assert row_spacing is not None and column_spacing is not None
        spatial = self._registry.dispatch(
            ToolCall(id="repeating-columns-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
        if spatial.result.is_error or not isinstance(payload, dict):
            return InstructionResult(
                status="ok",
                text=(
                    "3D 좌표를 읽지 못해 배치를 시작하지 않았습니다. 콘솔 연결(응답기·OSC "
                    "포트)을 확인한 뒤 다시 요청해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        coverage = payload.get("coverage") or {}
        fixtures = payload.get("fixtures")
        if coverage.get("complete") is not True or not isinstance(fixtures, list):
            return InstructionResult(
                status="ok",
                text=(
                    "전체 3D 패치를 완전히 읽지 못했습니다(부분/절단 응답). 일부만 읽은 상태로 "
                    "배치하면 누락된 장비를 덮어쓸 수 있어 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        def _named(predicate: Callable[[str], bool]) -> list[int]:
            return [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and not isinstance(item.get("fid"), bool)
                and predicate(str(item.get("name", "")))
            ]

        mmx = _named(lambda name: "mmx" in name.casefold())
        mmx_set = set(mmx)
        beam = [
            fid
            for fid in _named(lambda name: re.search(r"350\s*m?", name, re.IGNORECASE) is not None)
            if fid not in mmx_set  # MMX classification wins, so a type is never double-counted
        ]
        found_line = f"현재 패치에서 MMX {len(mmx)}대, 350 계열 {len(beam)}대를 확인했습니다."

        self._last_layout_spacing = (row_spacing, column_spacing)
        column_size = 10
        cycle = ("mmx", "mmx", "beam")
        pools = {"mmx": mmx, "beam": beam}
        cursor = {"mmx": 0, "beam": 0}
        # Budget = how many COMPLETE columns each type can still fill. Follow the
        # requested cyclic order, but SKIP a type that has no full column left
        # rather than stopping the whole walk at the first short type — the old
        # early-stop abandoned every later type in the cycle (e.g. 19 MMX + 20
        # 350 placed one MMX column and dropped all 20 beams). Stop only when no
        # type can fill another column.
        budget = {kind: len(pool) // column_size for kind, pool in pools.items()}
        columns: list[list[int]] = []
        step = 0
        while any(budget.values()):
            kind = cycle[step % len(cycle)]
            step += 1
            if budget[kind] <= 0:
                continue
            start = cursor[kind]
            columns.append(pools[kind][start : start + column_size])
            cursor[kind] = start + column_size
            budget[kind] -= 1

        if not columns:
            return InstructionResult(
                status="ok",
                text=(
                    f"{found_line} MMX/MMX/350 반복 배치는 한 열이 {column_size}대이므로, "
                    f"먼저 MMX가 최소 {column_size}대 있어야 첫 열을 만들 수 있습니다. "
                    "장비 타입이 이름으로 구분되는지(MMX·350 포함) 확인해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        fids = [fid for column in columns for fid in column]
        arranged = self._registry.dispatch(
            ToolCall(
                id="repeating-columns-write",
                name="arrange_fixtures",
                arguments={
                    "preset": "grid",
                    "fids": fids,
                    "rows": len(columns),
                    "columns": column_size,
                    "row_spacing": row_spacing,
                    "column_spacing": column_spacing,
                    "orientation": "xy",
                },
            )
        )
        placed_mmx = cursor["mmx"]
        placed_beam = cursor["beam"]
        summary = (
            f"{found_line} MMX {placed_mmx}대·350 계열 {placed_beam}대를 10대씩 "
            f"{len(columns)}열로, 열간 {row_spacing:g}m·장비간 {column_spacing:g}m 그리드로 "
            "배치하도록 요청했습니다. 승인 또는 라이브 잠금 상태에 따른 결과를 아래 명령 "
            "상태에서 확인해 주세요."
        )
        leftovers = []
        if len(mmx) - placed_mmx > 0:
            leftovers.append(f"MMX {len(mmx) - placed_mmx}대")
        if len(beam) - placed_beam > 0:
            leftovers.append(f"350 계열 {len(beam) - placed_beam}대")
        if leftovers:
            summary += (
                f" 남은 {', '.join(leftovers)}는 {column_size}대에 못 미쳐 완전한 열을 "
                "만들지 못했습니다. 요청하신 MMX·MMX·350 반복은 MMX가 350의 2배일 때 "
                "딱 맞는데 현재 수량은 그렇지 않습니다. 남은 장비를 (1) 부분 열로 그대로 "
                "붙일지, (2) 열당 대수를 바꿔 다시 배치할지 알려주시면 이어서 처리합니다."
            )
        self._pending_repeating_columns = None
        return InstructionResult(
            status="ok",
            text=summary,
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _multi_ring_circle_layout(self, text: str) -> InstructionResult | None:
        """Place a multi-ring circle: ask the missing decisions one card at a
        time (radii, then the remainder ring's order), then arrange each ring.

        This is an EXECUTING handler, not a canned clarifier: it reasons about
        the whole request (ring types/counts + a remainder ring), collects only
        what is genuinely missing through interactive cards, reads the real rig,
        and writes each ring with its own circle arrange (backup + verify per
        call). Count mismatches are reported, never guessed away.
        """
        rings = parse_ring_layout(text)
        if rings is None:
            return None

        radii = self._ask_ring_radii(len(rings))
        order = "fid"
        if any(r.kind == "remainder" and r.alternate for r in rings):
            order = self._ask_remainder_order()

        spatial = self._registry.dispatch(
            ToolCall(id="ring-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
            fixtures = payload["fixtures"]
            if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                raise ValueError("incomplete spatial read")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return InstructionResult(
                status="ok",
                text=(
                    "여러 겹 원형 배치를 계획했지만 전체 3D 좌표를 읽지 못해 시작하지 "
                    "않았습니다. 콘솔 연결을 확인한 뒤 다시 요청해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        def _valid(item: object) -> bool:
            return (
                isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and not isinstance(item.get("fid"), bool)
            )

        coord = {
            item["fid"]: (float(item.get("x", 0.0)), float(item.get("y", 0.0)))
            for item in fixtures
            if _valid(item)
        }
        key = {"fid": lambda f: f, "left": lambda f: coord[f][0], "front": lambda f: coord[f][1]}[
            order
        ]

        def _named(pred) -> list[int]:
            picked = [
                item["fid"] for item in fixtures if _valid(item) and pred(str(item.get("name", "")))
            ]
            return sorted(picked, key=key)

        mmx = _named(lambda n: "mmx" in n.casefold())
        mmx_set = set(mmx)
        beam = [
            fid
            for fid in _named(lambda n: re.search(r"350\s*m?", n, re.IGNORECASE) is not None)
            if fid not in mmx_set
        ]
        beam_set = set(beam)
        classified = mmx_set | beam_set
        others = sorted(
            (item["fid"] for item in fixtures if _valid(item) and item["fid"] not in classified),
            key=key,
        )

        pos = {"mmx": 0, "beam": 0}
        notes: list[str] = []
        ring_fids: list[list[int]] = []
        for index, ring in enumerate(rings, start=1):
            if ring.kind == "remainder":
                rest_mmx = mmx[pos["mmx"] :]
                rest_beam = beam[pos["beam"] :]
                pos["mmx"], pos["beam"] = len(mmx), len(beam)
                merged: list[int] = []
                for a, b in zip(rest_mmx, rest_beam, strict=False):
                    merged.extend((a, b))
                shorter = min(len(rest_mmx), len(rest_beam))
                tail = rest_mmx[shorter:] + rest_beam[shorter:]
                merged.extend(tail)
                merged.extend(others)
                ring_fids.append(merged)
            else:
                pool = mmx if ring.kind == "mmx" else beam
                want = ring.count or 0
                take = pool[pos[ring.kind] : pos[ring.kind] + want]
                pos[ring.kind] += len(take)
                if len(take) < want:
                    label = "MMX" if ring.kind == "mmx" else "350 계열"
                    notes.append(f"{index}번째 원 {label} {want}대 요청 중 {len(take)}대만 가능")
                ring_fids.append(take)

        outcomes: list[CommandOutcome] = []
        placed_lines: list[str] = []
        for index, (fids, radius) in enumerate(zip(ring_fids, radii, strict=False), start=1):
            if not fids:
                notes.append(f"{index}번째 원에 배치할 장비가 없습니다")
                continue
            arranged = self._registry.dispatch(
                ToolCall(
                    id=f"ring-write-{index}",
                    name="arrange_fixtures",
                    arguments={
                        "preset": "circle",
                        "fids": fids,
                        "radius": radius,
                        "start_angle": 0.0,
                        "orientation": "xy",
                    },
                )
            )
            outcomes.extend(arranged.command_outcomes)
            placed_lines.append(f"{index}번째 원(반지름 {radius:g}m): {len(fids)}대")

        summary = "여러 겹 원형 배치를 요청했습니다 — " + ", ".join(placed_lines) + "."
        if notes:
            summary += " 다만 " + "; ".join(notes) + "."
        summary += " 승인 또는 라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
        return InstructionResult(
            status="ok",
            text=summary,
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _ask_ring_radii(self, count: int) -> list[float]:
        """One card for the ring diameters (innermost→outer); default 4/6/8… m."""
        default = [2.0 + i for i in range(count)]  # radius 2,3,4… (diameter 4,6,8…)
        answer = self._ask_one(
            "각 원의 지름을 안쪽→바깥 순서로 알려주세요 (미터).",
            options=(
                QuestionOption(label="4·6·8m"),
                QuestionOption(label="6·8·10m"),
            ),
            why="원마다 반지름이 달라야 여러 겹으로 겹치지 않고 배치됩니다.",
        )
        if not answer:
            return default
        diameters = [float(v.replace(",", ".")) for v in re.findall(r"\d+(?:[.,]\d+)?", answer)]
        radii = [d / 2.0 for d in diameters if d > 0.0]
        if len(radii) < count:
            radii += default[len(radii) :]
        return radii[:count]

    def _ask_remainder_order(self) -> str:
        """One card for how the remainder ring's 번갈아 order is decided."""
        answer = self._ask_one(
            "마지막 원(남은 장비)을 어떤 순서로 번갈아 배치할까요?",
            options=(
                QuestionOption(label="FID 오름차순", description="패치 번호 순 — 가장 예측 가능"),
                QuestionOption(label="좌→우", description="현재 무대 x좌표 순"),
                QuestionOption(label="앞→뒤", description="현재 무대 y좌표 순"),
            ),
            why="circle 프리셋은 넘긴 FID 순서대로 채우므로 번갈아 기준이 필요합니다.",
        )
        if answer and ("좌" in answer or "left" in answer.casefold()):
            return "left"
        if answer and ("앞" in answer or "front" in answer.casefold()):
            return "front"
        return "fid"

    def _typed_two_row_layout(self, text: str) -> InstructionResult | None:
        """Place named MMX/350M rows without trusting the CLI model's tool view."""
        if _TYPED_TWO_ROW_REQUEST.search(text) is None:
            return None
        spatial = self._registry.dispatch(
            ToolCall(id="typed-layout-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
            fixtures = payload["fixtures"]
            if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                raise ValueError("incomplete spatial read")
            mmx = [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and "mmx" in str(item.get("name", "")).lower()
            ][:10]
            beam = [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and re.search(r"350\s*m", str(item.get("name", "")), re.IGNORECASE)
            ][:10]
            if len(mmx) != 10 or len(beam) != 10:
                raise ValueError("fixture types not uniquely identified")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return InstructionResult(
                status="ok",
                text=(
                    "MMX와 350M을 각각 10대로 확정할 수 있는 전체 패치 이름·3D 좌표를 "
                    "읽지 못해 배치를 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        arranged = self._registry.dispatch(
            ToolCall(
                id="typed-layout-write",
                name="arrange_fixtures",
                arguments={
                    "preset": "grid",
                    "fids": [*beam, *mmx],
                    "rows": 2,
                    "columns": 10,
                    "spacing": 1.5,
                    "orientation": "xy",
                },
            )
        )
        self._last_layout_spacing = (1.5, 1.5)
        return InstructionResult(
            status="ok",
            text="350M 10대 앞줄, MMX 10대 뒷줄의 1.5m 간격 2×10 그리드를 요청했습니다.",
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _vocabulary_layout(self, text: str) -> InstructionResult | None:
        """Apply an explicitly worded whole-rig geometry without model latency."""
        match = match_explicit_layout(text)
        if match is None:
            return None
        if self._spatial_fids is None:
            if self._gate.status["live_lock"]:
                return InstructionResult(
                    status="ok",
                    text=(
                        "라이브 잠금 중이라 현재 리그 좌표를 읽지 않았습니다. "
                        "잠금을 해제한 뒤 다시 요청하면 전체 배치 제안을 만들 수 있습니다."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            spatial = self._registry.dispatch(
                ToolCall(id="vocabulary-layout-read", name="get_spatial_context", arguments={})
            )
            try:
                payload = json.loads(spatial.result.content)
                fixtures = payload["fixtures"]
                if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                    raise ValueError("incomplete spatial read")
                fids = tuple(
                    fixture["fid"]
                    for fixture in fixtures
                    if isinstance(fixture, dict)
                    and isinstance(fixture.get("fid"), int)
                    and not isinstance(fixture.get("fid"), bool)
                )
                if not fids or len(fids) != len(fixtures) or len(set(fids)) != len(fids):
                    raise ValueError("invalid fixture identities")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                return InstructionResult(
                    status="ok",
                    text="전체 3D 좌표와 FID를 확인하지 못해 배치를 시작하지 않았습니다.",
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            self._spatial_fids = fids

        arguments: dict[str, object] = {
            "preset": match.preset,
            "fids": list(self._spatial_fids),
        }
        if match.rows is not None:
            arguments["rows"] = match.rows
        if match.columns is not None:
            arguments["columns"] = match.columns
        if match.spacing is not None:
            arguments["spacing"] = match.spacing
        if match.radius is not None:
            arguments["radius"] = match.radius
        if match.preset == "grid" and match.rows * match.columns != len(self._spatial_fids):
            return InstructionResult(
                status="ok",
                text=(
                    f"전체 장비는 {len(self._spatial_fids)}대입니다. 요청한 "
                    f"{match.rows}행×{match.columns}열은 장비 수와 일치하지 않아 "
                    "배치를 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        arranged = self._registry.dispatch(
            ToolCall(
                id="vocabulary-layout-write",
                name="arrange_fixtures",
                arguments=arguments,
            )
        )
        if match.spacing is not None:
            self._last_layout_spacing = (match.spacing, match.spacing)
        labels = {"grid": "그리드", "row": "일렬", "circle": "원형"}
        return InstructionResult(
            status="ok",
            text=(
                f"전체 배치 장비 {len(self._spatial_fids)}대를 {labels[match.preset]} "
                "형태로 배치하도록 요청했습니다."
            ),
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _plain_language_design_request(self, text: str) -> InstructionResult | None:
        """Collect five director decisions without creating show data.

        Each card gives three production-ready starting points. The free-text
        control is an equally valid fourth route: it records the director's
        own instruction verbatim rather than coercing it into a preset.
        """
        if _PLAIN_LANGUAGE_DESIGN_REQUEST.search(text) is None:
            return None
        questions: tuple[tuple[str, str, tuple[QuestionOption, ...]], ...] = (
            (
                "01 · 드라마투르기와 첫 시선",
                (
                    "곡의 첫 30초에서 관객의 시선을 어디에 고정할지 정합니다. "
                    "이후 포지션과 밝기 변화의 기준점입니다."
                ),
                (
                    QuestionOption(
                        label="보컬 고정 · 후면 긴장",
                        description=(
                            "전면은 낮게 남기고, 차가운 역광과 좁은 빔으로 "
                            "보컬 실루엣을 먼저 세웁니다."
                        ),
                    ),
                    QuestionOption(
                        label="리프 확장 · 무대 폭 공개",
                        description=(
                            "리프부터 좌우 폭을 열되 중심 밝기는 절제해, "
                            "후렴을 위한 헤드룸을 남깁니다."
                        ),
                    ),
                    QuestionOption(
                        label="드럼 기점 · 펄스 도입",
                        description=(
                            "킥·스네어의 첫 반복에 짧은 펄스를 주고, "
                            "나머지 레이어는 정지해 긴장을 유지합니다."
                        ),
                    ),
                ),
            ),
            (
                "02 · 색 체계와 화이트 포인트",
                (
                    "베이스·대비·화이트의 역할을 분리합니다. "
                    "백색은 가장 중요한 순간의 보상처럼 아껴 씁니다."
                ),
                (
                    QuestionOption(
                        label="딥 블루 · 스틸 화이트",
                        description=(
                            "차가운 청색을 유지하고 후렴 첫 박에서만 "
                            "스틸 화이트를 짧게 열어 금속성을 만듭니다."
                        ),
                    ),
                    QuestionOption(
                        label="청록 · 보라 대비",
                        description=(
                            "절의 청록과 프리코러스의 보라를 교대시켜, "
                            "후렴의 에너지를 색 변화 없이도 키웁니다."
                        ),
                    ),
                    QuestionOption(
                        label="모노크롬 · 실버 폭발",
                        description=(
                            "거의 무채색으로 출발해 실버·화이트를 "
                            "클라이맥스 전용 신호로 사용합니다."
                        ),
                    ),
                ),
            ),
            (
                "03 · 빔 공간과 포지션 문법",
                (
                    "빔이 무대를 어떻게 자를지 정합니다. 포지션은 장식이 아니라 "
                    "보컬·밴드·관객 중 어느 공간에 힘을 줄지의 선택입니다."
                ),
                (
                    QuestionOption(
                        label="크로스 빔 · 무대 중심 수렴",
                        description=(
                            "후면 빔을 X자로 교차해 중심 밀도를 만들고, "
                            "보컬 축은 비워 시야를 보호합니다."
                        ),
                    ),
                    QuestionOption(
                        label="팬 아웃 · 후렴에서 객석 확장",
                        description=(
                            "도입에서는 좁은 각도를 유지하다가 후렴 드롭에서만 "
                            "좌우와 객석 방향으로 한 번 크게 펼칩니다."
                        ),
                    ),
                    QuestionOption(
                        label="수직 샤프트 · 밴드 실루엣",
                        description=(
                            "상부 수직 빔과 낮은 전면광으로 밴드를 조각처럼 "
                            "보이게 합니다. 카메라와 관객 시야에 안정적입니다."
                        ),
                    ),
                ),
            ),
            (
                "04 · 움직임의 밀도와 전환 규칙",
                (
                    "무빙은 계속 돌리는 효과가 아니라 변화가 필요한 구간의 문장부호입니다. "
                    "움직임 밀도와 전환 형태를 정합니다."
                ),
                (
                    QuestionOption(
                        label="정지 우선 · 드롭 한 번만 이동",
                        description=(
                            "대부분은 헤드를 고정하고, 드롭 또는 후렴 진입에서만 "
                            "재배열해 변화의 크기를 선명하게 만듭니다."
                        ),
                    ),
                    QuestionOption(
                        label="박자 펄스 · 2·4박 강조",
                        description=(
                            "스네어·클랩에 짧은 딤머 또는 셔터 펄스를 쓰되, "
                            "포지션 이동은 마디 단위로 제한합니다."
                        ),
                    ),
                    QuestionOption(
                        label="느린 스윕 · 프레이즈 종료 이동",
                        description=(
                            "보컬 프레이즈 종료에만 2~4초 스윕을 넣어, "
                            "가사 전달을 가리지 않고 공간을 바꿉니다."
                        ),
                    ),
                ),
            ),
            (
                "05 · 후렴 클라이맥스의 메커니즘",
                (
                    "후렴의 '크게 터짐'을 밝기·포지션·색·빔 중 무엇으로 "
                    "들리게 할지 고릅니다. 한 번에 모두 바꾸지 않습니다."
                ),
                (
                    QuestionOption(
                        label="화이트 히트 · 0.5초 스냅",
                        description=(
                            "첫 다운비트에 전면과 후면을 동시에 열고 즉시 "
                            "메인 색으로 복귀해 한 번의 강한 타격을 만듭니다."
                        ),
                    ),
                    QuestionOption(
                        label="와이드 전개 · 2초 페이드",
                        description=(
                            "색은 유지하고 빔 폭과 무대 범위만 2초에 걸쳐 넓혀, "
                            "웅장하지만 눈부심이 적은 클라이맥스를 만듭니다."
                        ),
                    ),
                    QuestionOption(
                        label="스텝형 누적 · 4마디 상승",
                        description=(
                            "4마디 동안 레이어를 하나씩 더해 마지막 마디에만 "
                            "최대 밝기에 도달합니다. 긴 후렴에 적합합니다."
                        ),
                    ),
                ),
            ),
        )
        answers: list[tuple[str, str]] = []
        for prompt, why, options in questions:
            answer = self._ask_one(prompt, options=options, why=why)
            if answer is None:
                return InstructionResult(
                    status="ok",
                    text=(
                        "연출 결정을 기다리는 중에 인터뷰를 멈췄습니다. "
                        "아직 콘솔 명령, 장비 배치, 큐 저장은 수행하지 않았습니다."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            answers.append((prompt.split(" · ", 1)[0], answer))
        decision_lines = "\n".join(f"- {step}: {answer}" for step, answer in answers)
        return InstructionResult(
            status="ok",
            text=(
                "조명감독 연출 브리프를 확정했습니다.\n"
                f"{decision_lines}\n\n"
                "이 브리프는 다음 설계안의 기준입니다. 아직 콘솔 명령, 장비 배치, "
                "프리셋 리콜, 큐 저장은 수행하지 않았습니다. 실제 프로그래밍은 "
                "구간·시퀀스·프리셋·실행 범위를 별도로 확인한 뒤에만 진행합니다."
            ),
            command_outcomes=(),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _status_inquiry(self, text: str) -> InstructionResult | None:
        """Answer an exact conversational status question without model tools."""
        if _STATUS_INQUIRY.match(text) is None:
            return None
        return InstructionResult(
            status="ok",
            text=(
                "현재 상태 확인 요청으로 처리했습니다. 이 메시지로는 콘솔 명령을 "
                "생성하거나 실행하지 않습니다. 실행된 결과는 화면의 실행 이력과 "
                "명령별 상태를 기준으로 확인하세요."
            ),
            command_outcomes=(),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    # @MX:NOTE: [AUTO] one instruction turn — measurement start/finish, gate-truth
    #   summary composition, and the REQ-MVP-044 raw-detail/audit split all funnel
    #   through this single method
    def run_instruction(self, text: str) -> dict:
        """Drive one Korean instruction; sends + returns the final event."""
        self._turn_decisions = []
        if self._recorder is not None:
            self._recorder.turn_started()
        # M6c-1 Finding 1/2: bind THIS session's identity for the whole turn so
        # the shared gate/approval_channel can scope clearances and pending
        # approvals to this connection (no thread hop happens below — the
        # nested gate.screen()/request_approval() calls run synchronously on
        # this same worker thread, see server.safety.session_context).
        token = bind_session_key(self._session_key)
        try:
            try:
                result = self._status_inquiry(text)
                if result is None:
                    result = self._all_fixtures_elevation(text)
                if result is None:
                    result = self._basic_position_presets(text)
                if result is None:
                    result = self._position_cue_sheet(text)
                if result is None:
                    result = self._song_plan_edit(text)
                if result is None:
                    result = self._song_requery_resume(text)
                if result is None:
                    result = self._timeline_cue_edit(text)
                if result is None:
                    result = self._setlist_mode(text)
                if result is None:
                    result = self._song_design_interview(text)
                if result is None:
                    result = self._position_cue_store(text)
                if result is None:
                    result = self._look_pan_tilt(text)
                if result is None:
                    result = self._point_fixtures_at_target(text)
                if result is None:
                    result = self._position_mood_suggestion(text)
                if result is None:
                    result = self._repeating_type_columns_layout(text)
                if result is None:
                    result = self._typed_two_row_layout(text)
                if result is None:
                    result = self._multi_ring_circle_layout(text)
                if result is None:
                    result = self._vocabulary_layout(text)
                if result is None:
                    result = self._plain_language_design_request(text)
                if result is None:
                    # No canned clarifiers: an under-specified layout request
                    # (rings, alternation, shapes) goes to the model so it
                    # reasons about the WHOLE request and, if something is truly
                    # missing, asks one question at a time via ask_user — never a
                    # reflexive keyword-triggered line.
                    result = self._orchestrator.handle_instruction(
                        text,
                        history=tuple(self._history),
                        session_context=self._session_context_note(text),
                    )
            except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
                event = self._report_error(exc)
                self._record_history(text, event.get("message", ""))
                return event
            self._capture_last_created(result)
            views = [outcome_view(outcome) for outcome in result.command_outcomes]
            summary = self._compose_summary(result, views)
            if self._recorder is not None:
                self._recorder.turn_finished(retries_used=result.retries_used)
            event = chat_response_event(
                status=result.status, summary=summary, text=result.text, commands=views
            )
            self._send(event)
            self._record_history(text, result.text)
            return event
        finally:
            reset_session_key(token)

    def upload_vectorworks_export(self, file_name: str, content_base64: str) -> dict:
        """Replace this session's export and immediately start its guided analysis."""
        self._vectorworks_upload.replace(file_name, content_base64)
        return self.run_instruction(_VECTORWORKS_UPLOAD_INSTRUCTION)

    # -- internals ------------------------------------------------------------------

    def restore_history(self, messages: Sequence[Mapping[str, str]]) -> None:
        """Seed the rolling transcript from the client's persisted UI transcript.

        Refresh survival: the browser keeps the visible conversation in
        localStorage and reinjects it on (re)connect, so the model's cross-turn
        memory continues across a page refresh. Seeds a FRESH session only — a
        session that already holds live turns never lets a late or duplicate
        restore frame overwrite what actually happened here. Wire-level
        validation (roles, non-empty text, length caps) happened in
        ``parse_client_message``; the window cap is re-applied for defence.
        """
        if self._history:
            return
        for item in list(messages)[-HISTORY_MAX_MESSAGES:]:
            if item["role"] == "user":
                self._history.append(UserMessage(text=item["text"]))
            else:
                self._history.append(
                    ModelTurn(
                        text=item["text"],
                        tool_calls=(),
                        stop_reason="end",
                        usage=Usage(),
                        provider="history",
                    )
                )

    def _record_history(self, user_text: str, reply_text: str) -> None:
        """Append this turn's user instruction and assistant reply to memory.

        Only the user-visible exchange is kept — never the intermediate tool
        calls/results — so replaying it is cheap and re-feeds no console side
        effect. The window is trimmed from the front in whole pairs so the
        model never sees a user message stripped of its answer.
        """
        self._history.append(UserMessage(text=user_text))
        self._history.append(
            ModelTurn(
                text=reply_text or "",
                tool_calls=(),
                stop_reason="end",
                usage=Usage(),
                provider="history",
            )
        )
        excess = len(self._history) - HISTORY_MAX_MESSAGES
        if excess > 0:
            del self._history[:excess]

    def _capture_last_created(self, result: InstructionResult) -> None:
        """Snapshot the just-created look from this turn's SUCCESSFUL commands.

        Snapshot-only: a new creation replaces the prior value; a turn that
        creates nothing leaves the prior snapshot intact (so a later bare
        modification still anchors to the last real look)."""
        executed = [
            outcome.command
            for outcome in result.command_outcomes
            if outcome.status == "executed_ok"
        ]
        captured = parse_last_created(executed)
        if captured is not None:
            self._last_created = captured

    def _ask_one(
        self,
        prompt: str,
        *,
        options: tuple[QuestionOption, ...] = (),
        why: str = "",
        steps: tuple[str, ...] = (),
    ) -> str | None:
        """Ask the operator ONE question through the interactive card channel.

        This is how a direct handler collects a missing decision WITHOUT the
        wall-of-prose failure: the UI renders ``options`` as clickable buttons
        and always offers a free-text box, and the worker thread blocks here
        until exactly one answer returns — so a handler that needs several
        decisions calls this once per decision and the cards appear one at a
        time, never as a single unanswerable message.

        Returns the answer, or ``None`` when no UI is attached or the question
        went unanswered (timeout / disconnect) — the caller then falls back to
        a plain-text prompt instead of hanging.
        """
        if self._question_channel is None:
            return None
        answer = self._question_channel.ask(
            QuestionRequest(prompt=prompt, why=why, steps=steps, options=options)
        )
        if not isinstance(answer, str) or answer in ("", UNANSWERED):
            return None
        return answer

    def _session_context_note(self, text: str = "") -> str | None:
        """Cross-turn grounding plus reasoning aids for THIS instruction.

        ``text`` is the current instruction: recognized layout vocabulary is
        surfaced as guidance so the model REASONS about the whole request and
        asks any genuinely-missing parameter one at a time — replacing the old
        reflexive canned clarifier that fired on a keyword alone.
        """
        notes: list[str] = []
        last = self._last_created
        if last is not None and last.sequence is not None:
            target = f"Sequence {last.sequence}"
            if last.executor is not None:
                target += f" / Executor {last.executor}"
            notes.append(
                f"Session context — the last look you created is on {target}. "
                f'When the user asks to modify that look (e.g. "더 느리게" / make it '
                f"slower), apply the change to {target} — do NOT target an arbitrary "
                f"Sequence or Executor (such as Sequence 1 / Executor 1). Prefer "
                f"regenerating the look on {target} over blind-editing a different "
                f"target."
            )
        if self._last_layout_spacing is not None:
            row_gap, column_gap = self._last_layout_spacing
            notes.append(
                "Session context — the operator already set the layout spacing "
                f"this session: column gap {row_gap:g} m, fixture gap {column_gap:g} m. "
                "Reuse these for any follow-up placement (e.g. 나머지 장비도 배치해줘) "
                "instead of asking for spacing again; only ask for what is genuinely "
                "still missing."
            )
        if self._vectorworks_upload.content_base64 is not None:
            notes.append(
                "Session context — one Vectorworks export is uploaded for this "
                "conversation. Its bytes and any completed report are available only "
                "through vectorworks_autopatch; never request them in chat or infer "
                "details that tool did not report."
            )
        guidance = layout_terms_guidance(text)
        if guidance:
            notes.append(guidance)
        return "\n\n".join(notes) or None

    def _report_error(self, exc: Exception) -> dict:
        kind, message = classify_exception(exc)
        raw_detail = getattr(exc, "raw_detail", None) or repr(exc)
        provider_name = getattr(exc, "provider", "")
        self._audit.record(
            {
                "event": "provider_error",
                "kind": kind,
                "provider": provider_name,
                "raw_detail": raw_detail,
            }
        )
        if self._recorder is not None:
            self._recorder.turn_finished(retries_used=0, error=True)
        event = error_event(message=message, kind=kind)
        self._send(event)
        return event

    def _compose_summary(self, result: InstructionResult, views: list[dict]) -> str:
        parts: list[str] = []
        seen: set[str] = set()
        for decision in self._turn_decisions:
            line = _DECISION_SUMMARY.get(decision.status)
            if line and decision.status not in seen:
                seen.add(decision.status)
                parts.append(line)
        outcome_summary = summarize_outcomes(result.status, views)
        if outcome_summary:
            parts.append(outcome_summary)
        return " ".join(parts)
