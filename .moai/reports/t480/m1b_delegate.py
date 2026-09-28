"""t480 M1b — ChatSession 의 풀 판독 메서드 다섯을 console_slots 위임으로 바꾼다.

메서드 이름·시그니처·프로브 id 는 그대로 둔다(시험 대역이 이 메서드들을 묶어 쓴다).
본문만 `server.design.console_slots` 호출로 바꾸고, 도구 레지스트리를 콘솔 질의 함수로
감싸는 `_state_query` 를 하나 더한다.

실행(저장소 루트): `uv run python .moai/reports/t480/m1b_delegate.py`
"""

import ast
from pathlib import Path

SESSION = Path("server/web/session.py")
src = SESSION.read_text()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)

cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatSession")
methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}

NEW = {
    "_white_preset_slots": '''    def _white_preset_slots(self) -> dict[str, tuple[int, int] | str]:
        """카드 t453 — 흰색 이름 → 콘솔 컬러 프리셋 ``(풀, 슬롯)`` 또는 못 찾은 사유.

        카드 t480 — 본문은 ``server.design.console_slots.white_preset_slots``(업로드
        길 공용). 풀 번호 해석·풀 판독은 이 세션의 두 메서드를 그대로 넘긴다.
        """
        return white_preset_slots(
            self._resolve_named_pool_no,
            self._paged_pool_children,
            self._rig_paths.get("preset_pools", "DataPool/PresetPools"),
        )
''',
    "_phaser_slot_by_label": '''    def _phaser_slot_by_label(self, label: str) -> tuple[int, int] | None:
        """카탈로그 페이저 라벨 → 실기 ``(pool_no, slot)``, 못 찾으면 None(거부).

        카드 t480 — 본문은 ``server.design.console_slots.phaser_slot_by_label``
        (업로드 길 공용). 판독 규율은 그 독스트링에 있다.
        """
        return phaser_slot_by_label(
            self._resolve_named_pool_no,
            self._paged_pool_children,
            self._rig_paths.get("preset_pools", "DataPool/PresetPools"),
            label,
        )
''',
    "_resolve_named_pool_no": '''    def _resolve_named_pool_no(self, target_name: str, *, probe_id: str) -> int | None:
        """이름이 정확히 ``target_name``인 프리셋 풀의 번호 — 공용 몸통.

        카드 t480 — 본문은 ``server.design.console_slots.resolve_named_pool_no``
        (업로드 길 공용). 거절 규율은 그 독스트링에 있다.
        """
        return resolve_named_pool_no(
            self._state_query,
            self._rig_paths.get("preset_pools", "DataPool/PresetPools"),
            target_name,
            probe_id=probe_id,
        )

    def _state_query(self, probe_id: str, arguments) -> object | None:
        """``query_state`` 도구 한 번 — 해석된 응답, 실패면 None(카드 t480).

        ``server.design.console_slots`` 판독기가 콘솔을 묻는 통로다. 도구 호출
        id·인자는 옮기기 전과 같다(프로브 id 가 감사 기록의 열쇠다).
        """
        probe = self._registry.dispatch(
            ToolCall(id=probe_id, name="query_state", arguments=dict(arguments))
        )
        if probe.result.is_error:
            return None
        try:
            return json.loads(probe.result.content)
        except (json.JSONDecodeError, TypeError):
            return None
''',
    "_paged_pool_children": '''    def _paged_pool_children(self, path: str, *, probe_id: str) -> dict[int, str | None] | None:
        """``path`` 컨테이너의 자식 번호→이름 완전 판독 — 페이징 공용 몸통.

        카드 t480 — 본문은 ``server.design.console_slots.paged_pool_children``
        (업로드 길 공용). 페이징·무진전 방어 규율은 그 독스트링에 있다.
        """
        return paged_pool_children(self._state_query, path, probe_id=probe_id)
''',
    "_resolve_position_preset_labels": '''    def _resolve_position_preset_labels(
        self,
        labels: Iterable[str],
        *,
        start: int,
        span: int,
        pool_no: int = POSITION_PRESET_POOL,
    ) -> dict[str, int]:
        """룩 라벨 집합 -> Position 프리셋 슬롯, 콘솔 판독 1회(t232).

        카드 t480 — 풀을 한 번 판독하고, 라벨 해석은
        ``server.design.console_slots.resolve_position_preset_labels``(업로드 길
        공용)가 한다. 매칭·거부 규율은 그 독스트링에 있다.
        """
        return resolve_position_preset_labels(
            self._position_preset_pool_children(pool_no=pool_no),
            labels,
            start=start,
            span=span,
            pool_no=pool_no,
        )
''',
}

edits = []
for name, text in NEW.items():
    node = methods[name]
    start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
    edits.append((start, node.end_lineno, text))
for start, end, text in sorted(edits, reverse=True):
    lines[start - 1 : end] = [text]
out = "".join(lines)
anchor = "from server.design.song_cue_render import ("
block = (
    "from server.design.console_slots import (  # 카드 t480 — 업로드 길 공용 판독기\n"
    "    paged_pool_children,\n"
    "    phaser_slot_by_label,\n"
    "    resolve_named_pool_no,\n"
    "    resolve_position_preset_labels,\n"
    "    white_preset_slots,\n"
    ")\n"
)
out = out.replace(anchor, block + anchor, 1)
SESSION.write_text(out)
print("replaced:", sorted(NEW))
