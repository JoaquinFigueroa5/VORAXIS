"""Geometry helpers shared by the API, seeds and processing."""

import json
from typing import Any

from shapely import wkt as shapely_wkt
from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry.multipolygon import MultiPolygon

from app.core.exceptions import AppError


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Parse ``minx,miny,maxx,maxy`` into floats."""
    try:
        minx, miny, maxx, maxy = (float(part) for part in value.split(","))
    except ValueError as exc:
        raise AppError("bbox must be 'minx,miny,maxx,maxy'") from exc
    if minx >= maxx or miny >= maxy:
        raise AppError("bbox has invalid bounds")
    return minx, miny, maxx, maxy


def bbox_polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
    return box(*bbox).wkt


def geojson_to_multipolygon_wkt(geometry: dict[str, Any]) -> str:
    """Normalise a GeoJSON Polygon/MultiPolygon into a MultiPolygon WKT (EPSG:4326)."""
    geom = shape(geometry)
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    if geom.geom_type != "MultiPolygon":
        raise AppError("geometry must be a Polygon or MultiPolygon")
    return geom.wkt


def wkt_to_geojson(value: str) -> dict[str, Any]:
    return mapping(shapely_wkt.loads(value))


def as_geojson(text: str | None) -> dict[str, Any] | None:
    """ST_AsGeoJSON returns text; the API contract wants an object."""
    return json.loads(text) if text else None


def footprint_wkt(geometry: BaseGeometry | dict[str, Any]) -> str:
    geom = geometry if isinstance(geometry, BaseGeometry) else shape(geometry)
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return geom.wkt
