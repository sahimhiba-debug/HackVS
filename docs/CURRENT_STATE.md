# État actuel du dépôt (audit factuel, 28.09.2026)

Constats vérifiés sur le code au commit `3ffd880` (37 commits sur la branche). Aucune intention n'est décrite ici :
seulement ce qui existe, ce qui marche, ce qui manque.

## 1. Arborescence et volume
- `prototype/app/` : 16 modules Python, ≈ 4 200 lignes (avec `experiences/`). Application FastAPI unique (monolithe modulaire).
- `prototype/web/` : 8 pages HTML + 10 modules JS sans étape de construction.
- `prototype/data/` : taxonomie (36 concepts, faux amis, zones, langues), 37 profils fictifs, 150 profils synthétiques, jeux de calibration.
- `prototype/eval/` : 6 jeux moteur (base, adversarial, réservés 1-4), suggestions (dev, réservé, italien), faux amis, archives des premières exécutions, référence de CI.
- `prototype/experiences/` : expérience isolée « intentions scellées » (PSI ristretto255, relais, jetons k-anonymes).
- `prototype/tests/` : 59 tests (≈ 29 s), dont MCP de bout en bout (stdio et HTTP réels).
- Infrastructure : `Dockerfile` (une image), `.github/workflows/ci.yml` (lint, tests, non-régression des évaluations). **Pas** de Kubernetes, pas de Compose, pas de bus d'événements, pas d'observabilité.

## 2. Architecture actuelle
Monolithe FastAPI (`app/main.py`, ≈ 700 lignes, 38 routes) qui orchestre des modules :

| Module | Rôle | Déterministe ? | Testé |
|---|---|---|---|
| `parser_rules.py` | texte → critères (négations, préférences, lieux, faux amis composés) | oui | oui |
| `semantique.py`, `analyse.py` | IA locale e5 (ONNX) : suggère 1-3 compétences si les règles échouent | non (modèle), décision humaine | oui (+ benchmarks) |
| `parser_llm.py` | Claude ou Apertus (compatible OpenAI), JSON contraint, 1 réessai, repli | non | oui (serveurs simulés seulement) |
| `matching.py` | filtres durs, preuves citées mot pour mot, abstention, `expliquer()` | oui | oui |
| `store.py` | SQLite : besoins versionnés, relations (machine d'états + rôles), consentements, journal | oui | oui |
| `soiree.py` | plan de soirée : programme linéaire en nombres entiers (HiGHS via SciPy), glouton, aléatoire, absences expliquées, .ics | oui | oui |
| `club.py` | agrégats du Club (à recruter, offres dormantes) | oui | oui |
| `agenda.py` | créneaux communs privés | oui | oui |
| `securite.py` | signaux d'instructions dans les profils (données non fiables) | oui | oui |
| `mcp_serveur.py` | serveur MCP : client mince de l'API, jetons/portées, confirmation humaine (elicitation) | oui | oui |
| `experiences/` | intentions scellées (PSI) | oui | oui |

## 3. Modèle de domaine actuel
`Profil`, `Offre`, `Besoin`, `Critere`, `Exclusion`, `Ambiguite`, `Preuve` (champ + extrait + nature `declare|deduit|textuel`),
`Suggestion`, `Resultat`, `Explication`, `BesoinEnregistre`, `Relation`. La **provenance** existe au niveau d'une preuve
(extrait vérifié dans le profil) mais **pas** comme registre d'affirmations : il n'y a ni statut
(VÉRIFIÉ / DÉCLARÉ / INFÉRÉ / SYNTHÉTIQUE…), ni date d'observation, ni validité, ni source structurée.

## 4. Flux IA actuels
Besoin → règles → (si rien) IA locale propose, membre confirme → (option) LLM → validation par vocabulaire fermé →
filtres durs → preuves → abstention. Le LLM ne voit jamais les profils (test structurel).

## 5. Optimiseur
`soiree.optimal()` : MILP, objectif figé (valeur des aides + 0,5 × participants servis), contraintes figées
(1 rencontre/personne/tour, paire unique, langue commune, pas de paire déjà en relation). Optimum prouvé en < 0,1 s pour
122 participants. **Manques** : objectifs et contraintes non paramétrables, pas de frontière de Pareto, pas d'analyse de
sensibilité, pas de contre-factuel formel, pas de validateur indépendant du solveur.

## 6. Graphe
Il n'existe **pas** de graphe explicite : les relations « peut aider » sont recalculées à la demande (`soiree.valeurs`,
`matching.rechercher`). Pas de centralité, pas de ponts, pas de composantes, pas d'historique temporel.

