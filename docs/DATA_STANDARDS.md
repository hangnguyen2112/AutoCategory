# Data Standards & Validation Guide

**Version:** 1.0.0  
**Last Updated:** 2026-05-06

---

## 📋 Mục Lục

1. [Category Data Format](#category-data-format)
2. [Training Data Format](#training-data-format)
3. [Import/Export Formats](#importexport-formats)
4. [Validation Rules](#validation-rules)
5. [Data Quality Guidelines](#data-quality-guidelines)
6. [Common Errors & Solutions](#common-errors--solutions)

---

## 1. Category Data Format

### 1.1 Định dạng chuẩn (JSON)

```json
{
  "id": 123,
  "name": "iPhone",
  "parent_id": 120,
  "parent_name": "Điện thoại",
  "description": "Các sản phẩm iPhone của Apple",
  "is_active": 1,
  "level": 3,
  "metadata": {
    "icon": "📱",
    "keywords": ["iphone", "apple", "ios"],
    "aliases": ["ip", "ipon", "ái phôn"]
  }
}
```

### 1.2 Trường bắt buộc

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ | ID duy nhất của category |
| `name` | string | ✅ | Tên category (1-255 ký tự) |
| `parent_id` | integer/null | ⚠️ | ID category cha (null nếu là root) |
| `is_active` | 0 hoặc 1 | ✅ | Category có active không |

### 1.3 Trường tùy chọn

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `parent_name` | string | "" | Tên category cha (tự động generate) |
| `description` | string | "" | Mô tả chi tiết category |
| `level` | integer | auto | Level trong cây (0=root, 1=child...) |
| `metadata` | object | {} | Thông tin bổ sung (icon, keywords...) |

### 1.4 Ví dụ đầy đủ

```json
[
  {
    "id": 1,
    "name": "Điện tử",
    "parent_id": null,
    "parent_name": null,
    "description": "Các sản phẩm điện tử, công nghệ",
    "is_active": 1,
    "level": 0,
    "metadata": {
      "icon": "⚡",
      "keywords": ["electronics", "tech", "điện tử", "công nghệ"]
    }
  },
  {
    "id": 120,
    "name": "Điện thoại",
    "parent_id": 1,
    "parent_name": "Điện tử",
    "description": "Điện thoại di động, smartphone",
    "is_active": 1,
    "level": 1,
    "metadata": {
      "icon": "📱",
      "keywords": ["phone", "smartphone", "điện thoại", "đt", "đtdđ"],
      "aliases": ["dt", "đt", "đtdđ", "fone"]
    }
  },
  {
    "id": 123,
    "name": "iPhone",
    "parent_id": 120,
    "parent_name": "Điện thoại",
    "description": "Các sản phẩm iPhone của Apple. Bao gồm tất cả các dòng từ iPhone cũ đến mới nhất.",
    "is_active": 1,
    "level": 2,
    "metadata": {
      "icon": "🍎",
      "keywords": ["iphone", "apple", "ios"],
      "aliases": ["ip", "ipon", "ái phôn"],
      "common_mistakes": ["Thường bị nhầm với phụ kiện iPhone"],
      "related_categories": [124, 125]
    }
  }
]
```

---

## 2. Training Data Format

### 2.1 Định dạng chuẩn (JSONL - JSON Lines)

Mỗi dòng là 1 JSON object:

```jsonl
{"title":"iPhone 15 Pro Max 256GB zin đẹp 99%","description":"Máy đẹp sxdh fullbox bh 8 tháng","price":28000000,"category_id":123,"source":"feedback"}
{"title":"Laptop Dell core i5 ram 8G","description":"Máy còn tốt giá sv","price":5000000,"category_id":200,"source":"manual"}
```

### 2.2 Trường bắt buộc

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Tiêu đề bài đăng (không rỗng) |
| `category_id` | integer | ✅ | ID category đúng (must be leaf) |

### 2.3 Trường tùy chọn nhưng khuyến nghị

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | string | "" | Mô tả chi tiết |
| `price` | float | null | Giá sản phẩm (VNĐ) |
| `image_urls` | array | [] | Danh sách URL ảnh |
| `source` | string | "unknown" | Nguồn data (feedback, manual, import) |
| `predicted_category_id` | integer | null | Category dự đoán ban đầu |
| `predicted_confidence` | float | null | Confidence của prediction |
| `is_validated` | boolean | false | Đã được validate chưa |
| `validator_id` | integer | null | ID người validate |
| `created_at` | string | now | Timestamp ISO 8601 |

### 2.4 Ví dụ đầy đủ

```json
{
  "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên",
  "description": "Mình bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. Máy mới mua 3 tháng, còn zin all, BH còn 9 tháng. Bán vì lên đời. Fullbox phụ kiện đầy đủ.",
  "price": 28000000,
  "image_urls": [
    "https://storage.example.com/products/iphone15-1.jpg",
    "https://storage.example.com/products/iphone15-2.jpg"
  ],
  "category_id": 123,
  "category_path": "Điện tử > Điện thoại > iPhone",
  "predicted_category_id": 124,
  "predicted_confidence": 0.75,
  "was_corrected": true,
  "source": "feedback",
  "is_validated": true,
  "validator_id": 1,
  "validation_notes": "Đúng category, user chọn đúng",
  "created_at": "2026-05-06T10:30:00Z",
  "metadata": {
    "user_id": "user_123",
    "session_id": "session_456",
    "correction_reason": "Model dự đoán sai category con"
  }
}
```

---

## 3. Import/Export Formats

### 3.1 Categories Import

**Format:** JSON Array  
**File extension:** `.json`  
**Encoding:** UTF-8

```json
[
  { "id": 1, "name": "Category 1", ... },
  { "id": 2, "name": "Category 2", ... }
]
```

**Validation:**
- File phải là valid JSON
- Tất cả IDs phải unique
- parent_id phải tồn tại trong danh sách (hoặc null)
- Không được có vòng lặp (circular references)

### 3.2 Training Data Import

**Format:** JSONL (JSON Lines)  
**File extension:** `.jsonl`  
**Encoding:** UTF-8

```jsonl
{"title":"...","category_id":123}
{"title":"...","category_id":456}
```

**Tại sao JSONL?**
- ✅ Dễ stream (không cần load toàn bộ vào memory)
- ✅ Dễ append (thêm dòng mới)
- ✅ Dễ process parallel
- ✅ Dễ validate từng dòng

### 3.3 Export Formats

#### JSON Export (Categories)
```bash
GET /api/admin/data/export/categories?format=json

→ Downloads: categories_2026-05-06.json
```

#### JSONL Export (Training Data)
```bash
GET /api/admin/data/export/training?format=jsonl&validated_only=true

→ Downloads: training_data_2026-05-06.jsonl
```

#### CSV Export (For analysis)
```bash
GET /api/admin/data/export/training?format=csv

→ Downloads: training_data_2026-05-06.csv
```

CSV Format:
```csv
title,description,price,category_id,category_path,confidence,source
"iPhone 15 Pro Max","Máy đẹp...",28000000,123,"Điện tử > Điện thoại > iPhone",0.92,feedback
```

---

## 4. Validation Rules

### 4.1 Category Validation

#### Rule 1: ID phải duy nhất
```python
✅ PASS: [{"id": 1}, {"id": 2}]
❌ FAIL: [{"id": 1}, {"id": 1}]  # Duplicate ID
```

#### Rule 2: Name không được rỗng
```python
✅ PASS: {"id": 1, "name": "iPhone"}
❌ FAIL: {"id": 1, "name": ""}
❌ FAIL: {"id": 1, "name": null}
```

#### Rule 3: parent_id phải tồn tại
```python
✅ PASS: {"id": 2, "parent_id": 1}  # nếu category 1 tồn tại
❌ FAIL: {"id": 2, "parent_id": 999}  # category 999 không tồn tại
✅ PASS: {"id": 1, "parent_id": null}  # Root category OK
```

#### Rule 4: Không được vòng lặp
```python
❌ FAIL: 
[
  {"id": 1, "parent_id": 2},
  {"id": 2, "parent_id": 1}
]
# Circular reference: 1 → 2 → 1
```

#### Rule 5: is_active phải là 0 hoặc 1
```python
✅ PASS: {"id": 1, "is_active": 1}
✅ PASS: {"id": 1, "is_active": 0}
❌ FAIL: {"id": 1, "is_active": true}  # Must be int
❌ FAIL: {"id": 1, "is_active": 2}
```

### 4.2 Training Data Validation

#### Rule 1: Title không được rỗng
```python
✅ PASS: {"title": "iPhone 15", "category_id": 123}
❌ FAIL: {"title": "", "category_id": 123}
❌ FAIL: {"title": "   ", "category_id": 123}  # Whitespace only
```

#### Rule 2: category_id phải tồn tại
```python
✅ PASS: {"title": "...", "category_id": 123}  # nếu 123 tồn tại
❌ FAIL: {"title": "...", "category_id": 999}  # không tồn tại
```

#### Rule 3: category_id phải là leaf category
```python
✅ PASS: {"title": "...", "category_id": 123}  # 123 là leaf (không có con)
❌ FAIL: {"title": "...", "category_id": 1}  # 1 có category con
```

#### Rule 4: Price phải >= 0 (nếu có)
```python
✅ PASS: {"title": "...", "price": 1000000}
✅ PASS: {"title": "...", "price": 0}
✅ PASS: {"title": "...", "price": null}  # OK
❌ FAIL: {"title": "...", "price": -1000}
```

#### Rule 5: image_urls phải là valid URLs
```python
✅ PASS: {"title": "...", "image_urls": ["https://example.com/a.jpg"]}
✅ PASS: {"title": "...", "image_urls": []}  # Empty OK
❌ FAIL: {"title": "...", "image_urls": ["not-a-url"]}
❌ FAIL: {"title": "...", "image_urls": ["ftp://..."]}  # Only http(s)
```

### 4.3 Validation Response Format

```json
{
  "valid": false,
  "errors": [
    {
      "row": 3,
      "field": "category_id",
      "value": 999,
      "message": "Category ID 999 does not exist",
      "severity": "error"
    }
  ],
  "warnings": [
    {
      "row": 5,
      "field": "description",
      "value": "",
      "message": "Description is empty, classification may be less accurate",
      "severity": "warning"
    }
  ],
  "stats": {
    "total_rows": 100,
    "valid_rows": 97,
    "errors": 3,
    "warnings": 5
  }
}
```

---

## 5. Data Quality Guidelines

### 5.1 Category Data Quality

#### ✅ GOOD Examples

```json
{
  "id": 123,
  "name": "iPhone",
  "description": "Các sản phẩm iPhone của Apple. Bao gồm tất cả các dòng iPhone từ cũ đến mới. PHÂN BIỆT: Không phải phụ kiện iPhone (case, cáp...), đó là category riêng.",
  "metadata": {
    "keywords": ["iphone", "apple", "ios"],
    "aliases": ["ip", "ái phôn"],
    "common_mistakes": ["Thường bị nhầm với Phụ kiện iPhone"]
  }
}
```

**Tốt vì:**
- Description rõ ràng, chi tiết
- Có PHÂN BIỆT với category dễ nhầm
- Có keywords & aliases giúp search
- Có note về common mistakes

#### ❌ BAD Examples

```json
{
  "id": 123,
  "name": "iPhone",
  "description": "iPhone"
}
```

**Kém vì:**
- Description quá ngắn, không giúp gì
- Thiếu context
- Thiếu metadata

### 5.2 Training Data Quality

#### ✅ HIGH QUALITY Examples

```json
{
  "title": "iPhone 15 Pro Max 256GB Titan Tự Nhiên fullbox",
  "description": "Mình bán iPhone 15 Pro Max 256GB màu Titan Tự Nhiên. Máy mới mua 3 tháng, còn zin all, BH còn 9 tháng. Bán vì lên đời 16. Fullbox phụ kiện đầy đủ. Máy đẹp không trầy xước, pin 100%.",
  "price": 28000000,
  "category_id": 123
}
```

**Tốt vì:**
- Title đầy đủ thông tin quan trọng
- Description chi tiết, tự nhiên
- Category đúng và cụ thể (leaf)

#### ⚠️ MEDIUM QUALITY Examples

```json
{
  "title": "iphone 15",
  "description": "máy đẹp",
  "category_id": 123
}
```

**Trung bình vì:**
- Title thiếu chi tiết (dung lượng? màu?)
- Description quá ngắn
- Nhưng category đúng

#### ❌ LOW QUALITY Examples

```json
{
  "title": "máy",
  "description": "",
  "category_id": 123
}
```

**Kém vì:**
- Title quá chung chung
- Không có description
- Không đủ thông tin để phân loại

### 5.3 Data Balance

**Khuyến nghị phân bố dữ liệu:**

```python
# Tốt nhất: Balanced dataset
Category A: 1000 samples (20%)
Category B: 1000 samples (20%)
Category C: 1000 samples (20%)
...

# Chấp nhận được: Imbalanced nhưng không quá
Category A: 2000 samples (40%)
Category B: 1000 samples (20%)
Category C: 500 samples (10%)
...

# ❌ Tránh: Quá imbalanced
Category A: 9000 samples (90%)
Category B: 100 samples (1%)
Category C: 50 samples (0.5%)
# → Model sẽ bias về Category A
```

**Giải pháp khi imbalanced:**
1. Oversample minority classes
2. Undersample majority classes
3. Generate synthetic data
4. Use class weights trong training

---

## 6. Common Errors & Solutions

### 6.1 Import Errors

#### Error: "Duplicate category ID"
```
❌ Error: Category ID 123 appears multiple times

Solution:
- Kiểm tra file, đảm bảo mỗi ID chỉ xuất hiện 1 lần
- Nếu merge từ nhiều sources, deduplicate trước
```

#### Error: "Parent category not found"
```
❌ Error: Category 456 has parent_id=999, but category 999 does not exist

Solution:
- Import categories theo thứ tự: parent trước, children sau
- Hoặc đảm bảo tất cả parent categories có trong file
```

#### Error: "Circular reference detected"
```
❌ Error: Circular reference: 1 → 2 → 3 → 1

Solution:
- Review category hierarchy
- Đảm bảo không có vòng lặp
```

#### Error: "Invalid JSON format"
```
❌ Error: Unexpected token at line 45

Solution:
- Validate JSON trước: https://jsonlint.com
- Check encoding (phải là UTF-8)
- Check trailing commas, quotes
```

### 6.2 Training Data Errors

#### Error: "Category is not a leaf"
```
❌ Error: Category 1 (Điện tử) is not a leaf category

Solution:
- Chỉ dùng leaf categories (không có con)
- Ví dụ: Dùng "iPhone" thay vì "Điện thoại" hay "Điện tử"
```

#### Error: "Empty title"
```
❌ Error: Title is empty or whitespace-only at row 123

Solution:
- Đảm bảo mọi sample có title
- Remove whitespace-only titles
```

#### Error: "Invalid image URL"
```
❌ Error: Image URL "not-a-url" is invalid at row 456

Solution:
- Validate URLs before import
- Remove invalid URLs
- Ensure URLs are accessible
```

### 6.3 Validation Warnings

#### Warning: "Description is empty"
```
⚠️ Warning: Description is empty, may affect classification accuracy

Impact: Low-medium
Solution: Add descriptions when possible, but not required
```

#### Warning: "Very short title"
```
⚠️ Warning: Title is very short (<10 chars): "iphone"

Impact: Medium
Solution: Encourage more descriptive titles
```

#### Warning: "Imbalanced dataset"
```
⚠️ Warning: Category 123 has 5000 samples, while category 456 has only 50

Impact: High (model bias)
Solution: Balance dataset before training
```

---

## 7. Validation API

### 7.1 Validate Before Import

```bash
POST /api/admin/data/validate
Content-Type: application/json

{
  "data_type": "categories",  # or "training_data"
  "data": [
    {"id": 1, "name": "Test Category", ...},
    ...
  ]
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "row": 5,
      "message": "Description is empty",
      "severity": "warning"
    }
  ],
  "stats": {
    "total_rows": 100,
    "valid_rows": 100,
    "errors": 0,
    "warnings": 1
  }
}
```

### 7.2 Validate File

```bash
POST /api/admin/data/validate-file
Content-Type: multipart/form-data

file: categories.json
data_type: categories
```

### 7.3 Auto-fix Common Issues

```bash
POST /api/admin/data/auto-fix
{
  "data": [...],
  "fixes": [
    "trim_whitespace",
    "lowercase_fields",
    "remove_duplicates",
    "validate_urls"
  ]
}
```

---

## 8. Best Practices

### 8.1 Category Management

✅ **DO:**
- Luôn backup trước khi import
- Validate data trước khi import
- Test với một vài categories trước
- Document changes
- Keep version history

❌ **DON'T:**
- Import trực tiếp vào production
- Skip validation
- Delete categories đang có training data
- Change IDs của existing categories

### 8.2 Training Data

✅ **DO:**
- Collect diverse examples
- Balance dataset
- Validate and clean data
- Version your datasets
- Track data sources

❌ **DON'T:**
- Use duplicate samples
- Include spam/fake data
- Mix different data quality levels
- Train on uncleaned data

### 8.3 Data Hygiene

**Regular maintenance:**
```
Weekly:
- Review new training data
- Remove low-quality samples
- Check for duplicates

Monthly:
- Rebalance dataset
- Update category descriptions
- Archive old data

Quarterly:
- Full data audit
- Update validation rules
- Retrain models
```

---

## 9. Tools & Scripts

### 9.1 Validation Script

```python
# scripts/validate_data.py
python validate_data.py \
  --file categories.json \
  --type categories \
  --strict
```

### 9.2 Data Cleaning Script

```python
# scripts/clean_training_data.py
python clean_training_data.py \
  --input raw_data.jsonl \
  --output cleaned_data.jsonl \
  --remove-duplicates \
  --validate-categories
```

### 9.3 Balance Dataset Script

```python
# scripts/balance_dataset.py
python balance_dataset.py \
  --input training_data.jsonl \
  --output balanced_data.jsonl \
  --method oversample \
  --target-samples 1000
```

---

## 10. Checklist

### Category Import Checklist
- [ ] Backup current categories
- [ ] Validate JSON format
- [ ] Check for duplicate IDs
- [ ] Verify parent references
- [ ] Test import on staging
- [ ] Import to production
- [ ] Rebuild vector index
- [ ] Verify in admin dashboard

### Training Data Import Checklist
- [ ] Clean and validate data
- [ ] Remove duplicates
- [ ] Check category IDs exist
- [ ] Verify data quality
- [ ] Balance dataset (if needed)
- [ ] Test with small sample
- [ ] Import full dataset
- [ ] Verify in dashboard

---

## 📞 Support

**Questions about data standards?**
- Check examples in this document
- Use validation API before import
- Contact admin if validation fails

**Found a bug in validation?**
- Report to development team
- Include sample data (anonymized)
- Describe expected vs actual behavior
