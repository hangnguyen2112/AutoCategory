#!/bin/sh
# Idempotent setup for a remotely-managed Cloudflare Tunnel.
# Multiple Docker hosts run the same tunnel token as cloudflared replicas.
# This script NEVER deletes a tunnel or DNS record.
set -eu

CF_API="https://api.cloudflare.com/client/v4"
TUNNEL_NAME="${CF_TUNNEL_NAME:-autocategory-ha}"
TUNNEL_ID="${CF_TUNNEL_ID:-}"
HOSTNAME="${CF_SUBDOMAIN}.${CF_DOMAIN}"
ORIGIN_SERVICE="${CF_ORIGIN_SERVICE:-http://nginx:80}"
RUNTIME="/cf-runtime"
TOKEN_FILE="$RUNTIME/tunnel-token"
METADATA_FILE="$RUNTIME/tunnel.json"

for var in CF_API_TOKEN CF_ACCOUNT_ID CF_SUBDOMAIN CF_DOMAIN; do
  eval "value=\${$var:-}"
  if [ -z "$value" ]; then
    echo "ERROR: $var is required"
    exit 1
  fi
done

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

mkdir -p "$RUNTIME"
created=0

if [ -n "$TUNNEL_ID" ]; then
  echo "==> Reusing pinned tunnel $TUNNEL_ID"
  tunnel_response=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID")
  assert_success "$tunnel_response" "reading pinned tunnel"
  config_source=$(echo "$tunnel_response" | jq -r '.result.config_src // empty')
else
  echo "==> Looking for remotely-managed tunnel '$TUNNEL_NAME'"
  list_response=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel?name=$TUNNEL_NAME&is_deleted=false")
  assert_success "$list_response" "listing tunnels"
  remote_count=$(echo "$list_response" | jq -r --arg name "$TUNNEL_NAME" \
    '[.result[] | select(.name == $name and .config_src == "cloudflare")] | length')

  if [ "$remote_count" -gt 1 ]; then
    echo "ERROR: Found $remote_count remotely-managed tunnels named '$TUNNEL_NAME'."
    echo "Set CF_TUNNEL_ID to select one explicitly. No Cloudflare resource was changed."
    exit 1
  fi

  TUNNEL_ID=$(echo "$list_response" | jq -r --arg name "$TUNNEL_NAME" \
    '.result[] | select(.name == $name and .config_src == "cloudflare") | .id' | head -n 1)

  if [ -z "$TUNNEL_ID" ]; then
    local_id=$(echo "$list_response" | jq -r --arg name "$TUNNEL_NAME" \
      '.result[] | select(.name == $name and .config_src == "local") | .id' | head -n 1)
    if [ -n "$local_id" ]; then
      echo "ERROR: Tunnel '$TUNNEL_NAME' exists but is locally managed ($local_id)."
      echo "No Cloudflare resource was changed. Create a remotely-managed tunnel with"
      echo "a different CF_TUNNEL_NAME, or set CF_TUNNEL_ID to an existing remote tunnel."
      exit 1
    fi

    echo "==> Creating remotely-managed tunnel '$TUNNEL_NAME'"
    create_payload=$(jq -n --arg name "$TUNNEL_NAME" '{name:$name, config_src:"cloudflare"}')
    create_response=$(api_call POST "accounts/$CF_ACCOUNT_ID/cfd_tunnel" "$create_payload")
    assert_success "$create_response" "creating tunnel"
    TUNNEL_ID=$(echo "$create_response" | jq -r '.result.id // empty')
    created=1
  fi
  config_source="cloudflare"
fi

if [ "$config_source" != "cloudflare" ]; then
  echo "ERROR: Tunnel $TUNNEL_ID is not remotely managed (config_src=$config_source)."
  echo "No Cloudflare resource was changed."
  exit 1
fi

echo "==> Updating remote ingress for $HOSTNAME"
if [ "$created" -eq 1 ]; then
  existing_ingress='[]'
else
  config_response=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations")
  assert_success "$config_response" "reading tunnel configuration"
  existing_ingress=$(echo "$config_response" | jq -c '.result.config.ingress // []')
fi

merged_ingress=$(echo "$existing_ingress" | jq -c \
  --arg hostname "$HOSTNAME" --arg service "$ORIGIN_SERVICE" '
  [.[] | select((.hostname // "") != $hostname and (.service // "") != "http_status:404")]
  + [{hostname:$hostname, service:$service}, {service:"http_status:404"}]')
config_payload=$(jq -n --argjson ingress "$merged_ingress" '{config:{ingress:$ingress}}')
config_update=$(api_call PUT "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations" "$config_payload")
assert_success "$config_update" "updating tunnel configuration"

echo "==> Fetching shared replica token"
token_response=$(api_call GET "accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/token")
assert_success "$token_response" "fetching tunnel token"
tunnel_token=$(echo "$token_response" | jq -r '.result // empty')
if [ -z "$tunnel_token" ]; then
  echo "ERROR: Cloudflare returned an empty tunnel token"
  exit 1
fi
umask 077
printf '%s' "$tunnel_token" > "$TOKEN_FILE"
jq -n --arg id "$TUNNEL_ID" --arg name "$TUNNEL_NAME" --arg hostname "$HOSTNAME" \
  '{tunnel_id:$id, tunnel_name:$name, hostname:$hostname}' > "$METADATA_FILE"

echo "OK: tunnel=$TUNNEL_ID hostname=https://$HOSTNAME"
echo "The DNS publisher will wait for a connector before upserting the CNAME."
