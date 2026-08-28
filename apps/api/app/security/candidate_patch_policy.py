"""Fail-closed structural policy for model-generated Java test candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from itertools import islice
from typing import Final

from app.security.tool_policy import validate_repository_relative_path
from app.security.untrusted_content import (
    SecurityError,
    SecurityErrorCode,
    UntrustedContentTrust,
    find_hidden_characters,
)


MAX_CHANGES: Final = 64
MAX_CONTENT_BYTES_PER_FILE: Final = 262_144
MAX_TOTAL_CONTENT_BYTES: Final = 1_048_576
MAX_METADATA_ITEMS: Final = 64
MAX_METADATA_KEY_BYTES: Final = 128
MAX_METADATA_VALUE_BYTES: Final = 1_024
MAX_TOTAL_METADATA_BYTES: Final = 16_384
MAX_SCOPE_ENTRIES: Final = 512
MAX_SCOPE_ID_BYTES: Final = 128

_SCOPE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*\Z")
_WINDOWS_DRIVE_PREFIX = re.compile(r"[A-Za-z]:")
_BUILD_NAMES: Final = frozenset(
    {
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradle.properties",
        "gradlew",
        "gradlew.bat",
        "mvnw",
        "mvnw.cmd",
    }
)
_BUILD_DIRECTORIES: Final = frozenset({".gradle", ".mvn"})


class CandidatePatchOperation(StrEnum):
    """Permitted operation types for candidate patch changes."""

    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"
    COPY = "COPY"


class CandidatePatchObjectKind(StrEnum):
    """Object types that may appear in patch candidates."""

    TEXT = "TEXT"
    REGULAR_FILE = "REGULAR_FILE"
    GITLINK = "GITLINK"
    SUBMODULE = "SUBMODULE"


class CandidatePatchPolicyStatus(StrEnum):
    """Policy evaluation outcome status for candidate patches."""

    ALLOWED_TEST_ONLY_CANDIDATE = "ALLOWED_TEST_ONLY_CANDIDATE"
    BLOCKED_POLICY_VIOLATION = "BLOCKED_POLICY_VIOLATION"


class CandidatePatchPolicyReason(StrEnum):
    """Detailed reason codes for policy decisions on candidate patches."""

    ALLOWED = "ALLOWED"
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    MODEL_GENERATED_REQUIRED = "MODEL_GENERATED_REQUIRED"
    INVALID_PATH = "INVALID_PATH"
    OUTSIDE_APPROVED_TEST_SCOPE = "OUTSIDE_APPROVED_TEST_SCOPE"
    NON_JAVA_TEST_CANDIDATE = "NON_JAVA_TEST_CANDIDATE"
    BUILD_OR_DEPENDENCY_MUTATION_DENIED = "BUILD_OR_DEPENDENCY_MUTATION_DENIED"
    WORKFLOW_OR_CONFIGURATION_MUTATION_DENIED = (
        "WORKFLOW_OR_CONFIGURATION_MUTATION_DENIED"
    )
    SUBMODULE_MUTATION_DENIED = "SUBMODULE_MUTATION_DENIED"
    BINARY_OR_UNINSPECTABLE_CONTENT_DENIED = (
        "BINARY_OR_UNINSPECTABLE_CONTENT_DENIED"
    )
    METADATA_BOUND_EXCEEDED = "METADATA_BOUND_EXCEEDED"
    CONTENT_BOUND_EXCEEDED = "CONTENT_BOUND_EXCEEDED"
    CHANGE_COUNT_EXCEEDED = "CHANGE_COUNT_EXCEEDED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNKNOWN_OPERATION = "UNKNOWN_OPERATION"
    DUPLICATE_PATH = "DUPLICATE_PATH"
    CONFLICTING_ACTION = "CONFLICTING_ACTION"
    UNEXPECTED_SOURCE_PATH = "UNEXPECTED_SOURCE_PATH"
    ADD_TARGET_ALREADY_EXISTS = "ADD_TARGET_ALREADY_EXISTS"


@dataclass(frozen=True, slots=True)
class TrustedTestScope:
    """Trusted caller-supplied test authority; never inferred from filenames."""

    scope_id: str
    existing_test_files: tuple[str, ...] = ()
    addable_test_roots: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.scope_id) is not str or _SCOPE_ID.fullmatch(self.scope_id) is None:
            raise SecurityError(
                SecurityErrorCode.INVALID_SECURITY_INPUT, "scope_id has an invalid form"
            )
        try:
            scope_id_size = len(self.scope_id.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise SecurityError(
                SecurityErrorCode.INVALID_SECURITY_INPUT,
                "scope_id contains invalid Unicode",
            ) from error
        if scope_id_size > MAX_SCOPE_ID_BYTES:
            raise SecurityError(
                SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
                f"scope_id exceeds {MAX_SCOPE_ID_BYTES} bytes",
            )

        existing = _bounded_scope_paths(self.existing_test_files, "existing test file")
        roots = _bounded_scope_paths(self.addable_test_roots, "addable test root")
        if not existing and not roots:
            raise SecurityError(
                SecurityErrorCode.INVALID_SECURITY_INPUT,
                "trusted test scope requires at least one authority entry",
            )
        if len(existing) + len(roots) > MAX_SCOPE_ENTRIES:
            raise SecurityError(
                SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
                f"trusted scope entry count exceeds {MAX_SCOPE_ENTRIES}",
            )
        if len(set(existing) | set(roots)) != len(existing) + len(roots):
            raise SecurityError(
                SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
                "duplicate trusted scope path",
            )
        object.__setattr__(self, "existing_test_files", tuple(sorted(existing)))
        object.__setattr__(self, "addable_test_roots", tuple(sorted(roots)))


@dataclass(frozen=True, slots=True)
class CandidatePatchChange:
    """A single file change within a generated test patch candidate."""

    operation: CandidatePatchOperation | str
    target_path: object
    content: object = None
    source_path: object | None = None
    object_kind: CandidatePatchObjectKind | str = CandidatePatchObjectKind.TEXT
    metadata: object = ()


@dataclass(frozen=True, slots=True)
class GeneratedTestPatchCandidate:
    """Model-generated test patch candidate requiring policy evaluation before use."""

    trust_label: object
    changes: object
    metadata: object = ()


@dataclass(frozen=True, slots=True)
class CandidatePatchPolicyDecision:
    """Policy evaluation result for a candidate patch; never grants execution authority."""

    status: CandidatePatchPolicyStatus
    reason: CandidatePatchPolicyReason
    detail: str

    @property
    def allowed(self) -> bool:
        """Return True if the candidate is structurally eligible as a test-only change."""
        return self.status is CandidatePatchPolicyStatus.ALLOWED_TEST_ONLY_CANDIDATE


def _bounded_scope_paths(values: object, label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray, memoryview)):
        raise SecurityError(
            SecurityErrorCode.INVALID_SECURITY_INPUT, f"{label}s must be iterable"
        )
    try:
        supplied = tuple(islice(iter(values), MAX_SCOPE_ENTRIES + 1))  # type: ignore[arg-type]
    except TypeError as error:
        raise SecurityError(
            SecurityErrorCode.INVALID_SECURITY_INPUT, f"{label}s must be iterable"
        ) from error
    if len(supplied) > MAX_SCOPE_ENTRIES:
        raise SecurityError(
            SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
            f"{label} count exceeds {MAX_SCOPE_ENTRIES}",
        )
    validated = tuple(_strict_repository_path(value, label) for value in supplied)
    if len(set(validated)) != len(validated):
        raise SecurityError(
            SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
            f"duplicate {label}",
        )
    return validated


def _blocked(reason: CandidatePatchPolicyReason) -> CandidatePatchPolicyDecision:
    return CandidatePatchPolicyDecision(
        CandidatePatchPolicyStatus.BLOCKED_POLICY_VIOLATION,
        reason,
        "candidate blocked by generated-test patch policy",
    )


def _operation(value: object) -> CandidatePatchOperation | None:
    if type(value) is CandidatePatchOperation:
        return value
    if type(value) is str:
        try:
            return CandidatePatchOperation(value)
        except ValueError:
            return None
    return None


def _object_kind(value: object) -> CandidatePatchObjectKind | None:
    if type(value) is CandidatePatchObjectKind:
        return value
    if type(value) is str:
        try:
            return CandidatePatchObjectKind(value)
        except ValueError:
            return None
    return None


def _metadata_measure(
    value: object,
) -> tuple[CandidatePatchPolicyReason | None, int, int]:
    if type(value) is not tuple:
        return CandidatePatchPolicyReason.INVALID_CANDIDATE, 0, 0
    if len(value) > MAX_METADATA_ITEMS:
        return CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED, 0, 0

    total = 0
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            return CandidatePatchPolicyReason.INVALID_CANDIDATE, 0, 0
        key, metadata_value = item
        if type(key) is not str or type(metadata_value) is not str:
            return CandidatePatchPolicyReason.INVALID_CANDIDATE, 0, 0
        try:
            key_size = len(key.encode("utf-8"))
            value_size = len(metadata_value.encode("utf-8"))
        except UnicodeEncodeError:
            return CandidatePatchPolicyReason.INVALID_CANDIDATE, 0, 0
        total += key_size + value_size
        if (
            key_size > MAX_METADATA_KEY_BYTES
            or value_size > MAX_METADATA_VALUE_BYTES
            or total > MAX_TOTAL_METADATA_BYTES
        ):
            return CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED, 0, 0
    return None, len(value), total


def _strict_repository_path(value: object, label: str) -> str:
    path = validate_repository_relative_path(value, label)
    if _WINDOWS_DRIVE_PREFIX.match(path.split("/", 1)[0]) is not None:
        raise SecurityError(
            SecurityErrorCode.PATH_SCOPE_VIOLATION,
            f"{label} must not use drive semantics",
        )
    return path


def _path_reason(path: object) -> tuple[str | None, CandidatePatchPolicyReason | None]:
    try:
        return _strict_repository_path(path, "candidate path"), None
    except SecurityError:
        return None, CandidatePatchPolicyReason.INVALID_PATH


def _forbidden_path_reason(path: str) -> CandidatePatchPolicyReason | None:
    components = path.split("/")
    if ".gitmodules" in components:
        return CandidatePatchPolicyReason.SUBMODULE_MUTATION_DENIED
    if any(part in _BUILD_NAMES or part in _BUILD_DIRECTORIES for part in components):
        return CandidatePatchPolicyReason.BUILD_OR_DEPENDENCY_MUTATION_DENIED
    if components[0] == ".github":
        return CandidatePatchPolicyReason.WORKFLOW_OR_CONFIGURATION_MUTATION_DENIED
    return None


def _under(path: str, root: str) -> bool:
    return path.startswith(f"{root}/")


def evaluate_generated_test_patch_candidate(
    trusted_test_scope: TrustedTestScope,
    generated_candidate: GeneratedTestPatchCandidate,
) -> CandidatePatchPolicyDecision:
    """Return structural eligibility only; never apply or execute a candidate."""

    if type(trusted_test_scope) is not TrustedTestScope:
        return _blocked(CandidatePatchPolicyReason.INVALID_CANDIDATE)
    if type(generated_candidate) is not GeneratedTestPatchCandidate:
        return _blocked(CandidatePatchPolicyReason.INVALID_CANDIDATE)
    if generated_candidate.trust_label is not UntrustedContentTrust.MODEL_GENERATED:
        return _blocked(CandidatePatchPolicyReason.MODEL_GENERATED_REQUIRED)

    if type(generated_candidate.changes) is not tuple:
        return _blocked(CandidatePatchPolicyReason.INVALID_CANDIDATE)
    if len(generated_candidate.changes) > MAX_CHANGES:
        return _blocked(CandidatePatchPolicyReason.CHANGE_COUNT_EXCEEDED)
    changes = tuple(generated_candidate.changes)
    if not changes:
        return _blocked(CandidatePatchPolicyReason.INVALID_CANDIDATE)

    validated: list[tuple[CandidatePatchChange, str, CandidatePatchOperation | None]] = []
    for change in changes:
        if type(change) is not CandidatePatchChange:
            return _blocked(CandidatePatchPolicyReason.INVALID_CANDIDATE)

        target, path_reason = _path_reason(change.target_path)
        if path_reason is not None:
            return _blocked(path_reason)
        assert target is not None

        operation = _operation(change.operation)
        if operation in (CandidatePatchOperation.RENAME, CandidatePatchOperation.COPY):
            _, source_reason = _path_reason(change.source_path)
            if source_reason is not None:
                return _blocked(source_reason)
        elif operation in (CandidatePatchOperation.ADD, CandidatePatchOperation.MODIFY):
            if change.source_path is not None:
                return _blocked(CandidatePatchPolicyReason.UNEXPECTED_SOURCE_PATH)
        validated.append((change, target, operation))

    metadata_reason, total_metadata_items, total_metadata_bytes = _metadata_measure(
        generated_candidate.metadata
    )
    if metadata_reason is not None:
        return _blocked(metadata_reason)

    seen: dict[str, CandidatePatchOperation | None] = {}
    total_content_bytes = 0
    for change, target, operation in validated:
        prior = seen.get(target)
        if target in seen:
            reason = (
                CandidatePatchPolicyReason.DUPLICATE_PATH
                if prior is operation
                else CandidatePatchPolicyReason.CONFLICTING_ACTION
            )
            return _blocked(reason)
        seen[target] = operation

        forbidden_reason = _forbidden_path_reason(target)
        if forbidden_reason is not None:
            return _blocked(forbidden_reason)

        kind = _object_kind(change.object_kind)
        if kind in (CandidatePatchObjectKind.GITLINK, CandidatePatchObjectKind.SUBMODULE):
            return _blocked(CandidatePatchPolicyReason.SUBMODULE_MUTATION_DENIED)
        if kind not in (CandidatePatchObjectKind.TEXT, CandidatePatchObjectKind.REGULAR_FILE):
            return _blocked(
                CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED
            )

        if operation is None:
            return _blocked(CandidatePatchPolicyReason.UNKNOWN_OPERATION)
        if operation not in (CandidatePatchOperation.ADD, CandidatePatchOperation.MODIFY):
            return _blocked(CandidatePatchPolicyReason.UNSUPPORTED_OPERATION)

        if not target.endswith(".java"):
            return _blocked(CandidatePatchPolicyReason.NON_JAVA_TEST_CANDIDATE)
        if operation is CandidatePatchOperation.MODIFY:
            if target not in trusted_test_scope.existing_test_files:
                return _blocked(CandidatePatchPolicyReason.OUTSIDE_APPROVED_TEST_SCOPE)
        else:
            if target in trusted_test_scope.existing_test_files:
                return _blocked(CandidatePatchPolicyReason.ADD_TARGET_ALREADY_EXISTS)
            if not any(_under(target, root) for root in trusted_test_scope.addable_test_roots):
                return _blocked(CandidatePatchPolicyReason.OUTSIDE_APPROVED_TEST_SCOPE)

        if type(change.content) is not str:
            return _blocked(
                CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED
            )
        try:
            content_size = len(change.content.encode("utf-8"))
        except UnicodeEncodeError:
            return _blocked(
                CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED
            )
        total_content_bytes += content_size
        if (
            content_size > MAX_CONTENT_BYTES_PER_FILE
            or total_content_bytes > MAX_TOTAL_CONTENT_BYTES
        ):
            return _blocked(CandidatePatchPolicyReason.CONTENT_BOUND_EXCEEDED)
        try:
            hidden_characters = find_hidden_characters(change.content)
        except Exception:
            return _blocked(
                CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED
            )
        if hidden_characters:
            return _blocked(
                CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED
            )

        metadata_reason, metadata_items, metadata_bytes = _metadata_measure(change.metadata)
        if metadata_reason is not None:
            return _blocked(metadata_reason)
        total_metadata_items += metadata_items
        total_metadata_bytes += metadata_bytes
        if (
            total_metadata_items > MAX_METADATA_ITEMS
            or total_metadata_bytes > MAX_TOTAL_METADATA_BYTES
        ):
            return _blocked(CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED)

    return CandidatePatchPolicyDecision(
        CandidatePatchPolicyStatus.ALLOWED_TEST_ONLY_CANDIDATE,
        CandidatePatchPolicyReason.ALLOWED,
        "structurally eligible as a test-only candidate; no execution authority granted",
    )


__all__ = [
    "MAX_CHANGES",
    "MAX_CONTENT_BYTES_PER_FILE",
    "MAX_METADATA_ITEMS",
    "MAX_METADATA_KEY_BYTES",
    "MAX_METADATA_VALUE_BYTES",
    "MAX_SCOPE_ENTRIES",
    "MAX_SCOPE_ID_BYTES",
    "MAX_TOTAL_CONTENT_BYTES",
    "MAX_TOTAL_METADATA_BYTES",
    "CandidatePatchChange",
    "CandidatePatchObjectKind",
    "CandidatePatchOperation",
    "CandidatePatchPolicyDecision",
    "CandidatePatchPolicyReason",
    "CandidatePatchPolicyStatus",
    "GeneratedTestPatchCandidate",
    "TrustedTestScope",
    "evaluate_generated_test_patch_candidate",
]
