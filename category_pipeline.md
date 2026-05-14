# Pipeline triển khai AI tự động chọn danh mục sản phẩm

Tài liệu này mô tả pipeline dùng AI để tự động gợi ý/chọn danh mục cho bài đăng thương mại điện tử.

Mục tiêu hiện tại:

- File danh mục gốc chỉ cần lưu dữ liệu chuẩn của danh mục.
- Chỉ làm giàu trường `description` trong JSON/MySQL.
- Các trường phục vụ vector search như `path`, `is_leaf`, `parent_name`, `category_document` sẽ được sinh động khi build vector DB.

---

## 1. File danh mục nên lưu những gì?

Trong JSON hoặc MySQL, chỉ cần lưu các trường gốc như sau:

```json
{
  "id": 5,
  "name": "Laptop",
  "slug": "laptop",
  "description": "Máy tính xách tay, MacBook, laptop Dell, HP, Asus, Lenovo, ThinkPad, laptop gaming, laptop văn phòng, laptop cũ hoặc mới.",
  "icon": null,
  "image": "...",
  "parent_id": 1,
  "sort_order": 4,
  "is_featured": 0,
  "is_home_cheap": 0,
  "is_active": 1,
  "created_at": "2025-10-14 23:18:43",
  "updated_at": "2026-04-06 23:42:32"
}
```

Không cần lưu cố định các trường sau trong JSON/MySQL:

```text
parent_name
path
level
is_leaf
category_document
ai_description
```

Lý do: các trường này đều có thể tính lại từ `id`, `parent_id`, `name`, `description` khi build vector DB.

---

## 2. Các trường cần sinh khi build vector DB

Khi chạy script build vector, cần sinh các trường tạm sau.

### 2.1. `parent_name`

Lấy từ `parent_id` bằng cách lookup trong danh sách category.

Ví dụ:

```json
{
  "id": 5,
  "name": "Laptop",
  "parent_id": 1
}
```

Nếu category `id = 1` là `Đồ điện tử`, thì:

```json
{
  "parent_name": "Đồ điện tử"
}
```

### 2.2. `path`

Sinh bằng cách đi ngược cây cha/con từ category hiện tại lên root.

Ví dụ:

```text
Đồ điện tử > Laptop
```

Với cây nhiều cấp hơn, format vẫn là:

```text
Root > Parent > Child
```

### 2.3. `level`

Số cấp của category trong cây.

Ví dụ:

```text
Đồ điện tử                level = 0
Đồ điện tử > Laptop       level = 1
```

### 2.4. `is_leaf`

Một category là leaf nếu không có category active nào nhận nó làm cha.

Công thức:

```text
is_leaf = category.id không xuất hiện trong bất kỳ parent_id nào của category active khác
```

Chỉ nên auto-assign vào category `is_leaf = true`.

### 2.5. `category_document`

Đây là text tạm thời dùng để tạo embedding cho category.

Không cần lưu trong JSON/MySQL. Chỉ build khi gọi embedding model.

Format khuyến nghị:

```text
Đường dẫn danh mục: {path}.
Tên danh mục: {name}.
Mô tả: {description}.
```

Ví dụ:

```text
Đường dẫn danh mục: Đồ điện tử > Laptop.
Tên danh mục: Laptop.
Mô tả: Máy tính xách tay, MacBook, laptop Dell, HP, Asus, Lenovo, ThinkPad, laptop gaming, laptop văn phòng, laptop cũ hoặc mới.
```

---

## 3. Pipeline tổng thể

```text
1. Chuẩn bị danh mục
   JSON/MySQL categories
   ↓
   Build parent map, path, is_leaf
   ↓
   Build category_document
   ↓
   Embed category_document bằng ProtonX Embeddings
   ↓
   Upsert vector + payload vào Qdrant

2. Khi user đăng bài
   title + description + price + images
   ↓
   E4B multimodal product understanding
   ↓
   normalized_product_text
   ↓
   Build product embedding text
   ↓
   Embed product bằng ProtonX Embeddings
   ↓
   Qdrant search top K category
   ↓
   E4B rerank top K
   ↓
   Apply threshold
   ↓
   Auto assign / preselect / suggest top 3 / manual select
```

