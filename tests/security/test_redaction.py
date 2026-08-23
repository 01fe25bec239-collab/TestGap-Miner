import json
from dataclasses import fields
from pathlib import Path

import pytest

from app.security import (
    MAX_REDACTION_INPUT_BYTES,
    RedactionOutcome,
    RedactionResult,
    SecretFinding,
    SecurityErrorCode,
    redact_text,
    scan_text,
)


CORPUS_PATH = Path(__file__).with_name("fixtures") / "sec002_adversarial.json"
CORPUS_SCHEMA_VERSION = "testgap.sec002-adversarial.v1"
EXFILTRATION_CASE_ID = "SEC002-ATTACK-011-CREDENTIAL-EXFIL"


def load_corpus() -> list[dict[str, object]]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if raw.get("schema_version") != CORPUS_SCHEMA_VERSION:
        pytest.fail("unsupported adversarial corpus schema_version")
    return list(raw["cases"])


def find_case(case_id: str) -> dict[str, object]:
    for case in load_corpus():
        if case["case_id"] == case_id:
            return case
    pytest.fail(f"missing corpus case {case_id}")


SECRET_SAMPLES = [
    ("BEARER_CREDENTIAL", "Authorization: Bearer abc123DEF456ghi789"),
    ("BEARER_CREDENTIAL", "bearer ZZZ999xxx888yyy777"),
    (
        "PRIVATE_KEY_MATERIAL",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA1234\n-----END RSA PRIVATE KEY-----\n",
    ),
    (
        "PRIVATE_KEY_MATERIAL",
        "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNoZWdhemVsbG9maW5pc2g=\n",
    ),
    ("PROVIDER_TOKEN", "token " + "ghp_" + "A" * 36),
    ("PROVIDER_TOKEN", "token " + "gho_" + "B" * 36),
    ("PROVIDER_TOKEN", "token " + "github_pat_" + "C" * 24),
    ("PROVIDER_TOKEN", "slack xoxb-123456789012-987654321098"),
    ("PROVIDER_TOKEN", "key sk-" + "a" * 20),
    ("PROVIDER_TOKEN", "google AIza" + "D" * 35),
    (
        "JWT_SESSION_TOKEN",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    ),
    ("CLOUD_ACCESS_KEY_ID", "aws key AKIAIOSFODNN7EXAMPLE"),
    ("ASSIGNMENT_SECRET", "password=hunter2"),
    ("ASSIGNMENT_SECRET", 'api_key: "abcdef123456"'),
    ("ASSIGNMENT_SECRET", '"client_secret":"zzzzzzzzzz"'),
    ("ASSIGNMENT_SECRET", "access_token=qqqqqqqqqq"),
    ("URL_EMBEDDED_CREDENTIALS", "connect https://alice:s3cretpw@db.example.com/db"),
]


@pytest.mark.parametrize(("expected_kind", "sample"), SECRET_SAMPLES)
def test_every_supported_secret_form_is_detected(
    expected_kind: str, sample: str
) -> None:
    scan = scan_text(sample)
    assert scan.outcome == RedactionOutcome.REDACTED_CLEAN, sample
    assert scan.secrets_detected is True
    assert scan.reason == SecurityErrorCode.SECRET_DETECTED
    kinds = {finding.kind.value for finding in scan.findings}
    assert expected_kind in kinds, (sample, sorted(kinds))


@pytest.mark.parametrize(("expected_kind", "sample"), SECRET_SAMPLES)
def test_redaction_never_returns_raw_secret_bytes(
    expected_kind: str, sample: str
) -> None:
    del expected_kind
    result = redact_text(sample)
    assert isinstance(result, RedactionResult)
    assert result.outcome == RedactionOutcome.REDACTED_CLEAN
    assert result.reason == SecurityErrorCode.SECRET_DETECTED
    assert result.safe_text is not None
    assert "[REDACTED:" in result.safe_text
    for finding in result.findings:
        matched_span = sample[finding.start : finding.end]
        assert matched_span not in result.safe_text
    assert result.safe_text != sample


def test_findings_carry_only_spans_and_kinds() -> None:
    sample = "password=hunter2"
    scan = scan_text(sample)
    assert len(scan.findings) == 1
    finding = scan.findings[0]
    assert isinstance(finding, SecretFinding)
    assert sample[finding.start : finding.end] == "password=hunter2"
    assert tuple(field.name for field in fields(SecretFinding)) == ("kind", "start", "end")


