"""세션/툴 경로 ↔ 컨셉 파이프라인 다리 — SPEC-LDDESIGN-001 M6 §④b
(REQ-LDDESIGN-073·074, 카드 t439).

두 진입점이 각각 다른 큐 생성 모델을 쓰므로(REQ-003 이 아직 하나로
합치지 않은 상태 — M0 은 `bpm=density_bpm` 배선만 끝냈다, 두 경로
자체의 통합은 이 카드 범위 밖) 어댑터도 둘이다:

- :func:`build_concept_report` — ``server.web.session`` 의
  :class:`~server.design.song_plan.UnifiedSongLightingPlan` 에서 뽑는다
  (``TimestampedSection.label``/``start_ms``/``end_ms``).
- :func:`build_concept_report_from_songcue_sections` —
  ``server.orchestrator.tools`` 의 ``prepare_songcue``(사다리 경로,
  ``server.looks.songcue.SongCueSection``)에서 뽑는다. 이쪽은
  ``label``+``instance`` 가 이미 분리돼 있어(``SongCueSection``
  독스트링 — "라벨 + 회차") gates.py 가 기대하는 ``baseline_name``
  형식("Chorus 2" 류)을 ``f"{label} {instance}"`` 로 직접 조립한다 —
  session.py 경로보다 오히려 더 정확한 원천이다.

두 어댑터 모두 (baseline_name, start "M:SS", end "M:SS") 목록을 만들어
공통 실행기(``_run_concept_pipeline``)로 넘긴다 — 그 결과(13게이트·
MIB·린트/에너지 요약)를 JSON 직렬화 가능한 "컨셉 리포트" 딕셔너리로
묶는다.

**색(카드 t444).** 두 어댑터는 각 구간이 실제로 내는 색 이름을 원시
구간의 ``palette`` 로 실어 넘긴다 — 컨셉 게이트의 색 판정(G2·G5 흰색
조건·G6·G7)은 그 색으로만 한다(``server/concept/gates.py`` 모듈
독스트링). session.py 경로는 구간 결정의 팔레트(``SectionDecision.
palette.colors`` — 주색, 보조색 순. 콘솔로는 주색이 ``_song_color_value_
lines``, 보조색이 큐시트 반영의 back 그룹 절로 나간다)를, tools.py
경로는 감독 주색 덮어쓰기가 실제로 적용된 구간의 주색 한 개를 싣는다
(그 경로는 보조색을 내지 않는다 — ``_override_songcue_main_color``
독스트링). 색을 싣지 못한 구간은 빈 목록이고, 곡 전체에 색이 없으면
색 게이트는 n/a 다.

**콘솔 명령을 바꾸지 않는다** — 이 다리는 ADDITIVE 다. 기존 두 진입점이
오늘 내는 콘솔 명령·번들 자체는 이 파일이 손대지 않는다(REQ-073 은
컴파일 경로가 기존 하류를 재사용하는지를 검증하지, 배선 경로의 출력을
바꾸라고 요구하지 않는다). 실패는 예외를 올리지 않는다 — ``available:
False`` 와 사유를 담은 리포트를 낸다(가짜 값을 만들지 않는다, §4 B군과
같은 원칙 — 계산할 수 없는 것을 지어내지 않는다).

**알려진 격차(정직하게 기록 — 안 한 것을 못 한 것처럼 적지 않는다)**:

- ``TimestampedSection.label``(session.py 경로)은 컨셉 v2 의 9종 닫힌
  구간 어휘(REQ-005)와 반드시 일치하지 않는다 — 오디오 확정 경로는
  중립 이름(``S1`` 류)을, 직접 지시 경로는 자유 라벨을 쓴다
  (``server/spatial/position_cuesheet.py`` ``PositionSheetSection``
  독스트링). :func:`server.concept.gates.remap_baseline_sections` 는
  Chorus/Verse/Bridge/Intro/Finale 패턴을 못 찾으면 이미
  "Rap/Solo/Dance Break" 로 떨어뜨린다(gates.py 기존 동작 — 이 다리가
  새로 만든 실패 모드가 아니다) — 재매핑 품질이 곡마다 다를 수 있다는
  뜻이다.
- 마지막 구간의 끝 시각을 모르면(session.py 경로의 ``end_ms is None``,
  tools.py 경로는 애초에 ``end_ms`` 필드 자체가 없음) 이 다리는 마지막
  구간 시작 + 고정 꼬리(``_FALLBACK_TAIL_MS``)를 쓴다 — 실제 곡 길이가
  아니라 자리표시자다.
- BPM 이 선언되지 않았으면 컨셉 파이프라인을 아예 돌리지 않는다 —
  ``density.bar_seconds`` 가 마디 계산의 전제로 삼는 값이 기본값(120)
  추정이면 판정 자체가 근거 없는 값 위에 선다.
- (해소됨, 카드 t452 · PR #500) 곡이 (프레이즈 층의) ``cue_only`` 큐 바로
  뒤에서 끝나면(Outro 없이 Chorus 로 곡이 끝나는 등) gates.py 의 g9 검사가
  ``VocabError`` 를 던졌다 — 기준 이름을 마지막 track 행에 붙여 고쳤다
  (``test_concept_session_bridge.py`` ``TestSongEndingOnCueOnlyPhraseIsJudged``).

**행 단위 표(카드 t455).** 리포트의 ``rows`` 는 컨셉 큐 한 줄에 한 행이고,
``screen_position`` 으로 화면 구간(이 다리에 넘어온 구간 목록의 0-base
위치 — ``_song_timeline_payload`` 의 ``sections`` 와 같은 순서)과 짝을
짓는다. 짝 규칙(리드 승인 2026-09-23): k번째 section 행 ↔ 구간 k(순서
기준), phrase 행은 바로 앞 section 행의 구간, safety 행은 ``None``, 원샷은
ts 가 같은 section 행에 붙는다. 시각 기준은 쓰지 않는다 —
:func:`_mmss_from_ms` 가 ms 를 초 단위로 버리므로 15.5초에 시작하는 구간의
행이 ts 15 가 되어 앞 구간에 붙는다. 이름+회차 기준도 쓰지 않는다 —
``Pre-Chorus`` 는 화면 구간 이름이 아니고, 재매핑이 이름을 바꾼다(예:
``Outro`` → ``Rap/Solo/Dance Break``). section 행 수와 구간 수가 다르면
짝을 짓지 않는다(``row_pairing.available: False``, 모든 행 ``None``).
근거 등급(``evidence``)은 큐마다 등급을 매기는 생산자가 없어 전 행
``None`` 이다(생산자 배선은 카드 t457).
"""

