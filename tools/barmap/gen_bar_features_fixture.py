"""LOVE ATTACK 마디별 특징 고정 픽스처 생성기(카드 t535, 2026-10-10).

실제 오디오에서 `detect_beat_grid` → `derive_bars(..., 1)` →
`extract_bar_features`를 한 번 돌려 마디별 특징(음량·저역·보컬 대역 비율·온셋
개수 + 다운비트 ms)을 JSON으로 고정한다 — **파생 숫자만** 적는다. 오디오
자체는 커밋하지 않는다(REQ-LDBARMAP-014) — 이 파일은 숫자표일 뿐이라 허용된다
(``server/tests/fixtures/love_attack_beat_grid.json``과 같은 설계 원칙).

이 픽스처가 있으면 CI에서(로컬 원곡 없이도) M3 정밀도 조건(AC-LDBARMAP-007)을
"실제 오디오 경로②"로 재현할 수 있다 — mp3 파일이 저장소 밖에만 있어도 생성
시점에 한 번 재서 고정해 두면, 이후 테스트는 이 JSON만 읽는다.

실행(저장소 루트에서):
    .venv/bin/python tools/barmap/gen_bar_features_fixture.py \
        "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"

`server/` 아래 파일은 읽기만 한다(REQ-LDBARMAP-002/003) — 쓰는 파일은
`server/tests/fixtures/love_attack_bar_features_real.json` 하나뿐이다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.audio.bar_map import (  # noqa: E402
    BarMap,
    BeatGridResult,
    derive_bars,
    detect_beat_grid,
    extract_bar_features,
)

#: AC-LDBARMAP-016 — 감독이 귀로 확인해 확정한 첫 박 오프셋(progress.md §E.2).
CONFIRMED_FIRST_BEAT_OFFSET = 1

DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "server" / "tests" / "fixtures" / "love_attack_bar_features_real.json"
)


def generate(audio_path: Path, output_path: Path = DEFAULT_OUTPUT_PATH) -> dict:
    """실제 오디오에서 마디별 특징을 재 JSON 딕셔너리로 돌려주고(그리고 쓴다)."""
    audio_bytes = audio_path.read_bytes()

    grid = detect_beat_grid(audio_bytes)
    if not isinstance(grid, BeatGridResult):
        raise RuntimeError(f"비트 격자 검출 실패: {grid}")

    bar_map = derive_bars(grid.beat_times_ms, CONFIRMED_FIRST_BEAT_OFFSET)
    if not isinstance(bar_map, BarMap):
        raise RuntimeError(f"마디 지도 파생 실패: {bar_map}")

    features = extract_bar_features(audio_bytes, bar_map.bar_boundaries_ms)
    if isinstance(features, tuple):
        feature_rows = features
    else:
        raise RuntimeError(f"마디별 특징 추출 실패: {features}")

    payload = {
        "_source_note": (
            "LOVE ATTACK 82마디 특징(음량·저역·보컬 대역 비율·온셋 개수) — "
            "server.audio.bar_map.extract_bar_features()가 실제 LOVE ATTACK mp3에서 "
            "잰 값을 그대로 고정한 숫자(derived numbers)다. 원곡 오디오 자체는 "
            "커밋하지 않는다(REQ-LDBARMAP-014) — 이 파일은 파생 숫자일 뿐이라 "
            "허용된다. 디코드·비트 검출 경로는 server/audio/analyze.py의 analyze()와 "
            "동일하다(soundfile 읽기 -> mono 다운믹스 -> librosa.beat.beat_track "
            "hop=512). 첫 박 오프셋은 AC-LDBARMAP-016이 감독 귀 확정한 1(정수, "
            "beat_times 인덱스 mod 4)을 썼다. 카드 t535(M3 정밀도 보강)가 생성."
        ),
        "first_beat_offset": CONFIRMED_FIRST_BEAT_OFFSET,
        "bar_boundaries_ms": list(bar_map.bar_boundaries_ms),
        "bar_features": [
            {
                "bar": f.bar,
                "volume_norm": f.volume_norm,
                "low_band_norm": f.low_band_norm,
                "vocal_band_ratio": f.vocal_band_ratio,
                "onset_count": f.onset_count,
            }
            for f in feature_rows
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(rendered, encoding="utf-8")
    return payload


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: gen_bar_features_fixture.py <audio-path>")
        return 2
    audio_path = Path(argv[1])
    if not audio_path.exists():
        print(f"오디오 파일이 없습니다: {audio_path}")
        return 1
    payload = generate(audio_path)
    print(f"마디 {len(payload['bar_features'])}개 → {DEFAULT_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
