// Console health + execution-block indication (REQ-MVP-030/031 UI half) plus the
// degraded-state cause+action guidance (REQ-DEPLOY-012/013/018/019 UI half).
import { healthGuidance, healthLabel, type ConsoleInput, type StatusState } from "../protocol";

type StatusTone = "ok" | "warn" | "bad" | "muted";

export interface StatusDetail {
  label: string;
  value: string;
  tone: StatusTone;
}

const CONSOLE_INPUT_LABELS: Record<ConsoleInput, string> = {
  listening: "입력 포트 열림",
  silent: "입력 없음",
  undetermined: "미확인",
};

function consoleInputLabel(input: ConsoleInput | undefined): string {
  return input === undefined ? "미확인" : CONSOLE_INPUT_LABELS[input];
}

function consoleInputTone(input: ConsoleInput | undefined): StatusTone {
  if (input === "listening") return "ok";
  if (input === "silent") return "bad";
  return "muted";
}

export function statusDetails(
  status: StatusState | null,
  connected: boolean,
): StatusDetail[] {
  if (!connected) {
    return [{ label: "서버", value: "재연결 중", tone: "bad" }];
  }
  if (status === null) {
    return [
      { label: "서버", value: "연결됨", tone: "ok" },
      { label: "게이트", value: "상태 확인 중", tone: "muted" },
    ];
  }
  const details: StatusDetail[] = [
    { label: "서버", value: "연결됨", tone: "ok" },
    {
      label: "콘솔",
      value: healthLabel(status.health),
      tone: status.health === "online" ? "ok" : "bad",
    },
    {
      label: "OSC 입력",
      value: consoleInputLabel(status.console_input),
      tone: consoleInputTone(status.console_input),
    },
    {
      label: "실행",
      value: status.executions_blocked ? "차단" : "가능",
      tone: status.executions_blocked ? "bad" : "ok",
    },
    {
      label: "라이브 잠금",
      value: status.live_lock ? "제안만" : "꺼짐",
      tone: status.live_lock ? "warn" : "muted",
    },
  ];
  if (typeof status.reply_port === "number" && typeof status.receive_port === "number") {
    details.push({
      label: "응답 포트",
      value: `${status.reply_port} → ${status.receive_port} 불일치`,
      tone: "warn",
    });
  }
  return details;
}

export function StatusBanner({
  status,
  connected,
}: {
  status: StatusState | null;
  connected: boolean;
}) {
  if (!connected) {
    return (
      <div className="banner banner-offline">
        <div className="banner-main">서버 연결 끊김 — 재연결 중…</div>
        <StatusDetailStrip details={statusDetails(status, connected)} />
      </div>
    );
  }
  if (status === null) {
    return (
      <div className="banner">
        <div className="banner-main">상태 확인 중…</div>
        <StatusDetailStrip details={statusDetails(status, connected)} />
      </div>
    );
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
      <div className="banner-main">
        <span>{healthLabel(status.health)}</span>
        {status.executions_blocked && status.health !== "online" && (
          <span className="banner-block"> · 신규 명령 실행 차단됨</span>
        )}
        {status.live_lock && <span className="banner-lock"> · 라이브 잠금 활성 (read-only)</span>}
      </div>
      <StatusDetailStrip details={statusDetails(status, connected)} />
      {guidance && <div className="banner-guidance">{guidance}</div>}
    </div>
  );
}

function StatusDetailStrip({ details }: { details: StatusDetail[] }) {
  return (
    <div className="status-detail-strip" aria-label="운영 상태 상세">
      {details.map((detail) => (
        <span key={detail.label} className={`status-detail status-detail-${detail.tone}`}>
          <span className="status-detail-label">{detail.label}</span>
          <span className="status-detail-value">{detail.value}</span>
        </span>
      ))}
    </div>
  );
}
