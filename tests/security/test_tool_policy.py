import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.security import (
    MAX_REQUEST_PATHS,
    MAX_TOOLS,
    CapabilityRequest,
    SecurityError,
    SecurityErrorCode,
    ToolActionScope,
    ToolPolicy,
    evaluate_capability_request,
)


CORPUS_PATH = Path(__file__).with_name("fixtures") / "sec002_adversarial.json"
CORPUS_SCHEMA_VERSION = "testgap.sec002-adversarial.v1"
ANTI_KEYWORD_CASE_ID = "SEC002-BENIGN-005-ANTI-KEYWORD-DECOY"


def load_corpus() -> list[dict[str, object]]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if raw.get("schema_version") != CORPUS_SCHEMA_VERSION:
        pytest.fail("unsupported adversarial corpus schema_version")
    return list(raw["cases"])


def corpus_category(category: str) -> list[dict[str, object]]:
    return [case for case in load_corpus() if case["category"] == category]


def find_case(case_id: str) -> dict[str, object]:
    for case in load_corpus():
        if case["case_id"] == case_id:
            return case
    pytest.fail(f"missing corpus case {case_id}")


def default_policy() -> ToolPolicy:
    return ToolPolicy.build(
        "policy-default",
        (
            ToolActionScope(
                tool_name="file_read",
                actions=("read", "list"),
                path_scopes=("src",),
            ),
            ToolActionScope(
                tool_name="net_fetch",
                actions=("fetch",),
                path_scopes=("reports",),
                allow_network=True,
            ),
            ToolActionScope(
                tool_name="runner",
                actions=("execute",),
                path_scopes=("src",),
                allow_command_execution=True,
            ),
            ToolActionScope(tool_name="clock", actions=("now",)),
        ),
    )


def request(**overrides: object) -> CapabilityRequest:
    values: dict[str, object] = {
        "request_id": "request-1",
        "tool_name": "file_read",
        "action": "read",
        "repository_relative_paths": (),
        "requests_network": False,
        "requests_command_execution": False,
    }
    if "paths" in overrides:
        overrides["repository_relative_paths"] = overrides.pop("paths")
    values.update(overrides)
    return CapabilityRequest(**values)  # type: ignore[arg-type]


def assert_error(code: SecurityErrorCode, operation) -> None:
    with pytest.raises(SecurityError) as raised:
        operation()
    assert raised.value.code == code


def deny(policy: ToolPolicy, req: CapabilityRequest) -> SecurityErrorCode:
    decision = policy.authorize(req)
    assert decision.authorized is False
    assert decision.reason is not None
    return decision.reason


def test_allowlist_is_created_only_from_typed_trusted_policy_objects() -> None:
    policy = default_policy()
    assert policy.tools == ("clock", "file_read", "net_fetch", "runner")
    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: ToolPolicy.build(
            "policy-bad",
            ({"tool_name": "shell_exec", "actions": ["run"]},),  # type: ignore[list-item]
        ),
    )
    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: ToolPolicy.build("policy-bad", ("file_read",)),  # type: ignore[list-item]
    )
    assert_error(SecurityErrorCode.INVALID_SECURITY_INPUT, lambda: ToolPolicy())


def test_direct_tool_policy_instantiation_fails_closed() -> None:
    assert_error(SecurityErrorCode.INVALID_SECURITY_INPUT, lambda: ToolPolicy())
    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: ToolPolicy.build("bad id!", (ToolActionScope("tool_a", ("act",)),)),
    )


def test_duplicate_tools_fail_closed() -> None:
    assert_error(
        SecurityErrorCode.DUPLICATE_SECURITY_IDENTITY,
        lambda: ToolPolicy.build(
            "policy-dup",
            (
                ToolActionScope("same_tool", ("a",)),
                ToolActionScope("same_tool", ("b",)),
            ),
        ),
    )


def test_policy_size_bounds_fail_closed() -> None:
    oversized = tuple(
        ToolActionScope(f"tool_{index}", ("act",)) for index in range(MAX_TOOLS + 1)
    )
    assert_error(
        SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
        lambda: ToolPolicy.build("policy-big", oversized),
    )


