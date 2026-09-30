# Revue contradictoire — WOW audit, test de réduction, attaque du jury (2026-09-30)

Méthode : une revue **hostile en lecture seule** (agent séparé, sans droit d'écriture) a lu le code, les captures et la
vidéo enregistrées au commit `6dc7322`, puis vérifié ses constats par des scripts. Chaque constat ci-dessous a été
**rejoué** par l'équipe avant d'être corrigé. Rien ici n'est une validation par un jury réel : **aucun juré, aucun
membre du Club n'a vu la démonstration**. « WOW » n'est pas auto-certifié.

Légende : **F** = fait vérifié (fichier, test ou capture) · **H** = hypothèse non vérifiée.

## 1. Les 30 premières secondes (vidéo `captures/action/demo_action.webm`)

| t | Écran commun | Ce qu'un juré qui découvre comprend (H) | Constat |
|---|---|---|---|
| 0–7 s | « Jeudi 05.11 : 6 contributions proposées, dispersées » — barres d'horaires anonymes | des offres, avec des horaires ; pas encore pourquoi c'est un problème | F : la dispersion est **mise en scène** par des données préparées (dont 3 pièges réels : horaire du matin, personne qui refuse les sollicitations, offre sans horaire) |
| 8–19 s | (téléphone) Sophie écrit son besoin ; 3 exigences, « Règles simples — aucun modèle » | une personne demande de l'aide | F : avant correction, la **fiche en allemand** et le **lieu** étaient ajoutés par une règle sans avoir été demandés |
| ~20 s | « Proposition complète : 05.11 16:00–16:45 » + cadre sur la ligne de temps | « le serveur a trouvé un moment commun » — lisible en < 5 s (H) | F : avant correction, l'écran disait « **le seul moment** » alors que les disponibilités se recouvrent de 16:00 à 17:30 (6 créneaux de 45 min) |
| ~40 s | « Ce qui vient de changer » : ne couvre plus / reste valable / adaptations | le seul moment non trivial | hors des 30 premières secondes : **le « wow » éventuel arrive tard** (H) |

**Ce qui pourrait donner envie d'en voir plus (H)** : la valeur choisie en direct par le jury, et l'encadré rouge qui
dit ce qui tombe et ce qui tient sans rien inventer. Non mesuré.

**Correction de rythme retenue** : dans le script de 2 minutes, la perturbation est annoncée dès la 1re phrase
(« dans 40 secondes, vous changerez une condition ») ; l'écran « avant » passe de 7 s à 4 s à l'oral.

## 2. Test de réduction : « un réseau social avec matching » ?

La réduction la plus honnête proposée par la revue n'est pas « réseau social » (aucun graphe social n'est montré) mais :
**« un Doodle à plusieurs ressources + un annuaire d'offres + une confirmation liée à une version »**.

| Ce que la réduction décrit | Ce qu'elle ne décrit pas (F : implémenté et testé) |
|---|---|
| trouver un créneau commun | un accord lié à UNE version : si le moment change, **tous** reconfirment ; si seule une part change, seule cette personne |
| un annuaire d'offres | le calcul de ce qui **tombe** et de ce qui **tient**, et des adaptations admissibles (jamais sous le minimum fixé) |
| des confirmations | « bloqué » dit honnêtement, puis rouvert par un fait nouveau — jamais relancé tout seul |
| — | transmis ≠ reçu ≠ réalisé ; silence ≠ succès (+30 jours : « résultat inconnu ») |

**Conclusion (H)** : c'est de la **rigueur de coordination**, pas une capacité technologique nouvelle. La proposition
« aucun des membres mobilisés ne pouvait le faire seul » est vraie **dans ce cas** et **par construction** (une personne
ne porte pas deux gestes ; l'offre de chacun ne couvre qu'une exigence) : elle n'est pas démontrée en général.

## 3. Attaque du jury — cinq perspectives

