# Executed synthetic evaluation

The integration test `tests/backend/test_workflow.py` ran on MongoDB 8 with the separate FastAPI ML service. All values below come from `var/evaluation/workflow.json` generated on 2026-09-25. The data is **synthetic** and does not describe actual health conditions.

The experiment generated 16 population areas, two hospitals, connected synthetic roads, and annual healthcare demand for 2012–2025. Training rows use preceding-period demand. Years were separated chronologically: 2013–2019 for training, 2020–2022 for validation, and 2023–2025 for a held-out test. Model selection used the lowest validation RMSE.

| Algorithm | Test MAE | Test RMSE | Test R² | Test MAPE |
|---|---:|---:|---:|---:|
| linear_regression | 32.80 | 34.46 | 0.995 | 1.51% |
| random_forest | 64.48 | 110.31 | 0.953 | 2.63% |
| xgboost | 66.03 | 110.52 | 0.953 | 2.71% |

Selected algorithm: **linear_regression**. The low error in this deterministic dataset is not evidence of real-world predictive accuracy.

| Scenario | Population within 30 minutes | Average travel minutes | HAI underserved population | Relative site-cost units |
|---|---:|---:|---:|---:|
| Existing hospitals | 75.5% | 21.91 | 79,000 | 0 |
| +1 hospital | 100.0% | 13.70 | 12,500 | 1 |
| +3 hospitals | 100.0% | 8.21 | 0 | 3 |
| +5 hospitals | 100.0% | 7.06 | 0 | 5 |

The genetic algorithm used seed 42, 20 chromosomes and 10 generations in this integration experiment. Cost was held equal for all sites because no parcel prices were supplied. Coverage counts area populations at their polygon representative center; travel time follows the synthetic road graph and a 5 km/h access leg. HAI classification uses the documented weights and thresholds. The optimizer is heuristic, does not prove global optimality, and does not validate land purchase, engineering, cost, or public-health feasibility.
