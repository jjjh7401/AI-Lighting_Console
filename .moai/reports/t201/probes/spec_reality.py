"""t201 - SPEC 45개 실태 조사: 프론트매터가 아니라 증거로 상태를 가른다.

계기 주의(카드 지시): 프론트매터 status 는 실제 상태의 증거가 아니다.
moai spec drift 도 45개 중 9개에만 실제 답을 낸다 - 7개는 레코드 자체가 없고
29개는 GitImpliedStatus=era-exempt(미판정)다. 그 Drifted=false 는 미측정이지 정합이 아니다.

그래서 여기서는 세 가지를 따로 잰다:
  1. 프론트매터 status (참고값 — 근거 아님)
  2. 생애주기 산출물 존재 (spec/plan/acceptance/progress)
  3. origin/main 에서 그 SPEC-ID 를 언급한 커밋 수와 최초/최종 날짜
"""

import os
import re
import subprocess

SPECDIR = ".moai/specs"
REC = re.compile(r"^[0-9a-f]{40}\t", re.M)
STATUS = re.compile(r"^status:\s*(\S+)", re.M)
LIFECYCLE = ("spec.md", "plan.md", "acceptance.md", "progress.md")


def git_log():
    """origin/main 전량을 SHA/날짜/제목/본문으로 덤프한다."""
    out = subprocess.run(
        [
            "git",
            "log",
            "origin/main",
            "--format=%H%x09%ad%x09%s%x09%b",
            "--date=short",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def split_commits(text):
    """SHA 로 시작하는 줄을 경계로 커밋 단위로 자른다(본문이 여러 줄이라)."""
    idx = [m.start() for m in REC.finditer(text)]
    idx.append(len(text))
    return [text[idx[i] : idx[i + 1]] for i in range(len(idx) - 1)]


def frontmatter_status(path):
    """spec.md 의 status 필드. 파일이 없으면 no-spec.md 를 답한다."""
    if not os.path.exists(path):
        return "no-spec.md"
    with open(path, encoding="utf-8") as fh:
        head = fh.read(2000)
    m = STATUS.search(head)
    if m is None:
        return "no-status-field"
    return m.group(1)


def lifecycle_flags(d):
    """생애주기 파일 존재를 s/p/a/g 4글자로. 없으면 점."""
    marks = ""
    for name, ch in zip(LIFECYCLE, "spag", strict=True):
        if os.path.exists(os.path.join(d, name)):
            marks += ch
        else:
            marks += "."
    return marks


def progress_evidence(d):
    """progress.md 의 크기와 sync 완료 표지 유무."""
    p = os.path.join(d, "progress.md")
    if not os.path.exists(p):
        return 0, False
    with open(p, encoding="utf-8") as fh:
        body = fh.read()
    synced = "sync_commit_sha" in body
    return len(body.encode("utf-8")), synced


def main():
    commits = split_commits(git_log())
    ids = sorted(x for x in os.listdir(SPECDIR) if x.startswith("SPEC-"))
    print(f"# origin/main commits scanned: {len(commits)}")
    print(f"# SPEC directories: {len(ids)}")
    print("id\tstatus\tfiles\tprog_bytes\tsynced\tcommits\tfirst\tlast")
    for sid in ids:
        d = os.path.join(SPECDIR, sid)
        status = frontmatter_status(os.path.join(d, "spec.md"))
        marks = lifecycle_flags(d)
        pbytes, synced = progress_evidence(d)
        hits = [c for c in commits if sid in c]
        dates = sorted(c.split("\t")[1] for c in hits)
        first = dates[0] if dates else "-"
        last = dates[-1] if dates else "-"
        cols = [
            sid,
            status,
            marks,
            str(pbytes),
            "yes" if synced else "no",
            str(len(hits)),
            first,
            last,
        ]
        print("\t".join(cols))


if __name__ == "__main__":
    main()
