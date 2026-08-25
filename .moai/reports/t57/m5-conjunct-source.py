"""M5 — 열린 후보 둘의 연언을 「치환해 돌려서」 판정한다. 읽어서 추정하지 않는다."""

import hashlib
import pathlib
import shutil
import subprocess

cases = [
    (
        "607-cue_monitor",
        "server/tests/test_web_cue_monitor.py",
        607,
        "        event = recv_frame(ws)",
        '        event = drain_until(ws, "cue_monitor")',
    ),
    (
        "255-chat_response",
        "server/tests/test_web_panel_execute.py",
        255,
        "    return recv_frame(ws, timeout)",
        '    return drain_until(ws, "chat_response")',
    ),
]

for name, path_s, lineno, expect, lever in cases:
    target = pathlib.Path(path_s)
    backup = pathlib.Path("/tmp/t57_m5_backup_" + name + ".py")
    shutil.copy(target, backup)
    base = hashlib.sha256(target.read_bytes()).hexdigest()

    lines = target.read_text().splitlines(keepends=True)
    actual = lines[lineno - 1].rstrip("\n")
    print("CASE " + name)
    print("  line " + str(lineno) + " reads: " + repr(actual))
    if actual != expect:
        print("  ANCHOR MISMATCH — 판독하지 않는다")
        continue

    # 무뮤테이션 기준선
    pre = subprocess.run(
        [".venv/bin/python", "-m", "pytest", path_s, "-q", "-p", "no:randomly"],
        capture_output=True,
        text=True,
    )
    pre_line = [x for x in pre.stdout.splitlines() if "passed" in x or "failed" in x]
    print("  baseline: " + (pre_line[-1] if pre_line else "?"))

    lines[lineno - 1] = lever + "\n"
    target.write_text("".join(lines))
    reread = target.read_text().splitlines()[lineno - 1]
    applied = reread == lever
    print("  applied=" + str(applied) + "  now reads: " + repr(reread))
    if not applied:
        shutil.copy(backup, target)
        print("  APPLIED-CHECK FAILED — 판독하지 않는다")
        continue

    run = subprocess.run(
        [".venv/bin/python", "-m", "pytest", path_s, "-q", "-p", "no:randomly"],
        capture_output=True,
        text=True,
    )
    tail = [x for x in run.stdout.splitlines() if "passed" in x or "failed" in x]
    verdict = "SURVIVED" if run.returncode == 0 else "KILLED"
    print("  -> " + verdict + "  |  " + (tail[-1] if tail else "?"))
    for x in run.stdout.splitlines():
        if x.startswith("FAILED "):
            print("     " + x)

    shutil.copy(backup, target)
    print(
        "  restored sha256 match = " + str(hashlib.sha256(target.read_bytes()).hexdigest() == base)
    )
