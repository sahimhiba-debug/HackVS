# Inspection avant pivot — « registre vivant des capacités du Club »

> **Partie A seulement : aucune ligne de code n'a été modifiée.** Seul fichier créé : ce rapport.
> Établi le 2026-09-30 par lecture du code et exécution, pas à partir des README ni des rapports précédents.
> Commit inspecté : `9744027` (branche `claude/modest-bohr-xvk53n`, seule branche du dépôt, aucune PR ouverte ou fermée).
> Chemins relatifs à `prototype/` sauf mention contraire. **F** = fait vérifié (fichier, test ou commande exécutée) ·
> **H** = hypothèse ou jugement.

## 0. Résumé en dix lignes

1. Le moteur retenu, `intelligence/essai.py` (`Banc`, 1 078 lignes), est **déjà un compositeur d'emplacements** :
   exigences typées (`Etape` : nature, capacité codée, rôle, durée, livrable) × offres datées avec plages horaires,
   recherche bornée de créneaux, accord lié à une empreinte de portée, invalidation par geste, adaptations, blocage honnête.
2. Il lui manque le **niveau « registre »** : pas de patron réutilisable indépendant d'un porteur, pas d'énumération
   des capacités possibles sur l'ensemble des offres, pas de distance 0/1, pas de levier, pas de contrefactuel, pas
   d'objet Ask, pas de consentement comme objet (finalité, expiration), pas de diff entre deux instants.
3. Le levier et la composition existent **ailleurs**, dans la détection (`detection.py` : familles `COMPOSITION` et
   `LACUNE` « la plus petite levée qui débloquerait »), mais sur les **compétences de profil**, sans temps ni consentement.
4. Verdict A6 : **généralisable sans second moteur**, à condition de généraliser le `Banc` (pas la détection) et de
   faire de `CapabilityInstance` une **projection pure** au-dessus du journal du banc. Détail § 4.
5. Tests : **523 unitaires verts** (145 s), **6 E2E verts** dans Chromium, ruff et mypy propres, aucun secret ; CI
   **verte** sur le dernier commit (run 96) — rouge de 88 à 94 (benchmarks publiés divergents, corrigé en `9f2d0e9`).
