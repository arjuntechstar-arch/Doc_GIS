# 08 BACKEND

## 8.1 .NET 10
Use ASP.NET Core Web API.

Layers:
- API
- Application
- Domain
- Infrastructure
- Contracts

## 8.2 Patterns
- CQRS-style handlers where useful
- FluentValidation or equivalent
- EF Core
- PostGIS spatial types
- dependency injection
- centralized exception handling
- ProblemDetails

## 8.3 Services
- HospitalService
- PopulationService
- SpatialAnalysisService
- AccessibilityService
- DemandPredictionService
- CandidateSiteService
- OptimizationService
- ReportService
- AuditService

## 8.4 ML integration
The .NET API calls Python FastAPI for:
- train
- predict
- explain
- optimize

Use typed HTTP clients.
Implement:
- timeout
- retry for safe transient calls
- correlation ID
- structured logs

## 8.5 Background processing
Long-running analysis should not block HTTP requests.

Implement a job abstraction first. A local database-backed job queue is acceptable for the initial version. Keep the interface replaceable by Hangfire/Quartz/Azure Service Bus later.

## 8.6 Spatial response
Return GeoJSON from dedicated GIS endpoints.

## 8.7 Validation
Validate:
- coordinates
- geometry SRID
- numeric ranges
- weights sum
- number of hospitals
- file format
- required fields
- duplicate records

## 8.8 Observability
Include:
- structured logging
- request correlation
- duration
- job status
- ML run ID
- analysis run ID
- errors

Do not log passwords, tokens or sensitive personal information.
