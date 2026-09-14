#!/bin/sh
set -e

DOMAIN=165-232-178-215.sslip.io
STAGING_FLAG=""
if [ "$LETSENCRYPT_STAGING" = "true" ]; then
    STAGING_FLAG="--staging"
fi

# frontend-entrypoint.sh may have already created a self-signed placeholder at this
# exact path so nginx could start — certbot refuses to manage a certificate lineage it
# didn't create itself, so clear the placeholder's directory first (only when there's no
# real certbot-managed renewal config for this domain yet, i.e. we've never actually
# succeeded before).
if [ ! -f "/etc/letsencrypt/renewal/$DOMAIN.conf" ] && [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "==> Clearing placeholder certificate directory so certbot can claim $DOMAIN..."
    rm -rf "/etc/letsencrypt/live/$DOMAIN" "/etc/letsencrypt/archive/$DOMAIN"
fi

echo "==> Requesting certificate for $DOMAIN (staging=${LETSENCRYPT_STAGING:-false})..."
certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" $STAGING_FLAG \
    --non-interactive --agree-tos -m "$LETSENCRYPT_EMAIL" \
    --cert-name "$DOMAIN" --keep-until-expiring

# Safe to re-run indefinitely: certbot renew only actually renews when the current
# certificate is within its renewal window (default ~30 days before expiry) — every
# other invocation is a fast no-op. frontend-entrypoint.sh's own 5-minute reload loop
# is what actually picks up a freshly renewed certificate; this loop's only job is to
# ask certbot to check.
trap exit TERM
while :; do
    sleep 12h
    certbot renew --webroot -w /var/www/certbot --quiet $STAGING_FLAG
done
