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


def _validate_plugin_call_budget(command_line: str, *, field: str) -> None:
    size = len(command_line.encode("utf-8"))
    if size > MAX_PLUGIN_CALL_BYTES:
        raise ProtocolError(
            f"{field} encoded command line must fit {MAX_PLUGIN_CALL_BYTES} bytes, got {size}"
        )


def build_plugin_call(request: str) -> str:
    """Wrap one responder request string as an MA3 plugin-invoking command line."""
    return f'Plugin "{PLUGIN_NAME}" "{request}"'


def build_ping(request_id: str) -> str:
    """Round-trip liveness probe; responder replies kind=pong on /copilot/feedback."""
    _validate_request_id(request_id)
    return build_plugin_call(f"ping {request_id}")


def build_state_query(request_id: str, path: str) -> str:
    """Object-tree snapshot query (REQ-MVP-003); reply arrives on /copilot/state.

    ``path`` is parsed rest-of-line by the responder, so embedded spaces are
    legal (e.g. ``DataPool/Sequences/My Seq``).
    """
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    return build_plugin_call(f"state {request_id} {path}")


def build_introspect_query(request_id: str, path: str) -> str:
    _validate_request_id(request_id)
    _validate_rest(path, field="object path")
    line = build_plugin_call(f"introspect {request_id} {path}")
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


def build_exec_request(request_id: str, command: str) -> str:
    """Wrapped command execution with result capture (REQ-MVP-004).

    The responder runs ``Cmd(command)`` and replies kind=result on
    /copilot/feedback with the success flag and raw result/error string.
    """
    _validate_request_id(request_id)
    _validate_rest(command, field="command")
    return build_plugin_call(f"exec {request_id} {command}")


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
