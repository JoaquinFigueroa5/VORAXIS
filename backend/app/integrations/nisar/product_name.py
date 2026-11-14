"""NISAR granule name parsing.

Convention (NISAR product specs):

    NISAR_IL_PT_PROD_CYL_REL_P_FRM_MODE_POLE_S_Start_End_CRID_ACC_COV_SDS_CTR

e.g. ``NISAR_L2_PR_GCOV_035_098_A_019_2005_DHDH_M_20261111T234059_20261111T234134_P05036_N_F_J_001``

A pair is only comparable when track (REL), frame (FRM) and direction (P) match.
"""

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PATTERN = re.compile(
    r"^NISAR_(?P<level>L\d)_(?P<processing_type>[A-Z]{2})_(?P<product_type>[A-Z0-9]+)"
    r"_(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<direction>[AD])_(?P<frame>\d{3})"
    r"_(?P<mode>[A-Z0-9]{4})_(?P<polarization>[A-Z]{4})_(?P<observation_mode>[A-Z])"
    r"_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})"
    r"_(?P<crid>[A-Z0-9]+)_(?P<accuracy>[A-Z])_(?P<coverage>[A-Z])_(?P<sds>[A-Z])_(?P<counter>\d{3})$"
)

_DIRECTIONS = {"A": "ASCENDING", "D": "DESCENDING"}


@dataclass(frozen=True)
class ProductName:
    product_id: str
    level: str
    product_type: str
    cycle: int
    track: int
    frame: int
    orbit_direction: str
    mode: str
    polarization: str
    start: datetime
    end: datetime
    crid: str

    def as_metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data["start"] = self.start.isoformat()
        data["end"] = self.end.isoformat()
        return data


def _timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)


def parse_product_name(name: str | Path) -> ProductName | None:
    """Return the parsed fields, or None when the name does not follow the convention."""
    stem = Path(str(name)).name
    for suffix in (".h5", ".hdf5"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
    match = _PATTERN.match(stem)
    if match is None:
        return None
    fields = match.groupdict()
    return ProductName(
        product_id=stem,
        level=fields["level"],
        product_type=fields["product_type"],
        cycle=int(fields["cycle"]),
        track=int(fields["track"]),
        frame=int(fields["frame"]),
        orbit_direction=_DIRECTIONS[fields["direction"]],
        mode=fields["mode"],
        polarization=fields["polarization"],
        start=_timestamp(fields["start"]),
        end=_timestamp(fields["end"]),
        crid=fields["crid"],
    )
