"""Validation and small pure helpers behind the endpoints the frontend drives."""

from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError, ConflictError
from app.schemas.location import LocationCreate
from app.services import ingest_task_service
from app.services.analysis_service import compatibility_warnings
from app.services.change_service import tolerance_for_zoom
from app.services.location_service import LocationService

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[80.9, 16.0], [81.4, 16.0], [81.4, 16.5], [80.9, 16.5], [80.9, 16.0]]],
}


# --- locations ---------------------------------------------------------------


class FakeLocations:
    def __init__(self, existing=()):
        self.names = set(existing)
        self.created = None

    def get_model_by_name(self, _db, name):
        return SimpleNamespace(name=name) if name in self.names else None

    def create(self, _db, **fields):
        self.created = fields
        return SimpleNamespace(id="new-id")


def _create(payload, repo=None):
    service = LocationService(repo or FakeLocations())
    service.get = lambda _db, location_id: location_id  # no database in this test
    return service.create(None, LocationCreate(**payload)), service.repo


def test_location_from_bbox_is_stored_as_a_multipolygon():
    result, repo = _create({"name": "  Machilipatnam ", "country": "India", "bbox": [80.9, 16.0, 81.4, 16.5]})

    assert result == "new-id"
    assert repo.created["name"] == "Machilipatnam"
    assert repo.created["geometry_wkt"].startswith("MULTIPOLYGON")


def test_location_accepts_a_geojson_polygon_or_feature():
    _, repo = _create({"name": "a", "geometry": SQUARE})
    assert repo.created["geometry_wkt"].startswith("MULTIPOLYGON")
    _, repo = _create({"name": "b", "geometry": {"type": "Feature", "properties": {}, "geometry": SQUARE}})
    assert repo.created["geometry_wkt"].startswith("MULTIPOLYGON")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"name": "x"}, "exactly one of"),
        ({"name": "x", "bbox": [1, 1, 2, 2], "geometry": SQUARE}, "exactly one of"),
        ({"name": "x", "bbox": [81.4, 16.0, 80.9, 16.5]}, "west < east"),
        ({"name": "x", "bbox": [70, 10, 80, 20]}, "maximum is 3 per side"),
        ({"name": "x", "bbox": [80.0, 16.0, 80.001, 16.001]}, "too small"),
        ({"name": "x", "bbox": [200, 16.0, 201, 16.5]}, "longitude/latitude"),
        ({"name": "x", "geometry": {"type": "Point", "coordinates": [81, 16]}}, "Polygon or MultiPolygon"),
        ({"name": "x", "geometry": {"type": "Polygon"}}, "not valid GeoJSON"),
        ({"name": "   ", "bbox": [80.9, 16.0, 81.4, 16.5]}, "must not be blank"),
    ],
)
def test_location_rejects_bad_input_with_a_reason(payload, message):
    with pytest.raises(AppError, match=message):
        _create(payload)


def test_location_name_must_be_unique():
    with pytest.raises(ConflictError, match="already exists"):
        _create({"name": "Petén", "bbox": [80.9, 16.0, 81.4, 16.5]}, FakeLocations(existing={"Petén"}))


# --- analysis ----------------------------------------------------------------


def test_different_processing_versions_warn_instead_of_blocking():
    before = SimpleNamespace(processing_version="P05023")
    after = SimpleNamespace(processing_version="P05036")

    (warning,) = compatibility_warnings(before, after)
    assert "P05023" in warning and "P05036" in warning
    assert compatibility_warnings(before, before) == []
    assert compatibility_warnings(SimpleNamespace(processing_version=None), after) == []


# --- changes -----------------------------------------------------------------


def test_simplification_follows_the_map_zoom():
    assert tolerance_for_zoom(None) == 0.0  # keep every vertex
    assert tolerance_for_zoom(0) == pytest.approx(360 / 256)
    assert tolerance_for_zoom(10) == pytest.approx(360 / 256 / 1024)
    assert tolerance_for_zoom(8) > tolerance_for_zoom(12)
    assert tolerance_for_zoom(99) == tolerance_for_zoom(22)  # clamped


