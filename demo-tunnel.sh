#!/usr/bin/env bash
# Démo publique sur le MAC DU PITCH, exposée en HTTPS par un tunnel (docs/DEMO_TUNNEL.md).
#   PUBLIC_BASE_URL=https://<mac>.<tailnet>.ts.net HACKVS_CONSOLE_JETON=<jeton> ./demo-tunnel.sh
# Le serveur n'écoute que 127.0.0.1:8000 ; le tunnel (Tailscale Funnel, ou Cloudflare en secours) est lancé à part.
# Refuse de démarrer sans HACKVS_CONSOLE_JETON : derrière un tunnel, toutes les requêtes arrivent de 127.0.0.1, et la
# console (qui peut incarner chaque membre) ne doit jamais dépendre de l'adresse d'origine.
set -euo pipefail
cd "$(dirname "$0")/prototype"
[ -n "${PUBLIC_BASE_URL:-}" ] || { echo "ERREUR : PUBLIC_BASE_URL vide (l'adresse du tunnel, ex. https://mac-du-pitch.<tailnet>.ts.net)"; exit 1; }
case "$PUBLIC_BASE_URL" in https://*) ;; *) echo "ERREUR : PUBLIC_BASE_URL doit commencer par https://"; exit 1;; esac
[ -n "${HACKVS_CONSOLE_JETON:-}" ] || { echo "ERREUR : HACKVS_CONSOLE_JETON vide — exigé derrière un tunnel (python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"; exit 1; }
[ "${#HACKVS_CONSOLE_JETON}" -ge 16 ] || { echo "ERREUR : HACKVS_CONSOLE_JETON doit compter au moins 16 caractères"; exit 1; }
[ "${VERIFIER_SEULEMENT:-0}" = "1" ] && { echo "OK : configuration du tunnel valide."; exit 0; }
PY="${PY:-python3}"
mkdir -p var
test -s var/secret_demo || "$PY" -c "import secrets; print(secrets.token_urlsafe(48))" > var/secret_demo
chmod 600 var/secret_demo
# empêcher la veille (écran et système) tant que le serveur tourne — macOS seulement
VEILLE=()
command -v caffeinate >/dev/null && VEILLE=(caffeinate -dimsu)
echo "Club Pulse sur http://127.0.0.1:8000 — public : ${PUBLIC_BASE_URL} — QR de la salle : ${PUBLIC_BASE_URL}/qr/salle.svg"
exec ${VEILLE[@]+"${VEILLE[@]}"} env HACKVS_SECRET="$(cat var/secret_demo)" HACKVS_ESSAIS_DB=var/club_pulse.db \
  HACKVS_MODE=demo HACKVS_DB=:memory: HACKVS_DECISIONS_DB=:memory: HACKVS_CYCLE_DB=:memory: \
  HACKVS_FOIRE="${HACKVS_FOIRE:-1}" HACKVS_SALLE="${HACKVS_SALLE:-1}" \
  PUBLIC_BASE_URL="$PUBLIC_BASE_URL" HACKVS_CONSOLE_JETON="$HACKVS_CONSOLE_JETON" \
  "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
