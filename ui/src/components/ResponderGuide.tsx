// Responder provisioning guide (M4 — REQ-DEPLOY-010/011, AC-DEPLOY-006/007):
// an in-app button that installs the bundled CopilotResponder plugin into the
// onPC import directory, plus the onPC-load steps and the OSC-output-port
// instruction. All parse/status/summary logic lives in the pure, unit-tested
// provision.ts; this component only owns fetch() + React state.
//
// This surface NEVER sends an OSC command — provisioning is a filesystem copy on
// the backend. Only the file copy is off-gate (REQ-DEPLOY-024).
import { useCallback, useEffect, useState } from "react";

import { apiUrl } from "../launchContext";
import {
  allInstalled,
  installSummary,
  oscSlotWarning,
  parseInstalledList,
  parseResponderStatus,
  type ResponderStatusResponse,
} from "../provision";

export function ResponderGuide() {
  const [status, setStatus] = useState<ResponderStatusResponse | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await fetch(apiUrl("/api/provision/responder"));
      const parsed = parseResponderStatus(await response.text());
      if (parsed !== null) setStatus(parsed);
    } catch {
      setNotice("responder 상태를 불러오지 못했습니다 — 서버 연결을 확인해 주세요.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // `confirm` is passed ONLY by the explicit overwrite button. The plain
  // install button never sends it, so a slot disagreement stops the first time
  // regardless of what the UI believes the server state to be.
  const install = async (confirm = false) => {
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(
        apiUrl(`/api/provision/responder${confirm ? "?confirm_osc_slot=true" : ""}`),
        { method: "POST" },
      );
      if (response.status === 409) {
        // The guard refused and wrote nothing. Re-read so the warning below
        // reflects the server's view rather than this component's stale one.
        await load();
        setNotice(
          "설치를 중단했습니다 — OSC 응답 행이 설치본과 다릅니다. 아래 경고를 확인해 주세요.",
        );
        return;
      }
      if (response.ok) {
        // The POST body's ``installed`` is the list of files copied (distinct from
        // the GET status shape), so parse it with the dedicated list helper.
        setNotice(installSummary(parseInstalledList(await response.text())));
        await load();
      } else {
        setNotice(
          "responder 설치에 실패했습니다 — 플러그인 임포트 디렉터리 경로와 쓰기 권한을 확인해 주세요.",
        );
      }
    } catch {
      setNotice("responder 설치 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-section">
      <h3>CopilotResponder 설치</h3>
      <p className="settings-hint">
        onPC와 통신하려면 CopilotResponder 플러그인을 설치하고 onPC에서 로드해야 합니다.
      </p>

      {status !== null && (
        <>
          <p className="settings-hint">
            임포트 디렉터리: <code>{status.import_dir}</code>
            {allInstalled(status) ? " — 설치됨" : " — 미설치"}
          </p>
          <button className="settings-btn primary" disabled={busy} onClick={() => void install()}>
            responder 설치
          </button>
          {oscSlotWarning(status) !== null && (
            <div className="settings-notice warning">
              <p>{oscSlotWarning(status)}</p>
              <button
                className="settings-btn"
                disabled={busy}
                onClick={() => void install(true)}
              >
                설정 값으로 덮어쓰기
              </button>
            </div>
          )}
          <ol className="responder-steps">
            {status.guide.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </>
      )}

      {notice !== null && <div className="settings-notice">{notice}</div>}
    </section>
  );
}
