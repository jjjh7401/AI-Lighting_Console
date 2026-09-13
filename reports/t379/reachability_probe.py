"""카드 t379 — 룩 도달성 전수 조사. 콘솔 접촉 0, 순수 선택 계층만 잰다.

물음: EDM 열 룩 중 실측 실기 곡에서 세 종만 뽑혔다(haze-shafts x5 · intro-bed x4 ·
drop-crimson x7). 나머지 일곱은 "드물게 뽑히는" 것인가, 아니면 "어떤 곡을 넣어도
못 뽑히는" 죽은 항목인가 — 이 둘은 다른 결함이다.

방법. `songcue.map_sections_to_looks` 는 순수 함수다(§7 반복 회귀 + §8 대비 규율).
같은 다이내믹스의 형제 룩들 사이에서 무엇이 뽑히는가는 세 축이 정한다 —
(1) 되돌아옴(같은 라벨 반복) (2) 의도(§6 행의 밝기 구간) (3) 대비(직전 룩과의
자카드+색+밝기 차). 라벨을 §6 행 아무 데도 안 걸리는 무의미 문자열로 두면 (1)(2)
가 전부 빠지고 (3)만 남는다 — 그 상태에서 "직전 룩"을 자유롭게 정할 수 있으면
그 다이내믹스의 형제 전체에 대해 "이 룩이 이길 수 있는 직전 룩이 존재하는가"를
전수로 잴 수 있다.

`used_look_ids` 로 직전 구간의 선택을 강제한다 — 같은 다이내믹스의 다른 형제를
전부 배제하면 남는 것은 하나뿐이라 그 룩이 강제로 뽑힌다(§7 곡간 재사용 금지
기억이 인자로 들어오는 자리를 그대로 쓴 것 — 새 발명이 아니다).

리그 결합(그 룩의 역할이 실제 그룹에 묶이는가)은 이 조사의 범위 밖이다 — 그것은
`onsite-round-20260912/diag.py`·`sweep.py` 가 이미 재는 축이고, 여기서 재는 것은
"선택 계층이 이 룩을 한 번이라도 고를 수 있는가" 하나뿐이다.
"""

from __future__ import annotations

from server.looks.busking import genres_in, looks_for_genre
from server.looks.loader import load_library_from_dir
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN
from server.looks.songcue import map_sections_to_looks, parse_sections

lib = load_library_from_dir()

print("== 전수: 각 룩이 뽑힐 수 있는 '직전 룩'이 존재하는가 ==\n")

overall_dead: dict[str, list[str]] = {}

for genre in genres_in(lib):
    looks = looks_for_genre(lib, genre)
    by_dynamics: dict[int, list] = {}
    for look in looks:
        by_dynamics.setdefault(look.dynamics, []).append(look)

    reachable: set[str] = set()
    winner_of: dict[str, list[str]] = {look.look_id: [] for look in looks}

    for dynamics, siblings in by_dynamics.items():
        sibling_ids = {look.look_id for look in siblings}
        for prior in looks:  # 직전 룩 후보 — 전 장르 전 다이내믹스를 다 시도한다
            # 구간 0: prior 만 남기고 그 다이내믹스의 형제를 전부 배제해 강제 선택.
            prior_siblings = {
                other.look_id
                for other in by_dynamics.get(prior.dynamics, ())
                if other.look_id != prior.look_id
            }
            raw = [
                {"name": "X0", "start": 0},
                {"name": "X1", "start": 20},
            ]
            sections = parse_sections(raw)
            selections = map_sections_to_looks(
                sections,
                lib,
                genre,
                explicit_dynamics={0: prior.dynamics, 1: dynamics},
                used_look_ids=prior_siblings,
            )
            if selections[0].look is None or selections[0].look.look_id != prior.look_id:
                continue  # 강제 선택 자체가 안 됐다 — 이 시행은 못 믿는다, 건너뛴다
            second = selections[1].look
            if second is not None and second.look_id in sibling_ids:
                reachable.add(second.look_id)
                winner_of[second.look_id].append(prior.look_id)

    dead = sorted({look.look_id for look in looks} - reachable)
    if dead:
        overall_dead[genre] = dead
    print(f"장르 {genre}: 룩 {len(looks)}개, 도달 확인 {len(reachable)}개, 미도달 {len(dead)}개")
    for look_id in dead:
        print(f"  🔴 미도달: {look_id}")

print("\n== 요약 ==")
if overall_dead:
    for genre, dead in overall_dead.items():
        print(f"{genre}: {dead}")
else:
    print("모든 장르, 모든 룩이 이 축(대비 기반 형제 선택)으로 최소 한 번은 도달한다.")

print(
    "\n(참고) 다이내믹스 축·번위:",
    DYNAMICS_MIN,
    "~",
    DYNAMICS_MAX,
    " — 이 조사는 §6 행 라벨(코러스·벌스 등)로 걸리는 의도 축과 §7 되돌아옴 축은",
    "일부러 뺐다(무의미 라벨 사용). 그 둘을 켠 상태의 도달성은 별도 축이고 이",
    "스크립트는 재지 않는다 — 대비 축만으로도 도달하면 다른 두 축은 더 넓힐 뿐",
    "좁히지 않기 때문이다(§8 「좁은 필터는 좋은 룩을 조용히 버린다」 규율의 반대",
    "방향: 넓은 축에서 도달하면 좁은 축 조합에서도 도달 가능성은 줄지언정 0으로",
    "떨어지지는 않는다 — 이 함의는 증명하지 않았다, Gaps 로 남긴다).",
)
