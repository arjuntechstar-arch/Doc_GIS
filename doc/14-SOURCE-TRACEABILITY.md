# 14 SOURCE TRACEABILITY

## Purpose
Every external dataset, algorithm, framework and important implementation decision must be traceable.

## Dataset register

Maintain a table:

| ID | Dataset | Provider | URL | License | Download Date | Version | Use |
|---|---|---|---|---|---|---|---|
| D001 | OpenStreetMap | OSM | project URL | ODbL | record actual date | actual version | roads/hospitals |
| D002 | Population | provider | actual URL | actual license | actual date | actual version | demand |

Do not invent URLs or licenses. Record them when actually selected.

## Model register

| Model | Version | Dataset Version | Features | Metrics | Date |
|---|---|---|---|---|---|

## Requirement traceability

| Requirement | Module | API | Test |
|---|---|---|---|
| FR-007 | Accessibility | POST /accessibility/analyze | accessibility integration test |
| FR-011 | ML | POST /demand/train | ML training test |
| FR-015 | Optimization | POST /optimization/runs | optimization test |

## Decision log
Document:
- why XGBoost was selected;
- why PostGIS is used;
- why Genetic Algorithm is used;
- assumptions;
- limitations.

## Academic integrity
Do not fabricate:
- dataset statistics
- model metrics
- accuracy
- population counts
- optimization savings
- external references

All final reported values must come from executed experiments.
