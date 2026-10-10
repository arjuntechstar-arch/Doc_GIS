# 03 DATABASE — MongoDB

## Storage and schema
MongoDB stores WGS84 GeoJSON documents. Local defaults are `mongodb://localhost:27017/` and database `dog_gis` (overridable by environment variables). `src/backend/healthcare_gis/database.py` is the authoritative versioned collection validator and index initializer. Initialize and seed using `python -m healthcare_gis.initialize`; operations are idempotent. The `schema_migrations` collection records the version (v1 core spatial collections, v2 jobs, models, boundaries, and refresh tokens). Add explicit upgrade steps for later versions; never silently downgrade. MongoDB `_id` is an ObjectId; API contracts serialize IDs as strings. References are ObjectIds, validated by service code.

## Collections
- `users`: username, email, password_hash, role, is_active, created_at, updated_at.
- `hospitals`: external_id, name, hospital_type, bed_capacity, emergency_available, specialty_count, location (GeoJSON Point), status, created_at, updated_at. Longitude/latitude are `location.coordinates` in that order.
- `population_areas`: area_code, name, population, population_density, age_0_14, age_15_59, age_60_plus, geometry (GeoJSON MultiPolygon), year.
- `roads`: external_id, road_type, speed_kmh, length_km, geometry (GeoJSON LineString).
- `healthcare_demand`: area_id, period, demand_value, source, created_at.
- `accessibility_results`: area_id, nearest_hospital_id, distance_km, travel_time_minutes, capacity_score, emergency_score, population_coverage, accessibility_index, classification, analysis_run_id.
- `demand_predictions`: area_id, prediction_period, predicted_demand, lower_bound, upper_bound, model_version, run_id.
- `candidate_sites`: name, location (Point), population_score, demand_score, road_access_score, land_suitability_score, cost_score, feasibility_status, generated_run_id.
- `optimization_runs`: number_of_sites, objective_configuration, status, started_at, completed_at, model_version, error_message.
- `recommendations`: optimization_run_id, candidate_site_id, rank, total_score, estimated_population_served, estimated_avg_travel_time, accessibility_improvement, explanation.
- `analysis_runs`: analysis_type, parameters, status, created_by, created_at, completed_at.
- `audit_logs`: user_id, action, entity_type, entity_id, metadata, created_at.

## Geospatial operations
Create `2dsphere` indexes on hospitals.location, population_areas.geometry, roads.geometry, and candidate_sites.location. Use `$geoNear`, `$near`, `$geoWithin`, `$geoIntersects` and GeoJSON for spatial relationships. `$geoNear` distances are metres; convert explicitly to km. For area intersection/centroids/unions and routing operations unavailable in MongoDB, use Shapely/GeoPandas in the analysis service; transform coordinates to an appropriate projected CRS before planar measurement. Use a road graph for travel times; straight-line distance is not travel time. Bounding boxes must account for antimeridian crossings.

MongoDB does not enforce foreign keys. Validate referenced IDs in services, use transactions for multi-document operations where needed (requires replica set), and keep required compound unique indexes. Server validators check required fields and primitive shapes; detailed geometry topology and coordinate bounds need ingestion validation.

Additional collections are `jobs` (persistent queue), `models` (training metadata), `refresh_tokens` (revocable token IDs with TTL), and `boundaries` (study and excluded land-use polygons).

## Demo data
Seed only deterministic, clearly labeled synthetic hospitals, population areas, and roads. Their coordinates and counts do not represent observed healthcare conditions.
