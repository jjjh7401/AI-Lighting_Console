"""Responder wire-protocol codec v1 (M2) — Python twin of ``console/lua/copilot_responder.lua``.

Implements the server side of the protocol defined in ``console/lua/PROTOCOL.md``:

* **Requests** (server → console) ride ``/copilot/cmd`` as MA3 command lines that
  invoke the console-side plugin: ``Plugin "CopilotResponder" "<verb> <id> [rest]"``.
* **Replies** (console → server) arrive as a single OSC string argument on
  ``/copilot/state`` (snapshots, REQ-MVP-003) or ``/copilot/feedback``
  (execution results, REQ-MVP-004), encoded as **percent-encoded JSON** so the
  payload is comma/quote/space-free — safe for MA3's packed OSC-send string
  form (``"/addr,s,<payload>"`` splits on commas) and pure-ASCII regardless of
  UTF-8 object names.

This module is a pure codec: no sockets, no OSC I/O — the single UDP send
surface remains :meth:`server.bridge.osc.OscBridge.send_command`
(REQ-MVP-029 chokepoint unaffected).
"""

from __future__ import annotations

import json
import re
import urllib.parse
from collections.abc import Sequence

# @MX:NOTE: [AUTO] protocol version is embedded in every reply payload as "v";
#   bump only with a PROTOCOL.md revision (M3 tool-runner consumes this contract)
PROTOCOL_VERSION = 1

PLUGIN_NAME = "CopilotResponder"

MAX_PROPS_NAMES = 16

#: 요청 한 줄의 바이트 상한 — **이 값은 실측이 아니다.** 이 프로토콜이 스스로
#: 정한 프레이밍 상한이고, 콘솔이 받아 주는 한계와 대응하지 않는다.
#:
#: t60 이 실기로 잰 것 (방향·대상·단위를 함께 읽어라 — 이 셋이 빠져서
#: 이 저장소가 이미 두 번 오진했다):
#:   방향: 서버 -> 콘솔 (요청)    대상: exec 로 나가는 명령 한 줄
#:   단위: UTF-8 바이트 (전선에 실제로 나간 값)
#:   결과: **어떤 길이 축으로도 단조 임계값이 없다.**
#:     `Fixture 101` x142 (2026B) 통과 / x143 (2040B) 거절 — 3회 재현
#:     그러나 2065B · 2080B · 2167B 짜리 다른 줄은 통과하고,
#:     같은 계열 안에서 2044B 거절 / 2053B 통과 (2회 재현, 비단조).
#:
#: 회신 방향 절단 경계 `[1200, 1208)` 와 **섞지 마라** — 그건 콘솔 -> 서버
#: 스냅샷 payload 값이다(`docs/runbooks/fake-real-parity-method.md` §3).
#:
#: 판정 전문: `.moai/specs/SPEC-COPILOT-LXSEQ-002/t60-verdict.md`
MAX_PLUGIN_CALL_BYTES = 2048

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class ProtocolError(ValueError):
    """Raised when a payload or request cannot be encoded/decoded safely."""


# -- payload codec (replies: console -> server) ------------------------------


def encode_payload(payload: dict) -> str:
    """Encode a reply payload as percent-encoded JSON (test/simulation twin).

    Production replies are encoded by the Lua responder; this Python twin
    exists for the round-trip tooling and cross-language codec tests.
    """
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return urllib.parse.quote(text, safe="")


