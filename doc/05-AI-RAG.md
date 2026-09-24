# 05 AI / ML / OPTIMIZATION

## 5.1 ML objectives

### Model A: Healthcare demand prediction
Target: healthcare demand by geographic area and time period.

Candidate models:
1. Baseline: Linear Regression
2. Random Forest
3. XGBoost
4. Optional LightGBM

Use time-aware validation when temporal data exists.

Metrics:
- MAE
- RMSE
- R²
- MAPE where appropriate

### 5.2 Features
- population
- population_density
- population_growth
- elderly_ratio
- child_ratio
- historical_demand
- hospital_count
- total_beds
- nearest_hospital_distance
- nearest_hospital_travel_time
- emergency_coverage
- disease indicators if legally and ethically appropriate
- socioeconomic indicators where available

### 5.3 Healthcare Accessibility Index

Normalize component scores to [0,1].

Example:
```text
HAI =
0.30 * distance_score
+ 0.30 * travel_time_score
+ 0.20 * capacity_score
+ 0.20 * emergency_score
```

Weights must be configurable.

Higher HAI = better accessibility.

Classification:
- 0.00–0.24 Critical
- 0.25–0.49 Poor
- 0.50–0.74 Moderate
- 0.75–1.00 Good

These thresholds are configuration defaults, not universal healthcare standards.

### 5.4 Candidate-site scoring
Candidate sites receive:
- population coverage score
- predicted demand score
- road accessibility score
- land suitability score
- cost score
- distance from existing hospitals

### 5.5 Optimization
Implement a multi-objective optimization workflow.

Objectives:
MAX population coverage
MAX predicted demand coverage
MAX accessibility improvement
MAX road accessibility
MIN estimated cost
MIN average travel time

Use Genetic Algorithm initially.

Chromosome:
```text
[candidate_site_12, candidate_site_44, candidate_site_71]
```

Fitness:
```text
fitness =
w1*populationCoverage
+w2*demandCoverage
+w3*accessibilityImprovement
+w4*roadAccess
-w5*cost
```

Apply:
- selection
- crossover
- mutation
- elitism
- duplicate-location prevention
- feasibility constraints

### 5.6 Explainability
For demand prediction:
- feature importance
- SHAP where practical

For recommendations:
Return structured explanation:
```json
{
  "primaryFactors": [
    "high underserved population",
    "high predicted demand",
    "low current accessibility",
    "good road connectivity"
  ]
}
```

Never present an algorithmic recommendation as a guaranteed real-world optimal decision.

### 5.7 Model versioning
Every trained model must have:
- model_version
- training_data_version
- feature_schema_version
- algorithm
- hyperparameters
- metrics
- created_at

Save models outside source code and configure the storage location.
