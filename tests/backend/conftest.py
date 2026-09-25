import os
import secrets
import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from healthcare_gis.app import create_app
from healthcare_gis.security import passwords, now

@pytest.fixture
def api():
    uri = os.getenv("HEALTHCARE_GIS_TEST_MONGO_URI")
    if not uri: pytest.skip("Real MongoDB URI required")
    os.environ["RUN_WORKER"] = "0"
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    db = client["dog_gis_api_test"]
    client.drop_database(db.name)
    os.environ["JWT_SECRET"] = secrets.token_hex(32)
    with TestClient(create_app(db)) as http:
        db.users.insert_one({"username": "admin", "email": "a@example.test", "password_hash": passwords.hash("testing-password-123"), "role": "Admin", "is_active": True, "created_at": now(), "updated_at": now()})
        login = http.post("/api/v1/auth/login", json={"username": "admin", "password": "testing-password-123"})
        http.headers["Authorization"] = "Bearer " + login.json()["accessToken"]
        yield http, db
    client.drop_database(db.name)
    client.close()
