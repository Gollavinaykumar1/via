# VIA Security Report

## Authentication & Authorization
- **Method**: JWT (JSON Web Tokens)
- **Hashing**: bcrypt via passlib
- **Token Expiry**: Configurable (default 30 min)
- **Storage**: Token stored client-side in localStorage

## Input Validation
- All API inputs validated via Pydantic models
- Field length constraints (min/max)
- SQL injection prevented via parameterized asyncpg queries

## Rate Limiting
- Custom middleware: configurable requests per minute
- Applied globally to all endpoints

## Network Security
- CORS middleware configured (currently allow_origins=["*"] — restrict in production)
- HTTPS enforced by deployment platform (Render)

## File System Security
- Path traversal protection in file browser router
- Allowed file extension whitelist
- File size limits (500KB max for viewing)

## Secrets Management
- All secrets loaded from .env via python-dotenv
- .env excluded from git via .gitignore

## Recommendations
1. Restrict CORS origins to specific domains in production
2. Add CSRF protection for cookie-based sessions
3. Implement token refresh mechanism
4. Add request signing for GitHub/Render API calls
5. Enable audit logging for all auth events
6. Add rate limiting per-user, not just global
7. Rotate JWT_SECRET_KEY periodically
