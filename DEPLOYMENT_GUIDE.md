# Deployment Guide - AutoCategory

## Overview

Complete guide for deploying AutoCategory to production.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Server Requirements](#server-requirements)
3. [Production Environment Setup](#production-environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Database Setup](#database-setup)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup Configuration](#backup-configuration)
9. [Security Hardening](#security-hardening)
10. [Post-Deployment Validation](#post-deployment-validation)
11. [Scaling Considerations](#scaling-considerations)
12. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Code Preparation
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version tag created (`git tag v1.0.0`)

### Configuration
- [ ] Environment variables configured
- [ ] Secrets stored securely (not in code)
- [ ] Database migration plan prepared
- [ ] Backup strategy defined

### Infrastructure
- [ ] Server provisioned
- [ ] Domain name configured
- [ ] SSL certificate obtained
- [ ] Firewall rules configured

### Monitoring
- [ ] Prometheus installed
- [ ] Grafana dashboards ready
- [ ] Alerting configured
- [ ] Log aggregation setup

---

## Server Requirements

### Minimum Specs (Small Scale, <1000 req/hr)

```
CPU: 4 cores
RAM: 8 GB
Disk: 50 GB SSD
Network: 100 Mbps
OS: Ubuntu 22.04 LTS
```

### Recommended Specs (Medium Scale, <10000 req/hr)

```
CPU: 8 cores
RAM: 16 GB
Disk: 100 GB SSD
Network: 1 Gbps
OS: Ubuntu 22.04 LTS
```

### High Scale (>10000 req/hr)

```
CPU: 16+ cores
RAM: 32+ GB
Disk: 200 GB SSD
Network: 1 Gbps
OS: Ubuntu 22.04 LTS
Consider: Load balancer, multiple API servers
```

### Software Requirements

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx (optional, for reverse proxy)
sudo apt update
sudo apt install nginx -y
```

---

## Production Environment Setup

### 1. Clone Repository

```bash
# SSH into server
ssh user@your-server.com

# Clone code
git clone https://github.com/yourorg/autocategory.git
cd autocategory

# Checkout production branch/tag
git checkout v1.0.0
```

### 2. Configure Environment Variables

Create `.env` file:

```bash
# Copy example
cp .env.example .env

# Edit with production values
nano .env
```

**Production `.env`:**

```bash
# Application
ENV=production
DEBUG=false
SECRET_KEY=your-very-long-random-secret-key-here-change-this
API_VERSION=1.0.0

# Database
DATABASE_URL=postgresql://autocategory_user:strong_password@postgres:5432/autocategory
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=strong_redis_password

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=categories

# LLM
LLM_MODEL=gemma:2b
LLM_HOST=http://llm:8080
LLM_TIMEOUT=30

# Security
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
CORS_ORIGINS=https://admin.yourcompany.com

# Rate Limiting
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_IP=100

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090

# Backup
BACKUP_DIR=/backups
BACKUP_SCHEDULE=0 2 * * *  # 2 AM daily
BACKUP_RETENTION_DAYS=30

# Email (for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASSWORD=app_specific_password
ALERT_EMAIL=admin@yourcompany.com
```

### 3. Create Docker Network

```bash
docker network create autocategory_network
```

---

## Docker Deployment

### Production Docker Compose

**`docker-compose.prod.yml`:**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: autocategory_postgres
    environment:
      POSTGRES_DB: autocategory
      POSTGRES_USER: autocategory_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - autocategory_network
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U autocategory_user"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
  
  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: autocategory_redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - autocategory_network
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Qdrant Vector DB
  qdrant:
    image: qdrant/qdrant:latest
    container_name: autocategory_qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - autocategory_network
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # LLM Service (Gemma via llama-server)
  llm:
    image: ghcr.io/ggerganov/llama.cpp:server
    container_name: autocategory_llm
    volumes:
      - ./models:/models:ro
    command: -m /models/gemma-2b-it.gguf --port 8080 --host 0.0.0.0
    networks:
      - autocategory_network
    restart: always
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
  
  # FastAPI Application
  api:
    build:
      context: ./api
      dockerfile: Dockerfile.prod
    container_name: autocategory_api
    env_file: .env
    volumes:
      - ./api/data:/app/data:ro
      - ./backups:/backups
    ports:
      - "8000:8000"
    networks:
      - autocategory_network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      llm:
        condition: service_started
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
  
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: autocategory_nginx
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./admin-dashboard/dist:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    networks:
      - autocategory_network
    depends_on:
      - api
    restart: always

volumes:
  postgres_data:
  redis_data:
  qdrant_data:

networks:
  autocategory_network:
    external: true
```

### Build and Deploy

```bash
# Build API Docker image
docker-compose -f docker-compose.prod.yml build api

# Build frontend
cd admin-dashboard
npm install
npm run build
cd ..

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

---

## SSL/TLS Configuration

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d admin.yourcompany.com -d api.yourcompany.com

# Auto-renewal is configured by certbot
# Test renewal
sudo certbot renew --dry-run
```

### Option 2: Manual Certificate

```bash
# Create SSL directory
mkdir -p ssl

# Copy certificates
cp /path/to/fullchain.pem ssl/
cp /path/to/privkey.pem ssl/

# Set permissions
chmod 600 ssl/privkey.pem
```

### Nginx SSL Configuration

**`nginx/nginx.prod.conf`:**

```nginx
upstream api_backend {
    server api:8000;
}

server {
    listen 80;
    server_name admin.yourcompany.com api.yourcompany.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourcompany.com;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # API Proxy
    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

server {
    listen 443 ssl http2;
    server_name admin.yourcompany.com;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL Security (same as above)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API Proxy
    location /api {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Database Setup

### Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create admin user
docker-compose -f docker-compose.prod.yml exec api python scripts/init_admin.py

# Import initial categories
docker-compose -f docker-compose.prod.yml exec api python scripts/import_categories.py --file /app/data/categories.json
```

### Database Backup

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U autocategory_user autocategory > backup_$(date +%Y%m%d).sql

# Automated backup (add to crontab)
0 2 * * * /path/to/backup_script.sh
```

**`backup_script.sh`:**

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose -f /path/to/docker-compose.prod.yml exec -T postgres pg_dump -U autocategory_user autocategory | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Categories backup
docker-compose -f /path/to/docker-compose.prod.yml exec -T api python scripts/backup_restore.py backup categories

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

---

## Monitoring Setup

### Deploy Monitoring Stack

```bash
# Start Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana
# URL: https://monitoring.yourcompany.com
# Default: admin/admin123 (change immediately!)
```

### Configure Alerts

**Slack Webhook for Alerts:**

Add to `prometheus/alertmanager.yml`:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack-notifications'

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#alerts'
    title: 'AutoCategory Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}'
```

---

## Backup Configuration

### Automated Backups

**Backup Script** (`scripts/automated_backup.sh`):

```bash
#!/bin/bash
set -euo pipefail

COMPOSE_FILE="/opt/autocategory/docker-compose.prod.yml"
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Full system backup
echo "Starting full backup at $DATE"

# Database
docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U autocategory_user autocategory | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Categories
docker-compose -f $COMPOSE_FILE exec -T api python scripts/backup_restore.py backup categories

# Training data
docker-compose -f $COMPOSE_FILE exec -T api python scripts/backup_restore.py backup full

# Cleanup old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.json" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully"

# Send notification
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"✅ AutoCategory backup completed: $DATE\"}"
```

**Schedule with Cron:**

```bash
# Edit crontab
crontab -e

# Add line (daily at 2 AM)
0 2 * * * /opt/autocategory/scripts/automated_backup.sh >> /var/log/autocategory_backup.log 2>&1
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow SSH, HTTP, HTTPS only
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Fail2Ban (Brute Force Protection)

```bash
# Install
sudo apt install fail2ban -y

# Configure
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
```

### 3. Docker Security

```bash
# Run containers as non-root user
# Add to Dockerfile:
USER appuser

# Limit container resources
# In docker-compose.prod.yml:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### 4. Environment Secrets

```bash
# Use Docker secrets instead of .env for sensitive data
# Create secret
echo "my_secret_password" | docker secret create db_password -

# Use in docker-compose.prod.yml
secrets:
  - db_password

services:
  postgres:
    secrets:
      - db_password
```

---

## Post-Deployment Validation

### Health Checks

```bash
# API health
curl https://api.yourcompany.com/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}

# Classification test
curl -X POST https://api.yourcompany.com/api/classify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Product", "description": "Test", "price": 100000}'

# Admin dashboard
curl -I https://admin.yourcompany.com
# Should return 200 OK
```

### Performance Tests

```bash
# Install Apache Bench
sudo apt install apache2-utils -y

# Load test (100 concurrent requests, 1000 total)
ab -n 1000 -c 100 -H "X-API-Key: your-key" -p test_data.json -T "application/json" https://api.yourcompany.com/api/classify
```

### Monitoring Verification

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana
curl http://localhost:3000/api/health
```

---

## Scaling Considerations

### Horizontal Scaling (Multiple API Servers)

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
      
  # Add load balancer
  load_balancer:
    image: haproxy:latest
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    ports:
      - "8000:8000"
```

### Database Scaling

```bash
# Read replicas for PostgreSQL
# Use PgBouncer for connection pooling
# Consider managed database (AWS RDS, Google Cloud SQL)
```

### Caching Strategy

```yaml
# Add Varnish cache layer
varnish:
  image: varnish:latest
  volumes:
    - ./default.vcl:/etc/varnish/default.vcl:ro
  ports:
    - "80:80"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Check container status
docker ps -a

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Database Connection Issues

```bash
# Test connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U autocategory_user -d autocategory

# Check environment variables
docker-compose -f docker-compose.prod.yml exec api env | grep DATABASE
```

### High Response Times

```bash
# Check resource usage
docker stats

# Check database queries
docker-compose -f docker-compose.prod.yml exec postgres psql -U autocategory_user -d autocategory -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Clear cache
curl -X DELETE https://api.yourcompany.com/api/admin/system/cache?cache_type=all \
  -H "Authorization: Bearer your-jwt-token"
```

### SSL Certificate Issues

```bash
# Check certificate expiry
echo | openssl s_client -servername admin.yourcompany.com -connect admin.yourcompany.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew Let's Encrypt certificate
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## Emergency Procedures

### Rollback Deployment

```bash
# Stop current version
docker-compose -f docker-compose.prod.yml down

# Checkout previous version
git checkout v0.9.0

# Restore database backup
gunzip < /backups/db_YYYYMMDD.sql.gz | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U autocategory_user autocategory

# Start previous version
docker-compose -f docker-compose.prod.yml up -d
```

### Service Outage Response

1. **Check status page:** https://status.yourcompany.com
2. **View logs:** `docker-compose logs -f`
3. **Restart services:** `docker-compose restart`
4. **Notify users:** Post incident on status page
5. **Investigate root cause:** Review logs and metrics
6. **Implement fix:** Deploy hotfix if needed

---

## Support

- **Production Issues:** production@yourcompany.com
- **On-Call Phone:** +84 xxx xxx xxxx
- **Runbook:** https://docs.yourcompany.com/runbook
- **Incident Management:** https://oncall.yourcompany.com
