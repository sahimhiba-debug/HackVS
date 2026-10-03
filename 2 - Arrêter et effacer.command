#!/bin/bash
# JOUR J — DOUBLE-CLIQUER APRÈS LE PITCH. Réinitialise la salle (purge vérifiée : la promesse faite à la salle), ferme
# le tunnel (tailscale funnel reset), arrête le prototype, le deck et caffeinate. Ne touche JAMAIS au film du Bureau.
set -u
RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1
DOSSIER="${CLUBPULSE_DOSSIER:-$HOME/.clubpulse}"
PIDS="$DOSSIER/pids"
PORT="${CLUBPULSE_PORT:-8000}"
PORT_DECK="${CLUBPULSE_PORT_DECK:-8765}"
export CLUBPULSE_DOSSIER="$DOSSIER" CLUBPULSE_PORT="$PORT" CLUBPULSE_PORT_DECK="$PORT_DECK"
if [ -t 1 ]; then R=$'\033[1;31m'; V=$'\033[1;32m'; F=$'\033[0m'; else R=; V=; F=; fi
[ -f .venv/bin/activate ] && . .venv/bin/activate
ok=1

printf '\nClub Pulse — arrêt et effacement\n\n'

# 1. La salle : réinitialiser, puis vérifier qu'elle est vide
if python3 prototype/scripts/jour_j.py attendre "http://127.0.0.1:$PORT/sante" 2; then
  if sortie="$(python3 prototype/scripts/jour_j.py purger 2>&1)"; then printf '  %s● VERT%s     Salle effacée : %s\n' "$V" "$F" "$sortie"
  else printf '  %s● ROUGE%s    Salle : %s\n' "$R" "$F" "$sortie"; ok=0; fi
else
  printf '  %s● VERT%s     Salle : le serveur ne tournait plus — la salle (en mémoire) est déjà effacée\n' "$V" "$F"
fi

# 2. Le tunnel
TS="$(command -v tailscale || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale)"
if [ -x "$TS" ]; then
  "$TS" funnel reset >/dev/null 2>&1 && printf '  %s● VERT%s     Tunnel fermé\n' "$V" "$F" \
    || { printf '  %s● ROUGE%s    Tunnel : « tailscale funnel reset » a échoué\n' "$R" "$F"; ok=0; }
fi

# 3. Les processus (chacun avec ses enfants : groupe de processus)
for f in "$PIDS"/*; do
  [ -f "$f" ] || continue
  pid="$(cat "$f")"
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
done
for _ in 1 2 3 4 5 6 7 8 9 10; do
  vivants=0
  for f in "$PIDS"/*; do [ -f "$f" ] && kill -0 -- "-$(cat "$f")" 2>/dev/null && vivants=1; done
  [ "$vivants" = 0 ] && break
  sleep 0.5
done
for f in "$PIDS"/*; do [ -f "$f" ] && kill -KILL -- "-$(cat "$f")" 2>/dev/null; rm -f "$f"; done
libre() { python3 -c "import socket,sys; s=socket.socket(); sys.exit(1 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 0)" "$1"; }
for p in "$PORT" "$PORT_DECK"; do
  libre "$p" || { printf '  %s● ROUGE%s    le port %s est encore occupé\n' "$R" "$F" "$p"; ok=0; }
done
[ "$ok" = 1 ] && printf '  %s● VERT%s     Prototype, deck et caffeinate arrêtés\n' "$V" "$F"

if [ "$ok" = 1 ]; then printf '\n%sTout est éteint et effacé.%s\n\n' "$V" "$F"
else printf '\n%sQuelque chose résiste : voir ci-dessus (journaux : %s/logs).%s\n\n' "$R" "$DOSSIER" "$F"; exit 1; fi
