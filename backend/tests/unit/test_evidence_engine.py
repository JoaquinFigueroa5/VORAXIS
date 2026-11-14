from app.evidence import interpretation, scoring, temporal_analysis


def test_score_falls_off_with_distance_and_time():
    close = scoring.score(distance_km=0, radius_km=50, hours=0, window_hours=72)
    far = scoring.score(distance_km=50, radius_km=50, hours=0, window_hours=72)
    late = scoring.score(distance_km=0, radius_km=50, hours=72, window_hours=72)

    assert close == 1.0
    assert far == 0.0
    assert late == 0.0
    assert 0.0 < scoring.score(distance_km=25, radius_km=50, hours=36, window_hours=72) < 1.0


def test_explanation_does_not_claim_causation():
    text = interpretation.explain(
        source="USGS",
        event_type="EARTHQUAKE",
        distance_km=12.0,
        hours=-8.5,
        intersects=False,
        relation="NEAR",
    )

    assert "not a demonstrated cause" in text
    assert "12.0 km" in text


def test_hours_between_is_signed():
    from datetime import UTC, datetime, timedelta

    reference = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    event = reference - timedelta(hours=8)

    assert temporal_analysis.hours_between(reference, event) == -8.0
