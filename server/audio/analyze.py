"""오디오 바이트 → BPM · 구간 경계 · 온셋 · RMS · D 등급 후보 (REQ-MUSICSYNC-008).

순수 함수 하나가 이 모듈의 전부다. 파일 시스템·네트워크·콘솔 어느 것도 만지지
않으며(REQ-MUSICSYNC-008 · REQ-MUSICSYNC-010), 실패는 예외가 아니라 **사유를 담은
실패 결과**로 돌아온다(REQ-MUSICSYNC-012). 부분 결과를 성공 형상으로 위장하지
않는다 — :class:`AnalysisResult` 와 :class:`AnalysisFailure` 는 서로 다른 타입이라
호출자가 ``isinstance`` 하나로 가른다.

**librosa 는 함수 안에서 import 한다.** 기동 시간 대책이다(plan.md §E M2) —
크기 대책이 아니다. 번들에서 빼는 것은 import 위치가 아니라 PyInstaller 훅이
정한다. 그리고 librosa 가 아예 없는 배포본(폴백, plan.md §C 결정 1)에서도 이
모듈은 **import 가능해야** 한다. 그래서 최상위에는 표준 라이브러리만 온다.
"""

from __future__ import annotations

import importlib.util
import io
import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "AnalysisFailure",
    "AnalysisResult",
    "DCandidate",
    "MANUAL_BPM_FALLBACK_REASON",
    "analysis_available",
    "analyze",
]

#: 분석 프레임 간격. 22.05kHz 에서 512 샘플 ≈ 23.2ms 로, 구간 경계 판정 폭
#: (±1000ms)보다 40배 촘촘하다 — 경계 오차의 원인이 눈금이 되지 않게 하는 값이다.
_HOP_LENGTH = 512
_FRAME_LENGTH = 2048

#: 구간 경계 판정의 두 상수.
#:
#: ``_STEP_WINDOW_SECONDS`` 는 「앞 1초 평균과 뒤 1초 평균의 차」를 재는 창이고,
#: ``_MIN_SEGMENT_SECONDS`` 는 두 경계가 얼마나 붙을 수 있는지의 **BPM 을 모를 때의**
#: 하한이다. 3초보다 짧은 「구간」은 구간이 아니라 악센트이며, 악센트는 ``onsets_ms``
#: 가 나른다.
#:
#: 🔴 **초는 음악의 단위가 아니다** (t411). 이 값 하나만 쓰던 동안, 139.7 BPM 곡에서
#: 3000ms 는 **1.75마디** — 마디보다 짧은 하한이었다. 그러면 드럼 패턴의 2마디 프레이즈
#: 경계가 거의 다 통과해 결과가 구간 목록이 아니라 박자 격자가 된다. 실측
#: (`src/Club Diver.mp3`, 141초, BPM 139.7 확신 0.97): **구간 39개, 길이 중앙 2.0마디,
#: 4마디 미만 38/38.** BPM 을 알면 :data:`_MIN_SEGMENT_BARS` 가 하한을 정한다.
_STEP_WINDOW_SECONDS = 1.0
_MIN_SEGMENT_SECONDS = 3.0

#: 구간 하한의 **음악 단위**. 4/4 마디 수다.
#:
#: 4 는 고른 값이 아니라 실측 분포의 하한이다 —
#: ``docs/proposals/song-structure-lighting-standard.md`` §4 (Harmonix 912곡 9,214구간을
#: BPM 으로 마디 환산): **25% 하한이 라벨마다 4.0마디**다(intro·pre-chorus·post-chorus·
#: instrumental·break·transition·outro 가 4.0, verse·chorus·bridge·solo 는 7.8~8.0 에서
#: 시작). 4마디 미만 구간은 912곡에서 사실상 나타나지 않는다.
#:
#: 🔴 **8마디로 올리지 마라.** 같은 문서 §5 가 [HARD] 로 *"8마디를 기본값으로 쓰되 하드
#: 제약으로 걸지 마라 — 절반 이상이 8의 배수가 아니다"* 라고 못박았다. 8마디는 분포의
#: **최빈값**(42.6%)이고 4마디는 분포의 **하한**이다. 하한으로 걸어야 하는 것은 후자이며,
#: 8을 하한으로 걸면 실측된 4마디 구간(12.3%)을 지운다.
_MIN_SEGMENT_BARS = 4.0

#: 하한이 곡을 통째로 삼키는 것을 막는 나눗수. 20 BPM(계약 §6.1 하한)이면 한 마디가
#: 12초이고 4마디는 48초라, 그대로 걸면 3분 곡이 4구간이 된다. 기준 문서 §4 의 구간 수
#: 중앙값이 **10개**이므로 최소 6구간은 가능해야 한다는 것을 상한으로 쓴다 — 10 보다
#: 보수적인 값이다.
_MIN_SEGMENTS_PER_TRACK = 6.0

#: 계단으로 인정할 최소 로그 진폭 변화. ``0.25`` 는 약 28% 의 레벨 변화다.
#: 이보다 작은 흔들림을 경계로 읽으면 한 곡이 수십 구간으로 잘린다.
_MIN_LOG_STEP = 0.25