# @MX:ANCHOR: [AUTO] single decode point for all console responder replies —
#   round-trip tool (M2), tool-runner result confirmation (M3), and safety-gate
#   execution verification (M4) all parse responder payloads through here
# @MX:REASON: divergent ad-hoc parsing of the percent-encoded JSON wire form
#   would silently fork the protocol; keep exactly one decoder (fan_in >= 3 expected)
def decode_payload(text: str) -> dict:
    """Decode one responder reply payload (percent-encoded JSON, v1).

    Lenient input forms: percent-encoded JSON (canonical) or raw JSON (a
    future clean transport). Tries RAW JSON first and only falls back to
    percent-decode-then-parse on a raw-parse failure — this is safe by
    construction: a genuine percent-encoded payload is comma/quote/space-free
    (see module docstring), so it can never contain a literal `{`/`"` and
    therefore never parses as raw JSON directly, reliably falling through to
    the decode branch. Raw JSON, in turn, never touches ``unquote`` at all.
    (Deciding the input form by "does a %XX-shaped substring appear
    anywhere in the text" — the previous approach — is a false-positive trap:
    raw JSON whose string VALUES happen to contain a literal ``%XX``
    substring, e.g. ``{"note": "discount %20 code"}``, would be silently
    corrupted by an unwarranted percent-decode, including turning a literal
    ``%0A``/``%0D`` substring into a real newline/carriage-return
    character — "newline smuggling" into anything downstream that treats
    decoded values as single-line.)

    Raises :class:`ProtocolError` on anything else or when the decoded value
    is not a JSON object.
    """
    if not text:
        raise ProtocolError("empty payload")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        try:
            decoded = json.loads(urllib.parse.unquote(text))
        except json.JSONDecodeError as error:
            raise ProtocolError(f"payload is not valid (percent-encoded) JSON: {error}") from error
    if not isinstance(decoded, dict):
        raise ProtocolError(f"payload must decode to a JSON object, got {type(decoded).__name__}")
    return decoded


# -- request builders (server -> console, ride /copilot/cmd) ------------------


def _validate_request_id(request_id: str) -> None:
    if not request_id or not _REQUEST_ID.match(request_id):
        raise ProtocolError(
            f"request id must be a non-empty token of [A-Za-z0-9._-], got {request_id!r}"
        )


def _validate_rest(rest: str, *, field: str) -> None:
    if not rest:
        raise ProtocolError(f"{field} must be non-empty")
    if '"' in rest:
        # A double quote would terminate MA3's quoted plugin argument.
        # MA3 accepts single-quoted strings, so callers can rewrite
        # `Store Cue 5 "name"` as `Store Cue 5 'name'` (see PROTOCOL.md).
        raise ProtocolError(f'{field} must not contain a double quote ("): {rest!r}')
    if "\n" in rest or "\r" in rest:
        raise ProtocolError(f"{field} must be a single line: {rest!r}")


def _validate_property_name_token(property_name: str) -> None:
    _validate_rest(property_name, field="property name")
    if any(char.isspace() for char in property_name):
        raise ProtocolError(f"property name must be a single token: {property_name!r}")


def _validate_props_names(property_names: Sequence[str]) -> tuple[str, ...]:
    if isinstance(property_names, str):
        raise ProtocolError("property names must be a sequence of individual names")
    try:
        names = tuple(property_names)
    except TypeError as error:
        raise ProtocolError("property names must be a sequence of individual names") from error
    if not names:
        raise ProtocolError("property names must be non-empty")
    if len(names) > MAX_PROPS_NAMES:
        raise ProtocolError(f"too many property names: max {MAX_PROPS_NAMES}, got {len(names)}")
    for name in names:
        if not isinstance(name, str):
            raise ProtocolError(f"property name must be a string: {name!r}")
        _validate_property_name_token(name)
        if "," in name:
            raise ProtocolError(f"property name must not contain a comma: {name!r}")
    return names


