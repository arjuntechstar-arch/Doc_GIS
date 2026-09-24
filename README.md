# Healthcare GIS — Phase 1 database

The full specification is in `doc/` on the `develop_gpt` branch. This branch implements Phase 1 for the revised FastAPI + MongoDB stack: versioned collection validators, GeoJSON documents, 2dsphere indexes, and deterministic synthetic demo data. The demo counts and coordinates are fabricated and must not be treated as observed healthcare conditions. The FastAPI application and authentication belong to Phase 2.

## Initialize with your local MongoDB

Python 3.12+ and an already running MongoDB instance at `mongodb://localhost:27017/` are required. The default database name is exactly `dog_gis`. Initialize the schema and synthetic demo records with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/backend/requirements.txt pytest
PYTHONPATH=src/backend python -m healthcare_gis.initialize
```

These defaults can be overridden using `HEALTHCARE_GIS_MONGO_URI` and `HEALTHCARE_GIS_MONGO_DB`. The initializer creates validators and indexes in `dog_gis`, then upserts the labeled demo data. It will not drop or replace existing records. Review the synthetic demo inserts before running it against a database with existing data.

If you need a separate MongoDB server, `deployment/compose.yaml` provides an optional password-protected instance. Set `MONGO_ROOT_PASSWORD`, run `docker compose -f deployment/compose.yaml up -d --wait`, and set `HEALTHCARE_GIS_MONGO_URI` to an authenticated URI. The default settings above are for your existing local server.

To inspect the result in `mongosh`:

```javascript
use dog_gis
db.hospitals.find({external_id: /^DEMO-/})
db.hospitals.getIndexes()
```

## Test

```bash
PYTHONPATH=src/backend python -m compileall -q src/backend
PYTHONPATH=src/backend pytest -q tests/backend
# Run the integration test against a dedicated disposable database (it is deleted):
export HEALTHCARE_GIS_TEST_MONGO_URI="mongodb://localhost:27017/"
export HEALTHCARE_GIS_TEST_MONGO_DB=dog_gis_test
PYTHONPATH=src/backend pytest -q tests/backend
```

The MongoDB integration test skips if `HEALTHCARE_GIS_TEST_MONGO_URI` is unset. Its database name must end with `_test`; it deletes that database before and after the test. The bootstrap currently uses the local administrator account. Use a least-privilege application account for later phases. If port 27017 is occupied, update the optional Compose host port and connection URI together. MongoDB `2dsphere` handles geospatial indexing and proximity queries; road-network travel time will require a routing graph in Phase 4.
