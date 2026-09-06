// 정본 산출물 LXSEQ_SAMPLE_01_Sugar_r3.timeline.html 을 t279 페이로드 모양으로
// 옮긴 시각 확인용 픽스처. WebSocket 을 건너지 않고, 콘솔에 아무것도 쓰지 않는다.
import type { SongTimelineSection, SongTimelineView } from "../protocol";

interface Row {
  label: string;
  cue: number;
  start: number;
  end: number;
  bars: number;
  barStart: number;
  mood: string;
  primary: string;
  secondary: string | undefined;
  dLevel: number;
  intensity: { group: string; level: number }[] | undefined;
  groups: string[];
  movement: string;
  effect: string;
  trans: string;
  fade: number;
  note: string;
  manual?: boolean;
}

const ROWS: Row[] = [
  { label: "INTRO", cue: 10, start: 0, end: 8_000, bars: 4, barStart: 1, mood: "화사, 등장", primary: "P1 골드앰버", secondary: "P2 웜화이트", dLevel: 3, intensity: undefined, groups: ["BACK", "WASH-U", "HAZE"], movement: "STATIC", effect: "NONE", trans: "SNAP", fade: 0, note: "[MANUAL] 헤이즈 곡 시작 30초 전 선투입 · 첫 박에 스냅 인", manual: true },
  { label: "VERSE1", cue: 20, start: 8_000, end: 24_000, bars: 8, barStart: 5, mood: "경쾌, 근접", primary: "P2 웜화이트", secondary: "P1 골드앰버", dLevel: 4, intensity: [{ group: "KEY", level: 70 }, { group: "BACK", level: 35 }], groups: ["KEY", "BACK"], movement: "STATIC", effect: "NONE", trans: "XFADE", fade: 1.5, note: "보컬 인 · 페이스 확보 우선, 백라이트 낮게" },
  { label: "VERSE1", cue: 30, start: 24_000, end: 40_000, bars: 8, barStart: 13, mood: "확장, 그루브", primary: "P2 웜화이트", secondary: "P6 터쿼이즈", dLevel: 4, intensity: [{ group: "KEY", level: 70 }, { group: "SIDE", level: 40 }], groups: ["KEY", "BACK", "SIDE-L", "SIDE-R"], movement: "STATIC", effect: "PULSE @2bar", trans: "XFADE", fade: 2, note: "사이드 합류로 폭 확보 · 펄스는 2마디 주기 얕게" },
  { label: "PRE1", cue: 40, start: 40_000, end: 56_000, bars: 8, barStart: 21, mood: "축적, 상승", primary: "P6 터쿼이즈", secondary: "P5 딥퍼플", dLevel: 3, intensity: [{ group: "ALL", level: 60 }], groups: ["SIDE-L", "SIDE-R", "MOVER-U"], movement: "TILT-UP @slow", effect: "BREATHE @1bar", trans: "FADE", fade: 8, note: "8초에 걸쳐 서서히 · 후렴 직전 60 도달" },
  { label: "CHORUS1", cue: 50, start: 56_000, end: 72_000, bars: 8, barStart: 29, mood: "개방, 축제", primary: "P4 핫핑크", secondary: "P1 골드앰버", dLevel: 5, intensity: [{ group: "ALL", level: 90 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D"], movement: "FAN-OUT @mid", effect: "CHASE @1/8", trans: "SNAP", fade: 0, note: "후렴 첫 박 정확히 · 1차 웨이브 정점" },
  { label: "CHORUS1", cue: 60, start: 72_000, end: 88_000, bars: 8, barStart: 37, mood: "유지, 회전", primary: "P4 핫핑크", secondary: "P6 터쿼이즈", dLevel: 5, intensity: [{ group: "ALL", level: 90 }], groups: ["MOVER-U", "MOVER-D", "BACK"], movement: "CIRCLE @mid", effect: "CHASE @1/8", trans: "XFADE", fade: 1, note: "강도 유지, 색만 교체 · 후렴 후반 지루함 방지" },
  { label: "VERSE2", cue: 70, start: 88_000, end: 104_000, bars: 8, barStart: 45, mood: "하강, 근접", primary: "P2 웜화이트", secondary: "P5 딥퍼플", dLevel: 3, intensity: [{ group: "KEY", level: 65 }, { group: "BACK", level: 30 }], groups: ["KEY", "BACK"], movement: "STATIC", effect: "NONE", trans: "XFADE", fade: 2, note: "2차 웨이브 시작 · V1보다 5 낮게 잡아 후속 상승폭 확보" },
  { label: "PRE2", cue: 80, start: 104_000, end: 120_000, bars: 8, barStart: 53, mood: "축적, 압박", primary: "P6 터쿼이즈", secondary: "P4 핫핑크", dLevel: 4, intensity: [{ group: "ALL", level: 70 }], groups: ["SIDE-L", "SIDE-R", "MOVER-U", "LED-W"], movement: "TILT-UP @mid", effect: "PULSE @1beat", trans: "FADE", fade: 8, note: "PRE1보다 10 높게 · LED월 합류 · 펄스 1박 주기로 조임" },
  { label: "CHORUS2", cue: 90, start: 120_000, end: 136_000, bars: 8, barStart: 61, mood: "개방, 확산", primary: "P4 핫핑크", secondary: "P7 선셋오렌지", dLevel: 5, intensity: [{ group: "ALL", level: 95 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D", "LED-W"], movement: "FAN-OUT @fast", effect: "CHASE @1/8", trans: "SNAP", fade: 0, note: "2차 웨이브 정점 · 1차보다 5 높게" },
  { label: "CHORUS2", cue: 100, start: 136_000, end: 152_000, bars: 8, barStart: 69, mood: "유지, 확장", primary: "P1 골드앰버", secondary: "P4 핫핑크", dLevel: 5, intensity: [{ group: "ALL", level: 95 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D", "LED-W", "BLIND"], movement: "SWEEP-H @fast", effect: "CHASE @1/8", trans: "XFADE", fade: 1, note: "블라인더 합류 · 객석 직사 각도 리허설에서 확정" },
  { label: "BRIDGE", cue: 110, start: 152_000, end: 160_000, bars: 4, barStart: 77, mood: "절제, 집중", primary: "P5 딥퍼플", secondary: undefined, dLevel: 2, intensity: [{ group: "ALL", level: 35 }], groups: ["KEY", "BACK"], movement: "STATIC", effect: "NONE", trans: "XFADE", fade: 2.5, note: "급강하 · 3차 웨이브 lull 구간, 낙차 확보가 목적" },
  { label: "BRIDGE", cue: 120, start: 160_000, end: 168_000, bars: 4, barStart: 81, mood: "재점화, 축적", primary: "P5 딥퍼플", secondary: "P4 핫핑크", dLevel: 4, intensity: [{ group: "ALL", level: 75 }], groups: ["KEY", "BACK", "SIDE-L", "SIDE-R"], movement: "TILT-UP @fast", effect: "BREATHE @1bar", trans: "FADE", fade: 7, note: "마지막 후렴 직전까지 7초 상승 · 35→75" },
  { label: "CHORUS3", cue: 130, start: 168_000, end: 184_000, bars: 8, barStart: 85, mood: "폭발, 최대", primary: "P4 핫핑크", secondary: "P1 골드앰버", dLevel: 5, intensity: [{ group: "ALL", level: 100 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D", "WASH-U", "SIDE-L", "SIDE-R", "LED-W"], movement: "FAN-OUT @fast", effect: "CHASE @1/8", trans: "SNAP", fade: 0, note: "곡 전체 최고점 · 가용 그룹 전개 (FOH 제외)" },
  { label: "CHORUS3", cue: 140, start: 184_000, end: 200_000, bars: 8, barStart: 93, mood: "유지, 회전", primary: "P7 선셋오렌지", secondary: "P6 터쿼이즈", dLevel: 5, intensity: [{ group: "ALL", level: 100 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D", "WASH-U", "SIDE-L", "SIDE-R", "LED-W"], movement: "CIRCLE @fast", effect: "RAINBOW", trans: "XFADE", fade: 1, note: "더블 후렴 전반부 종료 · 색상만 순환시켜 체감 변화 유지" },
  { label: "CHORUS3", cue: 150, start: 200_000, end: 216_000, bars: 8, barStart: 101, mood: "최고조, 난반사", primary: "P4 핫핑크", secondary: "P6 터쿼이즈", dLevel: 5, intensity: [{ group: "ALL", level: 100 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D", "SIDE-L", "SIDE-R", "LED-W", "BLIND", "STROBE"], movement: "SWEEP-H @fast", effect: "STROBE @2bar", trans: "SNAP", fade: 0, note: "스트로브 구간 · 광과민성 사전 고지 필수 · 2마디 주기로 제한" },
  { label: "CHORUS3", cue: 160, start: 216_000, end: 232_000, bars: 8, barStart: 109, mood: "해소 준비", primary: "P1 골드앰버", secondary: "P2 웜화이트", dLevel: 5, intensity: [{ group: "ALL", level: 85 }], groups: ["MOVER-U", "MOVER-D", "BACK", "WASH-D"], movement: "CIRCLE @mid", effect: "TWINKLE", trans: "XFADE", fade: 2, note: "스트로브 해제 · 색온도 회복하며 종료 준비" },
  { label: "OUTRO", cue: 170, start: 232_000, end: 236_000, bars: 2, barStart: 117, mood: "잔향, 종료", primary: "P1 골드앰버", secondary: undefined, dLevel: 1, intensity: [{ group: "ALL", level: 20 }], groups: ["BACK", "WASH-U"], movement: "STATIC", effect: "NONE", trans: "FADE", fade: 3.5, note: "마지막 음 위에서 하강 · 85→20" },
  { label: "OUTRO", cue: 180, start: 236_000, end: 236_000, bars: 0, barStart: 119, mood: "암전", primary: "P8 블랙아웃", secondary: undefined, dLevel: 1, intensity: [{ group: "ALL", level: 0 }], groups: ["ALL"], movement: "STATIC", effect: "NONE", trans: "FADE", fade: 1.5, note: "[MANUAL] 곡 종료 확인 후 · 다음 곡 인계 시 BACK 15% 잔광 유지", manual: true },
];

const SECTIONS: SongTimelineSection[] = ROWS.map((row, index) => ({
  index: index + 1,
  label: row.label,
  start_ms: row.start,
  cue_number: row.cue,
  d_level: row.dLevel,
  palette: row.secondary === undefined ? [row.primary] : [row.primary, row.secondary],
  position: row.movement,
  texture: row.mood,
  fx: row.effect === "NONE" ? [] : [row.effect],
  accents: [],
  mib: false,
  trig_time_seconds: row.start / 1000,
  end_ms: row.end,
  duration_ms: row.end - row.start,
  bar_start: row.barStart,
  bar_count: row.bars,
  mood: row.mood,
  palette_primary: row.primary,
  palette_secondary: row.secondary,
  intensity: row.intensity,
  fixture_groups: row.groups,
  movement: row.movement,
  effect: row.effect,
  trans: row.trans,
  fade_seconds: row.fade,
  note: row.note,
  manual: row.manual ?? false,
}));

export const CUE_SHEET_EXAMPLE: SongTimelineView = {
  song_title: "Maroon 5 — Sugar",
  sequence_name: "Sequence 120",
  sequence_number: 120,
  timing_mode: "timecode",
  timecode_number: 901,
  lifecycle: "pending_approval",
  approval: "pending_review",
  director_decisions: [],
  sections: SECTIONS,
  lint: [],
  unresolved: [],
  disabled: [],
  readback: { verified: null, message: null },
  bpm: 120,
  time_signature: "4/4",
  musical_key: "D♭ major",
  total_duration_ms: 236_000,
  bar_count: 118,
  seconds_per_bar: 2,
  tc_source: "LTC",
  tc_origin: "00:00.0 = 곡 첫 음 (카운트인 없음)",
  tc_method: "DERIVED",
  tc_method_warning:
    "이 타임라인의 모든 타임코드는 마디 연산(1마디 = 2.000s)으로 도출한 값입니다. 음원 청취로 검증하지 않았습니다. 픽업·하프바 삽입이 있으면 전 구간이 어긋납니다. 리허설에서 LTC 대조 필수.",
  palette_legend: [
    { id: "P1", name: "골드 앰버", color: "#FFB43C" },
    { id: "P2", name: "웜 화이트", color: "#FFE0B0" },
    { id: "P4", name: "핫 핑크", color: "#FF3C9E" },
    { id: "P5", name: "딥 퍼플", color: "#5A2BC8" },
    { id: "P6", name: "터쿼이즈", color: "#2ED8D8" },
    { id: "P7", name: "선셋 오렌지", color: "#FF6A28" },
    { id: "P8", name: "블랙아웃", color: "#101418" },
  ],
};
