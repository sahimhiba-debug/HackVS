#!/bin/bash
# Fabrique les 8 voix de la vidéo avec une voix française de macOS (commande say)
#   → docs/video/voix/01.m4a … 08.m4a (ces fichiers passent devant la voix de synthèse Piper au montage).
#
#   ./docs/video/voix_mac.sh                       # sans argument : liste les voix françaises installées
#   ./docs/video/voix_mac.sh "Audrey (Premium)"    # fabrique les 8 fichiers avec cette voix
#   DEBIT=160 ./docs/video/voix_mac.sh "Audrey (Premium)"   # débit en mots par minute (165 par défaut)
#
# Même texte que SCRIPT_VIDEO.md, mêmes corrections de prononciation (Apertusse, Club Peulse, Anne-ci, i a) pour la
# voix seulement, une pause à chaque « / », une respiration entre les phrases. Compatible avec le bash 3.2 de macOS.
set -u

cd "$(dirname "$0")/../.." || exit 1          # racine du dépôt
DEBIT="${DEBIT:-165}"                         # la voix française par défaut parle vers 180 : un peu plus lent
SORTIE="docs/video/voix"

voix_francaises() {
  say -v '?' 2>/dev/null | grep -E '[[:space:]]fr_[A-Z][A-Z][[:space:]]' || true
}

if ! command -v say >/dev/null 2>&1 || ! command -v afconvert >/dev/null 2>&1; then
  echo "  Ce script tourne sur un Mac (commandes say et afconvert introuvables)."
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "  python3 est introuvable (xcode-select --install)."
  exit 1
fi

if [ $# -eq 0 ] || [ -z "$1" ]; then
  echo ""
  echo "  Voix françaises installées sur ce Mac :"
  echo ""
  LISTE="$(voix_francaises)"
  if [ -z "$LISTE" ]; then
    echo "    (aucune)"
  else
    echo "$LISTE" | sed 's/^/    /'
  fi
  echo ""
  echo "  Pour fabriquer les voix :   ./docs/video/voix_mac.sh \"Audrey (Premium)\""
  echo ""
  echo "  Une voix « Premium » manque ? Réglages Système → Accessibilité → Contenu énoncé → Voix du système"
  echo "  → Gérer les voix… → Français → cocher « Audrey (Premium) » (ou « Aurélie (Premium) », « Thomas (Premium) »)."
  exit 0
fi

VOIX="$1"
noms_francais() {                             # le nom exact de chaque voix (sans la langue ni la phrase d'exemple)
  voix_francaises | sed 's/[[:space:]]\{1,\}fr_[A-Z][A-Z].*$//'
}

if ! noms_francais | grep -qxF "$VOIX"; then
  echo "  Voix introuvable : « $VOIX »."
  echo "  Voix françaises installées :"
  voix_francaises | sed 's/^/    /'
  echo "  (une voix Premium se télécharge d'abord : lancez ./docs/video/voix_mac.sh sans argument pour la marche à suivre)"
  exit 1
fi

TMP="$(mktemp -d -t clubpulse-voix.XXXXXX)" || exit 1
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SORTIE"

echo "  voix : $VOIX · débit $DEBIT mots/min → $SORTIE/"
for N in 01 02 03 04 05 06 07 08; do
  TEXTE="$(python3 docs/video/outils/voix_synthese.py --texte-say "$N")" || exit 1
  if ! say -v "$VOIX" -r "$DEBIT" -o "$TMP/$N.aiff" "$TEXTE"; then
    echo "  say a échoué sur la séquence $N"; exit 1
  fi
  if ! afconvert -f m4af -d aac -b 128000 "$TMP/$N.aiff" "$SORTIE/$N.m4a"; then
    echo "  afconvert a échoué sur la séquence $N"; exit 1
  fi
  echo "  $SORTIE/$N.m4a"
done

echo "$VOIX" > "$SORTIE/.synthese"              # le montage garde la mention « Voix de synthèse » sur la carte de fin
echo ""
echo "  Les 8 voix sont prêtes. Écoutez-en une (afplay $SORTIE/01.m4a), puis montez : ./docs/video/monter.sh"
echo "  Pour revenir à la voix de synthèse Piper : supprimez $SORTIE/0*.m4a et $SORTIE/.synthese."
