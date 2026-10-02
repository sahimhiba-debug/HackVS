# Deck « Club Pulse » — mode d'emploi

Le deck visuel de la finale (Hack VS 2026), construit à partir de `06_SLIDE_CONTENT.md` et `02_STRUCTURE.md` dans le
design system figé. La direction artistique et les intentions slide par slide sont dans `DIRECTION.md`. Les rendus
de validation sont dans `review/final/nuit/` et `review/final/jour/`, un PNG par slide, numéroté.

## Lancer

```sh
python3 docs/presentation/deck/lancer.py        # ouvre http://127.0.0.1:8765/index.html
```

Puis appuyer sur `F` pour passer en plein écran.

- **Tout est local.** Polices (woff2), captures, film et données sont dans ce dossier. Il n'y a aucune requête
  réseau : c'est vérifié avec un navigateur qui refuse toute sortie.
- **Le serveur ne sert que ce dossier**, et seulement sur 127.0.0.1. Il est nécessaire parce que Chrome refuse de lire
  `data/gel.json` depuis un fichier ouvert en double-clic.
- **Si on ouvre quand même le deck en double-clic**, les slides 14 et 16 affichent en rouge
  « data/gel.json non lu — lancer le deck avec lancer.py ». Le deck ne montre jamais un chiffre faux sans le dire.
- **Sans Python sur la machine de la salle** : `npx serve` ou tout autre serveur statique local fait l'affaire.

## Clavier (et télécommande de présentation)

| Touche | Effet |
|---|---|
| → · ↓ · Espace · Entrée · Page Down · clic | étape suivante, puis slide suivante |
| ← · ↑ · Page Up · Retour arrière · clic droit | étape précédente |
| `N` | écran noir en mode nuit, écran neutre gris en mode jour (et retour) |
| `J` | bascule jour / nuit pour tout le deck, annoncée 2 s en haut à droite |
| `R` | mode répétition : chrono et 8 points de contrôle. `Maj+R` remet le chrono à zéro |
| `B` | sur la slide de démo : capture de secours de l'étape en cours (et retour) |
| `F` | plein écran |
| Début / Fin | première / dernière slide |

L'adresse garde la position (`#14.3` = slide 14, étape 3). Après un incident, recharger la page revient au même
endroit.

## Vendredi soir : remplir les chiffres du gel

Éditer **`data/gel.json`, et rien d'autre**, après le tag `gel-demo` : recopier les valeurs depuis
`docs/audit/club-pulse-pivot/PREUVES.md`.

- Chaque valeur est un texte, affiché tel quel : `"1 381"`, `"1 229 / 1 327"`, `"< 1 s"`, `"0"`.
- Une valeur `null` s'affiche `[GEL]`.
- `gel.commit` s'imprime en petit au-dessus des chiffres.
- La mesure IA (slide 16) est dans le même fichier, sous `ia`.

Vérifier ensuite : `python3 docs/presentation/deck/revue.py docs/presentation/deck/review/final/nuit 1 nuit` (puis la
même chose avec `jour`), et relire `16-14.png` et `18-16.png`.

## Mode jour (salle éclairée)

Un projecteur ne fait pas de noir : en salle éclairée, un carton noir devient gris délavé.

- **Le mode jour** passe en clair les seules slides sombres : les cinq cartons, la slide du film (plan B compris) et le
  noir final. Fond `#F2F3F5`, encre `#141923`, même composition au pixel, même apparition en 480 ms. Les fondus
  deviennent clairs, et l'écran `N` devient un gris neutre.
- **Aucune autre slide ne change.** C'est vérifié : les 17 autres PNG de `review/final/jour/` et `review/final/nuit/`
  sont identiques à l'octet.
- **Pour figer le mode au lancement** : `index.html?mode=jour` ou `?mode=nuit`. Le défaut est nuit.
- **Pendant la présentation**, `J` bascule tout le deck d'un coup. Il n'y a pas de choix slide par slide.
- **Le choix survit à un rechargement** de la page, dans le même onglet.
- **Pendant le film**, la vidéo garde ses propres noirs. Le raccord se fait par les cartons de fin du film, qui suivent
  la même décision.
- **Décision samedi** : test de salle, `04_DEMO_RUNBOOK.md` § 8, point 6.

