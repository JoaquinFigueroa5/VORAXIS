"""Check a running API against the real upstream services (no mocks).

    python scripts/check_api.py                       # http://localhost:8000/api/v1
    python scripts/check_api.py --url http://host:8000/api/v1 --lat 16.3 --lon 81.1

Exits with a non-zero code when any check fails. Checks that depend on data
(an analysed job, a configured FIRMS key) are skipped with a note instead of
failing, so the script is useful on a fresh install too.
"""

import argparse
import sys
from datetime import date, timedelta
from typing import Any

import httpx


class Checker:
    def __init__(self, base: str, timeout: float) -> None:
        self.base = base.rstrip("/")
        self.client = httpx.Client(timeout=timeout)
        self.passed = self.failed = self.skipped = 0

    def get(self, path: str, **params: Any) -> httpx.Response:
        return self.client.get(f"{self.base}{path}", params=params or None)

    def check(self, label: str, condition: bool, detail: str = "") -> bool:
        if condition:
            self.passed += 1
            print(f"  ok    {label}")
        else:
            self.failed += 1
            print(f"  FAIL  {label}" + (f"  ->  {detail}" if detail else ""))
        return condition

    def skip(self, label: str, reason: str) -> None:
        self.skipped += 1
        print(f"  skip  {label}  ({reason})")

    def json(self, label: str, path: str, **params: Any) -> Any | None:
        try:
            response = self.get(path, **params)
        except httpx.HTTPError as exc:
            self.check(f"{label} responds", False, str(exc))
            return None
        if not self.check(f"{label} responds 200", response.status_code == 200, response.text[:200]):
            return None
        return response.json()

    def has_keys(self, label: str, payload: Any, keys: tuple[str, ...]) -> None:
        missing = [key for key in keys if not isinstance(payload, dict) or key not in payload]
        self.check(f"{label} has {', '.join(keys)}", not missing, f"missing {missing}")


def section(title: str) -> None:
    print(f"\n{title}")


