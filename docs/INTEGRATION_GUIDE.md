# Complete Integration Guide for Frontend Developers

**Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Target Audience:** Frontend developers integrating with AutoCategory API

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Integration Patterns](#integration-patterns)
5. [Code Examples](#code-examples)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Best Practices](#best-practices)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## 1. Quick Start

### 1.1 Get API Key

```bash
1. Contact admin or register at: http://localhost:3001/admin
2. Create API key in dashboard
3. Copy API key (only shown once!)
4. Store securely (environment variable, not in code)
```

### 1.2 First API Call

```javascript
const API_KEY = process.env.AUTOCATEGORY_API_KEY;
const API_BASE = 'http://localhost:3001';

const response = await fetch(`${API_BASE}/api/classify`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    title: 'iPhone 15 Pro Max 256GB',
    description: 'Máy đẹp như mới'
  })
});

const result = await response.json();
console.log(result.category_path); // "Điện tử > Điện thoại > iPhone"
```

### 1.3 Check API Health

```javascript
const health = await fetch(`${API_BASE}/api/health`);
// → { "status": "ok" }
```

---

## 2. Authentication

### 2.1 API Key Authentication

**Khuyến nghị:** Dùng header `X-API-Key`

```javascript
headers: {
  'X-API-Key': 'sk_live_abc123...'
}
```

**Alternative:** Query parameter (không khuyến nghị cho production)

```javascript
fetch(`${API_BASE}/api/classify?api_key=sk_live_abc123...`)
```

### 2.2 JWT Token (Admin Dashboard Only)

```javascript
// Login
const loginResponse = await fetch(`${API_BASE}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'your_password'
  })
});

const { access_token } = await loginResponse.json();

