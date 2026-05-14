# Plan: Auto Category – Tự động chọn danh mục sản phẩm

## Mục tiêu

Xây dựng service tự động phân loại danh mục cho bài đăng sản phẩm thương mại điện tử, sử dụng LLM local (gemma-4-E2B-it qua llama server), deploy bằng Docker, public qua Cloudflare Tunnel.

---

## Kiến trúc tổng thể

```
[User / Browser]
      │
      ▼
[Cloudflare Tunnel / DNS]
      │
      ▼
[Nginx :80/:443]  ──► /api/*  ──► [FastAPI :8000]
                  ──► /*      ──► [Static test page]
                                        │
                      ┌─────────────────┼─────────────────┐
                      ▼                 ▼                 ▼
            [llama-server :8080] [Qdrant :6333]   [categories.json]
                gemma4-e4b       vector search     category data
           (llama.cpp server)    768-dim vectors   89 categories
```

### Services trong Docker Compose

| Service        | Image                                  | Role                               |
|----------------|----------------------------------------|------------------------------------|
| `api`          | Python 3.12 + FastAPI                  | Backend API, pipeline logic        |
| `llama-server` | ghcr.io/ggml-org/llama.cpp:server-cuda | LLM server (gemma4-e4b model)      |
| `qdrant`       | qdrant/qdrant                          | Vector database (768-dim vectors)  |
| `postgres`     | postgres:16-alpine                     | Primary database                   |
| `redis`        | redis:7-alpine                         | Caching & rate limiting            |
| `nginx`        | nginx:alpine                           | Reverse proxy, static files        |
| `cloudflared`  | cloudflare/cloudflared                 | Tunnel ra internet (production)    |

---

## Cấu trúc thư mục

```
autocategory/
├── plan.md
├── docker-compose.yml            # dev
├── docker-compose.prod.yml       # prod + cloudflared tunnel
├── .env.example
├── .env                          # local, không commit
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # settings từ env
│   ├── data/
│   │   └── categories.json       # copy từ categories_full_description_enriched.json
│   ├── services/
│   │   ├── category_builder.py   # build profiles, path, is_leaf từ JSON
│   │   ├── embedder.py           # sentence-transformers (Alibaba-NLP/gte-multilingual-base)
│   │   ├── llm_service.py        # gọi llama-server (gemma4-e4b model)
│   │   ├── qdrant_service.py     # upsert + search Qdrant (768-dim vectors)
│   │   └── classifier.py        # pipeline chính: understand → embed → search → rerank → threshold
│   └── routers/
│       ├── admin.py              # /api/admin/build-index
│       ├── classify.py           # /api/classify
│       └── category.py          # /api/categories
│
├── frontend/
│   └── index.html                # Test workflow page
│
├── nginx/
│   └── nginx.conf
│
└── cloudflare/
    ├── config.yml                # cloudflared tunnel config
    └── SETUP.md                  # hướng dẫn public
```

---

## Pipeline xử lý (runtime)

```
Input: title, description, price, image_urls?
          │
          ▼
[Step 1] LLM Product Understanding (gemma4-e4b via llama-server)
  → normalized_product_text
  → confidence
  → text_image_consistency
          │
          ▼
[Step 2] Build product_embedding_text
  "Tiêu đề gốc: {title}\nMô tả gốc: {desc}\nNội dung chuẩn hóa: {normalized}"
          │
          ▼
[Step 3] Embed product (Alibaba-NLP/gte-multilingual-base via sentence-transformers)
  → product_vector (768 dims)
          │
          ▼
[Step 4] Qdrant vector search top K
  filter: is_active=true, is_leaf=true
  → top_k candidates with similarity scores
          │
          ▼
[Step 5] LLM Rerank (gemma4-e4b via llama-server)
  → category_id, confidence, reason, alternatives
          │
          ▼
[Step 6] Apply threshold
  → decision: auto_assign | preselect | suggest_top3 | manual_select
```

---

## Threshold quyết định

| Condition                                              | Decision        |
|--------------------------------------------------------|-----------------|
| rerank_conf ≥ 0.90 + vector_sim ≥ 0.78 + margin ≥ 0.06 | `auto_assign`   |
| rerank_conf ≥ 0.75                                     | `preselect`     |
| rerank_conf ≥ 0.55                                     | `suggest_top3`  |
| text_image_consistency = "conflict" or conf < 0.55     | `manual_select` |

---

## Gemma Model Configuration

**Model:** gemma4-e4b (running in llama-server via llama.cpp)  
**Server:** llama.cpp server-cuda (OpenAI-compatible API)  
**Endpoint:** http://llama-server:8080

**Cấu hình trong `.env`:**
```bash
LLAMA_BASE_URL=http://llama-server:8080
LLAMA_MODEL=gemma4-e4b
LLAMA_TEMPERATURE=0.1
LLAMA_MAX_TOKENS=512
LLAMA_TIMEOUT=30
```

Model được load sẵn trong container llama-server, sử dụng OpenAI-compatible API format.

---

## Build vector index

Trước khi dùng, chạy 1 lần:

```
POST /api/admin/build-index
```

Pipeline build:
1. Đọc `categories.json`
2. Build parent map, path, level, is_leaf cho mỗi leaf category
3. Build `category_document` text
4. Embed qua Ollama `nomic-embed-text`
5. Upsert vào Qdrant collection `categories`

---

## Test page (frontend/index.html)

Mô phỏng chính xác toàn bộ pipeline, hiển thị từng bước:

1. **Input form**: title, description, price, image URL (optional)
2. **Step 1**: Gọi API → hiển thị normalized_product_text, confidence, consistency
3. **Step 2**: Hiển thị product_embedding_text đã build
4. **Step 3–4**: Hiển thị top K vector candidates (name, path, similarity score)
5. **Step 5**: Hiển thị rerank result (chosen category, confidence, reason)
6. **Step 6**: Hiển thị decision badge (auto_assign / preselect / suggest_top3 / manual_select)
7. **Final**: Hiển thị category được chọn với full path

---

## Cloudflare public

Hai cách:

### Cách 1: Cloudflare Tunnel (khuyến nghị, không cần mở port)
1. Tạo tunnel trên Cloudflare dashboard
2. Lấy tunnel token
3. Đặt vào `.env`: `CF_TUNNEL_TOKEN=xxx`
4. Chạy `docker-compose -f docker-compose.prod.yml up -d`
5. Trỏ subdomain vào tunnel

### Cách 2: Cloudflare DNS + Nginx SSL
1. Mở port 80/443 trên server
2. Cấu hình DNS A record trỏ về IP server
3. Dùng Cloudflare proxy (orange cloud)
4. Nginx terminate SSL

---

## Các bước triển khai

```
1. git clone / copy project
2. cp .env.example .env  →  điền các giá trị
3. docker-compose up -d  →  llama-server sẽ load gemma4-e4b model
4. Đợi services khởi động (healthcheck)
5. POST /api/admin/build-index  →  build vector DB với 89 categories
6. Mở http://localhost:3001  →  test page
7. Mở http://localhost:3001/admin  →  admin dashboard
8. (Production) Cloudflare Tunnel đã được cấu hình sẵn trong docker-compose.yml
```