6. Deux **trous d'adaptation confirmés par exécution** (§ 3, cas 3 et 7) : retirer une compétence de son profil, ou
   se déclarer indisponible / non sollicitable, **ne dégrade pas** un accord déjà donné (l'essai reste `AUTORISE`).
7. Le « rejeu » est déterministe pour le **journal du banc** (vérifié), mais l'état métier dépend aussi de données
   **hors journal** : profils, besoins, préférences, horloge du monde (en mémoire). « Même journal → même état » n'est
   donc vrai que pour une partie de l'état.
8. La parité IA ON/OFF n'est **pas testée** en tant que telle ; il n'existe ni empreinte de projection, ni interrupteur
   IA dans l'interface (le fournisseur est choisi une fois au démarrage). Apertus n'a **jamais** été appelé.
9. L'ancien prototype « Le Fil du Club » (`app/main.py`, 1 005 lignes, ~50 routes, 10 pages) est **toujours servi**
   par le même serveur, avec une identité par simple en-tête `X-Membre` et une réinitialisation non authentifiée.
10. Ce que le jury voit : un « Doodle multi-ressources » rigoureux. Ce qu'il ne voit pas : presque tout le travail
    remarquable (empreintes d'accord, invariants par marches aléatoires, oracle, espion anti-fuite, statuts de provenance).

---

## 1. Architecture réelle (A1)

### 1.1 Couches observées

```
 NAVIGATEUR  web/pulse/app.html (téléphones) · projection.html (écran commun) · console.html · regie.html
             + ANCIEN PROTOTYPE web/*.html (index, stage, decision, cycle, soiree, club, scene, scelle, presentation)
        │ HTTP JSON — X-Pulse-Session (HMAC) · X-Pulse-Console · [ancien : X-Membre en clair]
 ADAPTATEURS  app/pulse_api.py (routes Club Pulse, au_monde = un monde + un RLock, erreurs typées → HTTP)
              app/essai_api.py (routes du banc, 30 routes) · app/main.py (ANCIEN, ~50 routes + montage des routeurs)
              app/protections.py, app/observabilite.py (CSP par empreinte, 64 Kio, X-Request-ID, logs fermés)
        │
 SERVICE      intelligence/club_pulse.py  ClubPulse : coffre, sessions, IA, banc, vues, notes, préférences, cache
              d'analyse, horloge du monde. Compose tout ; ~530 lignes.
 VUES         vues_essai.py (qui voit quoi du banc, projection en rôles, paliers) · vues_intelligence.py (découvertes)
 DOMAINE      essai.py (Banc : offres, protocoles versionnés, accords, adaptation, livraison, observation, droits)
              detection.py + observateur.py + modele.py (8 familles d'opportunités sur profils pseudonymisés)
              explication.py, passerelle.py (opportunité → brouillon d'essai), memoire_club.py (souvenirs projetés)
 PRIVÉ        identite.py (Coffre, pseudonymes, codes, nettoyer) · acces.py (sessions) · politique.py (Rendu, k=3)
 IA           ia.py : Intelligence (6 tâches), Apertus (httpx, OpenAI-compatible), Maquette (tests), repli
 PLATEFORME   plateforme/memoire.py (journal SQLite en ajout seul, transactions, cache incrémental)
              plateforme/affirmations.py (Statut, Registre d'affirmations)
              + plateforme/{compilateur,optimisation,pipeline,…}.py : plateforme de décision de l'ANCIEN prototype
 DÉMO         intelligence/demo.py (9 étapes réelles), monde_demo.py, club_synthetique.py, data/*.json
 HORS PARCOURS adaptateurs/club/* (cycle, pareto, interventions, santé, extinction…), experiences/*, app/semantique
              (ONNX local), app/mcp_serveur.py, app/soiree.py (MILP scipy)
```

Direction des dépendances vérifiée par `tests/test_architecture.py` (F). Deux journaux distincts (F) :
`ClubPulse.r.memoire` (réseau : RENCONTRE, APPEL_IA, REDACTION des découvertes, HORLOGE) et `ClubPulse.banc.m`
(essais : OFFRE, ESSAI_VERSION, ESSAI_ETAT, ACCORD, RETRAIT, ADAPTATION, LIVRAISON, RECEPTION, CONTRIBUTION,
OBSERVATION, AVIS, REUTILISATION, PROJECTION, REDACTION des invitations, GESTE_JOUE).

### 1.2 Objets centraux (F)

| Objet | Où | Rôle | Persistance |
|---|---|---|---|
| `OffreVolontaire` | `essai.py:167` | ce qu'une personne accepte de fournir : nature, capacité codée, durée max, capacité (nb d'usages), période `du/au`, conditions, **plages** déclarées, version | journal banc (`OFFRE`, `OFFRE_RETIREE`), versionnée |
| `Etape` | `essai.py:122` | un **emplacement** : nature, concept, rôle, durée, livrable, contributeur, offre, invitation | dans `ESSAI_VERSION` |
| `Protocole` | `essai.py:142` | une action concrète : question, critère, échéance, étapes (≤ 4), fenêtre, créneau, durée minimale acceptable, origine | journal banc, versionné |
| `ACCORD` | `Banc._accord` | consentement à UNE version : empreinte de portée + empreinte matérielle des offres | journal banc |
| `Opportunite` | `modele.py` | proposition de la détection (signaux cités, rôles, manque, confiance) | **calculée, jamais stockée** |
| `Profil` (skills, recherches, disponible, accepte_introductions) | `app/models.py` | ce que le membre déclare | **en mémoire du processus** (non journalisé, non daté au-delà de `maj`) |
| `BesoinActif` | `modele.py` | un besoin publié | **liste en mémoire** (`r.besoins`) |
| `Personne/Organisation` | `identite.py` | identité réelle | coffre, en mémoire |
| `AppelIA` | `ia.py` | métadonnées d'un appel | journal réseau (`APPEL_IA`, statut `SIMULE` — voir § 2.3) |

### 1.3 God Objects, frontières, place de l'IA

- **`ClubPulse`** est un objet de composition trop large (H, F sur le contenu) : coffre, sessions, IA, deux journaux,
  vues, notes privées, préférences, cache d'analyse, horloge, commandes réseau ET commandes d'action. Pas de logique
  d'adaptation dedans, mais c'est l'endroit où un nouveau « registre » serait tenté de se greffer — à éviter.
- **`Banc`** (1 078 lignes) est cohésif mais mélange trois choses séparables : (a) le calcul pur de couverture et de
  composition (`offre_couvre`, `_composer`, `solutions`, `assembler`, `raisons_gestes`, `couverture`, `alternatives`),
  (b) la machine d'états et les commandes, (c) l'après-action (livraison, réception, observation, droits).
  Les lectures sont des replis O(n²) sur le journal complet (`reservations` parcourt tous les essais) : suffisant pour
  la démo, pas pour un registre qui énumère des capacités (H).
- **`app/main.py`** (ancien prototype) est un God module : état global, magasin, routes, pages, identité par en-tête.
- **Vues avec logique** (F) : `VuesEssai.palier` (paliers de preuve), `_libelle` (regex sur le texte du geste pour
  dériver « Voix en allemand »), traduction des raisons en texte public. Pas de décision métier, mais du calcul à
  déplacer si les paliers deviennent des statuts de capacité.
- **Où l'IA intervient** (F) : `comprendre_action` / `comprendre_demande` / `structurer_essai` (texte → proposition à
  confirmer), `capturer_rencontre` (note privée, locale par défaut), `expliquer` (reformulation d'une découverte,
  vérifiée par `adaptateurs/club/synthese.verifier` : nombres et identifiants inventés rejetés),
  `rediger_sollicitation` (message d'invitation). Toutes derrière `Intelligence._executer` : schéma → validation →
  repli déterministe tracé.
- **Où elle ne doit pas intervenir** (F : c'est le cas aujourd'hui) : couverture, composition, créneaux, accords,
  transitions, destinataires, droits, révélation d'identité. Aucune de ces fonctions n'importe `ia.py`.

---

## 2. Classification de l'existant (A2) et garanties (A3)

### 2.1 État des lieux (livrable 1)

Statuts : **V** = EXISTE + VÉRIFIÉ · **PV** = PARTIELLEMENT VÉRIFIÉ · **ND** = EXISTE MAIS NON DÉMONTRÉ · **S** = SIMULÉ ·
**P** = PROMESSE · **O** = OBSOLÈTE. Parcours : **D** démo actuelle · **T** tests seulement · **C** conservé hors parcours ·
**G** candidat à généralisation · **R** candidat au retrait du parcours visible.

| Domaine | État réel | Statut | Parcours | Preuve | Risque | Réutilisable |
|---|---|---|---|---|---|---|
| Journal d'événements (SQLite, ajout seul, transactions, idempotence par empreinte) | fiable, rejouable ; deux journaux séparés | V | D | `plateforme/memoire.py`, `test_atomicite.py` | pas de numéro de schéma ; `_ecrire` compte tout le journal à chaque écriture | **oui, fondation** |
| Offres datées + plages (≈ claims RESOURCE/SKILL+SLOT) | versionnées, retirables, expirent, capacité | V | D, G | `test_creneaux.py`, `test_essai.py` | seule une compétence déclarée au profil peut être offerte — vérifié à la publication seulement | **oui → Claim** |
| Compétences / recherches de profil (≈ claims SKILL/NEED) | en mémoire, non journalisées, non bi-temporelles | PV | D (onboarding), G | `club_pulse.onboarding` | **hors journal** : pas de rejeu, pas d'expiration, changement sans effet sur les accords | à migrer dans le journal |
| Composition bornée (`_composer`, `solutions`, `assembler`) | exhaustive au quart d'heure ; « manque » par exigence | V | D, G | `test_creneaux.py`, oracle `eval/benchmark_pulse.py` (118/118, 187/187, 122/122) | combinatoire liée à UN protocole ; aucune énumération globale | **cœur de `compose`** |
| Accord versionné (empreinte de portée + empreinte matérielle) | un accord ne suit ni une autre version ni d'autres conditions | V | D | `test_audit_essai.py` (P1/P2 rouges sur l'ancien code) | pas de finalité ni d'expiration propres | **→ ConsentGrant** |
| Machine d'états (`TRANSITIONS`) + réévaluation | BROUILLON…OBSERVEE, IMPOSSIBLE rouvrable | V | D | `test_essai_invariants.py` (marches aléatoires, 10 invariants) | états nommés « essai », pas « capacité » | **→ statuts d'instance** |
| Adaptation (remplacer, raccourcir, décaler, accepter_conditions, reprendre) | déterministe, choisie par le porteur, reconfirmations ciblées | V | D | `test_creneaux.py`, `test_action_collective.py` | pas d'« hypothèses » ni de « ce qu'on ignore » structurés | **→ recompose** |
| Paliers de preuve (proposé → accepté → transmis → livrable reçu → reçu) | jamais plus fort que la preuve | V | D | `test_creneaux.py::test_livrable_transmis…` | calculés dans la VUE | déplacer vers le domaine |
| Détection d'opportunités (8 familles, dont COMPOSITION et LACUNE/levier) | complète sur profils ; alimente les « découvertes » | PV | C (routes servies, non liées dans l'UI d'action) | `test_intelligence_detection.py`, `test_pourquoi.py` | second raisonnement « qui peut aider » parallèle au banc | **LACUNE → leverage** ; le reste : HIDE |
| Passerelle opportunité → essai (gestes « sur invitation ») | l'invité déclare sa dispo EN acceptant | V | C, G | `test_essai.py`, `test_boucle.py` | — | **= l'opportunité 1-à-1 comme patron à 2 emplacements** |
| Mémoire du Club (souvenirs projetés du banc) | contestable, bornée par droits | PV | C | `test_boucle.py` | faible valeur démo | KEEP (Outcome) |
| Coffre, pseudonymes, `nettoyer` | nom/org/courriel/tél. retirés ; effacement par destruction du lien | V | D | `test_identite_confidentialite_ia.py`, `test_ia_espion.py` | nettoyage par liste de noms : surnoms, fautes, initiales passent (H) | KEEP |
| Sessions HMAC 12 h, codes d'invitation | expiration, comparaison à temps constant | V | D | `test_securite_pulse.py`, `test_essai_securite.py` | **codes réutilisables, sans expiration, sans révocation** (F, HANDOFF § 12.5) | KEEP + durcir pour QR juré |
| Politique de rendu / projection en rôles | aucun nom sur l'écran commun ; consentement de projection | V | D | `test_action_collective.py`, balayage 767 écrans / 0 fuite | quasi-identifiants par horaires rares (HANDOFF § 13.5) | KEEP |
| Frontière IA (`Intelligence`, schémas, repli, disjoncteur) | 6 tâches, validation, repli tracé | PV | D (repli seulement) | `test_frontiere_ia.py`, `test_ia_espion.py` | **Apertus jamais exécuté** ; pas de « 1 retry » sur sortie invalide ; pas de fact IDs | **→ adaptateur EXTRACT/NARRATE/NORMALIZE** |
| Apertus réel | client écrit, jamais appelé | ND | — | `eval/resultats_apertus.md` (repli seulement) | endpoint/modèle/thinking non vérifiés | à valider en Phase 3 |
| Statuts SYNTHÉTIQUE/DÉCLARÉ/JOUÉ | présents sur le journal du banc | PV | D | `test_statuts_donnees.py` (3 tests) | APPEL_IA marqué `SIMULE` ; profils/besoins sans statut | KEEP + étendre |
| Horloge de démo | paramètre injecté ; +N jours depuis la console | S | D | `test_periode_demo.py` | **non persistée** : un redémarrage revient au 06.10 | → événement HORLOGE lu par le banc |
| Console / régie / projection | pilotage, gestes joués marqués | V | D | `test_e2e_action.py` | — | REFACTOR (console animateur) |
| Ancien prototype « Le Fil du Club » (`app/main.py`, 10 pages) | servi, autres données | O | C | `test_scene.py`, `test_e2e_scene.py` | **identité par `X-Membre`**, `/api/demo/reinitialiser` sans garde, surface d'attaque le jour J | **HIDE** (puis DELETE) |
| Plateforme de décision, cycle, pareto, interventions, santé, soirée (MILP), sémantique ONNX, MCP | code riche, tests propres | O | C | `eval/*`, tests dédiés | maintien, CI plus lente, confusion du récit | HIDE, coût § 7 |
| Benchmarks publiés reproductibles à l'octet | CI les rejoue et fait `git diff --exit-code` | V | T | CI run 96 vert ; `test_resultats_publies.py` | rouge de 88 à 94 : fragile à chaque changement de vue | KEEP |
| « Mutation testing » | **mutations manuelles** par `monkeypatch` (quelques gardes) | PV | T | `test_essai_invariants.py::test_une_mutation…`, `test_essai_securite.py` | aucun outil (mutmut/cosmic-ray absents) | BUILD en Phase 1 |
| Tests « par propriétés » | marches aléatoires à graines fixes, sans rétrécissement | PV | T | `test_essai_invariants.py` | pas d'Hypothesis | BUILD (oracle force brute) |
| Vidéo et captures de démo | enregistrées à `dd75a7c`, anciennes dates | O | D (secours) | `TODO-DEMO.md` | présenter une vidéo périmée | régénérer après stabilisation (B8) |

