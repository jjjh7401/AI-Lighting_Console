"""digest 계산 (SPEC-LDSTORE-001 M1 · 계약 §9).

계약 §9: *"모든 JSON digest 는 `sha256(UTF-8(RFC8785/JCS(value)))` 를
`sha256:<hex>` 로 표시한다."*

digest 는 **외부 플러그인이 같은 값을 계산해야 하는 wire 계약**이다. 근사 구현은
조용히 어긋나고, 어긋나면 정상 계획이 거부된다. 그래서 이 시험은 계약이 §9 의
"합성 예제 digest 재현 규칙" 으로 직접 제공한 **시험 벡터**에 대고 잰다 — 우리가
만든 기대값이 아니라 계약이 규정한 값이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.director.digest import canonical_digest, context_digest, raw_digest

_EXAMPLES = (
    Path(__file__).resolve().parents[2] / ".moai" / "specs" / "SPEC-LDPLUGIN-001" / "examples"
)

#: 계약 §9 "합성 예제 digest 재현 규칙" 의 규범 bytes. 문자열과 끝의 LF 하나까지 그대로다.
_AUDIO_FIXTURE_BYTES = b"Lighting Director synthetic audio fixture v1\n"
_COMPILER_FIXTURE_BYTES = b"Lighting Director synthetic compiler fixture v1\n"


def _example(name: str) -> dict:
    return json.loads((_EXAMPLES / name).read_text(encoding="utf-8"))


class TestRawBytesDigest:
    """계약 §9: raw bytes digest 에는 JCS 를 적용하지 않는다."""

    def test_audio_fixture_matches_the_declared_context_value(self):
        """계약이 규정한 audio fixture bytes → 예제의 audio.sha256."""
        declared = _example("context.json")["audio"]["sha256"]
        assert raw_digest(_AUDIO_FIXTURE_BYTES) == declared

    def test_compiler_fixture_matches_the_declared_build_digest(self):
        declared = _example("context.json")["compiler"]["build_digest"]
        assert raw_digest(_COMPILER_FIXTURE_BYTES) == declared

    def test_digest_has_contract_shape(self):
        value = raw_digest(b"")
        assert value.startswith("sha256:")
        hex_part = value.removeprefix("sha256:")
        assert len(hex_part) == 64
        assert hex_part == hex_part.lower()


class TestContextDigest:
    """계약 §9.1: ContextSnapshot 전체에서 **최상위 context_digest key 하나만** 제거."""

    def test_reproduces_the_contract_example_digest(self):
        snapshot = _example("context.json")
        declared = snapshot["context_digest"]
        assert context_digest(snapshot) == declared

    def test_nested_content_digests_are_not_removed(self):
        """§9.1: *"nested content_digest 등은 제거하지 않는다."*

        preset 의 content_digest 를 바꾸면 context_digest 도 바뀌어야 한다. 안 바뀌면
        중첩 digest 를 제거하고 있다는 뜻이고, 그러면 preset 내용 변경이 승인을
        무효화하지 못한다 — AC-LDPLUGIN-004 가 요구하는 안전 장치에 구멍이 난다.
        """
        snapshot = _example("context.json")
        before = context_digest(snapshot)
        snapshot["presets"][0]["content_digest"] = "sha256:" + "0" * 64
        assert context_digest(snapshot) != before

    def test_every_axis_change_moves_the_digest(self):
        """아홉 축 중 어느 것이 바뀌어도 digest 가 움직여야 한다 (AC-LDPLUGIN-004).

        일부 축만 digest 에 넣으면 나머지 축이 바뀌어도 이전 승인이 유효하게 남는다.
        축을 하나씩 건드려 전부 digest 를 움직이는지 확인한다.
        """
        baseline = context_digest(_example("context.json"))
        mutations = {
            "audio": lambda s: s["audio"].__setitem__("duration_ms", s["audio"]["duration_ms"] + 1),
            "show": lambda s: s.__setitem__("show_revision", s["show_revision"] + 1),
            "group membership": lambda s: s["groups"][0].__setitem__(
                "membership_revision", s["groups"][0]["membership_revision"] + 1
            ),
            "preset content": lambda s: s["presets"][0].__setitem__(
                "content_revision", s["presets"][0]["content_revision"] + 1
            ),
            "compiler": lambda s: s["compiler"].__setitem__("version", "changed"),
            "capability": lambda s: s.__setitem__(
                "capability_revision", s["capability_revision"] + 1
            ),
            "policy": lambda s: s.__setitem__(
                "safety_policy_revision", s["safety_policy_revision"] + 1
            ),
            "identity": lambda s: s["target"].__setitem__("identity_status", "unreadable"),
            "expiry": lambda s: s.__setitem__("expires_at", "2099-01-01T00:00:00Z"),
        }
        unmoved = []
        for axis, mutate in mutations.items():
            snapshot = _example("context.json")
            mutate(snapshot)
            if context_digest(snapshot) == baseline:
                unmoved.append(axis)
        assert unmoved == [], f"digest 가 움직이지 않은 축: {unmoved}"

    def test_destination_occupancy_change_moves_the_digest(self):
        """AC-LDPLUGIN-004 가 명시적으로 든 케이스 — destination occupancy."""
        snapshot = _example("context.json")
        before = context_digest(snapshot)
        destination = snapshot["target"]["destination"]
        destination["occupancy_revision"] = destination["occupancy_revision"] + 1
        assert context_digest(snapshot) != before


class TestCanonicalDigestIsJcsNotAnApproximation:
    """stdlib json 근사와 갈리는 지점을 고정한다.

    이 시험이 존재하는 이유: `json.dumps(sort_keys=True, separators=(',',':'))` 는
    계약의 예제 digest 를 **우연히 재현한다**(예제의 float 7개가 전부 정수값이 아니라서).
    그러나 JCS 가 아니다 — 정수값 float 에서 갈린다. 그 차이를 시험으로 남겨두지 않으면
    누군가 의존성을 걷어내고 stdlib 로 되돌리면서 조용히 wire 를 깬다.
    """

    def test_integral_float_serializes_without_trailing_zero(self):
        """JCS: 정수값 float 은 `1` 이다. stdlib json 은 `1.0` 을 쓴다."""
        as_float = canonical_digest({"x": 1.0})
        as_int = canonical_digest({"x": 1})
        assert as_float == as_int, "JCS 는 1.0 과 1 을 같게 직렬화한다"

        stdlib_bytes = json.dumps({"x": 1.0}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        assert raw_digest(stdlib_bytes) != as_float, (
            "stdlib json 이 JCS 와 같은 결과를 낸다면 이 시험의 전제가 사라진 것이다"
        )

    def test_key_order_does_not_matter(self):
        """계약 §9: object key 순서는 의미 없다."""
        assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})

    def test_array_order_does_matter(self):
        """계약 §9: array 순서는 유지한다."""
        assert canonical_digest({"a": [1, 2]}) != canonical_digest({"a": [2, 1]})

    def test_whitespace_does_not_matter(self):
        """계약 §9: 예쁜 출력·공백은 무관하다."""
        compact = json.loads('{"a":1,"b":[2,3]}')
        pretty = json.loads('{\n  "a" : 1,\n  "b" : [ 2, 3 ]\n}')
        assert canonical_digest(compact) == canonical_digest(pretty)

    def test_non_ascii_is_not_normalized(self):
        """계약 §9: *"별도 Unicode normalization 을 하지 않는다."*

        NFC 와 NFD 로 표기가 다른 같은 글자는 **다른** digest 를 내야 한다.
        정규화하면 두 표기가 같아져 계약을 어긴다.
        """
        nfc = {"label": "가"}  # 가 (조합 완성형)
        nfd = {"label": "가"}  # ㄱ + ㅏ (조합형)
        assert canonical_digest(nfc) != canonical_digest(nfd)


class TestPlanDigestScope:
    """계약 §9.2: 제출된 LightingPlan 전체. envelope·서버 metadata 는 제외."""

    def test_reproduces_the_contract_example_plan_digest(self):
        from server.director.digest import plan_digest

        plan = _example("plan.json")
        declared = _example("validation.json")["plan_digest"]
        assert plan_digest(plan) == declared

    def test_base_revision_is_included(self):
        """§9.2: *"base_revision·provenance·rationale 도 포함한다."*"""
        from server.director.digest import plan_digest

        plan = _example("plan.json")
        before = plan_digest(plan)
        plan["base_revision"] = plan["base_revision"] + 1
        assert plan_digest(plan) != before

    def test_envelope_fields_are_rejected_not_silently_ignored(self):
        """envelope 필드가 섞여 들어오면 조용히 무시하지 않는다.

        §9.2 는 `expected_revision`/`idempotency_key` 를 digest 대상에서 제외한다.
        그러나 그것들은 애초에 plan 안에 있으면 안 되는 필드다(계약 §3 의 envelope).
        조용히 걸러내면 잘못된 제출이 성공으로 보인다.
        """
        from server.director.digest import plan_digest

        plan = _example("plan.json")
        plan["expected_revision"] = 1
        with pytest.raises(ValueError):
            plan_digest(plan)
