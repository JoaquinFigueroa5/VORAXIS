SQM_METERS_PER_KM2 = 1_000_000.0


def square_meters_to_km2(value: float) -> float:
    return value / SQM_METERS_PER_KM2


def meters_to_km(value: float) -> float:
    return value / 1000.0
