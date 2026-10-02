# Livrables de présentation (archivés le 02.10, depuis la session cloud)

Ces fichiers n'existaient que dans le conteneur temporaire de la session Claude Code cloud ; ils sont ici pour ne rien
perdre en changeant de machine. Ce sont des **exports datés**, pas des sources : la référence pour samedi reste
`../deck/` (deck) et les `.md` de `docs/presentation/`.

| Fichier | Contenu | État |
|---|---|---|
| `CLUB_PULSE_PRESENTATION.pdf` | les sept documents de mise en scène (01 → 07) en un PDF, 26 pages | 01.10 — **ancien minutage (10 min, film 2:25)** |
| `CLUB_PULSE_FICHES_PRESENTATEUR.pdf` | fiches du présentateur : texte à dire (03b) à gauche, ce que voit le jury à droite, 21 pages A4 paysage | 01.10 — **ancien minutage (10 min, film 2:25)** ; textes et écrans toujours valables |
| `CLUB_PULSE_MOTION_1080p.mp4` | film de motion design (10:10, 1080p, sans son), emplacement de film de 2:25 | 01.10 — **ancien minutage** ; remplacé par le deck pour samedi |

Pour les régénérer : scripts dans `../outils/` (`md2pdf.py`, `fiches.py`) et `../motion/rendre.py`. Les scripts
d'outils sont archivés tels qu'ils ont tourné (chemins absolus de la session cloud) : adapter les chemins en tête de
fichier avant de les relancer ailleurs.
