"""HTTP composition root. Business operations live in service modules."""
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from pymongo.errors import DuplicateKeyError, PyMongoError
from healthcare_gis.database import connect, initialize
from healthcare_gis.security import key, tokens, decode, current_user, roles, verify, passwords, now, ROLES
from healthcare_gis.common import clean, oid, audit

logging.basicConfig(level=logging.INFO, format="%(message)s")

class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)

class Refresh(BaseModel):
    refreshToken: str

class NewUser(Login):
    password: str = Field(min_length=12, max_length=256)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    role: str = "Viewer"

class UserUpdate(BaseModel):
    role: str
    is_active: bool = True

def create_app(database=None):
    @asynccontextmanager
    async def lifespan(app):
        key()
        client = None
        if database is None:
            client, app.state.db = connect()
        else:
            app.state.db = database
        initialize(app.state.db)
        app.state.db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
        worker = None
        if os.getenv("RUN_WORKER", "1") == "1":
            from healthcare_gis.jobs import start_worker
            worker = start_worker(app.state.db)
        yield
        if worker:
            worker[0].set()
            worker[1].join(timeout=5)
        if client: client.close()

    app = FastAPI(title="Healthcare GIS", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:4200").split(","), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"])
    limiter, lock = defaultdict(deque), Lock()

    def problem(status, detail, errors=None):
        body = {"type": "about:blank", "title": "Request failed", "status": status, "detail": detail}
        if errors: body["errors"] = errors
        return JSONResponse(body, status_code=status, media_type="application/problem+json")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc): return problem(exc.status_code, str(exc.detail))
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc): return problem(422, "Validation failed", [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()])
    @app.exception_handler(DuplicateKeyError)
    async def conflict(request, exc): return problem(409, "A record with this unique key already exists")
    @app.exception_handler(PyMongoError)
    async def database_error(request, exc):
        logging.error("Database operation failed: %s", type(exc).__name__)
        return problem(503, "Database operation failed")
    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.error("Unhandled operation: %s", type(exc).__name__)
        return problem(500, "An unexpected error occurred")

    @app.middleware("http")
    async def request_context(request, call_next):
        started = time.monotonic()
        correlation = str(uuid.uuid4())
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return problem(400, "Invalid Content-Length")
        if content_length > 10_000_000:
            return problem(413, "Maximum request size is 10 MB")
        # Process-local limiter; reverse proxy must apply a shared limit when scaling workers.
        ip = request.client.host if request.client else "unknown"
        bucket_key = (ip, "login" if request.url.path.endswith("/login") else "api")
        with lock:
            bucket = limiter[bucket_key]
            while bucket and bucket[0] < started - 60: bucket.popleft()
            if len(bucket) >= (20 if bucket_key[1] == "login" else 300):
                return problem(429, "Too many requests; retry in one minute")
            bucket.append(started)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        response.headers["X-Content-Type-Options"] = "nosniff"
        logging.info(json.dumps({"correlation_id": correlation, "method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": round((time.monotonic() - started) * 1000)}))
        return response

    @app.get("/health")
    def health(request: Request):
        request.app.state.db.command("ping")
        return {"status": "ok"}

    @app.post("/api/v1/auth/login")
    def login(body: Login, request: Request):
        db = request.app.state.db
        user = db.users.find_one({"username": body.username, "is_active": True})
        if not user or not verify(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid username or password")
        audit(db, user, "login", "users", user["_id"])
        return tokens(db, user)

    @app.post("/api/v1/auth/refresh")
    def refresh(body: Refresh, request: Request):
        claims = decode(body.refreshToken, "refresh")
        db = request.app.state.db
        session = db.refresh_tokens.find_one_and_delete({"_id": claims["jti"]})
        user = db.users.find_one({"_id": oid(claims["sub"]), "is_active": True})
        if not session or not user: raise HTTPException(401, "Refresh token revoked or reused")
        return tokens(db, user)

    @app.get("/api/v1/auth/me")
    def me(user=Depends(current_user)): return clean(user)

    @app.get("/api/v1/admin/users")
    def users(request: Request, user=Depends(roles()), page: int = 1):
        return {"items": clean(list(request.app.state.db.users.find().skip(max(0, page - 1)*50).limit(50)))}

    @app.post("/api/v1/admin/users", status_code=201)
    def add_user(body: NewUser, request: Request, user=Depends(roles())):
        if body.role not in ROLES: raise HTTPException(422, "Invalid role")
        data = body.model_dump(exclude={"password"}) | {"password_hash": passwords.hash(body.password), "created_at": now(), "updated_at": now(), "is_active": True}
        db = request.app.state.db
        data["_id"] = db.users.insert_one(data).inserted_id
        audit(db, user, "create", "users", data["_id"])
        return clean(data)

    @app.put("/api/v1/admin/users/{id}")
    def edit_user(id: str, body: UserUpdate, request: Request, user=Depends(roles())):
        if body.role not in ROLES: raise HTTPException(422, "Invalid role")
        if str(user["_id"]) == id: raise HTTPException(409, "Cannot change your own administrative access")
        result = request.app.state.db.users.update_one({"_id": oid(id)}, {"$set": body.model_dump() | {"updated_at": now()}})
        if not result.matched_count: raise HTTPException(404, "User not found")
        audit(request.app.state.db, user, "update", "users", oid(id))
        return {"updated": True}

    @app.get("/api/v1/admin/audit")
    def audits(request: Request, user=Depends(roles())):
        return {"items": clean(list(request.app.state.db.audit_logs.find().sort("created_at", -1).limit(100)))}
    from healthcare_gis.data import router as data_router
    app.include_router(data_router)
    from healthcare_gis.analysis import router as analysis_router
    app.include_router(analysis_router)
    from healthcare_gis.demand import router as demand_router
    app.include_router(demand_router)
    from healthcare_gis.candidates import router as candidates_router
    from healthcare_gis.optimization import router as optimization_router
    app.include_router(candidates_router)
    app.include_router(optimization_router)
    from healthcare_gis.reports import router as reports_router
    app.include_router(reports_router)
    return app

app = create_app()
