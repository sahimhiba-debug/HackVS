# La vidéo de présélection (10 à 12 minutes)

Le jury regarde **sans nous**, à huis clos, et il n'est pas technique. Tout est ici, dans `docs/video/`. Le pitch en
direct ne change pas (`docs/presentation/`).

| Fichier | À quoi il sert |
|---|---|
| [SCRIPT_VIDEO.md](SCRIPT_VIDEO.md) | le script, 8 séquences numérotées, avec leur durée visée et leurs images |
| `prompteur.html` | le prompteur pour enregistrer la voix, séquence par séquence (flèches, espace = chrono) |
| [GUIDE_ENREGISTREMENT.md](GUIDE_ENREGISTREMENT.md) | une page : enregistrer 01.m4a … 08.m4a avec QuickTime |
| `voix/` | vos 8 enregistrements (ils restent sur le Mac, git les ignore) |
| `images/` | 31 clips 1920 × 1080 : le deck en motion design (fond sombre) et l'application réelle (monde fictif, IA éteinte) |
| `sous-titres-cible.srt` | les sous-titres calés sur les durées visées ; le montage refait le SRT exact sur votre voix |
| `equipe.txt` | l'équipe et le contact de la carte de fin : **à compléter** |
| `monter.sh` | le montage, sur le Mac → `out/club-pulse-presentation.mp4` |
| `RESUME_JURY.pdf` | une page pour le jury : problème, solution, ce qu'y gagne le Club, la demande, l'équipe |
| `outils/` | `video.py` (prompteur, sous-titres, montage, vérifications, secours HTML), `images.py` (refait les clips, pas besoin sur le Mac) |

## Sur le Mac, étape par étape

1. **Récupérer la branche** (Terminal, dans le dossier du dépôt) :
   `git fetch origin && git checkout foire-2026 && git pull`
2. **ffmpeg**, une seule fois : `conda install -y -c conda-forge ffmpeg` (environ 2 minutes ; `ffmpeg -version` doit répondre).
3. **L'équipe et le contact** : ouvrir `docs/video/equipe.txt` avec TextEdit, remplir les deux lignes, enregistrer.
4. **La voix** : suivre [GUIDE_ENREGISTREMENT.md](GUIDE_ENREGISTREMENT.md) avec `docs/video/prompteur.html` ouvert dans
   Safari. Huit fichiers dans `docs/video/voix/` : `01.m4a` … `08.m4a`.
5. **Le film** sur le Bureau : la **seule** vidéo du Bureau, comme pour le lanceur (ou `--film /chemin/du/film.mp4`).
6. **Monter** : `./docs/video/monter.sh` (environ 10 à 20 minutes). À la fin, chaque vérification affiche `[OK]` ou `[KO]` :
   durée entre 10 et 12 minutes, aucun silence de plus de 3 secondes (hors film), aucun mot interdit dans le script et
   les sous-titres, taille de 400 Mo au plus, son autour de -16 LUFS, image H.264 1920 × 1080, carte de fin remplie.
7. **Regarder** `docs/video/out/club-pulse-presentation.mp4` en entier, avec le son. Une séquence à refaire ? Réenregistrer
   seulement son fichier `NN.m4a`, puis relancer l'étape 6.
8. **Envoyer** au jury : `club-pulse-presentation.mp4`, et si demandé `RESUME_JURY.pdf`. Secours, si le jury ne peut pas
   lire le MP4 : `out/club-pulse-presentation-secours.html`, un seul fichier, qui s'ouvre dans n'importe quel navigateur
   (bouton Lecture). `out/club-pulse-presentation.srt` : les sous-titres seuls, si la plateforme d'envoi les demande.

Une vérification en `[KO]` :
- **durée trop courte** : lire plus lentement (les séquences 4, 5 et 6 surtout) ; **trop longue** : resserrer les pauses ;
- **silence** : l'heure du silence est affichée ; réenregistrer la séquence concernée ;
- **carte de fin** : compléter `equipe.txt`.

## Ce qui a été vérifié ici (fausses voix, faux film)

En cours : montage de bout en bout avec des voix de synthèse et un faux film ; le résultat chiffré sera ajouté ici.

## Refaire les images (pas nécessaire sur le Mac)

`cd prototype && python ../docs/video/outils/images.py` (Chromium de Playwright) : le deck v3 rejoué sans interaction,
en « mode vidéo » (aucun code à scanner, aucune consigne de régie, des mots simples), et l'application réelle sur un
serveur de démonstration isolé : monde fictif, mémoire seule, IA éteinte.
