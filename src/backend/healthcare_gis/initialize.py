"""Initialize the MongoDB schema and synthetic demo data."""
from healthcare_gis.database import connect, initialize, seed_demo

def main() -> None:
    client, db = connect()
    try:
        initialize(db)
        seed_demo(db)
        print(f"Database initialized: {db.hospitals.count_documents({'external_id': {'$regex': '^DEMO-'}})} demo hospitals, "
              f"{db.population_areas.count_documents({'area_code': {'$regex': '^DEMO-'}})} demo areas, "
              f"{db.roads.count_documents({'external_id': 'DEMO-R1'})} demo road")
    finally:
        client.close()

if __name__ == "__main__":
    main()
