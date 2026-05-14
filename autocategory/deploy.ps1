# AutoCategory Deployment Script for Windows
# Deploy all services with Cloudflare Tunnel

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🚀 AutoCategory Production Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ Error: .env file not found" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it"
    exit 1
}

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*?)\s*$') {
        $name = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Check required variables
$cfToken = [Environment]::GetEnvironmentVariable("CF_API_TOKEN", "Process")
$cfAccount = [Environment]::GetEnvironmentVariable("CF_ACCOUNT_ID", "Process")
$cfDomain = [Environment]::GetEnvironmentVariable("CF_DOMAIN", "Process")
$cfSubdomain = [Environment]::GetEnvironmentVariable("CF_SUBDOMAIN", "Process")

if (-not $cfToken -or -not $cfAccount -or -not $cfDomain) {
    Write-Host "❌ Error: Missing required Cloudflare configuration" -ForegroundColor Red
    Write-Host "Please configure CF_API_TOKEN, CF_ACCOUNT_ID, and CF_DOMAIN in .env"
    exit 1
}

Write-Host "📦 Step 1/7: Building Admin Dashboard..." -ForegroundColor Yellow
Set-Location admin-dashboard
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..."
    npm install
}
Write-Host "Building production bundle..."
npm run build
Set-Location ..
Write-Host "✅ Admin dashboard built successfully" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 2/7: Stopping existing containers..." -ForegroundColor Yellow
docker-compose down
Write-Host "✅ Containers stopped" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 3/7: Building Docker images..." -ForegroundColor Yellow
docker-compose build --no-cache
Write-Host "✅ Images built" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 4/7: Starting core services..." -ForegroundColor Yellow
docker-compose up -d llama-server qdrant postgres redis
Write-Host "Waiting for services to be healthy..."
Start-Sleep -Seconds 30
Write-Host "✅ Core services started" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 5/7: Starting API and Nginx..." -ForegroundColor Yellow
docker-compose up -d api nginx
Write-Host "Waiting for API to be healthy..."
Start-Sleep -Seconds 20
Write-Host "✅ API and Nginx started" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 6/7: Setting up Cloudflare Tunnel..." -ForegroundColor Yellow
# Run cf-setup once
docker-compose --profile setup up cf-setup
Write-Host "Starting Cloudflare Tunnel daemon..."
docker-compose --profile tunnel up -d cloudflared
Write-Host "✅ Cloudflare Tunnel configured" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Step 7/7: Initializing database..." -ForegroundColor Yellow
# Check if database is already initialized (skip for now, always run)
Write-Host "Running database migrations..."
docker-compose exec -T api alembic upgrade head

Write-Host "Creating admin user..."
docker-compose exec -T api python scripts/init_admin.py

Write-Host "Importing categories..."
docker-compose exec -T api python scripts/import_categories.py --file /app/data/categories.json

Write-Host "✅ Database initialized" -ForegroundColor Green
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🌐 Application URLs:"
Write-Host "   Local: http://localhost"
Write-Host "   Public: https://$cfSubdomain.$cfDomain"
Write-Host ""
Write-Host "📊 Admin Dashboard:"
Write-Host "   Local: http://localhost/admin"
Write-Host "   Public: https://$cfSubdomain.$cfDomain/admin"
Write-Host "   Default credentials: admin / admin123"
Write-Host "   ⚠️  CHANGE PASSWORD IMMEDIATELY!" -ForegroundColor Yellow
Write-Host ""
Write-Host "📚 API Documentation:"
Write-Host "   http://localhost/api/docs"
Write-Host ""
Write-Host "🔍 Service Status:"
docker-compose ps
Write-Host ""
Write-Host "📝 View logs:"
Write-Host "   docker-compose logs -f api"
Write-Host "   docker-compose logs -f cloudflared"
Write-Host ""
Write-Host "🛑 Stop all services:"
Write-Host "   docker-compose down"
Write-Host ""
