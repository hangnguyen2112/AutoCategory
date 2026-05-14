# Kế hoạch: Auto-Generate Product Content từ Ảnh

**Mục tiêu:** Tự động sinh tiêu đề, mô tả, và gợi ý giá từ ảnh sản phẩm khi user đăng bài

---

## Use Cases

### Scenario 1: User chỉ upload ảnh
```
Input:  📷 3 ảnh iPhone
Output: 
  ✅ Title: "iPhone 15 Pro Max 256GB Chính Hãng VN/A"
  ✅ Description: "Điện thoại iPhone 15 Pro Max, dung lượng 256GB, màu Titan Tự Nhiên. 
                   Máy nguyên seal chưa kích hoạt, fullbox phụ kiện đầy đủ."
  ✅ Suggested Price: 30,000,000 VND (range: 28M - 32M)
  ✅ Auto Category: Điện tử > Điện thoại > iPhone
```

### Scenario 2: User upload ảnh + nhập 1 ít thông tin
```
Input:  📷 Ảnh + "iPhone 15 Pro Max"
Output: Bổ sung description chi tiết, validate consistency với ảnh
```

### Scenario 3: Validate text vs image
```
Input:  "iPhone 15" + 📷 ảnh Samsung Galaxy
Output: ⚠️ Warning: "Ảnh không khớp với tiêu đề, vui lòng kiểm tra lại"
```

---

## Kiến trúc giải pháp

### Option 1: Ollama Multimodal Models (Khuyến nghị cho local)

**Models có sẵn:**
- `llama3.2-vision:11b` - Vision-language model từ Meta (balanced)
- `llama3.2-vision:90b` - Accuracy cao nhưng chậm
- `llava:13b` - Lightweight alternative
- `minicpm-v:8b` - Tốt cho tiếng Việt

**Ưu điểm:**
✅ Free, unlimited, privacy
✅ Chạy local như hiện tại
✅ Đã có infrastructure (Ollama đang chạy)
✅ Support multimodal trong llm_service.py

**Nhược điểm:**
⚠️ Cần VRAM cao (11B model ~ 8GB VRAM)
⚠️ Slower inference (~3-5s)
⚠️ Tiếng Việt kém hơn GPT-4V

### Option 2: Cloud Vision APIs (Hybrid approach)

**Services:**
- OpenAI GPT-4V / GPT-4O
- Google Gemini Pro Vision (free tier: 15 requests/min)
- Claude 3 with vision
- Cloudflare Workers AI (llama-3.2-vision free)

**Ưu điểm:**
✅ Accuracy cao
✅ Fast inference
✅ Tiếng Việt tốt (GPT-4V, Gemini)

**Nhược điểm:**
⚠️ Chi phí (GPT-4V: ~$0.01/image)
⚠️ Privacy concerns
⚠️ Rate limits

### Option 3: Hybrid - Best of both

```
Use Case                     | Model Choice
-----------------------------|------------------
Quick draft (user đang type) | Ollama llama3.2-vision (fast, free)
Final polish                 | GPT-4V or Gemini (quality)
Batch processing             | Ollama (cost effective)
Privacy-sensitive products   | Ollama only
```

---

## API Design

### Endpoint mới: POST /api/generate/from-images

```json
Request:
{
  "image_urls": [
    "https://storage.example.com/product1.jpg",
    "https://storage.example.com/product2.jpg"
  ],
  "existing_title": "",          // optional, để refine
  "existing_description": "",    // optional, để refine
  "generate_options": {
    "generate_title": true,
    "generate_description": true,
    "suggest_price": true,
    "suggest_category": true,
    "language": "vi"
  },
  "model": "auto"  // auto | local | cloud | hybrid
}

Response:
{
  "status": "ok",
  "generated": {
    "title": "iPhone 15 Pro Max 256GB Chính Hãng VN/A",
    "description": "Điện thoại iPhone 15 Pro Max...",
    "price_suggestion": {
      "estimate": 30000000,
      "range": [28000000, 32000000],
      "confidence": 0.75,
      "reasoning": "Dựa vào model máy, dung lượng, tình trạng nguyên seal"
    },
    "category_suggestion": {
      "category_id": 123,
      "category_path": "Điện tử > Điện thoại > iPhone",
      "confidence": 0.92
    },
    "detected_attributes": {
      "brand": "Apple",
      "model": "iPhone 15 Pro Max",
      "storage": "256GB",
      "color": "Titan Tự Nhiên",
      "condition": "Mới nguyên seal"
    }
  },
  "validation": {
    "image_quality": "good",
    "is_product_photo": true,
    "detected_objects": ["smartphone", "box", "accessories"]
  },
  "processing_time_ms": 3450,
  "model_used": "llama3.2-vision:11b"
}
```

