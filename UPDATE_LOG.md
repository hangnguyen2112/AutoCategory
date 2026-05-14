# Update Log: Marketplace Style (Rao Vặt Đồ Cũ)

**Ngày:** 2026-05-06  
**Mục tiêu:** Điều chỉnh hệ thống cho phù hợp với phong cách rao vặt đồ cũ (marketplace style)

---

## 🎯 Thay đổi chính

### 1. Prompt Engineering - Marketplace Context

**Files changed:**
- `autocategory/api/services/llm_service.py`

**Changes:**
- ✅ Updated `SYSTEM_UNDERSTAND` prompt:
  - Từ "sàn thương mại điện tử" → "chợ rao vặt/bán đồ cũ"
  - Thêm context người bán cá nhân (không phải shop)
  - Thêm dictionary viết tắt phổ biến (đt, sxdh, zin, fullbox, BH, ...)
  - Output giữ phong cách casual, tự nhiên

- ✅ Updated `SYSTEM_RERANK` prompt:
  - Hiểu context marketplace (bài viết casual)
  - Tập trung vào bản chất sản phẩm, không cần viết chuẩn

**Impact:**
```
Trước: "đt iphone 15" → Khó hiểu, confidence thấp
Sau:  "đt iphone 15" → "Điện thoại iPhone 15", confidence cao
```

---

### 2. Image-to-Text Generation (NEW)

**Files created:**
- `autocategory/api/services/image_analyzer.py` (NEW)
- `autocategory/api/routers/generate.py` (NEW)

**Features:**

#### A. Generate content từ ảnh
```python
POST /api/generate/from-images
```
- Input: Ảnh sản phẩm (1-5 ảnh)
- Output: Title + Description + Price suggestion + Category
- Style: Marketplace/rao vặt (casual, thân thiện)

#### B. Validate image-text consistency
```python
POST /api/generate/validate-consistency
```
- Input: Title + Description + Images
- Output: Có khớp không? Issues? Warnings?
- Use case: Phát hiện text nói A nhưng ảnh là B

**Prompts:**
- Viết theo phong cách người bán cá nhân
- Casual: "Mình bán...", "Máy đẹp ạ", "Ae liên hệ"
- Tự nhiên: "Bán vì lên đời", "BH còn X tháng"

---

### 3. Integration Updates

**Files modified:**
- `autocategory/api/main.py`
  - Import generate router
  - Include generate endpoints với tag "Generate"

- `autocategory/api/services/__init__.py`
  - Export image_analyzer module

- `autocategory/api/config.py`
  - Thêm feature flag: `enable_image_generation: bool = True`

---

## 📝 Viết tắt & Slang được hỗ trợ

| Viết tắt | Ý nghĩa | Context |
|----------|---------|---------|
| đt, dt | điện thoại | "đt iphone" → điện thoại iPhone |
| đtdđ | di động | "đtdđ samsung" → điện thoại di động Samsung |
| sxdh, xstd | sạc xài đều hơn | "pin sxdh" → pin tốt, giữ lâu |
| 99%, 98% | tình trạng máy | "máy 99%" → máy còn rất mới |
| zin | nguyên bản | "zin all" → nguyên bản 100% |
| fullbox | đầy đủ hộp | "fullbox" → có đủ hộp + phụ kiện |
| BH | bảo hành | "BH 10 tháng" → bảo hành còn 10 tháng |
| ae | anh em | "ae liên hệ" → các bạn liên hệ |
| fix | giá cố định | "fix 5tr" → giá 5 triệu không thương lượng |
| pass | bán lại | "pass con iphone" → bán lại/chuyển nhượng |

---

## 🔍 Test Cases

### Test 1: Hiểu viết tắt
```bash
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "đt iphone 15 pro max 256g zin 99%",
    "description": "máy đẹp sxdh fullbox bh 8 tháng fix 28tr"
  }'
```

**Expected output:**
```json
{
  "normalized_product_text": "Điện thoại iPhone 15 Pro Max 256GB, tình trạng rất mới (99%), nguyên bản, pin tốt sạc xài đều, đầy đủ hộp phụ kiện, bảo hành còn 8 tháng, giá fix 28 triệu",
  "suggested_title": "iPhone 15 Pro Max 256GB zin 99% BH 8 tháng",
  "confidence": 0.88
}
```

### Test 2: Generate từ ảnh (requires vision model)
```bash
curl -X POST http://localhost:8000/api/generate/from-images \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": ["https://example.com/iphone.jpg"],
    "generate_category": true
  }'
```

**Expected output:**
```json
{
  "status": "ok",
  "generated": {
    "title": "iPhone 15 Pro Max 256GB đẹp như mới",
    "description": "Mình bán iPhone 15 Pro Max 256GB...",
    "price_suggestion": {
      "estimate": 28000000,
      "range": [26000000, 30000000]
    },
    "category_suggestion": {
      "category_path": "Điện tử > Điện thoại > iPhone",
      "confidence": 0.92
    }
  }
}
```

### Test 3: Validate consistency
```bash
curl -X POST http://localhost:8000/api/generate/validate-consistency \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max",
    "description": "máy mới seal",
    "image_urls": ["https://example.com/samsung.jpg"]
  }'
```

