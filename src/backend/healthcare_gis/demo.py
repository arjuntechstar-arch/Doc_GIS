"""Reproducible synthetic city with varied demographics, facilities, roads and demand."""
import math
from datetime import datetime, timezone

from healthcare_gis.security import now
from healthcare_gis.spatial import GEOD

SOURCE = "DEMO-CITY-v3"
LEGACY_SOURCE = "DEMO-CITY-v2"
YEARS = range(2012, 2026)
CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

HOSPITALS = [
    ("Demo Central Medical Center", "General", 320, 12, True, [80.28, 13.08]),
    ("Demo North Community Hospital", "Community", 145, 6, True, [80.28, 13.14]),
    ("Demo East District Hospital", "General", 190, 8, True, [80.34, 13.08]),
    ("Demo South Community Hospital", "Community", 95, 4, False, [80.24, 13.02]),
    ("Demo West Specialty Center", "Specialty", 110, 9, True, [80.22, 13.10]),
]

POPULATIONS = (
    (8200, 11200, 9200, 15800),
    (12400, 17600, 11500, 21100),
    (9800, 23800, 14100, 19600),
    (15100, 28200, 18200, 24700),
)

X_EDGES = (80.20, 80.235, 80.28, 80.32, 80.36)
Y_EDGES = (13.00, 13.038, 13.082, 13.122, 13.16)


def _upsert_demand(db, area_id, year, value):
    period = datetime(year, 1, 1, tzinfo=timezone.utc)
    current = db.healthcare_demand.find_one(
        {"area_id": area_id, "period": period, "source": SOURCE}
    )
    if current:
        db.healthcare_demand.update_one(
            {"_id": current["_id"]}, {"$set": {"demand_value": value}}
        )
        return

    legacy = db.healthcare_demand.find_one(
        {"area_id": area_id, "period": period, "source": LEGACY_SOURCE}
    )
    if legacy:
        db.healthcare_demand.update_one(
            {"_id": legacy["_id"]},
            {"$set": {"source": SOURCE, "demand_value": value}},
        )
        return

    db.healthcare_demand.update_one(
        {"area_id": area_id, "period": period, "source": SOURCE},
        {"$setOnInsert": {"demand_value": value, "created_at": CREATED_AT}},
        upsert=True,
    )


def _population_profile(x, y):
    population = POPULATIONS[y][x]
    child_share = 0.16 + ((x * 3 + y * 2) % 6) * 0.018
    senior_share = 0.07 + ((x * 2 + y * 3) % 5) * 0.016
    children = round(population * child_share)
    seniors = round(population * senior_share)
    adults = population - children - seniors
    growth = 0.008 + ((x * 2 + y) % 6) * 0.003
    care_rate = 0.085 + child_share * 0.11 + senior_share * 0.32
    return population, children, adults, seniors, growth, care_rate


def _historical_demand(population, growth, care_rate, x, y, year):
    elapsed = year - 2012
    population_in_year = population / (1 + growth) ** (2025 - year)
    gradual_variation = 1 + 0.025 * math.sin(elapsed * 1.7 + x * 0.8 + y * 0.4)
    return round(population_in_year * care_rate * gradual_variation, 2)


def _road_profile(line):
    if line in (3, 5):
        return "arterial", 50.0
    if line in (1, 7):
        return "primary", 35.0
    return "local", 25.0


