# Developer Guide - AutoCategory

## Overview

This guide helps developers understand, modify, and extend the AutoCategory system.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Development Setup](#development-setup)
4. [Adding New Features](#adding-new-features)
5. [Database Schema](#database-schema)
6. [API Development](#api-development)
7. [Frontend Development](#frontend-development)
8. [Testing](#testing)
9. [Code Style](#code-style)
10. [Contributing](#contributing)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                    │
│  Admin Dashboard + User Interface                       │
└────────────┬────────────────────────────────────────────┘
             │ HTTP/REST
             ▼
┌────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│  - Authentication (JWT)                                 │
│  - Rate Limiting (Redis)                                │
│  - Request Logging                                      │
│  - Business Logic                                       │
└───┬──────┬──────┬──────┬──────┬──────┬─────────────────┘
    │      │      │      │      │      │
    │      │      │      │      │      └─────┐
    ▼      ▼      ▼      ▼      ▼            ▼
┌────────┐ ┌─────┐ ┌──────┐ ┌───────┐ ┌──────────┐
│ PostgreSQL Redis  Qdrant  LLM      Prometheus │
│ (Data)  (Cache) (Vectors)(Gemma)  (Metrics)   │
└────────┘ └─────┘ └──────┘ └───────┘ └──────────┘
```

### Data Flow

**Classification Request:**
1. Client → API (with API key header)
2. API validates API key (check Redis cache)
3. API extracts text from request
4. Embedder service generates embedding via Qdrant
5. Vector search finds top N similar categories
6. LLM service ranks and explains results
7. Response returned to client
8. Request logged to PostgreSQL

**Training Pipeline:**
1. Feedback → Training Data table
2. Admin validates samples via dashboard
3. Training script prepares dataset
4. Model fine-tuning (offline)
5. New model version saved
6. A/B test deployment
7. Monitor metrics, promote winner

---

## Project Structure

```
autocategory/
├── api/                          # Backend API
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Configuration management
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py
│   │   ├── admin.py              # Admin endpoints
│   │   ├── auth.py               # Authentication
│   │   ├── category.py           # Category management
│   │   └── classify.py           # Classification endpoints
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── classifier.py         # Main classification service
│   │   ├── embedder.py           # Embedding generation
│   │   ├── llm_service.py        # LLM interaction
│   │   ├── qdrant_service.py     # Vector DB operations
│   │   ├── category_builder.py   # Category tree builder
│   │   └── metrics_service.py    # Prometheus metrics
│   ├── models/                   # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── training_data.py
│   │   └── ...
│   ├── schemas/                  # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── classification.py
│   │   └── ...
│   ├── middleware/               # Custom middleware
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── logging.py
│   ├── scripts/                  # Utility scripts
│   │   ├── backup_restore.py     # Backup system
│   │   ├── category_versioning.py # Version control
│   │   └── training_pipeline.py  # Training automation
│   ├── data/                     # Data files
│   │   ├── categories.json       # Category tree
│   │   └── categories_versions/  # Version snapshots
│   └── requirements.txt          # Python dependencies
├── admin-dashboard/              # Frontend (React)
│   ├── src/
│   │   ├── main.jsx              # Entry point
│   │   ├── App.jsx               # Root component
│   │   ├── pages/                # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Users.jsx
│   │   │   ├── ApiKeys.jsx
│   │   │   ├── Categories.jsx
│   │   │   ├── TrainingData.jsx
│   │   │   ├── RequestLogs.jsx
│   │   │   ├── SystemControl.jsx
│   │   │   └── Configuration.jsx
│   │   ├── components/           # Reusable components
│   │   │   ├── Layout.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── services/             # API client
│   │   │   └── api.js
│   │   ├── store/                # State management
│   │   │   └── authStore.js
│   │   └── index.css             # Global styles
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite configuration
│   └── tailwind.config.js        # Tailwind CSS config
├── prometheus/                   # Monitoring config
│   ├── prometheus.yml
│   └── alert_rules.yml
├── grafana/                      # Dashboards
│   └── dashboards/
│       └── overview.json
├── nginx/                        # Reverse proxy
│   └── nginx.conf
├── docker-compose.yml            # Development setup
├── docker-compose.prod.yml       # Production setup
├── docker-compose.monitoring.yml # Monitoring stack
├── API_DOCUMENTATION.md          # API reference
├── DATA_STANDARDS.md             # Data formats
├── INTEGRATION_GUIDE.md          # Integration howto
├── ADMIN_MANUAL.md               # Admin guide
├── DEVELOPER_GUIDE.md            # This file
└── DEPLOYMENT_GUIDE.md           # Deployment instructions
```

---

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16
- Redis 7
- Git

### Clone Repository

```bash
git clone https://github.com/yourorg/autocategory.git
cd autocategory
```

### Backend Setup

```bash
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Initialize admin user
python scripts/init_admin.py

# Start development server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd admin-dashboard

# Install dependencies
npm install

# Start development server
npm run dev
# Opens at http://localhost:3001
```

### Docker Setup (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new_table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## Adding New Features

### Adding a New API Endpoint

**1. Define Pydantic Schema** (`api/schemas/example.py`):

```python
from pydantic import BaseModel, Field

class ExampleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    value: int = Field(gt=0)

class ExampleResponse(BaseModel):
    id: int
    result: str
```

**2. Create Router** (`api/routers/example.py`):

```python
from fastapi import APIRouter, Depends, HTTPException
from schemas.example import ExampleRequest, ExampleResponse
from services.example_service import ExampleService

router = APIRouter(prefix="/api/example", tags=["Example"])

@router.post("/", response_model=ExampleResponse)
async def create_example(
    request: ExampleRequest,
    service: ExampleService = Depends()
):
    try:
        result = await service.process(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**3. Create Service** (`api/services/example_service.py`):

```python
from schemas.example import ExampleRequest, ExampleResponse

class ExampleService:
    async def process(self, request: ExampleRequest) -> ExampleResponse:
        # Business logic here
        result = f"Processed: {request.title}"
        
        return ExampleResponse(
            id=1,
            result=result
        )
```

**4. Register Router** (`api/main.py`):

```python
from routers import example

app.include_router(example.router)
```

### Adding a Database Table

**1. Create Model** (`api/models/example.py`):

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**2. Create Migration**:

```bash
alembic revision --autogenerate -m "Add examples table"
alembic upgrade head
```

### Adding a Frontend Page

**1. Create Page Component** (`admin-dashboard/src/pages/Example.jsx`):

```javascript
import { useState, useEffect } from 'react'
import { exampleAPI } from '../services/api'
import toast from 'react-hot-toast'

export default function Example() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchItems()
  }, [])
  
  const fetchItems = async () => {
    try {
      const data = await exampleAPI.list()
      setItems(data.items)
    } catch (error) {
      toast.error('Failed to load items')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Example Page</h1>
      
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="card">
          {/* Your content here */}
        </div>
      )}
    </div>
  )
}
```

**2. Add API Methods** (`admin-dashboard/src/services/api.js`):

```javascript
export const exampleAPI = {
  list: () => client.get('/api/example').then(r => r.data),
  create: (data) => client.post('/api/example', data).then(r => r.data),
  delete: (id) => client.delete(`/api/example/${id}`).then(r => r.data),
}
```

**3. Add Route** (`admin-dashboard/src/App.jsx`):

```javascript
import Example from './pages/Example'

<Route path="/example" element={
  <ProtectedRoute>
    <Layout><Example /></Layout>
  </ProtectedRoute>
} />
```

**4. Add to Sidebar** (`admin-dashboard/src/components/Layout.jsx`):

```javascript
{ name: 'Example', path: '/example', icon: FileText }
```

---

## Database Schema

### Core Tables

**users:**
- `id` (PK)
- `username` (unique)
- `email` (unique)
- `password_hash`
- `role` (admin/developer/viewer)
- `is_active`
- `created_at`

**api_keys:**
- `id` (PK)
- `key` (unique, indexed)
- `name`
- `user_id` (FK → users)
- `rate_limit`
- `is_active`
- `expires_at`
- `last_used_at`

**categories:**
- Stored in JSON file `api/data/categories.json`
- Embedded in Qdrant vector database

**training_data:**
- `id` (PK)
- `title`
- `description`
- `price`
- `actual_category_id`
- `predicted_category_id`
- `confidence`
- `is_validated`
- `source`
- `created_at`

**request_logs:**
- `id` (PK)
- `timestamp`
- `endpoint`
- `method`
- `status_code`
- `response_time_ms`
- `api_key_id` (FK → api_keys)
- `request_body` (JSONB)
- `response_body` (JSONB)

### Relationships

```sql
api_keys.user_id → users.id
request_logs.api_key_id → api_keys.id
training_data.actual_category_id → categories (JSON file)
```

---

## API Development

### Authentication

**JWT Token Generation:**

```python
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**Dependency for Protected Routes:**

```python
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Usage
@router.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user["username"]}
```

### Rate Limiting

```python
import redis
from fastapi import HTTPException

redis_client = redis.Redis(host='localhost', port=6379)

async def check_rate_limit(api_key: str, limit: int = 1000):
    key = f"ratelimit:{api_key}:{datetime.now().hour}"
    count = redis_client.incr(key)
    
    if count == 1:
        redis_client.expire(key, 3600)  # 1 hour
    
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return count
```

### Error Handling

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## Frontend Development

### State Management (Zustand)

```javascript
import create from 'zustand'
import { persist } from 'zustand/middleware'

const useExampleStore = create(
  persist(
    (set, get) => ({
      items: [],
      selectedItem: null,
      
      setItems: (items) => set({ items }),
      selectItem: (item) => set({ selectedItem: item }),
      clearSelection: () => set({ selectedItem: null }),
    }),
    {
      name: 'example-storage',
      getStorage: () => localStorage,
    }
  )
)

export default useExampleStore
```

### Custom Hooks

```javascript
import { useState, useEffect } from 'react'
import { exampleAPI } from '../services/api'

export function useExample(id) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    if (!id) return
    
    exampleAPI.get(id)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [id])
  
  return { data, loading, error }
}
```

### TailwindCSS Custom Components

```css
/* src/index.css */
@layer components {
  .btn {
    @apply px-4 py-2 rounded font-medium transition-colors;
  }
  
  .btn-primary {
    @apply bg-blue-600 hover:bg-blue-700 text-white;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
}
```

---

## Testing

### Backend Tests (pytest)

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov-report=html
```

**Example Test** (`tests/test_classify.py`):

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_classify_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": "test_key"},
            json={
                "title": "iPhone 14 Pro Max",
                "description": "Brand new",
                "price": 25000000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "category_id" in data
        assert "confidence" in data
```

### Frontend Tests (Vitest + React Testing Library)

```bash
# Install test dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm run test

# Run with coverage
npm run test:coverage
```

**Example Test** (`src/pages/Dashboard.test.jsx`):

```javascript
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Dashboard from './Dashboard'
import * as api from '../services/api'

vi.mock('../services/api')

describe('Dashboard', () => {
  it('renders stats cards', async () => {
    api.systemAPI.health.mockResolvedValue({
      status: 'healthy',
      services: {}
    })
    
    render(<Dashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Total Requests')).toBeInTheDocument()
    })
  })
})
```

---

## Code Style

### Python (PEP 8 + Black)

```bash
# Format code
black api/

# Check style
flake8 api/

# Type checking
mypy api/
```

### JavaScript (ESLint + Prettier)

```bash
# Format code
npm run format

# Check style
npm run lint

# Fix auto-fixable issues
npm run lint:fix
```

### Commit Messages

Follow Conventional Commits:

```
feat: add new classification endpoint
fix: resolve rate limit bug
docs: update API documentation
refactor: simplify category service
test: add unit tests for classifier
chore: upgrade dependencies
```

---

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

**PR Checklist:**
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted (Black, Prettier)
- [ ] No linting errors
- [ ] All tests pass
- [ ] Reviewed by at least 1 person

---

## Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **React Docs:** https://react.dev
- **Tailwind CSS:** https://tailwindcss.com
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Qdrant:** https://qdrant.tech/documentation/
