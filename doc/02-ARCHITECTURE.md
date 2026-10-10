# 02 ARCHITECTURE

## 2.1 Logical architecture

```text
Angular Web GIS
      |
      v
FastAPI Web API
      |
  +---+-------------------+
  |                       |
  v                       v
MongoDB + 2dsphere     Python ML API
  |                       |
  |                 ML/Prediction
  |                 Optimization
  |
Spatial Analysis
```

## 2.2 Modules
- Identity
- Hospital Management
- Population Management
- Geographic Data
- Road Network
- Spatial Analysis
- Accessibility
- Demand Prediction
- Candidate Sites
- Optimization
- Recommendations
- GIS Visualization
- Reporting
- Audit

## 2.3 Recommended solution structure

```text
src/
  backend/
    healthcare_gis/
      api/
      services/
      models/
      database.py
  ml/
    healthcare_ml/
      api/
      data/
      features/
      models/
      training/
      prediction/
      optimization/
      spatial/
      tests/
  frontend/
    healthcare-gis-web/
      src/app/
        core/
        shared/
        auth/
        dashboard/
        map/
        hospitals/
        population/
        accessibility/
        demand/
        candidates/
        optimization/
        reports/
```

## 2.4 Architectural principles
- Modular FastAPI architecture with explicit service and persistence boundaries.
- Dependency inversion.
- DTOs at API boundaries.
- Repository/unit-of-work only where useful.
- Domain logic separated from infrastructure.
- Python service owns ML model execution.
- FastAPI service owns business workflow and authorization.
- MongoDB stores authoritative WGS84 GeoJSON and executes indexed geospatial queries; road travel times require a routing graph.
- Frontend never directly accesses the database.

## 2.5 Long-running jobs
Training, batch accessibility analysis and optimization must support asynchronous jobs.

Job lifecycle:
QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED.

## 2.6 Data flow
1. User uploads or imports data.
2. Validation service checks schema and geometry.
3. Data is stored in MongoDB.
4. Spatial feature engineering runs.
5. ML service trains or predicts.
6. Optimization engine generates recommendations.
7. Results are persisted.
8. Angular retrieves GeoJSON and analytics.
