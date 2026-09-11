"""LX-SEQ RIG 팩 PRESET 시트 파서 (SPEC-COPILOT-LXSEQ-003 M1).

순수 함수다 — 콘솔·네트워크 입출력 0. `server/lxseq/group_parser.py`(002 M1)의
관용구를 따르되 **판별을 정확 열 집합으로** 한다(REQ-LXSEQ3-001).

세 종류의 열 집합이 서로 다르고, 넷째(`preset-pos`)까지 넣어도 쌍마다 구별된다.
그래서 포함 검사가 필요 없다 — 포함 검사로는 `col` 과 `bm` 이 안 갈린다.

`preset-pos` 의 서명도 분기도 두지 않는다(REQ-LXSEQ3-002). 그 시트는 값 열이
없고 현장 레코드 대상이라 이 경로의 물건이 아니다.

## 왜 레코드가 `storable` 을 들고 다니는가

시트 19행이 전부 콘솔에 넣을 수 있는 값은 **아니다.** 실측(정본 CSV, 값 열 전수):

    dim 6/6   100% · 85% · 60% · 30% · 15% · 0%       -> 넣을 수 있다
    col 6/8   R255 G180 B60 형태                       -> 보류(아래)
    col 2/8   ~3200K · ~5600K                          -> 보류(아래)
    bm  0/5   Zoom 45 도 · Gobo OPEN · Prism OFF 형태  -> 보류(아래)

파싱과 투입은 다른 일이므로 **19행은 전부 레코드로 읽는다.** 대신 넣을 수 없는
행을 **버리지 않고 사유와 함께 나른다.** 그냥 넣을 수 있는 것만 처리하면 나머지가
어디로 갔는지 아무도 모르고, 다음 사람이 무엇을 풀어야 하는지도 모른다.

이 필드가 없으면 「19 레코드가 나온다」는 검사가 파싱만 재고 통과한다 — 그리고
문면대로 구현하면 「19건 성공」이 적히는데 13건은 저장 단계에서 터지거나 빈
프로그래머에 대해 저장된다.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from server.looks.schema import CONFIRMED_ATTRIBUTES, PROBE_GATED_ATTRIBUTES

if TYPE_CHECKING:
    # 형 주석에만 쓴다 — 런타임에 `server.prechk` 를 끌어오지 않는다. 능력 판독은
    # 콘솔을 읽는 일이고 이 모듈은 순수 파서다. 판독값은 **주입**으로 들어오므로
    # (`classify_storability` 의 `capabilities`) 이 모듈이 판독기를 호출할 일이
    # 없고, import 를 런타임에 두면 「파서가 콘솔 계층을 안 부른다」가 문면으로만
    # 남는다.
    from server.prechk.capability_read import ModeCapabilities

#: 세 종류의 **정확** 열 집합. 정본 실측이며 여기가 유일한 선언 자리다.
#:
#: 종류 이름은 `server/sheets/registry.py` 의 행 `kind` 와 **같은 어휘**다.
#: 짧은 이름(`dim`)을 따로 쓰면 두 어휘가 생기고, 둘이 갈리는 순간 산출물의
#: `sheet_kind` 가 레지스트리가 말하는 종류와 달라진다 — 이 저장소가 포트
#: 기본값에서 이미 치른 값이다(t61). 검사가 두 목록의 동일성을 잰다.
PRESET_SHEET_COLUMNS: dict[str, tuple[str, ...]] = dict(
    [
        ("preset-dim", ("ID", "Name", "Level", "Purpose")),
        ("preset-col", ("ID", "Name", "Value", "Purpose")),
        ("preset-bm", ("ID", "Name", "TargetGroup", "Value")),
    ]
)

#: 시트 종류별 ID 접두. 어긋난 행은 거부하고 보고한다(REQ-LXSEQ3-003).
PRESET_ID_PREFIXES: dict[str, str] = dict(
    [("preset-dim", "DIM."), ("preset-col", "COL."), ("preset-bm", "BM.")]
)

#: 이 저장소가 **실기로 재서** 콘솔이 받는다고 확인한 속성.
#: `server/looks/schema.py` 가 정본이다 — 여기서 사본을 만들지 않는다.
#:
#: 이 문장은 **이 줄에만** 걸린다. 아래 `_PROBE_REJECTED`·`_OUT_OF_SCOPE` 는 사본이
#: 맞지만, 정본에 끌어올 튜플이 **없다** — `schema.py` 는 그 이름들을 독스트링
#: 문장으로만 갖고 있다(튜플 선언 0건). 게다가 `_PROBE_REJECTED` 는 어휘 자체가
#: 다르다(아래 참조). 「정본에서 import 하면 되지 않나」는 여기서 두 번 어긋난다.
_ACCEPTED_ATTRIBUTES = frozenset(CONFIRMED_ATTRIBUTES + PROBE_GATED_ATTRIBUTES)

#: 감독 시트 토큰 -> 콘솔에 **쏘는** 어트리뷰트 이름. 두 어휘의 **유일한 연결 지점**이다.
#:
#: 🔴 둘을 한 목록으로 못 합친다 — 취향이 아니라 `_attribute_tokens` 술어의 **방향**
#: 때문이다. 그 술어는 목록 항목을 시트 토큰의 **접두사**로 쓴다:
#:
#:     목록 `Prism`  · 시트 `Prism`   ->  "prism".startswith("prism")    참
#:     목록 `Prism1` · 시트 `Prism`   ->  "prism".startswith("prism1")   거짓
#:     목록 `Prism`  · 시트 `Prism1`  ->  "prism1".startswith("prism")   참
#:
#: **짧은 항목이 엄격히 더 관대한데, 콘솔이 받는 이름(값)은 시트 토큰(키)보다 길다** —
#: 정확히 반대 방향이다. 그래서 매칭은 **키로만** 걸리고 발사는 **값으로만** 된다.
#: 정본 문면에 맞춰 키를 `Prism1` 로 "고치면" 시트 토큰 `Prism` 에 안 걸려
#: **BM.03 이 storable 로 열린다** — 정합성 개선이 아니라 회귀다.
#: `test_lxseq_preset_beam_vocabulary.py` 가 그 치환을 실제로 해서 고정한다.
#:
#: ⚠️ 값은 「콘솔이 **받는** 이름」이 아니라 「콘솔에 **쏘는/쏜** 이름」이며, 넷의
#: 출처 등급이 셋과 하나로 갈린다: `Focus1`·`Frost1`·`Shutter1` 은 t135 가
#: `Patch/FixtureTypes` DMX 채널 목록에서 **읽은** 이름이고, `Prism1` 은 **쏴서
#: `Failed` 를 받은** 이름이다(그 기종에 프리즘 채널이 없다). `Shutter1` 은 읽기만
#: 했고 값을 쏜 적이 없다 — danger 정책 배제라 승인 범위 밖이었다.
#:
#: 근거: `.moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md` §A.4-2b (t146 이 정본에 실었다).
#: 그 절이 M0 거절 넷을 축으로 가른다 — `Frost`·`Focus` 는 철자, `Prism` 은 부재,
#: `Shutter` 는 그 측정의 대상이 아니었다(반증되지 않은 것과 재확인된 것은 다르다).
#:
#: 그래도 이 표를 **전수 확정으로도** 읽지 마라. `Prism1` 만 `Failed` 로 다른 오류
#: 문자열을 냈고 그 차이의 원인은 **관측되지 않았다** — 채널 부재가 그 문자열을
#: 설명하는지까지는 안 쟀다. 이것은 「이 리그에서 이 선택으로는 안 받았다」이지
#: 「문법이 무효다」가 아니다.
_SHEET_TO_CONSOLE_ATTRIBUTE: dict[str, str] = dict(
    [("Focus", "Focus1"), ("Frost", "Frost1"), ("Prism", "Prism1"), ("Shutter", "Shutter1")]
)

#: 라이브 프로브가 거절한 속성 — **시트 어휘로** 적는다. 정의역은 위 표의 키다.
#: 파생이라 손으로 두 벌을 맞출 일이 없고, 오늘 값은 이전 튜플과 **바이트 동일**하다
#: (`("Focus", "Frost", "Prism", "Shutter")` — dict 가 삽입 순서를 지킨다).
#:
#: 🔴 보류를 「값이 수용 목록에 들어갔으면 자동으로 푼다」로는 **파생시키지 않는다.**
#: `server/orchestrator/tools.py` 의 소비 루프는 값을 명령으로 못 옮기는 배정이
#: **하나라도** 있으면 만들어 둔 번들을 통째로 버린다("…한 줄도 보내지 않았다").
#: bm 에는 적용 줄이 없으므로(`LXSEQ_PRESET_APPLY_ATTRIBUTE` 는 `preset-dim` 한 칸),
#: bm 한 행이 저절로 열리는 날 **그 bm 임포트가 통째로 0건**이 된다 — 「4 보류 +
#: 1 계획」이 아니라 0건이다. 파생은 그 지뢰를 심는 것이다. 대신 어긋남을 검사가
#: 잡는다(트립와이어 — 위 테스트 파일).
#:
#: ⚠️ 여기 한동안 「프리셋 임포트 **전체**가 0건 — bm 만이 아니다」라고 적혀 있었고
#: 그것은 **틀렸다**(t141 이 넣고 t154 가 반증). 소비 루프가 종류를 안 가리는 것은
#: 맞지만 **그 계획에 다른 종류가 애초에 못 들어온다**: `parse_preset_csv` 가 헤더에서
#: 종류 하나를 정하고(`:380`·`:434`), 그 함수의 프로덕션 호출지는 `import_lxseq_presets`
#: 안의 한 곳뿐이며(`tools.py:4883`) 인자는 시트 **한 장**이다. 한 번의 임포트 =
#: 한 시트 = 한 종류다. 막을 이유는 그대로다 — 그 시트가 0건이 되는 것으로 충분하다.
_PROBE_REJECTED = tuple(_SHEET_TO_CONSOLE_ATTRIBUTE)

#: 풀 계열 자체가 범위 밖인 것. `server/looks/schema.py:55-57` —
#: "Position/All/Gobo/Control/Shapers/Video are out of scope".
_OUT_OF_SCOPE = ("Gobo", "Position", "Control", "Shapers", "Video")

#: dim 의 `Level` 이 취하는 형태. 콘솔의 `Attribute 'Dimmer' At <n>` 이 퍼센트라
#: 시트와 단위가 같다 — 세 시트 중 **해석이 0인 유일한 자리**다.
_PERCENT = re.compile(r"^\s*(\d+)\s*%\s*$")

#: 보류 사유의 **닫힌 클래스**. 산문만 두면 13건이 한 덩어리로 보이고,
#: **어느 하나를 풀면 몇 건이 열리는지** 아무도 모른다. 클래스가 있으면
#: 「스케일 변환만 해결하면 6건」이 바로 읽힌다. 원인마다 처방과 소유자가 다르다.
HOLD_NO_RGB_VALUE = "no_rgb_value"  # col — RGB 도, 정의역 안의 색온도도 없다
HOLD_PROBE_REJECTED = "attribute_probe_rejected"  # bm — 라이브 프로브가 거절했다
HOLD_FAMILY_OUT_OF_SCOPE = "family_out_of_scope"  # bm — 풀 계열이 범위 밖이다
HOLD_VALUE_NOT_MACHINE_READABLE = "value_not_machine_readable"  # 형태가 아니다
HOLD_ATTRIBUTE_UNKNOWN = "attribute_unknown"  # bm — 어느 목록에도 없는 속성 이름이다
#: bm — 도(degree)로 적힌 값이 **그 기종·모드가 답한 물리 범위** 밖이다.
#: 어휘 축(위 셋)과 다르다: 속성은 쏠 수 있는데 **그 값**을 못 쏜다.
#: 이 보류를 푸는 것은 시트 값을 범위 안으로 고치는 것, 또는 그 값을 받는 기종으로
#: 배정을 바꾸는 것 둘뿐이다 — 값을 잘라 맞추는 것은 여기서 하지 않는다.
#: 능력 판독을 주지 않으면(`capabilities=None`) 애초에 걸리지 않는다.
HOLD_VALUE_OUT_OF_RANGE = "value_out_of_range"

#: 값 문장에서 속성 이름 후보로 읽을 토큰. 숫자·단위·한글은 보지 않는다.
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")

#: col 값에 RGB 삼원색이 적혔는지. 색온도만 있는 행과 가르는 데만 쓴다.
_HAS_RGB = re.compile(r"R\s*\d")

#: col 값에서 세 성분을 **꺼내는** 술어. `_HAS_RGB` 는 "R 뒤에 숫자"만 보므로
#: `R2 뭔가` 같은 반쪽 값도 통과시킨다 — 판정에 그것만 쓰면 판정기가 통과시킨 값을
#: 판독기가 못 읽고, 그러면 임포터가 **한 줄도** 안 보내고 통째로 거절한다
#: (`_lxseq_preset_apply_command` 의 fail-closed). 그래서 판정과 판독이 **이 하나**를
#: 같이 쓴다 — `preset_label_refusal` 이 같은 이유로 술어를 밖으로 낸 것과 같다(t97).
_RGB_TRIPLE = re.compile(r"R\s*(\d+)\s*G\s*(\d+)\s*B\s*(\d+)")

#: 콘솔이 받는 성분의 상한. 시트가 8비트 표기를 쓰므로 그 바깥은 옮길 대상이 아니다.
_RGB_COMPONENT_MAX = 255

#: bm 값 한 행이 성분을 나누는 문자. 정본 시트가 실제로 쓰는 것은 U+00B7 MIDDLE DOT
#: 이다(`hexdump` 로 확인: `c2 b7`). 가운뎃점은 다섯 행 **전부**에 같은 모양으로
#: 들어 있고, 다른 구분자를 쓰는 행은 없다.
_BM_SEGMENT_SEPARATOR = "\u00b7"

#: 조각의 **맨 앞** 낱말. 속성 이름은 조각의 첫머리에 온다는 것이 계약이다.
#: `_WORD` 를 `findall` 로 쓰면 `45° Zoom` 같은 뒤집힌 조각에서도 `Zoom` 을 찾아내
#: 값 자리에 `45°` 를 남긴다 — 그것은 시트가 뜻한 것이 아니고, 추측이다.
#: 앞에서 못 찾으면 **읽지 않은 것으로 보고**한다(아래 `_bm_segment_component`).
_LEADING_WORD = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)")


class UnknownPresetSheetError(ValueError):
    """헤더가 세 정확 열 집합 중 어느 것과도 같지 않다 — 파일 단위 판독 실패."""

    def __init__(self, header: tuple[str, ...]) -> None:
        self.header = header
        super().__init__("unknown_preset_sheet: " + ", ".join(header))


@dataclass(frozen=True)
class PresetHoldReason:
    """한 레코드를 막는 사유 하나 — 클래스와 산문을 **가른다**.

    클래스는 기계가 세고, 산문은 사람이 읽는다. 산문만 두면 「13 보류」가 한
    덩어리로 보인다.
    """

    hold_class: str
    detail: str


@dataclass(frozen=True)
class LxseqPresetRecord:
    """검증을 통과한 프리셋 1행.

    `value_raw` 는 **가공하지 않은 원문**이다. `purpose` 는 보존만 하고 값 산출에
    쓰지 않으며(REQ-LXSEQ3-004), `target_group` 은 문자열 그대로 두고 FID 로
    확장하지 않는다(REQ-LXSEQ3-005) — 그룹 멤버십은 어느 채널로도 읽히지 않아
    확장의 근거가 없다.
    """

    kind: str
    preset_id: str
    name: str
    value_raw: str
    row: int
    storable: bool
    #: 막는 사유 **전부**. 하나만 실으면 한 원인을 풀었을 때 그 행이 열릴 것처럼
    #: 보이는데 실제로는 다른 사유가 남아 안 열린다 — bm 1행이 Gobo(범위 밖)와
    #: Prism(거절) 둘 다에 막히는 것이 그 형태다.
    hold_reasons: tuple[PresetHoldReason, ...] = ()
    target_group: str | None = None
    purpose: str | None = None

    @property
    def hold_classes(self) -> tuple[str, ...]:
        """기계가 셀 수 있는 사유 클래스만."""
        return tuple(reason.hold_class for reason in self.hold_reasons)


@dataclass(frozen=True)
class PresetRowRejection:
    """행 거부 — 조용히 건너뛰지 않는다."""

    row: int
    preset_id_raw: str
    name_raw: str
    kind: str
    detail: str


@dataclass(frozen=True)
class PresetParseResult:
    sheet_kind: str
    records: tuple[LxseqPresetRecord, ...]
    rejected: tuple[PresetRowRejection, ...]


def _normalize(name: str) -> str:
    return name.strip().replace("\ufeff", "").replace(" ", "").lower()


def resolve_sheet_kind(header: tuple[str, ...]) -> str:
    """헤더의 **정확 열 집합**으로 종류를 정한다. 파일 이름을 보지 않는다.

    포함 검사를 쓰지 않는 이유: col(ID·Name·Value·Purpose)의 세 열을 포함
    검사로 두면 bm(ID·Name·TargetGroup·Value) 헤더가 그 서명에도 맞아 둘이
    안 갈린다. 정확 집합이면 넷이 쌍마다 구별된다.
    """
    present = frozenset(_normalize(name) for name in header)
    for kind, columns in PRESET_SHEET_COLUMNS.items():
        if present == frozenset(_normalize(name) for name in columns):
            return kind
    raise UnknownPresetSheetError(header)


def _attribute_tokens(value: str) -> list[str]:
    """값 문장에서 속성 이름으로 읽히는 토큰만 뽑는다. 값을 해석하지 않는다."""
    known_names = list(_ACCEPTED_ATTRIBUTES) + list(_PROBE_REJECTED) + list(_OUT_OF_SCOPE)
    found: list[str] = []
    for token in re.findall(_WORD, value):
        for known in known_names:
            if token.lower().startswith(known.lower()) and known not in found:
                found.append(known)
    return found


def classify_storability(
    kind: str,
    value_raw: str,
    *,
    capabilities: ModeCapabilities | None = None,
) -> tuple[bool, tuple[PresetHoldReason, ...]]:
    """이 값을 지금 콘솔에 넣을 수 있는가, 없으면 **무엇들이** 막는가.

    **부재가 아니라 판정이다.** 아래 사유는 전부 이 저장소가 이미 실기로 재서
    적어 둔 것이며(server/looks/schema.py), 다시 검색으로 찾아 닫힌 질문을
    열지 마라.

    사유를 **전부** 돌려준다. 하나만 돌려주면 한 원인을 풀었을 때 그 행이 열릴
    것처럼 보이는데 실제로는 다른 사유가 남아 안 열린다.

    ## `capabilities` — 능력 판독은 **주입**이지 조회가 아니다

    `capabilities` 는 `server.prechk.capability_read.read_mode_capabilities` 가
    읽어 둔 「그 기종·그 모드가 조정할 수 있는 축과 물리 범위」다. 이 함수는 그것을
    **받기만** 한다 — 여기서 콘솔을 읽으면 순수 함수가 아니게 되고, 파싱이 콘솔
    가동 여부에 묶인다.

    ``None`` (기본값)이면 범위 축은 **전혀 평가하지 않는다.** 인자 없이 부른
    결과는 이 축이 생기기 전과 같아야 하고, 그것을 검사가 다섯 행 전수로 잰다
    (`test_lxseq_preset_beam_range.py`).

    🔴 **도(degree)로 적힌 값만 대조한다.** `Frost 30%` 같은 퍼센트와 단위 없는
    맨숫자는 안 본다 — 역방향 축(Zoom 42.0->1.8)에서 콘솔의 `At` 매핑이 어느 끝을
    DMX 0 으로 두는지 **이 저장소는 아직 안 쟀다**(t235: 프로그래머 판독 별칭 부재).
    안 잰 방향으로 퍼센트를 도로 옮기는 것은 추측이고, 뒤집힌 값이 범위 안으로
    들어오면 안 잡는 것보다 나쁘다. 그 측정이 열리면 이 제약이 먼저 풀린다.

    🔴 **정규화(0~1) 축과 도 값은 대조하지 않는다.** `Frost1` 이
    `PHYSICALFROM=0.0 PHYSICALTO=1.0` 인 실측 예이고, 도 값이 그 축과 「범위 밖」인
    것은 단위가 다른 탓이지 값이 틀린 탓이 아니다 — 틀린 사유로 막지 않는다.
    """
    if kind == "preset-dim":
        if _PERCENT.match(value_raw):
            return True, ()
        return False, (
            PresetHoldReason(
                HOLD_VALUE_NOT_MACHINE_READABLE,
                "Level 이 퍼센트 형태가 아니다: " + value_raw.strip(),
            ),
        )

    if kind == "preset-col":
        components = _col_components(value_raw)
        if components is not None:
            # t134 실측(2026-08-30, MOVER-D 521 3.001): 콘솔은 퍼센트를 16비트로
            # **선형** 매핑한다 — At 70.6 -> COARSE 180 / FINE 188,
            # 180*256+188 = 46268 = round(70.6/100*65535), 오차 0.
            # 그러므로 이 변환은 더 이상 해석이 아니다.
            return True, ()
        if _HAS_RGB.search(value_raw):
            return False, (
                PresetHoldReason(
                    HOLD_VALUE_NOT_MACHINE_READABLE,
                    "RGB 자리가 R·G·B 세 성분으로 읽히지 않거나 0-255 밖이다: "
                    + value_raw.strip()
                    + " — 추측해서 옮기지 않는다",
                ),
            )
        return False, (
            PresetHoldReason(
                HOLD_NO_RGB_VALUE,
                "RGB 도 쓸 수 있는 색온도도 없다: "
                + value_raw.strip()
                + " — 켈빈은 Kim et al. (2002) 정의역 1667K-25000K 안에서만"
                " 옮긴다(밖은 외삽하지 않는다)",
            ),
        )

    tokens = _attribute_tokens(value_raw)
    unknown = _bm_unknown_attributes(value_raw)
    rejected = [a for a in tokens if a in _PROBE_REJECTED]
    out_of_scope = [a for a in tokens if a in _OUT_OF_SCOPE]
    reasons: list[PresetHoldReason] = []
    if unknown:
        reasons.append(
            PresetHoldReason(
                HOLD_ATTRIBUTE_UNKNOWN,
                "아는 어휘 어디에도 없는 속성: "
                + ", ".join(unknown)
                + " — 시트 오타이거나 이 저장소가 아직 재지 않은 속성이다."
                " 추측해서 콘솔로 보내지 않는다",
            )
        )
    if rejected:
        reasons.append(
            PresetHoldReason(
                HOLD_PROBE_REJECTED,
                "라이브 프로브가 거절한 속성: "
                + ", ".join(rejected)
                + " (server/looks/schema.py 의 M0 프로브 판정)",
            )
        )
    if out_of_scope:
        reasons.append(
            PresetHoldReason(
                HOLD_FAMILY_OUT_OF_SCOPE,
                "풀 계열이 범위 밖인 속성: "
                + ", ".join(out_of_scope)
                + " (server/looks/schema.py 의 범위 선언)",
            )
        )
    if _bm_components(value_raw) is None:
        # 어휘 축(위 둘)과 **다른 축**이다. 위는 「그 속성을 콘솔에 못 쏜다」이고
        # 이것은 「이 값을 성분으로 못 가른다」이다 — 한 행이 둘 다에 걸릴 수 있고,
        # 그때 사유는 둘 다 나와야 한다(이 함수의 독스트링).
        reasons.append(
            PresetHoldReason(
                HOLD_VALUE_NOT_MACHINE_READABLE,
                "성분으로 못 가르는 조각: "
                + ", ".join(_bm_unreadable_segments(value_raw))
                + " — 속성 이름으로 시작하는 조각만 옮긴다(버리지 않고 보고한다)",
            )
        )
    out_of_range = _bm_out_of_range_segments(value_raw, capabilities)
    if out_of_range:
        # 어휘 축·구조 축과 **또 다른 축**이다: 속성은 쏠 수 있고 조각도 읽히는데
        # 그 기종이 그 값을 못 낸다. 값·범위·채널을 사유 문면에 실어 감독이
        # **무엇을 고쳐야 하는지** 읽게 한다 — 값을 잘라 맞추지 않는다.
        reasons.append(
            PresetHoldReason(
                HOLD_VALUE_OUT_OF_RANGE,
                "콘솔이 답한 물리 범위 밖인 값: "
                + ", ".join(out_of_range)
                + " — 시트 값을 범위 안으로 고치거나 그 값을 내는 기종으로 배정을 바꾼다"
                " (잘라 맞추지 않는다)",
            )
        )
    if reasons:
        return False, tuple(reasons)
    return True, ()


def dim_level_percent(value_raw: str) -> int | None:
    """dim 의 ``Level`` 원문에서 퍼센트 정수를 꺼낸다. 형태가 아니면 ``None``.

    ``classify_storability`` 가 storable 판정에 쓰는 것과 **같은 정규식**을 쓴다.
    소비자 쪽에 정규식 사본을 두면 판정기와 판독기가 갈라져, 판정이 통과시킨 값을
    판독기가 못 읽는 날이 온다 — ``preset_label_refusal`` 이 같은 이유로 술어를
    밖으로 낸 것과 같은 규율이다(t97).

    명령 문형은 여기서 만들지 않는다. 이 모듈은 파싱만 하고, 번역은 툴 층이 한다
    (``test_lxseq_preset_tool.py::test_the_preset_modules_do_not_import_the_builder``).
    """
    match = _PERCENT.match(value_raw)
    if match is None:
        return None
    return int(match.group(1))


def _rgb_components(value_raw: str) -> tuple[int, int, int] | None:
    """col 원문에서 0-255 세 성분. 세 성분으로 안 읽히거나 범위 밖이면 ``None``.

    판정(`classify_storability`)과 판독(`col_rgb_percents`)이 **이 하나**를 쓴다.
    사본을 두면 판정이 통과시킨 값을 판독기가 못 읽는 날이 오고, 그날 임포터는
    한 줄도 안 보내고 통째로 거절한다.
    """
    match = _RGB_TRIPLE.search(value_raw)
    if match is None:
        return None
    values = tuple(int(group) for group in match.groups())
    if any(v > _RGB_COMPONENT_MAX for v in values):
        return None
    return values


#: col 값에서 색온도를 꺼내는 술어. `~3200K` · `3200K` 둘 다 받는다.
_KELVIN = re.compile(r"~?\s*(\d{3,5})\s*K\b", re.IGNORECASE)

#: Kim et al. (2002) 근사의 정의역. 밖은 **외삽하지 않고 보류**한다 —
#: 근사식을 정의역 밖으로 끌면 조용히 틀린 색이 나간다.
_KELVIN_MIN = 1667.0
_KELVIN_MAX = 25000.0


def planckian_xy(kelvin: float) -> tuple[float, float]:
    """색온도 -> CIE 1931 xy (플랑크 궤적 위의 점).

    **출처: Kim et al. (2002)**, "Design of Advanced Color Temperature Control
    System for HDTV Applications", Journal of the Korean Physical Society 41(6).
    플랑크 궤적의 3차 근사이며 정의역은 1667K-25000K 다. 「대략 이 식」이 아니라
    이 논문의 계수 그대로다.

    검산 앵커(식을 만드는 데 쓰지 않은 독립 기준):

    * **Illuminant A (2856K)** — CIE 표준광 A 는 **플랑크 복사체**다. 그래서 이
      식이 가장 정확히 맞아야 하는 자리이고, 실측 오차 dx 0.0005 · dy 0.0001 이다.
    * **D65 (6504K) · D50 (5003K)** — dy 가 0.005-0.007 어긋난다. 이것은 계수
      오류가 **아니다**: D 계열은 **주광 궤적** 위에 있고 플랑크 궤적에서 의도적으로
      떨어져 있다(Duv 약 +0.003). 어긋나야 맞는 자리에서 어긋나고, 맞아야 맞는
      자리에서 맞는다 — 그 대비가 이 계수의 근거다.
    """
    t = kelvin
    if t <= 4000.0:
        x = -0.2661239e9 / t**3 - 0.2343589e6 / t**2 + 0.8776956e3 / t + 0.179910
    else:
        x = -3.0258469e9 / t**3 + 2.1070379e6 / t**2 + 0.2226347e3 / t + 0.240390
    if t <= 2222.0:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif t <= 4000.0:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    return x, y


def kelvin_to_rgb(kelvin: float) -> tuple[int, int, int]:
    """색온도 -> sRGB 0-255. **손실 변환이다.**

    **출처: IEC 61966-2-1 (sRGB)** — D65 백색점, 표준 변환 행렬과 전달 함수.
    xy -> XYZ(Y=1) -> 선형 sRGB -> 감마.

    검산 앵커: D65 백색점 `xy(0.3127, 0.3290)` 을 넣으면 `(255, 255, 255)` 가
    나온다. D65 가 sRGB 백색이라는 것은 규격의 **정의**이므로, 행렬을 이 사실에
    맞춰 조정한 것이 아니라 규격 계수가 그 정의를 재현하는 것이다.

    🔴 **밝기는 정규화된다.** 최대 성분을 255 로 맞추므로 이 값은 **색상만**
    옮기고 광량은 옮기지 않는다. 프리셋이 싣는 것도 색이므로 의도한 범위다.

    🔴 **근사라는 사실을 숨기지 않는다.** 시트가 RGB 와 켈빈을 **둘 다** 싣는
    유일한 행(`COL.01` `R255 G180 B60 / ~2400K`)에서 저자값과 변환값을 나란히
    재면 `R 255/255 · G 180/160 · B 60/66` 으로, G 가 20/255 어긋난다. 그래서
    RGB 가 있으면 **저자값이 이긴다**(`_col_components` 의 순서) — 변환은 RGB 가
    아예 없는 행에만 쓴다.
    """
    return _xy_to_srgb(*planckian_xy(kelvin))


def _xy_to_srgb(x: float, y: float) -> tuple[int, int, int]:
    """CIE 1931 xy -> sRGB 0-255. **출처: IEC 61966-2-1** (D65, 표준 행렬·전달 함수).

    `kelvin_to_rgb` 에서 분리해 둔 이유는 검사다 — 행렬을 재려면 궤적이 아니라
    **백색점 xy 를 직접** 넣어야 한다(6504K 의 궤적 위 점은 D65 백색점과 미세하게
    다르다). 합쳐 두면 그 검사를 쓸 수 없다.
    """
    big_x, big_y, big_z = x / y, 1.0, (1.0 - x - y) / y
    linear = [
        3.2406 * big_x - 1.5372 * big_y - 0.4986 * big_z,
        -0.9689 * big_x + 1.8758 * big_y + 0.0415 * big_z,
        0.0557 * big_x - 0.2040 * big_y + 1.0570 * big_z,
    ]
    linear = [max(0.0, v) for v in linear]
    peak = max(linear)
    if peak > 0.0:
        linear = [v / peak for v in linear]
    out: list[int] = []
    for v in linear:
        encoded = 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
        out.append(round(max(0.0, min(1.0, encoded)) * 255))
    return (out[0], out[1], out[2])


def _kelvin_components(value_raw: str) -> tuple[int, int, int] | None:
    """색온도 단독 값 -> RGB. 정의역 밖이거나 켈빈이 없으면 ``None``."""
    match = _KELVIN.search(value_raw)
    if match is None:
        return None
    kelvin = float(match.group(1))
    if not (_KELVIN_MIN <= kelvin <= _KELVIN_MAX):
        return None
    return kelvin_to_rgb(kelvin)


def _col_components(value_raw: str) -> tuple[int, int, int] | None:
    """col 원문 -> RGB 성분. **판정기와 판독기가 함께 쓰는 유일한 술어다.**

    🔴 이 함수가 하나인 것이 계약이다. `tools.py:1757` 이 그 자리를 지목한다 —
    「판정기가 통과시킨 값을 판독기가 못 읽었다는 뜻이다. 둘은 같은 술어를 쓰므로
    여기 오면 술어가 갈라진 것이다」. 갈라지면 `_lxseq_preset_apply_command` 가
    `None` 을 내고 소비 루프가 **번들을 통째로 버린다**(`apply_untranslatable`) —
    2행을 얻으려다 col 8행을 다 잃는다. t229 가 그 형태를 실측으로 재현했다.

    순서가 계약이다: **RGB 가 있으면 저자값이 이긴다.** 켈빈 변환은 근사이므로
    시트가 명시한 값을 덮지 않는다.
    """
    components = _rgb_components(value_raw)
    if components is not None:
        return components
    return _kelvin_components(value_raw)


def col_conversion_note(value_raw: str) -> str | None:
    """켈빈에서 만든 값이면 **원값과 변환값을 나란히** 적은 한 줄. 아니면 ``None``.

    🔴 근사를 조용히 내보내지 않기 위한 자리다. 승인 카드에는 시트 원문(`~3200K`)만
    뜨는데 콘솔에 나가는 것은 근사된 RGB 다 — 그 둘이 다르다는 사실이 승인하는
    사람 눈앞에 있어야 한다. 「조용히 틀린 것이 크게 없는 것보다 나쁘다」.

    RGB 가 원문에 있으면 ``None`` 이다 — 그때는 변환이 일어나지 않았고, 알릴 근사도
    없다.
    """
    if _rgb_components(value_raw) is not None:
        return None
    components = _kelvin_components(value_raw)
    if components is None:
        return None
    return (
        value_raw.strip()
        + " -> R"
        + str(components[0])
        + " G"
        + str(components[1])
        + " B"
        + str(components[2])
        + " (켈빈→sRGB 근사 · Kim et al. 2002 + IEC 61966-2-1)"
    )


def col_rgb_percents(value_raw: str) -> tuple[float, float, float] | None:
    """col 원문 -> 콘솔 퍼센트 세 개. 옮길 수 없으면 ``None``.

    **소수 1자리는 형제 생산자와 맞춘 것이다.** `src/Lighting_Designer/
    90_빌드파이프라인/make_ma3.py:85-87` 이 같은 시트를 `%.1f` 로 방출하므로,
    같은 자리수를 쓰면 두 경로가 콘솔에 **같은 숫자**를 보낸다. 오늘 이 카드의
    출발점이 「한쪽은 통과하고 한쪽은 막힌 불일치」였고, 자리수를 늘리면 그
    불일치가 값 축에서 되살아난다.

    대가를 적어 둔다 — 소수 1자리는 0-255 중 **12개**(7 8 9 10 20 21 234 235
    245 246 247 248)에서 왕복이 ±1 로 어긋난다. **현재 시트의 18개 값은 그중
    하나도 안 쓴다(0/18).** 시트를 고쳐 저 값이 들어오면 이 줄이 걸려야 한다.
    전 구간 무손실이 필요해지면 소수 3자리가 0/256 이지만, **콘솔이 소수 몇
    자리까지 받는지는 안 쟀다** — 그것이 선행 측정이다.
    """
    components = _col_components(value_raw)
    if components is None:
        return None
    return tuple(round(v / 255 * 100, 1) for v in components)


def _bm_segment_component(segment: str) -> tuple[str, str] | None:
    """bm 값의 조각 하나 -> ``(속성, 원문값)``. 못 읽으면 ``None``.

    **원자다.** 아래 두 함수가 전부 이것만 부른다 — 조각을 읽는 방법이 한 곳에만
    있어야 「성분 목록」과 「못 읽은 조각 목록」이 서로 어긋날 수 없다.

    🔴 **어휘를 묻지 않는다.** 첫 낱말을 아는 이름 목록에 대보고 싶어지지만, 그러면
    이 술어가 **어휘 축과 한 몸**이 된다. 그 둘은 다른 질문이다:

        구조 축 (여기)      이 값을 (속성, 값) 조각으로 가를 수 있는가
        어휘 축 (아래 분기)  그 속성을 콘솔에 쏠 수 있는가

    실제로 한 몸으로 만들었다가 t135 의 트립와이어를 깼다. 그 검사는 목록을
    `Prism1` 로 치환하면 BM.03 이 **열린다**는 것을 실제로 쏴서 보여주는데(그것이
    그 치환이 회귀라는 증명이다), 구조 축이 어휘를 물으면 `Prism` 이 목록에서
    빠진 순간 조각도 못 읽게 되어 그 행이 **다른 사유로** 막힌다 — 증명이 조용히
    사라진다. 그래서 여기서는 첫 낱말을 **원문 그대로** 속성 이름으로 나른다.

    값 자리에 또 다른 **아는** 속성 이름이 있으면 ``None`` 이다. `Zoom 45 Iris 50`
    처럼 구분자 없이 붙은 조각을 통째로 `Zoom` 의 값으로 실으면 `Iris` 가 조용히
    사라진다 — 그것이 8.1 절이 막으려는 실패 그 자체다. 이쪽은 「아는 이름이
    값 안에 숨어 있는가」라 어휘 질문이 맞다.
    """
    text = segment.strip()
    match = _LEADING_WORD.match(text)
    if match is None:
        return None
    attribute = match.group(1)
    value = text[match.end() :].strip()
    if not value:
        return None
    if _attribute_tokens(value):
        return None
    return attribute, value


def _bm_components(value_raw: str) -> tuple[tuple[str, str], ...] | None:
    """bm 원문 -> ``(속성, 원문값)`` 목록. **판정기와 판독기가 함께 쓸 유일한 술어다.**

    `_col_components` 의 형제이고 계약도 같다 — 다른 것은 반환형뿐이다::

        col:  value_raw -> (R, G, B)                          3성분 **고정**
        bm:   value_raw -> (("Zoom", "45°"), ("Prism", "OFF")) **가변** 길이

    🔴 **가변 길이라 col 의 보장이 그대로 서지 않는다.** col 은 개수가 상수라
    한쪽이 성분을 흘리면 형태가 바로 깨지지만, bm 은 목록에서 하나가 빠져도
    여전히 목록이다. 그래서 「같은 술어를 부른다」만으로는 부족하고, **성분 수가
    보존되는지를 검사가 따로 지킨다**(`test_lxseq_preset_beam_components.py`).
    유실은 `apply_untranslatable` 보다 **조용한** 실패다 — 판정 통과, 명령 발사,
    콘솔엔 절반, 되읽기는 슬롯 점유만 확인.

    **원문값을 그대로 나르고 해석하지 않는다.** `45°` 의 `45` 가 콘솔에서 도인지
    퍼센트인지 이 저장소는 모른다 — dim 은 퍼센트, col 은 16비트 선형이 실측으로
    닫혔지만 `Zoom` 자리는 비어 있고, 프로그래머 판독 채널이 없어 **지금은 이 채널로
    못 잰다**(t235). 「원리적으로」가 아니다 — t235 가 그 벽을 **응답기 `ROOT_ALIASES` 에
    별칭이 없는 것**으로 좁혔고, 그것은 제거 가능한 미구현이다(다만 여는 것은 감독 승인
    사안이고 아직 안 열렸다). 그래서 명령 빌더는 **아직 만들지 않는다**
    (`.moai/reports/t229-bm/verdict.md` §8.2).

    **all-or-nothing 이다.** 조각 하나라도 못 읽으면 ``None`` — 읽은 것만 돌려주면
    그것이 곧 성분 유실이고, 이 함수가 막으려는 바로 그 실패다.
    """
    segments = value_raw.split(_BM_SEGMENT_SEPARATOR)
    components: list[tuple[str, str]] = []
    for segment in segments:
        component = _bm_segment_component(segment)
        if component is None:
            return None
        components.append(component)
    if not components:
        return None
    return tuple(components)


#: 시트 어휘와 콘솔 어휘가 **길이 방향이 반대**라 어휘 검사는 대칭이어야 한다
#: (`_SHEET_TO_CONSOLE_ATTRIBUTE` 주석의 접두 방향 표 참조). 다만 역방향을 그냥
#: 열면 `Zo` 가 `Zoom` 의 접두라는 이유로 통과한다 — 그것은 좁아진 fail-open 이지
#: 사라진 fail-open 이 아니다. 그래서 역방향은 **숫자 접미만** 허용한다: 두 어휘가
#: 실제로 갈리는 모양이 그것뿐이기 때문이다(넷 전부 `Focus`->`Focus1` 꼴, 실측).
_DIGIT_SUFFIX = re.compile(r"^\d+$")


def _is_known_attribute(name: str) -> bool:
    """이 속성 이름이 이 저장소가 **아는** 어휘 어딘가에 있는가.

    🔴 **fail-closed 축이다.** 아래 `rejected`/`out_of_scope` 는 「막는 목록에
    걸렸는가」를 묻는다 — 걸리는 게 없으면 사유가 0건이라 그 행이 열린다. 어느
    목록에도 없는 이름(시트 오타, 새 속성)이 정확히 그 구멍으로 나갔다(t137).
    이 술어는 반대로 「아는 목록에 **있는가**」를 물어서 모르는 것을 막는다.
    저장소의 다른 판정기들(`preset_mapper` POOL_UNREADABLE, `rig/section.py`
    SECTION_TRUNCATED)과 방향을 맞춘다.
    """
    lowered = name.lower()
    for known in list(_ACCEPTED_ATTRIBUTES) + list(_PROBE_REJECTED) + list(_OUT_OF_SCOPE):
        known_lower = known.lower()
        if lowered.startswith(known_lower):
            return True
        if known_lower.startswith(lowered) and _DIGIT_SUFFIX.match(known_lower[len(lowered) :]):
            return True
    return False


def _bm_unknown_attributes(value_raw: str) -> tuple[str, ...]:
    """읽히기는 하는데 아는 이름이 아닌 속성들. 못 읽은 조각은 여기 안 온다 —
    그쪽은 `HOLD_VALUE_NOT_MACHINE_READABLE` 이 이미 든다(축이 다르다)."""
    found: list[str] = []
    for segment in value_raw.split(_BM_SEGMENT_SEPARATOR):
        component = _bm_segment_component(segment)
        if component is None:
            continue
        name = component[0]
        if not _is_known_attribute(name) and name not in found:
            found.append(name)
    return tuple(found)


#: 조각 값에서 **명시된 도(degree)** 만 읽는 술어. `45°` · `45 deg` · `20 DEGREES` 를
#: 받고 `30%` · 맨숫자 `45` 는 받지 않는다.
#:
#: 🔴 **표기가 없으면 읽지 않는다.** 퍼센트를 물리값으로 옮기려면 콘솔의 `At` 매핑이
#: 어느 끝을 DMX 0 으로 두는지 알아야 하는데, 역방향 축(Zoom 42.0->1.8)에서 그 방향은
#: **안 쟀다**. 재지 않은 방향으로 퍼센트를 도로 옮기면 「넓게」가 「좁게」가 되어
#: 조용히 뒤집힌 값이 범위 안으로 들어간다 — 안 잡는 것보다 나쁘다.
#: `deg(?:rees?)?` 로 좁힌 것은 `45 degauss` 같은 다른 낱말을 도로 읽지 않기 위한
#: 것이고, 「degrees 는 도가 아닐 수도」라는 추측이 아니다.
_DEGREE_VALUE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(?:°|deg(?:rees?)?(?![A-Za-z0-9]))", re.IGNORECASE
)

#: 정규화 축(0~1)의 상한. `Frost1` 이 `PHYSICALFROM=0.0 PHYSICALTO=1.0` 인 실측 예다.
#: 도 값과 정규화 축은 **단위가 다르므로** 대조 자체가 성립하지 않는다 — 그런 짝은
#: 「범위 밖」이라고 부르지 않고 **안 잰 것으로 남긴다**(틀린 사유로 막는 것이
#: 안 막는 것보다 나쁘다).
_NORMALIZED_AXIS_MAX = 1.0


def _degree_value(value: str) -> float | None:
    """조각의 값 부분에서 도 값을 꺼낸다. 도 표기가 없으면 ``None``."""
    match = _DEGREE_VALUE.match(value)
    if match is None:
        return None
    return float(match.group(1))


def _bm_out_of_range_segments(
    value_raw: str, capabilities: ModeCapabilities | None
) -> tuple[str, ...]:
    """능력 판독과 시트 값을 대조해 **범위 밖** 조각의 설명을 고른다.

    `capabilities` 가 ``None`` 이면 **항상 빈 튜플**이다 — 주입이 없으면 이 축은
    존재하지 않는 것과 같고, 그것이 「인자 없이 부르면 예전과 바이트 동일」의 근거다.

    조각마다 **넷을 다 통과해야** 걸린다. 넷 전부가 하중을 진다:

    1. 조각이 (속성, 값) 으로 읽힌다 — 못 읽은 조각은 다른 사유가 이미 든다.
    2. 값에 **도 표기**가 있다 (`_DEGREE_VALUE` 주석의 방향 미측정 참조).
    3. 그 속성의 축이 판독되어 있고 두 끝이 다 읽혔다 (`AxisRange.measurable`).
       못 읽은 축을 「범위 밖」이라고 부르면 미판독이 결함으로 바뀐다.
    4. 그 축이 정규화(0~1) 모양이 아니다 (`_NORMALIZED_AXIS_MAX` 주석 참조).

    시트 토큰 -> 콘솔 이름은 `_SHEET_TO_CONSOLE_ATTRIBUTE` **하나만** 쓴다. 둘째 표를
    만들면 두 어휘의 연결 지점이 둘이 되고, 그 순간 한쪽만 고치는 날이 온다.
    표에 없는 토큰(`Zoom`)은 두 어휘가 같은 자리이므로 시트 토큰을 그대로 쓴다 —
    실측이 그것을 확인한다(FixtureType 11 채널 28 `ATTRIBUTE=Zoom`).

    ⚠️ **기종·모드 이름을 적지 못한다.** `ModeCapabilities` 는 타입/모드 슬롯을
    싣지 않으므로(`server/prechk/capability_read.py`) provenance 로 쓸 수 있는 것은
    축의 **채널 이름**뿐이다. 어느 기종의 판독을 주입했는지는 부르는 쪽이 안다.
    """
    if capabilities is None:
        return ()
    found: list[str] = []
    for segment in value_raw.split(_BM_SEGMENT_SEPARATOR):
        component = _bm_segment_component(segment)
        if component is None:
            continue
        attribute, value = component
        degrees = _degree_value(value)
        if degrees is None:
            continue
        axis = capabilities.axis(_SHEET_TO_CONSOLE_ATTRIBUTE.get(attribute, attribute))
        if axis is None or not axis.measurable:
            continue
        low = min(axis.physical_from, axis.physical_to)
        high = max(axis.physical_from, axis.physical_to)
        if low >= 0.0 and high <= _NORMALIZED_AXIS_MAX:
            continue
        # 정렬해서 담는다 — 판독기는 방향을 보존하지만(Zoom 42.0->1.8) 포함 검사는
        # 방향과 무관하다. 정렬 없이 `from <= v <= to` 로 쓰면 역방향 축의 모든 값이
        # 범위 밖이 된다.
        if low <= degrees <= high:
            continue
        found.append(
            segment.strip()
            + " -> "
            + axis.attribute
            + " 축 "
            + str(low)
            + "~"
            + str(high)
            + " (채널 '"
            + axis.channel_name
            + "')"
        )
    return tuple(found)


def _bm_unreadable_segments(value_raw: str) -> tuple[str, ...]:
    """성분으로 못 가른 조각들. 보류 사유 문면에 **그대로** 실린다.

    🔴 **버리지 않고 보고한다.** BM.05 의 `예비` 는 속성이 아니고, 정본 시트 규약
    (`src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md`)은 주석 토큰을 규정하지
    않는다 — 실제로 재서 확인했다(그 문서에 `예비` 0건). 규약이 없는 토큰을
    조용히 무시하면 시트가 뜻한 것의 일부가 소리 없이 사라진다.
    """
    return tuple(
        segment.strip()
        for segment in value_raw.split(_BM_SEGMENT_SEPARATOR)
        if _bm_segment_component(segment) is None
    )


def parse_preset_csv(text: str) -> PresetParseResult:
    """PRESET 시트 본문을 레코드와 거부로 가른다.

    행 검증 실패는 예외로 새어나가지 않는다. 파일 단위 실패인
    unknown_preset_sheet 만 UnknownPresetSheetError 로 올린다.
    한 행에 결함이 여럿이면 먼저 걸린 하나만 보고한다 — 행당 거부 하나다.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.DictReader(io.StringIO(text))
    header = tuple(reader.fieldnames or [])
    kind = resolve_sheet_kind(header)
    columns = PRESET_SHEET_COLUMNS[kind]
    actual = dict((_normalize(name), name) for name in header)
    prefix = PRESET_ID_PREFIXES[kind]
    value_column = "Level" if kind == "preset-dim" else "Value"

    records: list[LxseqPresetRecord] = []
    rejected: list[PresetRowRejection] = []
    seen: set[str] = set()

    for line_no, row in enumerate(reader, start=2):
        cell = dict((name, (row.get(actual[_normalize(name)]) or "").strip()) for name in columns)
        preset_id = cell["ID"]
        name = cell["Name"]
        problem = None
        if not preset_id:
            problem = ("empty_id", "ID 가 비었다")
        elif not preset_id.startswith(prefix):
            problem = (
                "id_prefix_mismatch",
                "이 시트는 " + prefix + " 로 시작해야 한다: " + preset_id,
            )
        elif preset_id in seen:
            problem = ("duplicate_id", "같은 ID 가 두 번 나온다: " + preset_id)
        elif not name:
            problem = ("empty_name", "Name 이 비었다")
        if problem is not None:
            rejected.append(
                PresetRowRejection(
                    row=line_no,
                    preset_id_raw=preset_id,
                    name_raw=name,
                    kind=problem[0],
                    detail=problem[1],
                )
            )
            continue

        seen.add(preset_id)
        value_raw = cell[value_column]
        storable, hold_reasons = classify_storability(kind, value_raw)
        records.append(
            LxseqPresetRecord(
                kind=kind,
                preset_id=preset_id,
                name=name,
                value_raw=value_raw,
                row=line_no,
                storable=storable,
                hold_reasons=hold_reasons,
                target_group=cell.get("TargetGroup") or None,
                purpose=cell.get("Purpose") or None,
            )
        )
    return PresetParseResult(sheet_kind=kind, records=tuple(records), rejected=tuple(rejected))
