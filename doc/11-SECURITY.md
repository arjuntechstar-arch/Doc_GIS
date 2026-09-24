# 11 SECURITY

## Authentication
Use JWT access tokens.

## Authorization
Roles:
- Admin
- GISAnalyst
- HealthcarePlanner
- Viewer

Use policy-based authorization where appropriate.

## Secrets
Never commit:
- JWT secret
- DB password
- API keys
- external service credentials

Use environment variables or local secret storage.

## File uploads
Validate:
- extension
- MIME type
- file size
- schema
- geometry
- row count

Do not execute uploaded files.

## API security
- HTTPS in production
- rate limiting
- CORS allowlist
- input validation
- parameterized queries
- anti-forgery considerations for browser flows
- secure password hashing

## Data privacy
Do not store identifiable patient records in the default project.

If health-related datasets are added:
- minimize data
- prefer aggregate geographic data
- remove direct identifiers
- document legal/ethical basis
- avoid displaying individual patient locations

## Logging
Never log:
- passwords
- JWTs
- API secrets
- patient identifiers

## GIS security
Restrict expensive spatial queries and large bounding boxes to prevent resource exhaustion.
