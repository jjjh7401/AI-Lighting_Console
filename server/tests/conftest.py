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


def fire_status_listeners(deps) -> int:
    """등록된 status 리스너를 **지금** 부른다 — 타이머를 기다리지 않고.

    **왜 지어낸 경로가 아닌가.** ``_heartbeat_loop`` 은 게이트 health 상태가 바뀔 때마다
    ``for notify in tuple(deps.status_listeners): notify()`` 로 이 집합을 돈다(app.py:255-256).
    이 함수는 **같은 집합의 같은 콜러블**을 부른다 — 재구현이 아니라 동일 객체다. 프레임 내용도
    테스트가 짓지 않는다 — ``push_status`` → ``send_event(session.status_snapshot())``
    (app.py:381-382).
    다른 것은 **호출 원인 하나**뿐이다: 저기서는 타이머, 여기서는 이 문장.

    그리고 그 루프는 실서비스에서 **실제로 돈다** — ``serve.py:103`` 의 ``--heartbeat-interval``
    기본값이 5.0 이고(``serve.py:382`` → ``app.py:279-281``), 즉 요청과 응답 사이에 ``status``
    한 장이 끼는 일은 가정이 아니라 운영 사실이다. 반면 테스트의 ``_deps`` 는 이 값을 안 주므로
    (``app.py:175`` 기본값 ``None``) 검사 중에는 루프가 **안 돈다** — 그래서 음성 대조군이
    결정적이고, 그래서 이 함수가 필요하다.

    **미는 프레임은 ``status`` 한 종류뿐이다.** ``push_status`` 가 보내는 것이
    ``session.status_snapshot()`` 이기 때문이다. 기대 타입이 ``status`` 인 자리 앞에 이것을 밀면
    두 헬퍼는 여전히 행동이 같다 — 그런 자리를 이 함수로 가르려 하지 마라.

    🔴 **고아 펌프 함정(t94).** ``recv_frame`` 은 시간이 초과돼도 자기 펌프 스레드를 안 죽인다.
    그 고아가 소켓에 매달려 **다음 프레임 한 장을 먹는다.** 그러므로 이 함수를 쓰는 검사에서
    「초과를 삼켜 ``None`` 으로 바꾸는」 판독을 쓰면, 그 뒤 읽기가 전부 거짓 0 이 된다.
    초과가 예정된 읽기를 이 함수 근처에 두지 마라.

    Returns: 부른 리스너 수.
    """
    listeners = tuple(deps.status_listeners)
    # 0 이면 이 함수는 조용히 아무것도 안 한 셈이 된다. 오늘의 검사들은 그 경우에도
    # 빨개지므로 공허해지지는 않는다 — 이 단언의 이유는 **재사용 안전**이다.
    # 다른 문맥(소켓을 아직 안 열었거나, 이미 닫힌 뒤)에서 이 함수를 부르면
    # 침묵이 통과로 읽힐 수 있고, 그때는 잡아줄 단정이 없다.
    assert listeners, "status 리스너가 0개다 — 소켓이 연결된 뒤에 불러야 한다"
    for notify in listeners:
        notify()
    return len(listeners)
