// 불러오기 성공 뒤 연결을 한 번 다시 맺는 규칙. 서버는 연결할 때 세션 값(줄 머리 sub_info 등)을
// 다시 보내므로, 이 재연결이 곧 상태 재수신이다. 불러오기가 실패하면(결과가 없으면) 연결을 건드리지 않는다.

/** 불러오기 결과가 있으면 재연결을 한 번 부르고 `true`, 결과가 없으면 아무것도 하지 않고 `false`. */
export function reconnectAfterTimelineLoad(loaded: unknown, reconnect: () => void): boolean {
  if (loaded === null) return false;
  reconnect();
  return true;
}
