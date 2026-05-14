# Kế hoạch: Feedback Learning & Category Sync System

**Mục tiêu:**
1. Thu thập feedback từ user (khi chọn category khác với dự đoán)
2. Sử dụng feedback để cải thiện model liên tục
3. Đồng bộ categories.json từ hệ thống chính và tự động rebuild vector index khi có thay đổi

---

## Phần 1: Feedback Collection System

### 1.1. Cấu trúc dữ liệu feedback

```json
{
  "feedback_id": "uuid",
  "timestamp": "2026-05-05T10:30:00Z",
  "ad_data": {
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Máy mới nguyên seal...",
    "price": 30000000,
    "image_urls": ["url1", "url2"]
  },
  "prediction": {
    "category_id": 123,
    "category_name": "Điện thoại",
    "category_path": "Điện tử > Điện thoại",
    "confidence": 0.85,
    "decision": "preselect",
    "alternatives": [...]
  },
  "user_selection": {
    "category_id": 456,
    "category_name": "Phụ kiện điện thoại",
    "category_path": "Điện tử > Phụ kiện > Phụ kiện điện thoại",
    "selected_at": "2026-05-05T10:31:00Z"
  },
  "metadata": {
    "is_correction": true,
    "correction_type": "wrong_prediction",
    "user_id": "optional",
    "session_id": "optional"
  }
}
```

### 1.2. API endpoints mới

#### **POST /api/feedback/submit**
```json
Request:
{
  "ad_data": {...},
  "prediction": {...},
  "user_selected_category_id": 456
}

Response:
{
  "status": "ok",
  "feedback_id": "uuid",
  "message": "Cảm ơn feedback, sẽ giúp cải thiện hệ thống"
}
```

#### **GET /api/feedback/stats**
```json
Response:
{
  "total_feedbacks": 1234,
  "corrections": 567,
  "correction_rate": 0.46,
  "top_confused_categories": [
    {"from": "Điện thoại", "to": "Phụ kiện", "count": 45},
    ...
  ]
}
```

#### **GET /api/feedback/export**
Query params: `?from=2026-05-01&to=2026-05-05&format=jsonl`
- Export feedback data để training
- Format: JSONL (1 JSON per line)

### 1.3. Lưu trữ feedback

**Option A: File-based (đơn giản, phù hợp MVP)**
```
autocategory/
  api/
    data/
      feedback/
        feedback_2026-05.jsonl    # Append-only log
        feedback_2026-06.jsonl
```

**Option B: SQLite (khuyến nghị)**
```sql
CREATE TABLE feedback (
    feedback_id TEXT PRIMARY KEY,
    timestamp DATETIME,
    ad_title TEXT,
    ad_description TEXT,
    ad_price REAL,
    predicted_category_id INTEGER,
    predicted_confidence REAL,
    user_selected_category_id INTEGER,
    is_correction BOOLEAN,
    raw_data TEXT  -- JSON dump
);

CREATE INDEX idx_correction ON feedback(is_correction, timestamp);
CREATE INDEX idx_categories ON feedback(predicted_category_id, user_selected_category_id);
```

### 1.4. Frontend integration

**Thêm vào test page (index.html):**
```javascript
// Sau khi user chọn category
async function submitFeedback(predictionResult, userSelectedCategoryId) {
  if (predictionResult.category_id !== userSelectedCategoryId) {
    await fetch('/api/feedback/submit', {
      method: 'POST',
      body: JSON.stringify({
        ad_data: currentAdData,
        prediction: predictionResult,
        user_selected_category_id: userSelectedCategoryId
      })
    });
    showToast('Cảm ơn bạn đã giúp cải thiện hệ thống!');
  }
}
```

---

## Phần 2: Category Sync System

### 2.1. Vấn đề cần giải quyết

- `categories.json` trong hệ thống chính thay đổi (thêm/sửa/xóa category)
- Cần đồng bộ về autocategory service
- Phát hiện thay đổi và tự động rebuild vector index

