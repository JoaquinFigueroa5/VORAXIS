"""How far, and how long before, each kind of event can plausibly relate to a change.

A change seen between two acquisitions happened somewhere in that interval, so
the reference window is [before, after]. Each phenomenon then gets its own
reach in space and its own lead time before the first acquisition:

- an earthquake acts at once and over tens of km;
- a fire detection is a 375 m pixel and the scar sits where it burned, but
  fires burn for days, so detections shortly before the first image count;
- rain is a 50 km grid cell and floods lag the rain by days.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Profile:
    event_type: str
    radius_km: float  # beyond this an event is not linked
    lead_days: float  # how long before the first acquisition still counts
    max_links: int  # strongest links kept per change


PROFILES: dict[str, Profile] = {
    "EARTHQUAKE": Profile("EARTHQUAKE", radius_km=50.0, lead_days=1.0, max_links=5),
    "FIRE": Profile("FIRE", radius_km=2.0, lead_days=5.0, max_links=10),
    # The event geometry is the whole grid cell, so the radius is only a tolerance.
    "PRECIPITATION": Profile("PRECIPITATION", radius_km=5.0, lead_days=7.0, max_links=1),
}

# Search margin around the changes when fetching each source, in degrees.
FETCH_MARGIN_DEG = {"EARTHQUAKE": 0.5, "FIRE": 0.05}
MAX_PRECIPITATION_CELLS = 6


def window(profile: Profile, before: datetime, after: datetime) -> tuple[datetime, datetime]:
    return before - timedelta(days=profile.lead_days), after
