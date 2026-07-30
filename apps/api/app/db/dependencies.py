from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import create_database_engine
from app.db.session import create_session_factory


@lru_cache(maxsize=1)
def _runtime_session_factory() -> sessionmaker[Session]:
    return create_session_factory(create_database_engine())


def get_db_session() -> Generator[Session, None, None]:
    session = _runtime_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