from __future__ import annotations

from collections.abc import Sequence

from server.concept.compile import compile_song
from server.concept.gates import SongBuild, build_song, evaluate_song
from server.design.song_plan import UnifiedSongLightingPlan

__all__ = ["build_concept_report", "build_concept_report_from_songcue_sections"]

#: 마지막 구간의 끝 시각을 모를 때 쓰는 고정 꼬리(밀리초) — 실제 곡
#: 길이를 아는 자리가 아니므로 자리표시자임을 리포트에도 남긴다.
_FALLBACK_TAIL_MS = 15_000


def _mmss_from_ms(ms: int) -> str:
    """``gates.remap_baseline_sections`` 가 기대하는 "M:SS" 문자열로
    바꾼다(``gates._mmss`` 의 역함수)."""
    total_seconds = max(0, ms) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _raw_sections(plan: UnifiedSongLightingPlan) -> list[dict[str, object]]:
    sections = plan.sections
    raw: list[dict[str, object]] = []
    for i, decision in enumerate(sections):
        start_ms = decision.section.start_ms
        end_ms = decision.section.end_ms
        if end_ms is None:
            end_ms = (
                sections[i + 1].section.start_ms
                if i + 1 < len(sections)
                else start_ms + _FALLBACK_TAIL_MS
            )
        raw.append(
            {
                "baseline_name": decision.section.label,
                "start": _mmss_from_ms(start_ms),
                "end": _mmss_from_ms(end_ms),
                "palette": list(decision.palette.colors),
            }
        )
    return raw


def _raw_sections_from_pairs(
    pairs: Sequence[tuple[str, int]],
    palettes: Sequence[Sequence[str]] | None = None,
) -> list[dict[str, object]]:
    """``(baseline_name, start_ms)`` 시간순 목록에서 raw_song 구간을
    낸다 — 원천(``SongCueSection``)에 ``end_ms`` 필드 자체가 없으므로
    다음 구간 시작(또는 마지막 구간은 고정 꼬리)에서 끝을 역산한다."""
    raw: list[dict[str, object]] = []
    for i, (baseline_name, start_ms) in enumerate(pairs):
        end_ms = pairs[i + 1][1] if i + 1 < len(pairs) else start_ms + _FALLBACK_TAIL_MS
        item: dict[str, object] = {
            "baseline_name": baseline_name,
            "start": _mmss_from_ms(start_ms),
            "end": _mmss_from_ms(end_ms),
        }
        if palettes is not None:
            item["palette"] = list(palettes[i])
        raw.append(item)
    return raw


