#!/bin/bash
# JOUR J — DOUBLE-CLIQUER APRÈS LE PITCH. Réinitialise la salle (purge vérifiée : la promesse faite à la salle), ferme
# le tunnel (tailscale funnel reset), arrête le prototype (v2 ou v1), le deck et caffeinate. Ne touche JAMAIS au film
# du Bureau. N'arrête que NOS processus (numéro et heure de démarrage vérifiés).
set -u
RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1
. prototype/scripts/jour_j_commun.sh
[ -f .venv/bin/activate ] && . .venv/bin/activate
ok=1

printf '\nClub Pulse — arrêt et effacement\n\n'

# 1. La salle : réinitialiser, puis vérifier qu'elle est vide
if python3 prototype/scripts/jour_j.py attendre "http://127.0.0.1:$PORT/sante" 2; then
  if sortie="$(python3 prototype/scripts/jour_j.py purger 2>&1)"; then vert "Salle effacée : $sortie"
  else rouge "Salle : $sortie"; ok=0; fi
else
  vert "Salle : le serveur ne tournait plus — la salle (en mémoire) est déjà effacée"
fi

# 2. Le tunnel
TS="$(tailscale_cli)"
if [ -x "$TS" ]; then
  if "$TS" funnel reset </dev/null >/dev/null 2>&1; then vert "Tunnel fermé"
  else rouge "Tunnel : « tailscale funnel reset » a échoué"; ok=0; fi
else
  orange "Tunnel : Tailscale introuvable sur ce Mac — rien à fermer"
fi

# 3. Les processus (chacun avec ses enfants : groupe de processus)
# shellcheck disable=SC2046
arreter $(tous_les_noms)
arretes=1
for p in "$PORT" "$PORT_DECK"; do
  occupe "$p" && { rouge "le port $p est encore occupé (un programme lancé à la main ?)"; arretes=0; ok=0; }
done
[ "$arretes" = 1 ] && vert "Prototype, deck et caffeinate arrêtés"

if [ "$ok" = 1 ]; then printf '\n%sTout est éteint et effacé.%s\n' "$V" "$F"; fin_de_fenetre
else printf '\n%sQuelque chose résiste : voir ci-dessus (journaux : %s/logs).%s\n' "$R" "$DOSSIER" "$F"; fin_de_fenetre; exit 1; fi
