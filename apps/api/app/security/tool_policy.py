"""Immutable provider-neutral tool/action allowlist and capability checks."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.security.untrusted_content import SecurityErrorCode, SecurityError


MAX_TOOL_NAME_LENGTH: Final = 64
MAX_ACTION_NAME_LENGTH: Final = 64
MAX_POLICY_ID_LENGTH: Final = 128
MAX_TOOLS: Final = 256
MAX_ACTIONS_PER_TOOL: Final = 64
MAX_SCOPES_PER_TOOL: Final = 64
MAX_REQUEST_PATHS: Final = 16
MAX_PATH_BYTES: Final = 4_096
ROOT_SCOPE: Final = "."

_POLICY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*\Z")
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.\-]*\Z")
_DRIVE_COMPONENT = re.compile(r"[A-Za-z]:")


def _raise(code: SecurityErrorCode, detail: str) -> None:
    raise SecurityError(code, detail)


def validate_repository_relative_path(value: object, label: str = "path") -> str:
    """Canonical repository-relative POSIX path validation; fail closed."""

    if type(value) is not str or not value or value != value.strip():
        _raise(
            SecurityErrorCode.PATH_SCOPE_VIOLATION,
            f"{label} must be a nonempty repository-relative POSIX path",
        )
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, f"{label} contains invalid Unicode")
    if size > MAX_PATH_BYTES:
        _raise(SecurityErrorCode.CONTEXT_BOUND_EXCEEDED, f"{label} exceeds {MAX_PATH_BYTES} bytes")
    if not value.isascii():
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} must be ASCII")
    if "\x00" in value or "\\" in value:
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} contains forbidden separators")
    if any(ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F for character in value):
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} contains control characters")
    if value == ".":
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} may not name the repository root")
    if value.startswith("/") or value.startswith("//"):
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} must not be absolute")
    components = value.split("/")
    if any(component == "" for component in components):
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} must be canonically separated")
    if ".." in components or "." in components:
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} contains traversal components")
    first = components[0]
    if first == "~" or first.startswith("~"):
        _raise(
            SecurityErrorCode.PATH_SCOPE_VIOLATION,
            f"{label} must not use host home-resolution semantics",
        )
    if _DRIVE_COMPONENT.fullmatch(first) is not None:
        _raise(SecurityErrorCode.PATH_SCOPE_VIOLATION, f"{label} must not use drive semantics")
    return value


def _validated_scope_path(value: object, label: str) -> str:
    if type(value) is not str or not value:
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, f"{label} must be a nonempty string")
    if value == ROOT_SCOPE:
        return ROOT_SCOPE
    return validate_repository_relative_path(value, label)


@dataclass(frozen=True, slots=True)
class ToolAuthorizationDecision:
    authorized: bool
    reason: SecurityErrorCode | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ToolActionScope:
    """Trusted-caller-declared authority for exactly one tool."""

    tool_name: str
    actions: tuple[str, ...]
    path_scopes: tuple[str, ...] = ()
    allow_network: bool = False
    allow_command_execution: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _validated_tool_name(self.tool_name))
        object.__setattr__(self, "actions", _validated_actions(self.actions))
        object.__setattr__(self, "path_scopes", _validated_path_scopes(self.path_scopes))
        if type(self.allow_network) is not bool:
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "allow_network must be a bool")
        if type(self.allow_command_execution) is not bool:
            _raise(
                SecurityErrorCode.INVALID_SECURITY_INPUT,
                "allow_command_execution must be a bool",
            )


def _validated_tool_name(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= MAX_TOOL_NAME_LENGTH
        or _NAME.fullmatch(value) is None
    ):
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "tool_name has an invalid form")
    return value


def _validated_actions(values: object) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "actions must be an iterable of names")
    try:
        supplied = tuple(values)  # type: ignore[arg-type]
    except TypeError:
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "actions must be iterable")
    if not supplied or len(supplied) > MAX_ACTIONS_PER_TOOL:
        _raise(
            SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
            f"a tool requires 1..{MAX_ACTIONS_PER_TOOL} actions",
        )
    seen: set[str] = set()
    for value in supplied:
        if (
            type(value) is not str
            or not 1 <= len(value) <= MAX_ACTION_NAME_LENGTH
            or _NAME.fullmatch(value) is None
        ):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "action name has an invalid form")
        if value in seen:
            _raise(
                SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
                "duplicate action name",
            )
        seen.add(value)
    return tuple(sorted(seen))


def _validated_path_scopes(values: object) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "path_scopes must be an iterable")
    try:
        supplied = tuple(values)  # type: ignore[arg-type]
    except TypeError:
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "path_scopes must be iterable")
    if len(supplied) > MAX_SCOPES_PER_TOOL:
        _raise(
            SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
            f"path scope count exceeds {MAX_SCOPES_PER_TOOL}",
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for value in supplied:
        scope = _validated_scope_path(value, "path scope")
        if scope in seen:
            _raise(
                SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
                "duplicate path scope",
            )
        seen.add(scope)
        normalized.append(scope)
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """One concrete tool/action invocation request to be checked, never executed."""

    request_id: str
    tool_name: str
    action: str
    repository_relative_paths: tuple[str, ...] = ()
    requests_network: bool = False
    requests_command_execution: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.request_id) is not str
            or not 1 <= len(self.request_id) <= MAX_POLICY_ID_LENGTH
            or _POLICY_ID.fullmatch(self.request_id) is None
        ):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "request_id has an invalid form")
        if type(self.tool_name) is not str or not self.tool_name:
            _raise(SecurityErrorCode.UNAUTHORIZED_TOOL, "tool_name must be nonempty text")
        if len(self.tool_name.encode("utf-8", errors="replace")) > MAX_TOOL_NAME_LENGTH:
            _raise(SecurityErrorCode.CONTEXT_BOUND_EXCEEDED, "tool_name exceeds its bound")
        if type(self.action) is not str or not self.action:
            _raise(SecurityErrorCode.UNAUTHORIZED_ACTION, "action must be nonempty text")
        if len(self.action.encode("utf-8", errors="replace")) > MAX_ACTION_NAME_LENGTH:
            _raise(SecurityErrorCode.CONTEXT_BOUND_EXCEEDED, "action exceeds its bound")
        if isinstance(self.repository_relative_paths, (str, bytes)):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "paths must be an iterable")
        try:
            paths = tuple(self.repository_relative_paths)  # type: ignore[arg-type]
        except TypeError:
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "paths must be iterable")
        if len(paths) > MAX_REQUEST_PATHS:
            _raise(
                SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
                f"path count exceeds {MAX_REQUEST_PATHS}",
            )
        for path in paths:
            if type(path) is not str:
                _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "paths must contain strings")
            try:
                size = len(path.encode("utf-8"))
            except UnicodeEncodeError:
                _raise(
                    SecurityErrorCode.INVALID_SECURITY_INPUT,
                    "requested path contains invalid Unicode",
                )
            if size > MAX_PATH_BYTES:
                _raise(
                    SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
                    f"requested path exceeds {MAX_PATH_BYTES} bytes",
                )
        object.__setattr__(self, "repository_relative_paths", paths)
        if type(self.requests_network) is not bool:
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "requests_network must be a bool")
        if type(self.requests_command_execution) is not bool:
            _raise(
                SecurityErrorCode.INVALID_SECURITY_INPUT,
                "requests_command_execution must be a bool",
            )


@dataclass(frozen=True, slots=True, init=False)
class ToolPolicy:
    """Immutable allowlist created only from trusted caller policy."""

    _policy_id: str
    _scopes: tuple[ToolActionScope, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        _raise(
            SecurityErrorCode.INVALID_SECURITY_INPUT,
            "ToolPolicy must be created with ToolPolicy.build",
        )

    @classmethod
    def build(cls, policy_id: str, scopes: Iterable[ToolActionScope]) -> ToolPolicy:
        if (
            type(policy_id) is not str
            or not 1 <= len(policy_id) <= MAX_POLICY_ID_LENGTH
            or _POLICY_ID.fullmatch(policy_id) is None
        ):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "policy_id has an invalid form")
        if isinstance(scopes, (str, bytes)):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "scopes must be ToolActionScope values")
        try:
            supplied = tuple(scopes)
        except TypeError:
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "scopes must be iterable")
        if not supplied or len(supplied) > MAX_TOOLS:
            _raise(SecurityErrorCode.CONTEXT_BOUND_EXCEEDED, f"policy requires 1..{MAX_TOOLS} tools")
        seen: set[str] = set()
        for scope in supplied:
            if not isinstance(scope, ToolActionScope):
                _raise(
                    SecurityErrorCode.INVALID_SECURITY_INPUT,
                    "scopes must contain only ToolActionScope values",
                )
            if scope.tool_name in seen:
                _raise(
                    SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
                    "duplicate tool scope",
                )
            seen.add(scope.tool_name)
        ordered = tuple(sorted(supplied, key=lambda scope: scope.tool_name))
        policy = object.__new__(cls)
        object.__setattr__(policy, "_policy_id", policy_id)
        object.__setattr__(policy, "_scopes", ordered)
        return policy

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(scope.tool_name for scope in self._scopes)

    @property
    def content_digest(self) -> str:
        payload = json.dumps(
            [
                {
                    "actions": list(scope.actions),
                    "allow_command_execution": scope.allow_command_execution,
                    "allow_network": scope.allow_network,
                    "path_scopes": list(scope.path_scopes),
                    "tool_name": scope.tool_name,
                }
                for scope in self._scopes
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def scope_for(self, tool_name: str) -> ToolActionScope | None:
        for scope in self._scopes:
            if scope.tool_name == tool_name:
                return scope
        return None

    def authorize(self, request: CapabilityRequest) -> ToolAuthorizationDecision:
        if not isinstance(request, CapabilityRequest):
            _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "request must be a CapabilityRequest")
        scope = self.scope_for(request.tool_name)
        if scope is None:
            return ToolAuthorizationDecision(
                False,
                SecurityErrorCode.UNAUTHORIZED_TOOL,
                "requested tool is not allowed",
            )
        if request.action not in scope.actions:
            return ToolAuthorizationDecision(
                False,
                SecurityErrorCode.UNAUTHORIZED_ACTION,
                "requested action is not allowed",
            )
        if request.repository_relative_paths:
            if not scope.path_scopes:
                return ToolAuthorizationDecision(
                    False,
                    SecurityErrorCode.PATH_SCOPE_VIOLATION,
                    "requested path authority is not granted to this tool",
                )
            for path in request.repository_relative_paths:
                canonical = _validated_request_path(path)
                if canonical is None or not _path_within_scopes(canonical, scope.path_scopes):
                    return ToolAuthorizationDecision(
                        False,
                        SecurityErrorCode.PATH_SCOPE_VIOLATION,
                        "requested path escapes the allowed repository scope",
                    )
        if request.requests_network and not scope.allow_network:
            return ToolAuthorizationDecision(
                False,
                SecurityErrorCode.NETWORK_ESCALATION_REQUEST,
                "network capability is not granted to this tool",
            )
        if request.requests_command_execution and not scope.allow_command_execution:
            return ToolAuthorizationDecision(
                False,
                SecurityErrorCode.COMMAND_EXECUTION_REQUEST,
                "command execution is not granted to this tool",
            )
        return ToolAuthorizationDecision(True, None, None)

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "content_digest": self.content_digest,
                "policy_id": self._policy_id,
                "tools": [scope.tool_name for scope in self._scopes],
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def evaluate_capability_request(
    policy: ToolPolicy, request: CapabilityRequest
) -> ToolAuthorizationDecision:
    if not isinstance(policy, ToolPolicy):
        _raise(SecurityErrorCode.INVALID_SECURITY_INPUT, "policy must be a ToolPolicy")
    return policy.authorize(request)


def _validated_request_path(path: str) -> str | None:
    try:
        return validate_repository_relative_path(path, "requested path")
    except SecurityError:
        return None


def _path_within_scopes(path: str, scopes: tuple[str, ...]) -> bool:
    for scope in scopes:
        if scope == ROOT_SCOPE:
            return True
        if path == scope or path.startswith(f"{scope}/"):
            return True
    return False


__all__ = [
    "MAX_ACTION_NAME_LENGTH",
    "MAX_ACTIONS_PER_TOOL",
    "MAX_PATH_BYTES",
    "MAX_POLICY_ID_LENGTH",
    "MAX_REQUEST_PATHS",
    "MAX_SCOPES_PER_TOOL",
    "MAX_TOOLS",
    "MAX_TOOL_NAME_LENGTH",
    "ROOT_SCOPE",
    "CapabilityRequest",
    "ToolActionScope",
    "ToolAuthorizationDecision",
    "ToolPolicy",
    "evaluate_capability_request",
    "validate_repository_relative_path",
]