def _concept_rows(
    build: SongBuild, *, screen_count: int
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """카드 t455 — 컨셉 큐 행 표와 화면 구간 짝짓기(규칙은 모듈 독스트링)."""
    section_count = sum(1 for row in build.table if row.kind == "section")
    paired = section_count == screen_count
    shots = {
        float(shot["ts"]): {"shot": shot["shot"], "target": shot["target"]}
        for shot in build.one_shots
    }
    rows: list[dict[str, object]] = []
    position: int | None = None
    seen_sections = 0
    for row, verdict in zip(build.table, build.mib, strict=True):
        if row.kind == "section":
            position = seen_sections
            seen_sections += 1
        rows.append(
            {
                "q": row.q,
                "ts": row.ts,
                "kind": row.kind,
                "section": row.section,
                "occurrence": row.occurrence,
                "trigger": row.trigger,
                "tracking": row.tracking,
                "mib": None if verdict is None else verdict.status,
                "one_shot": shots.get(row.ts) if row.kind == "section" else None,
                "evidence": None,
                "screen_position": (position if paired and row.kind != "safety" else None),
            }
        )
    reason = (
        None
        if paired
        else f"컨셉 구간 행 {section_count}개와 화면 구간 {screen_count}개가 짝이 안 맞는다"
    )
    return rows, {"available": paired, "reason": reason}


def _run_concept_pipeline(
    song_title: str,
    bpm: float | None,
    raw_sections: list[dict[str, object]],
    *,
    color_usage: str = "modulate",
) -> dict[str, object]:
    """두 어댑터의 공통 실행기 — REQ-073/074 §④b. 콘솔에 아무것도 쓰지
    않는다(순수 계산, 다른 ``server/concept/*`` 모듈과 같은 원칙). 실패는
    예외로 전파하지 않고 ``available: False`` 리포트로 되돌린다 — 이
    리포트는 부가 정보이지 기존 콘솔 명령 경로의 전제조건이 아니다
    (ADDITIVE 원칙, 호출자는 이 함수가 실패해도 오늘의 콘솔 명령 생성을
    그대로 계속한다)."""
    if bpm is None:
        return {
            "available": False,
            "reason": "BPM이 선언되지 않았다 — 컨셉 파이프라인의 마디 계산 전제가 없다",
        }
    if not raw_sections:
        return {"available": False, "reason": "구간이 없다"}

    try:
        raw_song = {"song": song_title, "bpm": bpm, "sections": raw_sections}
        build = build_song(raw_song)
        gates = evaluate_song(raw_song, color_usage=color_usage)
        compiled = compile_song(build)
        rows, row_pairing = _concept_rows(build, screen_count=len(raw_sections))
    except Exception as error:  # noqa: BLE001 — 컨셉 리포트는 부가 정보다,
        # 실패해도 기존 콘솔 명령 경로를 막지 않는다(ADDITIVE 원칙,
        # 모듈 독스트링 참고).
        return {"available": False, "reason": f"컨셉 파이프라인 실패: {error}"}

    return {
        "available": True,
        "gates": {
            name: {"passed": result.passed, "detail": result.detail}
            for name, result in gates.items()
        },
        "mib": [
            {"status": verdict.status} if verdict is not None else None for verdict in build.mib
        ],
        "lint_finding_count": len(compiled.lint_report.findings),
        "lint_disabled_rule_count": len(compiled.lint_report.disabled_rules),
        "energy_report_count": len(compiled.energy_reports),
        "rows": rows,
        "row_pairing": row_pairing,
    }


def build_concept_report(
    plan: UnifiedSongLightingPlan, *, color_usage: str = "modulate"
) -> dict[str, object]:
    """REQ-073/074 §④b — session.py 경로(``UnifiedSongLightingPlan``)
    어댑터. ``color_usage`` 는 감독의 Q2B 답(``"per_chorus"`` 면 G7 n/a).
    자세한 원칙은 모듈 독스트링 참고."""
    if not plan.sections:
        return {"available": False, "reason": "구간이 없다"}
    return _run_concept_pipeline(
        plan.song_title,
        plan.music_profile.bpm,
        _raw_sections(plan),
        color_usage=color_usage,
    )


def build_concept_report_from_songcue_sections(
    song_title: str,
    bpm: float | None,
    sections: Sequence[tuple[str, int]],
    *,
    palettes: Sequence[Sequence[str]] | None = None,
) -> dict[str, object]:
    """REQ-073/074 §④b — tools.py 경로(``prepare_songcue``, 사다리
    ``build_songcue_bundle``) 어댑터. ``sections`` 는 시간순
    ``(baseline_name, start_ms)`` 쌍이다 — 호출자가
    ``SongCueSection.label``/``.instance`` 를 ``f"{label}
    {instance}"`` 로 합쳐 넘긴다(gates.py 의 "Chorus 2" 류 baseline_name
    형식과 맞춘다; ``label``/``instance`` 분리가 이미 이 형식의 근원이다
    — ``songcue.py`` ``SongCueSection`` 독스트링). ``palettes`` 는
    ``sections`` 와 같은 순서의 구간별 실제 색 이름 목록이다(카드 t444,
    생략하면 입력에 색 없음). 자세한 원칙은 모듈 독스트링 참고."""
    if not sections:
        return {"available": False, "reason": "구간이 없다"}
    if palettes is not None and len(palettes) != len(sections):
        # 예외를 밖으로 내지 않는다(모듈 독스트링 ADDITIVE 원칙) — 색이
        # 어느 구간 것인지 모르면 짝을 추측하지 않는다.
        return {
            "available": False,
            "reason": f"구간 색 {len(palettes)}개가 구간 {len(sections)}개와 짝이 안 맞는다",
        }
    return _run_concept_pipeline(
        song_title, bpm, _raw_sections_from_pairs(list(sections), palettes)
    )
