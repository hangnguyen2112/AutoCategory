# Kế Hoạch Phát Triển: Admin Dashboard & Management System

**Mục tiêu:** Xây dựng hệ thống quản lý hoàn chỉnh với admin dashboard, authentication, monitoring, data management, và training pipeline.

---

## 🏗️ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                            │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ User Portal  │ Test Page    │ Admin        │ API Docs       │
│ (Public)     │ (Public)     │ Dashboard    │ (Swagger)      │
│              │              │ (Protected)  │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Auth         │ Rate Limit   │ API Key      │ CORS           │
│ Middleware   │ Middleware   │ Validation   │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend Services                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Classification│ Generation  │ Admin        │ Training       │
│ Service      │ Service      │ Service      │ Service        │
└──────────────┴──────────────┴──────────────┴────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data & Storage Layer                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ PostgreSQL   │ Qdrant       │ Redis        │ File Storage   │
│ (Users, API  │ (Vectors)    │ (Cache,      │ (Models,       │
│  Keys, Logs) │              │  Sessions)   │  Datasets)     │
└──────────────┴──────────────┴──────────────┴────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Ollama/LLM   │ Monitoring   │ Logging      │ Backup         │
│ Server       │ (Prometheus) │ (ELK)        │ (S3/Local)     │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 📋 Tổng Quan Các Module

### Module 1: Authentication & Authorization
- User management (admin, developer, viewer)
- JWT-based authentication
- Role-based access control (RBAC)
- API key generation & management
- Rate limiting per user/API key

### Module 2: Admin Dashboard UI
- System health monitoring
- Service control (start/stop/restart)
- Configuration management
- User & API key management
- Analytics & statistics
- Log viewer

### Module 3: Data Management
- Category import/export
- Category sync từ hệ thống chính
- Data validation
- Version control cho categories
- Backup & restore

### Module 4: Training & Fine-tuning
- Collect training data từ feedback
- Data annotation interface
- Training pipeline
- Model versioning
- A/B testing framework

### Module 5: Monitoring & Logging
- Real-time metrics (Prometheus)
- Request logging
- Error tracking
- Performance monitoring
- Alerting

### Module 6: Documentation
- API documentation (Swagger/OpenAPI)
- Integration guides
- Data standards documentation
- Admin user manual
- Developer guides

---

## 🗂️ Cấu Trúc Thư Mục Mới

