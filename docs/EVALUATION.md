# Évaluation : protocole, résultats, limites

**Tout est mesuré sur des données fictives** (37 profils de démonstration, 150 profils synthétiques), avec des cas écrits par
l'équipe de développement. Ces chiffres montrent que **les mécanismes fonctionnent comme conçus** ; ils ne prouvent pas
l'**utilité pour de vrais membres**, jamais testée. Statuts utilisés : **mesuré** (chiffre reproductible ci-dessous),
**post-hoc** (jeu déjà vu avant la mesure), **hypothèse** (non mesuré).

Reproduire (depuis `prototype/`) :
```bash
python -m eval.run_eval [--jeu X] [--semantique] [--membre-simule]   # moteur vs mots-clés
python -m eval.eval_suggestions --jeu dev|reserve --methode dense|hybride   # suggestions de l'IA locale
python -m eval.eval_faux_amis                                       # faux amis composés
python -m eval.run_eval --verifier                                  # non-régression (CI)
python -m pytest -q                                                 # 53 tests
```

## 1. Protocole : trois familles de jeux, jamais mélangées

| Famille | Jeux | Usage autorisé |
|---|---|---|
| **Développement** | `cas.json`, `cas_adversariaux.json`, `suggestions/dev.json`, `cas_faux_amis_composes.json` | Régler, corriger |
| **Calibration** | `data/calibration_paraphrases.json` (84), `data/calibration_negatifs.json` (62) | Choisir seuils et poids de l'IA locale, rien d'autre |
| **Réservés** | `cas_reserve*.json` (1 à 4), `suggestions/reserve.json` | Exécutés **une fois** ; ensuite ils deviennent des tests de régression (post-hoc) |