### Endpoint: POST /api/generate/validate-consistency

Kiểm tra text vs images có khớp không:

```json
Request:
{
  "title": "iPhone 15 Pro Max",
  "description": "...",
  "image_urls": [...]
}

Response:
{
  "is_consistent": true,
  "confidence": 0.88,
  "issues": [],
  "warnings": [
    {
      "type": "minor_mismatch",
      "message": "Tiêu đề nói '256GB' nhưng ảnh không rõ dung lượng",
      "severity": "low"
    }
  ]
}
```

### Endpoint: POST /api/generate/enhance

Cải thiện text dựa trên images:

```json
Request:
{
  "current_title": "iphone 15",
  "current_description": "máy đẹp",
  "image_urls": [...]
}

Response:
{
  "enhanced_title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên",
  "enhanced_description": "Điện thoại iPhone 15 Pro Max với chip A17 Pro...",
  "changes": [
    "Thêm thông tin dung lượng từ ảnh",
    "Thêm màu sắc",
    "Mở rộng mô tả chi tiết"
  ]
}
```

---

## Implementation với Ollama

### 1. Pull multimodal model

```bash
# Chọn 1 trong các models:
ollama pull llama3.2-vision:11b    # Khuyến nghị
# hoặc
ollama pull llava:13b              # Lightweight
# hoặc  
ollama pull minicpm-v:8b           # Tốt cho tiếng Việt
```

### 2. Service mới: image_analyzer.py

```python
"""
Image Analyzer Service – Generate content từ product images
"""
import logging
from typing import Any
import httpx
from config import settings

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(
    base_url=settings.ollama_base_url, 
    timeout=180.0
)

async def generate_from_images(
    image_urls: list[str],
    existing_title: str = "",
    existing_description: str = "",
    language: str = "vi"
) -> dict[str, Any]:
    """
    Sinh title, description từ ảnh sản phẩm
    """
    
    # Build prompt
    system_prompt = """Bạn là chuyên gia viết nội dung bài đăng bán hàng.
Nhiệm vụ: Phân tích ảnh sản phẩm và tạo tiêu đề + mô tả hấp dẫn bằng tiếng Việt.

YÊU CẦU:
1. Tiêu đề: Ngắn gọn, có thông tin chính (tên, model, đặc điểm nổi bật)
2. Mô tả: Chi tiết về sản phẩm, tình trạng, phụ kiện kèm theo
3. Phát hiện: Brand, model, màu sắc, tình trạng (mới/cũ)
4. Gợi ý giá: Dựa vào sản phẩm và tình trạng (nếu nhận diện được)

FORMAT JSON:
{
  "title": "...",
  "description": "...",
  "detected_attributes": {
    "brand": "...",
    "model": "...",
    "color": "...",
    "condition": "mới/cũ/like new"
  },
  "price_suggestion": {
    "estimate": 10000000,
    "range": [9000000, 11000000],
    "reasoning": "..."
  }
}"""

    user_prompt = "Phân tích ảnh sản phẩm này và tạo nội dung bài đăng:"
    
    if existing_title:
        user_prompt += f"\nTiêu đề hiện tại: {existing_title}"
    if existing_description:
        user_prompt += f"\nMô tả hiện tại: {existing_description}"
    
    # Build multipart content
    content = [{"type": "text", "text": user_prompt}]
    for url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {"url": url}
        })
    
    # Call Ollama
    payload = {
        "model": settings.vision_model,  # llama3.2-vision:11b
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "stream": False,
        "format": "json"
    }
    
    resp = await _client.post("/v1/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    
    # Parse response
    result_text = data["choices"][0]["message"]["content"]
    result = json.loads(result_text)
    
    return result


async def validate_image_text_consistency(
    title: str,
    description: str,
    image_urls: list[str]
) -> dict[str, Any]:
    """
    Kiểm tra text có khớp với ảnh không
    """
    system_prompt = """Bạn là trợ lý kiểm tra tính nhất quán.
So sánh nội dung text với ảnh sản phẩm, phát hiện mâu thuẫn.

FORMAT JSON:
{
  "is_consistent": true/false,
  "confidence": 0.0-1.0,
  "issues": ["Tiêu đề nói iPhone nhưng ảnh là Samsung", ...],
  "warnings": ["Không rõ màu sắc trong ảnh", ...]
}"""

    user_prompt = f"""Tiêu đề: {title}
Mô tả: {description}

Ảnh sản phẩm có khớp với nội dung text không?"""

    content = [{"type": "text", "text": user_prompt}]
    for url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {"url": url}
        })
    
    payload = {
        "model": settings.vision_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "stream": False,
        "format": "json"
    }
    
    resp = await _client.post("/v1/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    
    result = json.loads(data["choices"][0]["message"]["content"])
    return result
```

