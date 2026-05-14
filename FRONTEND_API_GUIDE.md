# Frontend API Integration Guide

**Base URL:** `http://your-domain.com/api` hoặc `http://localhost:8000/api`

---

## 🎯 Chức năng 1: Auto-Categorize (Phân loại tự động)

### Endpoint
```
POST /api/classify
```
> Yêu cầu header `X-API-Key`.

### Request Body
```typescript
interface ClassifyRequest {
  title: string;              // Required, 1-500 chars
  description?: string;        // Optional, max 5000 chars
  price?: number;             // Optional, >= 0
  image_urls?: string[];      // Optional, max 5 URLs
  fast?: boolean;             // Optional, default false (true = skip LLM understand)
}
```

### Response
```typescript
interface ClassifyResponse {
  status: string;                    // "ok"
  category_id: number;               // ID danh mục được chọn
  category_name: string;             // Tên danh mục
  category_path: string;             // Đường dẫn: "Điện tử > Điện thoại > iPhone"
  confidence: number;                // 0.0-1.0
  decision: "auto_assign" | "preselect" | "suggest_top3" | "manual_select";
  
  // Chi tiết thêm
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
  
  alternatives?: Array<{
    category_id: number;
    confidence: number;
  }>;
}
```

### Decision Types

| Decision | Meaning | Frontend Action |
|----------|---------|----------------|
| `auto_assign` | Rất tự tin (>90%) | Tự động chọn, không cần user confirm |
| `preselect` | Khá tự tin (75-90%) | Pre-select nhưng cho user xem & đổi nếu muốn |
| `suggest_top3` | Không chắc (55-75%) | Show top 3 options cho user chọn |
| `manual_select` | Không đủ info (<55%) | User phải tự chọn |

### Example Request
```javascript
// Ví dụ 1: Bài viết đơn giản
const response = await fetch('/api/classify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "iPhone 15 Pro Max 256GB zin đẹp 99%",
    description: "Máy đẹp sxdh fullbox bh 8 tháng"
  })
});

// Ví dụ 2: Với ảnh (để validate)
const response = await fetch('/api/classify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "iPhone 15 Pro Max 256GB",
    description: "Máy đẹp như mới",
    price: 28000000,
    image_urls: ["https://storage.example.com/image1.jpg"]
  })
});

// Ví dụ 3: Fast mode (nhanh hơn, ít chính xác hơn)
const response = await fetch('/api/classify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "iPhone 15 Pro Max 256GB",
    fast: true  // Bỏ qua LLM understand step
  })
});
```

### Example Response
```json
{
  "status": "ok",
  "category_id": 123,
  "category_name": "iPhone",
  "category_path": "Điện tử > Điện thoại > iPhone",
  "confidence": 0.92,
  "decision": "preselect",
  "understanding": {
    "normalized_product_text": "Điện thoại iPhone 15 Pro Max 256GB, tình trạng rất mới 99%, nguyên bản...",
    "suggested_title": "iPhone 15 Pro Max 256GB zin 99% BH 8 tháng",
    "suggested_description": "Mình bán iPhone 15 Pro Max 256GB. Máy đẹp còn 99%...",
    "confidence": 0.88
  },
  "candidates": [
    {
      "category_id": 123,
      "category_name": "iPhone",
      "category_path": "Điện tử > Điện thoại > iPhone",
      "similarity_score": 0.89
    },
    {
      "category_id": 124,
      "category_name": "Điện thoại thông minh",
      "category_path": "Điện tử > Điện thoại > Điện thoại thông minh",
      "similarity_score": 0.76
    }
  ]
}
```

---

## � Chức năng phụ 0: Gửi Feedback Phân Loại

Khi user sửa lại danh mục được gợi ý sai, gửi feedback để hệ thống học.

### Endpoint
```
POST /api/classify/feedback
```
> Yêu cầu JWT token (Authorization: Bearer ...) hoặc API key.

### Request Body
```typescript
interface FeedbackRequest {
  request_log_id: number;           // ID của request log cần sửa
  actual_category_id: number;       // Category ID đúng
  actual_category_name?: string;    // Tên category đúng (optional)
  actual_category_path?: string;    // Path (optional)
  note?: string;                    // Ghi chú thêm (max 500 chars)
}
```

### Example
```javascript
await fetch('/api/classify/feedback', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY  // hoặc Authorization: Bearer <token>
  },
  body: JSON.stringify({
    request_log_id: result.log_id,    // từ response của /api/classify
    actual_category_id: userSelectedId
  })
});
```

