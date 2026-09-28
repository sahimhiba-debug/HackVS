# Journal des boucles (mode autonome)

Chaque boucle : hypothèse → changement → tests → défauts trouvés → corrections → mesures avant/après → prochain problème.
Critères de sortie suivis : A (parcours E2E) · B (rejouable depuis zéro) · C (source unique des relations) ·
D (permissions) · E (explication = décision) · F (réciprocité testée) · G (simulation avant/après) · H (benchmark propre) ·
I (adversarial) · J (aucun défaut critique connu) · K (tests) · L (lint) · M (desktop + mobile) · N (démo stable) ·
O (abstention) · P (différent d'un outil de matchmaking).

## BOUCLE 1 — nouveau membre, réciprocité prouvée, explication = décision

**Hypothèse.** Le parcours central (« un nouveau membre rejoint le Club → besoin → candidats ») n'existe pas : les
profils sont figés ; et la « réciprocité » affichée n'est peut-être pas ce qu'elle prétend.

**Audit (code réel).**
- `matching.py` : la « réciprocité » = le candidat cherche quelque chose *dans le secteur* du demandeur. Ce n'est pas
  « le demandeur peut l'aider », et rien ne le prouve. La carte pouvait afficher « Réciprocité : cherche aussi… »
  À CÔTÉ de ma dimension « réciprocité non établie » : décision et explication contradictoires (critère E violé).
- `PAR_ID` était une copie figée des profils de référence : un nouveau membre y serait resté invisible.

**Changements.**
- Adhésion d'un nouveau membre (démo) : `POST /api/demo/rejoindre`, profil validé (vocabulaire fermé, ≥ 1 offre),
  **invisible par défaut** (recommandé à personne tant qu'il ne l'accepte pas), aucune coordonnée enregistrée.
  `par_id()` remplace la copie figée ; la réinitialisation retire les adhésions.
- Réciprocité PROUVÉE : le même moteur en sens inverse (une recherche ou un besoin public du candidat couvert par une
  offre du demandeur, citée mot pour mot). Le badge sectoriel est renommé honnêtement (« cherche aussi dans votre
  secteur ») et masqué quand la réciprocité prouvée est affichée. Classement du moteur inchangé (pas de réglage
  implicite sur les jeux réservés).

**Défauts trouvés en attaquant (reproduits par un test AVANT correction).**
- FUITE : le plan de soirée et l'espace de décision utilisaient les **brouillons** (privés) et les besoins **clos**
  comme « besoin publié » — un brouillon pouvait devenir la raison affichée d'une rencontre. Test rouge → correction à
  la source (`soiree._recherches` : seulement `STATUTS_PUBLICS`, règle unique partagée avec la Bourse) → vert.

**Tests.** `test_confidentialite_reseau.py` (2), `test_explications.py` (4) : nouveau membre invisible puis visible ;
réciprocité oui (Nadia ↔ Inès : développement web ↔ référencement) et non (financement) ; cohérence décision /
explication recalculée indépendamment sur les candidats de TOUS les membres (21 cartes : 3 réciprocités établies,
18 non) ; validation des entrées. **Test de mutation** : une réciprocité inventée et une réciprocité masquée sont
toutes deux détectées.

**Mesures.** 98 → 104 tests ; lint vert ; 20/20 scénarios ; non-régression des évaluations inchangée.

**Prochain problème prioritaire.** G (simulation avant/après d'une introduction sur le graphe) et la démonstration
guidée du parcours central, rejouable depuis zéro (A, B, N).

## BOUCLE 2 — suivi fondé sur la réciprocité, simulation avant/après, horloge unique

**Hypothèse.** Le parcours s'arrête à la rencontre ; un suivi n'a de valeur que s'il a une raison réelle, et « le
réseau évolue » doit se montrer par une simulation, pas s'affirmer.

**Changements.** Relance `RECIPROCITE_OUVERTE` (la rencontre a servi un sens ; l'autre sens est prouvé et n'était pas
la raison documentée → proposée à celui qui en bénéficie) ; `reseau.simuler` (copie du graphe, indicateurs avant/après,
nouveaux ponts, portée à 2 poignées de main ; rien n'est écrit) ; les besoins publics du magasin sont projetés dans la
mémoire (clos/dépubliés → `BESOIN_CLOS` ; brouillons et anonymes jamais).

**Défauts trouvés.**
- Source de vérité (encore) : les relances ne lisaient que les besoins de la mémoire, pas ceux de la Bourse.
- DEUX HORLOGES : le magasin horodatait en temps réel, la mémoire en temps simulé → un besoin publié après une rencontre
  paraissait antérieur ; la relance « nouveau besoin » ne se déclenchait jamais. Reproduit par un test rouge. Correction
  de fond : horloge injectable dans le magasin, l'application y branche l'horloge du réseau (une seule source de temps).

**Tests.** +2 (réciprocité ouverte proposée au bon membre et pas à l'autre ; simulation sans écriture ; besoin publié
après la rencontre → relance, puis clos → plus de relance, brouillon → jamais). 104 → 106 ; lint, 20/20, évaluations OK.

**Prochain problème.** Démonstration de scène déterministe et rejouable (monde isolé, horloge fixe), puis dossier compétition.

## BOUCLE 3 — scène de démonstration déterministe (`/demo/stage`)

**Hypothèse.** Une démo en direct doit être rejouable à l'identique, résister au rafraîchissement, au double clic et au
retour arrière, et ne rien montrer que le moteur ne calcule pas.

**Choix.** Option A (piloter la démo principale : état partagé, fragile) · B (second serveur : duplication) ·
**C retenue** : un monde isolé en mémoire (`app/stage.py`) avec son jeu de données fictif lisible
(`data/stage_reseau.json`, 16 membres, 3 grappes, 1 pont faible, 1 dormant, 1 refus, 1 profil ancien), une horloge
fixe, et les MÊMES fonctions du moteur. État côté serveur ; « précédent » = rejouer jusqu'à n−1.

**Ajouts produit.** Concept « Développement commercial en Allemagne » (vocabulaire fermé ; évaluations réservées
relancées : aucune régression) ; verbes de production reconnus comme offres même avec un lieu ; micro-cercle
(`adaptateurs/club/cercles.py`, glouton déterministe et explicable, proposition à accepter par chaque membre).

**Défauts trouvés en attaquant la scène.** L'adhésion affichait une proposition différente de ce qui était enregistré
(→ proposition puis validation visibles) ; la simulation appelait « pont » le premier lien d'un membre isolé (→ pont =
relie deux groupes existants) ; le micro-cercle incluait un profil vieux de 2 ans sans le dire (→ inconnues par membre) ;
« liens actifs » dépend d'une hypothèse de décroissance (→ retiré de la scène) ; « Pas 160 noms » dans un réseau de 16
(→ reformulé) ; disposition du graphe écrasée et étiquettes coupées (→ Kamada-Kawai, isolés à part, étiquettes intérieures).

**Tests.** `test_scene.py` (5) : rejeu identique 3 fois, récit produit par le moteur, précédent = séquentiel, fin,
réinitialisation, isolation, aucun champ privé. Navigateur (1440 px et 390 px) : 12 étapes, aucun débordement,
rafraîchissement conservé, double clic = une étape, clavier, aucune erreur JS. 106 → 111 tests.

## BOUCLE 4 — flux B : preuves, vidéo réelle, pitch, dossier de compétition

**Hypothèse.** Un jury doit pouvoir vérifier chaque phrase ; et une phrase du pitch ne doit jamais devenir fausse
après un refactor.

**Changements.** `competition/` (20 documents numérotés + FAILURES, ARCHITECTURE_DECISIONS, RESEARCH_LOG, pitchs 90 s /
3 min / 5 min, jury simulé, répétition, vidéo). Registre des preuves EXÉCUTABLE (`claims.json` →
`validate_competition_claims.py`, en CI) : contrôles réels, chiffres du pitch confrontés aux chiffres prouvés, routes
de la démo, durée de la vidéo. Vidéo réelle (144 s, WebM, Playwright) enregistrée depuis la scène, sous-titres depuis
une source unique ; documents vidéo et minutage générés.

**Défauts trouvés.** Le validateur produisait des faux positifs (minutages, références de fichiers, numérotation) :
exclus précisément ; **test de mutation du validateur** : une fausse métrique (« 73 % ») ajoutée au pitch est rejetée.
Mesure « temps avant la démo » fausse (133 s) → repère de régie. Code brut `PROPOSER_A_L_HUMAIN` affiché à l'écran →
texte humain, vidéo réenregistrée. Pitch : phrase invérifiable et injuste envers le Club remplacée.
Concurrence vérifiée par recherche web : mise en relation IA et communauté 365 jours existent déjà → retirées de notre
différenciation.

**Mesures.** 111 tests ; 20/20 ; claims vérifiées ; pitch 3 min ≈ 171 s estimé, démo dès ≈ 22 s, jargon 1,3 %.
