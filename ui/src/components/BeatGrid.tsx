// 박자 격자 — 콘솔 그룹 트랙 × 마디 (SPEC-LDBEAT-001 M2, 카드 t532).
//
// `CueSheetTimeline`을 대체하지 않는다 — 그 컴포넌트는 큐 번호 단위(한 큐 =
// 한 행), 이 컴포넌트는 마디 단위(한 콘솔 그룹 트랙이 여러 큐·여러 타임코드
// 이벤트에 걸쳐 리듬을 탄다)다(plan.md §B 위험 2). `RunbookMode`의 기존
// 5블록 순서는 그대로이고, 이 컴포넌트는 `CueSheetTimeline`과 `SongTimeline`
// 사이에 **추가되는 새 블록**이다(REQ-LDBEAT-004).
//
// M2 범위 — 읽기 전용: 트랙·격자 데이터 모델과 레이아웃이 안정된 뒤에 M3가
// 실제 편집(세 경로 — 직접 고르기/문장/AI 제안)을 얹는다. 여기서는 선택·접기
// 상태만 바뀌고, 콘솔에도 초안에도 아무것도 쓰지 않는다. 명령창의 두 제출
// 버튼은 M3 배선 전까지 비활성이다.
import { useMemo, useRef, useState } from "react";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";

/** REQ-LDBEAT-005(a) — 초기 표시 범위를 4마디 단위 행 7개로 나눈다. 배치
 * 규칙서 §4의 표 그대로(첫 행은 못갖춘마디 포함 3마디, 넷째 행도 3마디 —
 * "4마디 단위"는 표의 경계를 그대로 옮긴 것이지 균등 분할이 아니다). */
export const BEAT_GRID_BAR_ROWS: readonly (readonly [number, number])[] = [
  [0, 2],
  [3, 6],
  [7, 10],
  [11, 13],
  [14, 17],
  [18, 21],
  [22, 25],
] as const;

/** `bar`가 속한 행의 인덱스. 범위 밖이면 `-1`. */
export function barRowIndex(bar: number): number {
  return BEAT_GRID_BAR_ROWS.findIndex(([start, end]) => bar >= start && bar <= end);
}

/** `bar` 시점에 그 트랙이 하는 일 — 그 마디 이전(또는 그 마디)에 선언된
 * 가장 최근 칸. 아직 칸이 없으면 `null`(지어내지 않는다). */
export function cueForBar(track: BeatGridTrack, bar: number): BeatGridCue | null {
  let found: BeatGridCue | null = null;
  for (const cue of track.cues) {
    if (cue.bar > bar) break;
    found = cue;
  }
  return found;
}

/** REQ-LDBEAT-005(b) — "음원 0초 = 앞박, 1마디 = 환산 초"(배치 규칙서 §4
 * 기준). `secondsPerBar`가 없으면(타임라인에 BPM/박자 미확정) 환산할 수
 * 없으므로 `null`. */
