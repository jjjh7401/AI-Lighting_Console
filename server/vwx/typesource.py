"""라이브러리에 없는 픽스처 타입을 **어디서 가져올 것인가**.

지금까지 ``fixture_type_not_in_library``는 *"GDTF 라이브러리 임포트를 먼저 수행하라"*
는 **문장 하나**로 끝났다. 조작자는 무엇을·어디서·어디에 놓아야 하는지 듣지 못했다.
이 모듈이 그 자리를 채운다 — 막다른 길을 **행동 가능한 단계**로 바꾼다.

**갈래는 넷이고 순서가 있다**(``patch_add_fixtures.html`` — Insert New Fixture의
``Library`` 탭이 드라이브와 소스 MA/User/Shares를 고르게 한다):

======  =========================  ======================  ============
순위    갈래                        지금 손에 있는가          자동화
======  =========================  ======================  ============
①       MVR이 이미 동봉             **있다**                 파일 추출까지
②       사용자가 GDTF 파일 제출      물어본다                 놓을 자리 안내
③       GDTF Share에서 내려받기      네트워크·World Server    안내만
④       콘솔 Fixture Type 편집기     사람                     안내만
======  =========================  ======================  ============

①이 압도적으로 낫다. **도면이 실제로 쓴 그 버전**이라 이름으로 검색해 받는 것과 달리
버전이 어긋날 여지가 없다.

**[HARD] 언제 놓느냐가 중요하다.** round20 세션 GO 조건 ①은 *세션 중 GDTF 임포트*를
금지한다 — 타입 수가 늘면 라이브러리 열거가 절단 구간에 들어가 그 세션의 판정이
흔들린다. 그래서 이 모듈이 내는 모든 단계는 **세션 착수 전**을 명시한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from server.vwx.mvr import bundled_fixture_type_bytes

#: 갈래 이름 — 사용자에게 그대로 보인다.
SOURCE_BUNDLED_IN_MVR = "bundled_in_mvr"
SOURCE_USER_SUPPLIED_FILE = "user_supplied_gdtf"
SOURCE_GDTF_SHARE = "gdtf_share"
SOURCE_CONSOLE_EDITOR = "console_fixture_type_editor"

#: grandMA3 라이브러리 루트(사용자 홈 기준). 실물 확인: 이 아래에
#: ``fixturetypes`` · ``mvr`` · ``datapools`` 가 있다.
LIBRARY_ROOT = Path("MALightingTechnology") / "gma3_library"

#: GDTF 파일을 놓는 자리. ``Library`` 탭의 ``Internal`` 드라이브가 여기를 읽는다.
FIXTURE_TYPE_DIR = LIBRARY_ROOT / "fixturetypes"

#: MVR 파일을 놓는 자리 — ``patch_mvr.html``이 명시한다("The folder is ../gma3_library/mvr").
MVR_DIR = LIBRARY_ROOT / "mvr"

#: 조작자에게 보여 줄 경로 문자열 — **여기서 한 번만 만든다.** 문장마다 `Path`를
#: 다시 조립하면 그것이 형제 표면이고, 한 곳만 고쳤을 때 안내가 갈라진다.
FIXTURE_TYPE_HINT = str(Path("~") / FIXTURE_TYPE_DIR)
MVR_HINT = str(Path("~") / MVR_DIR)

#: 세션 중 임포트 금지의 근거. 모든 단계 문장이 이것을 달고 나간다.
BEFORE_SESSION_NOTE = (
    "**세션 착수 전에** 끝내라 — 세션 중 라이브러리를 늘리면 타입 열거가 절단 구간에 "
    "들어가 그 세션의 판정이 흔들린다(round20 세션 GO 조건 ①)."
)


@dataclass(frozen=True)
class ProvisioningStep:
    """타입 하나를 라이브러리에 올리는 방법 하나."""

    source: str
    instrument_type: str
    #: ``제조사@이름`` 표기. 비어 있으면 도면이 이름만 주었다는 뜻이다.
    gdtf_spec: str
    #: 지금 이 자리에서 파일을 낼 수 있는가. ``False``면 사람이 가져와야 한다.
    available_now: bool
    #: 조작자가 그대로 따라 할 수 있는 문장.
    action: str
    #: 파일을 낼 수 있을 때 그 바이트. ``available_now``가 참일 때만 찬다.
    payload: bytes | None = None
    suggested_filename: str = ""

    @property
    def install_hint(self) -> str:
        return f"{FIXTURE_TYPE_HINT}/{self.suggested_filename or '<이름>.gdtf'}"


def _share_step(instrument_type: str, spec: str) -> ProvisioningStep:
    return ProvisioningStep(
        source=SOURCE_GDTF_SHARE,
        instrument_type=instrument_type,
        gdtf_spec=spec,
        available_now=False,
        action=(
            f"GDTF Share에서 '{instrument_type}'을(를) 찾아 받는다. 콘솔에서는 "
            "Patch > Insert New Fixture > Library 탭의 Shares 소스로도 볼 수 있다"
            "(World Server 연결이 있어야 한다). "
            f"받은 파일은 {FIXTURE_TYPE_HINT}에 둔다. " + BEFORE_SESSION_NOTE
        ),
    )


def _editor_step(instrument_type: str, spec: str) -> ProvisioningStep:
    return ProvisioningStep(
        source=SOURCE_CONSOLE_EDITOR,
        instrument_type=instrument_type,
        gdtf_spec=spec,
        available_now=False,
        action=(
            f"콘솔의 Fixture Type 편집기에서 '{instrument_type}'을(를) 직접 만든다. "
            "채널 배치를 손으로 정의해야 하므로 마지막 수단이다 — 도면과 어긋나면 "
            "패치는 되지만 출력이 틀린다. " + BEFORE_SESSION_NOTE
        ),
    )


def _user_file_step(instrument_type: str, spec: str) -> ProvisioningStep:
    return ProvisioningStep(
        source=SOURCE_USER_SUPPLIED_FILE,
        instrument_type=instrument_type,
        gdtf_spec=spec,
        available_now=False,
        action=(
            f"'{instrument_type}'의 GDTF 파일이 있으면 주세요. "
            f"{FIXTURE_TYPE_HINT}에 두면 콘솔 Library 탭의 Internal 소스에 "
            "나타납니다. " + BEFORE_SESSION_NOTE
        ),
    )


def plan_for_missing_type(
    instrument_type: str,
    *,
    gdtf_spec: str = "",
    mvr_bytes: bytes | None = None,
) -> tuple[ProvisioningStep, ...]:
    """라이브러리에 없는 타입 하나를 올리는 방법을 **선호 순서로** 낸다.

    첫 항목이 가장 나은 갈래다. MVR이 그 타입을 동봉하고 있으면 그것이 첫 항목이고
    ``payload``에 파일이 실려 나간다 — 조작자가 받아 두기만 하면 된다.

    **빈 목록을 내지 않는다.** 자동화할 수 없는 갈래라도 사람이 밟을 길은 늘 있다.
    """
    steps: list[ProvisioningStep] = []

    if mvr_bytes is not None and gdtf_spec:
        payload = bundled_fixture_type_bytes(mvr_bytes, gdtf_spec)
        if payload is not None:
            filename = f"{gdtf_spec}.gdtf"
            steps.append(
                ProvisioningStep(
                    source=SOURCE_BUNDLED_IN_MVR,
                    instrument_type=instrument_type,
                    gdtf_spec=gdtf_spec,
                    available_now=True,
                    payload=payload,
                    suggested_filename=filename,
                    action=(
                        f"MVR이 '{gdtf_spec}'의 GDTF를 이미 담고 있다 — 도면이 실제로 쓴 "
                        f"그 버전이다. 꺼내서 {FIXTURE_TYPE_HINT}/{filename}에 "
                        "두거나, MVR 자체를 "
                        f"{MVR_HINT}에 두고 Patch 메뉴의 Import MVR로 넣는다"
                        "(그 경우 픽스처·Layer·Class까지 함께 들어온다). " + BEFORE_SESSION_NOTE
                    ),
                )
            )

    steps.append(_user_file_step(instrument_type, gdtf_spec))
    steps.append(_share_step(instrument_type, gdtf_spec))
    steps.append(_editor_step(instrument_type, gdtf_spec))
    return tuple(steps)


def plan_for_rows(
    rows: Sequence[Mapping[str, str]],
    known_types: Sequence[str],
    *,
    mvr_bytes: bytes | None = None,
) -> tuple[ProvisioningStep, ...]:
    """행 묶음에서 **라이브러리에 없는 타입 전부**의 조달 계획을 낸다.

    타입마다 첫 번째(가장 나은) 갈래 하나씩만 낸다 — 조작자가 볼 목록이 타입 수만큼
    길어지면 읽히지 않는다. 다른 갈래가 필요하면
    :func:`plan_for_missing_type`을 그 타입에 대해 직접 부른다.
    """
    known = set(known_types)
    seen: set[str] = set()
    plans: list[ProvisioningStep] = []
    for row in rows:
        name = (row.get("Instrument Type") or "").strip()
        if not name or name in known or name in seen:
            continue
        seen.add(name)
        spec = (row.get("GDTF Fixture") or "").strip()
        steps = plan_for_missing_type(name, gdtf_spec=spec, mvr_bytes=mvr_bytes)
        plans.append(steps[0])
    return tuple(plans)