---

## 4. Build vector DB từ JSON/MySQL

### 4.1. Input category

Input chỉ cần các trường chuẩn:

```json
{
  "id": 5,
  "name": "Laptop",
  "description": "Máy tính xách tay, MacBook, laptop Dell, HP, Asus, Lenovo, ThinkPad, laptop gaming, laptop văn phòng, laptop cũ hoặc mới.",
  "parent_id": 1,
  "is_active": 1
}
```

### 4.2. Sinh metadata runtime

Script build vector sinh:

```json
{
  "category_id": 5,
  "name": "Laptop",
  "parent_id": 1,
  "parent_name": "Đồ điện tử",
  "path": "Đồ điện tử > Laptop",
  "level": 1,
  "is_leaf": true,
  "is_active": true
}
```

### 4.3. Build `category_document`

```text
Đường dẫn danh mục: Đồ điện tử > Laptop.
Tên danh mục: Laptop.
Mô tả: Máy tính xách tay, MacBook, laptop Dell, HP, Asus, Lenovo, ThinkPad, laptop gaming, laptop văn phòng, laptop cũ hoặc mới.
```

### 4.4. Embed category

Dùng ProtonX Embeddings để tạo vector:

```text
category_document
   ↓
ProtonX Embeddings
   ↓
category_vector
```

Lưu ý bắt buộc:

```text
Category embedding model = Product embedding model
```

Nếu category dùng ProtonX Embeddings, product cũng phải dùng ProtonX Embeddings.

### 4.5. Upsert vào Qdrant

Qdrant payload khuyến nghị:

```json
{
  "category_id": 5,
  "name": "Laptop",
  "parent_id": 1,
  "parent_name": "Đồ điện tử",
  "path": "Đồ điện tử > Laptop",
  "level": 1,
  "is_leaf": true,
  "is_active": true,
  "description": "Máy tính xách tay, MacBook, laptop Dell, HP, Asus, Lenovo, ThinkPad, laptop gaming, laptop văn phòng, laptop cũ hoặc mới."
}
```

Chỉ nên upsert hoặc search category active.

---

## 5. Product understanding bằng E4B

Khi user đăng bài, gọi E4B một lần để hiểu text + ảnh.

### Prompt khuyến nghị

```text
Bạn là hệ thống chuẩn hóa bài đăng sản phẩm cho sàn thương mại điện tử.

Nhiệm vụ:
- Đọc title, description, price và ảnh nếu có.
- Viết lại thành một đoạn normalized_product_text rõ nghĩa để dùng cho semantic embedding.
- Mở rộng viết tắt phổ biến nếu chắc chắn.
- Dựa vào ảnh để bổ sung loại sản phẩm nếu text chưa rõ.
- Không chọn danh mục ở bước này.
- Không tự tạo category_id.
- Không bịa thương hiệu, model, dung lượng, thông số nếu không có bằng chứng.
- Nếu không chắc, viết trung lập.
- Nếu text và ảnh mâu thuẫn, phản ánh sự mâu thuẫn trong normalized_product_text.
- Trả về JSON hợp lệ, không thêm giải thích ngoài JSON.

Input:
Title: {{title}}
Description: {{description}}
Price: {{price}}
Images: {{images}}

Output JSON:
{
  "normalized_product_text": string,
  "confidence": number,
  "text_image_consistency": "consistent" | "image_clarifies_text" | "text_only" | "image_only" | "conflict" | "unknown"
}
```

### Ví dụ output

```json
{
  "normalized_product_text": "Bán điện thoại Apple iPhone 13 Pro Max 256GB, fullbox, pin 88%, máy nguyên bản, còn bảo hành.",
  "confidence": 0.95,
  "text_image_consistency": "text_only"
}
```

---

## 6. Build product embedding text

Không chỉ embed `normalized_product_text`; nên ghép cả raw text để tránh mất tín hiệu gốc.