### 2.2. Chiến lược sync

#### **Option A: Webhook-based (khuyến nghị)**

Hệ thống chính gọi webhook khi có thay đổi:

```
POST /api/admin/sync-categories
Content-Type: application/json
Authorization: Bearer <ADMIN_TOKEN>

{
  "source": "main_system",
  "categories_url": "https://main-system.com/api/categories/export",
  "webhook_secret": "xxx"
}
```

Flow:
1. Main system → webhook trigger
2. AutoCategory service download categories.json mới
3. So sánh checksum/hash với file hiện tại
4. Nếu khác → backup old file → save new file → rebuild index
5. Log và notify

#### **Option B: Polling-based**

Định kỳ check categories.json từ hệ thống chính:

```python
# Cron job chạy mỗi 6h
async def sync_categories_job():
    new_data = await fetch_categories_from_main_system()
    new_hash = hashlib.sha256(json.dumps(new_data).encode()).hexdigest()
    
    if new_hash != current_hash:
        backup_current_categories()
        save_new_categories(new_data)
        await rebuild_index()
        send_notification("Categories updated and index rebuilt")
```

#### **Option C: Manual với validation**

Admin upload file qua API:

```
POST /api/admin/upload-categories
Content-Type: multipart/form-data

file: categories.json
```

Flow:
1. Validate JSON structure
2. Validate required fields (id, name, parent_id, is_active)
3. Compare với file hiện tại
4. Show diff preview
5. Confirm → backup → save → rebuild

### 2.3. API endpoints cho sync

#### **POST /api/admin/sync-categories**
```json
Request:
{
  "source_url": "https://...",
  "auth_token": "xxx",
  "auto_rebuild": true
}

Response:
{
  "status": "ok",
  "changes_detected": true,
  "diff": {
    "added": 5,
    "modified": 12,
    "deleted": 2,
    "total_before": 1234,
    "total_after": 1237
  },
  "index_rebuilt": true,
  "rebuild_stats": {
    "leaf_categories_indexed": 567,
    "time_taken_seconds": 45.2
  }
}
```

#### **GET /api/admin/categories-version**
```json
Response:
{
  "current_version": "2026-05-05T10:00:00Z",
  "file_hash": "sha256:abc123...",
  "total_categories": 1237,
  "last_synced": "2026-05-05T10:00:00Z",
  "sync_source": "webhook"
}
```

#### **POST /api/admin/compare-categories**
Upload file để xem diff trước khi apply:
```json
Response:
{
  "diff": {
    "added": [
      {"id": 999, "name": "NFT & Crypto", "parent_id": 1}
    ],
    "modified": [
      {"id": 123, "before": {...}, "after": {...}}
    ],
    "deleted": [
      {"id": 456, "name": "Category cũ"}
    ]
  }
}
```

### 2.4. Rebuild index workflow

```python
async def rebuild_index_pipeline():
    """
    Rebuild toàn bộ vector index khi categories.json thay đổi
    """
    try:
        # 1. Load new categories
        categories = load_categories(settings.categories_json_path)
        
        # 2. Build leaf profiles
        profiles = build_leaf_profiles(categories)
        
        # 3. Embed all (có thể cache những category không đổi)
        vectors = await batch_embed(profiles)
        
        # 4. Backup old collection (optional)
        await backup_collection()
        
        # 5. Delete & recreate collection
        await delete_collection()
        await upsert_categories(profiles, vectors)
        
        # 6. Validate: sample search test
        await validate_index()
        
        # 7. Log + notify
        logger.info(f"Index rebuilt: {len(profiles)} categories")
        
        return {"status": "ok", "indexed": len(profiles)}
        
    except Exception as e:
        # Rollback to backup if available
        await restore_backup()
        raise
```

### 2.5. Optimization: Incremental update

Thay vì rebuild toàn bộ, chỉ update những category thay đổi:

```python
async def incremental_update(diff):
    """
    Chỉ re-embed và update categories thay đổi
    """
    # Delete removed categories
    if diff["deleted"]:
        await delete_points(diff["deleted"])
    
    # Update modified + added
    changed = diff["added"] + diff["modified"]
    if changed:
        profiles = build_leaf_profiles(changed)
        vectors = await batch_embed(profiles)
        await upsert_categories(profiles, vectors)
```

**Lưu ý:** Incremental phức tạp hơn, chỉ cần thiết khi categories >10k.

---

## Phần 3: Training Pipeline với Feedback

### 3.1. Khi nào training?

**Trigger conditions:**
- Đạt đủ N corrections (ví dụ: 500 corrections)
- Định kỳ (mỗi tuần/tháng)
- Manual trigger từ admin
- Correction rate vượt ngưỡng (>30%)

### 3.2. Training workflow

```
1. Export feedback corrections
   └─> feedback_corrections.jsonl

2. Preprocess & validate
   ├─> Loại bỏ spam/outliers
   ├─> Validate category IDs còn tồn tại
   └─> Balance classes (nếu cần)

3. Augment category descriptions
   ├─> Thêm "common mistakes" vào description
   ├─> Ví dụ: "iPhone case" thường bị nhầm với "Điện thoại"
   │   → Thêm vào description: "Không bao gồm điện thoại, chỉ phụ kiện bảo vệ"
   └─> Update categories.json

4. Rebuild vector index
   └─> Với descriptions đã được enrich

5. A/B test
   ├─> Test với 10% traffic
   ├─> Monitor metrics: accuracy, confusion matrix
   └─> Rollback nếu performance giảm

6. Deploy to production
   └─> Update categories.json + rebuild index
```

### 3.3. Metrics để theo dõi

```python
{
  "feedback_metrics": {
    "total_feedbacks": 1234,
    "correction_rate": 0.46,  # % predictions bị sửa
    "avg_confidence_when_correct": 0.88,
    "avg_confidence_when_wrong": 0.72
  },
  
  "model_metrics": {
    "accuracy": 0.87,  # % predictions đúng
    "top3_accuracy": 0.95,  # % category đúng nằm trong top 3
    "confusion_matrix": {
      "Điện thoại->Phụ kiện": 45,
      "Laptop->Linh kiện": 23,
      ...
    }
  },
  
  "performance_metrics": {
    "avg_classify_time_ms": 850,
    "p95_classify_time_ms": 1200,
    "rebuild_index_time_minutes": 12
  }
}
```

### 3.4. Enrich categories.json với feedback insights

```python
# Ví dụ: Sau khi phân tích feedback
category["description"] += (
    " PHÂN BIỆT: "
    "Không bao gồm [category thường bị nhầm]. "
    "Các từ khóa đặc trưng: [keywords từ correct examples]. "
    "Lưu ý: [common mistakes]."
)
```

**Ví dụ cụ thể:**

```json
{
  "id": 456,
  "name": "Phụ kiện điện thoại",
  "description": "Các phụ kiện cho điện thoại như ốp lưng, dán màn hình, cáp sạc, tai nghe không dây. PHÂN BIỆT: Không phải là điện thoại, máy tính bảng hay smartwatch (đó là thiết bị chính). Từ khóa: case, ốp, bao da, kính cường lực, miếng dán, adapter, cục sạc, dây sạc. Lưu ý: Sản phẩm 'bộ' (gồm điện thoại + phụ kiện) thuộc Điện thoại.",
  "enriched_from_feedback": {
    "common_confusions": ["Điện thoại", "Thiết bị đeo thông minh"],
    "distinguishing_keywords": ["case", "ốp", "dán", "cáp"],
    "last_updated": "2026-05-05"
  }
}
```

---

## Phần 4: Implementation Roadmap

### Phase 1: Feedback Collection (Week 1)
- [ ] Thêm feedback router và endpoints
- [ ] Implement SQLite storage
- [ ] Thêm feedback button vào test page
- [ ] Dashboard xem feedback stats

