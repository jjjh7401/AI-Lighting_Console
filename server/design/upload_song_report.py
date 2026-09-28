"""업로드 길(``prepare_songcue``) 보고서 — 조립기 번들 기준 (카드 t480).

업로드 길이 룩 라이브러리 조립기(``build_songcue_bundle``)를 쓰던 때의 보고서
(``server/looks/songcue_report.py``)는 그 번들의 구간·룩 판정 모양에 묶여 있었다.
조립기(``compose_song_cue_bundle``)로 합치면서 보고는 이 모듈이 한다. 지키는 규율은
같다:

* 명령 수신은 효과의 증거가 아니다 — 저장 뒤 시퀀스를 **되읽어** 계획한 큐와 대조한다.
* 되읽기가 안 왔으면 「없다」가 아니라 「못 읽었다」다(``requery`` 가 ``None``).
* 시스템 큐(``OffCue``·``CueZero`` — 번호가 없거나 1 미만)는 대조에서 뺀다
  (``songcue_report._observed_cues`` 와 같은 M0 실측 규율).
* 감독이 채팅에서 스쳐 읽는 고지(``to_operator_notice``)는 빠진 것이 있을 때만 말한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.design.song_cue_render import _safe_song_cue_name
from server.looks.songcue_report import PROPERTY_UNOBSERVED_NOTE


def stored_cues(bundle) -> tuple[object, ...]:
    """콘솔에 ``Store`` 줄이 나가는 큐 — 명령 생성기(``reviewed_song_commands``)와
    같은 판정: 포지션 프리셋도 밝기도 없는 큐는 건너뛴다."""
    return tuple(
        cue
        for cue in bundle.cues
        if cue.position.stored is not None or cue.dimmer.key_pct is not None
    )


def _cue_key(number: float) -> str:
    return f"{float(number):g}"


def _observed_cues(payload: Mapping[str, object]) -> list[dict[str, object]]:
    children = payload.get("children")
    if not isinstance(children, list):
        return []
    observed: list[dict[str, object]] = []
    for child in children:
        if not isinstance(child, Mapping) or child.get("class") != "Cue":
            continue
        number = child.get("cueNo")
        name = child.get("name")
        if (
            isinstance(number, int | float)
            and not isinstance(number, bool)
            and number >= 1
            and isinstance(name, str)
        ):
            observed.append({"cue_number": _cue_key(number), "name": name})
    return sorted(observed, key=lambda item: float(str(item["cue_number"])))


@dataclass(frozen=True)
class UploadSongReport:
    song_title: str
    sequence: int
    planned: tuple[dict[str, object], ...]
    skipped: tuple[dict[str, object], ...]
    not_executed: int
    failed: int
    notes: tuple[str, ...]
    requery: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "song_title": self.song_title,
            "sequence": self.sequence,
            "generated_cues": list(self.planned),
            "skipped_cues": list(self.skipped),
            "summary": {
                "generated_count": len(self.planned),
                "skipped_count": len(self.skipped),
                "not_executed": self.not_executed,
                "failed": self.failed,
            },
            "notes": list(self.notes),
            # 되읽기가 확인하는 것의 한계 — 옛 보고서와 같은 문장(값은 안 본다).
            "property_unobserved": PROPERTY_UNOBSERVED_NOTE,
            "requery": self.requery,
        }

    def to_korean(self) -> str:
        lines = [
            f"큐 {len(self.planned)}개 · 건너뜀 {len(self.skipped)}개 · "
            f"미실행 {self.not_executed}개 · 실패 {self.failed}개"
        ]
        if self.requery is not None:
            verdict = "일치" if self.requery["matched"] else "불일치"
            lines.append(
                f"되읽기 {verdict} — 계획 {len(self.requery['expected'])}개 · "
                f"콘솔 {len(self.requery['observed'])}개"
            )
        lines.extend(self.notes)
        return "\n".join(lines)

    def to_operator_notice(self) -> str:
        """감독이 읽는 한 문장 — 저장 못 한 큐가 있을 때만(옛 업로드 길 고지와 같은 계약,
        ``songcue_report.to_operator_notice``). 되읽기 결과는 ``to_korean`` 과
        ``requery`` 에 싣는다 — 옛 길도 고지에는 싣지 않았다."""
        if not self.skipped:
            return ""
        names = " · ".join(str(item["name"]) for item in self.skipped)
        return f"큐 {len(self.skipped)}건은 저장할 값이 없어 건너뛰었습니다({names})."


def build_upload_song_report(
    bundle,
    *,
    sequence: int,
    outcomes: Sequence[object] | None = None,
    requery_payload: Mapping[str, object] | None = None,
    notes: Sequence[str] = (),
) -> UploadSongReport:
    kept = stored_cues(bundle)
    kept_ids = {id(cue) for cue in kept}
    planned = tuple(
        {
            "sequence": sequence,
            "cue_number": _cue_key(cue.cue_number),
            "name": _safe_song_cue_name(cue.cue_name, cue.cue_number),
            "kind": cue.kind,
            # 구간의 D 레벨 — 이름이 밝기 단계를 정하지 않는다는 계약(t274)을 재는 값.
            "d_level": cue.d_level,
            "section_index": cue.section_index,
        }
        for cue in kept
    )
    skipped = tuple(
        {"cue_number": _cue_key(cue.cue_number), "name": cue.cue_name, "kind": cue.kind}
        for cue in bundle.cues
        if id(cue) not in kept_ids
    )
    statuses = [getattr(outcome, "status", outcome) for outcome in (outcomes or ())]
    requery = None
    if requery_payload is not None:
        observed = _observed_cues(requery_payload)
        expected = [{"cue_number": item["cue_number"], "name": item["name"]} for item in planned]
        requery = {"matched": observed == expected, "expected": expected, "observed": observed}
    return UploadSongReport(
        song_title=bundle.song_title,
        sequence=sequence,
        planned=planned,
        skipped=skipped,
        not_executed=statuses.count("not_executed"),
        failed=statuses.count("failed"),
        notes=tuple(note for note in notes if note),
        requery=requery,
    )