// Use token
const response = await fetch(`${API_BASE}/api/auth/users`, {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

### 2.3 Token Refresh

```javascript
// JWT tokens expire after 24 hours
// Refresh before expiry or handle 401 errors

async function fetchWithRefresh(url, options) {
  let response = await fetch(url, options);
  
  if (response.status === 401) {
    // Token expired, re-login
    const token = await refreshToken();
    options.headers['Authorization'] = `Bearer ${token}`;
    response = await fetch(url, options);
  }
  
  return response;
}
```

---

## 3. API Endpoints Reference

### 3.1 Classification Endpoint

#### POST /api/classify

**Purpose:** Phân loại danh mục cho bài đăng

**Request:**
```typescript
interface ClassifyRequest {
  title: string;              // Required, 1-500 chars
  description?: string;        // Optional, max 5000 chars
  price?: number;             // Optional, >= 0
  image_urls?: string[];      // Optional, max 5 URLs
  fast?: boolean;             // Optional, skip LLM understand
}
```

**Response:**
```typescript
interface ClassifyResponse {
  status: string;
  category_id: number;
  category_name: string;
  category_path: string;
  confidence: number;         // 0.0-1.0
  decision: 'auto_assign' | 'preselect' | 'suggest_top3' | 'manual_select';
  
  understanding?: {
    normalized_product_text: string;
    suggested_title: string;
    suggested_description: string;
    confidence: number;
    text_image_consistency: string;
  };
  
  candidates?: Array<{
    category_id: number;
    category_name: string;
    category_path: string;
    similarity_score: number;
  }>;
}
```

**Example:**
```javascript
const result = await fetch('/api/classify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    title: 'đt iphone 15 pro max 256g zin 99%',
    description: 'máy đẹp sxdh fullbox bh 8 tháng',
    price: 28000000
  })
}).then(r => r.json());

// Handle based on decision
switch (result.decision) {
  case 'auto_assign':
    selectCategory(result.category_id);
    showBadge('✅ Auto-selected');
    break;
  case 'preselect':
    selectCategory(result.category_id);
    showBadge('💡 Suggested');
    allowUserChange();
    break;
  case 'suggest_top3':
    showTopThreeOptions(result.candidates);
    break;
  case 'manual_select':
    showManualSelector();
    break;
}
```

### 3.2 Generation Endpoint

#### POST /api/generate/from-images

**Purpose:** Tạo nội dung bài đăng từ ảnh sản phẩm

**Request:**
```typescript
interface GenerateRequest {
  image_urls: string[];           // Required, 1-5 URLs (recommend 1)
  existing_title?: string;
  existing_description?: string;
  generate_category?: boolean;    // Default: true
}
```

**Response:**
```typescript
interface GenerateResponse {
  status: string;
  generated: {
    title: string;
    description: string;
    detected_attributes: {
      brand?: string;
      model?: string;
      color?: string;
      condition?: 'mới' | 'cũ' | 'như mới';
    };
    price_suggestion?: {
      estimate: number;
      range: [number, number];
      reasoning: string;
    };
    category_suggestion?: {
      category_id: number;
      category_name: string;
      category_path: string;
      confidence: number;
    };
  };
}
```

**Example:**
```javascript
// User uploads image
const file = document.getElementById('image').files[0];

// 1. Upload to your storage first
const imageUrl = await uploadToStorage(file);

// 2. Generate content
const result = await fetch('/api/generate/from-images', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    image_urls: [imageUrl],  // Just first image
    generate_category: true
  })
}).then(r => r.json());

// 3. Auto-fill form
document.getElementById('title').value = result.generated.title;
document.getElementById('description').value = result.generated.description;
document.getElementById('price').value = result.generated.price_suggestion.estimate;
selectCategory(result.generated.category_suggestion.category_id);
```

### 3.3 Validation Endpoint

#### POST /api/generate/validate-consistency

**Purpose:** Kiểm tra text có khớp với ảnh không

**Request:**
```typescript
interface ValidateRequest {
  title: string;
  description?: string;
  image_urls: string[];
}
```

**Response:**
```typescript
interface ValidateResponse {
  is_consistent: boolean;
  confidence: number;
  issues: string[];
  warnings: string[];
}
```

**Example:**
```javascript
const validation = await fetch('/api/generate/validate-consistency', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    title: 'iPhone 15 Pro Max',
    description: 'Máy mới nguyên seal',
    image_urls: [imageUrl]
  })
}).then(r => r.json());

if (!validation.is_consistent) {
  showWarning(validation.issues.join(', '));
}
```

### 3.4 Category Endpoints

#### GET /api/categories

**Purpose:** Lấy danh sách categories (cho dropdown/tree selector)

**Query Parameters:**
- `active_only=true` - Chỉ categories active
- `leaf_only=true` - Chỉ leaf categories (không có con)
- `parent_id=123` - Children của category 123

**Response:**
```typescript
interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  parent_name: string;
  path: string;
  level: number;
  is_active: boolean;
  has_children: boolean;
}
```

**Example:**
```javascript
// Get all active categories
const categories = await fetch('/api/categories?active_only=true', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());

// Build tree or dropdown
buildCategoryTree(categories);
```

#### GET /api/categories/{id}

**Purpose:** Chi tiết 1 category

**Example:**
```javascript
const category = await fetch('/api/categories/123', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());

console.log(category.path); // "Điện tử > Điện thoại > iPhone"
```

---

## 4. Integration Patterns

### 4.1 Pattern 1: User Writes → Auto-Classify

**Flow:**
```
User types title + description
  ↓
User clicks "Chọn danh mục tự động"
  ↓
Call POST /api/classify
  ↓
Handle decision:
  - auto_assign: Auto-select, minimal confirmation
  - preselect: Pre-fill, allow change
  - suggest_top3: Show 3 options
  - manual_select: Show full selector
```

**Code:**
```javascript
async function handleAutoClassify() {
  const title = titleInput.value;
  const description = descriptionInput.value;
  
  if (!title) {
    showError('Please enter a title');
    return;
  }
  
  showLoading('Analyzing...');
  
  try {
    const result = await classify({ title, description });
    
    hideLoading();
    
    if (result.decision === 'auto_assign') {
      selectCategory(result.category_id);
      showSuccess('Category auto-selected!');
    } else if (result.decision === 'preselect') {
      selectCategory(result.category_id);
      showInfo('Suggested category. You can change if needed.');
      showAlternatives(result.candidates);
    } else if (result.decision === 'suggest_top3') {
      showTopThreeModal(result.candidates);
    } else {
      showManualSelector();
      showWarning('Please select category manually');
    }
  } catch (error) {
    hideLoading();
    showError('Classification failed: ' + error.message);
  }
}
```

### 4.2 Pattern 2: Image Upload → Auto-Generate All

**Flow:**
```
User uploads image(s)
  ↓
Upload to storage → get URL
  ↓
Call POST /api/generate/from-images (with first image)
  ↓
Auto-fill entire form:
  - title
  - description
  - price
  - category
  ↓
User reviews & posts
```

**Code:**
```javascript
async function handleImageUpload(files) {
  if (files.length === 0) return;
  
  showLoading('Generating content from image...');
  
  try {
    // 1. Upload first image only (faster)
    const firstImage = files[0];
    const imageUrl = await uploadToStorage(firstImage);
    
    // 2. Generate content
    const result = await generateFromImages({
      image_urls: [imageUrl],
      generate_category: true
    });
    
    hideLoading();
    
    // 3. Auto-fill form
    titleInput.value = result.generated.title;
    descriptionInput.value = result.generated.description;
    
    if (result.generated.price_suggestion) {
      priceInput.value = result.generated.price_suggestion.estimate;
      showPriceRange(result.generated.price_suggestion.range);
    }
    
    if (result.generated.category_suggestion) {
      selectCategory(result.generated.category_suggestion.category_id);
    }
    
    showSuccess('Content generated! Please review before posting.');
    
  } catch (error) {
    hideLoading();
    showError('Generation failed: ' + error.message);
  }
}
```

### 4.3 Pattern 3: Progressive Enhancement

**Flow:**
```
User starts typing
  ↓
Debounced classify call (fast mode)
  ↓
Show real-time suggestions
  ↓
User finishes, clicks button
  ↓
Full classify (with LLM understand)
  ↓
Final result
```

**Code:**
```javascript
// Real-time preview (fast mode)
const debouncedClassify = debounce(async (title) => {
  if (title.length < 10) return;
  
  const result = await classify({ 
    title, 
    fast: true  // Skip LLM understand
  });
  
  showPreview(result.category_path);
}, 500);

titleInput.addEventListener('input', (e) => {
  debouncedClassify(e.target.value);
});

// Final classification (full mode)
async function finalClassify() {
  const result = await classify({ 
    title: titleInput.value,
    description: descriptionInput.value,
    fast: false  // Full analysis
  });
  
  selectCategory(result.category_id);
}
```

### 4.4 Pattern 4: Hybrid - Manual with AI Assist

**Flow:**
```
User manually selects category
  ↓
AI validates in background
  ↓
If mismatch detected:
  "Are you sure? AI suggests: [different category]"
  ↓
User confirms or changes
```

**Code:**
```javascript
categorySelector.addEventListener('change', async (e) => {
  const userSelectedId = e.target.value;
  
  // Validate in background
  const aiResult = await classify({
    title: titleInput.value,
    description: descriptionInput.value
  });
  
  if (aiResult.category_id !== parseInt(userSelectedId) && 
      aiResult.confidence > 0.75) {
    showConfirmation(
      `AI suggests: ${aiResult.category_path} (${(aiResult.confidence*100).toFixed(0)}% confidence). ` +
      `Keep your selection or use AI suggestion?`,
      () => {}, // Keep user selection
      () => selectCategory(aiResult.category_id) // Use AI
    );
  }
});
```

---

## 5. Code Examples

### 5.1 Complete React Component

```jsx
import React, { useState } from 'react';
import { classify, generateFromImages } from './api';

function ProductForm() {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: '',
    category_id: null
  });
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState(null);

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    try {
      // Upload image
      const imageUrl = await uploadImage(file);
      
      // Generate content
      const result = await generateFromImages({
        image_urls: [imageUrl],
        generate_category: true
      });

      // Auto-fill
      setFormData({
        title: result.generated.title,
        description: result.generated.description,
        price: result.generated.price_suggestion?.estimate || '',
        category_id: result.generated.category_suggestion?.category_id || null
      });

      setSuggestion(result.generated.category_suggestion);
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoClassify = async () => {
    if (!formData.title) {
      alert('Please enter a title');
      return;
    }

    setLoading(true);
    try {
      const result = await classify({
        title: formData.title,
        description: formData.description,
        price: parseFloat(formData.price) || null
      });

      setFormData(prev => ({
        ...prev,
        category_id: result.category_id
      }));

      setSuggestion({
        category_path: result.category_path,
        confidence: result.confidence,
        decision: result.decision
      });
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="product-form">
      <h2>Đăng bài mới</h2>
      
      {/* Image Upload */}
      <div className="form-group">
        <label>Ảnh sản phẩm:</label>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleImageUpload}
          disabled={loading}
        />
        <small>Upload ảnh để tự động tạo nội dung</small>
      </div>

      {/* Title */}
      <div className="form-group">
        <label>Tiêu đề:</label>
        <input
          type="text"
          value={formData.title}
          onChange={e => setFormData({ ...formData, title: e.target.value })}
          placeholder="iPhone 15 Pro Max 256GB..."
        />
      </div>

      {/* Description */}
      <div className="form-group">
        <label>Mô tả:</label>
        <textarea
          value={formData.description}
          onChange={e => setFormData({ ...formData, description: e.target.value })}
          placeholder="Máy đẹp, zin all..."
        />
      </div>

      {/* Price */}
      <div className="form-group">
        <label>Giá:</label>
        <input
          type="number"
          value={formData.price}
          onChange={e => setFormData({ ...formData, price: e.target.value })}
          placeholder="28000000"
        />
      </div>

      {/* Category */}
      <div className="form-group">
        <label>Danh mục:</label>
        <div className="category-selector">
          {formData.category_id && (
            <div className="selected-category">
              {suggestion?.category_path}
              {suggestion?.decision === 'auto_assign' && (
                <span className="badge">✅ Auto-selected</span>
              )}
              {suggestion?.decision === 'preselect' && (
                <span className="badge">💡 Suggested</span>
              )}
            </div>
          )}
          <button 
            onClick={handleAutoClassify}
            disabled={loading || !formData.title}
          >
            🤖 Chọn danh mục tự động
          </button>
        </div>
      </div>

      {/* Submit */}
      <button 
        className="btn-primary"
        disabled={loading || !formData.category_id}
      >
        {loading ? 'Đang xử lý...' : 'Đăng bài'}
      </button>
    </div>
  );
}

export default ProductForm;
```

### 5.2 API Client Module

```javascript
// api.js
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';
const API_KEY = process.env.REACT_APP_API_KEY;

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

export async function classify(data) {
  return request('/api/classify', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function generateFromImages(data) {
  return request('/api/generate/from-images', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function getCategories(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/categories${query ? '?' + query : ''}`);
}