def run(base: str, lat: float, lon: float, start: date, end: date, timeout: float) -> int:
    c = Checker(base, timeout)
    point = {"lat": lat, "lon": lon, "start": start.isoformat(), "end": end.isoformat()}
    provenance = ("source", "retrieved_at", "query")

    section("Service")
    health = c.json("health", "/health")
    if health:
        c.check("database reachable", health.get("database") is True)
        c.check("queue reachable", health.get("redis") is True)

    section("Stored data")
    locations = c.json("locations", "/locations")
    if locations is not None:
        c.check("locations is a list", isinstance(locations, list))
        if locations:
            c.has_keys("location", locations[0], ("id", "name", "geometry"))
            c.check("location geometry is GeoJSON", isinstance(locations[0]["geometry"], dict))
    for name, path in (("scenes", "/nisar/scenes"), ("observations", "/observations"), ("jobs", "/jobs")):
        payload = c.json(name, path)
        if payload is not None:
            c.check(f"{name} is a list", isinstance(payload, list))
    insights = c.json("insights", "/insights")
    if insights:
        c.has_keys("insights", insights, ("locations", "scenes", "observations", "change_events"))

    section("Context: NISAR (ASF DAAC)")
    nisar = c.json("context/nisar", "/context/nisar", **point)
    if nisar:
        c.has_keys("nisar", nisar, (*provenance, "total", "latest_by_level", "comparable_pairs", "granules"))
        c.check("nisar found products", nisar["total"] > 0, "no NISAR products over this point")
        if nisar["granules"]:
            granule = nisar["granules"][0]
            c.has_keys("granule", granule, ("product_id", "level", "track", "frame", "start", "age_days", "download_url", "footprint"))
            c.check("granules are newest first", all(a["start"] >= b["start"] for a, b in zip(nisar["granules"], nisar["granules"][1:], strict=False)))
            c.check("granule age is a non-negative integer", isinstance(granule["age_days"], int) and granule["age_days"] >= 0)
        for pair in nisar["comparable_pairs"][:1]:
            c.has_keys("pair", pair, ("track", "frame", "before", "after", "interval_days", "same_processing_version"))
            c.check("pair is in chronological order", pair["before"]["start"] < pair["after"]["start"])
    gcov = c.json("context/nisar level=GCOV", "/context/nisar", **point, level="GCOV")
    if gcov:
        c.check("level filter returns only GCOV", all(g["level"] == "GCOV" for g in gcov["granules"]))

    section("Context: earthquakes (USGS)")
    quakes = c.json("context/earthquakes", "/context/earthquakes", **point, radius_km=1000, min_magnitude=4)
    if quakes:
        c.has_keys("earthquakes", quakes, (*provenance, "total", "max_magnitude", "nearest", "data"))
        c.check("total matches data", quakes["total"] == len(quakes["data"]))
        if quakes["data"]:
            event = quakes["data"][0]
            c.has_keys("earthquake", event, ("id", "time", "magnitude", "place", "distance_km", "latitude", "longitude"))
            c.check("every event is inside the radius", all(e["distance_km"] <= 1000 * 1.01 for e in quakes["data"]))
            c.check("every event meets the minimum magnitude", all((e["magnitude"] or 0) >= 4 for e in quakes["data"]))
            c.check("nearest is the closest event", quakes["nearest"]["distance_km"] == min(e["distance_km"] for e in quakes["data"]))
        else:
            c.skip("earthquake fields", "no events in this window")

    section("Context: precipitation (NASA POWER)")
    rain = c.json("context/precipitation", "/context/precipitation", **point)
    if rain:
        c.has_keys("precipitation", rain, (*provenance, "available", "series"))
        if rain["available"]:
            c.has_keys("precipitation totals", rain, ("total_mm", "expected_mm", "anomaly_pct", "max_daily_mm", "peak_date", "elevation_m"))
            days = (end - start).days + 1
            c.check("one value per requested day", len(rain["series"]) == days, f"{len(rain['series'])} vs {days}")
            known = [p["mm"] for p in rain["series"] if p["mm"] is not None]
            c.check("total equals the sum of the series", abs(sum(known) - rain["total_mm"]) < 0.1)
            c.check("no negative rain", all(mm >= 0 for mm in known))
        else:
            c.skip("precipitation totals", "POWER has no data for this window yet")

    section("Context: fires (NASA FIRMS)")
    fire_start = max(start, end - timedelta(days=20))
    fire_point = {**point, "start": fire_start.isoformat()}
    response = c.get("/context/fires", **fire_point, radius_km=100)
    if response.status_code == 502 and "FIRMS_API_KEY" in response.text:
        c.skip("context/fires", "FIRMS_API_KEY is not set")
    elif c.check("context/fires responds 200", response.status_code == 200, response.text[:200]):
        fires = response.json()
        c.has_keys("fires", fires, (*provenance, "total", "detections_by_day", "data"))
        c.check("detections_by_day adds up", sum(fires["detections_by_day"].values()) == fires["total"])
        if fires["data"]:
            c.has_keys("fire", fires["data"][0], ("time", "latitude", "longitude", "distance_km", "frp_mw", "confidence"))
            c.check("every detection is inside the radius", all(f["distance_km"] <= 100 for f in fires["data"]))
        else:
            c.skip("fire fields", "no detections in this window")
    too_long = c.get("/context/fires", lat=lat, lon=lon, start="2026-01-01", end="2026-06-01")
    c.check("fire window over 31 days is rejected with 400", too_long.status_code == 400)

    section("Context: timeline")
    timeline = c.json("context/timeline", "/context/timeline", **point, radius_km=300)
    if timeline:
        c.has_keys("timeline", timeline, ("query", "total", "count_by_kind", "sources", "events"))
        c.check("timeline reports four sources", len(timeline["sources"]) == 4)
        c.check("every source states its status", all(s.get("status") in ("ok", "error") for s in timeline["sources"]))
        c.check("events are newest first", all(a["date"] >= b["date"] for a, b in zip(timeline["events"], timeline["events"][1:], strict=False)))
        c.check("count_by_kind adds up", sum(timeline["count_by_kind"].values()) == timeline["total"])

    section("Input validation")
    c.check("latitude out of range is rejected", c.get("/context/nisar", lat=120, lon=lon).status_code == 422)
    c.check("start after end is rejected", c.get("/context/earthquakes", lat=lat, lon=lon, start="2026-11-01", end="2026-10-01").status_code == 400)
    c.check("unknown change is 404", c.get("/changes/00000000-0000-0000-0000-000000000000").status_code == 404)

    section("Locations and ingestion")
    oversized = c.client.post(f"{c.base}/locations", json={"name": "check-too-big", "bbox": [70, 10, 80, 20]})
    c.check("oversized location is rejected with 400", oversized.status_code == 400)
    ambiguous = c.client.post(f"{c.base}/locations", json={"name": "check-ambiguous"})
    c.check("location without geometry is rejected with 400", ambiguous.status_code == 400)
    tasks = c.json("ingest tasks", "/ingest")
    if tasks is not None:
        c.check("ingest tasks is a list", isinstance(tasks, list))
        if tasks:
            c.has_keys("ingest task", tasks[0], ("id", "status", "stage", "progress", "product_id"))
    if locations:
        bad = c.client.post(f"{c.base}/ingest", json={"location_id": locations[0]["id"], "product_ids": ["not-a-granule"]})
        c.check("ingest of an invalid product name is rejected with 400", bad.status_code == 400)
    c.check("unknown ingest task is 404", c.get("/ingest/does-not-exist").status_code == 404)

    section("Analysis results")
    jobs = c.get("/jobs", status="COMPLETED", limit=1).json()
    if not jobs:
        c.skip("job, changes and tiles", "no completed analysis yet")
    else:
        job = jobs[0]
        c.has_keys("job", job, ("id", "status", "parameters", "result"))
        changes = c.json("changes of the job", "/changes", job_id=job["id"], limit=5)
        tiles = c.json("job tiles", f"/jobs/{job['id']}/tiles")
        if tiles:
            c.has_keys("tiles", tiles, ("bounds", "maxzoom", "layers", "legend"))
            c.check("all four layers are offered", set(tiles["layers"]) == {"before", "after", "difference", "mask"})
        listing = c.get("/changes", job_id=job["id"], limit=5)
        total = int(listing.headers.get("X-Total-Count", -1))
        c.check("change list reports the total in X-Total-Count", total >= len(changes or []))
        insights_job = c.json("job insights", f"/jobs/{job['id']}/insights")
        if insights_job:
            c.has_keys("job insights", insights_job, ("totals", "by_type", "by_direction", "score_histogram", "area_histogram", "evidence", "precipitation"))
            c.check("insights count matches the list total", insights_job["totals"]["changes"] == total)
            c.check("by_type adds up to the total", sum(t["count"] for t in insights_job["by_type"]) == total)
            c.check("score histogram adds up to the total", sum(b["count"] for b in insights_job["score_histogram"]) == total)
        collection = c.json("changes geojson", "/changes/geojson", job_id=job["id"], limit=50, zoom=10)
        if collection:
            c.check("geojson is a FeatureCollection", collection.get("type") == "FeatureCollection")
            c.check("geojson reports matched and returned", collection["numberMatched"] == total and collection["numberReturned"] <= 50)
            if collection["features"]:
                c.has_keys("feature properties", collection["features"][0]["properties"], ("id", "change_type", "label", "direction", "change_score"))
        vector = c.get(f"/jobs/{job['id']}/changes/tiles/0/0/0.mvt")
        c.check("vector tile responds as MVT", vector.status_code == 200 and "mapbox-vector-tile" in vector.headers.get("content-type", ""))
        if changes:
            change = changes[0]
            c.has_keys("change", change, ("id", "change_type", "geometry", "area_km2", "change_score", "direction", "mean_change_db"))
            only = c.get("/changes", job_id=job["id"], change_type=change["change_type"], limit=20).json()
            c.check("change_type filter is applied", bool(only) and all(x["change_type"] == change["change_type"] for x in only))
            strong = c.get("/changes", job_id=job["id"], sort="score", limit=20).json()
            c.check("sort=score orders by score", strong == sorted(strong, key=lambda x: -(x["change_score"] or 0)))
            c.check("change score is within [0, 1]", 0 <= (change["change_score"] or 0) <= 1)
            metrics = c.json("change metrics", f"/changes/{change['id']}/metrics")
            if metrics is not None:
                names = {metric["metric_name"] for metric in metrics}
                # dB metrics for real GCOV runs; amplitude pairs on older synthetic jobs.
                db_metrics = {"mean_change_db", "mean_backscatter_before_db", "mean_backscatter_after_db"}
                amplitudes = {"mean_absolute_difference", "std_absolute_difference"}
                c.check("metrics describe the polygon", db_metrics <= names or amplitudes <= names)
            evidence = c.json("change evidence", f"/changes/{change['id']}/evidence")
            if evidence is not None:
                c.check("evidence is a list", isinstance(evidence, list))
            explanation = c.json("change interpretation", f"/changes/{change['id']}/interpretation")
            if explanation:
                c.has_keys(
                    "interpretation",
                    explanation,
                    ("status", "period", "change", "classification", "metrics", "evidence", "sources", "limitations"),
                )
                c.check(
                    "interpretation names the sources it could not check",
                    isinstance(explanation["sources"], dict) and "NISAR" in explanation["sources"],
                )
            tile = c.get(f"/changes/{change['id']}/tiles/0/0/0", layer="difference")
            c.check("tile is a PNG", tile.status_code == 200 and tile.content[:8] == b"\x89PNG\r\n\x1a\n")
        elif changes is not None:
            c.skip("change, metrics, evidence, interpretation, tile", "the job produced no changes")

    print(f"\n{c.passed} passed, {c.failed} failed, {c.skipped} skipped")
    return 1 if c.failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000/api/v1")
    parser.add_argument("--lat", type=float, default=16.30, help="default: Krishna delta, India")
    parser.add_argument("--lon", type=float, default=81.10)
    parser.add_argument("--days", type=int, default=30, help="window ending 4 days ago")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    end = date.today() - timedelta(days=4)  # leaves room for POWER's latency
    start = end - timedelta(days=args.days - 1)
    print(f"Checking {args.url} at ({args.lat}, {args.lon}), {start} .. {end}")
    sys.exit(run(args.url, args.lat, args.lon, start, end, args.timeout))


if __name__ == "__main__":
    main()