export function barToSeconds(bar: number, secondsPerBar: number | null | undefined): number | null {
  if (!secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  return bar * secondsPerBar;
}

/** `barToSeconds`의 역함수 — `maxBar`로 클램프하고 내림한다. */
export function secondsToBar(
  seconds: number,
  secondsPerBar: number | null | undefined,
  maxBar: number,
): number | null {
  if (!secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  const bar = Math.floor(seconds / secondsPerBar);
  return Math.max(0, Math.min(maxBar, bar));
}

/** ±10초 스킵 — 재생 위치를 `[0, maxSeconds]`로 클램프한다. */
export function clampSkipSeconds(current: number, delta: number, maxSeconds: number): number {
  return Math.max(0, Math.min(maxSeconds, current + delta));
}

/** 층 역할(`server.design.rig.RIG_LAYER_ROLES`)의 화면 이름표. 트랙 식별자가
 * 아니라 줄 옆의 폴더 이름일 뿐이다(REQ-LDBEAT-004, 카드 t526 교정). */
export const LAYER_ROLE_FOLDER_LABELS: Readonly<Record<string, string>> = {
  key: "앞빛",
  back: "역광",
  side: "옆빛",
  wash: "워시",
  mover: "무빙",
  effect: "효과",
  audience: "객석",
};

const UNASSIGNED_FOLDER = "미분류";

export function layerFolderLabel(role: string | null | undefined): string {
  if (!role) return UNASSIGNED_FOLDER;
  return LAYER_ROLE_FOLDER_LABELS[role] ?? UNASSIGNED_FOLDER;
}

export interface BeatGridFolder {
  role: string;
  label: string;
  tracks: BeatGridTrack[];
}

/** 트랙을 층 역할 폴더로 묶는다 — 처음 등장한 순서를 유지한다(REQ-LDBEAT-004(b)
 * 의 "층 역할 폴더" 접기/펴기 단위). */
export function groupTracksByLayerFolder(tracks: BeatGridTrack[]): BeatGridFolder[] {
  const order: string[] = [];
  const byRole = new Map<string, BeatGridTrack[]>();
  for (const track of tracks) {
    const role = track.layer_role ?? UNASSIGNED_FOLDER;
    if (!byRole.has(role)) {
      byRole.set(role, []);
      order.push(role);
    }
    byRole.get(role)!.push(track);
  }
  return order.map((role) => ({
    role,
    label: role === UNASSIGNED_FOLDER ? UNASSIGNED_FOLDER : layerFolderLabel(role),
    tracks: byRole.get(role)!,
  }));
}

/** REQ-LDBEAT-010/AC-LDBEAT-004 — 실기 미확인 모양(§6: circle·발리후·위상
 * 펼침). 배치 규칙서 §3이 "⚠"로 표기한 바로 그 모양들이다. */
const UNCONFIRMED_SHAPE_KEYWORDS = ["서클", "발리후", "위상 펼침", "circle", "ballyhoo"];

export function isUnconfirmedShapeCue(label: string): boolean {
  const lower = label.toLowerCase();
  return UNCONFIRMED_SHAPE_KEYWORDS.some((kw) => lower.includes(kw.toLowerCase()));
}

export type ProbeStatus = "pass" | "fail" | "미실행";

/** REQ-LDBEAT-001~003의 9항목 — progress.md가 쓰는 같은 순서·같은 9개.
 * `probeResults`에 없는 항목은 "미실행"이 기본이다(한 자리에서 뒤집기 쉽게). */
export const DEFAULT_PROBE_LABELS: readonly { id: number; label: string }[] = [
  { id: 1, label: "타임코드 트랙 ≥3" },
  { id: 2, label: "Goto 2번 이후·여러 시퀀스 동시" },
  { id: 3, label: "프리셋 수정 전파" },
  { id: 4, label: "효과 프리셋 SM15·Measure" },
  { id: 5, label: "위치 프리셋 위 상대값" },
  { id: 6, label: "타임코드 중간 재생" },
  { id: 7, label: "큐 하나 그룹 하나 + Step 2" },
  { id: 8, label: "같은 그룹 두 시퀀스 분담" },
  { id: 9, label: "circle·발리후" },
];

export interface ProbeRow {
  id: number;
  label: string;
  status: ProbeStatus;
}

export function buildProbeStatusTable(
  probeResults?: Readonly<Record<number, ProbeStatus>>,
): ProbeRow[] {
  return DEFAULT_PROBE_LABELS.map(({ id, label }) => ({
    id,
    label,
    status: probeResults?.[id] ?? "미실행",
  }));
}

/** REQ-LDBEAT-001 게이트 — 9항목 중 하나라도 PASS가 아니면 그 항목에 의존하는
 * 콘솔 **쓰기**는 잠긴다(미리보기는 이 게이트의 대상이 아니다, 결정⑤). */
export function isWriteLocked(probes: readonly { status: ProbeStatus }[]): boolean {
  return probes.some((probe) => probe.status !== "pass");
}

/** 곡의 첫 칸인지 — "들어오는 전환" 토글이 비활성화되는 기준(REQ-LDBEAT-004(d)).
 * 곡 전체의 첫 칸(격자 표시 범위의 시작 마디)만 전환이 없다. */
export function isFirstCueOfSong(bar: number, grid: BeatGridView): boolean {
  return bar <= grid.bar_range.start;
}

export interface BeatGridFixturePoint {
  fid: number;
  name: string;
  x: number;
  y: number;
  z: number;
  rotx: number;
  roty: number;
  rotz: number;
  /** 콘솔 SELECTIONDATA로 **확인된** 소속 그룹 이름 — 이름 추정이 아니라
   * 읽은 값이어야 한다. 없으면(`null`/`undefined`) 미확인이고, 화면은
   * 반드시 회색이다(REQ-LDBEAT-004(f)). 이 값을 채우는 유일한 근거는
   * 콘솔 `SELECTIONDATA` 읽기다 — 장비 이름이 그룹 이름과 비슷해 보인다는
   * 것은 이 필드를 채울 근거가 **아니다**(레인 리뷰 05ad9ec4, 이름 접두
   * fallback 제거). 지금까지 확인된 그룹은 t525 §② 네 개뿐이고(그룹당
   * 앞 2대만) `.moai/reports/t525/verdict.md`의 "근거 2 — sf_index → fid
   * 대응" 표(파일 93~103행, 표 본문 100~103행)가 그 전체 목록이다 — MOVER-ALL(501·502) ·
   * BACK(201·202) · SIDE-L(301·302) · BLIND(601·602). */
  confirmedGroupName?: string | null;
}

interface StageBounds {
  minX: number;
  maxX: number;
  maxY: number;
  spanX: number;
  spanY: number;
}

/** 2D 무대 투영의 좌표 경계 — 실측 범위를 그대로 쓴다(상수를 지어내지
 * 않는다, t525 §③). 픽스처가 없으면 `null`. */
export function computeStageBounds(fixtures: readonly BeatGridFixturePoint[]): StageBounds | null {
  if (fixtures.length === 0) return null;
  const xs = fixtures.map((f) => f.x);
  const ys = fixtures.map((f) => f.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    maxY,
    spanX: Math.max(1, maxX - minX),
    spanY: Math.max(1, maxY - minY),
  };
}

const STAGE_VIEW_W = 300;
const STAGE_VIEW_H = 220;
const STAGE_MARGIN = 20;

/** 픽스처 좌표 → SVG 화면 좌표. 위 = 무대 뒤(Y 값이 큰 쪽), 아래 = 객석
 * (t525 §③ "위에서 본 그림" 관례 그대로 — Y 방향 자체는 이름 추정이라
 * 미확인으로 남는다, spec.md §5 항목 5). */
export function projectFixture(
  point: { x: number; y: number },
  bounds: StageBounds,
): { cx: number; cy: number } {
  const usableW = STAGE_VIEW_W - STAGE_MARGIN * 2;
  const usableH = STAGE_VIEW_H - STAGE_MARGIN * 2;
  const cx = STAGE_MARGIN + ((point.x - bounds.minX) / bounds.spanX) * usableW;
  // Y가 클수록(무대 뒤) 화면 위쪽 — bounds.maxY를 0으로 둔다.
  const cy = STAGE_MARGIN + ((bounds.maxY - point.y) / bounds.spanY) * usableH;
  return { cx, cy };
}

/** REQ-LDBEAT-004(f) — 그룹 소속이 **확인된** 장비만 칠하고, 나머지는 회색
 * (t525 §③ 패턴 — "확인된 것만" 색, 전체 칠하기를 거짓으로 보여주지
 * 않는다). "확인"의 유일한 근거는 `fixture.confirmedGroupName`(콘솔
 * SELECTIONDATA에서 읽은 값)이고, 그것이 화면에 떠 있는 어느 트랙의
 * `group_name`과 **정확히** 일치할 때만 그 트랙 색을 쓴다 — 이름이 비슷해
 * 보인다는 추론(접두 매칭)은 fallback으로도 쓰지 않는다(레인 리뷰
 * 05ad9ec4). 이것은 트랙의 `group_no_confirmed`(그룹 **번호** 확인 여부,
 * 다른 축)와 무관하다 — 번호를 몰라도 SELECTIONDATA가 이름으로 소속을
 * 확인해 줬다면 그것으로 충분하다. */
const TRACK_COLOR_PALETTE = ["#4f8cff", "#f85149", "#3fb950", "#d29922", "#b388ff", "#00c2cc"];
const UNCONFIRMED_FIXTURE_COLOR = "#5a5f6b";

export function fixtureDisplayColor(
  fixture: BeatGridFixturePoint,
  tracks: readonly BeatGridTrack[],
): string {
  if (!fixture.confirmedGroupName) return UNCONFIRMED_FIXTURE_COLOR;
  const confirmedKey = fixture.confirmedGroupName.toUpperCase();
  const index = tracks.findIndex((track) => track.group_name.toUpperCase() === confirmedKey);
  if (index < 0) return UNCONFIRMED_FIXTURE_COLOR;
  return TRACK_COLOR_PALETTE[index % TRACK_COLOR_PALETTE.length];
}

export interface BeatGridProps {
  grid: BeatGridView | null | undefined;
  /** 2D 무대 좌표 — 콘솔 접촉 0인 M2는 이 값을 props로만 받는다(살아있는
   * 읽기 경로가 없으면 지어내지 않는다). 비어 있으면 무대 칸은 "무대 좌표
   * 미제공" 안내로 떨어진다. */
  fixtures?: BeatGridFixturePoint[];
  probeResults?: Readonly<Record<number, ProbeStatus>>;
  secondsPerBar?: number | null;
}

/** 역할별 조건부 노출(REQ-LDBEAT-004(c)) — 무빙만 "움직임", KEY류는 "색"
 * 없음(기존 `cue_sheet_edit.py`의 `r.nocol` 관례와 같은 판단). M2의 큐
 * 내용은 아직 역할·모양·속도가 한 문장으로 묶인 `label` 하나뿐이라(M3가
 * 구조화한다), 여기서는 그 문장을 "내용" 한 줄로 그대로 보여준다 —
 * 밝기/위치/색/움직임을 문장에서 쪼개 지어내지 않는다. */
function roleFieldHints(role: string | null): string[] {
  const hints: string[] = ["밝기"];
  if (role === "mover" || role === "back" || role === "side" || role === "wash") hints.push("위치");
  if (role !== "mover") hints.push("색");
  if (role === "mover") hints.push("움직임");
  return hints;
}

export function BeatGrid({ grid, fixtures = [], probeResults, secondsPerBar = null }: BeatGridProps) {
  const [openFolders, setOpenFolders] = useState<Set<string>>(() => new Set());
  const [allOpen, setAllOpen] = useState(true);
  const [selected, setSelected] = useState<{ trackIndex: number; bar: number } | null>(null);
  const [transitionView, setTransitionView] = useState(false);
  const [playbackSeconds, setPlaybackSeconds] = useState(0);
  const [audioName, setAudioName] = useState<string | null>(null);
  const [commandText, setCommandText] = useState("");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const folders = useMemo(() => groupTracksByLayerFolder(grid?.tracks ?? []), [grid]);
  const probes = useMemo(() => buildProbeStatusTable(probeResults), [probeResults]);
  const writeLocked = isWriteLocked(probes);
  const stageBounds = useMemo(() => computeStageBounds(fixtures), [fixtures]);

  if (!grid) {
    return (
      <section className="beat-grid" aria-label="박자 격자">
        <p className="beat-grid-empty">박자 격자 데이터가 아직 없습니다.</p>
      </section>
    );
  }

  const maxBar = grid.bar_range.end;
  const isFolderOpen = (role: string) => allOpen || openFolders.has(role);
  const toggleFolder = (role: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (isFolderOpen(role)) {
        // 전역이 열림이면 이 폴더만 닫는 것이므로, 전역 "모두 펴기" 상태를
        // 끈 채 나머지만 열린 집합으로 바꾼다.
        setAllOpen(false);
        next.clear();
        for (const f of folders) if (f.role !== role) next.add(f.role);
      } else {
        next.add(role);
      }
      return next;
    });
  };
  const toggleAll = () => {
    if (allOpen || openFolders.size > 0) {
      setAllOpen(false);
      setOpenFolders(new Set());
    } else {
      setAllOpen(true);
    }
  };

  const selectedTrack = selected ? grid.tracks[selected.trackIndex] : null;
  const selectedCue = selectedTrack && selected ? cueForBar(selectedTrack, selected.bar) : null;
  const firstCue = selected ? isFirstCueOfSong(selected.bar, grid) : false;
  const viewBar = selected?.bar ?? grid.bar_range.start;

  const onSelectAudio = (file: File | null) => {
    if (!file) return;
    setAudioName(file.name);
    if (audioRef.current) {
      audioRef.current.src = URL.createObjectURL(file);
    }
  };

  const seek = (delta: number) => {
    const totalSeconds = barToSeconds(maxBar, secondsPerBar) ?? playbackSeconds;
    const next = clampSkipSeconds(playbackSeconds, delta, totalSeconds);
    setPlaybackSeconds(next);
    if (audioRef.current) audioRef.current.currentTime = next;
  };

  return (
    <section className="beat-grid" aria-label="박자 격자">
      <header className="beat-grid-head">
        <span className="beat-grid-title">박자 격자</span>
        <span className="beat-grid-song">{grid.song_title || "(곡 미지정)"}</span>
        {grid.note && <span className="beat-grid-note">{grid.note}</span>}
        <span className="beat-grid-range">
          {grid.bar_range.start}~{grid.bar_range.end}마디
        </span>
      </header>

      {/* ① 곡 전체 지도 — 0~25마디 표시 범위를 한 줄로. */}
      <div className="beat-grid-overview" role="img" aria-label="곡 전체 지도">
        {BEAT_GRID_BAR_ROWS.map(([start, end]) => (
          <span
            key={start}
            className={`beat-grid-ov-cell${barRowIndex(viewBar) === barRowIndex(start) ? " is-current" : ""}`}
            title={`${start}~${end}마디`}
          >
            {start}
          </span>
        ))}
      </div>

      <div className="beat-grid-toolbar">
        <button type="button" className="beat-grid-fold-all" onClick={toggleAll}>
          [모두 접기/펴기]
        </button>
        <span className="beat-grid-transport">
          <button type="button" onClick={() => seek(-10)}>
            ⏪ 10초
          </button>
          <button type="button" onClick={() => seek(10)}>
            10초 ⏩
          </button>
          <span className="beat-grid-clock">{playbackSeconds.toFixed(1)}초</span>
          <label className="beat-grid-audio-label">
            ♪ {audioName ?? "음원"}
            <input
              type="file"
              accept="audio/*"
              hidden
              onChange={(event) => onSelectAudio(event.target.files?.[0] ?? null)}
            />
          </label>
          <audio ref={audioRef} hidden />
        </span>
        {writeLocked && (
          <span className="beat-grid-locked" title="M1 프로브 9항목 중 미확인 항목이 있어 쓰기가 잠겨 있습니다">
            ⚠ 쓰기 잠김
          </span>
        )}
      </div>

      {/* ② 그룹-트랙 타임라인 — 층 역할 폴더로 묶고, 좌우 스크롤 + 한 화면
          고정 높이(REQ-LDBEAT-004(b)). */}
      <div className="beat-grid-body">
        <div className="beat-grid-lanes" role="table" aria-label="콘솔 그룹 트랙 타임라인">
          {folders.map((folder) => {
            const open = isFolderOpen(folder.role);
            return (
              <div className="beat-grid-folder" key={folder.role}>
                <button
                  type="button"
                  className="beat-grid-folder-head"
                  onClick={() => toggleFolder(folder.role)}
                >
                  {open ? "▾" : "▸"} {folder.label} ({folder.tracks.length}줄)
                </button>
                {open &&
                  folder.tracks.map((track) => {
                    const trackIndex = grid.tracks.indexOf(track);
                    return (
                      <div className="beat-grid-track" role="row" key={`${track.group_name}-${trackIndex}`}>
                        <span className="beat-grid-track-label">
                          {track.group_name}
                          {!track.group_no_confirmed && (
                            <span className="beat-grid-unconfirmed-badge" title="콘솔 그룹 번호 미확인">
                              ⚠
                            </span>
                          )}
                        </span>
                        <div className="beat-grid-track-cues">
                          {track.cues.length === 0 && (
                            <span className="beat-grid-cue-empty">이 구간에 칸 없음</span>
                          )}
                          {track.cues.map((cue) => (
                            <button
                              type="button"
                              key={cue.bar}
                              className={`beat-grid-cue${
                                selected?.trackIndex === trackIndex && selected.bar === cue.bar
                                  ? " is-selected"
                                  : ""
                              }`}
                              onClick={() => {
                                setSelected({ trackIndex, bar: cue.bar });
                                setTransitionView(false);
                              }}
                            >
                              {cue.label}
                              {isUnconfirmedShapeCue(cue.label) && (
                                <span className="beat-grid-shape-warn" title="실기 미확인 모양">
                                  ⚠ 실기 미확인
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
              </div>
            );
          })}
          {folders.length === 0 && (
            <p className="beat-grid-empty">{grid.note ?? "표시할 트랙이 없습니다."}</p>
          )}
        </div>

        {/* ③ 상세 창 — 2D 무대 + 이 마디 한눈에. */}
        <div className="beat-grid-detail">
          <div className="beat-grid-stage-pane">
            <h5>무대 (2D)</h5>
            {stageBounds ? (
              <svg viewBox={`0 0 ${STAGE_VIEW_W} ${STAGE_VIEW_H}`} className="beat-grid-stage">
                {fixtures.map((fixture) => {
                  const { cx, cy } = projectFixture(fixture, stageBounds);
                  return (
                    <circle
                      key={fixture.fid}
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill={fixtureDisplayColor(fixture, grid.tracks)}
                    >
                      <title>{`${fixture.name} (fid ${fixture.fid})`}</title>
                    </circle>
                  );
                })}
              </svg>
            ) : (
              <p className="beat-grid-empty">무대 좌표 미제공 — 콘솔 패치 읽기 경로가 아직 안 배선됨(M2).</p>
            )}
            <p className="beat-grid-stage-note">위 = 무대 뒤 · 색 = 소속 확인된 그룹만, 나머지 회색</p>
          </div>

          <div className="beat-grid-glance-pane">
            <h5>이 마디 한눈에 — {viewBar}마디</h5>
            <table className="beat-grid-glance-table">
              <tbody>
                {grid.tracks.map((track) => {
                  const cue = cueForBar(track, viewBar);
                  return (
                    <tr key={track.group_name}>
                      <td>{track.group_name}</td>
                      <td>{cue ? cue.label : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 큐 편집 칸 — M2는 읽기 전용 표시만(REQ-LDBEAT-004(c)(d)). */}
      {selected && selectedTrack && (
        <aside className="beat-grid-cue-panel" aria-label="큐 편집 칸">
          <header>
            <span>
              {selectedTrack.group_name} · {selected.bar}마디
            </span>
            <span className="beat-grid-cue-panel-actions">
              <button
                type="button"
                className={`beat-grid-transition-toggle${transitionView ? " is-on" : ""}`}
                disabled={firstCue}
                title={firstCue ? "곡 첫 큐 — 들어오는 전환 없음" : undefined}
                onClick={() => setTransitionView((v) => !v)}
              >
                전환
              </button>
              <button type="button" aria-label="닫기" onClick={() => setSelected(null)}>
                ✕
              </button>
            </span>
          </header>
          {transitionView ? (
            <div className="beat-grid-transition-view">
              <p>들어오는 전환 — 페이드 · 트리거 박 · 딜레이 · 트래킹(M3 배선 전까지 읽기 전용)</p>
            </div>
          ) : (
            <div className="beat-grid-cue-view">
              {roleFieldHints(selectedTrack.layer_role).map((field) => (
                <div className="beat-grid-cue-field" key={field}>
                  <span className="beat-grid-cue-field-label">{field}</span>
                  <span className="beat-grid-cue-field-value">{selectedCue?.label ?? "—"}</span>
                </div>
              ))}
            </div>
          )}
        </aside>
      )}

      {/* 하단 명령 입력 — M3 배선 전까지 제출 두 경로 모두 비활성. */}
      <div className="beat-grid-cmd">
        <input
          className="beat-grid-cmd-input"
          value={commandText}
          onChange={(event) => setCommandText(event.target.value)}
          placeholder="예: 22~25마디 MOVER-D 효과를 Sweep 2박으로"
        />
        <button type="button" disabled title="M3에서 배선">
          바로 적용(문장)
        </button>
        <button type="button" disabled title="M3에서 배선">
          AI 제안
        </button>
      </div>

      <div className="beat-grid-probe-pane" aria-label="M1 프로브 9항목 상태">
        <h5>M1 콘솔 확인 프로브</h5>
        <ul className="beat-grid-probe-list">
          {probes.map((probe) => (
            <li key={probe.id} className={`beat-grid-probe-${probe.status === "pass" ? "pass" : probe.status === "fail" ? "fail" : "pending"}`}>
              {probe.id}. {probe.label} — {probe.status}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
