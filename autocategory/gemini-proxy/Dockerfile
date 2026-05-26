FROM python:3.11-slim

WORKDIR /app

# curl-cffi (used by gemini-webapi v2) bundles its own libcurl — no apt deps needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
