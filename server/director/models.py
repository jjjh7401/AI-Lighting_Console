"""교환 객체 strict parsing (SPEC-LDSTORE-001 M1 · REQ-LDPLUGIN-007).

계약 §2 의 공통 wire 규칙을 **계약이 규범으로 지정한 JSON Schema 하나로** 집행한다.
타입·범위·pattern·closed-world·required 를 여기서 손으로 다시 적지 않는다 — 계약이
*"wire shape 의 단일 원본"* 을 스키마에 두었으므로 두 번째 원본을 만들면 그 둘이
어긋나는 날 어느 쪽이 맞는지 판정할 근거가 사라진다.

스키마가 이미 담고 있어 여기서 중복하지 않는 것들 (실측 확인, 2026-09-14):

- `Id` `^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$` · `Digest` `^sha256:[0-9a-f]{64}$`
- `Revision` 1..2147483647 · `Ms` 범위 · `environment` enum · `schema_version` const
- 모든 교환 객체의 `additionalProperties: false`
- 시각의 `format: date-time` **과 함께** `pattern: "Z$"` — 계약 §2 의 "끝은 Z" 를
  스키마가 직접 강제하므로 별도 검사를 넣지 않는다. 달력 유효성(2월 30일 거부)은
  format checker 가 맡는다. 계약 §11 이 *"format checker를 끈 validator에서는
  date-time까지 보장되지 않는다"* 고 경고하므로 checker 를 반드시 켠다.

스키마가 담을 수 없어 여기서 하는 것들:

- JSON 자체의 거부: 파싱 불가, 중복 key, 비유한 수(NaN/Infinity), invalid UTF-8.
  이것들은 **정규화 전에** 걸러야 한다 (계약 §9: 중복 key 는 canonicalization 전 거부).
- 전송 상한: 2 MiB.
- `environment` 가 **서버 deployment 와 일치**하는지. 스키마는 enum 만 알고 서버가
  어떤 환경인지는 모른다. 계약 §2: 클라이언트가 `synthetic` 으로 바꾸어 production
  안전 검사를 우회할 수 없다.
- 오류를 계약 §5 의 안정 code 와 §3 의 ErrorEnvelope 형태로 옮기기.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

#: 계약 §2 — 유일하게 허용되는 wire version.
SCHEMA_VERSION = "1.0.0"

#: 계약 §2 의 다섯 message_type. 스키마 `$defs` 의 이름과 같다.
MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        "context_snapshot",
        "lighting_plan",
        "validation_report",
        "feedback_record",
        "execution_receipt",
    }
)

#: 계약 §2 — "최대 structured plan 2 MiB". 다섯 중 plan 이 가장 크고 나머지는 자체
#: 상한(knowledge page 256 KiB 등)이 더 작으므로, raw bytes 에 이 한 값을 일률로 건다.
#: 보수적인 읽기다: 정상 예제 중 가장 큰 것이 59 KB 이므로 여유가 충분하다.
MAX_EXCHANGE_BYTES = 2 * 1024 * 1024

#: 계약 §3 — ErrorEnvelope 의 상한.
_MAX_DETAILS = 128
_MAX_MESSAGE_CHARS = 4096

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "exchange.schema.json"


@dataclass(frozen=True, slots=True)
class Detail:
    """ErrorEnvelope 의 details 항목 (계약 §3).

    ``field`` 는 **submitted 객체 root 기준 JSON Pointer** 또는 빈 문자열이다.
    """

    field: str
    message: str
    rule_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {"field": self.field, "message": self.message}
        if self.rule_id is not None:
            payload["rule_id"] = self.rule_id
        return payload


class ExchangeError(Exception):
    """계약 §5 의 안정 code 를 실은 거부.

    호출자는 ``code`` 로 분기한다. 계약 §5: *"호스트는 status/code로 분기하며
    message wording에 의존하지 않는다."* 따라서 ``message`` 는 사람이 읽는
    보조 정보이며 분기 근거가 아니다.
    """

    def __init__(
        self,
        code: str,
        http_status: int,
        message: str,
        details: tuple[Detail, ...] = (),
        supported_schema_versions: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.http_status = http_status
        self.message = message[:_MAX_MESSAGE_CHARS]
        self.details = details[:_MAX_DETAILS]
        self.supported_schema_versions = supported_schema_versions

    def to_envelope(self, request_id: str) -> dict[str, Any]:
        """계약 §3 의 ErrorEnvelope.

        stack trace·token·filesystem 경로를 넣지 않는다 — 그래서 예외 문자열이나
        스키마 검사기의 원문 메시지를 그대로 흘리지 않고, 필드별로 우리가 만든
        문장만 싣는다.
        """
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": [detail.as_dict() for detail in self.details],
            "request_id": request_id,
        }
        # 계약 §5: 버전 거부에**만** required 다.
        if self.supported_schema_versions is not None:
            error["supported_schema_versions"] = list(self.supported_schema_versions)
        return {"error": error}


def _schema_invalid(message: str, details: tuple[Detail, ...] = ()) -> ExchangeError:
    return ExchangeError("SCHEMA_INVALID", 422, message, details)


def _invalid_json(message: str) -> ExchangeError:
    return ExchangeError("INVALID_JSON", 422, message)


@lru_cache(maxsize=1)
def _raw_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=len(MESSAGE_TYPES))
def _validator(message_type: str) -> Draft202012Validator:
    """message_type 에 해당하는 `$defs` 하나에 직접 붙인 validator.

    루트는 다섯의 ``oneOf`` 인데, oneOf 실패는 root 에 "어느 것에도 맞지 않음"
    하나로 뭉쳐 나와 **어느 필드가 문제인지 pointer 가 사라진다.** message_type 으로
    먼저 갈라 해당 정의에 붙이면 leaf pointer 가 그대로 나온다. 검사 내용은 같은
    스키마이므로 단일 원본은 유지된다.
    """
    schema = _raw_schema()
    wrapper = {
        "$schema": schema["$schema"],
        "$ref": f"#/$defs/{message_type}",
        "$defs": schema["$defs"],
    }
    return Draft202012Validator(wrapper, format_checker=FormatChecker())


def _pointer(path: Any) -> str:
    """jsonschema 의 absolute_path 를 RFC6901 JSON Pointer 로.

    ``~`` 와 ``/`` 를 각각 ``~0`` ``~1`` 로 escape 한다 — 안 하면 그런 문자를 담은
    key 에서 pointer 가 다른 자리를 가리킨다.
    """
    parts = []
    for token in path:
        if isinstance(token, int):
            parts.append(str(token))
        else:
            parts.append(str(token).replace("~", "~0").replace("/", "~1"))
    return "".join(f"/{part}" for part in parts)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """중복 key 를 거부한다 (계약 §2 · §9).

    ``json.loads`` 의 기본 동작은 **마지막 값으로 조용히 덮어쓰기**다. 계약은
    중복 key 를 정규화 **전에** 거부하라고 규정하므로 여기서 막는다.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise _schema_invalid(
                "중복된 object key 를 거부합니다.", (Detail(f"/{key}", "duplicate key"),)
            )
        seen.add(key)
    return dict(pairs)


