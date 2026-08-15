/**
 * Standalone preview of CueMonitor with mock data — no backend needed.
 * Run: `npx vite` then open http://localhost:5173
 * (index.html temporarily points here instead of main.tsx)
 */
import React, { useState } from "react";
import ReactDOM from "react-dom/client";

import { CueMonitor } from "./components/CueMonitor";
import type { CueMonitorState } from "./protocol";
import "./styles.css";

const MOCK_STATE: CueMonitorState = {
  executors: [
    {
      executor_no: 101,
      status: "ok",
      sequence_no: 50,
      sequence_name: "Sequence 50",
      cues: [
        { no: 1, name: "K-Pop Opening", cue_no: 1 },
        { no: 2, name: "Golden Hour", cue_no: 2 },
        { no: 3, name: "Energetic Chorus", cue_no: 3 },
        { no: 4, name: "Ballad Yellow Red", cue_no: 4 },
        { no: 5, name: "Slow Fade Out", cue_no: 5 },
      ],
      current_cue: { status: "ok", value: "1 — K-Pop Opening" },
      last_app_action: { command: "Go+ Executor 101", ts: new Date(Date.now() - 3000).toISOString(), ok: true },
    },
    {
      executor_no: 102,
      status: "ok",
      sequence_no: 17,
      sequence_name: "Sequence 17",
      cues: [
        { no: 1, name: "Gobo Spin", cue_no: 1 },
        { no: 2, name: "Color Chase", cue_no: 2 },
      ],
      current_cue: { status: "ok", value: "1 — Gobo Spin" },
      last_app_action: { command: "Go+ Executor 102", ts: new Date(Date.now() - 8000).toISOString(), ok: true },
    },
    {
      executor_no: 103,
      status: "ok",
      sequence_no: 100,
      sequence_name: "Sequence 100",
      cues: [
        { no: 1, name: "Mirror Ball", cue_no: 1 },
        { no: 2, name: "Strobe Flash", cue_no: 2 },
        { no: 3, name: "Laser Sweep", cue_no: 3 },
      ],
      current_cue: { status: "ok", value: "1 — Mirror Ball" },
    },
    {
      executor_no: 105,
      status: "ok",
      sequence_no: 30,
      sequence_name: "Sequence 30",
      cues: [
        { no: 1, name: "Ballad Warm", cue_no: 1 },
        { no: 2, name: "Ballad Peak", cue_no: 2 },
      ],
      current_cue: { status: "ok", value: "1 — Ballad Warm" },
    },
    {
      executor_no: 111,
      status: "ok",
      sequence_no: 41,
      sequence_name: "Sequence 41",
      cues: [
        { no: 1, name: "Sunset Glow", cue_no: 1 },
      ],
      current_cue: { status: "ok", value: "1 — Sunset Glow" },
    },
    {
      executor_no: 191,
      status: "ok",
      sequence_no: 80,
      sequence_name: "Sequence 80",
      cues: [
        { no: 1, name: "Dim Fade", cue_no: 1 },
        { no: 2, name: "Bright Wash", cue_no: 2 },
        { no: 3, name: "Color Wheel", cue_no: 3 },
      ],
      current_cue: { status: "ok", value: "3 — Dim Fade" },
    },
    {
      executor_no: 192,
      status: "ok",
      sequence_no: 14,
      sequence_name: "Sequence 14",
      cues: [
        { no: 1, name: "Sine Wave", cue_no: 1 },
      ],
      current_cue: { status: "ok", value: "1 — Sine Wave" },
    },
    {
      executor_no: 193,
      status: "ok",
      sequence_no: 16,
      sequence_name: "Sequence 16",
      cues: [
        { no: 1, name: "Hue Rotate", cue_no: 1 },
        { no: 2, name: "Hue Pulse", cue_no: 2 },
        { no: 3, name: "Hue Static", cue_no: 3 },
        { no: 4, name: "Hue Fade", cue_no: 4 },
      ],
      current_cue: { status: "ok", value: "4 — Hue Fade" },
    },
  ],
  history: [
    { ts: new Date(Date.now() - 180_000).toISOString(), command: "Attribute 'Tilt' At 15", ok: true },
    { ts: new Date(Date.now() - 160_000).toISOString(), command: "ChangeDestination Root", ok: true },
    { ts: new Date(Date.now() - 155_000).toISOString(), command: "ClearAll", ok: true },
    { ts: new Date(Date.now() - 150_000).toISOString(), command: "Group 13", ok: true },
    { ts: new Date(Date.now() - 145_000).toISOString(), command: "Attribute 'Dimmer' At 100", ok: true },
    { ts: new Date(Date.now() - 140_000).toISOString(), command: "Attribute 'Zoom' At 10", ok: true },
    { ts: new Date(Date.now() - 135_000).toISOString(), command: "Attribute 'Iris' At 20", ok: true },
    { ts: new Date(Date.now() - 130_000).toISOString(), command: "Attribute 'Pan' At Relative -35 ; Attribute 'Tilt' At Relative -35", ok: true },
    { ts: new Date(Date.now() - 125_000).toISOString(), command: "Step 2", ok: true },
    { ts: new Date(Date.now() - 120_000).toISOString(), command: "Attribute 'Pan' At Relative 35 ; Attribute 'Tilt' At Relative 35", ok: true },
    { ts: new Date(Date.now() - 115_000).toISOString(), command: "Attribute 'Pan' At Phase 0 Thru 360", ok: true },
    { ts: new Date(Date.now() - 110_000).toISOString(), command: "Attribute 'Tilt' At Phase 90 Thru 450", ok: true },
    { ts: new Date(Date.now() - 105_000).toISOString(), command: "Attribute 'Pan' At Speed 30 ; Attribute 'Tilt' At Speed 30", ok: true },
    { ts: new Date(Date.now() - 100_000).toISOString(), command: "Store /overwrite Sequence 100 Cue 1 'Small Beam Wide Circle'", ok: true },
    { ts: new Date(Date.now() - 95_000).toISOString(), command: "ClearAll", ok: true },
    { ts: new Date(Date.now() - 90_000).toISOString(), command: "ChangeDestination Root", ok: true },
    { ts: new Date(Date.now() - 85_000).toISOString(), command: "ClearAll", ok: true },
    { ts: new Date(Date.now() - 80_000).toISOString(), command: "Off Sequence Thru", ok: false },
    { ts: new Date(Date.now() - 60_000).toISOString(), command: "ChangeDestination Root", ok: true },
    { ts: new Date(Date.now() - 30_000).toISOString(), command: "Group 13", ok: true },
  ],
  lastSyncAt: Date.now() - 5000,
  stale: false,
};

function Preview() {
  const [openExecutorNo, setOpenExecutorNo] = useState<number | null>(null);
  const toggleExecutor = (no: number) =>
    setOpenExecutorNo((cur) => (cur === no ? null : no));

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg)" }}>
      {/* Left placeholder — simulates the dashboard area */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)", fontSize: 14 }}>
        (대시보드 영역)
      </div>
      {/* Right panel — the CueMonitor under test */}
      <div style={{ width: 400, borderLeft: "1px solid #2b2f36", display: "flex", flexDirection: "column" }}>
        <CueMonitor
          cueMonitor={MOCK_STATE}
          openExecutorNo={openExecutorNo}
          onToggleExecutor={toggleExecutor}
          onRefresh={() => console.log("refresh")}
          onExecute={(no) => console.log("Go+", no)}
          onBack={(no) => console.log("Go-", no)}
          onStop={(no) => console.log("Off", no)}
          onGoto={(no, cue) => console.log("Goto", no, cue)}
        />
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Preview />
  </React.StrictMode>,
);
