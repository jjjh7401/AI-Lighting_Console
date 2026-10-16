// 콘솔 타임코드가 아직 돌고 있을 수 있다는 큰 알림 — 2차 전체 실행 N11.
// 「콘솔 같이」 정지는 승인 카드(`Off Timecode N`)를 따로 거친다. 카드가 거절·만료되면 앱 음원은 멈춰도
// 콘솔 타임코드는 계속 돈다. 그 사이 화면에 크게 보이고, 여기서 다시 끌 수 있다(끄기도 승인 카드를 거친다).
// 판정은 보낸 명령의 결과다(콘솔을 읽은 값이 아니다) — 문구가 「돌고 있을 수 있어요」 인 이유다.

export function ConsoleRunningBanner({
  visible,
  timecodeNumber,
  approvalPending,
  onStop,
}: {
  visible: boolean;
  timecodeNumber: number | null;
  /** 승인 카드가 떠 있는가(정지 카드를 기다리는 중일 수 있다). */
  approvalPending: boolean;
  onStop?: () => void;
}) {
  if (!visible) return null;
  const target = timecodeNumber !== null ? `Timecode ${timecodeNumber}` : "타임코드";
  return (
    <div className="beat-grid-console-running" role="alert">
      <strong>⚠ 콘솔 {target} 가 아직 돌고 있을 수 있어요</strong>
      <span>
        {approvalPending
          ? " — 정지 승인 카드를 기다리고 있어요. 카드에서 승인해야 콘솔이 멈춰요."
          : " — 앱은 멈췄지만 콘솔 정지가 확인되지 않았어요."}
      </span>
      {onStop && !approvalPending && (
        <button type="button" className="tbtn" onClick={onStop}>
          ■ 콘솔 끄기
        </button>
      )}
    </div>
  );
}
