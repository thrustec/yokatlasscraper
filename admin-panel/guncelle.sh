#!/usr/bin/env bash
# Paneli GitHub'daki (main) son sürüme günceller.
# Kullanım (sunucuda, admin-panel klasöründe):  sudo bash guncelle.sh
# Çalışan bot varsa önce sorar; sormadan devam etmek için:  sudo bash guncelle.sh --zorla
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Bu klasörde .env yok. Önce README'deki kurulumu yapın."
  exit 1
fi

COMPOSE="docker compose -f compose.admin.yaml"

aktif=$($COMPOSE exec -T runner python -c \
  "from adminpanel import db; print(db.one(\"SELECT count(*) AS n FROM ops.runs WHERE status IN ('queued','running')\")['n'])" \
  2>/dev/null || echo 0)
if [ "${aktif:-0}" != "0" ] && [ "${1:-}" != "--zorla" ]; then
  echo "Şu an $aktif bot çalışıyor ya da sırada. Güncelleme bunları durdurur."
  read -r -p "Yine de devam edilsin mi? (e/h) " cevap
  [ "$cevap" = "e" ] || { echo "İptal edildi."; exit 0; }
fi

echo "GitHub'dan son kod alınıyor..."
git pull --ff-only

echo "Panel yeniden kuruluyor..."
$COMPOSE up -d --build
$COMPOSE ps

echo
echo "Güncellendi: $(git log -1 --format='%h %s (%an, %cr)')"