| Perspective | Objection | F/H | Preuve regardée | Constat | Suite donnée |
|---|---|---|---|---|---|
| Ingénieur senior | La réception de la fiche marque tout le geste « voix » comme reçu, présentation comprise ; un retrait ensuite est ignoré | F | `essai.py` `constater`, capture p5 (datée du 03.11 pour une présentation le 05.11) | **défaut réel** | **corrigé** : `recevoir` (fiche) ≠ `constater` (geste au créneau, pas avant son jour) ; palier « livrable reçu » ; un retrait après réception rouvre l'adaptation. Test `test_une_fiche_recue_ne_vaut_pas_la_presentation…` |
| Ingénieur senior | La capacité compte des essais, pas des heures : une personne peut être engagée deux fois au même moment | F | `reservations`, capacité 2 de l'offre de Léa | **défaut réel** | **corrigé** : `occupations` + `_chevauche` dans `offre_couvre`. Test `test_une_personne_n_est_jamais_engagee_deux_fois…` (échoue sans la règle) |
| Ingénieur senior | +30 jours : un lieu accepté et engagé s'affichait « ne couvre plus » (l'offre datée avait expiré) | F (trouvé par l'équipe) | `raisons_gestes` | **défaut réel** | **corrigé** : après le moment de l'action, l'état actuel d'une offre ne requalifie plus un accord. Test `test_trente_jours_plus_tard…` (échoue sans la règle) |
| Ingénieur senior | Journal en mémoire par défaut ; plusieurs processus non testés | F | `reglages.py` | limite | documentée (§ limites du passage à Codex) ; `HACKVS_ESSAIS_DB` rend le journal durable |
| Expert produit | La fiche en allemand et le lieu sont **ajoutés** par une règle, pas demandés | F | `ia.py` `_action_regles`, capture a1 | **défaut réel** | **corrigé** : livrable seulement si un écrit est demandé ; lieu seulement s'il est nommé. Le besoin de la démo dit désormais « je n'ai ni stand ni personne qui parle allemand, et j'aimerais leur laisser une fiche en allemand » |
| Expert produit | Compatibilité = nature + code de capacité : une offre de **conseil** export datée serait proposée pour « **amener** des acheteurs » | F (par lecture) | `offre_couvre`, offre « Conseil pour lancer un produit… » | **limite non corrigée** | exclue aujourd'hui seulement parce qu'elle n'a pas d'horaire. Correction proposée : un **type d'acte** par geste et par offre. Point d'audit n° 1 |
| Expert produit | « Reste valable (rien à redonner) » à côté de « chaque participant reconfirme » | F | `app.html`, capture a3 | libellé contradictoire | **corrigé** : « Reste valable pour le créneau actuel — si le moment change, chacun reconfirme » |
| Responsable innovation | L'IA est-elle nécessaire ? La démo tourne en « règles simples » ; le créneau est une intersection d'intervalles | F | capture a1, `resultats_apertus.md` | **vrai : non nécessaire pour cette démo** | dit à l'oral ; Apertus **non exécuté** (aucun identifiant). Le banc comptait une exigence inventée comme juste → **notation stricte** + attente corrigée (« tenir NOTRE stand ») |
| Responsable innovation | La nouveauté revendiquée est un invariant de conception, pas un résultat observé | H | — | juste | présenté comme tel : aucune donnée d'usage |
| Représentant du Club | L'écran commun projetait le **brouillon** d'un membre et un texte d'offre identifiant (« stand de la distillerie, halle 3 ») | F | `essai_api.py` projection, capture p3 | **défaut réel** | **corrigé** : rien n'est projeté sans le choix de la porteuse (`autoriser_projection`, bouton sur SON téléphone, retirable) ; la projection ne contient que des horaires et des rôles ; adaptations dites en rôles. Test `test_rien_n_est_projete_sans_l_accord…` |
| Représentant du Club | WhatsApp suffit pour 3 personnes | H | outils réels du Club : **inconnus** | non tranché | test terrain proposé : même besoin via le groupe habituel et via Club Pulse ; mesurer temps jusqu'à une équipe confirmée, erreurs de créneau, relances |
| Investisseur | Aucun utilisateur, qui paie, coût d'hébergement | F | `PREUVES.md` | vrai | hypothèses affichées comme telles ; rien n'est chiffré |
| Investisseur | Valeur entre deux événements : les offres expirent, rien n'est reconduit | F | étape +30 jours | vrai **par choix** | la mémoire garde ce qui a été reçu et déclaré ; fréquence réelle des besoins à plusieurs : **non mesurée** (compter les demandes à plusieurs des 12 derniers mois) |

Libellés corrigés au passage (F) : « Voix allemande » et « Public germanophone » écrits en dur → libellés **dérivés du
geste** ; « Jeudi » écrit en dur → jour calculé ; « Produit : apporté » → « sa part (déclaré) » ; « confirmé par les
participants » affiché sans confirmation → « résultat DÉCLARÉ » ; « 3 adaptations admissibles » (plafond de 3) →
« 3 adaptations proposées, les plus proches d'abord » ; « brouillon (visible de vous seul) » sur un écran public →
« brouillon : rien n'est encore envoyé à personne ».

Écart signalé et expliqué : la vidéo annonçait « 944 ms » quand `delais.json` indique 341 ms. Ce sont deux mesures
différentes : la vidéo mesure dans la régie (3 cadres + enregistrement vidéo), le test sur une page de projection seule.
Les deux sont désormais publiées avec leur contexte.

## 4. Ce qui reste à valider (hors de portée de cette session)
1. Un juré réel comprend-il en 30 s ? → 3 personnes extérieures, vidéo coupée à 30 s, une question : « que fait le système ? ».
2. Un exposant formule-t-il ses besoins comme Sophie ? → 5 formulations réelles ; compter les exigences qu'il supprime.
3. Club Pulse fait-il mieux que le groupe habituel du Club ? → le test terrain ci-dessus.
4. Apertus apporte-t-il quelque chose ? → `eval/eval_apertus.py` avec un identifiant réel, formulations réelles.
