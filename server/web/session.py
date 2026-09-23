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

import base64
import binascii
import contextlib
import copy
import hashlib
import inspect
import json
import os
import re
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path

from server.audio.analyze import AnalysisResult, analyze
from server.concept.session_bridge import build_concept_report
from server.deploy.review import ReviewRequest
from server.design import color_names as _COLOR_NAMES
from server.design.capability_verdict import position_verdict
from server.design.cue_density import plan_cue_density, rotate_palette
from server.design.cue_sheet_apply import (
    ConsoleApplyError,
    layer_mapping_from_console_groups,
    plan_console_apply,
    timeline_group_names,
)
from server.design.cue_sheet_edit import (
    CueSheetEditError,
    apply_cue_sheet_edit,
    parse_cue_sheet_edit_request,
)
from server.design.interview import (
    Q1_CONCEPT,
    Q2_PALETTE,
    Q2B_COLOR_USAGE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
    DirectorInterview,
    UnresolvedAnswer,
)
from server.design.profile import (
    DEFAULT_BPM,
    SOURCE_GLOBAL_DEFAULT,
    BpmResolution,
    DirectorOverride,
    MusicProfile,
    SectionMoodResolution,
    UnresolvedMood,
    parse_sheet_bpm,
    resolve_bpm,
    resolve_section,
)
from server.design.rig import _LAYER_GROUP_ALIASES, build_rig_profile
from server.design.rig_capability_read import (
    DesignRigRead,
    read_design_rig,
)
from server.design.rig_capability_read import (
    notice_for as rig_capability_notice,
)
from server.design.rig_preflight import plan_rig_preflight, render_rig_preflight

# 카드 t441 — 아래 다섯은 (재수출 전용, 이 파일 안에서는 안 쓴다 —
# `as <같은 이름>` 은 ruff 가 인식하는 명시 재수출 표시다. 값·동작은
# `server/design/section_palette.py` 로 옮긴 바이트 그대로이고, 기존 테스트가
# `server.web.session` 에서 이 이름들을 직접 import 하는 자리를 깨지 않기
# 위해서만 다시 가져간다(모듈 독스트링 참고).
from server.design.section_palette import _ACCENT_WEIGHT_LADDER as _ACCENT_WEIGHT_LADDER
from server.design.section_palette import (
    _ARC_PALETTE,
    _COLOR_WORDS,
    _extract_color_words,
    _palette_colors,
    _section_palette_choice,
)
from server.design.section_palette import _CHORUS_IDENTITY_ROLES as _CHORUS_IDENTITY_ROLES
from server.design.section_palette import _arc_accent_weight as _arc_accent_weight
from server.design.section_palette import _arc_palette as _arc_palette
from server.design.section_palette import _distinct_from_primary as _distinct_from_primary
from server.design.section_palette import _hue_key as _hue_key
from server.design.section_palette import _per_chorus_palette as _per_chorus_palette
from server.design.song_cue_composer import (
    SongCueCompositionResult,
    compose_song_cue_bundle,
    position_axis_disabled,
)
from server.design.song_plan import (
    COLOR_USAGE_AXIS,
    D_AXIS,
    FX_AXIS,
    MANUAL_GO,
    PALETTE_AXIS,
    POSITION_AXIS,
    TEXTURE_AXIS,
    AccentDecision,
    ApprovalState,
    CueSheetSectionFields,
    CueSheetViewFields,
    DirectorDecision,
    DisabledNote,
    DLevelDecision,
    FxDecision,
    GroupIntensity,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
    apply_cue_sheet_section,
    apply_cue_sheet_view,
)
from server.llm.types import LLMProvider, ModelTurn, ToolCall, Usage, UserMessage
from server.looks.instantiate import LookInstantiation
from server.looks.song_history import SongLookMemory
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
from server.lxseq.cue_parser import parse_cue_csv
from server.lxseq.parser import parse_patch_csv
from server.orchestrator.last_created import LastCreated, parse_last_created
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.spatial_memory import SpatialMemory
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    TIMECODE_POOL_PATH,
    CommandOutcome,
    DeployPipelinePort,
    ExecutionContext,
    build_toolset,
)
from server.orchestrator.write_reason import showfile_write_risk
from server.prechk.query import read_properties
from server.presets.store import preset_store_commands as _preset_store_commands
from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import (
    BatchRisk,
    SafetyGate,
    ScreenDecision,
    WriteGateDeclarationError,
)
from server.safety.monitor import HealthMonitor
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key
from server.sheets.registry import (
    HANDLER_TAG_SESSION_METHOD,
    OUTCOME_AMBIGUOUS,
    OUTCOME_RESOLVED,
    REGISTRY,
    discriminate,
)
from server.spatial.mib import PositionCuePlan, position_cue_bundle, premove_follow_command
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    FX_POSITION_SEQUENCE,
    POSITION_PRESET_POOL,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    basic_position_presets,
    fan_chain,
    fan_pan_tilt,
    fx_position_presets,
    pointing_commands,
    position_cue_store_commands,
    position_preset_store_commands,
    preset_recall_command,
    radial_pan_tilt,
)
from server.spatial.position_cuesheet import (
    PositionSheetSection,
    build_position_cue_sheet,
    required_sheet_labels,
)
from server.spatial.position_fx import position_fx_commands, required_position_labels
from server.spatial.position_moods import match_position_mood
from server.spatial.vocabulary import (
    layout_terms_guidance,
    match_explicit_layout,
    parse_ring_layout,
)
from server.web.approval_bridge import ApprovalChannel
from server.web.cue_monitor import parse_current_cue_index
from server.web.korean_errors import classify_exception
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    CONSOLE_INPUT_LISTENING,
    CONSOLE_INPUT_UNDETERMINED,
    answer_delta_event,
    approval_request_event,
    chat_response_event,
    error_event,
    execution_preview_event,
    notice_event,
    progress_event,
    proposal_event,
    question_request_event,
    review_request_event,
    song_timeline_event,
    status_event,
)
from server.web.preview import build_execution_preview
from server.web.question import (
    UNANSWERED,
    ConfirmedSongAnalysis,
    ConfirmedSongSection,
    QuestionChannel,
    QuestionOption,
    QuestionRequest,
    SongSectionProposal,
    build_song_confirmation_card,
    is_bpm_octave_apart,
    parse_confirmed_bpm,
    parse_confirmed_sections,
    section_label,
)
from server.web.reply_discovery import ReplyPortMismatch
from server.web.timeline_draft import TimelineDraftHistory
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
    # 패치 검증 전용(patch_fixtures) — 서버가 실행한 명령의 성공/실패가 아니라
    # 실행 뒤 재조회로 판정한 결과다. "실행 실패"로 내보내면 UI에서 "앱이
    # 실행했는데 실패했다"로 읽힌다(2026-08-18 실전 테스트에서 그렇게 읽혔다).
    #
    # 앱은 실행했다 — 0건인 첫 번째 원인은 실행 순간 콘솔의 명령 목적지가
    # 픽스처 계층이 아니었던 것이다(Patch 편집기 열림 여부). "직접 실행 필요"로
    # 쓰면 서버-실행 모델과 모순된다.
    "not_created": "생성 안 됨 (Patch 편집기를 연 뒤 재시도 필요)",
    "partially_created": "부분 생성 (자동 재시도 안 함)",
}

# Korean summary lines derived from gate bundle decisions (gate truth).
_DECISION_SUMMARY: dict[str, str] = {
    "blocked_console_offline": "콘솔 오프라인 상태입니다 — 신규 명령 실행이 차단되었습니다.",
    "blocked_responder_degraded": (
        "콘솔 응답기가 저하 상태입니다 — 결과 확인이 불가능하여 "
        "부수효과 명령을 시작하지 않았습니다."
    ),
    # 두 버전 사유를 갈라 적는다 — 낮은 버전은 재임포트로 끝나지만 미인식은
    # 무엇이 도는지 모른다는 뜻이므로 조사가 먼저다 (REQ-READBACK2-004).
    "blocked_responder_version_mismatch": (
        "콘솔 응답기 버전이 기대값과 다릅니다 — 응답기를 다시 임포트해 주세요."
    ),
    "blocked_responder_version_unrecognized": (
        "콘솔 응답기가 알 수 없는 버전을 보고했습니다 — 어떤 응답기가 로드돼 있는지 확인해 주세요."
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

# A patched body rotation smaller than this reads as "not rotated": console
# rotation strings are exact ("0.0"), so the tolerance only absorbs float
# parsing noise, never a real installation tilt.
_ROTATION_TOLERANCE_DEGREES = 0.01

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
# 2026-08-16 실측: [^,:]+ ran past the sentence into the next line ("블루와
# 화이트. 타임코드 7로 맞춰줘.\n0…" became the palette). Stop at comma, colon,
# PERIOD, or NEWLINE — a hint is one clause, never the rest of the brief.
_SONG_CONCEPT_HINT = re.compile(r"컨셉\s*(?:은|는)?\s*[:\-]?\s*(?P<concept>[^,:.\n]+)")
_SONG_PALETTE_HINT = re.compile(r"팔레트\s*(?:는|은)?\s*[:\-]?\s*(?P<palette>[^,:.\n]+)")
# DI5 "QN만 다시" 부분 재인터뷰: an interview-card answer carrying "Q<N> 다시"
# is never fed to the current step's parser (it would corrupt a free-text
# step like Q1/Q5) — it restarts from Q<N> instead, keeping every earlier
# answer intact (DirectorInterview.restart_from).
#
# SPEC-COPILOT-COLORMODE-001 D2 — Q2B_COLOR_USAGE inserted `STEP_ORDER[2]`
# meant "Q3 다시" would silently restart the wrong step if this regex's
# numeric group were still fed straight into `STEP_ORDER[N-1]` (research.md
# §2, session.py:8619 실측). The alternation below recognizes "Q2B" (and its
# Korean alias "색 운용") ahead of the plain "Q<1-5>" numeric form, and the
# call site resolves through the explicit `_SONG_RESTART_STEP_BY_TOKEN`
# lookup table instead of an implicit index.
_SONG_RESTART = re.compile(r"[Qq]\s*(?P<no>2[Bb]|[1-5])\s*(?:만)?\s*다시")
_SONG_RESTART_COLOR_USAGE = re.compile(r"색\s*운용\s*다시")

_SONG_RESTART_STEP_BY_TOKEN: dict[str, str] = {
    "1": Q1_CONCEPT,
    "2": Q2_PALETTE,
    "2b": Q2B_COLOR_USAGE,
    "3": Q3_CLIMAX,
    "4": Q4_SPATIAL_STORY,
    "5": Q5_TEXTURE,
}
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
    Q2B_COLOR_USAGE: COLOR_USAGE_AXIS,
    Q3_CLIMAX: D_AXIS,
    Q4_SPATIAL_STORY: POSITION_AXIS,
    Q5_TEXTURE: TEXTURE_AXIS,
}

_DI_STEP_LABELS: dict[str, str] = {
    Q1_CONCEPT: "Q1 컨셉",
    Q2_PALETTE: "Q2 팔레트",
    Q2B_COLOR_USAGE: "Q2B 색 운용",
    Q3_CLIMAX: "Q3 클라이맥스",
    Q4_SPATIAL_STORY: "Q4 공간 스토리",
    Q5_TEXTURE: "Q5 전환 방식",
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
    # 카드 t403 — 확정 구간(role 이 명시된 경로, t393)의 표시 이름은
    # "Chorus 1" 처럼 역할 어휘를 그대로 담는다(`_confirmed_section_names`).
    # 아래 텍스트 검색을 그대로 두면 그 이름 안의 "Chorus" 글자를 절정
    # 신호로 오독해 곡의 **첫** 코러스에서 멈춘다(실측: 141초 곡에서 3초
    # 지점). role 이 있으면 텍스트 검색을 건너뛰고 role + D 레벨로
    # 판정한다 — 코러스 후보 중 D 레벨이 가장 높은(동률이면 나중) 구간을
    # 고른다("마지막 drop" 이 정본 §6 의 최댓값이기 때문이다).
    if any(section.role is not None for section in sections):
        d_levels = [section.d_level if section.d_level is not None else 0 for section in sections]
        chorus_candidates = [
            index for index, section in enumerate(sections, start=1) if section.role == "chorus"
        ]
        if chorus_candidates:
            return max(chorus_candidates, key=lambda index: (d_levels[index - 1], index))
        finale_candidates = [
            index for index, section in enumerate(sections, start=1) if section.role == "finale"
        ]
        if finale_candidates:
            return finale_candidates[-1]
        return len(sections)
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


def _occurrence_accent_label(
    role: str, occurrence: int, total: int, *, is_final_occurrence: bool
) -> str | None:
    """정본 §7.1 사다리를 회차 수가 얼마든 일반화한다 (카드 t403).

    코러스가 25회 반복돼도 매 회차를 찍으면 "짧고 드물어야" 하는 액센트가
    흔해져 정본 §6.1 을 어긴다 — 감독이 원한 것은 "부분마다 변조"(팔레트,
    t402)이지 "부분마다 폭발"이 아니다. 그래서 몇 회든 딱 **가운데**
    회차(무빙 포지션 전환)와 **마지막** 회차(블라인더/백색 플래시)만
    찍는다. 피날레는 항상 곡에 한 번뿐이라(싱글턴, t391) 항상 마지막이다.
    """
    if role == "finale":
        return "white flash" if is_final_occurrence else None
    if role != "chorus" or total <= 1:
        return None
    if is_final_occurrence:
        return "white flash"
    midpoint = max(2, round(total / 2))
    return "moving position hit" if occurrence == midpoint else None


def _accent_decision(
    records: Sequence[object],
    *,
    section_index: int,
    climax_index: int,
    role: str = "other",
    occurrence: int = 1,
    total_for_role: int = 0,
    is_final_occurrence: bool = False,
) -> AccentDecision:
    if section_index == climax_index:
        q3 = _projection(records, Q3_CLIMAX)
        climax = getattr(q3, "climax", None)
        color = getattr(climax, "accent_color", None)
        if isinstance(color, str) and color.strip():
            return AccentDecision(accents=(f"climax accent {color}",), source="director_climax")
        return AccentDecision(accents=("climax accent",), source="director_climax")
    # 카드 t403 — 절정 하나뿐이던 액센트를 회차 사다리로 넓힌다. 절정이
    # 아닌 구간은 §7.1 사다리의 가운데·마지막 회차에서만 액센트가 난다.
    label = _occurrence_accent_label(
        role, occurrence, total_for_role, is_final_occurrence=is_final_occurrence
    )
    if label is not None:
        return AccentDecision(accents=(label,), source="section_arc")
    return AccentDecision()


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
#: 카드 t405 — 회차마다 효과를 바꾼다. 고치기 전 실측(main@611ce34, Club
#: Diver.mp3 를 앱 경로로 끝까지 태운 타임라인 39구간): 서로 다른 효과가 넷뿐이고
#: 그중 26구간이 바이트 동일한 ``dimmer chase`` 였다. 원인은 둘이다 — ``_ARC_FX``
#: 가 역할당 효과를 한 벌만 갖고, 감독 질감이 medium 이면 아래 ``[:1]`` 이 **항상
#: 0번**을 집는다. 이 곡은 39구간 중 25개가 chorus 라 그 한 줄이 곡을 덮는다.
#:
#: 처방은 색이 카드 t402 에서 한 것과 같은 축이다: 회차(occurrence)로 사다리를
#: 돈다. **회차 1은 위 ``_ARC_FX`` 의 값과 바이트 동일**이라 기존 룩은 안 바뀐다.
#: 효과 이름은 지어내지 않는다 — 전부 이 저장소가 이미 싣고 있는 FX 라이브러리
#: 항목의 말이다(``server/fx/library/{movement,dimmer,color}.yaml``):
#: horizontal chase→``chase-horizontal``, bounce chase→``chase-bounce-run``,
#: v-shape swing→``sweep-vshape-swing``(셋 다 카드 t372 가 넣고 이 곡에서 한
#: 번도 안 뽑히던 것), soft wave→``wave-soft-rise``, cross diagonal→
#: ``diagonal-club-cross``, orbit→``circle-relative-orbit``, breathing→
#: ``pulse-breath``.
#:
#: 🔴 여기 쓰는 말은 ``song_cue_composer._contains_any`` 가 ``_BLACKOUT_TOKENS``
#: (blackout/암전/…)와 ``_AUDIENCE_TOKENS``(audience/blinder/객석/…)로 되읽는다 —
#: 새 이름을 더할 때 그 토큰이 문자열 안에 들어가면 구간이 통째로 블랙아웃이나
#: 객석 조명으로 오판된다. 아래 이름은 어느 토큰도 포함하지 않는다.
_ARC_FX_LADDER: dict[str, tuple[tuple[str, ...], ...]] = {
    "intro": ((),),
    "verse": (("slow pan",), ("slow tilt",), ("soft wave",)),
    "chorus": (
        ("dimmer chase", "pan sweep"),
        ("horizontal chase", "pan sweep"),
        ("bounce chase", "v-shape swing"),
        ("cross diagonal", "dimmer chase"),
    ),
    "bridge": (("slow tilt",), ("orbit",), ("breathing",)),
    "finale": (("dimmer chase", "accent sweep"),),
}


def _arc_fx_allowed(role: str, occurrence: int) -> tuple[str, ...] | None:
    """이 회차가 쓸 효과 묶음. 사다리가 없는 역할이면 ``None`` (카드 t405).

    회차는 1부터 센다 — 1회차는 항상 사다리 0번, 즉 ``_ARC_FX`` 와 같은 값이다.
    """
    rungs = _ARC_FX_LADDER.get(role)
    if not rungs:
        return None
    return rungs[(max(occurrence, 1) - 1) % len(rungs)]


#: 카드 t396 — bridge 로 볼 수 있는 **절대** 상한. 정본 6절 표가 breakdown·bridge 를
#: 20~35% 대역에 두므로 D1·D2 만 해당한다. 이웃 대비(상대) 조건만 쓰면 두 방향으로
#: 틀렸다(실측 2026-09-15, 감독 음원 8곡): 밝은 D4 가 이웃보다 낮다는 이유로 bridge 가
#: 되고(5건), 낮은 구간이 둘 연속이면 서로가 서로의 이웃이 되어 조건이 깨져 verse 로
#: 남았다(4건). 절대 대역으로 바꾸면 두 방향이 함께 닫힌다 — t371·t375 가 같은 계열의
#: 실수를 상대 문턱에 절대 대역을 섞어 고친 그 처방이다.
_BRIDGE_MAX_D_LEVEL = 2


def _infer_confirmed_role(index: int, d_levels: Sequence[int]) -> str:
    """오디오 확정 구간 하나의 아크 역할을 D 레벨만으로 추정한다 (카드 t393).

    이름·무드가 비어 있어 ``_section_role`` 의 자연어 판독이 닿지 않는 구간을
    위한 대체 판정기다. ``_ARC_D_LEVEL``(intro 2 · verse 3 · chorus 5 ·
    bridge 2 · finale 5)의 역표를 그대로 따른다: 첫 구간은 intro, 마지막
    구간은 finale, 최고 D 레벨 구간은(동률 허용) chorus, :data:`_BRIDGE_MAX_D_LEVEL`
    이하의 낮은 대역은 bridge, 나머지는 verse. 순전히 서수·측정값 기반이라 무드
    단어를 지어내지 않는다.

    bridge 판정은 **절대 대역**이다(카드 t396). 이웃 대비만 보던 앞선 규칙은 밝은
    구간을 bridge 로 오인하고 연속 저강도 구간을 놓쳤다 — 근거는
    :data:`_BRIDGE_MAX_D_LEVEL` 주석의 실측이다.
    """
    count = len(d_levels)
    if count == 0:
        return "other"
    if index == 0:
        return "intro"
    if index == count - 1:
        return "finale"
    level = d_levels[index]
    if level >= max(d_levels):
        return "chorus"
    if level <= _BRIDGE_MAX_D_LEVEL:
        return "bridge"
    return "verse"


#: 카드 t391 — 역할 → 표시 이름 앞머리. 콘솔 큐 목록이 이미 쓰는 어휘
#: (Intro / Verse N / Chorus N / Bridge N / Finale, 감독 실측)와 맞춘다.
#: `_infer_confirmed_role` 이 내는 역할 5종만 다루면 되므로 "other" 는
#: 방어적으로만 존재한다 — 확정 구간 경로에서는 나오지 않는다.
_CONFIRMED_ROLE_DISPLAY_NAME: dict[str, str] = {
    "intro": "Intro",
    "verse": "Verse",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "finale": "Finale",
    "other": "Section",
}

#: 이 역할은 곡에 한 번뿐이라 뒤에 회차 번호를 붙이지 않는다 — "Intro 1" 은
#: 감독 화면의 콘솔 큐 이름(Intro / Verse 1 / Verse 2 / ...)과 다른 어휘가
#: 된다.
_CONFIRMED_ROLE_SINGLETON = frozenset({"intro", "finale"})


def _confirmed_section_names(roles: Sequence[str]) -> list[str]:
    """오디오 확정 구간의 표시 이름 — 역할 + 회차 번호 (카드 t391).

    고침 전: 이름이 전부 중립 ASCII ``S<n>`` 이라 곡 하나에 같은 라벨이
    중복됐다(실측: 17개 라벨 중 8번째·9번째가 둘 다 ``S8`` — 마디 분할이
    한 구간을 두 큐로 쪼개면서 부모 이름을 그대로 물려받았기 때문). 콘솔의
    큐 목록은 같은 화면에서 ``Intro / Verse 1 / Verse 2 / Chorus 1 ...``
    처럼 역할+회차로 감독이 하나를 짚을 수 있게 이름 붙인다 — 이 함수는
    확정 구간에도 같은 어휘를 쓴다.

    ``dynamics``(D 레벨)는 이 이름과 **무관한 경로**로 전달된다
    (``_confirmed_section_input`` 의 ``dynamics`` 키, ``_map_section_to_look``
    이 명시 dynamics 를 이름보다 먼저 본다) — 그래서 이름을 "Chorus 1" 로
    바꿔도 D 레벨 판정을 우회하지 않는다(plan.md §C D5 가 지키려던 것과
    같은 불변식).

    지시문이 직접 구간을 적은 경로(``section_names``)는 이 함수를 타지
    않는다 — 그 경로는 이미 감독이 준 이름이 정본이다.
    """
    occurrence: dict[str, int] = {}
    names: list[str] = []
    for role in roles:
        prefix = _CONFIRMED_ROLE_DISPLAY_NAME.get(role, role.title() or "Section")
        if role in _CONFIRMED_ROLE_SINGLETON:
            names.append(prefix)
            continue
        occurrence[role] = occurrence.get(role, 0) + 1
        names.append(f"{prefix} {occurrence[role]}")
    return names


def _disambiguate_split_names(names: Sequence[str], source_origins: Sequence[int]) -> list[str]:
    """마디 분할로 한 구간이 여러 큐로 갈리면 라벨을 서로 다르게 만든다
    (카드 t391). ``plan_cue_density`` 는 시작 시각만 갈라 주고 이름은 부모
    구간 것을 그대로 물려주므로(``replace(sections[split.source_index], ...)``
    이 ``name`` 은 안 바꾼다), 같은 이름이 연달아 여러 번 나올 수 있다 —
    이 함수가 그 자리에만 회차 접미사(" (2/2)" 형태)를 붙인다. 쪼개지지
    않은 구간(부모당 큐 하나)의 이름은 바이트 그대로 둔다.
    """
    counts: dict[int, int] = {}
    for origin in source_origins:
        counts[origin] = counts.get(origin, 0) + 1
    seen: dict[int, int] = {}
    disambiguated: list[str] = []
    for name, origin in zip(names, source_origins, strict=True):
        total = counts[origin]
        if total <= 1:
            disambiguated.append(name)
            continue
        seen[origin] = seen.get(origin, 0) + 1
        disambiguated.append(f"{name} ({seen[origin]}/{total})")
    return disambiguated


# Direct positional intent inside one section's own wording. Ordered: an
# audience mention wins over a generic "퍼지/넓혀" in the same sentence.
_DIRECT_POSITION_INTENTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"보컬|vocal|솔로|한\s*명|시선.*모", re.IGNORECASE), ("Vocal DSC",)),
    (re.compile(r"객석|관객|audience|블라인더", re.IGNORECASE), ("Audience",)),
    (re.compile(r"넓혀|넓어지|넓게|확장|폭.*넓|퍼지", re.IGNORECASE), ("Fan Out",)),
    (re.compile(r"비워|비운|비어|고립|미니멀", re.IGNORECASE), ("Wall",)),
)


def _section_role(section: PositionSheetSection, *, section_index: int, section_count: int) -> str:
    # 카드 t393 — 오디오 확정 구간은 이름/무드가 비어(중립 ASCII·빈 문자열) 아래
    # 자연어 판독이 항상 "other" 로 떨어진다. 명시 role 이 실려 있으면(구간
    # 확정 경로가 t393 처방으로 채운 값) 그 값을 최우선으로 쓴다 — d_level 이
    # 명시 필드로 전역 기본값 우회를 푼 것과 같은 처방(position_cuesheet.py 참조).
    if section.role is not None:
        return section.role
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
        label=label, source="section_arc", notes=(f"감독 전환 방식 기준: {base.label}",)
    )


def _section_fx_decision(
    *,
    section: PositionSheetSection,
    section_index: int,
    climax_index: int,
    section_count: int,
    records: Sequence[object],
    occurrence: int = 1,
) -> FxDecision:
    base = _fx_decision(records)
    role = _section_role(section, section_index=section_index, section_count=section_count)
    arc = _ARC_FX.get(role)
    if arc is None:
        return base
    _, density = arc
    # 카드 t405 — 묶음은 회차 사다리에서, 축 개수(density)는 ``_ARC_FX`` 에서.
    # 사다리 칸은 전부 같은 길이라 density 는 회차와 무관하게 그대로다.
    allowed = _arc_fx_allowed(role, occurrence) or arc[0]
    if base.density <= 0:
        # Director asked for a calm texture — the arc never re-enables FX.
        return FxDecision(allowed=(), source="section_arc", disabled=allowed, density=0)
    if base.density == 1 and density > 1:
        # 감독 질감이 medium 이면 축이 하나로 깎인다. 예전에는 여기서 **항상**
        # 0번을 집어 회차 사다리가 통째로 지워졌다(실측: 26구간이 같은 효과).
        # 회차가 고른 묶음의 첫 축을 그대로 남겨 사다리를 살린다.
        allowed, density = allowed[:1], 1
    return FxDecision(allowed=allowed, source="section_arc", density=density)


#: 카드 t441 — 아크 팔레트 회전(`_hue_key`·`_distinct_from_primary`·
#: `_ACCENT_WEIGHT_LADDER`·`_arc_accent_weight`·`_CHORUS_IDENTITY_ROLES`·
#: `_arc_palette`·`_per_chorus_palette`)은 `server/design/section_palette.py`
#: 로 옮겼다 — 경로 B(`prepare_songcue`)가 같은 함수로 같은 색을 내려면
#: `server/web/session.py` 밖에 있어야 했다. 값·동작은 바이트 그대로이고
#: 이름은 위 import 로 다시 가져와 그대로 쓴다.


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


# 페이저 자동 제안(T12) — 곡 설계 섹션 큐의 역할 텍스트에서 고신뢰 쌍만
# 제안한다(코디네이터 매핑 표, 보수적). ``cue.cue_name``은 ``song_plan.
# CuePayload.cue_name == section.label == section.name``(디자인 인터뷰가
# 부여한 섹션 원문 이름) — session.py의 ``_section_role`` 역할 판별기가
# 쓰는 것과 같은 어휘를 재사용한다. '최고 에너지(드롭/후렴 피크 상당)'와
# '후렴'을 가르기 위해 기존 ``_SONG_CLIMAX_SECTION``(후렴|드롭|클라이맥스|
# 피크를 하나로 뭉뚱그림)을 두 갈래로 세분화했다 — 드롭/클라이맥스/피크
# 어휘가 있으면 최고 에너지, 없이 '후렴'만 있으면 일반 후렴이다.
# ``cue.d_level``(1-5)은 이 판별에 쓰지 않는다 — ``_ARC_D_LEVEL``에서
# chorus=finale=5로 같은 값을 공유해 최고 에너지/후렴/피날레를 구별할
# 신호가 못 된다(추측 금지 — 확인 결과는 worker_done에 보고). 매칭되지
# 않는 나머지 전부(인트로 포함)는 None — 정적 유지가 안전 기본값이다.
_PHASER_PEAK_SECTION = re.compile(r"드롭|클라이맥스|피크|drop|climax|peak", re.IGNORECASE)
_PHASER_CHORUS_SECTION = re.compile(r"후렴|chorus", re.IGNORECASE)


def _phaser_label_for_cue(cue) -> str | None:
    """섹션 큐 → 카탈로그 페이저 라벨 제안, 없으면 None(정적 유지 = 안전).

    MIB pre-move(``kind != 'section'``)는 어두운 순간의 순수 이동 큐라
    제외한다 — 페이저는 보이는 연출이므로 암전 이동에 실을 이유가 없다.
    블랙아웃 큐(``dimmer.blackout`` 또는 key_pct 없음/0)도 제외한다 —
    페이저 recall이 프로그래머 Dimmer 값을 되살려 의도한 암전을 깰 수
    있다(``_back_layer_value_lines``와 같은 안전 규율, key_pct<=0 가드).
    """
    if cue.kind != "section":
        return None
    if cue.dimmer.blackout or not cue.dimmer.key_pct or cue.dimmer.key_pct <= 0:
        return None
    name = cue.cue_name or ""
    if _PHASER_PEAK_SECTION.search(name):
        return "Drop Slam"
    if _PHASER_CHORUS_SECTION.search(name):
        return "Wave CM"
    if _SECTION_ROLE_BRIDGE.search(name):
        return "Breathe Cool"
    if _SECTION_ROLE_FINALE.search(name):
        return "Finale Slam"
    if _SECTION_ROLE_VERSE.search(name):
        return "Breathe Warm"
    return None


def _phaser_cue_value_lines(
    cue, fids: Sequence[int], phaser_slots: Mapping[str, tuple[int, int]]
) -> tuple[str, ...]:
    """제안된 페이저의 recall 한 줄(T11 §2 문법) — 슬롯 미해석이면 빈 튜플.

    ``position_cue_bundle``의 ``extra_value_lines``에 얹힌다: 플랜 자신의
    포지션/디머 라인 **뒤**에 온다(``_reviewed_song_commands`` 호출부),
    그래서 콤보/디머 페이저의 디머 스텝이 큐의 정적 key_pct를 프로그래머
    last-wins 규칙으로 정확히 덮어쓴다(계약 #5 순서 규율). recall이 멀티스텝
    페이저를 통째로 싣는 것은 **2026-08-19 실기 육안 확인**됐다(Drop Slam
    발사 → 조명이 페이저로 재생, 13번 프로브 §확인 기록). [잔여 ASSUMPTION —
    T11 프로브 §4] 이 recall을 담아 **저장한 큐**가 프리셋 참조를 보존하는지
    (참조 vs 평탄화)는 여전히 프로토콜로 판독 불가 — 곡 큐 재생의 육안
    확인이 남은 마지막 조각이다.
    """
    label = _phaser_label_for_cue(cue)
    if label is None:
        return ()
    resolved = phaser_slots.get(label)
    if resolved is None:
        return ()
    pool_no, slot = resolved
    return (_preset_recall_command(pool_no, fids, slot),)


#: recall 적재는 2026-08-19 실기 육안 확인으로 종결(Drop Slam 발사 → 페이저
#: 재생 관측, 13번 프로브 §확인 기록). T16의 MEMORYFOOTPRINT 부정 정황(1741 <
#: 2104)은 recall→재저장 경로의 저장 크기에 관한 것이었고 라이브 재생과는
#: 별개임이 판명됐다. [잔여 ASSUMPTION — T11 프로브 §4] 저장된 **큐**가
#: 프리셋 참조를 보존하는지(참조 vs 평탄화)는 여전히 판독 불가 — 리뷰
#: 시트는 이 잔여분만 고지한다.
_PHASER_REVIEW_ASSUMPTION_NOTE = (
    "페이저 제안은 승인 후 실기 슬롯을 조회해 배정합니다(못 찾으면 그 큐는 "
    "페이저 없이 진행). recall이 페이저를 싣는 것은 실기 확인됐고(2026-08-19), "
    "저장된 큐가 그 참조를 보존하는지는 판독할 수 없어 ASSUMPTION입니다 — "
    "곡 큐 재생은 콘솔 화면에서 직접 확인해 주세요."
)


def _phaser_failure_note(failures: Mapping[str, str]) -> str:
    """계약 #4 — 슬롯 미해석 페이저는 곡 설계를 무산시키지 않되, 사유를
    최종 회신에 반드시 노출한다(추측 없이 정직한 강등 고지)."""
    if not failures:
        return ""
    return " 페이저 미배정: " + "; ".join(failures.values()) + "."


def _color_failure_note(failures: Mapping[str, str]) -> str:
    """색 미해소는 곡 설계를 무산시키지 않되, 사유를 최종 회신에 노출한다.

    `_phaser_failure_note` 와 같은 관행 — 지어내지 않고 정직하게 강등을
    고지한다. 값이 없는 색 이름("gold"·"warm special" 등)은
    `server/design/color_names.py` 가 일부러 비워 둔 자리다.
    """
    if not failures:
        return ""
    return " 색 미반영: " + "; ".join(failures.values()) + "."


def _song_color_value_lines(
    cue, fids: Sequence[int], w_fids: frozenset[int] = frozenset()
) -> tuple[tuple[str, ...], str | None]:
    """SPEC-LDDESIGN-001 M2 — 큐의 팔레트 주색을 콘솔 값 라인으로 낸다.

    ``(값 라인들, 실패 사유 또는 None)``. **고치기 전 실측**: 감독 확정
    경로는 색을 한 줄도 보내지 않았다(`reports/lddesign-m2-cue-path/`)
    — 설계층은 팔레트를 들고 있는데 명령 생성기가 떨어뜨렸다.

    주색만 낸다. 보조색·유보색·언더페인팅은 M3(컬러 규칙)의 몫이고,
    이 자리에서 지어내면 그 규칙이 도착했을 때 두 출처가 생긴다.

    MIB 사전이동 큐(``kind == "mib_premove"``)는 건너뛴다 — 어둠 속 이동
    큐라 색 값이 공연에 보이지 않고, 사전에 색까지 얹을지는 아직 안 잰
    별도 판단이다.

    카드 t430 — ``w_fids``(W 채널 확인 기구, 기본 빈 집합)에 든 fid는
    ``fids``에서 빼고 별도 줄로 낸다: 오늘과 같은 R/G/B 줄에
    ``Attribute 'ColorRGB_W' At 0``을 이어붙인다. 값은 0 고정이다 — 이
    카드는 무대 색을 바꾸지 않는다(어느 흰색을 W로 낼지는 리드 결정
    대기, `.moai/reports/t430/verdict.md` §3). W 없이 부르면(``w_fids``
    빈 집합) 오늘과 바이트 동일하다. W 라인 없는 기구 목록이 비면 그
    줄은 아예 안 낸다.
    """
    if cue.kind != "section":
        return (), None
    palette = cue.color.palette
    if not palette:
        return (), None
    name = palette[0]
    rgb = _COLOR_NAMES.resolve_color_name(name)
    if rgb is None:
        return (), f"Q{cue.cue_number:g} {cue.cue_name!r}의 색 {name!r}은 표준 팔레트 10색에 없음"
    if not w_fids:
        return (_color_apply_command(fids, rgb),), None
    rgb_only_fids = [fid for fid in fids if fid not in w_fids]
    w_only_fids = [fid for fid in fids if fid in w_fids]
    lines: list[str] = []
    if rgb_only_fids:
        lines.append(_color_apply_command(rgb_only_fids, rgb))
    if w_only_fids:
        lines.append(_color_apply_command(w_only_fids, rgb) + " ; Attribute 'ColorRGB_W' At 0")
    return tuple(lines), None


def _back_layer_value_lines(cue, layer_mapping: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """결함 6 후속 (priority 6): Front/Back 분리 연출 — the director-confirmed
    'back' role group adds ONE group-addressed dimmer line to every LIT
    section cue, at 80% of the key level (the same key→back ratio the
    composer's layered-rig path uses). The group NUMBER is console-addressable
    without membership knowledge (RG5 — fids are never claimed); blackouts and
    MIB pre-moves stay untouched. The line comes AFTER the all-fixture key
    dimmer, so the console's last-wins programmer order lowers only the back
    group."""
    back_no = next(
        (
            entry["group_no"]
            for entry in layer_mapping
            if entry.get("role") == "back" and isinstance(entry.get("group_no"), int)
        ),
        None,
    )
    if back_no is None or cue.kind != "section":
        return ()
    key_pct = cue.dimmer.key_pct
    if key_pct is None or key_pct <= 0:
        return ()
    back_pct = cue.dimmer.back_pct if cue.dimmer.back_pct is not None else key_pct * 0.8
    return (f"Group {back_no} ; Attribute 'Dimmer' At {back_pct:g}",)


#: The placeholder title `_build_unified_song_plan` stamps on a fresh design —
#: auto-snapshots fall back to the sequence name instead of versioning it.
_DESIGN_INTERVIEW_TITLE = "Design Interview"

#: 카드 t311 — 좌표 판독이 실패한 **두 갈래**. 문면이 아니라 코드다:
#: 조준 핸들러와 곡 디자인이 같은 실패에 서로 다른 문장을 쓴다.
_COORD_GAP_UNREADABLE = "unreadable"
_COORD_GAP_TRUNCATED = "truncated"

#: 좌표 없는 리그에 디자인을 요청했을 때 감독이 읽는 한 줄. 「무엇을 못 만들었고
#: 왜인지」만 말한다 — 지어낸 좌표도, 지어낸 포지션도 내지 않는다는 규칙의 관측
#: 가능한 면(카드 t277 의 고지와 같은 결).
_COORD_GAP_NOTICES: dict[str, str] = {
    _COORD_GAP_UNREADABLE: (
        "3D 좌표를 읽지 못해 포지션(무브) 축은 만들지 못했습니다 — "
        "조도·컬러 큐만 설계했습니다. 콘솔 연결과 패치를 확인해 주세요."
    ),
    _COORD_GAP_TRUNCATED: (
        "3D 좌표 응답이 잘리거나 조회 한도에 도달해 포지션(무브) 축은 "
        "만들지 못했습니다 — 조도·컬러 큐만 설계했습니다."
    ),
    #: 판독은 성공했는데 좌표가 확인된 장비가 0대인 경우(패치 없는 리그).
    "empty": (
        "좌표가 확인된 장비가 없어 포지션(무브) 축은 만들지 못했습니다 — "
        "조도·컬러 큐만 설계했습니다."
    ),
}

#: 카드 t344 — 픽스처 타입 라이브러리 경로. ``orchestrator.tools`` 의
#: ``rig_paths["fixture_types"]`` 와 같은 값이며, 여기서 리터럴을 두 번 쓰는 대신
#: 상수로 둔다(경로 리터럴이 흩어지면 한 곳만 고쳐진다).
_FIXTURE_TYPES_ROOT = "Patch/FixtureTypes"

#: 리그 전체가 팬/틸트 하나도 없을 때 감독이 읽는 줄. 좌표 결손과 **다른 사실**이라
#: 문면을 따로 둔다: 좌표는 「어디에 있는지 모른다」, 이쪽은 「돌릴 수 있는 장비가
#: 없다」다.
_NO_POSITIONABLE_NOTICE = (
    "팬/틸트를 가진 장비가 리그에 없어 포지션(무브) 축은 만들지 못했습니다 — "
    "조도·컬러 큐만 설계했습니다."
)


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
# 저장 대상 시퀀스 변경 (2026-08-16): "시퀀스 320으로 변경/바꿔/옮겨" — 점유된
# 슬롯이 Store를 'Not allowed'로 거부했을 때 계획을 버리지 않고 옮기는 어휘.
_PLAN_EDIT_SEQUENCE = re.compile(
    r"시퀀스\s*(?P<no>\d+)\s*(?:번)?\s*(?:으로|로)\s*(?:변경|바꿔|바꾸|옮겨|옮기|저장|이동)"
)

# 리허설 편집 (handoff 2026-08-15 priority 5): "지금 이 큐"/"현재 큐" names the
# cue the console is PLAYING right now — no cue number in the instruction.
_REHEARSAL_EDIT_REQUEST = re.compile(r"(?:지금|현재)\s*(?:이|나가는|재생\s*중인)?\s*큐")

# 셋리스트 모드 (handoff 2026-08-15 priority 4): allocate the library's songs
# to consecutive setlist sequences (210, 220, …) and page-1 executors (101~).
_SETLIST_REQUEST = re.compile(r"셋\s*리스트|set\s*list", re.IGNORECASE)

#: t291 — 초안을 콘솔로 보내라는 요청. 「저장」(라이브러리)과 어휘가 갈린다:
#: 저장에는 콘솔이 없고, 반영에는 콘솔이 있다.
_DRAFT_APPLY_REQUEST = re.compile(
    r"콘솔[에은는]?\s*(반영|적용|전송|올려|보내)|초안\s*(을|를)?\s*(반영|적용)"
)

#: t295 — 위 술어는 콘솔과 동사가 **붙어** 있어야 맞는다. 실측(2026-09-06):
#: 「이 곡 큐시트를 콘솔 시퀀스 3에 올려줘」는 사이에 「시퀀스 3에」가 끼어
#: 안 맞고, 「올려」가 `cue_sheet_edit._BRIGHTER` 에 걸려 **조도 편집**으로
#: 갔다 — 감독은 데스크에 보냈다고 믿는데 아무것도 안 나가고, 요청하지 않은
#: 조도가 움직인다. 두 방향 중 더 위험한 쪽이다.
#:
#: 그래서 인접을 요구하는 대신 축을 둘로 나눈다: **목적지**와 **보내는 동사**가
#: 문장 안에 함께 있으면 반영이다. 인접은 요구하지 않는다.
_DRAFT_APPLY_DESTINATION = re.compile(r"콘솔|데스크|초안|시퀀스\s*\d+")
_DRAFT_APPLY_VERB = re.compile(r"반영|적용|전송|송출|올려|올리|보내")

#: t301 — 위 동사 중 **보내기 전용**인 것들. 「올려/올리」만 빠져 있다: 그 둘은
#: 조도를 올리는 뜻을 겸해 곡 브리핑 안의 연출 지시로도 나온다.
_DRAFT_APPLY_SEND_ONLY_VERB = re.compile(r"반영|적용|전송|송출|보내")

#: 「올려/올리」는 두 뜻을 겸한다 — 데스크에 올리는 것과 조도를 올리는 것.
#: 올리는 **대상이 큐시트 칸**이면 편집이므로 반영에서 뺀다. 이 축이 없으면
#: 「시퀀스 3의 큐 2 조도 올려줘」가 반영으로 새고, 그 방향은 조용히 틀린다
#: (감독이 고친 줄 아는 칸이 안 고쳐진다).
_DRAFT_APPLY_EDIT_OBJECT = re.compile(
    r"(조도|밝기|인텐시티|레벨|딤|페이드)\s*(를|을)?\s*\d*\s*%?\s*(더\s*)?(올려|올리|높여)"
)


#: 부정. 「아직 콘솔에는 적용하지 말고 …」는 반영 요청이 아니라 그 반대다.
_DRAFT_APPLY_NEGATED = re.compile(
    r"(반영|적용|전송|송출|올려|올리|보내)\S*\s*(하)?지\s*(는)?\s*(말|마)"
)

#: 반영 명령의 길이·줄 수 한도. 축을 넓히면서 실측된 회귀(2026-09-06)가 이
#: 한도의 근거다: 곡 설계 브리핑 한 건이 「시퀀스 110」(목적지)과 「조금
#: 올리고」(동사)를 함께 갖고 있어 반영으로 새면서 설계 인터뷰가 깨졌다.
#: 한 지시를 던지는 반영 문장은 짧다(코퍼스 최장 22자); 브리핑은 길다(그
#: 회귀 문장 197자). 경계 40자는 t290 편집 판별기와 같은 값으로 맞췄다.
#:
#: 넘치면 **거짓**을 답해 사슬로 흘려보낸다 — 콘솔 쓰기 쪽으로 닫는 방향이다.
_DRAFT_APPLY_MAX_CHARS = 40


def _is_draft_apply_request(text: str) -> bool:
    """이 문장이 「초안을 콘솔로 보내라」인가.

    참이 되는 조건은 여섯이다: (a) 설계 요청이 아니고, (b) 목적지가 있고,
    (c) 보내는 동사가 있고, (d) 올리는 대상이 큐시트 칸이 아니고, (e) 그 동사가
    부정되지 않았고, (f) 한 줄·40자 이내다. 하나라도 어긋나면 거짓이고, 문장은
    기존 라우트 사슬(편집·설계 인터뷰 …)로 그대로 흘러내린다.
    """
    stripped = text.strip()
    # 카드 t301 — 짧은 설계 브리핑이 길이 한도를 통과한다. 실측(t298):
    # 「시퀀스 110에 90초 록 곡 설계, 후렴에서 조금 올리고」 32자가 목적지
    # (시퀀스 110)와 동사(올리고)를 함께 들고 있어 반영으로 샜다. 길이는 이
    # 계열을 막을 축이 아니었다 — 긴 변형만 우연히 걸렸을 뿐이다. 새는 방향은
    # 감독의 설계 요청이 설계되는 대신 반영 거절을 답으로 받는 것이다.
    #
    # 그래서 설계 어휘 하나로 통째로 빼지는 **않는다**. 「곡 설계한 거 콘솔에
    # 반영해줘」는 진짜 반영이고, 그것까지 빼면 t295 가 닫은 더 위험한 방향
    # (데스크에 보냈다고 믿는데 아무것도 안 나간다)이 다시 열린다. 가르는 축은
    # **어느 동사가 그 문장을 반영으로 만들었나**다: 「올려/올리」는 데스크에
    # 올리는 뜻과 조도를 올리는 뜻을 겸해서 브리핑 안의 연출 지시로도 나오지만,
    # 「반영·적용·전송·송출·보내」는 브리핑이 쓸 일이 없는 보내기 전용 말이다.
    # 설계 요청이면서 보내기 전용 동사가 하나도 없으면 반영이 아니다.
    if (
        _SONG_DESIGN_REQUEST.search(stripped) is not None
        and _DRAFT_APPLY_SEND_ONLY_VERB.search(stripped) is None
    ):
        return False
    if len(stripped) > _DRAFT_APPLY_MAX_CHARS or "\n" in stripped:
        return False
    if _DRAFT_APPLY_NEGATED.search(stripped) is not None:
        return False
    if _DRAFT_APPLY_EDIT_OBJECT.search(stripped) is not None:
        return False
    if _DRAFT_APPLY_DESTINATION.search(stripped) is None:
        return False
    return _DRAFT_APPLY_VERB.search(stripped) is not None


#: t303 — 「쇼 전에 이름이 맞는지 봐 달라」. 읽기 전용 사전 점검 요청.
#:
#: 축은 둘이고 **함께** 있어야 한다: 점검 대상(리그·그룹 이름·주소·반영 전)과
#: 점검 동사(점검·확인). 한 축만으로는 안 받는다 — 「확인」은 흔한 말이라
#: 대상 없이 받으면 아래 사슬의 라우트들을 앞에서 가로챈다.
#:
#: 「프리플라이트/preflight」는 그 자체로 대상+동사라 단독으로 받는다.
_RIG_PREFLIGHT_SUBJECT = re.compile(r"리그|그룹\s*이름|그룹|주소|반영\s*전|쇼\s*전")
_RIG_PREFLIGHT_VERB = re.compile(r"점검|사전\s*확인|맞는지\s*확인|확인해")
_RIG_PREFLIGHT_LITERAL = re.compile(r"프리\s*플라이트|preflight", re.IGNORECASE)

#: 점검은 **보내는 말**과 섞이면 안 된다. 「콘솔에 반영하고 확인해줘」는 반영이지
#: 점검이 아니다 — 보내기 전용 동사가 있으면 이 라우트는 비켜선다(반영이 받는다).
_RIG_PREFLIGHT_BLOCKED_BY_SEND = re.compile(r"반영해|적용해|전송|송출|보내")


def _declared_slot_number(value: object) -> int | None:
    """타임라인이 **선언한** 풀 슬롯 번호. 0·None·문자열은 「번호 없음」이다.

    0 을 슬롯 0 으로 읽으면 사전 점검이 엉뚱한 자리를 재게 된다 — 시드 타임라인이
    ``sequence_number: 0`` 을 들고 온다(t303 실측).
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _is_rig_preflight_request(text: str) -> bool:
    """이 문장이 「쇼 전 리그 점검」인가.

    거짓이면 문장은 기존 라우트 사슬로 그대로 흘러내린다 — 이 술어는 새 문을
    열 뿐 기존 문의 판정을 바꾸지 않는다.
    """
    stripped = text.strip()
    if _RIG_PREFLIGHT_BLOCKED_BY_SEND.search(stripped) is not None:
        return False
    if _RIG_PREFLIGHT_LITERAL.search(stripped) is not None:
        return True
    if _RIG_PREFLIGHT_VERB.search(stripped) is None:
        return False
    return _RIG_PREFLIGHT_SUBJECT.search(stripped) is not None


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


def _section_arc_geometry(
    sections: Sequence[PositionSheetSection],
    section_origin: Sequence[int] | None,
) -> tuple[list[int], list[int], list[int], int, int]:
    """쪼갠 큐 목록을 **원래 구간** 기준의 아크 좌표로 되돌린다 (카드 t305).

    한 구간이 여러 큐로 갈려도 연출 아크(role · D 계단 · texture · FX)는
    구간 단위로 그대로여야 한다 — 정본의 Q020·Q030 은 둘 다 VERSE1 이고,
    구간이 둘로 갈렸다고 절정 위치가 옮겨 가지는 않는다.

    돌려주는 것은 큐마다 하나씩: 아크 위치(1-based), 그 구간을 여는 큐의
    번호(1-based, 재질의·미해소 보고가 쓰는 키), 구간 안에서 몇 번째
    큐인지(0 = 여는 큐), 그리고 원래 구간 수와 절정 구간 번호.

    ``section_origin`` 이 없거나 길이가 안 맞으면(계획 편집이 구간을
    넣거나 뺀 뒤) 항등으로 되돌아간다 — 쪼개기 전과 바이트 동일.
    """
    count = len(sections)
    origins = (
        list(section_origin)
        if section_origin is not None and len(section_origin) == count
        else list(range(count))
    )
    arc_positions: list[int] = []
    head_indexes: list[int] = []
    units: list[int] = []
    head_by_origin: dict[int, int] = dict()
    position_by_origin: dict[int, int] = dict()
    for offset, origin in enumerate(origins):
        if origin not in head_by_origin:
            head_by_origin[origin] = offset + 1
            position_by_origin[origin] = len(position_by_origin) + 1
        arc_positions.append(position_by_origin[origin])
        head_indexes.append(head_by_origin[origin])
        units.append(offset + 1 - head_by_origin[origin])
    originals = [sections[head_by_origin[origin] - 1] for origin in position_by_origin]
    return (
        arc_positions,
        head_indexes,
        units,
        len(position_by_origin),
        _climax_section_index(originals),
    )


def _section_palette_sizes(
    sections: Sequence[PositionSheetSection],
    *,
    profile: MusicProfile,
    palette_mode: str,
    concept_colors: tuple[str, ...],
    color_usage: str = "modulate",
) -> list[int]:
    """구간별 팔레트 색 수 — 쪼갠 큐가 서로 달라질 수 있는지의 판정 재료.

    감독 재질의 답변(``requery_overrides``)은 아직 없는 시점이라 여기서는
    보지 않는다. 오버라이드는 색을 **더하는** 쪽이므로 이 값은 실제보다
    작거나 같다 — 즉 이 판정은 덜 쪼개는 쪽으로만 틀린다. 같은 큐 둘을
    내는 것보다 안 쪼개는 쪽이 낫다는 카드의 방향과 같다.

    ``color_usage`` — SPEC-COPILOT-COLORMODE-001. 실제 산출(`_section_palette_choice`)
    과 어긋나지 않도록 여기도 같은 값을 전달한다(research.md §6).
    """
    count = len(sections)
    sizes: list[int] = []
    for index, section in enumerate(sections, start=1):
        role = _section_role(section, section_index=index, section_count=count)
        resolved = resolve_section(section.mood, profile, director_intent=None)
        tendency = getattr(resolved, "color_tendency", "white")
        colors, _source, _weight = _section_palette_choice(
            section,
            role=role,
            profile=profile,
            color_tendency=tendency,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            color_usage=color_usage,
        )
        sizes.append(len(colors))
    return sizes


def _split_sections_for_density(
    sections: Sequence[PositionSheetSection],
    *,
    profile: MusicProfile,
    palette_mode: str = "palette",
    concept_colors: tuple[str, ...] = (),
    color_usage: str = "modulate",
) -> tuple[list[PositionSheetSection], list[int], tuple[str, ...]]:
    """구간 목록을 마디 경계에서 쪼갠 큐 목록으로 넓힌다 (카드 t305).

    돌려주는 것은 (넓힌 구간 목록, 큐마다의 원래 구간 번호, 공개할 사유).
    BPM 이 선언되지 않았으면 입력이 그대로 나온다 — 오늘과 동일.

    카드 t391 — 한 구간이 여러 큐로 갈리면(``plan.splits`` 에서 같은
    ``source_index`` 가 둘 이상) 부모 이름을 그대로 물려받아 라벨이
    중복됐다(실측: 17개 라벨 중 8번째·9번째가 둘 다 ``S8``). 이름이
    바뀌는 구간은 쪼개진 자리에 한해서만이고, 쪼개지지 않은 구간의
    이름은 바이트 그대로 둔다(``_disambiguate_split_names``).
    """
    plan = plan_cue_density(
        [section.start_ms for section in sections],
        bpm=profile.bpm,
        meter=profile.meter,
        palette_sizes=_section_palette_sizes(
            sections,
            profile=profile,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            color_usage=color_usage,
        ),
    )
    source_origins = list(plan.source_origins)
    names = _disambiguate_split_names(
        [sections[split.source_index].name for split in plan.splits], source_origins
    )
    expanded = [
        replace(sections[split.source_index], start_ms=split.start_ms, name=name)
        for split, name in zip(plan.splits, names, strict=True)
    ]
    return expanded, source_origins, plan.notes


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
    section_origin: Sequence[int] | None = None,
    position_disabled_reason: str = "",
) -> UnifiedSongLightingPlan:
    arc_positions, head_indexes, units, section_count, climax_index = _section_arc_geometry(
        sections, section_origin
    )
    # 카드 t402·t403 — 역할이 같은 구간이 반복될 때(코러스 25회 등) 몇 번째
    # 회차인지 미리 센다. 원본(origin) 단위로 세야 한다 — 마디 분할로 갈린
    # 큐는 부모와 같은 회차를 공유해야, 부모가 이미 정한 팔레트 회전·액센트
    # 사다리가 자식 큐에서 흔들리지 않는다. `head_indexes[i] == i+1` 인
    # 자리(``units[i] == 0``)만 새 원본의 시작이다.
    origin_roles: dict[int, str] = {}
    for offset, section in enumerate(sections, start=1):
        if units[offset - 1] == 0:
            arc_index = arc_positions[offset - 1]
            origin_roles[head_indexes[offset - 1]] = _section_role(
                section, section_index=arc_index, section_count=section_count
            )
    role_totals: dict[str, int] = {}
    for role_name in origin_roles.values():
        role_totals[role_name] = role_totals.get(role_name, 0) + 1
    role_running: dict[str, int] = {}
    occurrence_by_head: dict[int, int] = {}
    for head in sorted(origin_roles):
        role_name = origin_roles[head]
        role_running[role_name] = role_running.get(role_name, 0) + 1
        occurrence_by_head[head] = role_running[role_name]
    # SPEC-COPILOT-COLORMODE-001 — Q2B_COLOR_USAGE decision, read once for
    # the whole plan (default "modulate" when unanswered, matching modulate
    # being the interview's recommended/first option).
    color_usage = _record_value(records, Q2B_COLOR_USAGE, "modulate")
    decisions: list[SectionDecision] = []
    unresolved: list[UnresolvedNote] = []
    roles: list[str] = []
    for index, section in enumerate(sections, start=1):
        arc_index = arc_positions[index - 1]
        head_index = head_indexes[index - 1]
        unit_index = units[index - 1]
        role = _section_role(section, section_index=arc_index, section_count=section_count)
        roles.append(role)
        # 카드 t402·t403 — 이 원본(head_index)이 자기 역할 안에서 몇 번째
        # 회차인지(사전 계산한 표에서 조회), 그 역할의 총 회차 수, 그리고
        # 그것이 **마지막** 회차인지.
        occurrence = occurrence_by_head.get(head_index, 1)
        total_for_role = role_totals.get(role, 0)
        is_final_occurrence = occurrence == total_for_role
        override = _section_director_override(
            section_index=arc_index,
            section_count=section_count,
            records=records,
            climax_index=climax_index,
        )
        # Priority (결함 4): 구간 재질의 답변 > 구간 직접 자연어 의도 > Q3/Q4.
        merged = (requery_overrides or {}).get(head_index)
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
            # 한 구간을 여러 큐로 쪼갰어도 감독에게는 카드가 **한 번** 떠야
            # 한다 — 같은 구간의 같은 무드를 큐 수만큼 되묻는 것은 잡음이다.
            if unit_index == 0:
                unresolved.append(
                    UnresolvedNote(
                        axis=POSITION_AXIS,
                        section_index=head_index,
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
        # 카드 t383 — 확정 분석이 잰 D 레벨(``section.d_level``)은 아직 아무도
        # 결정하지 않은 구간에서만 기본값을 채운다. 무드 단어나 감독 답변
        # (Q3 절정 포함, ``resolve_section`` 이 이미 SOURCE_DIRECTOR_INTENT 로
        # 최우선 처리했다)이 이미 정했으면 그 값을 덮지 않는다 — 여기서
        # 고치는 것은 「비어서 전역 기본값(D3)으로 떨어진」 구간뿐이다.
        if section.d_level is not None and d_source in (SOURCE_GLOBAL_DEFAULT, "fallback"):
            d_level, d_source = section.d_level, "confirmed_song_analysis"
        arc_d = _ARC_D_LEVEL.get(role)
        if arc_d is not None and d_source in (SOURCE_GLOBAL_DEFAULT, "fallback"):
            d_level, d_source = arc_d, "section_arc"
        # Palette: section's own color words > palette-conflict choice > Q2
        # palette blended with the role arc.
        palette_colors, palette_source, palette_weight = _section_palette_choice(
            section,
            role=role,
            profile=profile,
            color_tendency=resolved.color_tendency,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            occurrence=occurrence,
            color_usage=color_usage,
        )
        # 카드 t305 — 구간 안에서 이어지는 큐는 앞 큐와 **달라야** 한다.
        # 정본이 하는 것과 같은 축: 강도는 유지하고 색만 돌린다(Q060 "강도
        # 유지, 색만 교체" · Q140 "색상만 순환"). 색이 하나뿐인 구간은
        # 애초에 쪼개지지 않으므로(`plan_cue_density`) 여기서 같은 큐가
        # 나오는 일은 없다.
        # 카드 t398 — 회전은 이미 고른 색을 순서만 바꾼다(원소 추가 없음), 그래서
        # `palette_source` 는 **덮어쓰지 않는다**. 예전에는 여기서
        # "cue_density_rotation" 으로 갈아끼웠는데, 그러면 L5 가 아크 악센트인지
        # 감독 문구인지 구분할 근거(원래 출처)를 잃는다 — 이 리터럴은 코드베이스
        # 전체에서 이 한 줄이 유일한 생산자였다(다른 소비자 없음, grep 확인).
        if unit_index > 0:
            rotated = rotate_palette(palette_colors, unit_index)
            if rotated != palette_colors:
                palette_colors = rotated
        decisions.append(
            SectionDecision(
                section=TimestampedSection(
                    index=index,
                    label=section.name,
                    start_ms=section.start_ms,
                    source="song_design_interview",
                ),
                d=DLevelDecision(level=d_level, source=d_source),
                palette=PaletteDecision(
                    colors=palette_colors, source=palette_source, weight=palette_weight
                ),
                position=PositionDecision(
                    preset=position,
                    source=resolved.position_source,
                    candidates=resolved.position_candidates,
                ),
                texture=_section_texture_decision(
                    section=section,
                    section_index=arc_index,
                    climax_index=climax_index,
                    section_count=section_count,
                    records=records,
                ),
                fx=_plan_edit_fx(
                    _section_fx_decision(
                        section=section,
                        section_index=arc_index,
                        climax_index=climax_index,
                        section_count=section_count,
                        records=records,
                        occurrence=occurrence,
                    ),
                    (fx_overrides or {}).get(index),
                ),
                accent=_accent_decision(
                    records,
                    section_index=arc_index,
                    climax_index=climax_index,
                    role=role,
                    occurrence=occurrence,
                    total_for_role=total_for_role,
                    is_final_occurrence=is_final_occurrence,
                ),
                cue_number=index,
                fade_override=(fade_overrides or {}).get(index),
                role=role,
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
    # 카드 t311 — 좌표가 없으면 포지션 축은 **전곡** 비활성이다(구간별이 아니라).
    # 이 노트 하나가 작곡기·리뷰·타임라인 셋 모두의 판별기가 된다 — 축을 끈
    # 사실과 그 사유가 한 곳에만 적힌다.
    if position_disabled_reason:
        disabled = (*disabled, DisabledNote(axis=POSITION_AXIS, reason=position_disabled_reason))
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


_REVIEW_TRIGGER_LABELS = {
    "go": "수동 Go",
    "manual": "수동 Go",
    "manual_go": "수동 Go",
    "time": "큐 타임 자동",
    "trig_time": "큐 타임 자동",
    "follow": "Follow 자동",
    "timecode": "타임코드",
}


def _review_timing_label(timing: dict) -> str:
    mode = str(timing.get("mode") or "")
    if mode == "timecode":
        return f"타임코드 {timing.get('timecode_number')}번 슬롯 자동 진행"
    if mode == "trig_time":
        return "큐 타임 자동 진행"
    if mode == "manual_go":
        return "수동 Go"
    return mode or "미정"


def _review_lint_line(finding) -> str:
    """One check finding in field language — L5 (팔레트 이탈) gets a Korean
    template with the colors pulled out; unknown rules keep the raw
    description (honesty over polish)."""
    if finding.rule_id == "L5":
        colors = re.search(r"\[(.*?)\]", finding.description)
        color_text = colors.group(1).replace("'", "") if colors else finding.description
        if finding.cue_number:
            return f"큐 {finding.cue_number:g}: 팔레트 밖 포인트 컬러({color_text})"
        return f"팔레트 색 수 초과({color_text})"
    return f"{finding.rule_id} 큐 {finding.cue_number:g}: {finding.description}"


def _review_disabled_lines(composition, *, layer_mapped: bool = False) -> list[str]:
    """Known internal notes translated to one field-language line each,
    deduped; unknown notes pass through verbatim. ``layer_mapped`` reflects
    the SESSION's director-confirmed group mapping — the rig-profile note
    only knows the structural rig (patch=[], RG5), so without this flag the
    review said '레이어 매핑 없음' on a bundle that HAD Group-addressed back
    lines (실기 2026-08-16 관측)."""
    lines: list[str] = []
    for raw in [f"{note.rule_id}: {note.reason}" for note in composition.disabled_rule_notes] + [
        note.reason for note in composition.disabled_plan_notes
    ]:
        if "no mapped key/back layer" in raw or "degrades to single-layer" in raw:
            line = (
                "레이어 매핑 사용 — Back 그룹 디머 분리 적용(키 대비 80%). "
                "자동 체크 L6·L7은 그룹 멤버십을 읽을 수 없어 미적용"
                if layer_mapped
                else "레이어 매핑 없음 — 단일 레이어로 진행 (키/백 분리 체크 L6·L7 미적용)"
            )
        else:
            line = raw
        if line not in lines:
            lines.append(line)
    return lines


def _review_text(
    plan: UnifiedSongLightingPlan,
    composition: SongCueCompositionResult,
    *,
    layer_mapped: bool = False,
) -> str:
    cue_lines: list[str] = []
    any_phaser_proposed = False
    # 카드 t311 — 축이 꺼졌을 때의 빈 칸은 「포지션 유지」가 아니다. 그 말은
    # 감독이 고른 결과처럼 읽히는데, 여기서는 고른 적이 없다.
    empty_position = "포지션 불가(좌표 없음)" if position_axis_disabled(plan) else "포지션 유지"
    if composition.bundle is not None:
        for cue in composition.bundle.cues:
            trigger = _REVIEW_TRIGGER_LABELS.get(
                str(cue.timing.trigger).casefold(), str(cue.timing.trigger)
            )
            phaser_label = _phaser_label_for_cue(cue)
            phaser_note = f" · 페이저 제안: {phaser_label}" if phaser_label else ""
            if phaser_label:
                any_phaser_proposed = True
            cue_lines.append(
                f"큐 {cue.cue_number:g} {cue.cue_name} — D{cue.d_level} · "
                f"{cue.position.stored or empty_position} · "
                f"{'/'.join(cue.color.palette) or '컬러 유지'} · {trigger}{phaser_note}"
            )
    if not composition.lint_findings:
        lint = "자동 체크 통과"
    else:
        lint = "확인 포인트 {}건: {}".format(
            len(composition.lint_findings),
            "; ".join(_review_lint_line(finding) for finding in composition.lint_findings),
        )
        if any(finding.rule_id == "L5" for finding in composition.lint_findings):
            lint += " — 구간 무드/컨셉에서 더해진 색입니다. 의도한 포인트면 그대로 승인하세요"
    disabled_lines = _review_disabled_lines(composition, layer_mapped=layer_mapped)
    disabled = "" if not disabled_lines else " 참고: " + "; ".join(disabled_lines) + "."
    unresolved = (
        ""
        if not composition.requery_requirements
        else " 재질의 필요: "
        + "; ".join(requirement.prompt for requirement in composition.requery_requirements)
        + "."
    )
    timing = plan.timing.to_dict()
    timeline = "\n".join(cue_lines) if cue_lines else "저장 가능한 큐 없음"
    phaser_caveat = f" {_PHASER_REVIEW_ASSUMPTION_NOTE}" if any_phaser_proposed else ""
    return (
        f"전곡 리뷰 번들 — {plan.sequence_name.replace('Sequence', '시퀀스')} · "
        f"진행 {_review_timing_label(timing)}.\n"
        f"{timeline}\n{lint}.{unresolved}{disabled}{phaser_caveat}"
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


# ---------------------------------------------------------------------------
# LX-SEQ 큐시트 확장 생산자 (t283 -- t279 가 연 필드를 실제로 채운다)
#
# t279 는 모델 계층만 넓혔고 채우는 자리가 없었다. 여기가 그 자리다. 원칙 하나:
# **없는 것보다 틀린 것이 나쁘다.** 파이프라인이 이미 들고 있는 값에서 나오지
# 않는 필드는 채우지 않는다 -- 키 자체가 안 나간다.
#
# 지금 채우지 못하는 것과 그 이유는 아래 각 헬퍼의 주석에 적어 뒀다.

#: `4/4` 꼴의 박자표에서 마디당 박수를 읽는다. 못 읽으면 없음 -- 추측하지 않는다.
_METER_PATTERN = re.compile(r"\s*(\d+)\s*/\s*(\d+)\s*\Z")

#: 타임코드가 음원 대조로 **측정**된 구간임을 뜻하는 `TimestampedSection.source`
#: 값들. 오늘 이 파이프라인의 생산자는 `song_design_interview`(연출 인터뷰가
#: 받아 적은 시각)와 `song_timeline` 뿐이라 어느 것도 여기 없다 -- 그래서 오늘
#: 나가는 값은 항상 `DERIVED` 다. 음원 온셋에서 구간을 만드는 생산자가 생기면
#: 그 source 이름을 여기 더하는 것만으로 `MEASURED` 가 나간다.
_MEASURED_SECTION_SOURCES: frozenset[str] = frozenset({"confirmed_song_analysis"})

_TC_METHOD_MEASURED = "MEASURED"
_TC_METHOD_DERIVED = "DERIVED"
_TC_METHOD_DERIVED_WARNING = (
    "이 타임라인의 타임코드는 연출 인터뷰가 받아 적은 구간 시각에서 계산한 값입니다. "
    "음원 청취로 검증하지 않았습니다 — 픽업·하프바 삽입이 있으면 전 구간이 어긋납니다. "
    "리허설에서 대조하십시오."
)


def _song_beats_per_bar(meter: object) -> int | None:
    match = _METER_PATTERN.fullmatch(str(meter or ""))
    if match is None:
        return None
    beats = int(match.group(1))
    return beats if beats > 0 else None


def _song_seconds_per_bar(profile: MusicProfile) -> float | None:
    """한 마디의 초. **선언된** BPM 이 있을 때만 낸다.

    `effective_bpm` 을 쓰지 않는 것이 요점이다 -- 그 프로퍼티는 BPM 이 없으면
    기본값 120 을 답하므로, 그 값으로 마디를 계산해 내보내면 재지 않은 템포가
    실측처럼 보인다.
    """
    if profile.bpm is None:
        return None
    beats = _song_beats_per_bar(profile.meter)
    if beats is None:
        return None
    return beats * 60.0 / float(profile.bpm)


def _song_tc_method(plan: UnifiedSongLightingPlan) -> str:
    """구간 시각의 출처를 보고 정직하게 답한다.

    한 구간이라도 측정이 아닌 출처에서 왔으면 타임라인 전체가 `DERIVED` 다 --
    섞인 것을 `MEASURED` 라고 부르면 그 한 구간이 조용히 어긋난다.
    """
    if all(decision.section.source in _MEASURED_SECTION_SOURCES for decision in plan.sections):
        return _TC_METHOD_MEASURED
    return _TC_METHOD_DERIVED


def _song_cue_sheet_view_fields(plan: UnifiedSongLightingPlan) -> CueSheetViewFields:
    """타임라인 헤더 확장분.

    못 채우는 것: `total_duration_ms`·`bar_count`(곡 전체 길이를 아는 생산자가
    없다 -- 마지막 구간의 끝을 아무도 안 준다), `tc_source`·`tc_origin`(콘솔
    타임코드 출처와 0점 기준은 이 경로에 안 들어온다), `palette_legend`(룩
    라이브러리가 팔레트에 **이름**을 달지 않는다 -- 색값만 있고 `P1 골드앰버`
    같은 이름이 없어서 지어내지 않는다).
    """
    profile = plan.music_profile
    method = _song_tc_method(plan)
    return CueSheetViewFields(
        bpm=profile.bpm,
        time_signature=profile.meter,
        musical_key=profile.key_mode,
        seconds_per_bar=_song_seconds_per_bar(profile),
        tc_method=method,
        tc_method_warning=(_TC_METHOD_DERIVED_WARNING if method == _TC_METHOD_DERIVED else None),
    )


def _song_cue_sheet_section_fields(
    decision: SectionDecision,
    *,
    next_start_ms: int | None,
    cue: object | None,
    seconds_per_bar: float | None,
    layer_mapping: Sequence[Mapping[str, object]],
    manual_go: bool,
    position_disabled: bool = False,
) -> CueSheetSectionFields:
    """구간 하나의 큐시트 확장분.

    못 채우는 것: `mood`(연출 인터뷰의 시트 구간이 들고 있지만 계획으로 넘어올
    때 떨어진다 -- `TimestampedSection` 에 자리가 없다), `note`(구간별 메모를
    담는 필드가 계획에 없다).
    """
    section = decision.section
    end_ms = section.end_ms if section.end_ms is not None else next_start_ms
    duration_ms = (
        end_ms - section.start_ms if end_ms is not None and end_ms > section.start_ms else None
    )

    bar_start: int | None = None
    bar_count: int | None = None
    if seconds_per_bar:
        # 1-based -- 악보와 같은 셈. 구간이 마디 경계에 안 떨어지면 반올림이고,
        # 그 사실은 헤더의 `tc_method: DERIVED` 가 이미 말하고 있다.
        bar_start = int(round(section.start_ms / 1000.0 / seconds_per_bar)) + 1
        if duration_ms is not None:
            bar_count = int(round(duration_ms / 1000.0 / seconds_per_bar))

    intensity: list[GroupIntensity] = []
    movement: str | None = None
    effect: str | None = None
    trans: str | None = None
    fade_seconds: float | None = None
    lit = False
    if cue is not None:
        key_pct = cue.dimmer.key_pct
        back_pct = cue.dimmer.back_pct
        if key_pct is not None:
            intensity.append(GroupIntensity(group="KEY", level=int(round(key_pct))))
        if back_pct is not None:
            intensity.append(GroupIntensity(group="BACK", level=int(round(back_pct))))
        lit = key_pct is not None and key_pct > 0
        # 카드 t311 — 축이 꺼졌으면 `requested` 로도 되돌아가지 않는다. 그 값은
        # 무드 표가 낸 후보일 뿐이고, 앉힐 장비가 없는 이상 큐시트 MOVE 칸에
        # 적는 순간 지어낸 포지션이 된다.
        movement = None if position_disabled else (cue.position.stored or cue.position.requested)
        effect = " + ".join(cue.fx.permitted) or None
        fade_seconds = cue.fade_seconds
        # SNAP 은 페이드 0 이라는 사실 그대로다. 정본 어휘의 XFADE 는 내보내지
        # 않는다 -- 이 파이프라인은 크로스페이드와 단순 페이드를 구분하지 않아서,
        # 둘 중 하나를 고르면 그것은 계산이 아니라 추측이다.
        trans = "SNAP" if fade_seconds == 0 else "FADE"

    # 이 큐가 **그룹 번호로 지목하는** 콘솔 그룹. `_back_layer_value_lines` 와
    # 같은 조건이다: 불이 켜진 구간 큐에만 back 역할 그룹 줄이 붙는다.
    fixture_groups = (
        tuple(
            str(entry["group_name"])
            for entry in layer_mapping
            if entry.get("role") == "back" and entry.get("group_name")
        )
        if lit
        else ()
    )

    palette = decision.palette.colors
    return CueSheetSectionFields(
        end_ms=end_ms,
        duration_ms=duration_ms,
        bar_start=bar_start,
        bar_count=bar_count,
        # 룩 라이브러리에 팔레트 **이름**이 없다. 가진 것은 색값뿐이라 그것을
        # 그대로 싣는다 -- `P4 핫핑크` 같은 이름은 지어내지 않는다.
        palette_primary=palette[0] if palette else None,
        palette_secondary=palette[1] if len(palette) > 1 else None,
        intensity=tuple(intensity),
        fixture_groups=fixture_groups,
        movement=movement,
        effect=effect,
        trans=trans,
        fade_seconds=fade_seconds,
        manual=True if manual_go else None,
    )


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
    color_usage: str = "modulate",
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
    # t283 -- 큐시트 확장분. 구간 큐를 index 로 집어 와야 `fade_seconds` 말고도
    # 조도·무브·이펙트를 같이 읽는다(위의 `fade_by_section` 은 이제 이 사전의
    # 부분집합이지만, 기존 동작을 건드리지 않으려고 그대로 둔다).
    cue_by_section = (
        {
            cue.section_index: cue
            for cue in bundle.cues
            if cue.kind == "section" and cue.section_index is not None
        }
        if bundle is not None
        else {}
    )
    # 카드 t311 — 포지션 축이 꺼진 큐시트의 POSITION 칸은 **빈다**. 사유는
    # `disabled` 노트와 `warnings` 가 들고 있어, 빈 칸이 「모르겠다」가 아니라
    # 「못 만들었고 이유는 이것」으로 읽힌다.
    position_disabled = position_axis_disabled(plan)
    seconds_per_bar = _song_seconds_per_bar(plan.music_profile)
    manual_go = plan.timing.mode == MANUAL_GO
    start_ms_by_index = [decision.section.start_ms for decision in plan.sections]
    return apply_cue_sheet_view(
        {
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
                apply_cue_sheet_section(
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
                        "position": "" if position_disabled else decision.position.preset,
                        "texture": decision.texture.label,
                        "fx": list(decision.fx.allowed),
                        "fade_seconds": fade_by_section.get(decision.section.index),
                        "accents": list(decision.accent.accents),
                        "mib": decision.section.index in mib_section_indexes,
                        "trig_time_seconds": (
                            decision.section.start_seconds if plan.timing.uses_trig_time else None
                        ),
                        # 카드 t387 — 「왜 이렇게 만들었는지」 설명 리포트의 재료. 값은
                        # 이미 내보내고 있었지만 출처(source)는 버려지고 있었다 --
                        # `SectionDecision` 이 이미 갖고 있는 필드를 흘려보내지
                        # 않던 통로를 여는 것뿐, 새로 지어내는 값이 아니다.
                        "d_source": decision.d.source,
                        "palette_source": decision.palette.source,
                        # 카드 t406 핫픽스 — 채도/무게는 색 문자열이 아니라 여기로만
                        # 나른다(코디네이터 지시). UI 는 아직 이 키를 읽지 않는다 —
                        # 화면 표시가 필요해지면 그건 별도 카드다.
                        **(
                            {"palette_accent_weight": decision.palette.weight}
                            if decision.palette.weight
                            else {}
                        ),
                        "position_source": decision.position.source,
                        **(
                            {"position_candidates": list(decision.position.candidates)}
                            if decision.position.candidates
                            else {}
                        ),
                        "texture_source": decision.texture.source,
                        **({"role": decision.role} if decision.role else {}),
                    },
                    _song_cue_sheet_section_fields(
                        decision,
                        next_start_ms=(
                            start_ms_by_index[order + 1]
                            if order + 1 < len(start_ms_by_index)
                            else None
                        ),
                        cue=cue_by_section.get(decision.section.index),
                        seconds_per_bar=seconds_per_bar,
                        layer_mapping=layer_mapping,
                        manual_go=manual_go,
                        position_disabled=position_disabled,
                    ),
                )
                for order, decision in enumerate(plan.sections)
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
            # 카드 t439 — SPEC-LDDESIGN-001 M6 §④b. 컨셉 v2 파이프라인(13게이트·
            # MIB·린트/에너지)을 이 곡에 대해 돌려 부가 정보로 붙인다. ADDITIVE 다
            # — 오늘 콘솔로 나가는 명령은 위에서 이미 다 결정됐고 이 키는 그 뒤에
            # 붙을 뿐이다. 실패해도(`build_concept_report` 는 예외를 밖으로 안
            # 낸다, `server/concept/session_bridge.py` 독스트링) `available:
            # False` 로 계속 진행된다.
            "concept_report": build_concept_report(plan, color_usage=color_usage),
        },
        _song_cue_sheet_view_fields(plan),
    )


def _song_trig_time_token(start_ms: int) -> str:
    seconds, millis = divmod(start_ms, 1000)
    if millis == 0:
        return str(seconds)
    return f"{seconds}.{millis:03d}".rstrip("0")


#: `Store Sequence <n> Cue <m> …` — 큐 저장 한 줄.
_SONG_STORE_CUE = re.compile(r"^Store Sequence \d+ Cue (\d+(?:\.\d+)?)\b")
#: `Store Timecode <n>` — 타임코드 슬롯 쓰기 한 줄.
_SONG_STORE_TIMECODE = re.compile(r"^Store Timecode (\d+)\b")


# @MX:ANCHOR: [AUTO] `_song_finalize` 의 번들 위험 선언 문면을 만드는 유일한 자리
# @MX:REASON: 감독이 읽고 수락/거절을 정하는 문장이다(REQ-BULKGATE-007). 숫자는
#   **나갈 명령 자체**에서 읽는다 — 계획(state.timing)에서 읽으면 계획과 번들이
#   갈릴 때 카드가 사실과 다른 것을 말한다. 문면은 `prepare_songcue` 가 이미
#   출하한 어휘를 그대로 잇는다(tools.py `songcue_risk`).
def _song_write_risk_reason(sequence_no: int, commands: Sequence[str]) -> str:
    """이 번들이 쇼파일에 무엇을 하는지 — 시퀀스·큐 수·타임코드 슬롯·복원 부재."""
    cues = {matched.group(1) for line in commands if (matched := _SONG_STORE_CUE.match(line))}
    slots = [matched.group(1) for line in commands if (matched := _SONG_STORE_TIMECODE.match(line))]
    timecode = f"Timecode {slots[0]} 슬롯을 씁니다" if slots else "타임코드 슬롯은 쓰지 않습니다"
    return (
        f"쇼파일 쓰기 — Sequence {sequence_no} 에 큐 {len(cues)}건을 저장하고 "
        f"{timecode} "
        "(이 앱에는 시퀀스·타임코드 복원 경로가 없습니다)."
    )


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
                f"Sequence readback timed cue {cue_label}의 큐 타임(TrigTime)이 "
                f"{expected.trig_time}이 아닙니다: {trig_time!r}"
            )
    return None


def _validate_song_timecode_readback(payload: object, timecode_number: int) -> str | None:
    if not _song_readback_object_present(payload):
        return f"Timecode readback 응답에 Timecode {timecode_number} 객체가 없습니다."
    return None


#: 프리셋 **신규 저장** 동사 — 일곱 계열이 공유한다. '설정'·'세팅'은 2026-08-19
#: 실측으로 들어왔다: «포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을
#: 설정하고 …» 문장이 사전 핸들러 22개 중 **하나도** 매치하지 못해 LLM으로
#: 빠졌다. 조명감독은 「저장」만 쓰지 않는다 — 「깔아줘」·「구성해줘」·
#: 「준비해줘」·「등록해줘」·「채워줘」가 현장 어법이라 함께 받는다.
#:
#: `(?<!재)`는 재생성 의도(재설정·재세팅·재구성·재등록)가 신규 저장으로
#: 끌려오는 것을 막는다 — 두 흐름이 동사를 공유하므로 이 룩비하인드가 없으면
#: 「재구성해줘」가 저장 카드로 간다. 재생성 어휘 확장은 이번 범위 밖이라
#: 그 문장들은 오늘과 같은 경로(LLM)에 그대로 남는다.
_PRESET_STORE_VERB = (
    r"(?:저장|만들|잡아|생성|깔아|깔자|채워|넣어|올려"
    r"|(?<!재)(?:설정|세팅|구성|준비|등록))"
)

#: 디머 축 표기·동의어. '딤머'·'딜머'는 실측된 사용자 표기다 — 오타 하나가 축을
#: 바꿔버리면(포지션 트리거의 일반 명사 '프리셋'을 타고) 운영자가 요청한 적 없는
#: 풀에 10칸이 저장된다. 표기 누락은 오타가 아니라 결함이므로 저장·재생성 양쪽
#: 트리거에 같은 조각을 쓴다. 「밝기」·「광량」·「인텐시티」는 같은 축을 가리키는
#: 현장 어휘다.
_DIMMER_AXIS_WORD = r"(?:디머|딤머|딜머|dimmer|밝기|광량|인텐시티|intensity)"

#: 포지션이 **아닌** 축 명사들 — 포지션 트리거의 오라우팅 가드에 쓴다.
_NON_POSITION_AXIS_NOUN = r"(?:컬러|색|color|콤보|combo|복합|드롭|" + _DIMMER_AXIS_WORD + r")"

# The ten-basic-positions request: build the canonical position sequence for
# THIS rig and store it as consecutive Position presets, asking for the first
# preset number when the instruction does not carry one.
#
# 오라우팅 가드(2026-08-19 실측): 명사 대안의 '프리셋'은 일반 명사라 다른 축
# 문장까지 삼킨다 — «기본 딤머 프리셋 저장해줘»가 **포지션** 프리셋 10종을
# 만들었다. 그래서 다른 축 명사(컬러/디머/콤보/복합/드롭 계열)가 문장에 있고
# 포지션 명사(포지션/position)는 없으면 포지션 계열로 판정하지 않는다.
#
# 가드는 문장 **전체**를 봐야 한다 — 축 명사가 '기본'보다 앞에 오는 문장이
# 실재한다(«포지션, 컬러, 딤머의 기본 프리셋 …»). 그래서 트리거를 `\A`에 묶고
# 선행부를 `.*?`로 흘린다. 매치 오프셋을 읽는 호출자는 없다 —
# `_basic_position_presets`는 `search(...) is None`만 본다.
_BASIC_POSITIONS_REQUEST = re.compile(
    r"\A(?:(?=.*(?:포지션|position))|(?!.*" + _NON_POSITION_AXIS_NOUN + r"))"
    r".*?(?:기본|베이직|basic).{0,16}?(?:포지션|프리셋|position).*?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)
_BASIC_POSITIONS_START = re.compile(r"(?P<no>\d+)\s*(?:번)?\s*(?:부터|에서(?:부터)?|번대)")

# The FX-positions request: the geometric skeletons phaser effects swing
# around (sweeps, circle/bally bases, tails, splits), a set distinct from the
# design-oriented BASIC ten. The vocabulary is disjoint from
# `_BASIC_POSITIONS_REQUEST` (이펙트/효과/fx/effect vs 기본/베이직/basic), so
# neither request can leak into the other flow. '포지션' is REQUIRED between
# the effect word and the store verb — effect-APPLICATION sentences ("무빙
# 이펙트 적용해줘") carry an effect word but no position noun and no store
# verb, and must keep reaching their current handlers untouched.
_FX_POSITIONS_REQUEST = re.compile(
    r"(?:이펙트|효과|fx|effect).{0,16}?(?:포지션|position).*?(?:저장|만들|잡아|생성)",
    re.IGNORECASE | re.DOTALL,
)

# 포지션 이펙트 시퀀스: 저장된 FX 포지션 프리셋(FX_POSITION_SEQUENCE)을 실제로
# **소비**하는 빌더 — "좌우 스윕 시퀀스 만들어줘". 진입은 세 조각이 전부 있어야
# 한다: 효과어(스윕/플라이아웃/서클/발리후/웨이브) + 명사(시퀀스 | 포지션 이펙트)
# + 생성 동사. 효과어가 필수라서 프리셋 저장 문장("이펙트 포지션 프리셋 …")과
# 겹치지 않고, 명사·동사가 필수라서 이펙트 **적용** 문장("무빙 이펙트 적용해줘")은
# 그대로 기존 경로(모델/기존 핸들러)로 간다. 항목은 (효과, 어휘, 한글 라벨) —
# 라벨은 `position_fx_commands`의 시퀀스 라벨로 그대로 들어간다.
_POSITION_FX_VOCABULARY: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("sweep", re.compile(r"스[윕윅]|sweep", re.IGNORECASE), "좌우 스윕"),
    ("flyout", re.compile(r"플라이\s*아웃|flyout|하늘\S*\s*객석", re.IGNORECASE), "플라이아웃"),
    ("circle", re.compile(r"서클|원을?\s*그[리려]|동그라미|circle", re.IGNORECASE), "서클"),
    ("ballyhoo", re.compile(r"발리후|ballyhoo", re.IGNORECASE), "발리후"),
    ("wave", re.compile(r"웨이브|물결|wave", re.IGNORECASE), "웨이브"),
)
_POSITION_FX_NOUN = re.compile(r"시퀀스|포지션\s*이펙트", re.IGNORECASE)
_POSITION_FX_VERB = re.compile(r"만들|생성|저장|걸어")


# SPEC-COPILOT-INTENT-001 M1 — **명시적 부정은 하드 베토.** 위 어휘는 첫-매치가
# 곧 판정이라 "포지션이 아니라 컬러다"를 읽을 자리가 없다. 2026-08-19 실측:
# "원형 회전 R/G 컬러 페이저" 요청이 circle 정규식에 잡혀 팬/틸트 빌더로 갔고,
# 다음 발화에서 "컬러만, 포지션 아님"이라고 못박아도 **같은 곳으로 다시 갔다**.
# `아니면`(선택 접속)은 부정이 아니므로 제외한다 — "팬 아니면 틸트로"는 베토가
# 아니다.
#
# t27 — 「아님」이 새던 이유는 lookahead 가 아니라 **한글 음절**이다. `아님` 은
# `아니`+`ㅁ` 이 아니라 `아`+`님` 이라, 리터럴 `아니` 는 아예 매치되지 않는다.
# 실측(2026-08-23): 아니야·아니다는 잡히고 아님·아닙니다·아닌·아녜요는 전부
# 샜다. 조작자는 팬/틸트를 제외했다고 믿는데 콘솔에는 저장된다 — 실패 신호가
# 없어서 리허설에서야 드러난다.
#
# 어미를 열거하지 않는다. 한국어 부정 활용은 열거로 닫히지 않는다 —
# `아님·아녀·아닙·아닌` 을 더해도 다음 축약형에서 또 샌다. 대신 활용
# **패러다임**을 닫는다: `아니-` 의 둘째 음절은 언제나 초성 ㄴ + 중성
# {ㅣ, ㅑ, ㅕ, ㅖ} 이고 받침만 달라진다(니 님 닌 닙 녜 냐 녀 …). 받침 27종을
# 세는 대신 그 음절 구간을 통째로 잡는다.
def _hangul_span(cho: int, jungs: tuple[int, ...]) -> str:
    """초성·중성이 정해진 완성형 음절 구간을 문자클래스 조각으로 낸다.

    완성형 한글은 `0xAC00 + 초성*588 + 중성*28 + 받침` 이라 받침 27종이
    연속한다. 그래서 받침을 열거하지 않고 구간 하나로 덮을 수 있다.
    """
    spans = []
    for jung in jungs:
        start = 0xAC00 + cho * 588 + jung * 28
        spans.append(f"{chr(start)}-{chr(start + 27)}")
    return "".join(spans)


#: `아니-` 활용의 둘째 음절. 받침 **있는** 것만 모은다 — 받침 없는 `니` 는
#: `아니면`(선택 접속) · `아니냐`/`아니니`(의문)와 겹쳐 lookahead 가 필요하고,
#: 받침 있는 것들(님 닌 닙 …)은 그 겹침이 없다. 둘을 한 문에 넣으면 `아닙니다`
#: 처럼 **뒤에 `니` 가 따라오는 부정형**이 lookahead 에 걸려 사라진다(자체 대조군에서 적발).
_ANI_TAIL_CODA = "".join(
    f"{chr(0xAC00 + 2 * 588 + jung * 28 + 1)}-{chr(0xAC00 + 2 * 588 + jung * 28 + 27)}"
    for jung in (2, 6, 7, 20)
)
#: 받침 없는 활용형(냐 녀 녜)은 그대로 부정이고, `니` 만 lookahead 가 필요하다.
_ANI_TAIL_BARE = "".join(chr(0xAC00 + 2 * 588 + jung * 28) for jung in (2, 6, 7))

_POSITION_FX_VETO = re.compile(
    r"(?:포지션|무빙|빔|팬|틸트|position|pan|tilt)\s*(?:은|는|이|가|을|를)?\s*"
    rf"(?:아(?:니(?!면|냐|니)|[{_ANI_TAIL_BARE}{_ANI_TAIL_CODA}])"
    r"|말고|말구|제외|건드리지)",
    re.IGNORECASE,
)

# M2 — 비-포지션 속성축이 이펙트의 **주체**로 명시된 문장. 이 단어가 있으면
# 어휘 후보 둘이 맞서는 상태이므로, 조용히 포지션을 택하지 말고 카드 1장으로
# 축을 확정한다.
#
# 여기서 「포지션 낱말이 나오는가」로 카드를 건너뛰지 않는다(t34). 그 물음은
# 「사용자가 이 축을 원하는가」와 다르고, 배제 문장은 배제하려는 바로 그 낱말을
# 쓰기 때문에 낱말 판정이 배제를 긍정으로 뒤집는다 — `포지션 빼고 컬러 스윕` 이
# 축 확인 없이 포지션으로 진행했다. 극성을 어휘로 잡아 보려는 시도는 수렴하지
# 않았다(3라운드 실측, 커밋 메시지 참조): 매 라운드 새 어법이 새고 동시에 긍정
# 문장이 막히기 시작했다. 그래서 판정을 어휘에 두지 않고 카드에 넘긴다.
#
# 두 실패의 값이 대칭이 아닌 것이 근거다. 누출은 사용자가 배제한 축으로 조용히
# 시퀀스가 저장되는 것이고(실패 신호 없음, 콘솔 쓰기는 되돌리기 어렵다), 과잉은
# 질문 한 장이다.
_NON_POSITION_ATTRIBUTE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("색(컬러)", re.compile(r"컬러|색깔|색상|색이|색을|색만|colou?r|rgb", re.IGNORECASE)),
    ("밝기(디머)", re.compile(r"디머|밝기|dimmer", re.IGNORECASE)),
)
#: **통제된 선택지 문자열 전용**이다. `_ask_one` 이 돌려준 답에서는 「포지션
#: 낱말이 나오는가」가 곧 「사용자가 포지션을 골랐는가」다 — 선택지를 이 파일이
#: 직접 만들었으니 어휘와 의도가 같은 것을 가리킨다. 사용자가 자유롭게 쓴
#: 문장에는 쓰지 말 것: 거기서는 같은 물음이 배제를 긍정으로 뒤집는다(t34).
_POSITION_AXIS_CLAIM = re.compile(
    r"포지션|무빙|빔|팬|틸트|position|pan|tilt|조준|겨[누냥]", re.IGNORECASE
)

# 재생성: 이미 저장된 구간을 **제자리에서** 다시 잡는다. 큐는 프리셋 REFERENCE를
# 들고 있으므로 같은 번호에 다시 저장하면 그 프리셋을 쓰는 모든 큐가 따라온다.
# `_BASIC_POSITIONS_REQUEST`는 동사 대안에 '잡아'를 이미 갖고 있어 재생성 문장을
# **함께 매치한다**(2026-08-16 실측 — ASSUMPTION-83 반증). 교집합을 없애려면 이미
# 출하된 트리거를 좁혀야 하므로, 대신 디스패치 등록 순서로 행선지를 고정한다
# (REQ-PRESETGUARD-015). 어휘는 좁게 잡는다 — 넓힐수록 신규 저장이 새어든다(D-1).
#
# 꼬리는 **묶는다**. `.*?`로 열어 두면 "기본 포지션 10개 저장해줘, 끝나면 다시
# 알려줘" 처럼 `다시`가 다른 동사에 붙은 문장까지 재생성으로 끌려온다 — 그러면
# 저장 요청이 "다시 잡을 자리가 없습니다, 먼저 저장하세요"로 되돌아와 같은 문장을
# 다시 쳐도 영원히 같은 답이 나오고, 풀에 10칸 구간이 있으면 사용자가 언급한 적
# 없는 구간을 덮어쓰겠다는 카드가 뜬다.
_REGENERATE_POSITIONS_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?(?:포지션|프리셋|position)"
    r"(?:"
    # 그 자체로 재생성을 뜻하는 명사 — 뒤에 동사가 붙지 않아도 된다.
    r".{0,12}?(?:재생성|재조준|리포커스|refocus)"
    r"|"
    # `다시`는 부사라 홀로는 의미가 없다. 재생성 동사에 **붙어 있어야** 한다.
    #
    # `저장`은 여기 들어오면 안 된다 — 그건 **신규 저장**의 동사다. 넣으면
    # "기본 포지션 프리셋 21번부터 다시 저장해줘"가 재생성으로 끌려가고, 풀이
    # 비어 있으면 저장해달라는 요청에 "먼저 '기본 포지션 10개 저장'을 실행해
    # 주세요"라고 답하게 된다. 더 나쁜 건 첫 저장이 일부만 착지했을 때다 — 그
    # 구간은 정의상 10칸 연속이 아니므로, 가장 자연스러운 재시도 문장이 영구히
    # 거부된다. 게이트 보류나 부분 거절이 만드는 바로 그 상황이다.
    #
    # 사이에 어절 **하나**를 허용한다. `\S`는 공백을 넘지 못해서, 같은 어휘에 부사
    # 하나가 낀 "기본 포지션 다시 한번 잡아줘" · "다시 좀 잡아줘"가 재생성에서
    # 빠졌다. 그러면 저장 경로로 가 **새 구간에 저장**되는데, 운영자는 기존
    # 프리셋이 갱신됐다고 믿는다 — 큐는 옛 좌표를 계속 가리킨다. 어휘를 넓히는
    # 게 아니라 어절 하나를 건너뛰게 하는 것이라 F5 봉쇄(꼬리 12자 한도)는 그대로다.
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# FX 재생성: BASIC 재생성과 같은 문형에서 **명사만** 다르다. 어휘는
# `_FX_POSITIONS_REQUEST`와 같은 축(이펙트/효과/fx/effect)이라 BASIC 쪽
# (기본/베이직/basic)과 서로소다 — '기본' 문장은 여기 걸리지 않고 그 역도
# 성립하므로 상호 오라우팅이 없다. 꼬리 규율(묶인 '다시', '저장' 제외, 어절
# 하나 허용)은 위 `_REGENERATE_POSITIONS_REQUEST` 주석의 근거를 그대로
# 상속한다 — 두 정규식의 동사부는 의도적으로 동일하다.
_REGENERATE_FX_POSITIONS_REQUEST = re.compile(
    r"(?:이펙트|효과|fx|effect).{0,16}?(?:포지션|position)"
    r"(?:"
    r".{0,12}?(?:재생성|재조준|리포커스|refocus)"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# 기본 컬러 프리셋 저장 (SPEC-COPILOT-COLORPRESET-001 REQ-001): 어휘가 컬러축
# (컬러/색/color)이라 포지션축(포지션/position)과 서로소다 — 컬러 문장이 포지션
# 경로로 새지 않는다. 역방향은 성립하지 않는다: `_BASIC_POSITIONS_REQUEST`가
# 명사 대안에 '프리셋'을 이미 가져 "기본 컬러 프리셋 저장" 문장을 **함께
# 매치**하므로, 겹치는 입력의 행선지는 디스패치 등록 순서(컬러 먼저)로 고정한다
# — 재생성이 신규 저장보다 앞서는 것과 같은 형상이다(REQ-PRESETGUARD-015).
_BASIC_COLORS_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?(?:컬러|색|color).*?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)

# 컬러 재생성 (REQ-COLORPRESET-004): BASIC 재생성과 같은 문형에서 명사축만
# 컬러다. 꼬리 규율(묶인 '다시', '저장' 제외, 어절 하나 허용)은
# `_REGENERATE_POSITIONS_REQUEST` 주석의 근거를 그대로 상속한다 — 동사부는
# 의도적으로 동일하다. '재조준/리포커스'는 포지션 전용 어휘라 들이지 않는다.
_REGENERATE_COLORS_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?(?:컬러|색|color)"
    r"(?:"
    r".{0,12}?재생성"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

#: 표준 무대 팔레트 10색 — 슬롯 순서가 계약이다(spec.md §A.2): 슬롯 1은 항상
#: 'Warm White'이고 재생성 가족 필터의 first_label이 된다(포지션 'Home'·FX
#: 'Sweep L'과 같은 규율). RGB(0-100)는 spec §A.2의 고정 시퀀스 — 4번(Amber
#: 100/55/5)·8번(Blue 5/20/100)은 기존 `fx/library/color.yaml`의 실측 대역에서
#: 왔다. 전 장비 동일 값이지만 저장은 Selective(프로그래머 경유)뿐이다 —
#: Global/Universal 플래그는 미검증 문법(REQ-COLORPRESET-008).
#:
#: 카드 t408 — 표 본체는 `server/design/color_names.py` 로 옮겼다(팔레트
#: 범례가 없는 실제 곡에서도 `_palette_rgb` 가 같은 표를 순환 임포트 없이
#: 쓰기 위해서다). 여기서는 이름만 다시 가져간다 — 값은 바이트 그대로.
COLOR_PALETTE_SEQUENCE = _COLOR_NAMES.COLOR_PALETTE_SEQUENCE

#: 팔레트 라벨 → RGB(0-100) 역인덱스 — 멀티컬러 페이저 스텝은 팔레트 프리셋
#: 번호(`At Preset 4.x`)가 아니라 **이 RGB 값 자체**를 스텝에 직접 싣는다
#: (T1 프로브 결론, `08-color-phaser-m0-probe.md` §1). 팔레트 프리셋이 실제로
#: 저장된 슬롯 번호는 운영자가 저장 시점에 고른 값이라 코드가 아는 상수가
#: 아니다 — RGB 직접 지정은 그 의존을 없애고 `_color_apply_command`와 같은
#: 문법(라이브 검증됨)만 재사용한다.
_COLOR_PALETTE_RGB: dict[str, tuple[int, int, int]] = dict(COLOR_PALETTE_SEQUENCE)

#: 멀티컬러 페이저 프리셋 10종 카탈로그 — `docs/handoff/2026-08-16-session-
#: handoff.md` §2 표 그대로 고정(라벨·스텝·Form·Phase 순서가 계약). 슬롯 1은
#: 항상 'Breathe Warm'이고 재생성 가족 필터의 first_label이 된다(팔레트·
#: 포지션·FX와 같은 규율). 각 원소: (라벨, 스텝 순서의 팔레트 라벨들,
#: Form("sine"|"rectangle"), Phase 커맨드 토큰).
COLOR_PHASER_SEQUENCE: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("Breathe Warm", ("Warm White", "Amber"), "sine", "0"),
    ("Breathe Cool", ("Cool White", "Blue"), "sine", "0"),
    ("Chase RB", ("Red", "Blue"), "rectangle", "0"),
    ("Chase CM", ("Cyan", "Magenta"), "rectangle", "0"),
    ("Wave CM", ("Cyan", "Magenta"), "sine", "0 Thru 360"),
    ("Wave WA", ("Warm White", "Amber"), "sine", "0 Thru 360"),
    ("Rainbow", ("Red", "Green", "Blue"), "sine", "0 Thru 360"),
    ("Pulse RY", ("Red", "Yellow"), "sine", "0"),
    ("Duo GL", ("Green", "Lavender"), "sine", "180"),
    ("Slam RW", ("Red", "Warm White"), "rectangle", "0 Thru 360"),
)

# 멀티컬러 페이저 저장 (핸드오프 §2 지침 2): 어휘축(멀티컬러/컬러 이펙트/
# multi-color/color effect)이 기본 컬러 트리거의 어휘축(기본/베이직/basic)과
# 서로소 주장(축 토큰끼리는 참)에 더해, '기본'+페이저 어휘가 한 문장에 공존하는
# 합성 문장("기본 멀티컬러 페이저 저장해줘")은 기본 트리거의 갭(.{0,16}?)에도
# 매치되므로 **디스패치 등록 순서**(페이저가 기본보다 앞)가 행선지를 고정한다
# (2026-08-17 리뷰 실측 — run_instruction 디스패치 블록 참조).
# '컬러 페이저'는 일반 표현으로 들어온다 — 카탈로그 이름('멀티컬러')을 모르는
# 운영자가 쓰는 어휘다. 축이 붙어 있으므로 짐작이 아니다.
_COLOR_PHASER_REQUEST = re.compile(
    r"(?:멀티\s*컬러|컬러\s*(?:이펙트|페이저)|multi-?color|color\s*(?:effect|phaser))"
    r".{0,24}?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)

# 멀티컬러 페이저 재생성: BASIC/컬러 재생성과 같은 문형에서 어휘축만 다르다.
# 꼬리 규율(묶인 '다시', '저장' 제외, 어절 하나 허용)은 `_REGENERATE_COLORS_
# REQUEST` 주석의 근거를 그대로 상속한다 — 동사부는 의도적으로 동일하다.
_REGENERATE_COLOR_PHASER_REQUEST = re.compile(
    r"(?:멀티\s*컬러|컬러\s*이펙트|multi-?color|color\s*effect)"
    r"(?:"
    r".{0,12}?재생성"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

#: 디머 레벨 프리셋 10종 — T5 카탈로그(코디네이터 지시 고정). 라벨은 그대로
#: Dimmer 값(%)이다(Full=100). 슬롯 1은 항상 'Dim 10'이고 재생성 가족 필터의
#: first_label이 된다(팔레트·포지션·FX·멀티컬러와 같은 규율).
DIMMER_LEVEL_SEQUENCE: tuple[tuple[str, int], ...] = (
    ("Dim 10", 10),
    ("Dim 20", 20),
    ("Dim 30", 30),
    ("Dim 40", 40),
    ("Dim 50", 50),
    ("Dim 60", 60),
    ("Dim 70", 70),
    ("Dim 80", 80),
    ("Dim 90", 90),
    ("Full", 100),
)

# 기본 디머(레벨) 프리셋 저장 — 컬러의 `_BASIC_COLORS_REQUEST`를 어휘축만 바꿔
# 미러한다(기본/베이직/basic + 디머/dimmer). 컬러축(컬러/색/color)과 서로소라
# 두 계열이 서로의 문장을 삼키지 않는다. 포지션 트리거의 명사 대안 '프리셋'과는
# 여전히 교집합이 있지만(컬러와 같은 형상), 디스패치 등록 순서(디머가 포지션보다
# 앞)로 행선지를 고정한다(REQ-PRESETGUARD-015와 같은 패턴).
_BASIC_DIMMER_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?" + _DIMMER_AXIS_WORD + r".*?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)

# 디머 레벨 재생성: BASIC 재생성과 같은 문형에서 명사축만 디머다. 꼬리 규율은
# `_REGENERATE_POSITIONS_REQUEST` 주석의 근거를 그대로 상속한다. '재조준/
# 리포커스'는 포지션 전용 어휘라 들이지 않는다(컬러와 동일 사유).
_REGENERATE_DIMMER_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?" + _DIMMER_AXIS_WORD + r"(?:"
    r".{0,12}?재생성"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

#: 디머 페이저 프리셋 10종 — T5 카탈로그(코디네이터 지시 고정, T4 프로브
#: `09-dimmer-phaser-m0-probe.md`가 확인한 문법만 사용). 각 원소: (라벨,
#: 스텝 순서의 디머 값(%)들, Form("sine"|"rectangle"), Phase 커맨드 토큰).
#: 슬롯 1은 항상 'Breathe Soft'이고 재생성 가족 필터의 first_label이 된다.
DIMMER_PHASER_SEQUENCE: tuple[tuple[str, tuple[int, ...], str, str], ...] = (
    ("Breathe Soft", (30, 70), "sine", "0"),
    ("Breathe Deep", (10, 90), "sine", "0"),
    ("Pulse Hard", (0, 100), "rectangle", "0"),
    ("Pulse Half", (30, 100), "rectangle", "0"),
    ("Wave Soft", (30, 70), "sine", "0 Thru 360"),
    ("Wave Full", (0, 100), "sine", "0 Thru 360"),
    ("Ripple", (30, 60, 100), "sine", "0 Thru 360"),
    ("Flash Accent", (100, 20), "rectangle", "0"),
    ("Alt Half", (50, 100), "sine", "180"),
    ("Slam Run", (0, 100), "rectangle", "0 Thru 360"),
)

# 디머 페이저 저장: 컬러의 `_COLOR_PHASER_REQUEST`를 어휘축만 바꿔 미러한다
# (디머 이펙트/디머 페이저/dimmer effect/dimmer phaser). '기본' 접두를 요구하지
# 않는 점도 컬러의 멀티컬러 트리거와 동일 — 어휘 자체(이펙트/페이저 복합어)가
# 이미 레벨 트리거(단순 '디머')와 서로소다.
_DIMMER_PHASER_REQUEST = re.compile(
    _DIMMER_AXIS_WORD + r"\s*(?:이펙트|페이저|effect|phaser)"
    r".{0,24}?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)

# 디머 페이저 재생성: 디머 레벨 재생성과 같은 문형에서 어휘축만 다르다(컬러/
# 멀티컬러 재생성 쌍과 동일 형상).
_REGENERATE_DIMMER_PHASER_REQUEST = re.compile(
    _DIMMER_AXIS_WORD + r"\s*(?:이펙트|페이저|effect|phaser)"
    r"(?:"
    r".{0,12}?재생성"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

#: 콤보(컬러+디머 혼합) 페이저 프리셋 10종 — T8 카탈로그(코디네이터 지시
#: 고정, T7 프로브 ``10-combo-phaser-m0-probe.md``가 확인한 저장 풀만
#: 사용). 각 원소: (라벨, 스텝 순서의 (팔레트 라벨, 디머%) 쌍들,
#: Form("sine"|"rectangle"), Phase 커맨드 토큰). 슬롯 1은 항상 'Drop Slam'
#: 이고 재생성 가족 필터의 first_label이 된다(팔레트·포지션·컬러·디머와
#: 같은 규율). Rectangle 근사는 ``_color_phaser_form_commands``/
#: ``_dimmer_phaser_form_commands``와 동일한 ASSUMPTION(공식 수치 없음)을
#: 상속한다.
COMBO_PHASER_SEQUENCE: tuple[tuple[str, tuple[tuple[str, int], ...], str, str], ...] = (
    ("Drop Slam", (("Red", 100), ("Red", 0)), "rectangle", "0"),
    ("Breathe Amber", (("Warm White", 70), ("Amber", 30)), "sine", "0"),
    ("Breathe Blue", (("Cool White", 60), ("Blue", 25)), "sine", "0"),
    ("Police", (("Red", 100), ("Blue", 100)), "rectangle", "0"),
    ("Heartbeat", (("Red", 90), ("Red", 15)), "sine", "0"),
    ("Golden Wave", (("Amber", 100), ("Warm White", 40)), "sine", "0 Thru 360"),
    ("Ocean Wave", (("Cyan", 90), ("Blue", 30)), "sine", "0 Thru 360"),
    (
        "Rainbow Run",
        (("Red", 100), ("Green", 50), ("Blue", 100)),
        "sine",
        "0 Thru 360",
    ),
    ("Club Duo", (("Magenta", 100), ("Cyan", 40)), "rectangle", "180"),
    ("Finale Slam", (("Warm White", 100), ("Red", 0)), "rectangle", "0 Thru 360"),
)

# 콤보 페이저 저장: 컬러/디머 페이저 트리거를 어휘축만 바꿔 미러한다(콤보/
# combo/컬러디머/드롭 프리셋). 축 토큰 자체는 기존 5개 축과 서로소지만,
# 합성 문장 "컬러 디머 페이저 저장"은 디머 페이저 축('디머 페이저' 연속
# 토큰)에도 매치된다 — 그래서 **디스패치 등록 순서**가 콤보를 모든 프리셋
# 가족의 맨 앞에 둔다(2026-08-17 리뷰 실측, run_instruction 디스패치 블록).
# "드롭 프리셋"은 다른 축에 없는 명사 조합이다.
# '복합'은 사용자 확정 어휘다 — 신규 프리셋 종류가 아니라 이 콤보 계열
# (컬러+디머 혼합, All 1 풀)의 다른 이름이다.
_COMBO_PHASER_REQUEST = re.compile(
    r"(?:콤보|combo|복합|컬러\s*디머|드롭\s*프리셋)"
    r".{0,24}?" + _PRESET_STORE_VERB,
    re.IGNORECASE | re.DOTALL,
)

# 콤보 페이저 재생성: 다른 재생성 쌍과 동일 형상(트리거의 '잡아' 중첩으로
# 신규 저장보다 등록 순서가 앞이어야 함).
_REGENERATE_COMBO_PHASER_REQUEST = re.compile(
    r"(?:콤보|combo|컬러\s*디머|드롭\s*프리셋)"
    r"(?:"
    r".{0,12}?재생성"
    r"|"
    r".{0,12}?다시(?:\s+\S{1,6})?\s*(?:잡|만들|생성|갱신)"
    r")",
    re.IGNORECASE | re.DOTALL,
)


# ── 프리셋 계열 레지스트리 ────────────────────────────────────────────────────
#
# 위 `_*_REQUEST` 트리거는 계열 **하나**를 겨냥한 문장을 잡는다. 한 문장이 여러
# 계열을 지정하면(«포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을 설정하고
# 복합 프리셋도 …») 사전 핸들러 체인은 첫 매칭 하나만 실행하고 턴을 끝내므로
# 나머지 계열이 조용히 사라진다. 레지스트리는 "이 문장이 어느 계열들을
# 지정했나"를 트리거와 **독립적으로** 판정해 합성 핸들러가 선택 카드로 묻게 한다.
#
# `matches`는 트리거 정규식이 아니라 **어순 무관 토큰 존재** 판정이다. 트리거는
# 「수식어 → 축 → 동사」 순서를 요구하지만 실제 문장은 축을 앞에 세운다
# («포지션, 컬러, 딤머의 기본 프리셋 …» — '컬러'가 '기본'보다 앞이다). 어순을
# 요구하면 바로 그 문장에서 컬러·딤머 계열을 놓친다.
_PRESET_STORE_VERB_RE = re.compile(_PRESET_STORE_VERB)
_PRESET_BASIC_QUALIFIER_RE = re.compile(r"기본|베이직|basic|스탠다드|standard", re.IGNORECASE)
#: 포지션 축 동의어 — 「포커스」·「자리」·「위치」는 같은 축을 가리키는 현장 어휘다.
_PRESET_POSITION_AXIS_RE = re.compile(r"포지션|position|포커스|focus|자리|위치", re.IGNORECASE)
#: 컬러 축. '색'이 색상·색깔을 부분문자열로 덮는다 — 팔레트만 따로 받는다.
_PRESET_COLOR_AXIS_RE = re.compile(r"컬러|색|color|팔레트|palette", re.IGNORECASE)
_PRESET_DIMMER_AXIS_RE = re.compile(_DIMMER_AXIS_WORD, re.IGNORECASE)
#: 콤보 축 토큰. `컬러\s*디머`는 **그 자체가** 컬러·디머 어휘를 품고 있어, 걷어내지
#: 않으면 «컬러 디머 페이저 저장해줘»가 컬러·디머 페이저 후보로도 올라 이미
#: 출하된 행선지(디스패치 순서상 콤보가 맨 앞)를 카드 질문으로 바꿔버린다.
#: 그래서 콤보를 제외한 모든 계열은 이 토큰을 지운 문장 위에서 판정한다.
_PRESET_COMBO_AXIS_RE = re.compile(r"콤보|combo|복합|컬러\s*디머|드롭\s*프리셋", re.IGNORECASE)
#: 페이저 수식어 — 축 명사와 **결합**될 때만 계열을 지정한다. 「체이스」·「무빙」은
#: 조명감독이 페이저를 부르는 현장 어휘다.
_PRESET_PHASER_QUALIFIER_RE = re.compile(
    r"페이저|phaser|이펙트|effect|멀티\s*컬러|multi-?color|체이스|chase",
    re.IGNORECASE,
)
#: 축에 묶인 페이저 복합어. '기본 디머 페이저 저장'은 계열이 **하나**(디머 페이저)
#: 인 문장이다 — '기본'은 수식어일 뿐이라 기본 디머 계열까지 후보로 올리면
#: 출하된 단일 행선지가 카드 질문으로 바뀐다. 기본 계열은 이 복합어를 지운
#: 문장 위에서 판정한다.
#:
#: 페이저를 부르는 낱말은 수식어 쪽과 **같은 집합**이어야 한다 — 한쪽에만
#: 낱말을 더하면(예: '체이스') 그 문장이 페이저 계열로도, 기본 계열로도
#: 잡혀 카드에 두 줄이 뜬다.
_PHASER_WORD = r"(?:페이저|이펙트|phaser|effect|체이스|chase)"
_PRESET_COLOR_PHASER_COMPOUND_RE = re.compile(
    r"멀티\s*(?:컬러|color)|multi-?color|(?:컬러|색|color|팔레트|palette)\s*" + _PHASER_WORD,
    re.IGNORECASE,
)
_PRESET_DIMMER_PHASER_COMPOUND_RE = re.compile(
    _DIMMER_AXIS_WORD + r"\s*" + _PHASER_WORD, re.IGNORECASE
)
#: FX 포지션 복합어. '이펙트 포지션'은 기하 골격 계열(`_FX_POSITIONS_REQUEST`,
#: `FX_POSITION_SEQUENCE` 10종)이고 **기본 포지션과는 다른 계열**이다 — 기본
#: 포지션 계열이 그 문장을 자기 것으로 주장하면 안 되므로 판정 전에 걷어낸다.
#:
#: 수식어와 축 사이에 조사·꾸밈말이 끼는 실제 어법을 받는다(2026-08-19 사용자
#: 표현 «조명연출을 위한 포지션»): 붙어 있는 '이펙트 포지션'만 보면 그 문장이
#: 기본 포지션으로 새고, 같은 카드에 계열이 둘 뜬다. 간격은 짧게 묶어 둔다 —
#: 넓히면 "무빙 이펙트 적용하고 … 포지션 프리셋 저장" 같은 무관한 문장까지
#: FX로 끌려온다.
_PRESET_FX_POSITION_COMPOUND_RE = re.compile(
    r"(?:이펙트|효과|fx|effect|연출).{0,8}?(?:포지션|position)",
    re.IGNORECASE | re.DOTALL,
)
#: 축 **없는** 맨 '페이저' 판정용. '이펙트/effect'는 여기 들어오면 안 된다 —
#: "무빙 이펙트 만들어줘"(이펙트 적용)를 프리셋 카드로 끌어온다. '프리셋'을
#: 요구하는 것도 같은 이유다: "…페이저로 시퀀스 만들어줘"(recall)를 비켜간다.
_PRESET_BARE_PHASER_RE = re.compile(r"페이저|phaser", re.IGNORECASE)
_PRESET_NOUN_RE = re.compile(r"프리셋|preset", re.IGNORECASE)

#: 사용자가 실제로 만들거나 저장하려는 **최종 산출물**. 같은 문장에 프리셋
#: 참조와 이펙트·시퀀스 명사가 함께 있을 수 있어, 단어 존재만으로 콘솔 저장
#: 경로를 택하면 안 된다. 아래 분류는 쓰기 경로가 하나의 최종 산출물만 고르게
#: 하는 공통 기준이다.
_SEQUENCE_ARTIFACT_NOUN_RE = re.compile(r"시퀀스|sequence|큐|cue", re.IGNORECASE)
_EFFECT_ARTIFACT_NOUN_RE = re.compile(r"이펙트|effect|페이저|phaser|체이스|chase", re.IGNORECASE)
#: «프리셋 21번으로 B-R 이펙트를 만들어줘»의 프리셋은 **재료 참조**다.
#: 번호와 참조 조사(`으로`·`로`·`에서`)가 붙은 이 형태를 저장 대상으로
#: 오해하면 새 10개를 써 버린다. 목적격 `프리셋을 저장`과 처격
#: `프리셋에 저장`은 저장 대상이므로 참조가 아니다.
_PRESET_REFERENCE_RE = re.compile(
    r"(?:프리셋|preset)\s*\d*\s*(?:번)?\s*(?:으로|로|에서)",
    re.IGNORECASE,
)

#: 「전부/모두」 — 일곱 계열을 한 번에 부르는 어휘. 계열 축을 **하나도** 지목하지
#: 않은 문장에서만 성립한다: «컬러 프리셋 전부 저장해줘»의 '전부'는 계열이 아니라
#: 그 축의 10종을 가리키므로, 축이 있으면 그 축만 후보로 남긴다.
_PRESET_ALL_FAMILIES_RE = re.compile(
    r"전부|모두|전체|싹|일괄|풀\s*세트|full\s*set|7\s*계열|일곱\s*계열|70\s*종",
    re.IGNORECASE,
)

#: 재생성 표지. 축별 재생성 트리거는 축 명사를 요구하므로 축 없는 「전부」
#: 문장을 잡지 못한다 — 그 구멍을 이 낱말들로 막는다.
_PRESET_REGENERATION_MARK_RE = re.compile(r"다시|재생성|갱신", re.IGNORECASE)

#: 계열을 **좁히는** 수식어 전부(기본계·페이저계·연출계). 하나라도 있으면 그
#: 문장은 계열을 특정한 것이고, 하나도 없으면 축만 말한 것이다.
_PRESET_ANY_QUALIFIER_RE = re.compile(
    r"기본|베이직|basic|스탠다드|standard"
    r"|페이저|phaser|이펙트|effect|멀티\s*컬러|multi-?color|체이스|chase"
    r"|효과|fx|연출",
    re.IGNORECASE,
)

#: 재생성 트리거 전부. 레지스트리는 **신규 저장** 문장을 계열로 쪼개는 장치라,
#: 재생성 문장은 어느 계열도 후보로 올리지 않는다. 재생성 어휘가 저장 동사를
#: 공유하므로(«기본 컬러랑 포지션 다시 잡아줘» — '잡아'), 이 배제가 없으면
#: 다축 재생성 문장이 저장 카드로 끌려간다.
_REGENERATE_PRESET_REQUESTS: tuple[re.Pattern[str], ...] = (
    _REGENERATE_POSITIONS_REQUEST,
    _REGENERATE_FX_POSITIONS_REQUEST,
    _REGENERATE_COLORS_REQUEST,
    _REGENERATE_COLOR_PHASER_REQUEST,
    _REGENERATE_DIMMER_REQUEST,
    _REGENERATE_DIMMER_PHASER_REQUEST,
    _REGENERATE_COMBO_PHASER_REQUEST,
)

#: 프리셋 어휘를 **지나가며** 쓰는 남의 의도들. 곡 설계 브리프는 프리셋 번호로
#: 시작 슬롯을 지정하고("프리셋 21번부터") 무드를 색·밝기로 적는다
#: («파란색과 낮은 밝기로 시작하고 …») — 어순 무관 토큰 판정에는 컬러·디머
#: 두 계열로 보이지만 저장 요청이 아니다. 합성 카드는 체인 앞자리에 있어
#: 이런 문장을 가로채면 곡 설계 흐름 자체가 멎는다(2026-08-19 회귀).
#:
#: 트리거 정규식은 어순을 요구해 이 문장들을 원래 비켜갔다 — 배제가 필요한
#: 쪽은 레지스트리뿐이다.
_PRESET_FOREIGN_INTENT_REQUESTS: tuple[re.Pattern[str], ...] = (
    _SONG_DESIGN_REQUEST,
    _POSITION_SHEET_REQUEST,
    # «프리셋 28번 포지션을 **큐로** 저장해줘» — 프리셋을 **참조**해 큐를
    # 만드는 요청이지 프리셋을 만드는 요청이 아니다. 축만 말한 문장이 그 축의
    # 계열을 전부 올리게 되면서 이 문장이 카드로 끌려갔다(2026-08-19 회귀).
    _CUE_STORE_INTENT,
)


def _reads_as_preset_regeneration(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _REGENERATE_PRESET_REQUESTS)


def _programming_artifact_target(text: str) -> str | None:
    """문맥상 사용자가 만들 최종 산출물을 보수적으로 한 가지로 판정한다.

    우선순위는 ``시퀀스 → 프리셋 저장 → 이펙트``다. 시퀀스는 프리셋을
    *소비*할 수 있고, 프리셋은 이펙트를 *담아* 저장할 수 있다. 따라서
    «프리셋 21번으로 이펙트 시퀀스 만들어줘»의 최종 산출물은 시퀀스이고,
    «B-R 컬러 이펙트 프리셋 만들어줘»는 프리셋이다. 산출물이나 행위가
    명시되지 않으면 ``None`` — 콘솔 쓰기 경로는 선택하지 않는다.
    """
    if _PRESET_STORE_VERB_RE.search(text) is None:
        return None
    if _SEQUENCE_ARTIFACT_NOUN_RE.search(text) is not None:
        return "sequence"
    if _PRESET_NOUN_RE.search(text) is not None and _PRESET_REFERENCE_RE.search(text) is None:
        return "preset"
    if _EFFECT_ARTIFACT_NOUN_RE.search(text) is not None:
        return "effect"
    return None


def _preset_store_request(text: str) -> bool:
    """명시적으로 프리셋을 최종 산출물로 고른 신규 저장 문장인가."""
    if _reads_as_preset_regeneration(text):
        return False
    if any(pattern.search(text) is not None for pattern in _PRESET_FOREIGN_INTENT_REQUESTS):
        return False
    return _programming_artifact_target(text) == "preset"


def _reads_as_bare_phaser(text: str) -> bool:
    """축 없는 «페이저 프리셋 …» — 어느 한 계열로 **짐작하지 않는다**.

    세 페이저 계열 전부의 후보로 올려 합성 핸들러가 선택 카드로 묻게 한다.
    """
    if _PRESET_BARE_PHASER_RE.search(text) is None or _PRESET_NOUN_RE.search(text) is None:
        return False
    return not any(
        axis.search(text) is not None
        for axis in (
            _PRESET_POSITION_AXIS_RE,
            _PRESET_COLOR_AXIS_RE,
            _PRESET_DIMMER_AXIS_RE,
            _PRESET_COMBO_AXIS_RE,
        )
    )


def _reads_as_all_families(text: str) -> bool:
    """«프리셋 전부 깔아줘» — 일곱 계열을 한 번에 부르는 문장인가.

    성립 조건은 셋이다: 저장 문장이고, '프리셋' 명사가 있고, 계열 축을
    **하나도** 지목하지 않았다. 축이 있으면 '전부'는 계열이 아니라 그 축의
    10종을 뜻한다 — «컬러 프리셋 전부 저장해줘»는 컬러 하나만 남겨야 한다.

    각 계열 판정이 이 함수를 함께 보므로 「몇 계열인가」의 단일 소재는 여전히
    ``PRESET_FAMILIES``\\ 하나다 — 합성 핸들러는 고칠 것이 없다.

    재생성 표지(다시·재생성·갱신)는 여기서 따로 막는다. 축별 재생성 트리거는
    축 명사를 요구하는데 «프리셋 전부 다시 잡아줘»에는 축이 없어 그물을
    빠져나간다 — 그대로 두면 재생성 한마디가 일곱 계열 70칸의 저장 카드가 된다.
    """
    if _PRESET_ALL_FAMILIES_RE.search(text) is None:
        return False
    if _PRESET_NOUN_RE.search(text) is None:
        return False
    if _PRESET_REGENERATION_MARK_RE.search(text) is not None:
        return False
    return not any(
        axis.search(text) is not None
        for axis in (
            _PRESET_POSITION_AXIS_RE,
            _PRESET_COLOR_AXIS_RE,
            _PRESET_DIMMER_AXIS_RE,
            _PRESET_COMBO_AXIS_RE,
            _PRESET_PHASER_QUALIFIER_RE,
        )
    )


def _reads_as_unqualified_axis(text: str, axis: re.Pattern[str]) -> bool:
    """수식어 없이 축만 말한 문장인가 — 그 축의 계열을 **전부** 후보로 올린다.

    «딤머, 포지션, 컬러, 콤보 프리셋을 설정해줘» 처럼 운영자는 축만 말한다.
    그 축에 기본·연출·페이저가 몇 벌 있는지는 앱이 아는 사정이지 부탁할 때
    따져야 할 것이 아니다. 축만 말하면 그 축의 계열을 모두 카드에 체크해
    올리고, 필요 없는 줄은 체크를 풀면 된다 — 반대로 좁혀서 올리면 있는 줄도
    모르고 지나간다.

    수식어(기본/베이직/페이저/이펙트/체이스/연출…)가 **하나라도** 있으면 그
    문장은 계열을 특정한 것이므로 이 확장을 하지 않는다: «기본 컬러 프리셋»은
    기본 컬러 하나고, «컬러 페이저 프리셋»은 컬러 페이저 하나다.
    """
    if _PRESET_NOUN_RE.search(text) is None:
        return False
    if _PRESET_ANY_QUALIFIER_RE.search(text) is not None:
        return False
    return axis.search(text) is not None


def _without_combo_tokens(text: str) -> str:
    return _PRESET_COMBO_AXIS_RE.sub(" ", text)


def _designates(scoped: str, axis: re.Pattern[str]) -> bool:
    """기본 계열 하나가 지정됐나 — 축 명사에 수식어나 '프리셋' 명사가 딸려야 한다.

    '기본'만 요구하면 «포지션 프리셋과 컬러 프리셋 저장해줘»에서 두 계열을 모두
    놓친다 — 운영자는 계열 이름('기본 포지션')이 아니라 축과 명사로 말한다.
    반대로 축 명사 하나만 요구하면 프리셋과 무관한 문장("포지션 큐 만들어줘")까지
    끌려온다. 그래서 '기본' **또는** '프리셋'을 요구한다. 열거형 문장에서는
    명사 하나를 축들이 나눠 쓴다("포지션, 컬러 프리셋 저장해줘").
    """
    if axis.search(scoped) is None:
        return False
    return (
        _PRESET_BASIC_QUALIFIER_RE.search(scoped) is not None
        or _PRESET_NOUN_RE.search(scoped) is not None
    )


def _matches_basic_position_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_POSITION_AXIS_RE):
        return True
    scoped = _PRESET_FX_POSITION_COMPOUND_RE.sub(" ", _without_combo_tokens(text))
    return _designates(scoped, _PRESET_POSITION_AXIS_RE)


def _matches_fx_position_family(text: str) -> bool:
    """조명연출용 기하 포지션 계열 — 기본 포지션과 **다른** 10종이다.

    카탈로그는 `FX_POSITION_SEQUENCE`(Sweep L/R, Sky Out, Floor/Circle/Bally
    Base, Tail, Mirror Split, Fan Floor, Aisle Punch)로, 페이저가 그 둘레를
    도는 기하 골격이다. 이 계열이 레지스트리에서 빠져 있어 7계열 70종 중
    60종만 카드에 올랐다(2026-08-19 사용자 지적).

    '프리셋' 명사를 요구한다 — 축만 보면 «이펙트 포지션으로 시퀀스 만들어줘»
    (recall 경로)까지 계열로 세어 합성 카드가 그 문장을 가로챈다. 명사가 없는
    «이펙트 포지션 저장해줘»는 계열 하나로도 세어지지 않으므로 지금처럼
    단일 핸들러(`_fx_position_presets`)가 그대로 받는다.
    """
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_POSITION_AXIS_RE):
        return True
    if _PRESET_FX_POSITION_COMPOUND_RE.search(_without_combo_tokens(text)) is None:
        return False
    return _PRESET_NOUN_RE.search(text) is not None


def _matches_basic_color_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_COLOR_AXIS_RE):
        return True
    scoped = _PRESET_COLOR_PHASER_COMPOUND_RE.sub(" ", _without_combo_tokens(text))
    return _designates(scoped, _PRESET_COLOR_AXIS_RE)


def _matches_basic_dimmer_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_DIMMER_AXIS_RE):
        return True
    scoped = _PRESET_DIMMER_PHASER_COMPOUND_RE.sub(" ", _without_combo_tokens(text))
    return _designates(scoped, _PRESET_DIMMER_AXIS_RE)


def _matches_color_phaser_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_COLOR_AXIS_RE):
        return True
    scoped = _without_combo_tokens(text)
    if (
        _PRESET_COLOR_AXIS_RE.search(scoped) is not None
        and _PRESET_PHASER_QUALIFIER_RE.search(scoped) is not None
    ):
        return True
    return _reads_as_bare_phaser(text)


def _matches_dimmer_phaser_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _reads_as_unqualified_axis(_without_combo_tokens(text), _PRESET_DIMMER_AXIS_RE):
        return True
    scoped = _without_combo_tokens(text)
    if (
        _PRESET_DIMMER_AXIS_RE.search(scoped) is not None
        and _PRESET_PHASER_QUALIFIER_RE.search(scoped) is not None
    ):
        return True
    return _reads_as_bare_phaser(text)


def _matches_combo_phaser_family(text: str) -> bool:
    if not _preset_store_request(text):
        return False
    if _reads_as_all_families(text):
        return True
    if _PRESET_COMBO_AXIS_RE.search(text) is not None:
        return True
    return _reads_as_bare_phaser(text)


@dataclass(frozen=True)
class PresetFamily:
    """프리셋 계열 하나 — 다중 선택 카드의 한 줄이자 순차 실행의 한 단위.

    `matches`는 필드에 담긴 순수 함수라 `family.matches(text)`로 부른다
    (인스턴스 속성 조회이므로 self가 끼지 않는다).
    """

    key: str
    label: str
    matches: Callable[[str], bool]


#: 계열 순서가 계약이다 — 선택 카드의 줄 순서이자 순차 실행 순서다. 번호 규율은
#: 계열마다 자기 카드를 그대로 낸다: `Store Preset`은 경고 없이 덮어쓰므로 시작
#: 번호는 문장의 「N번부터」나 계열별 질문 카드에서만 온다.
#:
#: **7계열 × 10종 = 70종**이 이 앱의 프리셋 세트 전부다. FX 포지션(조명연출용
#: 기하 골격)은 기본 포지션과 같은 Position 풀을 쓰지만 카탈로그가 다른 별도
#: 계열이라 바로 뒤에 둔다 — 처음 등록에서 빠져 카드에 60종만 올랐다.
PRESET_FAMILIES: tuple[PresetFamily, ...] = (
    PresetFamily("basic_position", "기본 포지션", _matches_basic_position_family),
    PresetFamily("fx_position", "연출 포지션", _matches_fx_position_family),
    PresetFamily("basic_color", "기본 컬러", _matches_basic_color_family),
    PresetFamily("basic_dimmer", "기본 디머", _matches_basic_dimmer_family),
    PresetFamily("color_phaser", "컬러 페이저", _matches_color_phaser_family),
    PresetFamily("dimmer_phaser", "디머 페이저", _matches_dimmer_phaser_family),
    PresetFamily("combo_phaser", "콤보 페이저", _matches_combo_phaser_family),
)

# 페이저 recall(T11) — 저장된 카탈로그 30종(컬러/디머/콤보 페이저)을
# 소비(즉시 발사·해제·시퀀스화)하는 어휘. 저장·재생성 가족은 포괄 어휘축
# (멀티컬러/디머 이펙트/콤보 등)으로 문장을 매치하고, 여기는 반대로 라벨
# 자체(예: 'Breathe Warm')가 문장에 있어야만 발동한다 — 두 축이 사용하는
# 토큰 집합이 겹치지 않으므로(저장 문장에는 카탈로그 라벨이 없다) 디스패치
# 등록 순서를 저장·재생성 가족들보다 뒤에 둬도 그 문장들을 삼키지 않는다.
_PHASER_LABEL_POOL_NAME: dict[str, str] = {
    **{label: "Color" for label, *_ in COLOR_PHASER_SEQUENCE},
    **{label: "Dimmer" for label, *_ in DIMMER_PHASER_SEQUENCE},
    **{label: "All 1" for label, *_ in COMBO_PHASER_SEQUENCE},
}
#: 긴 라벨을 먼저 검사 — 한 라벨이 다른 라벨의 부분 문자열이 되는 사고를
#: 막는다(현재 30종 라벨 자체는 서로소이지만, 방어적으로 유지).
_PHASER_CATALOG_LABELS_BY_LENGTH: tuple[str, ...] = tuple(
    sorted(_PHASER_LABEL_POOL_NAME, key=len, reverse=True)
)

# 발사 동사 — '재생'은 '재생성'(가족 재생성 어휘)의 부분 문자열이므로 부정
# 전방탐색으로 그 겹침을 막는다(재생성 문장은 이미 위 재생성 가족들이
# 먼저 가로챈다는 전제와 별개로, 라벨+동사 조합만으로 재생성 문장을
# 오인식하지 않기 위한 이중 방어).
_PHASER_RECALL_VERB = re.compile(r"쳐\s*줘|쏴|걸어|발사|틀어|재생(?!성)", re.IGNORECASE)
# 해제 동사 — 발사 동사와 서로소(빼/꺼/해제/off/클리어는 발사 동사 목록에
# 없는 토큰).
_PHASER_RELEASE_VERB = re.compile(r"빼|꺼|해제|off|클리어", re.IGNORECASE)
# 2단계(시퀀스+실행기) 전용 명사 — 1단계(즉시 발사)와의 서로소는 이 명사의
# 유무로 가르고, 디스패치 등록 순서(2단계가 1단계보다 앞)로 고정한다.
_PHASER_RECALL_NOUN = re.compile(r"시퀀스|실행기|exec", re.IGNORECASE)


def _match_phaser_label(text: str) -> str | None:
    """문장에서 카탈로그 30종 라벨 중 하나를 찾는다 — 못 찾으면 None."""
    folded = text.casefold()
    for label in _PHASER_CATALOG_LABELS_BY_LENGTH:
        if label.casefold() in folded:
            return label
    return None


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


@dataclass(frozen=True)
class LayoutImageUpload:
    """One session's most-recently attached layout image (SPEC-COPILOT-IMGLAYOUT-001 M1).

    Ephemeral and WS-session-scoped, same as ``_UploadedVectorworksExport`` —
    but a new upload REPLACES the field wholesale (contract §1) rather than
    mutating in place, so the dataclass itself can stay frozen.
    """

    file_name: str
    mime_type: str
    content_base64: str


@dataclass(frozen=True)
class SongAudioUpload:
    """이 세션에 가장 최근 붙은 곡 오디오 한 개 (SPEC-COPILOT-MUSICSYNC-001 M2).

    ``LayoutImageUpload``·``UploadedSheet`` 와 같은 형태다: 불변이고, 새 업로드가
    통째로 교체하며, 교체 사실을 소리 내어 말한다.

    ``sha256`` 과 ``byte_length`` 는 **디코드된 바이트** 기준이다(base64 문자열이
    아니다) — 운영자가 원본 파일의 ``shasum -a 256`` 값과 대조할 수 있어야 한다.
    """

    file_name: str
    mime_type: str
    content_base64: str
    sha256: str
    byte_length: int


@dataclass(frozen=True)
class UploadedSheet:
    """SPEC-COPILOT-SHEETPIPE-001 M1 — 판별을 통과한 시트 한 장 (REQ-SHEETPIPE-001).

    ``LayoutImageUpload``와 같은 형태다: 불변이고, 새 업로드가 통째로 교체한다.
    그 선택이 노출 방식을 강제한다(REQ-SHEETPIPE-002) — 이 필드를
    ``build_toolset``에 그대로 넘기면 세션 생성 시점의 ``None``이 툴 클로저에
    영구히 얼어붙으므로 반드시 :class:`_UploadedSheetView`를 거쳐야 한다.
    한 ``build_toolset`` 호출 안에 두 형태가 동시에 살아 있다 — 가변
    ``_vectorworks_upload``는 필드를 직접 넘기고 불변 ``_layout_image``는 뷰를
    거친다 — 그래서 짝을 섞기 쉽고, 섞여도 조용하다.

    ``sha256``과 ``byte_length``는 디코드된 바이트 기준이다(base64 문자열이
    아니다): 운영자가 원본 파일의 ``shasum -a 256`` 값과 대조할 수 있어야 한다.
    """

    file_name: str
    kind: str
    content_base64: str
    sha256: str
    byte_length: int


def _count_patch_rows(data: bytes) -> str:
    parsed = parse_patch_csv(data.decode("utf-8-sig"))
    return (
        f"records {len(parsed.records)}건 · rejected {len(parsed.rejected)}건 · "
        f"excluded {len(parsed.excluded)}건"
    )


#: 종류별 행 수 판독기 (REQ-SHEETPIPE-004).
#:
#: A의 레지스트리에는 행 수를 세는 훅이 없다 — 행은 ``target``과
#: ``passthrough_args``만 든다. 그래서 "어느 통을 센 수인지"를 낼 수 있는 표는
#: B가 따로 들어야 하고, LXSEQ-002/003/004가 A에 행을 더할 때 이 표도 함께
#: 늘어난다. 그 사실은 plan.md §E의 "B는 열리지 않는다"와 어긋나므로 숨기지 않고
#: 여기 적어 둔다.
_SHEET_ROW_COUNTERS = dict()
_SHEET_ROW_COUNTERS["patch"] = _count_patch_rows


def _count_group_rows(data: bytes) -> str:
    """GROUP 시트의 데이터 행 수 — 첨부 안내에 싣는 한 줄."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "행 수를 세지 못했다"
    rows = [line for line in text.splitlines() if line.strip()]
    return f"그룹 {max(len(rows) - 1, 0)}개"


_SHEET_ROW_COUNTERS["group"] = _count_group_rows


def _count_preset_rows(data: bytes) -> str:
    """PRESET 시트의 데이터 행 수 — 첨부 안내에 싣는 한 줄.

    **읽는 수이지 넣는 수가 아니다.** 시트의 모든 행이 콘솔에 넣을 수 있는 값은
    아니어서, 실제 계획 수는 툴이 판정한다. 여기서 「N개」라고만 말하면 운영자가
    그 수만큼 들어갈 것으로 읽으므로 「행」이라고 적는다.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "행 수를 세지 못했다"
    rows = [line for line in text.splitlines() if line.strip()]
    return f"프리셋 시트 {max(len(rows) - 1, 0)}행"


_SHEET_ROW_COUNTERS["preset-dim"] = _count_preset_rows
_SHEET_ROW_COUNTERS["preset-col"] = _count_preset_rows
_SHEET_ROW_COUNTERS["preset-bm"] = _count_preset_rows


def _count_cue_rows(data: bytes) -> str:
    """CUE-EX 시트의 데이터 행 수 -- 첨부 안내에 싣는 한 줄. long format(한 큐
    x 한 그룹 = 한 행)이라 이 수가 곧 계획할 행 수다. 고유 큐 수도 함께
    싣는다 -- 행 수만 보이면 부분집합인지 알 수 없다.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "행 수를 세지 못했다"
    parsed = parse_cue_csv(text)
    return (
        f"레코드 {len(parsed.records)}건 · 큐 {len(parsed.cue_numbers)}개 · "
        f"rejected {len(parsed.rejections)}건"
    )


_SHEET_ROW_COUNTERS["cue-ex"] = _count_cue_rows

#: 첨부 이음매가 배선한 세션 메서드 이름 (SPEC-COPILOT-SHEETPIPE-001 결정 A).
#:
#: 레지스트리의 ``session_method`` 종 행은 이 자리로 온다. 이음매가 보낼 곳을
#: 아는 이름만 여기 있으며, 여기 없는 이름은 조용히 삼키지 않고 이름으로
#: 거절한다. 리터럴이 아니라 표로 두는 이유는 종류를 더하는 사람이 만져야 하는
#: 자리를 검사가 셀 수 있어야 하기 때문이다 (server/tests/test_sheet_kind_consumers.py).
_ATTACH_ROUTED_SESSION_METHODS = ("upload_vectorworks_export",)


def _sheet_row_counts(kind: str, data: bytes) -> str:
    """행 수는 이름 붙은 수다 (REQ-SHEETPIPE-004).

    ``ParseResult``는 ``records`` · ``rejected`` · ``excluded`` 세 통으로
    나뉘므로 맨 숫자 하나는 어느 통인지 말하지 않는다 — "행 12건"이라 적고 그중
    3건이 거부됐다면 그것은 운영자를 잘못 안심시키는 문장이다. 세 통을 전부
    이름과 함께 낸다.

    파싱은 종류가 정해진 뒤 정확히 한 번 돈다(A의 REQ-FILEARG-005). 모델에도
    콘솔에도 대상 툴에도 닿지 않는 국소 호출이므로 REQ-SHEETPIPE-003이 금지한
    "실행"이 아니다 — 그리고 0회여도 안 된다: 행 수를 낼 수 없기 때문이다.
    """
    counter = _SHEET_ROW_COUNTERS.get(kind)
    if counter is None:
        return "행 수 미상 — 이 종류의 행 수 판독기가 아직 없습니다"
    try:
        return counter(data)
    except Exception:
        return "행 수 판독 실패 — 파일은 담겼습니다"


def _base64_decoded_size(content_base64: str) -> int:
    """Decoded byte count of a PADDED base64 string, by length arithmetic.

    Exact for the input this receives: ``parse_client_message`` already ran
    ``b64decode(validate=True)``, so the string is well-formed base64 whose
    length is a multiple of 4 with 0–2 trailing ``=``. Each 4-char group
    encodes 3 bytes and each padding ``=`` removes exactly one byte:
    ``len * 3 // 4 - padding``. Arithmetic instead of a second decode because
    validation already paid the decode once — re-decoding a 5 MiB image just
    to print its size in an ack would allocate the whole payload again
    (security review IMG-SEC-05).
    """
    padding = len(content_base64) - len(content_base64.rstrip("="))
    return len(content_base64) * 3 // 4 - padding


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
    #: 카드 t305 — ``sections`` 는 마디 경계에서 쪼갠 **큐** 목록이다. 이
    #: 목록은 큐마다 원래 구간 번호(0-based)를 들고 있어서 연출 아크가 구간
    #: 단위로 유지된다. 비어 있으면 항등(쪼개기 전과 동일).
    section_origin: list[int] = dataclass_field(default_factory=list)
    #: 카드 t311 — 좌표를 못 읽어 포지션(무브) 축을 비활성으로 둔 사유. 빈
    #: 문자열이면 축이 살아 있고 오늘 이전과 문면이 같다.
    position_disabled_reason: str = ""
    #: 카드 t430 — W 채널 확인 기구(`_w_capable_fids` w_capable). 빈
    #: 집합이면 오늘과 동일(모든 기구가 RGB 줄만 받는다). 열거 실패·판독
    #: 불가는 빈 집합으로 남는다(무대 색 변화 0 — fail-closed).
    w_fids: frozenset[int] = dataclass_field(default_factory=frozenset)


@dataclass(frozen=True)
class _SongTimedCueExpectation:
    cue_no: float
    trig_time: str


@dataclass(frozen=True)
class _SongReadbackResult:
    paths: tuple[str, ...]
    failure: str | None = None


#: 안전 게이트가 명령을 **보류**한 상태들. 보류된 저장은 **당연히** 풀에 없으므로
#: 되읽기가 이를 미확인 결함으로 보고하면 정상 워크플로에서 상시 거짓 경보가 나고,
#: 무시되는 경보는 진짜 미착지도 함께 가린다 (REQ-PRESETGUARD-009).
#: 승인되면 착지할 수 있는 **보류** 상태.
_PRESET_GATE_AWAITING_STATUSES = frozenset({"proposal", "held"})

#: 게이트가 **차단/거부**한 상태 — 승인을 기다려도 착지하지 않는다. AC-009는 이들을
#: 미확인 결함으로 세지 말라고 요구할 뿐 **문면까지 지정하지는 않는다.** 이를
#: "승인 후 반영"으로 렌더하면 이미 부정 확정됐거나 오지 않을 승인을 기다리라고 말하게
#: 되므로, 분류는 보류로 유지하되 문면을 분리한다.
_PRESET_GATE_BLOCKED_STATUSES = frozenset({"blocked", "rejected", "locked"})

_PRESET_GATE_PENDING_STATUSES = _PRESET_GATE_AWAITING_STATUSES | _PRESET_GATE_BLOCKED_STATUSES

#: 확인 카드가 제시하는 승낙 버튼 라벨. 정확 일치가 **가장 강한 신호**다.
_PRESET_OVERWRITE_CONSENT_LABEL = "덮어쓰기 진행"
_PRESET_OVERWRITE_DECLINE_LABEL = "취소"

#: 실행기 할당 제안 카드의 버튼 라벨과 제안 대역(101~115). '걸기'는 승낙어
#: 집합에 없으므로 라벨 정확 일치를 별도 승낙 신호로 받는다.
_FX_EXECUTOR_ASSIGN_LABEL = "걸기"
_FX_EXECUTOR_SKIP_LABEL = "건너뛰기"
_FX_EXECUTOR_BAND = tuple(range(101, 116))

#: 승낙 어절에서 떼어내는 존대·청유 어미. 형태만 다른 **같은 답**을 받기 위한
#: 것이지 부분 문자열 매칭이 아니다 — 어미를 뗀 어절이 승낙어와 **통째로** 같아야
#: 한다. 긴 것부터 떼어야 "해주세요"가 "요"로 잘리지 않는다.
_PRESET_ANSWER_SUFFIXES = (
    "해주십시오",
    "해주세요",
    "해 주세요",
    "해줄래",
    "해줘요",
    "해주면",
    "해줘",
    "합니다",
    "할게요",
    "하세요",
    "해요",
    "할게",
    "하자",
    "하지",
    "해",
    "이에요",
    "예요",
    "입니다",
    "이요",
    "요",
    "죠",
)

#: 승낙으로 인정하는 어절(어미를 뗀 형태). 부분 문자열 매칭은 쓰지 않는다.
#:
#: `확인`·`네`·`예`·`응`은 평범한 한국어 단어의 조각이라 부분 매칭으로는 비승낙을
#: 승낙으로 삼킨다 — 실측: "잠깐 확인해보고요" · "안 되네요" · "확인 안 했어요" ·
#: "네가 판단해" · "예전 값으로 되돌려줘" 다섯 문장이 전부 승낙으로 읽혀 비가역
#: 덮어쓰기가 나갔다. 그래서 판정은 **어절 단위**다: 답을 공백으로 쪼개고 각
#: 어절에서 어미를 뗀 뒤, **모든 어절이** 승낙어여야 승낙이다. 이러면 "네"는
#: 승낙이지만 "네가 판단해"의 "네가"는 아니다 — 한 글자 승낙어가 다른 단어 안에
#: 숨어들 수 없다. `확인`은 그 자체로 "확인해보겠다"와 구별되지 않으므로
#: **어떤 형태로도** 승낙이 아니다.
_PRESET_CONSENT_WORDS = frozenset(
    {
        "덮어쓰기",
        "덮어써",
        "덮어쓰",
        "덮어쓸게",
        "덮어쓰자",
        "진행",
        "승인",
        "좋아",
        "네",
        "넵",
        "예",
        "응",
        "yes",
        "y",
        "ok",
        "okay",
        "오케이",
    }
)

#: 명시적 거절 어절. 승낙과 **같은 어절 규칙**으로 판정한다 — 부분 문자열로 찾으면
#: "취소하지 마"(= 취소하지 말라 = 승낙)가 거절로 읽힌다.
_PRESET_DECLINE_WORDS = frozenset(
    {
        "취소",
        "아니",
        "아니요",
        "아뇨",
        "중단",
        "그만",
        "보류",
        "안돼",
        "안됨",
        "no",
        "n",
        "cancel",
        "stop",
    }
)


def _preset_answer_words(answer: str) -> list[str]:
    """답을 어절로 쪼개고 각 어절에서 존대·청유 어미를 뗀다."""
    words: list[str] = []
    for raw in answer.split():
        word = raw.strip(" .!?~,·'\"()").casefold()
        for suffix in _PRESET_ANSWER_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix):
                word = word[: -len(suffix)]
                break
        if word:
            words.append(word)
    return words


def _preset_answer_intent(answer: str) -> str:
    """카드 응답의 의도 — ``consent`` · ``decline`` · ``unrecognised``.

    **모든** 어절이 같은 부류여야 그 부류로 판정한다. 하나라도 섞이거나 모르는
    말이면 ``unrecognised``이고, 그때 저장하지 않는 것은 승낙과 마찬가지로
    fail-closed다 — 다만 회신 문면이 다르다. 거절과 "못 알아들음"을 같은 말로
    묶으면 운영자가 거절한 적 없는데 거절했다고 통보받고, 무엇이 잘못됐는지 모르는
    채 같은 답을 반복하게 된다.
    """
    words = _preset_answer_words(answer)
    if not words:
        return "unrecognised"
    if all(word in _PRESET_CONSENT_WORDS for word in words):
        return "consent"
    if all(word in _PRESET_DECLINE_WORDS for word in words):
        return "decline"
    return "unrecognised"


@dataclass(frozen=True)
class _PresetSpanVerdict:
    """겹침 확인 카드의 판정 — 5상태(plan.md §B M1).

    ``clear``(검증된 빈칸)와 ``unverified``(풀 판독 실패)는 둘 다 진행하지만
    **절대 병합하지 않는다**: 병합하면 판독 실패가 *"검사했고 비어 있었다"* 로
    위장되며, 그것이 이 SPEC이 닫으려는 결함과 같은 형상이다.
    """

    state: str
    collisions: tuple[int, ...] = ()
    #: 판정이 가리키는 풀 — 문면(슬롯 표기·풀 이름)만 바꾸고 판정 로직은 풀
    #: 무관이다(REQ-COLORPRESET-003: 컬러 전용 카드·어휘 신설 금지). 기본값이
    #: 오늘의 Position이라 기존 생성 지점은 무수정 동작 동일(REQ-COLORPRESET-006).
    pool_no: int = POSITION_PRESET_POOL
    pool_label: str = "Position"

    @property
    def proceed(self) -> bool:
        return self.state in ("clear", "unverified", "confirmed")

    @property
    def approval_advisory(self) -> str:
        """**쓰기 전** 승인 카드에 실을 사실 — 판정 시점에 이미 아는 것만.

        ``unverified``만 여기 실린다. 판독 실패는 되돌릴 수 없는 쓰기를 승인할지
        고르는 사람이 **누르기 전에** 알아야 하는 사실인데, ``note``는 완료된
        저장 결과와 함께 조립되므로(``_preset_reply_text``) 쓰기가 끝난 뒤에야
        닿는다. ``confirmed``는 방금 그 운영자가 승낙한 사실이라 카드에 되싣지
        않고, ``clear``는 실을 것이 없다 — 마찰은 손실 가능성이 있는 자리에만
        놓인다(REQ-PRESETGUARD-005).
        """
        return self.note if self.state == "unverified" else ""

    @property
    def note(self) -> str:
        """회신에 덧붙일 문장 — 진행 사유를 형용사가 아닌 상태로 적는다."""
        if self.state == "unverified":
            return f"{self.pool_label} 풀을 읽지 못해 기존 점유를 확인하지 못했습니다."
        if self.state == "confirmed":
            return "덮어쓰기 승인: " + _preset_slot_list(self.collisions, self.pool_no) + "."
        return ""


@dataclass(frozen=True)
class _PresetStoreRun:
    """저장 루프 1회분 — 신규 저장과 재생성이 **공유**한다.

    두 경로가 각자 루프를 가지면 룩별 독립 번들·``ClearAll``·라벨 규율이
    한쪽만 퇴행한다(plan.md §E 위험 2).
    """

    outcomes: tuple[CommandOutcome, ...]
    stored: tuple[str, ...]
    skipped_notes: tuple[str, ...]
    expected: Mapping[int, str]
    #: 슬롯 → 게이트 처분 (`"awaiting"` 승인 대기 · `"blocked"` 차단·거부).
    #: 둘 다 미확인 결함으로 세지 않지만 회신 문면은 갈린다 — 차단된 저장은
    #: 승인을 기다려도 오지 않는다.
    pending: Mapping[int, str]
    #: 저장 **직전**의 풀 점유. 사전에 이미 차 있던 슬롯은 되읽기에서 "확인"으로
    #: 셀 수 없다(F3) — 응답기가 슬롯 번호(`i`)만 보내므로 내용이 바뀌었는지
    #: 관측할 수단이 없기 때문이다. `None`이면 판독 자체가 실패한 것이다.
    before: frozenset[int] | None = None


def _preset_slot_list(slots: Sequence[int], pool_no: int = POSITION_PRESET_POOL) -> str:
    return ", ".join(f"{pool_no}.{no}" for no in slots)


def _preset_recall_command(pool_no: int, fids: Sequence[int], preset_no: int) -> str:
    """``Fixture <fids> ; At Preset <pool>.<n>`` — 풀 일반형 recall 명령 빌더.

    ``pointing.preset_recall_command``의 문면·규칙(양수 preset_no, 빈 fids
    거부)을 임의 풀 번호에 적용한다 — ``_preset_store_commands``와 같은 세션
    계층 일반화(REQ-COLORPRESET-007, pool_no=2 출력은 문자 단위로 동일)이고,
    실측 문법 출처는 T11 프로브 §2(Color/Dimmer/All 1 3풀 전부 수락)다.
    """
    if not isinstance(pool_no, int) or isinstance(pool_no, bool) or pool_no <= 0:
        # 대칭 검증 — _preset_store_commands와 같은 이유(SEC-CMD-003).
        raise SpatialPointingError(f"pool number {pool_no!r} must be a positive integer")
    if preset_no <= 0:
        raise SpatialPointingError(f"preset number {preset_no!r} must be positive")
    if not fids:
        raise SpatialPointingError("no fixtures to recall the preset on")
    selection = " + ".join(str(fid) for fid in fids)
    return f"Fixture {selection} ; At Preset {pool_no}.{preset_no}"


def _preset_release_command(fids: Sequence[int]) -> str:
    """``Fixture <fids> ; At Preset 0`` — T11 프로브 §3 실측 해제 문법.

    ``Off`` 단독 명령도 응답기가 수락하지만(같은 프로브), 셀렉터 없이 실행하면
    그 순간 프로그래머에 남아 있는 임의의 선택을 해제해 recall과 무관한
    장비의 값을 지울 위험이 있다 — 이 형태는 recall과 동일한 셀렉터 접두를
    재사용해 항상 그 페이저가 실린 장비로만 해제를 좁힌다. 셀렉터 뒤에
    ``Off``를 이어붙이는 형태(``Group 11 Off``)는 응답기가 'Not implemented'로
    거부하므로(같은 프로브) 쓰지 않는다.
    """
    if not fids:
        raise SpatialPointingError("no fixtures to release the preset on")
    selection = " + ".join(str(fid) for fid in fids)
    return f"Fixture {selection} ; At Preset 0"


def _phaser_sequence_commands(
    pool_no: int,
    fids: Sequence[int],
    preset_no: int,
    sequence_no: int,
    label: str,
    *,
    cue_fade: int = 2,
) -> tuple[str, ...]:
    """``ChangeDestination Root`` → recall → 1큐 ``Store Sequence`` 번들.

    ``position_fx.position_fx_commands``의 프리앰블·라벨 검증 규율(``ChangeDestination
    Root``·``ClearAll``·따옴표 거부)을 미러하되, 그 모듈은 Position 풀(2)
    고정이라 임의 풀(Color/Dimmer/All 1)을 받을 수 없다 — 이 함수가 그
    일반형이다(``_preset_recall_command``와 같은 세션 계층 일반화, T11 프로브
    §2/§4 실측: recall 1줄 뒤 ``Store Sequence <n> Cue 1 '<label>' CueFade
    <f>``가 성공한다). ``/Merge``·``/Overwrite``는 절대 쓰지 않는다(단일
    큐라 필요 없음) — spatial(position_fx.py/pointing.py)은 무접촉이다.
    """
    if sequence_no <= 0:
        raise SpatialPointingError(f"sequence number {sequence_no!r} must be positive")
    if cue_fade < 0:
        raise SpatialPointingError(f"cue fade {cue_fade!r} must be non-negative")
    text = label.strip()
    if not text or "'" in text or '"' in text:
        raise SpatialPointingError(f"sequence label {label!r} is empty or carries a quote")
    recall = _preset_recall_command(pool_no, fids, preset_no)
    return (
        "ChangeDestination Root",
        "ClearAll",
        recall,
        f"Store Sequence {sequence_no} Cue 1 '{text}' CueFade {cue_fade}",
        f"Label Sequence {sequence_no} '{text}'",
        "ClearAll",
    )


def _color_apply_command(fids: Sequence[int], rgb: tuple[int, int, int]) -> str:
    """한 색을 컬러 가능 장비 전체에 싣는 **한 줄** 체인 (spec §B REQ-003).

    ``aimed_commands``의 한 줄 규율과 같은 이유(텍스트 중복 제거 방어)로
    선택과 세 어트리뷰트를 ``;``로 묶는다 — 문법은 룰북 라이브 검증분만
    (``Attribute 'ColorRGB_R' At <0-100>``, G/B 동일).
    """
    selection = " + ".join(str(fid) for fid in fids)
    r, g, b = rgb
    return (
        f"Fixture {selection} ; Attribute 'ColorRGB_R' At {r} ; "
        f"Attribute 'ColorRGB_G' At {g} ; Attribute 'ColorRGB_B' At {b}"
    )


#: 컬러 채널 3종 — 페이저 Form/레이어 명령은 R/G/B 세 채널 모두에 동일하게
#: 실어야 한 스텝의 색이 채널별로 다른 커브로 어긋나지 않는다.
_COLOR_PHASER_CHANNELS: tuple[str, ...] = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")


def _color_phaser_step_commands(
    fids: Sequence[int], rgbs: Sequence[tuple[int, int, int]]
) -> tuple[str, ...]:
    """멀티스텝 컬러 페이저를 프로그래머에 싣는 커맨드라인 시퀀스.

    라이브 실측(``08-color-phaser-m0-probe.md`` §1-B/§6.2): 첫 스텝은
    ``Fixture <fids> ; Attribute 'ColorRGB_R/G/B' At <n>``로 선택+값을 함께
    싣고, 이후 스텝은 선택이 프로그래머에 남아 있으므로 ``Step N`` 다음
    값 3줄만 보낸다 — 재선택하지 않는다. ``Step N`` 직후 곧바로 다음 스텝
    값을 잇고, ``Store Preset``은 이 함수 밖(``_preset_store_commands``,
    무수정)에서 별도로 붙는다 — Step 명령과 Store 명령을 합치지 않는다는
    함정①의 안전 순서를 그대로 따른다(같은 문서 §3, 재현되지 않았지만
    보수적으로 유지).

    2스텝(Breathe/Chase/Wave/Pulse/Duo/Slam)과 3스텝(Rainbow) 둘 다 라이브
    확인됨.
    """
    if len(rgbs) < 2:
        raise SpatialPointingError(f"color phaser needs at least 2 steps, got {len(rgbs)}")
    selection = " + ".join(str(fid) for fid in fids)
    commands: list[str] = []
    for step_no, (r, g, b) in enumerate(rgbs, start=1):
        chain = (
            f"Attribute 'ColorRGB_R' At {r} ; Attribute 'ColorRGB_G' At {g} ; "
            f"Attribute 'ColorRGB_B' At {b}"
        )
        if step_no == 1:
            commands.append(f"Fixture {selection} ; {chain}")
        else:
            commands.append(f"Step {step_no}")
            commands.append(chain)
    return tuple(commands)


def _color_phaser_form_commands(form: str) -> tuple[str, ...]:
    """Form 레이어 근사 — Sine은 라이브 검증됨, Rectangle은 ASSUMPTION.

    ``05-phaser-editor.md`` §4: Form 버튼은 Transition+Accel+Decel 레이어의
    단축키일 뿐 명령줄 키워드가 없다. Sine ≈ Accel −100 / Decel −100은
    R/G/B 세 채널 모두에서 라이브 수락 확인(``08-…-probe.md`` §3). Rectangle
    후보(Transition 0 / Accel 0 / Decel 0)는 §6.1에서 **명령 자체는 거부되지
    않음**을 확인했지만, 하드컷 파형이 실제로 만들어지는지(공식 Accel/Decel
    수치가 없음)는 이 저장소 구조상(OSC/Lua만, 화면을 볼 수 없음) 확인할 수
    없다 — Rectangle 커브는 검증되지 않은 근사치임을 여기 명시한다.
    """
    if form == "sine":
        curve = -100
    elif form == "rectangle":
        curve = 0
    else:
        raise SpatialPointingError(f"unknown color phaser form {form!r}")
    commands = [f"Attribute '{channel}' At Accel {curve}" for channel in _COLOR_PHASER_CHANNELS]
    commands += [f"Attribute '{channel}' At Decel {curve}" for channel in _COLOR_PHASER_CHANNELS]
    if form == "rectangle":
        commands += [f"Attribute '{channel}' At Transition 0" for channel in _COLOR_PHASER_CHANNELS]
    return tuple(commands)


def _color_phaser_phase_command(phase: str) -> str:
    """Phase 분산 — ``ColorRGB_R`` 한 채널에만 싣는다(레이어는 세트로 저장되므로
    한 채널만으로 충분, ``05-phaser-editor.md`` §5). ``"0"``/``"180"``/``"0 Thru
    360"`` 세 토큰 다 라이브 수락 확인됨(``08-…-probe.md`` §3/§6.3).
    """
    return f"Attribute 'ColorRGB_R' At Phase {phase}"


def _dimmer_apply_command(fids: Sequence[int], value: int) -> str:
    """한 디머 레벨을 대상 픽스처 전체에 싣는 **한 줄** 체인 —
    ``_color_apply_command``의 단일 채널('Dimmer') 미러(T4 프로브 §1 문법)."""
    selection = " + ".join(str(fid) for fid in fids)
    return f"Fixture {selection} ; Attribute 'Dimmer' At {value}"


def _dimmer_phaser_step_commands(fids: Sequence[int], values: Sequence[int]) -> tuple[str, ...]:
    """멀티스텝 디머 페이저를 프로그래머에 싣는 커맨드라인 시퀀스.

    ``_color_phaser_step_commands``의 단일 채널 미러 — 라이브 실측
    (``09-dimmer-phaser-m0-probe.md`` §2/§3): 첫 스텝은 ``Fixture <fids> ;
    Attribute 'Dimmer' At <n>``로 선택+값을 함께 싣고, 이후 스텝은 선택이
    프로그래머에 남아 있으므로 ``Step N`` 다음 값 1줄만 보낸다. 2스텝
    (Breathe/Pulse/Wave/Flash/Alt/Slam)과 3스텝(Ripple) 둘 다 라이브 확인됨
    (같은 문서 §2/§3, 함정① 무재현).
    """
    if len(values) < 2:
        raise SpatialPointingError(f"dimmer phaser needs at least 2 steps, got {len(values)}")
    selection = " + ".join(str(fid) for fid in fids)
    commands: list[str] = []
    for step_no, value in enumerate(values, start=1):
        chain = f"Attribute 'Dimmer' At {value}"
        if step_no == 1:
            commands.append(f"Fixture {selection} ; {chain}")
        else:
            commands.append(f"Step {step_no}")
            commands.append(chain)
    return tuple(commands)


def _dimmer_phaser_form_commands(form: str) -> tuple[str, ...]:
    """Form 레이어 근사 — ``_color_phaser_form_commands``의 단일 채널 미러.

    Sine(Accel −100/Decel −100)은 라이브 검증됨(``09-…-probe.md`` §2).
    Rectangle(Transition 0/Accel 0/Decel 0)은 컬러와 같은 사유로 ASSUMPTION —
    명령 자체는 거부되지 않지만(``08-…-probe.md`` §6.1과 동일 근사, 디머
    전용으로는 미시도) 하드컷 파형이 실제로 만들어지는지는 이 저장소 구조상
    (OSC/Lua만) 확인할 수 없다.
    """
    if form == "sine":
        curve = -100
    elif form == "rectangle":
        curve = 0
    else:
        raise SpatialPointingError(f"unknown dimmer phaser form {form!r}")
    commands = [f"Attribute 'Dimmer' At Accel {curve}", f"Attribute 'Dimmer' At Decel {curve}"]
    if form == "rectangle":
        commands.append("Attribute 'Dimmer' At Transition 0")
    return tuple(commands)


def _dimmer_phaser_phase_command(phase: str) -> str:
    """Phase 분산 — ``'Dimmer'`` 한 채널에 싣는다. ``"0"``/``"180"``/``"0 Thru
    360"`` 세 토큰 다 컬러 채널에서 라이브 수락 확인됨(``08-…-probe.md``
    §3/§6.3) — 디머 채널로는 문법 형태만 이식(같은 ``At Phase`` 커맨드).
    """
    return f"Attribute 'Dimmer' At Phase {phase}"


#: 콤보 채널 4종 — 컬러 3채널 + 디머 1채널. Form 레이어는 넷 모두에 동일하게
#: 실어야 한 스텝의 색·밝기가 채널별로 다른 커브로 어긋나지 않는다.
_COMBO_PHASER_CHANNELS: tuple[str, ...] = _COLOR_PHASER_CHANNELS + ("Dimmer",)


def _combo_phaser_step_commands(
    fids: Sequence[int], steps: Sequence[tuple[tuple[int, int, int], int]]
) -> tuple[str, ...]:
    """혼합(컬러+디머) 멀티스텝 페이저를 프로그래머에 싣는 커맨드라인 시퀀스.

    ``_color_phaser_step_commands``·``_dimmer_phaser_step_commands``를 한
    스텝에 합친 신설 빌더 — 기존 두 빌더는 문자 단위로 무수정이다. 각 스텝은
    컬러 RGB 3줄 + Dimmer 1줄을 한 체인으로 묶는다(T7 프로브 §2 항목 1/4/5
    실측 문법, ``10-combo-phaser-m0-probe.md``). 첫 스텝은 선택+값을 함께
    싣고, 이후 스텝은 선택이 프로그래머에 남아 있으므로 ``Step N`` 다음 값
    4줄만 보낸다 — 컬러/디머 단일축 빌더와 동일 규율. ``Step N``과
    ``Store Preset``은 이 함수 밖(``_preset_store_commands``)에서 별도로
    붙는다(함정①의 안전 순서, 재현되지 않았지만 보수적으로 유지).
    """
    if len(steps) < 2:
        raise SpatialPointingError(f"combo phaser needs at least 2 steps, got {len(steps)}")
    selection = " + ".join(str(fid) for fid in fids)
    commands: list[str] = []
    for step_no, ((r, g, b), dimmer) in enumerate(steps, start=1):
        chain = (
            f"Attribute 'ColorRGB_R' At {r} ; Attribute 'ColorRGB_G' At {g} ; "
            f"Attribute 'ColorRGB_B' At {b} ; Attribute 'Dimmer' At {dimmer}"
        )
        if step_no == 1:
            commands.append(f"Fixture {selection} ; {chain}")
        else:
            commands.append(f"Step {step_no}")
            commands.append(chain)
    return tuple(commands)


def _combo_phaser_form_commands(form: str) -> tuple[str, ...]:
    """Form 레이어 근사 — 컬러+디머 4채널 전부에 동일 레이어를 싣는다
    (``_color_phaser_form_commands``의 4채널 확장). Sine은 라이브 검증됨
    (컬러·디머 채널 각각 ``08-…-probe.md``/``09-…-probe.md``). Rectangle
    (Transition 0/Accel 0/Decel 0)은 여전히 ASSUMPTION — 명령 자체는
    거부되지 않지만(``08-…-probe.md`` §6.1) 하드컷 파형이 실제로 만들어
    지는지는 이 저장소 구조상(OSC/Lua만, 화면을 볼 수 없음) 확인할 수 없다.
    """
    if form == "sine":
        curve = -100
    elif form == "rectangle":
        curve = 0
    else:
        raise SpatialPointingError(f"unknown combo phaser form {form!r}")
    commands = [f"Attribute '{channel}' At Accel {curve}" for channel in _COMBO_PHASER_CHANNELS]
    commands += [f"Attribute '{channel}' At Decel {curve}" for channel in _COMBO_PHASER_CHANNELS]
    if form == "rectangle":
        commands += [f"Attribute '{channel}' At Transition 0" for channel in _COMBO_PHASER_CHANNELS]
    return tuple(commands)


def _combo_phaser_phase_command(phase: str) -> str:
    """Phase 분산 — ``ColorRGB_R`` 한 채널에만 싣는다(레이어는 세트로
    저장되므로 한 채널만으로 충분, 컬러/디머 페이저와 동일 규율).
    """
    return f"Attribute 'ColorRGB_R' At Phase {phase}"


def _preset_overwrite_refusal(verdict: _PresetSpanVerdict) -> str:
    """승낙 없이 끝난 카드의 회신. 침묵·거절·못 알아들음을 **구별해** 적는다.

    셋 다 저장하지 않는다는 점은 같지만 운영자가 다음에 할 일이 다르다. 못 알아들은
    것을 "승인받지 못했다"로 적으면 거절한 적 없는 사람에게 거절했다고 통보하는
    셈이고, 어떻게 답해야 하는지도 알려주지 않아 같은 답을 반복하게 만든다.
    """
    listed = _preset_slot_list(verdict.collisions, verdict.pool_no)
    if verdict.state == "unanswered":
        return (
            "덮어쓰기 확인 카드에 응답이 없어(UI 미연결 또는 무응답) 프리셋을 "
            f"저장하지 않았습니다 — 침묵은 승낙이 아니며, 덮어쓴 프리셋({listed})은 "
            "복구할 수 없습니다."
        )
    if verdict.state == "unrecognised":
        return (
            "덮어쓰기 확인 카드의 답을 승낙으로도 거절로도 읽지 못해 프리셋을 "
            f"저장하지 않았습니다 — 덮어쓸 대상은 {listed}입니다. "
            f"'{_PRESET_OVERWRITE_CONSENT_LABEL}' 또는 "
            f"'{_PRESET_OVERWRITE_DECLINE_LABEL}'로 답해 주세요."
        )
    return f"덮어쓰기를 승인받지 못해 프리셋을 저장하지 않았습니다: {listed}."


def _preset_pick_ready_span(named: Sequence[int], ready: Sequence[int]) -> int | None:
    """지목된 번호들이 후보 구간을 **정확히 하나** 가리킬 때만 그 구간을 낸다.

    재생성의 표적은 콘솔이 확인한 10칸 저장 구간이어야 한다. 후보 목록과 대조하지
    않으면 평범한 답이 엉뚱한 구간을 만든다 — *"2번째"*(두 번째라는 뜻)가 숫자 2로
    파싱돼 2.2~2.11을 덮어쓰면, 원래 구간은 한 칸 밀려 2.1을 참조하던 큐만 옛
    좌표에 남는다. 그 위에서 회신은 *"같은 자리에 다시 저장"* 이라 말한다.

    지목이 여럿이면(*"1번 말고 21번"*) 어느 쪽인지 알 수 없으므로 거절한다 —
    범위 검사만으로는 1도 후보일 때 잘못된 쪽을 고른다.
    """
    matched = {no for no in named if no in ready}
    return matched.pop() if len(matched) == 1 else None


def _preset_answer_to_ready_span(
    answer: str | None, ready: Sequence[int], pool_no: int = POSITION_PRESET_POOL
) -> int | None:
    """구간 선택 카드의 답 → 후보 구간. 특정하지 못하면 ``None``(저장 안 함)."""
    if answer is None:
        return None
    stripped = answer.strip()
    for start in ready:
        # 버튼을 그대로 눌렀을 때가 가장 강한 신호다. 라벨에는 "21 (2.21~2.30)"처럼
        # 숫자가 여럿 들어 있어 자릿수만 훑으면 오히려 모호해진다.
        if stripped in (str(start), f"{start} ({pool_no}.{start}~{pool_no}.{start + 9})"):
            return start
    return _preset_pick_ready_span([int(found) for found in re.findall(r"\d+", stripped)], ready)


def _preset_reply_text(
    run: _PresetStoreRun, verdict: _PresetSpanVerdict, readback: str, *, lead: str, tail: str
) -> str:
    """신규 저장과 재생성이 **공유**하는 회신 조립.

    두 경로의 회신 꼬리는 문구 몇 개만 다르고 나머지는 같았다. 되읽기 문면을
    고칠 때 두 곳을 각각 손대야 했고, 한쪽을 놓치면 조용히 갈라진다 — plan.md
    §E 위험 2가 저장 루프에 대해 지목한 드리프트 표면과 같은 것이다.
    """
    notes = f" 참고: {'; '.join(run.skipped_notes)}." if run.skipped_notes else ""
    guard_note = f" {verdict.note}" if verdict.note else ""
    readback_note = f" {readback}" if readback else ""
    return f"{lead}{notes}{guard_note}{readback_note} {tail}"


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
    capability; every write still rides the approval gate.

    ``setlist_sequence_nos`` (진행 순서 보드 연동, handoff 2026-08-15 item 3):
    the EXECUTED setlist allocation's slot order — written by the session's
    셋리스트 모드 only after its command bundle actually ran, read by the
    cue-monitor snapshot as the multi-song planned order. Same projection
    rule: a stored order is bookkeeping, never a console capability."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else None
        data = self._load()
        self._latest: dict | None = data.get("timeline") if data else None
        setlist = data.get("setlist") if data else None
        self._setlist: list[int] = (
            [no for no in setlist if isinstance(no, int)] if isinstance(setlist, list) else []
        )

    @property
    def latest(self) -> dict | None:
        return self._latest

    @latest.setter
    def latest(self, payload: dict | None) -> None:
        self._latest = payload
        if payload is not None:
            self._save()

    @property
    def setlist_sequence_nos(self) -> list[int]:
        return list(self._setlist)

    @setlist_sequence_nos.setter
    def setlist_sequence_nos(self, nos: list[int]) -> None:
        self._setlist = [no for no in nos if isinstance(no, int)]
        self._save()

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
        if not isinstance(timeline, dict):
            data = dict(data)
            data["timeline"] = None
        return data

    def _save(self) -> None:
        if self._path is None:
            return
        # Atomic same-dir temp + os.replace, mirroring PinStore._save — a crash
        # mid-write must leave the previous file intact.
        try:
            body = json.dumps(
                {"version": 1, "timeline": self._latest, "setlist": self._setlist},
                ensure_ascii=False,
            )
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


class PendingSongPlanStore:
    """Process-wide holder for the ONE pending (composed, not yet approved)
    song design (#2, 2026-08-16): a page refresh opens a NEW WebSocket
    session, and before this store that new session started with no pending
    plan — the director's un-stored edits were silently gone. Memory-only on
    purpose: `_SongDesignState` carries live interview/rig objects that have
    no JSON form, so a SERVER restart still clears it (disclosed in the
    structure-edit refusal). Holding a plan grants no console capability —
    every write still rides the approval gate."""

    def __init__(self) -> None:
        self.state: _SongDesignState | None = None


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


class _LayoutImageUploadView:
    """Adapts ``ChatSession._layout_image`` to ``LayoutImageUploadPort`` (M4).

    ``_layout_image`` is a ``LayoutImageUpload | None`` field that a new
    upload REPLACES wholesale (contract.md §1) — unlike
    ``_UploadedVectorworksExport``, it is never mutated in place. Passing
    ``self._layout_image`` straight into ``build_toolset`` at construction
    time would therefore freeze the pre-upload ``None`` into the
    ``analyse_layout_image`` tool closure forever. This view reads through to
    the CURRENT field on every access instead, so an upload that arrives
    after session construction is still visible to the tool.
    """

    def __init__(self, session: ChatSession) -> None:
        self._session = session

    @property
    def file_name(self) -> str | None:
        image = self._session._layout_image
        return image.file_name if image is not None else None

    @property
    def mime_type(self) -> str | None:
        image = self._session._layout_image
        return image.mime_type if image is not None else None

    @property
    def content_base64(self) -> str | None:
        image = self._session._layout_image
        return image.content_base64 if image is not None else None


class _SongAnalysisView:
    """``ChatSession._song_analysis`` 를 ``SongAnalysisPort`` 에 맞춘다 (SONGCONFIRM-001).

    ``_UploadedSheetView`` 와 같은 이유로 존재한다: 확정 기록은 카드가 끝난 뒤에야
    생기고 새 업로드가 통째로 지우는 필드라, 세션 생성 시점의 값을 그대로
    ``build_toolset`` 에 넘기면 ``None`` 이 ``prepare_songcue`` 클로저에 얼어붙는다.
    이 뷰는 접근할 때마다 현재 필드를 다시 읽는다(REQ-SONGCONFIRM-009).
    """

    def __init__(self, session: ChatSession) -> None:
        self._session = session

    @property
    def current(self) -> ConfirmedSongAnalysis | None:
        return self._session._song_analysis


class _SongInterviewRecordsView:
    """``ChatSession._song_interview_records`` 를 ``InterviewRecordsPort`` 에
    맞춘다 (카드 t441, SPEC-LDDESIGN-001 REQ-003).

    ``_SongAnalysisView`` 와 같은 이유로 존재한다: 인터뷰 기록은 그 인터뷰가
    끝난 뒤에야 생기고(``_song_design_interview_run``), 세션 생성 시점의
    빈 값을 그대로 ``build_toolset`` 에 넘기면 ``prepare_songcue`` 클로저에
    얼어붙는다. 이 뷰는 접근할 때마다 현재 필드를 다시 읽는다. 비어 있으면
    ``None`` — ``InterviewRecordsPort`` 독스트링이 약속하는 "기록 없음"이다.
    """

    def __init__(self, session: ChatSession) -> None:
        self._session = session

    @property
    def current(self) -> tuple[object, ...] | None:
        return self._session._song_interview_records or None


class _UploadedSheetView:
    """``ChatSession._uploaded_sheet``를 ``UploadedSheetPort``에 맞춘다.

    ``_LayoutImageUploadView``와 같은 이유로 존재한다: ``_uploaded_sheet``는 새
    업로드가 통째로 교체하는 필드이므로, 세션 생성 시점에 그 값을 그대로
    ``build_toolset``에 넘기면 업로드 이전의 ``None``이 ``import_uploaded_sheet``
    툴 클로저에 얼어붙는다. 이 뷰는 접근할 때마다 현재 필드를 다시 읽으므로
    세션 생성 뒤 도착한 업로드도 툴에게 보인다(AC-SHEETPIPE-003).

    이 결함은 조용하다 — 슬롯은 채워지고 안내도 뜨고 운영자 화면은 정상이다.
    어긋나는 것은 툴이 보는 것뿐이라, 운영자가 실제로 시켜 봐서
    ``no_uploaded_sheet`` 거절을 받기 전까지 아무 신호도 없다.
    """

    def __init__(self, session: ChatSession) -> None:
        self._session = session

    @property
    def file_name(self) -> str | None:
        sheet = self._session._uploaded_sheet
        return sheet.file_name if sheet is not None else None

    @property
    def kind(self) -> str | None:
        sheet = self._session._uploaded_sheet
        return sheet.kind if sheet is not None else None

    @property
    def content_base64(self) -> str | None:
        sheet = self._session._uploaded_sheet
        return sheet.content_base64 if sheet is not None else None


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

    def screen(self, commands: Sequence[str], *, risk: BatchRisk | None = None) -> ScreenDecision:
        # SPEC-COPILOT-BULKGATE-001 — 이 래퍼가 프로덕션의 유일한 게이트 진입
        # 지점이다. `risk` 를 안 받으면 선언은 여기서 조용히 사라지는 게
        # 아니라 TypeError 로 터진다(브라우저 실측에서 그렇게 잡혔다). 받아서
        # **그대로 전달한다** — 관찰만 하고 판단은 게이트가 한다.
        self._on_preview(commands)
        # 선언이 없는 호출은 인자 하나로 넘긴다 — 오늘과 바이트 동일하고,
        # `screen(commands)` 시그니처만 가진 기존 게이트 더블도 그대로 산다.
        # 선언이 있는데 아래 게이트가 못 받으면 조용히 흘리지 않고 크게 깨진다.
        decision = (
            self._gate.screen(commands) if risk is None else self._gate.screen(commands, risk=risk)
        )
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
        pending_plan_store: PendingSongPlanStore | None = None,
        spatial_memory: SpatialMemory | None = None,
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
        # #2 (2026-08-16): when a process-wide store is wired, the plan lives
        # THERE — a page refresh (new session) adopts it instead of losing it.
        self._pending_plan_store = pending_plan_store
        self._pending_song_plan_local: _SongDesignState | None = None
        # 결함 6: role → group-number mapping inferred from console group names
        # and confirmed by the director ONCE per session. None = not yet asked;
        # [] = declined or nothing inferable (single-layer, disclosed).
        self._song_layer_mapping: list[dict[str, object]] | None = None
        #: 카드 t311 — 이번 디자인 턴의 좌표 결손 고지(없으면 빈 문자열).
        self._design_coord_notice: str = ""
        self._timeline_store = timeline_store
        # Priority 3 (handoff 2026-08-15): approved console stores auto-save a
        # library version ("이름 (자동 vN)"). None (tests, bare deps) = no-op.
        self._timeline_library = timeline_library
        # t281 — 큐시트 초안 편집. `_draft_history` 는 편집 **직전** 상태만 쌓는
        # 되돌리기 스택이고, `_selected_cue` 는 화면에서 감독이 고른 큐 번호다
        # (chat 프레임이 실어 온다). 둘 다 콘솔과 무관하다.
        self._draft_history = TimelineDraftHistory()
        self._selected_cue: int | None = None
        # t291 — 콘솔 반영이 「무엇을 보낼지」 정할 때 대는 기준본. 첫 편집
        # 직전의 타임라인 깊은 사본이다. 이력의 걸음 수가 아니라 **값**을
        # 비교하므로, 되돌리기로 원래 값이 된 큐는 반영 대상에서 빠진다.
        self._draft_baseline: dict | None = None
        # Layout parameters the operator has already established this session
        # (column gap, fixture gap in metres). Persisted ACROSS turns and NOT
        # cleared after a placement, so a follow-up ("나머지도 배치해줘") reuses
        # them instead of the copilot re-asking for spacing it was already told.
        self._last_layout_spacing: tuple[float, float] | None = None
        # T12 — last reviewed-command build's unresolved phaser labels
        # (label → reason), stashed so ``_song_finalize`` can disclose them
        # in the final reply without threading a new return value through
        # ``_reviewed_song_commands``'s existing call sites/signature.
        self._last_phaser_failures: dict[str, str] = {}
        self._last_color_failures: dict[str, str] = {}
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
        # 지금 디스패치 중인 쓰기에 대해 **판정 시점에 이미 아는** 사실.
        # 승인 카드의 warnings로 흘러 들어간다(_notify_approval) — 회신에만
        # 실으면 되돌릴 수 없는 쓰기가 끝난 뒤에야 운영자에게 닿는다.
        self._approval_advisories: tuple[str, ...] = ()
        self._preview_counter = 0
        self._rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
        # REQ-DEPLOY-030 (#4): the single most-recent created look, persisted
        # ACROSS turns (unlike _turn_decisions, this is NOT reset per turn) so a
        # bare follow-up modification can anchor to the real target.
        self._last_created: LastCreated | None = None
        self._vectorworks_upload = _UploadedVectorworksExport()
        # 카드 t358 — 이 세션이 이미 무대에 올린 룩. 정본 §7 후반(곡 사이 재사용은
        # 결함)의 유일한 기억이고, 수명이 **세션 하나**라는 것이 그 규범의 범위와
        # 같다: 한 공연 안에서는 안 되풀이하고, 다음 공연은 빈손에서 시작한다.
        # 프로세스 전역이면 어제 쓴 룩이 오늘의 팔레트를 좁히고, 툴 호출 범위
        # (``ExecutionContext``)면 곡 하나를 못 넘긴다.
        self._song_look_memory = SongLookMemory()
        # SPEC-COPILOT-IMGLAYOUT-001 M1 — the layout-sketch attachment (most
        # recent only; a new upload replaces it). M3's ``analyse_layout_image``
        # tool reads this field; M1 only stores it.
        self._layout_image: LayoutImageUpload | None = None
        # SPEC-COPILOT-SHEETPIPE-001 M1 — the sheet attachment (most recent
        # only; a new upload replaces it wholesale). M2's
        # ``import_uploaded_sheet`` wrapper reads this through
        # ``_UploadedSheetView``; M1 only stores it.
        self._uploaded_sheet: UploadedSheet | None = None
        # SPEC-COPILOT-MUSICSYNC-001 M2 — 곡 오디오 첨부(가장 최근 하나만;
        # 새 업로드가 통째로 교체한다). 이 자리는 **보관만** 한다 — 분석은
        # ``analyse_song_audio`` 가 운영자가 요청했을 때 돈다.
        self._song_audio: SongAudioUpload | None = None
        #: 가장 최근 확정된 BPM 해소 결과(``analyse_song_audio``). 오디오와 달리
        #: 이것은 **사람이 확인한 뒤**에만 채워진다.
        self._song_bpm: BpmResolution | None = None
        #: SPEC-COPILOT-SONGCONFIRM-001 M1 — 사람이 확인한 곡 분석의 **불변 기록**
        #: (구간 채택 여부 + BPM 해소). 답이 미응답·자유입력 표식이면 비어 있고,
        #: 새 오디오 업로드가 무효화한다. ``_song_bpm`` 과 두 정본이 되지 않도록
        #: 기록의 ``bpm`` 은 ``_song_bpm`` 과 **같은 객체**다(REQ-SONGCONFIRM-006).
        self._song_analysis: ConfirmedSongAnalysis | None = None
        #: 카드 t441, SPEC-LDDESIGN-001 REQ-003 — 이 세션에서 **가장 최근에
        #: 완료된** 연출 인터뷰(경로 A, 채팅)의 답 기록
        #: (``DirectorInterview.audit_trail()``). 인터뷰가 완료될 때마다
        #: (``_song_design_interview_run`` 이 ``records = interview.audit_trail()``
        #: 를 만드는 자리) 갱신되고, 이후 `build_toolset` 이 `interview_records`
        #: 로 읽어 경로 B(``prepare_songcue``)가 같은 팔레트·색 운용 답을 쓸 수
        #: 있게 한다(`_SongInterviewRecordsView`). 인터뷰가 한 번도 끝나지
        #: 않았으면 빈 튜플 — 경로 B 는 그때 기록 없음(``None``)으로 읽는다.
        self._song_interview_records: tuple[object, ...] = ()
        # M6c-1 Finding 1/2: a unique identity for THIS connection, scoping the
        # shared approval_channel/review_channel/gate's per-session state so a
        # sibling ChatSession's disconnect or screening never leaks in.
        self._session_key = new_session_key()
        approval_channel.bind(self._notify_approval, session_key=self._session_key)
        if review_channel is not None:
            review_channel.bind(self._notify_review, session_key=self._session_key)
        if question_channel is not None:
            question_channel.bind(self._notify_question, session_key=self._session_key)
        # 리허설 편집: the live CurrentCue read rides the gate's own state
        # port (it also implements query_property — the same adoption
        # build_toolset performs). Tests stub this attribute directly.
        self._current_cue_port = gate.state_port
        # 카드 t344 — 장비 능력 판독도 같은 상태 포트를 탄다(`query_state` ·
        # `query_property` · `query_properties` 세 읽기를 다 갖춘 유일한 물건).
        # 테스트는 이 속성을 직접 스텁한다.
        self._rig_capability_port = gate.state_port
        registry = build_toolset(
            execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
            state_port=gate.state_port,
            bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision),
            # 카드 t110 — 프리셋·그룹 쓰기(`Store Preset` · `Store Group`)를
            # 게이트는 위험으로 분류하지 않으므로, 그 툴들은 자기 승인 통로를
            # 따로 묻는다. 여기에 안 실으면 `tools.py` 가 `DenyAllApprovalPort`
            # 로 떨어져 **앱에서는 항상 declined** 였다 — 하네스에서만 돌았다.
            # 새 통로를 만들지 않고 게이트와 같은 그 채널을 그대로 넘긴다:
            # `:3703` 에서 이미 이 세션 UI 에 bind 된 물건이라 사람이 답할 수
            # 있는 유일한 통로다. 통로 부재 시 거절(fail-closed)은 그대로다.
            group_approval_port=approval_channel,
            rig_paths=self._rig_paths,
            deploy_pipeline=deploy_pipeline,
            question_port=question_channel,
            vectorworks_upload=self._vectorworks_upload,
            # SPEC-COPILOT-IMGLAYOUT-001 M4: analyse_layout_image (M3) reads
            # the session's held image through this view (see
            # _LayoutImageUploadView) and reasons with the session's own
            # active provider — there is exactly one provider per session
            # (server/llm/factory.py builds a SINGLE active adapter), so
            # vision calls inherit its claude_code honest-refusal behavior
            # (REQ-IMGLAYOUT-006) automatically; no separate vision provider
            # config exists to wire.
            vision_provider=provider,
            layout_image_upload=_LayoutImageUploadView(self),
            # SPEC-COPILOT-SHEETPIPE-001 M2: the sheet slot goes through a
            # read-through view for the SAME reason the layout image does —
            # it is replaced wholesale, so passing the field itself would
            # freeze the pre-upload None into the wrapper's tool closure
            # (REQ-SHEETPIPE-002 · AC-SHEETPIPE-003).
            uploaded_sheet=_UploadedSheetView(self),
            # SPEC-COPILOT-SONGCONFIRM-001 M2: prepare_songcue 가 세션의 확정 곡
            # 분석 기록을 읽는 통로 — 위 두 뷰와 같은 읽기 투과 형태다(REQ-009).
            song_analysis=_SongAnalysisView(self),
            # 카드 t441, SPEC-LDDESIGN-001 REQ-003: prepare_songcue 가 세션의
            # (가장 최근에 완료된) 연출 인터뷰 기록을 읽는 통로 — 위
            # song_analysis 와 같은 읽기 투과 형태다.
            interview_records=_SongInterviewRecordsView(self),
            # 카드 t358: prepare_songcue 가 다음 곡의 룩을 고를 때 피할 대상.
            # 읽기 투과 뷰가 아니라 객체 자체를 넘기는 이유는 통째로 교체되지
            # 않기 때문이다 — 세션 내내 같은 객체가 자란다.
            song_look_memory=self._song_look_memory,
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
            # SPEC-COPILOT-SPATIALMEM-001: the process-wide remembered geometry
            # (app.py WebDeps). None in tests and bare deps, which keeps the
            # per-fixture walk — and every round-trip count asserted against
            # it — exactly as it was.
            spatial_memory=spatial_memory,
        )
        # Held so a look bundle re-enters the SAME run_commands tool the model
        # uses, rather than growing a second way to reach the console.
        self._registry = registry
        self._orchestrator = Orchestrator(
            provider=provider,
            registry=registry,
            system_prefix=system_prefix,
            # 진행 스트리밍: 러너는 웹소켓을 모른다. 이 세션이 자신의
            # ``send_event``(app.py가 스레드 안전하게 만들어 넘긴 싱크)로
            # 이어 붙이는 것이 전부다.
            progress=self._emit_progress,
            # 같은 이음매의 답변 절반 (SPEC-COPILOT-STREAM-001).
            answer=self._emit_answer,
        )

    @property
    def _pending_song_plan(self) -> _SongDesignState | None:
        """The pending (composed, unapproved) design — process-wide when a
        store is wired (#2: survives page refreshes), session-local in tests
        and bare deps."""
        if self._pending_plan_store is not None:
            return self._pending_plan_store.state
        return self._pending_song_plan_local

    @_pending_song_plan.setter
    def _pending_song_plan(self, state: _SongDesignState | None) -> None:
        if self._pending_plan_store is not None:
            self._pending_plan_store.state = state
        self._pending_song_plan_local = state

    def close(self) -> None:
        """Disconnect: unbind both channels for THIS session ONLY — denies
        this session's own pending requests, never another session's."""
        self._channel.unbind(session_key=self._session_key)
        if self._review_channel is not None:
            self._review_channel.unbind(session_key=self._session_key)
        parked = False
        if self._question_channel is not None:
            self._question_channel.unbind(session_key=self._session_key)
            # 질문 통로는 끊긴다고 답을 확정하지 않는다(question.py ``unbind``).
            # 아직 답을 기다리는 물음이 있으면 그 작업 스레드는 살아 있고, 답이
            # 오면 여기서 첨부를 읽는다 — 비워 버리면 새로고침 뒤에 답한 감독이
            # 「첨부가 없습니다」를 받는다.
            parked = self._question_channel.has_pending(session_key=self._session_key)
        if not parked:
            self._vectorworks_upload.clear()
            self._uploaded_sheet = None

    # -- event plumbing ----------------------------------------------------------

    @contextlib.contextmanager
    def _approval_advisory(self, note: str):
        """``note``를 이 블록 안에서 뜨는 모든 승인 카드에 얹는다.

        범위가 블록인 이유: 자문은 **이 쓰기**에 대한 사실이라 루프를 벗어난
        다음 턴의 카드에 묻어가면 거짓이 된다. 빈 문자열이면 아무것도 안 한다.
        """
        if not note:
            yield
            return
        previous = self._approval_advisories
        self._approval_advisories = previous + (note,)
        try:
            yield
        finally:
            self._approval_advisories = previous

    def _with_approval_advisories(self, request: ApprovalRequest) -> ApprovalRequest:
        """승인 카드의 ``warnings``에 현재 자문을 덧댄다 (UI 무수정 — 카드는
        이미 warnings를 렌더한다: ``ui/src/components/ApprovalCard.tsx``)."""
        if not self._approval_advisories:
            return request
        return ApprovalRequest(
            items=tuple(
                replace(
                    item,
                    warnings=item.warnings
                    + tuple(
                        note for note in self._approval_advisories if note not in item.warnings
                    ),
                )
                for item in request.items
            )
        )

    def _notify_approval(self, request_id: str, request: ApprovalRequest) -> None:
        self._send(
            approval_request_event(
                request_id=request_id, request=self._with_approval_advisories(request)
            )
        )

    def _notify_review(self, request_id: str, request: ReviewRequest) -> None:
        self._send(review_request_event(request_id=request_id, request=request))

    def _notify_question(self, request_id: str, request: QuestionRequest) -> None:
        self._send(question_request_event(request_id=request_id, request=request))

    def _emit_progress(self, *, phase: str, detail: str, seq: int) -> None:
        """오케스트레이터의 진행 한 줄을 이 연결의 이벤트 싱크로 이어 붙인다.

        느슨한 이음매의 세션 쪽 절반이다 — ``server/orchestrator/runner.py``\\ 는
        ``ProgressSink`` 하나만 알고 웹소켓·프로토콜·이벤트 모양은 모른다.
        ``send_event``\\ 는 app.py가 이미 스레드 안전하게 감싸 넘긴 콜러블이므로
        (턴은 ``asyncio.to_thread`` 워커에서 돈다) 여기서 다시 감쌀 것은 없다.
        """
        self._send(progress_event(phase=phase, detail=detail, seq=seq))

    def _emit_answer(self, *, delta: str, seq: int) -> None:
        """답변 조각 하나를 이 연결로 흘린다 (SPEC-COPILOT-STREAM-001).

        ``_emit_progress``\\ 와 같은 이음매의 같은 절반이다 — 러너는
        ``AnswerSink`` 하나만 알고, 이 메서드가 그것을 이 연결의 프로토콜
        프레임으로 바꾼다.
        """
        self._send(answer_delta_event(delta=delta, seq=seq))

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
        elif decision.status in (
            "blocked_console_offline",
            "blocked_responder_degraded",
            # 버전 차단도 health 상태 변화이므로 상태 스냅샷을 밀어 배너가
            # 사유를 받는다 (REQ-READBACK2-003).
            "blocked_responder_version_mismatch",
            "blocked_responder_version_unrecognized",
        ):
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
        # 카드 t320 — 룩 번들은 Store Preset 다발이다. 문면은 계획이 아니라
        # **나갈 명령**에서 읽는다(`showfile_write_risk`).
        execution = self._dispatch_declared(
            ToolCall(
                id=f"look-{plan.look_id}",
                name="run_commands",
                arguments={"commands": list(plan.commands)},
            ),
            risk=showfile_write_risk(plan.commands, kind="look_bundle"),
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
    def _axis_interpretation_note(
        fixtures: list[tuple[int, tuple[float, float, float]]],
    ) -> str:
        """방향·형상 해석의 **근거**를 사용자에게 보이는 한 줄 (INTENT-001 M3).

        2026-08-19 실측 사고: '좌→우'를 FID 순서로 해석해 8개 밴드를 만들었고,
        실제 좌표에서는 FID 1이 x=+3.0(우측)·FID 49~53이 x=−9.0(좌측)이었다 —
        즉 FID 순서와 무대 좌우는 무관했다. 오해가 조용히 성립하지 않도록,
        기하를 좌표에서 뽑은 핸들러는 **무엇을 어떻게 읽었는지** 회신에
        적는다. 사용자가 이 한 줄을 보고 즉시 잡을 수 있는 것이 목적이며,
        판독하지 못한 장비는 애초에 ``_read_pointing_coordinates``가 제외한다.
        """
        xs = [position[0] for _fid, position in fixtures]
        ys = [position[1] for _fid, position in fixtures]
        return (
            f"좌표 해석: 좌표 확인 {len(fixtures)}대 · "
            f"X {min(xs):.1f}~{max(xs):.1f} · Y {min(ys):.1f}~{max(ys):.1f} m "
            "— FID 순서가 아니라 콘솔 패치 좌표로 배치를 판단했습니다."
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

    def _try_rig_capabilities(self) -> DesignRigRead:
        """리그 능력 판독 — 실패해도 **빈 리그를 만들지 않는다**.

        카드 t344. 예전에는 이 자리에 ``patch=[]`` 리터럴이 있었고, 그것은 「패치를
        못 읽었다」와 「장비가 없다」를 바이트 동일하게 만들었다. 이제 콘솔에서 읽고,
        못 읽었으면 :attr:`DesignRigRead.gap` 에 코드가 실려 호출자가 고지한다.

        포트가 없으면(테스트·베어 deps) ``attempted=False`` 인 기본 판독이다 —
        「조회하지 않았다」이고 「읽었고 비었다」가 아니다.
        """
        port = getattr(self, "_rig_capability_port", None)
        if port is None:
            return DesignRigRead()
        return read_design_rig(port, fixture_types_root=_FIXTURE_TYPES_ROOT)

    def _try_pointing_coordinates(
        self, call_id: str
    ) -> tuple[list[tuple[int, tuple[float, float, float]]], str]:
        """``(fixtures, gap_kind)`` — 좌표를 읽었으면 gap 은 빈 문자열.

        카드 t311 — 이 판독의 **결과**와 「그래서 무엇을 멈출지」는 다른 문제다.
        조준(FOCUS/LOOK)은 좌표가 곧 그 기능이라 멈추는 것이 옳고, 곡 디자인은
        조도·색이 좌표와 무관하니 멈추면 안 된다. 그래서 판독은 여기 한 곳에
        두고, 중단 여부는 호출자가 정한다. gap 은 문면이 아니라 **코드**다
        (``unreadable`` / ``truncated``) — 호출자마다 감독에게 할 말이 다르고,
        문면을 여기서 만들면 호출자가 그것을 잘라 붙이게 된다.
        """
        spatial = self._registry.dispatch(
            ToolCall(id=call_id, name="get_spatial_context", arguments={})
        )
        if spatial.result.is_error:
            return [], _COORD_GAP_UNREADABLE
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
            ], ""
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return [], _COORD_GAP_TRUNCATED

    def _read_pointing_coordinates(
        self, call_id: str
    ) -> list[tuple[int, tuple[float, float, float]]] | InstructionResult:
        """Every coordinate-confirmed ``(fid, (x, y, z))`` — or the refusal.

        Shared by the FOCUS (point-at) and LOOK (fan/ring) handlers: both
        compute per-fixture pan/tilt from the console's own patch read, and
        both must refuse on a partial read rather than aim half a rig.
        """
        fixtures, gap = self._try_pointing_coordinates(call_id)
        if gap == _COORD_GAP_UNREADABLE:
            return self._pointing_refusal(
                "3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다. "
                "콘솔 연결을 확인해 주세요."
            )
        if gap:
            return self._pointing_refusal(
                "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 조명 방향 "
                "변경을 시작하지 않았습니다."
            )
        return fixtures

    def _read_pointing_frames(
        self, call_id: str
    ) -> (
        tuple[
            list[tuple[int, tuple[float, float, float]]],
            dict[int, float],
            list[int],
            list[int],
        ]
        | InstructionResult
    ):
        """Coordinates PLUS best-effort body rotations, for the direct aim paths.

        Returns ``(fixtures, rotz_by_fid, rotation_skipped, rotation_assumed)``
        or the refusal. The pan/tilt inverse model compensates ``Rotz`` only —
        ``Rotx``/``Roty`` were never live-measured (``server/spatial/
        pointing.py``) — so a fixture whose patched X/Y tilt is confirmed
        non-zero lands in ``rotation_skipped`` (aiming it would be confidently
        wrong), while a fixture whose rotation could not be read keeps the
        pre-rotation behaviour (assume 0) but is named in
        ``rotation_assumed`` so the reply can say the assumption out loud.
        """
        spatial = self._registry.dispatch(
            ToolCall(
                id=call_id,
                name="get_spatial_context",
                arguments={"include_rotation": True},
            )
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
            fixtures: list[tuple[int, tuple[float, float, float]]] = []
            rotz_by_fid: dict[int, float] = {}
            rotation_skipped: list[int] = []
            rotation_assumed: list[int] = []
            for record in records:
                if not (
                    isinstance(record, dict)
                    and isinstance(record.get("fid"), int)
                    and not isinstance(record.get("fid"), bool)
                ):
                    continue
                fid = record["fid"]
                position = (float(record["x"]), float(record["y"]), float(record["z"]))

                def _rotation(prop: str) -> float | None:
                    value = record.get(prop)  # noqa: B023 — consumed before next loop step
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        return float(value)
                    return None

                rotx, roty, rotz = _rotation("rotx"), _rotation("roty"), _rotation("rotz")
                if any(
                    value is not None and abs(value) > _ROTATION_TOLERANCE_DEGREES
                    for value in (rotx, roty)
                ):
                    rotation_skipped.append(fid)
                    continue
                if rotz is not None:
                    rotz_by_fid[fid] = rotz
                if rotx is None or roty is None or rotz is None:
                    rotation_assumed.append(fid)
                fixtures.append((fid, position))
            return fixtures, rotz_by_fid, rotation_skipped, rotation_assumed
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._pointing_refusal(
                "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 조명 방향 "
                "변경을 시작하지 않았습니다."
            )

    @staticmethod
    def _rotation_notes(rotation_skipped: list[int], rotation_assumed: list[int]) -> str:
        """The disclosure sentences the aim replies carry about body rotation."""
        notes = ""
        if rotation_skipped:
            notes += (
                f" 몸체 기울임 회전(Rotx/Roty)이 설정되어 조준식이 검증되지 않은 "
                f"{len(rotation_skipped)}대(FID "
                f"{', '.join(str(fid) for fid in rotation_skipped)})는 제외했습니다."
            )
        if rotation_assumed:
            notes += (
                f" 회전값을 읽지 못한 {len(rotation_assumed)}대(FID "
                f"{', '.join(str(fid) for fid in rotation_assumed)})는 회전 0으로 "
                "가정해 계산했습니다."
            )
        return notes

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
        frames = self._read_pointing_frames("pointing-read")
        if isinstance(frames, InstructionResult):
            return frames
        fixtures, rotz_by_fid, rotation_skipped, rotation_assumed = frames
        pointable: list[tuple[int, tuple[float, float, float]]] = []
        skipped: list[int] = []
        for fid, position in fixtures:
            try:
                aim_pan_tilt(position, target.as_tuple(), rotz=rotz_by_fid.get(fid, 0.0))
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
        commands = pointing_commands(pointable, target, dimmer=dimmer, rotz_by_fid=rotz_by_fid)
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
                f"Pan/Tilt를 요청했습니다.{skipped_note}"
                f"{self._rotation_notes(rotation_skipped, rotation_assumed)} "
                "승인 또는 라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 "
                "확인해 주세요."
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
        frames = self._read_pointing_frames("look-read")
        if isinstance(frames, InstructionResult):
            return frames
        fixtures, rotz_by_fid, rotation_skipped, rotation_assumed = frames
        # A design look's pan values are absolute programmer values, and the
        # fan/ring generators have no per-fixture rotation input — so a
        # confirmed non-zero Rotz invalidates the look for that fixture the
        # same way a non-zero Rotx/Roty invalidates aiming, and it joins the
        # named skip list instead of receiving a silently-wrong pan.
        rotation_skipped = list(rotation_skipped)
        untwisted: list[tuple[int, tuple[float, float, float]]] = []
        for fid, position in fixtures:
            if abs(rotz_by_fid.get(fid, 0.0)) > _ROTATION_TOLERANCE_DEGREES:
                rotation_skipped.append(fid)
            else:
                untwisted.append((fid, position))
        fixtures = untwisted
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 룩 포지션을 시작하지 않았습니다."
                + self._rotation_notes(rotation_skipped, rotation_assumed)
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
        # 카드 t320 — 프리셋 저장을 지시한 문장에서만 `Store Preset 2.<n>` 이
        # 붙는다. 안 붙은 회차는 프로그래머 값뿐이라 `showfile_write_risk` 가
        # `None` 을 답하고 선언이 카드를 만들지 않는다 — 그게 옳다.
        executed = self._dispatch_declared(
            ToolCall(id="look-write", name="run_commands", arguments={"commands": commands}),
            risk=showfile_write_risk(commands, kind="look_pan_tilt"),
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
                f"포지션으로 요청했습니다.{skipped_note}"
                f"{self._rotation_notes(rotation_skipped, rotation_assumed)}"
                f"{preset_note} 승인 또는 라이브 잠금 상태에 따른 결과를 아래 "
                "명령 상태에서 확인해 주세요."
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

    def _basic_position_presets(
        self, text: str, *, forced: bool = False
    ) -> InstructionResult | None:
        """Build the ten canonical positions for THIS rig and store them.

        Preset 1 of the run is ALWAYS 'Home'; the rest follow
        ``BASIC_POSITION_SEQUENCE`` from most basic to most varied. Number
        sourcing, the overwrite guard, the per-look store loop and the pool
        readback all live in ``_store_position_preset_sequence`` — shared
        with the FX flow so the two sets can never drift on safety behaviour.
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _BASIC_POSITIONS_REQUEST.search(text) is None
        ):
            return None
        return self._store_position_preset_sequence(
            text,
            noun="기본 포지션",
            sequence=BASIC_POSITION_SEQUENCE,
            build=basic_position_presets,
            read_id="basic-presets-read",
            bundle="basic-preset",
            example="기본 포지션 10개를 프리셋 21번부터 저장해줘",
        )

    def _fx_position_presets(self, text: str, *, forced: bool = False) -> InstructionResult | None:
        """Build the ten FX skeleton positions for THIS rig and store them.

        These are the geometric backbones phaser effects swing around
        (``FX_POSITION_SEQUENCE``: sweeps, sky/floor extremes, circle and
        bally bases, tails, splits), a set distinct from the design-oriented
        BASIC ten. The flow is the EXACT basic store flow — explicit-number
        occupancy guard, the one shared overwrite card, per-look bundles,
        post-store pool readback — via ``_store_position_preset_sequence``;
        no FX-specific card or vocabulary exists.
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _FX_POSITIONS_REQUEST.search(text) is None
        ):
            return None
        return self._store_position_preset_sequence(
            text,
            noun="FX 포지션",
            sequence=FX_POSITION_SEQUENCE,
            build=fx_position_presets,
            read_id="fx-presets-read",
            bundle="fx-preset",
            example="이펙트 포지션 프리셋을 41번부터 저장해줘",
        )

    def _position_fx_sequence(self, text: str) -> InstructionResult | None:
        """저장된 FX 포지션 프리셋을 **소비**하는 포지션 이펙트 시퀀스 빌더.

        `_fx_position_presets`가 저장한 골격(2.N~2.N+9)을 참조해 시퀀스 하나를
        만든다 — A/B형(sweep·flyout)은 2큐 크로스페이드, base형(circle·
        ballyhoo·wave)은 base 프리셋 위의 상대 페이저 1큐. 명령열은 전부
        ``position_fx_commands``(라이브 검증 문법)가 만들고, 이 핸들러는 세
        입력만 해석한다: 효과(어휘), FX 프리셋 시작 번호("N번부터" 또는 카드
        1장), 시퀀스 번호("시퀀스 N" 또는 카드 1장). 답을 못 읽으면 저장
        0건으로 거부한다 — 시퀀스 Store는 슬롯을 그대로 바꾸므로 번호는
        운영자의 결정이다. 디스패치는 ``run_commands`` 1번들: 기존 게이트
        경로 그대로, ``/Overwrite`` 없음.
        """
        matched = next(
            (
                (name, korean)
                for name, pattern, korean in _POSITION_FX_VOCABULARY
                if pattern.search(text) is not None
            ),
            None,
        )
        if matched is None:
            return None
        if _POSITION_FX_NOUN.search(text) is None or _POSITION_FX_VERB.search(text) is None:
            return None
        # M1 — 명시적 부정은 좌표 판독 **앞**에서 끝난다. 이 경로는 팬/틸트를
        # 쓰므로, 포지션 축을 배제한 문장에 대해서는 후보 자격 자체가 없다.
        # 회신을 만들지 않고 None으로 빠져 기존 폴백(모델·compose_fx)이 그
        # 문장을 그대로 받게 한다 — 여기서 카드를 띄우면 컬러 요청에 포지션
        # 질문이 붙는다.
        if _POSITION_FX_VETO.search(text) is not None:
            return None
        # M2 — 축 후보가 맞설 때는 조용히 포지션을 택하지 않는다. 카드 1장.
        conflict = next(
            (name for name, pattern in _NON_POSITION_ATTRIBUTE if pattern.search(text) is not None),
            None,
        )
        if conflict is not None:
            answer = self._ask_one(
                f"'{conflict}'을(를) 말씀하셨는데 이 경로는 빔을 움직입니다 — "
                "무엇이 움직이는 이펙트인가요?",
                options=(
                    QuestionOption(label=f"{conflict}이 바뀐다 (장비는 고정)"),
                    QuestionOption(label="빔이 움직인다 (포지션 이펙트)"),
                ),
                why=(
                    "포지션 이펙트는 팬/틸트를 쓰고 컬러·디머는 건드리지 않습니다. "
                    "축을 잘못 잡으면 요청과 다른 시퀀스가 저장됩니다."
                ),
            )
            if answer is None or _POSITION_AXIS_CLAIM.search(answer) is None:
                return None
        effect, label = matched
        fixtures = self._read_pointing_coordinates("position-fx-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 이펙트 시퀀스를 시작하지 않았습니다."
            )
        start_match = _BASIC_POSITIONS_START.search(text)
        if start_match is not None:
            fx_preset_start = int(start_match.group("no"))
        else:
            answer = self._ask_one(
                f"{label} 이펙트가 참조할 FX 포지션 프리셋이 몇 번부터 저장돼 "
                "있나요? (예: 41 → Preset 2.41~2.50)",
                options=(
                    QuestionOption(label="41"),
                    QuestionOption(label="31"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "이펙트 시퀀스는 저장된 FX 포지션 프리셋을 참조하므로 "
                    "시작 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                fx_preset_start = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "FX 프리셋 시작 번호를 받지 못해 시퀀스를 만들지 않았습니다. "
                    "예: '좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터'"
                )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                f"{label} 이펙트를 몇 번 시퀀스로 저장할까요? (예: 201) "
                "이미 데이터가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="201"),
                    QuestionOption(label="210"),
                    QuestionOption(label="220"),
                ),
                why=(
                    "Store Sequence는 지정한 슬롯에 그대로 저장되므로 "
                    "시퀀스 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 시퀀스를 만들지 않았습니다. "
                    "예: '좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터'"
                )
        # 점유 확인은 셋리스트/곡 설계와 같은 fail-closed 프로브를 재사용한다 —
        # 빈 시퀀스 Store는 자동 생성이라 비가역 위험이 낮지만, 점유된 슬롯은
        # 기존 쇼 데이터가 바뀌므로 승낙 없이는 저장하지 않는다.
        if fx_preset_start <= 0:
            return self._pointing_refusal("FX 프리셋 시작 번호는 1 이상이어야 합니다.")
        if sequence_no <= 0:
            return self._pointing_refusal("시퀀스 번호는 1 이상이어야 합니다.")
        if self._song_sequence_occupied(sequence_no):
            answer = self._ask_one(
                f"시퀀스 {sequence_no}에 기존 데이터가 있습니다. {label} 이펙트를 "
                "이 시퀀스에 저장하면 기존 큐가 바뀔 수 있습니다. 진행할까요?",
                options=(
                    QuestionOption(label="진행"),
                    QuestionOption(label=_PRESET_OVERWRITE_DECLINE_LABEL),
                ),
                why=(
                    "Store Sequence /Merge는 점유된 큐 슬롯의 내용을 바꾸며 "
                    "이 앱에는 시퀀스 복원 경로가 없습니다."
                ),
            )
            if answer is None or _preset_answer_intent(answer) != "consent":
                return self._pointing_refusal(
                    f"시퀀스 {sequence_no} 사용 승낙을 받지 못해 저장하지 않았습니다."
                )
        fids = [fid for fid, _position in fixtures]
        try:
            # 카드 t232 — 이 효과가 부르는 라벨만(1~2개) 라벨로 확인한 뒤
            # 실제 슬롯을 넘긴다. `fx_preset_start + offset`는 그 자리가
            # 진짜 그 라벨인지 보지 않았다(판독: `.moai/reports/t232/verdict.md`).
            needed_labels = required_position_labels(effect)
            preset_numbers = self._resolve_position_preset_labels(
                needed_labels, start=fx_preset_start, span=len(FX_POSITION_SEQUENCE)
            )
            commands = position_fx_commands(
                effect,
                fids=fids,
                preset_numbers=preset_numbers,
                sequence_no=sequence_no,
                label=label,
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"포지션 이펙트 명령을 만들 수 없습니다: {error}")
        executed = self._dispatch_declared(
            ToolCall(
                id="position-fx-write",
                name="run_commands",
                arguments={"commands": list(commands)},
            ),
            risk=showfile_write_risk(commands, kind="position_fx_sequence"),
        )
        span_end = fx_preset_start + len(FX_POSITION_SEQUENCE) - 1
        reply = (
            f"{label} 포지션 이펙트를 시퀀스 {sequence_no}에 저장 요청했습니다 "
            f"— FX 포지션 프리셋 2.{fx_preset_start}~2.{span_end} 구간을 "
            "참조합니다 (프리셋 참조 유지, 저장 후 ClearAll). 승인 또는 라이브 "
            "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요.\n"
            # M3 — 기하를 좌표에서 뽑았으므로 그 근거를 같은 회신에 싣는다.
            f"{self._axis_interpretation_note(fixtures)}"
        )
        outcomes = tuple(executed.command_outcomes)
        # 실행기 제안은 저장 번들이 **전건 executed_ok**로 끝났을 때만 — 승인
        # 대기·차단·부분 실행 위에 Assign을 얹으면 존재하지 않는 시퀀스를 걸거나
        # 게이트를 우회한 것처럼 보이는 회신이 된다.
        statuses = [outcome.status for outcome in outcomes]
        if (
            not executed.result.is_error
            and statuses
            and all(status == "executed_ok" for status in statuses)
        ):
            note, assign_outcomes = self._offer_fx_executor_assignment(sequence_no)
            reply = f"{reply}\n{note}"
            outcomes += assign_outcomes
        return InstructionResult(
            status="ok",
            text=reply,
            command_outcomes=outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _page_one_executors(self, *, probe_id: str) -> set[int] | None:
        """Page 1이 점유한 **실행기 번호** 집합 — 판독 불가 시 ``None``.

        응답기의 Page children이 나르는 ``i``는 실행기 번호가 아니라 페이지
        슬롯 인덱스다: **실행기 번호 = i + 100** (2026-08-16 콘솔 실측,
        i=4 ↔ Executor 104 — 이 매핑을 놓친 오판 하나가 점유된 105를
        '빈칸'으로 읽어 기존 바인딩을 덮어썼다). truncated 플래그와
        childCount 산술 불일치는 부분 창이므로 '더 작은 페이지'가 아니라
        '모름'이다 — `_position_preset_pool_slots`와 같은 이중 방어.
        """
        pages_root = self._rig_paths.get("pages", "DataPool/Pages")
        probe = self._registry.dispatch(
            ToolCall(
                id=probe_id,
                name="query_state",
                arguments={"path": f"{pages_root}/1"},
            )
        )
        if probe.result.is_error:
            return None
        try:
            payload = json.loads(probe.result.content)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        children = payload.get("children")
        if not isinstance(children, list):
            return None
        if payload.get("truncated"):
            return None
        node = payload.get("node")
        if isinstance(node, dict):
            child_count = node.get("childCount")
            if isinstance(child_count, int) and child_count > len(children):
                return None
        executors: set[int] = set()
        for child in children:
            if not isinstance(child, dict):
                continue
            try:
                executors.add(int(child.get("i", child.get("no"))) + 100)
            except (TypeError, ValueError):
                continue
        return executors

    def _offer_fx_executor_assignment(
        self, sequence_no: int
    ) -> tuple[str, tuple[CommandOutcome, ...]]:
        """방금 저장된 시퀀스를 **빈** 실행기에 걸지 제안한다 — 회신 꼬리
        한 줄과 Assign 번들 결과를 돌려준다.

        카드는 Page 1 점유를 **읽은 다음에만** 띄운다: 판독 불가 위에서 빈
        실행기를 고르면 점유 오판이 기존 바인딩을 소리 없이 덮어쓴다
        (2026-08-16 Executor 105 사고 — 이 게이트가 그 재발 방지이자 이
        기능의 존재 이유다). 승낙 후에도 Cmd의 OK는 착지 증거가 아니므로
        (같은 날 실측) 착지는 Page 1 **되읽기**로만 보고한다.
        """
        occupied = self._page_one_executors(probe_id="position-fx-executor-scan")
        if occupied is None:
            return ("실행기 점유를 읽지 못해 할당을 제안하지 않았습니다.", ())
        target = next((no for no in _FX_EXECUTOR_BAND if no not in occupied), None)
        if target is None:
            return (
                f"Executor {_FX_EXECUTOR_BAND[0]}~{_FX_EXECUTOR_BAND[-1]}가 모두 "
                "점유돼 있어 할당을 제안하지 않았습니다.",
                (),
            )
        answer = self._ask_one(
            f"시퀀스 {sequence_no}을(를) 실행기 {target}에 걸까요?",
            options=(
                QuestionOption(label=_FX_EXECUTOR_ASSIGN_LABEL),
                QuestionOption(label=_FX_EXECUTOR_SKIP_LABEL),
            ),
            why=(
                f"Page 1 판독에서 실행기 {target}이 비어 있었습니다 "
                f"(children i={target - 100} 부재 → Executor {target}). "
                "Assign은 기존 바인딩을 덮어쓰므로 빈 실행기만 제안합니다."
            ),
        )
        consented = answer is not None and (
            answer.strip() == _FX_EXECUTOR_ASSIGN_LABEL
            or _preset_answer_intent(answer) == "consent"
        )
        if not consented:
            return ("실행기 미할당 — 시퀀스는 저장된 상태 그대로입니다.", ())
        assign_commands = [f"Assign Sequence {sequence_no} At Executor {target}"]
        executed = self._dispatch_declared(
            ToolCall(
                id="position-fx-assign",
                name="run_commands",
                arguments={"commands": list(assign_commands)},
            ),
            risk=showfile_write_risk(assign_commands, kind="fx_executor_assign"),
        )
        outcomes = tuple(executed.command_outcomes)
        after = self._page_one_executors(probe_id="position-fx-executor-readback")
        if after is not None and target in after:
            return (
                f"시퀀스 {sequence_no}을(를) 실행기 {target}에 할당하고 되읽기로 "
                f"착지를 확인했습니다 — Page 1 children i={target - 100} "
                f"(= {target} − 100).",
                outcomes,
            )
        return (
            f"실행기 {target} 할당을 요청했지만 되읽기에서 착지 미확인입니다 — "
            f"콘솔에서 Executor {target}를 직접 확인해 주세요 (명령 OK는 착지 "
            "증거가 아닙니다).",
            outcomes,
        )

    def _phaser_slot_by_label(self, label: str) -> tuple[int, int] | None:
        """카탈로그 페이저 라벨 → 실기 ``(pool_no, slot)``, 못 찾으면 None(거부).

        슬롯 번호는 코드 상수가 아니다 — 저장 시점에 실제로 어느 칸에 앉았는지
        는 운영자의 저장 순서가 정하므로, 라벨을 키로 실기를 페이지드로 완전
        열거해 찾는다(T11 프로브 §5, ``_paged_pool_children`` 실측 입증). 어느
        풀을 열지는 ``_PHASER_LABEL_POOL_NAME``(카탈로그 3계열이 서로소이므로
        고정 매핑이 안전)으로 정하고, 그 풀의 실기 번호는 ``_resolve_named_
        pool_no``로 해석한다(하드코딩 금지, 기존 Color/Dimmer/All 1 리졸버와
        동일 규율). 중복명 접미('#2')는 ``presets_api._base_name``과 같은
        규율로 관용한다. 풀 해석 실패·페이징 판독 실패·라벨 부재는 모두
        None(추측 금지) — 판독 실패와 부재를 구별한 고지는 호출자 책임이다.
        """
        pool_name = _PHASER_LABEL_POOL_NAME.get(label)
        if pool_name is None:
            return None
        probe_slug = pool_name.lower().replace(" ", "")
        pool_no = self._resolve_named_pool_no(
            pool_name, probe_id=f"phaser-recall-pool-{probe_slug}"
        )
        if pool_no is None:
            return None
        pool_root = self._rig_paths.get("preset_pools", "DataPool/PresetPools")
        children = self._paged_pool_children(
            f"{pool_root}/{pool_no}", probe_id=f"phaser-recall-slots-{probe_slug}"
        )
        if children is None:
            return None
        for slot, name in children.items():
            base = name.split("#", 1)[0] if isinstance(name, str) else None
            if base == label:
                return pool_no, slot
        return None

    def _phaser_recall_fids(
        self, label: str, *, noun: str, probe_id_prefix: str
    ) -> tuple[list[int], str] | InstructionResult:
        """라벨의 소속 풀에 맞는 대상 장비 판별 — ``(fids, disclosure)`` 또는 거부.

        컬러를 포함한 페이저(Color/All 1 풀)는 컬러 판별이 상한이므로 ``_color_
        capability_and_disclosure``를 재사용하고(REQ-005, fail-closed), 디머
        전용 페이저(Dimmer 풀)는 판별 없이 전량 열거하는 ``_dimmer_pool_and_
        fids``를 재사용한다 — 두 계열 모두 이미 슬롯을 안 뒤에 다시 풀 번호를
        해석하지만(내부에서 한 번 더 조회), 저장 가족들과 판별 몸통을 공유해
        거절·고지 문면이 갈라지지 않게 하는 이득이 왕복 1회 비용을 상회한다
        (기존 저장 가족들의 리팩터 판단과 동일).
        """
        pool_name = _PHASER_LABEL_POOL_NAME[label]
        if pool_name == "Dimmer":
            shared = self._dimmer_pool_and_fids(noun=noun)
            if isinstance(shared, InstructionResult):
                return shared
            _pool_no, fids, disclosure = shared
            return fids, disclosure
        shared = self._color_capability_and_disclosure(noun=noun, probe_id_prefix=probe_id_prefix)
        if isinstance(shared, InstructionResult):
            return shared
        capable, disclosure = shared
        return capable, disclosure

    def _phaser_recall(self, text: str) -> InstructionResult | None:
        """*"Breathe Warm 쳐줘"* / *"Breathe Warm 꺼줘"* — 카탈로그 페이저를
        즉시 recall(발사)하거나 해제(off)한다.

        카탈로그 30종 라벨 중 하나가 문장에 있어야만 발동한다(``_match_
        phaser_label``) — 저장·재생성 가족의 포괄 어휘축과 서로소라 디스패치
        등록은 그 가족들보다 뒤에 둬도 안전하다. 2단계(``_phaser_recall_
        sequence``)와는 명사('시퀀스'/'실행기'/'exec') 유무로 갈라지며, 등록
        순서(2단계가 먼저)가 그 서로소를 고정한다.

        recall이 멀티스텝 페이저를 통째로 싣는지는 이 저장소의 프로토콜
        경로(OSC/Lua state/prop)로는 판독 불가다(T11 프로브 §1, 구조적
        한계 — 응답기 ``resolve_path``에 Programmer/Selection 별칭이 없다).
        회신에 그 ASSUMPTION을 명시하고 "실렸다"고 단정하지 않는다.
        """
        label = _match_phaser_label(text)
        if label is None:
            return None
        release = _PHASER_RELEASE_VERB.search(text) is not None
        launch = _PHASER_RECALL_VERB.search(text) is not None
        if not release and not launch:
            return None
        # 해제 동사를 발사보다 우선한다 — "쳐줬다가 꺼줘"류 합성 문장에서
        # 마지막 의도(해제)가 이겨야 하고, 두 동사가 겹칠 때 발사를 기본값
        # 으로 삼으면 의도치 않은 재발사가 된다(보수적 선택).
        action = "release" if release else "recall"
        verb_korean = "해제" if action == "release" else "발사"
        resolved = self._phaser_slot_by_label(label)
        if resolved is None:
            return self._pointing_refusal(
                f"'{label}' 페이저 프리셋을 콘솔에서 찾지 못해 {verb_korean}하지 "
                "않았습니다 — 저장돼 있는지, 라벨이 정확한지 확인해 주세요."
            )
        pool_no, slot = resolved
        pool_name = _PHASER_LABEL_POOL_NAME[label]
        probe_slug = pool_name.lower().replace(" ", "")
        shared = self._phaser_recall_fids(
            label, noun=f"'{label}' 페이저", probe_id_prefix=f"phaser-recall-{probe_slug}"
        )
        if isinstance(shared, InstructionResult):
            return shared
        fids, disclosure = shared
        try:
            command = (
                _preset_release_command(fids)
                if action == "release"
                else _preset_recall_command(pool_no, fids, slot)
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"{verb_korean} 명령을 만들 수 없습니다: {error}")
        executed = self._registry.dispatch(
            ToolCall(
                id=f"phaser-recall-{action}",
                name="run_commands",
                arguments={"commands": [command]},
            )
        )
        disclosure_note = f" {disclosure}" if disclosure else ""
        # recall의 페이저 적재는 2026-08-19 실기 육안 확인으로 종결(Drop Slam)
        # — 발사 회신은 더 이상 검증을 요구하지 않는다. 단 Rectangle 파형
        # 근사(Chase/Slam 계열)는 여전히 미검증이라 그 잔여만 남긴다.
        assumption_note = (
            ""
            if action == "release"
            else (
                " (Rectangle 계열 파형의 하드컷 여부는 미검증입니다 — "
                "해당 프리셋 발사 시 콘솔에서 확인해 주세요.)"
            )
        )
        return InstructionResult(
            status="ok",
            text=(
                f"'{label}' 페이저를 Preset {pool_no}.{slot}에서 장비 {len(fids)}대에 "
                f"{verb_korean} 요청했습니다.{disclosure_note}{assumption_note} 승인 또는 "
                "라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _phaser_recall_sequence(self, text: str) -> InstructionResult | None:
        """*"Breathe Warm 시퀀스로 쳐줘"* — 카탈로그 페이저를 새 시퀀스 1큐로
        저장하고, 저장이 전건 성공하면 빈 실행기에 걸도록 제안한다.

        1단계(``_phaser_recall``)와 어휘축(카탈로그 라벨 + 발사 동사)이
        겹친다 — 서로소는 명사('시퀀스'/'실행기'/'exec')의 유무로 가르고,
        디스패치 등록 순서를 이 함수가 1단계보다 **앞**에 둬서 고정한다
        (``_position_fx_sequence``가 ``_fx_position_presets``보다 앞인 것과
        같은 형상, REQ-PRESETGUARD-015류 등록 순서 고정). 시퀀스 번호 해석·
        점유 승낙 카드는 ``_position_fx_sequence``의 몸통을 그대로 미러하고,
        실행기 할당은 ``_offer_fx_executor_assignment``를 수정 없이 재사용
        한다(이미 시퀀스 번호만 받는 범용 함수).
        """
        label = _match_phaser_label(text)
        if label is None:
            return None
        if _PHASER_RECALL_NOUN.search(text) is None:
            return None
        if _PHASER_RECALL_VERB.search(text) is None:
            return None
        resolved = self._phaser_slot_by_label(label)
        if resolved is None:
            return self._pointing_refusal(
                f"'{label}' 페이저 프리셋을 콘솔에서 찾지 못해 시퀀스를 만들지 "
                "않았습니다 — 저장돼 있는지, 라벨이 정확한지 확인해 주세요."
            )
        pool_no, slot = resolved
        pool_name = _PHASER_LABEL_POOL_NAME[label]
        probe_slug = pool_name.lower().replace(" ", "")
        shared = self._phaser_recall_fids(
            label,
            noun=f"'{label}' 페이저 시퀀스",
            probe_id_prefix=f"phaser-recall-seq-{probe_slug}",
        )
        if isinstance(shared, InstructionResult):
            return shared
        fids, disclosure = shared
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                f"'{label}' 페이저를 몇 번 시퀀스로 저장할까요? (예: 201) "
                "이미 데이터가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="201"),
                    QuestionOption(label="210"),
                    QuestionOption(label="220"),
                ),
                why=(
                    "Store Sequence는 지정한 슬롯에 그대로 저장되므로 시퀀스 "
                    "번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    f"시퀀스 번호를 받지 못해 '{label}' 시퀀스를 만들지 않았습니다. "
                    f"예: '{label} 시퀀스 201로 쳐줘'"
                )
        if sequence_no <= 0:
            return self._pointing_refusal("시퀀스 번호는 1 이상이어야 합니다.")
        if self._song_sequence_occupied(sequence_no):
            answer = self._ask_one(
                f"시퀀스 {sequence_no}에 기존 데이터가 있습니다. '{label}' 페이저를 "
                "이 시퀀스에 저장하면 기존 큐가 바뀔 수 있습니다. 진행할까요?",
                options=(
                    QuestionOption(label="진행"),
                    QuestionOption(label=_PRESET_OVERWRITE_DECLINE_LABEL),
                ),
                why=(
                    "Store Sequence /Merge는 점유된 큐 슬롯의 내용을 바꾸며 "
                    "이 앱에는 시퀀스 복원 경로가 없습니다."
                ),
            )
            if answer is None or _preset_answer_intent(answer) != "consent":
                return self._pointing_refusal(
                    f"시퀀스 {sequence_no} 사용 승낙을 받지 못해 저장하지 않았습니다."
                )
        try:
            commands = _phaser_sequence_commands(pool_no, fids, slot, sequence_no, label)
        except SpatialPointingError as error:
            return self._pointing_refusal(f"페이저 시퀀스 명령을 만들 수 없습니다: {error}")
        executed = self._dispatch_declared(
            ToolCall(
                id="phaser-recall-sequence-write",
                name="run_commands",
                arguments={"commands": list(commands)},
            ),
            risk=showfile_write_risk(commands, kind="phaser_recall_sequence"),
        )
        disclosure_note = f" {disclosure}" if disclosure else ""
        reply = (
            f"'{label}' 페이저를 시퀀스 {sequence_no}에 저장 요청했습니다 — Preset "
            f"{pool_no}.{slot} 참조, 대상 장비 {len(fids)}대.{disclosure_note} "
            "(저장된 큐가 프리셋 참조를 보존하는지는 판독할 수 없어 ASSUMPTION입니다 "
            "— 시퀀스 재생은 콘솔 화면에서 확인해 주세요.) 승인 또는 "
            "라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
        )
        outcomes = tuple(executed.command_outcomes)
        # 실행기 제안은 저장 번들이 **전건 executed_ok**로 끝났을 때만 —
        # _position_fx_sequence와 동일한 게이트(존재하지 않는 시퀀스에 걸거나
        # 게이트를 우회한 것처럼 보이는 회신을 막는다).
        statuses = [outcome.status for outcome in outcomes]
        if (
            not executed.result.is_error
            and statuses
            and all(status == "executed_ok" for status in statuses)
        ):
            note, assign_outcomes = self._offer_fx_executor_assignment(sequence_no)
            reply = f"{reply}\n{note}"
            outcomes += assign_outcomes
        return InstructionResult(
            status="ok",
            text=reply,
            command_outcomes=outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _store_position_preset_sequence(
        self,
        text: str,
        *,
        noun: str,
        sequence: tuple[str, ...],
        build: Callable[[Sequence], Sequence[tuple]],
        read_id: str,
        bundle: str,
        example: str,
        pool_no: int = POSITION_PRESET_POOL,
        pool_label: str = "Position",
        read: Callable[[str], Sequence | InstructionResult] | None = None,
        apply: Callable[[object], Sequence[str]] = aimed_commands,
        lead_intro: str = "리그 배치에서 유도한",
        disclosure: str = "",
    ) -> InstructionResult | None:
        """Store one named look sequence as consecutive presets of ONE pool.

        The first preset number comes from the instruction ("N번부터") or from
        ONE question card — never from a guessed free slot: ``Store Preset``
        silently overwrites, so the number is the operator's call.
        Each look is applied, stored, labelled and cleared as its own bundle,
        so one refused look never voids the others.

        포지션 전용으로 태어난 몸통의 **풀 매개변수화**(SPEC-COPILOT-
        COLORPRESET-001 §A.1): ``pool_no``/``pool_label``은 경로·문면만 바꾸고
        점유 검사·카드·번들·되읽기 규율은 그대로다. 기본값이 오늘의 Position
        (2)이라 기존 호출 지점은 무수정 동작 동일(REQ-COLORPRESET-006).
        ``read``/``apply``는 소재 공급과 적용 명령만 바꾼다 — 컬러는 좌표가
        필요 없고(``_color_capable_fids``로 축소된 FID 목록) 조준 대신 색
        체인을 싣는다. ``disclosure``는 회신 lead에 붙는 산술 고지(REQ-005).
        """
        source = self._read_pointing_coordinates if read is None else read
        fixtures = source(read_id)
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                f"좌표가 확인된 장비가 없어 {noun} 프리셋을 시작하지 않았습니다."
            )
        start_match = _BASIC_POSITIONS_START.search(text)
        if start_match is not None:
            start_no = int(start_match.group("no"))
        else:
            count = len(sequence)
            free_starts = self._position_preset_free_starts(pool_no=pool_no)
            if free_starts:
                prompt = (
                    f"{noun} {count}개를 {pool_label} 프리셋 몇 번부터 저장할까요? "
                    f"{count}칸 연속 비어 있는 구간을 콘솔에서 확인했습니다."
                )
                options = tuple(
                    QuestionOption(
                        label=f"{start} ({pool_no}.{start}~{pool_no}.{start + count - 1} 비어 있음)"
                    )
                    for start in free_starts
                )
            else:
                prompt = (
                    f"{noun} {count}개를 {pool_label} 프리셋 몇 번부터 저장할까요? "
                    f"(예: 1 → Preset {pool_no}.1~{pool_no}.{count}) 이미 있는 번호는 덮어씁니다."
                )
                options = (
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                )
            answer = self._ask_one(
                prompt,
                options=options,
                why=(
                    "Store Preset은 기존 슬롯을 경고 없이 덮어쓰므로 "
                    "시작 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                start_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    f"시작 프리셋 번호를 받지 못해 저장을 시작하지 않았습니다. 예: '{example}'"
                )
        if start_no <= 0:
            return self._pointing_refusal("시작 프리셋 번호는 1 이상이어야 합니다.")
        # 가드는 `start_no`가 **확정된 지점**에 걸린다 — if/else 갈래 밖이다.
        # 질문 카드도 자유 입력을 항상 제공하므로(`_ask_one` 독스트링), else
        # 갈래에서 손으로 타이핑한 번호는 명시 번호와 **동일하게 무방비**다
        # (REQ-PRESETGUARD-001 '출처 무관' 조항).
        pool_slots = self._position_preset_pool_slots(pool_no=pool_no)
        verdict = self._confirm_preset_span_overwrite(
            start_no, pool_slots, intent="store", pool_no=pool_no, pool_label=pool_label
        )
        if not verdict.proceed:
            return self._pointing_refusal(_preset_overwrite_refusal(verdict))
        try:
            looks = build(fixtures)
        except SpatialPointingError as error:
            return self._pointing_refusal(f"{noun}을 계산할 수 없습니다: {error}")
        # 판독 실패는 승인 카드가 들고 나간다 — 회신은 쓰기 뒤에야 조립된다.
        with self._approval_advisory(verdict.approval_advisory):
            run = self._store_position_preset_looks(
                looks, start_no, before=pool_slots, bundle=bundle, pool_no=pool_no, apply=apply
            )
        if not run.stored:
            return self._pointing_refusal(
                "어느 포지션도 계산되지 않아 프리셋을 저장하지 않았습니다."
            )
        return InstructionResult(
            status="ok",
            text=_preset_reply_text(
                run,
                verdict,
                self._verify_preset_span_stored(run, pool_no=pool_no, pool_label=pool_label),
                lead=(
                    f"{lead_intro} {noun} {len(run.stored)}개를 "
                    f"{pool_label} 프리셋에 저장 요청했습니다: {', '.join(run.stored)}."
                    + (f" {disclosure}" if disclosure else "")
                ),
                tail=(
                    "각 프리셋은 적용→저장→ClearAll 순서로 처리했으며, 승인 또는 라이브 "
                    "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
                ),
            ),
            command_outcomes=run.outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _confirm_preset_span_overwrite(
        self,
        start_no: int,
        slots: set[int] | None,
        *,
        intent: str,
        pool_no: int = POSITION_PRESET_POOL,
        pool_label: str = "Position",
    ) -> _PresetSpanVerdict:
        """구간 ``2.N … 2.N+9``의 충돌을 판정하는 **공용 카드**.

        호출자는 둘(신규 저장 / 재생성)이고 카드는 하나다 — ``intent``는 문면만
        바꾸고 판정 로직은 동일하다. 카드를 둘로 나누면 fail-closed 규칙이 두 곳에
        복제되고 한쪽만 갱신되는 드리프트가 생긴다(spec.md §A.5).

        ``slots``가 ``None``이면 판독 불가이므로 ``unverified`` — **빈칸으로 접지
        않는다**(REQ-PRESETGUARD-004). 충돌이 없으면 질문 없이 통과한다
        (REQ-PRESETGUARD-005): 마찰은 손실 가능성이 있는 자리에만 놓인다.
        """
        span = len(BASIC_POSITION_SEQUENCE)
        if slots is None:
            return _PresetSpanVerdict("unverified", pool_no=pool_no, pool_label=pool_label)
        collisions = tuple(no for no in range(start_no, start_no + span) if no in slots)
        if not collisions:
            return _PresetSpanVerdict("clear", pool_no=pool_no, pool_label=pool_label)
        lead = (
            "지금 배치로 다시 잡으면"
            if intent == "regenerate"
            else f"{pool_no}.{start_no}~{pool_no}.{start_no + span - 1}에 저장하면"
        )
        answer = self._ask_one(
            f"{lead} 이미 저장된 프리셋 {len(collisions)}개를 덮어씁니다: "
            f"{_preset_slot_list(collisions, pool_no)}. 진행할까요?",
            options=(
                QuestionOption(label=_PRESET_OVERWRITE_CONSENT_LABEL),
                QuestionOption(label=_PRESET_OVERWRITE_DECLINE_LABEL),
            ),
            why=(
                "Store Preset은 경고 없이 덮어쓰고 이 앱에는 프리셋 복원 경로가 "
                "없습니다 — 덮어쓴 프리셋은 사라집니다."
            ),
        )
        if answer is None:
            return _PresetSpanVerdict(
                "unanswered", collisions, pool_no=pool_no, pool_label=pool_label
            )
        # 승낙은 **명시적·일의적**이어야 한다. 자유 입력은 언제나 열려 있으므로
        # ("잠깐 확인해보고요", "안 되네요") 승낙어를 부분 문자열로 찾으면 비승낙이
        # 승낙으로 삼켜진다. 어절 단위로 판정하고, 승낙도 거절도 아니면 저장하지
        # 않되 **거절과는 다른 문면**으로 답한다.
        intent = _preset_answer_intent(answer)
        if intent == "consent":
            return _PresetSpanVerdict(
                "confirmed", collisions, pool_no=pool_no, pool_label=pool_label
            )
        if intent == "decline":
            return _PresetSpanVerdict(
                "declined", collisions, pool_no=pool_no, pool_label=pool_label
            )
        return _PresetSpanVerdict(
            "unrecognised", collisions, pool_no=pool_no, pool_label=pool_label
        )

    def _store_position_preset_looks(
        self,
        looks: Sequence[tuple],
        start_no: int,
        *,
        before: set[int] | None,
        bundle: str = "basic-preset",
        pool_no: int = POSITION_PRESET_POOL,
        apply: Callable[[object], Sequence[str]] = aimed_commands,
    ) -> _PresetStoreRun:
        """룩마다 적용 → ``Store`` → ``Label`` → ``ClearAll``을 **별개 번들**로
        디스패치한다 — 한 룩이 거절돼도 나머지 아홉은 산다.

        신규 저장과 재생성이 이 하나를 공유한다(plan.md §E 위험 2).
        """
        outcomes: list[CommandOutcome] = []
        stored: list[str] = []
        skipped_notes: list[str] = []
        expected: dict[int, str] = {}
        pending: dict[int, str] = {}
        for offset, (label, aims, skipped) in enumerate(looks):
            preset_no = start_no + offset
            if not aims:
                skipped_notes.append(
                    f"{label}({pool_no}.{preset_no}): 조준 가능한 장비 없음 — 건너뜀"
                )
                continue
            commands = [
                *apply(aims),
                *_preset_store_commands(pool_no, preset_no, label),
                "ClearAll",
            ]
            executed = self._dispatch_declared(
                ToolCall(
                    id=f"{bundle}-{preset_no}",
                    name="run_commands",
                    arguments={"commands": commands},
                ),
                risk=showfile_write_risk(commands, kind="position_preset_look"),
            )
            outcomes.extend(executed.command_outcomes)
            stored.append(f"{pool_no}.{preset_no} '{label}'")
            expected[preset_no] = label
            statuses = {outcome.status for outcome in executed.command_outcomes}
            # 차단이 대기보다 우선한다 — 한 번들에 둘이 섞이면 "기다리면 된다"가
            # 아니라 "이 번들은 착지하지 않는다"가 운영자에게 필요한 사실이다.
            if statuses & _PRESET_GATE_BLOCKED_STATUSES:
                pending[preset_no] = "blocked"
            elif statuses & _PRESET_GATE_AWAITING_STATUSES:
                pending[preset_no] = "awaiting"
            if skipped:
                skipped_notes.append(f"{label}: FID {', '.join(str(fid) for fid in skipped)} 제외")
        return _PresetStoreRun(
            outcomes=tuple(outcomes),
            stored=tuple(stored),
            skipped_notes=tuple(skipped_notes),
            expected=expected,
            pending=pending,
            before=None if before is None else frozenset(before),
        )

    def _verify_preset_span_stored(
        self,
        run: _PresetStoreRun,
        *,
        pool_no: int = POSITION_PRESET_POOL,
        pool_label: str = "Position",
    ) -> str:
        """저장 루프가 끝난 뒤 풀을 **정확히 한 번** 되읽어 산술로 보고한다.

        이 저장소는 좌표 쓰기에서 이미 *"성공은 관측에서만 나온다"* 를 규율로
        갖는다. 프리셋 저장만 요청을 완료로 보고해 왔다 — 그리고 프리셋은 백업이
        원리적으로 불가능하다(spec.md §A.3).

        **보고이지 자기수정 루프가 아니다** — 미확인을 찾아도 재시도하지 않고
        회신을 오류 상태로 만들지도 않는다(REQ-PRESETGUARD-010).
        """
        if not run.expected:
            return ""
        slots = self._position_preset_pool_slots(pool_no=pool_no)
        if slots is None:
            # 판독 불가는 통과가 아니다 — 확인됨으로 보고하지 않는다.
            return (
                f"저장 결과를 되읽지 못했습니다 — {pool_label} 풀 판독 실패로 "
                f"{len(run.expected)}개 전건 미검증입니다."
            )
        # 슬롯 존재만으로는 **덮어쓰기가 착지했는지** 알 수 없다. 저장 직전에 이미
        # 차 있던 슬롯은 새 값이 들어갔든 안 들어갔든 똑같이 "있음"으로 보인다.
        # 응답기가 슬롯 번호(`i`)만 보내므로 내용을 대조할 수단이 없다 — 그래서
        # 사전 점유 슬롯은 **확인으로 세지 않고** 별도 범주로 정직하게 적는다.
        # 관측할 수 없는 것을 주장하지 않는다는 것이 이 SPEC의 규율이며, 하필
        # 덮어쓰기 경로에서 거짓 확인이 가장 많이 나온다.
        # 사전 판독 실패(`before is None`)와 사전 점유 관측은 **다른 상태**다. 앞은
        # 그 슬롯이 원래 차 있었는지조차 모르는 것이고, 뒤는 차 있었음을 관측했으나
        # 응답기가 슬롯 번호(`i`)만 보내 내용을 대조할 수단이 없는 것이다. 둘을 한
        # 바구니에 담아 "저장 전부터 차 있던 슬롯이라"고 적으면 **관측하지 않은 사전
        # 상태를 단언**하게 되고, 그것은 이 SPEC이 닫으려는 결함과 같은 형상이다.
        pre_state_unknown = run.before is None
        preexisting = frozenset() if pre_state_unknown else run.before
        landed, unprovable, unknown_before = [], [], []
        waiting, blocked, missing = [], [], []
        for no in sorted(run.expected):
            disposition = run.pending.get(no)
            if disposition == "blocked":
                blocked.append(no)
            elif disposition == "awaiting":
                waiting.append(no)
            elif no not in slots:
                missing.append(no)
            elif pre_state_unknown:
                unknown_before.append(no)
            elif no in preexisting:
                unprovable.append(no)
            else:
                landed.append(no)
        parts = [f"되읽기: 기대 {len(run.expected)}개 중 {len(landed)}개 확인"]
        if unknown_before:
            parts.append(
                f"덮어쓰기 확인 불가 {_preset_slot_list(unknown_before, pool_no)} — 저장 전 "
                "상태를 읽지 못해 원래 비어 있었는지 차 있었는지 알 수 없습니다"
            )
        if unprovable:
            parts.append(
                f"덮어쓰기 확인 불가 {_preset_slot_list(unprovable, pool_no)} — 저장 전부터 "
                "차 있던 슬롯이라 값이 바뀌었는지 콘솔에서 읽을 수 없습니다"
            )
        if waiting:
            parts.append(f"승인 대기 {_preset_slot_list(waiting, pool_no)} — 승인 후 반영")
        if blocked:
            parts.append(f"게이트 차단 {_preset_slot_list(blocked, pool_no)} — 반영되지 않음")
        if missing:
            parts.append(f"미확인 {_preset_slot_list(missing, pool_no)}")
        return "; ".join(parts) + "."

    def _regenerate_position_presets(self, text: str) -> InstructionResult | None:
        """*"지금 배치로 기본 포지션 다시 잡아줘"* — BASIC 구간을 제자리 갱신한다.

        디스패치 등록은 ``_basic_position_presets``보다 **앞**이다: 기존 트리거가
        '잡아'를 이미 대안으로 갖고 있어 재생성 문장을 함께 매치하므로, 겹치는
        입력의 행선지를 등록 순서로 고정한다(REQ-PRESETGUARD-015). 판정·저장
        규율은 전부 ``_regenerate_position_preset_sequence``에 있다 — FX 재생성과
        공유하므로 두 경로의 안전 동작이 갈라질 수 없다.
        """
        if _REGENERATE_POSITIONS_REQUEST.search(text) is None:
            return None
        return self._regenerate_position_preset_sequence(
            text,
            noun="기본 포지션",
            build=basic_position_presets,
            read_id="regenerate-presets-read",
            bundle="basic-preset",
            store_example="기본 포지션 10개 저장",
            first_label=BASIC_POSITION_SEQUENCE[0],
        )

    def _regenerate_fx_position_presets(self, text: str) -> InstructionResult | None:
        """*"지금 배치로 이펙트 포지션 다시 잡아줘"* — FX 구간을 제자리 갱신한다.

        페이저 시퀀스는 FX 프리셋의 REFERENCE를 들고 스윙하므로, 리그가 바뀐 뒤
        같은 번호에 다시 저장하면 그 프리셋을 쓰는 모든 이펙트가 새 좌표를
        따라온다 — BASIC 재생성과 동일한 논거다. 디스패치 등록은
        ``_fx_position_presets``보다 **앞**이다: FX 저장 트리거도 '잡아'를
        대안으로 가져 재생성 문장을 함께 매치한다(REQ-PRESETGUARD-015와 같은
        형상). 어휘(이펙트/효과/fx)는 BASIC(기본/베이직)과 서로소라 두 재생성이
        서로의 문장을 삼키지 않는다.
        """
        if _REGENERATE_FX_POSITIONS_REQUEST.search(text) is None:
            return None
        return self._regenerate_position_preset_sequence(
            text,
            noun="FX 포지션",
            build=fx_position_presets,
            read_id="regenerate-fx-presets-read",
            bundle="fx-preset",
            store_example="FX 포지션 10개 저장",
            first_label=FX_POSITION_SEQUENCE[0],
        )

    def _regenerate_position_preset_sequence(
        self,
        text: str,
        *,
        noun: str,
        build: Callable[[Sequence], Sequence[tuple]],
        read_id: str,
        bundle: str,
        store_example: str,
        first_label: str,
        pool_no: int = POSITION_PRESET_POOL,
        pool_label: str = "Position",
        read: Callable[[str], Sequence | InstructionResult] | None = None,
        apply: Callable[[object], Sequence[str]] = aimed_commands,
        lead_intro: str = "지금 리그 배치로",
        tail: str = "이 프리셋을 참조하는 큐는 별도 수정 없이 새 좌표를 따라갑니다.",
        disclosure: str = "",
    ) -> InstructionResult | None:
        """이미 저장된 10칸 구간을 지금 배치로 **제자리 갱신**한다 — 공용 몸통.

        큐는 프리셋 REFERENCE를 들고 있으므로(``pointing.py`` ``position_preset_
        store_commands`` 독스트링) 같은 번호에 다시 저장하면 그 프리셋을 쓰는 모든
        큐가 따라온다. 새 번호에 저장하면 기존 큐는 옛 좌표를 계속 가리키므로
        재생성이 성립하지 않는다 — 그래서 **새 시작 번호를 묻지 않는다.**

        BASIC과 FX가 이 하나를 공유한다(신규 저장의
        ``_store_position_preset_sequence``와 같은 이유): 풀 미상 거부·10칸 구간
        탐색·명시 번호 대조·덮어쓰기 카드·되읽기 산술이 두 곳에 복제되면 한쪽만
        갱신되는 드리프트가 생긴다.
        """
        source = self._read_pointing_coordinates if read is None else read
        fixtures = source(read_id)
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                f"좌표가 확인된 장비가 없어 {noun} 재생성을 시작하지 않았습니다."
            )
        pool_children = self._position_preset_pool_children(pool_no=pool_no)
        if pool_children is None:
            # 신규 저장(REQ-004, 진행)과 **반대**다 — 재생성은 표적 구간의 존재를
            # 전제하므로 미상 위에서 진행할 수 없다(REQ-PRESETGUARD-013).
            return self._pointing_refusal(
                f"{pool_label} 풀을 읽지 못해 다시 잡을 구간을 확인하지 못했습니다 — "
                "표적을 모르는 상태에서는 저장하지 않습니다."
            )
        pool_slots = set(pool_children)
        run_starts = self._position_preset_ready_starts(slots=pool_slots, pool_no=pool_no)
        if not run_starts:
            return self._pointing_refusal(
                f"10칸 연속 저장된 {noun} 구간을 찾지 못해 다시 잡을 자리가 "
                f"없습니다 — 먼저 '{store_example}'을 실행해 주세요."
            )
        # 가족 판별 — 구간 첫 슬롯의 이름이 시퀀스 첫 라벨과 일치해야 같은
        # 가족이다(콘솔의 중복명 자동 접미 '#N' 허용). 실측 2026-08-16: BASIC
        # (2.21~30)과 FX(2.41~50)가 한 덩어리로 이어진 풀에서 런 시작은 21
        # 하나뿐이라 FX 재생성이 카드 한 장 없이 2.21을 자동 선택, 기본
        # 프리셋 10개가 FX 값으로 덮였다. 그래서 후보는 런 시작이 아니라
        # **라벨이 맞는 모든 10칸 저장 지점**이다. 이름을 모르는 페이로드
        # (구버전)는 판별 불가로 런 시작을 그대로 후보에 남긴다 — 필터는
        # 아는 것만 거른다.
        span = len(BASIC_POSITION_SEQUENCE)

        def _is_family(name: object) -> bool:
            return isinstance(name, str) and (
                name == first_label or name.startswith(f"{first_label}#")
            )

        def _full_span(start: int) -> bool:
            return all(start + offset in pool_slots for offset in range(span))

        labeled = [
            slot
            for slot in sorted(pool_slots)
            if _is_family(pool_children.get(slot)) and _full_span(slot)
        ]
        unknown_runs = [
            start for start in run_starts if not isinstance(pool_children.get(start), str)
        ]
        ready = sorted(set(labeled) | set(unknown_runs))
        if not ready:
            return self._pointing_refusal(
                f"저장된 10칸 구간은 있으나 첫 슬롯 라벨이 '{first_label}'인 "
                f"{noun} 구간이 없습니다 — 먼저 '{store_example}'을 실행해 주세요."
            )
        # 지시가 번호를 담고 있으면 그 번호로 **재생성 안에서** 구간을 고른다.
        # 의도가 경로를 정하고, 번호는 그 경로 안의 구간을 정한다 — 번호가 있다고
        # 신규 저장으로 넘기면 "21번부터 기본 포지션 다시 잡아줘"가 풀 미상일 때
        # 재생성의 엄격한 규칙(미상이면 저장 안 함)을 잃고 카드 한 장 없이
        # 2.21~2.30을 덮어쓴다 — 이 SPEC이 없애려던 바로 그 형상이다.
        named = _BASIC_POSITIONS_START.search(text)
        if named is not None:
            named_no = int(named.group("no"))
            if (
                named_no not in ready
                and _full_span(named_no)
                and not _is_family(pool_children.get(named_no))
                and isinstance(pool_children.get(named_no), str)
            ):
                return self._pointing_refusal(
                    f"{named_no}번 구간의 첫 슬롯 라벨이 '{first_label}'이 아니라 "
                    f"{noun} 구간이 아닙니다 — 다른 가족의 프리셋을 덮지 않도록 "
                    "저장하지 않았습니다."
                )
            start_no = _preset_pick_ready_span([named_no], ready)
        elif len(ready) == 1:
            start_no = ready[0]
        else:
            answer = self._ask_one(
                "어느 구간을 지금 배치로 다시 잡을까요? 10칸 연속 저장된 구간을 "
                "콘솔에서 확인했습니다.",
                options=tuple(
                    QuestionOption(label=f"{start} ({pool_no}.{start}~{pool_no}.{start + 9})")
                    for start in ready
                ),
                why=("재생성은 그 자리를 덮어씁니다 — 어느 쇼의 구간인지는 운영자만 압니다."),
            )
            start_no = _preset_answer_to_ready_span(answer, ready, pool_no)
        if start_no is None:
            return self._pointing_refusal(
                "다시 잡을 구간을 하나로 특정하지 못해 저장하지 않았습니다. "
                f"10칸 연속 저장된 구간은 {_preset_slot_list(ready, pool_no)}에서 시작합니다 — "
                "그중 하나의 시작 번호만 답해 주세요."
            )
        verdict = self._confirm_preset_span_overwrite(
            start_no, pool_slots, intent="regenerate", pool_no=pool_no, pool_label=pool_label
        )
        if not verdict.proceed:
            return self._pointing_refusal(_preset_overwrite_refusal(verdict))
        try:
            looks = build(fixtures)
        except SpatialPointingError as error:
            return self._pointing_refusal(f"{noun}을 계산할 수 없습니다: {error}")
        # 판독 실패는 승인 카드가 들고 나간다 — 회신은 쓰기 뒤에야 조립된다.
        with self._approval_advisory(verdict.approval_advisory):
            run = self._store_position_preset_looks(
                looks, start_no, before=pool_slots, bundle=bundle, pool_no=pool_no, apply=apply
            )
        if not run.stored:
            return self._pointing_refusal(
                "어느 포지션도 계산되지 않아 프리셋을 저장하지 않았습니다."
            )
        return InstructionResult(
            status="ok",
            text=_preset_reply_text(
                run,
                verdict,
                self._verify_preset_span_stored(run, pool_no=pool_no, pool_label=pool_label),
                lead=(
                    f"{lead_intro} {noun} {len(run.stored)}개를 같은 자리에 "
                    f"다시 저장 요청했습니다: {', '.join(run.stored)}."
                    + (f" {disclosure}" if disclosure else "")
                ),
                tail=tail,
            ),
            command_outcomes=run.outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _resolve_named_pool_no(self, target_name: str, *, probe_id: str) -> int | None:
        """이름이 정확히 ``target_name``인 프리셋 풀의 번호 — 공용 몸통.

        `instantiate.py:220`의 함정을 세션 계층에 적용한 것이다(REQ-COLORPRESET-
        002): *"Preset 4.1 = Color"는 룰북 예시 프로즈이지 이 쇼파일의 계약이
        아니다* — 풀 이름은 운영자가 바꿀 수 있으므로 번호를 하드코딩하면
        손으로 만든 프리셋을 덮는다. ``DataPool/PresetPools`` 자식에서 이름
        일치 풀을 찾고, 실패·부재·절단은 전부 ``None``(거부)이다. 풀 목록은
        십수 개 규모라 페이징 없이 한 창을 읽고, 절단 주장(플래그 또는
        childCount 산술)이 있으면 추측하지 않는다. Color/Dimmer/All 1 세
        리졸버가 이름 문자열만 다른 복사본 3본으로 갈라져 있던 것을 한
        몸통으로 통합했다(2026-08-17 리뷰 — 거절 규율이 한쪽만 고쳐져
        조용히 갈라지는 분기 위험 제거). 프로브 id는 호출자별로 유지된다.
        """
        pool_root = self._rig_paths.get("preset_pools", "DataPool/PresetPools")
        probe = self._registry.dispatch(
            ToolCall(
                id=probe_id,
                name="query_state",
                arguments={"path": pool_root},
            )
        )
        if probe.result.is_error:
            return None
        try:
            payload = json.loads(probe.result.content)
        except (json.JSONDecodeError, TypeError):
            return None
        children = payload.get("children") if isinstance(payload, dict) else None
        if not isinstance(children, list):
            return None
        node = payload.get("node")
        child_count = node.get("childCount") if isinstance(node, dict) else None
        if bool(payload.get("truncated")) or (
            isinstance(child_count, int) and child_count > len(children)
        ):
            # 절단된 목록에 대상 풀이 없다 ≠ 풀이 없다 — 모름은 거부다.
            return None
        for child in children:
            if not isinstance(child, dict) or child.get("name") != target_name:
                continue
            try:
                return int(child.get("i", child.get("no")))
            except (TypeError, ValueError):
                return None
        return None

    def _resolve_color_pool_no(self) -> int | None:
        """The Color pool's NUMBER — ``_resolve_named_pool_no`` 위임.

        M0 실측(progress.md §E.1): 이 리그는 1 Dimmer · 2 Position · 3 Gobo ·
        4 Color · 5 Beam.
        """
        return self._resolve_named_pool_no("Color", probe_id="basic-color-pool-resolve")

    def _color_rig_fixture_pairs(
        self,
    ) -> tuple[list[tuple[int, int]], list[int]] | None:
        """``((slot, fid) …, fid_unread_slots)`` for every patched fixture —
        or None when the patch container cannot be read completely.

        컬러 저장은 좌표가 필요 없으므로 ``get_spatial_context``(픽스처당 4회
        속성 왕복) 대신 컨테이너 자식 목록(페이징 판독, 41대 리그는 24캡을
        넘는다)과 슬롯당 ``fid`` 속성 1회로 짝을 만든다. 판별(``_color_capable_
        fids``)은 slot 경로로 속성을 읽고, 선택·산술 고지는 fid로 말하므로 둘
        다 필요하다. fid를 읽지 못한 슬롯은 산술에서 이름을 부를 수 없으므로
        짝에서 빼고 슬롯 번호로 별도 보고한다(침묵 축소 금지, REQ-005).
        """
        fixtures_root = self._rig_paths.get("fixtures", "Patch/Stages/1/Fixtures")
        children = self._paged_pool_children(fixtures_root, probe_id="basic-color-fixture-list")
        if children is None:
            return None
        pairs: list[tuple[int, int]] = []
        fid_unread: list[int] = []
        for slot in sorted(children):
            read = read_properties(self._current_cue_port, f"{fixtures_root}/{slot}", ("fid",))[
                "fid"
            ]
            if not read.ok:
                fid_unread.append(slot)
                continue
            try:
                pairs.append((slot, int(str(read.value).strip())))
            except ValueError:
                fid_unread.append(slot)
        return pairs, fid_unread

    def _color_capability_and_disclosure(
        self, *, noun: str, probe_id_prefix: str
    ) -> tuple[list[int], str] | InstructionResult:
        """패치 열거 → 3-hop 컬러 판별 → 산술 고지 — ``(capable, disclosure)``
        또는 거부. 순서가 규율이다: ① 패치 픽스처 (slot, fid) 짝 열거(부분
        판독 = 거부 — 반쪽 리그에 색을 칠하지 않는다, 좌표 판독과 같은 규율)
        ② 3-hop 판별로 컬러 가능 FID만 남기고(REQ-005, fail-closed) ③ 제외·
        판별 불가를 대수+FID 산술로 고지 문장에 적는다(침묵 축소 금지).

        컬러(Color 풀)와 콤보(All 1 풀)가 공유하는 **뒷부분**이다 — 갈라지는
        것은 저장 풀 해석뿐. 두 호출자에 문면 동일 본문이 복사돼 있던 것을
        통합했다(2026-08-17 리뷰 — 거절·고지 문면이 한쪽만 고쳐져 조용히
        갈라지는 분기 위험 제거). 순수 추출 — 메시지 문면은 리팩터 이전과
        문자 단위로 동일하다.
        """
        enumerated = self._color_rig_fixture_pairs()
        if enumerated is None:
            return self._pointing_refusal(
                f"패치된 픽스처 목록을 읽지 못해 {noun} 프리셋을 시작하지 않았습니다."
            )
        pairs, fid_unread = enumerated
        if not pairs:
            return self._pointing_refusal(
                f"패치된 픽스처가 확인되지 않아 {noun} 프리셋을 시작하지 않았습니다."
            )
        capable, excluded, undetermined = self._color_capable_fids(
            pairs, probe_id_prefix=probe_id_prefix
        )
        if not capable:
            return self._pointing_refusal(
                f"컬러 어트리뷰트(ColorRGB)가 확인된 장비가 없어 {noun} 프리셋을 "
                f"저장하지 않았습니다 — 전체 {len(pairs)}대 중 컬러 없음 "
                f"{len(excluded)}대, 판별 불가 {len(undetermined)}대."
            )
        parts = [f"컬러 판별: 전체 {len(pairs)}대 중 {len(capable)}대 적용"]
        if excluded:
            parts.append(
                f"컬러 어트리뷰트 없음 {len(excluded)}대"
                f"(FID {', '.join(str(fid) for fid in excluded)}) 제외"
            )
        if undetermined:
            parts.append(
                f"판별 불가 {len(undetermined)}대"
                f"(FID {', '.join(str(fid) for fid in undetermined)}) 제외 — "
                "판독 실패는 보유로 치지 않습니다"
            )
        if fid_unread:
            parts.append(
                f"FID 미판독 {len(fid_unread)}대"
                f"(패치 슬롯 {', '.join(str(slot) for slot in fid_unread)}) 제외"
            )
        return capable, ", ".join(parts) + "."

    def _color_pool_and_capable_fids(
        self, *, noun: str
    ) -> tuple[int, list[int], str] | InstructionResult:
        """Color 풀 번호 해석 + 3-hop 컬러 판별 + 산술 고지 — ``(pool_no,
        capable, disclosure)`` 또는 거부.

        팔레트 색상표 저장(``_color_preset_material``)과 멀티컬러 페이저
        저장(``_color_phaser_preset_material``)이 공유하는 **앞부분**이다 —
        룩(스텝 커맨드) 구성만 갈라진다. 풀 해석 실패 = 거부(REQ-002),
        판별·고지는 ``_color_capability_and_disclosure`` 공용 뒷부분.
        """
        pool_no = self._resolve_color_pool_no()
        if pool_no is None:
            return self._pointing_refusal(
                "Color 풀을 찾지 못했습니다 — 프리셋 풀 목록에서 이름이 'Color'인 "
                f"풀을 확인하지 못해 {noun} 프리셋을 시작하지 않았습니다. "
                "풀 번호를 추측해 저장하면 다른 풀의 프리셋을 덮을 수 있습니다."
            )
        shared = self._color_capability_and_disclosure(noun=noun, probe_id_prefix="basic-color")
        if isinstance(shared, InstructionResult):
            return shared
        capable, disclosure = shared
        return pool_no, capable, disclosure

    def _color_preset_material(
        self, *, noun: str
    ) -> (
        tuple[int, list[int], tuple[tuple[str, tuple[str], tuple[()]], ...], str]
        | InstructionResult
    ):
        """컬러 저장·재생성이 공유하는 소재 — ``(pool_no, capable, looks,
        disclosure)`` 또는 거부. 공유 앞부분은 ``_color_pool_and_capable_
        fids``(REQ-COLORPRESET-006 리팩터), 이 함수는 팔레트 단일-스텝 룩
        구성만 맡는다.
        """
        shared = self._color_pool_and_capable_fids(noun=noun)
        if isinstance(shared, InstructionResult):
            return shared
        pool_no, capable, disclosure = shared
        looks = tuple(
            (label, (_color_apply_command(capable, rgb),), ())
            for label, rgb in COLOR_PALETTE_SEQUENCE
        )
        return pool_no, capable, looks, disclosure

    def _color_phaser_preset_material(
        self, *, noun: str
    ) -> (
        tuple[int, list[int], tuple[tuple[str, tuple[str, ...], tuple[()]], ...], str]
        | InstructionResult
    ):
        """멀티컬러 페이저 저장·재생성이 공유하는 소재 — ``_color_preset_
        material``과 앞부분(``_color_pool_and_capable_fids``)을 공유하고,
        룩 구성만 갈라진다: 팔레트 단일 값 대신 ``COLOR_PHASER_SEQUENCE``의
        스텝 시퀀스 + Form + Phase 커맨드를 싣는다(핸드오프 §2 지침 2).
        """
        shared = self._color_pool_and_capable_fids(noun=noun)
        if isinstance(shared, InstructionResult):
            return shared
        pool_no, capable, disclosure = shared
        looks = tuple(
            (
                label,
                (
                    *_color_phaser_step_commands(
                        capable, tuple(_COLOR_PALETTE_RGB[step_label] for step_label in steps)
                    ),
                    *_color_phaser_form_commands(form),
                    _color_phaser_phase_command(phase),
                ),
                (),
            )
            for label, steps, form, phase in COLOR_PHASER_SEQUENCE
        )
        return pool_no, capable, looks, disclosure

    def _basic_color_presets(self, text: str, *, forced: bool = False) -> InstructionResult | None:
        """*"기본 컬러 프리셋을 N번부터 저장해줘"* — 표준 무대 팔레트 10색을
        해석된 Color 풀의 연속 10칸에 저장한다(SPEC-COPILOT-COLORPRESET-001).

        포지션 프리셋 기계의 **세 번째 소비자**다: 번호 출처(지시 또는 카드 1장)·
        점유 검사·공용 덮어쓰기 카드·색별 독립 번들(적용→Store→Label→ClearAll)·
        페이지드 되읽기 산술 전부 ``_store_position_preset_sequence``가 수행한다
        — 컬러 전용 카드·어휘는 없다(REQ-003). 좌표 판독만 다르다: 컬러는 위치
        무관이라 3-hop 판별로 축소한 FID 목록이 소재다(REQ-005). 디스패치 등록은
        포지션 저장·재생성보다 **앞**이다 — `_BASIC_POSITIONS_REQUEST`가 명사
        대안 '프리셋'으로 "기본 컬러 프리셋 …" 문장을 함께 매치하기 때문이다
        (REQ-PRESETGUARD-015와 같은 등록 순서 고정).
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _BASIC_COLORS_REQUEST.search(text) is None
        ):
            return None
        material = self._color_preset_material(noun="기본 컬러")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._store_position_preset_sequence(
            text,
            noun="기본 컬러",
            sequence=tuple(label for label, _rgb in COLOR_PALETTE_SEQUENCE),
            build=lambda _fixtures: looks,
            read_id="basic-color-presets-read",
            bundle="basic-color-preset",
            example="기본 컬러 프리셋을 11번부터 저장해줘",
            pool_no=pool_no,
            pool_label="Color",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="표준 무대 팔레트에서 가져온",
            disclosure=disclosure,
        )

    def _regenerate_basic_color_presets(self, text: str) -> InstructionResult | None:
        """*"기본 컬러 다시 잡아줘"* — 저장된 컬러 10칸 구간을 제자리 갱신한다.

        리그가 바뀌면 컬러 가능 장비 집합이 바뀌므로 같은 번호에 다시 저장해
        프리셋을 쓰는 큐가 새 선택을 따라오게 한다 — 포지션·FX 재생성과 동일
        몸통(가족 필터 first_label='Warm White', 풀 미상 거부, REQ-004).
        디스패치 등록은 컬러 신규 저장보다 **앞**(트리거의 '잡아' 중첩)이고,
        포지션 재생성보다도 앞이다 — `_REGENERATE_POSITIONS_REQUEST`가 명사
        대안 '프리셋'으로 "기본 컬러 프리셋 다시 …" 문장을 함께 매치한다.
        """
        if _REGENERATE_COLORS_REQUEST.search(text) is None:
            return None
        material = self._color_preset_material(noun="기본 컬러")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._regenerate_position_preset_sequence(
            text,
            noun="기본 컬러",
            build=lambda _fixtures: looks,
            read_id="regenerate-color-presets-read",
            bundle="basic-color-preset",
            store_example="기본 컬러 프리셋 10개 저장",
            first_label=COLOR_PALETTE_SEQUENCE[0][0],
            pool_no=pool_no,
            pool_label="Color",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="표준 무대 팔레트로",
            tail="이 프리셋을 참조하는 큐는 별도 수정 없이 새 색을 따라갑니다.",
            disclosure=disclosure,
        )

    def _color_phaser_presets(self, text: str, *, forced: bool = False) -> InstructionResult | None:
        """*"멀티컬러 페이저 프리셋 저장해줘"* — 카탈로그 10종(핸드오프 §2)을
        해석된 Color 풀의 연속 10칸에 저장한다.

        기본 컬러 프리셋 기계의 소비자다: 번호 출처(지시 또는 카드 1장)·
        점유 검사·공용 덮어쓰기 카드·페이지드 되읽기 산술 전부
        ``_store_position_preset_sequence``가 수행한다 — 새 카드·새 어휘
        없음. 소재만 다르다: 팔레트 단일 값 대신 ``_color_phaser_preset_
        material``이 스텝·Form·Phase 커맨드를 실은 룩을 공급한다. 디스패치
        등록은 기본 컬러 저장·재생성 **바로 다음**이다 — 어휘축(멀티컬러/
        컬러 이펙트)이 기본 컬러 어휘축(기본/베이직/basic)과 서로소라 순서
        자체는 상호 오라우팅에 영향을 주지 않지만, 컬러 계열끼리 인접
        배치해 두 컬러 몸통의 안전 동작이 갈라지지 않는다는 것을 코드
        위치로도 드러낸다.
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _COLOR_PHASER_REQUEST.search(text) is None
        ):
            return None
        material = self._color_phaser_preset_material(noun="멀티컬러 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._store_position_preset_sequence(
            text,
            noun="멀티컬러 페이저",
            sequence=tuple(label for label, _steps, _form, _phase in COLOR_PHASER_SEQUENCE),
            build=lambda _fixtures: looks,
            read_id="color-phaser-presets-read",
            bundle="color-phaser-preset",
            example="멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool_no=pool_no,
            pool_label="Color",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="멀티컬러 페이저 카탈로그에서 가져온",
            disclosure=disclosure,
        )

    def _regenerate_color_phaser_presets(self, text: str) -> InstructionResult | None:
        """*"멀티컬러 페이저 다시 잡아줘"* — 저장된 페이저 10칸 구간을 제자리
        갱신한다.

        리그가 바뀌면 컬러 가능 장비 집합이 바뀌므로 같은 번호에 다시
        저장해 프리셋을 쓰는 큐가 새 선택을 따라오게 한다 — 기본 컬러
        재생성과 동일 몸통(가족 필터 first_label='Breathe Warm', 풀 미상
        거부). 디스패치 등록은 신규 저장보다 **앞**(트리거의 '잡아' 중첩,
        REQ-PRESETGUARD-015와 같은 형상)이다.
        """
        if _REGENERATE_COLOR_PHASER_REQUEST.search(text) is None:
            return None
        material = self._color_phaser_preset_material(noun="멀티컬러 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._regenerate_position_preset_sequence(
            text,
            noun="멀티컬러 페이저",
            build=lambda _fixtures: looks,
            read_id="regenerate-color-phaser-presets-read",
            bundle="color-phaser-preset",
            store_example="멀티컬러 페이저 프리셋 10개 저장",
            first_label=COLOR_PHASER_SEQUENCE[0][0],
            pool_no=pool_no,
            pool_label="Color",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="멀티컬러 페이저 카탈로그로",
            tail="이 프리셋을 참조하는 큐는 별도 수정 없이 새 페이저를 따라갑니다.",
            disclosure=disclosure,
        )

    def _resolve_combo_pool_no(self) -> int | None:
        """The 'All 1' pool's NUMBER — ``_resolve_named_pool_no`` 위임.

        콤보(컬러+디머 혼합) 프리셋은 T7 프로브(``10-combo-phaser-m0-probe.md``
        §1/§5)가 확정한 'All 1' 풀에 저장한다 — 함정②("혼합은 All 풀만
        수용")가 명령 수준에서는 재현되지 않았지만, 저장 콘텐츠가 실제로
        필터링됐는지는 판별 불가(같은 문서 §2 GAP)이므로 관측되지 않은
        위험을 피하는 보수적 선택으로 All 1을 기본 저장 대상으로 고정한다.
        이름이 정확히 ``All 1``인 풀만 찾는다(All 2~5는 별개 풀).
        """
        return self._resolve_named_pool_no("All 1", probe_id="combo-pool-resolve")

    def _combo_pool_and_capable_fids(
        self, *, noun: str
    ) -> tuple[int, list[int], str] | InstructionResult:
        """All 1 풀 번호 해석 + 3-hop 컬러 판별 + 산술 고지 — ``(pool_no,
        capable, disclosure)`` 또는 거부.

        ``_color_pool_and_capable_fids``의 미러 — 갈라지는 것은 저장 풀
        해석뿐(Color가 아니라 ``_resolve_combo_pool_no``), 판별·고지는
        ``_color_capability_and_disclosure`` 공용 뒷부분. 콤보는 컬러를
        반드시 포함하므로(T8 카탈로그, 모든 스텝이 팔레트 라벨을 갖는다)
        컬러 판별이 그대로 상한이다 — 디머는 판별 없이 컬러 가능 장비
        전체에 얹힌다(디머 없는 장비라는 반례가 이 리그 어디에도 없다는
        근거는 ``_dimmer_pool_and_fids`` 독스트링과 동일).
        """
        pool_no = self._resolve_combo_pool_no()
        if pool_no is None:
            return self._pointing_refusal(
                "All 1 풀을 찾지 못했습니다 — 프리셋 풀 목록에서 이름이 'All 1'인 "
                f"풀을 확인하지 못해 {noun} 프리셋을 시작하지 않았습니다. "
                "풀 번호를 추측해 저장하면 다른 풀의 프리셋을 덮을 수 있습니다."
            )
        shared = self._color_capability_and_disclosure(noun=noun, probe_id_prefix="combo")
        if isinstance(shared, InstructionResult):
            return shared
        capable, disclosure = shared
        return pool_no, capable, disclosure

    def _combo_phaser_preset_material(
        self, *, noun: str
    ) -> (
        tuple[int, list[int], tuple[tuple[str, tuple[str, ...], tuple[()]], ...], str]
        | InstructionResult
    ):
        """콤보(컬러+디머) 페이저 저장·재생성이 공유하는 소재 — ``_color_
        phaser_preset_material``의 미러, 소재만 ``COMBO_PHASER_SEQUENCE``의
        (팔레트 라벨, 디머%) 스텝 쌍 + Form + Phase 커맨드이고, 저장 풀은
        Color가 아니라 'All 1'(``_combo_pool_and_capable_fids``, T7 프로브).
        """
        shared = self._combo_pool_and_capable_fids(noun=noun)
        if isinstance(shared, InstructionResult):
            return shared
        pool_no, capable, disclosure = shared
        looks = tuple(
            (
                label,
                (
                    *_combo_phaser_step_commands(
                        capable,
                        tuple(
                            (_COLOR_PALETTE_RGB[palette_label], dimmer)
                            for palette_label, dimmer in steps
                        ),
                    ),
                    *_combo_phaser_form_commands(form),
                    _combo_phaser_phase_command(phase),
                ),
                (),
            )
            for label, steps, form, phase in COMBO_PHASER_SEQUENCE
        )
        return pool_no, capable, looks, disclosure

    def _combo_phaser_presets(self, text: str, *, forced: bool = False) -> InstructionResult | None:
        """*"콤보 페이저 프리셋 저장해줘"* — 카탈로그 10종(T8)을 해석된
        All 1 풀의 연속 10칸에 저장한다. ``_color_phaser_presets``의 미러 —
        공용 저장 몸통(``_store_position_preset_sequence``) 그대로, 소재만
        ``_combo_phaser_preset_material``이 공급한다.
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _COMBO_PHASER_REQUEST.search(text) is None
        ):
            return None
        material = self._combo_phaser_preset_material(noun="콤보 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._store_position_preset_sequence(
            text,
            noun="콤보 페이저",
            sequence=tuple(label for label, _steps, _form, _phase in COMBO_PHASER_SEQUENCE),
            build=lambda _fixtures: looks,
            read_id="combo-phaser-presets-read",
            bundle="combo-phaser-preset",
            example="콤보 페이저 프리셋을 51번부터 저장해줘",
            pool_no=pool_no,
            pool_label="All 1",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="콤보(컬러+디머) 페이저 카탈로그에서 가져온",
            disclosure=disclosure,
        )

    def _regenerate_combo_phaser_presets(self, text: str) -> InstructionResult | None:
        """*"콤보 페이저 다시 잡아줘"* — 저장된 콤보 페이저 10칸 구간을
        제자리 갱신한다. ``_regenerate_color_phaser_presets``의 미러 —
        가족 필터 first_label='Drop Slam', 풀 미상 거부.
        """
        if _REGENERATE_COMBO_PHASER_REQUEST.search(text) is None:
            return None
        material = self._combo_phaser_preset_material(noun="콤보 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, capable, looks, disclosure = material
        return self._regenerate_position_preset_sequence(
            text,
            noun="콤보 페이저",
            build=lambda _fixtures: looks,
            read_id="regenerate-combo-phaser-presets-read",
            bundle="combo-phaser-preset",
            store_example="콤보 페이저 프리셋 10개 저장",
            first_label=COMBO_PHASER_SEQUENCE[0][0],
            pool_no=pool_no,
            pool_label="All 1",
            read=lambda _call_id: capable,
            apply=list,
            lead_intro="콤보(컬러+디머) 페이저 카탈로그로",
            tail="이 프리셋을 참조하는 큐는 별도 수정 없이 새 페이저를 따라갑니다.",
            disclosure=disclosure,
        )

    def _resolve_dimmer_pool_no(self) -> int | None:
        """The Dimmer pool's NUMBER — ``_resolve_named_pool_no`` 위임.

        T4 프로브 전제검증(``09-dimmer-phaser-m0-probe.md``): 이 리그는
        풀 1='Dimmer'.
        """
        return self._resolve_named_pool_no("Dimmer", probe_id="basic-dimmer-pool-resolve")

    def _dimmer_pool_and_fids(self, *, noun: str) -> tuple[int, list[int], str] | InstructionResult:
        """Dimmer 풀 번호 해석 + 패치 픽스처 전량 열거 — ``(pool_no, fids,
        disclosure)`` 또는 거부.

        ``_color_pool_and_capable_fids``의 앞부분(풀 해석 → 픽스처 열거)을
        미러하되, 3-hop 컬러 판별(``_color_capable_fids``, REQ-COLORPRESET-
        005)의 대응물을 **두지 않는다** — T5 지시에 따른 의도적 생략, 근거는
        다음과 같다: 이 저장소의 기존 Dimmer 소비자(``spatial/mib.py:168``,
        ``spatial/pointing.py:324``, 본 파일의 무대 뒷조명 체인)는 전부 판별
        없이 대상 픽스처 전체에 ``Attribute 'Dimmer' At <n>``을 무조건 싣고,
        T4 프로브(``docs/research/ma3-effects/09-dimmer-phaser-m0-probe.md``
        §1/§2)도 ``'Dimmer'`` 속성명이 ``Group 11``(이 리그) 전체에서 거부
        없이 수락됨만 확인했다 — "Dimmer 없는 조명 장비"라는 반례를 이 리그·
        이 저장소 어디에서도 만들지 않아, 컬러처럼 fail-closed로 축소할
        근거가 없다. ``_color_rig_fixture_pairs``는 이름과 달리 컬러 속성을
        읽지 않는(패치 슬롯·fid 짝만 여는 범용 열거자)라 그대로 재사용한다.
        """
        pool_no = self._resolve_dimmer_pool_no()
        if pool_no is None:
            return self._pointing_refusal(
                "Dimmer 풀을 찾지 못했습니다 — 프리셋 풀 목록에서 이름이 'Dimmer'인 "
                f"풀을 확인하지 못해 {noun} 프리셋을 시작하지 않았습니다. "
                "풀 번호를 추측해 저장하면 다른 풀의 프리셋을 덮을 수 있습니다."
            )
        enumerated = self._color_rig_fixture_pairs()
        if enumerated is None:
            return self._pointing_refusal(
                f"패치된 픽스처 목록을 읽지 못해 {noun} 프리셋을 시작하지 않았습니다."
            )
        pairs, fid_unread = enumerated
        if not pairs:
            return self._pointing_refusal(
                f"패치된 픽스처가 확인되지 않아 {noun} 프리셋을 시작하지 않았습니다."
            )
        fids = sorted(fid for _slot, fid in pairs)
        disclosure = (
            (
                f"FID 미판독 {len(fid_unread)}대(패치 슬롯 "
                f"{', '.join(str(slot) for slot in fid_unread)}) 제외 — 판독 실패는 "
                "보유로 치지 않습니다."
            )
            if fid_unread
            else ""
        )
        return pool_no, fids, disclosure

    def _dimmer_preset_material(
        self, *, noun: str
    ) -> (
        tuple[int, list[int], tuple[tuple[str, tuple[str], tuple[()]], ...], str]
        | InstructionResult
    ):
        """디머 레벨 저장·재생성이 공유하는 소재 — ``(pool_no, fids, looks,
        disclosure)`` 또는 거부. ``_color_preset_material``의 미러, 공유
        앞부분은 ``_dimmer_pool_and_fids``, 이 함수는 레벨 단일-스텝 룩
        구성만 맡는다.
        """
        shared = self._dimmer_pool_and_fids(noun=noun)
        if isinstance(shared, InstructionResult):
            return shared
        pool_no, fids, disclosure = shared
        looks = tuple(
            (label, (_dimmer_apply_command(fids, value),), ())
            for label, value in DIMMER_LEVEL_SEQUENCE
        )
        return pool_no, fids, looks, disclosure

    def _dimmer_phaser_preset_material(
        self, *, noun: str
    ) -> (
        tuple[int, list[int], tuple[tuple[str, tuple[str, ...], tuple[()]], ...], str]
        | InstructionResult
    ):
        """디머 페이저 저장·재생성이 공유하는 소재 — ``_dimmer_preset_
        material``과 앞부분(``_dimmer_pool_and_fids``)을 공유하고, 룩 구성만
        갈라진다: 레벨 단일 값 대신 ``DIMMER_PHASER_SEQUENCE``의 스텝
        시퀀스 + Form + Phase 커맨드를 싣는다(``_color_phaser_preset_
        material`` 미러).
        """
        shared = self._dimmer_pool_and_fids(noun=noun)
        if isinstance(shared, InstructionResult):
            return shared
        pool_no, fids, disclosure = shared
        looks = tuple(
            (
                label,
                (
                    *_dimmer_phaser_step_commands(fids, values),
                    *_dimmer_phaser_form_commands(form),
                    _dimmer_phaser_phase_command(phase),
                ),
                (),
            )
            for label, values, form, phase in DIMMER_PHASER_SEQUENCE
        )
        return pool_no, fids, looks, disclosure

    def _basic_dimmer_presets(self, text: str, *, forced: bool = False) -> InstructionResult | None:
        """*"기본 디머 프리셋을 N번부터 저장해줘"* — 디머 레벨 10종을 해석된
        Dimmer 풀의 연속 10칸에 저장한다. ``_basic_color_presets``의 미러 —
        공용 저장 몸통(``_store_position_preset_sequence``)을 그대로 쓰고,
        소재만 ``_dimmer_preset_material``이 공급한다(컬러 판별 없음, T5
        지시).
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _BASIC_DIMMER_REQUEST.search(text) is None
        ):
            return None
        material = self._dimmer_preset_material(noun="디머 레벨")
        if isinstance(material, InstructionResult):
            return material
        pool_no, fids, looks, disclosure = material
        return self._store_position_preset_sequence(
            text,
            noun="디머 레벨",
            sequence=tuple(label for label, _value in DIMMER_LEVEL_SEQUENCE),
            build=lambda _fixtures: looks,
            read_id="basic-dimmer-presets-read",
            bundle="basic-dimmer-preset",
            example="디머 레벨 프리셋을 11번부터 저장해줘",
            pool_no=pool_no,
            pool_label="Dimmer",
            read=lambda _call_id: fids,
            apply=list,
            lead_intro="표준 디머 레벨에서 가져온",
            disclosure=disclosure,
        )

    def _regenerate_basic_dimmer_presets(self, text: str) -> InstructionResult | None:
        """*"기본 디머 다시 잡아줘"* — 저장된 디머 레벨 10칸 구간을 제자리
        갱신한다. ``_regenerate_basic_color_presets``의 미러 — 가족 필터
        first_label='Dim 10', 풀 미상 거부.
        """
        if _REGENERATE_DIMMER_REQUEST.search(text) is None:
            return None
        material = self._dimmer_preset_material(noun="디머 레벨")
        if isinstance(material, InstructionResult):
            return material
        pool_no, fids, looks, disclosure = material
        return self._regenerate_position_preset_sequence(
            text,
            noun="디머 레벨",
            build=lambda _fixtures: looks,
            read_id="regenerate-dimmer-presets-read",
            bundle="basic-dimmer-preset",
            store_example="디머 레벨 프리셋 10개 저장",
            first_label=DIMMER_LEVEL_SEQUENCE[0][0],
            pool_no=pool_no,
            pool_label="Dimmer",
            read=lambda _call_id: fids,
            apply=list,
            lead_intro="표준 디머 레벨로",
            tail="이 프리셋을 참조하는 큐는 별도 수정 없이 새 레벨을 따라갑니다.",
            disclosure=disclosure,
        )

    def _dimmer_phaser_presets(
        self, text: str, *, forced: bool = False
    ) -> InstructionResult | None:
        """*"디머 페이저 프리셋 저장해줘"* — 카탈로그 10종(T5)을 해석된 Dimmer
        풀의 연속 10칸에 저장한다. ``_color_phaser_presets``의 미러.
        """
        if _programming_artifact_target(text) != "preset" or (
            not forced and _DIMMER_PHASER_REQUEST.search(text) is None
        ):
            return None
        material = self._dimmer_phaser_preset_material(noun="디머 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, fids, looks, disclosure = material
        return self._store_position_preset_sequence(
            text,
            noun="디머 페이저",
            sequence=tuple(label for label, _values, _form, _phase in DIMMER_PHASER_SEQUENCE),
            build=lambda _fixtures: looks,
            read_id="dimmer-phaser-presets-read",
            bundle="dimmer-phaser-preset",
            example="디머 페이저 프리셋을 21번부터 저장해줘",
            pool_no=pool_no,
            pool_label="Dimmer",
            read=lambda _call_id: fids,
            apply=list,
            lead_intro="디머 페이저 카탈로그에서 가져온",
            disclosure=disclosure,
        )

    def _regenerate_dimmer_phaser_presets(self, text: str) -> InstructionResult | None:
        """*"디머 페이저 다시 잡아줘"* — 저장된 디머 페이저 10칸 구간을 제자리
        갱신한다. ``_regenerate_color_phaser_presets``의 미러 — 가족 필터
        first_label='Breathe Soft'.
        """
        if _REGENERATE_DIMMER_PHASER_REQUEST.search(text) is None:
            return None
        material = self._dimmer_phaser_preset_material(noun="디머 페이저")
        if isinstance(material, InstructionResult):
            return material
        pool_no, fids, looks, disclosure = material
        return self._regenerate_position_preset_sequence(
            text,
            noun="디머 페이저",
            build=lambda _fixtures: looks,
            read_id="regenerate-dimmer-phaser-presets-read",
            bundle="dimmer-phaser-preset",
            store_example="디머 페이저 프리셋 10개 저장",
            first_label=DIMMER_PHASER_SEQUENCE[0][0],
            pool_no=pool_no,
            pool_label="Dimmer",
            read=lambda _call_id: fids,
            apply=list,
            lead_intro="디머 페이저 카탈로그로",
            tail="이 프리셋을 참조하는 큐는 별도 수정 없이 새 페이저를 따라갑니다.",
            disclosure=disclosure,
        )

    #: 합성 문장이 고른 계열 → 그 계열을 실제로 실행하는 **기존** 핸들러 이름.
    #: 값이 바인딩된 함수가 아니라 이름인 것은 의도다 — 번호 카드·덮어쓰기
    #: 가드·계열별 독립 번들은 전부 그 핸들러 안에 있으므로 합성 경로는
    #: 어떤 규율도 복제하지 않고 ``getattr``로 원본을 부른다.
    _COMPOUND_FAMILY_HANDLERS = {
        "basic_position": "_basic_position_presets",
        "fx_position": "_fx_position_presets",
        "basic_color": "_basic_color_presets",
        "basic_dimmer": "_basic_dimmer_presets",
        "color_phaser": "_color_phaser_presets",
        "dimmer_phaser": "_dimmer_phaser_presets",
        "combo_phaser": "_combo_phaser_presets",
    }

    def _compound_preset_request(self, text: str) -> InstructionResult | None:
        """한 문장이 프리셋 계열을 **둘 이상** 지정했을 때 다중 선택 카드를 세우고,
        고른 계열을 등록 순서대로 이어서 실행한다.

        실측 근거(2026-08-19): "포지션, 컬러, 딤머의 기본 프리셋과 페이저
        프리셋을 설정하고 복합 프리셋도 All에 설정해줘"는 사전 핸들러 체인이
        **첫 매칭 하나만 실행하고 턴을 끝내는** 구조(``run_instruction``)와
        만나 여섯 계열 중 한 계열만 저장되거나, 아무 것도 매치하지 못해 LLM
        경로로 흘러 'Home' 하나만 생기는 결과를 냈다. 계열을 사람 대신 골라
        주는 것은 추측이므로(``Store Preset``은 경고 없이 덮어쓴다) 여기서
        하는 일은 **묻는 것**이다.

        규율 셋:

        1. 계열이 하나뿐인 문장은 ``None``\\ 을 돌려 **기존 단일 경로 그대로**
           흘려보낸다 — 카드도 새 문면도 없다(회귀 방지의 핵심).
        2. 카드는 한 장이다. 계열마다 한 장씩 묻지 않는다 —
           :meth:`_ask_one`\\ 의 ``multi=True``\\ 로 체크박스 한 장을 세우고,
           답은 고른 라벨을 ``", "``\\ 로 이은 문자열로 돌아온다.
        3. 실행은 원본 핸들러 호출뿐이다. 시작 번호 카드·덮어쓰기 동의·계열별
           독립 번들(적용→Store→Label→ClearAll)·되읽기는 전부 그 안에서 그대로
           일어난다 — 계열마다 자기 번호 카드를 그대로 낸다.

        한 계열이 거부·실패해도 나머지는 계속 진행하고, 끝에 계열별 결과를
        모은 요약 한 장을 돌린다 — look 하나가 거부돼도 나머지를 살리는 기존
        번들 규율과 같은 형상이다.

        「몇 계열인가」의 **단일 소재**는 ``PRESET_FAMILIES``\\ 의 ``matches``\\ 다 —
        여기에 두 번째 판정 규칙을 얹지 않는다. 얹어 본 적이 있다(프리셋 명사
        2회 · 동작 동사 2회 · 열거 구두점): 2026-08-17 리뷰가 등록 순서로 고정한
        세 문장이 축 어휘를 둘씩 담기 때문이었다. 그런데 그 셋은 레지스트리가
        콤보 토큰·축 결합 페이저 토큰을 걷어내면서 이미 한 계열로 확정되고
        (``TestCompositeVocabularyIsNotACompoundRequest``), 반대로 그 게이트는
        "페이저 프리셋 설정해줘"처럼 **정말 물어봐야 하는** 문장(어느 페이저
        계열인지 불명 + 단일 트리거는 하나도 매치하지 않음)을 LLM 경로로
        떨어뜨렸다. 그래서 지웠다 — 판정은 한 곳에서만 한다.
        """
        detected = tuple(family for family in PRESET_FAMILIES if family.matches(text))
        if len(detected) < 2:
            return None
        # 카드는 **일곱 계열 전부**를 싣고, 문장이 지목한 것만 미리 체크한다.
        # 지목된 것만 실으면 «… 모두 설정해줘»라고 적은 운영자에게 여섯 줄만
        # 보여 주게 되고(2026-08-19 재보고), 빠진 계열을 부르려면 문장을 다시
        # 써야 한다. 전부 실어 두면 카드 한 장에서 넓히거나 좁힐 수 있고,
        # 미체크 계열은 아무것도 저장하지 않으므로 덮어쓰기 위험도 늘지 않는다.
        rest = tuple(family for family in PRESET_FAMILIES if family not in detected)
        answer = self._ask_one(
            "한 문장에 프리셋 계열이 "
            f"{len(detected)}개 담겼습니다({' / '.join(f.label for f in detected)}). "
            "어느 계열을 저장할까요? 고른 계열을 순서대로 이어서 저장합니다."
            + (
                f" 나머지 {len(rest)}개({' / '.join(f.label for f in rest)})도 "
                "함께 고르실 수 있습니다."
                if rest
                else ""
            ),
            options=tuple(
                QuestionOption(
                    label=family.label,
                    description=f"{family.label} 카탈로그 10종을 연속 10칸에 저장합니다.",
                    selected=family in detected,
                )
                for family in PRESET_FAMILIES
            ),
            why=(
                "Store Preset은 경고 없이 덮어쓰고 이 앱에는 프리셋 복원 경로가 "
                "없습니다. 그래서 계열마다 시작 번호를 따로 여쭤보게 됩니다 — "
                "여기서 계열을 좁혀 두면 그만큼만 묻습니다. 체크된 계열이 이 문장이 "
                "지목한 것이고, 체크를 더하거나 풀어 그대로 바꾸실 수 있습니다."
            ),
            multi=True,
        )
        if answer is None:
            return InstructionResult(
                status="ok",
                text=(
                    f"프리셋 계열 {len(detected)}개({', '.join(f.label for f in detected)})가 "
                    "한 문장에 담겨 어느 계열을 저장할지 여쭤봤지만 답을 받지 못했습니다. "
                    "콘솔에는 아무것도 저장하지 않았습니다 — 계열을 고르시면 "
                    "고른 순서대로 시작 번호를 여쭤보고 저장합니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        # 카드가 **제시한** 것과 답으로 **받는** 것은 같은 집합이어야 한다.
        # 감지분으로 좁히면 카드에 미체크로 실어 둔 계열을 사용자가 체크했을 때
        # "알 수 없는 이름"으로 되돌려보내게 된다(2026-08-19 실측: 일곱 줄을 다
        # 체크했더니 «연출 포지션»만 거부됐다).
        by_label = {family.label: family for family in PRESET_FAMILIES}
        picked = [part.strip() for part in answer.split(",") if part.strip()]
        unknown = [part for part in picked if part not in by_label]
        if not picked or unknown:
            listed = ", ".join(unknown) if unknown else "(빈 답)"
            return InstructionResult(
                status="ok",
                text=(
                    f"고른 항목을 프리셋 계열로 알아보지 못해 아무것도 저장하지 "
                    f"않았습니다: {listed}. 어느 계열인지 추측하면 다른 계열의 "
                    "프리셋을 덮어쓸 수 있어 중단했습니다 — 아래 이름 중에서 "
                    f"골라 다시 말씀해 주세요: {', '.join(by_label)}."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        chosen_keys = {by_label[part].key for part in picked}
        # 실행 순서는 사용자가 체크한 순서가 아니라 ``PRESET_FAMILIES`` 순서다 —
        # 체크 순서는 UI 사정이고, 계열 간 순서는 등록 순서로 고정되어야 재현
        # 가능하다(사전 핸들러 등록 순서를 행선지 고정에 쓰는 것과 같은 규율).
        selected = [family for family in PRESET_FAMILIES if family.key in chosen_keys]
        outcomes: list[CommandOutcome] = []
        lines: list[str] = []
        statuses: list[str] = []
        stored = 0
        stopped: list[str] = []
        retries = 0
        model_calls = 0
        duration = 0.0
        for family in selected:
            handler = getattr(self, self._COMPOUND_FAMILY_HANDLERS[family.key])
            try:
                # `forced`: 계열은 **레지스트리**가 판정했고 사용자가 카드에서
                # 직접 체크해 확정했다. 핸들러의 트리거는 「수식어 → 축 → 동사」
                # 어순을 요구하는 단일 요청용 그물이라, 열거형 문장은 그 그물을
                # 빠져나간다 — 다시 검사하면 카드에서 고른 계열이 조용히
                # 건너뛰어진다(2026-08-19 실측: 일곱 중 다섯이 미저장).
                # 시작 번호 카드·덮어쓰기 가드·번들 규율은 그대로 살아 있다.
                result = handler(text, forced=True)
            except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
                self._audit.record(
                    {
                        "event": "compound_preset_family_error",
                        "family": family.key,
                        "raw_detail": repr(exc),
                    }
                )
                stopped.append(family.label)
                lines.append(
                    f"{family.label}: 실행 중 오류가 나 이 계열은 저장하지 못했습니다"
                    " — 나머지 계열은 계속 진행했습니다."
                )
                continue
            if result is None:
                # 계열 어휘는 감지했는데 해당 핸들러의 트리거가 이 문장을 받지
                # 않았다 — 조용히 넘기면 "저장했다"는 오보가 되므로 고지한다.
                stopped.append(family.label)
                lines.append(
                    f"{family.label}: 이 문장만으로는 저장 조건을 확정하지 못해 "
                    "건너뛰었습니다 — 이 계열만 따로 말씀해 주세요."
                )
                continue
            stored += 1
            statuses.append(result.status)
            outcomes.extend(result.command_outcomes)
            retries += result.retries_used
            model_calls += result.model_calls
            duration += result.duration_seconds
            lines.append(f"{family.label}: {result.text}")
        status = next((one for one in statuses if one != "ok"), "ok")
        order = " → ".join(family.label for family in selected)
        headline = f"고르신 프리셋 계열 {len(selected)}개를 이 순서로 처리했습니다: {order}"
        if stopped:
            headline += f" — {stored}개 진행, {len(stopped)}개 미저장({', '.join(stopped)})"
        return InstructionResult(
            status=status,
            text=headline + ".\n" + "\n".join(f"- {line}" for line in lines),
            command_outcomes=tuple(outcomes),
            retries_used=retries,
            model_calls=model_calls,
            duration_seconds=duration,
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
        executed = self._dispatch_declared(
            ToolCall(
                id="cue-store-write",
                name="run_commands",
                arguments={"commands": commands},
            ),
            risk=showfile_write_risk(commands, kind="position_cue_store"),
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
        # 2026-08-16 사용자 방향 확산: same verified-number proposals as the
        # design-interview path — empty sequence, console-confirmed presets.
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        requested_sequence = int(sequence_match.group("no")) if sequence_match is not None else None
        picked = self._song_pick_sequence(
            requested_sequence,
            purpose="포지션 큐 시트",
            refusal="시퀀스 번호를 받지 못해 큐 시트를 만들지 않았습니다.",
        )
        if isinstance(picked, InstructionResult):
            return picked
        sequence_no = picked
        preset_match = _SHEET_PRESET_START.search(text)
        if preset_match is not None:
            preset_start = int(preset_match.group("no"))
        else:
            asked = self._ask_position_preset_start(
                "프리셋 시작 번호를 받지 못해 큐 시트를 만들지 않았습니다."
            )
            if isinstance(asked, InstructionResult):
                return asked
            preset_start = asked
        if preset_start <= 0:
            return self._pointing_refusal("프리셋 시작 번호는 1 이상이어야 합니다.")
        fade_match = _CUE_FADE.search(text)
        fade_seconds = (
            float(fade_match.group("sec") or fade_match.group("sec2"))
            if fade_match is not None
            else 3.0
        )
        fids = [fid for fid, _position in fixtures]
        try:
            # 카드 t449 — t232 가 고친 세 경로와 같은 규율. 시트가 부를 라벨만
            # 모아 풀 1회 판독으로 실제 슬롯을 찾는다. `preset_start + index`
            # 는 그 슬롯이 진짜 그 라벨인지 보지 않았다(판독:
            # `.moai/reports/t449/verdict.md`). 못 찾거나 모호하면 여기서
            # 거부하고, 콘솔 쓰기는 한 줄도 나가지 않는다.
            needed_labels = required_sheet_labels(sections)
            preset_numbers = (
                self._resolve_position_preset_labels(
                    needed_labels, start=preset_start, span=len(BASIC_POSITION_SEQUENCE)
                )
                if needed_labels
                else {}
            )
            sheet = build_position_cue_sheet(
                sections,
                sequence_no=sequence_no,
                preset_numbers=preset_numbers,
                fids=fids,
                fade_seconds=fade_seconds,
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"포지션 큐 시트를 만들 수 없습니다: {error}")
        outcomes: list[CommandOutcome] = []
        for plan, bundle in zip(sheet.plans, sheet.bundles, strict=True):
            executed = self._dispatch_declared(
                ToolCall(
                    id=f"song-sheet-cue-{plan.cue_no:g}",
                    name="run_commands",
                    arguments={"commands": list(bundle)},
                ),
                risk=showfile_write_risk(bundle, kind="position_cue_sheet"),
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
                    QuestionOption(label="큐 타임 (자동 진행)"),
                    QuestionOption(label="수동 Go"),
                ),
                why=(
                    "Cue 저장 전에 수동 Go, 큐 타임(자동 진행), 타임코드 중 하나가 "
                    "명시적으로 확정돼야 합니다."
                ),
            )
            if answer is None:
                return None
            mode = _timing_mode_from_text(answer) or {
                "타임코드": "timecode",
                "큐 타임 (자동 진행)": "trig_time",
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
        layer_mapping: Sequence[Mapping[str, object]] = (),
        w_fids: frozenset[int] = frozenset(),
    ) -> tuple[str, ...]:
        bundle = composition.bundle
        if bundle is None:
            return ()
        phaser_slots, self._last_phaser_failures = self._phaser_slots_for_bundle(bundle)
        # 카드 t232 — 번호 참조를 라벨로 확인한다. 큐가 부르는 포지션 라벨을
        # 한 번에 모아 풀을 1회 판독으로 슬롯을 찾는다(`_phaser_slots_for_
        # bundle`과 같은 배치 규율) — `preset_start + index`는 그 슬롯이
        # 실제로 그 라벨인지 보지 않았다(판독: `.moai/reports/t232/verdict.md`).
        # 못 찾거나 모호하면 여기서 거부하고, 콘솔 쓰기는 한 줄도 나가지 않는다.
        needed_positions = {
            cue.position.stored for cue in bundle.cues if cue.position.stored is not None
        }
        position_slots = (
            self._resolve_position_preset_labels(
                needed_positions, start=preset_start, span=len(BASIC_POSITION_SEQUENCE)
            )
            if needed_positions
            else {}
        )
        # SPEC-LDDESIGN-001 M2 — 컨셉 색을 이 경로로 내보낸다. 미해소 사유는
        # 큐마다 모아 최종 회신에 노출한다(`_color_failure_note`).
        # 카드 t430 — w_fids(기본 빈 집합)는 `_song_color_value_lines`로
        # 그대로 전달한다. 빈 집합이면 오늘과 바이트 동일.
        color_failures: dict[str, str] = {}
        commands: list[str] = ["ChangeDestination Root"]
        for cue in bundle.cues:
            preset_no = None
            if cue.position.stored is not None:
                preset_no = position_slots[cue.position.stored]
            dimmer = cue.dimmer.key_pct
            color_lines, color_failure = _song_color_value_lines(cue, fids, w_fids)
            if color_failure is not None:
                color_failures[f"{cue.cue_number:g}"] = color_failure
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
            commands.extend(
                position_cue_bundle(
                    sequence_no,
                    plan,
                    fids,
                    extra_value_lines=(
                        *color_lines,
                        *_back_layer_value_lines(cue, layer_mapping),
                        *_phaser_cue_value_lines(cue, fids, phaser_slots),
                    ),
                )
            )
            if plan.premove:
                commands.append(premove_follow_command(sequence_no, plan))
        commands.extend(self._reviewed_song_timing_commands(bundle, sequence_no, timing))
        self._last_color_failures = color_failures
        return tuple(commands)

    def _phaser_slots_for_bundle(self, bundle) -> tuple[dict[str, tuple[int, int]], dict[str, str]]:
        """제안된 페이저 라벨을 실기에서 배치 해석한다(T12) — ``(resolved,
        failed)``.

        필요한 라벨만 중복 없이 한 번씩 조회한다(``_phaser_slot_by_label``,
        T11 §5 페이지드 열거 재사용) — 큐마다 반복 조회하지 않는다. 못 찾은
        라벨은 ``failed``에 사유를 남기고 ``resolved``에서 빠진다: 그 라벨을
        쓰는 모든 큐는 페이저 없이 그대로 진행한다 — 곡 설계 전체를 페이저
        부재로 무산시키지 않는다(계약 #4).
        """
        needed = {label for cue in bundle.cues if (label := _phaser_label_for_cue(cue)) is not None}
        resolved: dict[str, tuple[int, int]] = {}
        failed: dict[str, str] = {}
        for label in needed:
            slot = self._phaser_slot_by_label(label)
            if slot is None:
                failed[label] = f"'{label}' 페이저 프리셋을 콘솔에서 찾지 못했습니다"
            else:
                resolved[label] = slot
        return resolved, failed

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
        """디자인 요청 한 턴 — 본문은 ``_song_design_interview_run``.

        카드 t311 — 좌표 결손 고지는 이 경로의 **모든** 반환 지점에 실려야 한다
        (재질의 대기, 승인 대기, 저장 완료 …). 반환 지점마다 문장을 붙이면
        하나를 빠뜨리는 것이 기본값이 되므로, 고지는 여기 한 곳에서 붙인다 —
        카드 t277 이 연 ``InstructionResult.notices`` 통로를 그대로 쓴다.
        결손이 없는 회차에서는 빈 문자열이라 문면이 이전과 같다.
        """
        self._design_coord_notice = ""
        result = self._song_design_interview_run(text)
        if isinstance(result, InstructionResult) and self._design_coord_notice:
            return replace(result, notices=(*result.notices, self._design_coord_notice))
        return result

    def _song_design_interview_run(self, text: str) -> InstructionResult | None:
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
        # 카드 t302 — 업로드→분석→확인으로 이미 확정한 구간이 세션에 있는데, 이
        # 경로는 지시문에서만 구간을 읽어서 감독이 같은 구간을 손으로 다시 적어야
        # 했다. 그래서 분석 절반과 타임라인 절반이 이어지지 않았다. 지시문이 구간을
        # 하나도 안 들고 있을 때에만 확정 기록을 기본값으로 쓴다 — 명시한 구간이
        # 조용히 덮이는 일은 없다(prepare_songcue 의 REQ-SONGCONFIRM-009 와 같은 규칙).
        #
        # 이름은 `prepare_songcue` 가 이미 쓰는 중립 ASCII `S<n>` 을 그대로 따른다
        # (`_confirmed_section_input`, plan.md §C D5) — 확정 카드의 라벨은
        # `0:00–0:24 · D3` 이라 룩 어휘도 아니고 MA3 큐 라벨로도 안 남는다.
        # 무드는 **비운다**: DSP 는 시각과 D 레벨을 재지, 그 구간이 어떤 느낌인지는
        # 재지 않는다. 없는 것을 지어내는 대신 비워 두면 기존 미해소(requery) 경로가
        # 구간마다 감독에게 카드를 띄운다 — 이 경로가 원래 그러라고 있는 자리다.
        #
        # 카드 t383 — D 레벨은 무드와 달리 비우지 않는다. DSP 가 실측한 값을
        # `d_level` 에 그대로 싣는다 — 무드를 비운 채로 두면 `resolve_section`
        # 이 전역 기본값(D3)으로 떨어져 확정 실측값이 조용히 버려졌었다
        # (`_build_unified_song_plan` 이 이 필드를 우선순위대로 소비한다).
        #
        # 카드 t393 — 이름·무드가 비어 있어 `_section_role` 이 이 구간들을 전부
        # "other" 로 판독했고, 그 결과 `_ARC_PALETTE`/`_ARC_FX`/`_ARC_TEXTURE`
        # 세 표가 동시에 우회되어 17개 구간이 팔레트 1종·이펙트 1종·텍스처
        # 1종으로 뭉개졌다(실측). `_infer_confirmed_role` 로 D 레벨에서 역할을
        # 추정해 `role` 필드에 싣는다 — 지시문이 직접 적은 구간(`section_names`)
        # 은 이 블록을 타지 않으므로 그 경로의 정본은 그대로다.
        if not sections:
            confirmed = self._song_analysis
            accepted = confirmed.accepted if confirmed is not None else ()
            confirmed_d_levels = [section.d_level for section in accepted]
            confirmed_roles = [
                _infer_confirmed_role(position, confirmed_d_levels)
                for position in range(len(accepted))
            ]
            # 카드 t391 — 중립 ASCII S<n> 은 곡 하나에 라벨이 중복될 수 있고
            # (마디 분할이 부모 이름을 물려받는다) 콘솔의 큐 목록과 다른
            # 어휘였다. 역할+회차로 바꿔도 dynamics 는 아래 `d_level=` 로 여전히
            # 명시 전달되므로 룩 선택(`_map_section_to_look`)은 이름을 보지
            # 않는다 — 이름은 오직 표시용이다.
            confirmed_names = _confirmed_section_names(confirmed_roles)
            for _position, (section, role, name) in enumerate(
                zip(accepted, confirmed_roles, confirmed_names, strict=True), start=1
            ):
                sections.append(
                    PositionSheetSection(
                        name=name,
                        start_ms=section.start_ms,
                        mood="",
                        d_level=section.d_level,
                        role=role,
                    )
                )
        if not sections:
            return self._pointing_refusal(
                "곡 구간을 읽지 못해 연출 인터뷰를 시작하지 않았습니다. 형식: "
                "'디자인 큐 시트, 시퀀스 110, 프리셋 21번부터: 인트로 0:00 잔잔하게, "
                "후렴 0:40 클럽 드롭'"
            )
        # 카드 t311 — 좌표가 없어도 디자인은 계속한다. 좌표가 못 주는 것은
        # 포지션(무브) 축 하나뿐이고, 조도와 컬러는 좌표를 보지 않는다. 예전에는
        # 여기서 통째로 멈춰서 패치 없는 리그에는 큐 시트가 아예 안 나왔다
        # (2026-09-07 브라우저 실측). 대신 축 하나를 **비활성**으로 표시하고
        # 사유를 이름 대어 말한다 — 없는 좌표를 지어내는 일은 여전히 없다.
        fixtures, coord_gap = self._try_pointing_coordinates("song-design-read")
        if not coord_gap and not fixtures:
            coord_gap = "empty"
        position_gap = _COORD_GAP_NOTICES[coord_gap] if coord_gap else ""
        self._design_coord_notice = position_gap
        # 2026-08-16 사용자 방향: propose numbers the console VERIFIED instead
        # of static examples — an empty sequence slot for the store target,
        # and a preset range that actually holds all 10 basic positions.
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        requested_sequence = int(sequence_match.group("no")) if sequence_match is not None else None
        picked = self._song_pick_sequence(
            requested_sequence,
            purpose="디자인 큐 시트",
            refusal="시퀀스 번호를 받지 못해 연출 인터뷰를 시작하지 않았습니다.",
        )
        if isinstance(picked, InstructionResult):
            return picked
        sequence_no = picked
        preset_match = _SHEET_PRESET_START.search(text)
        if preset_match is not None:
            preset_start = int(preset_match.group("no"))
        else:
            asked = self._ask_position_preset_start(
                "프리셋 시작 번호를 받지 못해 연출 인터뷰를 시작하지 않았습니다."
            )
            if isinstance(asked, InstructionResult):
                return asked
            preset_start = asked
        timing = self._song_timing_choice(text)
        if timing is None:
            return InstructionResult(
                status="ok",
                text=(
                    "타이밍 모드가 확정되지 않아 큐를 쓰지 않았습니다. "
                    "수동 Go, 큐 타임(자동 진행), 타임코드 중 하나를 선택해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        bpm_match = _SONG_BPM.search(text)
        genre_match = _SONG_GENRE.search(text)
        # 카드 t381 — t302 는 구간을 확정 기록으로 잇지만 BPM 은 잇지 않았다.
        # `_split_sections_for_density`(t305, 마디 경계 분할)는 `profile.bpm`
        # 이 `None` 이면 분할을 한 건도 하지 않는다(`cue_density.py` 의 명시된
        # 규약) — 그래서 곡을 분석·확정해 놓고도 지시문에 BPM 을 다시 안 적으면
        # 마디 분할이 조용히 꺼졌다. 지시문이 명시하면 그 값이 최우선이고(오늘과
        # 동일), 없을 때만 확정 BPM 이 기본값이 된다 — 구간 기본값과 같은 규칙
        # (prepare_songcue 의 REQ-SONGCONFIRM-009).
        if bpm_match is not None:
            bpm = float(bpm_match.group("bpm"))
        elif self._song_bpm is not None and self._song_bpm.bpm is not None:
            bpm = self._song_bpm.bpm
        else:
            bpm = None
        profile = MusicProfile(
            bpm=bpm,
            genre=genre_match.group("genre") if genre_match is not None else None,
        )
        # 카드 t399 — 이 시점의 `rig` 는 아직 그룹을 모른다(레이어 매핑은
        # `_confirm_song_layer_mapping()` 이 감독 확인을 받은 뒤에야 나온다,
        # 아래). 좌표는 위에서 이미 읽은 값이고, **패치(장비 능력)는 카드
        # t344 가 배선했다** — 예전 `patch=[]` 리터럴은 「못 읽었다」와
        # 「장비가 없다」를 구별 불가능하게 만들었다. `DirectorInterview` 는
        # `rig.inventory`/`rig.geometry` 만 읽고 `rig.layers` 는 안 읽으므로
        # (Q4 공간 서사는 좌표·기종만 본다) 레이어 미확정 상태로 여기서
        # 지어도 인터뷰 질의에는 영향이 없다 — 계획에 실릴 최종 리그는
        # 매핑 확정 뒤 다시 짓는다.
        coords = [
            {"fid": fid, "x": position[0], "y": position[1], "z": position[2]}
            for fid, position in fixtures
        ]
        rig_read = self._try_rig_capabilities()
        rig = build_rig_profile(patch=list(rig_read.patch), groups={}, coords=coords)
        # 기종 단위 판정. 팬/틸트가 없는 기종은 계획 단계에서 **이름 대어** 거절되고,
        # 리그에 움직이는 장비가 하나도 없으면 Q4(공간 스토리)를 아예 묻지 않는다 —
        # 카드 t311 이 좌표 결손에 쓴 것과 **같은** 기제(`skipped_steps`)다.
        position_gate = position_verdict(rig_read.capabilities) if rig_read.capabilities else None
        capability_notices: list[str] = []
        rig_notice = rig_capability_notice(rig_read)
        if rig_notice:
            capability_notices.append(rig_notice)
        if position_gate is not None:
            refusal = position_gate.reason()
            if refusal:
                capability_notices.append(refusal)
            if not position_gate.any_positionable and not position_gap:
                position_gap = _NO_POSITIONABLE_NOTICE
        if capability_notices:
            self._design_coord_notice = " / ".join(
                part for part in (position_gap, *capability_notices) if part
            )
        else:
            self._design_coord_notice = position_gap
        pre_specified: dict[str, str] = {}
        concept_match = _SONG_CONCEPT_HINT.search(text)
        if concept_match is not None:
            pre_specified[Q1_CONCEPT] = concept_match.group("concept").strip()
        palette_match = _SONG_PALETTE_HINT.search(text)
        if palette_match is not None:
            pre_specified[Q2_PALETTE] = palette_match.group("palette").strip()
        self._pending_song_requery = None  # a fresh design supersedes a stale one
        self._pending_song_plan = None
        interview = DirectorInterview(
            profile,
            rig,
            pre_specified=pre_specified,
            # 카드 t311 — Q4 는 포지션 진행 서사를 묻는다. 좌표가 없으면 그
            # 답이 닿을 축이 없어 묻지 않는다(기본값으로 대신 답하지도 않는다).
            # 카드 t344 — 팬/틸트를 가진 장비가 아예 없을 때도 같은 이유로 묻지
            # 않는다. 두 사실은 다르지만 「답이 닿을 축이 없다」는 결론이 같아
            # **같은 기제**를 쓴다(두 번째 기제를 만들지 않는다).
            skipped_steps=(Q4_SPATIAL_STORY,) if position_gap else (),
        )
        failure = self._song_run_interview(interview)
        if failure is not None:
            return failure
        records = interview.audit_trail()
        # 카드 t441 — 이 인터뷰가 완료됐다(위 실패 없이 통과). 세션 필드에
        # 실어 경로 B(`prepare_songcue`)도 같은 팔레트·색 운용 답을 쓸 수
        # 있게 한다(`_SongInterviewRecordsView` 독스트링).
        self._song_interview_records = records
        # 결함 5: Q1 concept colors vs Q2 palette — surface the conflict as a
        # director card instead of silently repeating the Q2 palette.
        plan_warnings: list[str] = []
        if position_gap:
            plan_warnings.append(position_gap)
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
                "베이스 컬러 결정 — 색을 두 계열로 말씀하셨습니다.\n"
                f"컨셉 색: {' / '.join(concept_colors)}\n"
                f"팔레트: {' / '.join(_palette_colors(palette_value))}\n"
                "베이스 컬러를 어느 쪽으로 잡을까요?",
                options=(
                    QuestionOption(label="팔레트 베이스"),
                    QuestionOption(label="컨셉 색 베이스"),
                    QuestionOption(label="구간 분리 (잔잔한 구간 팔레트, 후렴 컨셉 색)"),
                ),
                why="결정 전에는 전역 팔레트를 조용히 덮어쓰지 않습니다.",
            )
            if conflict_answer and (
                "분리" in conflict_answer or "분배" in conflict_answer or "혼합" in conflict_answer
            ):
                palette_mode = "mixed"
            elif conflict_answer and "컨셉" in conflict_answer:
                palette_mode = "concept"
            elif conflict_answer is None:
                plan_warnings.append(
                    "베이스 컬러 미결정 — 감독 결정 전까지 Q2 팔레트를 유지합니다."
                )
        # 결함 6: role → group-number layer mapping, read from console group
        # names and confirmed once per session; single-layer stays disclosed.
        layer_mapping = self._confirm_song_layer_mapping()
        if not layer_mapping:
            plan_warnings.append(_SINGLE_LAYER_WARNING)
        else:
            # 카드 t399 — 매핑이 확정됐는데도 계획에 실리는 `rig` 는 위에서
            # `groups={}` 로 지어져 RG1 이 여전히 단일 레이어로 읽는다(순서
            # 문제: `rig` 를 짓는 시점이 `_confirm_song_layer_mapping()` 보다
            # 앞선다). 그룹 **멤버십**(어느 fid 가 그 그룹인지)은 이 통로로
            # 읽을 수 없어(`_confirm_song_layer_mapping` 독스트링) `groups`
            # 인자(역할 -> fid 목록)를 못 채운다 — 대신 `declared_layers` 에
            # 역할 -> **그룹 번호**를 싣는다. `RigLayers.mapping` 은 원래
            # fid 튜플을 기대하지만, RG1 게이트(`has_layer`/
            # `layer_rules_active`)는 그 튜플이 비었는지만 보고(`fids_for`
            # 는 프로덕션 어디서도 안 읽는다, grep 확인) 실제 fid 값을 쓰지
            # 않으므로 그룹 번호를 자리표시자로 넣어도 안전하다.
            declared_layers = {
                str(entry["role"]): (int(entry["group_no"]),)
                for entry in layer_mapping
                if entry.get("role") and isinstance(entry.get("group_no"), int)
            }
            if declared_layers:
                rig = build_rig_profile(
                    patch=list(rig_read.patch),
                    groups={},
                    coords=coords,
                    declared_layers=declared_layers,
                )
        # 카드 t305 — 긴 구간을 마디 경계에서 쪼갠다. 구간 하나에 큐 하나면
        # 32마디 후렴이 정적인 큐 한 장으로 끝난다. BPM 이 선언되지 않았으면
        # 이 호출은 입력을 그대로 돌려준다(오늘과 동일).
        sections, section_origin, density_notes = _split_sections_for_density(
            sections,
            profile=interview.working_profile,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            color_usage=_record_value(records, Q2B_COLOR_USAGE, "modulate"),
        )
        plan_warnings.extend(density_notes)
        # 카드 t430 — W 채널 확인 기구를 한 번 계산해 상태에 싣는다. 열거
        # 실패·빈 결과는 빈 집합으로 남는다(오늘과 동일, 무대 색 변화 0).
        w_fids: frozenset[int] = frozenset()
        color_pairs_enumerated = self._color_rig_fixture_pairs()
        if color_pairs_enumerated is not None:
            color_pairs, _fid_unread = color_pairs_enumerated
            if color_pairs:
                w_capable, _rgb_only, _undetermined = self._w_capable_fids(
                    color_pairs, probe_id_prefix="song-w-channel"
                )
                w_fids = frozenset(w_capable)
        state = _SongDesignState(
            sections=list(sections),
            section_origin=section_origin,
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
            position_disabled_reason=position_gap,
            w_fids=w_fids,
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
                    token = restart_match.group("no").lower()
                    interview.restart_from(_SONG_RESTART_STEP_BY_TOKEN[token])
                    break
                if raw_answer and _SONG_RESTART_COLOR_USAGE.search(raw_answer):
                    interview.restart_from(Q2B_COLOR_USAGE)
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
            section_origin=state.section_origin or None,
            position_disabled_reason=state.position_disabled_reason,
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
            color_usage=_record_value(state.records, Q2B_COLOR_USAGE, "modulate"),
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
            # 2026-08-16 user finding: after a server restart / browser
            # reconnect the in-memory pending plan is GONE, and an unmistakable
            # plan-structure edit ("큐 2와 3 사이에 브레이크 추가") fell through
            # to the model — which answered with a fabricated "서버 내부 오류"
            # apology. An unambiguous structure edit with no pending plan gets
            # an honest refusal instead; softer edits still fall through.
            if (
                _PLAN_EDIT_DELETE.search(text) is not None
                or _PLAN_EDIT_INSERT_BETWEEN.search(text) is not None
                or _PLAN_EDIT_INSERT_ADJACENT.search(text) is not None
            ):
                return self._pointing_refusal(
                    "수정할 보류 중 계획(승인 전 타임라인)이 없습니다 — 서버 재시작이나 "
                    "화면 새로고침으로 세션의 계획이 사라졌을 수 있습니다. 곡 설계를 "
                    "다시 실행해 계획을 만든 뒤 편집해 주세요. 이미 콘솔에 저장된 "
                    "타임라인의 포지션은 '타임라인 큐 N을 …으로' 형태로 수정할 수 있습니다."
                )
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
        sequence_move = _PLAN_EDIT_SEQUENCE.search(text)
        delete = _PLAN_EDIT_DELETE.search(text)
        between = _PLAN_EDIT_INSERT_BETWEEN.search(text)
        adjacent = _PLAN_EDIT_INSERT_ADJACENT.search(text)
        count = len(state.sections)
        if sequence_move is not None:
            new_sequence = int(sequence_move.group("no"))
            if new_sequence <= 0:
                return self._pointing_refusal("시퀀스 번호는 1 이상이어야 합니다.")
            previous = state.sequence_no
            state.sequence_no = new_sequence
            note = f"저장 대상 시퀀스 {previous} → {new_sequence}"
        elif delete is not None:
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
        return self._merge_timeline_cue_position(timeline, sections, slot, cue_no, target)

    def _rehearsal_cue_edit(self, text: str) -> InstructionResult | None:
        """리허설 편집 (priority 5): "지금 이 큐를 무대 중앙으로" — no cue
        number; the target cue is read off the console's live playback via
        the SEQUENCE handle's ``CurrentCue`` property (the T-H3 live-verified
        path cue_monitor uses — never the executor handle, never ``CueNo``).
        Because the cue may be ON STAGE right now, the merge NEVER runs
        without a fresh explicit approval card (라이브 중 승인 필수)."""
        if _REHEARSAL_EDIT_REQUEST.search(text) is None:
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
        sequence_no = timeline.get("sequence_number")
        if not isinstance(sequence_no, int):
            return self._pointing_refusal(
                "타임라인의 시퀀스 번호를 확인할 수 없어 수정하지 않았습니다."
            )
        if not timeline.get("console_stored"):
            return self._pointing_refusal(
                "리허설 편집은 콘솔에 저장된 타임라인만 대상입니다. 승인 전 계획은 "
                "'큐 N …' 형태로 수정해 주세요."
            )
        sequence_path = f"{self._rig_paths['sequences']}/{sequence_no}"
        read = read_properties(self._current_cue_port, sequence_path, ("CurrentCue",))["CurrentCue"]
        if not read.ok:
            return self._pointing_refusal(
                f"현재 큐를 읽지 못했습니다({read.error}). 큐 번호를 지정해 "
                "'타임라인 큐 N …'으로 수정해 주세요."
            )
        cue_no = parse_current_cue_index(str(read.value or ""))
        if cue_no is None:
            return self._pointing_refusal(
                f"시퀀스 {sequence_no}의 CurrentCue 값({read.value!r})에서 재생 중인 "
                "큐를 확인할 수 없습니다 — 시퀀스가 재생 중인지 확인해 주세요."
            )
        sections = timeline.get("sections")
        sections = sections if isinstance(sections, list) else []
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
                f"지금 나가는 큐 {cue_no}가 화면 타임라인에 없습니다. (보유 큐: {known or '없음'})"
            )
        label = str(sections[slot].get("label") or f"Cue {cue_no}")
        approval = self._ask_one(
            f"지금 나가는 큐 {cue_no}({label})의 포지션을 {target}(으)로 수정합니다.\n"
            "라이브 출력 중인 큐라 병합 즉시 무대에 반영됩니다. 진행할까요?",
            options=(
                QuestionOption(label="승인"),
                QuestionOption(label="취소"),
            ),
            why="리허설 편집은 라이브 출력을 바꿉니다 — 승인 없이는 실행하지 않습니다.",
        )
        if not _is_explicit_song_approval(approval):
            return InstructionResult(
                status="ok",
                text=(
                    f"지금 나가는 큐 {cue_no}({label}) 수정 계획을 보여드렸고, "
                    "승인 전이므로 콘솔에 쓰지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        result = self._merge_timeline_cue_position(
            timeline, sections, slot, cue_no, target, live=True
        )
        return result

    def _merge_timeline_cue_position(
        self,
        timeline: dict,
        sections: list,
        slot: int,
        cue_no: int,
        target: str,
        *,
        live: bool = False,
    ) -> InstructionResult:
        """The shared /Merge tail of the timeline + rehearsal cue edits:
        preset-start resolution, coordinate read, position-preset recall into
        ``Store Sequence S Cue N /Merge``, then the projection/replay update."""
        sequence_no = timeline["sequence_number"]
        preset_start = timeline.get("preset_start")
        if not isinstance(preset_start, int):
            asked = self._ask_position_preset_start(
                "프리셋 시작 번호를 받지 못해 큐를 수정하지 않았습니다."
            )
            if isinstance(asked, InstructionResult):
                return asked
            preset_start = asked
        fixtures = self._read_pointing_coordinates("timeline-edit-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal("좌표가 확인된 장비가 없어 큐를 수정하지 않았습니다.")
        fids = [fid for fid, _position in fixtures]
        try:
            resolved = self._resolve_position_preset_labels(
                (target,), start=preset_start, span=len(BASIC_POSITION_SEQUENCE)
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"큐를 수정할 수 없습니다: {error}")
        preset_no = resolved[target]
        commands = (
            "ChangeDestination Root",
            "ClearAll",
            preset_recall_command(fids, preset_no),
            f"Store Sequence {sequence_no} Cue {cue_no} /Merge",
            "ClearAll",
        )
        executed = self._dispatch_declared(
            ToolCall(
                id="rehearsal-cue-edit" if live else "timeline-cue-edit",
                name="run_commands",
                arguments={"commands": list(commands)},
            ),
            risk=showfile_write_risk(commands, kind="timeline_cue_merge"),
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
        live_note = " (리허설 — 재생 중 큐)" if live else ""
        updated["readback"] = {
            "verified": (timeline.get("readback") or {}).get("verified"),
            "message": (
                f"큐 {cue_no} 포지션을 {target}(으)로 수정 (Preset 2.{preset_no} 병합){live_note}"
            ),
        }
        store = self._timeline_store
        if store is not None:
            store.latest = updated
        self._send(song_timeline_event(timeline=updated))
        prefix = "지금 나가는 큐" if live else "감독 타임라인 큐"
        return InstructionResult(
            status="ok",
            text=(
                f"{prefix} {cue_no}의 포지션을 {target}(으)로 수정했습니다 — "
                f"Sequence {sequence_no} Cue {cue_no}에 Preset 2.{preset_no}을 병합하고 "
                "타임라인에 즉시 반영했습니다."
            ),
            command_outcomes=tuple(executed.command_outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    # -- t281 큐시트 초안 편집 (콘솔 무접촉) ---------------------------------

    @staticmethod
    def _draft_badge(timeline: dict, *, depth: int, report: Sequence[str]) -> dict:
        """화면이 「수정됨 · 미저장」을 그릴 수 있게 하는 표식을 얹은 사본.

        타임라인 사전에 얹는 **부가 필드 하나**다 — 구간 값은 건드리지 않으므로
        이 표식이 없던 기존 페이로드도 그대로 파싱된다(선택 필드).
        """
        stamped = dict(timeline)
        stamped["draft"] = {
            "dirty": depth > 0,
            "depth": depth,
            "last_change": list(report),
        }
        return stamped

    def _cue_sheet_draft_edit(self, text: str) -> InstructionResult | None:
        """선택된 큐의 큐시트 칸을 **초안에서** 고친다 — 콘솔 명령 0건.

        이 경로는 명령 문자열을 만들지 않고 ``self._registry.dispatch`` 를 부르지
        않는다. 하는 일은 (a) 요청 문장 읽기, (b) 순수 함수로 새 타임라인 만들기,
        (c) 직전 상태를 되돌리기 스택에 쌓기, (d) 화면 갱신 — 넷뿐이다.

        어느 큐인지는 문장의 「큐 N」이 먼저이고, 없으면 화면에서 감독이 고른
        큐(``self._selected_cue``)를 쓴다. 둘 다 없으면 **지어내지 않고** 거절한다.
        """
        # t290 — 화면에서 큐를 이미 고른 상태면 지시어 없는 짧은 명령도 받는다.
        # 판별기는 `cue_sheet_edit._is_anchorless_cue_command` 하나뿐이고, 곡
        # 브리핑 회귀(32건)는 그 판별기의 어휘 축이 계속 막는다.
        request = parse_cue_sheet_edit_request(text, cue_selected=self._selected_cue is not None)
        if request is None:
            return None  # 이 모듈의 어휘가 아니다 — 기존 사슬로 그대로 흘려보낸다
        store = self._timeline_store
        timeline = store.latest if store is not None else None
        if timeline is None:
            return self._pointing_refusal(
                "수정할 큐시트가 아직 없습니다. 곡 설계를 완료하거나 라이브러리에서 "
                "타임라인을 불러온 뒤 다시 요청해 주세요. 콘솔에는 아무것도 쓰지 않았습니다."
            )
        cue = request["cue"] or self._selected_cue
        if cue is None:
            return self._pointing_refusal(
                "어느 큐를 고칠지 알 수 없습니다 — 큐시트에서 큐를 먼저 선택하거나 "
                "'큐 3 …' 처럼 번호를 적어 주세요. 콘솔에는 아무것도 쓰지 않았습니다."
            )
        try:
            updated, report = apply_cue_sheet_edit(timeline, cue, request["changes"])
        except CueSheetEditError as error:
            # 사유는 한 가지 원인만 지목한다 — 거짓 사유가 참 사유를 가리지
            # 않게(t112 결함 계열). 시험이 이 문자열을 그대로 단언한다.
            return self._pointing_refusal(
                f"큐시트 초안을 수정하지 않았습니다 — {error} 콘솔에는 아무것도 쓰지 않았습니다."
            )
        self._remember_draft_baseline(timeline)
        self._draft_history.record(timeline)
        updated = self._draft_badge(updated, depth=self._draft_history.depth, report=report)
        store.latest = updated
        self._send(song_timeline_event(timeline=updated))
        return self._pointing_refusal(
            f"큐 {cue} 초안 수정 (콘솔 무접촉): {' · '.join(report)}. "
            "이 수정은 아직 초안입니다 — 「저장」을 눌러야 라이브러리에 남고, "
            "콘솔 반영은 별도의 승인 경로입니다."
        )

    # -- t291 초안 → 콘솔 반영 (기존 승인 게이트 그대로) --------------------------

    def _remember_draft_baseline(self, timeline: dict) -> None:
        """첫 편집 직전 상태를 기준본으로 잡는다. 곡이 바뀌면 기준도 바뀐다.

        곡을 새로 설계하거나 라이브러리에서 다른 판을 불러오면 예전 기준본은
        **다른 곡**의 것이다 — 그대로 두면 「달라진 큐」가 곡 전체로 부풀어
        건드리지도 않은 큐가 콘솔로 나간다. 그래서 곡 이름·시퀀스 번호가
        어긋나면 기준을 지금 것으로 새로 잡는다.
        """
        current = self._draft_baseline
        same_song = (
            current is not None
            and current.get("song_title") == timeline.get("song_title")
            and current.get("sequence_number") == timeline.get("sequence_number")
        )
        if not same_song:
            self._draft_baseline = copy.deepcopy(timeline)

    def _read_console_groups(self, call_id: str) -> tuple[object, str | None]:
        """``DataPool/Groups`` 읽기 한 번. ``(payload, 못 읽은 사유)``.

        **두 실패를 가른다**(t303): 콘솔이 답을 주지 않은 것과, 답은 줬는데
        그 답이 이름을 담지 않은 것. 주소록(:meth:`_console_group_address_book`)
        은 둘 다 「빈 주소록」으로 접어도 되지만, 사전 점검은 접으면 안 된다 —
        「닿지 못했다」를 「하나도 안 맞았다」로 보고하면 감독이 데스크를 켜는
        대신 그룹 이름을 고치러 간다.

        읽기는 이 한 자리뿐이다 — 두 번째 리더를 만들지 않는다.
        """
        execution = self._registry.dispatch(
            ToolCall(
                id=call_id,
                name="query_state",
                arguments={"path": "DataPool/Groups"},
            )
        )
        if execution.result.is_error:
            detail = (execution.result.content or "").strip()
            # 응답기는 사유를 `{"error": "…"}` 로 싼다. 감독에게는 그 속의 문장만
            # 보인다 — 감싼 JSON 을 그대로 띄우면 사유가 잡음에 묻힌다.
            try:
                unwrapped = json.loads(detail)
            except (TypeError, ValueError):
                unwrapped = None
            if isinstance(unwrapped, Mapping) and unwrapped.get("error"):
                detail = str(unwrapped["error"]).strip()
            return None, detail or "콘솔이 응답하지 않았습니다"
        try:
            return json.loads(execution.result.content), None
        except (TypeError, ValueError):
            return None, "콘솔 응답을 읽지 못했습니다(JSON 아님)"

    def _console_group_address_book(self, names: Sequence[str]) -> list[dict[str, object]]:
        """콘솔이 답한 그룹 이름으로 주소록을 만든다 — 없으면 빈 목록.

        읽기 한 번(``DataPool/Groups``)이고, 그 읽기도 다른 모든 조회와 같이
        게이트가 감사한다. 이름이 안 맞으면 그 이름은 그냥 안 들어간다.
        """
        if not names:
            return []
        payload, error = self._read_console_groups("draft-apply-group-address")
        if error is not None:
            return []
        return layer_mapping_from_console_groups(payload, names)

    # -- t303 리그 사전 점검 (읽기 전용) -----------------------------------------

    def _rig_preflight(self, text: str) -> InstructionResult | None:
        """쇼 전에 「이 곡의 어느 큐가 실제로 데스크에 닿는가」를 답한다.

        **읽기 전용이다.** 이 경로는 콘솔 쓰기 명령을 한 줄도 만들지 않고
        디스패치하지도 않는다 — ``run_commands`` 를 부르지 않는다. 나가는
        것은 주소록이 이미 쓰던 조회(``DataPool/Groups``) 한 번뿐이고, 그
        읽기도 다른 모든 조회와 같이 게이트가 감사한다.

        판정 규칙은 반영과 **같은 함수**를 쓴다 — 주소록은
        `layer_mapping_from_console_groups`, 큐별 판정은 반영의
        `plan_cue_console_apply` 를 그대로 부른다(t304). 점검은 통과했는데
        반영이 건너뛰는 어긋남을 만들지 않기 위해서다.

        읽기는 최대 셋이다: 주소록 하나(t303), 그리고 **번호가 선언돼 있을 때만**
        시퀀스 슬롯·타임코드 슬롯 하나씩(t304). 번호가 없으면 그 읽기는 아예
        나가지 않고 보고에 「재지 않았다」로 남는다.
        """
        if not _is_rig_preflight_request(text):
            return None
        store = self._timeline_store
        timeline = store.latest if store is not None else None
        if not isinstance(timeline, dict):
            return self._pointing_refusal(
                "점검할 큐시트가 없습니다. 곡 설계를 완료하거나 라이브러리에서 "
                "타임라인을 불러온 뒤 다시 요청해 주세요. 콘솔에는 아무것도 쓰지 않았습니다."
            )
        payload, error = self._read_console_groups("rig-preflight-groups")
        sequence_slot = timecode_slot = ""
        if error is None:
            # 슬롯은 **선언된 번호에만** 묻는다. 번호가 없으면 읽지 않는다 —
            # 어느 슬롯을 볼지 짐작하는 순간 그 답은 다른 곡의 답이 된다.
            sequence_no = _declared_slot_number(timeline.get("sequence_number"))
            if sequence_no is not None:
                sequence_slot = self._console_slot_state(
                    f"{self._rig_paths['sequences']}/{sequence_no}",
                    probe_id=f"rig-preflight-sequence-{sequence_no}",
                )
            timecode_no = _declared_slot_number(timeline.get("timecode_number"))
            if timecode_no is not None:
                pool = self._rig_paths.get("timecodes", TIMECODE_POOL_PATH)
                timecode_slot = self._console_slot_state(
                    f"{pool}/{timecode_no}",
                    probe_id=f"rig-preflight-timecode-{timecode_no}",
                )
        report = plan_rig_preflight(
            timeline,
            console_payload=payload,
            console_error=error,
            sequence_slot=sequence_slot,
            timecode_slot=timecode_slot,
        )
        return self._pointing_refusal(render_rig_preflight(report))

    def _draft_apply_target(self, timeline: dict, text: str) -> tuple[dict, str]:
        """반영에 쓸 타임라인 사본 + 주소록에 대해 감독에게 말할 한 줄.

        시드로 실린 곡(정본 문서를 옮긴 판)은 두 칸이 비어 있어서 오늘은 한 큐도
        나가지 못한다 — 콘솔 시퀀스 번호가 없고, 역할↔그룹 주소록이 없다. 둘 다
        **선언된 출처**에서만 채운다:

        * 시퀀스 번호 — 감독이 이번 지시문에 적은 「시퀀스 N」. 안 적었으면 안
          채운다(엉뚱한 시퀀스를 덮는 것이 이 앱에서 되돌릴 수 없는 사고다).
        * 주소록 — 콘솔이 스스로 보고한 그룹 이름과의 완전 일치. 짐작 없음.

        타임라인 원본은 건드리지 않는다. 구간(sections)도 손대지 않으므로
        「달라진 큐」 판정은 그대로다.
        """
        target = timeline
        notes: list[str] = []

        sequence_number = timeline.get("sequence_number")
        if not isinstance(sequence_number, int) or sequence_number < 1:
            declared = _CUE_SEQUENCE_NO.search(text)
            if declared is not None:
                target = dict(target)
                target["sequence_number"] = int(declared.group("no"))
                notes.append(
                    f"\n· 시퀀스 번호는 이번 지시문이 적은 {target['sequence_number']}번을 "
                    "썼습니다 (타임라인에는 번호가 없었습니다)."
                )

        mapping = target.get("layer_mapping")
        mapping = mapping if isinstance(mapping, list) else []
        if not mapping:
            names = timeline_group_names(target)
            resolved = self._console_group_address_book(names)
            if resolved:
                target = dict(target)
                target["layer_mapping"] = resolved
                found = ", ".join(
                    f"{entry['group_name']}=Group {entry['group_no']}" for entry in resolved
                )
                notes.append(f"\n· 콘솔이 보고한 그룹 이름으로 주소를 잡았습니다: {found}.")
            missing = [
                name
                for name in names
                if name.casefold() not in {str(e["group_name"]).casefold() for e in resolved}
            ]
            if missing:
                notes.append(
                    "\n· 콘솔에 같은 이름의 그룹이 없어 주소를 못 잡은 대상: "
                    + ", ".join(missing)
                    + " (이름을 지어내지 않습니다)."
                )
        return target, "".join(notes)

    def _cue_sheet_draft_apply(self, text: str) -> InstructionResult | None:
        """초안에서 바뀐 큐를 콘솔에 반영한다 — **기존 승인 경로 그대로**.

        새 경로를 만들지 않는다: 명령은 `server.design.cue_sheet_apply` 가
        순수하게 세우고, 발사는 다른 모든 콘솔 쓰기와 같은
        ``run_commands`` 디스패치다. 미리보기 카드·LiveLock·감사 로그가 전부
        그 경로에 이미 붙어 있으므로 여기에는 우회 플래그가 없다.

        **승인은 게이트가 준다** — 묻는 주체는 하나다(t299 Phase 2).
        t292 당시에는 게이트가 `Store Sequence … /Merge` 를 `safe` 로 분류해서
        승인 단계가 열리지 않았고(실측 세 번 모두 `executed N, blocked 0,
        approved 0`), 그래서 이 자리가 자기 채널로 수락을 따로 받았다.
        `blacklist.yaml` v6 이 그 오브젝트를 폐집합에 넣은 뒤로는 그 임시
        채널이 **두 번째 질문자**가 됐다 — 감독이 같은 명령을 두 번 승인했다.
        지금은 선언(`BatchRisk`)만 실어 보내고 카드는 게이트가 한 장 만든다.
        승인 못 받으면 명령은 0건 나간다.

        「저장」과는 다른 행위다 — 저장은 라이브러리에만 남기고 콘솔에는 한
        건도 보내지 않는다(`server/web/timeline_api.py`).
        """
        if not _is_draft_apply_request(text):
            return None
        store = self._timeline_store
        timeline = store.latest if store is not None else None
        if not isinstance(timeline, dict):
            return self._pointing_refusal(
                "반영할 큐시트 초안이 없습니다. 곡 설계를 완료하거나 라이브러리에서 "
                "타임라인을 불러온 뒤 다시 요청해 주세요. 콘솔에는 아무것도 쓰지 않았습니다."
            )
        baseline = self._draft_baseline
        if baseline is None:
            return self._pointing_refusal(
                "초안에서 달라진 큐가 없습니다. 먼저 큐시트를 수정한 뒤 반영해 주세요. "
                "콘솔에는 아무것도 쓰지 않았습니다."
            )
        target, address_note = self._draft_apply_target(timeline, text)
        try:
            plan = plan_console_apply(baseline, target)
        except ConsoleApplyError as error:
            return self._pointing_refusal(f"{error} 콘솔에는 아무것도 쓰지 않았습니다.")
        skipped_note = address_note + "".join(
            f"\n· 큐 {skip.cue_number}({skip.label}) 미반영 [{skip.reason}] — {skip.detail}"
            for skip in plan.skipped
        )
        if plan.is_empty:
            # 「전부 반영했습니다」를 절대 말하지 않는다 — 0건이 나갔다.
            return self._pointing_refusal(
                f"콘솔에 반영한 큐가 0건입니다 (건너뜀 {len(plan.skipped)}건)."
                f"{skipped_note}\n콘솔에는 아무것도 쓰지 않았습니다."
            )
        # 카드 t299 Phase 2 — 선언을 실어 보내고 **게이트가 유일한 질문자**가
        # 되게 한다. 사유는 손으로 적지 않고 **나갈 명령에서** 서버가 읽는다
        # (t323 규율, 열 자리 봉합과 같은 `showfile_write_risk`). 선언이 붙으면
        # 게이트가 분류 결과를 흡수해 번들 전체를 요청 **하나**로 만들고
        # (`gate.py` `approval_findings`), `kind` 를 감사 로그에 싣는다.
        risk = showfile_write_risk(list(plan.commands), kind="draft_apply")
        if risk is None:
            # 여기 오는 번들은 `Store Sequence … ` 를 반드시 싣는다(위에서
            # `plan.is_empty` 를 걸렀다). 그래도 선언이 안 읽히면 승인 없이
            # 쇼파일을 고치게 되므로 실행하지 않는다 — fail-closed.
            return self._pointing_refusal(
                f"Sequence {plan.sequence_number} 반영의 쇼파일 쓰기 선언을 "
                "읽지 못해 중단했습니다. 초안은 그대로 남아 있습니다."
                f"{skipped_note}\n콘솔에는 아무것도 쓰지 않았습니다."
            )
        executed = self._registry.dispatch(
            ToolCall(
                id="cue-sheet-draft-apply",
                name="run_commands",
                arguments={"commands": list(plan.commands)},
            ),
            ExecutionContext(risk=risk),
        )
        # 승인 거절은 「완료되지 않았다」와 다른 사건이다 — 감독이 카드를 거절한
        # 것이므로 그 문면으로 답한다. `rejected` 는 게이트에서 승인 거절
        # 경로에만 붙는다(다른 실패는 `blocked*` · `locked`).
        if any(outcome.status == "rejected" for outcome in executed.command_outcomes):
            return self._pointing_refusal(
                f"Sequence {plan.sequence_number} 반영을 승인받지 못해 "
                f"중단했습니다 (요청 {len(plan.applied)}건). 초안은 그대로 "
                f"남아 있습니다.{skipped_note}\n콘솔에는 아무것도 쓰지 않았습니다."
            )
        failed = [
            outcome
            for outcome in executed.command_outcomes
            if outcome.status in ("failed", "blocked", "rejected", "not_executed")
        ]
        # 「무엇이 나갔나」를 칸별로 적는다 — 조도만 나가던 때의 `큐 20→90%` 는
        # 이제 컬러·페이드가 같이 나갈 수 있어 실제와 어긋난다(t293).
        applied_note = ", ".join(
            f"큐 {cue}({plan.summaries.get(cue) or f'조도 {plan.targets.get(cue)}%'})"
            for cue in plan.applied
        )
        if executed.result.is_error or failed:
            return InstructionResult(
                status="ok",
                text=(
                    f"Sequence {plan.sequence_number} 반영이 완료되지 않았습니다 "
                    f"(요청 {len(plan.applied)}건 중 미완료 {len(failed)}건). "
                    "초안은 그대로 남아 있습니다." + skipped_note
                ),
                command_outcomes=tuple(executed.command_outcomes),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        # 반영된 값이 새 기준이다 — 같은 큐를 두 번 보내지 않게.
        self._draft_baseline = copy.deepcopy(timeline)
        return InstructionResult(
            status="ok",
            text=(
                f"Sequence {plan.sequence_number}에 초안 {len(plan.applied)}건을 "
                f"병합했습니다 ({applied_note})."
                f"{skipped_note}"
            ),
            command_outcomes=tuple(executed.command_outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _draft_step(self, *, redo: bool) -> dict:
        """되돌리기/다시하기 한 걸음. 콘솔·라이브러리 어느 쪽도 건드리지 않는다."""
        store = self._timeline_store
        current = store.latest if store is not None else None
        label = "다시하기" if redo else "되돌리기"
        if current is None:
            return chat_response_event(
                status="ok",
                summary=f"{label} 불가",
                text="되돌릴 큐시트 초안이 없습니다.",
                commands=[],
            )
        restored = self._draft_history.redo(current) if redo else self._draft_history.undo(current)
        if restored is None:
            return chat_response_event(
                status="ok",
                summary=f"{label} 불가",
                text=f"{label}할 초안 단계가 없습니다.",
                commands=[],
            )
        restored = self._draft_badge(restored, depth=self._draft_history.depth, report=())
        store.latest = restored
        self._send(song_timeline_event(timeline=restored))
        event = chat_response_event(
            status="ok",
            summary=f"초안 {label}",
            text=(
                f"큐시트 초안을 한 단계 {label}했습니다 (남은 되돌리기 "
                f"{self._draft_history.depth}단계). 콘솔과 저장본은 그대로입니다."
            ),
            commands=[],
        )
        self._send(event)
        return event

    def undo_timeline_draft(self) -> dict:
        """초안을 직전 상태로 되돌린다 (콘솔·라이브러리 무접촉)."""
        return self._draft_step(redo=False)

    def redo_timeline_draft(self) -> dict:
        """되돌리기로 물러난 초안을 다시 적용한다 (콘솔·라이브러리 무접촉)."""
        return self._draft_step(redo=True)

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
        playable: list[tuple[str, int]] = []
        for base in chosen:
            timeline = latest[base].get("timeline") or {}
            source = timeline.get("sequence_number")
            if not isinstance(source, int) or not timeline.get("console_stored"):
                skipped.append(f"{base}(콘솔 미저장 — 승인/저장 후 다시)")
                continue
            playable.append((base, source))
        if not playable:
            reasons = "; ".join(skipped) if skipped else "곡 없음"
            return self._pointing_refusal(f"셋리스트에 넣을 수 있는 곡이 없습니다: {reasons}.")

        def _rows_for(start: int) -> list[tuple[str, int, int, int]]:
            return [
                (base, source, start + _SETLIST_SEQ_STEP * index, exec_start + index)
                for index, (base, source) in enumerate(playable)
            ]

        def _occupied_slots(rows: list[tuple[str, int, int, int]]) -> list[str]:
            found: list[str] = []
            for base, source, slot, _exec_no in rows:
                if slot != source and self._console_slot_occupied(
                    f"{self._rig_paths['sequences']}/{slot}",
                    probe_id=f"setlist-slot-check-{slot}",
                ):
                    found.append(f"Sequence {slot} ({base} 슬롯)")
            return found

        # PRE-CHECK: every target slot must be empty (2026-08-15 safety rule).
        # 2026-08-16 사용자 방향: an occupied run is a QUESTION, not a dead
        # end — propose alternate verified-free base numbers on the spot.
        plan_rows = _rows_for(seq_start)
        occupied = _occupied_slots(plan_rows)
        if occupied:
            span = _SETLIST_SEQ_STEP * len(playable)
            free_bases: list[int] = []
            candidate = seq_start
            for _probe in range(8):
                candidate += span
                if not _occupied_slots(_rows_for(candidate)):
                    free_bases.append(candidate)
                if len(free_bases) == 2:
                    break
            options = tuple(QuestionOption(label=f"시퀀스 {slot}부터") for slot in free_bases) + (
                QuestionOption(label="취소"),
            )
            answer = self._ask_one(
                f"셋리스트 슬롯이 이미 사용 중입니다: {', '.join(occupied)}. "
                "기존 시퀀스는 덮어쓰지 않습니다.\n"
                + (
                    "빈 구간을 콘솔에서 확인했습니다 — 어느 번호부터 배분할까요? (직접 입력도 가능)"
                    if free_bases
                    else "빈 구간을 찾지 못했습니다 — 시작 번호를 직접 입력해 주세요."
                ),
                options=options,
                why="문제를 만나면 중단 대신 해결 방법을 함께 정합니다.",
            )
            number = re.search(r"\d+", answer or "")
            if answer is None or "취소" in (answer or "") or number is None:
                return self._pointing_refusal(
                    f"셋리스트 슬롯이 이미 사용 중입니다: {', '.join(occupied)}. "
                    "'시퀀스 N부터'로 빈 구간을 지정해 다시 요청해 주세요."
                )
            seq_start = int(number.group(0))
            plan_rows = _rows_for(seq_start)
            occupied = _occupied_slots(plan_rows)
            if occupied:
                return self._pointing_refusal(
                    f"지정한 구간도 사용 중입니다: {', '.join(occupied)}. "
                    "다른 시작 번호로 다시 요청해 주세요."
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
        executed = self._dispatch_declared(
            ToolCall(
                id="setlist-assign-bundle",
                name="run_commands",
                arguments={"commands": commands},
            ),
            risk=showfile_write_risk(commands, kind="setlist_assign"),
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
        # 진행 순서 보드 연동 (handoff item 3): the bundle RAN, so the plan's
        # slot order becomes the operator's multi-song planned order — the
        # cue monitor reads it as planned_sequence_nos. Recorded before the
        # readback loop on purpose: a readback mismatch is reported honestly
        # below, but the executed allocation order is still the show plan.
        if self._timeline_store is not None:
            self._timeline_store.setlist_sequence_nos = [slot for _b, _s, slot, _e in plan_rows]
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

    def _console_slot_state(self, path: str, *, probe_id: str) -> str:
        """One pool slot's verdict: 'empty' | 'occupied' | 'unreadable'.

        실측 2026-08-16 (사용자 질문 '왜 항상 같은 번호만 제안?'): the REAL
        console answers an EMPTY pool slot with an ERROR — ``ok:false, "path
        segment not found: …"`` — not an empty payload. That error is the
        console POSITIVELY stating absence (the same reading tools.py's
        requery path documents), so it maps to 'empty'; only a genuinely
        unknown failure (timeout, transport) stays 'unreadable'. FAIL-CLOSED
        consumers treat unreadable as occupied (#6), and the split lets
        fallback cards SAY why nothing could be proposed."""
        probe = self._registry.dispatch(
            ToolCall(id=probe_id, name="query_state", arguments={"path": path})
        )
        if probe.result.is_error:
            detail = str(probe.result.content or "").casefold()
            if "not found" in detail:
                return "empty"
            return "unreadable"
        try:
            payload = json.loads(probe.result.content)
        except (json.JSONDecodeError, TypeError):
            return "unreadable"
        if not isinstance(payload, dict):
            return "unreadable"
        return "occupied" if _setlist_node_exists(payload) else "empty"

    def _console_slot_occupied(self, path: str, *, probe_id: str) -> bool:
        """Fail-closed boolean view of `_console_slot_state`."""
        return self._console_slot_state(path, probe_id=probe_id) != "empty"

    def _song_sequence_occupied(self, sequence_no: int) -> bool:
        """True when the console already holds ANY data at this sequence slot
        — the same query_state posture the setlist pre-check uses."""
        return self._console_slot_occupied(
            f"{self._rig_paths['sequences']}/{sequence_no}",
            probe_id=f"song-design-slot-check-{sequence_no}",
        )

    def _timecode_occupied(self, timecode_no: int) -> bool:
        """Whether a Timecode pool slot already holds data (fail-closed)."""
        pool = self._rig_paths.get("timecodes", TIMECODE_POOL_PATH)
        return self._console_slot_occupied(
            f"{pool}/{timecode_no}", probe_id=f"song-design-timecode-check-{timecode_no}"
        )

    def _free_timecode_slots(self, start: int, *, count: int = 2, probes: int = 10) -> list[int]:
        """Up to ``count`` console-VERIFIED empty timecode slots from
        ``start + 1`` upward (step 1 — timecode pools are dense)."""
        free: list[int] = []
        candidate = start
        for _probe in range(probes):
            candidate += 1
            if not self._timecode_occupied(candidate):
                free.append(candidate)
                if len(free) == count:
                    break
        return free

    def _position_preset_pool_children(
        self, *, pool_no: int = POSITION_PRESET_POOL
    ) -> dict[int, str | None] | None:
        """ONE preset pool's stored slots mapped to their NAMES (or None
        when a child carried no name), or None when the pool cannot be read.

        ``pool_no``는 경로만 바꾼다(기본값 = 오늘의 Position 2, REQ-COLORPRESET-
        006) — 페이징·무진전 방어 규율은 :meth:`_paged_pool_children`에 있고
        컬러 풀(해석된 번호)도 같은 판독기를 탄다.
        """
        pool_root = self._rig_paths.get("preset_pools", "DataPool/PresetPools")
        return self._paged_pool_children(
            f"{pool_root}/{pool_no}", probe_id="song-design-preset-pool-read"
        )

    def _paged_pool_children(self, path: str, *, probe_id: str) -> dict[int, str | None] | None:
        """``path`` 컨테이너의 자식 번호→이름 완전 판독 — 페이징 공용 몸통.

        The responder caps ``children`` at 24 per reply (PROTOCOL §4.2), so
        containers past 24 children need PAGING: follow-up queries carry
        ``offset`` (the accumulated child count) and a paging-aware responder
        echoes it back. Live-measured 2026-08-16: a 31-preset pool made the
        store read-back report 10 freshly stored presets as "미확인 0/10"
        because slots 41~50 fell outside the first window — paged reads
        recover exactly that case.

        Names ride along because span-family selection needs them: the
        regeneration card offered a BASIC span for an FX regeneration request
        (live 2026-08-16) and the first option got picked — the name of a
        span's first slot is what tells the families apart.

        Truncation WITHOUT progress is still "cannot be read", not a smaller
        container: a legacy responder ignores ``offset`` (no echo, always the
        first window), so a paged reply missing the matching echo — or adding
        zero new children, or erroring, or blowing the page cap — aborts to
        None. Unknown ≠ empty — partial reads join the unreadable path, which
        every caller already renders honestly.
        """
        slots: dict[int, str | None] = {}
        seen = 0
        for page in range(10):  # 상한 10페이지(240슬롯) — 실제 컨테이너 크기의 여유 상계
            arguments: dict[str, object] = {"path": path}
            if page:
                # 후속 창은 누적 자식 수부터. 첫 요청은 기존 무페이징 판독과
                # 인자까지 동일하다(하위호환 — 구버전 응답기도 첫 창은 준다).
                arguments["offset"] = seen
            probe = self._registry.dispatch(
                ToolCall(
                    id=f"{probe_id}-p{page}" if page else probe_id,
                    name="query_state",
                    arguments=arguments,
                )
            )
            if probe.result.is_error:
                return None
            try:
                payload = json.loads(probe.result.content)
            except (json.JSONDecodeError, TypeError):
                return None
            children = payload.get("children") if isinstance(payload, dict) else None
            if not isinstance(children, list):
                return None
            if page:
                # 무진전 방어 — 구버전 응답기는 offset을 무시하고 항상 첫 창을
                # 돌려준다(에코 부재). 에코 불일치·신규 자식 0개도 같은 갈래:
                # 반복해도 전진이 없으므로 즉시 부분 판독(None)으로 내려간다.
                echo = payload.get("offset")
                if isinstance(echo, bool) or echo != seen:
                    return None
                if not children:
                    return None
            for child in children:
                if isinstance(child, dict):
                    try:
                        # 실기 responder는 슬롯 번호를 "i"로 보낸다 (PROTOCOL §4.2,
                        # rig_object와 동일 규칙); "no"는 정규화된 페이로드용.
                        number = int(child.get("i", child.get("no")))
                    except (TypeError, ValueError):
                        continue
                    name = child.get("name")
                    slots[number] = name if isinstance(name, str) else None
            seen += len(children)
            # 절단 판정은 두 경로 — 응답기 truncated 플래그 또는 childCount 산술.
            # 한쪽만 삭제돼도 나머지가 잡는다 (TRUNCATE-001과 같은 이중 방어).
            node = payload.get("node")
            child_count = node.get("childCount") if isinstance(node, dict) else None
            more = bool(payload.get("truncated")) or (
                isinstance(child_count, int) and child_count > seen
            )
            if not more:
                return slots  # 누적 == 총계(또는 총계 미달 주장 없음) — 완전 판독
            if not children:
                # 빈 창이 "더 있다"고 주장 — offset이 전진할 수 없는 모순.
                return None
        return None  # 페이지 상한 초과 — 부분 판독은 더 작은 컨테이너가 아니다

    def _position_preset_pool_slots(
        self, *, pool_no: int = POSITION_PRESET_POOL
    ) -> set[int] | None:
        """Number-only view of :meth:`_position_preset_pool_children`."""
        children = self._position_preset_pool_children(pool_no=pool_no)
        return None if children is None else set(children)

    def _resolve_position_preset_labels(
        self,
        labels: Iterable[str],
        *,
        start: int,
        span: int,
        pool_no: int = POSITION_PRESET_POOL,
    ) -> dict[str, int]:
        """룩 라벨 집합 -> Position 프리셋 슬롯, 콘솔 판독 1회(t232).

        `start + BASIC_POSITION_SEQUENCE.index(label)`로 번호를 짓던 옛
        경로는 그 자리가 실제로 그 라벨인지 확인하지 않았다 — 연속 10칸이
        다른 프리셋(예: 시트 프리셋)으로 채워져 있으면 조용히 엉뚱한 프리셋을
        불렀다(카드 t232 판독). 이 헬퍼는 ``_phaser_slot_by_label``과 같은
        규율로 풀을 완전 판독해(``_position_preset_pool_children``) 라벨을
        직접 찾는다.

        라벨은 베이스이름 매칭으로 찾는다(``#n`` 중복 접미 제거). 같은
        베이스이름이 여러 슬롯에 있으면 운영자가 고른 구간
        ``[start, start+span-1]`` 안의 슬롯을 우선한다 — 구간 안에 정확히
        하나가 있으면 그것을 쓴다. 구간 안에 하나도 없는데 구간 밖에 둘
        이상이면 모호 — 거부한다(추측 금지). 어디서든 후보가 딱 하나뿐이면
        그것을 쓴다. 풀을 읽지 못하면 그 자체로 거부한다 — 라벨 부재와는
        다른 사유를 남긴다.
        """
        pool = self._position_preset_pool_children(pool_no=pool_no)
        if pool is None:
            raise SpatialPointingError(
                f"Position 프리셋 풀(Preset {pool_no}.x)을 읽지 못해 라벨을 확인할 수 없습니다"
            )
        by_base: dict[str, list[int]] = {}
        for slot, name in pool.items():
            if not isinstance(name, str):
                continue
            base = name.split("#", 1)[0]
            by_base.setdefault(base, []).append(slot)
        span_end = start + span - 1
        resolved: dict[str, int] = {}
        for label in labels:
            if label in resolved:
                continue
            candidates = sorted(by_base.get(label, ()))
            if not candidates:
                raise SpatialPointingError(
                    f"'{label}' 라벨의 Position 프리셋을 콘솔에서 찾지 못했습니다"
                )
            if len(candidates) == 1:
                resolved[label] = candidates[0]
                continue
            in_span = [slot for slot in candidates if start <= slot <= span_end]
            if len(in_span) == 1:
                resolved[label] = in_span[0]
                continue
            raise SpatialPointingError(
                f"'{label}' 라벨이 Position 프리셋 여러 슬롯 {candidates}에 있어 특정할 수 없습니다"
            )
        return resolved

    def _position_preset_free_starts(
        self, *, count: int = 3, pool_no: int = POSITION_PRESET_POOL
    ) -> list[int] | None:
        """Start numbers where TEN consecutive pool slots are EMPTY —
        for the preset STORE path, the mirror image of
        `_position_preset_ready_starts`. None = pool unreadable."""
        slots = self._position_preset_pool_slots(pool_no=pool_no)
        if slots is None:
            return None
        span = len(BASIC_POSITION_SEQUENCE)
        starts: list[int] = []
        for base in range(1, 92, span):
            if all(base + offset not in slots for offset in range(span)):
                starts.append(base)
                if len(starts) == count:
                    break
        return starts

    def _dmx_channel_names(
        self, type_index: int, mode_index: int, *, probe_id_prefix: str
    ) -> list[str | None] | None:
        """Every channel NAME under one ``(type, mode)``'s ``DMXChannels`` —
        or None when the listing cannot be COMPLETELY read.

        The responder caps children per reply, and the channel listing hits
        that cap on real fixtures (M0 live probe 2026-08-16: type 2's 29
        channels came back 15-of-29 truncated), so this read pages exactly
        like :meth:`_position_preset_pool_children`: follow-up windows carry
        ``offset`` (accumulated child count), a paging-aware responder echoes
        it back, and truncation WITHOUT progress — no echo, zero new
        children, an error, or the page cap — aborts to None. Unknown ≠
        read: a partial channel list is not a smaller channel list, and the
        caller must not judge capability on one.

        A child that carries no string name contributes ``None`` — the
        listing arrived whole, but that channel's identity did not, and the
        caller's verdict must account for it (unknown ≠ absent).
        """
        types_root = self._rig_paths.get("fixture_types", "Patch/FixtureTypes")
        path = f"{types_root}/{type_index}/DMXModes/{mode_index}/DMXChannels"
        names: list[str | None] = []
        seen = 0
        for page in range(10):  # 상한 10페이지 — 실측 최대 29채널의 여유 상계
            arguments: dict[str, object] = {"path": path}
            if page:
                arguments["offset"] = seen
            probe = self._registry.dispatch(
                ToolCall(
                    id=f"{probe_id_prefix}-channels-t{type_index}m{mode_index}"
                    + (f"-p{page}" if page else ""),
                    name="query_state",
                    arguments=arguments,
                )
            )
            if probe.result.is_error:
                return None
            try:
                payload = json.loads(probe.result.content)
            except (json.JSONDecodeError, TypeError):
                return None
            children = payload.get("children") if isinstance(payload, dict) else None
            if not isinstance(children, list):
                return None
            if page:
                # 무진전 방어 — 구버전 응답기는 offset을 무시하고 항상 첫 창을
                # 돌려준다(에코 부재). 에코 불일치·신규 자식 0개는 전진 불가.
                echo = payload.get("offset")
                if isinstance(echo, bool) or echo != seen:
                    return None
                if not children:
                    return None
            for child in children:
                name = child.get("name") if isinstance(child, dict) else None
                names.append(name if isinstance(name, str) else None)
            seen += len(children)
            # 절단 판정은 이중 — truncated 플래그 또는 childCount 산술.
            node = payload.get("node")
            child_count = node.get("childCount") if isinstance(node, dict) else None
            more = bool(payload.get("truncated")) or (
                isinstance(child_count, int) and child_count > seen
            )
            if not more:
                return names
            if not children:
                return None
        return None  # 페이지 상한 초과 — 부분 판독은 더 짧은 채널 목록이 아니다

    def _fixture_color_channel_names(
        self, fixtures: Sequence[tuple[int, int]], *, probe_id_prefix: str
    ) -> dict[int, list[str | None] | None]:
        """``fid -> DMX 채널 이름 목록``(완전 판독) 또는 ``None``(판독 실패·
        미해소 절단) — ``_color_capable_fids``와 W 채널 분류
        (``_w_capable_fids``, 카드 t430)가 공유하는 3단계 판독.

        ``fixtures``는 ``(slot, fid)`` 쌍: ``slot``이 패치 자식 경로를
        가리키고(``rig_paths["fixtures"]`` 아래, 속성 판독은 PATH가
        필요), ``fid``가 호출자가 고르는 키다.

        기구별: ① ``FixtureType`` 속성 → ``"FixtureType N"``(표시 문자열,
        M0 실측 형태 — 끝 정수가 이 채널의 라이브러리 경로 인덱스) ②
        ``Mode`` 속성 → ``"<m> <name>"``(첫 토큰이 모드 경로 인덱스) ③
        ``(N, m)`` 조합의 ``DMXChannels`` 자식 이름, 페이징
        (:meth:`_dmx_channel_names`) — 조합 단위 캐시(왕복 예산은
        ``_color_capable_fids`` 독스트링과 동일). 판정(부분 문자열 기준)은
        호출자 몫이다 — 이 메서드는 이름 목록만 돌려준다.
        """
        fixtures_root = self._rig_paths.get("fixtures", "Patch/Stages/1/Fixtures")
        combo_names: dict[tuple[int, int], list[str | None] | None] = {}
        result: dict[int, list[str | None] | None] = {}
        for slot, fid in fixtures:
            reads = read_properties(
                self._current_cue_port,
                f"{fixtures_root}/{slot}",
                ("FixtureType", "Mode"),
            )
            type_read = reads["FixtureType"]
            mode_read = reads["Mode"]
            if not type_read.ok or not mode_read.ok:
                result[fid] = None
                continue
            # 표시 문자열 파싱 — M0 실측 형태만 받는다. 다른 형태(타입 이름 표시,
            # 무번호 모드)는 추측하지 않고 판별 불가로 내린다(fail-closed).
            type_match = re.fullmatch(r"FixtureType\s+(\d+)", str(type_read.value or "").strip())
            mode_match = re.match(r"(\d+)(?:\s|$)", str(mode_read.value or "").strip())
            if type_match is None or mode_match is None:
                result[fid] = None
                continue
            combo = (int(type_match.group(1)), int(mode_match.group(1)))
            if combo not in combo_names:
                combo_names[combo] = self._dmx_channel_names(
                    combo[0], combo[1], probe_id_prefix=probe_id_prefix
                )
            result[fid] = combo_names[combo]
        return result

    def _color_capable_fids(
        self, fixtures: Sequence[tuple[int, int]], *, probe_id_prefix: str
    ) -> tuple[list[int], list[int], list[int]]:
        """``(capable_fids, excluded_fids, undetermined_fids)`` for the color
        preset bundle — the M0-measured 3-hop discrimination
        (SPEC-COPILOT-COLORPRESET-001 REQ-005, progress.md §E.1).

        ``fixtures`` is ``(slot, fid)`` pairs: ``slot`` addresses the patch
        child under ``rig_paths["fixtures"]`` (the property reads need the
        PATH), ``fid`` is what the caller selects with (the return lists).

        Judged by SUBSTRING ``"ColorRGB"`` on the channel names
        :meth:`_fixture_color_channel_names` reads (shared 3-hop discovery)
        — ``ColorRGB_R/G/B`` and ``ColorRGB_W`` alike (measured: LEDBeam350
        carries the W channel).

        Verdicts: a name match → capable; a COMPLETELY read list with no
        match → excluded; everything else — a failed/unparseable property, an
        unresolved truncation, a nameless channel child masking the answer —
        → undetermined. unknown ≠ capable AND unknown ≠ excluded: silently
        promoting either way would aim the bundle at fixtures nobody judged
        or silently shrink it (REQ-005 forbids both).

        Round-trip budget: 2 property reads per fixture (FixtureType + Mode)
        plus ≤10 paged channel windows per DISTINCT ``(type, mode)``
        combination — cached per call, so the measured 41-fixture rig with
        ≤5 combinations costs 82 property reads + a handful of state pages.
        """
        channel_names = self._fixture_color_channel_names(fixtures, probe_id_prefix=probe_id_prefix)
        capable: set[int] = set()
        excluded: set[int] = set()
        undetermined: set[int] = set()
        for _slot, fid in fixtures:
            names = channel_names.get(fid)
            if names is not None and any(name is not None and "ColorRGB" in name for name in names):
                capable.add(fid)
            elif names is not None and all(name is not None for name in names):
                excluded.add(fid)  # 전 채널 이름 완독 + 부재 — 확정 제외
            else:
                undetermined.add(fid)  # 절단 미해소·무명 자식 — 판별 불가
        return sorted(capable), sorted(excluded), sorted(undetermined)

    def _w_capable_fids(
        self, fixtures: Sequence[tuple[int, int]], *, probe_id_prefix: str
    ) -> tuple[list[int], list[int], list[int]]:
        """``(w_capable_fids, rgb_only_fids, undetermined_fids)`` — 카드
        t430 W 채널 분류. ``_color_capable_fids``와 같은 3단계 판독을
        공유한다(:meth:`_fixture_color_channel_names`, 조합당 1회 캐시).
        콘솔 쓰기는 0 — 읽기만 한다.

        완전 판독 + ``"ColorRGB_W"`` 부분 문자열 존재 → w_capable. 완전
        판독 + 부재 → rgb_only. 실패·파싱 불가·미해소 절단은 모두
        undetermined다(``_color_capable_fids``와 같은 fail-closed 규율 —
        모르는 채널은 켜지 않는다). 호출자는 undetermined를 rgb_only와
        같이 다뤄야 한다(t430 결정 범위 §5 — RGB만 낸다).
        """
        channel_names = self._fixture_color_channel_names(fixtures, probe_id_prefix=probe_id_prefix)
        w_capable: set[int] = set()
        rgb_only: set[int] = set()
        undetermined: set[int] = set()
        for _slot, fid in fixtures:
            names = channel_names.get(fid)
            if names is not None and any(
                name is not None and "ColorRGB_W" in name for name in names
            ):
                w_capable.add(fid)
            elif names is not None and all(name is not None for name in names):
                rgb_only.add(fid)
            else:
                undetermined.add(fid)
        return sorted(w_capable), sorted(rgb_only), sorted(undetermined)

    def _ask_position_preset_start(self, refusal: str) -> int | InstructionResult:
        """The shared '기본 포지션이 프리셋 몇 번부터?' card — proposes only
        starts the console VERIFIED as ten consecutive stored presets, and
        falls back to the static examples when the pool is unreadable."""
        pool_slots = self._position_preset_pool_slots()
        ready_starts = self._position_preset_ready_starts(slots=pool_slots) if pool_slots else []
        if ready_starts:
            prompt = (
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                "저장돼 있나요? 콘솔에서 10칸 연속 저장된 구간을 확인했습니다."
            )
            options = tuple(
                QuestionOption(label=f"{start} (2.{start}~2.{start + 9} 저장 확인됨)")
                for start in ready_starts[:3]
            )
        else:
            if pool_slots is None:
                diagnosis = (
                    "Position 풀을 읽지 못했습니다 — 콘솔 응답이 불안정하면(responder) "
                    "잠시 후 다시 시도하면 확인된 구간을 제안할 수 있습니다."
                )
            elif not pool_slots:
                diagnosis = (
                    "Position 풀에 저장된 프리셋이 없습니다 — 먼저 "
                    "'기본 포지션 10개 저장'을 실행해 주세요."
                )
            else:
                diagnosis = (
                    f"Position 풀에 프리셋 {len(pool_slots)}개가 있지만 10칸 연속 "
                    "구간을 찾지 못했습니다."
                )
            prompt = (
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                f"저장돼 있나요? {diagnosis} 아래 예시는 검증되지 않은 번호입니다. "
                "(예: 21 → 2.21~2.30)"
            )
            options = (
                QuestionOption(label="1"),
                QuestionOption(label="11"),
                QuestionOption(label="21"),
            )
        answer = self._ask_one(
            prompt,
            options=options,
            why=(
                "큐는 프리셋 참조로 빌드됩니다 — 잘못된 슬롯을 리콜하면 "
                "그 자리에 있는 다른 포지션이 무대에 나갑니다."
            ),
        )
        try:
            return int(re.search(r"\d+", answer or "").group(0))
        except AttributeError:
            return self._pointing_refusal(refusal)

    def _song_probe_sequence_slots(
        self, start: int, *, count: int = 3, probes: int = 12, step: int = 10
    ) -> tuple[list[int], int, int]:
        """(verified-empty slots, occupied count, unreadable count) walking
        ``step`` at a time from ``start`` (inclusive). Unreadable slots get
        ONE retry pass — responder flapping is intermittent (핸드오프 실측:
        재시도로 해결), so a second probe usually revives them; a slot that
        fails twice stays unreadable (fail-closed, never proposed)."""
        free: list[int] = []
        occupied = 0
        retry_queue: list[int] = []
        candidate = start
        for _probe in range(probes):
            verdict = self._console_slot_state(
                f"{self._rig_paths['sequences']}/{candidate}",
                probe_id=f"song-design-slot-check-{candidate}",
            )
            if verdict == "empty":
                free.append(candidate)
                if len(free) == count:
                    break
            elif verdict == "occupied":
                occupied += 1
            else:
                retry_queue.append(candidate)
            candidate += step
        unreadable = 0
        for slot in retry_queue:
            if len(free) == count:
                break
            verdict = self._console_slot_state(
                f"{self._rig_paths['sequences']}/{slot}",
                probe_id=f"song-design-slot-recheck-{slot}",
            )
            if verdict == "empty":
                free.append(slot)
            elif verdict == "occupied":
                occupied += 1
            else:
                unreadable += 1
        free.sort()
        return free, occupied, unreadable

    def _song_free_sequence_slots(
        self, start: int, *, count: int = 3, probes: int = 12, step: int = 10
    ) -> list[int]:
        """Up to ``count`` console-VERIFIED empty sequence slots."""
        free, _occupied, _unreadable = self._song_probe_sequence_slots(
            start, count=count, probes=probes, step=step
        )
        return free

    def _position_preset_ready_starts(
        self,
        *,
        count: int = 3,
        slots: set[int] | None = None,
        pool_no: int = POSITION_PRESET_POOL,
    ) -> list[int]:
        """Start numbers where the pool holds TEN consecutive stored
        presets (s ~ s+9). ``slots`` skips a second pool read when the
        caller already fetched it. Unreadable pool → []."""
        stored = slots if slots is not None else self._position_preset_pool_slots(pool_no=pool_no)
        if not stored:
            return []
        span = len(BASIC_POSITION_SEQUENCE)
        starts: list[int] = []
        for slot in sorted(stored):
            if (slot - 1) in stored:
                continue  # not a run start
            if all(slot + offset in stored for offset in range(span)):
                starts.append(slot)
                if len(starts) == count:
                    break
        return starts

    def _song_pick_sequence(
        self, requested: int | None, *, purpose: str, refusal: str
    ) -> int | InstructionResult:
        """The store-target sequence, verified EMPTY up front (2026-08-16
        사용자 방향): a free requested number passes silently; an occupied or
        missing one opens a card that proposes console-verified empty slots."""
        if requested is not None and not self._song_sequence_occupied(requested):
            return requested
        free_slots, occupied, unreadable = self._song_probe_sequence_slots(
            (requested or 100) + 10 if requested is not None else 110
        )
        lead = (
            f"시퀀스 {requested}에는 이미 콘솔 데이터가 있어 그대로 저장하면 콘솔이 거부합니다. "
            if requested is not None
            else ""
        )
        if free_slots:
            prompt = (
                f"{lead}{purpose}를 어느 시퀀스에 저장할까요? "
                "비어 있는 번호를 콘솔에서 확인해 제안합니다. (직접 입력도 가능)"
            )
            options = tuple(QuestionOption(label=f"{slot} (비어 있음)") for slot in free_slots)
        else:
            diagnosis = f"탐침 결과: 점유 {occupied}곳 · 조회 실패 {unreadable}곳."
            if unreadable:
                diagnosis += (
                    " 콘솔 응답이 불안정합니다(responder) — 잠시 후 다시 시도하면 "
                    "검증된 번호를 제안할 수 있습니다."
                )
            prompt = (
                f"{lead}{purpose}를 어느 시퀀스에 저장할까요? 비어 있음을 확인한 "
                f"번호가 없어 직접 입력이 필요합니다. {diagnosis} 아래 예시는 "
                "검증되지 않은 번호이며, 이미 큐가 있으면 저장이 거부될 수 있습니다."
            )
            options = (
                QuestionOption(label="110"),
                QuestionOption(label="120"),
                QuestionOption(label="200"),
            )
        answer = self._ask_one(
            prompt,
            options=options,
            why="Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 운영자 결정입니다.",
        )
        try:
            return int(re.search(r"\d+", answer or "").group(0))
        except AttributeError:
            return self._pointing_refusal(refusal)

    def _song_recover_sequence(
        self, state: _SongDesignState, *, problem: str
    ) -> tuple[UnifiedSongLightingPlan, SongCueCompositionResult] | InstructionResult:
        """The interactive recovery card (2026-08-16 사용자 방향): explain the
        problem, PROPOSE verified-empty sequence slots, and let the director
        pick one on the spot. A pick retargets the pending plan and the caller
        stores immediately; cancel/no-answer keeps the plan editable."""
        free_slots, occupied, unreadable = self._song_probe_sequence_slots(state.sequence_no + 10)
        if free_slots:
            situation = (
                "비어 있는 시퀀스를 콘솔에서 확인했습니다 — 어디에 저장할까요? "
                "(선택하면 즉시 그 시퀀스에 저장합니다. 다른 번호는 직접 입력해도 됩니다.)"
            )
        else:
            situation = (
                f"비어 있음을 확인한 시퀀스가 없습니다 (탐침 결과: 점유 {occupied}곳 · "
                f"조회 실패 {unreadable}곳)."
            )
            if unreadable:
                situation += (
                    " 콘솔 응답이 불안정합니다(responder) — 잠시 기다렸다가 다시 "
                    "승인하면 검증된 번호를 제안할 수 있습니다."
                )
            situation += " 저장할 번호를 직접 입력해 주세요."
        options = tuple(QuestionOption(label=f"시퀀스 {slot}") for slot in free_slots) + (
            QuestionOption(label="취소 (계획 보존)"),
        )
        answer = self._ask_one(
            f"{problem}\n{situation}",
            options=options,
            why=(
                "문제를 만나면 중단 대신 해결 방법을 함께 정합니다. "
                "기존 시퀀스는 절대 덮어쓰지 않습니다."
            ),
        )
        number = re.search(r"\d+", answer or "")
        if (
            answer is None
            or _SONG_REQUERY_CANCEL.match(answer) is not None
            or "취소" in answer
            or number is None
        ):
            self._pending_song_plan = state
            return InstructionResult(
                status="ok",
                text=(
                    f"{problem} 저장하지 않았고 계획은 그대로 보존했습니다. "
                    "준비되면 '시퀀스 N으로 변경'이라고 답한 뒤 다시 승인해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        state.sequence_no = int(number.group(0))
        return self._song_compose(state)

    # @MX:ANCHOR: [AUTO] 카드 t318 — 번들 위험 선언을 실은 디스패치는 **전부**
    #   이 자리를 지난다. `tools.py` 밖의 봉합은 `ToolRegistry.dispatch` 만
    #   지나므로(`ExecutionContext.risk`), 선언이 배선을 못 지나는 사고도 전부
    #   여기서 잡힌다.
    # @MX:REASON: 선언이 조용히 사라지면 「0건 나갔다」가 거절·무작업과 구별되지
    #   않는다(SPEC-COPILOT-WRITEGATE-001). 새 심사 통로가 아니라 기존
    #   디스패치의 유일한 선언 입구다 — 게이트의 `@MX:ANCHOR` 는 그대로 하나다.
    def _dispatch_declared(self, call: ToolCall, *, risk: BatchRisk | None):
        """선언을 실어 디스패치한다 — 실을 수 없으면 조용한 0건 대신 크게 깨진다.

        배선 확인은 **호출 전** `Signature.bind` 로 한다. 핸들러를 돌리지 않고
        인자 수만 맞춰 보는 것이라, 핸들러 **안쪽**에서 나는 `TypeError`(진짜
        버그)는 이 자리가 삼키지 않는다 — 잡는 것은 「이 레지스트리는 선언을
        받을 수 없다」 하나뿐이다.

        쓸 것이 없는 회차는 여기까지 오지 않는다. 이 함수는 이미 만들어진
        명령 묶음에만 붙는다.

        카드 t320 — `risk` 는 `None` 일 수 있다. `showfile_write_risk` 가
        **나갈 명령**에서 쇼파일 쓰기를 못 읽으면 그렇게 답하고(프로그래머 값만
        찍는 번들), 그 회차는 선언으로 인한 카드를 띄우지 않는다. 배선 확인은
        그대로 한다 — 선언을 못 싣는 레지스트리는 선언이 있든 없든 사고다.
        """
        # 카드 t323 — `risk=None` 이 여기서는 **판단의 결과**다(프로그래머 값만
        # 찍는 번들). 레지스트리 등재분은 선언 없는 번들의 선언을 스스로 읽어
        # 만드는데, 그 자동 계산이 이 판단을 덮으면 안 된다.
        context = ExecutionContext(risk=risk, approval_owned_by_caller=True)
        dispatch = self._registry.dispatch
        try:
            inspect.signature(dispatch).bind(call, context)
        except TypeError as error:
            raise WriteGateDeclarationError(
                f"{type(self._registry).__name__}.dispatch 가 번들 위험 선언"
                f"(kind={getattr(risk, 'kind', None)!r})을 실은 ExecutionContext 를 "
                "받지 못합니다 — "
                "선언 없이 보내면 승인 카드 없이 쇼파일이 고쳐지므로 아무것도 "
                f"보내지 않았습니다: {error}"
            ) from error
        except (ValueError, AttributeError):
            # 시그니처를 못 읽는 호출 가능 객체(내장/래퍼)는 확인을 건너뛴다 —
            # 판단 못 한 것을 실패로 읽지 않는다. 실제로 못 받으면 아래 호출이
            # TypeError 로 터지고, 그건 여전히 조용한 0건이 아니다.
            pass
        return dispatch(call, context)

    def _song_finalize(
        self,
        state: _SongDesignState,
        plan: UnifiedSongLightingPlan,
        composition: SongCueCompositionResult,
    ) -> InstructionResult:
        review_text = _review_text(plan, composition, layer_mapped=bool(state.layer_mapping))
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
        # #3 (2026-08-16): resolve a conflicting timecode slot BEFORE approval
        # — same interactive posture as the sequence recovery card.
        timecode_no = state.timing.timecode_number
        timecode_note = ""
        if timecode_no is not None:
            if self._timecode_occupied(timecode_no):
                free_timecodes = self._free_timecode_slots(timecode_no)
                answer = self._ask_one(
                    f"타임코드 {timecode_no}번 슬롯에 기존 데이터가 있습니다. 어떻게 할까요?",
                    options=(QuestionOption(label=f"그대로 저장 ({timecode_no}번 슬롯)"),)
                    + tuple(
                        QuestionOption(label=f"타임코드 {slot}번 슬롯 (비어 있음)")
                        for slot in free_timecodes
                    )
                    + (QuestionOption(label="취소 (계획 보존)"),),
                    why="문제를 만나면 중단 대신 해결 방법을 함께 정합니다.",
                )
                if answer is None or "취소" in (answer or ""):
                    return self._pointing_refusal(
                        f"타임코드 {timecode_no}번 슬롯 충돌이 해결되지 않아 저장하지 않았습니다. "
                        "계획은 그대로 보존했습니다."
                    )
                if "그대로" in answer:
                    timecode_note = f" · 타임코드 {timecode_no}번 슬롯: 기존 슬롯에 저장(감독 확인)"
                else:
                    moved = re.search(r"\d+", answer)
                    if moved is None:
                        return self._pointing_refusal(
                            "타임코드 번호를 읽지 못해 저장하지 않았습니다. 계획은 보존했습니다."
                        )
                    state.timing = TimingPlan.timecode(int(moved.group(0)), source="director")
                    timecode_no = state.timing.timecode_number
                    plan, composition = self._song_compose(state)
                    review_text = _review_text(
                        plan, composition, layer_mapped=bool(state.layer_mapping)
                    )
                    self._song_send_timeline(state, plan, composition)
                    timecode_note = f" · 타임코드 {timecode_no}번 슬롯: 비어 있음 확인"
            else:
                timecode_note = f" · 타임코드 {timecode_no}번 슬롯: 비어 있음 확인"
        sequence_no = state.sequence_no
        # #5 (2026-08-16): the approval card carries a VERIFIED impact summary
        # — what gets created where, and that nothing existing is overwritten.
        sequence_free = not self._song_sequence_occupied(sequence_no)
        sequence_verdict = (
            "비어 있음 확인(신규 저장)"
            if sequence_free
            else "사용 중 — 승인 후 빈 시퀀스 선택 카드가 열립니다"
        )
        impact = (
            f"영향 요약 — 시퀀스 {sequence_no}: {sequence_verdict}"
            f"{timecode_note} · 기존 데이터 덮어쓰기: 없음."
        )
        approval = self._ask_one(
            f"{review_text}\n\n{impact}\n\n"
            f"이 전체 리뷰 번들을 시퀀스 {sequence_no}에 원자적으로 저장할까요?",
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
        # 2026-08-16 사용자 방향: a problem is a QUESTION, not a dead end.
        # An occupied target ("Not allowed") or a console-refused store opens
        # a recovery card that PROPOSES verified-empty sequences — picking one
        # stores immediately; declining keeps the plan editable.
        executed = None
        approved_plan = plan
        approved_composition = composition
        for _attempt in range(3):
            sequence_no = state.sequence_no
            if self._song_sequence_occupied(sequence_no):
                recovered = self._song_recover_sequence(
                    state,
                    problem=(
                        f"시퀀스 {sequence_no}에 이미 콘솔 데이터가 있어 그대로 저장하면 "
                        "콘솔이 'Not allowed'로 거부합니다."
                    ),
                )
                if isinstance(recovered, InstructionResult):
                    return recovered
                plan, composition = recovered
                continue
            self._pending_song_plan = None
            approved_plan = replace(plan, approval=ApprovalState.approved(reviewer="director"))
            approved_composition = compose_song_cue_bundle(approved_plan)
            self._song_send_timeline(
                state, approved_plan, approved_composition, lifecycle="approved"
            )
            try:
                commands = self._reviewed_song_commands(
                    approved_composition,
                    sequence_no=sequence_no,
                    preset_start=state.preset_start,
                    fids=state.fids,
                    timing=state.timing,
                    layer_mapping=state.layer_mapping,
                    w_fids=state.w_fids,
                )
            except SpatialPointingError as error:
                self._pending_song_plan = state
                return self._pointing_refusal(
                    f"리뷰 번들을 실행 명령으로 만들 수 없습니다: {error}"
                )
            # SPEC-COPILOT-WRITEGATE-001 — 감독이 실제로 쓰는 곡 흐름이 여기서
            # 나간다(업로드 → 분석 → 확인 → 인터뷰 → 이 번들). 2026-09-07
            # 브라우저 실측에서 `Store Sequence 210 Cue 1..4` 와
            # `Store Timecode 9` 가 나갔는데 게이트 승인은 0건이었다 —
            # 명령 텍스트만으로는 이 묶음이 안 잡히기 때문이다(`Store Sequence`
            # 는 `blacklist.yaml` 에 없다). 위의 `_ask_one` 리뷰 카드는 **계획**을
            # 승인받는 자리이고, 콘솔에 무엇이 나가는지를 게이트가 묻는 자리는
            # 여기다. 그래서 `prepare_songcue` 가 이미 쓰는 그 선언을 그대로 단다
            # (BULKGATE 의 `risk` — 새 심사 통로가 아니라 같은 `gate.screen`).
            #
            # 선언은 `ExecutionContext.risk` 로 흐른다. `tools.py` 밖에서는
            # `run_commands` 클로저를 직접 못 부르고 `dispatch` 만 지나기
            # 때문이고, 컨텍스트는 이미 그 두 번째 인자다 — `call.arguments`
            # 가 아니라 **코드가 만드는 자리**라 모델이 못 만진다.
            songcue_risk = BatchRisk(
                reason=_song_write_risk_reason(sequence_no, commands),
                kind="song_design",
            )
            executed = self._dispatch_declared(
                ToolCall(
                    id="song-design-reviewed-bundle",
                    name="run_commands",
                    arguments={"commands": list(commands)},
                ),
                risk=songcue_risk,
            )
            store_failures = [
                outcome
                for outcome in executed.command_outcomes
                if outcome.status in ("failed", "blocked", "rejected")
            ]
            if executed.result.is_error or store_failures:
                # Keep the plan editable, clear the half-filled programmer
                # (the chain stopped before its own ClearAll), then ask HOW
                # to proceed instead of just reporting the refusal.
                self._pending_song_plan = state
                self._registry.dispatch(
                    ToolCall(
                        id="song-design-cleanup",
                        name="run_commands",
                        arguments={"commands": ["ClearAll"]},
                    )
                )
                self._song_send_timeline(state, plan, composition, lifecycle="pending_approval")
                first_failure = store_failures[0] if store_failures else None
                detail = (
                    f"{first_failure.command} → {first_failure.detail or first_failure.status}"
                    if first_failure is not None
                    else str(executed.result.content)
                )
                recovered = self._song_recover_sequence(
                    state,
                    problem=(
                        f"시퀀스 {sequence_no} 저장이 콘솔에서 거부되었습니다({detail}). "
                        "프로그래머는 ClearAll로 정리했습니다."
                    ),
                )
                if isinstance(recovered, InstructionResult):
                    return replace(recovered, command_outcomes=tuple(executed.command_outcomes))
                plan, composition = recovered
                executed = None
                continue
            break
        if executed is None:
            self._pending_song_plan = state
            return self._pointing_refusal(
                "세 차례 시도에도 저장할 수 있는 시퀀스를 확정하지 못해 저장하지 "
                "않았습니다. 계획은 그대로 보존했습니다 — '시퀀스 N으로 변경' 후 "
                "다시 승인해 주세요."
            )
        sequence_no = state.sequence_no
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
                    f"{_phaser_failure_note(self._last_phaser_failures)}"
                    f"{_color_failure_note(self._last_color_failures)}"
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
                f"{_phaser_failure_note(self._last_phaser_failures)}"
                f"{_color_failure_note(self._last_color_failures)}"
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
    def run_instruction(self, text: str, selected_cue: int | None = None) -> dict:
        """Drive one Korean instruction; sends + returns the final event.

        ``selected_cue`` 는 화면에서 감독이 고른 큐 번호다(t281). 선택을 요청에
        **실어 보내는** 방식이라, 「지금 선택을 읽어라」 같은 별도 왕복이 없고
        모델 제공자가 없어도 동작한다. 기본값 None = 선택 없음(기존 동작).
        """
        self._selected_cue = selected_cue
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
                    # 합성 문장은 단일 계열 핸들러 **전부보다 앞**에서 걸러낸다 —
                    # 체인은 첫 매칭 하나만 실행하고 턴을 끝내므로, 여섯 계열을
                    # 지정한 문장이 아래로 흐르면 한 계열만 저장되고 나머지는
                    # 조용히 사라진다(2026-08-19 실측). 계열이 하나뿐인 문장은
                    # 이 핸들러가 ``None``\을 돌려 아래 기존 경로로 그대로
                    # 흘러내린다 — 단일 요청의 행선지는 바뀌지 않는다.
                    result = self._compound_preset_request(text)
                if result is None:
                    # 프리셋 가족 디스패치는 **구체적 어휘축 → 포괄 어휘축**
                    # 순서다(합성 문장 오라우팅 방지, 2026-08-17 리뷰 실측):
                    # ① 콤보(콤보/컬러 디머/드롭)가 맨 앞 — "컬러 디머 페이저
                    #    저장" 같은 합성 문장이 디머 페이저 축(디머 페이저)에도
                    #    매치되므로, 뒤에 두면 회색조 카탈로그가 Dimmer 풀에
                    #    저장되는 오라우팅이 실제로 발생했다.
                    # ② 페이저(멀티컬러/컬러 이펙트, 디머 이펙트/디머 페이저)가
                    #    기본(기본 컬러/기본 디머)보다 앞 — "기본 멀티컬러 페이저
                    #    저장"의 '멀티'가 기본 트리거의 .{0,16}? 갭에 흡수되어
                    #    팔레트 경로가 페이저 문장을 삼키는 것을 막는다. 역방향은
                    #    안전하다: 순수 기본 문장("기본 컬러 저장")은 페이저
                    #    축 토큰이 없어 페이저 트리거를 매치하지 못한다.
                    # 각 가족 안에서는 재생성이 신규 저장보다 앞이다 — 저장
                    # 트리거의 '잡아'가 재생성 문장을 함께 매치한다
                    # (REQ-PRESETGUARD-015와 같은 등록 순서 고정).
                    result = self._regenerate_combo_phaser_presets(text)
                if result is None:
                    result = self._combo_phaser_presets(text)
                if result is None:
                    result = self._regenerate_color_phaser_presets(text)
                if result is None:
                    result = self._color_phaser_presets(text)
                if result is None:
                    result = self._regenerate_dimmer_phaser_presets(text)
                if result is None:
                    result = self._dimmer_phaser_presets(text)
                if result is None:
                    # 기본(포괄) 계열은 페이저 뒤, 포지션 앞 — 포지션 트리거의
                    # 명사 대안 '프리셋'이 "기본 컬러 프리셋 …" 문장을 함께
                    # 매치하는 반면 컬러/디머 트리거는 포지션 문장을 매치할
                    # 수 없다(기존 근거 유지).
                    result = self._regenerate_basic_color_presets(text)
                if result is None:
                    result = self._basic_color_presets(text)
                if result is None:
                    result = self._regenerate_basic_dimmer_presets(text)
                if result is None:
                    result = self._basic_dimmer_presets(text)
                if result is None:
                    # 재생성이 신규 저장보다 **먼저**다 — 두 트리거의 교집합이
                    # 공집합이 아니므로(ASSUMPTION-83 반증) 등록 순서가 겹치는
                    # 입력의 행선지를 고정한다 (REQ-PRESETGUARD-015).
                    result = self._regenerate_position_presets(text)
                if result is None:
                    # FX 재생성도 같은 이유로 신규 FX 저장('잡아' 대안 포함)보다
                    # 앞이다 — 어휘(이펙트/효과/fx vs 기본/베이직)가 서로소라
                    # BASIC 재생성과는 어느 쪽 순서든 오라우팅이 없다.
                    result = self._regenerate_fx_position_presets(text)
                if result is None:
                    result = self._basic_position_presets(text)
                if result is None:
                    # 페이저 recall(T11)이 포지션 이펙트 시퀀스보다 **앞**이다 —
                    # 라이브 2026-08-17 실측: "Wave CM 시퀀스로 걸어줘"가
                    # position-FX의 세 게이트(효과어 'wave' + 명사 '시퀀스' +
                    # 동사 '걸어')를 전부 만족해 포지션 경로에 삼켜졌다
                    # ('Wave'를 품은 라벨 6종: Wave CM/WA/Soft/Full, Ocean
                    # Wave, Golden Wave). 페이저 핸들러는 **카탈로그 라벨**을
                    # 필수 게이트로 쓰므로(_match_phaser_label) 라벨 없는
                    # 포지션 문장("좌우 스윕 시퀀스 만들어줘")은 그대로 아래로
                    # 흘러내린다 — 구체 축 먼저라는 같은 규율의 적용이다.
                    # 2단계(시퀀스+실행기)가 1단계(즉시 발사)보다 먼저다 —
                    # 서로소는 명사('시퀀스'/'실행기'/'exec') 유무로 가른다.
                    result = self._phaser_recall_sequence(text)
                if result is None:
                    result = self._phaser_recall(text)
                if result is None:
                    # 효과어(스윕/서클/…)가 필수인 시퀀스 빌더가 프리셋 저장보다
                    # 먼저 본다 — 어휘가 더 구체적이고, 프리셋 저장 문장에는
                    # 효과어가 없어 그대로 아래로 흘러내린다.
                    result = self._position_fx_sequence(text)
                if result is None:
                    result = self._fx_position_presets(text)
                if result is None:
                    result = self._position_cue_sheet(text)
                if result is None:
                    result = self._song_plan_edit(text)
                if result is None:
                    result = self._song_requery_resume(text)
                if result is None:
                    result = self._rehearsal_cue_edit(text)
                if result is None:
                    result = self._timeline_cue_edit(text)
                if result is None:
                    result = self._setlist_mode(text)
                if result is None:
                    # t281 — 큐시트 초안 편집. 위의 콘솔 경로들(`_timeline_cue_edit`
                    # 등)이 **먼저** 본다: 그쪽은 「타임라인」 리터럴과 포지션 어휘를
                    # 필수 게이트로 쓰므로 서로소이고, 순서를 이렇게 두면 기존
                    # 콘솔 편집의 행선지가 이 변경으로 바뀌지 않는다.
                    # t291 — 「콘솔에 반영」은 편집보다 **먼저** 본다. 반영
                    # 문장에는 편집 동사('반영해줘'의 해줘)가 섞여 있어서, 뒤에
                    # 두면 지시어 없는 짧은 문장이 편집 라우트에 삼켜진다.
                    # t303 — 읽기 전용 사전 점검은 반영보다 **먼저** 본다.
                    # 술어끼리는 서로소다: 점검은 보내기 전용 동사(반영해·
                    # 적용해·전송·송출·보내)가 하나라도 있으면 비켜서고,
                    # 반영은 점검 어휘(점검·프리플라이트)를 동사로 쓰지 않는다.
                    # 순서를 이렇게 두는 이유는 방향이다 — 겹치는 입력이 생기면
                    # 콘솔에 쓰지 않는 쪽으로 닫힌다.
                    result = self._rig_preflight(text)
                if result is None:
                    result = self._cue_sheet_draft_apply(text)
                if result is None:
                    result = self._cue_sheet_draft_edit(text)
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
        """비이미지 첨부 하나를 받아 종류에 따라 갈라 보낸다.

        프레임 이름은 유산이다(SPEC-COPILOT-SHEETPIPE-001 결정 A) — 첨부 버튼은
        하나이고, 이미지가 아닌 파일은 전부 이 자리로 온다. 무엇인지 정하는 것은
        A의 판별기이며(``server/sheets/registry.py``), 확장자도 MIME도 분기에
        쓰이지 않는다. 세 갈래로 갈린다:

        * 세션 메서드가 받는 종류(오늘은 ``vectorworks``) — 오늘 그대로. 기존
          슬롯에 담고 지시문을 발화한다. 이 두 줄은 회수되지 않는다.
        * 시트 종류 — 슬롯에 담고 넷을 보이고 아무것도 실행하지 않는다
          (REQ-SHEETPIPE-003). ``notice_event``는 전사에 들어가지 않으므로 모델은
          이 안내를 보지 못하고, 래퍼 툴의 이름 붙은 거절로 슬롯 상태를 안다.
        * 판별 불가 — 슬롯에도 담지 않고 Vectorworks 경로로도 보내지 않으며,
          사유를 이름으로 밝힌다.
        """
        try:
            data = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError):
            return self._notify(f"'{file_name}'의 내용을 읽지 못했습니다 — base64가 아닙니다.")

        result = discriminate(data, filename_hint=file_name)
        if result.outcome != OUTCOME_RESOLVED:
            return self._reject_upload(file_name, result)

        kind = result.matched[0]
        row = next((entry for entry in REGISTRY if entry.kind == kind), None)
        handler = getattr(row, "handler", None)
        if getattr(handler, "kind_tag", None) == HANDLER_TAG_SESSION_METHOD:
            if getattr(handler, "name", None) not in _ATTACH_ROUTED_SESSION_METHODS:
                # 이 자리가 받을 수 있는 세션 메서드는 자기 자신뿐이다. 다른
                # 이름의 session_method 행이 생기면 그 종류를 어디로 보낼지는
                # 아직 정해진 바가 없으므로, 조용히 삼키지 않고 이름으로 말한다.
                return self._notify(
                    f"'{file_name}'은 '{kind}'로 판정됐지만 그 종류를 받는 세션 "
                    f"메서드가 이 첨부 경로에 배선돼 있지 않습니다."
                )
            self._vectorworks_upload.replace(file_name, content_base64)
            return self.run_instruction(_VECTORWORKS_UPLOAD_INSTRUCTION)

        return self._store_uploaded_sheet(file_name, kind, content_base64, data)

    def _notify(self, text: str) -> dict:
        event = notice_event(text)
        self._send(event)
        return event

    def _reject_upload(self, file_name: str, result) -> dict:
        """판별이 종류를 정하지 못했다 — 조용한 무동작 대신 사유를 이름으로 낸다.

        A가 정한 두 결과(``unknown_sheet_kind`` · ``ambiguous_sheet_kind``)를
        그대로 옮긴다. B는 그 규칙을 다시 정의하지 않고 운영자에게 전달만 한다.
        """
        if result.outcome == OUTCOME_AMBIGUOUS:
            detail = "여러 종류에 동시에 맞습니다: " + ", ".join(result.matched)
        else:
            detail = "어느 시트 종류에도, Vectorworks 내보내기에도 맞지 않습니다"
        text = f"'{file_name}'을 받지 못했습니다 ({result.outcome}) — {detail}."
        if result.hint:
            text = text + " " + result.hint
        return self._notify(text)

    def _store_uploaded_sheet(
        self, file_name: str, kind: str, content_base64: str, data: bytes
    ) -> dict:
        """시트 하나를 슬롯에 담고 넷을 보인다 — 실행은 0건이다.

        ``upload_layout_image``와 같은 형태다: 담기만 하고 지시문을 부르지
        않는다. 교체 사실을 소리 내어 말하는 것도 같은 이유다 — 침묵하면 운영자가
        두 장이 붙어 있다고 믿은 채 엉뚱한 시트로 만든 계획을 승인할 수 있다.
        """
        replaced = self._uploaded_sheet is not None
        self._uploaded_sheet = UploadedSheet(
            file_name=file_name,
            kind=kind,
            content_base64=content_base64,
            sha256=hashlib.sha256(data).hexdigest(),
            byte_length=len(data),
        )
        sheet = self._uploaded_sheet
        text = (
            f"'{file_name}' 첨부됨 — 종류 {sheet.kind} · sha256 {sheet.sha256} · "
            f"{sheet.byte_length}바이트 · {_sheet_row_counts(kind, data)}"
        )
        if replaced:
            text = text + " (이전에 첨부한 시트를 교체했습니다)"
        text = text + ". 아직 실행한 것은 없습니다 — 무엇을 할지 말씀해 주세요."
        return self._notify(text)

    def upload_layout_image(self, file_name: str, mime_type: str, content_base64: str) -> dict:
        """Replace this session's attached layout image (REQ-IMGLAYOUT-001/003).

        Storage only — unlike ``upload_vectorworks_export`` this does NOT start
        a guided instruction. The vision analysis is a tool the model reaches
        for (``analyse_layout_image``, M3) only once the operator has actually
        described what to do with the image; auto-analysing on upload would
        spend a model call before there is any description to analyse against.
        Wire-level validation (MIME allowlist, base64, the 5 MiB cap) already
        happened in ``parse_client_message`` — a message that reaches here is
        already accepted.
        """
        replaced = self._layout_image is not None
        self._layout_image = LayoutImageUpload(
            file_name=file_name, mime_type=mime_type, content_base64=content_base64
        )
        size_kb = _base64_decoded_size(content_base64) // 1024
        # The session keeps ONE image (contract.md §1 — a new upload replaces
        # it wholesale). Silence about that would let the operator believe two
        # sketches are attached, then approve a plan analysed against the
        # wrong one — so the replacement is said out loud.
        if replaced:
            event = notice_event(
                f"이미지 '{file_name}' 첨부됨 ({size_kb}KB) — 이전에 첨부한 이미지를 교체했습니다"
            )
        else:
            event = notice_event(f"이미지 '{file_name}' 첨부됨 ({size_kb}KB)")
        self._send(event)
        return event

    @property
    def song_audio(self) -> SongAudioUpload | None:
        """이 세션에 붙어 있는 곡 오디오 — 없으면 ``None``.

        읽기 전용 창이다. 거절된 프레임이 여기 흔적을 남기지 않는다는 것을
        시험이 이 창으로 확인한다(validate-before-store).
        """
        return self._song_audio

    def upload_song_audio(self, file_name: str, mime_type: str, content_base64: str) -> dict:
        """곡 오디오 한 개를 세션에 담는다 — 보관만 한다 (REQ-MUSICSYNC-013).

        ``upload_layout_image`` 와 같은 형태다: 담기만 하고 지시문을 부르지
        않는다. 업로드 순간에 분석을 돌리면, 운영자가 무엇을 할지 말하기도 전에
        수 초를 태운다. 분석은 :meth:`analyse_song_audio` 가 맡는다.

        와이어 검증(확장자·MIME·base64·64 MiB 상한 — 분할 전송이면 조립 검증까지)은
        ``parse_client_message`` 에서
        이미 끝났다 — 여기 닿은 메시지는 이미 받아들여진 것이다.

        교체를 소리 내어 말하는 이유는 ``upload_layout_image`` 와 같다: 침묵하면
        운영자가 두 곡이 붙어 있다고 믿은 채 엉뚱한 곡으로 만든 계획을 승인할 수
        있다.
        """
        data = base64.b64decode(content_base64, validate=True)
        replaced = self._song_audio is not None
        # SPEC-COPILOT-SONGCONFIRM-001 (REQ-SONGCONFIRM-005) — 확정 기록은 그 곡의
        # 것이다. 다른 곡이 올라오면 기록은 무효고, 기록이 **있었을 때만** 그 사실을
        # 한 문장으로 말한다. ``_song_bpm`` 은 손대지 않는다(plan.md §C D2-b).
        invalidated = self._song_analysis is not None
        self._song_analysis = None
        self._song_audio = SongAudioUpload(
            file_name=file_name,
            mime_type=mime_type,
            content_base64=content_base64,
            sha256=hashlib.sha256(data).hexdigest(),
            byte_length=len(data),
        )
        audio = self._song_audio
        text = f"'{file_name}' 첨부됨 — 오디오 · sha256 {audio.sha256} · {audio.byte_length}바이트"
        if replaced:
            text = text + " (이전에 첨부한 오디오를 교체했습니다)"
        text = text + ". 아직 분석한 것은 없습니다 — 무엇을 할지 말씀해 주세요."
        if invalidated:
            text = text + " 이전 분석 확정은 무효가 됐습니다 — 이 곡은 다시 분석해 주세요."
        return self._notify(text)

    def analyse_song_audio(
        self,
        *,
        sheet_bpm: object = None,
        fx_rate: float | None = None,
        beats_per_cycle: float | None = None,
    ) -> dict:
        """붙어 있는 곡을 재고, **사람에게 확인받고**, BPM 정본을 정한다.

        경로 위의 순서가 곧 이 SPEC 의 규율이다 — 측정은 DSP 가, 제안은 카드가,
        확정은 사람이 한다(REQ-MUSICSYNC-009 · REQ-MUSICSYNC-015). 확인 카드를
        건너뛰는 분기는 없다: 분석이 실패해도 **같은 카드**가 수동 BPM 입력으로
        서고(plan.md §C 결정 1 폴백), 카드를 못 띄우면 확정은 일어나지 않는다.

        ``sheet_bpm``\\ 은 호출자가 넘긴다 — 임포터가 읽은 ``HEAD.BPM`` 문자열을
        그대로 받아도 되고(``120 (고정)``), 없으면 ``None``. ``fx_rate`` 는
        **대조 전용**이며 어느 분기에서도 채택되지 않는다(plan.md §C 결정 3).

        콘솔 접촉: 0건. 이 메서드는 게이트도 실행 포트도 부르지 않는다.
        """
        audio = self._song_audio
        if audio is None:
            return self._notify("붙어 있는 곡 오디오가 없습니다 — 먼저 오디오를 첨부해 주세요.")

        outcome = analyze(base64.b64decode(audio.content_base64, validate=True))
        if isinstance(outcome, AnalysisResult):
            proposals = tuple(
                SongSectionProposal(
                    start_ms=candidate.start_ms,
                    end_ms=candidate.end_ms,
                    d_level=candidate.d_level,
                )
                for candidate in outcome.d_candidates
            )
            measured_bpm: float | None = outcome.bpm
            confidence: float | None = outcome.bpm_confidence
            fallback_reason: str | None = None
        else:
            proposals, measured_bpm, confidence = (), None, None
            fallback_reason = outcome.reason

        parsed_sheet_bpm = parse_sheet_bpm(sheet_bpm)
        card = build_song_confirmation_card(
            proposals=proposals,
            measured_bpm=measured_bpm,
            bpm_confidence=confidence,
            sheet_bpm=parsed_sheet_bpm,
            fallback_reason=fallback_reason,
        )
        if self._question_channel is None:
            # 볼 사람이 없는 카드는 카드가 아니다. 확정도 없다.
            answer = UNANSWERED
        else:
            answer = self._question_channel.ask(card, session_key=self._session_key)

        confirmed_bpm = parse_confirmed_bpm(answer, measured_bpm=measured_bpm)
        resolution = resolve_bpm(
            measured_bpm=confirmed_bpm,
            sheet_bpm=sheet_bpm,
            fx_rate=fx_rate,
            beats_per_cycle=beats_per_cycle,
        )
        self._song_bpm = resolution

        # SPEC-COPILOT-SONGCONFIRM-001 M1 (REQ-SONGCONFIRM-002/003) — 답이 미응답도
        # 자유입력 표식도 아니면 구간 판독을 붙여 확정 기록을 남긴다. 위의
        # ``_song_bpm`` 대입은 오늘 그대로이고, 기록은 그 **같은 객체**를 든다
        # (REQ-SONGCONFIRM-006). 같은 라벨을 가진 제안은 판정을 함께 받으며 그
        # 사실을 ``label_shared`` 로 남긴다(plan.md §F W1).
        verdict = parse_confirmed_sections(answer, proposals=proposals)
        # t414 — 사람이 적어 넣은 BPM 이 측정값의 배수(2배·절반)면 마디 길이가 두 배로
        # 달라진다. 카드의 구간 경계는 측정 BPM 의 4마디 하한이 만든 것이므로
        # (``analyze._min_segment_ms``) 그 구간표는 정정된 BPM 의 것이 아니다. 여기서
        # 다시 계산하지는 않는다 — REQ-SONGCONFIRM-004 가 카드에 없던 구간을 만드는 것을
        # 금지한다. 그래서 REQ-SONGCONFIRM-005 와 같은 문법으로 **확정을 무효로 하고
        # 소리 내어 말한다**: 침묵하면 절반 BPM 에 2마디짜리 구간표가 붙은 계획을
        # 사람이 승인한 줄 모른 채 쓴다.
        bpm_octave_corrected = is_bpm_octave_apart(confirmed_bpm, measured_bpm)
        if bpm_octave_corrected:
            verdict = None
        record: ConfirmedSongAnalysis | None = None
        if verdict is not None:
            labels = [section_label(proposal) for proposal in proposals]
            record = ConfirmedSongAnalysis(
                source_sha256=audio.sha256,
                source_file_name=audio.file_name,
                confirmed_at=datetime.now(UTC).isoformat(),
                bpm=resolution,
                sections=tuple(
                    ConfirmedSongSection(
                        index=index,
                        label=label,
                        start_ms=proposal.start_ms,
                        end_ms=proposal.end_ms,
                        d_level=proposal.d_level,
                        selected=selected,
                        label_shared=labels.count(label) > 1,
                    )
                    for index, (proposal, label, selected) in enumerate(
                        zip(proposals, labels, verdict, strict=True)
                    )
                ),
            )
        # 미응답 재분석이면 이전 기록도 내려놓는다 — 남겨 두면 그 기록의 ``bpm`` 이
        # 방금 갈아 끼운 ``_song_bpm`` 과 다른 객체가 되어 REQ-006 이 깨진다.
        self._song_analysis = record

        if resolution.bpm is None:
            lines = [f"BPM 은 확정되지 않았습니다 — 기본값 {DEFAULT_BPM:g} 로 남습니다."]
        else:
            lines = [f"BPM {resolution.bpm:g} 로 확정했습니다 ({resolution.source})."]
        lines.append(resolution.reason)
        # 어긋남은 채택 여부와 **무관하게** 항상 말한다(REQ-MUSICSYNC-017).
        lines.extend(resolution.mismatches)
        if fallback_reason:
            lines.append(fallback_reason)
        if bpm_octave_corrected:
            lines.append(
                f"측정 BPM {measured_bpm:g} 의 배수로 고쳐 주셨으므로 마디 길이가 달라집니다 — "
                "카드에 있던 구간 확정은 무효입니다. 이 곡은 다시 분석해 주세요."
            )
        # SPEC-COPILOT-SONGCONFIRM-001 M2 (REQ-SONGCONFIRM-013) — 기록이 생겼을 때만
        # 구간 결과와 다음 단계를 덧붙인다. 기록이 없는 갈래의 고지는 오늘 그대로다.
        if record is not None:
            lines.append(f"구간 {len(record.accepted)}건 채택 · {record.dropped_count}건 제외.")
            shared = sum(1 for section in record.sections if section.label_shared)
            if shared:
                lines.append(f"같은 라벨을 가진 구간 {shared}건은 함께 판정했습니다.")
            lines.append(
                "이 곡의 큐 리스트를 만들려면 타임코드 번호와 함께 말씀해 주세요 — "
                "확정한 구간을 그대로 씁니다."
            )
        return self._notify(" ".join(lines))

    @property
    def song_bpm(self) -> BpmResolution | None:
        """가장 최근 확정된 BPM 해소 결과 — 아직 없으면 ``None``."""
        return self._song_bpm

    @property
    def song_analysis(self) -> ConfirmedSongAnalysis | None:
        """사람이 확인한 곡 분석의 불변 기록 — 없으면 ``None`` (REQ-SONGCONFIRM-006).

        있을 때 ``song_analysis.bpm is song_bpm`` 이다 — 정본은 하나다.
        """
        return self._song_analysis

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
        multi: bool = False,
    ) -> str | None:
        """Ask the operator ONE question through the interactive card channel.

        This is how a direct handler collects a missing decision WITHOUT the
        wall-of-prose failure: the UI renders ``options`` as clickable buttons
        and always offers a free-text box, and the worker thread blocks here
        until exactly one answer returns — so a handler that needs several
        decisions calls this once per decision and the cards appear one at a
        time, never as a single unanswerable message.

        ``multi=True`` widens the SHAPE of that one answer, not the number of
        cards: the UI renders checkboxes plus a 「확인」 button and returns the
        chosen labels joined by ``", "``. Use it when the question is genuinely
        "which of these apply" (several preset families named in one sentence)
        rather than "which one" — a single-select card there receives one family
        and silently drops the rest.

        Returns the answer, or ``None`` when no UI is attached or the question
        went unanswered (timeout / disconnect) — the caller then falls back to
        a plain-text prompt instead of hanging.
        """
        if self._question_channel is None:
            return None
        answer = self._question_channel.ask(
            QuestionRequest(prompt=prompt, why=why, steps=steps, options=options, multi=multi)
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
        record = self._song_analysis
        if record is not None:
            # SPEC-COPILOT-SONGCONFIRM-001 M2 (REQ-SONGCONFIRM-007/008) — 확정 기록은
            # **이 통로**로만 모델에 닿는다(둘째 통로 없음). BPM 은 ``song_bpm``
            # 프로퍼티에서 읽는다: 기록의 ``bpm`` 과 같은 객체이고(REQ-006) 정본은
            # 그 프로퍼티 하나다 — 여기가 그 프로퍼티의 생산 판독자다. 채택 구간은
            # 상한 없이 전부 싣는다 — 잘라 내면 모델이 모르는 구간이 생기고 그것이
            # 이 SPEC 이 막는 결함이다(plan.md §F W3).
            bpm = self.song_bpm
            tempo = (
                "BPM not confirmed"
                if bpm is None or bpm.bpm is None
                else f"BPM {bpm.bpm:g} ({bpm.source})"
            )
            accepted = ", ".join(f"#{s.index} {s.label}" for s in record.accepted) or "none"
            notes.append(
                "Session context — the operator confirmed the song analysis of "
                f"'{record.source_file_name}' (sha256 {record.source_sha256[:8]}): {tempo}; "
                f"accepted sections ({len(record.accepted)}): {accepted}; "
                f"dropped {record.dropped_count}. When the operator asks for this song's "
                "cue list, call prepare_songcue WITHOUT the 'sections' argument so the "
                "confirmed sections are used as-is (the result reports sections_source = "
                "confirmed_analysis). Still obtain timecode_number from the operator — "
                "never choose it yourself."
            )
        guidance = layout_terms_guidance(text)
        if guidance:
            notes.append(guidance)
        return "\n\n".join(notes) or None

    def _report_error(self, exc: Exception) -> dict:
        kind, message = classify_exception(exc)
        raw_detail = getattr(exc, "raw_detail", None) or repr(exc)
        provider_name = getattr(exc, "provider", "")
        # 카드 t318 — 선언이 배선을 못 지난 사고를 `provider_error` 로 적으면
        # 감사 로그가 프로바이더 탓을 한다. 남는 이름이 곧 진단이라 갈라 적는다.
        event_name = (
            "write_gate_declaration_error"
            if isinstance(exc, WriteGateDeclarationError)
            else "provider_error"
        )
        self._audit.record(
            {
                "event": event_name,
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
        # 카드 t277 — 도구가 조용히 건너뛴 일은 **명령 표 뒤**에 붙는다. 앞에 두면
        # 「모두 실행했습니다」가 고지를 반박하는 것처럼 읽힌다: 순서대로 읽으면
        # 「보낸 것은 다 됐다, 다만 보내지 않은 것이 있다」가 되어 둘 다 참이다.
        # 건너뜀이 없는 회차에서는 비어 있어 이 줄 이전과 문면이 같다.
        parts.extend(result.notices)
        return " ".join(parts)
