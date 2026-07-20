"""resource_base() resolver tests (M6 — FEAS-1 / research §A.4).

The frozen-aware resource resolver is the single helper every bundled-asset
path routes through: dev checkout -> project root, frozen PyInstaller bundle ->
``sys._MEIPASS``. Both onedir (``_MEIPASS`` = ``_internal``) and onefile
(``_MEIPASS`` = temp extraction dir) set ``sys.frozen`` + ``sys._MEIPASS``, so
one resolver covers both (research §A.4).
"""

from __future__ import annotations

import sys
from pathlib import Path

from server.resources import resource_base


class TestResourceBaseDevMode:
    def test_dev_mode_returns_the_repo_root(self):
        # Not frozen -> the dev project root (the directory that contains the
        # `server/`, `ui/`, `config/`, `console/` trees).
        base = resource_base()
        assert base.is_dir()
        assert (base / "server").is_dir()
        assert (base / "server" / "resources.py").is_file()

    def test_dev_mode_root_matches_the_legacy_parents_climb(self):
        # Characterisation: the resolver's dev root MUST equal the repo root the
        # pre-M6 `Path(__file__).resolve().parents[2]` climbs from serve.py /
        # config.py resolved to (so no dev-path regression).
        legacy_from_serve = (
            Path(__file__).resolve().parents[1] / "web" / "serve.py"
        ).resolve().parents[2]
        assert resource_base() == legacy_from_serve


class TestResourceBaseFrozenMode:
    def test_frozen_returns_meipass(self, monkeypatch, tmp_path):
        # research §A.4: frozen build sets sys.frozen=True + sys._MEIPASS; the
        # resolver returns Path(sys._MEIPASS).
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        assert resource_base() == Path(str(tmp_path))

    def test_discriminates_on_frozen_not_meipass_presence(self, monkeypatch, tmp_path):
        # A stray _MEIPASS without sys.frozen must NOT flip to bundle mode — the
        # gate is `getattr(sys, "frozen", False)` (research §A.4 / Section D).
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert resource_base() != Path(str(tmp_path))
        assert (resource_base() / "server").is_dir()


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _freeze(monkeypatch, meipass):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)


class TestConfigPathRoutesThroughResourceBase:
    def test_dev_config_path_unchanged(self):
        from server.llm.config import default_config_path

        # Characterisation: dev-mode resolution is byte-identical to pre-M6.
        assert default_config_path() == _REPO_ROOT / "config" / "provider.toml"

    def test_frozen_config_path_under_meipass(self, monkeypatch, tmp_path):
        from server.llm.config import default_config_path

        _freeze(monkeypatch, tmp_path)
        assert default_config_path() == Path(str(tmp_path)) / "config" / "provider.toml"


class TestAssetsDirRoutesThroughResourceBase:
    def test_dev_assets_dir_unchanged(self):
        from server.rulebook.assembly import _assets_dir

        assert _assets_dir() == _REPO_ROOT / "server" / "rulebook" / "assets"

    def test_frozen_assets_dir_under_meipass(self, monkeypatch, tmp_path):
        from server.rulebook.assembly import _assets_dir

        _freeze(monkeypatch, tmp_path)
        assert _assets_dir() == Path(str(tmp_path)) / "server" / "rulebook" / "assets"


class TestResponderDirRoutesThroughResourceBase:
    def test_dev_responder_dir_unchanged(self):
        from server.deploy.provisioning import bundled_responder_dir

        assert bundled_responder_dir() == _REPO_ROOT / "console" / "lua"

    def test_frozen_responder_dir_under_meipass(self, monkeypatch, tmp_path):
        from server.deploy.provisioning import bundled_responder_dir

        _freeze(monkeypatch, tmp_path)
        assert bundled_responder_dir() == Path(str(tmp_path)) / "console" / "lua"