---

## �🖼️ Chức năng 2: Auto-Generate (Tạo tin từ ảnh)

### Endpoint
```
POST /api/generate/from-images
```

### Request Body
```typescript
interface GenerateRequest {
  image_urls: string[];           // Required, 1-5 URLs (KHUYẾN NGHỊ: chỉ dùng 1 ảnh đầu)
  existing_title?: string;        // Optional, để refine/improve
  existing_description?: string;  // Optional, để refine/improve
  generate_category?: boolean;    // Optional, default true
}
```

### Response
```typescript
interface GenerateResponse {
  status: string;  // "ok"
  generated: {
    title: string;                    // Tiêu đề được tạo
    description: string;              // Mô tả được tạo
    detected_attributes: {
      brand?: string;
      model?: string;
      color?: string;
      condition?: string;             // "mới" | "cũ" | "như mới"
    };
    price_suggestion?: {
      estimate: number;               // Giá ước tính (VNĐ)
      range: [number, number];        // [min, max]
      reasoning: string;
    };
    category_suggestion?: {           // Nếu generate_category = true
      category_id: number;
      category_name: string;
      category_path: string;
      confidence: number;
    };
  };
}
```

### Example Request
```javascript
// Ví dụ 1: Chỉ dùng 1 ảnh đầu (KHUYẾN NGHỊ)
const formData = new FormData();
const file = document.getElementById('imageInput').files[0];

// Upload ảnh lên storage của bạn trước
const imageUrl = await uploadToStorage(file);

// Gọi API generate
const response = await fetch('/api/generate/from-images', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_urls: [imageUrl],  // CHỈ 1 ảnh đầu tiên
    generate_category: true
  })
});

// Ví dụ 2: Nhiều ảnh (nếu cần quality cao)
const response = await fetch('/api/generate/from-images', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_urls: [imageUrl1, imageUrl2, imageUrl3],
    generate_category: true
  })
});

// Ví dụ 3: Refine existing content
const response = await fetch('/api/generate/from-images', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_urls: [imageUrl],
    existing_title: "iphone 15",  // User đã gõ sơ sơ
    existing_description: "máy đẹp",
    generate_category: true
  })
});
```

### Example Response
```json
{
  "status": "ok",
  "generated": {
    "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên",
    "description": "Mình bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. Máy còn đẹp như mới, fullbox đầy đủ phụ kiện. Ae quan tâm liên hệ nhé!",
    "detected_attributes": {
      "brand": "Apple",
      "model": "iPhone 15 Pro Max",
      "color": "Titan Tự Nhiên",
      "condition": "như mới"
    },
    "price_suggestion": {
      "estimate": 28000000,
      "range": [26000000, 30000000],
      "reasoning": "Dựa vào model máy và tình trạng như mới"
    },
    "category_suggestion": {
      "category_id": 123,
      "category_name": "iPhone",
      "category_path": "Điện tử > Điện thoại > iPhone",
      "confidence": 0.92
    }
  }
}
```

---

## � Chức năng 3: Generate từ Text

Từ tiêu đề + mô tả → đề xuất danh mục + thuộc tính (không cần ảnh).

### Endpoint
```
POST /api/generate/from-text
```

### Request Body
```typescript
interface GenerateFromTextRequest {
  title?: string;       // max 500 chars
  description?: string; // max 5000 chars
  price?: number;       // optional, >= 0
}
```

### Example
```javascript
const result = await fetch('/api/generate/from-text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'iphone 15 pro max 256g',
    description: 'máy đẹp 99% sxdh',
    price: 28000000
  })
}).then(r => r.json());
```

---

## 🔄 Chức năng 4: Generate Full (Ảnh + Text)

Kết hợp ảnh + text có sẵn → phân tích đầy đủ nhất.

### Endpoint
```
POST /api/generate/full
```

### Request Body
```typescript
interface GenerateFullRequest {
  image_urls: string[];  // Required, 1-5 URLs
  title?: string;        // max 500 chars
  description?: string;  // max 5000 chars
  price?: number;
}
```

---

## �🔍 Chức năng phụ: Validate Consistency

### Endpoint
```
POST /api/generate/validate-consistency
```

### Request Body
```typescript
interface ValidateRequest {
  title: string;
  description?: string;
  image_urls: string[];  // 1-5 URLs
}
```

