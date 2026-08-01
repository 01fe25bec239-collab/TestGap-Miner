"""DB-002 schema shape, boundary, and secret-storage checks."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.db.models import Base
from support import DB_002_TABLES, FORBIDDEN_TABLES, SECRET_NAME_PATTERN


def test_metadata_contains_exactly_the_db_002_tables() -> None:
    assert set(Base.metadata.tables) == DB_002_TABLES


def test_models_share_one_metadata_instance() -> None:
    from app.db.metadata import metadata

    assert Base.metadata is metadata
    assert all(table.metadata is metadata for table in Base.metadata.tables.values())


def test_no_model_column_looks_like_a_secret() -> None:
    offenders = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        # authorization_source is a provenance label, not a credential.
        if SECRET_NAME_PATTERN.search(column.name)
    ]
    assert offenders == []


def test_every_db_002_table_exists_in_the_database(migrated_engine: Engine) -> None:
    assert DB_002_TABLES <= set(inspect(migrated_engine).get_table_names())


def test_no_db_003_or_later_table_exists(migrated_engine: Engine) -> None:
    present = set(inspect(migrated_engine).get_table_names())
    assert present & FORBIDDEN_TABLES == set()
    assert present - {"alembic_version"} == DB_002_TABLES


def test_no_database_column_looks_like_a_secret(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    offenders = [
        f"{table}.{column['name']}"
        for table in DB_002_TABLES
        for column in inspector.get_columns(table)
        if SECRET_NAME_PATTERN.search(column["name"])
    ]
    assert offenders == []


def test_every_primary_key_is_a_uuid(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    for table in DB_002_TABLES:
        primary_key = inspector.get_pk_constraint(table)
        assert primary_key["constrained_columns"] == ["id"], table
        types = {c["name"]: str(c["type"]) for c in inspector.get_columns(table)}
        assert types["id"] == "UUID", table


def test_every_timestamp_column_is_timezone_aware(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    naive = [
        f"{table}.{column['name']}"
        for table in DB_002_TABLES
        for column in inspector.get_columns(table)
        if str(column["type"]).startswith("TIMESTAMP")
        and not column["type"].timezone
    ]
    assert naive == []


def test_issuer_subject_uniqueness_is_exact_and_not_case_folded(
    migrated_engine: Engine,
) -> None:
    inspector = inspect(migrated_engine)
    unique = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("auth_subjects")
    }
    assert unique["uq_auth_subjects_issuer_subject"] == ["issuer", "subject"]

    types = {c["name"]: str(c["type"]) for c in inspector.get_columns("auth_subjects")}
    assert types["issuer"] == "TEXT"
    assert types["subject"] == "TEXT"
    # No citext type and no lower()/upper() functional index.
    assert not any(
        "lower" in str(index.get("expressions", "")).lower()
        or "upper" in str(index.get("expressions", "")).lower()
        for index in inspector.get_indexes("auth_subjects")
    )


def test_external_github_identifiers_are_unique(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    installation = {
        c["name"]: c["column_names"]
        for c in inspector.get_unique_constraints("github_installations")
    }
    repository = {
        c["name"]: c["column_names"]
        for c in inspector.get_unique_constraints("repositories")
    }
    assert installation["uq_github_installations_github_installation_id"] == [
        "github_installation_id"
    ]
    assert repository["uq_repositories_github_repository_id"] == [
        "github_repository_id"
    ]


def test_active_access_uniqueness_is_partial(migrated_engine: Engine) -> None:
    indexes = {
        index["name"]: index
        for index in inspect(migrated_engine).get_indexes("repository_access")
    }
    active = indexes["uq_repository_access_active"]
    assert active["unique"] is True
    assert active["column_names"] == ["user_id", "installation_id", "repository_id"]
    # A permanent unique rule would block a valid re-grant; this one is scoped
    # to ACTIVE rows only.
    assert "ACTIVE" in str(active.get("dialect_options", {}))


def test_repository_access_foreign_keys_are_explicit(migrated_engine: Engine) -> None:
    referred = {
        fk["name"]: (fk["constrained_columns"], fk["referred_table"])
        for fk in inspect(migrated_engine).get_foreign_keys("repository_access")
    }
    assert referred["fk_repository_access_user_id_users"] == (["user_id"], "users")
    assert referred["fk_repository_access_installation_id_github_installations"] == (
        ["installation_id"],
        "github_installations",
    )
    assert referred["fk_repository_access_repository_id_repositories"] == (
        ["repository_id"],
        "repositories",
    )


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        (
            "users",
            {
                "ck_users_status_allowed",
                "ck_users_suspended_at_present",
                "ck_users_deprovisioned_at_present",
            },
        ),
        (
            "repository_access",
            {
                "ck_repository_access_status_allowed",
                "ck_repository_access_authorization_source_allowed",
                "ck_repository_access_active_not_terminated",
                "ck_repository_access_revoked_at_present",
                "ck_repository_access_expiry_distinct_from_revocation",
            },
        ),
        (
            "run_requests",
            {
                "ck_run_requests_request_kind_allowed",
                "ck_run_requests_kind_field_shape",
                "ck_run_requests_idempotency_key_version_positive",
                "ck_run_requests_github_repository_id_positive",
            },
        ),
        (
            "runs",
            {
                "ck_runs_state_allowed",
                "ck_runs_repair_attempts_used_range",
                "ck_runs_version_non_negative",
                "ck_runs_retry_attempts_used_range",
                "ck_runs_retry_limit_non_negative",
                "ck_runs_step_attempts_used_non_negative",
                "ck_runs_terminal_at_matches_state",
                "ck_runs_failure_code_matches_state",
                "ck_runs_abstention_code_matches_state",
                "ck_runs_cancellation_code_matches_state",
                "ck_runs_terminal_actor_matches_state",
                "ck_runs_terminal_actor_type_allowed",
                "ck_runs_parent_run_id_not_self",
            },
        ),
    ],
)
def test_named_check_constraints_are_present(
    migrated_engine: Engine, table: str, expected: set[str]
) -> None:
    present = {
        constraint["name"]
        for constraint in inspect(migrated_engine).get_check_constraints(table)
    }
    assert expected <= present
