# Authentication System - Phase 1 Complete

## Overview
This document describes the authentication and authorization system for AutoCategory API.

## Architecture

### Database Layer
- **PostgreSQL 16-alpine** - Primary database
- **Redis 7-alpine** - Session management and rate limiting
- **SQLAlchemy 2.0.35** - ORM with declarative models
- **Alembic 1.14.0** - Database migrations (for production)

### Authentication Methods
1. **JWT Tokens** - For web dashboard and admin APIs
   - Access Token: 24 hours expiration
   - Refresh Token: 30 days expiration
   - Algorithm: HS256

2. **API Keys** - For programmatic access
   - Format: `sk_live_...`, `sk_dev_...`, `sk_test_...`
   - Stored as SHA-256 hash
   - Per-key rate limits and permissions

### Database Schema

#### Users Table
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email
- `password_hash` - Bcrypt hashed password
- `role` - admin, developer, viewer
- `is_active` - Account status
- `last_login_at` - Last login timestamp

#### API Keys Table
- `id` - Primary key
- `key_hash` - SHA-256 hash of API key
- `key_prefix` - Display prefix (first 16 chars)
- `user_id` - Foreign key to users
- `rate_limit_per_minute` - Rate limit
- `rate_limit_per_day` - Daily limit
- `can_classify` - Classification permission
- `can_generate` - Generation permission
- `can_admin` - Admin permission
- `total_requests` - Usage counter
- `expires_at` - Expiration datetime

#### Other Tables
- `request_logs` - All API requests with metrics
- `training_data` - Collected training samples
- `system_config` - Dynamic configuration
- `category_sync_history` - Category synchronization logs
- `training_jobs` - Model training jobs
- `model_versions` - Model version management
- `audit_logs` - Audit trail for compliance

## Setup Instructions

### 1. Generate SECRET_KEY
```bash
cd autocategory/api
python generate_secret.py
```

Copy the generated key and add to `.env` file:
```env
SECRET_KEY=your_generated_secret_key_here
```

### 2. Configure Environment
Update `.env` file with database credentials:
```env
# Database
POSTGRES_USER=autocategory
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=autocategory
DATABASE_URL=postgresql://autocategory:your_secure_password@postgres:5432/autocategory

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=your_generated_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### 3. Start Services
```bash
cd autocategory
docker-compose up -d postgres redis
```

Wait for health checks to pass:
```bash
docker-compose ps
```

### 4. Initialize Database
```bash
docker-compose exec api python init_db.py
```

This will:
- Create all database tables
- Create default admin user (username: `admin`, password: `admin123`)

### 5. Change Admin Password
After initialization, login as admin and change the password:
```bash
POST /api/auth/change-password
{
  "old_password": "admin123",
  "new_password": "your_new_secure_password"
}
```

## API Endpoints

### Authentication

#### POST `/api/auth/login`
Login with username and password

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true
  }
}
```

#### POST `/api/auth/refresh`
Refresh access token using refresh token

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:** Same as login response

#### GET `/api/auth/me`
Get current user information

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "System Administrator",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login_at": "2024-01-01T12:00:00Z"
}
```

#### POST `/api/auth/change-password`
Change current user's password

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "old_password": "admin123",
  "new_password": "new_secure_password"
}
```

### User Management (Admin Only)

#### POST `/api/auth/register`
Create a new user (admin only)

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Request:**
```json
{
  "username": "developer1",
  "email": "dev@example.com",
  "password": "secure_password",
  "full_name": "John Developer",
  "role": "developer"
}
```

#### GET `/api/auth/users`
List all users (admin only)

**Query Parameters:**
- `skip` - Number of records to skip (default: 0)
- `limit` - Maximum number of records (default: 100)

#### GET `/api/auth/users/{user_id}`
Get user by ID (admin only)

#### PATCH `/api/auth/users/{user_id}`
Update user (admin only)

**Request:**
```json
{
  "email": "newemail@example.com",
  "role": "developer",
  "is_active": true
}
```

#### DELETE `/api/auth/users/{user_id}`
Delete user (admin only)

### API Key Management

#### POST `/api/auth/api-keys`
Create a new API key

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "Production API Key",
  "environment": "production",
  "rate_limit_per_minute": 60,
  "rate_limit_per_day": 10000,
  "can_classify": true,
  "can_generate": true,
  "can_admin": false,
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Response:**
```json
{
  "api_key": "sk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "key_info": {
    "id": 1,
    "name": "Production API Key",
    "key_prefix": "sk_live_xxxxxxxx...",
    "environment": "production",
    "rate_limit_per_minute": 60,
    "rate_limit_per_day": 10000,
    "can_classify": true,
    "can_generate": true,
    "can_admin": false,
    "total_requests": 0,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

⚠️ **Important:** The full API key is only shown once during creation. Save it securely!

#### GET `/api/auth/api-keys`
List current user's API keys

**Headers:**
```
Authorization: Bearer <access_token>
```

#### DELETE `/api/auth/api-keys/{key_id}`
Revoke an API key

**Headers:**
```
Authorization: Bearer <access_token>
```

## Using API Keys

### Header-based Authentication
Add API key to `X-API-Key` header:

```bash
curl -H "X-API-Key: sk_live_xxxxxxxxxxxx" \
     https://api.example.com/api/classify
