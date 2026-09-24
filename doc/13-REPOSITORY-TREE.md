# 13 REPOSITORY TREE

```text
healthcare-gis-ai/
│
├── docs/
│   ├── 00-MASTER-CODING-PROMPT.md
│   ├── 01-REQUIREMENTS.md
│   ├── 02-ARCHITECTURE.md
│   ├── 03-DATABASE.md
│   ├── 04-API-CONTRACTS.md
│   ├── 05-AI-RAG.md
│   ├── 06-TEMPLATES.md
│   ├── 07-FRONTEND.md
│   ├── 08-BACKEND.md
│   ├── 09-IMPLEMENTATION-PLAN.md
│   ├── 10-EVALUATION.md
│   ├── 11-SECURITY.md
│   ├── 12-WEEK-PLAN.md
│   ├── 13-REPOSITORY-TREE.md
│   ├── 14-SOURCE-TRACEABILITY.md
│   └── 15-README.md
│
├── src/
│   ├── backend/
│   │   ├── HealthcareGIS.Api/
│   │   ├── HealthcareGIS.Application/
│   │   ├── HealthcareGIS.Domain/
│   │   ├── HealthcareGIS.Infrastructure/
│   │   └── HealthcareGIS.Contracts/
│   │
│   ├── ml/
│   │   ├── healthcare_ml/
│   │   └── tests/
│   │
│   └── frontend/
│       └── healthcare-gis-web/
│
├── data/
│   ├── sample/
│   ├── raw/
│   └── processed/
│
├── tests/
│   ├── backend/
│   ├── frontend/
│   ├── ml/
│   └── e2e/
│
├── scripts/
├── deployment/
├── .env.example
├── docker-compose.yml
└── README.md
```

Keep generated datasets and model binaries out of git unless intentionally versioned.
