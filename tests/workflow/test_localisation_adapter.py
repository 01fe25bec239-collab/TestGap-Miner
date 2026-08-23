"""AGW-003 Workflow-owned localisation boundary semantics."""

import ast
import hashlib
import importlib
from pathlib import Path

import pytest

from app.retrieval import (
    CandidateIdentity,
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
    FileIdentity,
    Provenance,
    RepositoryIdentity,
    RevisionIdentity,
    TokenBudget,
    TrustLabel,
)
from app.workflow.localisation_adapter import (
    LOCALISATION_ADAPTER_CONTRACT_VERSION,
    LocalisationBoundary,
    LocalisationBoundaryFailureCode,
    LocalisationRequest,
    LocalisationResolution,
    LocalisationResolutionKind,
    LowLocalisationConfidence,
    invoke_localisation,
    resolve_localisation_result,
)


REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/TestGap-Miner")
OTHER_REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/Other-Miner")
REVISION_ID = RevisionIdentity("1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4")
OTHER_REVISION_ID = RevisionIdentity("b" * 40)
QUERY = "Locate the bounded retry handling for workflow transitions"
CONTENT = "def locate():\n    return 'context'\n"


def request(**overrides: object) -> LocalisationRequest:
    values: dict[str, object] = {
        "repository_id": REPOSITORY_ID,
        "revision_id": REVISION_ID,
        "query": QUERY,
    }
    values.update(overrides)
    return LocalisationRequest(**values)  # type: ignore[arg-type]


