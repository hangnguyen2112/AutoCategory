# Frontend API Integration Guide

**Base URL:** `https://autocategory.cucham.com/api` hoặc `http://localhost:8000/api`  
**API Docs (Swagger):** `http://localhost:8000/docs`  
**Version:** 2.0.0

---

## 🔐 Authentication

### API Key (dùng cho classify / generate)

Tất cả các endpoint `/classify` và `/generate/*` đều yêu cầu API key:

```http
X-API-Key: sk_live_xxxxxxxxxxxxxxxx
```

### JWT Token (dùng cho admin dashboard / feedback)

```http
Authorization: Bearer <access_token>
```

### Lấy JWT Token — POST /auth/login

```javascript
const res = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'your_password' })
});
const { access_token, refresh_token, expires_in, user } = await res.json();
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true
  }
}
```

### Refresh Token — POST /auth/refresh

```javascript
const res = await fetch('/api/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token: storedRefreshToken })
});
const { access_token } = await res.json();
```

### Đổi mật khẩu — POST /auth/change-password

```javascript
await fetch('/api/auth/change-password', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({ old_password: 'abc', new_password: 'newpass123' })
});
```

---

## 🔑 Quản lý API Key

### Tạo API Key — POST /auth/api-keys

```javascript
const res = await fetch('/api/auth/api-keys', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    name: 'My App Key',
    environment: 'production',       // production | development | test
    rate_limit_per_minute: 60,
    rate_limit_per_day: 1000,
    can_classify: true,
    can_generate: true,
    can_admin: false,
    expires_at: null                 // null = không hết hạn
  })
});
const { api_key } = await res.json();
// api_key chỉ hiển thị 1 lần khi tạo — lưu ngay!
```

### Danh sách API Key — GET /auth/api-keys

```javascript
const res = await fetch('/api/auth/api-keys', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const keys = await res.json();
```

### Thu hồi API Key — DELETE /auth/api-keys/{id}

