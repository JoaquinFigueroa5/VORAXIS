"""NISAR L2 GCOV (HDF5) -> AOI-cropped, dB-scaled Cloud Optimized GeoTIFF.

Pure raster code: no database, no object storage. `services/ingest_service.py`
owns the bookkeeping.

The HDF5 paths live in `GcovLayout` because they were written from the product
spec, not from a real granule. If the delivered files differ, change the layout
(or pass another one) instead of touching the reader.

Output grid: the AOI bounding box snapped to the product posting and padded
with NaN where the frame has no data. Two acquisitions of the same track/frame
ingested for the same AOI therefore land on the *same* grid, which is what
`processing/alignment.py` requires.
"""

import math
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import rasterio
import rasterio.shutil
from rasterio.transform import Affine
from rasterio.warp import transform_bounds
from rasterio.windows import Window
import shapely
from shapely import wkt as shapely_wkt
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import ProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)

_TERM = re.compile(r"^[HVRL]{4}$")
# Co-pol first: band 1 of the COG is what the change pipeline reads.
_TERM_ORDER = ("HHHH", "VVVV", "HVHV", "VHVH", "RHRH", "RVRV", "LHLH", "LVLV")
# Power below this (-50 dB) is far under the radar noise floor: edge artefacts, not signal.
MIN_VALID_POWER = 1e-5
# Source pixels held in memory per block (float32 -> ~64 MB).
_BLOCK_PIXELS = 16_000_000


@dataclass(frozen=True)
class GcovLayout:
    """Where things live inside the HDF5. `{band}` is LSAR/SSAR, `{frequency}` A/B."""

    grids: str = "/science/{band}/GCOV/grids/frequency{frequency}"
    identification: str = "/science/{band}/identification"
    x: str = "xCoordinates"
    y: str = "yCoordinates"
    x_spacing: str = "xCoordinateSpacing"
    y_spacing: str = "yCoordinateSpacing"
    projection: str = "projection"
    bands: tuple[str, ...] = ("LSAR", "SSAR")


DEFAULT_LAYOUT = GcovLayout()


@dataclass
class GcovInfo:
    path: Path
    band: str
    frequency: str
    grid_path: str
    epsg: int
    width: int
    height: int
    x_spacing: float
    y_spacing: float  # positive; rows run north -> south
    bounds: tuple[float, float, float, float]  # minx, miny, maxx, maxy (pixel edges)
    terms: list[str]  # real-valued diagonal covariance terms available
    dtype: str
    fill_value: float | None
    identification: dict[str, Any] = field(default_factory=dict)
    footprint_wkt: str | None = None  # EPSG:4326

    @property
    def crs(self) -> str:
        return f"EPSG:{self.epsg}"

    @property
    def polarizations(self) -> list[str]:
        return [term[:2] for term in self.terms]


@dataclass
class CogResult:
    path: Path
    crs: str
    width: int
    height: int
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    multilook: int
    frame_coverage: float  # fraction of the output grid inside the source frame
    bands: list[dict[str, Any]]
    units: str = "dB"

    def as_metadata(self) -> dict[str, Any]:
        return {
            "shape": [self.height, self.width],
            "transform": list(self.transform),
            "bounds": list(self.bounds),
            "resolution": list(self.resolution),
            "multilook": self.multilook,
            "frame_coverage": self.frame_coverage,
            "bands": self.bands,
            "units": self.units,
            "nodata": "nan",
        }


def _text(value: Any) -> Any:
    """HDF5 strings arrive as bytes, numpy bytes or 0-d/1-d arrays of them."""
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _text(value[()])
        return [_text(item) for item in value.tolist()]
    if isinstance(value, bytes | np.bytes_):
        return value.decode("utf-8", errors="replace").strip()
    if isinstance(value, np.generic):
        return value.item()
    return value


def normalize_term(polarization: str) -> str:
    """`HH` -> `HHHH`; `HVHV` stays. Only diagonal (real, backscatter) terms are valid."""
    value = polarization.strip().upper()
    if len(value) == 2:
        value = value * 2
    if not _TERM.match(value) or value[:2] != value[2:]:
        raise ProcessingError(
            f"'{polarization}' is not a backscatter term; expected e.g. HH, HV, VV or HHHH"
        )
    return value


def _find_grid(h5: h5py.File, frequency: str, layout: GcovLayout) -> tuple[str, str]:
    for band in layout.bands:
        path = layout.grids.format(band=band, frequency=frequency)
        if path in h5:
            return band, path
    tried = [layout.grids.format(band=band, frequency=frequency) for band in layout.bands]
    raise ProcessingError(
        f"no GCOV grid found in {Path(h5.filename).name}; tried {tried}. "
        "Run `python scripts/ingest_nisar.py inspect <file>` and adjust GcovLayout."
    )


