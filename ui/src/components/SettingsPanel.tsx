// In-app settings view (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003): terminal-free
// editing of API keys (masked, write-only), OSC ports, the plugin import
// directory, and the active provider. All request/parse/validate logic lives in
// the pure, unit-tested settings.ts; this component owns fetch() + React state.
import { useCallback, useEffect, useState } from "react";

import { apiUrl } from "../launchContext";
import {
  buildKeyPayload,
  buildSettingsPayload,
  formFromSettings,
  parseSettingsResponse,
  providerLabel,
  validateSettingsForm,
  type SettingsForm,
  type SettingsResponse,
} from "../settings";
import { ResponderGuide } from "./ResponderGuide";

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [loaded, setLoaded] = useState<SettingsResponse | null>(null);
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [keyDrafts, setKeyDrafts] = useState<Record<string, string>>({});
  // Providers for which the OS keystore was unavailable -> offer session-only.
  const [sessionOffer, setSessionOffer] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await fetch(apiUrl("/api/settings"));
      const parsed = parseSettingsResponse(await response.text());
      if (parsed !== null) {
        setLoaded(parsed);
        setForm(formFromSettings(parsed.settings));
      }
    } catch {
      setNotice("설정을 불러오지 못했습니다 — 서버 연결을 확인해 주세요.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const patch = (fields: Partial<SettingsForm>) =>
    setForm((current) => (current === null ? current : { ...current, ...fields }));

  const saveSettings = async () => {
    if (form === null) return;
    const found = validateSettingsForm(form);
    setErrors(found);
    if (found.length > 0) return;
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(apiUrl("/api/settings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: buildSettingsPayload(form),
      });
      if (response.ok) {
        setNotice("설정을 저장했습니다.");
        await load();
      } else {
        setNotice("설정 저장에 실패했습니다 — 입력값을 확인해 주세요.");
      }
    } catch {
      setNotice("설정 저장 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const saveKey = async (provider: string, sessionOnly: boolean) => {
    const key = (keyDrafts[provider] ?? "").trim();
    if (key === "") return;
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(apiUrl("/api/keys"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: buildKeyPayload(provider, key, sessionOnly),
      });
      if (response.ok) {
        setKeyDrafts((drafts) => ({ ...drafts, [provider]: "" }));
        setSessionOffer((offers) => ({ ...offers, [provider]: false }));
        setNotice(
          sessionOnly
            ? `${providerLabel(provider)} 키를 이번 세션에만 저장했습니다.`
            : `${providerLabel(provider)} 키를 저장했습니다.`,
        );
        await load();
      } else if (response.status === 503) {
        // OS credential store unavailable/locked/denied — offer session-only
        // (REQ-DEPLOY-006a; never a plaintext-disk fallback).
        setSessionOffer((offers) => ({ ...offers, [provider]: true }));
        setNotice(
          `${providerLabel(provider)}: OS 자격 증명 저장소를 사용할 수 없습니다 — 키는 디스크에 저장되지 않았습니다. 이번 세션에만 사용하려면 아래 버튼을 눌러 주세요.`,
        );
      } else {
        setNotice(`${providerLabel(provider)} 키 저장에 실패했습니다.`);
      }
    } catch {
      setNotice("키 저장 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const deleteKey = async (provider: string) => {
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(apiUrl(`/api/keys/${provider}`), { method: "DELETE" });
      if (response.ok) {
        setNotice(`${providerLabel(provider)} 키를 삭제했습니다.`);
        await load();
      } else {
        setNotice(`${providerLabel(provider)} 키 삭제에 실패했습니다.`);
      }
    } catch {
      setNotice("키 삭제 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="settings-overlay" role="dialog" aria-label="설정">
      <div className="settings-panel">
        <div className="settings-head">
          <h2>설정</h2>
          <button className="settings-close" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>

        {loaded === null || form === null ? (
          <div className="settings-loading">불러오는 중…</div>
        ) : (
          <>
            <section className="settings-section">
              <h3>API 키</h3>
              <p className="settings-hint">
                키는 OS 자격 증명 저장소에만 저장되며 화면에 다시 표시되지 않습니다.
              </p>
              {loaded.providers.map((provider) => (
                <div key={provider} className="settings-key-row">
                  <label>
                    {providerLabel(provider)}
                    <span className={loaded.keys[provider] ? "key-set" : "key-unset"}>
                      {loaded.keys[provider] ? "키 설정됨" : "키 없음"}
                    </span>
                  </label>
                  <div className="settings-key-controls">
                    <input
                      type="password"
                      autoComplete="off"
                      placeholder={loaded.keys[provider] ? "새 키 입력 (변경 시)" : "API 키 입력"}
                      value={keyDrafts[provider] ?? ""}
                      onChange={(event) =>
                        setKeyDrafts((drafts) => ({ ...drafts, [provider]: event.target.value }))
                      }
                    />
                    <button
                      className="settings-btn"
                      disabled={busy || (keyDrafts[provider] ?? "").trim() === ""}
                      onClick={() => saveKey(provider, false)}
                    >
                      키 저장
                    </button>
                    {loaded.keys[provider] && (
                      <button
                        className="settings-btn danger"
                        disabled={busy}
                        onClick={() => deleteKey(provider)}
                      >
                        삭제
                      </button>
                    )}
                  </div>
                  {sessionOffer[provider] && (
                    <button
                      className="settings-btn session"
                      disabled={busy || (keyDrafts[provider] ?? "").trim() === ""}
                      onClick={() => saveKey(provider, true)}
                    >
                      이번 세션에만 저장
                    </button>
                  )}
                </div>
              ))}
              {!loaded.keystore_available && (
                <p className="settings-warn">
                  OS 자격 증명 저장소를 사용할 수 없습니다 — 키는 이번 세션에만 저장됩니다.
                </p>
              )}
            </section>

            <section className="settings-section">
              <h3>연결 · 프로바이더</h3>
              <label className="settings-field">
                활성 프로바이더
                <select
                  value={form.active_provider}
                  onChange={(event) => patch({ active_provider: event.target.value })}
                >
                  {loaded.providers.map((provider) => (
                    <option key={provider} value={provider}>
                      {providerLabel(provider)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="settings-field">
                OSC 콘솔 송신 포트
                <input
                  type="number"
                  value={form.console_port}
                  onChange={(event) => patch({ console_port: Number(event.target.value) })}
                />
              </label>
              <label className="settings-field">
                OSC 피드백 수신 포트
                <input
                  type="number"
                  value={form.receive_port}
                  onChange={(event) => patch({ receive_port: Number(event.target.value) })}
                />
              </label>
              <label className="settings-field">
                플러그인 임포트 디렉터리
                <input
                  type="text"
                  value={form.plugin_import_dir}
                  onChange={(event) => patch({ plugin_import_dir: event.target.value })}
                />
              </label>
              <label className="settings-field readonly">
                웹 서버 (읽기 전용)
                <input type="text" value={`${loaded.settings.web_host}:${loaded.settings.web_port}`} readOnly />
              </label>
            </section>

            <ResponderGuide />

            {errors.length > 0 && (
              <ul className="settings-errors">
                {errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            )}

            <div className="settings-actions">
              <button className="settings-btn primary" disabled={busy} onClick={saveSettings}>
                설정 저장
              </button>
            </div>
          </>
        )}

        {notice !== null && <div className="settings-notice">{notice}</div>}
      </div>
    </div>
  );
}
