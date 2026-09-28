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