def _epsg(grid: h5py.Group, layout: GcovLayout) -> int:
    projection = grid.get(layout.projection)
    if projection is None:
        raise ProcessingError(f"{grid.name} has no '{layout.projection}' dataset")
    code = projection.attrs.get("epsg_code")
    if code is None and projection.shape == ():
        code = projection[()]
    try:
        return int(_text(np.asarray(code)))
    except (TypeError, ValueError) as exc:
        raise ProcessingError(f"cannot read an EPSG code from {projection.name}") from exc


def _spacing(grid: h5py.Group, name: str, coordinates: np.ndarray) -> float:
    if name in grid and grid[name].shape == ():
        return abs(float(grid[name][()]))
    if coordinates.size < 2:
        raise ProcessingError(f"{grid.name} has a single-pixel axis and no '{name}'")
    return abs(float(coordinates[-1] - coordinates[0])) / (coordinates.size - 1)


def _terms(grid: h5py.Group) -> list[str]:
    found = [
        name
        for name, item in grid.items()
        if isinstance(item, h5py.Dataset)
        and item.ndim == 2
        and _TERM.match(name)
        and name[:2] == name[2:]
    ]
    return sorted(found, key=lambda t: (_TERM_ORDER.index(t) if t in _TERM_ORDER else 99, t))


def _identification(h5: h5py.File, band: str, layout: GcovLayout) -> dict[str, Any]:
    group = h5.get(layout.identification.format(band=band))
    if group is None:
        return {}
    values: dict[str, Any] = {}
    for name, item in group.items():
        if isinstance(item, h5py.Dataset) and item.size <= 64:
            try:
                values[name] = _text(item[()])
            except Exception:  # an unreadable attribute must not block ingestion
                continue
    return values


def _footprint(identification: dict[str, Any], info_bounds, epsg: int) -> str:
    """Prefer the product's boundingPolygon; fall back to the grid extent."""
    polygon = identification.get("boundingPolygon")
    if isinstance(polygon, str) and polygon:
        try:
            geom = shapely_wkt.loads(polygon)
            geom = shapely.force_2d(geom)
            if not geom.is_valid:
                geom = geom.buffer(0)
            if not geom.is_empty:
                return geom.wkt
        except Exception:
            logger.warning("unparseable boundingPolygon; using the grid extent instead")
    west, south, east, north = transform_bounds(
        f"EPSG:{epsg}", "EPSG:4326", *info_bounds, densify_pts=21
    )
    return box(west, south, east, north).wkt


def inspect_gcov(
    path: str | Path, frequency: str = "A", layout: GcovLayout = DEFAULT_LAYOUT
) -> GcovInfo:
    """Read grid geometry and metadata without touching the image data."""
    path = Path(path)
    if not path.is_file():
        raise ProcessingError(f"HDF5 file not found: {path}")
    with h5py.File(path, "r") as h5:
        band, grid_path = _find_grid(h5, frequency.upper(), layout)
        grid = h5[grid_path]
        if layout.x not in grid or layout.y not in grid:
            raise ProcessingError(f"{grid_path} lacks {layout.x}/{layout.y}")
        x = np.asarray(grid[layout.x][()], dtype="float64")
        y = np.asarray(grid[layout.y][()], dtype="float64")
        if y.size > 1 and y[0] < y[-1]:
            raise ProcessingError("yCoordinates ascend (south-up grid); not supported yet")
        dx = _spacing(grid, layout.x_spacing, x)
        dy = _spacing(grid, layout.y_spacing, y)
        terms = _terms(grid)
        if not terms:
            raise ProcessingError(f"{grid_path} has no backscatter terms (HHHH, HVHV, ...)")
        first = grid[terms[0]]
        if first.shape != (y.size, x.size):
            raise ProcessingError(
                f"{first.name} is {first.shape} but the coordinates say {(y.size, x.size)}"
            )
        fill = first.attrs.get("_FillValue")
        epsg = _epsg(grid, layout)
        # Coordinates are pixel centres.
        bounds = (
            float(x[0] - dx / 2),
            float(y[-1] - dy / 2),
            float(x[-1] + dx / 2),
            float(y[0] + dy / 2),
        )
        identification = _identification(h5, band, layout)
        return GcovInfo(
            path=path,
            band=band,
            frequency=frequency.upper(),
            grid_path=grid_path,
            epsg=epsg,
            width=int(x.size),
            height=int(y.size),
            x_spacing=dx,
            y_spacing=dy,
            bounds=bounds,
            terms=terms,
            dtype=str(first.dtype),
            fill_value=None if fill is None else float(np.asarray(fill).ravel()[0]),
            identification=identification,
            footprint_wkt=_footprint(identification, bounds, epsg),
        )


