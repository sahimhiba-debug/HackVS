#!/usr/bin/env bash
# Déploie (ou met à jour) Club Pulse sur le VPS : récupère le code, construit, redémarre, vérifie la santé.
#   ./deploy.sh            depuis le dossier du dépôt sur le serveur (branche foire-2026 ou main après fusion)
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "ERREUR : .env absent — cp .env.example .env puis remplir (docs/DEPLOIEMENT.md)"; exit 1; }
set -a; . ./.env; set +a
for v in DOMAINE PUBLIC_BASE_URL HACKVS_SECRET HACKVS_CONSOLE_JETON; do
  [ -n "${!v:-}" ] || { echo "ERREUR : $v est vide dans .env"; exit 1; }
done
[ "${#HACKVS_SECRET}" -ge 32 ] || { echo "ERREUR : HACKVS_SECRET doit compter au moins 32 caractères"; exit 1; }
git pull --ff-only
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
echo "Vérification de santé : ${PUBLIC_BASE_URL}/sante"
for i in $(seq 1 30); do
  if curl -fsS --max-time 5 "${PUBLIC_BASE_URL}/sante" >/dev/null; then
    echo "OK : ${PUBLIC_BASE_URL} répond (essai $i)."
    curl -fsS --max-time 5 -H "X-Pulse-Console: ${HACKVS_CONSOLE_JETON}" "${PUBLIC_BASE_URL}/api/pulse/console/salle/etat" && echo
    exit 0
  fi
  sleep 4
done
echo "ÉCHEC : ${PUBLIC_BASE_URL}/sante ne répond pas après 2 minutes."
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail 60 app
exit 1
