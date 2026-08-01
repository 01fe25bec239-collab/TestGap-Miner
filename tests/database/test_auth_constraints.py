"""Auth constraint tests for CONTRACT-AUTH-001@1.0.0-draft.2.

DB-002 has no Auth runtime, so "denied" here means the exact-tuple
authorization lookup finds no active grant, never that a service refused a
request. No authorization decision is claimed to be tested.
"""

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AuthSubject,
    GitHubInstallation,
    Repository,
    RepositoryAccess,
    User,
)
from support import active_grant, assert_rejected

ISSUER = "https://issuer.example/"


def test_user_a_reaches_repository_a_through_installation_a(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    grant = active_grant(
        session,
        fixture_two.user_a,
        fixture_two.installation_a,
        fixture_two.repository_a,
    )
    assert grant is not None
    assert grant.id == fixture_two.grant_a.id
    assert grant.authorization_source == "GITHUB_VERIFIED"


def test_cross_repository_substitution_finds_no_grant(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert (
        active_grant(
            session,
            fixture_two.user_a,
            fixture_two.installation_a,
            fixture_two.repository_b,
        )
        is None
    )


def test_cross_installation_substitution_finds_no_grant(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert (
        active_grant(
            session,
            fixture_two.user_a,
            fixture_two.installation_b,
            fixture_two.repository_a,
        )
        is None
    )


def test_cross_user_substitution_finds_no_grant(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert (
        active_grant(
            session,
            fixture_two.user_b,
            fixture_two.installation_a,
            fixture_two.repository_a,
        )
        is None
    )


def test_grant_referencing_an_unknown_repository_is_rejected(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert_rejected(
        session,
        RepositoryAccess(
            user_id=fixture_two.user_a.id,
            installation_id=fixture_two.installation_a.id,
            repository_id=uuid.uuid4(),
        ),
    )


def test_duplicate_issuer_subject_linkage_to_another_user_is_rejected(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert_rejected(
        session,
        AuthSubject(user=fixture_two.user_b, issuer=ISSUER, subject="Subject-A"),
    )


def test_case_distinct_issuer_and_subject_are_separate_identities(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    case_distinct_subject = AuthSubject(
        user=fixture_two.user_b, issuer=ISSUER, subject="subject-a"
    )
    case_distinct_issuer = AuthSubject(
        user=fixture_two.user_b, issuer=ISSUER.upper(), subject="Subject-A"
    )
    session.add_all([case_distinct_subject, case_distinct_issuer])
    session.flush()

    # Subject-A / subject-a and the upper-case issuer are three distinct rows,
    # so neither issuer nor subject is folded to a single case.
    stored = session.scalars(
        select(AuthSubject).where(AuthSubject.issuer.in_([ISSUER, ISSUER.upper()]))
    ).all()
    assert {(row.issuer, row.subject) for row in stored} == {
        (ISSUER, "Subject-A"),
        (ISSUER, "Subject-B"),
        (ISSUER, "subject-a"),
        (ISSUER.upper(), "Subject-A"),
    }


def test_issuer_and_subject_are_stored_without_normalization(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    issuer = "  HTTPS://Issuer.Example/Realm/  "
    subject = "  Opaque|Subject/ID+value  "
    subject_row = AuthSubject(user=fixture_two.user_a, issuer=issuer, subject=subject)
    session.add(subject_row)
    session.flush()
    session.expire(subject_row)
    assert subject_row.issuer == issuer
    assert subject_row.subject == subject


def test_duplicate_github_installation_id_is_rejected(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert_rejected(
        session,
        GitHubInstallation(
            github_installation_id=1001, github_account_id=9999, account_type="USER"
        ),
    )


def test_duplicate_github_repository_id_is_rejected(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert_rejected(session, Repository(github_repository_id=3001))


def test_revoked_access_is_distinguishable_from_expired_access(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    now = datetime.now(UTC)
    fixture_two.grant_a.status = "REVOKED"
    fixture_two.grant_a.revoked_at = now
    fixture_two.grant_b.status = "EXPIRED"
    fixture_two.grant_b.expired_at = now
    session.flush()

    assert fixture_two.grant_a.revoked_at is not None
    assert fixture_two.grant_a.expired_at is None
    assert fixture_two.grant_b.expired_at is not None
    assert fixture_two.grant_b.revoked_at is None


def test_expired_access_may_not_borrow_revoked_at(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    fixture_two.grant_a.status = "EXPIRED"
    fixture_two.grant_a.expired_at = datetime.now(UTC)
    fixture_two.grant_a.revoked_at = datetime.now(UTC)
    assert_rejected(session, fixture_two.grant_a)


def test_revoked_access_requires_a_revocation_timestamp(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    fixture_two.grant_a.status = "REVOKED"
    assert_rejected(session, fixture_two.grant_a)


def test_active_access_may_not_carry_a_terminal_timestamp(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    fixture_two.grant_a.expired_at = datetime.now(UTC)
    assert_rejected(session, fixture_two.grant_a)


def test_historical_inactive_grants_remain_attributable(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    fixture_two.grant_a.status = "REVOKED"
    fixture_two.grant_a.revoked_at = datetime.now(UTC)
    fixture_two.user_a.status = "DEPROVISIONED"
    fixture_two.user_a.deprovisioned_at = datetime.now(UTC)
    fixture_two.installation_a.status = "SUSPENDED"
    fixture_two.installation_a.suspended_at = datetime.now(UTC)
    fixture_two.repository_a.status = "INACCESSIBLE"
    session.flush()

    historical = session.get(RepositoryAccess, fixture_two.grant_a.id)
    assert historical is not None
    assert historical.user.id == fixture_two.user_a.id
    assert historical.installation.id == fixture_two.installation_a.id
    assert historical.repository.id == fixture_two.repository_a.id
    assert (
        active_grant(
            session,
            fixture_two.user_a,
            fixture_two.installation_a,
            fixture_two.repository_a,
        )
        is None
    )


def test_a_second_active_grant_for_the_same_tuple_is_rejected(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    assert_rejected(
        session,
        RepositoryAccess(
            user=fixture_two.user_a,
            installation=fixture_two.installation_a,
            repository=fixture_two.repository_a,
        ),
    )


def test_re_grant_after_revocation_is_representable(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    fixture_two.grant_a.status = "REVOKED"
    fixture_two.grant_a.revoked_at = datetime.now(UTC)
    session.flush()

    regrant = RepositoryAccess(
        user=fixture_two.user_a,
        installation=fixture_two.installation_a,
        repository=fixture_two.repository_a,
    )
    session.add(regrant)
    session.flush()

    rows = session.scalars(
        select(RepositoryAccess).where(
            RepositoryAccess.user_id == fixture_two.user_a.id,
            RepositoryAccess.repository_id == fixture_two.repository_a.id,
        )
    ).all()
    assert {row.status for row in rows} == {"REVOKED", "ACTIVE"}
    assert len(rows) == 2
    assert (
        active_grant(
            session,
            fixture_two.user_a,
            fixture_two.installation_a,
            fixture_two.repository_a,
        ).id
        == regrant.id
    )


def test_re_grant_after_expiry_is_representable(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    now = datetime.now(UTC)
    fixture_two.grant_a.status = "EXPIRED"
    fixture_two.grant_a.expires_at = now - timedelta(days=1)
    fixture_two.grant_a.expired_at = now
    session.flush()

    regrant = RepositoryAccess(
        user=fixture_two.user_a,
        installation=fixture_two.installation_a,
        repository=fixture_two.repository_a,
    )
    session.add(regrant)
    session.flush()
    assert regrant.status == "ACTIVE"


def test_scheduled_expiry_may_precede_recorded_expiry(
    session: Session, fixture_two: SimpleNamespace
) -> None:
    """An ACTIVE grant whose expires_at has passed is still stored ACTIVE until
    reconciliation records expired_at; the two timestamps stay distinct."""
    past = datetime.now(UTC) - timedelta(hours=2)
    fixture_two.grant_a.expires_at = past
    session.flush()
    assert fixture_two.grant_a.status == "ACTIVE"
    assert fixture_two.grant_a.expired_at is None

    fixture_two.grant_a.status = "EXPIRED"
    fixture_two.grant_a.expired_at = datetime.now(UTC)
    session.flush()
    assert fixture_two.grant_a.expired_at > fixture_two.grant_a.expires_at


def test_unknown_lifecycle_status_values_are_rejected(session: Session) -> None:
    assert_rejected(session, User(status="ARCHIVED"))


def test_suspended_user_requires_a_suspension_timestamp(session: Session) -> None:
    assert_rejected(session, User(status="SUSPENDED"))
