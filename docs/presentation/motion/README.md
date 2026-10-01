# Motion — la présentation sans slides

Un film de motion design qui **remplace le deck** (`06_SLIDE_CONTENT.md`) et garde le créneau du court métrage. Il
suit le minutage de `02_STRUCTURE.md` et le texte de `03b_SCRIPT_A_DIRE.md` : la voix reste en direct, le film
porte l'image.

## Deux façons de l'utiliser

| | Pour quoi | Comment |
|---|---|---|
| **Lecteur de scène** (`index.html`) | **le soir même** — l'image attend la voix | ouvrir `index.html` dans Chrome, `F` plein écran. Chaque clic / Espace / → passe au temps suivant ; l'image s'arrête d'elle-même sur chaque phrase et attend. ← revient. `1`–`8` saute à un chapitre, `D` ouvre la démo de secours, `H` l'aide. |
| **Vidéo continue** (MP4, 10:10) | répéter, envoyer, secours si le lecteur ne s'ouvre pas | rendue par `rendre.py` ; minutage fixe de `02_STRUCTURE.md` |

Le lecteur est hors ligne : polices et captures sont dans le dépôt, aucun appel réseau.

## Le court métrage

Poser le fichier du film à côté de `index.html`, sous le nom **`film.mp4`**. Le lecteur le joue en plein écran au bon
moment (fin du chapitre 2, après « L'homme qui disait oui. »), puis enchaîne seul sur « Et après ? ». Un clic pendant
le film l'arrête et passe à la suite. Sans `film.mp4`, le lecteur affiche un emplacement noir et attend le clic : on
lance alors le film à la main (`05_FILM_INTEGRATION.md` § 5).

## Les chapitres

| # | Temps | Ce qu'on voit |
|---|---|---|
| 1 | 0:00 | la carte de Sophie (personnage fictif) tombe ; « On s'appelle. » ; la boîte à chaussures se remplit ; « Et après ? » dans l'anneau ouvert |
| 2 | 0:45 | « Ce qui se passe entre deux événements. » ; la Foire, un nuage de rencontres qui se défait avant le prochain événement ; « l'après. » ; « Oui. » ; « L'homme qui disait oui. » |
| — | 2:00 | **court métrage** (2:25) |
| 3 | 4:25 | « Et après ? » ; « Le même geste. Dans le vrai produit. » ; l'anneau s'ouvre sur **l'Établi réel** ; projecteur sur les trois pièces, le minibus manque |
| 4 | 5:10 | **démo en direct sur le vrai produit** — le lecteur n'est pas à l'écran. Touche `D` : plan B, les captures réelles de la démo, dans l'ordre |
| 5 | 7:10 | « Ce qui est prouvé. Rien de plus. » ; le reçu réel ; le journal (le monde tombe, il est rejoué) ; « Pauline » devient « transport » ; les chiffres du gel |
| 6 | 8:10 | « L'IA propose. Les règles vérifient. Le membre décide. » ; la chaîne mots → proposition → règles → Oui ; **1 / 26** ; l'interrupteur |
| 7 | 9:10 | « Et après, maintenant, il se passe quelque chose. » ; la carte et le reçu réel ; la phrase finale ; l'anneau se ferme ; Club Pulse |

Après l'acte 4 (« [Prénom], le téléphone est à toi. »), on passe à l'écran du produit. On revient au lecteur à 7:10
et on appuie sur `5` (le lecteur saute la démo de secours par défaut).

## Règles respectées

- **Écrans réels seulement** pour le produit : les captures de `../captures/` (`prototype/scripts/capturer_presentation.py`),
  étiquetées « écran réel ». Aucune maquette présentée comme un écran (D-PRES-3). L'anneau qui se ferme reste dans le
  film et dans ce motion ; sur l'écran réel, c'est la bordure verte (D-PRES-2).
- **Chiffres** : seulement au chapitre 5 (gel) et au chapitre 6 (1 / 26, CLAIMS n° 39 — 25 sorties rejetées par la
  validation). Les chiffres du gel viennent de `chiffres.js`, vide jusqu'au tag `gel-demo` : l'écran affiche `[GEL]`.
- La dernière phrase (« Si Jean-Marc dit oui, c'est que c'est oui. ») **se dit**, elle ne s'écrit pas : à l'image,
  l'anneau du logo se ferme pendant qu'on la prononce.
- Sophie, Pauline, Markus : personnages fictifs. Aucun logo de la Foire du Valais ni du Club des Affaires.

## Après le gel (vendredi 18:00)

1. Recopier les quatre valeurs de `PREUVES.md` dans `chiffres.js`.
2. Relancer le rendu (environ 20 min sur 4 cœurs) :

```sh
FF=$(python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
for i in 0 1 2 3; do python docs/presentation/motion/rendre.py $FF $((i*153)) $([ $i = 3 ] && echo 610 || echo $(((i+1)*153))) /tmp/s$i.mp4 & done; wait
printf "file '/tmp/s%d.mp4'\n" 0 1 2 3 > /tmp/l.txt && $FF -f concat -safe 0 -i /tmp/l.txt -c copy CLUB_PULSE_MOTION.mp4
```
