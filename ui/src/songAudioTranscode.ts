/**
 * 곡 오디오를 **모노 다운샘플 WAV** 로 바꿔 8 MiB 상한 안에 들여보낸다.
 *
 * ## 왜 필요한가 (실측 2026-09-14)
 *
 * 감독이 준 실제 곡 9개 중 **3개가 상한을 넘어 앱에 올라가지 않는다** —
 * `Cut and Run` 8.6MB · `scott-buckley-neon` 10.4MB · 감독 곡 31.5MB.
 * 8 MiB 상한은 `REQ-MUSICSYNC-014` 가 [Ubiquitous] 로 못박은 제품 계약이므로
 * 올릴 수 없다.
 *
 * ## 왜 품질을 거의 안 잃는가
 *
 * 서버의 `server/audio/analyze.py` 는 받은 바이트로 이렇게 한다:
 *
 * ```python
 * mono = numpy.ascontiguousarray(samples.mean(axis=1), ...)  # 스테레오를 즉시 버린다
 * librosa.beat.beat_track(y=mono, sr=sample_rate, ...)       # 원본 sr 을 그대로 쓴다
 * ```
 *
 * 즉 **스테레오는 이미 버려지고**, librosa 자체 기본 sr 이 22050 이다. 44.1kHz
 * 스테레오를 보내는 것은 분석에 쓰이지 않는 바이트를 네 배로 보내는 일이다.
 *
 * ## 감독 결정 (2026-09-14): 길이에 맞춰 자동
 *
 * 고정 sr 하나로는 안 된다 — 22050 은 짧은 곡에 충분하지만 260초 곡에서 10.9 MiB
 * 가 되고, 16000 고정은 짧은 곡에서도 8kHz 위를 버린다. 그래서 **사다리**를
 * 쓴다: 위에서부터 상한 안에 드는 첫 값을 고른다. 짧은 곡은 librosa 기본값
 * 22050 을 그대로 받으므로 지금과 같고, 긴 곡만 필요한 만큼 내려간다.
 *
 * 사다리 하한 11025 는 **곡 길이 한계**를 만든다 — 약 6분 20초. 그보다 긴 곡은
 * 어떤 sr 로도 상한에 안 들어오므로 `null` 을 답한다. 숨기지 않고 화면에 밝힌다.
 *
 * ## 전송 계약은 하나도 안 건드린다
 *
 * 상한(8 MiB) · 전송 수단(base64 over 로컬 WebSocket) · Tauri capability
 * (`no http, no websocket, no upload`) 전부 그대로다. 바뀌는 것은 클라이언트가
 * **무엇을 인코딩해 보내는가** 뿐이고, 그것은 `REQ-MUSICSYNC-014` 가 규정하지
 * 않는다.
 */

/** `server/web/messages.py` 의 `MAX_SONG_AUDIO_BYTES` 와 같은 값. */
export const MAX_SONG_AUDIO_BYTES = 8 * 1024 * 1024;

/**
 * sr 사다리 — 위에서부터 상한 안에 드는 첫 값을 쓴다.
 *
 * 22050 이 맨 위인 이유는 그것이 librosa 의 기본 sr 이기 때문이다. 즉 사다리
 * 첫 칸은 「분석기가 원래 쓰는 값」이고, 아래 칸들은 상한이 강제할 때만 쓴다.
 */
export const SAMPLE_RATE_LADDER = [22050, 16000, 11025] as const;

/** RIFF/WAVE 헤더 크기. 모노 16비트 PCM 은 확장 청크가 없다. */
const WAV_HEADER_BYTES = 44;

/** 모노 16비트 WAV 한 개의 바이트 수. */
export function estimateWavBytes(durationSeconds: number, sampleRate: number): number {
  const frames = Math.ceil(durationSeconds * sampleRate);
  return WAV_HEADER_BYTES + frames * 2;
}

/**
 * 이 길이의 곡을 상한 안에 넣을 수 있는 가장 높은 사다리 sr — 없으면 `null`.
 *
 * `null` 은 「변환하면 들어간다」의 부재이지 「파일이 깨졌다」가 아니다. 호출자는
 * 상한 수치와 함께 **길이가 원인**임을 사람에게 말해야 한다.
 */