### 3. Router mới: generate.py

```python
"""
Generate router: Auto-generate content from images
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services import image_analyzer, classifier

router = APIRouter()

class GenerateFromImagesRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=5)
    existing_title: str = Field(default="")
    existing_description: str = Field(default="")
    generate_category: bool = Field(default=True)

@router.post("/generate/from-images")
async def generate_from_images(req: GenerateFromImagesRequest):
    try:
        # Step 1: Generate content from images
        result = await image_analyzer.generate_from_images(
            image_urls=req.image_urls,
            existing_title=req.existing_title,
            existing_description=req.existing_description
        )
        
        # Step 2: Auto classify nếu yêu cầu
        if req.generate_category:
            category_result = await classifier.classify_product(
                title=result["title"],
                description=result["description"],
                price=result.get("price_suggestion", {}).get("estimate"),
                image_urls=req.image_urls,
                fast=False
            )
            result["category_suggestion"] = {
                "category_id": category_result["category_id"],
                "category_path": category_result["category_path"],
                "confidence": category_result["confidence"]
            }
        
        return {"status": "ok", "generated": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/validate-consistency")
async def validate_consistency(
    title: str,
    description: str,
    image_urls: list[str]
):
    try:
        result = await image_analyzer.validate_image_text_consistency(
            title, description, image_urls
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Update main.py

```python
from routers import admin, category, classify, generate  # NEW

app.include_router(generate.router, prefix="/api", tags=["Generate"])
```

### 5. Update config.py

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Vision model
    vision_model: str = Field(
        default="llama3.2-vision:11b",
        description="Ollama vision model for image analysis"
    )
    
    # Feature flags
    enable_image_generation: bool = Field(default=True)
    enable_cloud_vision: bool = Field(default=False)
    cloud_vision_api_key: str = Field(default="")
```

---

## Frontend Integration

### Update test page: frontend/index.html

```html
<!-- Thêm image upload section -->
<div class="card">
  <h3>📷 Auto-Generate từ Ảnh (Optional)</h3>
  
  <input type="file" id="imageFiles" multiple accept="image/*" max="5">
  <button onclick="uploadAndGenerate()">Upload & Generate</button>
  
  <div id="generatedContent" style="display: none;">
    <h4>Nội dung được tạo tự động:</h4>
    <div>
      <label>Tiêu đề:</label>
      <input id="generatedTitle" readonly>
      <button onclick="useGenerated('title')">✓ Dùng</button>
    </div>
    <div>
      <label>Mô tả:</label>
      <textarea id="generatedDescription" readonly></textarea>
      <button onclick="useGenerated('description')">✓ Dùng</button>
    </div>
    <div>
      <label>Giá gợi ý:</label>
      <span id="generatedPrice"></span>
    </div>
    <div>
      <label>Danh mục gợi ý:</label>
      <span id="generatedCategory"></span>
    </div>
  </div>
</div>

<script>
async function uploadAndGenerate() {
  const files = document.getElementById('imageFiles').files;
  if (!files.length) {
    alert('Chọn ít nhất 1 ảnh');
    return;
  }
  
  // Upload images first (to your storage)
  const imageUrls = await uploadImages(files);
  
  // Generate content
  const resp = await fetch('/api/generate/from-images', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      image_urls: imageUrls,
      generate_category: true
    })
  });
  
  const result = await resp.json();
  const gen = result.generated;
  
  // Show results
  document.getElementById('generatedTitle').value = gen.title;
  document.getElementById('generatedDescription').value = gen.description;
  document.getElementById('generatedPrice').textContent = 
    formatPrice(gen.price_suggestion.estimate) + 
    ` (${formatPrice(gen.price_suggestion.range[0])} - ${formatPrice(gen.price_suggestion.range[1])})`;
  document.getElementById('generatedCategory').textContent = 
    gen.category_suggestion.category_path;
  
  document.getElementById('generatedContent').style.display = 'block';
}

function useGenerated(field) {
  if (field === 'title') {
    document.getElementById('title').value = 
      document.getElementById('generatedTitle').value;
  } else if (field === 'description') {
    document.getElementById('description').value = 
      document.getElementById('generatedDescription').value;
  }
}
</script>
```

