"""M3 감독 귀 확인 후보 목록 생성기 (카드 t535, AC-LDBARMAP-007 정밀도 조건).

실제 오디오 경로② 고정 픽스처(``server/tests/fixtures/love_attack_bar_features_real.json``)
로 분류한 사건 중, 정밀도 조건(근거 있음 판정)을 통과하지 못한 검출을
``.moai/reports/SPEC-LDBARMAP-001-probes/m3-ear-check-candidates.md``로 적는다.

이 목록의 각 항목은 "오검출"도 "정답지 누락"도 아니다 — 최종 판정은 감독의
귀가 정한다(acceptance.md AC-LDBARMAP-007 § "근거 없음(unsupported) 사건의
처리"). 참고 섹션으로 구 규칙(절대 온셋 상수, 카드 t535 이전)의 근거 없음
목록도 같이 적는다 — 새 규칙이 치운 거짓 양성이 실제로 브레이크였는지
감독이 비교해 판단할 수 있게 한다.

실행(저장소 루트에서):
    .venv/bin/python tools/barmap/gen_ear_check_candidates.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import server.audio.bar_map as bar_map_module  # noqa: E402
from server.audio.bar_map import BarFeatures, classify_bar_events  # noqa: E402
from tools.barmap.ground_truth import parse_precision_evidence  # noqa: E402
from tools.barmap.scorer import event_precision  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "server" / "tests" / "fixtures" / "love_attack_bar_features_real.json"
OUTPUT_PATH = (
    REPO_ROOT / ".moai" / "reports" / "SPEC-LDBARMAP-001-probes" / "m3-ear-check-candidates.md"
)

#: 구 규칙(카드 t535 이전, 절대 온셋 상수) — bar_map.py에서는 이미 제거됐다
#: (새 규칙으로 교체). 참고 섹션 재현 목적으로만 이 스크립트에 리터럴로 남긴다.
_OLD_BREAK_MAX_ONSET_COUNT = 2


def _format_mmss(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:05.2f}"


def load_fixture(path: Path = FIXTURE_PATH) -> tuple[list[BarFeatures], list[int]]:
    """고정 픽스처(JSON, 파생 숫자) → ``BarFeatures`` 목록 + 마디 경계(ms)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    features = [
        BarFeatures(
            bar=row["bar"],
            volume_norm=row["volume_norm"],
            low_band_norm=row["low_band_norm"],
            vocal_band_ratio=row["vocal_band_ratio"],
            onset_count=row["onset_count"],
        )
        for row in data["bar_features"]
    ]
    return features, data["bar_boundaries_ms"]


def old_rule_detected_events(by_bar: dict[int, BarFeatures]) -> list[tuple[str, int]]:
    """구 규칙(절대 온셋 상수, 카드 t535 이전)을 재현한다 — 참고 섹션용."""
    break_bars = sorted(
        bar
        for bar, f in by_bar.items()
        if f.low_band_norm <= bar_map_module._BREAK_LOW_BAND_RATIO
        or (f.onset_count is not None and f.onset_count <= _OLD_BREAK_MAX_ONSET_COUNT)
    )
    kick_ratio = bar_map_module._KICK_ENTRY_LOW_BAND_RATIO
    kick_bars = sorted(bar for bar, f in by_bar.items() if f.low_band_norm >= kick_ratio)
    return [("break", b) for b in break_bars] + [("kick_entry", b) for b in kick_bars]


def _branch_description(f: BarFeatures, kind: str, *, rule: str) -> str:
    """어느 판정 분기가 이 검출을 냈는지 — ``rule`` 로 새/구 규칙을 구분해 정확히
    묘사한다(참고 섹션에서 구 규칙의 분기를 새 규칙 말로 잘못 적지 않도록)."""
    if kind == "kick_entry":
        ratio = bar_map_module._KICK_ENTRY_LOW_BAND_RATIO
        return f"저역≥{ratio}배 (저역={f.low_band_norm:.3f})"
    break_ratio = bar_map_module._BREAK_LOW_BAND_RATIO
    if f.low_band_norm <= break_ratio:
        return f"저역 절대 문턱(≤{break_ratio}배, 저역={f.low_band_norm:.3f})"
    if rule == "old":
        return f"온셋 절대 문턱(≤{_OLD_BREAK_MAX_ONSET_COUNT}개, 온셋={f.onset_count})"
    return f"저역 완화(dip)+온셋 비율 (저역={f.low_band_norm:.3f}, 온셋={f.onset_count})"


