import os

import pytest
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set (run inside docker compose)"
)

EXPECTED = {
    "geography": {"locations"},
    "catalog": {"nisar_scenes", "observations"},
    "processing": {"processing_jobs", "raster_assets"},
    "analysis": {"change_events", "change_metrics"},
    "evidence": {"auxiliary_events", "evidence_records"},
}


def test_all_tables_and_schemas_exist():
    engine = create_engine(os.environ["DATABASE_URL"])
    inspector = inspect(engine)

    for schema, tables in EXPECTED.items():
        present = set(inspector.get_table_names(schema=schema))
        assert tables <= present, f"{schema} is missing {tables - present}"


def test_spatial_indexes_are_gist():
    engine = create_engine(os.environ["DATABASE_URL"])
    inspector = inspect(engine)

    for schema, table in (
        ("geography", "locations"),
        ("catalog", "nisar_scenes"),
        ("analysis", "change_events"),
        ("evidence", "auxiliary_events"),
    ):
        indexes = inspector.get_indexes(table, schema=schema)
        # Plain B-tree indexes carry no postgresql_using key.
        assert any(
            index["dialect_options"].get("postgresql_using") == "gist" for index in indexes
        )
