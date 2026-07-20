"""Local-only operation regression (M10 Part C).

AC-DEPLOY-002 — 로컬 전용(local-only), 원격 백엔드 미의존 (REQ-DEPLOY-004 / 004a).
Four sub-checks, all AUTOMATED + OFFLINE (in-process; no onPC, no network):

  ① backend bind 주소가 127.0.0.1(비 0.0.0.0/공인)임을 확인.
  ② OSC 송수신이 localhost UDP임을 확인.
  ③ 소스 스캔 — 원격 클라우드 백엔드 엔드포인트 의존 0건 (LLM provider API 제외).
  ④ (반자동) 인터넷 차단(LLM API 제외) 상태에서도 UI·설정·health가 동작.

The LLM provider SDKs (anthropic / google-genai) are the ONLY sanctioned external
hosts; they are reached through their own SDKs, not through any endpoint URL this
app hardcodes. ④ proves the app does not HARD-depend on the internet: with an
absent/scripted (non-network) provider and no console, the UI static mount, the
settings API, and /healthz all still respond.
"""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent

# Hosts that are legitimately local (a loopback bind is REQUIRED for local-only —
# 127.0.0.1 is the CORRECT bind, not a violation).
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
# Bind hosts that would expose the backend beyond the local machine.
_PUBLIC_BIND_HOSTS = frozenset({"0.0.0.0", "::", ""})


class TestAcDeploy002BackendBind:
    """① backend binds loopback, never a public interface."""

    def test_web_and_console_hosts_default_to_loopback(self):
        from server.web.serve import parse_args

        args = parse_args([])
        assert args.host in _LOOPBACK_HOSTS, f"web bind host is not loopback: {args.host!r}"
        assert args.host not in _PUBLIC_BIND_HOSTS
        assert args.console_host in _LOOPBACK_HOSTS, (
            f"console host is not loopback: {args.console_host!r}"
        )

    def test_port_availability_probe_targets_loopback(self):
        # serve.main() probes the OSC feedback listener on 127.0.0.1 explicitly
        # (REQ-DEPLOY-026 fail-loud). Assert the literal loopback host is used for
        # the receive-port probe in the serve entry point.
        source = (PROJECT_ROOT / "server/web/serve.py").read_text(encoding="utf-8")
        assert '("127.0.0.1", args.receive_port' in source


class TestAcDeploy002OscLocalhostUdp:
    """② OSC send/recv is localhost UDP."""

    def test_bridge_config_defaults_are_loopback(self):
        from server.bridge.osc import BridgeConfig

        config = BridgeConfig()
        assert config.send_host in _LOOPBACK_HOSTS
        assert config.receive_host in _LOOPBACK_HOSTS

    def test_bridge_transport_is_udp(self):
        # The send surface is python-osc over UDP: a SimpleUDPClient (send) and a
        # ThreadingOSCUDPServer (receive). Assert both UDP transports are the ones
        # the bridge module wires — no TCP, no remote transport.
        source = (PROJECT_ROOT / "server/bridge/osc.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("pythonosc"):
                imported.update(alias.name for alias in node.names)
        assert "SimpleUDPClient" in imported  # UDP send
        assert "ThreadingOSCUDPServer" in imported  # UDP receive

    def test_serve_console_defaults_are_loopback_udp_ports(self):
        from server.web.serve import parse_args

        args = parse_args([])
        assert args.console_host in _LOOPBACK_HOSTS
        assert isinstance(args.console_port, int) and args.console_port > 0
        assert isinstance(args.receive_port, int) and args.receive_port > 0


class TestAcDeploy002NoRemoteBackend:
    """③ source scan — zero remote cloud-backend endpoint dependency."""

    def test_no_hardcoded_remote_http_endpoint(self):
        # The ONLY http(s):// literal our source may hardcode is the LOCAL loopback
        # URL the launcher opens in the browser. Any other absolute URL would be a
        # remote-backend dependency (the LLM SDKs reach their own hosts internally
        # and are the sanctioned exception — they hardcode no URL here).
        import re

        url_re = re.compile(r"https?://([^\s\"'/):]+)")
        offenders: list[str] = []
        for path in sorted(SERVER_DIR.rglob("*.py")):
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            if "/tests/" in f"/{rel}" or "/__pycache__/" in f"/{rel}":
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for host in url_re.findall(line):
                    # The launcher builds "http://{display_host}:{port}" where
                    # display_host is a loopback literal/placeholder — allow the
                    # loopback hosts and the f-string placeholder form.
                    if host in _LOOPBACK_HOSTS or host.startswith("{"):
                        continue
                    offenders.append(f"{rel}: {stripped}")
        assert offenders == [], f"remote backend endpoint dependency found: {offenders}"

    def test_launcher_local_url_is_loopback(self):
        from server.web.launcher import serve_local_url

        for bind in ("", "0.0.0.0", "::", "127.0.0.1"):
            url = serve_local_url(bind, 8765)
            assert url.startswith("http://127.0.0.1:") or url.startswith("http://localhost:"), url


class TestAcDeploy002OfflineOperation:
    """④ (semi-auto) UI / settings / health function with no network (absent LLM)."""

    def _offline_app(self, tmp_path):
        from server.deploy.keystore import SessionKeyStore
        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate
        from server.web.app import WebDeps, create_app
        from server.web.approval_bridge import ApprovalChannel
        from server.web.settings_api import SettingsDeps

        from .test_runner_self_correction import ScriptedProvider  # non-network double
        from .test_safety_gate import FakeConsole  # in-memory console, no OSC/network

        audit = AuditLog(tmp_path / "audit")
        channel = ApprovalChannel(timeout_seconds=2.0)
        gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)

        ui_dist = tmp_path / "dist"
        ui_dist.mkdir()
        (ui_dist / "index.html").write_text("<html>ui</html>", encoding="utf-8")

        settings = SettingsDeps(
            settings_path=tmp_path / "settings.toml",
            seed_path=tmp_path / "no-seed.toml",
            session=SessionKeyStore(),
            environ={},
        )
        deps = WebDeps(
            gate=gate,
            provider=ScriptedProvider([]),  # never called — no LLM, no network
            system_prefix="PREFIX",
            audit=audit,
            approval_channel=channel,
            ui_dist=ui_dist,
            settings=settings,
        )
        return create_app(deps)

    def test_health_ui_settings_work_with_no_network(self, tmp_path):
        # No network is reachable in this in-process test; the app must still serve
        # the SPA, the settings API, and health entirely from local state.
        with TestClient(self._offline_app(tmp_path)) as client:
            health = client.get("/healthz")
            assert health.status_code == 200
            assert health.json()["ok"] is True

            settings = client.get("/api/settings")
            assert settings.status_code == 200
            assert "settings" in settings.json()

            spa = client.get("/")
            assert spa.status_code == 200  # static SPA index served locally
