"""
Image Analyzer Service – Generate content từ product images cho rao vặt đồ cũ
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(base_url=settings.llama_base_url, timeout=180.0)


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

    system_prompt = """Bạn là người viết bài đăng bán hàng cá nhân trên chợ online (Chợ Tốt, Facebook Marketplace).

Phong cách: CASUAL, thân thiện, như người bình thường bán đồ cũ.
KHÔNG viết như shop chuyên nghiệp hay website bán hàng.

Nhiệm vụ: Xem ảnh sản phẩm và tạo tiêu đề + mô tả cho bài đăng.

YÊU CẦU TIÊU ĐỀ:
- Ngắn gọn, đủ thông tin (tên, đặc điểm nổi bật)
- Tự nhiên như người bán cá nhân viết
- Ví dụ: "iPhone 15 Pro Max 256GB đẹp như mới", "Laptop Dell core i5 ram 8G giá sinh viên"

YÊU CẦU MÔ TẢ:
- Thân thiện, tự nhiên (có thể dùng "mình", "em", "đang dùng")
- Mô tả tình trạng thực tế: còn mới %, dùng bao lâu, vì sao bán
- Có thể thêm: "Máy còn zin", "BH còn 10 tháng", "Fullbox", "Máy đẹp không trầy"
- Không quá dài dòng (3-5 câu là đủ)
- Có thể kết thúc bằng: "Máy đẹp giá tốt ạ", "Có fix cho ae thiện chí"

PHÁT HIỆN:
- Brand, model, màu sắc
- Tình trạng: mới/cũ/như mới (dựa vào ảnh)
- Phụ kiện kèm theo nếu thấy trong ảnh

GỢI Ý GIÁ:
- Ước tính giá thị trường (VNĐ)
- Nếu không chắc, để null

OUTPUT JSON (chỉ JSON, không markdown):
{
  "title": "...",
  "description": "...",
  "detected_attributes": {
    "brand": "...",
    "model": "...",
    "color": "...",
    "condition": "mới/cũ/như mới"
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
        "model": settings.llama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 800,
        "chat_template_kwargs": {"thinking": False},
    }

    try:
        resp = await _client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        result_text = data["choices"][0]["message"]["content"]

        # Extract JSON
        result = json.loads(result_text)
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
        "model": settings.llama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 512,
        "chat_template_kwargs": {"thinking": False},
    }

    try:
        resp = await _client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        result_text = data["choices"][0]["message"]["content"]

        result = json.loads(result_text)
        return result

    except Exception as e:
        logger.error(f"Error validating consistency: {e}")
        raise
