# Hướng dẫn public qua Cloudflare Tunnel

## Yêu cầu

- Tài khoản Cloudflare (free tier đủ dùng)
- Domain đã thêm vào Cloudflare
- Docker + Docker Compose đã cài

---

## Mô hình HA an toàn

Mỗi máy chạy một `cloudflared` replica của **cùng một remotely-managed tunnel**.
Cloudflare tự chuyển request sang replica còn hoạt động nếu một máy mất kết nối.
Mọi replica phải chạy cùng ứng dụng và phục vụ được cùng hostname/origin.

Script HA không bao giờ xóa tunnel hoặc DNS record. Nếu phát hiện tunnel local cũ,
script dừng lại trước khi thay đổi Cloudflare.

## Cách triển khai

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
CF_TUNNEL_NAME=autocategory-ha  # giống nhau trên mọi máy
# Tùy chọn; để trống sẽ tự tìm chính xác theo tên:
CF_TUNNEL_ID=
```

> **Không cần** vào Cloudflare dashboard để tạo tunnel hay DNS thủ công.

### Bước 4: Deploy replica

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare-ha.yml up -d --build --remove-orphans
```

Docker tự động:
- Tìm chính xác `CF_TUNNEL_NAME` và dùng lại remotely-managed tunnel nếu có.
- Chỉ tạo tunnel khi chưa có; không bao giờ xóa tunnel cũ.
- Merge hostname vào remote ingress mà không xóa các hostname khác.
- Trong cùng một container: lấy token, chạy `cloudflared` như một replica,
  chờ connector online rồi tự tạo/cập nhật CNAME.
- Container tiếp tục chạy để giám sát tiến trình `cloudflared`; Docker tự restart
  toàn bộ quy trình nếu connector thoát.

Xem tunnel đã chọn, connector và kết quả publish DNS:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare-ha.yml logs -f cloudflared
```

Thông thường không cần cấu hình `CF_TUNNEL_ID`. Chỉ điền UUID nếu tài khoản có
nhiều remotely-managed tunnel trùng chính xác một tên; trong trường hợp đó script
sẽ dừng an toàn thay vì tự chọn nhầm.

### Bước 5: Build index (lần đầu)

```bash
curl -X POST https://autocategory.yourdomain.com/api/admin/build-index
```

### Bước 6: Truy cập

```
https://autocategory.yourdomain.com          → Test page
https://autocategory.yourdomain.com/api/docs → Swagger UI
```

---

## Thêm máy mới

Copy cùng `.env` (đặc biệt `CF_ACCOUNT_ID`, `CF_DOMAIN`, `CF_TUNNEL_NAME`) sang
máy mới rồi chạy đúng lệnh deploy ở trên. Script tự nhận diện tunnel theo tên và
lấy token dùng chung. Không xóa tunnel, DNS hoặc volume trên máy cũ; máy cũ tiếp
tục là một replica đang hoạt động.

> Replica cùng tunnel là HA/failover, không bảo đảm round-robin. Nếu các máy chạy
> ứng dụng khác nhau hoặc cần điều phối tải theo health/địa lý, dùng tunnel riêng
> cho từng origin kết hợp Cloudflare Load Balancer.

## Chuyển từ tunnel local cũ mà không gián đoạn máy cũ

1. Nếu tunnel cũ là local và trùng tên, chọn một tên remote mới, ví dụ
   `CF_TUNNEL_NAME=autocategory-ha`. Script không tự chuyển đổi hay xóa tunnel local.
2. Deploy bằng HA overlay. Service `cloudflared` duy nhất tạo/reuse tunnel remote,
   kết nối, rồi tự chuyển CNAME production sau khi tunnel đã online.
3. Chạy cùng cấu hình `CF_TUNNEL_NAME` trên máy mới. Máy mới tự nhận tunnel và
   trở thành replica thứ hai; không có tài nguyên nào của máy cũ bị xóa.
4. Chỉ sau khi các replica mới hoạt động mới cân nhắc xóa tunnel local cũ bằng
   tay trên Cloudflare. Script của dự án không thực hiện bước xóa này.

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

## Bảo mật cho production

Các cổng PostgreSQL, Redis và Qdrant chỉ bind vào `127.0.0.1` của Docker host;
Nginx không public Qdrant dashboard. Với dashboard/API admin, nên dùng Cloudflare
Access (Zero Trust) nếu cần thêm một lớp xác thực ở edge.
