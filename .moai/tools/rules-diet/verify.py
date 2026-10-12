"""조항 보존 검증: 축소 전 원본의 모든 비어 있지 않은 줄이 (줄인 파일 + companion) 합집합에 남아 있는지 본다.

저장소 루트에서: python3 .moai/tools/rules-diet/verify.py   (빠진 줄이 있으면 종료 코드 1)
원본은 build.py 의 BASE_REF 커밋에서 읽는다. [HARD] 개수도 같이 비교한다.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402


def main():
    bad = 0
    for src, spec in build.SPECS.items():
        comps = sorted({build.COMPANIONS[d] for _, d in spec["moves"]})
        orig = subprocess.run(
            ["git", "show", f"{build.BASE_REF}:{src}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        texts = []
        for p in [src] + comps:
            with open(p, encoding="utf-8") as fh:
                texts.append(fh.read())
        pool = {ln.rstrip() for t in texts for ln in t.split("\n")}
        missing = [
            ln for ln in orig.split("\n") if ln.strip() and ln.rstrip() not in pool
        ]
        hard_o = orig.count("[HARD]")
        hard_n = sum(t.count("[HARD]") for t in texts)
        import check  # 글자 수 (frontmatter·주석 제외) 전/후

        before, after = len(check.counted(orig)), len(check.counted(texts[0]))
        print(
            f"{os.path.basename(src):42} chars {before:>6} -> {after:>6}  missing={len(missing):>3}  "
            f"[HARD] orig={hard_o:>3} now={hard_n:>3}"
        )
        for m in missing[:3]:
            print("      MISSING:", m[:110])
        bad += len(missing)
    print("TOTAL missing lines:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