def _reject_non_finite(literal: str) -> Any:
    """NaN · Infinity · -Infinity 를 거부한다 (계약 §2)."""
    raise _schema_invalid(
        "비유한 수는 허용되지 않습니다.", (Detail("", f"non-finite literal: {literal}"),)
    )


def parse_exchange(raw: bytes | str, *, environment: str) -> dict[str, Any]:
    """교환 객체 하나를 엄격히 파싱한다. 실패는 :class:`ExchangeError` 다.

    Args:
        raw: 수신한 그대로의 bytes (또는 str). 중복 key·비유한 수를 잡으려면
            파싱 전 원문이 필요하므로 dict 를 받지 않는다.
        environment: **서버의** deployment 환경 (``synthetic`` 또는 ``production``).
            payload 가 선언한 값과 일치해야 한다.

    Returns:
        검증을 통과한 payload dict.
    """
    # 상한은 **바이트**다. `str` 로 받은 경우 `len()` 은 문자 수를 세므로 한글처럼
    # 다중 바이트 문자에서 상한을 3배까지 통과시킨다 — 경계 검사에 그런 구멍을 두지
    # 않는다. 그래서 str 은 먼저 인코딩해 바이트로 잰다.
    payload_bytes = raw if isinstance(raw, bytes) else raw.encode("utf-8")

    if len(payload_bytes) > MAX_EXCHANGE_BYTES:
        raise ExchangeError(
            "PAYLOAD_TOO_LARGE",
            413,
            f"교환 객체가 상한 {MAX_EXCHANGE_BYTES} bytes 를 넘었습니다.",
        )

    try:
        text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise _invalid_json("UTF-8 로 해석할 수 없는 bytes 입니다.") from None

    try:
        payload = json.loads(
            text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_non_finite
        )
    except ExchangeError:
        raise
    except json.JSONDecodeError as error:
        raise _invalid_json(f"JSON 을 파싱하지 못했습니다: {error.msg}") from None

    if not isinstance(payload, dict):
        raise _schema_invalid(
            "교환 객체는 JSON object 여야 합니다.", (Detail("", "not an object"),)
        )

    # 버전 거부가 다른 사유보다 먼저다 — 구버전 클라이언트에게 무엇을 지원하는지
    # 알려주는 것이 "형식이 틀렸다"보다 실행 가능한 정보다 (계약 §5).
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ExchangeError(
            "UNSUPPORTED_SCHEMA_VERSION",
            422,
            f"지원하지 않는 schema_version 입니다: {version!r}",
            (Detail("/schema_version", f"expected {SCHEMA_VERSION!r}"),),
            supported_schema_versions=(SCHEMA_VERSION,),
        )

    message_type = payload.get("message_type")
    if message_type not in MESSAGE_TYPES:
        raise _schema_invalid(
            f"알 수 없는 message_type 입니다: {message_type!r}",
            (Detail("/message_type", "not one of the five contract exchanges"),),
        )

    # 스키마는 enum 만 알고 서버가 어느 환경인지는 모른다 (계약 §2).
    declared = payload.get("environment")
    if declared != environment:
        raise _schema_invalid(
            "선언된 environment 가 서버 deployment 와 일치하지 않습니다.",
            (Detail("/environment", f"server is {environment!r}, payload says {declared!r}"),),
        )

    errors = sorted(
        _validator(message_type).iter_errors(payload), key=lambda error: list(error.absolute_path)
    )
    if errors:
        details: list[Detail] = []
        for error in errors:
            details.extend(_details_for(error))
        raise _schema_invalid(
            f"{message_type} 이 계약 스키마를 위반했습니다.", tuple(details[:_MAX_DETAILS])
        )

    return payload


def _details_for(error: Any) -> tuple[Detail, ...]:
    """검사기 오류 하나를 ErrorEnvelope detail 로.

    ``additionalProperties`` 위반은 jsonschema 가 **부모 객체 경로**로 보고하므로
    그대로 쓰면 pointer 가 위반한 필드를 가리키지 않는다(closed-world 거부인데
    "어디가" 빠진다). 그 경우에만 위반 key 를 계산해 leaf pointer 를 만든다.

    검사기 원문 메시지는 싣지 않는다 — 값·경로가 새어나갈 수 있어 계약 §3 의
    "stack trace·token·filesystem 을 출력하지 않는다" 에 어긋날 소지가 있다.
    rule 이름만으로 호출자가 분기할 수 있다.
    """
    base = _pointer(error.absolute_path)
    rule = error.validator or "schema"

    if rule == "additionalProperties" and isinstance(error.instance, dict):
        allowed = set(error.schema.get("properties", {}))
        offending = sorted(set(error.instance) - allowed)
        if offending:
            return tuple(
                Detail(
                    f"{base}/{key.replace('~', '~0').replace('/', '~1')}",
                    "unknown field (closed-world)",
                )
                for key in offending
            )

    return (Detail(base, rule),)
