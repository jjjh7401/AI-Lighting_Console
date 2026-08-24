"""Suite-wide pytest fixtures for the server tests.

Autouse keyring neutralisation
------------------------------
Every test in this suite runs against a fresh in-memory keyring backend instead
of the real OS credential store (macOS Keychain / Windows Credential Manager).
This keeps the suite deterministic and unattended: REQ-DEPLOY-028 wired the
active-provider key read into ``server.web.serve.build_runtime`` at start-up, and
``GET /api/settings`` reads per-provider key presence (``_provider_key_status``),
so on a machine that already has a key stored under the app's service name those
paths would otherwise block on an interactive Keychain access prompt.

The fixture is deliberately override-friendly. A test that installs its own
backend — ``test_deploy_keystore.py::memory_keyring`` / ``broken_keyring``,
``test_web_serve.py::broken_keyring`` and its autouse ``_isolate_real_keyring``,
the AC-DEPLOY-016 store-unavailable simulations, etc. — still wins: its
``keyring.set_keyring`` call runs after this autouse default and replaces the
in-memory backend for that test. This fixture then restores the real backend
afterwards, so nothing leaks between tests.

An in-memory (rather than a null) backend is chosen because it round-trips
``set``/``get``: whichever backend is active when a seed-and-read test runs, the
seeded key is readable. Reads for keys that were never seeded return ``None``,
exactly as the previous real store did for an absent item — with no prompt.
"""

from __future__ import annotations

import threading

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

from server.deploy import keystore


class _InMemoryKeyring(KeyringBackend):
    """Deterministic in-memory keyring backend — never touches the real OS store."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self._store[(service, username)]
        except KeyError as error:
            raise PasswordDeleteError("not found") from error


@pytest.fixture(autouse=True)
def _neutralize_os_keyring():
    """Autouse — pin a fresh in-memory keyring for EVERY test so none touches the
    real OS Keychain.

    A per-test fixture that installs its own backend overrides this default (its
    ``set_keyring`` runs after), and the real backend captured here is restored
    on teardown. Session-only keys are cleared afterwards so the module-default
    ``SessionKeyStore`` never leaks across tests.
    """
    original = keyring.get_keyring()
    keyring.set_keyring(_InMemoryKeyring())
    try:
        yield
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()


def recv_frame(ws, timeout: float = 10.0) -> dict:
    """웹소켓 프레임 하나 — 아니면 실패. **행(hang)은 없다.**

    ``TestClient`` 의 웹소켓 수신에는 상한이 없다(`WebSocketTestSession.receive`
    → `portal.call(self._send_rx.receive)`, 인자 없음). 그래서 오지 않는 프레임
    하나가 **스위트 전체를 영영 멈춘다** — 실패가 아니라 정지다.

    회수 상한(`for _ in range(N)`)은 이것을 못 막는다. **회수는 각 회가 돌아와야
    세므로**, 1 회차가 안 오면 카운터가 안 올라가고 그 아래 `raise` 는 영영
    도달하지 못한다. 검사가, 그것이 쓰인 바로 그 경우에 공허해진다.

    실측(t52): 전량이 86% 에서 두 번 섰고 자리는
    ``test_web_app.py::test_vectorworks_upload_starts_a_guided_chat_turn`` 이었다.
    SHEETPIPE 판별기가 옛 픽스처 페이로드를 ``unknown_sheet_kind`` 로 판정해
    서버가 ``notice`` 만 보냈는데, 테스트는 ``chat_response`` 를 기다렸다.

    **이 독스트링이 여기 있는 이유**: 같은 모양의 사본이 세 파일에 생겼던 것은
    「왜 상한이 필요한가」가 코드 옆에 없었기 때문이다. 이 함수를 지우거나
    ``timeout`` 을 없애기 전에 위 문단을 먼저 반증해라.
    """
    box: dict[str, object] = {}

    def pump() -> None:
        try:
            box["event"] = ws.receive_json()
        except Exception as error:  # closed socket, decode failure, …
            box["error"] = error

    worker = threading.Thread(target=pump, daemon=True)
    worker.start()
    worker.join(timeout)
    if "event" not in box:
        raise AssertionError(f"no websocket frame within {timeout}s ({box.get('error')})")
    return box["event"]  # type: ignore[return-value]


def drain_until(ws, event_type: str, *, limit: int = 30) -> dict:
    """``event_type`` 이 나올 때까지 프레임을 버린다 — **시간 상한 위에서**.

    ``limit`` 은 회수 상한이고, 시간 상한은 :func:`recv_frame` 이 건다. 둘 다
    필요하다: 회수만 있으면 안 오는 프레임에 멈추고, 시간만 있으면 엉뚱한
    프레임이 무한히 오는 경우를 못 끊는다.
    """
    seen: list[str] = []
    for _ in range(limit):
        event = recv_frame(ws)
        seen.append(event["type"])
        if event["type"] == event_type:
            return event
    raise AssertionError(f"no {event_type!r} event within {limit} frames: {seen}")