def build_candidate_rows(
    features: list[BarFeatures],
    bar_boundaries_ms: list[int],
    unsupported: list[tuple[str, int]],
    *,
    rule: str = "new",
) -> list[dict]:
    """근거 없음 검출 각각에 대해 보고서 행(마디·시각·종류·분기·특징값)을 만든다."""
    by_bar = {f.bar: f for f in features}
    boundary_by_bar = {i + 1: ms for i, ms in enumerate(bar_boundaries_ms)}
    rows: list[dict] = []
    for kind, bar in unsupported:
        f = by_bar[bar]
        downbeat_s = boundary_by_bar.get(bar)
        downbeat_s = downbeat_s / 1000.0 if downbeat_s is not None else None
        rows.append(
            {
                "bar": bar,
                "kind": kind,
                "downbeat_s": downbeat_s,
                "downbeat_mmss": _format_mmss(downbeat_s) if downbeat_s is not None else "-",
                "branch": _branch_description(f, kind, rule=rule),
                "volume_norm": f.volume_norm,
                "low_band_norm": f.low_band_norm,
                "onset_count": f.onset_count,
            }
        )
    rows.sort(key=lambda r: r["bar"])
    return rows


def _render_table(rows: list[dict], *, verdict_column: bool) -> list[str]:
    base_header = (
        "| 마디 | 시각(초) | 시각(m:ss) | 종류 | 판정 분기 | "
        "음량(중앙값=1) | 저역(중앙값=1) | 온셋 개수 |"
    )
    header = base_header + (" 감독 판정 |" if verdict_column else "")
    sep = "|---|---|---|---|---|---|---|---|" + ("---|" if verdict_column else "")
    lines = [header, sep]
    if not rows:
        empty = "| - | - | - | - | - | - | - | - |" + ("  |" if verdict_column else "")
        lines.append(empty)
        return lines
    for r in rows:
        line = (
            f"| {r['bar']} | {r['downbeat_s']:.2f} | {r['downbeat_mmss']} | {r['kind']} | "
            f"{r['branch']} | {r['volume_norm']:.3f} | {r['low_band_norm']:.3f} | "
            f"{r['onset_count']} |"
        )
        if verdict_column:
            line += "  |"
        lines.append(line)
    return lines


def render_markdown(rows: list[dict], old_rows: list[dict]) -> str:
    lines = [
        "# M3 감독 귀 확인 후보 (카드 t535, AC-LDBARMAP-007 정밀도 조건)",
        "",
        '각 항목은 "오검출"도 "정답지 누락"도 아니다 — 최종 판정은 감독의 귀가 정한다.',
        "",
        "## 새 규칙(카드 t535) — 근거 없음 검출",
        "",
        *_render_table(rows, verdict_column=True),
        "",
        "## 참고 — 구 규칙(카드 t535 이전, 절대 온셋 상수) 근거 없음 검출",
        "",
        "새 규칙이 치운 거짓 양성이 실제로 진짜 브레이크였는지 비교용으로만 남긴다.",
        "",
        *_render_table(old_rows, verdict_column=False),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    features, bar_boundaries_ms = load_fixture()
    by_bar = {f.bar: f for f in features}
    evidence = parse_precision_evidence()

    events = classify_bar_events(features)
    detected = [(e.kind, e.start_bar) for e in events if e.kind in ("break", "kick_entry")]
    result = event_precision(detected, evidence)
    rows = build_candidate_rows(features, bar_boundaries_ms, result.unsupported)

    old_detected = old_rule_detected_events(by_bar)
    old_result = event_precision(old_detected, evidence)
    old_rows = build_candidate_rows(features, bar_boundaries_ms, old_result.unsupported, rule="old")

    markdown = render_markdown(rows, old_rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(
        f"새 규칙 정밀도 {result.supported}/{result.total}({result.rate_pct:.1f}%), "
        f"근거 없음 {len(rows)}건 — 구 규칙(참고) 정밀도 {old_result.supported}/{old_result.total}"
        f"({old_result.rate_pct:.1f}%), 근거 없음 {len(old_rows)}건 → {OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
