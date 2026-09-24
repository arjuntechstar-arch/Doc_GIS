# 04 API CONTRACTS

Base URL:
`/api/v1`

## Authentication
POST `/auth/login`
POST `/auth/refresh`
GET `/auth/me`

## Hospitals
GET `/hospitals`
GET `/hospitals/{id}`
POST `/hospitals`
PUT `/hospitals/{id}`
DELETE `/hospitals/{id}`
POST `/hospitals/import`

## Population
GET `/population/areas`
GET `/population/areas/{id}`
POST `/population/import`

## GIS
GET `/gis/hospitals?bbox=...`
GET `/gis/population?bbox=...`
GET `/gis/candidates?bbox=...`
GET `/gis/accessibility?bbox=...`

## Accessibility
POST `/accessibility/analyze`
GET `/accessibility/runs/{id}`
GET `/accessibility/results?runId=...`
GET `/accessibility/summary?runId=...`

Request example:
```json
{
  "areaIds": [],
  "weights": {
    "distance": 0.3,
    "travelTime": 0.3,
    "capacity": 0.2,
    "emergency": 0.2
  }
}
```

## Demand prediction
POST `/demand/train`
POST `/demand/predict`
GET `/demand/models`
GET `/demand/runs/{id}`

## Candidate sites
POST `/candidate-sites/generate`
GET `/candidate-sites`
GET `/candidate-sites/{id}`

## Optimization
POST `/optimization/runs`
GET `/optimization/runs/{id}`
GET `/optimization/runs/{id}/recommendations`

Request:
```json
{
  "numberOfHospitals": 3,
  "objectiveWeights": {
    "populationCoverage": 0.35,
    "demandCoverage": 0.25,
    "accessibilityImprovement": 0.25,
    "roadAccess": 0.1,
    "cost": 0.05
  }
}
```

## Reports
GET `/reports/accessibility/{runId}`
GET `/reports/optimization/{runId}`
GET `/reports/export/{runId}?format=csv`

## Jobs
GET `/jobs/{id}`
POST `/jobs/{id}/cancel`

## API conventions
- ProblemDetails for errors.
- Pagination for collection endpoints.
- Consistent validation errors.
- UTC timestamps.
- GeoJSON for spatial result endpoints.
- FastAPI OpenAPI/Swagger enabled.
