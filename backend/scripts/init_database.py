"""Create schemas and upgrade the database to head.

Safe to run repeatedly: schemas use IF NOT EXISTS, Alembic is idempotent.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import settings

SCHEMAS = ("geography", "catalog", "processing", "analysis", "evidence")


def main() -> None:
    engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        for schema in SCHEMAS:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    command.upgrade(config, "head")
    print("database is at head")


if __name__ == "__main__":
    main()