#: **국소 봉우리들의 중앙값** 대비 이 비율을 넘는 봉우리만 경계가 된다. 절대
#: 문턱(``_MIN_LOG_STEP``)과 **둘 다** 넘어야 한다 — 절대값만 쓰면 조용한 곡에서
#: 경계가 사라지고, 상대값만 쓰면 계단이 없는 곡에서도 최대 봉우리 하나가
#: 무조건 경계가 된다.
#:
#: 중앙값을 쓰는 이유(t371): 최댓값 하나를 기준으로 삼으면, 곡 안에 유독 큰
#: 계단이 하나(예: 무음에 가까운 브레이크다운 → 드롭) 있을 때 그 계단이
#: 기준을 밀어올려 그보다 작은 **진짜** 경계들을 통째로 지운다 — 실측(t371):
#: 5구간 합성곡에서 4번째 계단(진폭 0.06→1.00)이 2번째 계단(0.35→0.85, 로그
#: 진폭차 0.85)을 눌러 지웠다(최댓값 기준 문턱 1.13 > 0.85). 중앙값은 국소
#: 봉우리 **하나**의 크기에 흔들리지 않는다 — 실측으로 확인(합성 대조군 6종 +
#: 순수 배열 스트레스 테스트 2종, `reports/t371/`).
_RELATIVE_PEAK_RATIO = 0.4

#: D 등급 띠 — 구간 RMS 를 **가장 큰 구간의 RMS** 로 나눈 비의 상한이다.
#: 절대 음압이 아니라 곡 안에서의 상대 세기를 등급으로 삼는 이유는, 마스터링
#: 레벨이 다른 두 곡이 같은 연출을 요구할 수 있기 때문이다.
_D_LEVEL_BANDS = ((0.20, 1), (0.40, 2), (0.60, 3), (0.80, 4))
_D_LEVEL_TOP = 5

#: 곡 자체의 최소~최대 폭으로 다시 늘릴지 판단하는 문턱(t375). 위 띠는 "가장
#: 큰 구간"을 100%로 놓고 재는데, 마스터링 압축이 심한 실제 곡은 구간 RMS 가
#: 전부 그 근처(예: 0.65~1.00)에 몰려 하위 띠가 구조적으로 닿지 못한다 —
#: 실측(reports/t375/): 17구간 실제 곡에서 12개가 D5 로 뭉쳤다. 그럴 때만
#: 기준점을 "가장 큰 구간 하나"에서 "이 곡에서 관측된 폭(최소~최대)"으로
#: 옮긴다. 두 조건을 **함께** 요구한다 — 조용한 구간이 상대적으로는 커도
#: (비율 조건 통과) 그 차이가 잡음 수준이면(로그 폭이 작으면) 늘리는 순간
#: 잡음을 등급 차이로 둔갑시킨다:
#:
#: (1) 가장 조용한 구간조차 가장 큰 구간의 이 비율 이상이다 — 절대 폭 상위
#:     두 칸(D4/D5 문턱 0.60)에 이미 몰려 있다는 신호. `_D_LEVEL_BANDS` 의
#:     D4 문턱과 같은 값을 쓴다.
#: (2) 가장 크고 작은 구간의 로그 차가 `_MIN_LOG_STEP` 이상이다 — 그 몰림이
#:     진짜 세기 차라는 확인(경계 판정에 이미 쓰는 것과 같은 기준을 그대로
#:     재사용해, "이 정도는 넘어야 진짜 계단"이라는 상수를 두 곳에서 따로
#:     매기지 않는다).
_D_LEVEL_RESCALE_QUIET_RATIO_FLOOR = 0.60

#: 기본 기준점으로 매긴 등급이 **한 띠에** 이 비율 이상 몰리면 등급이 판별을 못 하고
#: 있는 것으로 본다 (t412).
#:
#: 실측 (`src/Club Diver.mp3` 13구간): 12/13 = 0.92 가 D5 였다. 그 결과
#: `_infer_confirmed_role` 의 「최고 레벨이면 chorus」 규칙이 가운데 구간 전부를
#: chorus 로 만들고 팔레트·효과·질감 세 표가 같은 항목을 골랐다 — 구간을 정리해도
#: 무대는 「전부 똑같다」.
#:
#: 만장일치(1.0)를 요구하지 않는 이유: 실제 사례가 12/13 이었다. 곡 하나가 outro
#: 하나만 다른 등급을 받아도 나머지 열둘이 뭉개진 것은 그대로다. 기준 문서 §4 의
#: 실측(트랙 중앙 구간 10개에 고유 라벨 6~7개)에 비추면 0.7 은 관대한 쪽이다.
_D_LEVEL_DEGENERATE_SHARE = 0.70

