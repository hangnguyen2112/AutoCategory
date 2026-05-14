#!/usr/bin/env python3
"""
AutoCategory – Cloudflare Tunnel auto-setup
============================================
Chạy MỘT LẦN trước khi deploy production.
Script tự động:
  1. Lấy Zone ID từ domain
  2. Tạo tunnel (hoặc reuse nếu đã có)
  3. Ghi cloudflare/credentials.json
  4. Ghi cloudflare/config.yml
  5. Tạo/cập nhật DNS CNAME record

Điền vào .env:
  CF_API_TOKEN   API Token Cloudflare
                 Quyền cần thiết: Cloudflare Tunnel:Edit + DNS:Edit
                 Tạo tại: dash.cloudflare.com/profile/api-tokens
  CF_ACCOUNT_ID  Account ID (góc dưới bên phải sidebar dashboard)
  CF_SUBDOMAIN   Subdomain muốn dùng, VD: autocategory
  CF_DOMAIN      Domain của bạn, VD: yourdomain.com

Tùy chọn:
  CF_TUNNEL_NAME Tên tunnel (mặc định: autocategory)
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx chưa cài. Chạy: pip install httpx")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"
CF_DIR = ROOT / "cloudflare"
CF_DIR.mkdir(exist_ok=True)


# ── Load .env ──────────────────────────────────────────────────────────────
def _load_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


env = {**_load_env_file(ENV_FILE), **os.environ}

CF_API_TOKEN = env.get("CF_API_TOKEN", "").strip()
CF_ACCOUNT_ID = env.get("CF_ACCOUNT_ID", "").strip()
CF_SUBDOMAIN = env.get("CF_SUBDOMAIN", "").strip()
CF_DOMAIN = env.get("CF_DOMAIN", "").strip()
TUNNEL_NAME = env.get("CF_TUNNEL_NAME", "autocategory").strip()

# ── Validate ───────────────────────────────────────────────────────────────
missing = [
    k for k, v in [
        ("CF_API_TOKEN", CF_API_TOKEN),
        ("CF_ACCOUNT_ID", CF_ACCOUNT_ID),
        ("CF_SUBDOMAIN", CF_SUBDOMAIN),
        ("CF_DOMAIN", CF_DOMAIN),
    ]
    if not v
]
if missing:
    print(f"\nERROR: Thiếu biến trong .env: {', '.join(missing)}")
    print("  Xem .env.example để biết cách điền.\n")
    sys.exit(1)

FULL_HOSTNAME = f"{CF_SUBDOMAIN}.{CF_DOMAIN}"

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}
client = httpx.Client(
    base_url="https://api.cloudflare.com/client/v4",
    headers=HEADERS,
    timeout=30.0,
)


def _check(resp: httpx.Response, label: str) -> dict:
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {}
    if not data.get("success"):
        errors = data.get("errors", [])
        msg = "; ".join(e.get("message", str(e)) for e in errors)
        print(f"\nERROR [{label}]: {msg}")
        sys.exit(1)
    return data


# ── Step 1: Zone ID ────────────────────────────────────────────────────────
def get_zone_id(domain: str) -> str:
    resp = client.get("/zones", params={"name": domain})
    data = _check(resp, "get zone")
    zones = data.get("result", [])
    if not zones:
        print(f"\nERROR: Không tìm thấy zone cho '{domain}'.")
        print("  → Đảm bảo domain đã được thêm vào Cloudflare.\n")
        sys.exit(1)
    zone_id = zones[0]["id"]
    print(f"   Zone ID: {zone_id}")
    return zone_id


# ── Step 2: Tunnel ─────────────────────────────────────────────────────────
def get_or_create_tunnel(account_id: str, name: str) -> tuple[str, str]:
    """Return (tunnel_id, secret_b64). Tạo mới hoặc reuse nếu credentials.json còn."""
    creds_file = CF_DIR / "credentials.json"

    # Kiểm tra tunnel cùng tên đang active
    resp = client.get(
        f"/accounts/{account_id}/cfd_tunnel",
        params={"name": name, "is_deleted": "false"},
    )
    data = _check(resp, "list tunnels")
    tunnels = data.get("result", [])

    if tunnels and creds_file.exists():
        tunnel_id = tunnels[0]["id"]
        creds = json.loads(creds_file.read_text(encoding="utf-8"))
        if creds.get("TunnelID") == tunnel_id:
            print(f"   Reuse tunnel: {name} ({tunnel_id})")
            return tunnel_id, creds["TunnelSecret"]

    # Xoá tunnel cũ cùng tên nếu không còn credentials (tránh conflict)
    for t in tunnels:
        client.delete(f"/accounts/{account_id}/cfd_tunnel/{t['id']}")
        print(f"   Removed stale tunnel: {t['id']}")

    # Tạo mới
    secret = base64.b64encode(secrets.token_bytes(32)).decode()
    resp = client.post(
        f"/accounts/{account_id}/cfd_tunnel",
        json={"name": name, "config_src": "local", "tunnel_secret": secret},
    )
    data = _check(resp, "create tunnel")
    tunnel_id = data["result"]["id"]
    print(f"   Created tunnel: {name} ({tunnel_id})")
    return tunnel_id, secret


# ── Step 3: credentials.json ───────────────────────────────────────────────
def write_credentials(account_id: str, tunnel_id: str, secret: str) -> None:
    path = CF_DIR / "credentials.json"
    path.write_text(
        json.dumps(
            {"AccountTag": account_id, "TunnelSecret": secret, "TunnelID": tunnel_id},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"   Wrote {path.relative_to(ROOT)}")


# ── Step 4: config.yml ─────────────────────────────────────────────────────
def write_config(tunnel_id: str, hostname: str) -> None:
    config = (
        f"tunnel: {tunnel_id}\n"
        f"credentials-file: /etc/cloudflared/credentials.json\n"
        f"\n"
        f"ingress:\n"
        f"  - hostname: {hostname}\n"
        f"    service: http://nginx:80\n"
        f"  - service: http_status:404\n"
    )
    path = CF_DIR / "config.yml"
    path.write_text(config, encoding="utf-8")
    print(f"   Wrote {path.relative_to(ROOT)}")


# ── Step 5: DNS CNAME ──────────────────────────────────────────────────────
def upsert_cname(zone_id: str, subdomain: str, domain: str, tunnel_id: str) -> None:
    name = f"{subdomain}.{domain}"
    content = f"{tunnel_id}.cfargotunnel.com"
    payload = {"type": "CNAME", "name": name, "content": content, "proxied": True, "ttl": 1}

    resp = client.get(f"/zones/{zone_id}/dns_records", params={"name": name, "type": "CNAME"})
    data = _check(resp, "list dns")
    existing = data.get("result", [])

    if existing:
        record_id = existing[0]["id"]
        resp = client.put(f"/zones/{zone_id}/dns_records/{record_id}", json=payload)
        _check(resp, "update dns")
        print(f"   Updated CNAME: {name} → {content}")
    else:
        resp = client.post(f"/zones/{zone_id}/dns_records", json=payload)
        _check(resp, "create dns")
        print(f"   Created CNAME: {name} → {content}")


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n🚀 Cloudflare Tunnel Setup → https://{FULL_HOSTNAME}\n")

    print("1/4  Zone ID...")
    zone_id = get_zone_id(CF_DOMAIN)

    print("2/4  Tunnel...")
    tunnel_id, secret = get_or_create_tunnel(CF_ACCOUNT_ID, TUNNEL_NAME)

    print("3/4  Config files...")
    write_credentials(CF_ACCOUNT_ID, tunnel_id, secret)
    write_config(tunnel_id, FULL_HOSTNAME)

    print("4/4  DNS record...")
    upsert_cname(zone_id, CF_SUBDOMAIN, CF_DOMAIN, tunnel_id)

    print(f"""
✅  Setup xong!

Deploy:
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

Sau đó build index (lần đầu):
  curl -X POST https://{FULL_HOSTNAME}/api/admin/build-index

Truy cập:
  https://{FULL_HOSTNAME}          ← Test page
  https://{FULL_HOSTNAME}/api/docs ← API docs
""")


if __name__ == "__main__":
    main()
