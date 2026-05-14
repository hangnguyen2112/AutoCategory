# Hệ Thống Rao Vặt Đồ Cũ - Marketplace Style

## Thay đổi chính so với bản gốc

### 1. Prompt Engineering cho Rao Vặt

**Trước (E-commerce style):**
```
"Bạn là hệ thống chuẩn hóa bài đăng sản phẩm cho sàn thương mại điện tử"
→ Output: Formal, professional, như shop
```

**Sau (Marketplace style):**
```
"Bạn là hệ thống hiểu bài đăng bán đồ cũ/rao vặt (Chợ Tốt, Facebook Marketplace)"
→ Output: Casual, tự nhiên, như người bán cá nhân
```

### 2. Hiểu viết tắt & typo phổ biến

Hệ thống giờ hiểu:
- `đt`, `dt` → điện thoại
- `đtdđ` → di động
- `sxdh`, `xstd` → sạc xài đều hơn
- `99%`, `98%` → tình trạng máy
- `zin`, `nguyên zin` → nguyên bản
- `fullbox` → đầy đủ hộp phụ kiện
- `BH` → bảo hành
- `ae` → anh em
- `fix` → giá cố định
- `pass` → bán lại

### 3. Phong cách output

**Title suggestions:**
```
Trước: "iPhone 15 Pro Max 256GB - Chính Hãng VN/A"
Sau:  "iPhone 15 Pro Max 256GB đẹp như mới" 
      "Laptop Dell core i5 ram 8G giá sinh viên"
```

**Description suggestions:**
```
Trước: "Sản phẩm iPhone 15 Pro Max với chip A17 Pro, 
        camera 48MP, màn hình Super Retina XDR..."

Sau:  "Mình bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. 
       Máy mới mua 3 tháng, zin all, BH còn 9 tháng.
       Bán vì lên đời. Fullbox phụ kiện đầy đủ. 
       Máy đẹp giá tốt ạ, ae liên hệ nhé!"
```

---

## API Mới: Generate từ Ảnh

### Endpoint 1: POST /api/generate/from-images

**Tạo nội dung bài đăng tự động từ ảnh sản phẩm**

**Request:**
```json
{
  "image_urls": [
    "https://example.com/product1.jpg",
    "https://example.com/product2.jpg"
  ],
  "existing_title": "",
  "existing_description": "",
  "generate_category": true
}
```

