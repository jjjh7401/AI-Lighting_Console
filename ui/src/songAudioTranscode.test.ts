// 곡 오디오 다운샘플 변환 — 8 MiB 상한 안에 넣는 판단부.
//
// 이 저장소에는 DOM 시험 하네스가 없다(App.test.tsx 헤더). 그래서
// `transcodeSongAudio` 의 브라우저 API 부분은 여기서 부르지 않고, 판단 로직만
// 순수 함수로 갈라 시험한다 — 그것이 이 모듈을 그렇게 나눈 이유다.
//
// 길이는 전부 **실측값**이다 (2026-09-14, `.moai/reports/threshold-widen-20260914/`).
// 감독이 준 실제 곡을 `analyze()` 로 태워 얻은 duration 이며, 지어낸 숫자가 아니다.
import { describe, expect, it } from "vitest";

import {
  MAX_SONG_AUDIO_BYTES,
  MAX_TRANSCODABLE_SECONDS,
  SAMPLE_RATE_LADDER,
  encodeWavMono16,
  estimateWavBytes,
  pickSampleRate,
  transcodedFileName,
} from "./songAudioTranscode";

/** 실측 곡 길이, 초 — 상한을 넘어 지금 올라가지 않는 셋에 ✗ 를 달았다. */
const MEASURED_SECONDS = {
  iceCream: 78.1,
  letsDance: 91.0,
  clubDiver: 145.7,
  morning: 153.3,
  dinoDino: 178.3, // ✗ 원본 31.5MB
  tooCool: 181.6,
  cutAndRun: 214.8, // ✗ 원본 8.6MB
  rain: 222.6,
  neon: 259.1, // ✗ 원본 10.4MB
} as const;

describe("사다리가 상한 안에 드는 가장 높은 sr 을 고른다", () => {
  it("짧은 곡은 librosa 기본값 22050 을 그대로 받는다", () => {
    // 감독 곡(178.3초)이 여기 속한다 — 품질을 하나도 안 내주고 31.5MB 가 통과한다.
    expect(pickSampleRate(MEASURED_SECONDS.dinoDino)).toBe(22050);
    expect(pickSampleRate(MEASURED_SECONDS.morning)).toBe(22050);
    expect(pickSampleRate(MEASURED_SECONDS.iceCream)).toBe(22050);
  });

  it("긴 곡은 필요한 만큼만 내려간다", () => {
    expect(pickSampleRate(MEASURED_SECONDS.cutAndRun)).toBe(16000);
    expect(pickSampleRate(MEASURED_SECONDS.neon)).toBe(16000);
    expect(pickSampleRate(MEASURED_SECONDS.rain)).toBe(16000);
  });

  it("실측 9곡 전부 상한 안에 들어온다", () => {
    for (const [name, seconds] of Object.entries(MEASURED_SECONDS)) {
      const sampleRate = pickSampleRate(seconds);
      expect(sampleRate, name).not.toBeNull();
      expect(estimateWavBytes(seconds, sampleRate as number), name).toBeLessThanOrEqual(
        MAX_SONG_AUDIO_BYTES,
      );
    }
  });

  it("사다리가 공허하지 않다 — 고정 22050 으로는 셋이 상한을 넘는다", () => {
    // 대조군. 이 단언이 없으면 위 시험들은 「아무 sr 이나 다 들어간다」와
    // 구별되지 않는다. 사다리가 실제로 일을 하는지 재는 자리다.
    //
    // 🔴 이 대조군이 실제로 일했다 — 처음에 `tooCool`(181.6초)을 초과 목록에
    // 넣었는데 22050 에서 8,008,604바이트로 상한 안이다. 코드가 아니라 내가
    // 틀렸고, 이 단언이 그것을 잡았다.
    const overAt22050 = Object.entries(MEASURED_SECONDS).filter(
      ([, seconds]) => estimateWavBytes(seconds, 22050) > MAX_SONG_AUDIO_BYTES,
    );
    expect(overAt22050.map(([name]) => name)).toEqual(["cutAndRun", "rain", "neon"]);
  });

  it("사다리는 내림차순이다 — 첫 칸이 가장 높아야 「가장 높은 값」이 성립한다", () => {
    const descending = [...SAMPLE_RATE_LADDER].sort((a, b) => b - a);
    expect([...SAMPLE_RATE_LADDER]).toEqual(descending);
  });
});