## 7. Évaluation et tests
Forte : jeux réservés écrits avant le code, première exécution archivée, non-régression en CI, benchmarks des
suggestions, faux amis, italien, réidentification. **Manque** : évaluation des décisions composites (constat → plan →
validation), rejouabilité d'une exécution, benchmark des fournisseurs de modèles en réel (aucune clé).

## 8. Composants solides à conserver
Moteur de preuves et d'abstention ; machine d'états des relations ; MILP de soirée ; IA locale calibrée ; MCP avec
confirmation humaine ; suite de tests et CI ; séparation démo / réel (mode réel refuse au lieu de simuler).

## 9. Duplication et dette technique
- `main.py` concentre routes, identité démo, vues et règles de visibilité (≈ 700 lignes).
- La logique « qui peut aider qui » est dispersée : `matching.rechercher`, `soiree.valeurs`, Bourse (`main.bourse`), `club.tableau`.
- Fournisseurs LLM codés dans `parser_llm.py` (pas de passerelle de modèles, pas de registre de capacités, pas de trace de repli structurée).
- Aucun enregistrement d'exécution : on ne peut pas rejouer ni auditer une décision passée.
- Données de profils en JSON + surcharges SQLite (acceptable pour une démo, pas pour un mode réel).

## 10. Risques de sécurité connus
- Démo : l'identité est un en-tête `X-Membre` (le mode réel refuse ; aucune authentification de l'API).
- Intentions scellées (expérience) — failles identifiées par auto-attaque, **non corrigées** :
  1. seul l'agent initiateur apprend le résultat : un faux acheteur peut sonder sans que la victime le sache ;
  2. analyse de trafic : les messages de consentement ne circulent qu'entre paires compatibles ;
  3. collusion relais + membre : pseudonyme ↔ connexion authentifiée ⇒ identité ;
  4. la révélation « simultanée » par engagement n'empêche pas l'abandon après ouverture de l'autre (équité impossible à deux sans tiers).
- Détection des consignes dans les profils : heuristique (défense principale : structurelle).

## 11. Capacités manquantes (au regard de la cible « plateforme de décision »)
Registre d'affirmations avec statuts ; spécification de décision typée ; compilateur de décision ; enregistrement et
rejeu d'exécutions ; certificat de décision ; échelle de validation explicite ; critique et gardien ; passerelle de
modèles avec capacités vérifiées ; graphe explicite ; Pareto, sensibilité, contre-factuels, tests de stress ;
adaptateur de challenge séparé du cœur générique.

## 12. Mise à jour : tranche verticale livrée (après l'audit ci-dessus)

