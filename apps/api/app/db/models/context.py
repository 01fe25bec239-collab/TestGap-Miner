"""DB-004 RAG context-selection metadata persistence.

Physical storage for ``CONTRACT-RAG-001`` context bundles and selected context
items. Only bounded provenance metadata is stored: the exact repository
revision identity each item came from, its inclusive line range, the SHA-256
of the selected text, and the supplied token accounting.

ContextItem.content, repository source bytes, and every other raw payload are
deliberately absent: provenance digests and identities are the durable record.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_in

# CONTRACT-RAG-001@1.0.0-draft.1 vocabulary and bounds.
RAG_CONTRACT_VERSION = "1.0.0-draft.1"
MAX_RAG_TOKEN_BUDGET = 2_000_000
TRUST_LABELS = ("UNTRUSTED_REPOSITORY_TEXT",)

# RAG identity domains accept at most 256 ASCII characters.
IDENTITY_LENGTH = 256
REVISION_LENGTH = 64
SHA256_LENGTH = 64
MAX_FILE_IDENTITY_BYTES = 4_096


class ContextBundle(Base):
    """One persisted ContextBundle selection without any selected content."""

    __tablename__ = "rag_context_bundles"
    __table_args__ = (
        sa.CheckConstraint(
            f"max_tokens BETWEEN 1 AND {MAX_RAG_TOKEN_BUDGET}",
            name="max_tokens_range",
        ),
        sa.CheckConstraint(
            f"consumed_tokens BETWEEN 0 AND {MAX_RAG_TOKEN_BUDGET}",
            name="consumed_tokens_range",
        ),
        sa.CheckConstraint(
            "consumed_tokens <= max_tokens",
            name="consumed_tokens_within_budget",
        ),
    )

    # RAG-owned explicit bundle identity; never inferred from a filesystem path.
    context_bundle_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    repository_id: Mapped[str] = mapped_column(sa.String(IDENTITY_LENGTH))
    revision_id: Mapped[str] = mapped_column(sa.String(REVISION_LENGTH))
    contract_version: Mapped[str] = mapped_column(sa.String(64))

    max_tokens: Mapped[int] = mapped_column(sa.Integer)
    consumed_tokens: Mapped[int] = mapped_column(sa.Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())

    items: Mapped[list["ContextBundleItem"]] = relationship(
        back_populates="bundle", order_by="ContextBundleItem.position"
    )


class ContextBundleItem(Base):
    """One ordered selected-context unit bound to exactly one bundle."""

    __tablename__ = "rag_context_items"
    __table_args__ = (
        # Supplied item order is semantically meaningful, so membership
        # positions are unique per bundle and dense from one.
        sa.UniqueConstraint(
            "context_bundle_id", "position", name="uq_rag_context_items_bundle_position"
        ),
        sa.CheckConstraint("position >= 1", name="position_positive"),
        sa.CheckConstraint("start_line > 0", name="start_line_positive"),
        sa.CheckConstraint("end_line >= start_line", name="end_line_not_before_start"),
        sa.CheckConstraint("token_count > 0", name="token_count_positive"),
        sa.CheckConstraint(sql_in("trust_label", TRUST_LABELS), name="trust_label_allowed"),
        sa.CheckConstraint(
            f"octet_length(file_identity) <= {MAX_FILE_IDENTITY_BYTES}",
            name="file_identity_bounded",
        ),
    )

    context_item_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    context_bundle_id: Mapped[str] = mapped_column(
        sa.ForeignKey("rag_context_bundles.context_bundle_id"), index=True
    )
    position: Mapped[int] = mapped_column(sa.Integer)

    candidate_id: Mapped[str] = mapped_column(sa.String(IDENTITY_LENGTH))
    file_identity: Mapped[str] = mapped_column(sa.Text)
    start_line: Mapped[int] = mapped_column(sa.Integer)
    end_line: Mapped[int] = mapped_column(sa.Integer)
    content_sha256: Mapped[str] = mapped_column(sa.String(SHA256_LENGTH))
    trust_label: Mapped[str] = mapped_column(sa.Text)
    token_count: Mapped[int] = mapped_column(sa.Integer)

    bundle: Mapped[ContextBundle] = relationship(back_populates="items")
