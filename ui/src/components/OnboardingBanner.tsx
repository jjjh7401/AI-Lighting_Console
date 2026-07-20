// Non-intrusive onboarding banner (M3 — REQ-DEPLOY-005, first-run guidance not a
// forced wizard): when the active provider's API key is unset, a slim banner
// points the operator to Settings. The show/hide decision is the pure, tested
// onboardingMessage(); this component only fetches state and renders.
import { useEffect, useState } from "react";

import { onboardingMessage, parseSettingsResponse } from "../settings";

export function OnboardingBanner({
  onOpenSettings,
  refreshSignal,
}: {
  onOpenSettings: () => void;
  refreshSignal: number;
}) {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    (async () => {
      try {
        const response = await fetch("/api/settings");
        const parsed = parseSettingsResponse(await response.text());
        if (!disposed) setMessage(parsed === null ? null : onboardingMessage(parsed));
      } catch {
        if (!disposed) setMessage(null);
      }
    })();
    return () => {
      disposed = true;
    };
  }, [refreshSignal]);

  if (message === null) return null;

  return (
    <div className="onboarding-banner">
      <span>{message}</span>
      <button className="onboarding-open" onClick={onOpenSettings}>
        설정 열기
      </button>
    </div>
  );
}
