"""FastAPI WebSocket app (M5 — REQ-MVP-020: Korean chat over WebSocket).

One WebSocket endpoint (``/ws``) speaks protocol v1 (``server/web/PROTOCOL.md``).
The receive loop stays free while an instruction runs on a worker thread
(``asyncio.to_thread``), so approval decisions and lock toggles are processed
DURING an in-flight instruction — the async half of the M4 approval bridge and
the lock-first guarantee (REQ-MVP-035) depend on exactly this.

The app also owns the runtime loops the M4 modules left to the server
lifecycle: periodic responder heartbeats (REQ-MVP-030/031 detection) and the
periodic showfile-backup tick (REQ-MVP-017 rule ②).

Chokepoint discipline (AC-MVP-019): this module never imports the OSC send
surface — it receives the finished gate via :class:`WebDeps` (composed by
``server.safety.bootstrap``).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from server.llm.types import LLMProvider
from server.orchestrator.tools import DeployPipelinePort
from server.safety.audit import AuditLog
from server.safety.backup import BackupManager
from server.safety.gate import SafetyGate
from server.safety.session_context import new_session_key
from server.web.approval_bridge import ApprovalChannel
from server.web.cue_monitor import cue_monitor_snapshot
from server.web.dash import build_dash_catalog, resolved_executor_nos, send_dash_catalog
from server.web.handshake import (
    CLOSE_POLICY_VIOLATION,
    HandshakePolicy,
    evaluate_handshake,
)
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    ProtocolError,
    approval_request_event,
    approval_resolved_event,
    busy_event,
    error_event,
    parse_client_message,
    review_resolved_event,
)
from server.web.panel import (
    PANEL_GO_VERB,
    PANEL_OFF_VERB,
    PANEL_UNKNOWN_TARGET_MESSAGE,
    PanelRuntime,
    PanelStore,
    PinStore,
)
from server.web.provision_api import ProvisionDeps, build_provision_router
from server.web.session import ChatSession
from server.web.settings_api import SettingsDeps, build_settings_router

_PROTOCOL_ERROR_MESSAGE = "잘못된 메시지 형식입니다. 프로토콜 v1 스키마를 확인해 주세요."
_STALE_APPROVAL_MESSAGE = "만료되었거나 알 수 없는 승인 요청입니다."
_STALE_REVIEW_MESSAGE = "만료되었거나 알 수 없는 리뷰 요청입니다."
_BUSY_MESSAGE = "이전 지시를 처리 중입니다 — 완료된 뒤 다시 시도해 주세요."
_PANEL_TASK_ERROR_MESSAGE = "패널 요청을 처리하지 못했습니다."


@dataclass
class WebDeps:
    """Everything the web app consumes — composed by serve.py / tests."""

    gate: SafetyGate
    provider: LLMProvider
    system_prefix: str
    audit: AuditLog
    approval_channel: ApprovalChannel
    review_channel: ApprovalChannel | None = None
    deploy_pipeline: DeployPipelinePort | None = None
    recorder: RoundTripRecorder | None = None
    rig_paths: dict[str, str] | None = None
    ui_dist: Path | None = None
    backup_manager: BackupManager | None = None
    heartbeat_interval_seconds: float | None = None
    backup_poll_seconds: float | None = None
    settings: SettingsDeps | None = None
    provision: ProvisionDeps | None = None
    # M7.1 (REQ-DEPLOY-002a): the /ws Origin+token gate. ``None`` = no gate,
    # which is the pre-M7.1 behaviour dev runs and unit tests compose.
    handshake: HandshakePolicy | None = None
    # REQ-DEPLOY-018 follow-up: bind-probe the console's OSC input port so a
    # console_offline state can name the RIGHT cause. ``None`` = no probe, and
    # the status surface reports ``undetermined`` (the pre-existing meaning).
    console_input_probe: Callable[[], str] | None = None
    # REQ-DEPLOY-018/026 follow-up: the third console_offline cause — the console
    # replying to a port the app does not listen on. ``None`` = no diagnosis, and
    # the status surface omits both port numbers (the pre-existing meaning).
    # Non-blocking by contract: the status frame is built on the event loop.
    reply_port_probe: Callable[[], object] | None = None
    # SHOWUI M3: the show-control panel's server-side truth (pinned tiles + the
    # last rig enumeration), shared by every connection because both halves are
    # process state, not per-client state. ``None`` means "build the default on
    # first use" — so a packaged run gets a panel without serve.py wiring, while
    # a test that never presses a tile never touches the user's pin file.
    panel: PanelStore | None = None
    status_listeners: set = field(default_factory=set)


async def _safe_send(websocket: WebSocket, event: dict) -> None:
    # Client gone -> drop silently; server events are best-effort.
    with contextlib.suppress(Exception):
        await websocket.send_json(event)


async def _heartbeat_loop(deps: WebDeps, interval: float) -> None:
    last_state: str | None = None
    while True:
        try:
            state = await asyncio.to_thread(deps.gate.heartbeat)
        except Exception as error:  # mirrors _backup_loop — the loop survives
            deps.audit.record({"event": "heartbeat_tick_failed", "detail": str(error)})
        else:
            if state != last_state:
                last_state = state
                for notify in tuple(deps.status_listeners):
                    notify()
        await asyncio.sleep(interval)


async def _backup_loop(deps: WebDeps, interval: float) -> None:
    manager = deps.backup_manager
    if manager is None:
        return
    while True:
        try:
            await asyncio.to_thread(manager.tick)
        except Exception as error:  # BackupError included — the loop survives
            deps.audit.record({"event": "backup_tick_failed", "detail": str(error)})
        await asyncio.sleep(interval)


def create_app(deps: WebDeps) -> FastAPI:
    """Build the FastAPI app around one composed dependency set."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks: list[asyncio.Task] = []
        if deps.heartbeat_interval_seconds:
            tasks.append(
                asyncio.create_task(_heartbeat_loop(deps, deps.heartbeat_interval_seconds))
            )
        if deps.backup_poll_seconds:
            tasks.append(asyncio.create_task(_backup_loop(deps, deps.backup_poll_seconds)))
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="MA3 Copilot", lifespan=lifespan)

    # SHOWUI M3 — the panel store is process state (a pin file + the last rig
    # enumeration), so it is built ONCE and shared by every connection. Built
    # lazily so a run that never opens the panel never reads the pin file.
    _panel_store: PanelStore | None = deps.panel

    def panel_store() -> PanelStore:
        nonlocal _panel_store
        if _panel_store is None:
            _panel_store = PanelStore(state_port=deps.gate.state_port, pins=PinStore())
        return _panel_store

    # M7.4b (AC-DEPLOY-025 Stage-2): once the Stage-2 window loads the BUNDLED
    # app (origin ``tauri://localhost``) instead of navigating to the backend,
    # its ``/api/*`` reads are CROSS-origin to the backend. Without CORS the
    # webview silently blocks every settings/provision fetch. The allowlist is
    # EXACTLY the handshake's Stage-2 trusted origins — no wildcard, no new
    # literal, no widening past what the ``/ws`` gate already trusts. Stage-1
    # browser mode is same-origin (served BY the backend) and needs none, so an
    # ungated launch (no handshake) adds no CORS surface at all. Credentials are
    # NOT allowed: nothing here authenticates with cookies, and allow-credentials
    # would only widen what a mistaken origin entry could reach.
    if deps.handshake is not None and deps.handshake.trusted_origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(deps.handshake.trusted_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["content-type"],
        )

    @app.get("/healthz")
    def healthz() -> dict:
        gate_status = deps.gate.status
        return {"ok": True, **gate_status}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        # M7.1 (REQ-DEPLOY-002a / AC-DEPLOY-025 / FEAS-9): authorize the upgrade
        # BEFORE accept(). A rejected client is closed without ever being
        # accepted, so it reaches no session, no gate and no console. The reject
        # reason stays server-side — the peer learns only that it was refused.
        subprotocol: str | None = None
        if deps.handshake is not None:
            decision = evaluate_handshake(
                deps.handshake,
                origin=websocket.headers.get("origin"),
                subprotocols=websocket.scope.get("subprotocols") or (),
            )
            if not decision.accepted:
                deps.audit.record(
                    {"event": "ws_handshake_rejected", "reason": decision.reason}
                )
                await websocket.close(code=CLOSE_POLICY_VIOLATION)
                return
            subprotocol = decision.subprotocol

        await websocket.accept(subprotocol=subprotocol)
        loop = asyncio.get_running_loop()

        def send_event(event: dict) -> None:
            # Thread-safe: session events originate on the worker thread.
            asyncio.run_coroutine_threadsafe(_safe_send(websocket, event), loop)

        session = ChatSession(
            gate=deps.gate,
            provider=deps.provider,
            system_prefix=deps.system_prefix,
            audit=deps.audit,
            send_event=send_event,
            approval_channel=deps.approval_channel,
            recorder=deps.recorder,
            rig_paths=deps.rig_paths,
            review_channel=deps.review_channel,
            deploy_pipeline=deps.deploy_pipeline,
            console_input_probe=deps.console_input_probe,
            reply_port_probe=deps.reply_port_probe,
        )

        def push_status() -> None:
            send_event(session.status_snapshot())

        deps.status_listeners.add(push_status)

        # -- show-control panel (SHOWUI M3) -----------------------------------
        #
        # The panel gets its OWN session identity. The gate keys clearances per
        # session, so sharing the chat's key would let a chat turn's screening
        # invalidate a panel clearance and vice versa — REQ-SHOWUI-013 requires
        # the two paths to serialize independently, and this is what makes that
        # true rather than merely intended.
        panel_key = new_session_key()
        panel = PanelRuntime(
            gate=deps.gate,
            store=panel_store(),
            send_event=send_event,
            session_key=panel_key,
        )

        def notify_panel_approval(request_id: str, request) -> None:
            # A held panel bundle rides the EXISTING approval card (REQ-SHOWUI-008);
            # the channel is payload-agnostic, so this is wiring, not a new flow.
            send_event(approval_request_event(request_id=request_id, request=request))

        deps.approval_channel.bind(notify_panel_approval, session_key=panel_key)

        # Two independent lanes, not one lock. The execute lane is 1-in-flight
        # and REFUSES a second press (panel_busy, REQ-SHOWUI-011). The stop lane
        # never refuses (REQ-SHOWUI-012 — stop is single-press, zero-wait) but
        # does serialize stops against each other: every screen() resets this
        # session's clearance Counter, so two stops screened concurrently would
        # leave the first uncleared and silently un-stopped — which would make
        # an All Off of N tiles stop one tile (REQ-SHOWUI-025).
        panel_stop_lane = asyncio.Lock()
        panel_side_lane = asyncio.Lock()  # catalog / pin / unpin — store mutations
        panel_execute_task: asyncio.Task | None = None
        panel_tasks: set[asyncio.Task] = set()

        async def panel_task(fn, *args, lane: asyncio.Lock | None = None) -> None:
            if lane is not None:
                await lane.acquire()
            try:
                await asyncio.to_thread(fn, *args)
            except Exception as error:  # a panel failure must not kill the socket
                deps.audit.record({"event": "panel_task_failed", "detail": str(error)})
                await _safe_send(
                    websocket, error_event(message=_PANEL_TASK_ERROR_MESSAGE, kind="panel")
                )
            finally:
                if lane is not None:
                    lane.release()

        def spawn_panel(coro) -> asyncio.Task:
            task = asyncio.create_task(coro)
            panel_tasks.add(task)
            task.add_done_callback(panel_tasks.discard)
            return task

        current_task: asyncio.Task | None = None
        await websocket.send_json(session.status_snapshot())
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = parse_client_message(raw)
                except ProtocolError:
                    await _safe_send(
                        websocket, error_event(message=_PROTOCOL_ERROR_MESSAGE, kind="protocol")
                    )
                    continue
                message_type = message["type"]
                if message_type == "chat":
                    if current_task is not None and not current_task.done():
                        await _safe_send(websocket, busy_event(_BUSY_MESSAGE))
                        continue
                    current_task = asyncio.create_task(
                        asyncio.to_thread(session.run_instruction, message["text"])
                    )
                elif message_type == "approval_decision":
                    resolved = deps.approval_channel.resolve(
                        message["request_id"], approved=message["approved"]
                    )
                    if resolved:
                        await _safe_send(
                            websocket,
                            approval_resolved_event(
                                request_id=message["request_id"],
                                approved=message["approved"],
                            ),
                        )
                    else:
                        await _safe_send(
                            websocket,
                            error_event(message=_STALE_APPROVAL_MESSAGE, kind="protocol"),
                        )
                elif message_type == "review_decision":
                    resolved = deps.review_channel is not None and deps.review_channel.resolve(
                        message["request_id"], approved=message["approved"]
                    )
                    if resolved:
                        await _safe_send(
                            websocket,
                            review_resolved_event(
                                request_id=message["request_id"],
                                approved=message["approved"],
                            ),
                        )
                    else:
                        await _safe_send(
                            websocket,
                            error_event(message=_STALE_REVIEW_MESSAGE, kind="protocol"),
                        )
                elif message_type == "lock":
                    session.set_lock(message["active"])
                elif message_type in ("panel_execute", "panel_stop"):
                    target_kind, target = message["target_kind"], message["target"]
                    if not panel.contains(target_kind, target):
                        # REQ-SHOWUI-022 membership half. Refused HERE, before a
                        # bundle exists: an unknown target must never be able to
                        # reach gate.screen() as a plausible-looking command.
                        await _safe_send(
                            websocket,
                            error_event(message=PANEL_UNKNOWN_TARGET_MESSAGE, kind="panel"),
                        )
                    elif message_type == "panel_execute":
                        if panel_execute_task is not None and not panel_execute_task.done():
                            panel.busy(target_kind, target)
                        else:
                            panel_execute_task = spawn_panel(
                                panel_task(panel.fire, PANEL_GO_VERB, target_kind, target)
                            )
                    else:
                        # Busy-guard EXEMPT (REQ-SHOWUI-012): a stop is handled
                        # while an execute is still inside screen(), and may call
                        # gate.screen() concurrently with it. The exemption is a
                        # scheduling property — the stop still goes through the
                        # gate, exactly like every other panel command.
                        spawn_panel(
                            panel_task(
                                panel.fire,
                                PANEL_OFF_VERB,
                                target_kind,
                                target,
                                lane=panel_stop_lane,
                            )
                        )
                elif message_type == "panel_catalog_request":
                    spawn_panel(panel_task(panel.send_catalog, lane=panel_side_lane))
                elif message_type == "panel_pin":
                    spawn_panel(
                        panel_task(panel.pin, session.last_created, lane=panel_side_lane)
                    )
                elif message_type == "panel_unpin":
                    spawn_panel(
                        panel_task(
                            panel.unpin,
                            message["target_kind"],
                            message["target"],
                            lane=panel_side_lane,
                        )
                    )
                elif message_type == "dash_catalog_request":
                    # SPEC-COPILOT-DASHUI-001 M2 — shares panel_side_lane with
                    # panel_catalog_request/pin/unpin: this is another
                    # many-round-trip state_port read, and serializing it
                    # against the existing catalog build avoids stacking
                    # concurrent OSC query storms on the console.
                    def _dash_catalog_and_membership() -> None:
                        # M6 — the build's VERIFIED executor console numbers
                        # become panel members (AC-DASHUI-005): the SHOWUI
                        # catalog's own executor tiles carry pool slots the
                        # console does not address, so without this the dash
                        # tiles' only legitimate targets would be rejected
                        # as "not on the panel".
                        event = send_dash_catalog(deps.gate.state_port, send_event)
                        panel.register_dash_executors(
                            resolved_executor_nos(event["sections"])
                        )

                    spawn_panel(
                        panel_task(_dash_catalog_and_membership, lane=panel_side_lane)
                    )
                elif message_type == "cue_monitor_request":
                    # T-C, wave 2 (ad-hoc contract, no SPEC on file). Resolves
                    # its own executor numbers on demand (dash.py's own
                    # console-verification step, REQ-DASHUI-011) rather than
                    # depending on a prior dash_catalog_request having run —
                    # shares panel_side_lane for the same reason dash does:
                    # another many-round-trip state_port read that should not
                    # stack concurrent OSC query storms on the console.
                    def _cue_monitor() -> None:
                        sections = build_dash_catalog(deps.gate.state_port)
                        console_nos = resolved_executor_nos(sections)
                        event = cue_monitor_snapshot(
                            deps.gate.state_port,
                            deps.gate.state_port,
                            deps.audit,
                            console_nos,
                        )
                        send_event(event)

                    spawn_panel(panel_task(_cue_monitor, lane=panel_side_lane))
                else:  # status_request
                    await _safe_send(websocket, session.status_snapshot())
        except WebSocketDisconnect:
            pass
        finally:
            deps.status_listeners.discard(push_status)
            # Unbind FIRST: a panel bundle parked on a pending approval is
            # released denied (fail-safe, acceptance.md §D edge case 8), so the
            # bounded wait below has something that can actually finish. The
            # panel's running state dies with the connection — it is a derived
            # observation, and "probably still running" is not a render
            # (REQ-SHOWUI-015).
            deps.approval_channel.unbind(session_key=panel_key)
            session.close()  # unbind the approval channel — pending waits deny
            for task in tuple(panel_tasks):
                if not task.done():
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(asyncio.shield(task), timeout=10.0)
            if current_task is not None and not current_task.done():
                # The worker was denied by close(); give it a bounded finish.
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(asyncio.shield(current_task), timeout=10.0)

    # In-app settings/key REST API (M3) + responder provisioning API (M4).
    # Registered BEFORE the catch-all static mount at "/" so /api/* resolves to
    # the routers, not the SPA index.
    if deps.settings is not None:
        app.include_router(build_settings_router(deps.settings))

    if deps.provision is not None:
        app.include_router(build_provision_router(deps.provision))

    if deps.ui_dist is not None and Path(deps.ui_dist).is_dir():
        app.mount("/", StaticFiles(directory=str(deps.ui_dist), html=True), name="ui")

    return app
