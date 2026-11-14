"""Sync ASF DAAC products into catalog.nisar_scenes.

Usage:
    python scripts/sync_nisar_catalog.py --bbox -90.6,15.9,-89.0,17.8 \
        --start 2026-06-01 --end 2026-06-30
"""

import argparse

from app.core.database import SessionLocal
from app.services.nisar_service import NisarService
from app.utils.dates import parse_datetime
from app.utils.geometry import parse_bbox


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", required=True, help="minx,miny,maxx,maxy")
    parser.add_argument("--start", required=True, help="ISO date/time")
    parser.add_argument("--end", required=True, help="ISO date/time")
    parser.add_argument("--max-results", type=int, default=250)
    args = parser.parse_args()

    with SessionLocal() as db:
        count = NisarService().sync_from_catalogue(
            db,
            bbox=parse_bbox(args.bbox),
            start=parse_datetime(args.start),
            end=parse_datetime(args.end),
            max_results=args.max_results,
        )
    print(f"synced {count} scenes")


if __name__ == "__main__":
    main()
