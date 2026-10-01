# Deck « Club Pulse » — direction artistique

## La direction, en quinze lignes

1. **Lumière.** Le deck vit sur le blanc `#FFFFFF` et le gris d'app `#F2F3F5`, comme le produit. Le noir n'apparaît que
   pour les cinq cartons d'acte : c'est une ponctuation du récit, et c'est la même que celle du film.
2. **Le rouge est un scalpel.** Un mot, un chiffre, un point par slide, jamais plus de 10 % de la surface. Ce rouge
   veut toujours dire ce qu'il veut dire dans le produit : la marque, ce qui manque, ce qui compte.
3. **L'objet central, c'est l'anneau du logo**, copié du design system sans le redessiner. Il se dessine aux trois
   quarts quand il manque une pièce. Il se ferme quand le Club peut le faire. Il sert aussi d'indicateur de
   progression, discret, en bas à droite.
4. **Éditorial suisse.** Composition au fer à gauche, sur une marge de 160 px. Asymétrie assumée, grille de 8 px,
   deux niveaux typographiques au plus.
5. **Lisible à 25 m.** Phrases-affiches de 112 à 180 px. Corps à 36–40 px. Étiquettes mono à 28 px au minimum, en
   `--secondary` (6:1) et jamais en `--tertiary`.
6. **Le produit se montre tel qu'il est.** Captures réelles, sans cadre décoratif. Si une capture manque, un
   emplacement l'annonce par son nom de fichier.
7. **Un mouvement porte une idée, sinon il n'existe pas** :
   - la carte se pose ;
   - l'anneau se dessine, puis se ferme ;
   - les idées entrent une à une, au clic.
8. **Un seul easing**, `cubic-bezier(0.22, 1, 0.36, 1)`, et trois durées : 240, 480 et 720 ms.
9. **Coupe sèche** entre les slides, comme au montage du film. Fondu de 240 ms seulement vers et depuis le noir.
10. **V1 tient le rythme.** Rien ne part sur une minuterie, tout part au clic.
11. **Aucun chiffre écrit en dur.** Les chiffres viennent de `data/gel.json`, et un chiffre absent s'affiche `[GEL]`.
12. **La chaleur vient des monogrammes pastel** du design system (M-04, M-11, M-17, M-23). Ce sont des visages
    pseudonymes, jamais des illustrations.
13. **Hors ligne de bout en bout** : polices, captures et film sont dans le dossier.
14. **« Et après ? »** est un lieu. Même corps, même position, trois fois : le public le reconnaît avant de le lire.
15. **Fin sans logo triomphant.** La carte, le reçu, la phrase, puis le noir.

## Les slides et leur intention

