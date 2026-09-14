"""교환 객체 strict parsing (SPEC-LDSTORE-001 M1 · AC-LDPLUGIN-007).

계약(`.moai/specs/SPEC-LDPLUGIN-001/contract.md`) §2 의 공통 wire 규칙과 §5 의 안정
오류 code 를 기계로 고정한다. 이 파일이 지키는 것은 **무엇을 받아들이는가**가 아니라
**무엇을 거절하며 그 사유를 무엇이라 부르는가**다.

계약 §5 마지막 문단: *"호스트는 status/code로 분기하며 message wording에 의존하지
않는다."* 따라서 이 시험도 **code 문자열을 단언**한다 — "거절되었다"만 확인하면
거짓 사유로 먼저 거절되는 경우를 못 잡는다. 거짓 사유와 참 사유는 둘 다 "거절"이라
성공/실패 이분법에 걸리지 않는다.

양성 대조가 이 파일의 절반이다. 전부 거절하는 파서는 아래 거절 시험 전부를
통과시키므로, 계약 §11 의 예제 다섯이 실제로 통과하는지 같은 회차에서 확인한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.director.models import ExchangeError, parse_exchange

_SPEC_DIR = Path(__file__).resolve().parents[2] / ".moai" / "specs" / "SPEC-LDPLUGIN-001"
_EXAMPLES = _SPEC_DIR / "examples"

#: 계약 §2 의 다섯 message_type ↔ §11 의 예제 파일.
_FIVE_EXCHANGES: tuple[tuple[str, str], ...] = (
    ("context_snapshot", "context.json"),
    ("lighting_plan", "plan.json"),
    ("validation_report", "validation.json"),
    ("feedback_record", "feedback.json"),
    ("execution_receipt", "execution.json"),
)

#: 변형 기반(mutation base). 다섯 중 가장 작아 거절 시험이 빠르다.
_MUTATION_BASE = "feedback.json"


def _fixture_bytes(name: str) -> bytes:
    return (_EXAMPLES / name).read_bytes()


def _fixture_dict(name: str) -> dict:
    return json.loads(_fixture_bytes(name))


def _env_of(name: str) -> str:
    """예제가 선언한 environment. 서버 deployment 와 일치해야 통과한다(계약 §2)."""
    return _fixture_dict(name)["environment"]


def _mutated(**changes) -> tuple[bytes, str]:
    """변형 기반을 얕게 고쳐 bytes 로 돌려준다. environment 도 함께 돌려준다."""
    payload = _fixture_dict(_MUTATION_BASE)
    payload.update(changes)
    return json.dumps(payload).encode("utf-8"), _env_of(_MUTATION_BASE)


class TestPositiveControlFiveExchangesParse:
    """양성 대조 — 이것 없이는 아래 거절 시험이 공허하다."""

    @pytest.mark.parametrize(("message_type", "filename"), _FIVE_EXCHANGES)
    def test_contract_example_parses(self, message_type: str, filename: str):
        raw = _fixture_bytes(filename)
        parsed = parse_exchange(raw, environment=_env_of(filename))
        assert parsed["message_type"] == message_type
        assert parsed["schema_version"] == "1.0.0"

    def test_all_five_message_types_are_covered(self):
        """계약 §2 가 정의한 다섯을 하나도 빠뜨리지 않았는지."""
        covered = {message_type for message_type, _ in _FIVE_EXCHANGES}
        assert covered == {
            "context_snapshot",
            "lighting_plan",
            "validation_report",
            "feedback_record",
            "execution_receipt",
        }


class TestSchemaVersionRejection:
    """계약 §5: unknown schema version 에는 supported_schema_versions 가 required."""

    def test_wrong_schema_version_is_unsupported_not_generic_invalid(self):
        raw, env = _mutated(schema_version="1.1.0")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        error = excinfo.value
        assert error.code == "UNSUPPORTED_SCHEMA_VERSION"
        assert error.http_status == 422
        # 이 code 에만 required 다 — 다른 거절에 붙으면 안 된다.
        assert error.supported_schema_versions == ("1.0.0",)

    def test_supported_versions_absent_on_other_rejections(self):
        raw, env = _mutated(message_type="not_a_message_type")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        assert excinfo.value.supported_schema_versions is None


class TestClosedWorldRejection:
    """계약 §2: closed-world. unknown 필드를 무시하지 않는다."""

    def test_unknown_field_is_schema_invalid_with_pointer(self):
        raw, env = _mutated(definitely_not_in_the_contract="x")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        error = excinfo.value
        assert error.code == "SCHEMA_INVALID"
        assert error.http_status == 422
        pointers = [detail.field for detail in error.details]
        assert "/definitely_not_in_the_contract" in pointers

    def test_null_is_rejected_anywhere(self):
        """계약 §2: null 은 어디에서도 사용하지 않는다."""
        raw, env = _mutated(feedback_id=None)
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        assert excinfo.value.code == "SCHEMA_INVALID"

    def test_duplicate_key_is_rejected_before_canonicalization(self):
        """계약 §9: 중복 key 는 JCS 정규화 *전에* 거부한다."""
        raw = b'{"schema_version": "1.0.0", "schema_version": "1.0.0"}'
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment="synthetic")
        assert excinfo.value.code == "SCHEMA_INVALID"


class TestNonFiniteAndEncodingRejection:
    def test_nan_is_rejected(self):
        raw = b'{"schema_version": "1.0.0", "x": NaN}'
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment="synthetic")
        assert excinfo.value.code in {"INVALID_JSON", "SCHEMA_INVALID"}

    def test_infinity_is_rejected(self):
        raw = b'{"schema_version": "1.0.0", "x": Infinity}'
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment="synthetic")
        assert excinfo.value.code in {"INVALID_JSON", "SCHEMA_INVALID"}

    def test_unparseable_json_is_invalid_json(self):
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(b"{not json", environment="synthetic")
        assert excinfo.value.code == "INVALID_JSON"
        assert excinfo.value.http_status == 422

    def test_invalid_utf8_is_rejected(self):
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(b'{"schema_version": "\xff\xfe"}', environment="synthetic")
        assert excinfo.value.code in {"INVALID_JSON", "SCHEMA_INVALID"}


class TestEnvironmentCannotBeDowngraded:
    """계약 §2: 클라이언트가 synthetic 으로 바꾸어 production 안전 검사를 우회할 수 없다."""

    def test_environment_mismatch_is_rejected(self):
        raw, _ = _mutated(environment="synthetic")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment="production")
        assert excinfo.value.code == "SCHEMA_INVALID"

    def test_matching_environment_is_accepted(self):
        """음성 대조의 짝 — 불일치만 거절하고 일치는 통과해야 한다."""
        name = _MUTATION_BASE
        parsed = parse_exchange(_fixture_bytes(name), environment=_env_of(name))
        assert parsed["environment"] == _env_of(name)


class TestErrorEnvelopeShape:
    """계약 §3 의 ErrorEnvelope. stack trace·token·filesystem 을 출력하지 않는다."""

    def test_envelope_has_contract_shape(self):
        raw, env = _mutated(definitely_not_in_the_contract="x")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        envelope = excinfo.value.to_envelope(request_id="req-0001")

        assert set(envelope) == {"error"}
        error = envelope["error"]
        assert set(error) >= {"code", "message", "details", "request_id"}
        assert error["request_id"] == "req-0001"
        assert isinstance(error["details"], list)
        assert len(error["details"]) <= 128
        assert len(error["message"]) <= 4096
        for detail in error["details"]:
            assert set(detail) <= {"field", "rule_id", "message"}
            # field 는 JSON Pointer 또는 빈 문자열.
            assert detail["field"] == "" or detail["field"].startswith("/")

    def test_envelope_leaks_no_paths_or_secrets(self):
        raw, env = _mutated(definitely_not_in_the_contract="x")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        rendered = json.dumps(excinfo.value.to_envelope(request_id="req-0002"))
        for leak in ("Traceback", "/Users/", "/home/", "site-packages", "Bearer "):
            assert leak not in rendered

    def test_supported_versions_key_absent_when_not_a_version_error(self):
        raw, env = _mutated(definitely_not_in_the_contract="x")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        envelope = excinfo.value.to_envelope(request_id="req-0003")
        assert "supported_schema_versions" not in envelope["error"]

    def test_supported_versions_key_present_on_version_error(self):
        raw, env = _mutated(schema_version="9.9.9")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=env)
        envelope = excinfo.value.to_envelope(request_id="req-0004")
        assert envelope["error"]["supported_schema_versions"] == ["1.0.0"]


class TestValidationReachesLeaves:
    """검사가 최상위만 훑고 끝나지 않는지.

    앞의 거절 시험은 전부 최상위 필드를 건드린다. 최상위만 검사하는 구현도 그것들을
    통과시키므로, **깊은 곳의 위반**을 따로 쏘아 pointer 가 leaf 를 가리키는지 본다.
    대조군은 손대지 않은 원본이 통과하는 것이다 (`TestPositiveControl...`).
    """

    def test_deep_id_pattern_violation_reports_leaf_pointer(self):
        payload = _fixture_dict("plan.json")
        payload["cues"][0]["cue_id"] = "!!not-a-valid-id!!"
        raw = json.dumps(payload).encode("utf-8")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=_env_of("plan.json"))
        assert excinfo.value.code == "SCHEMA_INVALID"
        assert "/cues/0/cue_id" in [detail.field for detail in excinfo.value.details]

    def test_deep_unknown_field_reports_leaf_pointer(self):
        payload = _fixture_dict("plan.json")
        payload["cues"][0]["sneaky_field"] = 1
        raw = json.dumps(payload).encode("utf-8")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=_env_of("plan.json"))
        assert excinfo.value.code == "SCHEMA_INVALID"
        assert "/cues/0/sneaky_field" in [detail.field for detail in excinfo.value.details]


class TestSchemaCopyMatchesContract:
    """런타임 사본이 계약의 규범 스키마와 바이트가 같은지.

    제품 코드는 `.moai/specs/` 를 읽지 않는다 — 패키징에 포함되지 않고 SPEC 은
    아카이브된다. 그래서 패키지 안에 사본을 둔다. 사본은 **드리프트가 가능한
    두 번째 파일**이므로 그 동일성을 기계로 고정한다.
    """

    def test_package_copy_is_byte_identical(self):
        normative = (_SPEC_DIR / "schemas" / "exchange.schema.json").read_bytes()
        shipped = (
            Path(__file__).resolve().parents[1] / "director" / "schemas" / "exchange.schema.json"
        ).read_bytes()
        assert shipped == normative


class TestTransportLimits:
    """계약 §2 의 고정 상한. 넘으면 PAYLOAD_TOO_LARGE (413)."""

    def test_over_two_mebibyte_plan_is_payload_too_large(self):
        payload = _fixture_dict(_MUTATION_BASE)
        payload["message_type"] = "lighting_plan"
        payload["padding"] = "p" * (2 * 1024 * 1024 + 1)
        raw = json.dumps(payload).encode("utf-8")
        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(raw, environment=_env_of(_MUTATION_BASE))
        assert excinfo.value.code == "PAYLOAD_TOO_LARGE"
        assert excinfo.value.http_status == 413

    def test_limit_counts_bytes_not_characters(self):
        """상한은 바이트다 — 다중 바이트 문자로 우회할 수 없다.

        `str` 입력에 `len()` 을 쓰면 문자 수를 세므로, 한글 1자 = 3 bytes 에서
        상한을 3배까지 통과시킨다. 경계 검사의 구멍이라 회귀로 고정한다.
        """
        payload = _fixture_dict(_MUTATION_BASE)
        # 문자 수는 상한 이하, 바이트 수는 상한 초과가 되도록 채운다.
        char_count = (2 * 1024 * 1024 // 3) + 1024
        payload["padding"] = "가" * char_count
        as_text = json.dumps(payload, ensure_ascii=False)

        assert len(as_text) < 2 * 1024 * 1024, "문자 수는 상한 이하여야 이 시험이 의미가 있다"
        assert len(as_text.encode("utf-8")) > 2 * 1024 * 1024, "바이트 수는 상한을 넘어야 한다"

        with pytest.raises(ExchangeError) as excinfo:
            parse_exchange(as_text, environment=_env_of(_MUTATION_BASE))
        assert excinfo.value.code == "PAYLOAD_TOO_LARGE"
