"""이 리그의 기종이 Iris 를 갖는가 — 채널 이름을 끝까지 읽어서 답한다. 읽기 전용.

주의: 이 트리는 한 응답에 15개만 준다(childCount 40 인데 truncated=True).
전진은 **받은 개수**만큼 — 요청 수만큼 전진하면 잘린 조각에서 건너뛰기가 생기고,
0개를 받으면 멈춘다(안 그러면 무한 루프).
"""

from server.safety.bootstrap import build_console_stack

WANT = ("iris", "zoom", "frost")


def main() -> None:
    stack = build_console_stack(receive_port=9005)
    try:
        q = stack.gate.state_port.query_state

        def listing(path):
            """선언된 childCount 까지 페이지를 넘기며 전부 모은다."""
            try:
                first = q(path)
            except Exception as exc:
                return None, f"{type(exc).__name__}", None
            declared = first.get("node", {}).get("childCount")
            pairs = [(c.get("i"), c.get("name")) for c in first.get("children", [])]
            while isinstance(declared, int) and len(pairs) < declared:
                try:
                    page = q(path, offset=len(pairs))
                except Exception as exc:
                    return pairs, f"{type(exc).__name__} (부분)", declared
                got = [(c.get("i"), c.get("name")) for c in page.get("children", [])]
                if not got:
                    break
                pairs.extend(got)
            return pairs, None, declared

        types, err, _ = listing("Patch/FixtureTypes")
        if not types:
            raise SystemExit(f"타입 목록 실패: {err}")

        print(f"{'기종':32} {'모드':20} {'채널':>9}  Iris  Zoom  Frost")
        for slot, name in types:
            modes, err, _ = listing(f"Patch/FixtureTypes/{slot}/DMXModes")
            if not modes:
                print(f"{str(name)[:31]:32} {'(모드 못 읽음)':20}")
                continue
            mslot, mname = modes[0]
            chans, err, declared = listing(
                f"Patch/FixtureTypes/{slot}/DMXModes/{mslot}/DMXChannels"
            )
            if chans is None:
                print(f"{str(name)[:31]:32} {str(mname)[:19]:20} 못 읽음 {err}")
                continue
            low = [str(c[1]).lower() for c in chans]
            marks = ["🟢" if any(w in c for c in low) else "—" for w in WANT]
            full = f"{len(chans)}/{declared}"
            flag = "" if declared in (None, len(chans)) else "  🔴부분"
            print(
                f"{str(name)[:31]:32} {str(mname)[:19]:20} {full:>9}  "
                f"{marks[0]:4}  {marks[1]:4}  {marks[2]:4}{flag}"
            )
    finally:
        stack.stop()


main()
