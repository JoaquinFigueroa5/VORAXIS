"""Ingestion bookkeeping with in-memory repositories (no database, no MinIO)."""

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import rasterio
from shapely.geometry import box, mapping

from app.core.exceptions import AppError, NotFoundError, ProcessingError
from app.services.ingest_service import IngestService, _parse_time
from scripts.make_synthetic_gcov import product_name, write_gcov

START = datetime(2026, 10, 30, 23, 40, 59, tzinfo=UTC)
PETEN = box(-90.62, 15.92, -88.98, 17.82)


class FakeDb:
    def __init__(self):
        self.rows = {}
        self.commits = 0
        self.rollbacks = 0

    def get(self, _model, key):
        return self.rows.get(key)

    def add(self, _row):
        pass

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeLocations:
    def __init__(self, geometry=PETEN):
        self.location = SimpleNamespace(id=uuid.uuid4(), name="Petén")
        self.geometry = geometry

    def get(self, _db, location_id):
        if location_id != self.location.id:
            return None
        return self.location, json.dumps(mapping(self.geometry))

    def get_model_by_name(self, _db, name):
        return self.location if name == self.location.name else None


class FakeScenes:
    def __init__(self):
        self.by_product = {}

    def get_by_product_id(self, _db, product_id):
        return self.by_product.get(product_id)

    def upsert(self, db, *, product_id, **fields):
        scene = SimpleNamespace(id=uuid.uuid4(), product_id=product_id, **fields)
        self.by_product[product_id] = scene
        db.rows[scene.id] = scene
        return scene


class FakeObservations:
    def __init__(self):
        self.rows = []

    def list(self, _db, *, scene_id, location_id, limit=50):
        return [o for o in self.rows if o.scene_id == scene_id and o.location_id == location_id]

    def create(self, _db, **fields):
        row = SimpleNamespace(id=uuid.uuid4(), storage_status="DISCOVERED", **fields)
        self.rows.append(row)
        return row


class FakeRasters:
    def __init__(self):
        self.rows = []

    def source_for_observation(self, _db, observation_id):
        return next((a for a in self.rows if a.observation_id == observation_id), None)

    def delete(self, _db, asset):
        self.rows.remove(asset)

    def create(self, _db, *, metadata=None, **fields):
        row = SimpleNamespace(id=uuid.uuid4(), extra_metadata=metadata, **fields)
        self.rows.append(row)
        return row


class FakeStorage:
    def __init__(self):
        self.uploads = {}

    def ensure_bucket(self):
        pass

    def upload_file(self, local_path, key, content_type="application/octet-stream"):
        with rasterio.open(local_path) as cog:  # the file must still exist here
            self.uploads[key] = (cog.count, cog.descriptions, cog.tags(ns="IMAGE_STRUCTURE"))
        return key


class NoEarthdata:
    def download(self, _url, _destination, progress=None):
        return False


class FakeAsf:
    def __init__(self, product=None):
        self.product = product

    def find_product(self, product_id):
        return self.product


@pytest.fixture()
def granule(tmp_path):
    return write_gcov(tmp_path / f"{product_name(START, 34)}.h5", start=START, shape=(200, 250))


@pytest.fixture()
def service():
    return IngestService(
        scenes=FakeScenes(),
        observations=FakeObservations(),
        rasters=FakeRasters(),
        locations=FakeLocations(),
        earthdata=NoEarthdata(),
        storage=FakeStorage(),
        asf=FakeAsf(),
    )


def test_local_file_registers_scene_observation_and_source_asset(service, granule):
    db = FakeDb()

    result = service.ingest(db, location_name="Petén", h5_path=granule)

    scene = service.scenes.by_product[granule.stem]
    assert scene.product_type == "GCOV"
    assert scene.polarization == ["HH", "HV"]
    assert scene.acquisition_start == START
    assert scene.orbit_direction == "ASCENDING"
    assert scene.footprint_wkt.startswith("MULTIPOLYGON")

    (observation,) = service.observations.rows
    assert observation.storage_status == "READY"
    assert observation.processing_version == "P05036"
    assert observation.acquisition_date == START

    (asset,) = service.rasters.rows
    assert asset.asset_type == "SOURCE" and asset.format == "COG"
    assert asset.crs == "EPSG:32615"
    assert asset.storage_path == f"sources/{observation.id}/{granule.stem}.tif"
    assert asset.extra_metadata["polarizations"] == ["HH", "HV"]
    assert asset.extra_metadata["units"] == "dB"
    assert (asset.extra_metadata["track"], asset.extra_metadata["frame"]) == (98, 19)
    json.dumps(asset.extra_metadata)  # must fit a JSONB column

    count, descriptions, structure = service.storage.uploads[asset.storage_path]
    assert count == 2 and descriptions == ("HH", "HV") and structure["LAYOUT"] == "COG"
    assert result.storage_path == asset.storage_path and not result.skipped


