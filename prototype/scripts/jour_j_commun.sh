# Commun aux trois double-clics du jour J (« 1 - Lancer Club Pulse », « 2 - Arrêter et effacer », « 3 - Passer en v1 »).
# Chargé par `. prototype/scripts/jour_j_commun.sh` depuis la racine du dépôt. Compatible avec le bash 3.2 de macOS.
DOSSIER="${CLUBPULSE_DOSSIER:-$HOME/.clubpulse}"
LOGS="$DOSSIER/logs"
PIDS="$DOSSIER/pids"
mkdir -p "$LOGS" "$PIDS" && chmod 700 "$DOSSIER"
PORT="${CLUBPULSE_PORT:-8000}"
PORT_DECK="${CLUBPULSE_PORT_DECK:-8765}"
export CLUBPULSE_DOSSIER="$DOSSIER" CLUBPULSE_PORT="$PORT" CLUBPULSE_PORT_DECK="$PORT_DECK"
if [ -t 1 ]; then R=$'\033[1;31m'; V=$'\033[1;32m'; O=$'\033[1;33m'; F=$'\033[0m'; else R=; V=; O=; F=; fi
vert() { printf '  %s● VERT%s     %s\n' "$V" "$F" "$*"; }
orange() { printf '  %s● ORANGE%s   %s\n' "$O" "$F" "$*"; }
rouge() { printf '  %s● ROUGE%s    %s\n' "$R" "$F" "$*"; }
stop() { printf '\n%sARRÊT : %s%s\n' "$R" "$*" "$F"; fin_de_fenetre; exit 1; }
# AUDIT I7 : si Terminal ferme la fenêtre à la fin du script, le verdict ne serait lu nulle part — on attend Entrée.
fin_de_fenetre() { if [ -t 0 ] && [ -t 1 ]; then printf '\n(Entrée pour fermer cette fenêtre) '; read -r _; fi; }

python_du_depot() {
  if [ -f .venv/bin/activate ]; then
    . .venv/bin/activate && vert "Python : .venv activé"
  else
    orange "Python : pas de .venv à la racine du dépôt — python3 du système (COMMENT_PRESENTER.md, annexe)"
  fi
  command -v python3 >/dev/null 2>&1 || stop "python3 introuvable"
  PY="$(command -v python3)"
  export PY
}

# AUDIT I2 : un fichier de pids/ garde le numéro ET l'heure de démarrage. Après un redémarrage du Mac, le numéro peut
# désigner un autre programme : on ne tue que si les deux correspondent — jamais un processus étranger.
noter() { printf '%s\n%s\n' "$2" "$(ps -o lstart= -p "$2" 2>/dev/null)" >"$PIDS/$1"; }
notre() {
  [ -f "$1" ] || return 1
  _pid="$(sed -n 1p "$1")"
  _debut="$(sed -n 2p "$1")"
  [ -n "$_pid" ] && [ -n "$_debut" ] && [ "$(ps -o lstart= -p "$_pid" 2>/dev/null)" = "$_debut" ]
}
# arrêter(nom…) : chaque groupe de processus nôtre (enfants compris), TERM puis KILL après 5 s ; fichiers retirés
arreter() {
  _groupes=""
  for _nom in "$@"; do
    _f="$PIDS/$_nom"
    if notre "$_f"; then
      _g="$(sed -n 1p "$_f")"
      kill -TERM -- "-$_g" 2>/dev/null
      _groupes="$_groupes $_g"
    fi
    rm -f "$_f"
  done
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    _vivants=0
    for _g in $_groupes; do kill -0 -- "-$_g" 2>/dev/null && _vivants=1; done
    [ "$_vivants" = 0 ] && return 0
    sleep 0.5
  done
  for _g in $_groupes; do kill -KILL -- "-$_g" 2>/dev/null; done
  return 0
}
tous_les_noms() { for _f in "$PIDS"/*; do [ -f "$_f" ] && basename "$_f"; done; }
occupe() { python3 -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)" "$1"; }
tailscale_cli() { command -v tailscale || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale; }
# AUDIT (mineur) : `open -Ra` montrerait Chrome dans le Finder ; on demande seulement si l'application existe.
chrome() {
  if osascript -e 'id of application "Google Chrome"' >/dev/null 2>&1 || ! command -v osascript >/dev/null 2>&1; then
    open -a "Google Chrome" "$@" 2>/dev/null && return 0
  fi
  open "$@" 2>/dev/null || orange "Chrome : ouvrir à la main $*"
}