---

## Use Cases nâng cao

### 1. Smart Form Auto-Fill

```
User: [Drag & drop 3 ảnh iPhone]
      ↓
System: [Tự động điền]
  - Title: "iPhone 15 Pro Max 256GB..."
  - Description: "Điện thoại iPhone..."
  - Price: 30,000,000
  - Category: Auto-selected "Điện tử > Điện thoại > iPhone"
      ↓
User: Review & post hoặc sửa nếu cần
```

### 2. Quality Check trước khi đăng

```
User submit form
    ↓
System check:
  ✓ Title khớp với ảnh
  ✓ Description không mâu thuẫn với ảnh
  ⚠️ Warning: "Ảnh hơi mờ, có thể chụp lại rõ hơn?"
  ⚠️ Warning: "Thiếu ảnh tình trạng máy?"
    ↓
Cho phép đăng hoặc yêu cầu chỉnh sửa
```

### 3. Suggest Missing Info

```
Detected: ảnh có box + phụ kiện
Current description: "iPhone 15 Pro Max"

Suggestion: 💡 Thêm "Fullbox phụ kiện đầy đủ" vào mô tả?
```

### 4. Multi-language

```
Generate in Vietnamese: Default
Generate in English: For international listings
Both: Bilingual descriptions
```

---

## Performance Optimization

### 1. Caching

```python
# Cache generated content by image hash
image_hash = hashlib.md5(image_data).hexdigest()
cached = await redis.get(f"generated:{image_hash}")
if cached:
    return json.loads(cached)
```

### 2. Progressive Loading

```
Step 1: Quick draft (3s)  → Show immediately
Step 2: Enhance (5s more) → Update when ready
```

### 3. Batch Processing

```python
# Cho admin upload hàng loạt
async def batch_generate(image_batches: list[list[str]]):
    tasks = [generate_from_images(imgs) for imgs in image_batches]
    results = await asyncio.gather(*tasks)
    return results
```

---

## Metrics & Monitoring

```python
# Track usage
generate_requests = Counter("generate_from_images_total")
generate_success = Counter("generate_from_images_success_total")
generate_duration = Histogram("generate_from_images_seconds")

# Quality metrics
user_edit_rate = Gauge("generated_content_edit_rate")  # % user sửa
user_accept_rate = Gauge("generated_content_accept_rate")  # % dùng nguyên
```

---

## Pricing Estimation Database

Để gợi ý giá chính xác hơn, có thể:

### Option 1: Rule-based

```python
PRICE_RULES = {
    "iPhone 15 Pro Max 256GB": {"min": 28000000, "max": 32000000},
    "iPhone 15 Pro Max 512GB": {"min": 33000000, "max": 37000000},
    # ...
}

def estimate_price(brand, model, storage, condition):
    key = f"{brand} {model} {storage}"
    base = PRICE_RULES.get(key, {"min": 0, "max": 0})
    
    if condition == "mới":
        return base
    elif condition == "like new":
        return {"min": base["min"] * 0.8, "max": base["max"] * 0.9}
    elif condition == "cũ":
        return {"min": base["min"] * 0.6, "max": base["max"] * 0.7}
```