# @MX:WARN: [AUTO] 이 검사를 다른 요청 빌더로 **퍼뜨리지 마라.** 특히 exec 로.
# @MX:REASON: `MAX_PLUGIN_CALL_BYTES = 2048` 은 이 프로토콜이 스스로 정한 값이지
#   콘솔이 받아 주는 실측 상한이 아니다. t60 이 실기로 쟀고(판정:
#   `.moai/specs/SPEC-COPILOT-LXSEQ-002/t60-verdict.md`), 콘솔의 거절은 **어떤
#   길이 축으로도 단조 임계값이 아니었다**:
#     `Fixture 101` x142 (전선 2026B) 통과 / x143 (2040B) 거절 — 3회 재현
#     그런데 2065B·2080B·2167B 짜리 다른 줄들은 통과하고,
#     같은 계열 안에서도 2044B 는 거절인데 2053B 는 통과다(2회 재현, 비단조).
#   그러므로 바이트 예산 검사는 양방향으로 틀린다 — 2048 로 두면 위 2040B 실패를
#   못 막고, 실패 지점 근처로 낮추면 콘솔에서 멀쩡히 도는 2167B 명령을 막는다.
#   introspect/props 에 남아 있는 이 검사도 어떤 실측에도 대응하지 않는다. 읽기
#   질의라 잘못 거절돼도 파급이 작아 t60 이 건드리지 않았을 뿐이다 — 「돌고 있으니
#   맞는 값」으로 읽지 마라.
#   긴 명령에 대한 방어는 검사가 아니라 **호출부가 명령을 짧게 유지하는 것**이다
#   (t66: 그룹 선택 줄 86 FID 1201B -> 182B).
def _validate_plugin_call_budget(command_line: str, *, field: str) -> None:
    size = len(command_line.encode("utf-8"))
    if size > MAX_PLUGIN_CALL_BYTES:
        raise ProtocolError(
            f"{field} encoded command line must fit {MAX_PLUGIN_CALL_BYTES} bytes, got {size}"
        )


def _validate_plugin_name(plugin_name: str) -> None:
    """Reject a plugin name that cannot survive the ``Plugin "<name>"`` quoting.

    The name lands INSIDE the double-quoted invocation target, so an embedded
    double quote would terminate it early and reshape the command line.
    """
    if not plugin_name:
        raise ProtocolError("plugin name must be non-empty")
    if '"' in plugin_name:
        raise ProtocolError(f'plugin name must not contain a double quote ("): {plugin_name!r}')
    if "\n" in plugin_name or "\r" in plugin_name:
        raise ProtocolError(f"plugin name must be a single line: {plugin_name!r}")


# @MX:NOTE: [AUTO] ``plugin_name`` exists for the deploy alias path
#   (server/safety/console.py::_redeploy_via_alias): a responder redeploy must
#   run its `Delete Plugin <own slot>` from a DIFFERENT plugin object, because
#   MA3 2.4.2 raises an unanswerable confirm dialog when the running plugin
#   deletes itself (docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md §1.2).
def build_plugin_call(request: str, *, plugin_name: str = PLUGIN_NAME) -> str:
    """Wrap one responder request string as an MA3 plugin-invoking command line.

    ``plugin_name`` defaults to the responder; pass an alias name to run the
    request from a temporary duplicate of the responder instead.
    """
    _validate_plugin_name(plugin_name)
    return f'Plugin "{plugin_name}" "{request}"'


def build_ping(request_id: str) -> str:
    """Round-trip liveness probe; responder replies kind=pong on /copilot/feedback."""
    _validate_request_id(request_id)
    return build_plugin_call(f"ping {request_id}")


def build_state_query(request_id: str, path: str, offset: int | None = None) -> str:
    """Object-tree snapshot query (REQ-MVP-003); reply arrives on /copilot/state.

    ``path`` is parsed rest-of-line by the responder, so embedded spaces are
    legal (e.g. ``DataPool/Sequences/My Seq``).

    ``offset`` (PROTOCOL.md §4.2 paging, responder 1.6.0) is the 0-based
    ``children`` window start. ``None`` **and** ``0`` both emit the historical
    request bytes (no token) — the first window needs no marker and stays
    byte-identical for pre-1.6.0 responders. A positive value appends one
    trailing ``offset=<n>`` token. A pre-1.6.0 responder parses that token as
    part of the path and replies ``ok:false`` with **no** ``offset`` echo;
    callers MUST treat a missing echo (or ``ok:false``) on a paged request as
    "no progress" and stop paging rather than retry (PROTOCOL.md §4.2).
    """
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    if isinstance(offset, bool) or (offset is not None and not isinstance(offset, int)):
        raise ProtocolError(f"offset must be an int or None: {offset!r}")
    if offset is not None and offset < 0:
        raise ProtocolError(f"offset must be >= 0: {offset!r}")
    if not offset:
        return build_plugin_call(f"state {request_id} {path}")
    return build_plugin_call(f"state {request_id} {path} offset={offset}")