export async function validateConsistency(data) {
  return request('/api/generate/validate-consistency', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}
```

### 5.3 Vanilla JavaScript Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>AutoCategory Demo</title>
</head>
<body>
  <h1>Đăng bài sản phẩm</h1>
  
  <form id="productForm">
    <div>
      <label>Tiêu đề:</label>
      <input type="text" id="title" required>
    </div>
    
    <div>
      <label>Mô tả:</label>
      <textarea id="description"></textarea>
    </div>
    
    <div>
      <label>Danh mục:</label>
      <span id="categoryDisplay">Chưa chọn</span>
      <input type="hidden" id="category_id">
      <button type="button" onclick="autoClassify()">
        🤖 Chọn tự động
      </button>
    </div>
    
    <button type="submit">Đăng bài</button>
  </form>
  
  <div id="loading" style="display:none;">Đang xử lý...</div>

  <script>
    const API_KEY = 'your_api_key_here';
    const API_BASE = 'http://localhost:3001';

    async function autoClassify() {
      const title = document.getElementById('title').value;
      const description = document.getElementById('description').value;

      if (!title) {
        alert('Vui lòng nhập tiêu đề');
        return;
      }

      document.getElementById('loading').style.display = 'block';

      try {
        const response = await fetch(`${API_BASE}/api/classify`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
          },
          body: JSON.stringify({ title, description })
        });

        if (!response.ok) {
          throw new Error('API request failed');
        }

        const result = await response.json();

        document.getElementById('category_id').value = result.category_id;
        document.getElementById('categoryDisplay').textContent = 
          result.category_path + ` (${(result.confidence*100).toFixed(0)}%)`;

        if (result.decision === 'auto_assign') {
          alert('✅ Danh mục đã được chọn tự động!');
        } else if (result.decision === 'preselect') {
          alert('💡 Gợi ý danh mục. Bạn có thể thay đổi nếu muốn.');
        }
      } catch (error) {
        alert('Lỗi: ' + error.message);
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    }

    document.getElementById('productForm').addEventListener('submit', async (e) => {
      e.preventDefault();

      const category_id = document.getElementById('category_id').value;
      if (!category_id) {
        alert('Vui lòng chọn danh mục');
        return;
      }

      // Submit form...
      alert('Đăng bài thành công!');
    });
  </script>
</body>
</html>
```

---

## 6. Error Handling

### 6.1 HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | Check permissions |
| 429 | Rate Limited | Slow down, retry later |
| 500 | Server Error | Retry or contact support |

### 6.2 Error Response Format

```json
{
  "detail": "Error message here"
}
```

### 6.3 Error Handling Pattern

```javascript
async function classifyWithErrorHandling(data) {
  try {
    const response = await fetch('/api/classify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid API key');
      } else if (response.status === 429) {
        throw new Error('Rate limit exceeded. Please try again later.');
      } else if (response.status === 400) {
        const error = await response.json();
        throw new Error('Invalid request: ' + error.detail);
      } else {
        throw new Error('Server error. Please try again.');
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Classification error:', error);
    showUserError(error.message);
    throw error;
  }
}
```

---

## 7. Rate Limiting

### 7.1 Default Limits

| Tier | Requests/Minute | Requests/Day |
|------|-----------------|--------------|
| Free | 10 | 100 |
| Developer | 60 | 1,000 |
| Production | 120 | 10,000 |
| Enterprise | Custom | Custom |

### 7.2 Rate Limit Headers

```javascript
const response = await fetch('/api/classify', ...);

// Check rate limit info
console.log(response.headers.get('X-RateLimit-Limit'));      // 60
console.log(response.headers.get('X-RateLimit-Remaining'));  // 45
console.log(response.headers.get('X-RateLimit-Reset'));      // 1683123456
```

### 7.3 Handle Rate Limiting

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const resetTime = response.headers.get('X-RateLimit-Reset');
      const waitTime = resetTime ? 
        (parseInt(resetTime) * 1000 - Date.now()) : 
        60000; // Default 60s

      console.log(`Rate limited. Waiting ${waitTime}ms...`);
      await sleep(waitTime);
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

---

## 8. Best Practices

### 8.1 Performance

✅ **DO:**
- Use fast mode for real-time previews
- Cache category list locally
- Only send first image for generation
- Debounce user input
- Use progressive loading

❌ **DON'T:**
- Call API on every keystroke
- Send all 5 images for generation
- Ignore rate limits
- Block UI unnecessarily

### 8.2 Security

✅ **DO:**
- Store API key in environment variables
- Use HTTPS only
- Validate user input before sending
- Handle errors gracefully
- Log API errors for debugging

❌ **DON'T:**
- Expose API key in client-side code
- Store API key in Git
- Send sensitive data in URLs
- Trust API responses blindly

### 8.3 UX

✅ **DO:**
- Show loading states
- Display confidence levels
- Allow manual override
- Provide feedback
- Handle errors gracefully

❌ **DON'T:**
- Auto-select without confirmation on low confidence
- Hide alternatives
- Force AI decisions
- Ignore user preferences

---

## 9. Testing

### 9.1 Unit Testing

```javascript
// api.test.js
import { classify, generateFromImages } from './api';

describe('API Client', () => {
  test('classify returns valid response', async () => {
    const result = await classify({
      title: 'iPhone 15 Pro Max 256GB',
      description: 'Máy đẹp như mới'
    });

    expect(result).toHaveProperty('category_id');
    expect(result).toHaveProperty('confidence');
    expect(result.confidence).toBeGreaterThan(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
  });

  test('handles errors correctly', async () => {
    await expect(classify({ title: '' }))
      .rejects
      .toThrow();
  });
});
```

### 9.2 Integration Testing

```javascript
// integration.test.js
describe('Product Form Integration', () => {
  test('complete flow: upload image → generate → classify → submit', async () => {
    // 1. Upload image
    const imageUrl = await uploadImage(testImage);
    expect(imageUrl).toBeTruthy();

    // 2. Generate content
    const generated = await generateFromImages({
      image_urls: [imageUrl],
      generate_category: true
    });
    expect(generated.generated.title).toBeTruthy();

    // 3. Verify category
    const classified = await classify({
      title: generated.generated.title,
      description: generated.generated.description
    });
    expect(classified.category_id).toBe(
      generated.generated.category_suggestion.category_id
    );

    // 4. Submit (mock)
    const submitted = await submitProduct({
      ...generated.generated,
      category_id: classified.category_id
    });
    expect(submitted.success).toBe(true);
  });
});
```

### 9.3 Manual Testing Checklist

- [ ] Test with Vietnamese text
- [ ] Test with abbreviated text (đt, sxdh, zin...)
- [ ] Test with very short title (<10 chars)
- [ ] Test with very long description (>1000 chars)
- [ ] Test with image upload
- [ ] Test with invalid image URL
- [ ] Test with invalid API key
- [ ] Test rate limiting
- [ ] Test network errors
- [ ] Test different decision types

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue: "Invalid API key"
```
Solution:
1. Check API key is correct
2. Check header name: X-API-Key
3. Check API key is active in dashboard
4. Contact admin if still failing
```

#### Issue: "Rate limit exceeded"
```
Solution:
1. Check current limits in dashboard
2. Implement retry logic with backoff
3. Optimize number of API calls
4. Upgrade plan if needed
```

#### Issue: "Low confidence classifications"
```
Solution:
1. Add more details in title/description
2. Add images for validation
3. Use full mode (fast=false)
4. Provide feedback to improve model
```

#### Issue: "Timeout errors"
```
Solution:
1. Check network connection
2. Increase timeout (default 30s)
3. Try fast mode for quicker response
4. Check API status page
```

### 10.2 Debug Mode

```javascript
// Enable debug logging
const DEBUG = true;

async function classifyDebug(data) {
  if (DEBUG) {
    console.log('Request:', data);
  }

  const start = Date.now();
  const result = await classify(data);
  const duration = Date.now() - start;

  if (DEBUG) {
    console.log('Response:', result);
    console.log('Duration:', duration + 'ms');
  }

  return result;
}
```

### 10.3 Support

**Need help?**
- Check API documentation: http://localhost:3001/docs
- Check API status: http://localhost:3001/api/health
- Contact support: admin@localhost
- Join Discord: https://discord.gg/autocategory

---

## 📚 Additional Resources

- [API Documentation](http://localhost:3001/docs) - Interactive API docs
- [Data Standards](./DATA_STANDARDS.md) - Data format specifications
- [Admin Manual](./ADMIN_MANUAL.md) - For admins
- [GitHub Examples](https://github.com/autocategory/examples) - Code samples

---

**Version History:**
- v1.0.0 (2026-05-06) - Initial release
