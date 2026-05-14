# Phase 2 API Testing Guide

## Quick Start

### 1. Start the System

```powershell
cd d:\Ads\AutoCategory\autocategory
docker-compose up -d
```

Wait for all services to be healthy:
```powershell
docker-compose ps
```

### 2. Initialize Database & Get Admin Token

```powershell
# Initialize database with admin user
docker-compose exec api python init_db.py

# Login as admin (default credentials)
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"admin\",\"password\":\"admin123\"}'
```

Save the `access_token` from response - you'll need it for admin endpoints.

### 3. Test Admin APIs

#### A. Request Logs Management

```powershell
# List all request logs
$TOKEN = "your-access-token-here"
curl -X GET "http://localhost:8000/api/admin/logs/requests" `
  -H "Authorization: Bearer $TOKEN"

# Get request statistics
curl -X GET "http://localhost:8000/api/admin/logs/stats" `
  -H "Authorization: Bearer $TOKEN"

# Filter logs by endpoint
curl -X GET "http://localhost:8000/api/admin/logs/requests?endpoint=classify&limit=10" `
  -H "Authorization: Bearer $TOKEN"

# Get single log details
curl -X GET "http://localhost:8000/api/admin/logs/requests/1" `
  -H "Authorization: Bearer $TOKEN"
```

#### B. Training Data Management

```powershell
# List training data
curl -X GET "http://localhost:8000/api/admin/training-data" `
  -H "Authorization: Bearer $TOKEN"

# Create training sample manually
curl -X POST "http://localhost:8000/api/admin/training-data" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Máy mới 100%, fullbox",
    "price": 30000000,
    "actual_category_id": 123,
    "actual_category_name": "Điện thoại",
    "source": "manual",
    "quality_score": 1.0
  }'

# Get training statistics
curl -X GET "http://localhost:8000/api/admin/training-data/stats/overview" `
  -H "Authorization: Bearer $TOKEN"

# Validate training sample
curl -X PATCH "http://localhost:8000/api/admin/training-data/1" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"is_validated": true}'

# Bulk validate multiple samples
curl -X POST "http://localhost:8000/api/admin/training-data/bulk-validate?data_ids=1&data_ids=2&data_ids=3" `
  -H "Authorization: Bearer $TOKEN"
```

#### C. System Configuration

```powershell
# List all configurations
curl -X GET "http://localhost:8000/api/admin/config" `
  -H "Authorization: Bearer $TOKEN"

# Get specific config
curl -X GET "http://localhost:8000/api/admin/config/THRESHOLD_AUTO_ASSIGN" `
  -H "Authorization: Bearer $TOKEN"

# Update configuration
curl -X PATCH "http://localhost:8000/api/admin/config/THRESHOLD_AUTO_ASSIGN" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "value": "0.92",
    "description": "Ngưỡng tự động gán (cập nhật)"
  }'

# Bulk update configs
curl -X POST "http://localhost:8000/api/admin/config/bulk-update" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "configs": [
      {"key": "THRESHOLD_AUTO_ASSIGN", "value": "0.90"},
      {"key": "THRESHOLD_PRESELECT", "value": "0.75"}
    ]
  }'

# Get config categories
curl -X GET "http://localhost:8000/api/admin/config/categories/list" `
  -H "Authorization: Bearer $TOKEN"
```

### 4. Test Rate Limiting

```powershell
# Create API key first
$response = curl -X POST "http://localhost:8000/api/auth/api-keys" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "name": "Test Key",
    "environment": "dev",
    "rate_limit_per_minute": 5,
    "rate_limit_per_day": 100
  }'

# Extract API key from response
$API_KEY = "sk_dev_xxxx"

# Make 6 requests quickly (should hit rate limit on 6th)
for ($i=1; $i -le 6; $i++) {
    Write-Host "Request $i"
    curl -X GET "http://localhost:8000/api/categories" `
      -H "X-API-Key: $API_KEY"
}

# Check rate limit headers in response
```

### 5. Test Request Logging Middleware

```powershell
# Make a classification request
curl -X POST "http://localhost:8000/api/classify" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{
    "title": "iPhone 15 Pro",
    "description": "Máy mới, chưa active",
    "price": 28000000
  }'

# Check if it was logged
curl -X GET "http://localhost:8000/api/admin/logs/requests?endpoint=classify&limit=1" `
  -H "Authorization: Bearer $TOKEN"

# Should see classification details in log
```

### 6. Test Error Cases

```powershell
# Try accessing admin endpoint without token (should get 401)
curl -X GET "http://localhost:8000/api/admin/logs/requests"

# Try with invalid token (should get 401)
curl -X GET "http://localhost:8000/api/admin/logs/requests" `
  -H "Authorization: Bearer invalid-token"

