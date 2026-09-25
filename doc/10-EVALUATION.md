# 10 EVALUATION

## 10.1 ML evaluation
For demand prediction:
- MAE
- RMSE
- R²
- MAPE when meaningful

Compare at least:
- baseline
- Random Forest
- XGBoost

Use train/validation/test separation appropriate to temporal data.

## 10.2 Spatial evaluation
Measure:
- percentage population within configured travel-time threshold
- average travel time
- median travel time
- underserved population
- hospital capacity coverage

## 10.3 Optimization evaluation
Compare:
- existing network
- optimized network

Metrics:
- population coverage improvement
- demand coverage improvement
- average travel time reduction
- underserved population reduction
- estimated cost

Do not claim that an optimization solution is globally optimal unless the mathematical method and constraints justify that claim.

## 10.4 Scenario evaluation
At minimum:
Scenario A: existing hospitals
Scenario B: +1 hospital
Scenario C: +3 hospitals
Scenario D: +5 hospitals

Generate comparative results.

## 10.5 Explainability
Show:
- model feature importance
- SHAP plots when used
- optimization objective contributions
- recommendation factors

## 10.6 Academic outputs
Generate:
- methodology
- dataset description
- preprocessing
- model comparison
- evaluation metrics
- GIS maps
- optimization results
- limitations
- future work
