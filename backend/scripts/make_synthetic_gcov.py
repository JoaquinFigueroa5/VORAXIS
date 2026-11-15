"""Write small HDF5 files that mimic the NISAR L2 GCOV layout.

For developing the ingestion without Earthdata access. The structure follows the
product spec (see `app/processing/ingest_gcov.GcovLayout`); it is *not* a copy of
a real granule, so re-check the layout when real data arrives.

    python scripts/make_synthetic_gcov.py            # before/after pair in data/nisar/
    python scripts/ingest_nisar.py ingest --file data/nisar/<name>.h5 --location "Petén"
"""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np
from rasterio.warp import transform_bounds
from shapely.geometry import box

# UTM 15N, inside the seeded "Petén" AOI (same spot as scripts/smoke_analysis.py).
DEFAULT_ORIGIN = (780_000.0, 1_850_000.0)
DEFAULT_EPSG = 32615


def product_name(start: datetime, cycle: int, track: int = 98, frame: int = 19) -> str:
    end = start + timedelta(seconds=35)
    return (
        f"NISAR_L2_PR_GCOV_{cycle:03d}_{track:03d}_A_{frame:03d}_2005_DHDH_M_"
        f"{start:%Y%m%dT%H%M%S}_{end:%Y%m%dT%H%M%S}_P05036_N_F_J_001"
    )


def write_gcov(
    path: Path,
    *,
    start: datetime,
    shape: tuple[int, int] = (400, 500),
    posting: float = 20.0,
    origin: tuple[float, float] = DEFAULT_ORIGIN,
    epsg: int = DEFAULT_EPSG,
    seed: int = 11,
    change_block: tuple[slice, slice] | None = None,
    change_db: float = -6.0,
    nodata_block: tuple[slice, slice] | None = None,
) -> Path:
    """`origin` is the top-left pixel *edge*. Backscatter is linear power (gamma0).

    `seed` drives the scene itself: reuse it across dates so only `change_block`
    differs. `change_db` < 0 darkens the block (flood/burn-like).
    """
    rows, cols = shape
    rng = np.random.default_rng(seed)
    # Smooth "terrain" plus speckle-like multiplicative noise, around -8 dB (HH).
    yy, xx = np.mgrid[0:rows, 0:cols]
    base_db = -8.0 + 1.5 * np.sin(xx / 60.0) + 1.0 * np.cos(yy / 45.0)
    hh = 10 ** (base_db / 10) * rng.gamma(shape=16, scale=1 / 16, size=shape)
    hv = 10 ** ((base_db - 7.0) / 10) * rng.gamma(shape=16, scale=1 / 16, size=shape)
    if change_block is not None:
        factor = 10 ** (change_db / 10)
        hh[change_block] *= factor
        hv[change_block] *= factor
    hh, hv = hh.astype("float32"), hv.astype("float32")
    if nodata_block is not None:
        hh[nodata_block] = np.nan
        hv[nodata_block] = np.nan

    x = origin[0] + posting * (np.arange(cols) + 0.5)
    y = origin[1] - posting * (np.arange(rows) + 0.5)
    bounds = (origin[0], origin[1] - rows * posting, origin[0] + cols * posting, origin[1])
    footprint = box(*transform_bounds(f"EPSG:{epsg}", "EPSG:4326", *bounds, densify_pts=21))

    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h5:
        grid = h5.create_group("/science/LSAR/GCOV/grids/frequencyA")
        for name, data in (("HHHH", hh), ("HVHV", hv)):
            dataset = grid.create_dataset(
                name, data=data, chunks=(min(rows, 512), min(cols, 512)), compression="gzip"
            )
            dataset.attrs["_FillValue"] = np.float32(np.nan)
            dataset.attrs["units"] = np.bytes_("1")
        grid.create_dataset("xCoordinates", data=x)
        grid.create_dataset("yCoordinates", data=y)
        grid.create_dataset("xCoordinateSpacing", data=float(posting))
        grid.create_dataset("yCoordinateSpacing", data=-float(posting))
        projection = grid.create_dataset("projection", data=np.uint32(epsg))
        projection.attrs["epsg_code"] = epsg
        grid.create_dataset("listOfCovarianceTerms", data=np.array([b"HHHH", b"HVHV"]))
        grid.create_dataset("listOfPolarizations", data=np.array([b"HH", b"HV"]))

        ident = h5.create_group("/science/LSAR/identification")
        end = start + timedelta(seconds=35)
        for name, value in (
            ("productType", "GCOV"),
            ("boundingPolygon", footprint.wkt),
            ("zeroDopplerStartTime", start.strftime("%Y-%m-%dT%H:%M:%S.%f")),
            ("zeroDopplerEndTime", end.strftime("%Y-%m-%dT%H:%M:%S.%f")),
            ("orbitPassDirection", "Ascending"),
            ("productVersion", "0.1.0"),
            ("granuleId", path.stem),
            ("isSynthetic", "True"),
        ):
            ident.create_dataset(name, data=np.bytes_(value))
        ident.create_dataset("trackNumber", data=np.uint32(98))
        ident.create_dataset("frameNumber", data=np.uint32(19))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/nisar"))
    parser.add_argument("--size", type=int, default=600, help="pixels per side")
    args = parser.parse_args()

    first = datetime(2026, 10, 30, 23, 40, 59, tzinfo=UTC)
    second = first + timedelta(days=12)
    shape = (args.size, args.size)
    block = (slice(args.size // 3, args.size // 2), slice(args.size // 4, args.size // 2))
    before = write_gcov(args.out / f"{product_name(first, 34)}.h5", start=first, shape=shape)
    after = write_gcov(
        args.out / f"{product_name(second, 35)}.h5",
        start=second,
        shape=shape,
        change_block=block,
    )
    print(before)
    print(after)


if __name__ == "__main__":
    main()
