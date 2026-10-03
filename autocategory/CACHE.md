# Cache xử lý sản phẩm

Cache bật mặc định, gồm memory trong mỗi worker và Redis dùng chung. Redis lỗi
thì xử lý tiếp bằng memory; cache không làm thay đổi kiểm tra quyền của endpoint.

| Cấu hình | Mặc định | Áp dụng |
|---|---:|---|
| `CACHE_ENABLED` | `true` | Bật/tắt result cache |
| `CACHE_EMBEDDING_TTL` | 86400 giây | Vector theo model và text gốc |
| `CACHE_LLM_TTL` | 3600 giây | Hiểu sản phẩm, thuộc tính nhanh/đầy đủ |
| `CACHE_CLASSIFICATION_TTL` | 600 giây | Kết quả phân loại hoàn chỉnh |
| `CACHE_CATALOG_TTL` | 3600 giây | Catalog option đã chuẩn hóa |
| `CACHE_MEMORY_ENTRIES` | 512 | Tổng số entry tối đa mỗi worker |
| `CACHE_MEMORY_BYTES` | 16777216 | Tổng payload memory tối đa mỗi worker |

Các biến này được đọc từ environment khi API khởi động. TTL bằng 0 bỏ qua cache
của tầng tương ứng. Redis entry có TTL; memory dùng LRU và không kéo dài TTL khi
đọc từ Redis. Kết quả trả về là bản sao, tránh request sửa dữ liệu dùng chung.

## Điều kiện tái sử dụng

Khóa cache giữ nguyên title, description, price và chế độ xử lý; không bỏ dấu hay
xóa phủ định để gộp đầu vào. Khóa chứa hash của input, model và prompt.
Các kết quả phụ thuộc danh mục còn chứa phiên bản taxonomy; thuộc tính còn chứa
định nghĩa field/options và, với chế độ đầy đủ, ngày hiện tại để xử lý bảo hành.

Phiên bản taxonomy nằm tại `system_config.cache.taxonomy_version` trong PostgreSQL.
Ghi Category/CategoryField qua `SessionLocal` đổi phiên bản trong cùng transaction;
rollback không đổi phiên bản. Qdrant đổi phiên bản trước và sau mutation, kể cả
ghi một phần rồi lỗi. Worker kiểm tra phiên bản hiện tại trước khi tra cache;
không đọc được phiên bản thì bỏ qua cache phụ thuộc taxonomy.

Khi viết thêm đường ghi bằng raw SQL hoặc legacy bulk mappings, phải gọi
`bump_taxonomy_revision(db)` trong transaction hoặc đánh dấu
`db.info['taxonomy_changed'] = True` trước commit. Khi thay đổi thuật toán ngoài
prompt, tăng phiên bản pipeline/cache để tránh dùng kết quả của thuật toán cũ.

Request trùng được gộp trong mỗi worker. Redis chia sẻ kết quả đã hoàn tất giữa
các worker; chưa dùng khóa phân tán để gộp cache miss giữa nhiều worker.
LLM/Qdrant lỗi hoặc JSON hỏng vẫn có thể trả fallback, nhưng không lưu kết quả
thiếu do lỗi. Kết quả hợp lệ xác định rằng chưa biết thuộc tính có thể được cache.
Request phân loại/hiểu sản phẩm có ảnh bỏ qua result cache vì cùng URL có thể
trỏ đến nội dung ảnh mới. Embedding text vẫn có thể được tái sử dụng.

## Theo dõi

Admin gọi `GET /api/admin/system/cache/metrics` để xem hit, miss và hit rate theo
từng tầng. Số liệu có phạm vi worker và được đặt lại khi process khởi động lại.
Một classification hit bỏ qua các tầng LLM/embedding/retrieval bên trong, vì vậy
không cộng hit/miss các tầng để suy ra hit rate của toàn bộ request.

Kiểm thử: `python -m pytest tests/test_result_cache.py -q`.