```javascript
await fetch(`/api/auth/api-keys/${keyId}`, {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 🤖 Chức năng 1: Auto-Categorize

### POST /classify

Yêu cầu `X-API-Key`.

**Request:**
```typescript
interface ClassifyRequest {
  title: string;           // max 500 chars
  description?: string;    // max 5000 chars
  price?: number;
  image_urls?: string[];   // max 5 URLs
  fast?: boolean;          // default false — true = bỏ qua LLM understand, nhanh hơn
}
```

**Response:**
```typescript
interface ClassifyResponse {
  status: string;          // "ok"
  category_id: number;
  category_name: string;
  category_path: string;   // "Điện tử > Điện thoại > iPhone"
  confidence: number;      // 0.0–1.0
  decision: "auto_assign" | "preselect" | "suggest_top3" | "manual_select";
  understanding?: {
    suggested_title: string;
    suggested_description: string;
    normalized_product_text: string;
    confidence: number;
  };
  candidates?: Array<{
    category_id: number;
    category_name: string;
    category_path: string;
    similarity_score: number;
  }>;
}
```

**Decision logic:**

| Decision | Confidence | Frontend nên làm |
|---|---|---|
| `auto_assign` | ≥ 90% | Tự động chọn, hiện badge "Đã tự động phân loại" |
| `preselect` | 75–90% | Pre-fill, để user confirm |
| `suggest_top3` | 55–75% | Hiện top 3 để user chọn |
| `manual_select` | < 55% | Yêu cầu user tự chọn |

**Ví dụ:**
```javascript
const res = await fetch('/api/classify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    title: 'iPhone 15 Pro Max 256GB xanh 99%',
    description: 'Máy đẹp fullbox bh 8 tháng',
    fast: false
  })
});
const result = await res.json();
// result.decision, result.confidence, result.category_name...
```

---

## 📝 Chức năng phụ: Feedback Phân Loại

### POST /classify/feedback

Khi user sửa lại danh mục sai → gửi feedback để cải thiện hệ thống.  
Yêu cầu JWT token (`Authorization: Bearer ...`).

```javascript
await fetch('/api/classify/feedback', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    request_log_id: result.log_id,    // ID từ response classify
    actual_category_id: selectedId,
    actual_category_name: 'iPhone',
    note: 'Model nhầm'
  })
});
```

---

## 🖼️ Chức năng 2: Generate từ Ảnh

### POST /generate/from-images

Yêu cầu `X-API-Key`. AI đọc ảnh → sinh tiêu đề + mô tả + danh mục + thuộc tính.

**Request:**
```typescript
interface GenerateFromImagesRequest {
  image_urls: string[];         // 1–5 URLs, khuyến nghị chỉ dùng 1
  existing_title?: string;      // Gợi ý để AI cải thiện
  existing_description?: string;
  generate_category?: boolean;  // default true
}
```

**Response:**
```json
{
  "status": "ok",
  "mode": "from_images",
  "generated": {
    "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên như mới",
    "description": "Mình bán iPhone 15 Pro Max 256GB...",
    "detected_attributes": {
      "brand": "Apple",
      "model": "iPhone 15 Pro Max",
      "variant": "256GB",
      "color": "Natural Titanium",
      "condition": "like_new",
      "condition_detail": "pin 92%, không trầy",
      "accessories": ["hộp", "cáp USB-C"],
      "warranty": "in_warranty",
      "category_hint": "Điện thoại"
    },
    "price_suggestion": {
      "estimate": 28000000,
      "range": [26000000, 30000000],
      "reasoning": "..."
    },
    "category_suggestion": {
      "category_id": 123,
      "category_name": "iPhone",
      "category_path": "Điện tử > Điện thoại > iPhone",
      "confidence": 0.92,
      "decision": "auto_assign",
      "attributes": []
    }
  }
}
```

**Ví dụ:**
```javascript
const res = await fetch('/api/generate/from-images', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    image_urls: [imageUrl],   // CHỈ 1 ảnh đầu — nhanh hơn nhiều
    generate_category: true
  })
});
const { generated } = await res.json();
```

---

## 📄 Chức năng 3: Generate từ Text

### POST /generate/from-text

Yêu cầu `X-API-Key`. Từ tiêu đề + mô tả → cải thiện nội dung + gợi ý danh mục + thuộc tính (không cần ảnh).

**Request:**
```typescript
interface GenerateFromTextRequest {
  title?: string;       // max 500 chars
  description?: string; // max 5000 chars
  price?: number;
}
```

**Response:**
```json
{
  "status": "ok",
  "mode": "from_text",
  "suggested": {
    "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên",
    "description": "Mình bán iPhone 15 Pro Max 256GB...",
    "confidence": 0.88
  },
  "category_suggestion": {
    "category_id": 123,
    "category_name": "iPhone",
    "category_path": "Điện tử > Điện thoại > iPhone",
    "confidence": 0.92,
    "decision": "auto_assign",
    "attributes": []
  },
  "candidates": []
}
```

---

## 🔄 Chức năng 4: Generate Full (Ảnh + Text)

### POST /generate/full

Yêu cầu `X-API-Key`. Kết hợp ảnh + text → phân tích đầy đủ nhất.

**Request:**
```typescript
interface GenerateFullRequest {
  image_urls: string[];  // 1–5 URLs
  title?: string;
  description?: string;
  price?: number;
}
```

**Response:**
```json
{
  "status": "ok",
  "mode": "full",
  "generated": {
    "title": "...",
    "description": "..."
  },
  "image_analysis": { },
  "category_suggestion": { },
  "candidates": []
}
```

---

## ⚡ Chức năng 5: Streaming Pipeline (SSE)

### POST /generate/stream

Yêu cầu `X-API-Key`. Trả về kết quả từng bước qua Server-Sent Events — UI cập nhật dần, không cần chờ toàn bộ.

**Request:**
```typescript
interface GenerateStreamRequest {
  image_urls?: string[];
  title?: string;
  description?: string;
  price?: number;
  full?: boolean;  // true = AI đề xuất giá trị thuộc tính (chậm hơn nhưng chính xác hơn)
}
```

**Stream events theo thứ tự:**

| `step` | Nội dung |
|---|---|
| `analyzing_image` | Bắt đầu phân tích ảnh |
| `image_analysis` | `title`, `description`, `detected_attributes`, `price_suggestion` |
| `analyzing_text` | Bắt đầu phân tích text (khi không có ảnh) |
| `text_analysis` | `title`, `description`, `confidence` |
| `classifying` | Bắt đầu phân loại |
| `classification` | `category_id`, `category_name`, `category_path`, `confidence`, `decision`, `candidates` |
| `loading_attributes` | Bắt đầu load thuộc tính |
| `attributes` | `attributes`, `selected_values` |
| `done` | Hoàn tất |
| `error` | Lỗi tại `stage` nào đó |

**Ví dụ frontend:**
```javascript
const res = await fetch('/api/generate/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    image_urls: [imageUrl],
    full: false
  })
});

const reader = res.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    const event = JSON.parse(line.slice(6));

    switch (event.step) {
      case 'image_analysis':
        fillTitle(event.title);
        fillDescription(event.description);
        break;
      case 'classification':
        selectCategory(event.category_id, event.category_name);
        break;
      case 'attributes':
        fillAttributes(event.selected_values);
        break;
      case 'done':
        hideLoading();
        break;
      case 'error':
        showError(`Lỗi tại ${event.stage}: ${event.message}`);
        break;
    }
  }
}
```

---

## ✅ Chức năng 6: Validate Consistency

### POST /generate/validate-consistency

Kiểm tra text có khớp ảnh không. Không cần API key.

```javascript
const res = await fetch('/api/generate/validate-consistency', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'iPhone 15 Pro Max',
    description: 'Máy mới nguyên seal',
    image_urls: ['https://cdn.example.com/product.jpg']
  })
});

