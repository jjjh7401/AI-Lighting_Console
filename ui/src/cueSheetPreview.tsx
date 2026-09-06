/**
 * 큐시트 타임라인 단독 미리보기 — 백엔드 없이 눈으로 확인하는 용도.
 * 실행: `npm --prefix ui run dev` 뒤 http://localhost:5173/cuesheet-preview.html
 * 왼쪽은 정본 샘플(Sugar) 페이로드, 오른쪽은 확장 필드가 하나도 없는
 * 오늘의 서버 페이로드 — 두 경우가 같은 화면에서 어떻게 보이는지 나란히 본다.
 */
import React from "react";
import ReactDOM from "react-dom/client";

import { CueSheetTimeline } from "./components/CueSheetTimeline";
import { CUE_SHEET_EXAMPLE } from "./components/cueSheetExample";
import { SONG_TIMELINE_EXAMPLE } from "./components/songTimelineExample";
import "./styles.css";

function Preview() {
  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh", padding: 20, display: "grid", gap: 20 }}>
      <CueSheetTimeline timeline={CUE_SHEET_EXAMPLE} />
      <CueSheetTimeline timeline={SONG_TIMELINE_EXAMPLE} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Preview />
  </React.StrictMode>,
);
