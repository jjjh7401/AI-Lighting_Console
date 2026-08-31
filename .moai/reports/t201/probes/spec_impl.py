"""t201 보조 계기 - 그 SPEC 을 언급한 커밋이 실제 구현 경로를 건드렸나.

spec_reality.py 의 commits 열은 SPEC 문서만 고친 커밋도 센다.
「살아 있는 목표」와 「이미 구현됐다」를 가르려면 그 커밋들이 server/ 나 src/ 를
건드렸는지 봐야 한다. 코드를 여는 게 아니라 git 이 기록한 경로만 읽는다.
"""

import os
import subprocess

SPECDIR = ".moai/specs"
IMPL_PREFIX = ("server/", "src/")


def touched(sid):
    """그 SPEC-ID 를 언급한 커밋들이 건드린 고유 파일 경로."""
    out = subprocess.run(
        [
            "git",
            "log",
            "origin/main",
            f"--grep={sid}",
            "--name-only",
            "--format=",
            "--diff-merges=first-parent",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = set(p for p in out.stdout.split("\n") if p.strip())
    impl = set(p for p in paths if p.startswith(IMPL_PREFIX))
    tests = set(p for p in impl if "/tests/" in p or "test_" in p)
    return paths, impl, tests


def main():
    ids = sorted(x for x in os.listdir(SPECDIR) if x.startswith("SPEC-"))
    print("id\tfiles_all\timpl_files\ttest_files\tnontest_impl")
    for sid in ids:
        paths, impl, tests = touched(sid)
        nontest = len(impl) - len(tests)
        cols = [sid, str(len(paths)), str(len(impl)), str(len(tests)), str(nontest)]
        print("\t".join(cols))


if __name__ == "__main__":
    main()