def load_demo(db):
    if db.population_areas.count_documents(
        {"area_code": {"$not": {"$regex": "^DEMO-"}}}
    ):
        raise ValueError(
            "Use a separate database for demo data; "
            "non-demo population areas already exist"
        )

    for index, hospital in enumerate(HOSPITALS, 1):
        name, hospital_type, beds, specialties, emergency, coordinates = hospital
        db.hospitals.update_one(
            {"external_id": f"DEMO-CITY-H{index}"},
            {
                "$set": {
                    "name": name,
                    "hospital_type": hospital_type,
                    "bed_capacity": beds,
                    "specialty_count": specialties,
                    "emergency_available": emergency,
                    "location": {"type": "Point", "coordinates": coordinates},
                    "status": "Active",
                    "updated_at": now(),
                },
                "$setOnInsert": {"created_at": now()},
            },
            upsert=True,
        )

    for x in range(4):
        for y in range(4):
            west, east = X_EDGES[x], X_EDGES[x + 1]
            south, north = Y_EDGES[y], Y_EDGES[y + 1]
            ring = [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
            population, children, adults, seniors, growth, care_rate = (
                _population_profile(x, y)
            )
            area_m2 = abs(
                GEOD.polygon_area_perimeter(
                    [coordinate[0] for coordinate in ring],
                    [coordinate[1] for coordinate in ring],
                )[0]
            )
            db.population_areas.update_one(
                {"area_code": f"DEMO-CITY-{x}-{y}", "year": 2025},
                {
                    "$set": {
                        "name": f"Demo district {x + 1}-{y + 1}",
                        "population": population,
                        "population_density": population / (area_m2 / 1e6),
                        "age_0_14": children,
                        "age_15_59": adults,
                        "age_60_plus": seniors,
                        "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]},
                    }
                },
                upsert=True,
            )
            area = db.population_areas.find_one(
                {"area_code": f"DEMO-CITY-{x}-{y}", "year": 2025}
            )
            for year in YEARS:
                _upsert_demand(
                    db,
                    area["_id"],
                    year,
                    _historical_demand(population, growth, care_rate, x, y, year),
                )

    for area in db.population_areas.find(
        {"area_code": {"$in": ["DEMO-A1", "DEMO-A2"]}}
    ):
        for year in YEARS:
            _upsert_demand(
                db,
                area["_id"],
                year,
                round(area["population"] * 0.12 * 1.025 ** (year - 2012), 2),
            )

    for axis in range(2):
        for line in range(9):
            road_type, speed = _road_profile(line)
            coordinates = [
                [
                    80.2 + (line if axis else index) * 0.02,
                    13 + (index if axis else line) * 0.02,
                ]
                for index in range(9)
            ]
            length = sum(
                abs(GEOD.inv(start[0], start[1], end[0], end[1])[2]) / 1000
                for start, end in zip(coordinates, coordinates[1:])
            )
            db.roads.update_one(
                {"external_id": f"DEMO-CITY-R{axis}-{line}"},
                {
                    "$set": {
                        "road_type": road_type,
                        "speed_kmh": speed,
                        "length_km": length,
                        "geometry": {"type": "LineString", "coordinates": coordinates},
                    }
                },
                upsert=True,
            )

    boundaries = [
        (
            "Demo study boundary",
            "boundary",
            [[80.19, 12.99], [80.37, 12.99], [80.37, 13.17], [80.19, 13.17], [80.19, 12.99]],
        ),
        (
            "Demo lake",
            "water",
            [[80.33, 13.13], [80.35, 13.13], [80.35, 13.15], [80.33, 13.15], [80.33, 13.13]],
        ),
        (
            "Demo protected greenbelt",
            "protected_forest",
            [[80.205, 13.125], [80.225, 13.125], [80.225, 13.15], [80.205, 13.15], [80.205, 13.125]],
        ),
        (
            "Demo mixed-use center",
            "commercial",
            [[80.265, 13.065], [80.29, 13.065], [80.29, 13.09], [80.265, 13.09], [80.265, 13.065]],
        ),
        (
            "Demo residential quarter",
            "residential",
            [[80.295, 13.025], [80.32, 13.025], [80.32, 13.05], [80.295, 13.05], [80.295, 13.025]],
        ),
    ]
    for name, land_use, coordinates in boundaries:
        db.boundaries.update_one(
            {"name": name},
            {
                "$set": {
                    "land_use": land_use,
                    "geometry": {"type": "Polygon", "coordinates": [coordinates]},
                }
            },
            upsert=True,
        )

    return {
        "synthetic": True,
        "version": SOURCE,
        "areas": db.population_areas.count_documents({}),
        "hospitals": db.hospitals.count_documents({}),
        "roads": db.roads.count_documents({}),
        "demandRecords": db.healthcare_demand.count_documents({}),
    }
