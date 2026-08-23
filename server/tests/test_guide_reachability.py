"""t24 — 사용 가이드가 배포되는 앱에 도달하는지, 그리고 낡지 않았는지.

`docs/user-guide.html` 은 저장소에만 있었고 사용자가 받는 앱에는 들어가지 않았다.
`git grep -l user-guide -- ui/ src-tauri/ packaging/` 가 빈 출력이었다. 감독이 조준
기능을 모른 진짜 이유가 이것일 수 있다 — 목록에 없어서가 아니라 목록에 닿을 수 없어서다.

해결은 빌드 시점 복사다. prebuild 가 원본을 ui/public 으로 복사하고, Vite 가 그것을
ui/dist 로 통과시키고, 기존 catch-all 마운트가 /user-guide.html 로 서빙한다.
커밋된 사본이 없으므로 원본은 하나뿐이다.

이 가드가 보는 것은 존재가 아니라 일치다. 존재만 보면 절반만 막힌다:

    원본이 갱신됨 -> prebuild 가 안 돌아 옛 사본이 남음
                  -> 존재 검사 통과 (파일은 있다)
                  -> 감독은 낡은 가이드를 본다

존재는 신선도의 증거가 아니다. 그래서 체크섬을 대조한다.

범위 판단 하나를 밝힌다. 빌드를 한 적 없는 트리에는 사본이 없고, 그것은 결함이
아니라 아직 배포 단계에 오지 않은 상태다. 반면 ui/dist 가 있는데 가이드만 없으면
복사 스텝이 실제 빌드에서 건너뛰어진 것이므로 실패해야 한다. 그래서 공허 통과
방지는 배선 검사가 상시로 지고, 신선도 검사는 해당 산출물이 있을 때 건다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = PROJECT_ROOT / "docs" / "user-guide.html"
STAGED = PROJECT_ROOT / "ui" / "public" / "user-guide.html"
DIST_DIR = PROJECT_ROOT / "ui" / "dist"
DIST_COPY = DIST_DIR / "user-guide.html"
UI_PACKAGE = PROJECT_ROOT / "ui" / "package.json"
APP_TSX = PROJECT_ROOT / "ui" / "src" / "App.tsx"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prebuild_command() -> str:
    scripts = json.loads(UI_PACKAGE.read_text(encoding="utf-8"))["scripts"]
    return scripts.get("prebuild", "")


class TestTheGuideIsWiredIntoTheBuild:
    """배선 검사 — 항상 돈다. 공허 통과를 막는 축이다."""

    def test_the_original_exists(self) -> None:
        assert ORIGINAL.is_file(), "원본 가이드가 없다 — 복사할 대상이 사라졌다"

    def test_a_prebuild_step_copies_the_guide(self) -> None:
        command = _prebuild_command()
        assert "docs/user-guide.html" in command, "prebuild 가 원본을 가리키지 않는다: " + repr(
            command
        )
        assert "public/user-guide.html" in command, (
            "prebuild 의 복사 대상이 ui/public 이 아니다: " + repr(command)
        )

    def test_the_copy_step_is_unconditional(self) -> None:
        command = _prebuild_command()
        skips = [tok for tok in ("[ -f", "[ -e", "||", "if ") if tok in command]
        assert not skips, (
            "복사 스텝에 조건부 스킵이 있다: "
            + repr(skips)
            + " — 이미 있으면 건너뛰면 원본이 갱신돼도 옛 사본이 남는다"
        )

    def test_the_header_links_to_the_served_copy(self) -> None:
        assert "/user-guide.html" in APP_TSX.read_text(encoding="utf-8"), (
            "상시 헤더에 가이드 링크가 없다 — 배포돼도 감독이 닿을 길이 없다"
        )


class TestTheDeployedCopyIsNotStale:
    """신선도 검사 — 산출물이 있을 때 건다. 존재가 아니라 일치를 본다."""

    def test_a_staged_copy_matches_the_original(self) -> None:
        if not STAGED.exists():
            pytest.skip("ui/public 사본 없음 — 아직 빌드 전 트리다")
        assert _digest(STAGED) == _digest(ORIGINAL), (
            "ui/public 사본이 원본과 다르다 — prebuild 없이 원본만 갱신됐다"
        )

    def test_a_built_bundle_carries_a_fresh_guide(self) -> None:
        if not DIST_DIR.is_dir():
            pytest.skip("ui/dist 없음 — 이 트리에서 빌드가 돈 적이 없다")
        assert DIST_COPY.is_file(), "빌드 산출물이 있는데 가이드가 없다 — 복사 스텝이 건너뛰어졌다"
        assert _digest(DIST_COPY) == _digest(ORIGINAL), (
            "빌드된 가이드가 원본과 다르다 — 감독이 낡은 문서를 본다"
        )


class TestTheComparatorCanActuallyFail:
    """실패할 수 없는 가드는 가드가 아니다."""

    def test_one_changed_byte_is_detected(self, tmp_path: Path) -> None:
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_bytes(b"<html>guide</html>")
        b.write_bytes(b"<html>guidf</html>")
        assert _digest(a) != _digest(b), "체크섬 비교가 한 바이트 차이를 못 잡는다"

    def test_identical_bytes_compare_equal(self, tmp_path: Path) -> None:
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_bytes(b"<html>guide</html>")
        b.write_bytes(b"<html>guide</html>")
        assert _digest(a) == _digest(b), "동일 내용을 다르다고 판정한다"
