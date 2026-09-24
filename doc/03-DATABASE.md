# 03 DATABASE

## 3.1 Database
PostgreSQL with PostGIS extension.

## 3.2 Core tables

### users
- id UUID PK
- username
- email
- password_hash
- role
- is_active
- created_at
- updated_at

### hospitals
- id UUID PK
- external_id
- name
- hospital_type
- bed_capacity
- emergency_available
- specialty_count
- latitude
- longitude
- location geometry(Point, 4326)
- status
- created_at
- updated_at

### population_areas
- id UUID PK
- area_code
- name
- population
- population_density
- age_0_14
- age_15_59
- age_60_plus
- geometry geometry(MultiPolygon, 4326)
- year

### roads
- id UUID PK
- external_id
- road_type
- speed_kmh
- length_km
- geometry geometry(LineString, 4326)

### healthcare_demand
- id UUID PK
- area_id FK
- period
- demand_value
- source
- created_at

### accessibility_results
- id UUID PK
- area_id FK
- nearest_hospital_id FK nullable
- distance_km
- travel_time_minutes
- capacity_score
- emergency_score
- population_coverage
- accessibility_index
- classification
- analysis_run_id FK

### demand_predictions
- id UUID PK
- area_id FK
- prediction_period
- predicted_demand
- lower_bound nullable
- upper_bound nullable
- model_version
- run_id

### candidate_sites
- id UUID PK
- name
- location geometry(Point, 4326)
- population_score
- demand_score
- road_access_score
- land_suitability_score
- cost_score
- feasibility_status
- generated_run_id

### optimization_runs
- id UUID PK
- number_of_sites
- objective_configuration JSONB
- status
- started_at
- completed_at
- model_version
- error_message

### recommendations
- id UUID PK
- optimization_run_id FK
- candidate_site_id FK
- rank
- total_score
- estimated_population_served
- estimated_avg_travel_time
- accessibility_improvement
- explanation JSONB

### analysis_runs
- id UUID PK
- analysis_type
- parameters JSONB
- status
- created_by
- created_at
- completed_at

### audit_logs
- id UUID PK
- user_id
- action
- entity_type
- entity_id
- metadata JSONB
- created_at

## 3.3 Spatial indexes
Create GiST indexes on:
- hospitals.location
- population_areas.geometry
- roads.geometry
- candidate_sites.location

## 3.4 Required spatial operations
Use PostGIS for:
- ST_DWithin
- ST_Distance
- ST_Intersects
- ST_Contains
- ST_Within
- ST_Intersection
- ST_Transform
- ST_Union
- ST_Centroid

Do not use raw Euclidean latitude/longitude distance for production spatial calculations.

## 3.5 Migrations
All schema changes must use EF Core migrations.
Seed only deterministic demo data.
