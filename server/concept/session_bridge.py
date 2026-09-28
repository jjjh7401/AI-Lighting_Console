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
근거 등급(``evidence``)은 :func:`server.concept.evidence.evidence_for_row` 가
행 종류·구간·트리거·회차로 매긴다(카드 t457, REQ-022/071) — 조문이 받치지
않는 행은 ``None`` 이다.
"""

from __future__ import annotations

from collections.abc import Sequence

from server.concept.color_strip import render_concept_bullet
from server.concept.compile import compile_song
from server.concept.cue_model import CueState
from server.concept.description import describe
from server.concept.evidence import evidence_for_row
from server.concept.gates import SongBuild, build_song, evaluate_song
from server.concept.headroom import compute_cue_headroom
from server.design.interview import (
    Q1_CONCEPT,
    SOURCE_FREE_TEXT,
    SOURCE_OPTION,
    SOURCE_PRE_SPECIFIED,
)
from server.design.song_plan import UnifiedSongLightingPlan

__all__ = [
    "CONCEPT_BULLET_AUTO_DRAFT_REASON",
    "GLANCE_RULE",
    "GLANCE_STAGES",
    "build_concept_report",
    "build_concept_report_from_songcue_sections",
    "concept_bullet",
    "glance_stages",
]

#: 카드 t485 — 인과 불릿 원천(인터뷰 Q1 기록의 ``source``)별 화면 출처 표식.
#: 여기 없는 출처(``auto_draft`` 등)는 감독이 한 말이 아니므로 원문으로 싣지 않는다.
_CONCEPT_BULLET_ORIGINS = {
    SOURCE_FREE_TEXT: "인터뷰 Q1 — 직접 입력",
    SOURCE_OPTION: "인터뷰 Q1 — 제안 중 선택",
    SOURCE_PRE_SPECIFIED: "인터뷰 Q1 — 요청 문장에서 읽음",
}
CONCEPT_BULLET_AUTO_DRAFT_REASON = (
    "Q1 컨셉에 감독 답이 없다 — 빈 답이라 첫 제안이 자동 초안으로 들어갔다(원문 아님)"
)

#: 카드 t482 — 컨셉 패널 "한눈에" 5단계(REQ-097, 감독 채택 DESIGN.md §4.2 의 이름).
GLANCE_STAGES = ("시작", "쌓기", "강조", "예고", "정점→마무리")
#: 구간 → 단계 배정 규칙의 출처 표식. DESIGN.md §4.2 는 배정 규칙을 적지 않았고
#: (「모든 수치는 큐 데이터에서 파생」만 요구), 아래 규칙은 리드가 2026-09-28 에
#: 제안한 것이다 — 감독 확인 전이라 화면이 이 표식을 그대로 보인다.
GLANCE_RULE = "lead-proposed-2026-09-28"

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
    # 카드 t482 — 큐 설명(REQ-023/070, ``describe()``)의 "직전 상태". 첫 큐는
    # ``resolver.resolve_sequence`` 가 쓰는 초기 상태와 같다.
    prev_state = CueState(dim={}, color=None, pos="home", motion=0)
    for raw, row, verdict, state in zip(
        build.rows, build.table, build.mib, build.states, strict=True
    ):
        if row.kind == "section":
            position = seen_sections
            seen_sections += 1
        description = describe(
            prev_state,
            state,
            raw.get("ops", ()),
            compute_cue_headroom(state),  # type: ignore[arg-type]
        )
        prev_state = state
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
                "evidence": evidence_for_row(row.kind, row.section, row.trigger, row.occurrence),
                "screen_position": (position if paired and row.kind != "safety" else None),
                # 카드 t461 — REQ-093 (4) 헤드룸 경고의 원천. 컨셉 그룹 로스터
                # (density.GROUP_ROSTER) 기준 꺼진 그룹 수, headroom 재사용.
                "unused_groups": compute_cue_headroom(state).unused_groups,
                # 카드 t482 — 해석된 상태 차이로만 조립한 한 문장(지어낸 문장 0).
                "description": description,
            }
        )
    reason = (
        None
        if paired
        else f"컨셉 구간 행 {section_count}개와 화면 구간 {screen_count}개가 짝이 안 맞는다"
    )
    return rows, {"available": paired, "reason": reason}


#: 카드 t461 — 해제 전까지 아껴 두는 효과 그룹(gates.py ``_EFFECT_GROUPS`` 와 같은 둘).
_RESERVE_GROUPS: tuple[str, ...] = ("BLIND", "STROBE")


def _concept_reserve(
    build: SongBuild, rows: Sequence[dict[str, object]]
) -> list[dict[str, object]]:
    """카드 t461 — REQ-090(BLIND 잠금)·REQ-093 (3)의 서버 원천.

    리저브 그룹은 해석된 큐 상태에서 **처음 켜지는 행**이 해제 큐다(한 번도 안
    켜지면 ``released_q`` 가 None). 유보색은 입력(``raw_song["reserved"]``)이
    선언했을 때만 나오고, 해제 큐는 입력 색으로 판정한 곡(``color_source ==
    "input"``)에서만 찾는다 — 상수 팔레트 색은 증거가 아니다(카드 t444).
    ``screen_position`` 은 그 행의 화면 구간(짝짓기가 안 됐으면 None).
    """

    def released(predicate) -> tuple[int | None, int | None]:
        for row, state, table_row in zip(rows, build.states, build.table, strict=True):
            if predicate(state, table_row):
                return int(row["q"]), row["screen_position"]  # type: ignore[return-value]
        return None, None

    items: list[dict[str, object]] = []
    for name in _RESERVE_GROUPS:
        q, position = released(lambda state, _row, name=name: state.dim.get(name, 0) > 0)
        items.append({"name": name, "kind": "group", "released_q": q, "screen_position": position})
    for color in build.reserved:
        if build.color_source == "input":
            wanted = color.casefold()
            q, position = released(
                lambda _state, row, wanted=wanted: any(c.casefold() == wanted for c in row.colors)
            )
        else:
            q, position = None, None
        items.append({"name": color, "kind": "color", "released_q": q, "screen_position": position})
    return items


def glance_stages(roles: Sequence[str | None]) -> dict[str, object]:
    """카드 t482 — "한눈에" 5단계에 어느 화면 구간(0부터 위치)이 드는지 정한다.

    규칙(``GLANCE_RULE``, 리드 제안 — 감독 확인 전). ``roles`` 는 화면 구간
    순서의 아크 역할(``SectionDecision.role``: intro/verse/chorus/bridge/finale)
    이다. 첫 후렴 f, 마지막 후렴 l, 끝에서 둘째 후렴 p 라 하면:

    - 시작 = f 앞의 intro 구간
    - 쌓기 = f 앞의 나머지 구간(verse·pre 등)
    - 강조 = f 부터 p 까지(사이의 verse 포함) — 마지막 후렴을 뺀 후렴 구간
    - 예고 = p 와 l 사이 구간(마지막 후렴 직전 bridge/verse)
    - 정점→마무리 = l 부터 곡 끝까지(outro/finale 포함)

    후렴이 없으면 끝의 finale 연속 구간을 정점→마무리로, 나머지를 시작/쌓기로
    둔다. 구간이 없는 단계는 빈 위치 목록과 사유를 낸다. 역할이 하나라도
    없으면(서버가 판독하지 않은 곡) 배정하지 않는다 — 지어내지 않는다.
    카드 수치(Q 범위·시간·색·밝기)는 여기서 만들지 않는다: UI 가 CUE SHEET 와
    같은 구간 데이터에서 계산한다(REQ-097, 원천을 둘로 나누지 않는다).
    """
    if not roles or any(role is None for role in roles):
        return {
            "available": False,
            "rule": GLANCE_RULE,
            "reason": "구간 역할(role) 원천이 없다 — 서버가 아크 역할을 판독하지 않은 곡",
            "stages": [],
        }
    n = len(roles)
    choruses = [i for i, role in enumerate(roles) if role == "chorus"]
    buckets: dict[str, list[int]] = {stage: [] for stage in GLANCE_STAGES}
    reasons: dict[str, str | None] = {stage: None for stage in GLANCE_STAGES}
    if choruses:
        first, last = choruses[0], choruses[-1]
        buckets["시작"] = [i for i in range(first) if roles[i] == "intro"]
        buckets["쌓기"] = [i for i in range(first) if roles[i] != "intro"]
        buckets["정점→마무리"] = list(range(last, n))
        if len(choruses) >= 2:
            before_last = choruses[-2]
            buckets["강조"] = list(range(first, before_last + 1))
            buckets["예고"] = list(range(before_last + 1, last))
            if not buckets["예고"]:
                reasons["예고"] = "마지막 후렴 바로 앞도 후렴이다"
        else:
            reasons["강조"] = "후렴이 하나뿐이라 그 후렴을 정점으로 셌다"
            reasons["예고"] = "끝에서 둘째 후렴이 없다"
    else:
        tail_start = n
        while tail_start > 0 and roles[tail_start - 1] == "finale":
            tail_start -= 1
        buckets["시작"] = [i for i in range(tail_start) if roles[i] == "intro"]
        buckets["쌓기"] = [i for i in range(tail_start) if roles[i] != "intro"]
        buckets["정점→마무리"] = list(range(tail_start, n))
        reasons["강조"] = reasons["예고"] = "후렴(chorus) 구간이 없다"
    for stage in GLANCE_STAGES:
        if not buckets[stage] and reasons[stage] is None:
            reasons[stage] = "이 단계에 드는 구간이 없다"
    return {
        "available": True,
        "rule": GLANCE_RULE,
        "reason": None,
        "stages": [
            {"stage": stage, "positions": buckets[stage], "reason": reasons[stage]}
            for stage in GLANCE_STAGES
        ],
    }


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
        reserve = _concept_reserve(build, rows)
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
        "reserve": reserve,
    }


def concept_bullet(records: Sequence[object]) -> dict[str, object]:
    """카드 t485 — REQ-013·032·080 인과 불릿 원문. ``records`` 는
    ``DirectorInterview.audit_trail()`` 이다.

    원천은 인터뷰 Q1(컨셉) 기록 하나다 — 워크시트 YAML 로더(``load_worksheet``)는 앱
    경로에서 불리지 않는다. 감독이 실제로 준 글자(직접 입력·제안 선택·요청 문장)만
    바이트 그대로 싣는다(``render_concept_bullet``, 요약·윤문 없음). 빈 답으로 첫
    제안이 들어간 자동 초안은 감독 말이 아니므로 원문으로 싣지 않고 사유를 낸다.
    """
    record = next((r for r in records if getattr(r, "step", None) == Q1_CONCEPT), None)
    if record is None:
        return {"available": False, "reason": "인터뷰 Q1(컨셉) 기록이 없다"}
    source = getattr(record, "source", None)
    origin_label = _CONCEPT_BULLET_ORIGINS.get(source) if isinstance(source, str) else None
    if origin_label is None or not getattr(record, "confirmed", False):
        return {"available": False, "reason": CONCEPT_BULLET_AUTO_DRAFT_REASON}
    free_text = getattr(record, "free_text", None)
    text = free_text if isinstance(free_text, str) else str(getattr(record, "value", ""))
    if not text.strip():
        return {"available": False, "reason": "Q1 컨셉 답이 비어 있다"}
    return {
        "available": True,
        "text": render_concept_bullet(text),
        "origin": source,
        "origin_label": origin_label,
    }


def build_concept_report(
    plan: UnifiedSongLightingPlan, *, color_usage: str = "modulate"
) -> dict[str, object]:
    """REQ-073/074 §④b — session.py 경로(``UnifiedSongLightingPlan``)
    어댑터. ``color_usage`` 는 감독의 Q2B 답(``"per_chorus"`` 면 G7 n/a).
    자세한 원칙은 모듈 독스트링 참고."""
    if not plan.sections:
        return {"available": False, "reason": "구간이 없다"}
    report = _run_concept_pipeline(
        plan.song_title,
        plan.music_profile.bpm,
        _raw_sections(plan),
        color_usage=color_usage,
    )
    # 카드 t482 — "한눈에" 단계 배정(역할만 본다). 리포트를 못 만든 경우의
    # ``{available: False, reason}`` 두 키 계약은 그대로 둔다.
    if report.get("available"):
        report["glance"] = glance_stages([decision.role for decision in plan.sections])
    return report


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
    report = _run_concept_pipeline(
        song_title, bpm, _raw_sections_from_pairs(list(sections), palettes)
    )
    # 카드 t482 — 사다리 경로에는 아크 역할 원천이 없다(이름+회차 쌍만 온다).
    if not report.get("available"):
        return report
    report["glance"] = {
        "available": False,
        "rule": GLANCE_RULE,
        "reason": "이 경로(사다리 prepare_songcue)에는 구간 역할(role) 원천이 없다",
        "stages": [],
    }
    return report
