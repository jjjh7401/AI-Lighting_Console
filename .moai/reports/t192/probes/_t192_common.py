"""t192 탐침 공용부 — transcript 에서 Bash 호출과 그 결과를 꺼낸다.

계기 한계를 여기 한 곳에 모아 둔다:
- Bash tool_use 의 input.command 만 본다. bash -c 안에 숨은 형태는 못 본다.
- tool_result 는 tool_use_id 로 짝짓는다. 짝을 못 찾으면 호출자가 따로 센다.
"""

import json
import os

ROOT = "/Users/studiox/.claude/projects"


def bump(counter: dict, key) -> None:
    counter[key] = counter.get(key, 0) + 1


def collect_uses(obj, out: list) -> None:
    """레코드 어디에 있든 Bash tool_use 의 (id, command) 를 모은다."""
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use" and obj.get("name") == "Bash":
            inp = obj.get("input")
            tid = obj.get("id")
            if isinstance(inp, dict) and isinstance(tid, str):
                cmd = inp.get("command")
                if isinstance(cmd, str):
                    out.append((tid, cmd))
        for value in obj.values():
            collect_uses(value, out)
    elif isinstance(obj, list):
        for value in obj:
            collect_uses(value, out)


def collect_results(obj, out: dict) -> None:
    """tool_use_id -> 결과 본문 텍스트."""
    if isinstance(obj, dict):
        if obj.get("type") == "tool_result":
            tid = obj.get("tool_use_id")
            text = _result_text(obj.get("content"))
            if isinstance(tid, str) and text is not None:
                out[tid] = text
        for value in obj.values():
            collect_results(value, out)
    elif isinstance(obj, list):
        for value in obj:
            collect_results(value, out)


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if parts:
            return "\n".join(parts)
    return None


def iter_transcripts():
    """transcript 파일마다 (프로젝트 디렉터리명, uses, results, 파싱실패수) 를 내놓는다."""
    for entry in sorted(os.listdir(ROOT)):
        pdir = os.path.join(ROOT, entry)
        if not os.path.isdir(pdir):
            continue
        for name in os.listdir(pdir):
            if not name.endswith(".jsonl"):
                continue
            uses: list = []
            results: dict = {}
            bad = 0
            path = os.path.join(pdir, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    for raw in handle:
                        line = raw.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except ValueError:
                            bad += 1
                            continue
                        collect_uses(record, uses)
                        collect_results(record, results)
            except OSError:
                continue
            yield entry, uses, results, bad


def line_count(text: str) -> int:
    body = text.rstrip("\n")
    return 0 if body == "" else body.count("\n") + 1
