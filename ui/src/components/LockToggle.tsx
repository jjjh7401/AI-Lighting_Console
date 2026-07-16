// Live-lock toggle (REQ-MVP-016 UI half) — lock state comes from the server.
import { type StatusState } from "../protocol";

export function LockToggle({
  status,
  onToggle,
}: {
  status: StatusState | null;
  onToggle: (active: boolean) => void;
}) {
  const active = status?.live_lock ?? false;
  return (
    <label className="lock-toggle">
      <input
        type="checkbox"
        checked={active}
        onChange={(event) => onToggle(event.target.checked)}
      />
      <span>라이브 잠금 {active ? "켜짐 (제안만 생성)" : "꺼짐"}</span>
    </label>
  );
}
