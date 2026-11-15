"""Point lookups with fake upstream clients (no network)."""

from datetime import UTC, date, datetime

import pytest

from app.core import cache
from app.core.exceptions import AppError, UpstreamError
from app.services import context_service
from app.services.context_service import (
    ContextService,
    comparable_pairs,
    haversine_km,
    resolve_window,
    trim_granule,
)

LAT, LON = 16.30, 81.10
WINDOW = {"start": date(2026, 10, 15), "end": date(2026, 11, 5)}


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()
    yield
    cache.clear()


def _product(level, track, frame, start, crid="P05036", size=5_000_000_000, pol="HH"):
    name = f"NISAR_L2_PR_{level}_{track:03d}_{frame:03d}_{start[:10]}"
    return {
        "sceneName": name,
        "processingLevel": level,
        "pathNumber": track,
        "frameNumber": frame,
        "flightDirection": "DESCENDING",
        "mainBandPolarization": [pol, "HV"],
        "polarization": None,
        "crid": crid,
        "startTime": start,
        "stopTime": start,
        "bytes": {f"{name}.h5": {"bytes": size}, f"{name}_QA_STATS.h5": {"bytes": 70_000}},
        "browse": [f"https://x/{name}_NATIVE.png", f"https://x/{name}_LATLON.png"],
        "url": f"https://x/{name}.h5",
        "geometry": {"type": "Polygon", "coordinates": []},
    }


class FakeAsf:
    def __init__(self, products):
        self.products, self.calls = products, 0

    def search_point(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        level = kwargs.get("processing_level")
        return [p for p in self.products if level is None or p["processingLevel"] == level]


class FakeUsgs:
    def fetch_radius(self, **kwargs):
        self.kwargs = kwargs
        return [
            {
                "external_id": "us1",
                "event_date": datetime(2026, 10, 20, 3, 0, tzinfo=UTC),
                "latitude": 16.30,
                "longitude": 82.10,
                "depth_km": 10.0,
                "magnitude": 5.2,
                "metadata": {"place": "Bay of Bengal", "url": "https://usgs/us1"},
            },
            {
                "external_id": "us2",
                "event_date": datetime(2026, 10, 25, 3, 0, tzinfo=UTC),
                "latitude": 16.40,
                "longitude": 81.10,
                "depth_km": 5.0,
                "magnitude": 3.1,
                "metadata": {"place": "near Machilipatnam"},
            },
        ]


class FakePower:
    def __init__(self, series):
        self.series = series

    def fetch_series(self, **kwargs):
        self.kwargs = kwargs
        return None if self.series is None else dict(self.series)


class FakeFirms:
    def __init__(self, configured=True):
        self.configured = configured

    def fetch_events(self, **kwargs):
        self.kwargs = kwargs
        return [
            {
                "event_date": datetime(2026, 10, 26, 7, 0, tzinfo=UTC),
                "latitude": 16.31,
                "longitude": 81.11,
                "magnitude": 4.0,
                "metadata": {"confidence": "nominal", "satellite": "N20", "collection": "VIIRS_NOAA20_NRT"},
            },
            {
                "event_date": datetime(2026, 10, 26, 19, 0, tzinfo=UTC),
                "latitude": 16.32,
                "longitude": 81.12,
                "magnitude": 9.0,
                "metadata": {"confidence": "high"},
            },
            {  # in the bbox corner but outside the radius
                "event_date": datetime(2026, 10, 27, 7, 0, tzinfo=UTC),
                "latitude": 16.74,
                "longitude": 81.55,
                "magnitude": 2.0,
                "metadata": {},
            },
        ]


RAIN = {
    "total_mm": 130.0,
    "expected_mm": 60.0,
    "anomaly_pct": 116.7,
    "max_daily_mm": 71.0,
    "peak_date": "2026-11-03",
    "window_start": "2026-10-15",
    "window_end": "2026-11-05",
    "days_with_data": 3,
    "days_requested": 3,
    "daily_mm": {"2026-10-28": 42.0, "2026-11-02": 17.0, "2026-11-03": 71.0},
    "elevation_m": 18.0,
    "endpoint": "https://power/daily?x=1",
}

PRODUCTS = [
    _product("GCOV", 149, 80, "2026-10-10T13:09:52Z", crid="P05023"),
    _product("GCOV", 149, 80, "2026-10-22T13:09:52Z"),
    _product("GCOV", 149, 80, "2026-11-03T13:09:53Z"),
    _product("GCOV", 156, 10, "2026-11-04T00:09:14Z"),
    _product("GSLC", 149, 80, "2026-11-03T13:09:53Z", size=22_000_000_000),
]


def _service(**overrides):
    clients = {
        "asf": FakeAsf(PRODUCTS),
        "usgs": FakeUsgs(),
        "power": FakePower(RAIN),
        "firms": FakeFirms(),
    }
    clients.update(overrides)
    return ContextService(**clients)


def test_haversine_and_window():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.19, abs=0.05)
    assert haversine_km(LAT, LON, LAT, LON) == 0
    assert resolve_window(30, date(2026, 10, 1), date(2026, 10, 14)) == (date(2026, 10, 1), date(2026, 10, 14))
    first, last = resolve_window(7, None, date(2026, 10, 14))
    assert (first, last) == (date(2026, 10, 8), date(2026, 10, 14))
    with pytest.raises(AppError, match="start must not be after end"):
        resolve_window(7, date(2026, 11, 1), date(2026, 10, 1))


