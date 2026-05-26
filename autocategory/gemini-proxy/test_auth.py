import asyncio
from gemini_webapi import GeminiClient

async def main():
    c = GeminiClient("fake_invalid_xxxxx", None)
    await c.init(timeout=15, auto_close=False, auto_refresh=False)
    r = await c.generate_content("goi gemini toi dang dung la gi")
    print(r.text[:300])
    await c.close()

asyncio.run(main())
