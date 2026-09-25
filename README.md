# Healthcare Atlas — GIS and future hospital planning

A local-first decision-support system for healthcare accessibility, demand forecasting, and hospital site selection. Backend: FastAPI. Data: MongoDB GeoJSON with `2dsphere` indexes. ML: a separate FastAPI service with scikit-learn and XGBoost. UI: Angular Material and Leaflet. See `doc/` for requirements, architecture, and API contracts.

**Demo data is entirely synthetic.** It cannot establish real hospital demand or site suitability. Recommendations require engineering, land, transport, financial, environmental, legal, and public-health assessment. The optimizer is a heuristic, not a proof of global optimality.

## Local setup

Requires Python 3.12+, Node.js 24+, npm, and a running MongoDB at `mongodb://localhost:27017/`. The requested database name is `dog_gis`. MongoDB must support GeoJSON `2dsphere` indexes. Install dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cd src/frontend/healthcare-gis-web && npm ci && cd ../../..
python scripts/configure.py
python scripts/bootstrap.py
python scripts/run.py
```

On Windows PowerShell, replace the first two commands with `py -3.12 -m venv .venv` and `.\.venv\Scripts\Activate.ps1`; the remaining commands are the same. The bootstrap command prompts for a password of at least 12 characters. It creates an Admin account named `admin` without resetting an existing account. `scripts/configure.py` creates ignored `.env` with random JWT and service keys. Edit the MongoDB URI in that file if your server uses authentication. Existing `.env` is never overwritten.

Open `http://localhost:4200` and sign in. The API documentation is at `http://localhost:8000/docs`; the ML service is on `127.0.0.1:8001` and requires `ML_SERVICE_KEY`. Start from your own aggregate GeoJSON or click **Load synthetic demo** as Admin. The demo loader is repeatable and adds 16 synthetic districts, two hospitals, connected roads, land-use boundaries and 14 years of generated demand. Then run Accessibility → Demand Training → Prediction → Candidate Generation → Optimization. Analyze +1, +3 and +5 hospital scenarios and export CSV, GeoJSON or PDF. Jobs appear in Analysis history and can be cancelled. A background worker starts with the API; one API process is appropriate for the local setup.

No manual database edits are needed. The schema initializer runs when the API starts. `python -m healthcare_gis.initialize` is available with `PYTHONPATH=src/backend` for the earlier two-area demo; the Dashboard demo loader expands that data and adds its historical demand. On Windows, run `set PYTHONPATH=src/backend` in Command Prompt or `$env:PYTHONPATH='src/backend'` in PowerShell before the module command.

## Tests and validation

```bash
# With your own MongoDB server, use only a disposable *_test database:
export HEALTHCARE_GIS_TEST_MONGO_URI=mongodb://localhost:27017/
python scripts/validate.py
cd src/frontend/healthcare-gis-web && npm run build && npm test
```

PowerShell: `$env:HEALTHCARE_GIS_TEST_MONGO_URI='mongodb://localhost:27017/'`. Tests delete the `dog_gis_test` and `dog_gis_api_test` databases. Never point test runs at a database you wish to preserve. If a `mongod` executable is available, `MONGOD_BINARY=/path/to/mongod python scripts/test_live.py` starts a disposable server on port 27018 instead. `scripts/test_browser.py` starts all services and runs the Playwright browser flow; install its browser first with `cd src/frontend/healthcare-gis-web && npx playwright install chromium --only-shell`.

The live suite tests schema, geospatial indexes, authentication, CRUD/imports, routing, HAI, forecasting, feasibility, GA, scenarios, and exports. The measured synthetic results are written to `var/evaluation/workflow.json` by the test and summarized in `doc/16-EVALUATION-RESULTS.md`. Do not use them as observed healthcare findings.

## Optional Docker deployment

The default setup uses your existing MongoDB. To run a password-protected isolated MongoDB: set `MONGO_ROOT_PASSWORD` in a local ignored `.env`, then `docker compose --env-file .env -f deployment/compose.yaml up -d`. For all services, use `docker compose --env-file .env -f deployment/full.yaml up --build -d`, then bootstrap an admin with `docker compose --env-file .env -f deployment/full.yaml exec api python -m healthcare_gis.bootstrap`. The full Compose stack serves the UI at `http://localhost:4200`. The `dog_gis` database inside Compose is separate from your host's local MongoDB. Keep the generated secrets in `.env` and provide a strong `MONGO_ROOT_PASSWORD`.

## Import formats

Uploads accept JSON arrays or GeoJSON FeatureCollections, up to 10 MB and 5,000 records. Hospital properties include `name`, `bed_capacity`, `emergency_available`, `specialty_count`, `hospital_type`, `status` and Point `location`. Population areas require `area_code`, `year`, `name`, `population`, `population_density`, age groups summing to population, and MultiPolygon `geometry`. Roads require `speed_kmh`, `length_km` and LineString `geometry`. Boundaries require Polygon `geometry`, `name`, and `land_use` (`boundary`, `water`, `protected_forest`, `residential`, `commercial`, or `vacant`). Demand observations use `area_id`, integer `period` year, nonnegative `demand_value`, and `source`. WGS84 coordinates are `[longitude, latitude]`. Network junctions should share coordinates at intersections; grade-separated crossings should not. Uploads are validated before insertion and partial batch writes are removed on rejection.

Forecast training needs at least 24 area/year observations spanning five years, with an earlier demand observation for each training row. Training separates years chronologically and compares Linear Regression, Random Forest, and XGBoost. A connected road graph, geographic boundaries, and forecasts are needed for candidate generation and optimization. Travel times use imported road speeds and a 5 km/h access leg; unreachable routes are labeled and receive a documented 240-minute penalty only inside optimizer fitness. Without parcel prices, site costs are assumed equal and reported as relative units. The model store is `MODEL_STORAGE`, outside source control.

For troubleshooting, confirm `python scripts/run.py` reports all services started, `/health` returns `{"status":"ok"}`, MongoDB port 27017 is reachable, and the frontend proxy is active. A failed job exposes its status and a bounded error in Analysis history. Change the MongoDB URI in `.env` if the host or authentication differs; restart services after configuration edits. Production use requires HTTPS, a restricted MongoDB account, shared rate limiting across replicas, secure secret storage, and a proper durable worker deployment.