def test_granule_keeps_what_the_map_needs():
    granule = trim_granule(PRODUCTS[1])

    assert granule["level"] == "GCOV" and (granule["track"], granule["frame"]) == (149, 80)
    assert granule["polarization"] == ["HH", "HV"]  # falls back to mainBandPolarization
    assert granule["size_gb"] == 5.0  # the science file, not the QA sidecar
    assert granule["browse_png"].endswith("_LATLON.png")
    assert granule["download_url"].endswith(".h5")
    assert isinstance(granule["age_days"], int)


def test_nisar_summarises_levels_and_freshness():
    result = _service().nisar(latitude=LAT, longitude=LON, **WINDOW)

    assert result["total"] == 5 and result["has_gcov"]
    assert result["count_by_level"] == {"GCOV": 4, "GSLC": 1}
    assert result["latest_by_level"]["GCOV"]["start"] == "2026-11-04T00:09:14Z"
    assert [g["start"] for g in result["granules"]] == sorted(
        (g["start"] for g in result["granules"]), reverse=True
    )
    assert result["source"] and result["retrieved_at"] and result["query"]["level"] == "ALL"


def test_comparable_pairs_are_consecutive_dates_of_one_track_and_frame():
    pairs = comparable_pairs([trim_granule(p) for p in PRODUCTS])

    assert len(pairs) == 2  # track 156 has a single date; GSLC is not GCOV
    newest, older = pairs
    assert (newest["track"], newest["frame"]) == (149, 80)
    assert newest["before"]["start"][:10] == "2026-10-22" and newest["after"]["start"][:10] == "2026-11-03"
    assert newest["interval_days"] == 12.0 and newest["same_processing_version"] is True
    assert newest["download_gb"] == 10.0
    assert older["same_processing_version"] is False  # P05023 -> P05036


def test_two_files_of_the_same_pass_are_not_a_pair():
    same_pass = [
        trim_granule(_product("GCOV", 48, 80, "2026-10-15T13:01:33Z")),
        trim_granule(_product("GCOV", 48, 80, "2026-10-15T13:01:50Z")),
    ]
    assert comparable_pairs(same_pass) == []


def test_level_filter_and_cache():
    asf = FakeAsf(PRODUCTS)
    service = _service(asf=asf)

    first = service.nisar(latitude=LAT, longitude=LON, level="GCOV", **WINDOW)
    again = service.nisar(latitude=LAT, longitude=LON, level="GCOV", **WINDOW)
    service.nisar(latitude=LAT, longitude=LON, level="ALL", **WINDOW)

    assert all(g["level"] == "GCOV" for g in first["granules"])
    assert again is first and asf.calls == 2  # the repeat came from the cache


