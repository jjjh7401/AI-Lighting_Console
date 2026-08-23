"""가이드의 안전 주장 트립와이어 — 주장과 그 출처(코드)를 쌍으로 확인한다.

## 왜 있는가

`docs/user-guide.html` 의 산문은 §D 검사가 보지 못한다. t43·t44 에서 뮤테이션을
각각 3회·4회 쐈는데 **전부 통과**했다 — 그중 하나는 무대 안전 전제를
「열지 않아도 됩니다」로 **정반대로 뒤집은** 것이었다. 그래도 전 검사가 초록이었다.

두 카드의 정확성 근거는 매번 「전수 대조와 등록부 인용」이었다. 그건 그때 사람이
성실했다는 뜻이지 다음 사람도 그러리라는 보장이 아니다.

## 무엇을 단언하는가 — 그리고 무엇을 못 하는가

이 검사는 **주장의 참·거짓을 재지 않는다.** 산문의 의미는 기계가 못 잰다.
대신 두 가지 **존재**를 잰다:

    CLAIM-GONE   가이드에서 그 주장이 사라졌거나 개수가 줄었다
    SOURCE-GONE  코드에서 그 주장의 근거 문장이 사라졌다

전자는 **가이드가 조용히 뒤집히는 것**을, 후자는 **코드가 바뀌어 가이드가 낡는 것**을
잡는다. 두 방향이 다르므로 둘 다 있어야 한다.

**개수를 못 박는다.** 존재만 보면 문구가 여러 곳일 때 하나를 지워도 통과한다 —
t45 실측: 「되돌리기가 없습니다」는 2곳이라 한 곳을 뒤집었을 때 안 물었다.

## 한계 (다음 사람이 과신하지 않도록)

- **문구를 바꿔 쓰면 빨개진다.** 그게 의도다 — 안전 주장은 조용히 재작성되면 안 된다.
  정당한 재작성이면 이 표의 문구도 함께 고치면 된다.
- **여기 없는 주장은 안 지킨다.** 5쌍은 무대에서 비싸게 드러나는 것만 골랐다.
  op-note 8개 중 UI 동작을 말하는 것(E-14·E-28·E-29·E-32)은 코드 출처가
  `ui/` 라 이 검사가 다루지 않는다 — 미검증으로 남았다.
- **주장이 옳은지는 여전히 사람이 읽어야 한다.**

    python3 .moai/scripts/guide-safety-tripwire.py     # exit 1 이면 위반
"""

import re
import sys
from pathlib import Path

PAIRS = [
    (
        "에디터 전제",
        "patch writes only take when the operator has the Patch editor open",
        ["열려 있지 않으면", "만들어지지 않습니다"],
    ),
    # 개수를 못 박는다 — 부분문자열 존재만 보면 문구가 여러 곳일 때 하나를 지워도
    # 통과한다(t45 실측: 「되돌리기가 없습니다」는 2곳이라 한 곳을 뒤집어도 안 물었다).
    ("실행 취소 없음", "이 앱에는 실행 취소가 없다", [("되돌리기가 없습니다", 2)]),
    ("거절 시 중단", "그 자리에서 멈추고 나머지는 not_attempted", ["그 자리에서 멈춰"]),
    ("붙여넣기 금지", "붙여넣기는 개행·공백이 조용히", ["줄바꿈과 공백이 조용히 깨져"]),
    ("성공 아님", "a clean plugin exit is NOT success", ["오류 없이 끝났다고 성공은 아닙니다"]),
]


def run(guide="docs/user-guide.html", tools="server/orchestrator/tools.py"):
    joined = re.sub(r'"\s*\n\s*"', "", Path(tools).read_text())
    g = Path(guide).read_text()
    bad = 0
    for name, src, keys in PAIRS:
        if src not in joined:
            print(f"SOURCE-GONE: {name} — 코드에서 근거 문장이 사라졌다. 가이드도 함께 고쳐라.")
            bad += 1
        for k in keys:
            phrase, want = k if isinstance(k, tuple) else (k, 1)
            got = g.count(phrase)
            if got < want:
                print(
                    f"CLAIM-GONE: {name} — 가이드의 주장이 줄었다: "
                    f"{phrase!r} {want}곳 기대, {got}곳 발견"
                )
                bad += 1
    print(bad)
    return bad


if __name__ == "__main__":
    sys.exit(1 if run(*sys.argv[1:]) else 0)