```
autocategory/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
│
├── api/
│   ├── main.py                          # FastAPI app entry
│   ├── config.py                        # Cấu hình từ env/DB
│   ├── dependencies.py                  # Auth dependencies
│   ├── requirements.txt
│   │
│   ├── auth/                            # NEW: Authentication
│   │   ├── __init__.py
│   │   ├── jwt.py                       # JWT token handling
│   │   ├── password.py                  # Password hashing
│   │   └── permissions.py               # RBAC logic
│   │
│   ├── models/                          # NEW: Database models
│   │   ├── __init__.py
│   │   ├── user.py                      # User model
│   │   ├── api_key.py                   # API key model
│   │   ├── request_log.py               # Request logs
│   │   ├── training_data.py             # Training data
│   │   └── config.py                    # System config
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── classify.py                  # Classification endpoint
│   │   ├── generate.py                  # Generation endpoint
│   │   ├── category.py                  # Category management
│   │   │
│   │   ├── auth.py                      # NEW: Login/register
│   │   ├── users.py                     # NEW: User management
│   │   ├── api_keys.py                  # NEW: API key CRUD
│   │   ├── admin.py                     # NEW: Admin operations
│   │   ├── system.py                    # NEW: System control
│   │   ├── monitoring.py                # NEW: Metrics endpoint
│   │   ├── data.py                      # NEW: Data import/export
│   │   └── training.py                  # NEW: Training pipeline
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   ├── image_analyzer.py
│   │   ├── llm_service.py
│   │   ├── embedder.py
│   │   ├── qdrant_service.py
│   │   ├── category_builder.py
│   │   │
│   │   ├── auth_service.py              # NEW: Auth logic
│   │   ├── api_key_service.py           # NEW: API key management
│   │   ├── config_service.py            # NEW: Dynamic config
│   │   ├── monitoring_service.py        # NEW: Metrics collection
│   │   ├── data_service.py              # NEW: Data import/export
│   │   └── training_service.py          # NEW: Training pipeline
│   │
│   ├── middleware/                      # NEW: Middleware
│   │   ├── __init__.py
│   │   ├── auth.py                      # Auth middleware
│   │   ├── rate_limit.py                # Rate limiting
│   │   ├── logging.py                   # Request logging
│   │   └── error_handler.py             # Error handling
│   │
│   ├── schemas/                         # NEW: Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── category.py
│   │   ├── training.py
│   │   └── monitoring.py
│   │
│   ├── data/
│   │   ├── categories.json
│   │   ├── categories_backup/
│   │   ├── training_data/               # NEW: Training datasets
│   │   ├── models/                      # NEW: Trained models
│   │   └── logs/                        # NEW: Application logs
│   │
│   └── scripts/                         # NEW: Utility scripts
│       ├── init_db.py                   # Initialize database
│       ├── create_admin.py              # Create first admin user
│       ├── import_categories.py         # Import categories
│       ├── train_model.py               # Train model
│       └── backup.py                    # Backup script
│
├── admin-dashboard/                     # NEW: Admin UI
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx            # Overview
│   │   │   ├── SystemControl.jsx        # Start/stop services
│   │   │   ├── Configuration.jsx        # Edit configs
│   │   │   ├── Users.jsx                # User management
│   │   │   ├── ApiKeys.jsx              # API key management
│   │   │   ├── Categories.jsx           # Category management
│   │   │   ├── Training.jsx             # Training pipeline
│   │   │   ├── Monitoring.jsx           # Metrics & logs
│   │   │   └── DataImport.jsx           # Import/export data
│   │   │
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MetricCard.jsx
│   │   │   ├── LogViewer.jsx
│   │   │   └── ...
│   │   │
│   │   ├── services/
│   │   │   └── api.js                   # API client
│   │   │
│   │   └── utils/
│   │       ├── auth.js
│   │       └── ...
│   │
│   └── Dockerfile
│
├── frontend/                            # Public test page (existing)
│   ├── index.html
│   ├── test-classify.html
│   └── test-generate.html
│
├── database/                            # NEW: Database
│   ├── init.sql                         # Initial schema
│   └── migrations/
│
├── monitoring/                          # NEW: Monitoring stack
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── alertmanager/
│       └── config.yml
│
├── docs/                                # NEW: Documentation
│   ├── API_DOCUMENTATION.md
│   ├── DATA_STANDARDS.md
│   ├── INTEGRATION_GUIDE.md
│   ├── ADMIN_MANUAL.md
│   ├── DEVELOPER_GUIDE.md
│   └── DEPLOYMENT_GUIDE.md
│
└── nginx/
    └── nginx.conf
```

---

