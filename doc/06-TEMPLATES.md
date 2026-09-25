# 06 TEMPLATES

## 6.1 Analysis configuration

```json
{
  "analysisName": "City Healthcare Accessibility - Baseline",
  "travelMode": "road",
  "weights": {
    "distance": 0.3,
    "travelTime": 0.3,
    "capacity": 0.2,
    "emergency": 0.2
  }
}
```

## 6.2 Training configuration

```yaml
model: xgboost
target: demand_value
validation: time_split
metrics:
  - mae
  - rmse
  - r2
random_seed: 42
```

## 6.3 Candidate generation configuration

```json
{
  "minPopulation": 5000,
  "minDemand": 1000,
  "minRoadAccessScore": 0.5,
  "minDistanceFromExistingHospitalKm": 3,
  "excludedLandUse": ["water", "protected_forest"]
}
```

## 6.4 Optimization configuration

```json
{
  "numberOfHospitals": 3,
  "populationCoverageWeight": 0.35,
  "demandCoverageWeight": 0.25,
  "accessibilityImprovementWeight": 0.25,
  "roadAccessWeight": 0.10,
  "costWeight": 0.05,
  "populationSize": 100,
  "generations": 150,
  "mutationRate": 0.05,
  "seed": 42
}
```

## 6.5 API error

```json
{
  "type": "https://httpstatuses.com/400",
  "title": "Validation failed",
  "status": 400,
  "detail": "The supplied analysis configuration is invalid.",
  "errors": {}
}
```

## 6.6 GeoJSON Feature example

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [80.27, 13.08]
  },
  "properties": {
    "candidateId": "..."
  }
}
```

## 6.7 Recommendation response

```json
{
  "rank": 1,
  "candidateSiteId": "...",
  "totalScore": 0.942,
  "estimatedPopulationServed": 82400,
  "estimatedAverageTravelTimeMinutes": 11.2,
  "accessibilityImprovement": 0.31,
  "explanation": {
    "primaryFactors": [
      "high underserved population",
      "strong road connectivity",
      "high predicted demand"
    ]
  }
}
```
