"""t509 — LOVE ATTACK 음악 순간 지도 (t505 스크립트를 곡 일반으로 바꾼 사본, 제품 코드 수정 0).

바뀐 점(t505 대비): 구간은 t509 app_sections.py 가 앱 경로로 낸 JSON 에서 읽는다.
출력 파일 이름은 음원 이름에서 딴다. 측정 방법(비트·HPSS·대역·다운비트 근거)은 같다.

실행 (프로젝트 venv, librosa 0.11.0):
    PY=.venv/bin/python; M=.moai/reports/t505/measure_music_map.py
    $PY $M map-phase "<song.mp3>" <out_dir> <listen_dir> <phase 0~3> <app_sections.json>
    $PY $M bpm8 <sample_music_dir> <out_dir>
    $PY $M listen-double "<song>" <listen_dir>

map  — 마디별 표(비트·다운비트·킥/스네어 후보·필·빌드업·드롭·보컬 추정)를 JSON/MD 로,
       확인용 클릭 wav 두 개(원곡+비트 클릭, 원곡+킥/스네어 클릭)를 listen_dir 에 쓴다.
bpm8 — t499 의 8곡에 앱과 같은 경로로 BPM 을 다시 재고, 절반·두 배 의심 근거를 표로 낸다.

앱 경로 재현: server/audio/analyze.py 와 같은 디코드(soundfile, 채널 평균 모노, 원 샘플레이트),
hop 512, librosa.beat.beat_track(units="time"), BPM = 60 / 박 간격 중앙값.
그 밖의 모든 것(HPSS·대역 분리·다운비트·필·빌드업·드롭·보컬)은 이 스크립트가 새로 만든 추정이다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

HOP = 512
PHASE_OVERRIDE: int | None = None
N_FFT = 2048

# 대역(Hz) — 킥 몸통 / 스네어·클랩 / 보컬 기본 대역
KICK_BAND = (35.0, 120.0)
SNARE_BAND = (1500.0, 5000.0)
SNARE_BODY_BAND = (150.0, 400.0)
VOCAL_BAND = (300.0, 3400.0)


def load_like_app(path: Path) -> tuple[np.ndarray, int]:
    samples, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(samples.mean(axis=1), dtype=np.float32)
    return mono, sr


def app_beats(y: np.ndarray, sr: int) -> tuple[np.ndarray, float, float]:
    """앱(analyze.py:352-354, _tempo_from_beats)과 같은 비트·BPM."""
    beat_times = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units="time")[1]
    intervals = np.diff(beat_times)
    intervals = intervals[intervals > 0]
    median = float(np.median(intervals))
    spread = float(np.std(intervals)) / median
    return beat_times, 60.0 / median, max(0.0, min(1.0, 1.0 - spread))


def band_energy(S: np.ndarray, freqs: np.ndarray, band: tuple[float, float]) -> np.ndarray:
    lo, hi = band
    idx = (freqs >= lo) & (freqs < hi)
    return S[idx].sum(axis=0)


def onset_env_from(energy: np.ndarray) -> np.ndarray:
    """대역 에너지(로그) 의 양의 변화량 — 단순 스펙트럴 플럭스."""
    log_e = np.log1p(energy / (np.median(energy) + 1e-9))
    flux = np.maximum(0.0, np.diff(log_e, prepend=log_e[0]))
    return flux


def pick_onsets(env: np.ndarray, sr: int, rel_threshold: float) -> np.ndarray:
    thr = rel_threshold * float(np.percentile(env, 99))
    peaks = librosa.util.peak_pick(
        env, pre_max=3, post_max=3, pre_avg=10, post_avg=10, delta=thr, wait=6
    )
    return librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)


def nearest_beat_pos(t: float, beats: np.ndarray) -> tuple[int, float]:
    """t 에 가장 가까운 박 번호와 박 길이 대비 어긋남(-0.5~0.5)."""
    i = int(np.argmin(np.abs(beats - t)))
    period = float(np.median(np.diff(beats)))
    return i, (t - beats[i]) / period


def map_song(audio: Path, out_dir: Path, listen_dir: Path, sections: list[dict]) -> dict:
    y, sr = load_like_app(audio)
    duration = len(y) / sr
    beats, bpm, conf = app_beats(y, sr)
    period = 60.0 / bpm

    # HPSS — 타악/화성 분리 (STFT 진폭에서)
    D = librosa.stft(y, n_fft=N_FFT, hop_length=HOP)
    H, P = librosa.decompose.hpss(D)
    Sp = np.abs(P) ** 2
    Sh = np.abs(H) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    frame_t = librosa.frames_to_time(np.arange(Sp.shape[1]), sr=sr, hop_length=HOP)

    kick_e = band_energy(Sp, freqs, KICK_BAND)
    snare_e = band_energy(Sp, freqs, SNARE_BAND) + band_energy(Sp, freqs, SNARE_BODY_BAND)
    perc_all = Sp.sum(axis=0)
    vocal_e = band_energy(Sh, freqs, VOCAL_BAND)
    harm_all = Sh.sum(axis=0) + 1e-12
    rms = librosa.feature.rms(y=y, frame_length=N_FFT, hop_length=HOP)[0]

    kick_t = pick_onsets(onset_env_from(kick_e), sr, 0.5)
    snare_t = pick_onsets(onset_env_from(snare_e), sr, 0.5)
    perc_onsets = librosa.onset.onset_detect(
        onset_envelope=onset_env_from(perc_all), sr=sr, hop_length=HOP, units="time"
    )

    # ---- 다운비트 추정: 박 번호 i 의 위상 (i - phase) % 4 == 0 을 마디 1박으로 본다.
    # 근거 셋을 따로 재서 각각 고른 위상을 기록한다(합의 여부가 신뢰도).
    def frame_at(t: float) -> int:
        return int(min(len(frame_t) - 1, max(0, round(t * sr / HOP))))

    # (a) 스네어·클랩 후보가 놓인 박 위치 — 백비트(2·4박)면 1박은 그 직전 박
    snare_slot = np.zeros(4)
    for t in snare_t:
        i, off = nearest_beat_pos(t, beats)
        if abs(off) < 0.2:
            snare_slot[i % 4] += 1
    # (b) 화성 변화(크로마 차이)가 큰 박 — 코드는 마디 1박에서 바뀌는 경우가 많다
    chroma = librosa.feature.chroma_cqt(y=librosa.istft(H, hop_length=HOP), sr=sr, hop_length=HOP)
    beat_frames = np.array([frame_at(t) for t in beats])
    chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
    novelty = np.r_[0.0, np.linalg.norm(np.diff(chroma_sync, axis=1), axis=0)]
    chroma_slot = np.zeros(4)
    for i, v in enumerate(novelty[: len(beats)]):
        chroma_slot[i % 4] += v
    # (c) 앱 구간 경계에 가장 가까운 박 — 구간은 마디 1박에서 시작한다는 가정
    boundary_slot = np.zeros(4)
    for s in sections[1:]:
        i, off = nearest_beat_pos(s["start_ms"] / 1000.0, beats)
        boundary_slot[i % 4] += 1

    snare_phase = int((np.argmax(snare_slot[[0, 1, 2, 3]] + snare_slot[[2, 3, 0, 1]]) - 1) % 4)
    # 백비트 쌍 (k, k+2) 중 합이 큰 쪽의 k 가 2박이면 1박은 k-1. 쌍 (1,3)/(0,2) 를 구분하려면
    # 화성·경계 근거가 필요하다 — 그래서 스네어는 "1박 후보 두 개" 만 좁힌다.
    pair_scores = {k: snare_slot[k] + snare_slot[(k + 2) % 4] for k in range(4)}
    backbeat_k = max(range(4), key=lambda k: pair_scores[k])
    snare_candidates = sorted({(backbeat_k - 1) % 4, (backbeat_k + 1) % 4})
    chroma_phase = int(np.argmax(chroma_slot))
    boundary_phase = int(np.argmax(boundary_slot))
    votes = [chroma_phase, boundary_phase]
    # 구간 시작의 실제 저역 에너지 도약 시각이 놓인 박 위치(경계 지연과 무관한 근거)
    lowe = band_energy(np.abs(D) ** 2, freqs, (30.0, 150.0))
    lj = np.diff(np.log1p(lowe), prepend=0.0)
    jump_slot = np.zeros(4)
    for s in sections[1:]:
        t = s["start_ms"] / 1000.0
        idx = np.where((frame_t > t - 2 * period) & (frame_t < t + 2 * period))[0]
        tj = frame_t[idx[np.argmax(lj[idx])]]
        jump_slot[int(np.argmin(np.abs(beats - tj))) % 4] += 1
    jump_phase = int(np.argmax(jump_slot))
    phase = PHASE_OVERRIDE if PHASE_OVERRIDE is not None else jump_phase
    downbeat_evidence = {
        "snare_slot_counts": snare_slot.tolist(),
        "snare_backbeat_pair_start": backbeat_k,
        "snare_downbeat_candidates": snare_candidates,
        "snare_phase_naive": snare_phase,
        "chroma_novelty_by_slot": [round(v, 3) for v in chroma_slot.tolist()],
        "chroma_phase": chroma_phase,
        "boundary_slot_counts": boundary_slot.tolist(),
        "boundary_phase": boundary_phase,
        "lowjump_slot_counts": jump_slot.tolist(),
        "lowjump_phase": jump_phase,
        "chosen_phase": phase,
        "agree_chroma_boundary": chroma_phase == boundary_phase,
        "chosen_in_snare_candidates": phase in snare_candidates,
        "votes": votes,
    }

    def grid_slots(ts, start, end):
        """마디 안 16분 격자(1.1~4.4) 중 후보가 ±1/8박 안에 놓인 칸."""
        step = (end - start) / 16
        out = []
        for t in ts:
            if start - step / 2 <= t < end - step / 2:
                q = int(round((t - start) / step))
                if abs((t - start) / step - q) <= 0.5 and q < 16:
                    out.append(f"{q // 4 + 1}.{q % 4 + 1}")
        return sorted(set(out), key=lambda x: (int(x[0]), int(x[2])))

    # ---- 마디 만들기
    downbeat_idx = [i for i in range(len(beats)) if (i - phase) % 4 == 0]
    bars = []
    for n, bi in enumerate(downbeat_idx):
        start = float(beats[bi])
        end = float(beats[bi + 4]) if bi + 4 < len(beats) else start + 4 * period
        f0, f1 = frame_at(start), frame_at(end)
        last_beat_start = start + 3 * (end - start) / 4
        bars.append(
            {
                "bar": n + 1,
                "start_s": round(start, 3),
                "end_s": round(end, 3),
                "kicks": [round(t, 3) for t in kick_t if start <= t < end],
                "snares": [round(t, 3) for t in snare_t if start <= t < end],
                "kick_grid": grid_slots(kick_t, start, end),
                "snare_grid": grid_slots(snare_t, start, end),
                "perc_onsets": int(sum(1 for t in perc_onsets if start <= t < end)),
                "perc_onsets_last_beat": int(
                    sum(1 for t in perc_onsets if last_beat_start <= t < end)
                ),
                "rms": float(rms[f0:f1].mean()) if f1 > f0 else 0.0,
                "kick_energy": float(kick_e[f0:f1].mean()) if f1 > f0 else 0.0,
                "vocal_ratio": float((vocal_e[f0:f1] / harm_all[f0:f1]).mean()) if f1 > f0 else 0.0,
            }
        )
    pickup = [round(float(t), 3) for t in beats[: downbeat_idx[0]]]

    # 구간 이름
    for b in bars:
        mid = (b["start_s"] + b["end_s"]) / 2 * 1000
        sec = next((s for s in sections if s["start_ms"] <= mid < s["end_ms"]), sections[-1])
        b["section"] = sec["name"]
        b["section_i"] = sec["i"]
        b["section_first_bar"] = False
    seen = set()
    for b in bars:
        if b["section_i"] not in seen:
            seen.add(b["section_i"])
            b["section_first_bar"] = True

    # ---- 순간 추정 (모두 [추정])
    rms_arr = np.array([b["rms"] for b in bars])
    kick_arr = np.array([b["kick_energy"] for b in bars])
    kick_ref = float(np.percentile(kick_arr, 75))
    last_med = float(np.median([b["perc_onsets_last_beat"] for b in bars]))
    voc_raw = np.array([b["vocal_ratio"] for b in bars])
    voc = np.convolve(voc_raw, np.ones(4) / 4, mode="same")
    voc_thr = float(np.percentile(voc, 50))
    for k, b in enumerate(bars):
        b["kick_present"] = b["kick_energy"] >= 0.35 * kick_ref
        b["fill"] = b["perc_onsets_last_beat"] >= max(3, 2 * last_med)
        prev = bars[k - 1] if k else None
        b["drop_entry"] = bool(
            prev is not None
            and b["kick_present"]
            and not prev["kick_present"]
            and b["rms"] >= 1.15 * prev["rms"]
        )
        b["vocal_ratio_smoothed"] = float(voc[k])
        b["vocal_est"] = bool(voc[k] >= voc_thr)
    # 빌드업: 드롭 진입 직전 최대 8마디 중 킥이 빠져 있고 RMS 가 오르는 연속 구간
    for b in bars:
        b["buildup"] = False
    for k, b in enumerate(bars):
        if not b["drop_entry"]:
            continue
        j = k - 1
        while j >= 0 and k - j <= 8 and not bars[j]["kick_present"]:
            j -= 1
        run = list(range(j + 1, k))
        if len(run) >= 2 and rms_arr[run[-1]] > rms_arr[run[0]]:
            for r in run:
                bars[r]["buildup"] = True
    # 보컬 시작/끝: 추정값이 바뀌는 마디
    vocal_events = []
    for k in range(1, len(bars)):
        if bars[k]["vocal_est"] != bars[k - 1]["vocal_est"]:
            vocal_events.append(
                {
                    "bar": bars[k]["bar"],
                    "t": bars[k]["start_s"],
                    "event": "start" if bars[k]["vocal_est"] else "end",
                }
            )
    for b in bars:
        b["vocal_event"] = next((e["event"] for e in vocal_events if e["bar"] == b["bar"]), "")

    # ---- 경계 정렬: 앱 구간 경계와 가장 가까운 다운비트의 거리
    db_times = np.array([b["start_s"] for b in bars])
    boundary_fit = []
    for s in sections[1:]:
        t = s["start_ms"] / 1000.0
        d = db_times - t
        j = int(np.argmin(np.abs(d)))
        boundary_fit.append(
            {
                "section": s["name"],
                "boundary_s": round(t, 3),
                "nearest_downbeat_s": float(db_times[j]),
                "diff_ms": int(round(d[j] * 1000)),
                "diff_beats": round(float(d[j]) / period, 2),
            }
        )

    # ---- 확인용 wav
    listen_dir.mkdir(parents=True, exist_ok=True)
    stem = audio.stem.replace(" ", "_")
    downbeats = db_times
    other_beats = np.array([t for t in beats if not np.any(np.isclose(t, downbeats))])
    click_db = librosa.clicks(
        times=downbeats, sr=sr, click_freq=1760, click_duration=0.06, length=len(y)
    )
    click_b = librosa.clicks(
        times=other_beats, sr=sr, click_freq=880, click_duration=0.04, length=len(y)
    )
    mix = 0.6 * y / (np.max(np.abs(y)) + 1e-9) + 0.5 * click_db + 0.35 * click_b
    beat_wav = listen_dir / f"{stem}_beats_clicks_phase{phase}.wav"
    sf.write(str(beat_wav), (mix / max(1.0, np.max(np.abs(mix)))).astype(np.float32), sr)
    click_k = librosa.clicks(
        times=kick_t, sr=sr, click_freq=440, click_duration=0.05, length=len(y)
    )
    click_s = librosa.clicks(
        times=snare_t, sr=sr, click_freq=3000, click_duration=0.03, length=len(y)
    )
    mix2 = 0.6 * y / (np.max(np.abs(y)) + 1e-9) + 0.45 * click_k + 0.3 * click_s
    ks_wav = listen_dir / f"{stem}_kick_snare_clicks.wav"
    sf.write(str(ks_wav), (mix2 / max(1.0, np.max(np.abs(mix2)))).astype(np.float32), sr)

    result = {
        "audio": str(audio),
        "sample_rate": sr,
        "duration_s": round(duration, 3),
        "app_path_bpm": bpm,
        "app_path_confidence": conf,
        "n_beats": int(len(beats)),
        "beats_s": [round(float(t), 3) for t in beats],
        "pickup_beats_s": pickup,
        "downbeat": downbeat_evidence,
        "n_bars": len(bars),
        "n_kick_candidates": int(len(kick_t)),
        "n_snare_candidates": int(len(snare_t)),
        "kick_on_beat_ratio": float(
            np.mean([abs(nearest_beat_pos(t, beats)[1]) < 0.15 for t in kick_t])
        ),
        "snare_on_beat_ratio": float(
            np.mean([abs(nearest_beat_pos(t, beats)[1]) < 0.15 for t in snare_t])
        ),
        "boundary_fit": boundary_fit,
        "vocal_events": vocal_events,
        "bars": bars,
        "listen": {"beats": str(beat_wav), "kick_snare": str(ks_wav)},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{audio.stem.replace(' ', '_').lower()}_map_phase{phase}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1)
    )
    return result


def bpm_doubt(sample_dir: Path, out_dir: Path, songs: list[str]) -> list[dict]:
    """곡마다 앱 경로 BPM + 절반·두 배 의심 근거.

    근거(모두 재는 값, 해석은 [추정]):
      - tempogram 자기상관에서 BPM, BPM/2, BPM*2 위치의 세기 비율
      - 타악 온셋 수 / 박 수 (박당 타악 사건이 많으면 BPM 이 실제보다 낮게 잡혔을 가능성)
      - 킥 후보 간격 중앙값을 BPM 으로 환산한 값
      - beat_track 에 start_bpm 을 두 배·절반으로 줘서 다시 잰 값(사전 확률에 끌리는지)
    """
    rows = []
    for name in songs:
        y, sr = load_like_app(sample_dir / name)
        beats, bpm, conf = app_beats(y, sr)
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
        ac = librosa.autocorrelate(oenv, max_size=int(4 * sr / HOP * 2))
        ac = ac / (ac[0] + 1e-9)

        def ac_at(b: float, ac=ac, sr=sr) -> float:
            lag = 60.0 / b * sr / HOP
            lo, hi = int(lag * 0.97), int(lag * 1.03) + 1
            if hi >= len(ac):
                return float("nan")
            return float(ac[lo:hi].max())

        _, P = librosa.decompose.hpss(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
        Sp = np.abs(P) ** 2
        freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
        perc_on = librosa.onset.onset_detect(
            onset_envelope=onset_env_from(Sp.sum(axis=0)), sr=sr, hop_length=HOP, units="time"
        )
        kick_t = pick_onsets(onset_env_from(band_energy(Sp, freqs, KICK_BAND)), sr, 0.25)
        kick_iv = np.diff(kick_t)
        kick_iv = kick_iv[(kick_iv > 0.2) & (kick_iv < 2.0)]
        kick_bpm = 60.0 / float(np.median(kick_iv)) if kick_iv.size else float("nan")
        alt = {}
        for label, start in (("x2", bpm * 2), ("half", bpm / 2)):
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, start_bpm=start)
            alt[label] = float(np.atleast_1d(tempo)[0])
        rows.append(
            {
                "song": name,
                "app_bpm": round(bpm, 2),
                "confidence": round(conf, 3),
                "ac_bpm": round(ac_at(bpm), 3),
                "ac_half": round(ac_at(bpm / 2), 3),
                "ac_double": round(ac_at(bpm * 2), 3),
                "perc_onsets_per_beat": round(len(perc_on) / max(1, len(beats)), 2),
                "kick_interval_bpm": round(kick_bpm, 2),
                "retrack_start_x2": round(alt["x2"], 2),
                "retrack_start_half": round(alt["half"], 2),
            }
        )
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bpm_doubt.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return rows


def app_sections(path: Path) -> list[dict]:
    """t509 app_sections.py 출력(앱 분석 경로의 구간 경계·이름)."""
    return [
        {"i": x["i"], "name": x["name"], "start_ms": x["start_ms"], "end_ms": x["end_ms"]}
        for x in json.loads(path.read_text())["sections"]
    ]


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode in ("map", "map-phase"):
        if mode == "map-phase":
            PHASE_OVERRIDE = int(sys.argv[5])
        secs = app_sections(Path(sys.argv[6]))
        r = map_song(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), secs)
        print(
            json.dumps(
                {k: v for k, v in r.items() if k not in ("bars", "beats_s")},
                ensure_ascii=False,
                indent=1,
            )
        )
    elif mode == "bpm8":
        songs = [
            "Rain.mp3",
            "Club Diver.mp3",
            "Cut and Run.mp3",
            "Ice cream.mp3",
            "Morning.mp3",
            "Too Cool.mp3",
            "scott-buckley-neon.mp3",
            "걸그룹DinoDino_C_max최고품질.wav",
        ]
        bpm_doubt(Path(sys.argv[2]), Path(sys.argv[3]), songs)


def listen_double_check(audio: Path, listen_dir: Path) -> Path:
    """앱 BPM 박(높은 클릭)과 박 사이 중간점(낮은 클릭)을 덧입힌 wav.

    듣는 사람이 「발이 높은 클릭에만 맞는가, 낮은 클릭까지 다 맞는가」로
    BPM 이 맞는지·두 배인지를 판단하게 한다.
    """
    y, sr = load_like_app(audio)
    beats, _, _ = app_beats(y, sr)
    mids = (beats[:-1] + beats[1:]) / 2
    hi = librosa.clicks(times=beats, sr=sr, click_freq=1760, click_duration=0.05, length=len(y))
    lo = librosa.clicks(times=mids, sr=sr, click_freq=660, click_duration=0.04, length=len(y))
    mix = 0.6 * y / (np.max(np.abs(y)) + 1e-9) + 0.45 * hi + 0.3 * lo
    listen_dir.mkdir(parents=True, exist_ok=True)
    out = listen_dir / f"{audio.stem.replace(' ', '_')}_appbpm_hi_midpoint_lo.wav"
    sf.write(str(out), (mix / max(1.0, np.max(np.abs(mix)))).astype(np.float32), sr)
    return out


if __name__ == "__main__" and sys.argv[1] == "listen-double":
    print(listen_double_check(Path(sys.argv[2]), Path(sys.argv[3])))
