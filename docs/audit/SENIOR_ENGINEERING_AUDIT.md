# Audit d'ingénierie senior — Club Pulse (Phase A : cartographie, lecture seule)

> 2026-09-30, commit `43fd20d`. Aucune modification de code avant ce rapport. Chaque constat renvoie à une commande,
> un fichier ou une mesure reproductible. Les constats numérotés `Fxx` sont détaillés et suivis dans
> [SENIOR_ENGINEERING_FINDINGS.md](SENIOR_ENGINEERING_FINDINGS.md). Chemins relatifs à `prototype/`.
> **F** = fait vérifié · **H** = jugement.

## 0. Vue d'ensemble

| Mesure (F) | Valeur |
|---|---|
| Code Python (hors tests) | `intelligence` 6 378 l. · `app` 5 807 · `plateforme` 1 471 · `adaptateurs` 2 186 · `eval` 2 826 · `scripts` 2 163 |
| Modules | 85 ; **41** atteints par Club Pulse (routes `/api/pulse`), **39** seulement via `app.main` (ancien prototype, plateforme de décision, adaptateur réseau), **5** atteints de nulle part (`app.mcp_serveur`, 3 scripts `experiences/mesure_*`, `adaptateurs/__init__`) |
| Routes Club Pulse | **71** ; 2 sans session (`/acces`, `/jure`, limitées) ; 23 console ; 46 membre |
| Tests | 81 fichiers, 580 fonctions ; 12 E2E Chromium (hermétiques, + mode salle en CI) |
| Journal | SQLite append-only (`plateforme/memoire.py`), id = empreinte du contenu, 31 types d'événements écrits par `intelligence/` (chaînes libres, sans catalogue central) |

## 1. Architecture

### 1.1 Couches et dépendances (F : graphe d'imports calculé sur l'AST)

```
plateforme/            journal (Memoire, Evt), affirmations (Statut), optimisation   ← n'importe rien du projet (testé)
app/{models,taxonomy,matching,parser_*}   « bibliothèques de domaine historiques », sans HTTP (testé)
intelligence/          domaine Club Pulse : essai (Banc), capacites (Registre), club_pulse (façade), ia, roles_ia, jure…
app/{main,pulse_api,capacites_api,essai_api,protections,…}   adaptateurs HTTP — les seuls à connaître FastAPI (testé)
web/pulse/*.html       PWA sans framework ; aucune règle métier (présentation seulement)
```
- La direction des dépendances est **vérifiée par un test** (`tests/test_architecture.py`) : le domaine n'importe ni
  FastAPI ni les routes ; une seule frontière réseau (`ia.py`) ; un seul endroit choisit le fournisseur IA.
- **Dette de nommage (H)** : le paquet `app` contient à la fois des adaptateurs HTTP et des bibliothèques de domaine
  (`models`, `taxonomy`, `matching`, `parser_rules`) importées 30 fois par `intelligence`. C'est **documenté et gardé
  par test**, donc sans risque ; un lecteur externe y verra pourtant un cycle `app ↔ intelligence` au niveau des paquets.
- **Cycles de modules** : 4 détectés. 3 sont `TYPE_CHECKING` seulement (`club_pulse ↔ vues_*`, SAFE). 1 réel,
  `adaptateurs.club.cycle ↔ reseau`, contourné par 4 imports locaux (ancien produit, **F15**).