## Déposer le film

Copier le fichier sous **`assets/film.mp4`**. Ce fichier est ignoré par git (`.gitignore`) : il ne va jamais dans le dépôt public ; on le
copie à la main (AirDrop, clé USB). `lancer.py` sert les vidéos par plages : on peut sauter dans le film, et Safari
peut le lire. Format sûr : MP4 H.264.

- **Premier clic** sur la slide du film : lecture en plein écran.
- **À la fin**, le dernier plan reste figé. C'est l'ancienne slide 7.
- **Clic suivant** : « Et après ? ».
- **Sans fichier**, la slide affiche le plan B de `05_FILM_INTEGRATION.md` § 6 : le carton, puis les trois phrases,
  au clic.

Tester sur la machine de la salle : le format doit être lisible sans codec à télécharger.

## Samedi : les captures

Les sept emplacements portent les noms exacts du runbook (`04_DEMO_RUNBOOK.md` § 6), dans `assets/captures/` :

- `etabli-1-manque.png` — slide 10 ;
- `tel-1-demande.png`, `tel-1b-proposition.png`, `etabli-2-peut.png`, `tel-2-recu.png`, `etabli-3-retrait.png`,
  `tel-3-jure.png` — touche `B` sur la slide de démo ;
- `tel-2-recu.png` — slide 18 aussi.

**État actuel** : une première série réelle est déjà en place. Elle a été prise le 01.10 sur la machine de
développement par `prototype/scripts/capturer_presentation.py`.

**Samedi** : remplacer les fichiers par ceux de la répétition, sous les mêmes noms. Un fichier absent affiche un
emplacement rouge pointillé qui porte son nom.

**Slide 18** : le reçu est recadré sur sa carte, sans retouche de l'image, par l'attribut
`data-recadrage="472px 32px 584px 32px"` sur l'image (marges haut, droite, bas, gauche, en pixels de la capture). Si la
nouvelle capture place la carte du reçu ailleurs, ajuster ces quatre valeurs, puis relancer la revue.

## Mode répétition (`R`)

Le chrono démarre à l'appui sur `R`. Une barre discrète, en bas de l'écran, suit les huit points de contrôle de
`02_STRUCTURE.md`. Chacun est enregistré quand on arrive sur la slide qui lui correspond :

| Point | Cible |
|---|---|
| « Et après ? » (après les mains levées) | 0:35 |
| « Il s'appelle Jean-Marc. » (carton) | 1:55 |
| Fin du film (film de 3:21) | 5:21 |
| Établi plein écran | 5:45 |
| Reçu sur le téléphone (repère « Le reçu » de la slide de démo) | 8:40 |
| Slide chiffres | 10:30 |
| Slide IA | 11:25 |
| Carte + reçu | 12:40 |

Lecture de la barre :

- **Vert** : dans les temps, à 15 s près.
- **Rouge** : la coupe prévue s'affiche en une ligne.
- **Retard en cours de route** : si on dépasse la cible du prochain point de plus de 15 s, la coupe s'affiche avant
  même d'y arriver.

Cibles du 02.10 au soir : film final de 3:21, créneau de 15 minutes, fin visée à 13:30 avec 1:30 de marge
(`02_STRUCTURE.md`). Si le film ne part pas (plan B), ignorer les cibles après 2:00 : tout avance de 1:40.

Le mode est éteint par défaut. On ne présente jamais avec.

## Vérifié (01.10, Chromium)

- **Navigation au clavier complète**, aller et retour : 24 slides, 48 états.
- **Réseau coupé** : zéro requête sortante, polices chargées, aucune erreur JavaScript.
- **Animations** : uniquement `transform` et `opacity`, plus le tracé de l'anneau (`stroke-dashoffset`, justifié dans
  `DIRECTION.md`).
- **Fluidité** : 17 ms par image en moyenne pendant les deux moments signature, sur un Chromium sans GPU.
- **`prefers-reduced-motion`** : tout devient un fondu simple.
- **Contraste** : AA partout, dans les deux modes (83 textes contrôlés, aucun échec). Le plus bas est la pastille « M-23 », à 4,45:1 en 32 px, alors que AA exige 3:1 pour du
  texte de cette taille.
- **Plan B du film et emplacement de capture manquante** : testés.
