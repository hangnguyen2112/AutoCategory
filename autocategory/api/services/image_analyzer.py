"""
Image Analyzer Service – Generate content từ product images cho rao vặt đồ cũ
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import settings
from services.llm_service import get_llm_client, is_lm_studio, _extract_json, post_completions_with_retry

logger = logging.getLogger(__name__)


def _build_multipart_content(text: str, image_urls: list[str]) -> list[dict]:
    """Build multipart content với text + images"""
    content = [{"type": "text", "text": text}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


async def generate_from_images(
    image_urls: list[str],
    existing_title: str = "",
    existing_description: str = "",
) -> dict[str, Any]:
    """
    Sinh title, description từ ảnh sản phẩm theo phong cách rao vặt đồ cũ
    """

    system_prompt = """Bạn là chuyên gia phân tích sản phẩm và viết bài đăng bán hàng cá nhân trên chợ online Việt Nam (Chợ Tốt, Facebook Marketplace).

Nhiệm vụ: Xem ảnh sản phẩm và tạo tiêu đề + mô tả + thông tin chi tiết cho bài đăng.

═══ TIÊU ĐỀ ═══
- Ngắn gọn, đủ thông tin: thương hiệu + model/dòng + dung lượng/kích thước/màu + tình trạng
- Tự nhiên như người bán cá nhân viết
- Ví dụ: "iPhone 15 Pro Max 256GB xanh đẹp như mới", "Laptop Dell Inspiron 15 core i5 gen12 ram 16G SSD 512 mới 99%"

═══ MÔ TẢ (QUAN TRỌNG - phải đầy đủ thông tin) ═══
Mô tả PHẢI bao gồm TẤT CẢ những gì nhìn thấy/biết được:
1. Thương hiệu & model chính xác (Apple/Samsung/Dell/Nike/Honda...)
2. Thông số kỹ thuật: dung lượng, RAM, màn hình, dung tích, kích thước, màu sắc chính xác
3. Phiên bản: quốc tế/VN, năm sản xuất, thế hệ (gen), variant
4. Tình trạng thực tế từ ảnh: % còn mới, có trầy xước không, móp méo, màn hình, pin %
5. Phụ kiện đi kèm thấy trong ảnh: hộp, sạc, cáp, tai nghe, bao da, giấy bảo hành
6. Bảo hành: seal còn nguyên / BH hãng / shop / hết BH
7. Lý do bán (tự nhiên): mua thừa, nâng cấp, không hợp, cần tiền...
Phong cách CASUAL thân thiện (dùng "mình", "em", "máy"), 4-7 câu. Đặt thông tin kỹ thuật vào đầu rồi mới tới tình trạng và lý do bán.

⚠️ QUY TẮC BẮT BUỘC – KHÔNG được vi phạm:
- KHÔNG dùng cụm "tùy ảnh", "hoặc ... tùy ảnh", "khoảng ... tùy", "không chắc"
- Nếu phân vân giữa 2 lựa chọn (VD: "Xám hoặc Đen") → chọn cái bạn THIÊN VỀ hơn và viết thẳng cái đó, không liệt kê cả 2
- Nếu không thấy rõ từ ảnh nhưng nhận ra được model sản phẩm → dùng kiến thức thực tế về sản phẩm đó ngoài thị trường để suy ra (VD: Lock&Lock LHC4249S chỉ có màu đen và dung tích 500ml → điền luôn)
- Nếu hoàn toàn không xác định được dù đã dùng kiến thức thực tế → BỎ QUA thông số đó
- Viết như người bán CHÍNH CHỦ đang rao — họ biết rõ sản phẩm của mình, không dùng từ mơ hồ

