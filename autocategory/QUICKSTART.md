# Quick Start Guide - Testing Authentication System

## Prerequisites
- Docker and Docker Compose installed
- Python 3.12+ (for local testing)

## Step-by-Step Setup

### 1. Generate JWT Secret Key
```bash
cd autocategory/api
python generate_secret.py
```

Copy the output and save it for the next step.

### 2. Create .env File
Copy `.env.example` to `.env`:
```bash
cd autocategory
cp .env.example .env
```

Edit `.env` and update these critical values:
```env
# Replace with your generated secret key
SECRET_KEY=your_generated_secret_key_from_step_1

# Set a secure database password
POSTGRES_PASSWORD=your_secure_database_password

# Update DATABASE_URL with the same password
DATABASE_URL=postgresql://autocategory:your_secure_database_password@postgres:5432/autocategory
```

### 3. Start Database Services
```bash
docker-compose up -d postgres redis
```

Wait for health checks (30 seconds):
```bash
docker-compose ps
```

You should see:
```
NAME                 STATUS          PORTS
autocategory-postgres   Up (healthy)   5432/tcp
autocategory-redis      Up (healthy)   6379/tcp
```

### 4. Initialize Database
```bash
# Method 1: Using docker-compose (recommended)
docker-compose run --rm api python init_db.py

# Method 2: If API service is running
docker-compose exec api python init_db.py
```

Expected output:
```
============================================================
AutoCategory Database Initialization
============================================================
Creating database tables...
✓ Database tables created successfully
Creating admin user...
✓ Admin user created successfully
  Username: admin
  Password: admin123
  ⚠️  Please change the admin password after first login!
============================================================
✓ Database initialization completed successfully!
============================================================
```

### 5. Start API Service
```bash
docker-compose up -d api
```

Check logs:
```bash
docker-compose logs -f api
```

You should see:
```
Creating database tables...
✓ Database tables created successfully
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6. Test Authentication

#### A. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Save the `access_token` for the next steps!**

#### B. Get Current User Info
```bash
# Replace <ACCESS_TOKEN> with the token from step A
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

#### C. Change Admin Password
```bash
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "admin123",
    "new_password": "MyNewSecurePassword123!"
  }'
```

#### D. Create a New User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer1",
    "email": "dev@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Developer",
    "role": "developer"
  }'
```

#### E. Create API Key
```bash
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
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

**Important:** Save the `api_key` from the response - it's only shown once!

#### F. Test API Key
```bash
# Replace <API_KEY> with the key from step E
curl http://localhost:8000/api/classify \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Máy mới 100%, nguyên seal"
  }'
```

### 7. Access API Documentation
Open your browser and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

You can test all endpoints interactively using the "Authorize" button with your access token.

## Troubleshooting

### Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Wait for health check to pass (30 seconds)

3. Check database credentials in `.env`

4. View PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

### Redis Connection Error
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions:**
1. Check Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Verify REDIS_URL in `.env`

### Invalid Token Error
```
401 Unauthorized: Invalid authentication credentials
```

**Solutions:**
1. Token may have expired - login again
2. Check Authorization header format: `Bearer <token>`
3. Verify SECRET_KEY in `.env` matches the one used to create tokens

### Import Errors
```
ModuleNotFoundError: No module named 'models'
```

**Solutions:**
1. Make sure you're in the correct directory:
   ```bash
   cd autocategory/api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Testing with Postman

### 1. Import Collection
Create a new Postman collection with these requests:

**Environment Variables:**
- `base_url`: `http://localhost:8000`
- `access_token`: (will be set after login)

### 2. Login Request
```
POST {{base_url}}/api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Tests Script:**
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("access_token", response.access_token);
    pm.environment.set("refresh_token", response.refresh_token);
}
```

### 3. Authenticated Requests
Add to Headers:
```
Authorization: Bearer {{access_token}}
```

## Next Steps

After verifying authentication works:

1. **Test All Endpoints**
   - Try creating multiple users with different roles
   - Test role-based access control
   - Create API keys with different permissions
   - Verify rate limiting

2. **Database Inspection**
   ```bash
   # Connect to PostgreSQL
   docker-compose exec postgres psql -U autocategory -d autocategory
   
   # List tables
   \dt
   
   # View users
   SELECT id, username, email, role, is_active FROM users;
   
   # View API keys
   SELECT id, key_prefix, name, user_id, is_active FROM api_keys;
   
   # Exit
   \q
   ```

3. **Monitor Logs**
   ```bash
   # API logs
   docker-compose logs -f api
   
   # Database logs
   docker-compose logs -f postgres
   
   # All services
   docker-compose logs -f
   ```

4. **Proceed to Phase 2**
   See `ADMIN_SYSTEM_PLAN.md` for Phase 2 implementation:
   - Request logging middleware
   - Admin APIs for data management
   - System configuration endpoints
   - Category synchronization

## Production Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Generate new SECRET_KEY (never reuse development keys)
- [ ] Set strong POSTGRES_PASSWORD
- [ ] Configure CORS_ORIGINS (don't use `*`)
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limits appropriately
- [ ] Set up database backups
- [ ] Enable audit logging
- [ ] Review and restrict API key permissions
- [ ] Set up monitoring and alerts
- [ ] Use Alembic migrations instead of init_db.py
- [ ] Configure log rotation
- [ ] Set DATA_RETENTION_DAYS appropriately

## Support

For issues or questions:
- Check `AUTH_README.md` for detailed documentation
- Review `ADMIN_SYSTEM_PLAN.md` for the full roadmap
- Check Docker logs for error messages
- Verify environment variables in `.env`
