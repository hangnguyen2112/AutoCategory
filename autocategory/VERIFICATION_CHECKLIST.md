# Phase 1 Verification Checklist

Use this checklist to verify Phase 1 is correctly installed and working.

## Prerequisites
- [ ] Docker installed and running
- [ ] Docker Compose installed
- [ ] Ports 5432, 6379, 8000 available

## Setup Steps

### 1. Generate Secret Key
```bash
cd autocategory/api
python generate_secret.py
```
- [ ] SECRET_KEY generated
- [ ] Copied to `.env` file

### 2. Environment Configuration
```bash
cd ..
cp .env.example .env
nano .env  # or use your favorite editor
```

Required values in `.env`:
- [ ] `SECRET_KEY` - Set from step 1
- [ ] `POSTGRES_PASSWORD` - Set secure password
- [ ] `DATABASE_URL` - Updated with correct password
- [ ] `REDIS_URL` - Verified (default: `redis://redis:6379/0`)

### 3. Start Database Services
```bash
docker-compose up -d postgres redis
```

- [ ] PostgreSQL container started
- [ ] Redis container started

Wait 30 seconds for health checks:
```bash
docker-compose ps
```

- [ ] `autocategory-postgres` shows `Up (healthy)`
- [ ] `autocategory-redis` shows `Up (healthy)`

### 4. Initialize Database
```bash
docker-compose run --rm api python init_db.py
```

Expected output:
- [ ] "Database tables created successfully"
- [ ] "Admin user created successfully"
- [ ] Username: `admin`, Password: `admin123` displayed

### 5. Start API Service
```bash
docker-compose up -d api
```

- [ ] API container started

Check logs:
```bash
docker-compose logs api | grep -E "(Started|Creating database)"
```

- [ ] "Creating database tables..." message appears
- [ ] "Database tables created successfully" message appears
- [ ] "Uvicorn running on http://0.0.0.0:8000" message appears

### 6. Test Health Endpoint
```bash
curl http://localhost:8000/api/health
```

- [ ] Returns `{"status":"ok"}`

### 7. Test API Documentation
Open browser:
- [ ] http://localhost:8000/docs loads (Swagger UI)
- [ ] http://localhost:8000/redoc loads (ReDoc)
- [ ] See "Authentication" section with endpoints

### 8. Test Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

- [ ] Returns 200 OK
- [ ] Response includes `access_token`
- [ ] Response includes `refresh_token`
- [ ] Response includes `user` object with `role: "admin"`

Save the `access_token` for next steps:
```bash
export ACCESS_TOKEN="<paste_access_token_here>"
```

### 9. Test Get Current User
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

- [ ] Returns user object
- [ ] Shows `username: "admin"`
- [ ] Shows `role: "admin"`
- [ ] Shows `is_active: true`

### 10. Test Change Password
```bash
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "admin123",
    "new_password": "NewSecurePassword123!"
  }'
```

- [ ] Returns `{"message": "Password changed successfully"}`

Try logging in with new password:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "NewSecurePassword123!"}'
```

- [ ] Login successful with new password
- [ ] Old password no longer works

### 11. Test Create User (Admin Only)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer1",
    "email": "dev@example.com",
    "password": "DevPassword123!",
    "full_name": "John Developer",
    "role": "developer"
  }'
```

- [ ] Returns user object
- [ ] Shows `username: "developer1"`
- [ ] Shows `role: "developer"`

### 12. Test List Users
```bash
curl http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

- [ ] Returns array of users
- [ ] Contains admin user
- [ ] Contains developer1 user (if created)

### 13. Test Create API Key
```bash
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test API Key",
    "environment": "development",
    "rate_limit_per_minute": 60,
    "rate_limit_per_day": 1000,
    "can_classify": true,
    "can_generate": true,
    "can_admin": false
  }'
```

- [ ] Returns `api_key` (full key)
- [ ] Returns `key_info` object
- [ ] Key starts with `sk_dev_` (for development environment)

Save the API key:
```bash
export API_KEY="<paste_api_key_here>"
```

### 14. Test API Key Authentication
```bash
curl http://localhost:8000/api/health \
  -H "X-API-Key: $API_KEY"
```

- [ ] Returns `{"status":"ok"}`

### 15. Test List API Keys
```bash
curl http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