def build_introspect_query(request_id: str, path: str, offset: int | None = None) -> str:
    """Handle field-name/type discovery; reply arrives on /copilot/state.

    ``offset`` (PROTOCOL.md 4.7 paging, responder 1.6.2) is the 0-based start
    into the FULL enumerated name list. ``None`` **and** ``0`` both emit the
    historical request bytes (no token), so a still-deployed 1.6.1 responder
    keeps answering the unpaged call byte-for-byte. A positive value appends
    one trailing ``offset=<n>`` token.

    A pre-1.6.2 responder folds that token into the path and replies
    ``ok:false`` with **no** ``offset`` echo, so a caller that pages MUST read
    a missing echo as "this responder cannot page" and stop -- never retry the
    same offset. Same contract as ``build_state_query``, deliberately: two
    different paging rules for one token shape is how a caller ends up paging
    one verb correctly and the other into the path.

    Advance ``offset`` by the number of entries actually RECEIVED, never by a
    fixed page size -- the window width is decided by the responder's payload
    budget, not by the request.
    """
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    if isinstance(offset, bool) or (offset is not None and not isinstance(offset, int)):
        raise ProtocolError(f"offset must be an int or None: {offset!r}")
    if offset is not None and offset < 0:
        raise ProtocolError(f"offset must be >= 0: {offset!r}")
    rest = f"introspect {request_id} {path}"
    if offset:
        rest = f"{rest} offset={offset}"
    line = build_plugin_call(rest)
    _validate_plugin_call_budget(line, field="introspect request")
    return line


def build_prop_query(request_id: str, path: str, property_name: str) -> str:
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    _validate_property_name_token(property_name)
    return build_plugin_call(f"prop {request_id} {path} {property_name}")


def build_props_query(request_id: str, path: str, property_names: Sequence[str]) -> str:
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    names = _validate_props_names(property_names)
    line = build_plugin_call(f"props {request_id} {','.join(names)} {path}")
    _validate_plugin_call_budget(line, field="props request")
    return line


def build_exec_request(request_id: str, command: str, *, plugin_name: str = PLUGIN_NAME) -> str:
    """Wrapped command execution with result capture (REQ-MVP-004).

    The responder runs ``Cmd(command)`` and replies kind=result on
    /copilot/feedback with the success flag and raw result/error string.

    ``plugin_name`` names the plugin object that RUNS the command. It defaults
    to the responder; the deploy alias path passes a temporary duplicate so a
    responder redeploy never deletes the plugin it is executing from.
    """
    _validate_request_id(request_id)
    _validate_rest(command, field="command")
    return build_plugin_call(f"exec {request_id} {command}", plugin_name=plugin_name)


def build_deploy_request(request_id: str, name: str, lua_source: str) -> str:
    """Plugin deployment request (M7, REQ-MVP-019; PROTOCOL.md §2 ``deploy``).

    Name and source are percent-encoded (RFC 3986 style, nothing spared) so
    the request tokens are pure ASCII with no spaces and no double quotes —
    they survive MA3's quoted plugin-argument form regardless of the Lua
    source content. The responder percent-decodes, re-compiles in the console
    runtime, and creates/updates the plugin object (ASSUMPTION-6).
    """
    _validate_request_id(request_id)
    if not name:
        raise ProtocolError("plugin name must be non-empty")
    if not lua_source:
        raise ProtocolError("lua source must be non-empty")
    encoded_name = urllib.parse.quote(name, safe="")
    encoded_source = urllib.parse.quote(lua_source, safe="")
    return build_plugin_call(f"deploy {request_id} {encoded_name} {encoded_source}")
