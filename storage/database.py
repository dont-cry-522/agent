"""
database — SQLite 引擎与 Session 管理
====================================

单例模式：整个进程共享一个 engine。

用法：
    from storage.database import get_session

    with get_session() as session:
        session.add(...)
        session.commit()
"""

from pathlib import Path

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session


DB_PATH = Path("data") / "docagent.db"

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def _get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


def get_session() -> Session:
    return _get_sessionmaker()()


def init_db():
    """创建所有表（幂等，已存在的表不会重复创建）"""
    from storage.models import Base
    Base.metadata.create_all(bind=_get_engine())
