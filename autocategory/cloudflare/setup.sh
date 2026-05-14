#!/bin/sh
# Cloudflare Tunnel auto-setup – chạy trong Docker, đọc từ env, ghi ra /cf-runtime
set -e

CF_API="https://api.cloudflare.com/client/v4"
TUNNEL_NAME="${CF_TUNNEL_NAME:-autocategory}"
HOSTNAME="${CF_SUBDOMAIN}.${CF_DOMAIN}"
RUNTIME="/cf-runtime"
CREDS="$RUNTIME/credentials.json"
CONFIG="$RUNTIME/config.yml"

# ── Validate ────────────────────────────────────────────────────────────────
for var in CF_API_TOKEN CF_ACCOUNT_ID CF_SUBDOMAIN CF_DOMAIN; do
  eval "val=\$$var"
  if [ -z "$val" ]; then
    echo "ERROR: $var chua duoc set trong .env"
    exit 1
  fi
done

AUTH="Authorization: Bearer $CF_API_TOKEN"

cf_get() { curl -sf -H "$AUTH" "$CF_API/$1"; }
cf_put() { curl -sf -X PUT  -H "$AUTH" -H "Content-Type: application/json" "$CF_API/$1" -d "$2"; }
cf_del() { curl -sf -X DELETE -H "$AUTH" "$CF_API/$1" > /dev/null 2>&1 || true; }

cf_post_verbose() {
  # Returns full response + HTTP code on separate line (no -f so body is shown on 4xx/5xx)
  curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST -H "$AUTH" -H "Content-Type: application/json" \
    "$CF_API/$1" -d "$2" || true
}

mkdir -p "$RUNTIME"

# ── 1. Zone ID ───────────────────────────────────────────────────────────────
echo "==> 1/4  Zone ID cho $CF_DOMAIN ..."
zone_id=$(cf_get "zones?name=$CF_DOMAIN" | jq -r '.result[0].id // empty')
if [ -z "$zone_id" ]; then
  echo "ERROR: Khong tim thay zone '$CF_DOMAIN' tren Cloudflare."
  exit 1
fi
echo "     Zone ID: $zone_id"

# ── 2. Tunnel ────────────────────────────────────────────────────────────────
echo "==> 2/4  Tunnel '$TUNNEL_NAME' ..."

# List existing tunnels
list_resp=$(curl -sf -w "\nHTTP_CODE:%{http_code}" -H "$AUTH" \
  "$CF_API/accounts/$CF_ACCOUNT_ID/cfd_tunnel?name=$TUNNEL_NAME&is_deleted=false") || true
list_http=$(echo "$list_resp" | grep "HTTP_CODE:" | sed 's/HTTP_CODE://')
list_json=$(echo "$list_resp" | grep -v "HTTP_CODE:")
echo "     List tunnels: HTTP $list_http"
if [ "$list_http" != "200" ]; then
  echo "ERROR: Tunnel list API failed (HTTP $list_http): $list_json"
  exit 1
fi
tunnel_id=$(echo "$list_json" | jq -r '.result[0].id // empty')
echo "     tunnel_id=[$tunnel_id]"
secret=""

# Reuse neu tunnel ton tai va credentials khop
if [ -n "$tunnel_id" ] && [ -f "$CREDS" ]; then
  stored_id=$(jq -r '.TunnelID // empty' "$CREDS" 2>/dev/null || true)
  if [ "$stored_id" = "$tunnel_id" ]; then
    secret=$(jq -r '.TunnelSecret' "$CREDS")
    echo "     Reuse tunnel: $tunnel_id"
  fi
fi

# Tao moi neu chua co hoac khong khop
if [ -z "$secret" ]; then
  echo "     Creating new tunnel..."
  # Xoa tunnel cu cung ten neu co
  for tid in $(echo "$list_json" | jq -r '.result[].id // empty'); do
    cf_del "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$tid"
    echo "     Removed stale tunnel: $tid"
  done

  secret=$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -d '\n')
  echo "     secret len=${#secret}"

  create_resp=$(cf_post_verbose "accounts/$CF_ACCOUNT_ID/cfd_tunnel" \
    "{\"name\":\"$TUNNEL_NAME\",\"config_src\":\"local\",\"tunnel_secret\":\"$secret\"}")
  create_http=$(echo "$create_resp" | grep "HTTP_CODE:" | sed 's/HTTP_CODE://')
  create_json=$(echo "$create_resp" | grep -v "HTTP_CODE:")
  echo "     Create tunnel: HTTP $create_http"

  if [ "$create_http" != "200" ]; then
    echo "ERROR: Create tunnel failed (HTTP $create_http):"
    echo "$create_json"
    exit 1
  fi

  tunnel_id=$(echo "$create_json" | jq -r '.result.id // empty')
  if [ -z "$tunnel_id" ]; then
    echo "ERROR: No tunnel_id in response:"
    echo "$create_json"
    exit 1
  fi
  echo "     Created tunnel: $tunnel_id"
fi

# ── 3. Ghi credentials.json ──────────────────────────────────────────────────
echo "==> 3/4  Ghi config files ..."
cat > "$CREDS" <<EOF
{
  "AccountTag": "$CF_ACCOUNT_ID",
  "TunnelSecret": "$secret",
  "TunnelID": "$tunnel_id"
}
EOF

cat > "$CONFIG" <<EOF
tunnel: $tunnel_id
credentials-file: /cf-runtime/credentials.json

ingress:
  - hostname: $HOSTNAME
    service: http://nginx:80
  - service: http_status:404
EOF
echo "     Wrote $CREDS"
echo "     Wrote $CONFIG"

# ── 4. DNS CNAME ─────────────────────────────────────────────────────────────
echo "==> 4/4  DNS CNAME $HOSTNAME ..."
cname_val="${tunnel_id}.cfargotunnel.com"
dns_payload="{\"type\":\"CNAME\",\"name\":\"$HOSTNAME\",\"content\":\"$cname_val\",\"proxied\":true,\"ttl\":1}"

dns_json=$(cf_get "zones/$zone_id/dns_records?name=$HOSTNAME&type=CNAME")
record_id=$(echo "$dns_json" | jq -r '.result[0].id // empty')

if [ -n "$record_id" ]; then
  cf_put "zones/$zone_id/dns_records/$record_id" "$dns_payload" > /dev/null
  echo "     Updated CNAME: $HOSTNAME -> $cname_val"
else
  curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
    "$CF_API/zones/$zone_id/dns_records" -d "$dns_payload" > /dev/null
  echo "     Created CNAME: $HOSTNAME -> $cname_val"
fi

echo ""
echo "OK  Cloudflare setup xong! https://$HOSTNAME"