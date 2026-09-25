"""JWT authentication, rotating refresh tokens and role policies."""
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from bson import ObjectId
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

passwords = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
ROLES = {"Admin", "GISAnalyst", "HealthcarePlanner", "Viewer"}

def now():
    return datetime.now(timezone.utc)

def key():
    value = os.environ.get("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    return value

def tokens(db, user):
    result = {}
    for kind, duration in [("access", timedelta(minutes=15)), ("refresh", timedelta(days=7))]:
        jti = secrets.token_hex(24)
        expires = now() + duration
        claims = {"sub": str(user["_id"]), "type": kind, "jti": jti,
                  "iat": now(), "exp": expires, "iss": "healthcare-gis", "aud": "healthcare-gis"}
        result[kind + "Token"] = jwt.encode(claims, key(), algorithm="HS256")
        if kind == "refresh":
            db.refresh_tokens.insert_one({"_id": jti, "user_id": user["_id"], "expires_at": expires})
    result["tokenType"] = "bearer"
    return result

def decode(token, kind):
    try:
        claims = jwt.decode(token, key(), algorithms=["HS256"], issuer="healthcare-gis", audience="healthcare-gis", options={"require": ["exp", "iat", "sub", "jti", "type"]})
        if claims["type"] != kind or not ObjectId.is_valid(claims["sub"]):
            raise ValueError()
        return claims
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid or expired token")

def current_user(request: Request, auth: HTTPAuthorizationCredentials = Depends(bearer)):
    if auth is None:
        raise HTTPException(401, "Authentication required")
    claims = decode(auth.credentials, "access")
    user = request.app.state.db.users.find_one({"_id": ObjectId(claims["sub"]), "is_active": True})
    if not user:
        raise HTTPException(401, "User is inactive or missing")
    return user

def roles(*allowed):
    def check(user=Depends(current_user)):
        if user["role"] != "Admin" and user["role"] not in allowed:
            raise HTTPException(403, "Your role does not permit this operation")
        return user
    return check

def verify(password, hashed):
    try:
        return passwords.verify(hashed, password)
    except VerificationError:
        return False
