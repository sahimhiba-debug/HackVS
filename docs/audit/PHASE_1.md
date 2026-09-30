# Phase 1 — Capability core : compte rendu de sortie

> Branche `claude/modest-bohr-xvk53n`, à partir de `160d245` (rapport d'inspection validé). Chemins relatifs à
> `prototype/`. **F** = fait vérifié par une commande ou un test · **H** = jugement.
> Critère de sortie fixé : *le scénario A tourne de bout en bout SANS IA* ; plus, selon vos amendements, *même
> journal → même empreinte de l'état complet, profils et horloge compris* et la sécurité de base (ancien prototype).

## 1. Verdict

**Critère de sortie atteint (F).** Le scénario A passe par l'API, sessions réelles, sans aucun appel au modèle :
`delegation_acheteurs` est `ONE_AWAY` (il manque le minibus) → Ask « Un minibus de 12 places ou plus ? Le 09.10
13:30–15:00… » → Pauline répond sur son téléphone (14 places) → `ACTIVE`, les trois pièces présentes et consenties.
Il a été rejoué **10 fois de suite, 10/10**, sur un monde neuf à chaque fois.
Tests : `tests/test_capacites.py::test_scenario_a_*` (le second vérifie `ia.appels == []`, l'absence d'`APPEL_IA` dans
le journal et le statut `DECLARE` de chaque fait écrit).

## 2. Commits (petits, un sujet chacun ; tests verts à chaque étape)

| Commit | Nature | Test de correction rouge sur l'ancien code (pour la bonne raison) |
|---|---|---|
| `a6282d5` security(serveur) | ancien prototype non servi par défaut ; `HACKVS_ANCIEN_PROTOTYPE=1` → seulement cette machine, ou jeton de console | `test_service_ancien.py` : 13 rouges avant (routes anciennes, identité `X-Membre` et réinitialisation répondaient 200) |
| `18829d4` fix(etat) | profils, besoins, préférences, horloge journalisés ; état = repli ; `empreinte_etat()` ; reprise du journal au démarrage | `test_etat_journalise.py` : rouges avant (horloge revenue au 06.10 ; liste d'essais vide au redémarrage) |
| `c3c4678` refactor(banc) | composition hors essai (`eid=None`), sans changement de comportement | — (suite inchangée : 547 verts) |
| `bea0bc7` feat(banc) | contraintes numériques d'emplacement ; consentement de FINALITÉ sur le mécanisme `ACCORD` existant | nouvelle fonctionnalité (`test_banc_finalite.py`) |
| `575d1a1` feat(capacites) | patrons (données), index bi-temporel, projection, distance 0/1, Ask, réponse, consentement, API, vues en rôles | nouvelle fonctionnalité (`test_capacites.py`, règle d'architecture) |
| `ff6d0ec` fix(composition) | recherche **complète** + `ACTIVE` dès qu'une composition entièrement consentie existe | `test_capacites_oracle.py` : 13 graines rouges avant (8 distance fausse, 5 ACTIVE manqué) |
| *(ce commit)* test + docs | tests tueurs de mutants, config mutmut, README, ce compte rendu | — |

## 3. Ce qui existe maintenant (F)

- **Un journal, tout l'état.** `ClubPulse.journal` (celui du banc ; fichier si `HACKVS_ESSAIS_DB`) porte `SEMIS`,
  `PROFIL` (champs déclaratifs seulement), `BESOIN`, `PREFERENCES`, `HORLOGE`, les appels IA, les textes rédigés, les
  essais, offres et consentements. `_appliquer` est le seul chemin qui modifie cet état, en direct comme au rejeu ; un
  journal d'un autre monde est refusé. **Hors journal par conception** : coffre d'identités et activation des
  comptes, sessions, notes privées. `test_meme_journal_meme_empreinte_de_l_etat_complet` : même journal → même
  empreinte, et l'empreinte change quand l'horloge avance (non vacueux).
- **Le serveur reprend son journal** (`Demo(reprendre=True)`) au lieu de l'effacer. Écart trouvé en chemin : avant,
  `HACKVS_ESSAIS_DB` ne survivait jamais à un redémarrage du serveur servi. Le scénario guidé ne peut pas reprendre au
  milieu (son contexte n'est pas journalisé) : la console le dit, et « Nouvelle démonstration » repart à zéro.
- **Registre** (`intelligence/capacites.py`) :
  - 6 patrons en données (`data/patrons/`), FICTIFS, auteur humain obligatoire (un auteur qui nomme un modèle ou
    « IA » est refusé), validés contre la taxonomie ;
  - `index_claims`, index bi-temporel : validité (`du/au`, plages) × enregistrement (`recorded_at`/`superseded_at`) ;
    une claim expirée ou remplacée n'est jamais supprimée ; requêtes « tel que le journal le savait » (`vu_au`) ;
  - `Registre.instance` compose avec **le compositeur du banc** et expose une distance de 0 ou 1 seulement ; la pièce
    manquante devient une Ask (catégorie, créneau, expiration) ;
  - `repondre` : un oui = une offre datée pour le créneau + un consentement de finalité ; l'Ask est relue au moment
    de la réponse, donc une seule liaison ; un non est journalisé et n'est jamais attribué ;
  - `consentir` : consentement d'un membre dont l'offre compose déjà la capacité.
- **Statuts** : `ONE_AWAY`, `PROPOSED`, `CONSENTED`, `ACTIVE`, `DEGRADED`, `EXTINCT`.
  - **ACTIVE ≡ AUTORISÉ** (votre décision) : toutes les pièces sont valables à t et consenties pour la finalité.
    L'exécution reste au niveau de l'essai.
  - **CONSENTED n'est pas un doublon de PROPOSED dans le code** : PROPOSED = composable, aucun consentement donné ;
    CONSENTED = au moins un consentement déjà donné. Les deux sont gardés et documentés dans le module.
- **API** (adaptateur mince, sans règle métier) : `GET /api/pulse/console/capacites`, `GET /api/pulse/moi/asks`,
  `POST /api/pulse/moi/asks/{id}/reponse`, `POST /api/pulse/moi/capacites/{id}/consentement`. Les vues sont en rôles :
  ni nom, ni texte d'offre, et un consentement perdu est désigné par son emplacement, jamais par la personne.
- **Architecture** (test) : le registre importe le banc, ni l'IA ni la détection ; l'IA n'importe pas le registre ; le
  banc ignore le registre.

## 4. Qualité : oracle, propriétés, mutation (F)

- **Oracle en force brute** (`tests/test_capacites_oracle.py`). Réimplémentation naïve et indépendante des règles :
  tous les créneaux au quart d'heure × toutes les affectations injectives. Elle tourne sur 300 graines + 12 graines
  de régression. Vérifications : distance, ACTIVE, conformité de chaque liaison, cohérence de l'Ask. Un garde
  empêche l'oracle d'être vacueux (les mondes produisent les cas distance 0, 1, au-delà, et ACTIVE).
  **6 000 graines** vérifiées hors suite : 0 désaccord après le correctif.
- **Il a trouvé deux défauts réels** :
  1. `Banc._composer` était **glouton** : une personne ayant deux offres faisait manquer une composition existante.
     Ce compositeur sert aussi les adaptations des essais, qui pouvaient donc manquer une alternative admissible.
  2. Le registre ne regardait que le **premier** créneau composable et manquait un créneau entièrement consenti.

  Correctif dans le compositeur partagé : une recherche en profondeur (4 gestes au plus) dont le premier chemin est
  exactement le choix glouton d'avant. Toute équipe trouvée auparavant reste donc la même ; seuls les échecs à tort
  deviennent des solutions. Les résultats publiés des benchmarks sont inchangés à l'octet.
- **Mutation** (mutmut 3.8.0, `setup.cfg`, limitée à `intelligence/capacites.py`) :

  | Campagne | Tués | Survivants | Score brut |
  |---|---|---|---|
  | 1 (tests de la fonctionnalité + oracle) | 496 / 682 | 182 | 72,7 % |
  | 2 (+ `test_capacites_regles.py`) | 595 / 682 | 83 | 87,2 % |
  | finale (+ 7 tests ciblés, fonction morte retirée) | **617 / 678** | 61 | **91,0 %** |

  Les 61 survivants finaux sont **tous équivalents**, classés un par un dans `docs/audit/phase1_mutants_survivants.txt` :
  - 20 : clés et `mode` de sérialisation internes à l'empreinte de portée, calculée de la même façon des deux côtés ;
  - 3 : rôle d'affichage du geste, non lu par le registre ;
  - 13 : `maximum` des recherches, dont seul le premier résultat est lu ; `garder` sous `permis` ; facteur du tri ;
  - 9 : modes de sérialisation du semis, bornes de troncature (40 et 41 caractères), `pop` jamais absent ;
  - 16 : message d'erreur enveloppé, encodage, `split` à borne, défaut d'attribut sous un minimum supérieur à 1, et
    une garde défensive dont la branche n'est pas atteignable dans les données actuelles.

  Aucun survivant à comportement réel. Les tests écrits pour tuer les mutants ont révélé des manques de test, pas de
  nouveau défaut du code : borne exacte des minimums, compétence non déclarée, portée calculée sur le mauvais
  emplacement, bornes bi-temporelles, retrait d'une offre dans l'index, préférence « le plus de consentements »,
  `DEGRADED` à distance 1, lecture des consentements après un emplacement disparu, réouverture d'une compétence.
- **Commande** : `cd prototype && python -m mutmut run && python -m mutmut results`. Durée ≈ 4 min. **Elle n'est pas
  en CI** : c'est une décision à prendre (coût : ~4 min par exécution).

## 5. Vérifications finales (2026-09-30)

| Contrôle | Résultat |
|---|---|
| `pytest` (hors E2E) | **905 passed** (523 au début de la phase) |
| E2E Chromium (scène, Club Pulse, action collective) | 6/6 ; 11 exécutions sur le code modifié pendant la phase : **1 échec isolé** (`test_e2e_pulse`, juste après `reproduire_sprint.py`, machine chargée), puis 10 exécutions vertes d’affilée. Cause **non établie** : c'est consigné tel quel, sans le qualifier de « flake ». À surveiller en CI. |
| ruff · mypy · secrets | propres · 76 fichiers sans erreur · aucun secret |
| `make eval` (non-régression, 20 scénarios, cohérence pitch ↔ code) | vert |
| `scripts/reproduire_sprint.py` puis `git status eval/` | aucun écart : résultats publiés identiques à l'octet |
| Scénario A ×10 | 10/10 |
| Projection des 6 patrons | ≈ 90 ms (machine de développement) |

## 6. Ce qui n'est PAS fait (par le plan, ou trouvé et laissé)

- **Cas 3 et 7 d'A4** (retirer une compétence du profil, se déclarer indisponible ou non sollicitable) : ces faits sont
  maintenant **journalisés et relisibles**, mais ne dégradent toujours pas un accord ou un consentement existant.
  C'est prévu en Phase 2, test rouge d'abord.
- Levier, composants critiques, plafond d'Ask, retrait d'un consentement de finalité, reçu, écran « Mes données »,
  Pulse diff : **Phase 2**.
- Deux réponses **concurrentes** à une même Ask : une seule liaison, par construction (verrou du monde + relecture
  de l'Ask). Il n'existe **pas encore de test à fils concurrents** : Phase 2, comme prévu.
- Type d'acte d'un geste (« conseiller » ≠ « amener ») : non traité.
- Trouvé en chemin, **non corrigé** (hors périmètre, à décider) : `onboarding` range dans le profil le texte libre
  **non nettoyé** du membre. Or ce profil est ce que lit le moteur, qui est censé ne voir que du texte nettoyé.
  C'était déjà le cas avant cette phase ; la journalisation n'a rien changé.
- Données de démonstration B9 (40 membres, ~180 claims) : non construites. Il n'y a que le semis minimal du scénario A.
- Écrans « Établi » et « Passeport » : non construits (B7). Il n'y a que l'API.
- Artefacts périmés (vidéo, captures, DEMO_SCRIPT § 6, PREUVES, `competition/*`) : **non régénérés**, comme demandé
  (fin de Phase 3).

## 7. Points à trancher avant la Phase 2

1. **Mutation en CI** : l'ajouter (≈ 4 min, sur `capacites.py` seulement) ou la garder en commande manuelle ?
2. **Texte d'onboarding non nettoyé** : le corriger dans un commit de sécurité séparé, en Phase 2 ?
3. **Semis de démonstration** : garder le scénario A le vendredi 09.10, pour ne jamais toucher à l'action collective
   du jeudi (choix actuel), ou tout regrouper sur un même jour pour la scène ?
