"""WebSocket protocol v1 (M5 — REQ-MVP-020/021/022 wire contract).

Versioned message schema between the FastAPI WebSocket server and its clients
(the React UI and the M6 measurement harness). The full contract is documented
in ``server/web/PROTOCOL.md``; this module is the executable half: strict
client-message validation plus one builder per server event type.

Client messages that fail validation raise :class:`ProtocolError` and never
reach the orchestrator or the safety gate.
"""

from __future__ import annotations

import base64
import binascii
import json
import math

from server.deploy.review import ReviewRequest
from server.safety.approval import ApprovalRequest
from server.web.question import QuestionRequest

PROTOCOL_VERSION = 1

VECTORWORKS_UPLOAD_EXTENSIONS = (".csv", ".txt", ".xlsx", ".mvr")
MAX_VECTORWORKS_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_VECTORWORKS_UPLOAD_BASE64_LENGTH = ((MAX_VECTORWORKS_UPLOAD_BYTES + 2) // 3) * 4

# SPEC-COPILOT-IMGLAYOUT-001 M1 — the layout-sketch attachment channel. Same
# validate-before-store shape as the Vectorworks export above: an unlisted MIME
# type or an oversized payload never reaches session storage.
LAYOUT_IMAGE_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")
MAX_LAYOUT_IMAGE_BYTES = 5 * 1024 * 1024
MAX_LAYOUT_IMAGE_BASE64_LENGTH = ((MAX_LAYOUT_IMAGE_BYTES + 2) // 3) * 4

# SPEC-COPILOT-MUSICSYNC-001 M2 — 곡 오디오 첨부 채널 (REQ-MUSICSYNC-013/014).
# 위 둘과 같은 validate-before-store 형태이고, **전송 수단은 새로 만들지
# 않는다**: 오늘의 로컬 WebSocket 위 base64 그대로다. Tauri capability 의
# 「no http, no websocket, no upload」 방어선(AC-DEPLOY-027 Layer 3)을 오디오
# 한 개를 받자고 뚫지 않는다.
#
# 첨부 라우터(``vectorworks_export_upload``)로 보내지 않는 이유는 판별기가
# **CSV 헤더를 읽어서** 종류를 정하기 때문이다(``server/sheets/registry.py``) —
# 오디오 바이트에 그 판별기를 걸면 ``unknown_sheet_kind`` 로 떨어진다.
SONG_AUDIO_UPLOAD_EXTENSIONS = (".wav", ".flac", ".mp3", ".m4a")
SONG_AUDIO_MIME_TYPES = (
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/flac",
    "audio/x-flac",
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
)
# 실효 상한은 **디코드된 원본 64 MiB 하나**다(REQ-MUSICSYNC-026). 아래 base64
# 문자열 길이 상한은 그 64 MiB 에서 파생된 값이지 별도 상한이 아니다 — 두 개의
# 상한이 있는 것처럼 읽히면 나중에 한쪽만 고쳐진다. 2026-09-14 전에는 8 MiB 였고
# 감독 곡 31.5MB 가 어느 경로로도 안 올라갔다.
MAX_SONG_AUDIO_BYTES = 64 * 1024 * 1024
MAX_SONG_AUDIO_BASE64_LENGTH = ((MAX_SONG_AUDIO_BYTES + 2) // 3) * 4
_SONG_AUDIO_CAP_PHRASE = (
    f"상한 {MAX_SONG_AUDIO_BYTES // (1024 * 1024)} MiB({MAX_SONG_AUDIO_BYTES}바이트)"
)

# 분할 전송의 조각 하나 상한(REQ-MUSICSYNC-027). 상한을 64 MiB 로 올려도 **한
# 프레임**으로는 못 보낸다 — ``server/web/serve.py`` 의 ``uvicorn.run`` 이
# ``ws_max_size`` 를 주지 않아 기본 16777216(16 MiB)이 프레임 천장이고, 31.5MB 곡의
# base64 는 약 42MB 다. 조각 base64 4 MiB 는 JSON 으로 감싸도 그 천장 안에 넉넉히 든다.
MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH = 4 * 1024 * 1024

# The show-control panel's client messages (SPEC-COPILOT-SHOWUI-001 M1). Like
# the M7 "review_decision" extension before it this is ADDITIVE: the protocol
# version stays 1 and every type below is registered on BOTH allowlists — here
# and in ``ui/src/protocol.ts`` — because a type present on only one side goes
# silently missing on the client and loudly wrong on the server
# (REQ-SHOWUI-014).
PANEL_CLIENT_MESSAGE_TYPES = (
    "panel_execute",
    "panel_stop",
    # T-H5 (coordinator directive, 2026-08-02) — the closed Playback verb
    # quartet widens to include step-back and jump-to-cue (server/web/
    # panel.py's PANEL_VERBS). "panel_back" carries the SAME (target_kind,
    # target) shape as panel_execute/panel_stop; "panel_goto" additionally
    # carries the destination cue number.
    "panel_back",
    "panel_goto",
    "panel_pin",
    "panel_unpin",
    "panel_catalog_request",
)

# The console-info dashboard's client message (SPEC-COPILOT-DASHUI-001 M1).
# Additive on the panel family's terms: v stays 1, registered on BOTH
# allowlists in the same change (REQ-DASHUI-006 / AC-DASHUI-001). Payload-free
# — sent on connect and on manual refresh, never on a timer (REQ-DASHUI-021).
DASH_CLIENT_MESSAGE_TYPES = ("dash_catalog_request",)

# The live cue-progress monitor's client message (T-C, wave 2 — ad-hoc
# contract, no SPEC on file). Additive on the same terms as the dash/panel
# families above: v stays 1, registered on both allowlists here and in
# ``ui/src/protocol.ts``. Payload-free — the client asks for a fresh snapshot,
# there is nothing client-supplied to validate.
CUE_MONITOR_CLIENT_MESSAGE_TYPES = ("cue_monitor_request",)

# Refresh survival (2026-08-13): the client persists the visible transcript in
# localStorage; on (re)connect it reinjects that transcript so the model's
# cross-turn memory continues across a page refresh. Bounds mirror the
# session's own rolling window (server/web/session.py HISTORY_MAX_MESSAGES).
HISTORY_RESTORE_MAX_MESSAGES = 16
HISTORY_RESTORE_MAX_TEXT_CHARS = 4000
HISTORY_RESTORE_ROLES = ("user", "assistant")

# Closed set of client -> server message types. "review_decision" is the M7
# additive extension (deploy review) — protocol version stays 1.
CLIENT_MESSAGE_TYPES = (
    "chat",
    "vectorworks_export_upload",
    # SPEC-COPILOT-IMGLAYOUT-001 M1 — the layout-sketch attachment channel.
    "layout_image_upload",
    # SPEC-COPILOT-MUSICSYNC-001 M2 — 곡 오디오 첨부 채널. 위 둘과 같은 규약:
    # v 는 1 그대로이고, ``ui/src/protocol.ts`` 의 허용 목록에도 **같은 변경에서**
    # 등록한다. 한쪽에만 있는 타입은 클라이언트에서 조용히 사라지고 서버에서
    # 시끄럽게 틀린다.
    "song_audio_upload",
    # REQ-MUSICSYNC-027 — 한 프레임에 안 담기는 곡의 분할 전송. 조립은 연결 하나에
    # 하나인 :class:`SongAudioAssembly` 가 하고, ``end`` 가 검증을 통과해야만 위
    # ``song_audio_upload`` 와 같은 보관 경로로 넘어간다.
    "song_audio_upload_begin",
    "song_audio_upload_chunk",
    "song_audio_upload_end",
    # SPEC-COPILOT-MUSICSYNC-001 M2 후속 — 「지금 재라」 요청. 업로드 프레임은
    # 바이트를 담고 멈추므로(REQ-MUSICSYNC-013 은 보관까지다), 분석·확인 카드·
    # BPM 확정(REQ-MUSICSYNC-015)을 **부르는 것**이 따로 필요하다. 이 타입이
    # 없으면 ``ChatSession.analyse_song_audio`` 는 시험만이 부르는 죽은 경로다.
    "song_audio_analyse",
    # 카드 t647(SPEC-LDBARMAP-002 M3) — 첨부된 곡 오디오로 마디 지도를 만들어 달라는 요청.
    # 위 ``song_audio_analyse`` 와 달리 BPM 확정 계약에 닿지 않는다. 오프셋은 사람이 귀로
    # 정한 값을 프레임이 싣는다(필수, 기본값 없음). ``ui/src/protocol.ts`` 는 UI 카드의 몫이다.
    "bar_map_analyse",
    "approval_decision",
    "review_decision",
    # [round24 후속] 모델이 되묻고 사용자가 답하는 통로. 승인·검토와 달리
    # 실패가 「거부」가 아니라 **미응답**이다 — 없는 답을 지어내지 않게 하는 것이 목적.
    "question_answer",
    # t281 — 큐시트 초안 되돌리기/다시하기. 초안만 움직이고 콘솔·라이브러리에는
    # 닿지 않는다. 페이로드가 없다 — 무엇을 되돌릴지는 서버의 초안 이력이 안다.
    "timeline_draft_undo",
    "timeline_draft_redo",
    "lock",
    "status_request",
    # 새로고침 생존: 복원된 화면 기록을 새 세션에 재주입(위 상수 참조).
    "history_restore",
    # 카드 t551(SPEC-LDBEAT-001 M3) — 박자 격자 편집 세 길의 전용 채널.
    # 채팅(`"chat"`) 디스패치 체인과 분리된 별도 메시지 타입이다 —
    # `session.beat_grid_edit`/`beat_grid_suggest`/`beat_grid_suggestion_apply`
    # 가 직접 받는다(AC-LDBEAT-005).
    "beat_grid_edit",
    "beat_grid_suggest",
    "beat_grid_suggestion_apply",
    # 카드 t551 후속(지시 1항, mockup `aNo` 핸들러) — 제안 거절. 적용과
    # 같은 모양(suggestion_id 하나)이지만 편집을 부르지 않는다.
    "beat_grid_suggestion_reject",
    # SPEC-LDARRANGE-001 두 번째 묶음 — 자동 배치 초안(한 단위). 제안은 페이로드 없이
    # 요청하고, 「적용」·「거절」은 서버가 준 draft_id 하나만 되돌려 보낸다.
    "beat_grid_draft_propose",
    "beat_grid_draft_apply",
    "beat_grid_draft_reject",
    # 카드 t551 후속(지시 1항) — 프리셋 서랍 열기 요청. 페이로드 없음(현재
    # 곡의 격자 사용처 집계는 서버가 안다, dash_catalog_request와 같은 모양).
    "beat_grid_drawer_request",
    # 카드 t589(REQ-LDBEAT-015(h)) — "+ 새 프리셋 만들기" 다이얼로그. 이름·
    # 설명을 받아 서버가 번호를 배정한다(`beat_grid_edit`과 같은 길로,
    # 새 콘솔 쓰기 경로는 만들지 않는다) — AC-LDBEAT-005.
    "beat_grid_new_preset",
    # 반영 준비 — 상단 바 타임코드 번호 입력. 콘솔에 쓰지 않는다(초안·보관함에만 적는다).
    "beat_grid_timecode_set",
    # 카드 t563(SPEC-LDBEAT-001 M4, REQ-LDBEAT-011~013/017) — 상단 바
    # 콘솔 버튼 셋. `beat_grid_edit` 과 달리 이 셋은 콘솔에 **쓴다**
    # (run_commands -> 기존 안전 게이트) — 새 무승인 경로를 만들지 않는다.
    "beat_grid_apply",
    "beat_grid_preview",
    "beat_grid_preview_off",
    # 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」 재생·정지. 위 미리보기와 같은
    # 게이트 경로(세션 1회 승인)를 탄다. 페이로드 없음(타임코드 번호는 서버의 소유
    # 기록에 있다).
    "beat_grid_console_play",
    "beat_grid_console_stop",
    # 카드 t565 — 2D 무대 판독 요청. 페이로드 없음(곡 트랙 이름과 패치·그룹
    # 경로는 서버가 안다). 콘솔 읽기만 한다.
    "beat_grid_stage_request",
    # 카드 t571(REQ-LDBEAT-024(c) 후속) — 런북 화면이 열릴 때(세션에 첨부가
    # 없을 때) 이 곡에 저장된 오디오 링크를 요청한다. 페이로드 없음 — 지금
    # 곡이 무엇인지는 서버의 ``song_timeline_store`` 가 이미 안다.
    "song_audio_link_request",
    *PANEL_CLIENT_MESSAGE_TYPES,
    *DASH_CLIENT_MESSAGE_TYPES,
    *CUE_MONITOR_CLIENT_MESSAGE_TYPES,
)

# The panel messages that address ONE console object, and therefore carry the
# (target_kind, target) pair the parser validates before anything downstream
# can build a command bundle out of it. "panel_goto" is NOT here — it shares
# the (target_kind, target) shape but carries an ADDITIONAL "cue" field, so it
# gets its own parsing branch below rather than silently accepting an extra
# field this tuple's branch never checks.
PANEL_TARGETED_MESSAGE_TYPES = ("panel_execute", "panel_stop", "panel_back", "panel_unpin")

# The tile's type badge — design.md §4 (LOOK / FX / SEQ), plus the additive
# MACRO badge (SPEC-COPILOT-DASHUI-001 REQ-DASHUI-012): without it the catalog
# route would stamp a macro tile with the "sequence" badge (panel.py
# ``_CATALOG_ITEM_KIND``) — the exact mis-badge plan.md D4 guards against.
PANEL_ITEM_KINDS = ("look", "effect", "sequence", "macro")

# @MX:ANCHOR: [AUTO] the closed set of console object classes a panel tile may
# address. Consumed by the client-message parser, the item constructor, and
# (from M2) the catalog builder and the pin store.
# @MX:REASON: REQ-SHOWUI-003 — a fixture's `no` is its patch SLOT, which is not
# its fixture id; only sequences, executors and macros are objects whose `no` is
# the address the console fires ("macro" is the SPEC-COPILOT-DASHUI-001
# REQ-DASHUI-012 additive entry: the rulebook-verified run form is
# ``Macro <no>``, 00_grammar.md:60). Admitting "fixtures" here would let the
# panel send `Go+ Fixture <slot>` and hit the wrong thing on stage.
PANEL_TARGET_KINDS = ("executor", "sequence", "macro")

# Where a tile came from: a chat-created look the user pinned (REQ-SHOWUI-004)
# or an object enumerated from the rig (REQ-SHOWUI-001).
PANEL_ITEM_SOURCES = ("pin", "auto")

# 카드 t589 — "beat_grid_new_preset.field"가 가리킬 수 있는 다섯 편집
# 다이얼로그(`ui/src/components/BeatGrid.tsx`의 다섯 셀렉트와 1:1). 이
# 문자열 자체는 `apply_beat_grid_edit`가 쓰는 칸 필드 이름(예:
# "position_preset_no")과는 다른 이름 공간이다 — 서버의
# `ChatSession.beat_grid_new_preset`이 이 값을 보고 칸 필드로 번역한다.
BEAT_GRID_NEW_PRESET_FIELDS = ("dimmer_preset", "dimmer_effect", "position", "color", "effect")
# beat_grid_apply 의 mode — 기존 「⇪ 콘솔에 반영」(격자 초안 전체)과, 상단 바의
# 「필요한 프리셋 만들기」(연출 프리셋 계획 → 기존 승인 카드). 새 메시지 타입은 만들지 않는다.
BEAT_GRID_APPLY_MODES = ("apply", "preset_plan")

# Why a catalog section is incomplete. These mirror the rig-context reasons
# (``server/orchestrator/tools.py``) and stay DISTINCT on the wire: "this path
# does not exist in the loaded showfile" and "the console did not answer" ask
# the operator for different actions, and merging them is exactly how two dead
# rig paths survived a whole stage unnoticed (REQ-SHOWUI-002).
PANEL_SECTION_STATUSES = ("ok", "path_not_resolved", "console_unreachable")

# ``status.console_input`` — the console-OSC-input reachability verdict carried
# alongside ``health`` so the UI can name the RIGHT cause for a console_offline
# state. Three values, deliberately NOT two: collapsing "we could not tell" into
# "nothing is listening" is how a confidently-wrong message gets shown again.
CONSOLE_INPUT_LISTENING = "listening"  # the port is held — the console's OSC input is live
CONSOLE_INPUT_SILENT = "silent"  # the port is free — nothing is listening there
CONSOLE_INPUT_UNDETERMINED = "undetermined"  # not determined (remote console / not probed)


class ProtocolError(ValueError):
    """A client message violated the protocol (rejected before any handling)."""


class LayoutImageRejectedError(ProtocolError):
    """A ``layout_image_upload`` frame failed validation (MIME / base64 / size).

    A ProtocolError SUBCLASS, not a sibling: everything upstream that treats a
    bad frame as "reject before handling" keeps working unchanged. The app
    layer catches this class FIRST so the contract's named error kind
    ("layout_image_rejected" — contract.md §1, mirrored in
    ``ui/src/protocol.ts``) reaches the client instead of the anonymous
    kind="protocol"; the UI needs the name to tell "your image was refused,
    here is why" apart from "your frame was malformed".
    """


class SongAudioRejectedError(ProtocolError):
    """``song_audio_upload`` 프레임이 검증을 통과하지 못했다 (REQ-MUSICSYNC-014).

    :class:`LayoutImageRejectedError` 와 같은 이유로 ``ProtocolError`` 의
    **하위 클래스**다 — 상류에서 「처리 전 거절」로 다루는 모든 자리가 그대로
    동작한다. app 층이 이 클래스를 **먼저** 잡아 이름 붙은 종류
    (``song_audio_rejected``)로 내보내므로, UI 는 「파일이 거절됐다, 이유는
    이것이다」를 「프레임이 깨졌다」와 가를 수 있다.

    사유 문자열은 **한국어이고 상한 수치를 명시**한다(AC-MUSICSYNC-014). 그대로
    사용자에게 전달해도 안전하다 — 모든 문구는 여기서 쓴 고정 문장이고,
    끼워 넣는 값은 서버가 가진 허용 목록과 상한 숫자뿐이다. 사용자 페이로드는
    한 바이트도 문구에 들어가지 않는다.
    """


def _is_object_number(value: object) -> bool:
    """True when ``value`` is a console object number the panel may address.

    ``bool`` is checked FIRST because it is an ``int`` subclass in Python:
    without that guard ``True`` would sail through as object number 1 and the
    panel would fire at whatever sits in slot 1.

    Console pools are 1-based, so 0 addresses nothing — it is rejected in the
    same breath as a negative number rather than being handed downstream as a
    plausible-looking target.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _check_song_audio_name_and_mime(file_name: object, mime_type: object) -> None:
    """단일 프레임과 분할 ``begin`` 이 **같은** 파일 이름·MIME 규칙을 쓴다."""
    if not isinstance(file_name, str) or not file_name.strip():
        raise SongAudioRejectedError("오디오 파일 이름이 비어 있습니다.")
    if not file_name.lower().endswith(SONG_AUDIO_UPLOAD_EXTENSIONS):
        allowed = ", ".join(SONG_AUDIO_UPLOAD_EXTENSIONS)
        raise SongAudioRejectedError(
            f"오디오 파일의 확장자가 허용 목록에 없습니다 — 허용: {allowed}"
        )
    if mime_type not in SONG_AUDIO_MIME_TYPES:
        allowed = ", ".join(SONG_AUDIO_MIME_TYPES)
        raise SongAudioRejectedError(
            f"오디오 파일의 MIME 종류가 허용 목록에 없습니다 — 허용: {allowed}"
        )


class SongAudioAssembly:
    """분할 전송(begin · chunk · end)을 조립한다 — 연결 하나에 하나 (REQ-MUSICSYNC-027).

    조립 중인 부분 바이트는 **세션 첨부가 아니다.** :meth:`finish` 가 조각 수와
    총 길이를 대조해 통과해야만 ``song_audio_upload`` 와 같은 모양의 dict 를
    돌려주고, 호출자는 그것을 기존 보관 경로에 넘긴다. 어느 단계에서든 거절되면
    버퍼를 버린다 — 깨진 분할이 다음 전송에 섞이지 않게 한다.
    """

    def __init__(self) -> None:
        self._header: dict | None = None
        self._parts: list[bytes] = []
        self._received = 0

    @property
    def active(self) -> bool:
        return self._header is not None

    def _reset(self) -> None:
        self._header = None
        self._parts = []
        self._received = 0

    def _refuse(self, reason: str) -> SongAudioRejectedError:
        self._reset()
        return SongAudioRejectedError(reason)

    def begin(self, message: dict) -> None:
        # 새 begin 은 이전 미완성 전송을 버린다 — 운영자가 다른 곡을 고른 경우다.
        self._reset()
        self._header = message

    def add(self, message: dict) -> None:
        if self._header is None:
            raise self._refuse("오디오 조각이 시작 신호 없이 왔습니다 — 파일을 다시 올려 주세요.")
        if message["index"] != len(self._parts):
            expected = len(self._parts)
            raise self._refuse(
                f"오디오 조각 순서가 어긋났습니다 — {expected}번을 기다렸는데 "
                f"{message['index']}번이 왔습니다. 파일을 다시 올려 주세요."
            )
        payload = message["payload"]
        total = self._header["total_bytes"]
        if self._received + len(payload) > total:
            raise self._refuse(
                f"오디오 조각이 선언한 총 크기 {total}바이트를 넘었습니다 "
                "— 파일을 다시 올려 주세요."
            )
        self._parts.append(payload)
        self._received += len(payload)

    def finish(self) -> dict:
        header = self._header
        if header is None:
            raise self._refuse("오디오 전송 종료 신호가 시작 신호 없이 왔습니다.")
        if len(self._parts) != header["chunk_count"] or self._received != header["total_bytes"]:
            reason = (
                f"오디오 분할 전송이 완전하지 않습니다 — 조각 {len(self._parts)}/"
                f"{header['chunk_count']}개, {self._received}/{header['total_bytes']}바이트. "
                "파일을 다시 올려 주세요."
            )
            raise self._refuse(reason)
        data = b"".join(self._parts)
        self._reset()
        return {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_upload",
            "file_name": header["file_name"],
            "mime_type": header["mime_type"],
            "content_base64": base64.b64encode(data).decode("ascii"),
        }


def parse_client_message(raw: str) -> dict:
    """Parse + validate one client text frame; returns the normalized message."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"not valid JSON: {error}") from error
    if not isinstance(message, dict):
        raise ProtocolError("message must be a JSON object")
    if message.get("v") != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version: {message.get('v')!r}")
    message_type = message.get("type")
    if message_type not in CLIENT_MESSAGE_TYPES:
        raise ProtocolError(f"unknown message type: {message_type!r}")

    if message_type == "chat":
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProtocolError("chat.text must be a non-empty string")
        # t281 — 화면에서 고른 큐 번호를 요청에 실어 보낸다. 선택 필드이므로
        # 이 키가 없던 기존 클라이언트 프레임은 그대로 통과한다. bool 을 먼저
        # 막는다 — 파이썬에서 bool 은 int 의 하위형이라 True 가 큐 1로 샌다.
        selected = message.get("selected_cue")
        if selected is not None and (
            not isinstance(selected, int) or isinstance(selected, bool) or selected < 1
        ):
            raise ProtocolError("chat.selected_cue must be a positive integer when present")
        return {
            "v": PROTOCOL_VERSION,
            "type": "chat",
            "text": text,
            "selected_cue": selected,
        }

    if message_type == "beat_grid_edit":
        # 카드 t551 — 편집 경로 ①(changes)과 ②(sentence)는 정확히 하나만
        # 싣는다. 어느 쪽이든 bar/target 은 "changes" 경로에만 필수다
        # — "sentence" 경로는 문장 자체가 마디·트랙을 정한다(세션 쪽
        # 파서가 그 책임을 진다).
        has_changes = "changes" in message
        has_sentence = "sentence" in message
        if has_changes == has_sentence:
            raise ProtocolError("beat_grid_edit must carry exactly one of changes/sentence")
        if has_sentence:
            sentence = message.get("sentence")
            if not isinstance(sentence, str) or not sentence.strip():
                raise ProtocolError("beat_grid_edit.sentence must be a non-empty string")
            return {"v": PROTOCOL_VERSION, "type": "beat_grid_edit", "sentence": sentence}
        bar = message.get("bar")
        target = message.get("target")
        changes = message.get("changes")
        if not isinstance(bar, int) or isinstance(bar, bool):
            raise ProtocolError("beat_grid_edit.bar must be an integer")
        if not isinstance(target, str) or not target.strip():
            raise ProtocolError("beat_grid_edit.target must be a non-empty string")
        if not isinstance(changes, dict) or not changes:
            raise ProtocolError("beat_grid_edit.changes must be a non-empty object")
        return {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_edit",
            "bar": bar,
            "target": target,
            "changes": changes,
        }

    if message_type == "beat_grid_preview":
        # 카드 t563 — 상단 바 「▶ 이 마디 콘솔에서 보기」. `beat_grid_suggest`
        # 와 같은 모양(마디 하나)이지만 트랙(target)은 없다 — 가장 최근
        # 반영이 쓴 모든 트랙을 대상으로 한다(session.beat_grid_preview).
        bar = message.get("bar")
        if not isinstance(bar, int) or isinstance(bar, bool):
            raise ProtocolError("beat_grid_preview.bar must be an integer")
        return {"v": PROTOCOL_VERSION, "type": "beat_grid_preview", "bar": bar}

    if message_type == "beat_grid_suggest":
        bar = message.get("bar")
        target = message.get("target")
        if not isinstance(bar, int) or isinstance(bar, bool):
            raise ProtocolError("beat_grid_suggest.bar must be an integer")
        if not isinstance(target, str) or not target.strip():
            raise ProtocolError("beat_grid_suggest.target must be a non-empty string")
        return {"v": PROTOCOL_VERSION, "type": "beat_grid_suggest", "bar": bar, "target": target}

    if message_type == "beat_grid_timecode_set":
        # 반영 준비 — 상단 바 타임코드 번호 입력. 정수 모양만 가리고, 1 이상인지와 초안에
        # 적을지는 세션이 본다(거절 사유를 화면에 보이려고 여기서 막지 않는다).
        timecode_number = message.get("timecode_number")
        if not isinstance(timecode_number, int) or isinstance(timecode_number, bool):
            raise ProtocolError("beat_grid_timecode_set.timecode_number must be an integer")
        return {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_timecode_set",
            "timecode_number": timecode_number,
        }

    if message_type == "beat_grid_new_preset":
        # 카드 t589(REQ-LDBEAT-015(h)) — "+ 새 프리셋 만들기" 다이얼로그.
        # 번호는 여기서 짓지 않는다(서버의 `beat_grid_new_preset`이
        # `preset_pools.yaml`로 고른다) — 이 자리는 입력 모양만 본다.
        bar = message.get("bar")
        target = message.get("target")
        field = message.get("field")
        label = message.get("label")
        description = message.get("description")
        aim = message.get("aim")
        if not isinstance(bar, int) or isinstance(bar, bool):
            raise ProtocolError("beat_grid_new_preset.bar must be an integer")
        if not isinstance(target, str) or not target.strip():
            raise ProtocolError("beat_grid_new_preset.target must be a non-empty string")
        if field not in BEAT_GRID_NEW_PRESET_FIELDS:
            raise ProtocolError(
                f"beat_grid_new_preset.field must be one of {BEAT_GRID_NEW_PRESET_FIELDS}"
            )
        if not isinstance(label, str) or not label.strip():
            raise ProtocolError("beat_grid_new_preset.label must be a non-empty string")
        if not isinstance(description, str) or not description.strip():
            raise ProtocolError("beat_grid_new_preset.description must be a non-empty string")
        # 카드 t599(REQ-LDBEAT-015(i-3)) — "position"만 목표 좌표(x·y·z,
        # 미터, `server/spatial/pointing.py` 틀)를 **필수**로 받는다. 다른
        # 네 필드는 이 입력을 모른다 — 있으면 모양이 틀렸다고 거절한다
        # (엄격 유지, 조용히 무시하지 않는다).
        if field == "position":
            if not isinstance(aim, dict):
                raise ProtocolError("beat_grid_new_preset.aim is required when field is 'position'")
            for axis in ("x", "y", "z"):
                value = aim.get(axis)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProtocolError(f"beat_grid_new_preset.aim.{axis} must be a finite number")
                if not math.isfinite(value):
                    raise ProtocolError(f"beat_grid_new_preset.aim.{axis} must be a finite number")
        elif aim is not None:
            raise ProtocolError("beat_grid_new_preset.aim is only valid when field is 'position'")
        # 카드 t603 — "effect"만 효과 레시피(fx_id·주기 박/마디)를 **필수**로 받는다
        # (t593 `preset_fx_recipes` 모양). 다른 필드에 오면 거절한다(aim 과 같은 엄격함).
        fx = message.get("fx")
        if field == "effect":
            if not isinstance(fx, dict):
                raise ProtocolError("beat_grid_new_preset.fx is required when field is 'effect'")
            fx_id = fx.get("fx_id")
            unit = fx.get("period_unit")
            value = fx.get("period_value")
            if not isinstance(fx_id, str) or not fx_id.strip():
                raise ProtocolError("beat_grid_new_preset.fx.fx_id must be a non-empty string")
            if unit not in ("beat", "bar"):
                raise ProtocolError("beat_grid_new_preset.fx.period_unit must be 'beat' or 'bar'")
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ProtocolError(
                    "beat_grid_new_preset.fx.period_value must be a positive integer"
                )
        elif fx is not None:
            raise ProtocolError("beat_grid_new_preset.fx is only valid when field is 'effect'")
        # 카드 t594 — "color"만 목표 RGB(r·g·b, 0~100%)를 **필수**로 받는다
        # (t589 `preset_colors` 모양). 다른 필드에 오면 거절한다(aim 과 같은 엄격함).
        rgb = message.get("rgb")
        if field == "color":
            if not isinstance(rgb, dict):
                raise ProtocolError("beat_grid_new_preset.rgb is required when field is 'color'")
            for channel in ("r", "g", "b"):
                value = rgb.get(channel)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProtocolError(
                        f"beat_grid_new_preset.rgb.{channel} must be a finite number"
                    )
                if not math.isfinite(value) or not (0 <= value <= 100):
                    raise ProtocolError(
                        f"beat_grid_new_preset.rgb.{channel} must be a finite number in 0..100"
                    )
        elif rgb is not None:
            raise ProtocolError("beat_grid_new_preset.rgb is only valid when field is 'color'")
        parsed: dict[str, object] = {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_new_preset",
            "bar": bar,
            "target": target,
            "field": field,
            "label": label,
            "description": description,
        }
        if aim is not None:
            parsed["aim"] = aim
        if fx is not None:
            parsed["fx"] = {
                "fx_id": fx["fx_id"].strip(),
                "period_unit": fx["period_unit"],
                "period_value": fx["period_value"],
            }
        if rgb is not None:
            parsed["rgb"] = rgb
        return parsed

    if message_type in ("beat_grid_suggestion_apply", "beat_grid_suggestion_reject"):
        suggestion_id = message.get("suggestion_id")
        if not isinstance(suggestion_id, str) or not suggestion_id.strip():
            raise ProtocolError(f"{message_type}.suggestion_id must be a non-empty string")
        return {
            "v": PROTOCOL_VERSION,
            "type": message_type,
            "suggestion_id": suggestion_id,
        }

    if message_type in ("beat_grid_draft_apply", "beat_grid_draft_reject"):
        draft_id = message.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ProtocolError(f"{message_type}.draft_id must be a non-empty string")
        return {"v": PROTOCOL_VERSION, "type": message_type, "draft_id": draft_id}

    if message_type == "vectorworks_export_upload":
        file_name = message.get("file_name")
        content_base64 = message.get("content_base64")
        if not isinstance(file_name, str) or not file_name.strip():
            raise ProtocolError("vectorworks_export_upload.file_name must be a non-empty string")
        if not file_name.lower().endswith(VECTORWORKS_UPLOAD_EXTENSIONS):
            extensions = ", ".join(VECTORWORKS_UPLOAD_EXTENSIONS)
            raise ProtocolError(
                f"vectorworks_export_upload.file_name must end with one of: {extensions}"
            )
        if not isinstance(content_base64, str) or not content_base64:
            raise ProtocolError(
                "vectorworks_export_upload.content_base64 must be a non-empty base64 string"
            )
        if len(content_base64) > MAX_VECTORWORKS_UPLOAD_BASE64_LENGTH:
            raise ProtocolError("vectorworks_export_upload exceeds the 8 MiB limit")
        try:
            payload = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ProtocolError(
                f"vectorworks_export_upload.content_base64 is not valid base64: {error}"
            ) from error
        if not payload:
            raise ProtocolError("vectorworks_export_upload.content_base64 must not decode to empty")
        if len(payload) > MAX_VECTORWORKS_UPLOAD_BYTES:
            raise ProtocolError("vectorworks_export_upload exceeds the 8 MiB limit")
        return {
            "v": PROTOCOL_VERSION,
            "type": "vectorworks_export_upload",
            "file_name": file_name.strip(),
            "content_base64": content_base64,
        }

    if message_type == "layout_image_upload":
        file_name = message.get("file_name")
        mime_type = message.get("mime_type")
        content_base64 = message.get("content_base64")
        # Every rejection below is LayoutImageRejectedError (not the generic
        # ProtocolError) so the app layer can forward the reason under the
        # contract's kind="layout_image_rejected". The reason strings are safe
        # to surface: each one is a fixed phrase authored HERE — the only
        # interpolations are the server-owned MIME allowlist and binascii's
        # own diagnostic (which reports character counts, never payload bytes).
        if not isinstance(file_name, str) or not file_name.strip():
            raise LayoutImageRejectedError(
                "layout_image_upload.file_name must be a non-empty string"
            )
        if mime_type not in LAYOUT_IMAGE_MIME_TYPES:
            allowed = ", ".join(LAYOUT_IMAGE_MIME_TYPES)
            raise LayoutImageRejectedError(
                f"layout_image_upload.mime_type must be one of: {allowed}"
            )
        if not isinstance(content_base64, str) or not content_base64:
            raise LayoutImageRejectedError(
                "layout_image_upload.content_base64 must be a non-empty base64 string"
            )
        if len(content_base64) > MAX_LAYOUT_IMAGE_BASE64_LENGTH:
            raise LayoutImageRejectedError("layout_image_upload exceeds the 5 MiB limit")
        try:
            payload = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise LayoutImageRejectedError(
                f"layout_image_upload.content_base64 is not valid base64: {error}"
            ) from error
        if not payload:
            raise LayoutImageRejectedError(
                "layout_image_upload.content_base64 must not decode to empty"
            )
        if len(payload) > MAX_LAYOUT_IMAGE_BYTES:
            raise LayoutImageRejectedError("layout_image_upload exceeds the 5 MiB limit")
        return {
            "v": PROTOCOL_VERSION,
            "type": "layout_image_upload",
            "file_name": file_name.strip(),
            "mime_type": mime_type,
            "content_base64": content_base64,
        }

    if message_type == "song_audio_upload":
        file_name = message.get("file_name")
        mime_type = message.get("mime_type")
        content_base64 = message.get("content_base64")
        # validate-before-store: 아래 어느 줄에서 걸리든 세션 보관은 일어나지
        # 않는다. 상한 검사가 **두 번** 나오는 것은 중복이 아니다 — 앞의 것은
        # 디코드 비용 자체를 막는 문자열 길이 검사이고, 판정하는 것은 뒤의
        # 디코드된 바이트 검사다(``:218`` 의 기존 검사와 같은 형태).
        _check_song_audio_name_and_mime(file_name, mime_type)
        if not isinstance(content_base64, str) or not content_base64:
            raise SongAudioRejectedError("오디오 파일의 내용이 비어 있습니다.")
        if len(content_base64) > MAX_SONG_AUDIO_BASE64_LENGTH:
            raise SongAudioRejectedError(
                f"오디오 파일이 {_SONG_AUDIO_CAP_PHRASE}를 넘습니다 — 더 짧은 구간을 올려 주세요."
            )
        try:
            payload = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise SongAudioRejectedError(
                f"오디오 파일의 내용을 읽지 못했습니다 — base64 가 아닙니다: {error}"
            ) from error
        if not payload:
            raise SongAudioRejectedError("오디오 파일의 내용이 비어 있습니다.")
        if len(payload) > MAX_SONG_AUDIO_BYTES:
            raise SongAudioRejectedError(
                f"오디오 파일이 {_SONG_AUDIO_CAP_PHRASE}를 넘습니다 "
                f"— 받은 크기 {len(payload)}바이트. 더 짧은 구간을 올려 주세요."
            )
        return {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_upload",
            "file_name": file_name.strip(),
            "mime_type": mime_type,
            "content_base64": content_base64,
        }

    if message_type == "song_audio_upload_begin":
        file_name = message.get("file_name")
        mime_type = message.get("mime_type")
        _check_song_audio_name_and_mime(file_name, mime_type)
        total_bytes = message.get("total_bytes")
        chunk_count = message.get("chunk_count")
        if not _is_object_number(total_bytes) or not _is_object_number(chunk_count):
            raise SongAudioRejectedError(
                "오디오 분할 전송의 총 크기와 조각 수는 1 이상의 정수여야 합니다."
            )
        if total_bytes > MAX_SONG_AUDIO_BYTES:
            raise SongAudioRejectedError(
                f"오디오 파일이 {_SONG_AUDIO_CAP_PHRASE}를 넘습니다 "
                f"— 받은 크기 {total_bytes}바이트. 더 짧은 구간을 올려 주세요."
            )
        return {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_upload_begin",
            "file_name": file_name.strip(),
            "mime_type": mime_type,
            "total_bytes": total_bytes,
            "chunk_count": chunk_count,
        }

    if message_type == "song_audio_upload_chunk":
        index = message.get("index")
        content_base64 = message.get("content_base64")
        # bool 을 먼저 막는다 — 파이썬에서 bool 은 int 의 하위형이라 True 가 조각 1로 샌다.
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise SongAudioRejectedError("오디오 조각 번호는 0 이상의 정수여야 합니다.")
        if not isinstance(content_base64, str) or not content_base64:
            raise SongAudioRejectedError("오디오 조각의 내용이 비어 있습니다.")
        if len(content_base64) > MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH:
            raise SongAudioRejectedError(
                f"오디오 조각 하나가 상한 {MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH}자를 넘습니다."
            )
        try:
            payload = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise SongAudioRejectedError(
                f"오디오 조각의 내용을 읽지 못했습니다 — base64 가 아닙니다: {error}"
            ) from error
        return {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_upload_chunk",
            "index": index,
            "payload": payload,
        }

    if message_type == "song_audio_upload_end":
        return {"v": PROTOCOL_VERSION, "type": "song_audio_upload_end"}

    if message_type == "song_audio_analyse":
        # 페이로드가 없다 — 잴 곡은 이미 세션에 있다. 이 프레임이 나르는 것은
        # **대조용 부수 값** 셋뿐이고 셋 다 선택이다.
        #
        # ``sheet_bpm`` 은 임포터가 읽은 ``HEAD.BPM`` 문자열 **그대로** 받는다
        # (``120 (고정)``). 여기서 미리 숫자로 깎지 않는 이유는 깎는 자리를 하나로
        # 묶어 두기 위해서다 — 정본은 ``server.design.profile.parse_sheet_bpm``
        # 하나이고, 두 자리에서 깎으면 두 규칙이 조용히 갈라진다.
        #
        # ``bool`` 을 먼저 걸러 내는 것은 ``_is_object_number`` 가 세운 이유와
        # 같다: 파이썬에서 ``bool`` 은 ``int`` 의 하위형이라, 안 막으면 ``True``
        # 가 FX-Rate 1.0 으로 흘러 들어가 역산값을 조용히 오염시킨다.
        sheet_bpm = message.get("sheet_bpm")
        if sheet_bpm is not None and not isinstance(sheet_bpm, str):
            raise ProtocolError("song_audio_analyse.sheet_bpm must be a string or null")
        normalized_contrast: dict[str, float | None] = {}
        for field_name in ("fx_rate", "beats_per_cycle"):
            value = message.get(field_name)
            if value is None:
                normalized_contrast[field_name] = None
                continue
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ProtocolError(f"song_audio_analyse.{field_name} must be a number or null")
            normalized_contrast[field_name] = float(value)
        return {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_analyse",
            "sheet_bpm": sheet_bpm,
            **normalized_contrast,
        }

    if message_type == "bar_map_analyse":
        # 카드 t647(SPEC-LDBARMAP-002 M3, AC-LDBARENTRY-002) — 첫 박 오프셋은 필수이고 기본값이
        # 없다. 없거나 null 이거나 정수가 아니면 0 으로 채우지 않고 거절한다: 조용히 0 이 되면
        # 첫 박을 잘못 짚은 마디 지도가 아무 신호 없이 저장된다. ``bool`` 을 먼저 거른다 — 위
        # 분기와 같은 이유로 파이썬에서 ``bool`` 은 ``int`` 의 하위형이라 ``True`` 가 1 로 샌다.
        # 범위(0~3)는 여기서 재지 않는다 — 박 수는 세션이 한 곳에서 판정한다.
        first_beat_offset = message.get("first_beat_offset")
        if not isinstance(first_beat_offset, int) or isinstance(first_beat_offset, bool):
            raise ProtocolError("bar_map_analyse.first_beat_offset must be an integer")
        return {
            "v": PROTOCOL_VERSION,
            "type": "bar_map_analyse",
            "first_beat_offset": first_beat_offset,
        }

    if message_type == "question_answer":
        request_id = message.get("request_id")
        answer = message.get("answer")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("question_answer.request_id must be a non-empty string")
        if not isinstance(answer, str) or not answer.strip():
            raise ProtocolError("question_answer.answer must be a non-empty string")
        return {
            "v": PROTOCOL_VERSION,
            "type": "question_answer",
            "request_id": request_id,
            "answer": answer,
        }

    if message_type == "history_restore":
        raw_messages = message.get("messages")
        if not isinstance(raw_messages, list) or not raw_messages:
            raise ProtocolError("history_restore.messages must be a non-empty list")
        normalized: list[dict] = []
        # Only the newest window is admitted — the tail is what carries context,
        # and the session's own rolling window is the same size.
        for item in raw_messages[-HISTORY_RESTORE_MAX_MESSAGES:]:
            if not isinstance(item, dict):
                raise ProtocolError("history_restore.messages items must be objects")
            role = item.get("role")
            text = item.get("text")
            if role not in HISTORY_RESTORE_ROLES:
                raise ProtocolError("history_restore.role must be 'user' or 'assistant'")
            if not isinstance(text, str) or not text.strip():
                raise ProtocolError("history_restore.text must be a non-empty string")
            normalized.append({"role": role, "text": text[:HISTORY_RESTORE_MAX_TEXT_CHARS]})
        return {"v": PROTOCOL_VERSION, "type": "history_restore", "messages": normalized}

    if message_type in ("approval_decision", "review_decision"):
        request_id = message.get("request_id")
        approved = message.get("approved")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError(f"{message_type}.request_id must be a non-empty string")
        if not isinstance(approved, bool):
            raise ProtocolError(f"{message_type}.approved must be a boolean")
        return {
            "v": PROTOCOL_VERSION,
            "type": message_type,
            "request_id": request_id,
            "approved": approved,
        }

    if message_type == "lock":
        active = message.get("active")
        if not isinstance(active, bool):
            raise ProtocolError("lock.active must be a boolean")
        return {"v": PROTOCOL_VERSION, "type": "lock", "active": active}

    if message_type in PANEL_TARGETED_MESSAGE_TYPES:
        # REQ-SHOWUI-022: the target is client-controlled, so it is validated
        # HERE — at parse time, before any caller can exist. A malformed target
        # therefore cannot reach a command bundle and cannot reach
        # ``gate.screen()``; it is refused with the same ProtocolError as any
        # other malformed frame and answered with an error event.
        #
        # This is the parse-time half only. Whether the (kind, no) pair names an
        # object that actually EXISTS in the catalog or the pin store is a
        # membership question, and membership is checked against the panel
        # store — which M2 introduces.
        target = message.get("target")
        if not _is_object_number(target):
            raise ProtocolError(f"{message_type}.target must be a positive integer object number")
        target_kind = message.get("target_kind")
        if target_kind not in PANEL_TARGET_KINDS:
            raise ProtocolError(f"{message_type}.target_kind must be one of {PANEL_TARGET_KINDS}")
        return {
            "v": PROTOCOL_VERSION,
            "type": message_type,
            "target_kind": target_kind,
            "target": target,
        }

    if message_type == "panel_goto":
        # T-H5 — same target validation as PANEL_TARGETED_MESSAGE_TYPES above
        # (repeated rather than shared via that tuple, since this branch adds
        # a field the others don't have and never should), PLUS the
        # destination cue number. Parse-time validation proves ``cue`` is a
        # positive integer, not that the sequence actually carries it —
        # that membership question is the panel store's job (T-H5's
        # ``register_executor_cues``/``executor_has_cue``), exactly the same
        # division of labor as the target's own membership check.
        target = message.get("target")
        if not _is_object_number(target):
            raise ProtocolError("panel_goto.target must be a positive integer object number")
        target_kind = message.get("target_kind")
        if target_kind not in PANEL_TARGET_KINDS:
            raise ProtocolError(f"panel_goto.target_kind must be one of {PANEL_TARGET_KINDS}")
        cue = message.get("cue")
        if not _is_object_number(cue):
            raise ProtocolError("panel_goto.cue must be a positive integer cue number")
        return {
            "v": PROTOCOL_VERSION,
            "type": "panel_goto",
            "target_kind": target_kind,
            "target": target,
            "cue": cue,
        }

    if message_type == "beat_grid_apply":
        # 같은 「⇪」 길을 쓰되 mode 로 가른다. mode 가 없으면 기존 「콘솔에 반영」과 같다.
        mode = message.get("mode", "apply")
        if mode not in BEAT_GRID_APPLY_MODES:
            raise ProtocolError(f"beat_grid_apply.mode must be one of {BEAT_GRID_APPLY_MODES}")
        return {"v": PROTOCOL_VERSION, "type": "beat_grid_apply", "mode": mode}

    if message_type in (
        "panel_pin",
        "panel_catalog_request",
        "dash_catalog_request",
        "cue_monitor_request",
        # t281 — 초안 되돌리기/다시하기도 페이로드가 없다. 여기 등록하지 않으면
        # 아래 마지막 줄이 이들을 통째로 ``status_request`` 로 바꿔치기한다.
        "timeline_draft_undo",
        "timeline_draft_redo",
        # 카드 t551 후속(지시 1항) — 프리셋 서랍 열기도 페이로드가 없다
        # (현재 격자 사용처는 서버가 이미 안다).
        "beat_grid_drawer_request",
        # SPEC-LDARRANGE-001 두 번째 묶음 — 자동 배치 초안 요청도 페이로드가 없다
        # (마디 지도와 현재 격자 구성은 서버가 안다).
        "beat_grid_draft_propose",
        # 카드 t563 — 「콘솔에 반영」·「끄기」도 페이로드가 없다. 반영은
        # 지금 격자 초안 전체를 쓰고, 끄기는 가장 최근 반영의 모든
        # 시퀀스를 끈다 — 둘 다 번호를 서버가 쥐고 있어 클라이언트가
        # 보낼 것이 없다.
        "beat_grid_preview_off",
        # 카드 t578 — 「콘솔 같이」 재생·정지도 페이로드가 없다(번호는 소유 기록).
        "beat_grid_console_play",
        "beat_grid_console_stop",
        # 카드 t565 — 무대 판독 요청도 페이로드가 없다.
        "beat_grid_stage_request",
        # 카드 t571 — 곡 오디오 링크 요청도 페이로드가 없다(지금 곡은
        # 서버가 이미 안다).
        "song_audio_link_request",
    ):
        # Payload-free by design. The pin seed is the server's own
        # ``_last_created`` cross-turn memory (REQ-SHOWUI-004), and the
        # catalog/monitor requests ask for the whole (replace-semantics)
        # snapshot — so there is no client-supplied target here to get wrong
        # or to trust.
        return {"v": PROTOCOL_VERSION, "type": message_type}

    return {"v": PROTOCOL_VERSION, "type": "status_request"}


# -- server -> client event builders -------------------------------------------


def _event(event_type: str, **fields) -> dict:
    return {"v": PROTOCOL_VERSION, "type": event_type, **fields}


def chat_response_event(*, status: str, summary: str, text: str, commands: list[dict]) -> dict:
    """One instruction's final report (REQ-MVP-022 — Korean result reporting)."""
    return _event("chat_response", status=status, summary=summary, text=text, commands=commands)


def beat_grid_suggestion_event(
    *, suggestion_id: str, bar: int, target: str, changes: dict, rationale: str
) -> dict:
    """SPEC-LDBEAT-001 M3(카드 t551) — 박자 격자 편집 경로 ③(AI 제안)의
    보류 카드. ``changes``는 「적용」클릭이 그대로 ``beat_grid_suggestion_
    apply``에 되돌려 보낼 그 편집 요청이다(생성~적용 사이 상태 diff 0,
    결정④)."""
    return _event(
        "beat_grid_suggestion",
        suggestion_id=suggestion_id,
        bar=bar,
        target=target,
        changes=changes,
        rationale=rationale,
    )


def beat_grid_suggestion_consumed_event(*, suggestion_id: str) -> dict:
    """카드 t551 — ``approval_resolved``와 같은 짝 이벤트. 보류 카드가
    소비됐다(적용됐든, 모르는/만료된 id로 거절됐든)는 것을 UI에 알려
    보류 목록에서 지우게 한다. id가 애초에 없었어도(거절 경로) 보낸다 —
    UI 쪽 필터는 없는 id를 지우려 해도 안전한 no-op이다."""
    return _event("beat_grid_suggestion_consumed", suggestion_id=suggestion_id)


def beat_grid_draft_event(*, draft_id: str, draft: dict) -> dict:
    """SPEC-LDARRANGE-001 두 번째 묶음 — 자동 배치 초안 한 단위(보류). 화면은 이것을 제안
    카드로 보여 주고, 「적용」이나 「거절」 때 ``draft_id`` 하나만 되돌려 보낸다. 칸마다
    ``bar``와 ``label``만 싣는다. 구조화 필드는 적용할 때 서버가 정한다."""
    tracks = [
        {
            "group_name": track["group_name"],
            "group_no": track["group_no"],
            "group_no_confirmed": track["group_no_confirmed"],
            "layer_role": track["layer_role"],
            "cells": [{"bar": cue["bar"], "label": cue["label"]} for cue in track["cues"]],
        }
        for track in draft["tracks"]
    ]
    return _event(
        "beat_grid_draft",
        draft_id=draft_id,
        bar_range=dict(draft["bar_range"]),
        windows=[dict(window) for window in draft["windows"]],
        tracks=tracks,
    )


def beat_grid_draft_consumed_event(*, draft_id: str) -> dict:
    """SPEC-LDARRANGE-001 두 번째 묶음 — 보류 초안이 소비됐다(적용·거절 공통). 없던 id도 보낸다."""
    return _event("beat_grid_draft_consumed", draft_id=draft_id)


def beat_grid_send_status_event(
    *,
    pending_apply_count: int,
    last_action: str,
    ok: bool,
    reason: str | None = None,
    blocked_cells: list[dict],
    approval_vs_sent: dict | None = None,
    stale_tracks: list[str] | None = None,
    notices: list[str] | None = None,
) -> dict:
    """카드 t563(REQ-LDBEAT-011~013/017) — 상단 바 콘솔 버튼 셋
    (``beat_grid_apply``/``beat_grid_preview``/``beat_grid_preview_off``)과,
    대기 수 배지를 갱신시키는 ``beat_grid_edit`` 성공 때마다의 공용 상태.
    ``blocked_cells``는 ``{group_name, bar, reason}`` 전수 목록(에미터의
    "부분 적용 0건" 판정을 그대로 보여준다) — 거절 1건을 요약 문구로
    뭉개지 않는다. ``approval_vs_sent``는 반영(쓰기) 성공 때만 채워진다
    (미리보기/편집은 비교 대상인 "승인 파일"이 없다). ``stale_tracks``
    (카드 t572) — 소유권 레코드에는 있지만 이번 반영의 격자에는 없는
    트랙 이름 전수. 지워지지 않고 그대로 남아 있다는 뜻이다."""
    return _event(
        "beat_grid_send_status",
        pending_apply_count=pending_apply_count,
        last_action=last_action,
        ok=ok,
        reason=reason,
        blocked_cells=blocked_cells,
        approval_vs_sent=approval_vs_sent,
        stale_tracks=list(stale_tracks) if stale_tracks is not None else [],
        notices=list(notices) if notices is not None else [],
    )


def beat_grid_drawer_event(*, sections: list[dict]) -> dict:
    """카드 t551 후속(지시 1항) — mockup 프리셋 서랍(디머 1·위치 2·색 4)과
    같은 세 섹션. 내용은 `server.design.beat_grid_presets.
    build_preset_drawer`의 실제 콘솔 판독 결과다 — 데모 데이터 0건,
    못 읽은 풀은 ``unread: true``로 솔직하게 비어 있다."""
    return _event("beat_grid_drawer", sections=sections)


def beat_grid_stage_event(*, fixtures: list[dict], groups: list[dict], unread: list[str]) -> dict:
    """카드 t565(SPEC-LDBEAT-001 REQ-022) — 2D 무대 한 장. ``fixtures`` 는 패치
    좌표({fid,name,x,y,z}), ``groups`` 는 박자 격자 트랙과 이름이 같은 콘솔 그룹의
    소속({group_no,group_name,member_fids,complete}), ``unread`` 는 못 읽은 이유
    그대로다(`server.design.beat_grid_stage.read_beat_grid_stage`, 콘솔 읽기만)."""
    return _event("beat_grid_stage", fixtures=fixtures, groups=groups, unread=unread)


def song_audio_link_event(
    *,
    status: str,
    file_name: str | None = None,
    mime_type: str | None = None,
    content_base64: str | None = None,
    sha256: str | None = None,
    byte_length: int | None = None,
) -> dict:
    """카드 t571(REQ-LDBEAT-024(c) 후속) — 지금 곡에 저장된 오디오 링크
    (단일 프레임에 들어가는 경우) **또는** 그 상태만.

    ``status`` 는 ``"none"``(지금 곡을 모름, 또는 이 곡엔 저장된 링크가
    아예 없음) · ``"missing"``(링크는 있는데 파일이 없거나 해시가 안 맞음)
    · ``"found"``(있고 맞음) 셋 중 하나다. ``found`` 인데 base64 가 한
    프레임에 못 들어갈 만큼 크면 이 이벤트 대신 아래 분할 트리오
    (``song_audio_link_begin``/``_chunk``/``_end``)가 나간다 — REQ-
    MUSICSYNC-027 의 업로드 분할과 같은 이유를 반대 방향에 적용한 것이다.
    """
    return _event(
        "song_audio_link",
        status=status,
        file_name=file_name,
        mime_type=mime_type,
        content_base64=content_base64,
        sha256=sha256,
        byte_length=byte_length,
    )


def song_audio_link_begin_event(
    *,
    file_name: str,
    mime_type: str,
    sha256: str,
    byte_length: int,
    chunk_count: int,
) -> dict:
    """카드 t571 — 분할 전송 시작. ``status`` 는 항상 ``"found"`` — missing/
    none 은 내용이 없으므로 분할할 것도 없다(``song_audio_link_event`` 하나로
    족하다)."""
    return _event(
        "song_audio_link_begin",
        status="found",
        file_name=file_name,
        mime_type=mime_type,
        sha256=sha256,
        byte_length=byte_length,
        chunk_count=chunk_count,
    )


def song_audio_link_chunk_event(*, index: int, content_base64: str) -> dict:
    """카드 t571 — 분할 전송 조각 하나. ``song_audio_upload_chunk`` 와 같은 모양."""
    return _event("song_audio_link_chunk", index=index, content_base64=content_base64)


def song_audio_link_end_event() -> dict:
    """카드 t571 — 분할 전송 종료. 조립은 클라이언트 쪽(``protocol.ts``)이 한다."""
    return _event("song_audio_link_end")


def approval_request_event(*, request_id: str, request: ApprovalRequest) -> dict:
    """One pending approval bundle: commands + risk reasons + warnings (REQ-MVP-021)."""
    return _event(
        "approval_request",
        request_id=request_id,
        items=[
            {
                "command": item.command,
                "risk_reasons": list(item.risk_reasons),
                "warnings": list(item.warnings),
            }
            for item in request.items
        ],
        actions=["approve", "reject"],
    )


def execution_preview_event(*, preview: dict) -> dict:
    return _event("execution_preview", **preview)


def approval_resolved_event(*, request_id: str, approved: bool) -> dict:
    """The decision echo so the UI can retire the approval card."""
    return _event("approval_resolved", request_id=request_id, approved=approved)


def review_request_event(*, request_id: str, request: ReviewRequest) -> dict:
    """One pending deploy review (M7, REQ-MVP-019/027): everything the
    reviewer must see — name, bounded source preview, compile verdict, and
    the destructive-scan report with its best-effort caveat."""
    scan = request.scan
    return _event(
        "review_request",
        request_id=request_id,
        plugin_name=request.plugin_name,
        source_preview=request.source_preview,
        source_length=request.source_length,
        source_truncated=request.source_truncated,
        compile_ok=request.compile_ok,
        scan={
            "destructive": scan.destructive,
            "findings": [
                {
                    "line": finding.line,
                    "command": finding.command,
                    "kind": finding.kind,
                    "matched_entry": finding.matched_entry,
                    "reasons": list(finding.reasons),
                }
                for finding in scan.findings
            ],
            "dynamic_calls": [
                {"line": call.line, "snippet": call.snippet} for call in scan.dynamic_calls
            ],
            "caveat": scan.caveat,
        },
        actions=["approve", "reject"],
    )


def question_request_event(*, request_id: str, request: QuestionRequest) -> dict:
    """모델이 사용자에게 던지는 물음 하나 — 추측 대신 질문.

    ``options``가 비면 자유 입력, 차 있으면 선택지 + 자유 입력이다. 선택지가
    사용자의 실제 사정을 다 담지 못하는 경우가 실물에서 흔해 자유 입력을 항상 연다.
    """
    return _event("question_request", request_id=request_id, **request.to_dict())


def question_resolved_event(*, request_id: str, answer: str) -> dict:
    """답 반향 — UI가 질문 카드를 내린다."""
    return _event("question_resolved", request_id=request_id, answer=answer)


def review_resolved_event(*, request_id: str, approved: bool) -> dict:
    """The review decision echo so the UI can retire the review card."""
    return _event("review_resolved", request_id=request_id, approved=approved)


def status_event(
    *,
    health: str,
    live_lock: bool,
    executions_blocked: bool,
    console_input: str = CONSOLE_INPUT_UNDETERMINED,
    reply_port: int | None = None,
    receive_port: int | None = None,
) -> dict:
    """Gate-truth status surface (REQ-MVP-030/031 UI half + lock state).

    ``console_input``, ``reply_port`` and ``receive_port`` are ADDITIVE fields
    (protocol version stays 1, same call as the M7 ``review_decision``
    extension): purely informational diagnosis carriers with safe defaults, so a
    client that ignores them behaves exactly as before and a server that never
    diagnoses emits the pre-existing meaning. They NEVER alter ``health`` or
    ``executions_blocked`` — the gate's verdict is untouched; only the cause the
    UI names for it becomes accurate.

    ``reply_port``/``receive_port`` are the reply-port MISMATCH pair, and they
    appear together or not at all: a console reply was observed on
    ``reply_port`` while the app listens on ``receive_port``. Reporting both
    numbers, rather than silently switching to the observed one, is what keeps
    REQ-DEPLOY-026 intact — the operator decides which of the two moves.
    """
    return _event(
        "status",
        health=health,
        live_lock=live_lock,
        executions_blocked=executions_blocked,
        console_input=console_input,
        reply_port=reply_port,
        receive_port=receive_port,
    )


def proposal_event(*, commands: list[str], reasons: list[str]) -> dict:
    """A read-only proposal card produced under the live lock (REQ-MVP-016)."""
    return _event("proposal", commands=list(commands), reasons=list(reasons))


def error_event(*, message: str, kind: str = "") -> dict:
    """A Korean user-facing error — NEVER carries raw SDK text (REQ-MVP-044)."""
    return _event("error", message=message, kind=kind)


def busy_event(message: str) -> dict:
    """The session is already processing an instruction (one at a time)."""
    return _event("busy", message=message)


def notice_event(message: str) -> dict:
    """A standalone Korean notice (e.g. backup failure, REQ-MVP-034 UI half)."""
    return _event("notice", message=message)


def progress_event(*, phase: str, detail: str, seq: int) -> dict:
    """턴이 **도는 동안** 흘러나가는 한 줄 (진행 스트리밍).

    실측: 한 턴은 모델 호출 최대 24회 + 도구당 수백 콘솔 왕복이고, 그 사이
    화면에는 아무 프레임도 도착하지 않았다 — 종전에는 턴이 전부 끝난 뒤
    ``chat_response`` 하나뿐이었다. ``phase``\\ 는 ``model_call`` ·
    ``tool_start`` · ``tool_done``, ``detail``\\ 은 한국어 사용자 문구,
    ``seq``\\ 는 **턴 안에서만** 1부터 단조증가한다(턴 경계에서 되돌아간다).

    소멸성 상태다: 클라이언트는 마지막 한 줄만 들고 있다가 그 턴의 종결
    프레임(``chat_response``/``error``)에서 지운다 — 대화록에 쌓이지 않는다.
    """
    return _event("progress", phase=phase, detail=detail, seq=seq)


def answer_delta_event(*, delta: str, seq: int) -> dict:
    """답변 본문 조각 하나 (SPEC-COPILOT-STREAM-001).

    ``progress``\\ 가 *무엇을 하는 중인지*\\ 를 한 줄로 갈아끼운다면, 이것은
    *답 그 자체*\\ 를 도착하는 대로 이어 붙인다. 실측(2026-08-20): 좌표 판독
    턴에서 마지막 모델 호출이 6~10초를 쓰는데 그동안 화면에는 진행 한 줄만
    있었다.

    누적 채널이다 — 받는 쪽이 ``delta``\\ 를 순서대로 이어 붙이면 지금까지의
    본문이 된다. ``seq``\\ 는 턴 안에서 1부터 단조증가하므로 늦게 도착한
    조각이 앞선 상태를 되돌리지 못한다.

    **판정을 싣지 않는다.** 상태·명령 목록·요약은 여전히 ``chat_response``\\ 의
    몫이고, 이 채널이 통째로 유실돼도 답은 온전하다. 그래서 클라이언트는 턴
    종결 프레임에서 이 조각들을 버리고 ``chat_response``\\ 의 본문으로 갈아
    끼운다 — 두 벌을 남기면 같은 답이 두 번 보인다.
    """
    return _event("answer_delta", delta=delta, seq=seq)


# -- show-control panel (SPEC-COPILOT-SHOWUI-001 M1) ---------------------------


# @MX:ANCHOR: [AUTO] the panel tile's identity on the wire and in the pin store.
# @MX:REASON: REQ-SHOWUI-003 — pool numbers are non-contiguous, so "the Nth
# tile" and "object N" are different objects. Keying on the console's REAL `no`
# (never a list position) is what stops a rig with sequences at 2, 7, 41 from
# resolving tile #3 to a non-existent "Sequence 3". The `kind:no` shape also
# keeps Executor 41 and Sequence 41 apart, which a bare number cannot.
def panel_item_id(target_kind: str, target: int) -> str:
    """The stable tile key: ``"<target_kind>:<no>"`` (e.g. ``"executor:191"``)."""
    return f"{target_kind}:{target}"


def panel_item(
    *,
    kind: str,
    target_kind: str,
    target: int,
    name: str,
    source: str,
    appearance: str | None = None,
) -> dict:
    """One panel tile — the frozen item schema every later milestone builds on.

    | field         | meaning                                                  |
    |---------------|----------------------------------------------------------|
    | ``id``        | ``"<target_kind>:<no>"`` — derived, never a list position |
    | ``kind``      | the LOOK / FX / SEQ type badge (design.md §4)             |
    | ``target_kind``| the console object class the command addresses           |
    | ``target``    | the console's REAL object number                          |
    | ``name``      | the console name, verbatim                                |
    | ``appearance``| the appearance colour chip, or ``None``                   |
    | ``source``    | ``"pin"`` (chat-pinned) or ``"auto"`` (rig-enumerated)    |

    Every enum is closed and every violation raises — a tile that cannot be
    addressed correctly must not be constructed at all, because by the time it
    reaches a command bundle the wrong object is already on stage.
    """
    if kind not in PANEL_ITEM_KINDS:
        raise ValueError(f"panel item kind must be one of {PANEL_ITEM_KINDS}, got {kind!r}")
    if target_kind not in PANEL_TARGET_KINDS:
        raise ValueError(
            f"panel item target_kind must be one of {PANEL_TARGET_KINDS}, got {target_kind!r}"
        )
    if not _is_object_number(target):
        raise ValueError(f"panel item target must be a positive integer, got {target!r}")
    if source not in PANEL_ITEM_SOURCES:
        raise ValueError(f"panel item source must be one of {PANEL_ITEM_SOURCES}, got {source!r}")
    return {
        "id": panel_item_id(target_kind, target),
        "kind": kind,
        "target_kind": target_kind,
        "target": target,
        "name": name,
        "appearance": appearance,
        "source": source,
    }


def panel_section(
    *,
    name: str,
    status: str,
    truncated: bool = False,
    drilldown_capped: bool = False,
    contents_unavailable: bool = False,
) -> dict:
    """One catalog section's own account of how complete it is.

    A short tile list with no completeness signal is worse than no list at all:
    the operator would trust a rig they cannot fully see. The three flags mirror
    the rig-context ones (``server/orchestrator/tools.py``) and are carried all
    the way to the UI (REQ-SHOWUI-001):

    - ``truncated`` — the responder itself said the listing was cut short.
    - ``drilldown_capped`` — the per-call query budget ran out before every
      container in this section was opened, so tiles are missing.
    - ``contents_unavailable`` — at least one container could NOT be opened.
      Distinct from a verified-empty container: collapsing the two makes a
      console that failed mid-walk look like a show with nothing configured.

    ``status`` keeps the two failure causes apart (REQ-SHOWUI-002).
    """
    if status not in PANEL_SECTION_STATUSES:
        raise ValueError(
            f"panel section status must be one of {PANEL_SECTION_STATUSES}, got {status!r}"
        )
    return {
        "name": name,
        "status": status,
        "truncated": bool(truncated),
        "drilldown_capped": bool(drilldown_capped),
        "contents_unavailable": bool(contents_unavailable),
    }


def panel_catalog_event(*, items: list[dict], sections: list[dict]) -> dict:
    """The panel's executable tile list plus per-section completeness.

    ``items`` order IS grid order (REQ-SHOWUI-005/017): append-only, never
    sorted by either side. A tile that moves under the operator's finger
    mid-show is a misfire waiting to happen.
    """
    return _event("panel_catalog", items=list(items), sections=list(sections))


def panel_item_state_event(
    *, target_kind: str, target: int, running: bool, cue: str | None = None
) -> dict:
    """One tile's playback state. ``cue`` is the running sequence's current cue
    number when the console reported one (design.md §2), else ``None`` —
    a string because MA3 cue numbers are not integers (e.g. "1.5")."""
    return _event(
        "panel_item_state",
        id=panel_item_id(target_kind, target),
        target_kind=target_kind,
        target=target,
        running=bool(running),
        cue=cue,
    )


def panel_busy_event(*, target_kind: str, target: int, message: str) -> dict:
    """A panel execution was refused because one is already in flight.

    Names the tile it refused: the UI locks a tile the moment it is pressed
    (REQ-SHOWUI-011), so a bare busy message would leave that tile latched with
    nothing to unlock it. Distinct from ``busy`` — that one is the chat turn
    lock, which the panel deliberately does not share (REQ-SHOWUI-013).
    """
    return _event(
        "panel_busy",
        id=panel_item_id(target_kind, target),
        target_kind=target_kind,
        target=target,
        message=message,
    )


# -- console-info dashboard (SPEC-COPILOT-DASHUI-001 M1) ------------------------
#
# The dashboard's read-only pool catalog. INFO-ONLY BY SHAPE (REQ-DASHUI-007):
# a dash entry carries the console fact (``no`` + ``name``) and nothing a
# command could be built from — no ``target_kind``, no derived ``id``, no
# command string. Non-fireability is a missing field, not a runtime check:
# there is nothing here for a future caller to hand to ``gate.screen()``.

# The wire fields that would make an entry addressable (the PanelItem address
# triple). The section builder refuses to carry any of them, so a fire-shaped
# record cannot ride the dashboard event even by accident.
_DASH_FORBIDDEN_ITEM_KEYS = ("id", "target_kind", "target")


def dash_item(
    *,
    no: int,
    name: str,
    appearance: str | None = None,
    meta: dict | None = None,
) -> dict:
    """One read-only dashboard entry — a console fact, not a fire address.

    | field         | meaning                                                  |
    |---------------|----------------------------------------------------------|
    | ``no``        | the console's REAL object number — pools are             |
    |               | non-contiguous (REQ-DASHUI-005)                          |
    | ``name``      | the console name, verbatim                               |
    | ``appearance``| the appearance colour chip, or ``None``                  |
    | ``meta``      | optional extra facts, e.g. the fixture-count summary     |
    |               | (REQ-DASHUI-009) — omitted when absent                   |

    Deliberately NOT a ``panel_item``: the address triple (``id`` /
    ``target_kind`` / ``target``) does not exist here, so nothing downstream
    can turn this record into a command bundle (REQ-DASHUI-007).
    """
    if not _is_object_number(no):
        raise ValueError(f"dash item no must be a positive integer object number, got {no!r}")
    if not isinstance(name, str):
        raise ValueError(f"dash item name must be a string, got {name!r}")
    item: dict = {"no": no, "name": name, "appearance": appearance}
    if meta is not None:
        if not isinstance(meta, dict):
            raise ValueError(f"dash item meta must be a dict, got {meta!r}")
        item["meta"] = dict(meta)
    return item


def dash_section(
    *,
    name: str,
    status: str,
    items: list[dict],
    truncated: bool = False,
    drilldown_capped: bool = False,
    contents_unavailable: bool = False,
) -> dict:
    """One dashboard section: its own completeness plus its info-only entries.

    ``status`` and the three completeness flags reuse the panel-section
    vocabulary verbatim (REQ-DASHUI-004): the two failure causes stay distinct
    and the flags carry all the way to the UI. Unlike ``panel_catalog``'s flat
    tile list, ``items`` ride INSIDE their section — a dashboard section is a
    self-contained pool view.

    Any entry carrying a fire-address field is refused outright: the info-only
    property (REQ-DASHUI-007) is enforced at construction, not left to caller
    discipline.
    """
    if status not in PANEL_SECTION_STATUSES:
        raise ValueError(
            f"dash section status must be one of {PANEL_SECTION_STATUSES}, got {status!r}"
        )
    checked: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"dash section items must be dicts, got {item!r}")
        forbidden = [key for key in _DASH_FORBIDDEN_ITEM_KEYS if key in item]
        if forbidden:
            raise ValueError(
                f"dash section {name!r} refused a fire-shaped item (carries {forbidden})"
            )
        checked.append(item)
    return {
        "name": name,
        "status": status,
        "truncated": bool(truncated),
        "drilldown_capped": bool(drilldown_capped),
        "contents_unavailable": bool(contents_unavailable),
        "items": checked,
    }


def dash_catalog_event(*, sections: list[dict]) -> dict:
    """The console-info dashboard catalog (REQ-DASHUI-006).

    A refresh REPLACES the whole list — the ``panel_catalog`` replace
    semantics, inherited: merging would keep pools the showfile no longer has.
    Section order is wire order; nothing sorts it (REQ-DASHUI-003).
    """
    return _event("dash_catalog", sections=list(sections))


# -- live cue-progress monitor (T-C, wave 2 — ad-hoc contract, no SPEC) --------
#
# Two independent read paths (see ``server/web/cue_monitor.py`` for the
# builders): a per-executor cue-progress row, and a console-independent
# recent-execution history read off the audit log. Both ride inside ONE
# ``cue_monitor`` event with replace semantics — same family convention as
# ``dash_catalog``/``panel_catalog``.

CUE_EXECUTOR_STATUSES = ("ok", "unassigned", "unavailable")


def cue_executor_entry(
    *,
    executor_no: int,
    status: str,
    sequence_no: int | None = None,
    sequence_name: str | None = None,
    cues: list[dict] | None = None,
    current_cue: dict | None = None,
    last_app_action: dict | None = None,
    planned_position: int | None = None,
) -> dict:
    """One executor's live cue-progress row.

    ``status``:
    - ``"ok"`` — the assigned sequence's cue list was read.
    - ``"unassigned"`` — the executor answered but carries no sequence.
    - ``"unavailable"`` — the executor (or its sequence) could not be read.

    ``current_cue`` is independently Optional (contract item 1): it carries
    its OWN ``status`` (``"ok"`` / ``"unavailable"``), because the current-cue
    property read can fail even when the sequence/cue-list read above
    succeeded — the two are never conflated into one verdict.

    ``last_app_action`` (T-H, additive) is a THIRD independent claim: the most
    recent command the app itself sent this executor and whether the console
    ok'd it (``{"command", "ts", "ok"}``), or ``None`` when the app has never
    sent this executor anything. It is never a claim about whether the
    console is CURRENTLY playing that command — only that it was sent and
    acknowledged (or not).

    ``planned_position`` (진행 순서 보드, additive) is this executor's 1-based
    slot in the operator's PLANNED show order (the director timeline's
    sequence), or ``None`` for an executor the plan does not name. The
    ordering itself is applied by the snapshot builder; this field only lets
    the UI badge the planned rows.
    """
    if status not in CUE_EXECUTOR_STATUSES:
        raise ValueError(
            f"cue executor status must be one of {CUE_EXECUTOR_STATUSES}, got {status!r}"
        )
    return {
        "executor_no": executor_no,
        "status": status,
        "sequence_no": sequence_no,
        "sequence_name": sequence_name,
        "cues": list(cues) if cues is not None else [],
        "current_cue": current_cue,
        "last_app_action": last_app_action,
        "planned_position": planned_position,
    }


def cue_history_entry(
    *,
    ts: str,
    command: str,
    ok: bool,
    target_kind: str | None = None,
    target_no: int | None = None,
) -> dict:
    """One recent-execution row (contract item 2) — read from the audit log,
    independent of any console connection.

    ``target_kind``/``target_no`` (T-H, additive) are the best-effort
    attribution of which console object this command addressed, parsed from
    the command string itself (``server/web/cue_monitor.py``'s
    ``_parse_command_target``). Both are ``None`` when the command does not
    parse as one of the known playback forms — the row is still returned,
    never dropped, so the full history stays visible even when this module
    cannot say who it was for.
    """
    return {
        "ts": ts,
        "command": command,
        "ok": bool(ok),
        "target_kind": target_kind,
        "target_no": target_no,
    }


def cue_monitor_event(*, executors: list[dict], history: list[dict]) -> dict:
    """The live cue-progress-monitor snapshot.

    Replace semantics, same as ``dash_catalog``/``panel_catalog`` — no
    server-side merge with a previous snapshot.
    """
    return _event("cue_monitor", executors=list(executors), history=list(history))


def song_timeline_event(*, timeline: dict) -> dict:
    """Read-only director timeline projection. The payload deliberately carries
    no console commands; execution remains behind the server approval gate."""
    return _event("song_timeline", timeline=timeline)