def test_private_key_block_absorbs_inner_assignment_overlap() -> None:
    text = (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\npassword = hunter22\n"
        "-----END RSA PRIVATE KEY-----\n"
    )
    scan = scan_text(text)
    assert len(scan.findings) == 1
    assert scan.findings[0].kind.value == "PRIVATE_KEY_MATERIAL"
    redacted = redact_text(text)
    assert "MIIEpA" not in (redacted.safe_text or "")
    assert "hunter22" not in (redacted.safe_text or "")


def test_multiple_findings_are_ordered_and_all_redacted() -> None:
    text = "Bearer aaa12345bbb and password=hunter2x"
    result = redact_text(text)
    starts = [finding.start for finding in result.findings]
    assert starts == sorted(starts)
    assert len(result.findings) == 2
    kinds = {finding.kind.value for finding in result.findings}
    assert kinds == {"BEARER_CREDENTIAL", "ASSIGNMENT_SECRET"}
    assert "aaa12345bbb" not in (result.safe_text or "")
    assert "hunter2x" not in (result.safe_text or "")
    assert "[REDACTED:BEARER_CREDENTIAL]" in (result.safe_text or "")
    assert "[REDACTED:ASSIGNMENT_SECRET]" in (result.safe_text or "")


@pytest.mark.parametrize(
    "benign",
    [
        "tokenize the corpus before training the ranker",
        "The secret ingredient is flour.",
        "password rules are documented in the handbook",
        "AKIA is the prefix used for access keys",
        "He bears a heavy load today",
        "Run mvn -q verify before review.",
        "",
    ],
)
def test_clean_text_stays_untouched(benign: str) -> None:
    scan = scan_text(benign)
    assert scan.outcome == RedactionOutcome.NO_SECRETS_DETECTED
    assert scan.reason is None
    assert scan.findings == ()
    redacted = redact_text(benign)
    assert redacted.outcome == RedactionOutcome.NO_SECRETS_DETECTED
    assert redacted.safe_text == benign


def test_scanning_is_deterministic() -> None:
    sample = SECRET_SAMPLES[0][1]
    first = scan_text(sample)
    second = scan_text(sample)
    assert first == second
    assert first.findings == second.findings


@pytest.mark.parametrize(
    ("payload", "expected_outcome"),
    [
        (None, RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        (42, RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        (b"raw bytes payload", RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        (["list"], RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        ("\udcffbad surrogate", RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        ("x" * (MAX_REDACTION_INPUT_BYTES + 1), RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED),
        ("safe\x00binary-ish", RedactionOutcome.UNSCANNABLE_CONTENT_BLOCKED),
    ],
)
def test_unscannable_inputs_fail_closed(
    payload: object, expected_outcome: RedactionOutcome
) -> None:
    scan = scan_text(payload)
    assert scan.outcome == expected_outcome
    assert scan.reason == SecurityErrorCode.REDACTION_FAILED
    assert scan.findings == ()
    redacted = redact_text(payload)
    assert redacted.outcome == expected_outcome
    assert redacted.reason == SecurityErrorCode.REDACTION_FAILED
    assert redacted.safe_text is None
    assert redacted.findings == ()


def test_exact_input_bound_is_scannable() -> None:
    boundary = "x" * MAX_REDACTION_INPUT_BYTES
    scan = scan_text(boundary)
    assert scan.outcome == RedactionOutcome.NO_SECRETS_DETECTED


def test_scan_results_never_echo_secret_bytes() -> None:
    sentinel = "SUP3RS3NTINELTOKENVALUE"
    text = f"Authorization: Bearer {sentinel}"
    scan = scan_text(text)
    assert scan.secrets_detected is True
    rendered_result = repr(scan) + str(scan)
    rendered_findings = "".join(repr(finding) for finding in scan.findings)
    combined = rendered_result + rendered_findings
    assert sentinel not in combined
    assert text not in combined


def test_corpus_exfiltration_case_is_detected_and_neutralised() -> None:
    corpus_case = find_case(EXFILTRATION_CASE_ID)
    content = str(corpus_case["content"])
    assert corpus_case["expect_secret_scan_hit"] is True
    scan = scan_text(content)
    assert scan.secrets_detected is True
    kinds = {finding.kind.value for finding in scan.findings}
    assert "PROVIDER_TOKEN" in kinds
    redacted = redact_text(content)
    assert redacted.outcome == RedactionOutcome.REDACTED_CLEAN
    synthetic_token = "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert synthetic_token not in (redacted.safe_text or "")
    assert "[REDACTED:" in (redacted.safe_text or "")