def context_bundle(
    *,
    repository_id: RepositoryIdentity = REPOSITORY_ID,
    revision_id: RevisionIdentity = REVISION_ID,
) -> ContextBundle:
    item = ContextItem(
        context_item_id=ContextItemIdentity("context-001"),
        candidate_id=CandidateIdentity("candidate-001"),
        provenance=Provenance(
            repository_id=repository_id,
            revision_id=revision_id,
            file_identity=FileIdentity("apps/api/app/workflow/planning.py"),
            start_line=1,
            end_line=2,
            content_sha256=_sha256(CONTENT),
        ),
        trust_label=TrustLabel.UNTRUSTED_REPOSITORY_TEXT,
        content=CONTENT,
        token_count=5,
    )
    return ContextBundle(
        context_bundle_id=ContextBundleIdentity("bundle-001"),
        repository_id=repository_id,
        revision_id=revision_id,
        items=(item,),
        token_budget=TokenBudget(max_tokens=10, consumed_tokens=5),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class FakeBoundary:
    """Deterministic fake returning scripted values in order."""

    def __init__(self, results: list[object]) -> None:
        self._results = results
        self.calls: list[LocalisationRequest] = []

    def localise(self, request: LocalisationRequest) -> object:
        self.calls.append(request)
        result = self._results[min(len(self.calls) - 1, len(self._results) - 1)]
        if isinstance(result, Exception):
            raise result
        if isinstance(result, type) and issubclass(result, Exception):
            raise result()
        return result


class NoLocaliseMethod:
    pass


class NotCallableLocalise:
    localise = "not callable"


def test_contract_version_is_stable() -> None:
    assert (
        LOCALISATION_ADAPTER_CONTRACT_VERSION
        == "CONTRACT-WORKFLOW-LOCALISATION-ADAPTER-001@1.0.0-draft.1"
    )


def test_request_is_validated_and_canonical() -> None:
    value = request()
    assert value.canonical_dict() == {
        "query": QUERY,
        "repository_id": REPOSITORY_ID.value,
        "revision_id": REVISION_ID.value,
    }
    assert value == request()


@pytest.mark.parametrize(
    ("overrides", "message_part"),
    [
        ({"repository_id": "repo"}, "repository_id"),
        ({"repository_id": None}, "repository_id"),
        ({"revision_id": "a" * 40}, "revision_id"),
        ({"query": ""}, "nonempty"),
        ({"query": "   padded   "}, "outer whitespace"),
        ({"query": 42}, "nonempty"),
        ({"query": None}, "nonempty"),
        ({"query": "x" * 16_385}, "exceeds"),
    ],
)
def test_malformed_requests_are_rejected_at_construction(
    overrides, message_part
) -> None:
    with pytest.raises((TypeError, ValueError)) as raised:
        request(**overrides)
    assert message_part in str(raised.value)


def test_query_surrogates_fail_closed() -> None:
    with pytest.raises(ValueError):
        request(query="\ud800")


def test_valid_bundle_resolves_with_exact_identity() -> None:
    bundle = context_bundle()
    result = invoke_localisation(FakeBoundary([bundle]), request())

    assert result.kind == LocalisationResolutionKind.CONTEXT_AVAILABLE
    assert result.context_bundle is bundle
    assert result.failure_code is None


def test_low_confidence_marker_is_distinct_from_failure() -> None:
    result = invoke_localisation(
        FakeBoundary([LowLocalisationConfidence()]), request()
    )

    assert result.kind == LocalisationResolutionKind.LOW_LOCALISATION_CONFIDENCE
    assert result.context_bundle is None
    assert result.failure_code is None


def test_empty_valid_bundle_still_binds_exactly() -> None:
    empty = ContextBundle(
        context_bundle_id=ContextBundleIdentity("bundle-empty"),
        repository_id=REPOSITORY_ID,
        revision_id=REVISION_ID,
        items=(),
        token_budget=TokenBudget(max_tokens=8, consumed_tokens=0),
    )
    result = invoke_localisation(FakeBoundary([empty]), request())

    assert result.kind == LocalisationResolutionKind.CONTEXT_AVAILABLE
    assert result.context_bundle is empty


@pytest.mark.parametrize(
    "result_value",
    [None, 42, "bundle", {}, [], object()],
)
def test_non_bundle_results_are_malformed(result_value) -> None:
    outcome = resolve_localisation_result(result_value, request())
    assert outcome.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
    assert outcome.failure_code == LocalisationBoundaryFailureCode.MALFORMED_RESULT
    assert outcome.context_bundle is None


def test_context_bundle_subclass_is_rejected() -> None:
    class ShadowBundle(ContextBundle):  # type: ignore[misc]
        pass

    forged = ShadowBundle.__new__(ShadowBundle)
    object.__setattr__(forged, "context_bundle_id", ContextBundleIdentity("x"))
    object.__setattr__(forged, "repository_id", OTHER_REPOSITORY_ID)
    object.__setattr__(forged, "revision_id", REVISION_ID)
    object.__setattr__(forged, "items", ())
    object.__setattr__(
        forged, "token_budget", TokenBudget(max_tokens=1, consumed_tokens=0)
    )

    outcome = resolve_localisation_result(forged, request())
    assert outcome.failure_code == LocalisationBoundaryFailureCode.MALFORMED_RESULT


def test_repository_mismatch_fails_closed() -> None:
    drifted = context_bundle(repository_id=OTHER_REPOSITORY_ID)
    outcome = resolve_localisation_result(drifted, request())

    assert outcome.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
    assert outcome.context_bundle is None
    assert outcome.failure_code == LocalisationBoundaryFailureCode.REPOSITORY_MISMATCH


def test_revision_mismatch_fails_closed() -> None:
    drifted = context_bundle(revision_id=OTHER_REVISION_ID)
    outcome = resolve_localisation_result(drifted, request())

    assert outcome.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
    assert outcome.failure_code == LocalisationBoundaryFailureCode.REVISION_MISMATCH


def test_repository_mismatch_precedes_revision_mismatch() -> None:
    drifted = context_bundle(
        repository_id=OTHER_REPOSITORY_ID, revision_id=OTHER_REVISION_ID
    )
    outcome = resolve_localisation_result(drifted, request())
    assert outcome.failure_code == LocalisationBoundaryFailureCode.REPOSITORY_MISMATCH


@pytest.mark.parametrize(
    "raised", [RuntimeError("internal"), ValueError("bad"), KeyError("k")]
)
def test_boundary_exceptions_become_typed_failures(raised) -> None:
    result = invoke_localisation(FakeBoundary([raised]), request())

    assert result.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
    assert result.failure_code == LocalisationBoundaryFailureCode.BOUNDARY_ERROR
    assert result.context_bundle is None


def test_boundary_without_entrypoint_fails_closed() -> None:
    for boundary in (None, NoLocaliseMethod(), NotCallableLocalise(), 42):
        result = invoke_localisation(boundary, request())
        assert result.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
        assert result.failure_code == LocalisationBoundaryFailureCode.BOUNDARY_ERROR


def test_invalid_request_object_fails_closed() -> None:
    result = invoke_localisation(FakeBoundary([context_bundle()]), None)

    assert result.kind == LocalisationResolutionKind.BOUNDARY_FAILURE
    assert result.failure_code == LocalisationBoundaryFailureCode.INVALID_REQUEST


def test_adversarial_attribute_access_fails_closed() -> None:
    class ExplodingResult:
        def __getattr__(self, name: str) -> object:
            raise RuntimeError(f"no {name}")

    outcome = resolve_localisation_result(ExplodingResult(), request())
    assert outcome.failure_code == LocalisationBoundaryFailureCode.MALFORMED_RESULT


def test_resolution_payloads_are_consistent() -> None:
    with pytest.raises(TypeError):
        LocalisationResolution(LocalisationResolutionKind.CONTEXT_AVAILABLE)
    with pytest.raises(ValueError):
        LocalisationResolution(
            LocalisationResolutionKind.CONTEXT_AVAILABLE,
            context_bundle=context_bundle(),
            failure_code=LocalisationBoundaryFailureCode.BOUNDARY_ERROR,
        )
    with pytest.raises(ValueError):
        LocalisationResolution(
            LocalisationResolutionKind.BOUNDARY_FAILURE,
            context_bundle=context_bundle(),
        )
    with pytest.raises(TypeError):
        LocalisationResolution(LocalisationResolutionKind.BOUNDARY_FAILURE)


def test_boundary_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakeBoundary([context_bundle()]), LocalisationBoundary)
    assert not isinstance(NoLocaliseMethod(), LocalisationBoundary)


def test_boundary_call_is_total_over_equivalent_inputs() -> None:
    first = invoke_localisation(FakeBoundary([context_bundle()]), request())
    second = invoke_localisation(FakeBoundary([context_bundle()]), request())
    assert first.kind == second.kind
    assert first.context_bundle == second.context_bundle


def test_adapter_modules_have_no_network_or_filesystem_surface() -> None:
    forbidden_modules = {
        "os",
        "os.path",
        "pathlib",
        "socket",
        "subprocess",
        "urllib",
        "urllib.request",
        "httpx",
        "requests",
        "uuid",
        "random",
        "secrets",
        "datetime",
        "time",
    }
    module = importlib.import_module("app.workflow.localisation_adapter")
    tree = ast.parse(Path(module.__file__ or "").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            assert node.module not in forbidden_modules