# --- ingestion tasks ---------------------------------------------------------


class FakeJob:
    def __init__(self, status, meta=None, result=None, exc_info=None):
        self.id = "task-1"
        self._status, self.meta, self._result, self.exc_info = status, meta or {}, result, exc_info
        self.enqueued_at = self.started_at = self.ended_at = None

    def get_status(self, refresh=True):
        return self._status

    def return_value(self):
        return self._result


def test_running_task_reports_stage_and_progress():
    job = FakeJob(
        SimpleNamespace(value="started"),  # RQ hands back an enum
        meta={"product_id": "P", "location_id": "L", "stage": "DOWNLOADING", "progress": 37, "detail": "1.80 GB de 4.89 GB"},
    )
    task = ingest_task_service.to_out(job)

    assert (task.status, task.stage, task.progress) == ("RUNNING", "DOWNLOADING", 37)
    assert task.detail == "1.80 GB de 4.89 GB" and task.result is None


def test_finished_task_is_ready_with_its_observation():
    job = FakeJob("finished", meta={"stage": "UPLOADING", "progress": 93}, result={"observation_id": "obs-1"})
    task = ingest_task_service.to_out(job)

    assert (task.status, task.stage, task.progress) == ("COMPLETED", "READY", 100)
    assert task.result == {"observation_id": "obs-1"}


def test_failed_task_shows_the_message_not_the_traceback():
    trace = 'Traceback (most recent call last):\n  File "x.py", line 1\napp.core.exceptions.AppError: the AOI does not overlap the frame\n'
    task = ingest_task_service.to_out(FakeJob("failed", exc_info=trace))

    assert task.status == "FAILED"
    assert task.error == "app.core.exceptions.AppError: the AOI does not overlap the frame"


def test_ingest_rejects_names_that_are_not_gcov(monkeypatch):
    from app.schemas.ingest import IngestRequest

    service = ingest_task_service.IngestTaskService(earthdata=SimpleNamespace(configured=True))
    db = SimpleNamespace(get=lambda _model, _id: SimpleNamespace(id=_id))
    location = "07cc3f73-da30-447c-992f-fb4a4536aa9d"

    with pytest.raises(AppError, match="not a NISAR granule name"):
        service.create(db, IngestRequest(location_id=location, product_ids=["hola"]))
    gslc = "NISAR_L2_PR_GSLC_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001"
    with pytest.raises(AppError, match="only GCOV"):
        service.create(db, IngestRequest(location_id=location, product_ids=[gslc]))


def test_ingest_needs_credentials_unless_the_file_is_already_there(tmp_path, monkeypatch):
    from app.schemas.ingest import IngestRequest

    monkeypatch.setattr(ingest_task_service.settings, "nisar_data_dir", str(tmp_path))
    name = "NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001"
    queued = []
    monkeypatch.setattr(ingest_task_service, "enqueue_ingest", lambda location_id, **options: queued.append(options) or "task-1")
    service = ingest_task_service.IngestTaskService(earthdata=SimpleNamespace(configured=False))
    service.get = lambda task_id: task_id
    db = SimpleNamespace(get=lambda _model, _id: SimpleNamespace(id=_id))
    request = IngestRequest(location_id="07cc3f73-da30-447c-992f-fb4a4536aa9d", product_ids=[f"{name}.h5", name])

    with pytest.raises(AppError, match="Earthdata credentials"):
        service.create(db, request)

    (tmp_path / f"{name}.h5").write_bytes(b"cached")
    assert service.create(db, request) == ["task-1"]  # duplicates and the .h5 suffix collapse
    assert queued == [{"product_id": name, "polarizations": None, "multilook": 4, "force": False}]
