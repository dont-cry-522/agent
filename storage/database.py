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

from sqlalchemy import create_engine, Engine, inspect, text
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
    """创建所有表并自动添加新增列（幂等）"""
    from storage.models import Base
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)

    _migrate_missing_columns(engine)


def _migrate_missing_columns(engine: Engine):
    """为已存在的表添加模型中新增的列（SQLite 不支持 ALTER TABLE ... ADD IF NOT EXISTS）"""
    from storage.models import Base
    insp = inspect(engine)
    for table_cls in Base.__subclasses__():
        table_name = table_cls.__tablename__
        if table_name not in insp.get_table_names():
            continue
        existing = {c["name"] for c in insp.get_columns(table_name)}
        for col in table_cls.__table__.columns:
            if col.name not in existing and not col.primary_key:
                col_type = _sql_type(col)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = ""
                if col.server_default is not None:
                    default = f" DEFAULT {col.server_default.arg}"
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type} {nullable}{default}"
                try:
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print(f"[migrate] {table_name}.{col.name} added")
                except Exception as e:
                    print(f"[migrate] {table_name}.{col.name} failed: {e}")


def _sql_type(col) -> str:
    t = str(col.type).upper()
    if "VARCHAR" in t or t == "STRING":
        return "TEXT"
    if "INT" in t:
        return "INTEGER"
    if "FLOAT" in t or "DOUBLE" in t:
        return "REAL"
    if "TEXT" in t or "CLOB" in t:
        return "TEXT"
    if "JSON" in t:
        return "TEXT"
    if "BOOLEAN" in t:
        return "INTEGER"
    if "DATETIME" in t:
        return "TEXT"
    return "TEXT"
