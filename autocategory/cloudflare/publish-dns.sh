#!/bin/sh
# Publish DNS only after the selected tunnel has at least one connector.
# This script never deletes a tunnel, connector, or DNS record.
set -eu

CF_API="https://api.cloudflare.com/client/v4"
RUNTIME="/cf-runtime"
METADATA_FILE="$RUNTIME/tunnel.json"
WAIT_SECONDS="${CF_CONNECTOR_WAIT_SECONDS:-180}"

for var in CF_API_TOKEN CF_ACCOUNT_ID CF_DOMAIN; do
  eval "value=\${$var:-}"
  if [ -z "$value" ]; then
    echo "ERROR: $var is required"
    exit 1
  fi
done

if [ ! -s "$METADATA_FILE" ]; then
  echo "ERROR: Missing tunnel metadata: $METADATA_FILE"
  exit 1
fi

TUNNEL_ID=$(jq -r '.tunnel_id // empty' "$METADATA_FILE")
HOSTNAME=$(jq -r '.hostname // empty' "$METADATA_FILE")
if [ -z "$TUNNEL_ID" ] || [ -z "$HOSTNAME" ]; then
  echo "ERROR: Invalid tunnel metadata"
  exit 1
fi

AUTH="Authorization: Bearer $CF_API_TOKEN"

api_call() {
  method="$1"
  path="$2"
  payload="${3:-}"
  if [ -n "$payload" ]; then
    curl -sS -X "$method" -H "$AUTH" -H "Content-Type: application/json" \
      "$CF_API/$path" --data "$payload"
  else
    curl -sS -X "$method" -H "$AUTH" "$CF_API/$path"
  fi
}

assert_success() {
  response="$1"
  label="$2"
  if ! echo "$response" | jq -e '.success == true' >/dev/null 2>&1; then
    echo "ERROR: Cloudflare API failed while $label"
    echo "$response" | jq -c '{errors, messages}' 2>/dev/null || echo "$response"
    exit 1
  fi
}

echo "==> Waiting for tunnel $TUNNEL_ID to have an active connector"
elapsed=0
while :; do
  if [ -n "${CLOUDFLARED_PID:-}" ] && ! kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
    echo "ERROR: cloudflared exited before the tunnel became ready; DNS was not changed."
    exit 1
  fi
  tunnel=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID")
  assert_success "$tunnel" "checking tunnel status"
  tunnel_status=$(echo "$tunnel" | jq -r '.result.status // "unknown"')
  connections=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/connections")
  assert_success "$connections" "checking tunnel connections"
  connector_count=$(echo "$connections" | jq -r '.result | length')
  case "$tunnel_status" in
    healthy|degraded)
      if [ "$connector_count" -gt 0 ]; then
        echo "==> Tunnel status=$tunnel_status, connectors=$connector_count"
        break
      fi
      ;;
  esac
  if [ "$elapsed" -ge "$WAIT_SECONDS" ]; then
    echo "ERROR: Tunnel did not become ready within ${WAIT_SECONDS}s (status=$tunnel_status, connectors=$connector_count); DNS was not changed."
    exit 1
  fi
  sleep 3
  elapsed=$((elapsed + 3))
done

echo "==> Resolving zone for $CF_DOMAIN"
zone_response=$(api_call GET "zones?name=$CF_DOMAIN")
assert_success "$zone_response" "resolving zone"
zone_id=$(echo "$zone_response" | jq -r '.result[0].id // empty')
if [ -z "$zone_id" ]; then
  echo "ERROR: Cloudflare zone not found: $CF_DOMAIN"
  exit 1
fi

echo "==> Upserting DNS CNAME $HOSTNAME"
dns_response=$(api_call GET "zones/$zone_id/dns_records?name=$HOSTNAME")
assert_success "$dns_response" "reading DNS record"
record_count=$(echo "$dns_response" | jq -r '.result | length')
if [ "$record_count" -gt 1 ]; then
  echo "ERROR: Multiple DNS records exist for $HOSTNAME; DNS was not changed."
  exit 1
fi

record_id=$(echo "$dns_response" | jq -r '.result[0].id // empty')
record_type=$(echo "$dns_response" | jq -r '.result[0].type // empty')
target="$TUNNEL_ID.cfargotunnel.com"
dns_payload=$(jq -n --arg name "$HOSTNAME" --arg content "$target" \
  '{type:"CNAME", name:$name, content:$content, proxied:true, ttl:1}')

if [ -n "$record_id" ]; then
  if [ "$record_type" != "CNAME" ]; then
    echo "ERROR: $HOSTNAME already exists as $record_type; DNS was not changed."
    exit 1
  fi
  dns_update=$(api_call PUT "zones/$zone_id/dns_records/$record_id" "$dns_payload")
else
  dns_update=$(api_call POST "zones/$zone_id/dns_records" "$dns_payload")
fi
assert_success "$dns_update" "upserting DNS record"

echo "OK: https://$HOSTNAME -> $target"
