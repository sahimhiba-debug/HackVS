# 09 — Script de démonstration : une page, trois scènes (`/demo/stage`)

Données : réseau de scène FICTIF (16 membres inventés + Sophie, `prototype/data/stage_reseau.json`). Horloge simulée.
Chaque chiffre est calculé en direct par le moteur réel ; la scène se rejoue à l'identique (testé 3 fois).
Commandes : **→ / espace** suivant · **←** précédent · **R** réinitialiser · clic sur une relation du graphe (scène B).
Mesures de lisibilité : `competition/rehearsal/MESURES_SCENE.md` (attente après clic < 200 ms ; aucune erreur).

**Durée cible : 2 min 30 s.** Les chiffres entre crochets sont ceux de la scène sans modèle d'IA (vérifiés par
`validate_competition_claims.py`). Si un modèle est configuré, la scène A change : **rejouer toute la scène avant de
monter sur scène** et lire les chiffres à l'écran, pas ceux de ce script.

| # | Scène | L'écran montre (calculé) | On dit (≤ 2 phrases) | Durée |
|---|---|---|---|---|
| 0 | — | Deux îlots, 16 membres | « La Foire crée les rencontres. Un mois plus tard, qu'en reste-t-il — et que doit faire l'organisatrice ? » | 10 s |
| 1 | A | La phrase de Sophie ; à gauche les règles (comprennent mal → s'abstiennent) ; à droite l'IA (non configurée ici, ou vérifiée) | « Une vraie phrase : trois besoins, une langue, une exclusion. Nos règles échouent — c'est exactement là que l'IA doit prouver sa valeur, et chaque critère qu'elle propose doit citer le texte. » | 25 s |
| 2 | A | Markus : preuve citée, réciprocité PROUVÉE, inconnu affiché | « Pas une liste : une personne dont le profil prouve qu'elle peut aider — et qui cherche justement ce que Sophie produit. » | 15 s |
| 3 | A | Coordonnées : non → oui après son accord ; ligne de temps | « Une introduction, pas un numéro. Il pouvait refuser. » | 10 s |
| 4 | B | 4 phénomènes ; 2 ponts fragiles en orange | « Vue de l'organisatrice : deux parties du Club ne tiennent qu'à un fil. » | 15 s |
| 5 | B | Plan vert « Consolider » [robuste 4 → 8] vs rouge « Réunir les îlots » [reliés 8 → 15, robuste reste 4] | « Une seule introduction ce mois-ci. Réunir les îlots, ou consolider ? Aucun plan ne gagne sur tout : le système montre le prix, elle choisit. » | 25 s |
| 6 | B | Relation Jérôme – Thomas : [4 membres coupés de leur groupe de 8] ; **cliquer une autre relation** en direct | « Et si cette relation s'éteint ? Voici qui le Club perd. » (clic) « Celle-ci, en revanche, est doublée : personne n'est coupé. » | 20 s |
| 7 | C | [1 relance, avec sa preuve ; 17 silences] | « Dix jours plus tard : une seule raison nouvelle de se reparler. Le reste : silence. » | 15 s |
| 8 | C | 3 demandes refusées : Japon (abstention), membre qui a refusé, introduction sans aide prouvée | « Il sait dire non — et dit pourquoi. » | 10 s |
| 9 | C | Ce qui est fait / observé / simulé / non mesuré | « Tout ceci est fictif et calculé. La valeur réelle se mesure par un pilote — voici comment. » | 5 s |

## Plans B
- **Pas de réseau dans la salle** : tout tourne en local (`uvicorn app.main:app`), sans aucune dépendance externe.
- **Modèle d'IA absent, lent ou en panne** : la scène A le dit elle-même et continue par la reformulation (testé :
  panne → repli visible ; interprétation sans personne de prouvé → reformulation). Ne jamais dire « l'IA a compris »
  si l'écran indique « non configurée ».
- **Navigateur planté** : la vidéo de secours (`competition/video/`) — à régénérer sur cette scène en trois actes
  (`scripts/enregistrer_video.py`).
- **Question hors scène** : `/decision`, `/cycle`, `/` restent disponibles, mais ne sont pas montrés spontanément.
