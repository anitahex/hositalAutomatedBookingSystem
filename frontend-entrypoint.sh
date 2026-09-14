#!/bin/sh
set -e

DOMAIN=165-232-178-215.sslip.io
CERT_DIR=/etc/letsencrypt/live/$DOMAIN

# nginx.conf's :443 block references $CERT_DIR/fullchain.pem and privkey.pem — nginx
# refuses to start at all if those files don't exist yet, but certbot's webroot method
# (certbot-entrypoint.sh) needs nginx already running on :80 to serve the ACME challenge
# before it can obtain the real certificate. Breaking that chicken-and-egg cycle: generate
# a throwaway self-signed placeholder here just so nginx has *something* to load and can
# start; it's untrusted (browser warning) but only exists until certbot's first
# successful run replaces this whole directory with the real, trusted certificate.
if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    echo "==> No certificate yet — generating a temporary self-signed placeholder so nginx can start..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN"
fi

# Graceful reload (spawns new worker processes, drains old ones — never drops active
# connections, including long-lived WebSocket audio-recording ones) so nginx picks up
# the real certificate once certbot obtains it, and any renewed certificate later,
# without ever needing a hard restart or cross-container signaling.
( while true; do sleep 300; nginx -s reload 2>/dev/null || true; done ) &

echo "==> Starting nginx..."
exec nginx -g "daemon off;"