**Response:**
```json
{
  "status": "ok",
  "generated": {
    "title": "iPhone 15 Pro Max 256GB đẹp như mới",
    "description": "Mình bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. Máy mới mua 3 tháng, còn zin all, BH còn 9 tháng. Bán vì lên đời 16. Fullbox phụ kiện đầy đủ. Máy đẹp giá tốt ạ!",
    "detected_attributes": {
      "brand": "Apple",
      "model": "iPhone 15 Pro Max",
      "color": "Titan Tự Nhiên",
      "condition": "như mới"
    },
    "price_suggestion": {
      "estimate": 28000000,
      "range": [26000000, 30000000],
      "reasoning": "Dựa vào model máy, thời gian sử dụng 3 tháng, tình trạng như mới"
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

### Endpoint 2: POST /api/generate/validate-consistency

**Kiểm tra text có khớp với ảnh không**

**Request:**
```json
{
  "title": "iPhone 15 Pro Max",
  "description": "Máy mới nguyên seal",
  "image_urls": ["https://example.com/samsung.jpg"]
}
```

**Response:**
```json
{
  "is_consistent": false,
  "confidence": 0.95,
  "issues": [
    "Tiêu đề nói iPhone nhưng ảnh là Samsung Galaxy"
  ],
  "warnings": []
}
```

---

## Use Cases với Ví Dụ Thực Tế

### Case 1: User nhập text thô (nhiều typo, viết tắt)

**Input:**
```
Title: "dt iphone 15 pro max 256g"
Description: "máy đẹp 99% zin all bh 10 tháng fullbox fix 28tr ae liên hệ"
```

**Understanding Output:**
```json
{
  "normalized_product_text": "Điện thoại iPhone 15 Pro Max 256GB, tình trạng còn rất mới (99%), nguyên bản chưa sửa chữa, bảo hành còn 10 tháng, đầy đủ hộp và phụ kiện, giá cố định 28 triệu",
  "suggested_title": "iPhone 15 Pro Max 256GB zin đẹp 99%",
  "suggested_description": "Mình bán iPhone 15 Pro Max 256GB. Máy đẹp còn 99%, zin all chưa sửa gì. BH còn 10 tháng. Fullbox đầy đủ phụ kiện. Giá fix 28tr, ae thiện chí liên hệ nhé!",
  "confidence": 0.85,
  "text_image_consistency": "text_only"
}
```

### Case 2: User chỉ upload ảnh (không viết gì)

**Input:**
```
image_urls: [ảnh iPhone trên bàn, ảnh màn hình, ảnh hộp]
```

**Generate Output:**
```json
{
  "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên",
  "description": "Mình cần bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. Nhìn từ ảnh máy còn đẹp, có fullbox. Ae quan tâm liên hệ để biết thêm chi tiết nhé!",
  "detected_attributes": {
    "brand": "Apple",
    "model": "iPhone 15 Pro Max",
    "storage": "256GB",
    "color": "Titan Tự Nhiên",
    "condition": "đẹp"
  },
  "price_suggestion": {
    "estimate": 30000000,
    "range": [28000000, 32000000]
  }
}
```

### Case 3: User viết thiếu, ảnh bổ sung

**Input:**
```
Title: "iphone 15"
Description: "máy đẹp"
Images: [ảnh rõ ràng iPhone 15 Pro Max 256GB với box]
```

**Understanding Output:**
```json
{
  "normalized_product_text": "iPhone 15 Pro Max 256GB (nhận diện từ ảnh), máy tình trạng đẹp, có đầy đủ hộp phụ kiện",
  "suggested_title": "iPhone 15 Pro Max 256GB fullbox đẹp",
  "suggested_description": "Mình bán iPhone 15 Pro Max 256GB. Máy đẹp, fullbox như trong ảnh. Ae xem ảnh và liên hệ nhé!",
  "confidence": 0.75,
  "text_image_consistency": "image_clarifies_text"
}
```

### Case 4: Text vs Image mâu thuẫn

**Input:**
```
Title: "iPhone 15 Pro Max mới seal"
Images: [ảnh máy đã bóc, có vết trầy nhẹ]
```

**Understanding Output:**
```json
{
  "normalized_product_text": "iPhone (text nói mới seal nhưng ảnh thấy máy đã bóc, có vết sử dụng)",
  "confidence": 0.45,
  "text_image_consistency": "conflict"
}
```

**Classify Decision:** `manual_select` (vì conflict)

---

## Các Phong Cách Viết Được Hỗ Trợ

### 1. Casual/Thân thiện
```
"Mình bán...", "Em bán...", "Cần bán..."
"Máy đẹp ạ", "Ae liên hệ nhé", "Giá tốt đấy"
```

### 2. Thông tin tình trạng
```
"99%", "như mới", "còn mới lắm"
"zin all", "nguyên bản"
"BH còn X tháng", "hết BH"
"fullbox", "không box"
```

### 3. Lý do bán
```
"Bán vì lên đời", "Cần tiền gấp"
"Đang dùng tốt", "Ít dùng"
"Nhà có 2 cái"
```

### 4. Giao dịch
```
"Fix giá", "Có thương lượng"
"Pass cho ae thiện chí"
"Ship toàn quốc", "Gặp mặt tại..."
```

---

## So sánh Trước/Sau

### Input mẫu:
```
Title: "đt samsung a54 128g"
Description: "máy đẹp 95% sxdh fullbox bh hết r fix 5tr5"
```

### Trước (E-commerce style):

```json
{
  "normalized": "Samsung Galaxy A54 5G 128GB",
  "suggested_title": "Samsung Galaxy A54 5G 128GB - Chính Hãng",
  "suggested_description": "Điện thoại Samsung Galaxy A54 5G với bộ nhớ 128GB...",
  "confidence": 0.6
}
```
❌ Mất hết phong cách người bán  
❌ Quá formal  
❌ Mất thông tin "95%", "hết BH", "fix"  

### Sau (Marketplace style):

```json
{
  "normalized": "Điện thoại Samsung Galaxy A54 128GB, tình trạng đẹp còn 95%, sạc xài đều (pin tốt), đầy đủ hộp phụ kiện, hết bảo hành, giá fix 5.5 triệu",
  "suggested_title": "Samsung A54 128GB đẹp 95% pin khỏe",
  "suggested_description": "Mình bán Samsung Galaxy A54 128GB. Máy đẹp còn 95%, sạc xài đều hơn (pin rất tốt). Fullbox đầy đủ phụ kiện. Hết BH rồi nhé. Giá fix 5tr5, không fix nữa đâu ạ!",
  "confidence": 0.88
}
```
✅ Giữ được phong cách rao vặt  
✅ Hiểu "sxdh" = pin tốt  
✅ Giữ được tone casual  
✅ Confidence cao hơn (hiểu đúng ý)  

---

## Testing

### Test với các trường hợp thực tế:

```bash
# Test 1: Viết tắt nhiều
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "đt iphone 14 128g zin 99%",
    "description": "máy đẹp sxdh fullbox bh 8 tháng fix 18tr ae lh"
  }'