def test_earthquakes_carry_distance_nearest_and_strongest():
    usgs = FakeUsgs()
    result = _service(usgs=usgs).earthquakes(latitude=LAT, longitude=LON, radius_km=500, **WINDOW)

    assert result["total"] == 2 and result["max_magnitude"] == 5.2
    assert result["nearest"]["id"] == "us2" and result["nearest"]["distance_km"] == pytest.approx(11.1, abs=0.2)
    assert result["strongest"]["id"] == "us1"
    assert result["data"][0]["id"] == "us2"  # newest first
    assert usgs.kwargs["end"].date() == date(2026, 11, 6)  # exclusive end covers the last day


def test_precipitation_returns_a_series_and_totals():
    result = _service().precipitation(latitude=LAT, longitude=LON, **WINDOW)

    assert result["available"] and result["total_mm"] == 130.0 and result["anomaly_pct"] == 116.7
    assert result["elevation_m"] == 18.0 and result["endpoint"].startswith("https://power")
    assert result["series"][0] == {"date": "2026-10-28", "mm": 42.0}
    assert "daily_mm" not in result


def test_precipitation_without_data_is_reported_not_raised():
    result = _service(power=FakePower(None)).precipitation(latitude=LAT, longitude=LON, **WINDOW)
    assert result["available"] is False and result["series"] == []


def test_fires_are_filtered_to_the_radius_and_counted_per_day():
    firms = FakeFirms()
    result = _service(firms=firms).fires(latitude=LAT, longitude=LON, radius_km=20, **WINDOW)

    assert result["total"] == 2  # the corner detection is 60 km away
    assert result["max_frp_mw"] == 9.0 and result["total_frp_mw"] == 13.0
    assert result["detections_by_day"] == {"2026-10-26": 2}
    assert all(item["distance_km"] <= 20 for item in result["data"])
    west, south, east, north = firms.kwargs["bbox"]
    assert west < LON < east and south < LAT < north


def test_fires_reject_long_windows_and_a_missing_key():
    with pytest.raises(AppError, match="at most 31 days"):
        _service().fires(latitude=LAT, longitude=LON, start=date(2026, 1, 1), end=date(2026, 6, 1))
    with pytest.raises(UpstreamError, match="FIRMS_API_KEY"):
        _service(firms=FakeFirms(configured=False)).fires(latitude=LAT, longitude=LON, **WINDOW)


def test_upstream_failures_become_502_and_are_not_cached():
    class Broken:
        calls = 0

        def fetch_radius(self, **_):
            Broken.calls += 1
            raise RuntimeError("connection reset")

    service = _service(usgs=Broken())
    for _ in range(2):
        with pytest.raises(UpstreamError, match="connection reset") as error:
            service.earthquakes(latitude=LAT, longitude=LON, **WINDOW)
        assert error.value.status_code == 502
    assert Broken.calls == 2


def test_timeline_merges_sources_newest_first_and_survives_one_failing(monkeypatch):
    service = _service(firms=FakeFirms(configured=False))

    result = service.timeline(latitude=LAT, longitude=LON, radius_km=300, **WINDOW)

    assert result["count_by_kind"] == {"nisar": 4, "earthquake": 2, "precipitation": 2, "fire": 0}
    assert result["total"] == 8
    dates = [event["date"] for event in result["events"]]
    assert dates == sorted(dates, reverse=True)
    statuses = {source["source"]: source["status"] for source in result["sources"]}
    assert statuses["NASA FIRMS (VIIRS)"] == "error" and statuses["USGS FDSN"] == "ok"
    rain_days = [event for event in result["events"] if event["kind"] == "precipitation"]
    assert {event["mm"] for event in rain_days} == {42.0, 71.0}  # 17 mm is not a heavy day
    assert context_service.HEAVY_RAIN_DAY_MM == 20.0
