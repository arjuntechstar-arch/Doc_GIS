# AI-Driven Healthcare Accessibility and Optimal Future Hospital Location Planning using GIS

## Project summary
A GIS + AI decision-support platform that evaluates current healthcare accessibility, predicts future healthcare demand, identifies underserved areas and determines suitable locations for future hospitals using multi-objective optimization.

## Key technologies
- Angular
- FastAPI
- MongoDB GeoJSON + 2dsphere
- Python/FastAPI
- XGBoost
- scikit-learn
- GeoPandas
- OpenStreetMap
- Leaflet/OpenLayers

## Core workflow
```text
Data
 ↓
Spatial Processing
 ↓
Accessibility Analysis
 ↓
Demand Prediction
 ↓
Candidate Generation
 ↓
Optimization
 ↓
Hospital Recommendations
 ↓
Before/After Analysis
 ↓
GIS Dashboard
```

## Local development
The coding agent must provide exact commands after implementation.

Expected components:
1. MongoDB
2. FastAPI backend
3. Python ML API
4. Angular frontend

## Demo workflow
1. Login.
2. Load demo city dataset.
3. Open GIS Explorer.
4. Run accessibility analysis.
5. View underserved areas.
6. Train/load demand model.
7. Generate future demand.
8. Generate candidate sites.
9. Run optimization.
10. View recommended hospitals.
11. Compare baseline and proposed scenarios.
12. Export results.

## Important limitation
The application is a decision-support system. A recommended location is an algorithmic result based on configured data, constraints and objectives. It is not a substitute for engineering, financial, environmental, legal or public-health feasibility studies.

## Expected final deliverables
- Complete source code
- Versioned MongoDB schema/index initialization
- Demo dataset
- ML models/training scripts
- API documentation
- Frontend
- Automated tests
- Deployment instructions
- Evaluation report
- Architecture documentation
