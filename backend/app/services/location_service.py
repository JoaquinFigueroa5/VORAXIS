from collections.abc import Sequence

from shapely.geometry import box, shape

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationCreate, LocationOut
from app.utils.geometry import as_geojson, footprint_wkt

# Larger areas would not fit one NISAR frame and produce rasters too big to analyse.
MAX_SIDE_DEGREES = 3.0
MIN_SIDE_DEGREES = 0.01


class LocationService:
    def __init__(self, repo: LocationRepository | None = None) -> None:
        self.repo = repo or LocationRepository()

    @staticmethod
    def _to_out(row) -> LocationOut:
        location, geojson = row
        return LocationOut(
            id=location.id,
            name=location.name,
            country=location.country,
            description=location.description,
            geometry=as_geojson(geojson),
            created_at=location.created_at,
        )

    def list(self, db, limit: int = 50, offset: int = 0) -> list[LocationOut]:
        return [self._to_out(row) for row in self.repo.list(db, limit=limit, offset=offset)]

    def search(self, db, query: str, limit: int = 20) -> Sequence[LocationOut]:
        return [self._to_out(row) for row in self.repo.search(db, query, limit=limit)]

    def get(self, db, location_id) -> LocationOut:
        row = self.repo.get(db, location_id)
        if row is None:
            raise NotFoundError(f"location {location_id} not found")
        return self._to_out(row)

    def create(self, db, payload: LocationCreate) -> LocationOut:
        geometry = self._geometry(payload)
        name = payload.name.strip()
        if not name:
            raise AppError("name must not be blank", code="location_name_blank")
        if self.repo.get_model_by_name(db, name) is not None:
            raise ConflictError(
                f"a location named '{name}' already exists",
                code="location_name_taken",
                params={"name": name},
            )
        location = self.repo.create(
            db,
            name=name,
            country=payload.country,
            description=payload.description,
            geometry_wkt=footprint_wkt(geometry),
        )
        return self.get(db, location.id)

    @staticmethod
    def _geometry(payload: LocationCreate):
        if (payload.geometry is None) == (payload.bbox is None):
            raise AppError("send exactly one of 'geometry' or 'bbox'", code="location_geometry_or_bbox")
        if payload.bbox is not None:
            west, south, east, north = payload.bbox
            if west >= east or south >= north:
                raise AppError(
                    "bbox must be [west, south, east, north] with west < east and south < north",
                    code="location_bbox_order",
                )
            geometry = box(west, south, east, north)
        else:
            raw = payload.geometry
            if raw.get("type") == "Feature":
                raw = raw.get("geometry") or {}
            try:
                geometry = shape(raw)
            except Exception as exc:
                raise AppError(
                    f"geometry is not valid GeoJSON: {exc}", code="location_geojson_invalid"
                ) from exc
            if geometry.geom_type not in ("Polygon", "MultiPolygon"):
                raise AppError("geometry must be a Polygon or MultiPolygon", code="location_shape")
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
            if geometry.is_empty or geometry.geom_type not in ("Polygon", "MultiPolygon"):
                raise AppError(
                    "geometry is empty or self-intersecting beyond repair",
                    code="location_geometry_broken",
                )

        west, south, east, north = geometry.bounds
        if west < -180 or east > 180 or south < -90 or north > 90:
            raise AppError(
                "coordinates must be longitude/latitude in degrees (EPSG:4326)",
                code="location_out_of_range",
            )
        width, height = east - west, north - south
        if max(width, height) > MAX_SIDE_DEGREES:
            raise AppError(
                f"the area spans {width:.2f} x {height:.2f} degrees; the maximum is "
                f"{MAX_SIDE_DEGREES:g} per side. Draw a smaller area.",
                code="location_too_large",
                params={"width": f"{width:.2f}", "height": f"{height:.2f}", "max": f"{MAX_SIDE_DEGREES:g}"},
            )
        if min(width, height) < MIN_SIDE_DEGREES:
            raise AppError(
                f"the area is too small; each side must be at least {MIN_SIDE_DEGREES:g} degrees",
                code="location_too_small",
                params={"min": f"{MIN_SIDE_DEGREES:g}"},
            )
        return geometry
