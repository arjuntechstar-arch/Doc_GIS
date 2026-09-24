# 09 IMPLEMENTATION PLAN

Build in phases. Each phase must compile and pass tests before continuing.

## Phase 0 - Repository foundation
- create repository
- add documentation
- add .gitignore
- add README
- create solution structure
- configure local settings templates

Acceptance:
- solution builds
- frontend starts
- Python environment starts

## Phase 1 - Database
- PostgreSQL/PostGIS
- EF Core
- entities
- migrations
- spatial indexes
- demo seed

Acceptance:
- database initializes
- migrations succeed
- demo records visible

## Phase 2 - Backend foundation
- API
- authentication
- RBAC
- Swagger
- ProblemDetails
- logging
- health checks

## Phase 3 - Hospital/population/GIS
- CRUD
- imports
- GeoJSON
- map endpoints

## Phase 4 - Accessibility
- spatial nearest-hospital analysis
- road travel-time approximation
- HAI
- underserved classification
- result persistence

## Phase 5 - ML demand prediction
- training dataset builder
- baseline model
- XGBoost
- evaluation
- model persistence
- prediction API

## Phase 6 - Candidate sites
- candidate generation
- land/geometry constraints
- scoring
- map visualization

## Phase 7 - Optimization
- genetic algorithm
- multi-objective scoring
- selected-site persistence
- before/after simulation

## Phase 8 - Dashboard
- KPI cards
- charts
- maps
- recommendation screen
- export

## Phase 9 - Testing
- unit
- integration
- API
- ML
- spatial
- end-to-end

## Phase 10 - Hardening
- security
- performance
- logging
- configuration
- documentation
- local deployment

## Phase 11 - Final validation
Run complete workflow:
Import → Analyze → Predict → Generate Candidates → Optimize → Compare → Export.

Never mark the project complete if any stage requires manual database editing.
