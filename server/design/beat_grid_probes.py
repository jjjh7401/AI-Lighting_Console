"""M1 콘솔 확인 프로브 9항목 판정 — progress.md를 그대로 읽는다 (카드 t537,
REQ-LDBEAT-003(b)).

`beatGridM1Probes.ts`(카드 t534가 손으로 옮긴 TS 상수)가 겪은 낡음 문제를
반복하지 않는다 — 이 모듈은 progress.md의 M1 표를 **그 자리에서** 파싱해
돌려준다. 해석·매핑·추측은 하지 않는다: 판정 칸의 글자를 굵게 표시(``**``)
만 벗겨 그대로 돌려준다(예: ``"통과(구조)"``, ``"미확인"``, ``"움직임 없음"``).

실패-경로(REQ-LDBEAT-003(b)/AC-LDBEAT-009(d)): 표가 없거나 파싱할 수
없으면 9항목 전부 `UNCONFIRMED_STATUS`("미확인")로 떨어진다 — 지어낸
PASS는 0건이다. 콘솔 접촉 0건 — 이 모듈은 파일 하나만 읽는다.
"""

from __future__ import annotations

from pathlib import Path

from server.resources import resource_base

__all__ = [
    "DEFAULT_PROBE_IDS",
    "UNCONFIRMED_STATUS",
    "default_progress_md_path",
    "parse_m1_probe_table",
    "read_m1_probe_results",
    "read_m1_probe_results_from_path",
]

#: REQ-LDBEAT-001~003의 9항목(⑩⑪은 v3 재승인 때 추가된 확장 항목이라
#: 이 SPEC의 게이트 대상이 아니다 — 카드 t537 범위는 1~9만).
DEFAULT_PROBE_IDS: tuple[int, ...] = tuple(range(1, 10))

#: 표가 없거나·그 항목 행이 없거나·파싱할 수 없을 때의 정직한 기본값.
#: progress.md 자신이 쓰는 네 갈래(통과/부분/미확인/움직임 없음) 중
#: "판정 근거 없음"과 글자가 같다(§M1 "판정 갈래" 정의, progress.md).
UNCONFIRMED_STATUS = "미확인"

_CIRCLED_DIGIT_BASE = 0x2460  # ①

_PROGRESS_MD_RELATIVE = Path(".moai") / "specs" / "SPEC-LDBEAT-001" / "progress.md"


def _circled_digit_value(ch: str) -> int | None:
    """``①``~``⑨`` 한 글자를 1~9로. 그 밖의 글자는 ``None``(추측하지 않음)."""
    offset = ord(ch) - _CIRCLED_DIGIT_BASE
    if 0 <= offset <= 8:
        return offset + 1
    return None


def parse_m1_probe_table(progress_md_text: str) -> dict[int, str]:
    """progress.md 전체 텍스트에서 M1 9항목 표의 판정 칸을 그대로 돌려준다.

    표 모양(``| 항목 | 판정 | 무엇을 봤나 | 근거 |``)의 각 데이터 줄에서
    1번째 칸(항목)이 ``①``~``⑨``로 시작하면, 2번째 칸(판정)의 텍스트를
    ``**`` 굵게 표시만 벗겨 그 항목 번호에 매단다. ⑩⑪(확장 항목)·헤더·
    구분선·다른 표의 줄은 무시한다. 찾지 못한 항목은 이 딕셔너리에
    **없다**(호출자가 `read_m1_probe_results`로 "미확인"을 채운다) —
    빈 결과가 "전부 미확인"을 뜻하는 게 아니라, 호출자가 그렇게
    해석하도록 비워 두는 것뿐이다.
    """
    results: dict[int, str] = {}
    for line in progress_md_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or not cells[0]:
            continue
        probe_id = _circled_digit_value(cells[0][0])
        if probe_id is None:
            continue
        status_text = cells[1].replace("**", "").strip()
        if not status_text:
            continue
        results[probe_id] = status_text
    return results


def read_m1_probe_results(progress_md_text: str | None) -> dict[int, str]:
    """1~9항목 전부를 채운 완전한 딕셔너리로 돌려준다 — 표에 없는 항목,
    `progress_md_text`가 `None`(파일 부재)이거나 파싱 결과가 빈 항목은
    모두 `UNCONFIRMED_STATUS`다(AC-LDBEAT-009(d), 지어낸 PASS 0건)."""
    parsed = parse_m1_probe_table(progress_md_text) if progress_md_text else {}
    return {probe_id: parsed.get(probe_id, UNCONFIRMED_STATUS) for probe_id in DEFAULT_PROBE_IDS}


def default_progress_md_path() -> Path:
    """이 SPEC의 progress.md 경로 — dev 체크아웃과 PyInstaller 번들 둘 다
    `server.resources.resource_base`로 가른다(frozen 번들은 `.moai/`를
    담지 않을 수 있다 — 그때는 `read_m1_probe_results_from_path`의
    파일-부재 경로가 정직하게 "미확인"으로 떨어진다)."""
    return resource_base() / _PROGRESS_MD_RELATIVE


def read_m1_probe_results_from_path(path: Path) -> dict[int, str]:
    """`path`를 읽어 9항목을 돌려준다 — 파일이 없거나 못 읽으면(권한·I/O
    오류 등) 역시 전부 "미확인"(REQ-LDBEAT-003(b) 실패-경로, 예외를
    밖으로 내지 않는다)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = None
    return read_m1_probe_results(text)
