#!/bin/bash
# PLAN B — DOUBLE-CLIQUER si la check-list dit « PASSER EN v1 » (le tunnel ne passe pas). Sans rien taper :
#   1. arrête le prototype du tunnel et ferme le tunnel (le deck et caffeinate continuent) ;
#   2. relance la démo v1 joignable sur le réseau local du Mac (son point d'accès, ou le Wi-Fi) — comme `make demo` ;
#   3. ouvre Chrome sur l'Établi et sur le deck v1, et affiche l'adresse du téléphone de Pauline.
# La suite : 04_DEMO_RUNBOOK.md (v1). Pour tout arrêter ensuite : « 2 - Arrêter et effacer ».
set -u
RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1
. prototype/scripts/jour_j_commun.sh

printf '\nClub Pulse — passage en v1 (sans tunnel)\n\n'
python_du_depot

# 1. Le prototype du tunnel s'arrête ; le tunnel se ferme
arreter prototype
TS="$(tailscale_cli)"
[ -x "$TS" ] && "$TS" funnel reset </dev/null >/dev/null 2>&1 && vert "Tunnel fermé"
occupe "$PORT" && stop "le port $PORT est encore occupé — double-clic sur « 2 - Arrêter et effacer », puis réessayer"

# 2. L'adresse du Mac sur le réseau local : point d'accès du Mac (bridge100), sinon Wi-Fi
IP="${CLUBPULSE_IP:-}"
for itf in bridge100 en0 en1; do
  [ -n "$IP" ] && break
  IP="$(ipconfig getifaddr "$itf" 2>/dev/null || true)"
done
[ -n "$IP" ] || stop "aucune adresse réseau : activer le partage de connexion du Mac, ou le Wi-Fi"

JETON="$(python3 prototype/scripts/jour_j.py jeton)" || stop "jeton de console non créé"
command -v pbcopy >/dev/null 2>&1 && printf '%s' "$JETON" | pbcopy
VAR="${CLUBPULSE_VAR:-var}"
set -m
(
  cd prototype || exit 1
  mkdir -p "$VAR"
  test -s "$VAR/secret_demo" || python3 -c "import secrets; print(secrets.token_urlsafe(48))" >"$VAR/secret_demo"
  chmod 600 "$VAR/secret_demo"
  HACKVS_SECRET="$(cat "$VAR/secret_demo")" HACKVS_ESSAIS_DB="$VAR/club_pulse.db" HACKVS_MODE=demo HACKVS_DB=:memory: \
    HACKVS_DECISIONS_DB=:memory: HACKVS_CYCLE_DB=:memory: HACKVS_FOIRE="${HACKVS_FOIRE:-1}" HACKVS_SALLE="${HACKVS_SALLE:-1}" \
    HACKVS_URL_PUBLIQUE="http://$IP:$PORT" HACKVS_CONSOLE_JETON="$JETON" PUBLIC_BASE_URL= \
    exec nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-access-log
) </dev/null >"$LOGS/prototype-v1.log" 2>&1 &
noter prototype $!
set +m

if python3 prototype/scripts/jour_j.py attendre "http://127.0.0.1:$PORT/sante" 90; then vert "Démo v1 : http://$IP:$PORT"
else rouge "Démo v1 : ne répond pas — dernières lignes du journal :"; tail -n 8 "$LOGS/prototype-v1.log"; fi
occupe "$PORT_DECK" || orange "Deck : arrêté — relancer « 1 - Lancer Club Pulse » n'est pas utile ; ouvrir le deck v1 à la main (annexe A3)"
chrome "http://127.0.0.1:$PORT/etabli" "http://127.0.0.1:$PORT_DECK/index.html"

printf '\n  Téléphone de Pauline : se connecter au réseau du Mac, puis ouvrir  http://%s:%s/app\n' "$IP" "$PORT"
printf '  Console (jeton : ⌘-V, il est dans le presse-papiers) : http://127.0.0.1:%s/console\n' "$PORT"
printf '  La suite : docs/presentation/04_DEMO_RUNBOOK.md, § 2. Pour tout arrêter : « 2 - Arrêter et effacer ».\n'
fin_de_fenetre