def test_second_run_is_a_no_op_unless_forced(service, granule):
    db = FakeDb()
    first = service.ingest(db, location_name="Petén", h5_path=granule)
    service.storage.uploads.clear()

    again = service.ingest(db, location_name="Petén", h5_path=granule)
    assert again.skipped and again.observation_id == first.observation_id
    assert not service.storage.uploads

    forced = service.ingest(
        db, location_name="Petén", h5_path=granule, force=True, polarizations=["HH"]
    )
    assert not forced.skipped
    assert len(service.observations.rows) == 1 and len(service.rasters.rows) == 1
    assert service.rasters.rows[0].extra_metadata["polarizations"] == ["HH"]


def test_failure_marks_the_observation_failed(granule):
    service = IngestService(
        scenes=FakeScenes(),
        observations=FakeObservations(),
        rasters=FakeRasters(),
        locations=FakeLocations(geometry=box(-70.7, -33.3, -70.0, -32.5)),
        earthdata=NoEarthdata(),
        storage=FakeStorage(),
    )
    db = FakeDb()

    with pytest.raises(ProcessingError, match="does not overlap"):
        service.ingest(db, location_name="Petén", h5_path=granule)

    assert service.observations.rows[0].storage_status == "FAILED"
    assert not service.rasters.rows and db.rollbacks == 1


def test_download_without_credentials_explains_what_to_do(service, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.ingest_service.settings.nisar_data_dir", str(tmp_path))
    scene = service.scenes.upsert(
        FakeDb(), product_id="NISAR_X", product_type="GCOV", source_url="https://example.invalid/x.h5"
    )
    with pytest.raises(AppError, match="EARTHDATA_USERNAME"):
        service.ingest(FakeDb(), location_name="Petén", product_id=scene.product_id)


def test_unknown_inputs_are_rejected(service, granule):
    with pytest.raises(NotFoundError):
        service.ingest(FakeDb(), location_name="Nowhere", h5_path=granule)
    with pytest.raises(NotFoundError, match="ASF does not list it"):
        service.ingest(FakeDb(), location_name="Petén", product_id="NISAR_MISSING")
    with pytest.raises(AppError, match="scene id, a product id or an .h5"):
        service.ingest(FakeDb(), location_name="Petén")


def test_nisar_nanosecond_timestamps_parse():
    assert _parse_time("2026-11-11T23:40:59.123456789") == datetime(
        2026, 11, 11, 23, 40, 59, 123456, tzinfo=UTC
    )
    assert _parse_time("2026-11-11T23:40:59Z") == datetime(2026, 11, 11, 23, 40, 59, tzinfo=UTC)
    assert _parse_time("") is None


def test_progress_is_reported_through_every_stage(service, granule):
    stages = []
    service.ingest(
        FakeDb(),
        location_name="Petén",
        h5_path=granule,
        on_progress=lambda stage, detail=None: stages.append(stage),
    )
    assert stages == ["CONVERTING", "UPLOADING", "READY"]  # a local file is not downloaded


def test_product_missing_from_the_catalogue_is_fetched_from_asf(service, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.ingest_service.settings.nisar_data_dir", str(tmp_path))
    name = "NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001"
    service.asf = FakeAsf(
        {
            "sceneName": name,
            "processingLevel": "GCOV",
            "startTime": "2026-11-03T13:09:53Z",
            "stopTime": "2026-11-03T13:10:27Z",
            "flightDirection": "DESCENDING",
            "mainBandPolarization": ["HH", "HV"],
            "url": f"https://example.invalid/{name}.h5",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[79.3, 15.5], [82.2, 15.5], [82.2, 18.2], [79.3, 18.2], [79.3, 15.5]]],
            },
        }
    )

    # The scene gets registered, then the download stops for lack of credentials.
    with pytest.raises(AppError, match="EARTHDATA_USERNAME"):
        service.ingest(FakeDb(), location_name="Petén", product_id=name)

    scene = service.scenes.by_product[name]
    assert scene.product_type == "GCOV" and scene.source_url.endswith(".h5")
    assert scene.polarization == ["HH", "HV"]
