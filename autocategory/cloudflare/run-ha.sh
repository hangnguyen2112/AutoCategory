#!/bin/sh
# One-container lifecycle: resolve/create tunnel, run connector, publish DNS,
# then supervise cloudflared for the lifetime of the container.
set -eu

PID_FILE="/tmp/cloudflared.pid"
TOKEN_FILE="/cf-runtime/tunnel-token"
cloudflared_pid=""

stop_cloudflared() {
  if [ -n "$cloudflared_pid" ] && kill -0 "$cloudflared_pid" 2>/dev/null; then
    kill -TERM "$cloudflared_pid" 2>/dev/null || true
    wait "$cloudflared_pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
}

on_signal() {
  stop_cloudflared
  exit 0
}

trap on_signal INT TERM

/setup-ha.sh

echo "==> Starting cloudflared connector"
/usr/local/bin/cloudflared --no-autoupdate tunnel run --token-file "$TOKEN_FILE" &
cloudflared_pid=$!
printf '%s\n' "$cloudflared_pid" > "$PID_FILE"

if ! CLOUDFLARED_PID="$cloudflared_pid" /publish-dns.sh; then
  echo "ERROR: DNS publish failed; stopping connector so Docker can retry cleanly."
  stop_cloudflared
  exit 1
fi

echo "==> Tunnel is ready; supervising cloudflared pid=$cloudflared_pid"
set +e
wait "$cloudflared_pid"
exit_code=$?
set -e
rm -f "$PID_FILE"
echo "ERROR: cloudflared exited with code $exit_code"
exit "$exit_code"
