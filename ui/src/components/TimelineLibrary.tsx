// Director-timeline library panel (여러 곡·여러 버전 저장/불러오기 — user
// request, 2026-08-14). Lives inside RunbookMode above the SongTimeline.
//
// Split for the "no DOM/jsdom test harness" bound (protocol.ts header):
// TimelineLibraryView is hook-free and directly callable in tests; the named
// TimelineLibrary owns fetch() + React state, mirroring PaperworkPanel's
// split. Loading an entry is a REVIEW action only — the server swaps the
// shared replay store and the client applies the same projection the
// song_timeline WebSocket frame would carry. Nothing here fires a console
// command.
import { useCallback, useEffect, useState } from "react";

import type { SongTimelineView } from "../protocol";
import {
  deleteTimelineFromLibrary,
  fetchTimelineList,
  loadTimelineFromLibrary,
  saveTimelineToLibrary,
  timelineItemMeta,
  type TimelineLibraryItem,
} from "../timelineLibrary";

export interface TimelineLibraryViewProps {
  items: TimelineLibraryItem[] | null;
  open: boolean;
  draftName: string;
  busy: boolean;
  notice: string | null;
  hasTimeline: boolean;
  onToggleOpen: () => void;
  onDraftNameChange: (next: string) => void;
  onSave: () => void;
  onLoad: (id: string) => void;
  onDelete: (id: string) => void;
}

export function TimelineLibraryView({
  items,
  open,
  draftName,
  busy,
  notice,
  hasTimeline,
  onToggleOpen,
  onDraftNameChange,
  onSave,
  onLoad,
  onDelete,
}: TimelineLibraryViewProps) {
  const count = items?.length ?? 0;
  // 접힌 라벨이 스스로 상태를 말한다 (카드 t309). 기본 화면에서도 보이는
  // 손잡이라, 여는 클릭 없이도 "몇 개 있나"를 알아야 한다. 아직 못 읽었으면
  // (items === null) 개수를 꾸며내지 않고 아무 말도 하지 않는다 — 비었다는
  // 주장과 못 읽었다는 사실은 다르다.
  const countLabel = items === null ? "" : count > 0 ? ` (${count})` : " — 저장된 것 없음";
  return (
    <section className="timeline-library" aria-label="타임라인 라이브러리">
      <header className="timeline-library-head">
        <button
          type="button"
          className="timeline-library-toggle"
          onClick={onToggleOpen}
          aria-expanded={open}
        >
          {open ? "▾" : "▸"} 타임라인 라이브러리{countLabel}
        </button>
        {open && (
          <div className="timeline-library-save">
            <input
              className="timeline-library-name"
              value={draftName}
              placeholder="저장 이름 (곡 제목·버전)"
              onChange={(event) => onDraftNameChange(event.target.value)}
              disabled={busy || !hasTimeline}
            />
            <button
              type="button"
              className="timeline-library-save-button"
              onClick={onSave}
              disabled={busy || !hasTimeline || draftName.trim() === ""}
              title={hasTimeline ? "현재 감독 타임라인을 저장" : "저장할 타임라인이 아직 없습니다"}
            >
              현재 타임라인 저장
            </button>
          </div>
        )}
      </header>
      {open && notice !== null && <p className="timeline-library-notice">{notice}</p>}
      {open &&
        (items === null ? (
          <p className="timeline-library-empty">라이브러리를 불러오지 못했습니다.</p>
        ) : items.length === 0 ? (
          <p className="timeline-library-empty">
            저장된 타임라인이 없습니다 — 설계를 완료한 뒤 이름을 붙여 저장하세요.
          </p>
        ) : (
          <ul className="timeline-library-list">
            {items.map((item) => (
              <li className="timeline-library-item" key={item.id}>
                <div className="timeline-library-item-text">
                  <span className="timeline-library-item-name">{item.name}</span>
                  <span className="timeline-library-item-meta">{timelineItemMeta(item)}</span>
                </div>
                <div className="timeline-library-item-actions">
                  <button
                    type="button"
                    className="timeline-library-load"
                    onClick={() => onLoad(item.id)}
                    disabled={busy}
                  >
                    불러오기
                  </button>
                  <button
                    type="button"
                    className="timeline-library-delete"
                    onClick={() => onDelete(item.id)}
                    disabled={busy}
                    aria-label={`${item.name} 삭제`}
                  >
                    삭제
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}

export function TimelineLibrary({
  hasTimeline,
  onLoaded,
}: {
  hasTimeline: boolean;
  onLoaded: (timeline: SongTimelineView) => void;
}) {
  // null = 아직/못 읽음. 마운트 때 한 번 읽어 접힌 라벨이 개수를 말할 수 있게
  // 한다 (카드 t309) — 기본 화면의 감독은 펼치기 전에 "저장본이 있나"를 알아야
  // 여기가 손잡이라는 걸 안다.
  const [items, setItems] = useState<TimelineLibraryItem[] | null>(null);
  const [open, setOpen] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setItems(await fetchTimelineList());
  }, []);

  useEffect(() => {
    void refresh();
  }, [open, refresh]);

  const handleSave = useCallback(async () => {
    setBusy(true);
    setNotice(null);
    const ok = await saveTimelineToLibrary(draftName.trim());
    setNotice(ok ? `"${draftName.trim()}" 저장 완료` : "저장하지 못했습니다.");
    if (ok) setDraftName("");
    await refresh();
    setBusy(false);
  }, [draftName, refresh]);

  const handleLoad = useCallback(
    async (id: string) => {
      setBusy(true);
      setNotice(null);
      const timeline = await loadTimelineFromLibrary(id);
      if (timeline === null) {
        setNotice("불러오지 못했습니다.");
      } else {
        onLoaded(timeline);
        setNotice("타임라인을 불러왔습니다 — 감독 타임라인에 표시됩니다.");
      }
      setBusy(false);
    },
    [onLoaded],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("이 저장본을 삭제할까요?")) return;
      setBusy(true);
      setNotice(null);
      if (!(await deleteTimelineFromLibrary(id))) setNotice("삭제하지 못했습니다.");
      await refresh();
      setBusy(false);
    },
    [refresh],
  );

  return (
    <TimelineLibraryView
      items={items}
      open={open}
      draftName={draftName}
      busy={busy}
      notice={notice}
      hasTimeline={hasTimeline}
      onToggleOpen={() => setOpen((value) => !value)}
      onDraftNameChange={setDraftName}
      onSave={() => void handleSave()}
      onLoad={(id) => void handleLoad(id)}
      onDelete={(id) => void handleDelete(id)}
    />
  );
}