## 🔐 Module 1: Authentication & Authorization

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- admin, developer, viewer
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Keys table
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,  -- First 8 chars for display
    name VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 1000,
    
    -- Permissions
    can_classify BOOLEAN DEFAULT TRUE,
    can_generate BOOLEAN DEFAULT TRUE,
    can_admin BOOLEAN DEFAULT FALSE,
    
    -- Usage tracking
    total_requests INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Metadata
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Request logs table
CREATE TABLE request_logs (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    user_id INTEGER REFERENCES users(id),
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_body TEXT,
    response_status INTEGER,
    response_time_ms FLOAT,
    
    -- Classification details
    input_title TEXT,
    input_description TEXT,
    predicted_category_id INTEGER,
    confidence FLOAT,
    decision VARCHAR(50),
    
    -- Metadata
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Training data table
CREATE TABLE training_data (
    id SERIAL PRIMARY KEY,
    
    -- Input
    title TEXT NOT NULL,
    description TEXT,
    price FLOAT,
    image_urls TEXT[],
    
    -- Prediction
    predicted_category_id INTEGER,
    predicted_confidence FLOAT,
    
    -- Ground truth
    actual_category_id INTEGER NOT NULL,
    
    -- Source
    source VARCHAR(50) DEFAULT 'feedback',  -- feedback, manual, import
    is_validated BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System config table
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(50) DEFAULT 'string',  -- string, int, float, bool, json
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,  -- Hide value in UI
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Category sync history
CREATE TABLE category_sync_history (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255),
    sync_type VARCHAR(50),  -- manual, webhook, scheduled
    changes_detected BOOLEAN,
    categories_added INTEGER DEFAULT 0,
    categories_modified INTEGER DEFAULT 0,
    categories_deleted INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    synced_by INTEGER REFERENCES users(id),
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints - Authentication

```python
# /api/auth/login
POST /api/auth/login
{
  "username": "admin",
  "password": "secret"
}
→ Returns: { "access_token": "...", "token_type": "bearer", "user": {...} }

# /api/auth/register (only for admins to create users)
POST /api/auth/register
{
  "username": "developer1",
  "email": "dev@example.com",
  "password": "...",
  "role": "developer"
}
→ Requires: Admin token

# /api/auth/me
GET /api/auth/me
→ Returns current user info

# /api/auth/change-password
POST /api/auth/change-password
{
  "old_password": "...",
  "new_password": "..."
}
```

### API Endpoints - API Key Management

```python
# List API keys
GET /api/api-keys
→ Returns list of user's API keys (masked)

# Create API key
POST /api/api-keys
{
  "name": "Production Key",
  "rate_limit_per_minute": 60,
  "rate_limit_per_day": 10000,
  "expires_at": "2027-01-01T00:00:00Z"
}
→ Returns: { "api_key": "sk_live_abc123...", "key_id": 1 }
# ⚠️ API key chỉ hiển thị 1 lần!

# Revoke API key
DELETE /api/api-keys/{key_id}

# Update API key settings
PATCH /api/api-keys/{key_id}
{
  "rate_limit_per_minute": 120
}
```

---

## 🎛️ Module 2: Admin Dashboard

### Dashboard Pages

#### 1. Overview Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│  AutoCategory Admin Dashboard                     [User] [⚙️] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 System Health                                             │
│  ┌──────────┬──────────┬──────────┬──────────┐              │
│  │ API      │ LLM      │ Qdrant   │ Database │              │
│  │ ✅ Online│ ✅ Online│ ✅ Online│ ✅ Online│              │
│  └──────────┴──────────┴──────────┴──────────┘              │
│                                                               │
│  📈 Today's Statistics                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐              │
│  │ Requests │ Success  │ Avg Time │ Errors   │              │
│  │ 1,234    │ 98.5%    │ 1.2s     │ 18       │              │
│  └──────────┴──────────┴──────────┴──────────┘              │
│                                                               │
│  📊 Category Distribution (Top 10)                            │
│  [Bar chart showing most classified categories]              │
│                                                               │
│  🔑 API Key Usage                                             │
│  [Table showing top API keys by usage]                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2. System Control
```
┌─────────────────────────────────────────────────────────────┐
│  System Control                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔧 Services                                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ⚙️ API Service        ✅ Running   [Restart] [Stop]    │  │
│  │ 🤖 LLM Server         ✅ Running   [Restart] [Stop]    │  │
│  │ 🔍 Qdrant             ✅ Running   [Restart] [Stop]    │  │
│  │ 💾 PostgreSQL         ✅ Running   [Restart] [Stop]    │  │
│  │ 🔴 Redis              ❌ Stopped   [Start]             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  🔄 Bulk Operations                                           │
│  [Restart All] [Stop All] [Rebuild Index]                    │
│                                                               │
│  📝 Recent Logs                                               │
│  [2026-05-06 10:30:45] INFO: API started                     │
│  [2026-05-06 10:30:46] INFO: Connected to Qdrant             │
│  [View Full Logs →]                                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Configuration Management
```
┌─────────────────────────────────────────────────────────────┐
│  Configuration                                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🤖 LLM Settings                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Model Name:     [gemma4-e4b                    ] [Test] │  │
│  │ Temperature:    [0.1                           ]        │  │
│  │ Max Tokens:     [512                           ]        │  │
│  │ Base URL:       [http://llama-server:8080      ]        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  🔑 API Keys (External Services)                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ProtonX API:    [••••••••••••••••••••          ] [Edit] │  │
│  │ OpenAI API:     [Not Set                       ] [Add]  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  📊 Qdrant Settings                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Host:           [qdrant                        ]        │  │
│  │ Port:           [6333                          ]        │  │
│  │ Collection:     [categories                    ]        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ⚙️ System Settings                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Enable Image Gen: [✓] Enable  [ ] Disable             │  │
│  │ Log Level:        [ ] DEBUG [✓] INFO [ ] WARNING      │  │
│  │ Default Rate Limit: [60                        ]/min   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  [Save Changes] [Revert] [Export Config]                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 4. User & API Key Management
```
┌─────────────────────────────────────────────────────────────┐
│  Users                                        [+ Create User] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [Search: ____________] [Filter: All Roles ▼]                │
│                                                               │
│  Username    Email            Role       Status   Actions     │
│  ────────────────────────────────────────────────────────────│
│  admin       admin@ex.com     Admin      Active   [Edit] [⚙️] │
│  dev1        dev1@ex.com      Developer  Active   [Edit] [🔑]│
│  viewer1     view@ex.com      Viewer     Inactive [Edit]     │
│                                                               │
│  API Keys (for dev1)                                          │
│  ────────────────────────────────────────────────────────────│
│  Name          Prefix    Usage      Rate Limit   Status       │
│  Prod Key      sk_live_  1.2K/day   100/min      Active       │
│  Test Key      sk_test_  50/day     10/min       Active       │
│                                                               │
│  [+ Create API Key]                                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 5. Category Management
```
┌─────────────────────────────────────────────────────────────┐
│  Categories                      [Import] [Export] [Rebuild] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📂 Category Tree                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [+] Điện tử (450 subcategories)                        │  │
│  │   [+] Điện thoại (120)                                 │  │
│  │     ├─ iPhone (45) ✅ Active                           │  │
│  │     ├─ Samsung (35) ✅ Active                          │  │
│  │     └─ Xiaomi (20) ✅ Active                           │  │
│  │   [+] Laptop (80)                                      │  │
│  │ [+] Xe cộ (230)                                        │  │
│  │ [+] Thời trang (180)                                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  🔄 Sync Status                                               │
│  Last synced: 2026-05-06 08:00:00                            │
│  Source: webhook from main system                            │
│  Changes: +5 added, 3 modified, 0 deleted                    │
│  [Sync Now] [View History]                                   │
│                                                               │
│  📊 Index Status                                              │
│  Total categories: 1,234                                     │
│  Indexed (leaf): 567                                         │
│  Last rebuilt: 2026-05-06 08:05:00                           │
│  [Rebuild Index Now]                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 6. Training Pipeline
```
┌─────────────────────────────────────────────────────────────┐
│  Training & Fine-tuning                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Training Data                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Total samples: 1,234                                    │  │
│  │ Validated: 890 (72%)                                    │  │
│  │ Corrections: 567                                        │  │
│  │ Ready for training: ✅ Yes                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  🔄 Training Jobs                                             │
│  [+ Start New Training]                                       │
│                                                               │
│  Job ID   Model       Status      Progress  Started          │
│  ──────────────────────────────────────────────────────────  │
│  #123     gemma-ft    ✅ Complete  100%     2026-05-01 10:00│  │
│  #124     gemma-ft-v2 🔄 Running   45%      2026-05-06 08:00│  │
│                                                               │
│  📈 Model Performance                                         │
│  Current model: gemma-ft (v1.2)                              │
│  Accuracy: 87.5%                                             │
│  Top-3 Accuracy: 95.2%                                       │
│  Avg confidence: 0.83                                        │
│                                                               │
│  [Compare Models] [Deploy Model] [Rollback]                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 7. Monitoring & Logs
```
┌─────────────────────────────────────────────────────────────┐
│  Monitoring                                  [Real-time: ON] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Real-time Metrics                                         │
│  [Line chart: Requests/second over time]                     │
│  [Line chart: Response time over time]                       │
│  [Bar chart: Status codes distribution]                      │
│                                                               │
│  📝 Request Logs                        [Filter: All ▼]      │
│  [Search: ____________] [Date: Today ▼]                      │
│                                                               │
│  Time     Endpoint        Status  Time    Category           │
│  ──────────────────────────────────────────────────────────  │
│  10:30:45 /api/classify   200     1.2s    Điện thoại/iPhone │
│  10:30:46 /api/classify   200     0.8s    Laptop            │
│  10:30:47 /api/generate   500     3.2s    Error             │
│  10:30:48 /api/classify   200     1.1s    Xe máy            │
│                                                               │
│  🔍 Error Logs                                                │
│  [2026-05-06 10:30:47] ERROR: LLM timeout                    │
│  [2026-05-06 10:25:32] ERROR: Qdrant connection failed       │
│                                                               │
│  [Export Logs] [Clear Old Logs]                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Module 3: Data Management

### Data Standards Documentation

#### Category Data Format
```json
{
  "id": 123,
  "name": "iPhone",
  "parent_id": 120,
  "parent_name": "Điện thoại",
  "description": "Các sản phẩm iPhone của Apple",
  "is_active": 1,
  "level": 3,
  "path": "Điện tử > Điện thoại > iPhone",
  "metadata": {
    "icon": "📱",
    "keywords": ["iphone", "apple", "ios"],
    "common_mistakes": ["ip", "ipon"]
  }
}
```

#### Training Data Format
```json
{
  "title": "iPhone 15 Pro Max 256GB zin đẹp 99%",
  "description": "Máy đẹp sxdh fullbox bh 8 tháng",
  "price": 28000000,
  "image_urls": ["https://..."],
  "category_id": 123,
  "category_path": "Điện tử > Điện thoại > iPhone",
  "source": "feedback",
  "validated": true,
  "metadata": {
    "predicted_category": 124,
    "predicted_confidence": 0.75,
    "was_corrected": true
  }
}
```

### Import/Export APIs

```python
# Import categories
POST /api/admin/data/import/categories
Content-Type: multipart/form-data
file: categories.json

→ Returns validation report + import stats

# Export categories
GET /api/admin/data/export/categories?format=json
→ Downloads categories.json

# Import training data
POST /api/admin/data/import/training
Content-Type: multipart/form-data
file: training_data.jsonl

# Export training data
GET /api/admin/data/export/training?validated_only=true
→ Downloads training_data.jsonl

# Validate data before import
POST /api/admin/data/validate
{
  "data_type": "categories",
  "data": [...]
}
→ Returns validation errors
```

### Data Validation Rules

```python
# Category validation
- id: required, integer, unique
- name: required, string, 1-255 chars
- parent_id: nullable, integer, exists in categories
- is_active: 0 or 1
- description: optional, string

# Training data validation
- title: required, non-empty string
- category_id: required, exists in categories
- category_id must be a leaf category
- If has image_urls, must be valid URLs
```

---

## 🎓 Module 4: Training & Fine-tuning

### Training Pipeline

```
1. Data Collection
   ├─ Feedback từ users (corrections)
   ├─ Manual annotation
   └─ Import từ external sources
   
2. Data Validation & Cleaning
   ├─ Remove duplicates
   ├─ Validate category IDs
   ├─ Filter low-quality samples
   └─ Balance classes
   
3. Data Augmentation (optional)
   ├─ Paraphrase titles/descriptions
   ├─ Add synonyms
   └─ Generate synthetic samples
   
4. Training
   ├─ Split train/val/test
   ├─ Train model (fine-tune LLM or embeddings)
   ├─ Track metrics
   └─ Save checkpoints
   
5. Evaluation
   ├─ Accuracy on test set
   ├─ Confusion matrix
   ├─ A/B test with current model
   └─ User acceptance testing
   
6. Deployment
   ├─ Deploy new model
   ├─ Monitor performance
   ├─ Rollback if needed
   └─ Archive old model
```

### Training API

```python
# Start training job
POST /api/admin/training/start
{
  "model_type": "embeddings",  # or "llm_finetune"
  "dataset_id": "latest",
  "config": {
    "epochs": 10,
    "batch_size": 32,
    "learning_rate": 0.0001
  }
}
→ Returns job_id

# Get training status
GET /api/admin/training/jobs/{job_id}
→ Returns status, progress, metrics

# List training jobs
GET /api/admin/training/jobs

# Deploy trained model
POST /api/admin/training/deploy/{job_id}

# Rollback to previous model
POST /api/admin/training/rollback
```

---

## 📡 Module 5: Monitoring & Logging

### Metrics Collected

```python
# Request metrics
- Total requests
- Requests per endpoint
- Success rate
- Error rate
- Response time (avg, p50, p95, p99)

# Classification metrics
- Categories distribution
- Confidence distribution
- Decision types distribution
- Correction rate

# System metrics
- CPU usage
- Memory usage
- Disk usage
- Network I/O
- LLM inference time
- Qdrant search time

# Business metrics
- Active users
- API key usage
- Daily/monthly requests
- Cost per request (if using cloud)
```

### Monitoring Stack

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  
  node-exporter:
    image: prom/node-exporter
    
  cadvisor:
    image: gcr.io/cadvisor/cadvisor
```

---

## 📚 Module 6: Documentation

### Documentation Files to Create

1. **API_DOCUMENTATION.md**
   - Complete API reference
   - Request/response examples
   - Error codes
   - Rate limits

2. **DATA_STANDARDS.md**
   - Category data format
   - Training data format
   - Validation rules
   - Import/export formats

3. **INTEGRATION_GUIDE.md**
   - How to integrate with frontend
   - Authentication flow
   - API key usage
   - Code examples (JS, Python, cURL)

4. **ADMIN_MANUAL.md**
   - How to use admin dashboard
   - User management
   - System configuration
   - Troubleshooting

5. **DEVELOPER_GUIDE.md**
   - Architecture overview
   - How to add new features
   - How to customize
   - Testing guidelines

6. **DEPLOYMENT_GUIDE.md**
   - Production deployment
   - Docker setup
   - Environment variables
   - Backup & restore
   - Monitoring setup

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Setup PostgreSQL database
- [ ] Create database schema
- [ ] Implement authentication (JWT)
- [ ] Create auth endpoints
- [ ] Implement API key management
- [ ] Add auth middleware to existing endpoints
- [ ] Create admin user script

### Phase 2: Admin Dashboard Backend (Week 3-4)
- [ ] System control endpoints
- [ ] Configuration management endpoints
- [ ] User management endpoints
- [ ] Monitoring endpoints
- [ ] Data import/export endpoints
- [ ] Training pipeline endpoints

### Phase 3: Admin Dashboard Frontend (Week 5-6)
- [ ] Setup React/Vue admin dashboard
- [ ] Login page
- [ ] Dashboard overview
- [ ] System control page
- [ ] Configuration page
- [ ] User & API key management page
- [ ] Category management page
- [ ] Monitoring & logs page

### Phase 4: Data Management (Week 7)
- [ ] Data validation logic
- [ ] Import/export functionality
- [ ] Category sync from main system
- [ ] Version control for categories
- [ ] Backup & restore scripts

### Phase 5: Training Pipeline (Week 8-9)
- [ ] Feedback collection system
- [ ] Data annotation interface
- [ ] Training scripts
- [ ] Model versioning
- [ ] A/B testing framework
- [ ] Deployment automation

### Phase 6: Monitoring & Logging (Week 10)
- [ ] Setup Prometheus
- [ ] Setup Grafana dashboards
- [ ] Request logging
- [ ] Error tracking
- [ ] Alerting rules

### Phase 7: Documentation (Week 11)
- [ ] API documentation
- [ ] Data standards
- [ ] Integration guide
- [ ] Admin manual
- [ ] Developer guide
- [ ] Deployment guide

### Phase 8: Testing & Polish (Week 12)
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Security audit
- [ ] UI/UX improvements
- [ ] Bug fixes
- [ ] Production deployment

---

## 🔑 Key Technical Decisions

### 1. Authentication: JWT
- Stateless, scalable
- Refresh tokens for security
- Easy to integrate with frontend

### 2. Database: PostgreSQL
- Relational data (users, API keys, logs)
- ACID compliance
- Good for analytics queries

### 3. Admin UI: React + Tailwind CSS
- Modern, responsive
- Rich ecosystem
- Easy to customize

### 4. Monitoring: Prometheus + Grafana
- Industry standard
- Rich visualization
- Alerting support

### 5. API Documentation: FastAPI OpenAPI
- Auto-generated
- Interactive (Swagger UI)
- Always up-to-date

---

## 💰 Estimated Costs

### Development
- Backend development: 8-10 weeks
- Frontend development: 4-5 weeks
- Testing & polish: 2 weeks
- **Total: ~12-15 weeks**

### Infrastructure (Monthly)
- VPS (4 CPU, 16GB RAM): $50-100
- PostgreSQL: Included
- Storage (100GB): $10
- Monitoring: Free (self-hosted)
- **Total: ~$60-110/month**

---

## 📋 Next Steps

1. Review this plan
2. Prioritize features
3. Decide on tech stack for admin UI
4. Set up development environment
5. Start with Phase 1 (Authentication)

**Muốn tôi bắt đầu implement Phase 1 không?**
