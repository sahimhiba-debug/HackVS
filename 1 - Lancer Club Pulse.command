#!/bin/bash
# JOUR J — DOUBLE-CLIQUER. Lance tout, sans rien taper :
#   a. le film : la SEULE vidéo posée sur le Bureau est copiée dans le deck (docs/presentation/deck/assets/film.mp4) ;
#   b. l'environnement Python (.venv) ;  c. le jeton de la console (~/.clubpulse/jeton, copié dans le presse-papiers) ;
#   d. PUBLIC_BASE_URL=https://clubpulse.tailfcbc50.ts.net ;
#   e. en arrière-plan : le prototype, le tunnel (tailscale funnel --bg), le serveur du deck, caffeinate
#      (journaux : ~/.clubpulse/logs) ;
#   f. attend que tout réponde, réinitialise la salle, ouvre Chrome sur la régie et le deck v2 ;
#   g. affiche la check-list (aussi sur http://127.0.0.1:8000/preflight) : « FEU VERT v2 » ou « PASSER EN v1 ».
# Pour tout arrêter : « 2 - Arrêter et effacer.command ». Dépannage : docs/presentation/COMMENT_PRESENTER.md (annexe).
set -u
RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1
DOSSIER="${CLUBPULSE_DOSSIER:-$HOME/.clubpulse}"
LOGS="$DOSSIER/logs"
PIDS="$DOSSIER/pids"
mkdir -p "$LOGS" "$PIDS" && chmod 700 "$DOSSIER"
PORT="${CLUBPULSE_PORT:-8000}"
PORT_DECK="${CLUBPULSE_PORT_DECK:-8765}"
export CLUBPULSE_DOSSIER="$DOSSIER" CLUBPULSE_PORT="$PORT" CLUBPULSE_PORT_DECK="$PORT_DECK"
export PUBLIC_BASE_URL="${CLUBPULSE_URL_PUBLIQUE:-https://clubpulse.tailfcbc50.ts.net}"
export CLUBPULSE_DECK_URL="http://127.0.0.1:$PORT_DECK/v2.html"
[ "$PORT_DECK" = "8765" ] || export HACKVS_DECK_ORIGINES="http://127.0.0.1:$PORT_DECK http://localhost:$PORT_DECK"
if [ -t 1 ]; then R=$'\033[1;31m'; V=$'\033[1;32m'; O=$'\033[1;33m'; F=$'\033[0m'; else R=; V=; O=; F=; fi
vert() { printf '  %s● VERT%s     %s\n' "$V" "$F" "$*"; }
orange() { printf '  %s● ORANGE%s   %s\n' "$O" "$F" "$*"; }
rouge() { printf '  %s● ROUGE%s    %s\n' "$R" "$F" "$*"; }
stop() { printf '\n%sARRÊT : %s%s\n' "$R" "$*" "$F"; exit 1; }

printf '\nClub Pulse — lancement du jour J\n\n'

# b. Python (avant le film : c'est lui qui cherche et copie)
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate && vert "Python : .venv activé"
else
  orange "Python : pas de .venv à la racine du dépôt — python3 du système (COMMENT_PRESENTER.md, annexe)"
fi
PY="$(command -v python3)" || stop "python3 introuvable"
export PY

# a. Le film
python3 prototype/scripts/jour_j.py film

# relance propre : les processus d'un lancement précédent sont arrêtés d'abord
for f in "$PIDS"/*; do
  [ -f "$f" ] || continue
  pid="$(cat "$f")"
  if kill -0 "$pid" 2>/dev/null; then kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null; sleep 1; fi
  rm -f "$f"
done
occupe() { python3 -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)" "$1"; }
occupe "$PORT" && stop "un autre programme utilise déjà le port $PORT (un ancien Terminal de démo ?) — le fermer, ou redémarrer le Mac"
occupe "$PORT_DECK" && stop "un autre programme utilise déjà le port $PORT_DECK (un ancien deck ?) — le fermer, ou redémarrer le Mac"

# c. Le jeton de la console
JETON="$(python3 prototype/scripts/jour_j.py jeton)" || stop "jeton de console non créé"
export HACKVS_CONSOLE_JETON="$JETON"
if command -v pbcopy >/dev/null 2>&1; then
  printf '%s' "$JETON" | pbcopy && vert "Jeton de la console : copié dans le presse-papiers (⌘-V dans la régie)"
else
  orange "Jeton de la console : presse-papiers indisponible — il est dans $DOSSIER/jeton"
fi

# e. En arrière-plan, chacun dans son groupe de processus (l'arrêt les retrouve tous, enfants compris)
set -m
nohup ./demo-tunnel.sh </dev/null >"$LOGS/prototype.log" 2>&1 &
echo $! >"$PIDS/prototype"
nohup python3 docs/presentation/deck/lancer.py "$PORT_DECK" --sans-navigateur </dev/null >"$LOGS/deck.log" 2>&1 &
echo $! >"$PIDS/deck"
if command -v caffeinate >/dev/null 2>&1; then
  nohup caffeinate -dimsu </dev/null >/dev/null 2>&1 &
  echo $! >"$PIDS/caffeinate"
fi
set +m
TS="$(command -v tailscale || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale)"
if [ -x "$TS" ]; then
  if "$TS" funnel --bg "$PORT" >"$LOGS/tunnel.log" 2>&1; then vert "Tunnel : tailscale funnel --bg $PORT"
  else rouge "Tunnel : refusé (journal : $LOGS/tunnel.log) — Tailscale connecté ? Funnel autorisé ?"; fi
else
  rouge "Tunnel : Tailscale introuvable (App Store, puis se connecter)"
fi

# f. Attendre que tout réponde
printf '\n  attente du prototype, du deck et de l'"'"'adresse publique…\n'
if python3 prototype/scripts/jour_j.py attendre "http://127.0.0.1:$PORT/sante" 90; then vert "Prototype : http://127.0.0.1:$PORT"
else rouge "Prototype : ne répond pas — dernières lignes du journal :"; tail -n 8 "$LOGS/prototype.log"; fi
python3 prototype/scripts/jour_j.py attendre "$CLUBPULSE_DECK_URL" 20 || rouge "Deck : ne répond pas (journal : $LOGS/deck.log)"
python3 prototype/scripts/jour_j.py attendre "$PUBLIC_BASE_URL/sante" "${CLUBPULSE_ATTENTE_PUBLIQUE:-45}" \
  || rouge "Adresse publique : $PUBLIC_BASE_URL ne répond pas (encore ?) — la check-list continue de vérifier"
python3 prototype/scripts/jour_j.py purger >/dev/null 2>&1 && vert "Salle : réinitialisée"

REGIE="http://127.0.0.1:$PORT/salle/regie"
if open -Ra "Google Chrome" >/dev/null 2>&1; then open -a "Google Chrome" "$REGIE" "$CLUBPULSE_DECK_URL"
else open "$REGIE" "$CLUBPULSE_DECK_URL" 2>/dev/null || orange "Chrome : ouvrir à la main $REGIE puis $CLUBPULSE_DECK_URL"; fi

# g. La check-list
python3 prototype/scripts/jour_j.py preflight
if [ $? -ne 0 ]; then
  open -a "Google Chrome" "http://127.0.0.1:$PORT/preflight" >/dev/null 2>&1 || true
  printf '\n  La page http://127.0.0.1:%s/preflight se met à jour toute seule : attendre le feu vert, ou passer en v1.\n' "$PORT"
fi
printf '\n  Régie : coller le jeton (⌘-V) quand elle le demande. Pour tout arrêter : « 2 - Arrêter et effacer ».\n\n'