// Response:
// {
//   "is_consistent": false,
//   "confidence": 0.95,
//   "issues": ["Tiêu đề nói iPhone nhưng ảnh là Samsung Galaxy"],
//   "warnings": []
// }
```

---

## 💡 Chức năng 7: Tư vấn Người Mua

### POST /generate/buyer-advice

LLM đóng vai trợ lý mua đồ cũ. Không cần API key.

```javascript
const res = await fetch('/api/generate/buyer-advice', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'iPhone 15 Pro Max 256GB',
    description: 'Máy đẹp 99% fullbox',
    price: 28000000,
    image_urls: ['https://cdn.example.com/product.jpg'] // optional
  })
});
const { advice } = await res.json();
// advice.price_assessment, advice.checklist, advice.red_flags, advice.tips
```

---

## 🎨 Frontend Workflows

### Workflow 1: User tự viết → Auto-categorize

```
User nhập title + description
  → POST /classify
  → auto_assign:   hiện badge "Đã phân loại tự động"
  → preselect:     pre-fill, user confirm
  → suggest_top3:  hiện 3 lựa chọn
  → manual_select: user tự chọn danh mục
```

### Workflow 2: Upload ảnh → đầy đủ nội dung (Streaming)

```
User upload ảnh
  → POST /generate/stream (SSE)
      ├── image_analysis  → fill title + description ngay
      ├── classification  → select category ngay
      └── attributes      → fill thuộc tính ngay
  → User review & chỉnh sửa
  → User click Đăng bài
```

### Workflow 3: Hybrid — Generate từ ảnh + refine bằng text

```
1. POST /generate/from-images  → generate initial content
2. User chỉnh sửa title/description
3. POST /classify               → re-classify với nội dung đã sửa
```

---

## ⚡ Performance Tips

| Tình huống | Endpoint | Ghi chú |
|---|---|---|
| Nhanh nhất | `POST /classify` với `fast: true` | 0.5–1s, bỏ qua LLM understand |
| Bình thường | `POST /classify` với `fast: false` | 2–3s, có LLM understand |
| UX tốt nhất | `POST /generate/stream` | Hiển thị kết quả từng bước |
| Offline-first | `POST /generate/from-images` 1 ảnh | ~2–3s, nhanh hơn nhiều ảnh |

```javascript
// Fast mode khi user đang typing live preview
if (isLivePreview || isMobile) {
  classify({ title, fast: true });
}

// Chỉ gửi ảnh đầu tiên
const result = await generateFromImages({ image_urls: [images[0]] });
```

---

## 🛠️ Rate Limiting

- **Không có API key:** 60 req/phút, 1000 req/ngày (theo IP)
- **Có API key:** Theo giá trị `rate_limit_per_minute` / `rate_limit_per_day` của key đó
- **429 Too Many Requests:** Thử lại sau 60 giây

---

## 🐛 Error Handling

| Status | Ý nghĩa |
|---|---|
| `200` | Thành công |
| `400` | Request không hợp lệ |
| `401` | Thiếu hoặc sai token/API key |
| `403` | Không đủ quyền |
| `404` | Không tìm thấy |
| `429` | Rate limit vượt quá |
| `500` | Lỗi server |

```javascript
try {
  const res = await fetch('/api/classify', {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (res.status === 429) {
    const retryAfter = res.headers.get('Retry-After') || 60;
    showError(`Quá nhiều request. Thử lại sau ${retryAfter}s`);
    return;
  }
  if (!res.ok) {
    const err = await res.json();
    showError(err.detail || 'Có lỗi xảy ra');
    return;
  }
  const result = await res.json();
} catch {
  showError('Không thể kết nối đến server');
}
```

---

## 🧪 Test Cases

```json
// Điện thoại — expected: "iPhone", confidence > 0.85
{ "title": "iphone 15 pro max 256g zin 99%", "description": "máy đẹp sxdh fullbox bh 8 tháng" }

// Laptop — expected: "Laptop", confidence > 0.80
{ "title": "laptop dell i5 ram 8g", "description": "máy còn tốt giá sv" }

// Xe máy — expected: "Honda SH"
{ "title": "sh 150 đời 2020 bstp", "description": "xe đẹp máy zin" }
```

---

## 📞 Links

- **Swagger UI:** `http://localhost:8000/docs`
- **Health check:** `GET /api/health`
- **Admin dashboard:** `http://localhost:3001/admin`