### Option 2: ML-based

Crawl giá từ các sàn thương mại điện tử, train model dự đoán giá:

```python
# Features: brand, model, storage, condition, color, age
price_prediction_model.predict([features])
```

### Option 3: Real-time market data

```python
async def get_market_price(product_name: str):
    # Query từ database giá thị trường cập nhật hàng ngày
    prices = await db.query(
        "SELECT AVG(price), MIN(price), MAX(price) "
        "FROM market_prices "
        "WHERE product_name LIKE ? AND listed_date > NOW() - INTERVAL 7 DAY",
        f"%{product_name}%"
    )
    return prices
```

---

## Security & Privacy

1. **Image validation:**
   - Check file type, size (<5MB)
   - Scan for malicious content
   - NSFW detection (không cho ảnh không phù hợp)

2. **Rate limiting:**
   - 20 generations/user/hour (free tier)
   - 100 generations/user/hour (premium)

3. **Privacy:**
   - Không lưu ảnh sau khi xử lý (hoặc xóa sau 24h)
   - Option: "Use local model only" cho privacy-sensitive items

---

## Cost Analysis

### Local (Ollama llama3.2-vision:11b)

**Hardware requirements:**
- VRAM: 8GB minimum (11B model)
- GPU: RTX 3070 or better
- Processing time: 3-5s per request

**Cost:** FREE (electricity only)

### Cloud (GPT-4V)

**Pricing:**
- $0.01 per image
- 1000 generations/day = $10/day = $300/month

**When to use:**
- High-value products (car, real estate)
- Quality over speed
- Mobile app (no GPU)

---

## Roadmap

### Phase 1: MVP (Week 1-2)
- [ ] Setup Ollama vision model
- [ ] Implement basic generate endpoint
- [ ] Simple frontend upload & display
- [ ] Test với 50 sản phẩm mẫu

### Phase 2: Enhanced (Week 3)
- [ ] Price suggestion với rule-based
- [ ] Category auto-suggestion integration
- [ ] Image-text consistency validation
- [ ] Better prompts cho tiếng Việt

### Phase 3: Production (Week 4)
- [ ] Caching & optimization
- [ ] Rate limiting
- [ ] Metrics & monitoring
- [ ] A/B test: với/không vision

### Phase 4: Advanced (Month 2)
- [ ] Hybrid cloud/local
- [ ] ML price prediction
- [ ] Batch processing
- [ ] Mobile app integration

---

## Integration với Category Classification

**Combined workflow:**

```
1. User upload ảnh
    ↓
2. Generate title + description + price
    ↓
3. Auto-classify category (dùng generated text + images)
    ↓
4. Show full form pre-filled
    ↓
5. User review & adjust
    ↓
6. Submit
    ↓
7. Save feedback (generated vs final) để improve model
```

---

## Expected Results

**Without vision:**
- User phải tự gõ title, description (2-5 phút)
- Thiếu thông tin chi tiết
- Typo, grammar errors

**With vision:**
- Auto-fill trong 5 giây
- Description đầy đủ, chuyên nghiệp
- Giảm 80% effort cho user
- Tăng chất lượng bài đăng → Tăng conversion

---

## Demo Script

```bash
# 1. Pull vision model
ollama pull llama3.2-vision:11b

# 2. Update .env
echo "VISION_MODEL=llama3.2-vision:11b" >> .env
echo "ENABLE_IMAGE_GENERATION=true" >> .env

# 3. Restart services
docker-compose restart api

# 4. Test
curl -X POST http://localhost:8000/api/generate/from-images \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": ["https://example.com/iphone.jpg"],
    "generate_category": true
  }'
```

---

## Tổng kết

✅ **Khả thi:** Hoàn toàn có thể làm với Ollama
✅ **Chi phí:** Free nếu dùng local, có GPU tốt
✅ **Timeline:** MVP trong 2 tuần
✅ **Impact:** Giảm 80% thời gian đăng bài cho user
✅ **Scalable:** Có thể hybrid cloud khi cần

**Bước tiếp theo:**
1. Quyết định dùng local hay cloud (hoặc hybrid)
2. Test Ollama vision model với sản phẩm thực tế
3. Implement MVP endpoint
4. Đánh giá quality trước khi rollout
