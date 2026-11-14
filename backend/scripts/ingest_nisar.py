"""Inspect and ingest NISAR GCOV granules.

    # 1. Look at a file before trusting the layout (no database needed)
    python scripts/ingest_nisar.py inspect data/nisar/NISAR_L2_PR_GCOV_....h5 [--tree]

    # 2. Convert only (no database / storage): writes a COG next to you
    python scripts/ingest_nisar.py convert data/nisar/X.h5 out.tif --bbox=-90.6,15.9,-89.0,17.8

    # 3. Full ingestion: COG -> object storage -> Observation + RasterAsset
    python scripts/ingest_nisar.py ingest --file data/nisar/X.h5 --location "Petén"
    python scripts/ingest_nisar.py ingest --product-id NISAR_L2_PR_GCOV_... --location "Petén"

Inside docker, files under backend/data/ are visible at /app/data/.
"""

import argparse
import json
from pathlib import Path


def _inspect(args) -> None:
    from app.processing.ingest_gcov import describe_tree, inspect_gcov

    if args.tree:
        print("\n".join(describe_tree(args.file)))
        print()
    info = inspect_gcov(args.file, frequency=args.frequency)
    megapixels = info.width * info.height / 1e6
    print(f"file          {info.path.name} ({info.path.stat().st_size / 1e6:.1f} MB)")
    print(f"grid          {info.grid_path}")
    print(f"crs           {info.crs}")
    print(f"size          {info.width} x {info.height} px ({megapixels:.1f} MP)")
    print(f"posting       {info.x_spacing} x {info.y_spacing}")
    print(f"bounds        {info.bounds}")
    print(f"terms         {info.terms} dtype={info.dtype} fill={info.fill_value}")
    print(f"footprint     {info.footprint_wkt}")
    for key, value in sorted(info.identification.items()):
        if key != "boundingPolygon":
            print(f"  id.{key} = {value}")


def _convert(args) -> None:
    from shapely.geometry import box

    from app.processing.ingest_gcov import gcov_to_cog
    from app.utils.geometry import parse_bbox

    result = gcov_to_cog(
        args.file,
        args.output,
        aoi=box(*parse_bbox(args.bbox)) if args.bbox else None,
        polarizations=args.polarization,
        frequency=args.frequency,
        multilook=args.multilook,
    )
    print(json.dumps({"path": str(result.path), "crs": result.crs, **result.as_metadata()}, indent=2))


def _ingest(args) -> None:
    from app.core.database import SessionLocal
    from app.core.logging import configure_logging
    from app.services.ingest_service import IngestService

    configure_logging()
    with SessionLocal() as db:
        result = IngestService().ingest(
            db,
            location_id=args.location_id,
            location_name=args.location,
            h5_path=args.file,
            scene_id=args.scene_id,
            product_id=args.product_id,
            polarizations=args.polarization,
            frequency=args.frequency,
            multilook=args.multilook,
            force=args.force,
        )
    print(json.dumps(result.as_dict(), indent=2))


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--frequency", default="A", choices=("A", "B"))
    parser.add_argument(
        "--polarization",
        action="append",
        help="HH, HV, VV... repeatable; default = every backscatter term, co-pol first",
    )
    parser.add_argument(
        "--multilook", type=int, default=1, help="average NxN pixels (in power) before dB"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="print grid, CRS, terms and identification")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--frequency", default="A", choices=("A", "B"))
    inspect.add_argument("--tree", action="store_true", help="also list every HDF5 group/dataset")
    inspect.set_defaults(handler=_inspect)

    convert = commands.add_parser("convert", help="HDF5 -> COG on disk, nothing else")
    convert.add_argument("file", type=Path)
    convert.add_argument("output", type=Path)
    convert.add_argument("--bbox", help="minx,miny,maxx,maxy in EPSG:4326; write --bbox=-90.6,... when it starts with a minus")
    _common(convert)
    convert.set_defaults(handler=_convert)

    ingest = commands.add_parser("ingest", help="HDF5 -> COG -> storage -> database")
    ingest.add_argument("--file", type=Path, help="local .h5; omit to download from Earthdata")
    ingest.add_argument("--scene-id", help="catalog.nisar_scenes id")
    ingest.add_argument("--product-id", help="granule name already in the catalogue")
    ingest.add_argument("--location", help="location name, e.g. 'Petén'")
    ingest.add_argument("--location-id")
    ingest.add_argument("--force", action="store_true", help="re-ingest a READY observation")
    _common(ingest)
    ingest.set_defaults(handler=_ingest)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