| Capacité de la cible | État | Où |
|---|---|---|
| Registre d'affirmations, 9 statuts, transitions contrôlées | fait, testé | `plateforme/affirmations.py` |
| Compilateur d'intention → spécification (agir / s'abstenir / escalader) | fait (grammaire FR, sans LLM) | `plateforme/compilateur.py`, `adaptateurs/club/` |
| Optimisation MILP, frontière de Pareto (points supportés), sensibilité | fait ; Pareto presque dégénéré sur nos données | `plateforme/optimisation.py` |
| Échelle de validation L0-L8, validateurs indépendants du solveur | fait (L1 = Pydantic ; L4 = gardien ; L7 = critique) | `plateforme/validation.py` |
| Critique / gardien / médiateur | fait, déterministes | `plateforme/critique.py` |
| Exécution persistée, instantané, rejeu identique, branches, stress + réparation | fait | `plateforme/execution.py`, `pipeline.py` |
| Certificat dérivé des enregistrements | fait | `plateforme/certificat.py` |
| Passerelle de modèles (annoncé / configuré / vérifié, repli tracé) | fait ; **aucun fournisseur vérifié** (pas de clé ici) | `plateforme/modeles.py`, `/api/modeles` |
| Espace de décision | fait (mode démo) | `/decision` |
| Mémoire du réseau (journal d'événements, horloge explicite, graphe dérivé, décroissance, croissance) | fait | `plateforme/memoire.py` |
| Cycle des relations (relance documentée ou abstention, suivi, opportunité, soirée suivante) | fait (mode démo, horloge simulée) | `adaptateurs/club/cycle.py`, `/cycle` |
| Évaluation de la plateforme | 20/20 scénarios, en CI | `eval/eval_decisions.py` |
| Plan d'action : décision humaine enregistrée (non réécrivable) → aperçu à blanc → exécution SIMULÉE → vérification → dossier de preuves | fait ; aucun canal d'envoi réel (refusé explicitement en mode réel) | `plateforme/action.py` |
| Pare-feu de contexte / d'outils | **pas fait** (aucun LLM dans la boucle de décision : rien à filtrer pour l'instant) | — |
| Failles des intentions scellées (§10) | **non corrigées** | — |

Exigences non tenues à dessein : pas de bus d'événements, pas de Kubernetes, pas de base de graphe (une seule
instance, < 200 nœuds : NetworkX en mémoire suffit ; voir TARGET_ARCHITECTURE).

## 13. Nouvelle cible « Club Network OS » — audit et premier pas (mise à jour)

Audit du code réel (pas de la description) :
- déjà présent : besoin → candidats prouvés, filtres durs, abstention ; introduction en DOUBLE ACCORD (le magasin :
  proposée → acceptée [coordonnées partagées] → rencontre → clôture avec résultat) ; moteur de décision complet ;
  mémoire temporelle et relances documentées ;
- défaut d'abstraction trouvé : DEUX sources de vérité pour les relations (magasin des introductions ≠ mémoire des
  soirées) ; une introduction rencontrée n'entrait jamais dans le cycle de suivi ;
- manques : classement par pertinence seule, pas d'état de relation explicite, pas de chemin chaud, pas de boîte réseau.

Premier pas livré (`adaptateurs/club/reseau.py`) :
- une seule ligne de temps : le magasin (propriétaire du workflow et des permissions) est PROJETÉ dans la mémoire,
  de façon idempotente ; la réinitialisation vide les deux (plus de faits orphelins) ;
- état de relation dérivé des faits : AUCUNE → RECOMMANDEE → INTRO_DEMANDEE → INTRO_ACCEPTEE → RENCONTREE →
  SUIVI_EN_ATTENTE (≥ 10 jours) → SUIVI → OPPORTUNITE → RESULTAT_UTILE ; terminaux DECLINEE, SANS_SUITE ;
  A_RAVIVER (> 90 jours, hypothèse de produit) ; PAS_MAINTENANT ;
- chaque candidat : pertinence, réciprocité, réseau (direct / via un contact / pont entre groupes / premier lien),
  contexte, POURQUOI MAINTENANT, CONNU / DÉDUIT / INCONNU ; jamais de coordonnée, jamais de score de personne ;
- boîte réseau (onglet Suivi) : seulement des actions possibles maintenant.

Défauts trouvés par l'attaque et corrigés : l'intermédiaire d'un chemin chaud était NOMMÉ (le lien intermédiaire–candidat
lui appartient) → la proposition de présentation va d'abord à l'intermédiaire ; `retrodater` ne décalait pas
l'historique (historique fictif incohérent) ; horloges du cycle et du réseau d'origines différentes (+10 jours valait 15).
