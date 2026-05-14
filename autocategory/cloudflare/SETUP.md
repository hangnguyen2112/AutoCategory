# Hướng dẫn public qua Cloudflare Tunnel

## Yêu cầu

- Tài khoản Cloudflare (free tier đủ dùng)
- Domain đã thêm vào Cloudflare
- Docker + Docker Compose đã cài
- Python 3.8+ + `pip install httpx`

---

## Cách nhanh nhất (script tự động)

### Bước 1: Tạo Cloudflare API Token

1. Vào **dash.cloudflare.com/profile/api-tokens**
2. **Create Token** → **Create Custom Token**
3. Cấp quyền:
   - `Cloudflare Tunnel` → `Edit`
   - `DNS` → `Edit` (chọn zone của domain bạn)
4. Copy token

### Bước 2: Lấy Account ID

Vào **dash.cloudflare.com** → sidebar góc phải dưới → copy **Account ID**

### Bước 3: Điền .env

```bash
CF_API_TOKEN=your_api_token_here
CF_ACCOUNT_ID=your_account_id_here
CF_SUBDOMAIN=autocategory       # subdomain muốn dùng
CF_DOMAIN=yourdomain.com        # domain đã có trong Cloudflare
```

> **Không cần** vào Cloudflare dashboard để tạo tunnel hay DNS thủ công.

### Bước 4: Deploy (không cần thêm bước nào)

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Docker tự động:
- ✅ Service `cf-setup` gọi Cloudflare API, lấy Zone ID, tạo tunnel
- ✅ Ghi credentials + config vào Docker volume `cf_runtime`
- ✅ Tạo DNS CNAME record có Cloudflare proxy
- ✅ Service `cloudflared` khởi động sau khi setup xong

### Bước 6: Build index (lần đầu)

```bash
curl -X POST https://autocategory.yourdomain.com/api/admin/build-index
```

### Bước 7: Truy cập

```
https://autocategory.yourdomain.com          → Test page
https://autocategory.yourdomain.com/api/docs → Swagger UI
```

---

## Chạy lại setup (đổi subdomain / domain)

Chỉ cần sửa `.env` rồi restart – `cf-setup` tự xóa tunnel cũ và tạo mới:

```bash
# Xóa volume cũ để force setup lại
docker-compose -f docker-compose.yml -f docker-compose.prod.yml \
  rm -sf cf-setup cloudflared
docker volume rm autocategory_cf_runtime

# Deploy lại
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kiểm tra nhanh sau deploy

```bash
# Health check
curl https://autocategory.yourdomain.com/api/health

# Test classify
curl -X POST https://autocategory.yourdomain.com/api/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"Pass ip13 prm 256g fullbox","description":"pin 88, còn bh","price":12500000}'
```

---

## Bảo mật admin endpoint

Thêm vào `nginx/nginx.conf` để chỉ cho IP nội bộ gọi `/api/admin/`:

```nginx
location /api/admin/ {
    allow 127.0.0.1;
    deny all;
    proxy_pass http://api_backend;
    proxy_set_header Host $host;
}
```

## Kiểm tra nhanh sau deploy

```bash
# Health check
curl https://autocategory.yourdomain.com/api/health

# Index categories
curl -X POST https://autocategory.yourdomain.com/api/admin/build-index

# Test classify
curl -X POST https://autocategory.yourdomain.com/api/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"Pass ip13 prm 256g fullbox","description":"pin 88, còn bh","price":12500000}'
```

---

## Bảo mật cho production

Nếu API cần giới hạn truy cập, thêm vào nginx.conf:

```nginx
# Restrict /api/admin/* chỉ cho IP nội bộ
location /api/admin/ {
    allow 127.0.0.1;
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://api_backend;
}
```

Hoặc dùng Cloudflare Access (Zero Trust) để protect toàn bộ app.
