"""Load database/seeds/locations.geojson. Idempotent by (name)."""

import json
from pathlib import Path

from app.core.database import SessionLocal
from app.repositories.location_repository import LocationRepository
from app.utils.geometry import geojson_to_multipolygon_wkt

SEED_PATH = Path(__file__).resolve().parents[2] / "database" / "seeds" / "locations.geojson"


def main() -> None:
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    repo = LocationRepository()
    inserted = 0
    with SessionLocal() as db:
        for feature in payload["features"]:
            properties = feature["properties"]
            existing = repo.search(db, properties["name"], limit=1)
            if any(row[0].name == properties["name"] for row in existing):
                continue
            repo.create(
                db,
                name=properties["name"],
                country=properties.get("country"),
                description=properties.get("description"),
                geometry_wkt=geojson_to_multipolygon_wkt(feature["geometry"]),
            )
            inserted += 1
    print(f"inserted {inserted} locations (seed: {SEED_PATH.name})")


if __name__ == "__main__":
    main()
