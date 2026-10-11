// 카드 t571(SPEC-LDBEAT-001 REQ-LDBEAT-024(c) 후속) — 서버가 돌려준 저장된
// 오디오 링크를 `File`로 되돌린다.
//
// 분할 조립 자체(begin/chunk/end 상태 전이)는 `protocol.ts`가 든다(DOM 무관,
// 서버 `SongAudioAssembly`의 클라이언트 짝) — 이 모듈은 이미 다 모인
// base64 문자열을 `File`로 바꾸는, 딱 그 한 걸음만 맡는다. `atob`/`Uint8Array`/
// `File`은 Node 18+ 전역이라(이 저장소의 vitest 는 jsdom 없이 돈다,
// `audioAutoConnect.ts`와 같은 바운드) jsdom 없이도 시험할 수 있다.

/** base64 → 원본 바이트. */
export function base64ToBytes(contentBase64: string): Uint8Array {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** 서버가 돌려준 오디오 링크(단일 프레임이든 분할 조립 결과든, 둘 다
 * `protocol.ts`에서 같은 모양으로 접힌다)를 `attachedSongAudioFile`과 같은
 * `File`로 되돌린다. 세션 업로드가 들고 있는 `File`과 구분할 자리에서
 * `BeatGrid`가 쓸 `linkedSongAudioFile` 프로퍼티용이다. */
export function buildFileFromSongAudioLink(params: {
  fileName: string;
  mimeType: string;
  contentBase64: string;
}): File {
  const bytes = base64ToBytes(params.contentBase64);
  return new File([bytes], params.fileName, { type: params.mimeType });
}
