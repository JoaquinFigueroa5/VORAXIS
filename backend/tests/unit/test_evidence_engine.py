from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.exceptions import AppError
from app.evidence import classification, collection, interpretation, scoring, temporal_analysis
from app.evidence.profiles import PROFILES, window
from app.integrations.auxiliary import firms_client, power_client

BEFORE = datetime(2026, 10, 2, 0, 24, tzinfo=UTC)
AFTER = datetime(2026, 10, 14, 0, 24, tzinfo=UTC)


def _score(distance_km, event_date, profile="EARTHQUAKE", event_strength=1.0):
    p = PROFILES[profile]
    return scoring.score(
        distance_km=distance_km,
        radius_km=p.radius_km,
        event_date=event_date,
        before=BEFORE,
        after=AFTER,
        lead_days=p.lead_days,
        event_strength=event_strength,
    )


# --- scoring -----------------------------------------------------------------


def test_score_is_full_between_the_acquisitions_and_falls_with_distance():
    inside = BEFORE + timedelta(days=5)
    assert _score(0, inside) == 1.0
    assert _score(50, inside) == 0.0
    assert 0.0 < _score(25, inside) < 1.0


def test_events_after_the_second_acquisition_cannot_explain_the_change():
    assert _score(0, AFTER + timedelta(hours=1)) == 0.0


def test_lead_time_depends_on_the_phenomenon():
    three_days_early = BEFORE - timedelta(days=3)
    assert _score(0, three_days_early, "EARTHQUAKE") == 0.0  # 1 day of lead
    assert _score(0, three_days_early, "FIRE") == pytest.approx(0.4)  # 5 days
    assert _score(0, three_days_early, "PRECIPITATION") == pytest.approx(4 / 7, abs=1e-3)


def test_radius_depends_on_the_phenomenon():
    inside = BEFORE + timedelta(days=1)
    assert _score(3, inside, "FIRE") == 0.0  # a fire 3 km away is another fire
    assert _score(3, inside, "EARTHQUAKE") > 0.9


def test_search_window_starts_before_the_first_acquisition():
    start, end = window(PROFILES["FIRE"], BEFORE, AFTER)
    assert start == BEFORE - timedelta(days=5) and end == AFTER


def test_event_strength():
    assert scoring.strength("EARTHQUAKE", 6.0, None) == 1.0
    assert scoring.strength("EARTHQUAKE", 4.5, None) == pytest.approx(0.5)
    assert scoring.strength("FIRE", 10.0, {"confidence": "high"}) == 1.0
    assert scoring.strength("FIRE", 10.0, {"confidence": "low"}) == 0.5
    dry = scoring.strength("PRECIPITATION", 3.0, {"total_mm": 3.0, "anomaly_pct": -80.0})
    wet = scoring.strength("PRECIPITATION", 180.0, {"total_mm": 180.0, "anomaly_pct": 90.0})
    assert dry < 0.1 and wet == 1.0
    seasonal = scoring.strength("PRECIPITATION", 151.0, {"total_mm": 151.0, "anomaly_pct": -4.0})
    assert seasonal == pytest.approx(0.5, abs=0.01)  # a lot of rain, but the usual amount


def test_explanation_does_not_claim_causation():
    text = interpretation.explain(
        source="USGS",
        event_type="EARTHQUAKE",
        distance_km=12.0,
        hours=-8.5,
        intersects=False,
        relation="NEAR",
        magnitude=5.4,
    )

    assert "not a demonstrated cause" in text
    assert "12.0 km" in text and "M5.4" in text


def test_hours_between_is_signed():
    reference = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    assert temporal_analysis.hours_between(reference, reference - timedelta(hours=8)) == -8.0


# --- FIRMS -------------------------------------------------------------------

