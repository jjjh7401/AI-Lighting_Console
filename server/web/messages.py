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
    "approval_decision",
    "review_decision",
    # [round24 후속] 모델이 되묻고 사용자가 답하는 통로. 승인·검토와 달리
    # 실패가 「거부」가 아니라 **미응답**이다 — 없는 답을 지어내지 않게 하는 것이 목적.
    "question_answer",
    "lock",
    "status_request",
    # 새로고침 생존: 복원된 화면 기록을 새 세션에 재주입(위 상수 참조).
    "history_restore",
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
        return {"v": PROTOCOL_VERSION, "type": "chat", "text": text}

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

    if message_type in (
        "panel_pin",
        "panel_catalog_request",
        "dash_catalog_request",
        "cue_monitor_request",
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
