"""moai update 뒤에 줄인 규칙 판본을 다시 입힌다 (snapshot/ 을 저장소에 덮어쓰고 150k 점검).

저장소 루트에서:
  python3 .moai/tools/rules-diet/reapply.py          # 덮어쓰기 + 점검
  python3 .moai/tools/rules-diet/reapply.py --dry-run # 어느 파일이 다른지만 출력 (아무것도 쓰지 않음)
점검이 실패하면 종료 코드 1 이다. 이 스크립트는 moai update 를 실행하지 않는다.
"""
import filecmp
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")


def main():
    if not os.path.exists("CLAUDE.md"):
        sys.exit("저장소 루트에서 실행하세요")
    dry = "--dry-run" in sys.argv
    changed = 0
    for root, _, names in os.walk(SNAP):
        for n in names:
            src = os.path.join(root, n)
            rel = os.path.relpath(src, SNAP)
            if rel.startswith("dot-"):  # build.py 가 선행 점을 dot- 로 바꿔 저장했다
                rel = "." + rel[4:]
            if os.path.exists(rel) and filecmp.cmp(src, rel, shallow=False):
                continue
            changed += 1
            print(("DIFF   " if dry else "WRITE  ") + rel)
            if not dry:
                os.makedirs(os.path.dirname(rel), exist_ok=True)
                shutil.copyfile(src, rel)
    print(f"{changed} file(s) {'differ' if dry else 'written'}")
    sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "check.py")]))


if __name__ == "__main__":
    main()
