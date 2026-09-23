/**
 * t454 — 런북 모드 단독 미리보기. 백엔드·콘솔 없이 눈으로 확인하는 용도.
 * 실행: `npm --prefix ui run dev` 뒤 http://localhost:5173/runbook-preview.html
 *
 * 데이터는 예제가 아니라 서버 `_song_timeline_payload` 의 실제 출력이다
 * (`.moai/reports/t454/measure_payload.py` 가 만든 `payload.json` 사본, 8구간·
 * 120 BPM 시험 곡). 그래서 「데이터 없음」 칸도 오늘 서버가 실제로 비워 두는
 * 칸 그대로 보인다.
 */
import React from "react";
import ReactDOM from "react-dom/client";

import type { SongTimelineView } from "./protocol";
import { RunbookMode } from "./components/RunbookMode";
import serverPayload from "./components/runbookServerPayload.json";
import "./styles.css";

const timeline = serverPayload as unknown as SongTimelineView;

function Preview() {
  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh", padding: 20 }}>
      <RunbookMode
        cueMonitor={{ executors: [], history: [], lastSyncAt: null, stale: false }}
        timeline={timeline}
      />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Preview />
  </React.StrictMode>,
);

// `?open` 이면 접힌 패널(컨셉·GATE 상세)을 펼친 채 보여 준다 — 헤드리스 캡처용.
// 제품 화면의 기본값(접힘)은 바꾸지 않는다.
if (new URLSearchParams(location.search).has("open")) {
  setTimeout(() => {
    document.querySelectorAll("details").forEach((node) => {
      node.open = true;
    });
  }, 0);
}