describe("들어갈 수 없는 곡은 숨기지 않고 null 이다", () => {
  it("하한 sr 로도 안 들어가면 null", () => {
    expect(pickSampleRate(MAX_TRANSCODABLE_SECONDS + 1)).toBeNull();
    expect(pickSampleRate(600)).toBeNull();
  });

  it("한계 길이는 정확히 경계다 — 그 값은 들어가고 1초 더는 안 들어간다", () => {
    expect(pickSampleRate(MAX_TRANSCODABLE_SECONDS)).toBe(11025);
    expect(
      estimateWavBytes(MAX_TRANSCODABLE_SECONDS, 11025),
    ).toBeLessThanOrEqual(MAX_SONG_AUDIO_BYTES);
    expect(estimateWavBytes(MAX_TRANSCODABLE_SECONDS + 1, 11025)).toBeGreaterThan(
      MAX_SONG_AUDIO_BYTES,
    );
  });

  it("한계는 6분 20초 근처다 — 화면 문구가 이 값을 쓴다", () => {
    expect(MAX_TRANSCODABLE_SECONDS).toBe(380);
  });

  it("쓰레기 길이를 0 이나 NaN 으로 받아도 지어내지 않는다", () => {
    expect(pickSampleRate(0)).toBeNull();
    expect(pickSampleRate(-1)).toBeNull();
    expect(pickSampleRate(Number.NaN)).toBeNull();
    expect(pickSampleRate(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("WAV 인코더가 서버가 읽을 수 있는 바이트를 낸다", () => {
  const ascii = (bytes: Uint8Array, offset: number, length: number) =>
    String.fromCharCode(...bytes.subarray(offset, offset + length));

  it("RIFF/WAVE/fmt/data 청크 이름이 자리에 있다", () => {
    const bytes = encodeWavMono16(new Float32Array(4), 22050);
    expect(ascii(bytes, 0, 4)).toBe("RIFF");
    expect(ascii(bytes, 8, 4)).toBe("WAVE");
    expect(ascii(bytes, 12, 4)).toBe("fmt ");
    expect(ascii(bytes, 36, 4)).toBe("data");
  });

  it("모노 16비트 PCM 으로 적고 sr 을 그대로 싣는다", () => {
    const bytes = encodeWavMono16(new Float32Array(8), 16000);
    const view = new DataView(bytes.buffer);
    expect(view.getUint16(20, true)).toBe(1); // PCM
    expect(view.getUint16(22, true)).toBe(1); // 채널 1개
    expect(view.getUint32(24, true)).toBe(16000);
    expect(view.getUint32(28, true)).toBe(16000 * 2); // 바이트/초
    expect(view.getUint16(32, true)).toBe(2); // 바이트/프레임
    expect(view.getUint16(34, true)).toBe(16); // 비트/표본
  });

  it("길이 필드가 실제 바이트와 맞는다", () => {
    const samples = new Float32Array(100);
    const bytes = encodeWavMono16(samples, 11025);
    const view = new DataView(bytes.buffer);
    expect(bytes.length).toBe(44 + 200);
    expect(view.getUint32(4, true)).toBe(36 + 200);
    expect(view.getUint32(40, true)).toBe(200);
  });

  it("범위를 넘는 표본을 클램프한다 — 래핑하면 부호가 뒤집혀 온셋으로 읽힌다", () => {
    const bytes = encodeWavMono16(new Float32Array([2, -2, 0]), 22050);
    const view = new DataView(bytes.buffer);
    expect(view.getInt16(44, true)).toBe(32767);
    expect(view.getInt16(46, true)).toBe(-32767);
    expect(view.getInt16(48, true)).toBe(0);
  });

  it("estimateWavBytes 가 실제 인코딩 결과와 일치한다", () => {
    // 추정과 실제가 어긋나면 상한 판단이 조용히 틀린다.
    const sampleRate = 11025;
    const seconds = 2;
    const samples = new Float32Array(Math.ceil(seconds * sampleRate));
    expect(encodeWavMono16(samples, sampleRate).length).toBe(
      estimateWavBytes(seconds, sampleRate),
    );
  });
});

describe("변환된 파일 이름", () => {
  it("확장자만 wav 로 갈아낀다", () => {
    expect(transcodedFileName("걸그룹DinoDino_C_max최고품질.wav")).toBe(
      "걸그룹DinoDino_C_max최고품질.wav",
    );
    expect(transcodedFileName("Cut and Run.mp3")).toBe("Cut and Run.wav");
    expect(transcodedFileName("scott-buckley-neon.mp3")).toBe("scott-buckley-neon.wav");
  });

  it("점이 없는 이름에도 확장자를 붙인다 — 서버는 확장자로 종류를 본다", () => {
    expect(transcodedFileName("track")).toBe("track.wav");
  });

  it("숨김 파일의 앞 점을 확장자로 오해하지 않는다", () => {
    expect(transcodedFileName(".hidden")).toBe(".hidden.wav");
  });
});