| # | Slide | Acte | Intention (une phrase) |
|---|---|---|---|
| 1 | La carte (M1) | 1 | Une carte de visite se pose une fois : l'objet que tout le monde a déjà donné pour rien. |
| 2 | Et après ? (1/3) | 1 | La question, posée à sa place, qui reviendra au même endroit. |
| 3 | Carton DEMANDE | 2 | Ouvrir l'acte : ce qui se passe entre deux événements. |
| 4 | Le vide | 2 | Les rencontres se serrent autour de la Foire, et rien ne traverse la ligne jusqu'au prochain événement. |
| 5 | Oui. | 2 | Le seul mot qui change tout. Son point rouge, c'est le point du logo : la pièce qui arrive. |
| 6 | Carton CONTRIBUTION | 2 | Annoncer Jean-Marc, puis couper au noir. |
| F | Le film | 3 | Le court métrage en plein écran ; à la fin, le dernier plan reste figé (ce qui remplace l'ancienne slide 7). Sans fichier, le plan B s'affiche : le carton et les trois phrases. |
| 8 | Et après ? (2/3) | resp. | La même question, au même pixel, après le film. |
| 9 | Carton ESSAI | 4 | Passer de la fiction au produit. |
| 10a | Il manque une pièce (M4) | 4 | L'anneau se dessine aux trois quarts et s'arrête : le manque se voit avant qu'on le dise. |
| 10 | L'Établi | 4 | L'écran réel, plein cadre, sans légende : la demande existe pour de vrai. |
| 11 | Démo — fond | 5–6 | Un fond qui ne rivalise pas avec le produit. Six repères discrets avancent au clic, et la touche B affiche la capture de secours de l'étape. |
| 11R | Reprise (M4) | 6 | Le point glisse dans la brèche et l'anneau se ferme : le Club peut le faire. |
| 12 | Carton RÉSULTAT | 7 | Annoncer ce qui est prouvé, rien de plus. |
| 13 | Trois preuves | 7 | Le reçu, le journal et le retrait, une ligne chacun, au clic. |
| 14 | Les chiffres du gel (M5) | 7 | Cinq chiffres mono posés un à un, tous lus dans `gel.json`. |
| 15 | L'IA | 8 | Trois verbes, trois rôles ; le soulignement rouge tombe sur « décide ». |
| 16 | 1 / 26 | 8 | La mesure telle qu'elle est : un chiffre, et vingt-six cases dont une seule est pleine. |
| 17a | Et après ? (3/3) | 9 | La question revient une dernière fois, à sa place exacte, juste avant sa réponse. |
| 17b | Carton REÇU | 9 | La réponse en deux temps : « Et après », puis « , maintenant, il se passe quelque chose. » |
| 18 | La carte et le reçu (M6) | 9 | La carte revient à l'identique et s'écarte ; le reçu réel se pose avec le même geste. |
| 19 | Phrase finale | 9 | « La Foire crée la rencontre. Club Pulse crée l'après. » ; le dernier membre se dit, il ne s'écrit pas. |
| 20 | Noir | 9 | Le silence. |
| 21 | Repères pour les questions | Q&R | Le lockup et la source de chaque affirmation. |

## Idées que le brief n'avait pas prévues (une par acte au plus)

- **Acte 2 — le point rouge de « Oui. ».** Le point final est celui du logo, la pièce qui arrive : le mot et la
  marque se répondent sans un mot de plus.
- **Acte 2 — les monogrammes sur « le vide ».** Cinq pastilles pseudonymes se serrent autour de la Foire et aucune
  ne traverse : on voit « des centaines de rencontres » sans afficher un chiffre. (Le brief autorise les pastels ;
  l'idée, c'est leur placement.)
- **Acte 5 — des repères de démo qui servent de chronomètre.** Le repère « reçu » est le point de contrôle de 6:35 du
  mode répétition : V1 clique en même temps que V2 agit.
- **Acte 6 — une slide de reprise ajoutée (11R).** Elle fait exister la fermeture de l'anneau (M4) après la démo,
  sans toucher l'écran réel (D-PRES-2).
- **Acte 7 — le zéro vérifié.** Le « 0 » de la slide 14 porte la coche verte du langage de confiance (design system
  § 3, « Zéro vérifié ») : c'est la seule couleur de la slide, et elle a un sens.
- **Acte 8 — les vingt-six cases.** Le « 1 / 26 » devient visible, pas seulement lisible : une case pleine,
  vingt-cinq vides. On ne peut pas le lire à la hausse.
- **Acte 9 — « Et après ? » (3/3) juste avant le carton REÇU.** C'est la condition du « même pixel » (M2), et la
  question reçoit sa réponse à l'endroit même où elle a été posée.

## Écarts assumés au brief, et pourquoi

- **Les deux dessins de l'anneau animent `stroke-dashoffset`, pas `transform` ni `opacity`.** C'est le seul moyen de
  dessiner un arc sans le redessiner autrement que le design system. L'effet reste de la peinture sur un seul SVG,
  sans aucune mise en page recalculée : on reste à 60 fps (mesuré dans la revue).
- **L'ancienne slide 7, « dernier plan figé », est absorbée par la slide du film.** La vidéo s'arrête sur sa dernière
  image ; le clic suivant mène à « Et après ? ».
- **« Et après ? » n'est plus sur fond noir** (06_SLIDE_CONTENT) : le brief réserve le noir aux cinq cartons. Pour la
  même raison, la phrase finale (19) est en clair.
- **Les sept captures sont déjà présentes** (`assets/captures/`), prises le 01.10 sur la machine de développement par
  `prototype/scripts/capturer_presentation.py`. Ce sont des écrans réels ; on les remplace samedi, sous les mêmes noms.
  L'emplacement de remplacement ne s'affiche que si un fichier manque.

## Revue — défauts trouvés et corrigés

(rempli à chaque passe : `review/v1/`, `review/v2/`, `review/final/`)

### Passe 1 (review/v1) → corrigé en v2

1. **Slide 1, carte** : texte tassé en haut, centre vide, un trait gratuit. On aurait dit un gabarit.
   → Composition de carte éditoriale : lieu en mono en haut, « Sophie » 136 px en bas à gauche, filets de contact en
   bas à droite. Trait retiré.
2. **Cartons 3, 9, 12** : veuves typographiques (« événements. », « produit. », « plus. » seuls sur leur ligne).
   → Coupures écrites à la main et `text-wrap: balance`.
3. **Indicateur de progression** : un cercle partiellement rempli se lisait comme un spinner de chargement.
   → Neuf arcs séparés, un par acte, encre pour les actes passés.
4. **« Oui. »** : le point de Jakarta est carré, alors que le point du logo est rond.
   → Point rond rouge dessiné, à la taille du point typographique.
5. **« Et après ? »** : l'espace normale avant « ? » ouvrait un trou.
   → Espace fine insécable (U+202F), comme en typographie française.
6. **Slide 11R** : le point absorbé dépassait de l'anneau fermé (une bosse en haut à gauche).
   → Le point glisse dans la brèche, l'arc se ferme, puis le point s'efface (240 ms).
7. **Slide 16** : l'espacement du mono étirait « 1 / 26 ».
   → « 1/26 » serré, barre oblique en gris secondaire.
8. **Slide 18** : le reçu était l'écran du téléphone entier, illisible à 25 m.
   → Recadrage sur la carte du reçu (`object-view-box`, image non modifiée), 740 px de large, posé sur la carte comme
   un objet sur une table.
9. **Slide 10** : l'indicateur se superposait à l'écran réel.
   → Masqué sur les captures plein cadre.

### Passe 2 (review/v2) → corrigé en final

1. **Slide 4, « le vide »** : la composition était tassée en haut à gauche, et la moitié basse restait vide.
   → Ligne descendue à 686 px, pastilles à 132 px et mieux réparties, étiquettes à 44 px.
2. **Indicateur** : encore trop petit pour se lire comme un anneau.
   → 72 px, trait 3,2.
3. **Contraste mesuré, AA non atteint** à deux endroits :
   - repères de démo pas encore atteints, 1,52:1 → `--secondary` (6:1) ;
   - barre oblique de « 1/26 », 1,68:1 → `--secondary`.

### Ce qui reste volontairement

- **Slide 11 (démo) très vide.** Elle est faite pour ne pas rivaliser avec le produit projeté par ailleurs.
- **Plan B du film en texte long (52 px).** Il ne s'affiche que si le film ne part pas, et V1 le dit en même temps.

### Ajout — mode jour (projection en salle éclairée)

Un projecteur ne fait pas de noir. Les cinq cartons, la slide du film et le noir final existent donc en deux rendus :

- **nuit** : noir et blanc ;
- **jour** : `#F2F3F5` et `#141923`.

Tout le reste est inchangé, à l'octet près. Le choix est global : `J`, ou `?mode=` au lancement ; il n'y a jamais de
choix slide par slide. En mode jour, l'écran `N` devient un gris neutre, parce qu'un noir en salle claire attire plus
l'œil qu'un gris calme. Contraste AA vérifié dans les deux modes. Revue : `review/final/nuit/` et
`review/final/jour/`.