### 2.2 Garanties annoncées (A3)

Commandes exécutées depuis `prototype/` avec `HACKVS_SEMANTIQUE=0`. Résultats du 2026-09-30.

| Garantie | Preuve dans le code | Test | Commande | Résultat | Limitation |
|---|---|---|---|---|---|
| Identité réelle séparée des données du moteur | `Coffre.pseudonymiser` ; `ClubPulse.__init__` ne passe que des profils pseudonymisés | `test_identite_confidentialite_ia.py::test_le_moteur_ne_recoit_que_des_pseudonymes` | `pytest -q tests/test_identite_confidentialite_ia.py` | vert | le journal du banc contient les **identifiants internes** (`s01`) et les **textes libres** d'offres (« stand de la distillerie, halle 3 ») : quasi-identifiants hors coffre |
| Aucune identité du coffre envoyée au modèle | `Intelligence.proteger` → `nettoyer(message, identites())` sur CHAQUE appel | `test_ia_espion.py::test_aucune_identite…` (6 tâches, espion) — rouge sur l'ancien code (commit `6eecb53`) | `pytest -q tests/test_ia_espion.py` | vert | nettoyage **lexical** : un surnom, une initiale, une faute de frappe ne sont pas retirés (H, non testé) |
| Aucun appel IA lors d'une lecture ou d'un rejeu | narrations écrites par commande (`narrer_decouverte`, `rediger_invitations`) et journalisées (`REDACTION`) ; GET relit | `test_ia_espion.py::test_une_lecture_ou_un_rejeu…` | idem | vert | les sorties d'**extraction** (`comprendre_action`) ne sont pas journalisées (seule la version confirmée par l'humain l'est) : acceptable, à documenter comme tel |
| Parité IA ON/OFF (même journal → même état → même empreinte) | aucune fonction « empreinte de projection » ; fournisseur fixé au démarrage (`depuis_environnement`) | **aucun test de parité** | sonde : démo complète avec un fournisseur espion (sortie toujours rejetée) vs sans IA | état métier identique ; empreinte du journal banc identique | **trivial** : l'espion est rejeté, donc repli. Une sortie IA *valide* différente produit des exigences différentes (par conception, avant confirmation humaine). Pas d'interrupteur UI. → **ND** |
| SYNTHÉTIQUE / DÉCLARÉ / JOUÉ séparés | `Banc.origine(statut)` ; `ClubPulse.joue()` ; `GESTE_JOUE` journalisé | `test_statuts_donnees.py` (3, rouges avant `2919ee3`) | `pytest -q tests/test_statuts_donnees.py` | vert | `APPEL_IA` journalisé en `SIMULE` (`club_pulse.py:96`) : faux libellé ; profils et besoins **sans statut** (hors journal) |
| Gestes joués réellement journalisés, survivent au redémarrage | `jouer()` écrit `GESTE_JOUE` | `test_statuts_donnees.py::test_la_marque_joue_survit…` | idem | vert | — |
| Replay déterministe | `Evt.id` = empreinte du contenu ; horloge injectée | `test_ia_espion` (même empreinte après redémarrage) | sonde : deux démos complètes | empreintes banc et réseau identiques | l'état dépend de **profils, besoins, préférences, horloge hors journal** ; `test_redemarrage.py` teste **l'ancien prototype**, pas Club Pulse |
| Benchmarks reproductibles bit à bit | `scripts/reproduire_sprint.py` + `git diff --exit-code -- eval/` en CI | `test_resultats_publies.py` | CI run 96 | vert (rouge runs 88–94) | non rejoué localement dans cette inspection (durée) ; le résultat CI fait foi |
| Autorisations | `_exiger_porteur`, `decider` (404 si non concerné), console : en-tête + jeton ou machine locale | `test_essai_securite.py`, `test_securite_pulse.py` | `make test` | vert | ancien prototype : **n'importe qui peut être n'importe quel membre** via `X-Membre` (mode démo) |
| Sessions, expiration | HMAC-SHA256, 12 h, horloge injectable | `test_securite_pulse.py` | idem | vert | codes d'invitation permanents, pas de révocation d'un jeton |
| CSRF | pas de cookie : en-têtes personnalisés (`X-Pulse-Session`, `X-Pulse-Console`) | `test_essai_securite.py:254` | idem | vert | ancien prototype : en-tête `X-Membre`, même raisonnement (pré-vol CORS) |
| Rate limiting | `Limiteur` en mémoire : 10/min/IP sur `/acces`, 30/min/membre sur les tâches IA | `test_securite_pulse.py` | idem | vert | un processus ; derrière un NAT de salle, tous les jurés partagent une IP → **10 scans/minute au total** (H, risque pour le flux QR) |
| Concurrence | un `RLock` par monde, toute requête dessous | `test_essai_securite.py` (fils : 200 + 409) | idem | vert | mono-processus |
| Atomicité | `Memoire.transaction()` réentrante, rollback + vidage du cache | `test_atomicite.py` | idem | vert | — |
| Stale versions | `_verifier_version` → 409 sur toute commande engageante | `test_essai_securite.py`, sonde cas 12 | idem | `Conflit` | — |
| Refus | jamais redemandé ; jamais nommé ; exclu des candidats | `test_creneaux.py::test_un_refus_n_est_jamais_garde…` | idem | vert | — |
| Retrait | `RETRAIT` → réévaluation ; refusé après l'action ; anonyme à l'écran commun | `test_creneaux.py::test_un_retrait_apres_accord…` | idem | vert | pas d'objet consentement avec reçu présentable |
| Réutilisation | `REUTILISATION` par participant, niveau le plus restrictif | `test_essai.py` | idem | vert | — |
| Adaptation | § 3 | `test_creneaux.py`, `test_audit_essai.py`, marches | idem | vert | trous cas 3 et 7 |
| E2E | Chromium réel, deux téléphones + écran commun | `test_e2e_action.py`, `test_e2e_pulse.py`, `test_e2e_scene.py` | `HACKVS_E2E_OBLIGATOIRE=1 pytest -q tests/test_e2e_*.py` | **6 passed (60 s)** | machine de dev, pas un réseau de salle |
| Mutation testing | gardes mutées à la main | 2 fichiers | — | vert | pas d'outil, pas de score |
| CI | `.github/workflows/ci.yml` : qualité, dépendances (pip-audit), reproductibilité + E2E | — | GitHub Actions | **run 96 (`9744027`) : success** ; runs 92–94 : failure | — |
| Lint / types / secrets | ruff, mypy (plugin Pydantic), `verifier_secrets.py` | — | `ruff check . && mypy … && python scripts/verifier_secrets.py` | propres | — |

