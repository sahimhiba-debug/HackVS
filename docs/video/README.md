# La vidéo de présélection (10 à 12 minutes)

Le jury regarde **sans nous**, à huis clos, et il n'est pas technique. Tout est ici, dans `docs/video/`. Le pitch en
direct ne change pas (`docs/presentation/`).

| Fichier | À quoi il sert |
|---|---|
| [SCRIPT_VIDEO.md](SCRIPT_VIDEO.md) | le script, 8 séquences numérotées, avec leur durée visée et leurs images |
| `prompteur.html` | le prompteur pour enregistrer la voix, séquence par séquence (flèches, espace = chrono) |
| [GUIDE_ENREGISTREMENT.md](GUIDE_ENREGISTREMENT.md) | une page : enregistrer 01.m4a … 08.m4a avec QuickTime |
| `voix-synthese/` | **les 8 voix de synthèse** (Piper, voix « siwis », hors ligne) utilisées par défaut ; [CHOIX_DE_LA_VOIX.md](voix-synthese/CHOIX_DE_LA_VOIX.md), échantillons dans `comparaison/` |
| `voix/` | vos propres enregistrements, s'il y en a un jour : **ils passent devant la synthèse, fichier par fichier** (git les ignore) |
| `sources/film.mp4` | le film (branche `video-sources`) : pris en premier par le montage, sinon la seule vidéo du Bureau |
| `images/` | 31 clips 1920 × 1080 : le deck en motion design (fond sombre) et l'application réelle (monde fictif, IA éteinte) |
| `sous-titres-cible.srt` | les sous-titres calés sur les durées visées ; le montage refait le SRT exact sur votre voix |
| `equipe.txt` | l'équipe et le contact de la carte de fin : **à compléter** |
| `monter.sh` | le montage, sur le Mac → `out/club-pulse-presentation.mp4` |
| `RESUME_JURY.pdf` | une page pour le jury : problème, solution, ce qu'y gagne le Club, la demande, l'équipe |
| `outils/` | `video.py` (prompteur, sous-titres, montage, vérifications, secours HTML), `images.py` (refait les clips, pas besoin sur le Mac) |

## Sur le Mac, étape par étape (voix de synthèse, vrai film)

1. **Récupérer la branche** (Terminal, dans le dossier du dépôt) :
   `git fetch origin && git checkout foire-2026 && git pull`
2. **Le film** : `mkdir -p docs/video/sources && git show origin/video-sources:docs/video/sources/film.mp4 > docs/video/sources/film.mp4`
   (le dossier `sources/` est ignoré sur cette branche : rien à committer).
3. **ffmpeg**, une seule fois : `conda install -y -c conda-forge ffmpeg`.
4. **Le contact** de la carte de fin : `docs/video/equipe.txt`, ligne « Contact : » (TextEdit).
5. **Monter** : `./docs/video/monter.sh` → `docs/video/out/club-pulse-presentation.mp4`, et toutes les lignes `[OK]`.
6. **Regarder en entier, avec le son**, puis envoyer : le MP4 ; si demandé `RESUME_JURY.pdf` ; en secours
   `out/club-pulse-presentation-secours.html` ; `out/club-pulse-presentation.srt` si la plateforme veut les sous-titres à part.

Changer de voix : écouter `voix-synthese/comparaison/`, puis (une fois `pip install sherpa-onnx soundfile numpy`)
`python3 docs/video/outils/voix_synthese.py` régénère les 8 fichiers. **Plan B** si la voix de synthèse ne vous plaît
pas : la voix « Premium » de macOS — Réglages Système → Accessibilité → Contenu énoncé → Voix du système → Gérer les
voix → Français → télécharger « Audrey (Premium) » (ou « Aurélie (Premium) ») — puis
`python3 docs/video/outils/voix_synthese.py --mac "Audrey (Premium)"` et l'étape 5.
Votre propre voix, plus tard : `GUIDE_ENREGISTREMENT.md`, les fichiers dans `voix/` passent devant.

Une vérification en `[KO]` :
- **durée trop courte** : lire plus lentement (les séquences 4, 5 et 6 surtout) ; **trop longue** : resserrer les pauses ;
- **silence** : l'heure du silence est affichée ; réenregistrer la séquence concernée ;
- **carte de fin** : compléter `equipe.txt`.

## Ce qui a été vérifié ici (fausses voix, faux film)

Montage de bout en bout avec 8 voix de synthèse et un faux film de 3 min 21 s posé sur un faux Bureau (même détection que le lanceur) : **tout est vert** (11 min 31 s, 96 Mo, -16,1 LUFS, aucun silence de plus de 3 s, aucun mot interdit). Détail : [RAPPORT_MONTAGE.md](RAPPORT_MONTAGE.md).

## Refaire les images (pas nécessaire sur le Mac)

`cd prototype && python ../docs/video/outils/images.py` (Chromium de Playwright) : le deck v3 rejoué sans interaction,
en « mode vidéo » (aucun code à scanner, aucune consigne de régie, des mots simples), et l'application réelle sur un
serveur de démonstration isolé : monde fictif, mémoire seule, IA éteinte.