### Response
```typescript
interface ValidateResponse {
  is_consistent: boolean;
  confidence: number;
  issues: string[];      // Lỗi nghiêm trọng
  warnings: string[];    // Cảnh báo nhỏ
}
```

### Example
```javascript
const response = await fetch('/api/generate/validate-consistency', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "iPhone 15 Pro Max",
    description: "Máy mới nguyên seal",
    image_urls: ["https://storage.example.com/samsung.jpg"]
  })
});

// Response
{
  "is_consistent": false,
  "confidence": 0.95,
  "issues": ["Tiêu đề nói iPhone nhưng ảnh là Samsung Galaxy"],
  "warnings": []
}
```

---

## 🎨 Frontend Workflows

### Workflow 1: User tự viết → Auto-categorize
```
1. User nhập title + description
2. [Optional] User upload ảnh
3. User click "Đăng bài" hoặc "Chọn danh mục tự động"
   ↓
4. Frontend gọi POST /api/classify
   ↓
5. Nhận response với decision:
   - auto_assign → Tự động chọn, hiện badge "Đã chọn tự động"
   - preselect → Pre-fill category, cho user confirm
   - suggest_top3 → Show 3 options, user chọn
   - manual_select → Yêu cầu user chọn thủ công
```

### Workflow 2: User chỉ upload ảnh → Auto-generate all
```
1. User upload 1 ảnh (hoặc nhiều ảnh, nhưng khuyến nghị chỉ gửi ảnh đầu)
2. User click "Tạo tin tự động" hoặc drag & drop ảnh
   ↓
3. Frontend upload ảnh lên storage → get URL
   ↓
4. Frontend gọi POST /api/generate/from-images
   {
     image_urls: [firstImageUrl],  // CHỈ ảnh đầu
     generate_category: true
   }
   ↓
5. Nhận response, auto-fill form:
   - title → input title
   - description → textarea description
   - price_suggestion.estimate → input price
   - category_suggestion → select category
   ↓
6. Show notification: "Đã tạo nội dung tự động, vui lòng kiểm tra"
7. User review & adjust nếu cần
8. User click "Đăng bài"
```

### Workflow 3: Hybrid - Generate từ ảnh + Refine
```
1. User upload ảnh
2. System generate basic content
   ↓
3. User sửa một chút (thêm giá, chi tiết)
   ↓
4. User click "Chọn danh mục tự động"
   ↓
5. Frontend gọi POST /api/classify với:
   {
     title: userEditedTitle,
     description: userEditedDescription,
     image_urls: [firstImageUrl]
   }
   ↓
6. System classify với cả text + image
```

---

## ⚡ Performance Tips

### 1. Chỉ gửi ảnh đầu tiên (KHUYẾN NGHỊ)
```javascript
// ❌ Chậm: Gửi tất cả ảnh
const allImages = [img1, img2, img3, img4, img5];
await generateFromImages(allImages);  // ~8-10 giây

// ✅ Nhanh: Chỉ gửi ảnh đầu
const firstImage = [img1];
await generateFromImages(firstImage);  // ~2-3 giây
```

### 2. Progressive Loading
```javascript
// Show skeleton/loading ngay
showLoadingSkeleton();

// Generate từ 1 ảnh đầu (nhanh)
const quickResult = await fetch('/api/generate/from-images', {
  body: JSON.stringify({ 
    image_urls: [images[0]], // Chỉ ảnh đầu
    generate_category: true 
  })
});

// Fill form ngay với quick result
fillForm(quickResult.generated);

// [Optional] Enhance với nhiều ảnh hơn (background)
if (images.length > 1) {
  enhanceInBackground(images);
}
```

### 3. Fast Mode cho classify
```javascript
// Normal mode: ~2-3 giây (có LLM understand)
await classify({ title, description, fast: false });

// Fast mode: ~0.5-1 giây (bỏ qua understand)
await classify({ title, description, fast: true });

// Dùng fast mode khi:
// - User đang typing (live preview)
// - Batch processing nhiều items
// - Mobile/slow connection
```

### 4. Caching
```javascript
// Cache generated content theo image hash
const imageHash = await hashImage(imageBlob);
const cached = localStorage.getItem(`generated_${imageHash}`);

if (cached) {
  return JSON.parse(cached);  // Instant!
} else {
  const result = await generateFromImages([imageUrl]);
  localStorage.setItem(`generated_${imageHash}`, JSON.stringify(result));
  return result;
}
```

