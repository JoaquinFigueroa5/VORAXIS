"""NASA Harmony is the path for server-side subsetting/reprojection.

Not wired yet: it requires Earthdata credentials and a job/polling client. The
contract is kept here so the pipeline can switch to Harmony without touching
callers.
"""

from typing import Any

from app.core.exceptions import NotImplementedFeature
from app.integrations.nisar.earthdata_client import EarthdataClient


class HarmonyClient:
    def __init__(self, earthdata: EarthdataClient | None = None) -> None:
        self.earthdata = earthdata or EarthdataClient()

    @property
    def available(self) -> bool:
        return self.earthdata.configured

    def request_subset(self, *, product_id: str, bbox, variables: list[str]) -> dict[str, Any]:
        raise NotImplementedFeature(
            "Harmony subsetting is not implemented; download full products for now"
        )
