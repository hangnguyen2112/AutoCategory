# API Documentation - AutoCategory

## Table of Contents
1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Error Handling](#error-handling)
4. [Endpoints](#endpoints)
   - [Auth & User Management](#auth--user-management)
   - [Classification](#classification-endpoints)
   - [Generate Content](#generate-content)
   - [Categories (Public)](#categories-public)
   - [Admin - Logs](#admin---logs)
   - [Admin - Training Data](#admin---training-data)
   - [Admin - Config](#admin---config)
   - [Admin - Categories](#admin---categories)
   - [Admin - System](#admin---system)
5. [SDKs & Examples](#sdks--examples)

---

## Authentication

AutoCategory supports two authentication methods:

### 1. API Keys (For External Integrations)

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:3001/api/classify
```

### 2. JWT Tokens (For Admin Dashboard)

**Login to get JWT token:**
```bash
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

**Use JWT token:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:3001/api/auth/users
```

---

## Rate Limiting

- **Per API Key:** 1000 requests per hour
- **Per IP Address:** 100 requests per hour (unauthenticated)
- **Admin Endpoints:** 500 requests per hour

**Rate limit headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1704067200
```

**Rate limit exceeded response:**
```json
{
  "detail": "Rate limit exceeded. Try again in 3600 seconds."
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message here",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Endpoints

### Classification Endpoints

#### POST /api/classify

Classify a product into the most relevant category. Requires `X-API-Key` header.

**Request:**
```bash
curl -X POST http://localhost:3001/api/classify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 14 Pro Max 256GB",
    "description": "Brand new, sealed, with warranty",
    "price": 25000000
  }'
```

**Request Body:**
```json
{
  "title": "string (max 500 chars)",
  "description": "string (optional, max 5000 chars)",
  "price": "float (optional, >= 0)",
  "image_urls": ["string (optional, max 5 URLs)"],
  "fast": "boolean (optional, default false — true skips LLM understand step)"
}
```

**Response:**
```json
{
  "status": "ok",
  "category_id": 123,
  "category_name": "iPhone",
  "category_path": "Điện tử > Điện thoại > iPhone",
  "confidence": 0.92,
  "decision": "preselect",
  "understanding": {
    "normalized_product_text": "...",
    "suggested_title": "iPhone 14 Pro Max 256GB zin 99%",
    "suggested_description": "...",
    "confidence": 0.88,
    "text_image_consistency": "text_only"
  },
  "candidates": [
    {
      "category_id": 123,
      "category_name": "iPhone",
      "category_path": "Điện tử > Điện thoại > iPhone",
      "similarity_score": 0.89
    }
  ],
  "alternatives": [
    { "category_id": 124, "confidence": 0.76 }
  ]
}
```

**Decision values:**

| Decision | Confidence | Recommended Action |
|---|---|---|
| `auto_assign` | ≥ 90% | Auto-select, no confirmation needed |
| `preselect` | ≥ 75% | Pre-fill but allow user to change |
| `suggest_top3` | ≥ 55% | Show top 3 options for user to pick |
| `manual_select` | < 55% | Require manual category selection |

#### POST /api/classify/feedback

Submit a correction when the predicted category is wrong. Requires JWT or API key.

**Request Body:**
```json
{
  "request_log_id": 456,
  "actual_category_id": 125,
  "actual_category_name": "Điện thoại thông minh",
  "actual_category_path": "Điện tử > Điện thoại > Điện thoại thông minh",
  "note": "optional note"
}
```

**Response:**
```json
{
  "success": true,
  "training_data_id": 789,
  "was_corrected": true
}
```

---

### Auth & User Management

All auth/user endpoints are under `/api/auth/`. JWT required for user management (admin only).

#### POST /api/auth/login
#### POST /api/auth/refresh
#### GET /api/auth/me
#### POST /api/auth/change-password

#### GET /api/auth/users

List all users. Admin only.

**Query Parameters:**
- `skip` (int, default=0): Number of records to skip
- `limit` (int, default=100): Maximum records to return

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "full_name": "Admin User",
      "role": "admin",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### POST /api/auth/register

Create a new user. Admin only.

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "New User",
  "role": "developer"
}
```

#### PATCH /api/auth/users/{user_id}

Update user info. Admin only.

#### DELETE /api/auth/users/{user_id}

Delete a user. Admin only.

---

### Admin - API Keys

#### GET /api/auth/api-keys

List all API keys.

**Response:**
```json
{
  "api_keys": [
    {
      "id": 1,
      "key": "ac_1234567890abcdef****",
      "name": "Production API",
      "user_id": 1,
      "rate_limit": 1000,
      "is_active": true,
      "expires_at": "2025-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z",
      "usage_count": 5432,
      "last_used_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

#### POST /api/auth/api-keys

Create a new API key.

```json
{
  "name": "My API Key",
  "rate_limit": 1000,
  "expires_in_days": 365
}
```

**Response:**
```json
{
  "id": 2,
  "key": "ac_abcdef1234567890",
  "name": "My API Key",
  "rate_limit": 1000,
  "expires_at": "2025-01-15T00:00:00Z",
  "message": "⚠️ Save this key now! You won't be able to see it again."
}
```

#### DELETE /api/auth/api-keys/{key_id}

Revoke an API key.

---

### Generate Content

All generate endpoints are public (no auth required).

#### POST /api/generate/from-images

AI reads images → generate title, description, category, attributes.

**Request:**
```json
{
  "image_urls": ["https://..."],
  "existing_title": "",
  "existing_description": "",
  "generate_category": true
}
```

#### POST /api/generate/from-text

From title + description → suggest category + attributes.

**Request:**
```json
{
  "title": "iPhone 15 Pro Max 256GB",
  "description": "Máy đẹp như mới",
  "price": 28000000
}
```

#### POST /api/generate/full

Combined: images + text → full analysis.

**Request:**
```json
{
  "image_urls": ["https://..."],
  "title": "string (optional)",
  "description": "string (optional)",
  "price": 0
}
```

#### POST /api/generate/validate-consistency

Check if title/description matches what's in the images.

**Request:**
```json
{
  "title": "iPhone 15",
  "description": "Máy mới",
  "image_urls": ["https://..."]
}
```

**Response:**
```json
{
  "is_consistent": false,
  "confidence": 0.95,
  "issues": ["Tiêu đề nói iPhone nhưng ảnh là Samsung"],
  "warnings": []
}
```

---

### Categories (Public)

No auth required.

#### GET /api/categories

All active categories with hierarchy info.

#### GET /api/categories/leaves

Only leaf (bottom-level) categories.

#### GET /api/categories/{category_id}/attributes

Get field definitions for a specific category.

#### POST /api/categories/{category_id}/suggest-fields

LLM suggests field values based on product title/description.

**Request:**
```json
{
  "title": "iPhone 15 Pro Max",
  "description": "Máy đẹp 99%"
}
```

---

### Admin - Logs

JWT required (admin).

#### GET /api/admin/logs/requests

List classification request logs with filters.

#### GET /api/admin/logs/requests/{log_id}

Get a single request log with full detail (including pipeline steps, LLM reason).

#### GET /api/admin/logs/stats

Aggregated stats: total requests, accuracy rate, top categories, etc.

#### DELETE /api/admin/logs/requests/cleanup

Delete old logs. Accepts `days_to_keep` query param.

---

### Admin - Training Data

JWT required (admin).

#### GET /api/admin/training-data
#### POST /api/admin/training-data
#### GET /api/admin/training-data/{data_id}

#### PATCH /api/admin/training-data/{data_id}

Update a training sample (not PUT).

#### DELETE /api/admin/training-data/{data_id}
#### GET /api/admin/training-data/stats/overview
#### POST /api/admin/training-data/bulk-validate

---

### Admin - Config

JWT required (admin). Manage system configuration key-value pairs.

#### GET /api/admin/config
#### POST /api/admin/config
#### GET /api/admin/config/{key}
#### PATCH /api/admin/config/{key}
#### DELETE /api/admin/config/{key}
#### POST /api/admin/config/bulk-update
#### GET /api/admin/config/categories/list

---

### Admin - Categories

JWT required (admin).

#### POST /api/admin/categories/sync

Sync categories from the configured upstream source.

#### GET /api/admin/categories/sync/history
#### GET /api/admin/categories/sync/latest
#### GET /api/admin/categories/sync/stats

#### POST /api/admin/categories/import

Import categories from JSON file. Multipart form-data with `file` field.

#### GET /api/admin/categories/export

Export all categories as JSON.

#### POST /api/admin/categories/generate-descriptions

Auto-generate LLM descriptions for categories that lack one.

#### POST /api/admin/categories/rebuild-index

Rebuild Qdrant vector index from DB. Use `force: true` to overwrite all.

**Request:**
```json
{
  "force": true,
  "only_leaf_categories": true
}
```

#### PATCH /api/admin/categories/{category_id}

Update a category's name and/or description.

**Request:**
```json
{
  "name": "Tên mới",
  "description": "Mô tả mới"
}
```

**Response:**
```json
{
  "id": 5,
  "name": "Tên mới",
  "description": "Mô tả mới"
}
```

#### POST /api/admin/categories/sync-omni

Sync categories + attributes from Omni API.

#### GET /api/admin/categories/attributes

All category attributes across the full tree.

#### GET /api/admin/categories/attributes/{category_id}

Attributes for a specific category.

#### GET /api/admin/categories/omni-config

Current Omni API sync configuration.

#### GET /api/admin/categories/count

Total category count.

---

### Admin - System

JWT required (admin).

#### GET /api/admin/system/health

Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": {"status": "running", "cpu": 25.3, "memory": 512},
    "llm": {"status": "running", "cpu": 45.2, "memory": 2048},
    "qdrant": {"status": "running", "cpu": 10.1, "memory": 1024},
    "postgres": {"status": "running", "cpu": 15.0, "memory": 256}
  },
  "uptime_seconds": 345600
}
```

#### POST /api/admin/system/services/{service_name}/control

Start/stop/restart a service.

**Path param:** `service_name` = `llm`, `qdrant`, `api`, etc.

**Request:**
```json
{
  "action": "restart"
}
```

#### POST /api/admin/system/cache/clear

Clear application cache.

#### GET /api/admin/system/logs
#### GET /api/admin/system/metrics
#### GET /api/admin/system/database/stats
#### GET /api/admin/system/info

---

## SDKs & Examples

### Python

```python
import requests

# Classification
response = requests.post(
    'http://localhost:3001/api/classify',
    headers={'X-API-Key': 'your-api-key'},
    json={
        'title': 'iPhone 14 Pro Max',
        'description': 'Brand new',
        'price': 25000000
    }
)
result = response.json()
print(f"Category: {result['category_name']}")
print(f"Confidence: {result['confidence']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:3001/api/classify', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'iPhone 14 Pro Max',
    description: 'Brand new',
    price: 25000000
  })
});

const result = await response.json();
console.log(`Category: ${result.category_name}`);
console.log(`Confidence: ${result.confidence}`);
```

### PHP

```php
<?php
$ch = curl_init('http://localhost:3001/api/classify');
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'X-API-Key: your-api-key',
    'Content-Type: application/json'
]);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
    'title' => 'iPhone 14 Pro Max',
    'description' => 'Brand new',
    'price' => 25000000
]));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$result = json_decode($response, true);

echo "Category: " . $result['category_name'] . "\n";
echo "Confidence: " . $result['confidence'] . "\n";
?>
```

---

## Support

- **Email:** admin@localhost
- **Documentation:** http://localhost:3001/docs
- **Status Page:** http://localhost:3001/api/health
