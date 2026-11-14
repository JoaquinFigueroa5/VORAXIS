"""Catalogue mapping, no network and no credentials."""

from app.integrations.nisar.catalog_mapper import map_asf_product

SAMPLE = {
    "fileID": "NISAR_L2_PR_GCOV_001_20260620T103000_20260620T103500_001_A_001",
    "sceneName": "NISAR_L2_PR_GCOV_001_20260620T103000_20260620T103500_001_A_001",
    "processingLevel": "GCOV",
    "maturity": "PROVISIONAL",
    "startTime": "2026-06-20T10:30:00Z",
    "stopTime": "2026-06-20T10:35:00Z",
    "flightDirection": "ASCENDING",
    "polarization": "VV+VH",
    "url": "https://datapool.asf.alaska.edu/GCOV/NISAR/example.h5",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-90.1, 16.0], [-89.5, 16.0], [-89.5, 16.6], [-90.1, 16.6], [-90.1, 16.0]]
        ],
    },
}


def test_maps_required_fields():
    payload = map_asf_product(SAMPLE)

    assert payload is not None
    assert payload["product_type"] == "GCOV"
    assert payload["polarization"] == ["VV", "VH"]
    assert payload["acquisition_start"].isoformat().startswith("2026-06-20T10:30")
    assert payload["footprint_wkt"].startswith("MULTIPOLYGON")


def test_skips_products_without_geometry():
    assert map_asf_product({**SAMPLE, "geometry": None}) is None
    assert map_asf_product({**SAMPLE, "fileID": None, "sceneName": None}) is None
