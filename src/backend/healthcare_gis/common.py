from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from healthcare_gis.security import now

def oid(value):
    if not ObjectId.is_valid(value):
        raise HTTPException(422, "Invalid record ID")
    return ObjectId(value)

def clean(value):
    if isinstance(value, ObjectId): return str(value)
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, dict): return {("id" if k == "_id" else k): clean(v) for k, v in value.items() if k != "password_hash"}
    if isinstance(value, (list, tuple)): return [clean(v) for v in value]
    return value

def audit(db, user, action, entity, entity_id=None, metadata=None):
    row = {"user_id": user["_id"], "action": action, "entity_type": entity, "metadata": metadata or {}, "created_at": now()}
    if entity_id is not None: row["entity_id"] = entity_id
    db.audit_logs.insert_one(row)
