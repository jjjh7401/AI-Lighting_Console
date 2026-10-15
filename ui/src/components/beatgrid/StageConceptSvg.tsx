/** 무대 개념도 — 시안 `drawStage` 의 자리 배치를 그대로 옮긴다.
 *
 * 패치 좌표를 못 읽으면 이 그림을 대신 그린다. 장비 위치는 지어내지 않는다.
 * 뒤(BACK)·옆(SIDE-L/R)·앞(FOH)·워시 면·무빙 두 줄(U/D)·블라인드 자리만 보여 준다.
 * 색과 밝기는 칸 데이터가 있을 때 칠하는 것이라 여기서는 중립 회색이다.
 */
export function StageConceptSvg({ width, height }: { width: number; height: number }) {
  const W = width;
  const H = height;
  const L0 = 60;
  const R0 = W - 60;
  const SW = R0 - L0;
  // 시안 `row(n, a, b)` — n개를 a~b 사이에 고르게.
  const row = (n: number, a: number, b: number) =>
    Array.from({ length: n }, (_, i) => a + (b - a) * (n === 1 ? 0.5 : i / (n - 1)));
  const lamp = (x: number, y: number, r: number, key: string) => (
    <circle key={key} cx={x} cy={y} r={r} fill="#333" />
  );
  // 무빙 한 대: 빔 삼각형 + 헤드 사각형(시안 `mv`). 기본 기울기 45 → 길이 ≈ 98.5.
  const beam = (x: number, y: number, key: string) => (
    <g key={key}>
      <polygon points={`${x},${y} ${x - 9},${y + 98.5} ${x + 9},${y + 98.5}`} fill="#444" opacity={0.4} />
      <rect x={x - 5} y={y - 5} width={10} height={10} fill="#333" />
    </g>
  );
  const label = (x: number, y: number, text: string, anchor: "start" | "middle" | "end" = "start") => (
    <text key={`${text}-${x}-${y}`} x={x} y={y} fontSize={10} fill="#8a889a" textAnchor={anchor}>
      {text}
    </text>
  );
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="beat-grid-stage beat-grid-stage-concept" role="img" aria-label="무대 개념도">
      <rect width={W} height={H} fill="#101014" />
      {/* 워시 면 — 시안 `ZB.wash` 자리 */}
      <rect x={L0} y={70} width={SW} height={170} fill="#1b1b22" stroke="#333" />
      {row(10, L0 + 22, R0 - 22).flatMap((x, i) => [lamp(x, 226, 5, `wf${i}`), lamp(x, 86, 5, `wb${i}`)])}
      {row(8, L0 + 60, R0 - 60).map((x, i) => lamp(x, 264, 5, `fo${i}`))}
      {row(12, L0 + 10, R0 - 10).map((x, i) => lamp(x, 30, 6, `ba${i}`))}
      {row(6, 92, 212).flatMap((y, i) => [lamp(28, y, 6, `sl${i}`), lamp(W - 28, y, 6, `sr${i}`)])}
      {row(8, L0 + 30, R0 - 30).map((x, i) => beam(x, 54, `mu${i}`))}
      {row(8, L0 + 30, R0 - 30).map((x, i) => beam(x, 120, `md${i}`))}
      {row(6, W / 2 - 110, W / 2 + 110).map((x, i) => (
        <rect key={`bl${i}`} x={x - 9} y={41} width={18} height={8} fill="#444" />
      ))}
      {label(L0 + 44, 284, "FOH")}
      {label(L0 + 6, 250, "WASH")}
      {label(L0, 16, "BACK")}
      {label(W / 2, 36, "BLIND", "middle")}
      {label(14, 76, "SIDE-L")}
      {label(W - 14, 76, "SIDE-R", "end")}
      {label(L0 - 14, 58, "U", "end")}
      {label(L0 - 14, 124, "D", "end")}
    </svg>
  );
}
