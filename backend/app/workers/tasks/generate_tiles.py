"""XYZ raster tiles for a change event.

Serving tiles from the difference COG is phase 7. Until then the API is explicit
(501) rather than returning a blank tile that looks like "no change".
"""

from app.core.exceptions import NotImplementedFeature


def run(change_id: str) -> None:
    raise NotImplementedFeature("tile generation from COG assets is not implemented yet")
