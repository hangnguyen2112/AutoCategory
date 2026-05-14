# 🚀 Hướng Dẫn Deploy AutoCategory

## Chuẩn Bị

### 1. Yêu Cầu Hệ Thống
- Docker & Docker Compose
- Node.js 18+ & npm
- Tài khoản Cloudflare (free tier)
- Domain đã add vào Cloudflare

### 2. Cấu Hình Cloudflare

#### Bước 1: Tạo API Token
1. Vào https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token** → **Create Custom Token**
3. Cấp quyền:
   - `Cloudflare Tunnel` → `Edit`
   - `DNS` → `Edit` (chọn zone của domain)
4. Click **Continue to summary** → **Create Token**
5. Copy token (chỉ hiển thị 1 lần!)

#### Bước 2: Lấy Account ID
1. Vào https://dash.cloudflare.com
2. Sidebar bên trái, phần dưới → copy **Account ID**

### 3. Cấu Hình Môi Trường

Copy `.env.example` thành `.env`:
```bash
cp .env.example .env
```

Sửa các giá trị sau trong `.env`:

```bash
# ── Database (QUAN TRỌNG: Đổi mật khẩu!) ──────────────────
POSTGRES_PASSWORD=YourSecurePassword123!@#

# ── JWT Authentication (QUAN TRỌNG: Đổi secret key!) ────────
SECRET_KEY=your-random-64-char-hex-string-here
# Generate: python -c "import secrets; print(secrets.token_hex(32))"

# ── Cloudflare Tunnel ─────────────────────────────────────
CF_API_TOKEN=your_cloudflare_api_token_here
CF_ACCOUNT_ID=your_cloudflare_account_id_here
CF_SUBDOMAIN=autocategory
CF_DOMAIN=yourdomain.com
CF_TUNNEL_NAME=autocategory

# ── CORS (Thêm domain của bạn) ────────────────────────────
CORS_ORIGINS=http://localhost,http://localhost:3000,http://localhost:3001,https://autocategory.yourdomain.com
```

## Deployment

### Option 1: Deploy Script Tự Động (Khuyên Dùng)

#### Windows:
```powershell
.\deploy.ps1
```

#### Linux/Mac:
```bash
chmod +x deploy.sh
./deploy.sh
```

Script tự động:
1. ✅ Build admin dashboard
2. ✅ Build Docker images
3. ✅ Start tất cả services
4. ✅ Setup Cloudflare Tunnel
5. ✅ Initialize database
6. ✅ Import categories

### Option 2: Deploy Thủ Công

#### Bước 1: Build Admin Dashboard
```bash
cd admin-dashboard
npm install
npm run build
cd ..
```

#### Bước 2: Start Services
```bash
# Stop containers cũ (nếu có)
docker-compose down

# Build và start services
docker-compose up -d llama-server qdrant postgres redis

# Đợi services khởi động (30s)
sleep 30

# Start API và Nginx
docker-compose up -d api nginx

# Đợi API ready (20s)
sleep 20
```

#### Bước 3: Setup Cloudflare Tunnel
```bash
# Run setup script (chạy 1 lần)
docker-compose --profile setup up cf-setup

# Start tunnel daemon
docker-compose --profile tunnel up -d cloudflared
```

#### Bước 4: Initialize Database
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create admin user (username: admin, password: admin123)
docker-compose exec api python scripts/init_admin.py

# Import categories
docker-compose exec api python scripts/import_categories.py --file /app/data/categories.json

# Build Qdrant index
curl -X POST http://localhost/api/admin/build-index
```

## Kiểm Tra Deployment

### 1. Check Service Status
```bash
docker-compose ps
```

Tất cả services phải có status **Up** và **healthy**.

### 2. Check Logs
```bash
# API logs
docker-compose logs -f api

# Cloudflare tunnel logs
docker-compose logs -f cloudflared

# All logs
docker-compose logs -f
```

### 3. Test Endpoints

#### Health Check
```bash
curl http://localhost/api/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

#### Test Classification
```bash
curl -X POST http://localhost/api/classify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 14 Pro Max 256GB",
    "description": "Máy mới fullbox bảo hành 12 tháng"
  }'
```

### 4. Access URLs

- **Test Page**: http://localhost hoặc https://autocategory.yourdomain.com
- **Admin Dashboard**: http://localhost/admin hoặc https://autocategory.yourdomain.com/admin
- **API Docs**: http://localhost/api/docs
- **Qdrant Dashboard**: http://localhost/qdrant/dashboard

## Post-Deployment

### 1. Đổi Mật Khẩu Admin

**QUAN TRỌNG**: Đổi mật khẩu admin ngay sau khi deploy!

1. Login vào admin dashboard: http://localhost/admin
2. Username: `admin`, Password: `admin123`
3. Click user menu → **Change Password**

### 2. Tạo API Keys

1. Vào **Admin Dashboard** → **API Keys**
2. Click **Create API Key**
3. Điền thông tin:
   - Name: `Production Key`
   - Rate Limit: `60` requests/minute
   - Expires At: chọn ngày hết hạn
4. Copy API key (chỉ hiển thị 1 lần!)

### 3. Monitor System

Check Grafana dashboards:
```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
# Username: admin, Password: admin123
```

### 4. Setup Automated Backups

Thêm vào crontab:
```bash
# Backup daily at 2 AM
0 2 * * * cd /path/to/autocategory && docker-compose exec -T api python scripts/backup_restore.py backup --retention-days 30
```

## Troubleshooting

### Services không start
```bash
# Check logs
docker-compose logs -f

# Restart specific service
docker-compose restart api

# Rebuild and restart
docker-compose up -d --build api
```

### Cloudflare Tunnel không hoạt động
```bash
# Check tunnel logs
docker-compose logs cloudflared

# Re-setup tunnel
docker-compose --profile setup up cf-setup --force-recreate
docker-compose --profile tunnel restart cloudflared
```

### Admin Dashboard 404
```bash
# Rebuild admin dashboard
cd admin-dashboard
npm run build
cd ..

# Restart nginx
docker-compose restart nginx
```

### Database connection failed
```bash
# Check postgres logs
docker-compose logs postgres

# Check connection
docker-compose exec api python -c "from main import engine; engine.connect()"
```

### Qdrant index empty
```bash
# Rebuild index
curl -X POST http://localhost/api/admin/build-index

# Check index info
curl http://localhost/api/admin/index-info
```

## Maintenance

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
./deploy.sh  # hoặc deploy.ps1 trên Windows
```

### View Real-time Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f cloudflared
```

### Stop All Services
```bash
docker-compose down

# Stop and remove volumes (⚠️ XÓA DỮ LIỆU!)
docker-compose down -v
```

### Backup Database
```bash
# Manual backup
docker-compose exec api python scripts/backup_restore.py backup

# Restore from backup
docker-compose exec api python scripts/backup_restore.py restore --backup-id <backup-id>
```

## Support

Nếu gặp vấn đề:
1. Check logs: `docker-compose logs -f`
2. Check system status: `docker-compose ps`
3. Check documentation: `README.md`, `API_DOCUMENTATION.md`
4. Create issue on GitHub

---

**Happy Deploying! 🚀**
