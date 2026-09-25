"""Create the initial administrator without a committed default password."""
import getpass
import os
from healthcare_gis.database import connect, initialize
from healthcare_gis.security import passwords, now

def main():
    client, db = connect()
    try:
        initialize(db)
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Administrator password (12+ characters): ")
        if len(password) < 12: raise ValueError("Password requires at least 12 characters")
        db.users.update_one({"username": username}, {"$setOnInsert": {"email": os.getenv("ADMIN_EMAIL", "admin@localhost.example"), "password_hash": passwords.hash(password), "role": "Admin", "is_active": True, "created_at": now(), "updated_at": now()}}, upsert=True)
        print("Administrator ready; existing accounts were not overwritten")
    finally: client.close()

if __name__ == "__main__": main()