def describe_tree(path: str | Path, max_items: int = 400) -> list[str]:
    """Flat listing of every group/dataset: the first thing to run on a real granule."""
    lines: list[str] = []

    def visit(name: str, item: Any) -> None:
        if len(lines) >= max_items:
            return
        if isinstance(item, h5py.Dataset):
            extra = ""
            if item.size == 1:
                try:
                    extra = f" = {_text(item[()])!r}"[:120]
                except Exception:
                    extra = ""
            lines.append(f"/{name}  {item.shape} {item.dtype}{extra}")
        else:
            lines.append(f"/{name}/")

    with h5py.File(path, "r") as h5:
        h5.visititems(visit)
    return lines


@dataclass(frozen=True)
class _Grid:
    """Output grid plus where it sits on the source pixel grid."""

    transform: Affine
    width: int
    height: int
    col_offset: int  # source column of output column 0 (may be negative)
    row_offset: int


def _output_grid(info: GcovInfo, aoi: BaseGeometry | None, multilook: int) -> _Grid:
    minx, miny, maxx, maxy = info.bounds
    if aoi is None:
        want = info.bounds
    else:
        want = transform_bounds("EPSG:4326", info.crs, *aoi.bounds, densify_pts=21)
        if want[0] >= maxx or want[2] <= minx or want[1] >= maxy or want[3] <= miny:
            raise ProcessingError(
                f"the AOI does not overlap {info.path.name} "
                f"(AOI {tuple(round(v) for v in want)} vs frame "
                f"{tuple(round(v) for v in info.bounds)} in {info.crs})"
            )
    res_x, res_y = info.x_spacing * multilook, info.y_spacing * multilook
    # Snap to absolute multiples of the output resolution so every acquisition
    # of this AOI shares one grid.
    left = math.floor(want[0] / res_x) * res_x
    right = math.ceil(want[2] / res_x) * res_x
    top = math.ceil(want[3] / res_y) * res_y
    bottom = math.floor(want[1] / res_y) * res_y
    col_offset = round((left - minx) / info.x_spacing)
    row_offset = round((maxy - top) / info.y_spacing)
    # Re-derive the origin from the source grid: exact even if the product is
    # not snapped to its posting.
    origin_x = minx + col_offset * info.x_spacing
    origin_y = maxy - row_offset * info.y_spacing
    return _Grid(
        transform=Affine(res_x, 0.0, origin_x, 0.0, -res_y, origin_y),
        width=max(1, round((right - left) / res_x)),
        height=max(1, round((top - bottom) / res_y)),
        col_offset=col_offset,
        row_offset=row_offset,
    )


def _read_block(
    dataset: h5py.Dataset,
    fill_value: float | None,
    row0: int,
    rows: int,
    col0: int,
    cols: int,
) -> np.ndarray:
    """Read a source window in linear power, NaN outside the frame and on invalid pixels."""
    block = np.full((rows, cols), np.nan, dtype="float32")
    height, width = dataset.shape
    r0, r1 = max(row0, 0), min(row0 + rows, height)
    c0, c1 = max(col0, 0), min(col0 + cols, width)
    if r0 >= r1 or c0 >= c1:
        return block
    data = dataset[r0:r1, c0:c1].astype("float32", copy=False)
    with np.errstate(invalid="ignore"):
        invalid = ~np.isfinite(data) | (data < MIN_VALID_POWER)
    if fill_value is not None and np.isfinite(fill_value):
        invalid |= data == fill_value
    data = np.where(invalid, np.nan, data)
    block[r0 - row0 : r1 - row0, c0 - col0 : c1 - col0] = data
    return block


def _multilook(block: np.ndarray, looks: int) -> np.ndarray:
    """Average `looks x looks` cells in linear power (speckle reduction)."""
    if looks == 1:
        return block
    rows, cols = block.shape[0] // looks, block.shape[1] // looks
    stacked = block.reshape(rows, looks, cols, looks)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-NaN cells
        return np.nanmean(stacked, axis=(1, 3)).astype("float32")