- **État global** : un monde par processus (`creer_routeur` → `etat["demo"]`), un verrou réentrant par monde (chaque
  requête s'exécute entière dessous) ; limiteurs de fréquence en mémoire du processus. Assumé pour un processus de
  démonstration ; partagé entre fichiers de tests (voir § 7).
- **Horloge** : un paramètre partout dans le domaine Club Pulse (`aujourd_hui`, journalisée `HORLOGE`) ; aucune
  `date.today()` dans `intelligence/` (F : recherche). Exception héritée : `plateforme/pipeline.py:107` (**F18**).
- **Surface héritée co-résidente (F11)** : 39 modules chargés par `app.main` seulement (ancien prototype « Le Fil du
  Club », plateforme de décision, adaptateur réseau), servis uniquement derrière `HACKVS_ANCIEN_PROTOTYPE=1` (périmètre
  testé). Ils portent aussi les benchmarks publiés (`reproduire_sprint`, vérifiés à l'octet en CI) : les supprimer
  casserait des preuves ; les garder exige une frontière documentée.
- **Tout Club Pulse n'existe qu'en `HACKVS_MODE=demo`** (`app/main.py:922`) — cohérent avec un prototype sur monde
  fictif, à dire tel quel (**F20**).

### 1.2 Objets centraux (F : mesures AST)

| Classe | Taille | Rôle | Jugement |
|---|---|---|---|
| `essai.Banc` | 1 033 l., 80 méthodes (61 publiques) | journal, offres, hypothèses, lecture d'essai, transitions, alternatives, recherche de créneaux (compositeur), commandes porteur / participants, consentement de finalité, horloge | **God object** (**F06**) : 12 responsabilités ; cohérent (un seul compositeur) mais coûteux à relire |
| `club_pulse.ClubPulse` | 721 l., 69 méthodes | façade du monde : identités, sessions, IA, profils, besoins, capacités, QR juré, démo | façade large mais mince (délègue) ; H : acceptable |
| `capacites.Registre` | 300 l., 23 méthodes | registre des capacités | taille saine |
| `ia.Intelligence` | 432 l., 20 méthodes | fournisseur, validation, repli, rejeu, tâches historiques | OK ; les rôles du registre sont sortis dans `roles_ia.py` |

## 2. Domaine — objets métier et sources de vérité

| Objet | Défini | Créé par | Modifié | Source de vérité | Persistant / dérivé | Invariant explicite |
|---|---|---|---|---|---|---|
| **Claim** (offre / compétence déclarée) | `capacites.Claim`, `index_claims` | projection de `PROFIL` + `OFFRE` | jamais (bi-temporel : nouvelle version) | journal | **dérivé** | fenêtre `du/au`, provenance `Statut` |
| **Offre volontaire** | `essai.OffreVolontaire` | `Banc.publier_offre` (membre) | `modifier_offre` (auteur seul), `retirer_offre` | journal `OFFRE`, `OFFRE_RETIREE` | persistant (événements) | auteur seul modifie / retire (`Interdit`) |
| **Consent de finalité** | `ACCORD{finalite}` / `RETRAIT{finalite}` | `Banc.consentir_finalite` (membre, sa propre offre) | jamais ; retrait = nouvel événement | journal | persistant | pièce retirée ⇒ refus définitif (`Conflit`) ; validité recalculée (`raison_consentement`, 6 motifs) |
| **Agreement** (accord d'essai) | `ACCORD{essai}` / `RETRAIT{essai}` | `Banc.decider` (participant) | jamais ; nouvelle version ⇒ reconfirmation | journal | persistant | portée exacte (empreinte) de la version |
| **Capability** (`Instance`) | `capacites.Instance` | `Registre.instance` (calcul) | jamais | journal + profils + horloge + patrons | **dérivé** (cache par clé) | statut ∈ {ONE_AWAY, PROPOSED, CONSENTED, ACTIVE, DEGRADED, EXTINCT, None} |
| **Patron** (capacité attendue) | `capacites.Patron`, `data/patrons/*.json` | humains (fichiers) | nouvelle version | fichiers versionnés | configuration | validé (Pydantic, concepts connus) |
| **Gap / Ask** | `capacites.Ask` | `Registre._composer` (distance 1) | jamais | dérivé | dérivé | une pièce, une catégorie, jamais une personne |
| **Essai** (action collective) | `essai.Protocole` + `ESSAI_*` | porteur | versions, transitions gardées | journal | persistant | `TRANSITIONS` + `_transition` (refus sinon) |
| **Outcome** | `OBSERVATION`, états `OBSERVEE` / `RESULTAT_INCONNU` | participants | jamais | journal | persistant | séparé d'ACTIVE et d'EN_COURS (voir § 3) |
| **AICall** | `ia.AppelIA` → `APPEL_IA` | `Intelligence._executer` | jamais | journal (`Statut.OBSERVE`) | persistant | `issue` ∈ {MODEL_CALLED, CACHE_REPLAY, FALLBACK_FORM} |
| **Provenance** | `plateforme.affirmations.Statut` | `Banc._ecrire` (origine du bloc) | jamais | chaque événement | persistant | SYNTHETIQUE / DECLARE / JOUE / OBSERVE / SIMULE (horloge seule) |
| **Passe juré** | `jure.PassesJure` | console | consommé une fois | mémoire du processus (voulu) + `PASSE_JURE` | éphémère + trace | nonce unique, expiration, HMAC |
| **Identité** | `identite.Coffre` | import des adhésions | effacement | coffre (hors journal, par conception) | persistant hors journal | jamais vers un modèle (`proteger`, canari) ; jamais dans le journal (`_net`) |

**Constat (F05)** : `ACCORD` et `RETRAIT` portent **deux sens** (accord d'essai / consentement de finalité), distingués
par la présence de la clé `finalite` ou `essai`. Tous les lecteurs actuels filtrent correctement (F : les 24 sites
lus) ; un lecteur futur qui oublierait le filtre mélangerait deux consentements. Les charges d'événements sont des
`dict[str, Any]` non typés : le schéma de chaque type n'existe que dans le code qui l'écrit et le lit.

## 3. Machines à états

**Essai / Agreement** — explicite : `essai.TRANSITIONS`, toute transition passe par `_transition` qui refuse le reste.
```
""→BROUILLON→PROPOSE⇄AUTORISE→EN_COURS→CONTRIBUTION_RECUE→OBSERVEE
        ↘ A_ADAPTER ↔ PROPOSE/AUTORISE ; IMPOSSIBLE → A_ADAPTER (rouvert par un fait nouveau, jamais un lancement direct)
EN_COURS/CONTRIBUTION_RECUE → RESULTAT_INCONNU (14 j sans observation) → OBSERVEE (observation tardive, datée)
finaux : ANNULE, EXPIRE, OBSERVEE
```
ACTIVE (capacité) ≠ EN_COURS (essai) ≠ Outcome (OBSERVEE / RESULTAT_INCONNU) : trois objets distincts (F).

**Capability** — implicite et **dérivée** (fonction pure de l'état) : pas de transitions stockées, donc pas de
transition « silencieuse » possible ; le Pulse (`pulse_diff`) reconstruit les passages entre deux positions du journal.
`statut=None` (non composable) n'est affiché que si la recherche a été bornée (correctif Phase 3).

**Consent de finalité** — `∅ → ACCORD(v1) → RETRAIT(v1)` terminal pour cette pièce ; re-consentement = nouvelle pièce
+ nouvel `ACCORD(v2)` ; validité **recalculée** à chaque lecture (retrait, expiration, portée changée, offre retirée /
expirée, conditions changées, membre qui ne peut plus). Testé : `test_reconsentement.py`, `test_adaptation_profil.py`.

**AICall** — un enregistrement immuable par appel ; `CACHE_REPLAY` seulement depuis un `MODEL_CALLED` de même clé,
jamais IA éteinte ; aucun appel pendant un rejeu (`ClubPulse.au` construit une IA sans fournisseur, testé).

**Passe juré** — `émis → consommé` (409 ensuite) | `expiré` (401) ; session qui meurt avec le passe ; `PASSE_JURE`
journalisé à l'activation. Transitions non persistées au-delà du processus (voulu : redémarrage = passes invalides).

**Outcome** — `OBSERVATION` qualifiée (positif / négatif / mitigé / non concluant), jamais inférée ; sans observation :
`RESULTAT_INCONNU`, affiché tel quel.

## 4. Journal et rejeu

- **Propriété vérifiée ici (F)** : journal fichier, parcours réponse → récit IA → retrait → passe juré → relance →
  acquittement → +1 jour, puis redémarrage (`Demo(reprendre=True)`) : 27 événements des deux côtés, **même empreinte
  d'état complet, même projection** (statuts, distances, relances, acquittements), **0 appel IA au rejeu**.
- Tests existants : redémarrage (`test_etat_journalise.py`), rejeu à une position (`test_pulse.py`), aucun modèle ni
  écriture pendant le rejeu. **Trou (F07)** : aucun test ne couvre les types récents (`RECHERCHE_*`, `PASSE_JURE`,
  `APPEL_IA` avec clé de rejeu) au redémarrage — la propriété tient (ci-dessus) mais n'est pas gardée.
- **Hors journal, par conception** : coffre d'identités, sessions, notes privées, passes juré en attente,
  interrupteur IA, réglages (`Reglages` : budgets, plafonds), fichiers de patrons. L'égalité de rejeu suppose donc la
  même configuration (**F17** : à écrire dans le contrat « même version du moteur »).
- Identifiants : offres `of-` + empreinte (auteur, texte, position dans le journal) — déterministes ; aucun `uuid4`
  ni horodatage réel dans le domaine Club Pulse (`plateforme/execution.py` en a, ancien produit).
- Clé de rejeu IA : HMAC du secret du processus — le rejeu d'un appel IA **après redémarrage** exige `HACKVS_SECRET`
  (documenté en Phase 3).

## 5. Moteurs — unicité

| Moteur | Implémentation | Doublon ? (F) |
|---|---|---|
| Composition d'équipe / créneaux | `Banc._composer` (+ `solutions`, `candidats`) | **un seul** : registre et essais l'appellent (P1.3) |
| Capacités, levier, pièces critiques, what-if | `Registre` → `Banc.solutions` ; `status_if` = superposition `Banc.hypothese` | un seul ; oracle force brute en test |
| Adaptation d'essai | `Banc.alternatives` / `_reevaluer` | un seul |
| Consentement de finalité | `Banc.consentir_finalite` / `raison_consentement` | un seul |
| Accord d'essai | `Banc.decider` / `_accord_donne` | un seul (même type d'événement que le consentement : F05) |
| Matching historique | `app/matching.py`, `adaptateurs.club.*` | **ancien produit** (détection d'opportunités, F08/F11) — pas un second moteur de capacités |

## 6. Frontière IA et vie privée

- **Registre des capacités** : EXTRACT / NORMALIZE / NARRATE ne produisent que des **propositions** ; validation par le
  code ; rejet → 1 nouvel essai → forme déterministe ; le modèle n'écrit que la trace `APPEL_IA` (testé :
  `test_canaris_prompts.py`, `test_roles_ia.py`) ; parité ON/OFF non vacueuse (`test_parite_ia.py`).
- **Préparer un essai / une action** : sortie du modèle = brouillon retourné, **rien n'est écrit** (F : `essai_api.py:191,212`).
- **Écart (F01, HIGH)** : `POST /api/pulse/moi/demandes` → `ClubPulse.demander` écrit un `BESOIN` **interprété par le
  modèle** (validé : vocabulaire fermé, extraits mot pour mot) **sans confirmation du membre**, puis lance la détection
  d'opportunités. L'état dépend donc du modèle sur ce chemin, que la parité ne couvre pas. La route n'est appelée par
  **aucun écran** (branche « détection » retirée du parcours visible) mais reste ouverte à toute session membre.
- Canari d'identité : corpus des prompts réellement envoyés, 150 membres, deux défenses indépendantes (contre-épreuve
  faite en Phase 3). Journaux applicatifs : métadonnées seulement (ni entrée, ni prompt, ni sortie).

## 7. Tests

- **Flaky réel (F04)** : `test_essai_securite.py:252` forge une session en remplaçant les 2 derniers caractères de la
  signature par `00` ; si la vraie signature finit par `00` (1/256, secret aléatoire par processus) le « faux » est le
  vrai → 200 au lieu de 401. C'est l'échec isolé observé en fin de Phase 3.
- **Sonde de disponibilité E2E cassée (F03)** : `tests/test_e2e_scene.py:serveur` interroge `/api/stage` (404 depuis le
  périmètre de la Phase 1) ; `HTTPError` est un `OSError` → la boucle attend ses **80 × 0,25 s = 20 s** puis continue
  sans jamais avoir vu le serveur prêt (F : mesuré 20,2 s ; `/etabli` répond en 0,1 s). Un serveur qui ne démarre pas
  serait découvert plus tard, par un échec trompeur ; chaque `serveur()` coûte 20 s.
- **Tests potentiellement vacueux (F10)** : 3 tests de `test_frontiere_textes.py` vérifient l'**absence** de noms
  sans vérifier que le texte utile est **présent** — ils passeraient si le texte était perdu.
- État partagé : un seul `app` et un seul monde par processus pour tous les fichiers de tests (réinitialisation par
  route) ; limiteurs partagés. Pas de dépendance d'ordre observée hormis F04.
- Assertions faibles : `assert evs` / `assert ops` servent de gardes avant des boucles (acceptable). Aucune `assert
  x is not None` isolée dans les tests Club Pulse.
- Propriétés : oracle force brute (6 000 graines), non-régression du compositeur (4 000), rejeu à 5 positions.
  **Hypothesis n'est pas installé** ; l'intérêt de l'ajouter est évalué dans les findings (F21).
- Mutation : 1 197 / 1 299 tués sur `capacites.py`, 102 survivants **tous classés** (`docs/audit/mutants_survivants.txt`) ;
  campagne GitHub #4 en cours au moment d'écrire.

## 8. Sécurité (résumé ; détail dans les findings)

- Surface Club Pulse : 71 routes ; seules `/acces` et `/jure` sans session, toutes deux limitées ; console par
  en-tête + (jeton | machine locale) ; membre par session HMAC expirante ; pas de cookie ⇒ pas de CSRF membre (testé).
- IDOR : contrôles dans le domaine (`Introuvable` pour qui n'est pas concerné, `Interdit` sinon) ; testés au cas par
  cas, **pas de balayage systématique** de toutes les routes membre à identifiant (F08).
- `/acces` est limité **par IP** (10/min) : dans une salle derrière un NAT, tout le public partage ce quota (**F09**).
- Console sans jeton = « cette machine » : correct tant que les en-têtes de proxy ne sont crus que de 127.0.0.1
  (défaut d'uvicorn) ; à documenter pour tout déploiement non local (**F19**).
- QR juré : expiration, nonce consommé, HMAC, limites par code et par session — testés (Phase 3).
- Secrets : scanner propre ; `pip-audit` en CI.

## 9. Performance (mesurée, rien d'optimisé)

| Opération (monde de démo, cache froid) | Médiane |
|---|---|
| `projection_capacites` (6 patrons) | 459 ms |
| vue console de l'Établi | 418 ms (0 ms cache chaud) |
| `asks_pour` | 416 ms |
| `pulse(0)` (deux rejeux) | 495 ms |
Profil : 918 recherches `_composer`, **1 087 appels `candidats`**, chacun reconstruit toutes les `OffreVolontaire`
depuis le journal (`Banc.offres`). Coût quadratique, sans effet à l'échelle de la démo (cache par écriture) (**F13**).

## 10. Documentation

- **`docs/ARCHITECTURE.md` décrit le produit d'avant le pivot** (boucle OBSERVER → DÉTECTER → ACTIVER → APPRENDRE,
  `activation.py`) et ne mentionne ni le registre des capacités, ni l'Établi, ni les rôles IA, ni le QR juré ;
  **ADR 0004** cite `intelligence/activation.py`, **qui n'existe plus** (**F02**, HIGH : le jury passe du pitch au code).
- `docs/` compte ~20 documents de périodes différentes (instantanés du 28.09, recherche, vision « Valais Ecosystem OS »,
  journal des boucles) sans marquage « historique » (**F16**).
- Audits de phase (`docs/audit/PHASE_*.md`) : à jour et reliés aux commits.

## 11. Scorecards (qualitatives, sans note globale)

| Domaine | Solide (F) | Faible (F/H) |
|---|---|---|
| **Architecture** | direction des dépendances testée ; un seul compositeur ; façade + vues séparées | `Banc` God object (F06) ; paquet `app` à double rôle ; 39 modules hérités co-résidents (F11) |
| **Domaine** | objets métier nets ; dérivé vs persistant clair ; ACTIVE / EN_COURS / Outcome séparés | `ACCORD`/`RETRAIT` à deux sens ; charges d'événements non typées (F05) |
| **Sécurité** | périmètre ; sessions HMAC ; QR juré ; pas de CSRF ; secrets propres | `/acces` par IP (F09) ; routes membre sans écran encore ouvertes (F08) ; pas de balayage IDOR |
| **Frontière IA** | propositions seulement dans le registre ; canari à deux défenses ; parité non vacueuse ; statuts véridiques | `/moi/demandes` écrit une interprétation du modèle sans confirmation (F01) |
| **Rejeu** | redémarrage et rejeu à position testés ; déterminisme vérifié ici avec les types récents | types récents non gardés par test (F07) ; config hors journal à contractualiser (F17) |
| **Tests** | oracle, mutation classée, E2E hermétiques + mode salle, contre-épreuves systématiques | 1 test flaky (F04) ; sonde E2E cassée (F03) ; 3 tests potentiellement vacueux (F10) |
| **Performance** | mesurée ; cache par écriture ; budget de nœuds | coût quadratique de `candidats` (F13), sans effet à l'échelle démo |
| **Documentation** | audits de phase précis ; décisions tracées dans les commits | architecture et ADR 0004 périmés (F02) ; `docs/` sans statut historique (F16) |

## 12. Priorités (vagues)

1. **Vague 1 — tests, sans risque produit** : F04 (flaky), F03 (sonde E2E), F07 (rejeu des types récents), F10
   (tests vacueux), F08-a (balayage IDOR de toutes les routes membre), F05-a (test de séparation des deux sens
   d'`ACCORD`/`RETRAIT`).
2. **Vague 2 — décisions (documentées avant d'agir)** : F01 (route `/moi/demandes`), F08 (routes sans écran :
   DELETE / KEEP / DEPRECATE), F09 (`/acces` par IP).
3. **Vague 3 — documentation** : `docs/architecture/ARCHITECTURE.md` du système réel, ADR nécessaires, marquage
   historique des anciens documents (F02, F11, F16, F17, F20).
4. **Reporté après la démo, documenté** : découpage de `Banc` (F06), coût de `candidats` (F13), typage des charges
   d'événements (F05-b), `type: ignore` (F14).