@pytest.mark.parametrize(
    "scope_factory",
    [
        lambda: ToolActionScope("bad name", ("act",)),
        lambda: ToolActionScope("", ("act",)),
        lambda: ToolActionScope("tool_a", ()),
        lambda: ToolActionScope("tool_a", ("bad action",)),
        lambda: ToolActionScope("tool_a", ("act", "act")),
        lambda: ToolActionScope("tool_a", ("act",), path_scopes=("../escape",)),
        lambda: ToolActionScope("tool_a", ("act",), path_scopes=("src//x",)),
        lambda: ToolActionScope("tool_a", ("act",), path_scopes=("/absolute",)),
        lambda: ToolActionScope("tool_a", ("act",), path_scopes="src"),  # type: ignore[arg-type]
        lambda: ToolActionScope("tool_a", ("act",), allow_network="yes"),  # type: ignore[arg-type]
        lambda: ToolActionScope("tool_a", ("act",), allow_command_execution=1),  # type: ignore[arg-type]
    ],
)
def test_malformed_scopes_fail_closed(scope_factory) -> None:
    with pytest.raises(SecurityError):
        scope_factory()


def test_root_scope_grants_repository_wide_relative_authority() -> None:
    policy = ToolPolicy.build(
        "policy-root",
        (ToolActionScope("file_read", ("read",), path_scopes=(".",)),),
    )
    assert policy.authorize(request(paths=("any/where/file.txt",))).authorized is True
    assert (
        deny(policy, request(paths=("/etc/passwd",)))
        == SecurityErrorCode.PATH_SCOPE_VIOLATION
    )


@pytest.mark.parametrize(
    ("tool_name", "action"),
    [("ghost_tool", "read"), ("shell_exec", "run"), ("net_fetch", "post")],
)
def test_unlisted_tools_and_actions_are_denied(tool_name: str, action: str) -> None:
    policy = default_policy()
    expected = (
        SecurityErrorCode.UNAUTHORIZED_ACTION
        if tool_name in {"net_fetch"}
        else SecurityErrorCode.UNAUTHORIZED_TOOL
    )
    assert deny(policy, request(tool_name=tool_name, action=action)) == expected


@pytest.mark.parametrize(
    "hostile_path",
    [
        "../secrets.txt",
        "../../../../../etc/shadow",
        "/etc/passwd",
        "//double/slash",
        "src//nested.py",
        "src/",
        "./src/app.py",
        "src/./app.py",
        "src/../secret.py",
        "..",
        ".",
        "src\\evil.py",
        "\\\\host\\share\\file",
        "C:/Windows/system32/config",
        "~/private/key.pem",
        "~root/pwned",
        "src/\nnewline.py",
        "src/\tnested.py",
        "src/\x00null.py",
        " src/leading-space.py",
        "src/trailing-space.py ",
    ],
)
def test_hostile_paths_are_denied(hostile_path: str) -> None:
    policy = default_policy()
    assert (
        deny(policy, request(repository_relative_paths=(hostile_path,)))
        == SecurityErrorCode.PATH_SCOPE_VIOLATION
    )


def test_scope_containment_boundaries() -> None:
    policy = default_policy()
    assert policy.authorize(request(paths=("src",))).authorized is True
    assert policy.authorize(request(paths=("src/app.py",))).authorized is True
    assert policy.authorize(request(paths=("src/deep/nested/a.java",))).authorized is True
    sibling_prefix = request(paths=("src-extra/file.txt",))
    assert deny(policy, sibling_prefix) == SecurityErrorCode.PATH_SCOPE_VIOLATION
    outside = request(paths=("tests/test_app.py",))
    assert deny(policy, outside) == SecurityErrorCode.PATH_SCOPE_VIOLATION


def test_tool_without_path_authority_cannot_gain_it_by_request() -> None:
    policy = default_policy()
    assert (
        deny(policy, request(tool_name="clock", action="now", paths=("src/app.py",)))
        == SecurityErrorCode.PATH_SCOPE_VIOLATION
    )