FIRMS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
16.71234,-90.31234,335.2,0.4,0.4,2026-10-05,1842,N20,VIIRS,h,2.0NRT,295.1,12.4,D
16.72000,-90.30000,310.0,0.4,0.4,2026-10-06,612,N20,VIIRS,n,2.0NRT,290.0,3.1,N
,,300.0,0.4,0.4,2026-10-06,0612,N20,VIIRS,l,2.0NRT,290.0,1.0,N
"""


def test_firms_csv_becomes_fire_events():
    events = firms_client.parse_csv(FIRMS_CSV, "VIIRS_NOAA20_NRT")

    assert len(events) == 2  # the row without a position is dropped
    first, second = events
    assert first["event_type"] == "FIRE" and first["source"] == "FIRMS"
    assert first["event_date"] == datetime(2026, 10, 5, 18, 42, tzinfo=UTC)
    assert second["event_date"] == datetime(2026, 10, 6, 6, 12, tzinfo=UTC)  # "612" -> 06:12
    assert (first["latitude"], first["longitude"]) == (16.71234, -90.31234)
    assert first["magnitude"] == 12.4
    assert first["metadata"]["confidence"] == "high"
    assert second["metadata"]["confidence"] == "nominal"
    assert first["external_id"] != second["external_id"]


def test_firms_error_text_is_not_parsed_as_no_fires():
    with pytest.raises(AppError, match="Invalid MAP_KEY"):
        firms_client.parse_csv("Invalid MAP_KEY.", "VIIRS_NOAA20_NRT")


def test_firms_header_only_means_no_detections():
    assert firms_client.parse_csv(FIRMS_CSV.splitlines()[0] + "\n", "VIIRS_NOAA20_NRT") == []


class _FirmsHttp:
    """Stands in for httpx.Client: answers per collection name found in the URL."""

    def __init__(self, answers):
        self.answers, self.urls = answers, []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, url):
        self.urls.append(url)
        collection = url.split("/")[-4]

        class Response:
            text = self.answers.get(collection, FIRMS_CSV.splitlines()[0] + "\n")

            def raise_for_status(self):
                pass

        return Response()


def _firms(monkeypatch, answers):
    http = _FirmsHttp(answers)
    monkeypatch.setattr(firms_client.settings, "firms_api_key", "test-key")
    monkeypatch.setattr(firms_client.httpx, "Client", lambda **_: http)
    events = firms_client.FirmsClient().fetch_events(
        bbox=(80.0, 15.6, 81.5, 16.6), start=BEFORE, end=BEFORE + timedelta(days=7)
    )
    return events, http


def test_firms_queries_the_current_satellites_and_survives_a_retired_one(monkeypatch):
    events, http = _firms(
        monkeypatch, {"VIIRS_NOAA21_NRT": FIRMS_CSV, "VIIRS_SNPP_NRT": "Invalid source."}
    )

    assert len(events) == 2  # NOAA-21 detections kept although S-NPP failed
    collections = [url.split("/")[-4] for url in http.urls]
    assert {"VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT"} <= set(collections)
    assert collections.count("VIIRS_SNPP_NRT") == 1  # not retried for the second chunk
    assert collections.count("VIIRS_NOAA21_NRT") == 2  # 8 days = two 5-day requests
    assert not any("_SP" in name for name in collections)  # archive only when NRT is empty


def test_firms_fails_only_when_no_collection_answers(monkeypatch):
    bad = dict.fromkeys(firms_client.NRT_SOURCES + firms_client.ARCHIVE_SOURCES, "Invalid MAP_KEY.")
    with pytest.raises(AppError, match="no FIRMS collection answered"):
        _firms(monkeypatch, bad)


# --- POWER -------------------------------------------------------------------


def test_precipitation_cell_contains_the_point():
    west, south, east, north = power_client.cell_bounds(-90.33, 16.67)
    assert west <= -90.33 < east and south <= 16.67 < north
    assert east - west == 0.625 and north - south == 0.5


def test_precipitation_summary_totals_and_anomaly():
    daily = {"20261001": 0.0, "20261002": 40.0, "20261003": 90.0, "20261004": None}
    climatology = {"OCT": 10.0}

    summary = power_client.summarise(daily, climatology, date(2026, 10, 1), date(2026, 10, 4))

    assert summary["total_mm"] == 130.0
    assert summary["expected_mm"] == 30.0  # three days with data at 10 mm/day
    assert summary["anomaly_pct"] == pytest.approx(333.3, abs=0.1)
    assert summary["max_daily_mm"] == 90.0 and summary["peak_date"] == "2026-10-03"
    assert summary["days_with_data"] == 3 and summary["days_requested"] == 4


def test_precipitation_without_data_is_none_not_zero():
    assert power_client.summarise({}, {"OCT": 10.0}, date(2026, 10, 1), date(2026, 10, 4)) is None


def test_precipitation_cells_follow_the_changed_area():
    points = [(-90.30, 16.60, 5.0), (-90.31, 16.61, 2.0), (-89.10, 17.40, 0.5)]
    cells = collection.precipitation_cells(points)

    assert len(cells) == 2
    west, south, east, north = power_client.cell_bounds(-90.30, 16.60)
    assert cells[0] == ((west + east) / 2, (south + north) / 2)  # most area first


# --- classification ----------------------------------------------------------


def _classify(**overrides):
    values = {
        "direction": "DECREASE",
        "mean_change_db": -5.0,
        "before_db": -8.0,
        "after_db": -13.0,
        "polarization": "HH",
        "evidence": [],
    }
    values.update(overrides)
    return classification.classify(**values)


FIRE = {"event_type": "FIRE", "score": 0.6, "magnitude": 14.0, "metadata": {"confidence": "high"}}
RAIN = {
    "event_type": "PRECIPITATION",
    "score": 0.8,
    "magnitude": 160.0,
    "metadata": {"total_mm": 160.0, "anomaly_pct": 120.0},
}
QUAKE = {"event_type": "EARTHQUAKE", "score": 0.5, "magnitude": 6.1, "metadata": {}}


def test_fire_nearby_and_a_drop_is_a_possible_burn_scar():
    result = _classify(evidence=[FIRE])
    assert result.change_type == "POSSIBLE_BURN_SCAR" and result.confidence == "MEDIUM"
    assert "FIRMS" in result.reasons[0]


def test_fire_with_a_rise_stays_a_weak_hypothesis():
    result = _classify(direction="INCREASE", mean_change_db=3.0, after_db=-5.0, evidence=[FIRE])
    assert result.change_type == "POSSIBLE_BURN_SCAR" and result.confidence == "LOW"


def test_drop_to_water_level_is_possible_flooding_and_rain_raises_confidence():
    dry = _classify(mean_change_db=-11.0, after_db=-19.0)
    wet = _classify(mean_change_db=-11.0, after_db=-19.0, evidence=[RAIN])

    assert dry.change_type == wet.change_type == "POSSIBLE_FLOODING"
    assert (dry.confidence, wet.confidence) == ("LOW", "MEDIUM")
    assert "160 mm" in wet.reasons[1]


def test_water_thresholds_follow_the_polarization():
    assert _classify(before_db=-13.0, after_db=-19.0, mean_change_db=-6.0).change_type == "POSSIBLE_FLOODING"
    # -19 dB in cross-pol is ordinary land, not water.
    cross = _classify(before_db=-13.0, after_db=-19.0, mean_change_db=-6.0, polarization="HV")
    assert cross.change_type != "POSSIBLE_FLOODING"


def test_seasonal_rain_does_not_support_a_flood_hypothesis():
    seasonal = {**RAIN, "magnitude": 151.0, "metadata": {"total_mm": 151.0, "anomaly_pct": -4.0}}
    result = _classify(mean_change_db=-11.0, after_db=-19.0, evidence=[seasonal])
    assert result.change_type == "POSSIBLE_FLOODING" and result.confidence == "LOW"


def test_strong_drop_under_anomalous_rain_is_partial_flooding_not_vegetation_loss():
    kwargs = {"mean_change_db": -5.5, "before_db": -8.0, "after_db": -13.5}
    assert _classify(**kwargs).change_type == "POSSIBLE_VEGETATION_LOSS"
    wet = _classify(**kwargs, evidence=[RAIN])
    assert wet.change_type == "POSSIBLE_FLOODING" and wet.confidence == "LOW"
    assert "parcial" in wet.reasons[0]


def test_rise_after_heavy_rain_is_possible_flooded_vegetation():
    result = _classify(direction="INCREASE", mean_change_db=3.0, after_db=-5.0, evidence=[RAIN])
    assert result.change_type == "POSSIBLE_FLOODED_VEGETATION"


def test_water_that_brightens_is_possible_recession():
    result = _classify(direction="INCREASE", mean_change_db=8.0, before_db=-20.0, after_db=-12.0)
    assert result.change_type == "POSSIBLE_WATER_RECESSION"


def test_drop_over_dense_vegetation_without_fire_is_possible_vegetation_loss():
    result = _classify(mean_change_db=-3.0, before_db=-7.0, after_db=-10.0)
    assert result.change_type == "POSSIBLE_VEGETATION_LOSS"


def test_strong_earthquake_alone_is_a_low_confidence_hypothesis():
    result = _classify(mean_change_db=-1.5, before_db=-12.0, after_db=-13.5, evidence=[QUAKE])
    assert result.change_type == "POSSIBLE_SEISMIC_DISTURBANCE" and result.confidence == "LOW"
    assert "GUNW" in result.reasons[1]


def test_nothing_fits_stays_unclassified():
    result = _classify(mean_change_db=-1.5, before_db=-12.0, after_db=-13.5)
    assert result.change_type == "UNCLASSIFIED" and result.confidence == "NONE"
    assert result.label == "Cambio sin clasificar"


def test_every_label_fits_the_column_and_has_a_spanish_name():
    for change_type, label in classification.LABELS_ES.items():
        assert len(change_type) <= 50 and label


# --- collection --------------------------------------------------------------


class _Db:
    def commit(self):
        pass

    def rollback(self):
        pass


class _Usgs:
    def fetch_events(self, **kwargs):
        self.kwargs = kwargs
        return []


class _Firms:
    configured = False


class _Power:
    def fetch_event(self, **kwargs):
        raise RuntimeError("timeout")


def test_collection_reports_each_source_and_never_raises(monkeypatch):
    monkeypatch.setattr(collection, "EvidenceRepository", lambda: None)
    usgs = _Usgs()

    report = collection.collect(
        _Db(),
        bbox=(-90.4, 16.5, -90.2, 16.8),
        points=[(-90.3, 16.6, 1.0)],
        before=BEFORE,
        after=AFTER,
        usgs=usgs,
        firms=_Firms(),
        power=_Power(),
    )

    assert report["USGS"] == {
        "status": "ok",
        "event_type": "EARTHQUAKE",
        "events_found": 0,
        "events_stored": 0,
    }
    assert report["FIRMS"]["status"] == "skipped" and "FIRMS_API_KEY" in report["FIRMS"]["detail"]
    assert report["POWER"]["status"] == "error" and "timeout" in report["POWER"]["detail"]
    assert usgs.kwargs["bbox"][0] == pytest.approx(-90.9)  # search margin applied
    assert usgs.kwargs["start"] == BEFORE - timedelta(days=1)


def test_a_distant_fire_does_not_override_the_radar_signature():
    far_fire = {**FIRE, "score": 0.3}
    result = _classify(mean_change_db=-11.0, after_db=-19.0, evidence=[far_fire, RAIN])
    assert result.change_type == "POSSIBLE_FLOODING"
