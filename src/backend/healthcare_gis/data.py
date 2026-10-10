"""Validated data ingestion, CRUD and bounded GeoJSON queries."""
import json
import math
from typing import Literal
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from pydantic import BaseModel, Field, ConfigDict, model_validator
from shapely.geometry import shape, mapping, box
from healthcare_gis.security import roles, current_user, now
from healthcare_gis.common import clean, oid, audit

router = APIRouter(prefix="/api/v1")

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Geometry(Strict):
    type: Literal["Point", "MultiPolygon", "Polygon", "LineString"]
    coordinates: list

    @model_validator(mode="after")
    def valid(self):
        def coordinates(values):
            if values and isinstance(values[0], (int, float)):
                if len(values) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
                    raise ValueError("Use two finite coordinates [longitude, latitude]")
                if not -180 <= values[0] <= 180 or not -90 <= values[1] <= 90:
                    raise ValueError("Coordinates are outside WGS84 bounds")
            else:
                for value in values: coordinates(value)
        try:
            coordinates(self.coordinates)
            geom = shape(self.model_dump())
        except (TypeError, ValueError, IndexError, AttributeError): raise ValueError("Invalid GeoJSON geometry")
        if geom.is_empty or not geom.is_valid: raise ValueError("Empty or invalid geometry topology")
        if len(str(self.coordinates)) > 500000: raise ValueError("Geometry is too complex")
        return self

class Hospital(Strict):
    external_id: str | None = Field(default=None, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    hospital_type: str = "General"
    bed_capacity: int = Field(ge=0, le=100000)
    emergency_available: bool = False
    specialty_count: int = Field(default=0, ge=0, le=1000)
    location: Geometry
    status: Literal["Active", "Inactive"] = "Active"
    @model_validator(mode="after")
    def point(self):
        if self.location.type != "Point": raise ValueError("Hospital location must be Point")
        return self

class Population(Strict):
    area_code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    population: int = Field(ge=0)
    population_density: float = Field(ge=0)
    age_0_14: int = Field(ge=0)
    age_15_59: int = Field(ge=0)
    age_60_plus: int = Field(ge=0)
    geometry: Geometry
    year: int = Field(ge=1900, le=2200)
    @model_validator(mode="after")
    def polygon(self):
        if self.geometry.type != "MultiPolygon": raise ValueError("Population geometry must be MultiPolygon")
        if self.age_0_14 + self.age_15_59 + self.age_60_plus != self.population:
            raise ValueError("Age groups must sum to population")
        return self

class Road(Strict):
    external_id: str | None = None
    road_type: str = "road"
    speed_kmh: float = Field(gt=0, le=150)
    length_km: float = Field(ge=0)
    geometry: Geometry
    one_way: bool = False
    @model_validator(mode="after")
    def line(self):
        if self.geometry.type != "LineString": raise ValueError("Road geometry must be LineString")
        return self

class Boundary(Strict):
    name: str = Field(min_length=1, max_length=200)
    land_use: Literal["boundary", "water", "protected_forest", "residential", "commercial", "vacant"]
    geometry: Geometry
    @model_validator(mode="after")
    def polygon(self):
        if self.geometry.type not in ("Polygon", "MultiPolygon"): raise ValueError("Boundary must be a polygon")
        return self

class Demand(Strict):
    area_id: str
    period: int = Field(ge=1900, le=2200)
    demand_value: float = Field(ge=0)
    source: str = Field(min_length=1, max_length=200)

MODELS = {"hospitals": Hospital, "population": Population, "roads": Road, "boundaries": Boundary, "demand": Demand}
COLLECTIONS = {"hospitals": "hospitals", "population": "population_areas", "roads": "roads", "boundaries": "boundaries", "demand": "healthcare_demand"}

def prepare(db, kind, model):
    row = model.model_dump(exclude_none=True)
    row["_id"] = ObjectId()
    if kind == "hospitals": row.update(created_at=now(), updated_at=now())
    if kind == "demand":
        from datetime import datetime, timezone
        row["area_id"] = oid(row["area_id"])
        if not db.population_areas.find_one({"_id": row["area_id"]}): raise HTTPException(422, "Unknown population area")
        row["period"] = datetime(row["period"], 1, 1, tzinfo=timezone.utc)
        row["created_at"] = now()
    return row

@router.post("/{kind}/import", status_code=201)
async def import_data(kind: str, request: Request, file: UploadFile = File(...), user=Depends(roles())):
    if kind not in MODELS: raise HTTPException(404, "Unknown dataset")
    if not (file.filename or "").lower().endswith((".json", ".geojson")) or file.content_type not in ("application/json", "application/geo+json", "application/octet-stream"):
        raise HTTPException(422, "Upload JSON or GeoJSON with an appropriate content type")
    raw = await file.read(10_000_001)
    if len(raw) > 10_000_000: raise HTTPException(413, "Maximum upload is 10 MB")
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            field = "location" if kind == "hospitals" else "geometry"
            payload = [f.get("properties", {}) | ({} if kind == "demand" else {field: f["geometry"]}) for f in payload["features"]]
        if not isinstance(payload, list) or not 1 <= len(payload) <= 5000: raise ValueError("Supply 1–5000 records")
        models = [MODELS[kind].model_validate(item) for item in payload]
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc)[:1500])
    db = request.app.state.db
    rows = [prepare(db, kind, model) for model in models]
    ids = [r["_id"] for r in rows]
    try:
        db[COLLECTIONS[kind]].insert_many(rows, ordered=True)
    except Exception:
        db[COLLECTIONS[kind]].delete_many({"_id": {"$in": ids}})
        raise HTTPException(409, "Import rejected; duplicate or invalid records. No rows from this batch retained")
    audit(db, user, "import", kind, metadata={"count": len(rows)})
    return {"imported": len(rows), "ids": clean(ids)}