def test_network_capability_is_denied_unless_trusted_policy_grants_it() -> None:
    policy = default_policy()
    granted = policy.authorize(
        request(
            tool_name="net_fetch",
            action="fetch",
            repository_relative_paths=("reports/summary.json",),
            requests_network=True,
        )
    )
    assert granted.authorized is True
    assert (
        deny(
            policy,
            request(
                tool_name="file_read",
                action="read",
                paths=("src/app.py",),
                requests_network=True,
            ),
        )
        == SecurityErrorCode.NETWORK_ESCALATION_REQUEST
    )
    assert (
        deny(
            policy,
            request(tool_name="clock", action="now", requests_network=True),
        )
        == SecurityErrorCode.NETWORK_ESCALATION_REQUEST
    )


def test_command_execution_is_denied_unless_trusted_policy_grants_it() -> None:
    policy = default_policy()
    allowed = policy.authorize(
        request(
            tool_name="runner",
            action="execute",
            paths=("src/Main.java",),
            requests_command_execution=True,
        )
    )
    assert allowed.authorized is True
    denied = deny(
        default_policy(),
        request(
            tool_name="file_read",
            action="read",
            paths=("src/app.py",),
            requests_command_execution=True,
        ),
    )
    assert denied == SecurityErrorCode.COMMAND_EXECUTION_REQUEST
    assert (
        deny(
            default_policy(),
            request(tool_name="clock", action="now", requests_command_execution=True),
        )
        == SecurityErrorCode.COMMAND_EXECUTION_REQUEST
    )


def test_one_bad_path_denies_the_whole_request() -> None:
    policy = default_policy()
    mixed = request(paths=("src/app.py", "../../../../etc/passwd"))
    assert deny(policy, mixed) == SecurityErrorCode.PATH_SCOPE_VIOLATION


def test_oversize_path_count_fails_closed_at_construction() -> None:
    paths = tuple("src/f{0}.py".format(index) for index in range(MAX_REQUEST_PATHS + 1))
    assert_error(
        SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
        lambda: request(repository_relative_paths=paths),
    )


def test_evaluate_convenience_matches_policy_authorize() -> None:
    policy = default_policy()
    req = request(paths=("src/app.py",))
    direct = policy.authorize(req)
    via_function = evaluate_capability_request(policy, req)
    assert direct == via_function
    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: evaluate_capability_request("not a policy", req),  # type: ignore[arg-type]
    )
    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: evaluate_capability_request(policy, "not a request"),  # type: ignore[arg-type]
    )


SYNTHETIC_TOOL_TOKEN = "sk-" + "S3NTIN3LTOKEN" * 4
SYNTHETIC_ACTION_TOKEN = "ghp_" + "S3NTIN3LACTION" * 4


def test_unauthorized_tool_denial_never_echoes_requested_tool_name() -> None:
    decision = default_policy().authorize(
        request(tool_name=SYNTHETIC_TOOL_TOKEN, action="read")
    )
    assert decision.authorized is False
    assert decision.reason == SecurityErrorCode.UNAUTHORIZED_TOOL
    assert decision.detail == "requested tool is not allowed"
    rendered = repr(decision) + str(decision) + str(decision.detail)
    assert SYNTHETIC_TOOL_TOKEN not in rendered


def test_unauthorized_action_denial_never_echoes_requested_action() -> None:
    decision = default_policy().authorize(
        request(tool_name="file_read", action=SYNTHETIC_ACTION_TOKEN)
    )
    assert decision.authorized is False
    assert decision.reason == SecurityErrorCode.UNAUTHORIZED_ACTION
    assert decision.detail == "requested action is not allowed"
    rendered = repr(decision) + str(decision) + str(decision.detail)
    assert SYNTHETIC_ACTION_TOKEN not in rendered
    assert SYNTHETIC_TOOL_TOKEN not in rendered


def test_path_authority_denial_uses_constant_detail() -> None:
    secret_shaped_tool = "AKIAIOSFODNN7EXAMPLE"
    decision = default_policy().authorize(
        request(tool_name=secret_shaped_tool, action="now", paths=("src/app.py",))
    )
    assert decision.authorized is False
    assert decision.reason == SecurityErrorCode.UNAUTHORIZED_TOOL
    assert decision.detail == "requested tool is not allowed"
    rendered = repr(decision) + str(decision)
    assert secret_shaped_tool not in rendered