### 2.3 Points hérités de la dernière session de durcissement

| Point | Constat (F) |
|---|---|
| Tests espions anti-fuite (coffre → IA) | présents et verts (`tests/test_ia_espion.py`, 2 tests) ; ils échouaient sur le code d'avant `6eecb53` (message du commit). |
| Statuts SYNTHÉTIQUE/DÉCLARÉ/JOUÉ | présents et verts (`test_statuts_donnees.py`). Écart restant : `APPEL_IA` en `SIMULE`. |
| Dates sur la Foire | `club_synthetique.AUJOURD_HUI` = mardi 06.10.2026, `monde_demo.JOUR_SCENE` = jeudi 08.10, Foire 02–11.10 ; `test_periode_demo.py` (3) vert. |
| Artefacts périmés (non régénérés, comme demandé) | `docs/audit/club-pulse-pivot/captures/action/demo_action.webm` et `demo_action.json` (commit `dd75a7c`, « 05.11 ») ; `p0…p6*.png`, `a1…a4*.png`, `b1*.png` (« Jeudi 05.11 ») ; `delais.json` ; `DEMO_SCRIPT.md` § 6 ; `REVUE_JURY.md` § 1 ; `PREUVES.md` (514 tests, désormais 523 + 6 E2E) ; `captures/essai-*.png` (ancien scénario « étiquette »). Aussi `competition/video/demo.webm` et `competition/*` (pitch de l'ancien prototype « Le Fil du Club ») : **non alignés sur Club Pulse**. Liste tenue dans `TODO-DEMO.md`. |
| **Correctif 3** | **Le journal de session n'est pas dans le dépôt et je n'y ai pas accès** (contexte effacé). Reconstruction à partir des messages de commit : la série « stage-0 audit » compte, dans l'ordre, (1) IA `6eecb53`, (2) CI E2E `fbb9898`, (3) **provenance SYNTHÉTIQUE/DÉCLARÉ/JOUÉ `2919ee3`**, (4) dates `1a855b1`, puis (5) benchmarks CI `9f2d0e9` — `9f2d0e9` les cite lui-même dans cet ordre (« after the AI, CI, provenance and date commits »). Si « correctif 3 » désigne la provenance : **traité**, poussé sur la branche, CI verte ; **non fusionné** au sens d'une PR (aucune PR ; la branche de travail est la seule branche). Reste de ce correctif : `APPEL_IA` en `SIMULE` au lieu d'un statut propre (risque faible : libellé d'audit faux ; coût : 1 ligne + 1 test). **À confirmer par vous** si la numérotation du journal diffère. |

---

## 3. Vérification critique du moteur d'adaptation (A4)

Méthode : lecture de `essai.py` + sonde exécutée sur la démo réelle (`Demo` jusqu'à l'étape 4, essai `AUTORISE`),
script hors dépôt. « Invalide ce qui doit l'être ? » = l'état et la couverture changent-ils ?