```

### Rate Limiting
Each API key has per-minute and per-day rate limits:
- Default: 60 requests/minute, 1000 requests/day
- Configurable per key
- Returns `429 Too Many Requests` when exceeded

### Permissions
API keys have granular permissions:
- `can_classify` - Can use classification endpoints
- `can_generate` - Can use generation endpoints
- `can_admin` - Can access admin endpoints

## Role-Based Access Control (RBAC)

### Roles

#### Admin
- Full system access
- User management (create, update, delete users)
- API key management
- System configuration
- Training management
- All API access

#### Developer
- Create and manage own API keys
- View logs and monitoring
- Export data
- Use classification and generation APIs

#### Viewer
- Read-only access
- View logs and monitoring
- No API access

### Checking Permissions in Code

```python
from dependencies import CurrentUser, CurrentAdminUser
from auth import require_permission, Permission

# Require authenticated user
@router.get("/protected")
async def protected_route(current_user: CurrentUser):
    return {"user": current_user.username}

# Require admin role
@router.post("/admin-only")
async def admin_route(current_admin: CurrentAdminUser):
    return {"message": "Admin access granted"}

# Check specific permission
@router.post("/custom")
async def custom_route(current_user: CurrentUser):
    require_permission(current_user.role, Permission.DATA_EXPORT)
    return {"message": "Permission granted"}
```

## Security Best Practices

### Password Security
- Minimum 8 characters
- Hashed with bcrypt (high cost factor)
- Never stored in plain text
- Regular password rotation recommended

### API Key Security
- Store API keys securely (environment variables, secrets manager)
- Use different keys for development and production
- Set appropriate rate limits
- Set expiration dates for temporary access
- Revoke unused keys immediately
- Monitor usage for suspicious activity

### JWT Token Security
- Short-lived access tokens (24 hours)
- Longer refresh tokens (30 days)
- Tokens signed with HS256
- SECRET_KEY must be kept secure
- Tokens invalidated on password change (future enhancement)

### Database Security
- Connection pooling with limits
- Prepared statements (SQLAlchemy ORM)
- Foreign key constraints
- Audit logging for compliance

## Monitoring and Logging

### Request Logs
All API requests are logged to `request_logs` table:
- Endpoint, method, response time
- Classification details (if applicable)
- User feedback (corrections)
- IP address, user agent

### Audit Logs
Security-sensitive actions logged to `audit_logs` table:
- User creation/modification/deletion
- API key generation/revocation
- System configuration changes
- Role changes

### Usage Analytics
Track API key usage:
- Total requests
- Last used timestamp
- Rate limit violations

## Troubleshooting

### Database Connection Failed
```
Error: could not connect to server
```

**Solution:**
- Check PostgreSQL is running: `docker-compose ps postgres`
- Verify DATABASE_URL in .env
- Check network connectivity

### Invalid Token
```
401 Unauthorized: Invalid authentication credentials
```

**Solution:**
- Token may be expired - use refresh token
- SECRET_KEY may have changed - login again
- Token format incorrect - check Authorization header

### API Key Not Working
```
401 Unauthorized: Invalid API key
```

**Solution:**
- Check API key is active (not revoked)
- Verify key hasn't expired
- Ensure key has required permissions
- Check rate limits not exceeded

### Permission Denied
```
403 Forbidden: Insufficient permissions
```

**Solution:**
- Check user role has required permission
- Verify API key has permission flags set
- Contact admin to grant access

## Next Steps (Phase 2)

After completing Phase 1 (Authentication & Database), the next phase includes:

1. **Admin Backend APIs**
   - Request log management
   - Training data management
   - System configuration API
   - Category synchronization
   - Model version management

2. **Request Logging Middleware**
   - Auto-log all API requests
   - Track response times
   - Collect training data from corrections

3. **Rate Limiting Middleware**
   - Redis-based rate limiting
   - Per-API-key limits
   - Global limits

4. **API Documentation**
   - OpenAPI/Swagger UI
   - Interactive testing
   - Code examples

See `ADMIN_SYSTEM_PLAN.md` for the complete 12-week roadmap.