def _to_db(power: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return (10.0 * np.log10(power)).astype("float32")


def gcov_to_cog(
    h5_path: str | Path,
    destination: str | Path,
    *,
    aoi: BaseGeometry | None = None,
    polarizations: list[str] | None = None,
    frequency: str = "A",
    multilook: int = 1,
    layout: GcovLayout = DEFAULT_LAYOUT,
) -> CogResult:
    """Write one COG with a band per polarisation, in dB, NaN as nodata.

    `aoi` is a shapely geometry in EPSG:4326 (only its bounding box is used);
    None converts the whole frame. `multilook` > 1 averages NxN source pixels
    before the dB conversion.
    """
    if multilook < 1:
        raise ProcessingError("multilook must be >= 1")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    info = inspect_gcov(h5_path, frequency=frequency, layout=layout)

    terms = [normalize_term(p) for p in polarizations] if polarizations else info.terms
    terms = list(dict.fromkeys(terms))
    missing = [term for term in terms if term not in info.terms]
    if missing:
        raise ProcessingError(
            f"{info.path.name} has no {missing}; available terms: {info.terms}"
        )

    grid = _output_grid(info, aoi, multilook)
    inside_cols = min(grid.col_offset + grid.width * multilook, info.width) - max(grid.col_offset, 0)
    inside_rows = min(grid.row_offset + grid.height * multilook, info.height) - max(grid.row_offset, 0)
    coverage = max(inside_cols, 0) * max(inside_rows, 0) / (
        grid.width * grid.height * multilook * multilook
    )

    block_rows = max(1, _BLOCK_PIXELS // (grid.width * multilook * multilook))
    stats = [{"count": 0, "sum": 0.0, "min": math.inf, "max": -math.inf} for _ in terms]
    scratch = destination.with_name(destination.stem + ".scratch.tif")
    profile = {
        "driver": "GTiff",
        "height": grid.height,
        "width": grid.width,
        "count": len(terms),
        "dtype": "float32",
        "crs": info.crs,
        "transform": grid.transform,
        "nodata": float("nan"),
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "BIGTIFF": "IF_SAFER",
    }
    logger.info(
        "converting %s -> %sx%s px, %s band(s) %s, multilook %s",
        info.path.name,
        grid.width,
        grid.height,
        len(terms),
        terms,
        multilook,
    )
    try:
        with h5py.File(info.path, "r") as h5, rasterio.open(scratch, "w", **profile) as sink:
            sink.update_tags(units="dB", source=info.path.name)
            for index, term in enumerate(terms, start=1):
                dataset = h5[f"{info.grid_path}/{term}"]
                if np.iscomplexobj(np.empty(0, dtype=dataset.dtype)):
                    raise ProcessingError(f"{dataset.name} is complex; expected real backscatter")
                sink.set_band_description(index, term[:2])
                for start in range(0, grid.height, block_rows):
                    rows = min(block_rows, grid.height - start)
                    power = _read_block(
                        dataset,
                        info.fill_value,
                        grid.row_offset + start * multilook,
                        rows * multilook,
                        grid.col_offset,
                        grid.width * multilook,
                    )
                    decibels = _to_db(_multilook(power, multilook))
                    valid = decibels[np.isfinite(decibels)]
                    if valid.size:
                        band = stats[index - 1]
                        band["count"] += int(valid.size)
                        band["sum"] += float(valid.sum(dtype="float64"))
                        band["min"] = min(band["min"], float(valid.min()))
                        band["max"] = max(band["max"], float(valid.max()))
                    sink.write(
                        decibels,
                        index,
                        window=Window(0, start, grid.width, rows),
                    )
        if all(band["count"] == 0 for band in stats):
            raise ProcessingError(
                f"{info.path.name} has no valid pixels inside the AOI (all nodata)"
            )
        rasterio.shutil.copy(
            scratch,
            destination,
            driver="COG",
            compress="DEFLATE",
            predictor="YES",
            blocksize=512,
            overview_resampling="average",
            bigtiff="IF_SAFER",
        )
    finally:
        scratch.unlink(missing_ok=True)

    total = grid.width * grid.height
    bands = [
        {
            "index": index,
            "polarization": term[:2],
            "term": term,
            "hdf5_path": f"{info.grid_path}/{term}",
            "valid_fraction": round(band["count"] / total, 6),
            "min_db": round(band["min"], 3) if band["count"] else None,
            "max_db": round(band["max"], 3) if band["count"] else None,
            "mean_db": round(band["sum"] / band["count"], 3) if band["count"] else None,
        }
        for index, (term, band) in enumerate(zip(terms, stats, strict=True), start=1)
    ]
    left, top = grid.transform.c, grid.transform.f
    return CogResult(
        path=destination,
        crs=info.crs,
        width=grid.width,
        height=grid.height,
        transform=tuple(grid.transform)[:6],
        bounds=(
            left,
            top - grid.height * info.y_spacing * multilook,
            left + grid.width * info.x_spacing * multilook,
            top,
        ),
        resolution=(info.x_spacing * multilook, info.y_spacing * multilook),
        multilook=multilook,
        frame_coverage=round(coverage, 6),
        bands=bands,
    )