def test_policy_digest_is_deterministic_and_sensitive_to_change() -> None:
    first = default_policy()
    second = default_policy()
    assert first.content_digest == second.content_digest
    assert first.canonical_json() == second.canonical_json()
    widened = ToolPolicy.build(
        "policy-default",
        (
            ToolActionScope(
                tool_name="file_read",
                actions=("read", "list", "delete"),
                path_scopes=("src",),
            ),
            ToolActionScope(
                tool_name="net_fetch",
                actions=("fetch",),
                path_scopes=("reports",),
                allow_network=True,
            ),
            ToolActionScope(
                tool_name="runner",
                actions=("execute",),
                path_scopes=("src",),
                allow_command_execution=True,
            ),
            ToolActionScope(tool_name="clock", actions=("now",)),
        ),
    )
    assert widened.content_digest != first.content_digest


def test_policy_objects_resist_mutation_attempts() -> None:
    scope = ToolActionScope("file_read", ("read",), path_scopes=("src",))
    with pytest.raises(FrozenInstanceError):
        scope.allow_network = True  # type: ignore[misc]
    policy = default_policy()
    with pytest.raises(FrozenInstanceError):
        policy._scopes = ()  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        policy.tools = ("anything",)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        req = request()
        req.requests_network = True  # type: ignore[misc]


def test_corpus_tool_requests_produce_expected_decisions() -> None:
    policy = default_policy()
    checked = 0
    for case_data in load_corpus():
        tool_request = case_data["tool_request"]
        if tool_request is None:
            continue
        checked += 1
        payload = dict(tool_request)  # type: ignore[arg-type]
        req = CapabilityRequest(
            request_id=str(case_data["case_id"]).lower(),
            tool_name=str(payload["tool_name"]),
            action=str(payload["action"]),
            repository_relative_paths=tuple(payload["paths"]),  # type: ignore[arg-type]
            requests_network=bool(payload["requests_network"]),
            requests_command_execution=bool(payload["requests_command_execution"]),
        )
        decision = policy.authorize(req)
        expected = case_data["expected_tool_decision"]
        assert expected is not None
        assert decision.authorized == expected["authorized"], case_data["case_id"]
        assert decision.reason is not None
        assert decision.reason.value == expected["reason"], case_data["case_id"]
    assert checked >= 4


def test_anti_keyword_decoy_cannot_alter_tool_policy_or_capabilities() -> None:
    decoy_case = find_case(ANTI_KEYWORD_CASE_ID)
    untrusted_text = str(decoy_case["content"])
    policy = default_policy()
    digest_before = policy.content_digest

    short_probe = untrusted_text[:30]
    assert (
        deny(policy, request(tool_name=short_probe, action="read"))
        == SecurityErrorCode.UNAUTHORIZED_TOOL
    )
    with pytest.raises(SecurityError) as oversized_tool_name:
        request(tool_name=untrusted_text, action="read")
    assert oversized_tool_name.value.code == SecurityErrorCode.CONTEXT_BOUND_EXCEEDED
    assert (
        deny(policy, request(action=short_probe, paths=("src/app.py",)))
        == SecurityErrorCode.UNAUTHORIZED_ACTION
    )
    assert (
        deny(policy, request(paths=(untrusted_text,)))
        == SecurityErrorCode.PATH_SCOPE_VIOLATION
    )
    assert (
        deny(
            policy,
            request(
                tool_name="clock",
                action="now",
                requests_network=True,
                requests_command_execution=True,
            ),
        )
        == SecurityErrorCode.NETWORK_ESCALATION_REQUEST
    )

    assert_error(
        SecurityErrorCode.INVALID_SECURITY_INPUT,
        lambda: ToolPolicy.build(
            "policy-untrusted",
            ({"allow_all_tools": True},),  # type: ignore[list-item]
        ),
    )

    with pytest.raises(TypeError):
        CapabilityRequest(  # type: ignore[call-arg]
            request_id="ak-structural",
            tool_name="file_read",
            action="read",
            workflow_state="PLANNING",
        )
    with pytest.raises(TypeError):
        CapabilityRequest(  # type: ignore[call-arg]
            request_id="ak-structural-2",
            tool_name="file_read",
            action="read",
            rag_budget={"max_tokens": 999_999_999},
        )

    assert policy.content_digest == digest_before
    assert policy.authorize(request(paths=("src/app.py",))).authorized is True
