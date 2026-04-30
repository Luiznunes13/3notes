import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./3notes.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_chamado_validacao()


def _migrate_chamado_validacao():
    """Adds validation columns to chamado table if they don't exist yet.
    Existing rows default to validado=1 (already validated under old system)."""
    migrations = [
        "ALTER TABLE chamado ADD COLUMN validado BOOLEAN DEFAULT 1",
        "ALTER TABLE chamado ADD COLUMN validado_por TEXT",
        "ALTER TABLE chamado ADD COLUMN validado_em TIMESTAMP",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(__import__("sqlalchemy").text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore


def get_session():
    with Session(engine) as session:
        yield session
