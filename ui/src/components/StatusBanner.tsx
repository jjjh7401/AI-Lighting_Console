// Console health + execution-block indication (REQ-MVP-030/031 UI half).
import { healthLabel, type StatusState } from "../protocol";

export function StatusBanner({
  status,
  connected,
}: {
  status: StatusState | null;
  connected: boolean;
}) {
  if (!connected) {
    return <div className="banner banner-offline">서버 연결 끊김 — 재연결 중…</div>;
  }
  if (status === null) {
    return <div className="banner">상태 확인 중…</div>;
  }
  const cls =
    status.health === "online" ? "banner-online" : "banner-offline";
  return (
    <div className={`banner ${cls}`}>
      <span>{healthLabel(status.health)}</span>
      {status.executions_blocked && status.health !== "online" && (
        <span className="banner-block"> · 신규 명령 실행 차단됨</span>
      )}
      {status.live_lock && <span className="banner-lock"> · 라이브 잠금 활성 (read-only)</span>}
    </div>
  );
}
