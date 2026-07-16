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
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from server.llm.types import LLMProvider
from server.safety.audit import AuditLog
from server.safety.backup import BackupManager
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    ProtocolError,
    approval_resolved_event,
    busy_event,
    error_event,
    parse_client_message,
)
from server.web.session import ChatSession

_PROTOCOL_ERROR_MESSAGE = "잘못된 메시지 형식입니다. 프로토콜 v1 스키마를 확인해 주세요."
_STALE_APPROVAL_MESSAGE = "만료되었거나 알 수 없는 승인 요청입니다."
_BUSY_MESSAGE = "이전 지시를 처리 중입니다 — 완료된 뒤 다시 시도해 주세요."


@dataclass
class WebDeps:
    """Everything the web app consumes — composed by serve.py / tests."""

    gate: SafetyGate
    provider: LLMProvider
    system_prefix: str
    audit: AuditLog
    approval_channel: ApprovalChannel
    recorder: RoundTripRecorder | None = None
    rig_paths: dict[str, str] | None = None
    ui_dist: Path | None = None
    backup_manager: BackupManager | None = None
    heartbeat_interval_seconds: float | None = None
    backup_poll_seconds: float | None = None
    status_listeners: set = field(default_factory=set)


async def _safe_send(websocket: WebSocket, event: dict) -> None:
    # Client gone -> drop silently; server events are best-effort.
    with contextlib.suppress(Exception):
        await websocket.send_json(event)


async def _heartbeat_loop(deps: WebDeps, interval: float) -> None:
    last_state: str | None = None
    while True:
        state = await asyncio.to_thread(deps.gate.heartbeat)
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

    @app.get("/healthz")
    def healthz() -> dict:
        gate_status = deps.gate.status
        return {"ok": True, **gate_status}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
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
        )

        def push_status() -> None:
            send_event(session.status_snapshot())

        deps.status_listeners.add(push_status)
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
                elif message_type == "lock":
                    session.set_lock(message["active"])
                else:  # status_request
                    await _safe_send(websocket, session.status_snapshot())
        except WebSocketDisconnect:
            pass
        finally:
            deps.status_listeners.discard(push_status)
            session.close()  # unbind the approval channel — pending waits deny
            if current_task is not None and not current_task.done():
                # The worker was denied by close(); give it a bounded finish.
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(asyncio.shield(current_task), timeout=10.0)

    if deps.ui_dist is not None and Path(deps.ui_dist).is_dir():
        app.mount("/", StaticFiles(directory=str(deps.ui_dist), html=True), name="ui")

    return app