### Phase 2: Category Sync (Week 2)
- [ ] API endpoint sync-categories (webhook)
- [ ] Implement diff detection
- [ ] Auto rebuild index khi có thay đổi
- [ ] Backup/restore mechanism

### Phase 3: Training Pipeline (Week 3-4)
- [ ] Export và analyze feedback
- [ ] Script để enrich categories.json
- [ ] A/B testing framework
- [ ] Metrics dashboard

### Phase 4: Automation (Week 5)
- [ ] Scheduled sync job (polling)
- [ ] Auto-training trigger
- [ ] Alerting khi correction rate cao
- [ ] Production monitoring

---

## Phần 5: File Structure Changes

```
autocategory/
  api/
    data/
      categories.json               # Main categories file
      categories_backup/            # Backup old versions
        categories_2026-05-01.json
        categories_2026-05-05.json
      feedback/
        feedback.db                 # SQLite database
        feedback_export/            # Exported JSONL for training
          corrections_2026-05.jsonl
    
    routers/
      feedback.py                   # NEW: Feedback endpoints
    
    services/
      sync_service.py               # NEW: Category sync logic
      feedback_service.py           # NEW: Feedback processing
      training_service.py           # NEW: Training pipeline
    
    scripts/
      enrich_categories.py          # Enrich từ feedback
      compare_categories.py         # Diff tool
      validate_categories.py        # Validation

  monitoring/
    metrics_dashboard.html          # Monitor feedback & performance
```

---

## Phần 6: Environment Variables

Thêm vào `.env`:

```bash
# Feedback
FEEDBACK_ENABLED=true
FEEDBACK_DB_PATH=./data/feedback/feedback.db

# Category Sync
CATEGORY_SYNC_ENABLED=true
CATEGORY_SOURCE_URL=https://main-system.com/api/categories
CATEGORY_SYNC_TOKEN=xxx
CATEGORY_SYNC_INTERVAL_HOURS=6
AUTO_REBUILD_ON_CHANGE=true

# Admin API
ADMIN_API_TOKEN=your_secret_token_here
```

---

## Phần 7: Monitoring & Alerts

### Metrics cần track

```python
# Prometheus metrics
feedback_total = Counter("feedback_submissions_total")
feedback_corrections = Counter("feedback_corrections_total")
category_sync_success = Counter("category_sync_success_total")
category_sync_failures = Counter("category_sync_failures_total")
index_rebuild_duration = Histogram("index_rebuild_seconds")
```

### Alerts

1. **Correction rate > 40%** trong 24h → Model degrading
2. **Category sync failed** 3 lần liên tiếp → Check network/auth
3. **Index rebuild failed** → Critical, rollback
4. **Classify latency > 2s** p95 → Performance issue

---

## Phần 8: Security Considerations

1. **Admin endpoints:**
   - Require API token authentication
   - Rate limiting: 10 requests/minute
   - Log all admin actions

2. **Feedback spam prevention:**
   - Rate limit: 100 submissions/IP/hour
   - Validate category IDs exist
   - Optional: CAPTCHA cho public API

3. **Category sync:**
   - Webhook signature verification
   - Validate JSON schema strictly
   - Dry-run mode trước khi apply

---

## Tổng kết

**Workflow hoàn chỉnh:**

```
User chọn category khác prediction
         ↓
  Save to feedback.db
         ↓
Đủ corrections → Analyze feedback
         ↓
  Enrich categories.json
         ↓
Main system update categories
         ↓
  Webhook → Sync service
         ↓
  Detect changes → Rebuild index
         ↓
  Monitor performance
         ↓
     [Repeat]
```

**Lợi ích:**
✅ Model tự động cải thiện theo thời gian
✅ Luôn đồng bộ với categories hệ thống chính
✅ Có thể rollback khi có vấn đề
✅ Metrics đầy đủ để đánh giá hiệu quả
✅ Automation giảm công việc thủ công

**Next steps:**
1. Review plan này với team
2. Prioritize phases
3. Start với Phase 1 (Feedback Collection)
