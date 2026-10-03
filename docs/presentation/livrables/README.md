# Livrables de présentation (archivés le 02.10, depuis la session cloud)

Ces fichiers n'existaient que dans le conteneur temporaire de la session Claude Code cloud ; ils sont ici pour ne rien
perdre en changeant de machine. Ce sont des **exports datés**, pas des sources : la référence pour samedi reste
`../deck/` (deck) et les `.md` de `docs/presentation/`.

| Fichier | Contenu | État |
|---|---|---|
| `CLUB_PULSE_PRESENTATION.pdf` | les sept documents de mise en scène (01 → 07) en un PDF | **régénéré le 03.10** (Foire 2026 : 15 min, film 3:21, passe découverte, Suivi) |
| `CLUB_PULSE_FICHES_PRESENTATEUR.pdf` | fiches du présentateur : texte à dire (03b) à gauche, ce que voit le jury à droite, A4 paysage | **régénéré le 03.10** : acte 6 (rôle masqué, passe découverte, Suivi) à jour ; le **fil horaire** de la première page garde l'ancien minutage — la référence est `02_STRUCTURE.md` |
| `SCRIPT_v2_IMPRIMABLE.pdf` · `.html` | script oral v2 (18 min) en A4 paysage : chrono, colonne V1 (à dire), colonne V2 (régie, écrans), colonne écran / action, phrases par cœur | **généré le 03.10** depuis `03_SCRIPT_ORAL_v2.md` par `../outils/script_imprimable.py` (aucune réécriture à la main) |
| `CLUB_PULSE_MOTION_1080p.mp4` | film de motion design (10:10, 1080p, sans son), emplacement de film de 2:25 | 01.10 — **ancien minutage** ; remplacé par le deck pour samedi |

Pour les régénérer : scripts dans `../outils/` (`md2pdf.py`, `fiches.py`) et `../motion/rendre.py`. Les scripts
d'outils sont archivés tels qu'ils ont tourné (chemins absolus de la session cloud) : adapter les chemins en tête de
fichier avant de les relancer ailleurs.
