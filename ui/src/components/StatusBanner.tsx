// Console health + execution-block indication (REQ-MVP-030/031 UI half) plus the
// degraded-state cause+action guidance (REQ-DEPLOY-012/013/018/019 UI half).
import { healthGuidance, healthLabel, type StatusState } from "../protocol";

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
  // Cause+action guidance shows only for a degraded state (null when online).
  // The backend's diagnosis refines the console_offline case so the operator is
  // sent to the ONE thing that is wrong: a stopped responder, or a console
  // replying to a port the app does not listen on — instead of a healthy onPC
  // being blamed for both.
  const guidance = healthGuidance(
    status.health,
    status.console_input,
    status.reply_port,
    status.receive_port,
  );
  return (
    <div className={`banner ${cls}`}>
      <span>{healthLabel(status.health)}</span>
      {status.executions_blocked && status.health !== "online" && (
        <span className="banner-block"> · 신규 명령 실행 차단됨</span>
      )}
      {status.live_lock && <span className="banner-lock"> · 라이브 잠금 활성 (read-only)</span>}
      {guidance && <div className="banner-guidance">{guidance}</div>}
    </div>
  );
}