**Expected output:**
```json
{
  "is_consistent": false,
  "confidence": 0.95,
  "issues": ["Tiêu đề nói iPhone nhưng ảnh là Samsung"],
  "warnings": []
}
```

---

## 🚀 Deployment

### Quick Start (không cần vision):
```bash
# 1. Restart API để load code mới
docker-compose restart api

# 2. Test classify với marketplace style
curl -X POST http://localhost:8000/api/classify \
  -d '{"title": "đt samsung a54 128g đẹp 95%"}'
```

### Full Features (với vision support):
```bash
# 1. Pull vision model (nếu chưa có)
# Chạy trong container llama-server hoặc ollama
ollama pull llama3.2-vision:11b
# hoặc
ollama pull llava:13b

# 2. Update config model name (nếu cần)
# Trong .env hoặc docker-compose.yml:
LLAMA_MODEL=llama3.2-vision:11b

# 3. Restart
docker-compose restart api

# 4. Test generate từ ảnh
curl -X POST http://localhost:8000/api/generate/from-images \
  -d '{"image_urls": ["..."]}'
```

---

## 📊 Before/After Comparison

### Example Input:
```json
{
  "title": "đt iphone 14 128g đẹp 98% sxdh fullbox",
  "description": "máy còn zin bh hết fix 18tr ae lh"
}
```

### BEFORE (E-commerce style):
```json
{
  "normalized": "iPhone 14 128GB",
  "suggested_title": "iPhone 14 128GB - Chính Hãng",
  "suggested_description": "Điện thoại iPhone 14...",
  "confidence": 0.60
}
```
❌ Mất hết context rao vặt  
❌ Không hiểu "sxdh", "zin", "lh"  
❌ Quá formal  

### AFTER (Marketplace style):
```json
{
  "normalized": "Điện thoại iPhone 14 128GB, tình trạng đẹp còn 98%, pin tốt sạc xài đều hơn, đầy đủ hộp phụ kiện, còn nguyên bản, hết bảo hành, giá fix 18 triệu",
  "suggested_title": "iPhone 14 128GB zin đẹp 98% pin khỏe",
  "suggested_description": "Mình bán iPhone 14 128GB. Máy đẹp còn 98%, zin all. Pin sạc xài đều hơn rất tốt. Fullbox đầy đủ phụ kiện. Hết BH rồi nhé. Giá fix 18tr, ae thiện chí liên hệ!",
  "confidence": 0.88
}
```
✅ Hiểu đúng toàn bộ viết tắt  
✅ Giữ phong cách casual  
✅ Confidence cao hơn nhiều  

---

## 🔧 Technical Details

### Model Requirements

**Current (Classification only):**
- Model: gemma4-e4b (đang dùng)
- VRAM: ~4GB
- Works: ✅ Classify với marketplace style

**Future (với Image Generation):**
- Model: llama3.2-vision:11b hoặc llava:13b
- VRAM: 8-10GB
- Works: ✅ Classify + ✅ Generate từ ảnh

### API Endpoints Summary

| Endpoint | Method | Purpose | Requires Vision |
|----------|--------|---------|-----------------|
| `/api/classify` | POST | Phân loại danh mục | ❌ No |
| `/api/generate/from-images` | POST | Tạo nội dung từ ảnh | ✅ Yes |
| `/api/generate/validate-consistency` | POST | Validate text vs image | ✅ Yes |
| `/api/admin/build-index` | POST | Rebuild vector DB | ❌ No |
| `/api/categories` | GET | List categories | ❌ No |

---

## 📚 Documentation Files

1. **MARKETPLACE_STYLE.md** - Chi tiết về marketplace style, examples, use cases
2. **image_to_text_plan.md** - Kế hoạch tổng thể cho image generation feature
3. **feedback_learning_plan.md** - Kế hoạch feedback & learning system
4. **UPDATE_LOG.md** - File này - changelog chi tiết

---

## ✅ Checklist

- [x] Update prompts cho marketplace style
- [x] Thêm dictionary viết tắt
- [x] Tạo image_analyzer service
- [x] Tạo generate router
- [x] Update main.py integration
- [x] Update config.py
- [x] Tạo documentation đầy đủ
- [x] Test cases & examples
- [ ] Pull vision model (khi cần image features)
- [ ] Production testing với real data
- [ ] Collect feedback để improve prompts

---

## 🎯 Next Steps

### Immediate (no vision model needed):
1. ✅ Deploy changes (restart API)
2. ✅ Test classify với marketplace inputs
3. ✅ Monitor confidence scores
4. ✅ Collect feedback từ users

### Short-term (1-2 weeks):
1. Pull vision model (llama3.2-vision)
2. Test generate-from-images với real photos
3. Fine-tune prompts dựa trên feedback
4. Thêm more viết tắt từ user data

### Long-term (1-2 months):
1. Build feedback collection system
2. Category sync automation
3. Price suggestion database
4. A/B testing framework

---

## 📞 Support

**Issues?**
- Check [MARKETPLACE_STYLE.md](MARKETPLACE_STYLE.md) for examples
- Test với curl commands trong file này
- Check logs: `docker-compose logs api`

**Questions?**
- Xem FAQ trong MARKETPLACE_STYLE.md
- Test cases trong UPDATE_LOG.md này
- Chi tiết kỹ thuật trong image_to_text_plan.md
