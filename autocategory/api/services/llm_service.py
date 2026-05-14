"""
LLM service – gọi llama-server (llama.cpp) OpenAI-compat API.
Hỗ trợ vision qua mmproj (image_url content type).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(base_url=settings.llama_base_url, timeout=180.0)

# ── helpers ────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Trích JSON từ response text, bỏ qua markdown code fence nếu có."""
    # Strip closed thinking blocks, then any unclosed ones (truncated at max_tokens)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _build_user_content(text: str, image_urls: list[str] | None) -> Any:
    """Tạo content dạng multipart nếu có ảnh, text-only nếu không."""
    if not image_urls:
        return text
    parts: list[dict] = [{"type": "text", "text": text}]
    for url in image_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


async def _chat(system: str, user_content: Any) -> str:
    """Gọi /v1/chat/completions (OpenAI-compat). user_content có thể là str hoặc list."""
    payload: dict[str, Any] = {
        "model": settings.llama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 512,
        "chat_template_kwargs": {"thinking": False},
    }
    resp = await _client.post("/v1/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ── Product Understanding ───────────────────────────────────────────────────────

SYSTEM_UNDERSTAND = """Bạn là hệ thống hiểu và chuẩn hóa bài đăng bán đồ cũ/rao vặt (như Chợ Tốt, Facebook Marketplace).

Context: Người dùng là người bán cá nhân, không phải shop chuyên nghiệp.
- Viết phong cách casual: "mình bán", "em đang dùng", "cần bán gấp"
- Có thể có typo, viết tắt (đt = điện thoại, đtdđ = di động, sxdh = sạc xài đều hơn, 99% = còn rất mới)
- Thông tin có thể thiếu hoặc không chuẩn
- Giá có thể ghi "thương lượng", "fix", "pass", "đẹp giá tốt"

Nhiệm vụ:
- Đọc title, description, price và ảnh nếu có.
- Hiểu ý người viết (xử lý typo, viết tắt phổ biến).
- Viết lại thành normalized_product_text rõ nghĩa để tìm danh mục.
- Tách suggested_title (ngắn gọn, CÓ THỂ GIỮ PHONG CÁCH RAO VẶT nếu phù hợp).
- Tách suggested_description (tự nhiên, thân thiện, như người bán cá nhân).
- Dựa vào ảnh để bổ sung thông tin nếu text chưa rõ.
- KHÔNG chọn danh mục, KHÔNG tự tạo category_id.
- Không bịa thương hiệu/model nếu không có bằng chứng.
- Nếu text và ảnh mâu thuẫn, phản ánh trong text_image_consistency.
- Trả về JSON hợp lệ, KHÔNG thêm giải thích ngoài JSON.

Khi có ảnh, hãy nhận diện và mô tả trong normalized_product_text:
- Thương hiệu/hãng: logo, tên in trên sản phẩm (Apple, Samsung, Nike, Honda...)
- Tình trạng: ngoại hình (trầy xước, móp, mới/cũ rõ ràng)
- Màu sắc chính của sản phẩm
- Dung lượng/kích thước/model nếu hiển thị trên màn hình hoặc nhãn
- Phụ kiện đi kèm nếu thấy trong ảnh (hộp, sạc, tai nghe...)
- Nhãn bảo hành, seal còn nguyên hay không
- Phiên bản (quốc tế/VN, màu sắc đặc trưng của từng phiên bản)
- Bất kỳ thông tin nào giúp xác định thuộc tính sản phẩm (loại, tình trạng, dung lượng, kết nối, bảo hành)

Viết tắt phổ biến cần hiểu:
- đt, dt = điện thoại
- đtdđ = di động
- xstd, sxdh = sạc xài đều hơn
- 99%, 98% = tình trạng máy (%)
- zin, nguyên zin = nguyên bản chưa sửa
- fullbox = đầy đủ hộp phụ kiện
- BH = bảo hành
- ram, rom = RAM, ROM
- core i5, i7 = Intel Core i5/i7
- ae = anh em
- fix = giá cố định không thương lượng
- pass = bán lại/chuyển nhượng

Output JSON format (chỉ JSON, không markdown):
{
  "normalized_product_text": string,
  "suggested_title": string,
  "suggested_description": string,
  "confidence": number (0.0-1.0),
  "text_image_consistency": "text_only" | "consistent" | "image_clarifies_text" | "image_only" | "conflict" | "unknown"
}"""


async def understand_product(
    title: str,
    description: str = "",
    price: float | None = None,
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    text_parts = [f"Title: {title}"]
    if description:
        text_parts.append(f"Description: {description}")
    if price is not None:
        text_parts.append(f"Price: {price}")

    user_text = "\n".join(text_parts)
    user_content = _build_user_content(user_text, image_urls)

    raw = await _chat(SYSTEM_UNDERSTAND, user_content)
    logger.info("LLM raw response: %s", raw[:500])
    result = _extract_json(raw)
    logger.info("Extracted JSON: %s", result)
    if not result:
        logger.warning("LLM understand_product returned non-JSON: %s", raw[:200])
        return {
            "normalized_product_text": title,
            "suggested_title": title,
            "suggested_description": description or "",
            "confidence": 0.3,
            "text_image_consistency": "text_only" if not image_urls else "unknown",
        }
    return result


# ── Category Rerank ─────────────────────────────────────────────────────────────

SYSTEM_RERANK = """Bạn là hệ thống phân loại danh mục bài đăng cho chợ rao vặt/bán đồ cũ.

Context: Người đăng là người bán cá nhân, không phải shop.
- Bài viết có thể casual, thiếu thông tin
- Tập trung vào bản chất sản phẩm, không phải cách viết
- Ví dụ: "đt cũ" → Điện thoại cũ, "laptop sinh viên" → Laptop/Máy tính xách tay

Nhiệm vụ:
- Chọn category phù hợp nhất cho bài đăng.
- CHỈ được chọn category_id trong danh sách ứng viên được cung cấp.
- KHÔNG tự tạo category mới.
- Ưu tiên danh mục con cụ thể nhất.
- Hiểu ý người viết qua ngữ cảnh (không cần viết chuẩn).
- Nếu không đủ thông tin, trả confidence thấp (< 0.55).
- Trả về JSON hợp lệ, KHÔNG thêm giải thích ngoài JSON.

Output JSON format (chỉ JSON, không markdown):
{
  "category_id": number | null,
  "confidence": number (0.0-1.0),
  "reason": string,
  "alternatives": [
    {"category_id": number, "confidence": number}
  ]
}"""


async def rerank_categories(
    product_embedding_text: str,
    understanding_confidence: float,
    text_image_consistency: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates_text = "\n".join(
        f"- id={c['category_id']} | {c.get('path', c.get('name'))}"
        for c in candidates
    )

    user_msg = f"""Bài đăng:
{product_embedding_text}

Thông tin hiểu bài đăng:
- product_understanding_confidence: {understanding_confidence}
- text_image_consistency: {text_image_consistency}

Danh mục ứng viên:
{candidates_text}"""

    raw = await _chat(SYSTEM_RERANK, user_msg)
    result = _extract_json(raw)
    if not result:
        logger.warning("LLM rerank_categories returned non-JSON: %s", raw[:200])
        best = candidates[0] if candidates else None
        return {
            "category_id": best["category_id"] if best else None,
            "confidence": 0.3,
            "reason": "LLM response parse error",
            "alternatives": [],
        }
    return result


# ── Field Value Suggestion ──────────────────────────────────────────────────────

SYSTEM_SUGGEST_FIELDS = """Bạn là hệ thống gợi ý giá trị thuộc tính sản phẩm cho bài đăng rao vặt Việt Nam.
Dựa vào thông tin sản phẩm và danh sách trường cần điền, hãy gợi ý giá trị phù hợp nhất.

Quy tắc:
- Với field type "select" hoặc "radio": chỉ được chọn đúng một trong các giá trị options (trả về value, không phải label).
- Với field type "text": tạo nội dung ngắn gọn phù hợp.
- Nếu không đủ thông tin để đoán chắc chắn, trả về null cho field đó.
- Chỉ trả về JSON, không giải thích thêm.
- QUAN TRỌNG: Trả về đúng chính xác chuỗi value như trong options=[], không tự thêm bớt hay dịch sang ngôn ngữ khác.

Giải mã từ lóng tiếng Việt (dùng khi điền trường Tình trạng / condition):
- "zin", "nguyên zin", "máy zin", "full zin" = máy ĐÃ QUA SỬ DỤNG nhưng còn nguyên bản, chưa qua sửa chữa → chọn option có nghĩa "đã sử dụng, chưa sửa chữa"
- "pin X%" với X < 100 = máy đã qua sử dụng, chưa sửa chữa (trừ khi có dấu hiệu sửa chữa khác)
- "like new", "99%", "98%", "mới 99%", "lướt web" = đã qua sử dụng, gần như mới → chọn option "đã sử dụng, chưa sửa chữa"
- "mới 100%", "chưa kích hoạt", "còn seal", "fullseal", "new 100%" = máy mới hoàn toàn → chọn option "mới"
- "bán lại", "pass", "thanh lý" = đã qua sử dụng
- "cấn", "móp", "trầy", "vỡ màn" = đã qua sử dụng, có hư hỏng → option "có lỗi"

Màu sắc (mau_sac): Trả về tên màu tiếng Việt đơn giản đúng với options. Ví dụ: "màu vàng (Gold)" → "Vàng", "màu xanh Sierra Blue" → "Xanh dương".

Format trả về:
{"field_key": "value_hoặc_null", ...}"""


def _compute_warranty_hint(text: str, today: "datetime") -> str:
    """Parse ngày hết hạn bảo hành từ text, so sánh với today, trả về hint rõ ràng."""
    from datetime import datetime
    combined = text.lower()
    # Patterns: "BH đến 6/2025", "bảo hành đến tháng 3/2026", "hết hạn BH 12/2025"
    patterns = [
        r'(?:b[aả]o\s*h[aà]nh|\bbh\b)[^\d]{0,20}(?:th[aá]ng\s*)?(\d{1,2})[/\-](\d{4})',
        r'(?:đến|hết|tới|den|het|toi)[^\d]{0,10}(?:th[aá]ng\s*)?(\d{1,2})[/\-](\d{4})',
        r'(?:th[aá]ng\s*)?(\d{1,2})[/\-](\d{4})\s*(?:b[aả]o\s*h[aà]nh|\bbh\b)',
    ]
    for pat in patterns:
        m = re.search(pat, combined)
        if m:
            try:
                month, year = int(m.group(1)), int(m.group(2))
                if 1 <= month <= 12 and 2000 <= year <= 2100:
                    if today.year > year or (today.year == year and today.month > month):
                        return f"ĐÃ HẾT bảo hành (hết hạn {month}/{year}, hôm nay {today.strftime('%d/%m/%Y')})"
                    else:
                        return f"CÒN bảo hành (hết hạn {month}/{year}, hôm nay {today.strftime('%d/%m/%Y')})"
            except ValueError:
                continue
    return ""


def _prefilter_conditional_fields(fields: list[dict], title: str, description: str) -> list[dict]:
    """Với các nhóm field conditional cùng parent (vd: dong_may_apple, dong_may_dell, dong_may_asus
    đều conditional on field 'hang'), detect brand từ title/description và chỉ giữ lại field phù hợp.
    Giảm đáng kể số token cần truyền vào LLM.

    Thuật toán scoring cho mỗi field trong nhóm:
    - +10 nếu parent_field_value (brand name) xuất hiện trong text
    - +5 nếu bất kỳ option value nào của field match với text (match dài hơn ưu tiên hơn)
    Nếu nhóm có winner rõ ràng (score > 0) → chỉ giữ field đó, drop hết field còn lại trong nhóm.
    Nếu không detect được → giữ nguyên tất cả (LLM tự chọn, cap 15 options mỗi field).
    """
    from collections import defaultdict

    combined = f"{title} {description}".lower()

    # Tách conditional fields (có parent_field_id) và non-conditional
    parent_groups: dict[str, list[dict]] = defaultdict(list)
    non_conditional: list[dict] = []

    for f in fields:
        pid = f.get("parent_field_id")
        if pid is not None:
            parent_groups[str(pid)].append(f)
        else:
            non_conditional.append(f)

    result = list(non_conditional)

    for pid, group in parent_groups.items():
        if len(group) <= 1:
            result.extend(group)
            continue

        # Score từng field trong nhóm
        best_score = 0
        best_field = None

        for f in group:
            score = 0

            # Heuristic 1: parent_field_value (brand) xuất hiện trong text
            pval = (f.get("parent_field_value") or "").lower().strip()
            if pval and pval in combined:
                score += 10

            # Heuristic 2: option values/labels của field match với text
            # Ưu tiên match dài hơn (tránh "HP" match trong "PHP", "Asus" match "Asus ROG")
            opts = f.get("field_options") or []
            best_match_len = 0
            for o in opts:
                oval = (o.get("value") or "").lower().strip()
                if oval and len(oval) >= 4 and oval in combined:
                    if len(oval) > best_match_len:
                        best_match_len = len(oval)
            if best_match_len >= 4:
                # Score tỉ lệ thuận với độ dài match (match dài hơn = chắc hơn)
                score += min(5 + best_match_len // 4, 15)

            if score > best_score:
                best_score = score
                best_field = f

        if best_score > 0 and best_field is not None:
            logger.debug(
                "_prefilter: parent=%s → kept '%s' (score=%d), dropped %d sibling fields",
                pid, best_field.get("field_key"), best_score, len(group) - 1,
            )
            result.append(best_field)
        else:
            # Không detect được brand → giữ tất cả, cap 15 options/field để bảo vệ token limit
            result.extend(group)

    return result


async def suggest_field_values(
    title: str,
    description: str,
    fields: list[dict],
) -> dict[str, str | None]:
    """Gợi ý giá trị cho các fields của một danh mục dựa vào thông tin sản phẩm.
    Nếu nhiều fields, gọi LLM theo batch để tránh vượt ngưỡng token.
    """
    if not fields:
        return {}

    from datetime import datetime as _dt
    today = _dt.now()
    today_str = today.strftime("%d/%m/%Y")

    # Pre-compute warranty status from text (Python is reliable, LLM is not)
    warranty_hint = _compute_warranty_hint(f"{title} {description or ''}", today)
    warranty_note = ""
    if warranty_hint:
        warranty_note = f"\n\n[KẾT QUẢ TÍNH TOÁN BẢO HÀNH - ĐÃ XÁC NHẬN]: {warranty_hint}\nVới field bảo hành, PHẢI dùng kết quả tính toán trên, không tự suy đoán."

    # Smart-filter: for groups of conditional fields sharing the same parent (e.g. dong_may_apple /
    # dong_may_dell / dong_may_asus all conditional on brand), detect which one applies from the
    # product text and drop the rest. This can cut hundreds of irrelevant options from the prompt.
    fields = _prefilter_conditional_fields(fields, title, description or "")

    # Batch fields to avoid exceeding llama ctx-size (8192 tokens)
    # ~25 fields per batch is safe given options can be verbose
    BATCH_SIZE = 25
    all_results: dict[str, str | None] = {}

    for batch_start in range(0, len(fields), BATCH_SIZE):
        batch = fields[batch_start : batch_start + BATCH_SIZE]

        fields_text_parts = []
        for f in batch:
            opts = f.get("field_options") or []
            if opts:
                # Show up to 50 options for detected fields, fall back to 15 for unfiltered large lists
                # After _prefilter_conditional_fields, brand-matched fields keep all options (≤50 shown);
                # unmatched fallback fields still cap at 15 to protect the 8192-token limit.
                max_opts = min(len(opts), 50) if len(opts) <= 50 else 15
                opts_str = ", ".join(f"'{o.get('value')}' ({o.get('label')})" for o in opts[:max_opts])
                fields_text_parts.append(
                    f"- {f['field_key']} [{f['field_type']}] \"{f['field_label']}\": options=[{opts_str}]"
                )
            else:
                fields_text_parts.append(
                    f"- {f['field_key']} [{f['field_type']}] \"{f['field_label']}\""
                )

        fields_text = "\n".join(fields_text_parts)

        user_msg = f"""Ngày hôm nay: {today_str}
Thông tin sản phẩm:
Tiêu đề: {title}
Mô tả: {description or '(không có)'}

Các trường cần gợi ý giá trị:
{fields_text}{warranty_note}

Hãy trả về JSON với key là field_key và value là giá trị phù hợp nhất (hoặc null nếu không đủ thông tin)."""

        try:
            raw = await _chat(SYSTEM_SUGGEST_FIELDS, user_msg)
            result = _extract_json(raw)
            if result:
                known_keys = {f["field_key"] for f in batch}
                all_results.update({k: v for k, v in result.items() if k in known_keys})
            else:
                logger.warning("suggest_field_values batch %d returned non-JSON: %s", batch_start, raw[:200])
        except Exception as exc:
            logger.warning("suggest_field_values batch %d failed: %s", batch_start, exc)

    return all_results


# ── Category Description Generation ──────────────────────────────────────────

# Prompt cho danh mục LÁ (leaf) — cần tựa keywords để match sản phẩm cụ thể
SYSTEM_DESCRIBE_LEAF = """Bạn là hệ thống tạo dữ liệu cho vector search trong sàn rao vặt tiếng Việt.

Nhiệm vụ: Với danh mục lá (leaf), tạo text keyword-dense để embed vào vector database.

Quy tắc BẮT BUỘC:
1. Liệt kê tên sản phẩm, dòng sản phẩm, thương hiệu đặc trưng cho ĐÚNG danh mục này
2. Thêm từ đồng nghĩa và cách viết tắt phổ biến nếu có (ví dụ: điện thoại → dt, đtdđ, smartphone)
3. CHỈ liệt kê sản phẩm thuộc danh mục này — KHÔNG liệt kê sản phẩm của danh mục anh/em hay danh mục cha
   Ví dụ: "RAM" → chỉ liệt kê RAM, không thêm CPU/SSD/mainboard
   Ví dụ: "Áo nam" → chỉ liệt kê các loại áo, không thêm quần/giày/túi
   Ví dụ: "Xe máy" → chỉ liệt kê xe máy, không thêm ô tô/xe đạp/phụ tùng
4. KHÔNG dùng các cụm chung xuất hiện ở mọi danh mục: bán lại, pass, thanh lý, mới 99%, máy cũ, zin, fullbox
5. Tối đa 40 từ
6. Chỉ trả về text thuần, không giải thích, không markdown

Ví dụ tốt cho "Điện thoại":
điện thoại smartphone di động dt đtdđ iPhone Samsung Galaxy Xiaomi Redmi Oppo Realme Vivo Nokia

Ví dụ tốt cho "RAM":
RAM DDR4 DDR5 LPDDR5 bộ nhớ thanh RAM Kingston HyperX Corsair Samsung 8GB 16GB 32GB

Ví dụ tốt cho "Áo nam":
áo nam áo thun áo sơ mi áo polo áo khoác áo phông áo len áo hoodie áo vest Uniqlo Zara H&M

Ví dụ xấu (KHÔNG làm):
"RAM" → RAM DDR4 card màn hình CPU SSD HDD mainboard (liệt kê lẫn danh mục khác)
"Áo nam" → áo quần giày túi thắt lưng phụ kiện thời trang nam (liệt kê cả danh mục cha)"""

# Prompt cho danh mục CHA (parent) — chỉ cần mô tả phạm vi nhóm để navigate
SYSTEM_DESCRIBE_PARENT = """Bạn là hệ thống tạo dữ liệu cho vector search trong sàn rao vặt tiếng Việt.

Nhiệm vụ: Với danh mục CHA (có danh mục con), tạo text ngắn mô tả phạm vi của nhóm.

Quy tắc:
1. Liệt kê 4–6 nhóm hàng/chủ đề chính trong danh mục này
2. Không đi sâu vào sản phẩm/model cụ thể (danh mục con sẽ phụ trách)
3. KHÔNG dùng: bán lại, pass, thanh lý, mới 99%, zin, fullbox
4. Tối đa 20 từ
5. Chỉ trả về text, không giải thích

Ví dụ tốt cho “Đồ điện tử”:
điện thoại laptop máy tính bảng thiết bị đeo thông minh máy ảnh tivi linh kiện phụ kiện điện tử"""


async def generate_category_description(
    category_name: str,
    category_path: str,
    field_labels: list[str],
    is_leaf: bool = True,
) -> str:
    """Sinh keyword-dense description cho embedding/vector search."""
    system_prompt = SYSTEM_DESCRIBE_LEAF if is_leaf else SYSTEM_DESCRIBE_PARENT

    if is_leaf:
        fields_hint = ""
        if field_labels:
            fields_hint = f"\nThuộc tính đặc trưng: {', '.join(field_labels[:8])}"
        user_msg = f"""Danh mục lá: {category_name}
Đường dẫn: {category_path}{fields_hint}"""
    else:
        user_msg = f"""Danh mục cha: {category_name}
Đường dẫn: {category_path}"""

    try:
        raw = await _chat(system_prompt, user_msg)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        raw = re.sub(r"<think>.*$", "", raw, flags=re.DOTALL).strip()
        raw = raw.strip('"').strip("'").strip()
        return raw[:400] if raw else ""
    except Exception as exc:
        logger.warning("generate_category_description failed for %s: %s", category_name, exc)
        return ""

