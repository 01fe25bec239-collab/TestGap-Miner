"""Deterministic secret detection and redaction-safe derived text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.security.untrusted_content import SecurityErrorCode


MAX_REDACTION_INPUT_BYTES: Final = 262_144


class RedactionOutcome(StrEnum):
    NO_SECRETS_DETECTED = "NO_SECRETS_DETECTED"
    REDACTED_CLEAN = "REDACTED_CLEAN"
    REDACTION_FAILED_FAIL_CLOSED = "REDACTION_FAILED_FAIL_CLOSED"
    UNSCANNABLE_CONTENT_BLOCKED = "UNSCANNABLE_CONTENT_BLOCKED"


class SecretKind(StrEnum):
    BEARER_CREDENTIAL = "BEARER_CREDENTIAL"
    PRIVATE_KEY_MATERIAL = "PRIVATE_KEY_MATERIAL"
    PROVIDER_TOKEN = "PROVIDER_TOKEN"
    JWT_SESSION_TOKEN = "JWT_SESSION_TOKEN"
    CLOUD_ACCESS_KEY_ID = "CLOUD_ACCESS_KEY_ID"
    ASSIGNMENT_SECRET = "ASSIGNMENT_SECRET"
    URL_EMBEDDED_CREDENTIALS = "URL_EMBEDDED_CREDENTIALS"


@dataclass(frozen=True, slots=True)
class SecretFinding:
    kind: SecretKind
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SecretScanResult:
    outcome: RedactionOutcome
    reason: SecurityErrorCode | None
    findings: tuple[SecretFinding, ...]

    @property
    def secrets_detected(self) -> bool:
        return bool(self.findings)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    outcome: RedactionOutcome
    reason: SecurityErrorCode | None
    safe_text: str | None
    findings: tuple[SecretFinding, ...]

    @property
    def secrets_detected(self) -> bool:
        return bool(self.findings)


def _bearer() -> re.Pattern[str]:
    return re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")


def _private_key_block() -> re.Pattern[str]:
    return re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----.*?"
        r"(-----END [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----|\Z)",
        re.DOTALL,
    )


def _provider_token() -> re.Pattern[str]:
    alternatives = (
        r"\bgh[pousr]_[A-Za-z0-9]{16,}\b",
        r"\bgithub_pat_[A-Za-z0-9_]{20,}\b",
        r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b",
        r"\bsk-[A-Za-z0-9_\-]{16,}\b",
        r"\bAIza[0-9A-Za-z_\-]{35}\b",
    )
    return re.compile("|".join(alternatives))


def _jwt() -> re.Pattern[str]:
    return re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")


def _cloud_access_key() -> re.Pattern[str]:
    return re.compile(r"\bAKIA[0-9A-Z]{16}\b")


def _assignment_secret() -> re.Pattern[str]:
    names = (
        r"password",
        r"passwd",
        r"pwd",
        r"api[_\-]?key",
        r"apikey",
        r"secret",
        r"access[_\-]?token",
        r"refresh[_\-]?token",
        r"client[_\-]?secret",
        r"private[_\-]?key",
    )
    value = r"(?:\"[^\"]{6,}\"|'[^']{6,}'|[^\s\"'`]{6,})"
    return re.compile(
        r"(?i)\b("
        + "|".join(names)
        + r")(?:[_\-][A-Za-z0-9_\-]{0,20})?[\"']?\s*[:=]\s*"
        + value
    )


def _url_credentials() -> re.Pattern[str]:
    return re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s/:@]+:[^\s/@]+@[A-Za-z0-9]")


_PATTERNS: Final[tuple[tuple[SecretKind, re.Pattern[str]], ...]] = (
    (SecretKind.PRIVATE_KEY_MATERIAL, _private_key_block()),
    (SecretKind.BEARER_CREDENTIAL, _bearer()),
    (SecretKind.PROVIDER_TOKEN, _provider_token()),
    (SecretKind.JWT_SESSION_TOKEN, _jwt()),
    (SecretKind.CLOUD_ACCESS_KEY_ID, _cloud_access_key()),
    (SecretKind.ASSIGNMENT_SECRET, _assignment_secret()),
    (SecretKind.URL_EMBEDDED_CREDENTIALS, _url_credentials()),
)

_REDACTED_TOKEN_PREFIX: Final = "[REDACTED:"


def scan_text(text: object) -> SecretScanResult:
    """Scan one bounded text unit; findings carry spans only, never bytes."""

    prepared = _prepared_scan(text)
    if isinstance(prepared, RedactionOutcome):
        if prepared == RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED:
            return SecretScanResult(prepared, SecurityErrorCode.REDACTION_FAILED, ())
        return SecretScanResult(prepared, SecurityErrorCode.REDACTION_FAILED, ())
    findings = _collect_findings(prepared)
    outcome = (
        RedactionOutcome.REDACTED_CLEAN if findings else RedactionOutcome.NO_SECRETS_DETECTED
    )
    reason = SecurityErrorCode.SECRET_DETECTED if findings else None
    return SecretScanResult(outcome, reason, findings)


def redact_text(text: object) -> RedactionResult:
    """Return a derived model/log-safe representation; raw input is untouched."""

    prepared = _prepared_scan(text)
    if isinstance(prepared, RedactionOutcome):
        return RedactionResult(prepared, SecurityErrorCode.REDACTION_FAILED, None, ())
    findings = _collect_findings(prepared)
    if not findings:
        return RedactionResult(
            RedactionOutcome.NO_SECRETS_DETECTED, None, prepared, ()
        )
    pieces: list[str] = []
    cursor = 0
    for finding in findings:
        pieces.append(prepared[cursor : finding.start])
        pieces.append(f"{_REDACTED_TOKEN_PREFIX}{finding.kind.value}]")
        cursor = finding.end
    pieces.append(prepared[cursor:])
    return RedactionResult(
        RedactionOutcome.REDACTED_CLEAN,
        SecurityErrorCode.SECRET_DETECTED,
        "".join(pieces),
        findings,
    )


def _prepared_scan(text: object) -> str | RedactionOutcome:
    if type(text) is not str:
        return RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        return RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED
    if size > MAX_REDACTION_INPUT_BYTES:
        return RedactionOutcome.REDACTION_FAILED_FAIL_CLOSED
    if "\x00" in text:
        return RedactionOutcome.UNSCANNABLE_CONTENT_BLOCKED
    return text


def _collect_findings(content: str) -> tuple[SecretFinding, ...]:
    candidates: list[tuple[int, int, str, SecretFinding]] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(content):
            finding = SecretFinding(kind=kind, start=match.start(), end=match.end())
            candidates.append((finding.start, -(finding.end - finding.start), kind.value, finding))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    selected: list[SecretFinding] = []
    last_end = -1
    for _, _, _, finding in candidates:
        if finding.start < last_end:
            continue
        selected.append(finding)
        last_end = finding.end
    return tuple(selected)


__all__ = [
    "MAX_REDACTION_INPUT_BYTES",
    "RedactionOutcome",
    "RedactionResult",
    "SecretFinding",
    "SecretKind",
    "SecretScanResult",
    "redact_text",
    "scan_text",
]