#: 곡 전체 다이내믹 폭의 잡음 바닥, 로그 비. 이보다 좁으면 「없는 다이내믹」이다.
#:
#: 🔴 **`_MIN_LOG_STEP` 을 재사용하지 않는다** (t412). 그 상수는 「**프레임 사이**
#: 계단으로 인정할 최소 변화」이고 이것은 「**곡 전체**에 걸친 폭」이다 — 단위가 다른
#: 두 양에 같은 문턱을 쓰면 한쪽이 조용히 틀린다. 한 순간의 23% 도약은 잡음일 수
#: 있지만 곡 전체에 걸친 23% 폭은 구조다. 실측: `src/Club Diver.mp3` 의 robust 폭
#: 0.208 이 `_MIN_LOG_STEP`(0.25)에 막혀 재조정이 안 됐다.
#:
#: 값의 근거는 **실측한 잡음 바닥**이다. 이득을 전부 같게 준 합성 트랙(진짜 다이내믹 0)
#: 에서 구간 평균의 로그 폭은 구간 4·6·10개에서 각각 0.0015 / 0.0016 / 0.0017 이었다
#: (대조: 이득 0.2/0.5/0.9/0.35 → 1.5009). 0.02 는 그 하한의 약 12배다.
#:
#: 🔴 합성 클릭 트랙에서 잰 값이므로 0.0017 은 **하한**이고, 실제 음악의 잡음 바닥은
#: 더 높다. 그래서 여유를 크게 두었다 — 이 숫자를 「실제 음악의 잡음 바닥」이라고
#: 주장하지 않는다.
_D_LEVEL_RANGE_NOISE_FLOOR = 0.02

#: 재조정 판단(과 재조정 범위)에 쓸 quietest/loudest 를 고를 때, 나머지
#: 구간들과 log 로 이만큼 단절된 극단값은 "이 곡의 진짜 최저/최고"가 아니라
#: 별도로 떨어진 이상값으로 보고 건너뛴다(t400). t371 이 최댓값 하나 대신
#: 국소 봉우리의 중앙값을 쓴 것과 같은 발상 — 값 하나의 극단성에 전체 판단이
#: 끌려가지 않게 한다. `_MIN_LOG_STEP`(0.25, "이 정도는 넘어야 진짜 계단")의
#: 두 배를 쓴다: 인접한 두 구간의 로그 차가 진짜 계단 하나로도 설명이 안 될
#: 만큼 커야("계단 두 개 몫") 그 값을 통째로 건너뛴다는 뜻이다.
_OUTLIER_GAP_LOG_STEP = 2 * _MIN_LOG_STEP

#: 위 이상값-건너뛰기를 적용할 최소 표본 수. 표본이 이보다 적으면 어떤 값이
#: "이상값"이고 어떤 값이 "진짜 넓은 다이내믹"인지 구별할 근거가 없다 —
#: 합성 픽스처(4~6구간)의 회귀 시험들이 전부 이 대역에 있어, 이 문턱 아래는
#: 원래의 min/max 를 그대로 쓴다(no-op).
_OUTLIER_TRIM_MIN_SECTIONS = 10

#: 표본 하나당 최대 몇 개까지 이상값으로 건너뛸지 — 표본의 10%를 넘는
#: 개수를 한쪽에서 건너뛰면 "몇 개의 극단값 제외"가 아니라 "분포 자체를
#: 재정의"하는 셈이 된다.
_OUTLIER_TRIM_MAX_FRACTION = 0.10

#: 디코드된 샘플 수가 헤더가 선언한 프레임 수의 이 비율보다 적으면 조용한 잘림으로
#: 본다(t416). mp3 는 인코더 패딩 때문에 선언과 디코드가 몇 프레임 어긋날 수 있어
#: 1.0 이 아니다. 실측한 잘림은 0.15~0.19(합성 변형)였다. 실제 곡 Let's Dance.mp3 의
#: 0.647 은 잘림이 아니라 선언 쪽이 부푼 것이었다(t440) — :func:`_mp3_length_is_a_bitrate_guess`.
_MIN_DECODED_FRACTION = 0.98

