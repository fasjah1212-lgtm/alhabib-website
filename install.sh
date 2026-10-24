#!/bin/bash
# Puts the new Alhabib site live on the factory's own server (nginx).
# The old site is not deleted: its nginx settings are backed up and one command brings it back.
set -u
DOMAIN=alhabibfactory.com
NEW=/var/www/alhabib-new
ZIP=https://github.com/fasjah1212-lgtm/alhabib-website/archive/refs/heads/main.tar.gz
BK=/root/alhabib-backup-$(date +%Y%m%d-%H%M%S)

say()  { echo; echo ">>> $*"; }
stop() { echo; echo "XXXXX STOPPED: $* XXXXX"; echo "Nothing on the live site was changed."; exit 1; }
reload_nginx() { systemctl reload nginx 2>/dev/null || nginx -s reload; }

[ "$(id -u)" = 0 ] || stop "run as root"
command -v nginx >/dev/null || stop "nginx not found"

# 1. find the old site's nginx settings
OLD=$(grep -lE "server_name[^;]*$DOMAIN" /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf 2>/dev/null | head -1)
[ -n "$OLD" ] || stop "no nginx settings for $DOMAIN"
say "old site settings: $OLD"
grep -nE "server_name|proxy_pass|root |ssl_certificate|listen" "$OLD"
OTHERS=$(grep -hoE "server_name[^;]*" "$OLD" | tr ' \t' '\n\n' | grep -vE "^(server_name|)$" | grep -vE "^(www\.)?$DOMAIN$" | sort -u | tr '\n' ' ')
[ -z "$OTHERS" ] || stop "this file also serves: $OTHERS"
CERT=$(grep -m1 -E "^\s*ssl_certificate\s" "$OLD" | awk '{print $2}' | tr -d ';')
KEY=$(grep -m1 -E "^\s*ssl_certificate_key\s" "$OLD" | awk '{print $2}' | tr -d ';')
[ -n "$CERT" ] && [ -f "$CERT" ] && [ -n "$KEY" ] && [ -f "$KEY" ] || stop "SSL certificate not found"
say "certificate: $CERT"
V6=""; grep -q "\[::\]" "$OLD" && V6=yes

# 2. back up nginx
mkdir -p "$BK" && cp -a /etc/nginx "$BK/nginx" && cp -a "$OLD" "$BK/old-site.conf" || stop "backup failed"
say "backup: $BK"

# 3. download the new site
TMP=$(mktemp -d)
curl -fsSL -o "$TMP/site.tar.gz" "$ZIP" || stop "download failed"
tar -xzf "$TMP/site.tar.gz" -C "$TMP" || stop "unpack failed"
SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
[ -f "$SRC/index.html" ] && [ -f "$SRC/works.html" ] || stop "site files incomplete"
rm -rf "$SRC/src" "$SRC/README.md" "$SRC/install.sh" "$SRC/restore-old-site.sh" "$SRC/.htaccess"
[ -d "$NEW" ] && mv "$NEW" "$BK/previous-new-site"
mkdir -p "$(dirname "$NEW")" && mv "$SRC" "$NEW" && chmod -R a+rX "$NEW" || stop "copy failed"
say "new site files: $NEW ($(find "$NEW" -type f | wc -l) files)"

# 4. nginx settings for the new site, in the same folder the old ones were in
if [ "$(dirname "$OLD")" = /etc/nginx/conf.d ]; then CONF=/etc/nginx/conf.d/alhabib-new.conf; else CONF=/etc/nginx/sites-available/alhabib-new; fi
cat > "$CONF" <<EOF
# new Alhabib site (static files). Old settings saved in $BK
server {
  listen 80;
$( [ -n "$V6" ] && echo '  listen [::]:80;')
  server_name $DOMAIN www.$DOMAIN;
  location /.well-known/acme-challenge/ { root $NEW; }
  location / { return 301 https://$DOMAIN\$request_uri; }
}
server {
  listen 443 ssl;
$( [ -n "$V6" ] && echo '  listen [::]:443 ssl;')
  server_name www.$DOMAIN;
  ssl_certificate $CERT;
  ssl_certificate_key $KEY;
  return 301 https://$DOMAIN\$request_uri;
}
server {
  listen 443 ssl;
$( [ -n "$V6" ] && echo '  listen [::]:443 ssl;')
  server_name $DOMAIN;
  ssl_certificate $CERT;
  ssl_certificate_key $KEY;
  root $NEW;
  index index.html;
  location / { try_files \$uri \$uri/ \$uri.html =404; }
  location ~* \.(jpg|jpeg|png|webp|svg|gif|mp4|css|js)$ { expires 7d; add_header Cache-Control "public"; }
  gzip on;
  gzip_types text/css application/javascript image/svg+xml application/xml;
}
EOF

# restore script, written before anything is switched
cat > /root/restore-old-site.sh <<EOF
#!/bin/bash
rm -f /etc/nginx/sites-enabled/alhabib-new /etc/nginx/conf.d/alhabib-new.conf
cp -a "$BK/old-site.conf" "$OLD"
nginx -t && (systemctl reload nginx 2>/dev/null || nginx -s reload) && echo "OLD SITE IS BACK"
EOF
chmod +x /root/restore-old-site.sh

# 5. switch: turn the old settings off, the new ones on
rm -f "$OLD"
[ "$CONF" = /etc/nginx/sites-available/alhabib-new ] && ln -sf "$CONF" /etc/nginx/sites-enabled/alhabib-new
if ! nginx -t; then
  bash /root/restore-old-site.sh
  stop "nginx rejected the new settings (old site restored)"
fi
reload_nginx
sleep 2

# 6. check the live answer from this server; go back if it is not the new site
PAGE=$(curl -sk --noproxy "*" --resolve $DOMAIN:443:127.0.0.1 https://$DOMAIN/)
CODE=$(curl -sk --noproxy "*" -o /dev/null -w "%{http_code}" --resolve $DOMAIN:443:127.0.0.1 https://$DOMAIN/works.html)
if echo "$PAGE" | grep -q 'class="nav float"' && [ "$CODE" = 200 ]; then
  echo
  echo "=============================================="
  echo " DONE: the new site is live on $DOMAIN"
  echo " to bring the old site back:  bash /root/restore-old-site.sh"
  echo "=============================================="
else
  bash /root/restore-old-site.sh
  stop "the new site did not answer correctly (old site restored)"
fi