---

## 🎯 UI/UX Recommendations

### 1. Auto-Categorize Button
```html
<!-- Trong form đăng bài -->
<button onclick="autoClassify()">
  🤖 Chọn danh mục tự động
</button>
```

### 2. Generate từ Ảnh
```html
<!-- Option A: Upload button -->
<input type="file" id="image" accept="image/*" onchange="autoGenerate()">
<button>📷 Tạo tin từ ảnh</button>

<!-- Option B: Drag & Drop -->
<div class="drop-zone" ondrop="handleDrop(event)">
  Kéo thả ảnh vào đây để tạo tin tự động
</div>
```

### 3. Decision Badge
```javascript
// Show badge theo decision type
const badges = {
  auto_assign: '✅ Đã chọn tự động',
  preselect: '💡 Gợi ý cho bạn',
  suggest_top3: '🤔 Chọn 1 trong 3',
  manual_select: '✋ Vui lòng chọn thủ công'
};
```

### 4. Loading States
```javascript
// Classify loading
showLoading('Đang phân tích bài đăng...');

// Generate loading
showLoading('Đang tạo nội dung từ ảnh...');
// Sub-steps:
// "Đang nhận diện sản phẩm..."
// "Đang tạo tiêu đề..."
// "Đang gợi ý danh mục..."
```

### 5. Confidence Indicator
```javascript
// Show confidence level to user
function getConfidenceLabel(confidence) {
  if (confidence >= 0.9) return '✅ Rất chắc chắn';
  if (confidence >= 0.75) return '👍 Khá chắc chắn';
  if (confidence >= 0.55) return '🤔 Không chắc lắm';
  return '❓ Cần kiểm tra lại';
}
```

---

## 🐛 Error Handling

### Status Codes
- `200` - Success
- `400` - Bad request (missing fields, invalid format)
- `404` - Not found
- `500` - Server error

### Example Error Response
```json
{
  "detail": "Invalid image URL or image not accessible"
}
```

### Frontend Handling
```javascript
try {
  const response = await fetch('/api/classify', {
    method: 'POST',
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const error = await response.json();
    showError(error.detail || 'Có lỗi xảy ra');
    return;
  }
  
  const result = await response.json();
  // Handle success
  
} catch (error) {
  showError('Không thể kết nối đến server');
}
```

---

## 📱 Mobile Optimization

### 1. Compress ảnh trước khi upload
```javascript
async function compressImage(file) {
  // Resize to max 1024px width
  // Quality: 80%
  return compressedBlob;
}
```

### 2. Chỉ dùng 1 ảnh đầu trên mobile
```javascript
if (isMobile) {
  // Chỉ cho upload 1 ảnh
  imageInput.multiple = false;
  // Luôn dùng fast mode
  classifyOptions.fast = true;
}
```

---

## 🧪 Testing Examples

### Test Data

**Test Case 1: Điện thoại cũ**
```json
{
  "title": "đt iphone 15 pro max 256g zin 99%",
  "description": "máy đẹp sxdh fullbox bh 8 tháng fix 28tr"
}
```
Expected: Category "iPhone", confidence >0.8

**Test Case 2: Laptop**
```json
{
  "title": "laptop dell i5 ram 8g",
  "description": "máy còn tốt giá sv"
}
```
Expected: Category "Laptop", confidence >0.75

**Test Case 3: Xe máy**
```json
{
  "title": "sh 150 đời 2020 bstp",
  "description": "xe đẹp máy zin"
}
```
Expected: Category "Xe máy > Honda SH"

---

## 💡 Best Practices

### DO ✅
- Chỉ gửi ảnh đầu tiên cho generate (trừ khi cần quality cao)
- Validate input trước khi gọi API
- Show loading state cho user
- Cache results khi có thể
- Handle errors gracefully
- Show confidence level cho user quyết định

### DON'T ❌
- Không gửi 5 ảnh cùng lúc cho mọi request (chậm)
- Không gọi API liên tục khi user đang typing
- Không trust 100% vào auto-categorize confidence thấp (<0.55)
- Không skip user confirmation cho decision = suggest_top3 hoặc manual_select

---

## 📞 Support

**API Documentation:** http://your-domain.com/docs (FastAPI auto-generated)  
**Health Check:** `GET /api/health`  
**Version:** 1.0.0

**Questions?**
- Check examples trong file này
- Test với curl commands
- Xem logs: `docker-compose logs api`
