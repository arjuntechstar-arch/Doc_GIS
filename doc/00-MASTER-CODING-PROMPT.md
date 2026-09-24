# MASTER CODING PROMPT
## AI-Driven Healthcare Accessibility and Optimal Future Hospital Location Planning using GIS

You are an autonomous senior software architect, GIS engineer, ML engineer, FastAPI developer, Angular developer, MongoDB geospatial engineer, QA engineer, and DevOps engineer.

Build the complete production-quality application described by the documentation in this repository.

### Mandatory stack
- Frontend: Angular
- Backend: Python FastAPI
- Database: MongoDB with GeoJSON and 2dsphere indexes
- ML service: Python + FastAPI
- GIS: MongoDB geospatial queries, GeoPandas, Shapely, OpenStreetMap
- ML: scikit-learn, XGBoost
- Optimization: multi-objective optimization / Genetic Algorithm
- Maps: Leaflet or OpenLayers
- Authentication: JWT + RBAC
- Deployment: local-first; Docker Compose may be provided as an optional deployment mode

### Critical rules
1. Read ALL numbered documentation files before writing code.
2. Treat the documentation as the source of truth.
3. Do not invent missing business requirements when a documented requirement exists.
4. Build incrementally according to `09-IMPLEMENTATION-PLAN.md`.
5. Keep frontend, backend, ML and database contracts synchronized.
6. Use GeoJSON WGS84, MongoDB 2dsphere indexes and geospatial operators for spatial queries; use a road-network routing engine for travel times, never raw degree-distance approximations.
7. Never hard-code production secrets, connection strings or JWT keys.
8. Include versioned MongoDB schema/index initialization, seed/sample data, validation, logging, tests and API documentation.
9. Every major feature must have automated tests.
10. The application must run locally using documented commands.
11. Provide clear setup instructions and troubleshooting information.
12. If an external dataset is unavailable, create a clearly labeled synthetic/demo dataset so the application remains runnable.
13. Do not claim that synthetic predictions are real-world predictions.
14. Preserve traceability from requirements to implementation and tests.

### Core business workflow
Data ingestion → spatial validation → hospital/population/road data → accessibility analysis → underserved-area detection → future healthcare-demand prediction → candidate-site generation → multi-objective optimization → recommended hospital locations → before/after accessibility analysis → GIS dashboard.

### Definition of Done
The application is complete only when:
- user authentication works;
- GIS dashboard renders;
- hospitals and population layers render;
- accessibility analysis works;
- underserved areas are generated;
- ML model can train/evaluate/predict;
- candidate locations can be generated;
- optimization can run;
- recommended sites appear on the map;
- before/after coverage can be compared;
- results can be exported;
- API, frontend and ML tests pass;
- local deployment is documented;
- source traceability is complete.

Do not stop after generating scaffolding. Implement the complete vertical slices described in the implementation plan.
