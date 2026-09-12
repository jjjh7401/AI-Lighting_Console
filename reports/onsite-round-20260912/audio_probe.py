"""경로 1단계 실측 — analyze() 가 실제로 BPM·구간·세기를 내는가.

저장소에 실제 곡 오디오가 없어(find 결과 0건) 합성 곡을 만들어 쏜다.
합성 곡은 실제 곡이 아니므로 이 측정이 답하는 것은 「분석기가 도는가」이지
「실제 곡에서 맞는가」가 아니다.
"""

import io
import math
import struct
import wave

from server.audio.analyze import AnalysisFailure, AnalysisResult, analyze

SR = 22050
BPM = 120.0
#: (구간 길이 초, 진폭) — 조용 → 중간 → 크게 → 아주 조용 → 최대
PLANS = {
    "A 원본 (큰 계단 포함)": [(8, 0.10), (8, 0.35), (8, 0.85), (6, 0.06), (10, 1.00)],
    "B 대조군 (큰 계단 제거)": [(8, 0.10), (8, 0.35), (8, 0.85), (6, 0.40), (10, 0.90)],
    "C 대조군 (계단만 둘)": [(8, 0.35), (8, 0.85)],
}


def synth(PLAN) -> bytes:
    beat = 60.0 / BPM
    frames = bytearray()
    t = 0.0
    for seconds, amp in PLAN:
        n = int(seconds * SR)
        for i in range(n):
            tt = t + i / SR
            # 비트마다 어택이 있는 단순 펄스 + 저음
            phase = (tt % beat) / beat
            env = math.exp(-6.0 * phase)
            v = amp * env * math.sin(2 * math.pi * 110.0 * tt)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32000))
        t += seconds
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    return buf.getvalue()


for name, PLAN in PLANS.items():
    audio = synth(PLAN)
    out = analyze(audio)
    print(f"\n=== {name} ===")
    print("  심은 진폭:", [a for _, a in PLAN], f"→ 심은 경계 {len(PLAN) - 1}개")
    if isinstance(out, AnalysisFailure):
        print("  🔴 실패:", out.reason)
        continue
    assert isinstance(out, AnalysisResult)
    print(
        f"  BPM {out.bpm:.1f} (신뢰도 {out.bpm_confidence:.3f})"
        f" · 검출 구간 {len(out.d_candidates)}개"
    )
    for c in out.d_candidates:
        print(f"    {c.start_ms / 1000:5.1f}~{c.end_ms / 1000:5.1f}s  D{c.d_level}")
