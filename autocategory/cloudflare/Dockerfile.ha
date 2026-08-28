FROM alpine:3.20
RUN apk add --no-cache curl jq
COPY setup-ha.sh /setup-ha.sh
COPY publish-dns.sh /publish-dns.sh
RUN chmod +x /setup-ha.sh /publish-dns.sh
CMD ["/setup-ha.sh"]
