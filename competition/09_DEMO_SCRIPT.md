# 09 — Script de démonstration : une histoire, une page (`/demo/stage`)

Données : réseau de scène FICTIF (16 membres inventés + Sophie, `prototype/data/stage_reseau.json`). Horloge simulée.
Chaque chiffre est calculé en direct par le moteur ; la scène se rejoue à l'identique (testé) ; aucune IA générative,
aucun appel réseau. Commandes : **→ / espace** suivant · **←** précédent · **R** réinitialiser · **T** tour de contrôle ·
clic sur une relation (à partir de l'étape 8) : simuler sa disparition.
Lisibilité mesurée : `competition/rehearsal/MESURES_SCENE.md` · Bout en bout : `tests/test_e2e_scene.py`.

**Fil à raconter (une phrase par étape) :** nouveau membre → besoin → candidats → consentement → rencontre → suivi →
opportunité → le réseau change → le refus → la saturation → ce qui est prouvé.

| # | Chapitre | L'écran montre (calculé) | On dit | Durée |
|---|---|---|---|---|
| 0 | — | 16 membres, deux îlots | « La Foire crée des rencontres. Que deviennent-elles quand elle se termine ? » | 5 s |
| 1 | Nouveau membre | Sa phrase ; le système propose, Sophie valide ; invisible par défaut | « Sophie arrive. Une phrase suffit ; c'est elle qui valide, et elle choisit d'être visible. » | 10 s |
| 2 | Besoin | Besoin principal, langue, contrainte — chacun avec le mot qui le justifie | « Il comprend chaque demande et montre le mot qui la justifie. Des règles vérifiables, pas d'IA. » | 15 s |
| 3 | Candidats | Markus : preuve citée, réciprocité prouvée, inconnu | « Pas parce qu'il lui ressemble : parce que son profil prouve qu'il peut l'aider. » | 15 s |
| 4 | Consentement | Coordonnées cachées → partagées après son accord | « Une introduction, pas un numéro. Il peut refuser. » | 10 s |
| 5 | Rencontre | Ligne de temps de la relation | « La relation garde son histoire. » | 5 s |
| 6 | Suivi | [1 relance fondée · 17 silences] | « Une seule raison nouvelle de se reparler ; le reste, silence. » | 10 s |
| 7 | Opportunité | « affaire en cours déclarée » | « Une opportunité — pas encore un résultat. » | 5 s |
| 8 | Réseau | [groupes 2 → 1 · robuste 4 → 15 · isolés 2 → 2] | « Trois introductions prouvées : les îlots n'en forment plus qu'un. » | 20 s |
| 9 | **Abstention** | « Je pourrais inventer une connexion. Je préfère m'abstenir. » [15 possibles · 0 fondée] ; trait gris : ce qu'un moteur par ressemblance proposerait | « Chantal n'a aucune relation. La relier embellirait notre propre indicateur. Aucune raison prouvée : il s'abstient. » | 25 s |
| 10 | Saturation | Soirées [9 → 1 → 0] puis abstention | « Il ne fabrique pas de rencontres. » | 10 s |
| 11 | Bilan | Fait / simulé / règles / non mesuré | « Tout est fictif et calculé en direct ; la valeur réelle se mesurera par un pilote. » | 5 s |

Durée : ≈ 2 min 15. Les chiffres entre crochets sont vérifiés par `validate_competition_claims.py` (C05, C09, C23, C24).
**Tour de contrôle (T)** : pour une question d'organisateur ; chaque chiffre s'ouvre sur sa définition et sa liste.

## Plans B
- **Pas de réseau dans la salle** : tout tourne en local (`uvicorn app.main:app`), sans aucune dépendance externe.
- **Navigateur planté** : `competition/video/demo.webm` (même histoire, sous-titrée) ; ou **R** puis « Rejouer tout ».
- **Clic sans effet** : une seule action est acceptée à la fois (protection du double clic) ; attendre une seconde.