export function pickSampleRate(durationSeconds: number): number | null {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return null;
  for (const sampleRate of SAMPLE_RATE_LADDER) {
    if (estimateWavBytes(durationSeconds, sampleRate) <= MAX_SONG_AUDIO_BYTES) {
      return sampleRate;
    }
  }
  return null;
}

/**
 * 사다리 하한이 만드는 곡 길이 한계, 초. 화면 문구가 이 값을 쓴다 — 숫자를 두
 * 곳에 따로 적으면 한쪽만 고쳐진다.
 */
export const MAX_TRANSCODABLE_SECONDS = Math.floor(
  (MAX_SONG_AUDIO_BYTES - WAV_HEADER_BYTES) /
    (SAMPLE_RATE_LADDER[SAMPLE_RATE_LADDER.length - 1] * 2),
);

/**
 * 모노 Float32 표본을 16비트 PCM WAV 바이트로 싼다.
 *
 * 클램프를 빼면 -1..1 을 넘는 표본이 정수 래핑으로 **반대 부호의 큰 값**이 되어
 * 딸깍 소리가 아니라 온셋으로 읽힌다 — 분석기가 그것을 경계로 볼 수 있다.
 */
export function encodeWavMono16(samples: Float32Array, sampleRate: number): Uint8Array {
  const bytes = new Uint8Array(WAV_HEADER_BYTES + samples.length * 2);
  const view = new DataView(bytes.buffer);

  const writeAscii = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  };

  const dataBytes = samples.length * 2;
  writeAscii(0, "RIFF");
  view.setUint32(4, 36 + dataBytes, true);
  writeAscii(8, "WAVE");
  writeAscii(12, "fmt ");
  view.setUint32(16, 16, true); // fmt 청크 크기
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // 모노
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // 바이트/초
  view.setUint16(32, 2, true); // 바이트/프레임
  view.setUint16(34, 16, true); // 비트/표본
  writeAscii(36, "data");
  view.setUint32(40, dataBytes, true);

  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(WAV_HEADER_BYTES + index * 2, Math.round(clamped * 32767), true);
  }
  return bytes;
}

/** 원본 파일명을 변환된 WAV 의 이름으로 — 확장자만 갈아낀다. */
export function transcodedFileName(originalName: string): string {
  const dot = originalName.lastIndexOf(".");
  const stem = dot > 0 ? originalName.slice(0, dot) : originalName;
  return `${stem}.wav`;
}

/** `Uint8Array` → base64. 큰 배열에서 스택이 터지지 않게 조각으로 넘긴다. */
export function toBase64(bytes: Uint8Array): string {
  const CHUNK = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + CHUNK));
  }
  return btoa(binary);
}

/** 변환 결과 — 사람에게 무엇이 바뀌었는지 말할 수 있을 만큼 싣는다. */
export interface TranscodedSongAudio {
  fileName: string;
  mimeType: "audio/wav";
  contentBase64: string;
  sampleRate: number;
  durationSeconds: number;
  byteLength: number;
}

/**
 * 파일 하나를 모노 다운샘플 WAV 로 바꾼다. 상한에 넣을 수 없으면 `null`.
 *
 * 브라우저 API(`AudioContext` / `OfflineAudioContext`)를 쓰는 유일한 자리이며
 * 얇게 유지한다 — 이 저장소에는 DOM 시험 하네스가 없으므로(`App.test.tsx` 헤더)
 * 판단 로직은 전부 위의 순수 함수에 있고 여기서는 그것을 부르기만 한다.
 *
 * `OfflineAudioContext` 를 채널 1개로 만들면 다운믹스와 리샘플을 브라우저가
 * 함께 해 준다 — 손으로 보간하지 않는다.
 */
export async function transcodeSongAudio(file: File): Promise<TranscodedSongAudio | null> {
  const decodeContext = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await decodeContext.decodeAudioData(await file.arrayBuffer());
  } finally {
    void decodeContext.close();
  }

  const sampleRate = pickSampleRate(decoded.duration);
  if (sampleRate === null) return null;

  const frames = Math.ceil(decoded.duration * sampleRate);
  const offline = new OfflineAudioContext(1, frames, sampleRate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();

  const bytes = encodeWavMono16(rendered.getChannelData(0), sampleRate);
  return {
    fileName: transcodedFileName(file.name),
    mimeType: "audio/wav",
    contentBase64: toBase64(bytes),
    sampleRate,
    durationSeconds: decoded.duration,
    byteLength: bytes.length,
  };
}