#: MPEG Layer III 비트레이트 표(kbps) — MPEG1 과 MPEG2/2.5. 인덱스 0(free)·15(금지)는 0.
_MP3_BITRATES_V1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
_MP3_BITRATES_V2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
#: 버전 비트(3=MPEG1, 2=MPEG2, 0=MPEG2.5)별 표본율 표. 규격대로 MPEG2 는 MPEG1 의 절반,
#: MPEG2.5 는 4분의 1 이다 — 나눗셈으로 적어 두면 콘솔 포트와 같은 정수 리터럴(8000)이
#: 이 층에 생기지 않는다(``test_audio_boundary.py`` 의 포트 리터럴 0건 고정).
_MP3_MPEG1_SAMPLE_RATES = (44100, 48000, 32000)
_MP3_SAMPLE_RATES = {
    3: _MP3_MPEG1_SAMPLE_RATES,
    2: tuple(rate // 2 for rate in _MP3_MPEG1_SAMPLE_RATES),
    0: tuple(rate // 4 for rate in _MP3_MPEG1_SAMPLE_RATES),
}
#: 첫 프레임을 찾으려고 ID3 태그 뒤를 훑는 최대 바이트 수.
_MP3_SYNC_SEARCH_BYTES = 65536

#: 폴백(librosa 없는 배포본)에서 돌려주는 사유. 확인 카드는 이 사유를 읽고
#: **수동 BPM 입력 카드**로 갈아탄다 — 카드 경로 자체는 살아 있다
#: (plan.md §C 결정 1 · AC-MUSICSYNC-017).
MANUAL_BPM_FALLBACK_REASON = (
    "이 배포본에는 오디오 분석기가 포함되어 있지 않습니다 — BPM 을 직접 입력해 주세요."
)


@dataclass(frozen=True)
class DCandidate:
    """구간 하나에 대한 D 등급 **후보**.

    후보다. 확정이 아니다 — 사람이 확인 카드에서 끄거나 고칠 수 있어야 한다
    (REQ-MUSICSYNC-015).
    """

    start_ms: int
    end_ms: int
    d_level: int


@dataclass(frozen=True)
class AnalysisResult:
    """측정에 성공한 결과. 여섯 축을 모두 채운다(REQ-MUSICSYNC-008)."""

    bpm: float
    bpm_confidence: float
    boundaries_ms: tuple[int, ...]
    onsets_ms: tuple[int, ...]
    rms_curve: tuple[float, ...]
    d_candidates: tuple[DCandidate, ...]


@dataclass(frozen=True)
class AnalysisFailure:
    """측정하지 못했다 — 그리고 **왜 못 했는지**를 들고 온다.

    ``bpm`` 같은 필드를 일부러 갖지 않는다. 가지면 호출자가 실패 결과에서 숫자를
    읽어 갈 수 있고, 그 숫자는 지어낸 숫자다(표준 §3.6 규칙 4).
    """

    reason: str


def analysis_available() -> bool:
    """이 배포본에 분석기가 들어 있는가 — import 하지 않고 존재만 본다.

    폴백 분기(plan.md §C 결정 1)의 판정 지점이다. ``import librosa`` 로 확인하면
    있는 경우에 수 초를 태우므로, 사양만 조회한다.
    """
    for module_name in ("librosa", "numpy", "soundfile"):
        try:
            if importlib.util.find_spec(module_name) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def _mp3_frame(payload: bytes, at: int) -> tuple[int, int] | None:
    """``at`` 에 MPEG Layer III 프레임 헤더가 있으면 (프레임 바이트 수, kbps), 아니면 None."""
    if at + 4 > len(payload) or payload[at] != 0xFF or (payload[at + 1] & 0xE0) != 0xE0:
        return None
    version = (payload[at + 1] >> 3) & 3
    if version == 1 or ((payload[at + 1] >> 1) & 3) != 1:  # 예약 버전, Layer III 아님
        return None
    bitrate_index, rate_index = payload[at + 2] >> 4, (payload[at + 2] >> 2) & 3
    table = _MP3_BITRATES_V1 if version == 3 else _MP3_BITRATES_V2
    if not table[bitrate_index] or rate_index == 3:
        return None
    kbps = table[bitrate_index]
    per_kbps = 144000 if version == 3 else 72000
    size = per_kbps * kbps // _MP3_SAMPLE_RATES[version][rate_index] + ((payload[at + 2] >> 1) & 1)
    return size, kbps


def _mp3_length_is_a_bitrate_guess(payload: bytes) -> bool:
    """이 mp3 의 선언 길이가 **첫 프레임 비트레이트로 어림한 값**인가 (t443).

    Xing/Info/VBRI 헤더가 없으면 판독기(libsndfile·ffprobe·afinfo)는 길이를
    ``파일 크기 ÷ 첫 프레임 비트레이트`` 로 어림한다. CBR 이면 이 어림이 맞지만,
    VBR 이면 틀린다 — Let's Dance.mp3 는 첫 프레임 128kbps·평균 약 197kbps 라
    140.5초로 부풀었고 실제 곡은 90.98초였다(t440 실측, 프레임이 파일 끝까지 연속).

    헤더가 없고 **프레임 비트레이트가 둘 이상 섞였을 때만** 참이다. 판단이 서지 않으면
    (프레임을 못 찾음, 헤더 있음, 한 비트레이트뿐) 거짓 — 절단 검사를 그대로 둔다.
    """
    start = 0
    if payload[:3] == b"ID3" and len(payload) >= 10:
        start = 10 + ((payload[6] << 21) | (payload[7] << 14) | (payload[8] << 7) | payload[9])
        if payload[5] & 0x10:  # ID3v2.4 꼬리표(footer)
            start += 10
    for at in range(start, min(len(payload), start + _MP3_SYNC_SEARCH_BYTES)):
        frame = _mp3_frame(payload, at)
        if frame and _mp3_frame(payload, at + frame[0]):  # 다음 프레임까지 이어져야 진짜 동기
            break
    else:
        return False
    if any(tag in payload[at : at + frame[0]] for tag in (b"Xing", b"Info", b"VBRI")):
        return False
    first_kbps = frame[1]
    while frame:
        if frame[1] != first_kbps:
            return True
        at += frame[0]
        frame = _mp3_frame(payload, at)
    return False


def analyze(audio_bytes: bytes) -> AnalysisResult | AnalysisFailure:
    """오디오 바이트열 하나를 재서 여섯 축을 돌려준다.

    예외를 호출자 밖으로 내보내지 않는다(REQ-MUSICSYNC-012). 어떤 바이트열이
    들어와도 :class:`AnalysisResult` 이거나 :class:`AnalysisFailure` 다.
    """
    if not isinstance(audio_bytes, bytes | bytearray | memoryview):
        return AnalysisFailure("오디오 입력이 바이트열이 아닙니다.")
    payload = bytes(audio_bytes)
    if not payload:
        return AnalysisFailure("오디오 바이트열이 비어 있습니다.")

    try:
        import librosa
        import numpy
        import soundfile
    except ImportError:
        return AnalysisFailure(MANUAL_BPM_FALLBACK_REASON)

    try:
        info = soundfile.info(io.BytesIO(payload))
        declared_frames = info.frames
        samples, sample_rate = soundfile.read(io.BytesIO(payload), dtype="float32", always_2d=True)
    except Exception as error:  # soundfile 은 형식마다 다른 예외를 낸다
        return AnalysisFailure(f"오디오 형식을 읽지 못했습니다: {error}")

    if samples.size == 0 or sample_rate <= 0:
        return AnalysisFailure("오디오에 샘플이 없습니다.")

    # t416 — 디코더가 **예외 없이** 중간에서 멈출 수 있다(합성 변형으로 재현, 읽힌
    # 비율 0.15~0.19). 부분 오디오로 잰 BPM·구간을 곡의 값으로 제안하느니 정직하게
    # 거절한다. 단 t440 실측: 이 검사를 처음 부른 실제 곡 Let's Dance.mp3 는 잘린
    # 게 아니었다 — 헤더 없는 VBR 이라 선언 140.55초가 비트레이트 어림이었고, 프레임
    # 3,791개가 파일 끝까지 이어져 곡은 실제로 90.98초다(soundfile·librosa·ffmpeg 일치).
    # 옛 서술의 「libmpg123 dequantization failed」는 그 곡에선 재현되지 않았다(합성
    # 변형에서만 찍힌다 — 91초 뒤엔 디코드할 프레임이 없다). 그래서 선언이
    # 어림인 경우(t443)는 기준에서 뺀다 — 디코더는 그대로 두고 판정만 고친다.
    length_is_a_guess = info.format == "MP3" and _mp3_length_is_a_bitrate_guess(payload)
    if (
        declared_frames > 0
        and not length_is_a_guess
        and len(samples) < declared_frames * _MIN_DECODED_FRACTION
    ):
        decoded_s = len(samples) / sample_rate
        declared_s = declared_frames / sample_rate
        return AnalysisFailure(
            f"오디오를 끝까지 읽지 못했습니다 — 파일은 {declared_s:.1f}초인데 "
            f"{decoded_s:.1f}초에서 디코더가 멈췄습니다. 곡의 일부만 분석하면 BPM 과 "
            "구간이 틀리므로 분석하지 않습니다. 파일을 WAV 등으로 다시 내보내 올려 주세요."
        )

    mono = numpy.ascontiguousarray(samples.mean(axis=1), dtype=numpy.float32)
    duration_ms = int(round(len(mono) * 1000.0 / sample_rate))
    if duration_ms < 2000:
        return AnalysisFailure(f"오디오가 너무 짧습니다({duration_ms}ms) — 최소 2000ms 필요.")

    try:
        rms = librosa.feature.rms(y=mono, frame_length=_FRAME_LENGTH, hop_length=_HOP_LENGTH)[0]
        beat_times = librosa.beat.beat_track(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )[1]
        onset_times = librosa.onset.onset_detect(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )
    except Exception as error:  # 분석기 내부 실패도 예외로 새어 나가지 않는다
        return AnalysisFailure(f"오디오를 분석하지 못했습니다: {error}")

    bpm, confidence = _tempo_from_beats(numpy, beat_times)
    if bpm is None:
        return AnalysisFailure("박을 찾지 못해 BPM 을 재지 못했습니다.")

    frame_ms = _HOP_LENGTH * 1000.0 / sample_rate
    # BPM 을 경계 판정에 넘긴다 — 구간 하한은 초가 아니라 마디다(t411). BPM 은 위에서
    # 이미 나왔으므로 새 계산이 아니라 이미 있는 값을 잇는 것이다.
    boundaries_ms = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=bpm)
    d_candidates = _grade_sections(numpy, rms, frame_ms, boundaries_ms, duration_ms)

    return AnalysisResult(
        bpm=bpm,
        bpm_confidence=confidence,
        boundaries_ms=boundaries_ms,
        onsets_ms=tuple(int(round(t * 1000.0)) for t in onset_times),
        rms_curve=tuple(float(value) for value in rms),
        d_candidates=d_candidates,
    )


def _tempo_from_beats(numpy, beat_times) -> tuple[float | None, float]:
    """박 시각들에서 BPM 과 확신을 뽑는다.

    ``beat_track`` 이 돌려주는 템포 추정치 대신 **박 간격의 중앙값**을 쓴다. 추정치는
    한 곡에 하나뿐이라 흔들림을 감출 수 있지만, 간격 분포는 흔들림을 그대로
    보여 준다 — 그리고 그 흔들림이 곧 ``bpm_confidence`` 다.
    """
    if len(beat_times) < 4:
        return None, 0.0
    intervals = numpy.diff(numpy.asarray(beat_times, dtype=float))
    intervals = intervals[intervals > 0]
    if intervals.size < 3:
        return None, 0.0
    median = float(numpy.median(intervals))
    if median <= 0:
        return None, 0.0
    spread = float(numpy.std(intervals)) / median
    confidence = max(0.0, min(1.0, 1.0 - spread))
    return 60.0 / median, confidence


def _min_segment_ms(*, bpm: float | None, duration_ms: int) -> float:
    """두 경계가 붙을 수 있는 하한, 밀리초.

    BPM 을 알면 :data:`_MIN_SEGMENT_BARS` 마디, 모르면 :data:`_MIN_SEGMENT_SECONDS` 초다.
    **BPM 을 모를 때 120 을 가정하지 않는다** — 기준 문서와 계약(`LD-TIME-002`)이 같은
    것을 요구하고, 이 저장소의 ``server/design/profile.py`` 도 같은 이유로 FX-Rate 역산을
    채택 후보에서 뺐다. 추측한 tempo 로 구간을 자르면 그 오차가 곧 조명 시각의 오차다.

    두 경계를 함께 지킨다:

    * **아래로는** 옛 초 하한 밑으로 내려가지 않는다. 이 단조성이 실용적으로 중요하다 —
      하한이 오르기만 하면 「경계가 거절되기를 기대하는」 기존 시험은 새로 깨질 수 없다.
    * **위로는** 곡 길이의 ``1/_MIN_SEGMENTS_PER_TRACK`` 을 넘지 않는다. 아주 느린 곡에서
      4마디가 곡의 절반이 되는 것을 막는다.

    Args:
        bpm: 측정된 BPM. ``None``·0·음수·비유한 값은 모두 「모른다」로 다룬다 —
            ``float("nan")`` 은 비교가 전부 거짓이라 조용히 통과할 수 있어 명시로 막는다.
        duration_ms: 곡 전체 길이. 상한 계산에 쓴다.
    """
    seconds_floor = _MIN_SEGMENT_SECONDS * 1000.0
    if bpm is None or not math.isfinite(bpm) or bpm <= 0:
        return seconds_floor

    bar_ms = 4.0 * 60_000.0 / bpm
    bars_floor = _MIN_SEGMENT_BARS * bar_ms
    capped = min(bars_floor, duration_ms / _MIN_SEGMENTS_PER_TRACK)
    return max(seconds_floor, capped)


def _boundaries_from_rms(
    numpy, rms, frame_ms: float, duration_ms: int, *, bpm: float | None
) -> tuple[int, ...]:
    """에너지 계단이 있는 자리를 구간 경계로 읽는다.

    앞뒤 1초 평균의 차(novelty)를 재고, **절대 문턱과 상대 문턱을 둘 다** 넘는
    봉우리만 경계로 받는다. 곡의 시작(0ms)은 언제나 경계다 — 첫 구간이 어디서
    시작하는지는 측정 대상이 아니다.

    ⚠️ 한계를 숨기지 않는다: 이것은 **에너지 기반** 분절기다. 음색이나 화성만
    바뀌고 세기가 그대로인 전환은 잡지 못한다. 합성 픽스처는 세기 계단으로
    경계를 만들므로 이 한계가 픽스처에서는 드러나지 않는다(design.md §6 W10).
    """
    window = max(1, int(round(_STEP_WINDOW_SECONDS * 1000.0 / frame_ms)))
    log_rms = numpy.log(numpy.asarray(rms, dtype=float) + 1e-8)
    if log_rms.size <= 2 * window:
        return (0,)

    cumulative = numpy.concatenate(([0.0], numpy.cumsum(log_rms)))

    def window_mean(start: int, stop: int) -> float:
        return float((cumulative[stop] - cumulative[start]) / (stop - start))

    novelty = numpy.zeros(log_rms.size, dtype=float)
    for index in range(window, log_rms.size - window):
        before = window_mean(index - window, index)
        after = window_mean(index, index + window)
        novelty[index] = abs(after - before)

    # 문턱을 적용하기 **전에** 먼저 국소 봉우리들만 모은다 — 이 목록의 중앙값이
    # "이 곡에서 흔한 계단 크기"이고, 그것이 상대 문턱의 기준이다. 단 하나의
    # 최댓값이 아니라 이 집합의 중앙값을 쓰면, 유독 큰 계단 하나가 나머지
    # 진짜 경계들의 문턱을 밀어올리는 일이 없다(위 상수 설명 참조).
    local_maxima = [
        novelty[index]
        for index in range(window, log_rms.size - window)
        if novelty[index] == novelty[max(0, index - window) : index + window + 1].max()
    ]
    typical_peak = float(numpy.median(local_maxima)) if local_maxima else 0.0
    peak_floor = max(_MIN_LOG_STEP, _RELATIVE_PEAK_RATIO * typical_peak)
    candidates = [
        index
        for index in range(window, log_rms.size - window)
        if novelty[index] >= peak_floor
        and novelty[index] == novelty[max(0, index - window) : index + window + 1].max()
    ]

    min_segment_ms = _min_segment_ms(bpm=bpm, duration_ms=duration_ms)

    # 곡의 양 끝에서 하한 미만의 조각을 만드는 후보를 **거리 필터보다 먼저** 버린다.
    #
    # 시작 쪽은 원래 막혀 있었고 끝 쪽은 t375 에서 막았다(178.3초 곡에서 마지막
    # 경계가 177.3초에 잡혀 1.0초 구간이 나왔다). 남는 꼬리는 구간이 아니라
    # 악센트이고, 악센트는 ``onsets_ms`` 가 나른다.
    #
    # 🔴 **순서가 load-bearing 이다** (t411). 이 판정이 거리 필터 *뒤*에 있던 동안,
    # 나중에 버려질 후보가 먼저 뽑혀 이웃을 억눌렀다 — 정본 픽스처 실측: 계단
    # 32000ms 와 36000ms 중 36000 쪽의 로그 계단이 더 커서 먼저 뽑히고, 32000 을
    # 거리로 죽인 뒤, 자기도 꼬리 판정에서 버려져 **둘 다 사라졌다**. 하한이 3초일
    # 때는 4초 간격이 거리를 통과해 드러나지 않던 결함이다.
    def _leaves_a_full_segment(index: int) -> bool:
        millis = index * frame_ms
        return (
            millis >= min_segment_ms
            and millis < duration_ms
            and duration_ms - millis >= min_segment_ms
        )

    eligible = [index for index in candidates if _leaves_a_full_segment(index)]

    min_distance = min_segment_ms / frame_ms
    accepted: list[int] = []
    for index in sorted(eligible, key=lambda i: (-novelty[i], i)):
        if all(abs(index - taken) >= min_distance for taken in accepted):
            accepted.append(index)

    boundaries = [0]
    boundaries.extend(int(round(index * frame_ms)) for index in sorted(accepted))
    return tuple(boundaries)


def _grade_sections(
    numpy, rms, frame_ms: float, boundaries_ms: tuple[int, ...], duration_ms: int
) -> tuple[DCandidate, ...]:
    """구간마다 D 등급 후보 하나 — 곡 안에서의 **상대** 세기로 매긴다.

    기본 기준점은 "가장 큰 구간의 RMS" 다. 다만 그 구간조차 곡 전체가
    압축돼 상위 띠에 몰려 있을 때는(`_should_rescale_to_song_range`)
    기준점을 "이 곡에서 관측된 최소~최대 폭"으로 옮긴다 — 절대 음압이
    아니라 상대 세기를 쓰는 설계 의도(위 `_D_LEVEL_BANDS` 주석)는 그대로
    두고, 상대 비교의 **기준점**만 곡 자체의 관측 폭으로 좁힌다. 진짜
    다이내믹이 없는 곡(전 구간이 잡음 수준 차이만 남)은 그 조건을 만족하지
    않아 그대로 남는다 — 없는 다이내믹을 지어내지 않는다.

    재조정 여부 판단과 재조정 범위는 전체 min/max 가 아니라
    `_robust_song_extremes` 가 고른, 나머지와 단절된 극단값을 건너뛴
    min/max 를 쓴다(t400) — 재조정을 **하지 않을** 때의 분모(`loudest`)는
    여전히 전체 max 그대로다: "가장 큰 구간을 100%로" 라는 기본 설계는
    구간 하나 때문에 흔들리지 않는다.
    """
    edges = [*boundaries_ms, duration_ms]
    means: list[float] = []
    spans: list[tuple[int, int]] = []
    for start_ms, end_ms in zip(edges[:-1], edges[1:], strict=True):
        start_frame = int(math.floor(start_ms / frame_ms))
        end_frame = max(start_frame + 1, int(math.ceil(end_ms / frame_ms)))
        window = numpy.asarray(rms[start_frame:end_frame], dtype=float)
        means.append(float(window.mean()) if window.size else 0.0)
        spans.append((start_ms, end_ms))

    loudest = max(means) if means else 0.0
    robust_loudest, robust_quietest = _robust_song_extremes(means)

    # 기본 기준점으로 매긴 비를 먼저 계산해 재조정 판정에 넘긴다 (t412) — 「등급이
    # 판별을 못 하고 있는가」는 그 비를 봐야 답할 수 있고, 폭만으로는 알 수 없다.
    default_ratios = [(mean / loudest) if loudest > 0 else 0.0 for mean in means]
    rescale = _should_rescale_to_song_range(robust_loudest, robust_quietest, ratios=default_ratios)

    candidates: list[DCandidate] = []
    for (start_ms, end_ms), mean in zip(spans, means, strict=True):
        if rescale:
            ratio = (mean - robust_quietest) / (robust_loudest - robust_quietest)
        else:
            ratio = (mean / loudest) if loudest > 0 else 0.0
        level = _D_LEVEL_TOP
        for upper, band_level in _D_LEVEL_BANDS:
            if ratio < upper:
                level = band_level
                break
        candidates.append(DCandidate(start_ms=start_ms, end_ms=end_ms, d_level=level))
    return tuple(candidates)


def _robust_song_extremes(means: list[float]) -> tuple[float, float]:
    """재조정 판단·범위에 쓸 (loudest, quietest) — 단절된 극단값은 건너뛴다.

    표본이 `_OUTLIER_TRIM_MIN_SECTIONS` 개 미만이면 원래의 min/max 를 그대로
    돌려준다(no-op) — 적은 표본에서는 무엇이 "이상값"이고 무엇이 "진짜 넓은
    다이내믹"인지 구별할 근거가 없다(t375 합성 회귀 픽스처가 전부 이
    대역이다). 그 이상이면, 정렬된 값에서 양 끝부터 훑어 인접한 두 값의
    로그 차가 `_OUTLIER_GAP_LOG_STEP` 을 넘는 동안만 건너뛰되, 한쪽에서
    `_OUTLIER_TRIM_MAX_FRACTION` 를 넘는 개수는 건너뛰지 않는다.
    """
    if not means:
        return 0.0, 0.0
    ordered = sorted(means)
    n = len(ordered)
    if n < _OUTLIER_TRIM_MIN_SECTIONS:
        return ordered[-1], ordered[0]

    max_trim = max(1, int(n * _OUTLIER_TRIM_MAX_FRACTION))

    low_index = 0
    while low_index + 1 < n and low_index < max_trim:
        lower, upper = ordered[low_index], ordered[low_index + 1]
        if lower <= 0 or math.log(upper / lower) < _OUTLIER_GAP_LOG_STEP:
            break
        low_index += 1

    high_index = n - 1
    while high_index - 1 >= 0 and (n - 1 - high_index) < max_trim:
        lower, upper = ordered[high_index - 1], ordered[high_index]
        if lower <= 0 or math.log(upper / lower) < _OUTLIER_GAP_LOG_STEP:
            break
        high_index -= 1

    return ordered[high_index], ordered[low_index]


def _grading_is_degenerate(ratios: Sequence[float]) -> bool:
    """기본 기준점으로 매긴 등급이 한 띠에 몰려 **판별을 못 하고** 있는가 (t412).

    이 판정이 묻는 것은 「폭이 얼마나 넓은가」가 아니라 「등급이 일을 하고 있는가」다.
    등급의 용도는 구간을 서로 다르게 다루는 것이고, 전부 같은 등급이면 그 용도가
    사라진다 — 실측: 13구간 중 12개가 D5 라 팔레트·효과·질감이 모두 같은 항목을 골랐다.

    구간이 둘 미만이면 ``False`` 다. 하나뿐인 등급이 하나인 것은 당연하며 결함이
    아니다 — 여기서 ``True`` 를 답하면 구간 하나짜리 입력마다 기준점을 옮긴다.
    """
    if len(ratios) < 2:
        return False

    counts: dict[int, int] = {}
    for ratio in ratios:
        level = _D_LEVEL_TOP
        for upper, band_level in _D_LEVEL_BANDS:
            if ratio < upper:
                level = band_level
                break
        counts[level] = counts.get(level, 0) + 1

    return max(counts.values()) / len(ratios) >= _D_LEVEL_DEGENERATE_SHARE


def _should_rescale_to_song_range(
    loudest: float, quietest: float, *, ratios: Sequence[float] | None
) -> bool:
    """등급 기준점을 곡 자체의 관측 폭으로 옮길지.

    두 갈래 중 하나면 옮긴다 — 새 갈래는 **덧붙인** 것이므로, 전에 재조정되던 곡은
    전부 그대로 재조정된다(t412).

    **갈래 A (기존)** — 두 조건을 함께 요구한다:

    (1) 가장 조용한 구간조차 이미 `_D_LEVEL_RESCALE_QUIET_RATIO_FLOOR` 를
        넘는다 — 절대 폭 상위 두 칸에 몰려 있다는 신호.
    (2) 가장 크고 작은 구간의 로그 차가 `_MIN_LOG_STEP` 이상이다 — 그 몰림이
        잡음이 아니라 진짜 세기 차라는 확인.

    **갈래 B (t412)** — 등급이 실제로 판별에 실패하고 있고, 그 좁은 폭이 잡음은
    아닐 때:

    (1) `_grading_is_degenerate` — 한 띠에 몰려 있다.
    (2) 로그 폭이 `_D_LEVEL_RANGE_NOISE_FLOOR` 이상 — 없는 다이내믹을 지어내지
        않는다.

    갈래 B 가 필요한 이유는 갈래 A 의 조건 (2)가 `_MIN_LOG_STEP` 을 빌려 쓰기
    때문이다. 그 상수는 프레임 사이 계단의 문턱이고 곡 전체 폭의 문턱이 아니다 —
    실측 곡의 폭 0.208 이 0.25 에 막혀 12/13 이 D5 로 남았다.

    Args:
        ratios: 기본 기준점(최대 구간 = 1.0)으로 계산한 구간별 비. ``None`` 이면
            갈래 B 를 평가하지 않는다 — 호출자가 아직 계산하지 않았다는 뜻이고,
            없는 값을 0 으로 가정해 판정하지 않는다.
    """
    if loudest <= 0 or quietest <= 0 or quietest >= loudest:
        return False

    spread = math.log(loudest / quietest)

    if (quietest / loudest) >= _D_LEVEL_RESCALE_QUIET_RATIO_FLOOR and spread >= _MIN_LOG_STEP:
        return True

    if ratios is not None and _grading_is_degenerate(ratios):
        return spread >= _D_LEVEL_RANGE_NOISE_FLOOR

    return False