@router.get("/hospitals")
@router.get("/population/areas")
@router.get("/roads")
@router.get("/boundaries")
def list_data(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=200), search: str = "", user=Depends(current_user)):
    kind = request.url.path.split("/")[3]
    collection = request.app.state.db[COLLECTIONS[kind]]
    query = {}
    if search:
        import re
        query = {"name": {"$regex": re.escape(search[:100]), "$options": "i"}}
    return {"items": clean(list(collection.find(query).sort("_id", 1).skip((page-1)*pageSize).limit(pageSize))), "total": collection.count_documents(query), "page": page, "pageSize": pageSize}

@router.get("/hospitals/{id}")
@router.get("/population/areas/{id}")
def record(id: str, request: Request, user=Depends(current_user)):
    collection = "hospitals" if "/hospitals/" in request.url.path else "population_areas"
    row = request.app.state.db[collection].find_one({"_id": oid(id)})
    if not row: raise HTTPException(404, "Record not found")
    return clean(row)

@router.post("/hospitals", status_code=201)
def add_hospital(body: Hospital, request: Request, user=Depends(roles("GISAnalyst"))):
    db = request.app.state.db
    row = prepare(db, "hospitals", body)
    db.hospitals.insert_one(row)
    audit(db, user, "create", "hospitals", row["_id"])
    return clean(row)

@router.put("/hospitals/{id}")
def update_hospital(id: str, body: Hospital, request: Request, user=Depends(roles("GISAnalyst"))):
    db = request.app.state.db
    data = body.model_dump(exclude_none=True) | {"updated_at": now()}
    if not db.hospitals.update_one({"_id": oid(id)}, {"$set": data}).matched_count: raise HTTPException(404, "Hospital not found")
    audit(db, user, "update", "hospitals", oid(id))
    return clean(db.hospitals.find_one({"_id": oid(id)}))

@router.delete("/hospitals/{id}")
def delete_hospital(id: str, request: Request, user=Depends(roles())):
    db = request.app.state.db
    # Soft deletion preserves historical analysis references.
    if not db.hospitals.update_one({"_id": oid(id)}, {"$set": {"status": "Inactive", "updated_at": now()}}).matched_count: raise HTTPException(404, "Hospital not found")
    audit(db, user, "deactivate", "hospitals", oid(id))
    return {"deleted": True}

def bounds_query(bbox, field):
    if not bbox: return {}
    try:
        w, s, e, n = map(float, bbox.split(","))
        if not all(math.isfinite(x) for x in (w,s,e,n)) or not (-180<=w<=180 and -180<=e<=180 and -90<=s<n<=90): raise ValueError()
        width = e-w if e>=w else 360-w+e
        if width > 10 or n-s > 10 or width <= 0: raise ValueError()
        polygons = [box(w,s,e,n)] if w<e else [box(w,s,180,n), box(-180,s,e,n)]
        clauses = [{field: {"$geoIntersects": {"$geometry": mapping(p)}}} for p in polygons]
        return clauses[0] if len(clauses)==1 else {"$or":clauses}
    except ValueError: raise HTTPException(422, "bbox must be west,south,east,north spanning at most 10 degrees")

def features(rows, field):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": r[field], "properties": clean({k:v for k,v in r.items() if k != field})} for r in rows]}

@router.get("/gis/{layer}")
def gis(layer: str, request: Request, bbox: str | None = None, runId: str | None = None, user=Depends(current_user)):
    db = request.app.state.db
    if layer in ("hospitals", "population", "roads", "boundaries", "candidates"):
        coll = "candidate_sites" if layer=="candidates" else COLLECTIONS[layer]
        field = "location" if layer in ("hospitals", "candidates") else "geometry"
        query = bounds_query(bbox, field)
        if layer=="hospitals": query["status"]="Active"
        if layer=="candidates" and runId: query["generated_run_id"]=oid(runId)
        return features(list(db[coll].find(query).limit(5000)), field)
    if layer in ("accessibility", "underserved", "demand", "recommendations"):
        coll = {"accessibility":"accessibility_results", "underserved":"accessibility_results", "demand":"demand_predictions", "recommendations":"recommendations"}[layer]
        key = "analysis_run_id" if layer in ("accessibility", "underserved") else "run_id" if layer=="demand" else "optimization_run_id"
        if not runId: return {"type":"FeatureCollection", "features":[]}
        query = {key:oid(runId)}
        if layer=="underserved": query["accessibility_index"]={"$lt":.5}
        rows=[]
        for result in db[coll].find(query).limit(5000):
            source = db.candidate_sites.find_one({"_id":result["candidate_site_id"]}) if layer=="recommendations" else db.population_areas.find_one({"_id":result["area_id"]})
            if source:
                field = "location" if layer=="recommendations" else "geometry"
                geo=source[field]
                if bbox:
                    q=bounds_query(bbox, field)
                    source_coll=db.candidate_sites if layer=="recommendations" else db.population_areas
                    if not source_coll.find_one({"_id":source["_id"], **q}): continue
                rows.append(result | {"geometry":geo, "name":source["name"]})
        return features(rows,"geometry")
    raise HTTPException(404,"Unknown map layer")