Format khuyến nghị:

```text
Tiêu đề gốc: {{title}}
Mô tả gốc: {{description}}
Nội dung chuẩn hóa: {{normalized_product_text}}
```

Ví dụ:

```text
Tiêu đề gốc: Pass ip13 prm 256g fullbox
Mô tả gốc: pin 88, máy zin, còn bh
Nội dung chuẩn hóa: Bán điện thoại Apple iPhone 13 Pro Max 256GB, fullbox, pin 88%, máy nguyên bản, còn bảo hành.
```

---

## 7. Embed product và vector search

### 7.1. Embed product

```text
product_embedding_text
   ↓
ProtonX Embeddings
   ↓
product_vector
```

### 7.2. Search Qdrant

Filter khuyến nghị:

```json
{
  "must": [
    {
      "key": "is_active",
      "match": {
        "value": true
      }
    },
    {
      "key": "is_leaf",
      "match": {
        "value": true
      }
    }
  ]
}
```

Top K khuyến nghị:

```text
K = 20 mặc định
K = 30 nếu E4B confidence thấp hoặc bài đăng quá ngắn
```

---

## 8. E4B rerank top K

Sau khi Qdrant trả về top K category, gọi E4B để chọn category cuối.

### Prompt rerank

```text
Bạn là hệ thống phân loại danh mục bài đăng cho sàn thương mại điện tử.

Nhiệm vụ:
- Chọn category phù hợp nhất cho bài đăng.
- Chỉ được chọn category_id trong danh sách ứng viên.
- Không tự tạo category mới.
- Ưu tiên danh mục con cụ thể nhất.
- Nếu không đủ thông tin, trả confidence thấp.
- Nếu bài đăng có text và ảnh mâu thuẫn, không được confidence cao.
- Trả về JSON hợp lệ, không thêm giải thích ngoài JSON.

Bài đăng:
{{product_embedding_text}}

Thông tin hiểu bài đăng:
product_understanding_confidence: {{confidence}}
text_image_consistency: {{text_image_consistency}}

Danh mục ứng viên:
{{top_k_categories}}

Output JSON:
{
  "category_id": number | null,
  "confidence": number,
  "reason": string,
  "alternatives": [
    {
      "category_id": number,
      "confidence": number
    }
  ]
}
```

---

## 9. Apply threshold

Không auto assign chỉ dựa vào một tín hiệu. Nên kết hợp:

```text
product_understanding_confidence
text_image_consistency
vector_top1_similarity
similarity_margin
rerank_confidence
```

### Auto assign

```text
Auto assign nếu:
- product_understanding_confidence >= 0.75
- text_image_consistency != "conflict"
- rerank_confidence >= 0.90
- vector_top1_similarity >= 0.78
- vector_top1_similarity - vector_top2_similarity >= 0.06
```

### Preselect

```text
Nếu rerank_confidence >= 0.75 nhưng chưa đủ auto assign:
→ chọn sẵn category cho user, nhưng cho phép đổi.
```

### Suggest top 3

```text
Nếu rerank_confidence >= 0.55:
→ hiển thị top 3 category cho user chọn.
```

### Manual select

```text
Nếu text_image_consistency = "conflict" hoặc confidence quá thấp:
→ yêu cầu user chọn thủ công.
```

---

## 10. Pseudocode build category vector

