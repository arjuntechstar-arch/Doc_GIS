"""Versioned MongoDB schema, indexes and synthetic demo seed for Phase 1."""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
from pymongo import ASCENDING, GEOSPHERE, MongoClient
from pymongo.database import Database

SCHEMA_VERSION = 2
FIELDS: dict[str, tuple[list[str], dict[str, Any]]] = {}
S = {"bsonType": "string"}
N = {"bsonType": ["int", "long", "double", "decimal"], "minimum": 0}
D = {"bsonType": "date"}
OID = {"bsonType": "objectId"}
OBJ = {"bsonType": "object"}
B = {"bsonType": "bool"}
SCORE = {"bsonType": ["int", "long", "double", "decimal"], "minimum": 0, "maximum": 1}

def geo(kind: str) -> dict[str, Any]:
    return {"bsonType": "object", "required": ["type", "coordinates"], "properties": {
        "type": {"enum": [kind]}, "coordinates": {"bsonType": "array"}}}

def collection(collection_name: str, required: str, **properties: Any) -> None:
    FIELDS[collection_name] = (required.split(), properties)

collection("users", "username email password_hash role is_active created_at updated_at",
           username=S, email=S, password_hash=S, role={"enum": ["Admin", "GISAnalyst", "HealthcarePlanner", "Viewer"]}, is_active=B, created_at=D, updated_at=D)
collection("hospitals", "name hospital_type bed_capacity emergency_available specialty_count location status created_at updated_at",
           external_id=S, name=S, hospital_type=S, bed_capacity=N, emergency_available=B, specialty_count=N, location=geo("Point"), status=S, created_at=D, updated_at=D)
collection("population_areas", "area_code name population population_density age_0_14 age_15_59 age_60_plus geometry year",
           area_code=S, name=S, population=N, population_density=N, age_0_14=N, age_15_59=N, age_60_plus=N, geometry=geo("MultiPolygon"), year={"bsonType": "int"})
collection("roads", "road_type speed_kmh length_km geometry",
           external_id=S, road_type=S, speed_kmh={"bsonType": ["int", "long", "double", "decimal"], "minimum": 0, "exclusiveMinimum": True}, length_km=N, geometry=geo("LineString"))
collection("healthcare_demand", "area_id period demand_value source created_at", area_id=OID, period=D, demand_value=N, source=S, created_at=D)
collection("analysis_runs", "analysis_type parameters status created_at", analysis_type=S, parameters=OBJ, status=S, created_by=OID, created_at=D, completed_at=D)
collection("accessibility_results", "area_id capacity_score emergency_score population_coverage accessibility_index classification analysis_run_id",
           area_id=OID, nearest_hospital_id=OID, distance_km=N, travel_time_minutes=N, capacity_score=SCORE, emergency_score=SCORE, population_coverage=SCORE, accessibility_index=SCORE, classification=S, analysis_run_id=OID)
collection("demand_predictions", "area_id prediction_period predicted_demand model_version run_id",
           area_id=OID, prediction_period=D, predicted_demand=N, lower_bound=N, upper_bound=N, model_version=S, run_id=OID)
collection("candidate_sites", "name location population_score demand_score road_access_score land_suitability_score cost_score feasibility_status generated_run_id",
           name=S, location=geo("Point"), population_score=SCORE, demand_score=SCORE, road_access_score=SCORE, land_suitability_score=SCORE, cost_score=SCORE, feasibility_status=S, generated_run_id=OID)
collection("optimization_runs", "number_of_sites objective_configuration status",
           number_of_sites={"bsonType": "int", "minimum": 1}, objective_configuration=OBJ, status=S, started_at=D, completed_at=D, model_version=S, error_message=S)
collection("recommendations", "optimization_run_id candidate_site_id rank total_score estimated_population_served estimated_avg_travel_time accessibility_improvement explanation",
           optimization_run_id=OID, candidate_site_id=OID, rank={"bsonType": "int", "minimum": 1}, total_score=N, estimated_population_served=N, estimated_avg_travel_time=N, accessibility_improvement={"bsonType": ["int", "long", "double", "decimal"]}, explanation=OBJ)
collection("audit_logs", "action entity_type metadata created_at", user_id=OID, action=S, entity_type=S, entity_id=OID, metadata=OBJ, created_at=D)

# Added in schema v2 for the application and asynchronous workflow.
V2_FIELDS = {
    "boundaries": (["name", "land_use", "geometry"], {
        "name": S, "land_use": {"enum": ["boundary", "water", "protected_forest", "residential", "commercial", "vacant"]},
        "geometry": {"bsonType": "object", "required": ["type", "coordinates"], "properties": {
            "type": {"enum": ["Polygon", "MultiPolygon"]}, "coordinates": {"bsonType": "array"}}}}),
    "jobs": (["kind", "parameters", "status", "created_by", "created_at"], {
        "kind": S, "parameters": OBJ, "status": {"enum": ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]},
        "created_by": OID, "created_at": D, "started_at": D, "lease_until": D, "completed_at": D,
        "result": OBJ, "error": S}),
    "models": (["model_version", "algorithm", "metrics", "created_at"], {
        "model_version": S, "algorithm": S, "metrics": OBJ, "created_at": S}),
    "refresh_tokens": (["user_id", "expires_at"], {"user_id": OID, "expires_at": D}),
}