Chaque jeu réservé est commité **avant** l'implémentation qu'il mesure (l'historique Git en fait foi) ; la première
exécution est archivée dans `eval/archives/`.

## 2. Moteur de mise en relation (analyse par règles)

Mesures sur le top 3 (ce que le membre voit). **Référence** = mots-clés **avec les mêmes filtres durs** : la comparaison
isole le classement.

| Jeu | Statut | succès@3 moteur | réf. | violations moteur | réf. | abstention correcte moteur | réf. |
|---|---|---|---|---|---|---|---|
| Base (20) | dév. | 16/16 | 14/16 | **0/20** | 8/20 | 20/20 | 17/20 |
| Adversarial (20) | dév. | 13/13 | 12/13 | **0/20** | 5/20 | 20/20 | 16/20 |
| Réservé 1 (14) — 1re exécution | réservé | 9/12 | 11/12 | **0/14** | 4/14 | 11/14 | 13/14 |
| Réservé 2 (18) — 1re exécution | réservé, circulaire | 15/15 | 7/15 | 0/18 | 0/18 | 18/18 | 14/18 |
| Réservé 3 (20) — 1re exécution | réservé | 5/15 | 7/15 | 1/20 | 4/20 | 11/20 | 14/20 |
| Réservé 4 (20) — 1re exécution | réservé | 3/15 | 7/15 | 2/20 | 2/20 | 7/20 | 12/20 |

**Lecture honnête.** Le moteur à règles **propose rarement un mauvais contact**, mais sur des formulations libres
(réservés 3 et 4) il **se tait trop** : la référence trouve plus souvent. Les 3 violations restantes sont des faux amis
de règles documentés (« acheter un camion frigorifique neuf » → transport ; « bouteilles de cidre » → boissons ;
PC lents → cybersécurité via la catégorie parente).

## 3. La vraie boucle produit : l'IA propose, le membre confirme

Quand les règles ne reconnaissent aucune compétence, l'IA locale propose 1 à 3 compétences ; le membre clique ou
choisit « Aucune ». `--membre-simule` rejoue ce clic (même logique que l'interface). **Hypothèse de borne haute** :
le membre reconnaît la bonne compétence si elle lui est proposée ; hors catalogue, il ne choisit rien.

| Jeu (post-hoc) | Règles seules : succès@3 · violations · abstention | Règles + IA locale + membre | Mots-clés |
|---|---|---|---|
| Réservé 3 | 7/15 · 1/20 · 13/20 | **14/15 · 1/20 · 20/20** | 7/15 · 4/20 · 14/20 |
| Réservé 4 | 3/15 · 2/20 · 7/20 | **15/15 · 2/20 · 19/20** | 7/15 · 2/20 · 12/20 |
| Base, adversarial, réservés 1-2 | inchangés | inchangés (aucune régression) | — |

Indépendant de l'hypothèse : **la bonne compétence figure dans les options proposées dans 8/8 et 12/12 questions**.
Aucune violation ajoutée : l'IA ne rend personne éligible.

## 4. Suggestions de l'IA locale (multilingual-e5-large, ONNX, CPU)

Jeu dev (24 besoins FR/DE/EN + 6 hors catalogue) et jeu **réservé** rédigé en même temps, exécuté une fois.

| Méthode | Jeu | hit@1 | hit@3 | MRR | options affichées hors sujet | hors catalogue avec options |
|---|---|---|---|---|---|---|
| Dense seul (avant) | dev | 0,750 | 0,875 | 0,828 | 48/72 | 6/6 |
| **Hybride** | dev | 0,833 | 0,958 | 0,894 | 21/47 | 6/6 |
| Dense seul (avant) | **réservé** | 0,667 | 0,875 | 0,784 | 50/72 | 6/6 |
| **Hybride** | **réservé** | **0,792** | **0,917** | **0,865** | **26/48** | 6/6 |
| Dense seul | **italien** (12, aucune règle italienne) | 1,000 | 1,000 | 1,000 | 23/36 | — |
| **Hybride** | **italien** | **1,000** | **1,000** | **1,000** | **3/16** | — |

Hybride = z-score dense (max par expression + prototype) + 0,3 × lexical IDF (idée du score hybride de BGE-M3) ;
poids choisi sur la calibration. La fusion RRF (Haystack) a été **mesurée et écartée** (hit@3 0,870 contre 0,948 sur la
calibration). n = 24 : l'écart en hit@1 sur le réservé correspond à 3 cas.

**Échec assumé** : sur la calibration, les quantiles du meilleur score dense des besoins hors catalogue et des vrais
besoins se recouvrent (même après normalisation) : **aucun seuil ne permet à l'IA de s'abstenir seule**. D'où la règle :
elle suggère, le membre confirme, le moteur s'abstient. La décision automatique existe (`HACKVS_SEMANTIQUE_AUTO=1`) mais
reste désactivée : avec ~50 négatifs, la règle de trois borne le taux de fausses acceptations à ≈ 5 % seulement.

**Italien** (`suggestions/italien.json`, rédigé avant toute adaptation) : aucune règle italienne n'existe, et pourtant la
bonne compétence est proposée pour 12/12 besoins dans la chaîne complète (11 par la question de l'IA locale, 1 par les
règles). Seuls les toponymes (Zurigo, Ginevra…) et les noms de langue ont ensuite été ajoutés au vocabulaire.
Limite : jeu sans négatif (hors catalogue), 12 cas.

Latence mesurée : ≈ 77 ms en médiane (max 103 ms) par suggestion, 4 cœurs CPU.

## 5. Faux amis composés

`eval/cas_faux_amis_composes.json`, rédigé avant le mécanisme : 8 cas visés par la liste éditable, 4 volontairement
**hors liste**.

| | Avant | Après |
|---|---|---|
| Cas de la liste (« comptabilité carbone », « avocat pour un divorce »…) | 3/8 évités | **8/8** |
| Cas hors liste (« formation de yoga », « loueur de voitures »…) | 0/4 | **0/4** |

Le mécanisme ne généralise pas : c'est une liste de données, à enrichir par le Club. Angle mort connu.

## 6. Plan de soirée (programme linéaire en nombres entiers, HiGHS)

Contraintes : ≤ 1 rencontre par personne et par tour, jamais deux fois la même paire, langue commune obligatoire,
membres disponibles et consentants. Objectif : aides prouvées + 0,5 par participant ayant ≥ 1 rencontre utile.

| Données | Tours | Participants | Paires utiles (écartées faute de langue) | Participants avec ≥ 1 rencontre utile : optimum · glouton · aléatoire (30) | Optimum prouvé en |
|---|---|---|---|---|---|
| Club démo | 3 | 32 | 28 (3) | 21 · 20 · 20,7 | 12 ms |
| Synthétique | 2 | 122 | 276 (13) | **85 · 66 · 71,0** | 24 ms |
| Synthétique | 3 | 122 | 276 (13) | **92 · 74 · 79,2** | 84 ms |
| Synthétique | 4 | 122 | 276 (13) | **94 · 77 · 85,1** | 76 ms |

Sur un petit Club, l'optimisation n'apporte presque rien ; elle compte à l'échelle d'une vraie soirée. Le temps est
dominé par le calcul des valeurs de paires (≈ 1,2 s pour 122 participants), pas par le solveur.

## 6 bis. Plateforme de décision (`python -m eval.eval_decisions`)

20 scénarios dont l'attendu est fixé AVANT l'exécution (données fictives, aucun LLM) ; résultats détaillés dans
`prototype/eval/resultats_decisions.md`, rejoués en CI. **20/20 conformes** après correction d'un vrai défaut trouvé
par le scénario S09 (le solveur plantait sur un problème vide ; il s'abstient désormais).

Ce qui est vérifié : décisions (proposer / s'abstenir / escalader / bloquer) sur demandes nominales, vagues,
hors bornes, injectées ou contournant le consentement ; rejeu bit à bit identique (démo et 150 membres synthétiques) ;
branches contre-factuelles et refus par la politique ; test de stress structurel et aléatoire reproductible ; blocage
si la politique exige des preuves VÉRIFIÉES ou si les affirmations sont périmées ; paires déjà en relation exclues ;
certificat dérivé des enregistrements ; honnêteté sur données fictives.

Ce qui ne l'est PAS : la qualité des rencontres pour de vrais membres. Sur nos données, la frontière de Pareto est
presque dégénérée (1 point sur le club synthétique, 1 à 2 sur la démo) : le générateur synthétique ne produit
aucune réciprocité. La capacité existe ; on ne la présente pas comme un résultat.

## 6 ter. Cycle des relations (`/cycle`, `tests/test_cycle.py`)

Boucle : soirée approuvée → rencontres (SIMULE tant qu'un membre ne déclare pas les avoir faites) → 10 jours →
« pourquoi reprendre contact ? » **seulement** s'il existe une raison nouvelle et documentée → le membre accepte →
suivi (DECLARE) → opportunité « ami d'un ami » (INFERE) → la soirée suivante l'optimise, sans répéter aucune paire.

Scénario de démonstration (fictif, un seul besoin écrit à la main, publié 6 jours après la soirée) :

| Étape | Mesure |
|---|---|
| 10 jours après la soirée 1 | **1 relance** (Sophie ↔ Reto : besoin nouveau + offre citée mot pour mot) ; **21 abstentions** (« rien de nouveau ») |
| Suivi accepté | 1 opportunité : Grégoire peut aider Sophie, Reto les connaît tous deux |
| Soirée 2 | Sophie–Grégoire planifiés ; 0 paire répétée ; 0 validateur en échec |

Croissance sans aucun besoin nouveau (horloge simulée, 30 jours entre soirées, mêmes contraintes) :

| Club | Rencontres utiles S1 · S2 · S3 | Groupes connectés S1 → S3 | Portée à 2 poignées de main S1 → S3 |
|---|---|---|---|
| Démo (37 fictifs) | 22 · 6 · **abstention** | 3 → 3 (S2) | 4,67 → 6,1 (S2) |
| Synthétique (150) | 91 · 74 · 52 | **11 → 1** | **4,4 → 14,3** |

Lecture honnête : la croissance est mécanique (plus de soirées, plus de liens) et le vivier de rencontres UTILES
s'épuise (91 → 52 ; le Club de démo n'a plus rien à proposer à la 3e soirée, et la plateforme s'abstient plutôt que
de fabriquer des rencontres). Seuls de nouveaux besoins publiés le renouvellent — c'est ce que la relance documentée
cherche à provoquer. Non mesuré : si de vrais membres acceptent les relances et se revoient ; la décroissance des liens
(demi-vie 30 jours) est une hypothèse de modélisation, pas une mesure.

## 7. Sécurité, confidentialité, agent (tests automatisés)

| Propriété | Comment c'est vérifié |
|---|---|
| Aucune violation de consentement / visiteur | invariants de l'évaluation + tests |
| Preuves citées mot pour mot | `preuve_valide` : 100 % sur tous les jeux (vrai par construction, garde-fou si un LLM rédigeait) |
| Raison opaque si elle touche au consentement | `test_expliquer_ne_revele_pas_un_refus_d_introductions` |
| Injection indirecte via un profil | profil malveillant : alerte transmise, classement inchangé, rien sans confirmation |
| Le LLM ne voit pas les profils | test structurel sur la requête envoyée |
| MCP : authentification et portées | 401 sans jeton, portée « lecture » refusée avant toute question au membre |
| MCP : machine d'états | 403 (mauvais rôle), 409 (mauvais état), parcours complet jusqu'à la clôture |
| Aucun appel externe non documenté | télémétrie onnxruntime découverte (import → Microsoft) et coupée ; test |
| Signaux d'instruction : faux positifs | 0 sur 187 profils existants (nos données : contrôle, pas une preuve de précision) |

## 8. Ce qui n'est PAS mesuré
- Utilité pour de vrais membres ; acceptabilité des questions ; qualité des messages d'introduction.
- Claude et Apertus contre leurs API réelles (aucune clé ni accès réseau autorisé dans cet environnement ; testés avec
  des serveurs simulés : flux, sortie contrainte, refus, JSON invalide, réessai, panne).
- Reranker neuronal (poids hébergés sur Hugging Face, inaccessible ici).
- Robustesse à des centaines de profils réels hétérogènes (les synthétiques sont réguliers).
