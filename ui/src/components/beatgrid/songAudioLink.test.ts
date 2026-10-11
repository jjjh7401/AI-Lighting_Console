import { describe, expect, it } from "vitest";

import { base64ToBytes, buildFileFromSongAudioLink } from "./songAudioLink";

describe("base64ToBytes", () => {
  it("decodes to the original bytes", () => {
    const original = new Uint8Array([0, 1, 2, 3, 255, 254, 253]);
    let binary = "";
    for (const byte of original) binary += String.fromCharCode(byte);
    const encoded = btoa(binary);
    expect(Array.from(base64ToBytes(encoded))).toEqual(Array.from(original));
  });

  it("decodes an empty string to zero bytes", () => {
    expect(base64ToBytes("").length).toBe(0);
  });
});

describe("buildFileFromSongAudioLink", () => {
  it("builds a File carrying the given name, type, and bytes", async () => {
    const original = new Uint8Array([10, 20, 30]);
    let binary = "";
    for (const byte of original) binary += String.fromCharCode(byte);
    const file = buildFileFromSongAudioLink({
      fileName: "track.wav",
      mimeType: "audio/wav",
      contentBase64: btoa(binary),
    });
    expect(file.name).toBe("track.wav");
    expect(file.type).toBe("audio/wav");
    expect(file.size).toBe(original.length);
    const bytes = new Uint8Array(await file.arrayBuffer());
    expect(Array.from(bytes)).toEqual(Array.from(original));
  });

  it("builds a File usable by audioSourceId (name + size identity)", () => {
    // audioAutoConnect.ts의 audioSourceId는 {name, size}만 본다 — 이 함수가
    // 만든 File도 그 모양을 그대로 만족해야 한다(BeatGrid가 같은 경로로
    // 먹인다).
    const file = buildFileFromSongAudioLink({
      fileName: "a.mp3",
      mimeType: "audio/mpeg",
      contentBase64: "",
    });
    expect(typeof file.name).toBe("string");
    expect(typeof file.size).toBe("number");
  });
});
