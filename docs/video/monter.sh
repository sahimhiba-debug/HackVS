#!/bin/bash
# Monte la vidéo de présélection sur le Mac : vos 8 voix + les images du dépôt + le film du Bureau
#   → docs/video/out/club-pulse-presentation.mp4 (1920 × 1080, H.264, -16 LUFS, sous-titres incrustés, carte de fin)
#
#   ./docs/video/monter.sh                       # voix dans docs/video/voix/01.m4a … 08.m4a, film = la seule vidéo du Bureau
#   ./docs/video/monter.sh --voix ~/Desktop/voix # un autre dossier de voix
#   ./docs/video/monter.sh --film ~/Movies/film.mp4
#
# Compatible avec le bash 3.2 de macOS. Rien n'est envoyé nulle part : tout se passe sur le Mac.
set -u

cd "$(dirname "$0")/../.." || exit 1          # racine du dépôt

trouver() {                                    # trouver ffmpeg / ffprobe : PATH, Homebrew, conda
  nom="$1"
  if command -v "$nom" >/dev/null 2>&1; then command -v "$nom"; return 0; fi
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/miniconda3/bin" "$HOME/anaconda3/bin" "$HOME/miniforge3/bin" \
           "$HOME/opt/miniconda3/bin" "$HOME/opt/anaconda3/bin" /opt/miniconda3/bin /opt/anaconda3/bin; do
    if [ -x "$d/$nom" ]; then echo "$d/$nom"; return 0; fi
  done
  if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/$nom" ]; then echo "$CONDA_PREFIX/bin/$nom"; return 0; fi
  return 1
}

FFMPEG="$(trouver ffmpeg)"
FFPROBE="$(trouver ffprobe)"
if [ -z "$FFMPEG" ] || [ -z "$FFPROBE" ]; then
  echo ""
  echo "  ffmpeg est introuvable. Installez-le avec conda (une seule fois, environ 2 minutes) :"
  echo ""
  echo "      conda install -y -c conda-forge ffmpeg"
  echo ""
  echo "  puis relancez : ./docs/video/monter.sh"
  exit 1
fi
if ! "$FFMPEG" -hide_banner -filters 2>/dev/null | grep -q " ass "; then
  echo "  Ce ffmpeg ne sait pas incruster les sous-titres (libass absent)."
  echo "  Installez celui de conda-forge :   conda install -y -c conda-forge ffmpeg"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "  python3 est introuvable (il est fourni avec les outils de développement d'Apple : xcode-select --install)."
  exit 1
fi

echo "  ffmpeg : $FFMPEG"
exec python3 docs/video/outils/video.py monter --ffmpeg "$FFMPEG" --ffprobe "$FFPROBE" "$@"
