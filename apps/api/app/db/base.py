import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

from app.db.metadata import metadata


class Base(DeclarativeBase):
    """Single declarative boundary bound to the one shared MetaData."""

    metadata = metadata

    type_annotation_map = {
        uuid.UUID: sa.Uuid(),
        datetime: sa.DateTime(timezone=True),
    }


def sql_in(column: str, values: tuple[str, ...]) -> str:
    """Render a check-constraint membership test over exact uppercase values."""
    return f"{column} IN ({', '.join(repr(value) for value in values)})"