# Try accessing admin endpoint as developer (should get 403)
# First create developer user and login
curl -X POST "http://localhost:8000/api/auth/register" `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "username": "dev1",
    "password": "dev123",
    "email": "dev@example.com",
    "role": "developer"
  }'

# Login as developer
$DEV_TOKEN = "..."

# Try to delete training data (developers can read but only admins can delete)
curl -X DELETE "http://localhost:8000/api/admin/training-data/1" `
  -H "Authorization: Bearer $DEV_TOKEN"
```

## Testing Checklist

### Middleware
- [ ] Request logging captures all API calls
- [ ] Request logging skips /docs, /health endpoints
- [ ] Rate limiting works with API keys
- [ ] Rate limiting works with IP (no API key)
- [ ] Rate limit headers present in response
- [ ] Rate limit returns 429 when exceeded
- [ ] Redis failure doesn't break API

### Request Logs API
- [ ] List logs with pagination works
- [ ] Filter by endpoint works
- [ ] Filter by method works
- [ ] Filter by status code works
- [ ] Filter by user/API key works
- [ ] Filter by date range works
- [ ] Get single log works
- [ ] Statistics calculation correct
- [ ] Cleanup deletes old logs

### Training Data API
- [ ] List training data works
- [ ] Create training sample works
- [ ] Get single sample works
- [ ] Update sample works
- [ ] Validate sample works
- [ ] Delete sample works
- [ ] Statistics calculation correct
- [ ] Bulk validation works
- [ ] Only validated samples count for training

### System Config API
- [ ] List configs works
- [ ] Filter by category works
- [ ] Get single config works
- [ ] Create config works
- [ ] Update config works
- [ ] Delete config works
- [ ] Bulk update works
- [ ] Secret values are masked
- [ ] reveal_secret parameter works
- [ ] Config categories list works

### Permissions
- [ ] Admin can access all endpoints
- [ ] Developer can read training data
- [ ] Developer can read request logs
- [ ] Viewer cannot access admin endpoints
- [ ] Unauthenticated gets 401
- [ ] Wrong role gets 403

### Performance
- [ ] List endpoints respond in < 500ms
- [ ] Statistics queries respond in < 1s
- [ ] Middleware adds < 50ms overhead
- [ ] Pagination works for large datasets
- [ ] Rate limiting is fast (Redis)

## Common Issues

### Redis Connection Failed
**Symptom:** Warning in logs "Redis connection failed, rate limiting will be disabled"

**Solution:**
```powershell
# Check Redis container
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis
```

### Database Connection Failed
**Symptom:** 500 errors on all database queries

**Solution:**
```powershell
# Check PostgreSQL container
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Verify DATABASE_URL in .env
```

### Rate Limiting Not Working
**Symptom:** Can make unlimited requests

**Solution:**
1. Check Redis is running
2. Check API key has rate limits set
3. Check Redis keys: `docker-compose exec redis redis-cli KEYS "rate_limit:*"`

### Request Logs Empty
**Symptom:** `/api/admin/logs/requests` returns empty array

**Solution:**
1. Make some API calls first (classify, generate)
2. Check middleware is loaded: Look for middleware in app startup logs
3. Check database: `docker-compose exec postgres psql -U postgres -d autocategory -c "SELECT COUNT(*) FROM request_logs;"`

## Interactive API Documentation

Access interactive docs at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

All admin endpoints require Bearer token authentication. Click "Authorize" button and enter: `Bearer your-token-here`

## Monitoring

### Database Queries
```powershell
# Check table sizes
docker-compose exec postgres psql -U postgres -d autocategory -c "
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Check request log count
docker-compose exec postgres psql -U postgres -d autocategory -c "
SELECT COUNT(*) as total_logs, 
       COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as errors,
       COUNT(CASE WHEN was_corrected = true THEN 1 END) as corrections
FROM request_logs;
"
```

### Redis Keys
```powershell
# Check Redis keys
docker-compose exec redis redis-cli KEYS "*"

# Check rate limit keys
docker-compose exec redis redis-cli KEYS "rate_limit:*"

# Check specific rate limit
docker-compose exec redis redis-cli GET "rate_limit:minute:api_key_1:12345"
```

## Next Steps

After verifying Phase 2 core features work:

1. **Add Category Sync API** - Sync categories from main system
2. **Add System Control API** - Service health, logs, cache control
3. **Update Classification Endpoint** - Store results in request.state for logging
4. **Add Feedback Endpoint** - Allow users to correct classifications
5. **Create Phase 3 Frontend** - React dashboard for admins

---

**Phase 2 Core Features: Ready for Testing**

Last updated: 2025-01-07