- [ ] Returns array of API keys
- [ ] Shows `key_prefix` (not full key)
- [ ] Shows usage stats (`total_requests`)

### 16. Test Classification with API Key
```bash
curl -X POST http://localhost:8000/api/classify \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Máy mới 100%, nguyên seal"
  }'
```

- [ ] Returns classification result
- [ ] Shows `category` information
- [ ] Shows `confidence` score

### 17. Test Role-Based Access Control

#### Try accessing admin endpoint with developer user:
First, login as developer:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "developer1", "password": "DevPassword123!"}'
```

Save developer token:
```bash
export DEV_TOKEN="<paste_developer_token_here>"
```

Try to access admin endpoint:
```bash
curl http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer $DEV_TOKEN"
```

- [ ] Returns `403 Forbidden`
- [ ] Error message mentions insufficient permissions

### 18. Database Verification

Connect to PostgreSQL:
```bash
docker-compose exec postgres psql -U autocategory -d autocategory
```

Check tables:
```sql
\dt
```

- [ ] Shows 9 tables: users, api_keys, request_logs, training_data, system_config, category_sync_history, training_jobs, model_versions, audit_logs

Check users:
```sql
SELECT id, username, role, is_active FROM users;
```

- [ ] Shows admin user
- [ ] Shows developer1 user (if created)

Check API keys:
```sql
SELECT id, key_prefix, name, user_id FROM api_keys;
```

- [ ] Shows created API keys

Exit:
```sql
\q
```

### 19. Redis Verification

Connect to Redis:
```bash
docker-compose exec redis redis-cli
```

Test ping:
```
PING
```

- [ ] Returns `PONG`

Exit:
```
EXIT
```

### 20. Docker Compose Services

Check all services:
```bash
docker-compose ps
```

- [ ] All services show `Up` status
- [ ] postgres shows `(healthy)`
- [ ] redis shows `(healthy)`
- [ ] api shows `Up`

Check logs for errors:
```bash
docker-compose logs | grep -i error
```

- [ ] No critical errors present

## Summary

### Quick Status Check
Run this command to verify everything is working:
```bash
echo "=== Docker Services ===" && \
docker-compose ps && \
echo -e "\n=== API Health ===" && \
curl -s http://localhost:8000/api/health && \
echo -e "\n\n=== Login Test ===" && \
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token' && \
echo -e "\nAll systems operational! ✅"
```

Expected output:
- Services: All `Up (healthy)`
- Health: `{"status":"ok"}`
- Login: Access token (long string)
- Final message: "All systems operational! ✅"

## Troubleshooting

### Common Issues

#### "Connection refused" error
- [ ] Check services are running: `docker-compose ps`
- [ ] Check ports are not in use: `lsof -i :5432,6379,8000`
- [ ] Restart services: `docker-compose restart`

#### "Database does not exist" error
- [ ] Run init_db.py: `docker-compose run --rm api python init_db.py`
- [ ] Check DATABASE_URL in `.env`

#### "Invalid authentication credentials" error
- [ ] Check SECRET_KEY in `.env` is set
- [ ] Verify token format: `Bearer <token>`
- [ ] Token may be expired - login again

#### "ModuleNotFoundError" error
- [ ] Install dependencies: `docker-compose build api`
- [ ] Restart API: `docker-compose restart api`

#### "403 Forbidden" error
- [ ] Verify user role has required permissions
- [ ] Check if user account is active
- [ ] Verify API key has required permission flags

## All Checks Passed? ✅

If all items above are checked:

🎉 **Phase 1 is successfully installed and working!**

**Next Steps:**
1. Review `AUTH_README.md` for detailed documentation
2. Read `PHASE1_SUMMARY.md` for what was accomplished
3. See `ADMIN_SYSTEM_PLAN.md` for Phase 2 plan
4. Start implementing Phase 2: Admin Backend APIs

**Recommended:**
- Change admin password from default
- Create users for your team
- Generate API keys for applications
- Test all endpoints in Swagger UI
- Review security settings in `.env`

---

**Need Help?**
- Documentation: `AUTH_README.md`
- Quick Start: `QUICKSTART.md`
- Logs: `docker-compose logs -f`
- Database: `docker-compose exec postgres psql -U autocategory -d autocategory`