| # | Cas | Mécanisme | Invalide réellement ? | Preuve |
|---|---|---|---|---|
| 1 | Une personne accepte | `decider` revérifie `offre_couvre` sous le verrou ; accord = empreinte de portée + empreinte matérielle | oui (refus si l'offre ne couvre plus) | `test_essai.py`, `test_action_collective.py` |
| 2 | Sa disponibilité (plages d'offre) change | `modifier_offre` → `_revoir_essais_de_l_offre` → `A_ADAPTER` ou `IMPOSSIBLE` | oui | `test_creneaux.py::test_perturbation…`, 6 heures jury |
| 3 | **Sa compétence déclarée change** (retirée du profil) | profil hors journal ; `offre_couvre` ne relit pas le profil | **NON** — sonde : Léa retire « traduction », essai reste `AUTORISE`, couverture `None` | sonde F |
| 4 | Une ressource disparaît (offre retirée) | `retirer_offre` → réévaluation | oui | marches aléatoires, `test_creneaux.py` |
| 5 | Une offre expire | offres exigées valables jusqu'à l'échéance ; `echeances()` réévalue PROPOSE/AUTORISE ; après l'action, accord figé | oui (A_ADAPTER/EN_COURS non réévalués par l'horloge, mais les alternatives sont recalculées au choix et le lancement revérifie) | `test_trente_jours…`, `lancer` |
| 6 | Retrait de consentement | `RETRAIT` → réévaluation ; refusé après l'action ; « une personne s'est retirée » en projection | oui | `test_creneaux.py` |
| 7 | **Indisponibilité** (profil `disponible=False`, non sollicitable) | règles dures lues seulement pour de **nouvelles** sollicitations (commentaire `club_pulse.py:200`) | **NON** — sonde : essai reste `AUTORISE` | sonde F ; choix de conception documenté, incompatible avec l'invariant B3.1 |
| 8 | Deux contributions de la même personne | `raisons_gestes` par geste (P2) ; `_composer` interdit deux gestes au même auteur ; `occupations` interdit deux créneaux qui se chevauchent | oui | `test_p2_…`, `test_une_personne_n_est_jamais_engagee_deux_fois…` |
| 9 | Plusieurs contributions liées à une même capacité | `reservations` ≤ `capacite` de l'offre, tous essais confondus | oui pour la capacité d'une offre ; **aucune notion de composant partagé entre capacités** (levier) | marches, mutation de la règle de capacité |
| 10 | Contribution partiellement invalide | par geste : `perdus` vs `A_REDEMANDER` ; adaptation ciblée | oui | `test_creneaux.py` |
| 11 | Condition qui change après acceptance (écart d'audit) | empreinte matérielle `_materiel` (quoi, nature, concept, conditions) + contrôles numériques (durée, dates, plages, capacité) | **oui pour l'offre** (corrigé P1, `test_audit_essai.py` rouge avant) ; **non** pour ce qui vit hors offre : compétence au profil (cas 3), disponibilité/sollicitabilité au profil (cas 7), règles dures d'éligibilité (`_eligibilite`, jamais relue après l'accord) | tests P1 + sonde |
| 12 | Décision ancienne rejouée | `_verifier_version` → `Conflit` ; double clic même version → idempotent | oui | sonde : `Conflit` |
| 13 | Deux décisions concurrentes | RLock du monde + transaction | oui (200 + 409) | `test_essai_securite.py` (fils) ; mono-processus |
| 14 | Adaptation impossible | `IMPOSSIBLE` + `_manques` ; rouvert par un fait nouveau, jamais relancé seul | oui ; le message dit la **cause** et ce qui manque, pas « ce qu'on sait / ce qu'on ignore / ce qui débloquerait » de manière structurée | `test_sans_solution_bloque_puis_debloque…` |
| 15 | Adaptation exigeant un nouveau consentement | toute nouvelle version change les portées concernées → reconfirmation ; `decaler` : tout le monde ; `accepter_conditions` : porteur puis personne | oui | `test_creneaux.py`, `test_audit_essai.py::test_p1_revision…` |

**Conclusion A4.** Pour tout ce qui passe par une **offre**, le moteur invalide réellement ce qui doit l'être, et c'est
démontré par des tests qui échouaient sur l'ancien code. Les trous sont **à la frontière du profil** : un fait déclaré
hors du journal du banc (compétence, disponibilité générale, consentement aux sollicitations) ne dégrade jamais un
accord existant. Dans le modèle cible, où une capacité n'existe que si **tous** ses composants sont valides à t, c'est
bloquant : il faut que ces faits deviennent des claims journalisées que la couverture relit (Phase 1).
Autre écart relevé : `Banc._jour` et `_eligibilite` sont des **fonctions externes** (horloge et profils en mémoire)
appelées pendant le repli : la couverture n'est pas une fonction du seul journal.

---

## 4. Question centrale (A5) — ce que le jury voit en deux minutes

**Ce qu'il voit (F, vidéo et DEMO_SCRIPT) :** des barres d'horaires anonymes ; Sophie tape son besoin ; trois exigences
« règles simples » ; un créneau commun 16:00–16:45 ; Léa accepte sur son téléphone ; deux accords « joués » ; le jury
donne une heure ; un encadré « ne couvre plus / reste valable / adaptations » ; Sophie choisit ; tout le monde
reconfirme ; la fiche arrive ; +30 jours : « résultat inconnu ».

**Ce qu'il comprend (H, cohérent avec `REVUE_JURY.md` § 2) :** « un Doodle à plusieurs ressources avec des
confirmations ». Le recalcul après la perturbation est le seul moment non trivial, et il arrive vers 0:44.

**Ce qu'il doit croire sans le voir :** que l'accord est lié à une version (empreinte) et que seule la bonne personne
reconfirme ; que rien n'est inventé (oracle force brute) ; qu'aucune identité ne part vers un modèle (espion) ; que
lire ne déclenche rien ; que « joué » est journalisé ; que les invariants tiennent sur des milliers de pas aléatoires ;
que l'écran commun ne fuit rien (767 écrans).

**Ce qui reste invisible et qui est remarquable :** la **pièce manquante** (le moteur sait exactement quelle exigence
manque et pourquoi, `assembler.manque`) ; le **contrefactuel** implicite de `raisons_gestes` (qui tombe si X change) ;
le **levier** calculé par la détection (`LACUNE`) ; la distinction transmis ≠ reçu ≠ réalisé ; le blocage honnête qui
se rouvre. Le pivot doit précisément mettre **ces trois objets au premier plan** : l'emplacement vide, ce qu'il
débloquerait, ce qui tomberait sans lui. Tout le reste existe déjà.

---

## 5. Verdict de compatibilité (A6)

**Verdict : OUI, généralisable sans second moteur — à condition de généraliser le `Banc` et non la détection.**

### 5.1 Ce qui se généralise directement

| Concept cible | Équivalent existant | Généralisation |
|---|---|---|
| `CapabilityPattern` (slots typés + contraintes, auteur humain) | `Protocole` sans porteur ni créneau : `etapes` (nature, concept, rôle, durée, livrable) + `fenetre` + `duree_min_acceptable` | extraire un **modèle** de protocole, écrit en données (JSON versionné), jamais par l'IA ; un `Protocole` devient une instance liée d'un patron |
| slot | `Etape` | + contraintes numériques (≥ 15 pers., ≥ 12 places) : **nouveau** champ `contraintes` vérifié par `offre_couvre` |
| `compose` | `_composer` + `solutions` + `assembler` | appliqué à (patron, index des claims, t) au lieu de (essai) ; **même code**, paramétré |
| `distance` 0/1 | `assembler()["manque"]` (liste d'exigences sans offre) | `len(manque)` ∈ {0, 1, ≥2} ; n'exposer que 0 et 1 |
| `critical_components` | `raisons_gestes` + `alternatives` par geste | contrefactuel : retirer la claim liée, relancer `compose` ; calculé |
| `recompose` / NO SAFE MATCH | `alternatives`, `_reevaluer` → `IMPOSSIBLE`, `_manques` | + champs structurés : cause, sait, ignore, débloquerait |
| statuts d'instance | `PROPOSE`, `AUTORISE`, `A_ADAPTER`, `IMPOSSIBLE`, `EXPIRE` | ONE_AWAY = distance 1 (projection, non écrit) · PROPOSED = PROPOSE · CONSENTED = AUTORISE · ACTIVE = EN_COURS (ou AUTORISE si on définit ACTIVE comme « tous accords valides à t » — **à trancher**) · DEGRADED = A_ADAPTER · EXTINCT = IMPOSSIBLE/EXPIRE/ANNULE |
| `ConsentGrant` | `ACCORD` (empreinte de portée) + `PROJECTION` + `REUTILISATION` | ajouter finalité, portée lisible, `expires_at`, reçu ; **ne pas** créer une seconde table de consentements |
| `Claim` | `OffreVolontaire` (versions, `du/au`, retrait, plages, concept) | généraliser en `kind` (RESOURCE/SKILL/SLOT…) ; y migrer compétences de profil et besoins ; `recorded_at` = `seq`/`le`, `superseded` = version suivante |
| `leverage` | `detection.py` famille `LACUNE` (« plus petite levée qui débloquerait ») | **porter la règle** sur les instances ONE_AWAY du banc (nb d'instances dont la pièce manquante est le même slot) ; ne pas garder deux calculs |
| `Ask` | invitation (`Etape.invitation`, `rediger_invitations`, personne déclare EN acceptant) | l'Ask est une invitation adressée à une **catégorie** (concept + règles dures) au lieu d'une personne ; expiration = échéance |
| opportunité 1-à-1 | `passerelle.brouillon` : opportunité → protocole à gestes sur invitation | = patron à 2 emplacements (bénéficiaire + contributeur) ; **déjà presque le cas** |
| `Outcome`, `Agreement` | `CONTRIBUTION`, `OBSERVATION`, `AVIS` ; `ACCORD` | relier à l'instance ; rien à recréer |
| `pulse_diff` | replis purs + horloge paramètre | exige que l'horloge et toutes les claims soient **dans le journal** ; diff = projection(t1) − projection(t0) |

### 5.2 Ce qui manque (BUILD)

1. Patrons en données + chargement validé (6 patrons écrits comme par le Club).
2. **Index des claims** au lieu du balayage complet du journal (sinon énumérer patrons × claims sera lent : `reservations` est déjà O(essais × étapes) par appel).
3. Contraintes numériques de slot (capacité de salle, places), et **type d'acte** (HANDOFF § 13.1 : « conseiller » ≠ « amener »).
4. Journalisation des compétences de profil, besoins, disponibilité générale, horloge — et relecture par la couverture (ferme les trous A4 cas 3, 7, 11).
5. Objet Ask avec plafond par membre (aujourd'hui : aucun budget d'attention dans le banc ; l'ancien moteur avait `BUDGET_ATTENTION = 2`, retiré avec lui).
6. `ConsentGrant` avec reçu et expiration ; écran « Mes données ».
7. Projection `CapabilityInstance` + empreinte canonique (pour la parité et le rejeu).
8. Validateur de citations par fact IDs (aujourd'hui : `synthese.verifier` vérifie nombres et identifiants, sans IDs de faits) ; « 1 retry » avant repli.

### 5.3 Ce qu'il ne faut surtout pas dupliquer

- **Un second compositeur** : la détection (`COMPOSITION` = couverture par ensembles sur les profils) et le banc
  (`_composer` avec créneaux) composent déjà deux fois. Le registre doit utiliser **uniquement** celui du banc ; la
  famille `COMPOSITION` de la détection doit disparaître du parcours.
- **Une seconde machine d'états** : `CapabilityInstance.status` doit être **dérivé** de `TRANSITIONS`, pas une table parallèle.
- **Un second journal** : pas de « capability store » ; les instances sont recalculées.
- **Un second système de consentement** : `ACCORD` enrichi, pas remplacé.
- **Une seconde couche de rendu** : `Rendu` / `VuesEssai` restent le seul chemin vers un humain.

### 5.4 L'abstraction « capacité » est-elle bonne ici ?

Oui, **si** « capacité » désigne une *projection* (« le Club pourrait faire X maintenant, à ces conditions ») et
jamais une garantie — ce que le code sait déjà faire (paliers jamais plus forts que la preuve). Deux mises en garde (H) :
- **Explosion combinatoire** : une instance par (patron × liaisons) est ingérable. Proposition : une instance par
  (patron × fenêtre), portant **la meilleure liaison** et un nombre d'alternatives, comme `solutions(maximum=3)`.
- **Temps** : la plupart des capacités n'existent qu'à un créneau. Le patron doit porter une **fenêtre** (ou une
  récurrence) ; sans cela, « le Club peut accueillir une délégation » est une affirmation atemporelle que le moteur ne
  peut pas vérifier. Proposition de nom si l'ambiguïté gêne à l'écran : « **assemblage** » pour l'instance,
  « **recette** » pour le patron — le code peut garder `CapabilityPattern` / `CapabilityInstance`.

---

## 6. Architecture cible proposée (livrable 2)

```
 web/pulse : Établi (écran commun) · Passeport · Téléphone (Ask, reçu, retrait, Mes données) · Console animateur
        │  HTTP (adaptateurs minces, inchangés dans leur rôle)
 SERVICE  ClubPulse allégé : composition seulement ; RegistreService (commandes Ask / réponse / retrait)
        │
 PROJECTIONS (pures, recalculables, empreinte canonique)
   capacites.projeter(journal, patrons, t) → [CapabilityInstance]      ← compose / distance / leverage / critical
   capacites.pulse_diff(journal, t0, t1)                                ← deux projections
 DOMAINE
   patrons/ (données JSON versionnées, auteur humain, validées)          ← NOUVEAU (données, pas code)
   essai.Banc  = moteur d'activation : claims (ex-offres) + instances engagées (ex-protocoles) + accords + adaptation
                 découpé en  couverture.py (pur : offre_couvre, _composer, solutions, raisons)  +  banc.py (commandes)
   asks.py     = sélection d'Ask (catégorie, plafond, expiration) — lit la projection, écrit des événements ASK_*
   identite / acces / politique : inchangés
 IA  ia.py → rôles EXTRACT / NARRATE / NORMALIZE ; paquet de faits avec IDs ; AICall journalisé et rejoué
 JOURNAL  plateforme/memoire.py (un seul journal pour claims, horloge, instances engagées, Ask, consentements)
```

Règles ajoutées à `test_architecture.py` : `capacites` n'importe ni `ia` ni `detection` ; `ia` n'importe ni
`capacites` ni `essai` ; seuls `asks` et le service écrivent des événements ASK ; les patrons ne sont écrits par
aucun module IA.

---

## 7. Inventaire KEEP / REFACTOR / REUSE / HIDE / DELETE / BUILD (livrable 3)

| Action | Éléments |
|---|---|
| **KEEP** | `plateforme/memoire.py`, `plateforme/affirmations.py` (Statut), `identite.py`, `acces.py`, `politique.py`, `erreurs.py`, `app/pulse_api.au_monde`, `app/protections.py`, `app/observabilite.py`, `memoire_club.py`, tests de sécurité/atomicité/espion/statuts, CI (3 jobs), `eval/benchmark_pulse.py` (oracle + balayage des écrans) |
| **REFACTOR** | `essai.py` → séparer couverture pure / commandes ; `OffreVolontaire` → `Claim` (rétrocompatible : `kind` par défaut) ; `ACCORD` → + finalité, expiration, reçu ; `ClubPulse` → retirer notes/préférences/profils vers le journal ; `VuesEssai.palier` → domaine ; `_libelle` (regex) → libellé porté par le patron ; `APPEL_IA` → statut propre |
| **REUSE** | `detection.py` famille `LACUNE` (règle de levier), `passerelle.brouillon` (1-à-1 = patron à 2 slots), `explication.py` (structure « déclaré / observé / confirmé / inconnu »), `ia.py` (adaptateur), `synthese.verifier` (base du validateur de citations), `test_essai_invariants.py` (marches → propriétés du registre) |
| **HIDE** (non servi en démo, code gardé) | `app/main.py` et ses 10 pages (ancien prototype) ; routes découvertes `/moi/decouvertes*`, `/console/intelligence` ; `plateforme/{compilateur,optimisation,pipeline,…}` ; `adaptateurs/club/*` ; `experiences/*` ; `app/semantique.py` (ONNX), `app/mcp_serveur.py`, `app/soiree.py` ; routes « banc d'essai étiquette » (`/moi/essais/preparer`, `structurer_essai`) ; `competition/*` (pitch de l'ancien prototype) |
| **DELETE** (après démonstration de non-régression) | familles de détection sans objet dans le registre (`CONVERGENCE`, `CAPACITE_DORMANTE`, `SUIVI`…) ; graphe `memoire.graphe/fermetures/indicateurs` (networkx) s'il n'est plus lu ; ancien prototype après le hackathon. Rien n'est supprimé avant la Phase 2. |
| **BUILD** | patrons + chargeur ; index des claims ; contraintes de slot et type d'acte ; `capacites.py` (projection, distance, leverage, critical, recompose structuré, pulse_diff) ; `asks.py` (plafond, catégorie, concurrence) ; `ConsentGrant` + reçu + « Mes données » ; empreinte de projection + test de parité IA ON/OFF en CI ; interrupteur IA dans l'UI ; validateur de fact IDs + 1 retry ; QR juré (codes à usage unique, expirants) ; Établi / Passeport / Console ; tests par propriétés contre oracle ; mutation testing outillé (mutmut) sur `capacites` et la couverture |

**Éléments de la liste B11 déjà présents** (non supprimés, statut et coût) :

| Élément | Où | Statut | Coût de maintien |
|---|---|---|---|
| graphe social / métriques réseau | `plateforme/memoire.graphe`, `web/cycle.html`, `web/decision.html`, `adaptateurs/club/reseau.py` | hors parcours, servi | networkx + tests eval ; faible si caché |
| scores / santé / pareto | `adaptateurs/club/sante.py`, `pareto.py`, `web/js/club.js` | hors parcours, servi | ~400 lignes + benchmarks publiés (font rougir la CI s'ils divergent) |
| agent MCP | `app/mcp_serveur.py`, `scripts/mcp_club.py` | hors parcours | dépendance `mcp`, tests stdio/HTTP |
| « chatbot » / analyse libre en flux | `app/main.py /api/analyser/flux`, `app/parser_llm.py` (Claude) | ancien prototype | dépendance `anthropic` facultative |

---

## 8. Plan de migration en 4 phases (livrable 5)

Principe : chaque phase se termine par `make quality-check` vert et le scénario de la phase **rejoué 10 fois**.
Petits commits ; refactor, feature et correctif jamais mélangés ; chaque test de correction vérifié **rouge** sur
l'ancien code.

### Phase 1 — Capability core (sortie : scénario A de bout en bout SANS IA)

| | |
|---|---|
| Fichiers | `intelligence/essai.py` (découpe), NOUVEAU `intelligence/couverture.py` (pur), NOUVEAU `intelligence/capacites.py`, NOUVEAU `data/patrons/*.json`, `club_pulse.py` (profils/besoins/horloge → journal), `plateforme/affirmations.py` |
| Généraliser | `OffreVolontaire` → `Claim(kind)` ; `Protocole` sans porteur → `CapabilityPattern` ; `assembler` → `compose(patron, claims, t)` ; `manque` → `distance` |
| Ne pas dupliquer | `_composer`/`solutions` (déplacés, pas réécrits) ; `TRANSITIONS` |
| Tests à ajouter | oracle force brute (patrons × claims ≤ 6 × 20) vs `compose` ; propriétés : distance ∈ {0,1,≥2} cohérente avec l'oracle, ACTIVE ⇒ composants valides à t (B3.1), claim expirée ⇒ invalide mais présente (B3.9), projection recalculée = projection incrémentale (B3.3) ; **cas 3 et 7 d'A4 rouges puis verts** ; empreinte de projection stable sur deux rejeux (B3.13) ; les 523 tests existants verts sans modification d'attente |
| Risques | casser P1/P2 en déplaçant la couverture (mitigation : déplacement mécanique d'abord, commit dédié, tests inchangés) ; performance (index) |
| Critère de sortie | scénario A (capacité à une pièce → Ask → réponse → active) via l'API, IA désactivée ; oracle 100 % ; mutation score ≥ seuil fixé avant exécution sur `couverture.py` |
| Commits proposés | `refactor(couverture): extract pure coverage and composition from Banc (no behaviour change)` · `feat(claims): journal profile skills, needs, availability and clock` · `fix(adaptation): a withdrawn skill or declared unavailability degrades an accord (A4 cases 3, 7)` · `feat(capacites): patterns as data, compose and distance projection` · `test(capacites): brute-force oracle and properties` |

### Phase 2 — Activation (sortie : retrait → dégradation → recomposition vérifiable, retrait anonyme)

| | |
|---|---|
| Fichiers | `capacites.py` (leverage, critical_components, recompose structuré, pulse_diff), NOUVEAU `intelligence/asks.py`, `essai.py` (`ACCORD` → ConsentGrant), `vues_essai.py` (Passeport, Mes données), `app/essai_api.py` (routes Ask, reçu, retrait) |
| Généraliser | `LACUNE` → `leverage` ; invitation → Ask à une catégorie ; `alternatives` → `recompose` + « NO SAFE MATCH » (cause / sait / ignore / débloquerait) |
| Ne pas dupliquer | le calcul de levier de `detection.py` (porté puis retiré du parcours) ; `Rendu` |
| Tests à ajouter | B3.5, 7, 10, 11, 12 ; concurrence : 2 réponses simultanées à une Ask ⇒ une liaison, déterministe (fils + ordre `seq`) ; plafond 1 Ask/membre/semaine ; retrait jamais attribué (balayage des écrans étendu) ; pulse_diff = diff de deux rejeux |
| Risques | Ask perçue comme assignation (texte : « une personne du Club qui… », jamais un nom choisi) ; plafond qui bloque la démo |
| Critère de sortie | le scénario C sans IA : réponse → capacité CONSENTED/ACTIVE → retrait → DEGRADED à la projection suivante → recomposition proposée → décision humaine ; 10 fois de suite |
| Commits proposés | `feat(capacites): leverage and counterfactual critical components` · `feat(asks): minimal time-bound ask to a category, weekly cap` · `feat(consentement): grant with purpose, expiry and receipt` · `feat(pulse): diff of two replays` · `feat(vues): capability passport and « my data »` |

### Phase 3 — IA (sortie : parité IA ON/OFF verte en CI)

| | |
|---|---|
| Fichiers | `ia.py` (rôles EXTRACT/NARRATE/NORMALIZE, paquet de faits à IDs, 1 retry, `AICall` journalisé avec `used_fact_ids`, `schema_valid`, `fallback_used`), `adaptateurs/club/synthese.py` (validateur de citations), `prompts/*_v2.md`, UI (interrupteur), QR juré (`identite.py` : codes à usage unique, expirants) |
| Vérifier au moment d'implémenter | endpoint, nom de modèle, authentification, sortie structurée et mode « thinking » d'Apertus dans la documentation officielle (Public AI / Hugging Face / vLLM swiss-ai) — **rien de cela n'est vérifié aujourd'hui** |
| Tests à ajouter | parité : même journal ⇒ même état ⇒ même empreinte de projection, avec fournisseur Maquette *valide* et sans IA ; canaris d'interdiction (consentement, validité, disponibilité, acceptation, score, identité) ; injections FR/DE/suisse allemand ; rejeu des AICall sans appel (espion) |
| Risques | sorties IA valides mais différentes qui changent l'état (mitigation : l'IA n'écrit jamais, l'humain confirme ; la parité porte sur le journal) ; limite de débit par IP derrière le NAT de la salle |
| Critère de sortie | job CI « parité » vert ; démo complète en AI OFF ; aucune mention « Powered by Apertus » sans appel réussi journalisé |
| Commits proposés | `feat(ia): extract/narrate/normalize roles behind one adapter` · `feat(ia): fact-id citation validator, one retry then template` · `test(ia): AI on/off parity in CI` · `feat(ui): visible AI switch` · `feat(acces): single-use expiring juror QR codes` |

### Phase 4 — Expérimental (feature flags ; ne commence pas avant A/B/C solides)

Chaînes/cycles, what-if, recettes, synthèse agrégée organisateur (k ≥ 5). Critère d'entrée : A/B/C 10× d'affilée,
réseau dégradé et AI OFF compris. Commit type : `feat(experimental): <x> behind flag, off by default`.

---

## 9. Risques (livrable 6)

**Techniques**
1. Découper `essai.py` casse des gardes subtiles (P1/P2, `apres_action`, `occupations`) — mitigation : déplacement mécanique, tests inchangés.
2. Performance d'une projection globale sur des replis O(n²) — mitigation : index des claims, cache par `seq`.
3. Migrer les profils dans le journal change l'empreinte des benchmarks publiés → CI de reproductibilité rouge (déjà arrivé runs 88–94) — mitigation : régénération dans le même commit, deux exécutions comparées.
4. Horloge : aujourd'hui non persistée ; `Demo.reinitialiser` **vide** le journal même durable (`banc.m.vider()`).
5. Mono-processus : verrou, limiteurs, sessions en mémoire.

**Produit**
6. « Capacité » lue comme une promesse du Club (B1 l'interdit) — libellés et paliers doivent rester plus faibles que la preuve.
7. Ask perçue comme une assignation ou un démarchage.
8. Six patrons écrits par l'équipe présentés comme « du Club » : à marquer FICTIF.

**Démo**
9. Flux QR juré : 10 accès/min/IP derrière un NAT = blocage ; codes réutilisables ; ancien prototype servi avec `X-Membre` et `/api/demo/reinitialiser` ouverts sur le même port.
10. Artefacts périmés (vidéo, captures, `competition/*`) montrés par erreur.
11. Le « wow » (scénario C) dépend de la projection suivante après retrait : si la recomposition n'existe pas dans les données, l'écran dit « NO SAFE MATCH » — il faut une donnée de secours préparée **et** assumée.

---

## 10. Ce qui ne vaut PAS la peine d'être construit (livrable 7)

- Tout ce que liste B11 (graphe animé, constellations, particules, agents négociateurs, scores, feed, capture passive, Neo4j/Graphiti, chatbot, patrons générés par IA, infrastructure distribuée).
- Un solveur (MILP/CP) pour la composition : la recherche bornée existante est exhaustive, explicable et testée contre un oracle ; `scipy` reste pour l'ancien prototype seulement.
- Une énumération de **toutes** les liaisons d'un patron : une meilleure liaison + ≤ 3 alternatives suffit (comme aujourd'hui).
- Un déplacement physique en paquets `domain/ activation/ …` : aucun comportement nouveau (déjà écarté dans `RECOMPOSITION.md` § 7.6).
- Plusieurs processus / PostgreSQL avant le hackathon.
- Un deuxième canal de narration pour la console : la console montre des états, pas de prose.
- Réécrire la détection d'opportunités : n'en garder que la règle de levier.
- Des notifications poussées : la relecture à 0,7 s tient la démo (mesurée).

---

## Annexe — commandes exécutées pendant l'inspection

```
cd prototype
HACKVS_SEMANTIQUE=0 python -m pytest -q --ignore=tests/test_e2e_scene.py --ignore=tests/test_e2e_pulse.py --ignore=tests/test_e2e_action.py
  → 523 passed in 145.79s
HACKVS_SEMANTIQUE=0 HACKVS_E2E_OBLIGATOIRE=1 python -m pytest -q tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py
  → 6 passed in 59.54s
ruff check .                                  → All checks passed!
python -m mypy app adaptateurs plateforme intelligence   → Success: no issues found in 73 source files
python scripts/verifier_secrets.py            → aucun secret trouvé
GitHub Actions, workflow CI                   → run 96 (9744027) success ; 95 success ; 92–94 failure
Sonde (script hors dépôt, sur la démo réelle) :
  parité état métier IA espion/aucune         → True (trivial : sortie rejetée → repli)
  deux rejeux de la démo, empreintes          → identiques (banc et réseau)
  cas 3 : compétence retirée du profil        → essai reste AUTORISE, couverture None   (TROU)
  cas 7 : disponible=False, non sollicitable  → essai reste AUTORISE                    (TROU)
  cas 12 : décision sur version périmée       → Conflit
  statut des APPEL_IA                         → {SIMULE}
```

Non exécuté : `scripts/reproduire_sprint.py` en local (le job CI de reproductibilité du run 96 fait foi) ; Apertus
(aucun identifiant) ; aucun test sur un vrai réseau de salle ni avec de vrais téléphones.
