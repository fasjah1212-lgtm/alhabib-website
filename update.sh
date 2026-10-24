#!/bin/bash
# Updates the new Alhabib site on the factory's server: fresh files from GitHub and the current nginx settings.
# Run after install.sh. If anything is wrong the previous version goes straight back.
set -u
DOMAIN=alhabibfactory.com
NEW=/var/www/alhabib-new
ZIP=https://github.com/fasjah1212-lgtm/alhabib-website/archive/${1:-refs/heads/main}.tar.gz
BK=/root/alhabib-update-$(date +%Y%m%d-%H%M%S)

say()  { echo; echo ">>> $*"; }
stop() { echo; echo "XXXXX STOPPED: $* XXXXX"; echo "The live site was not changed."; exit 1; }
reload_nginx() { systemctl reload nginx 2>/dev/null || nginx -s reload; }

[ "$(id -u)" = 0 ] || stop "run as root"
CONF=/etc/nginx/sites-available/alhabib-new
[ -f "$CONF" ] || CONF=/etc/nginx/conf.d/alhabib-new.conf
[ -f "$CONF" ] && [ -d "$NEW" ] || stop "new site not installed yet (run install.sh)"
CERT=$(grep -m1 -E "^\s*ssl_certificate\s" "$CONF" | awk '{print $2}' | tr -d ';')
KEY=$(grep -m1 -E "^\s*ssl_certificate_key\s" "$CONF" | awk '{print $2}' | tr -d ';')
[ -f "$CERT" ] && [ -f "$KEY" ] || stop "SSL certificate not found"
V6=""; grep -q "\[::\]" "$CONF" && V6=yes

# 1. keep the current version
mkdir -p "$BK" && cp -a "$CONF" "$BK/nginx.conf" || stop "backup failed"

# 2. download and swap in the new files
TMP=$(mktemp -d)
curl -fsSL -o "$TMP/site.tar.gz" "$ZIP" || stop "download failed"
tar -xzf "$TMP/site.tar.gz" -C "$TMP" || stop "unpack failed"
SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
[ -f "$SRC/index.html" ] && [ -f "$SRC/works.html" ] || stop "site files incomplete"
rm -rf "$SRC/src" "$SRC/README.md" "$SRC/install.sh" "$SRC/update.sh" "$SRC/.htaccess"
chmod -R a+rX "$SRC"
mv "$NEW" "$BK/site" || stop "could not move the current files"
mv "$SRC" "$NEW" || { mv "$BK/site" "$NEW"; stop "copy failed"; }
say "new files in place ($(find "$NEW" -type f | wc -l) files), previous version in $BK"

back() {
  rm -rf "$NEW"; mv "$BK/site" "$NEW"; cp -a "$BK/nginx.conf" "$CONF"
  nginx -t && reload_nginx
}

# 3. current nginx settings (same as install.sh)
L6_80=""; L6_443=""
[ -n "$V6" ] && L6_80="  listen [::]:80;" && L6_443="  listen [::]:443 ssl;"
cat > "$CONF" <<EOF
# new Alhabib site (static files). Updated $(date); previous settings in $BK
server {
  listen 80;
$L6_80
  server_name $DOMAIN www.$DOMAIN;
  location /.well-known/acme-challenge/ { root $NEW; }
  location / { return 301 https://$DOMAIN\$request_uri; }
}
server {
  listen 443 ssl;
$L6_443
  server_name www.$DOMAIN;
  ssl_certificate $CERT;
  ssl_certificate_key $KEY;
  return 301 https://$DOMAIN\$request_uri;
}
server {
  listen 443 ssl;
$L6_443
  server_name $DOMAIN;
  ssl_certificate $CERT;
  ssl_certificate_key $KEY;
  root $NEW;
  index index.html;
  # clean addresses: /works serves works.html, and old *.html links move to the clean form
  if (\$request_uri ~ ^/index(\.html)?(\?.*)?\$) { return 301 /\$2; }
  if (\$request_uri ~ ^/([a-z-]+)\.html(\?.*)?\$) { return 301 /\$1\$2; }
  location / { try_files \$uri \$uri.html \$uri/ =404; }
  location ~* \.(jpg|jpeg|png|webp|svg|gif|mp4|css|js)$ { expires 7d; add_header Cache-Control "public"; }
  gzip on;
  gzip_types text/css application/javascript image/svg+xml application/xml;
}
EOF

# 4. check, then confirm the live answer; go back if anything is off
if ! nginx -t; then back; stop "nginx rejected the settings (previous version restored)"; fi
reload_nginx
sleep 2
PAGE=$(curl -sk --noproxy "*" --resolve $DOMAIN:443:127.0.0.1 https://$DOMAIN/)
CODE=$(curl -sk --noproxy "*" -o /dev/null -w "%{http_code}" --resolve $DOMAIN:443:127.0.0.1 https://$DOMAIN/works)
if echo "$PAGE" | grep -q 'class="nav float"' && [ "$CODE" = 200 ]; then
  echo
  echo "=============================================="
  echo " DONE: the site on $DOMAIN is updated"
  echo "=============================================="
else
  back
  stop "the updated site did not answer correctly (previous version restored)"
fi