```python
def build_parent_maps(categories):
    category_by_id = {c["id"]: c for c in categories}
    active_categories = [c for c in categories if c.get("is_active") == 1]
    active_parent_ids = {c["parent_id"] for c in active_categories if c.get("parent_id") is not None}
    return category_by_id, active_parent_ids


def build_path(category, category_by_id):
    names = []
    current = category

    while current:
        names.append(current["name"])
        parent_id = current.get("parent_id")
        current = category_by_id.get(parent_id) if parent_id else None

    return " > ".join(reversed(names))


def build_level(path):
    return max(len(path.split(" > ")) - 1, 0)


def build_category_document(category, path):
    description = category.get("description") or category.get("name")
    return f"Đường dẫn danh mục: {path}. Tên danh mục: {category['name']}. Mô tả: {description}."


def build_category_vector_profiles(categories):
    category_by_id, active_parent_ids = build_parent_maps(categories)
    profiles = []

    for category in categories:
        if category.get("is_active") != 1:
            continue

        is_leaf = category["id"] not in active_parent_ids
        if not is_leaf:
            continue

        path = build_path(category, category_by_id)
        parent = category_by_id.get(category.get("parent_id"))
        parent_name = parent["name"] if parent else None
        level = build_level(path)
        category_document = build_category_document(category, path)

        profiles.append({
            "category_id": category["id"],
            "name": category["name"],
            "parent_id": category.get("parent_id"),
            "parent_name": parent_name,
            "path": path,
            "level": level,
            "is_leaf": True,
            "is_active": True,
            "description": category.get("description"),
            "category_document": category_document,
        })

    return profiles
```

---

## 11. Pseudocode runtime suggest category

```python
def suggest_category(post):
    understanding = call_e4b_product_understanding(
        title=post["title"],
        description=post.get("description", ""),
        price=post.get("price"),
        images=post.get("images", [])
    )

    product_embedding_text = f"""
Tiêu đề gốc: {post["title"]}
Mô tả gốc: {post.get("description", "")}
Nội dung chuẩn hóa: {understanding["normalized_product_text"]}
""".strip()

    product_vector = protonx_embed(product_embedding_text)

    top_k = 30 if understanding["confidence"] < 0.75 else 20

    candidates = qdrant_search(
        vector=product_vector,
        top_k=top_k,
        filters={
            "is_active": True,
            "is_leaf": True
        }
    )

    rerank_result = call_e4b_category_rerank(
        product_text=product_embedding_text,
        confidence=understanding["confidence"],
        text_image_consistency=understanding["text_image_consistency"],
        candidates=candidates
    )

    decision = apply_threshold(
        understanding=understanding,
        candidates=candidates,
        rerank_result=rerank_result
    )

    save_category_suggestion_log(
        post=post,
        understanding=understanding,
        candidates=candidates,
        rerank_result=rerank_result,
        decision=decision
    )

    return decision
```

---

## 12. Log cần lưu

```sql
CREATE TABLE category_suggestion_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    post_id BIGINT NULL,

    raw_title TEXT,
    raw_description TEXT,
    price DECIMAL(15,2) NULL,

    normalized_product_text TEXT,
    product_understanding_confidence DECIMAL(5,4),
    text_image_consistency VARCHAR(50),

    embedding_model VARCHAR(100),
    vector_candidates JSON,

    rerank_category_id BIGINT NULL,
    rerank_confidence DECIMAL(5,4),
    rerank_reason TEXT,

    final_category_id BIGINT NULL,
    user_changed BOOLEAN DEFAULT FALSE,

    decision VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 13. Chỉ số cần đo

Quan trọng nhất:

```text
Top-20 recall
```

Nghĩa là category đúng có nằm trong top 20 từ vector search không.

Các chỉ số khác:

```text
Top-1 vector accuracy
Top-3 vector accuracy
E4B rerank accuracy
Auto-assign accuracy
User changed rate
Manual select rate
Conflict rate
```

Nếu Top-20 recall thấp, cần cải thiện:

```text
description của category
category_document format
normalized_product_text
embedding model
K
```

---

## 14. Kết luận triển khai

Thiết kế cuối cùng:

```text
DB/JSON chỉ lưu:
- id
- name
- slug
- description đã làm giàu
- parent_id
- sort_order
- is_active
- image/icon nếu cần

Khi build vector DB thì sinh:
- parent_name
- path
- level
- is_leaf
- category_document

Qdrant lưu:
- vector của category_document
- payload gồm category_id, name, path, parent_id, parent_name, level, is_leaf, is_active, description

Runtime:
- E4B tạo normalized_product_text
- ProtonX embed product
- Qdrant search top K
- E4B rerank
- threshold quyết định auto/suggest/manual
```
