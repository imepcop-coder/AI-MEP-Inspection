import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ai_mep_inspection.db"
)

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_sqlite_columns():
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            result = conn.execute(text(f"PRAGMA table_info({table_name});"))
            existing_columns = {row[1] for row in result.fetchall()}
            added_column = False

            for column in table.columns:
                if column.name in existing_columns:
                    continue

                column_type = column.type.compile(dialect=engine.dialect)
                if "BOOLEAN" in column_type.upper():
                    sql_type = "BOOLEAN"
                elif "INTEGER" in column_type.upper():
                    sql_type = "INTEGER"
                elif "DATETIME" in column_type.upper():
                    sql_type = "DATETIME"
                elif "TEXT" in column_type.upper():
                    sql_type = "TEXT"
                elif "STRING" in column_type.upper():
                    sql_type = "VARCHAR(255)"
                else:
                    sql_type = "TEXT"

                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {sql_type};"))
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table_name}_{column.name} ON {table_name}({column.name});"
                ))
                added_column = True

            if added_column:
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
