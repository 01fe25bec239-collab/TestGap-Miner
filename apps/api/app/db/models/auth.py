"""Auth identity and repository authorization persistence.

Every field, status value, and lifecycle meaning below comes from
``CONTRACT-AUTH-001@1.0.0-draft.2``. Physical names, SQL types, constraint
names, and indexes are Database-owned; the semantics are not.

Issuer and subject are stored and compared exactly and case-sensitively. No
lowercasing, uppercasing, trimming, URL normalization, or alias resolution is
performed here, and no ``citext`` or functional index is used.

No password, password hash, OAuth code, access token, refresh token, GitHub
private key, installation token, webhook secret, API secret, browser session
token, or raw Authorization header is stored by any table in this module.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_in

USER_STATUSES = ("ACTIVE", "SUSPENDED", "DEPROVISIONED")
AUTH_SUBJECT_STATUSES = ("ACTIVE", "REVOKED")
INSTALLATION_STATUSES = ("ACTIVE", "SUSPENDED", "DELETED")
INSTALLATION_ACCOUNT_TYPES = ("USER", "ORGANIZATION")
REPOSITORY_STATUSES = ("ACTIVE", "ARCHIVED", "INACCESSIBLE", "DELETED")
REPOSITORY_ACCESS_STATUSES = ("ACTIVE", "REVOKED", "EXPIRED")
AUTHORIZATION_SOURCES = ("GITHUB_VERIFIED",)


class User(Base):
    """Canonical human user. Email, username, and display name are not identity
    keys and are deliberately absent; MVP requires no local credential field."""

    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint(sql_in("status", USER_STATUSES), name="status_allowed"),
        sa.CheckConstraint(
            "status <> 'SUSPENDED' OR suspended_at IS NOT NULL",
            name="suspended_at_present",
        ),
        sa.CheckConstraint(
            "status <> 'DEPROVISIONED' OR deprovisioned_at IS NOT NULL",
            name="deprovisioned_at_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(sa.Text, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now(), onupdate=sa.func.now()
    )
    suspended_at: Mapped[datetime | None]
    deprovisioned_at: Mapped[datetime | None]

    auth_subjects: Mapped[list["AuthSubject"]] = relationship(back_populates="user")
    repository_access: Mapped[list["RepositoryAccess"]] = relationship(
        back_populates="user"
    )


class AuthSubject(Base):
    """External authentication subject linked to exactly one canonical user."""

    __tablename__ = "auth_subjects"
    __table_args__ = (
        # Exact bytes, default collation: case-sensitive by construction.
        sa.UniqueConstraint("issuer", "subject"),
        sa.CheckConstraint(
            sql_in("status", AUTH_SUBJECT_STATUSES), name="status_allowed"
        ),
        sa.CheckConstraint(
            "status <> 'REVOKED' OR revoked_at IS NOT NULL",
            name="revoked_at_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), index=True)
    issuer: Mapped[str] = mapped_column(sa.Text)
    subject: Mapped[str] = mapped_column(sa.Text)
    provider_name: Mapped[str | None] = mapped_column(sa.Text)
    provider_account_id: Mapped[str | None] = mapped_column(sa.Text)
    status: Mapped[str] = mapped_column(sa.Text, default="ACTIVE")
    linked_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    revoked_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(back_populates="auth_subjects")


class GitHubInstallation(Base):
    """GitHub App installation identity. Installation tokens and App private
    keys are never stored."""

    __tablename__ = "github_installations"
    __table_args__ = (
        sa.UniqueConstraint("github_installation_id"),
        sa.CheckConstraint(
            sql_in("status", INSTALLATION_STATUSES), name="status_allowed"
        ),
        sa.CheckConstraint(
            sql_in("account_type", INSTALLATION_ACCOUNT_TYPES),
            name="account_type_allowed",
        ),
        sa.CheckConstraint(
            "github_installation_id > 0 AND github_account_id > 0",
            name="github_ids_positive",
        ),
        sa.CheckConstraint(
            "status <> 'SUSPENDED' OR suspended_at IS NOT NULL",
            name="suspended_at_present",
        ),
        sa.CheckConstraint(
            "status <> 'DELETED' OR deleted_at IS NOT NULL",
            name="deleted_at_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    github_installation_id: Mapped[int] = mapped_column(sa.BigInteger)
    github_account_id: Mapped[int] = mapped_column(sa.BigInteger)
    account_type: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[str] = mapped_column(sa.Text, default="ACTIVE")
    installed_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    suspended_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    last_synced_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())

    repository_access: Mapped[list["RepositoryAccess"]] = relationship(
        back_populates="installation"
    )


class Repository(Base):
    """Repository identity. Owner/name strings are mutable display metadata that
    must never authorize access, so they are not persisted here. Repository
    source bytes are outside the Auth contract and outside PostgreSQL."""

    __tablename__ = "repositories"
    __table_args__ = (
        sa.UniqueConstraint("github_repository_id"),
        sa.CheckConstraint(
            sql_in("status", REPOSITORY_STATUSES), name="status_allowed"
        ),
        sa.CheckConstraint("github_repository_id > 0", name="github_id_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    github_repository_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[str] = mapped_column(sa.Text, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now(), onupdate=sa.func.now()
    )
    last_synced_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())

    repository_access: Mapped[list["RepositoryAccess"]] = relationship(
        back_populates="repository"
    )


class RepositoryAccess(Base):
    """Repository authorization scoped to the exact
    user + GitHub App installation + repository tuple.

    Uniqueness is partial rather than permanent: at most one ``ACTIVE`` grant may
    exist per tuple, while ``REVOKED`` and ``EXPIRED`` rows remain stored for
    historical attribution and a later re-grant stays representable.
    """

    __tablename__ = "repository_access"
    __table_args__ = (
        sa.Index(
            "uq_repository_access_active",
            "user_id",
            "installation_id",
            "repository_id",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        sa.CheckConstraint(
            sql_in("status", REPOSITORY_ACCESS_STATUSES), name="status_allowed"
        ),
        sa.CheckConstraint(
            sql_in("authorization_source", AUTHORIZATION_SOURCES),
            name="authorization_source_allowed",
        ),
        # An ACTIVE grant has not yet been marked expired or revoked. A future
        # expires_at, or a null expires_at, both remain valid.
        sa.CheckConstraint(
            "status <> 'ACTIVE' OR (expired_at IS NULL AND revoked_at IS NULL)",
            name="active_not_terminated",
        ),
        # Explicit withdrawal uses revoked_at only.
        sa.CheckConstraint(
            "status <> 'REVOKED' OR revoked_at IS NOT NULL",
            name="revoked_at_present",
        ),
        # Expiry is recorded by a scheduled boundary, a recorded expiry, or both,
        # and never by borrowing revoked_at.
        sa.CheckConstraint(
            "status <> 'EXPIRED' OR ("
            "(expires_at IS NOT NULL OR expired_at IS NOT NULL)"
            " AND revoked_at IS NULL)",
            name="expiry_distinct_from_revocation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), index=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("github_installations.id"), index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("repositories.id"), index=True
    )
    status: Mapped[str] = mapped_column(sa.Text, default="ACTIVE")
    authorization_source: Mapped[str] = mapped_column(
        sa.Text, default="GITHUB_VERIFIED"
    )
    granted_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    last_verified_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    expires_at: Mapped[datetime | None]
    expired_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(back_populates="repository_access")
    installation: Mapped[GitHubInstallation] = relationship(
        back_populates="repository_access"
    )
    repository: Mapped[Repository] = relationship(back_populates="repository_access")
