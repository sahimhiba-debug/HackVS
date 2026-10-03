#!/usr/bin/env bash
# APRÈS LE PITCH : efface TOUTES les données du mode salle (participants, capacités, réponses, reçus) et vérifie.
#   ./purge.sh               (lit PUBLIC_BASE_URL et HACKVS_CONSOLE_JETON dans .env, ou dans l'environnement)
#   ./purge.sh --tout        efface AUSSI le journal du Club (volume « pulse ») et redémarre — la démo repart à zéro
set -euo pipefail
cd "$(dirname "$0")"
if [ -f ./.env ]; then set -a; . ./.env; set +a; fi   # démo par tunnel : variables déjà exportées, pas de .env
: "${PUBLIC_BASE_URL:?PUBLIC_BASE_URL vide}" "${HACKVS_CONSOLE_JETON:?HACKVS_CONSOLE_JETON vide}"
curl -fsS -X POST -H "X-Pulse-Console: ${HACKVS_CONSOLE_JETON}" "${PUBLIC_BASE_URL}/api/pulse/console/salle/purger"; echo
etat=$(curl -fsS -H "X-Pulse-Console: ${HACKVS_CONSOLE_JETON}" "${PUBLIC_BASE_URL}/api/pulse/console/salle")
echo "$etat" | grep -q '"participants":0' && echo "OK : salle vide." || { echo "ÉCHEC : la salle n'est pas vide : $etat"; exit 1; }
if [ "${1:-}" = "--tout" ]; then
  docker compose -f docker-compose.prod.yml down
  docker volume rm "$(basename "$PWD" | tr '[:upper:]' '[:lower:]')_pulse" || true
  docker compose -f docker-compose.prod.yml up -d
  echo "Journal du Club effacé, service redémarré."
fi