# Each tuple is (index key specification, options). 2dsphere indexes use GeoJSON WGS84.
INDEXES = {
    "users": [([("username", ASCENDING)], {"unique": True}), ([("email", ASCENDING)], {"unique": True})],
    "hospitals": [([("external_id", ASCENDING)], {"unique": True, "partialFilterExpression": {"external_id": {"$type": "string"}}}), ([("location", GEOSPHERE)], {})],
    "population_areas": [([("area_code", ASCENDING), ("year", ASCENDING)], {"unique": True}), ([("geometry", GEOSPHERE)], {})],
    "roads": [([("external_id", ASCENDING)], {"unique": True, "partialFilterExpression": {"external_id": {"$type": "string"}}}), ([("geometry", GEOSPHERE)], {})],
    "candidate_sites": [([("location", GEOSPHERE)], {}), ([("generated_run_id", ASCENDING)], {})],
    "healthcare_demand": [([("area_id", ASCENDING), ("period", ASCENDING), ("source", ASCENDING)], {"unique": True})],
    "accessibility_results": [([("analysis_run_id", ASCENDING), ("area_id", ASCENDING)], {"unique": True})],
    "demand_predictions": [([("run_id", ASCENDING), ("area_id", ASCENDING)], {"unique": True})],
    "recommendations": [([("optimization_run_id", ASCENDING), ("rank", ASCENDING)], {"unique": True}), ([("optimization_run_id", ASCENDING), ("candidate_site_id", ASCENDING)], {"unique": True})],
    "audit_logs": [([("user_id", ASCENDING), ("created_at", ASCENDING)], {})],
    "boundaries": [([("geometry", GEOSPHERE)], {})],
    "jobs": [([("status", ASCENDING), ("created_at", ASCENDING)], {})],
    "models": [([("model_version", ASCENDING)], {"unique": True})],
    "refresh_tokens": [([("expires_at", ASCENDING)], {"expireAfterSeconds": 0})],
}

def connect() -> tuple[MongoClient, Database]:
    client = MongoClient(os.getenv("HEALTHCARE_GIS_MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=5000, tz_aware=True)
    client.admin.command("ping")
    return client, client[os.getenv("HEALTHCARE_GIS_MONGO_DB", "dog_gis")]

def initialize(db: Database) -> None:
    """Idempotently apply schema versions 1 and 2; never downgrade an unknown schema."""
    current = db.schema_migrations.find_one({"_id": "schema"})
    if current and current["version"] > SCHEMA_VERSION:
        raise RuntimeError("Database schema is newer than this application")
    names = set(db.list_collection_names())
    for name, (required, properties) in {**FIELDS, **V2_FIELDS}.items():
        validator = {"$jsonSchema": {"bsonType": "object", "required": required, "properties": properties}}
        if name not in names:
            db.create_collection(name, validator=validator, validationLevel="strict")
        else:
            db.command({"collMod": name, "validator": validator, "validationLevel": "strict"})
        for keys, options in INDEXES.get(name, []):
            db[name].create_index(keys, **options)
    db.schema_migrations.update_one({"_id": "schema"}, {"$set": {"version": SCHEMA_VERSION}, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}}, upsert=True)

def seed_demo(db: Database) -> None:
    """Fabricated Chennai-area geometry and counts; never treat as real observations."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for code, name, xy, beds in [
        ("DEMO-H1", "Demo Central Hospital", [80.2707, 13.0827], 150),
        ("DEMO-H2", "Demo South Hospital", [80.2400, 13.0400], 80),
    ]:
        db.hospitals.update_one({"external_id": code}, {"$setOnInsert": {
            "name": name, "hospital_type": "General", "bed_capacity": beds,
            "emergency_available": True, "specialty_count": 4,
            "location": {"type": "Point", "coordinates": xy}, "status": "Active",
            "created_at": now, "updated_at": now}}, upsert=True)
    for code, name, population, (w, s, e, n) in [
        ("DEMO-A1", "Demo Central Area", 12000, [80.26, 13.07, 80.28, 13.09]),
        ("DEMO-A2", "Demo South Area", 9000, [80.23, 13.03, 80.25, 13.05]),
    ]:
        ring = [[w, s], [e, s], [e, n], [w, n], [w, s]]
        db.population_areas.update_one({"area_code": code, "year": 2026}, {"$setOnInsert": {
            "name": name, "population": population, "population_density": float(population / 2),
            "age_0_14": population // 5, "age_15_59": population * 7 // 10,
            "age_60_plus": population // 10,
            "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]}}}, upsert=True)
    db.roads.update_one({"external_id": "DEMO-R1"}, {"$setOnInsert": {
        "road_type": "primary", "speed_kmh": 40.0, "length_km": 7.5,
        "geometry": {"type": "LineString", "coordinates": [[80.24, 13.04], [80.2707, 13.0827]]}}}, upsert=True)