═══ DETECTED_ATTRIBUTES (thông tin máy móc để hệ thống đọc) ═══
Trích xuất CHÍNH XÁC từ ảnh, không đoán mò nếu không thấy rõ:
- brand: thương hiệu chính xác (Apple, Samsung, Dell, Nike, Honda, Sony...)
- model: tên model đầy đủ (iPhone 15 Pro Max, Galaxy S24 Ultra, Vios E 2019...)
- variant: dung lượng/kích thước/phiên bản (256GB, 16GB RAM, 1.5L, Size 42...)
- color: màu sắc chính xác (Natural Titanium, Đen, Đỏ cam...)
- condition: new | like_new | good | fair | poor (dựa vào ngoại quan ảnh)
- condition_detail: mô tả tình trạng ngắn gọn (pin 88%, không trầy, hộp đầy đủ...)
- accessories: danh sách phụ kiện thấy trong ảnh ["hộp", "sạc 20W", "cáp Lightning"]
- warranty: none | in_warranty | shop_warranty | unknown
- category_hint: gợi ý loại sản phẩm (Điện thoại/Laptop/Xe máy/Giày/...)
- extra: dict các thông tin kỹ thuật khác (screen_size, battery, storage, engine_cc...)

GỢI Ý GIÁ: Ước tính giá thị trường VNĐ theo tình trạng thực tế. Nếu không chắc để null.

OUTPUT JSON (chỉ JSON, không markdown):
{
  "title": "...",
  "description": "...",
  "detected_attributes": {
    "brand": "...",
    "model": "...",
    "variant": "...",
    "color": "...",
    "condition": "new|like_new|good|fair|poor",
    "condition_detail": "...",
    "accessories": [],
    "warranty": "none|in_warranty|shop_warranty|unknown",
    "category_hint": "...",
    "extra": {}
  },
  "price_suggestion": {
    "estimate": 10000000,
    "range": [9000000, 11000000],
    "reasoning": "..."
  }
}"""

    user_prompt = "Xem ảnh sản phẩm này và tạo bài đăng bán đồ cũ:"

    if existing_title:
        user_prompt += f"\n\nTiêu đề hiện có (có thể cải thiện): {existing_title}"
    if existing_description:
        user_prompt += f"\nMô tả hiện có (có thể cải thiện): {existing_description}"

    content = _build_multipart_content(user_prompt, image_urls)

    payload = {
        "model": get_llm_client()[1],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 3000,
    }

    try:
        data = await post_completions_with_retry(payload)
        result_text = data["choices"][0]["message"]["content"]

        # Extract JSON — also strips any reasoning blocks LM Studio may inject
        result = _extract_json(result_text)
        if result is None:
            raise ValueError(f"No valid JSON in response. finish_reason={data['choices'][0].get('finish_reason')}")
        return result

    except Exception as e:
        logger.error(f"Error generating from images: {e}")
        raise


async def validate_image_text_consistency(
    title: str,
    description: str,
    image_urls: list[str],
) -> dict[str, Any]:
    """
    Kiểm tra text có khớp với ảnh không
    """
    system_prompt = """Bạn là trợ lý kiểm tra bài đăng bán hàng.
So sánh nội dung text với ảnh, tìm mâu thuẫn hoặc không khớp.

Kiểm tra:
- Text nói sản phẩm A nhưng ảnh là sản phẩm B
- Màu sắc, model không khớp
- Tình trạng không khớp (text nói mới nhưng ảnh thấy cũ)

OUTPUT JSON:
{
  "is_consistent": true/false,
  "confidence": 0.0-1.0,
  "issues": ["Lỗi nghiêm trọng...", ...],
  "warnings": ["Cảnh báo nhỏ...", ...]
}"""

    user_prompt = f"""Tiêu đề: {title}
Mô tả: {description}

Kiểm tra xem ảnh có khớp với nội dung không?"""

    content = _build_multipart_content(user_prompt, image_urls)

    payload = {
        "model": get_llm_client()[1],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 1200,
    }

    try:
        data = await post_completions_with_retry(payload)
        result_text = data["choices"][0]["message"]["content"]

        result = _extract_json(result_text)
        if result is None:
            raise ValueError(f"No valid JSON in response. finish_reason={data['choices'][0].get('finish_reason')}")
        return result

    except Exception as e:
        logger.error(f"Error validating consistency: {e}")
        raise
