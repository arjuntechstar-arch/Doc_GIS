import os
import pytest
from pymongo import GEOSPHERE, MongoClient
from pymongo.errors import WriteError
from healthcare_gis.database import FIELDS, INDEXES, initialize, seed_demo


def test_all_collections_have_validators_and_spatial_indexes():
    assert len(FIELDS) == 12
    for name, field in [("hospitals", "location"), ("population_areas", "geometry"),
                        ("roads", "geometry"), ("candidate_sites", "location")]:
        assert FIELDS[name][1][field]["properties"]["type"]
        assert any((field, GEOSPHERE) in keys for keys, _ in INDEXES[name])


def test_migration_and_seed_on_disposable_mongodb():
    uri = os.environ.get("HEALTHCARE_GIS_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set HEALTHCARE_GIS_TEST_MONGO_URI to run MongoDB integration test")
    name = os.environ.get("HEALTHCARE_GIS_TEST_MONGO_DB", "dog_gis_test")
    assert name.endswith("_test"), "Test may only delete a database ending in _test"
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[name]
    try:
        client.drop_database(name)
        initialize(db)
        seed_demo(db)
        initialize(db)
        seed_demo(db)
        assert db.schema_migrations.find_one({"_id": "schema"})["version"] == 1
        assert db.hospitals.count_documents({}) == 2
        assert db.population_areas.count_documents({}) == 2
        assert db.roads.count_documents({}) == 1
        assert any(i.get("key", {}).get("location") == "2dsphere" for i in db.hospitals.list_indexes())
        assert db.hospitals.find_one({"location": {"$near": {"$geometry": {"type": "Point", "coordinates": [80.27, 13.08]}, "$maxDistance": 20000}}})
        with pytest.raises(WriteError):
            db.hospitals.insert_one({"name": "Invalid: missing required properties"})
    finally:
        client.drop_database(name)
        client.close()
