#!/bin/bash
# JOUR J — DOUBLE-CLIQUER. Lance tout, sans rien taper :
#   a. le film : la SEULE vidéo posée sur le Bureau est copiée dans le deck (docs/presentation/deck/assets/film.mp4) ;
#   b. l'environnement Python (.venv) ;  c. le jeton de la console (~/.clubpulse/jeton, copié dans le presse-papiers) ;
#   d. PUBLIC_BASE_URL=https://clubpulse.tailfcbc50.ts.net ;
#   e. en arrière-plan : le prototype, le tunnel (tailscale funnel --bg), le serveur du deck, caffeinate
#      (journaux : ~/.clubpulse/logs) ;
#   f. attend que tout réponde, réinitialise la salle, ouvre Chrome sur la régie et le deck v2 ;
#   g. affiche la check-list (aussi sur http://127.0.0.1:8000/preflight) : « FEU VERT v2 », « RÉPARER D'ABORD »
#      ou « PASSER EN v1 » (alors : « 3 - Passer en v1 »).
# Pour tout arrêter : « 2 - Arrêter et effacer.command ». Dépannage : docs/presentation/COMMENT_PRESENTER.md (annexe).
set -u
RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1
. prototype/scripts/jour_j_commun.sh
export PUBLIC_BASE_URL="${CLUBPULSE_URL_PUBLIQUE:-https://clubpulse.tailfcbc50.ts.net}"
export CLUBPULSE_DECK_URL="http://127.0.0.1:$PORT_DECK/v2.html"
[ "$PORT_DECK" = "8765" ] || export HACKVS_DECK_ORIGINES="http://127.0.0.1:$PORT_DECK http://localhost:$PORT_DECK"

printf '\nClub Pulse — lancement du jour J\n\n'

# b. Python (avant le film : c'est lui qui cherche et copie)
python_du_depot

# a. Le film
python3 prototype/scripts/jour_j.py film

# relance propre : les processus NÔTRES d'un lancement précédent sont arrêtés d'abord (jamais un étranger)
# shellcheck disable=SC2046
arreter $(tous_les_noms)
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
noter prototype $!
nohup python3 docs/presentation/deck/lancer.py "$PORT_DECK" --sans-navigateur </dev/null >"$LOGS/deck.log" 2>&1 &
noter deck $!
if command -v caffeinate >/dev/null 2>&1; then
  nohup caffeinate -dimsu </dev/null >/dev/null 2>&1 &
  noter caffeinate $!
fi
set +m

# AUDIT I5 : si Funnel n'est pas autorisé, `tailscale funnel` affiche une adresse à visiter et ATTEND — jamais de
# fenêtre figée : délai maximal, puis voyant rouge et journal.
TS="$(tailscale_cli)"
if [ -x "$TS" ]; then
  "$TS" funnel --bg "$PORT" </dev/null >"$LOGS/tunnel.log" 2>&1 &
  tp=$!
  n=0
  while kill -0 "$tp" 2>/dev/null && [ "$n" -lt $(( ${CLUBPULSE_ATTENTE_TUNNEL:-20} * 2 )) ]; do sleep 0.5; n=$((n + 1)); done
  if kill -0 "$tp" 2>/dev/null; then
    kill "$tp" 2>/dev/null
    rouge "Tunnel : Tailscale attend une action (Funnel autorisé pour ce Mac ?) — voir $LOGS/tunnel.log"
  elif wait "$tp"; then
    vert "Tunnel : tailscale funnel --bg $PORT"
  else
    rouge "Tunnel : refusé — Tailscale connecté ? Funnel autorisé ? (journal : $LOGS/tunnel.log)"
  fi
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

chrome "http://127.0.0.1:$PORT/salle/regie" "$CLUBPULSE_DECK_URL"
printf '\n  Régie : coller le jeton (⌘-V) quand elle le demande. Pour tout arrêter : « 2 - Arrêter et effacer ».\n'
printf '  Si la check-list dit « PASSER EN v1 » : « 3 - Passer en v1 ».\n'

# g. La check-list — son verdict est la DERNIÈRE ligne
if ! python3 prototype/scripts/jour_j.py preflight; then
  chrome "http://127.0.0.1:$PORT/preflight" >/dev/null 2>&1    # la page se met à jour toute seule
fi
fin_de_fenetre
