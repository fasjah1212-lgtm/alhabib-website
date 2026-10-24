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

# 1. find every nginx file that serves the domain, and its certificate
DUMP=$(nginx -T 2>/dev/null)
echo "$DUMP" | grep -nE "# configuration file|^\s*listen|^\s*server_name|^\s*ssl_certificate|proxy_pass" | grep -v "mime.types\|fastcgi\|snippets" | head -40
FILES=$(echo "$DUMP" | awk -v d="$DOMAIN" '/^# configuration file /{f=$4; sub(/:$/,"",f)} /^[ \t]*server_name/ && index($0,d){print f}' | sort -u)
[ -n "$FILES" ] || stop "no nginx settings for $DOMAIN"
for f in $FILES; do
  case "$f" in /etc/nginx/sites-enabled/*|/etc/nginx/conf.d/*) ;; *) stop "settings are inside $f, needs a manual look";; esac
  O=$(grep -hoE "server_name[^;]*" "$f" | tr ' \t' '\n\n' | grep -vE "^(server_name|)$" | grep -vE "^(www\.)?$DOMAIN$" | sort -u | tr '\n' ' ')
  [ -z "$O" ] || stop "$f also serves: $O"
done
say "old site settings: $FILES"
CERT=$(echo "$DUMP" | grep -E "^\s*ssl_certificate\s" | grep "$DOMAIN" | head -1 | awk '{print $2}' | tr -d ';')
KEY=$(echo "$DUMP" | grep -E "^\s*ssl_certificate_key\s" | grep "$DOMAIN" | head -1 | awk '{print $2}' | tr -d ';')
if [ -z "$CERT" ] || [ ! -f "$CERT" ]; then
  for d in /etc/letsencrypt/live/$DOMAIN /etc/letsencrypt/live/$DOMAIN-0001 /etc/letsencrypt/live/www.$DOMAIN; do
    [ -f "$d/fullchain.pem" ] && CERT=$d/fullchain.pem && KEY=$d/privkey.pem && break
  done
fi
[ -n "$CERT" ] && [ -f "$CERT" ] && [ -n "$KEY" ] && [ -f "$KEY" ] || { ls /etc/letsencrypt/live/ 2>/dev/null; stop "SSL certificate not found"; }
say "certificate: $CERT"
V6=""; for f in $FILES; do grep -q "\[::\]" "$f" && V6=yes; done

# 2. back up nginx
mkdir -p "$BK/old" && cp -a /etc/nginx "$BK/nginx" || stop "backup failed"
for f in $FILES; do cp -a "$f" "$BK/old/$(echo "$f" | tr / _)" || stop "backup failed"; done
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
FIRST=$(echo "$FILES" | head -1)
if [ "$(dirname "$FIRST")" = /etc/nginx/conf.d ]; then CONF=/etc/nginx/conf.d/alhabib-new.conf; else CONF=/etc/nginx/sites-available/alhabib-new; fi
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
{ echo '#!/bin/bash'
  echo 'rm -f /etc/nginx/sites-enabled/alhabib-new /etc/nginx/conf.d/alhabib-new.conf'
  for f in $FILES; do echo "cp -a '$BK/old/$(echo "$f" | tr / _)' '$f'"; done
  echo 'nginx -t && (systemctl reload nginx 2>/dev/null || nginx -s reload) && echo "OLD SITE IS BACK"'
} > /root/restore-old-site.sh
chmod +x /root/restore-old-site.sh

# 5. switch: turn the old settings off, the new ones on
for f in $FILES; do rm -f "$f"; done
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
