FROM cloudflare/cloudflared:latest AS cloudflared

FROM debian:13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl jq \
    && rm -rf /var/lib/apt/lists/*
COPY --from=cloudflared /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY setup-ha.sh /setup-ha.sh
COPY publish-dns.sh /publish-dns.sh
COPY run-ha.sh /run-ha.sh
RUN chmod +x /setup-ha.sh /publish-dns.sh /run-ha.sh
CMD ["/run-ha.sh"]