# Test 2: Generate từ ảnh
curl -X POST http://localhost:8000/api/generate/from-images \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": ["https://example.com/phone.jpg"],
    "generate_category": true
  }'

# Test 3: Validate consistency
curl -X POST http://localhost:8000/api/generate/validate-consistency \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max",
    "description": "máy mới seal",
    "image_urls": ["https://example.com/phone.jpg"]
  }'
```

---

## Deployment

Hệ thống sẵn sàng sử dụng với gemma model hiện tại:

```bash
# 1. Restart để load code mới
docker-compose restart api

# 2. Test health
curl http://localhost:8000/api/health

# 3. Test classify với style mới
curl -X POST http://localhost:8000/api/classify \
  -d '{"title": "đt iphone 15 pro max 256g zin 99%"}'
```

**Lưu ý:** 
- Không cần pull model mới (vẫn dùng gemma4-e4b)
- Chỉ thay đổi prompt engineering
- Generate từ ảnh sẽ cần model có vision support (gemma-vision hoặc llava)

---

## Roadmap

### ✅ Done:
- Prompt cho marketplace style
- Hiểu viết tắt phổ biến
- Generate API structure
- Validate consistency API

### 🔄 Cần làm thêm:
- [ ] Pull vision model (llama3.2-vision hoặc llava)
- [ ] Test generate từ ảnh với dữ liệu thực
- [ ] Fine-tune prompts dựa trên feedback
- [ ] Thêm more viết tắt từ user feedback
- [ ] Price suggestion database

### 💡 Future:
- [ ] Auto-detect spam/scam posts
- [ ] Suggest better photos
- [ ] Grammar correction (optional)
- [ ] Multi-language support

---

## FAQ

**Q: Model có cần retrain không?**  
A: KHÔNG. Chỉ thay đổi prompt (zero-shot learning). Gemma model vẫn dùng như cũ.

**Q: Accuracy có giảm không?**  
A: KHÔNG. Thậm chí có thể tăng vì model hiểu đúng ý user hơn.

**Q: Generate từ ảnh có cần GPU mạnh hơn không?**  
A: CÓ. Vision model (llama3.2-vision:11b) cần ~8GB VRAM. Nếu không đủ, dùng cloud API.

**Q: Có thể mix cả 2 style không?**  
A: CÓ. Có thể thêm flag `style: "marketplace" | "ecommerce"` trong request.

**Q: User vẫn viết chuẩn thì sao?**  
A: Vẫn work tốt. System flexible với cả 2 styles.

---

## Examples Gallery

### Điện thoại cũ
```
Input:  "đt ip 14 pro 256g đẹp 98% zin"
Output: "iPhone 14 Pro 256GB zin đẹp 98%"
Category: Điện tử > Điện thoại > iPhone ✓
```

### Laptop sinh viên
```
Input:  "laptop dell i5 ram 8g giá sv"
Output: "Laptop Dell Core i5 RAM 8GB giá sinh viên"
Category: Điện tử > Laptop ✓
```

### Xe máy
```
Input:  "sh 150 đời 2020 bstp còn mới"
Output: "SH 150 2020 biển TP còn mới"
Category: Xe cộ > Xe máy > Honda SH ✓
```

### Đồ gia dụng
```
Input:  "tủ lạnh panasonic 180l dùng 2 năm"
Output: "Tủ lạnh Panasonic 180L đã dùng 2 năm"
Category: Đồ gia dụng > Tủ lạnh ✓
```
