# Architecture — Club Pulse

> **Pivot du 2026-09-29.** Le parcours visible est désormais le **banc d'essai partagé** : `intelligence/essai.py`
> (domaine), `intelligence/vues_essai.py` (vues par personne), `app/essai_api.py` (routes), mêmes couches et mêmes règles
> de dépendance que ci-dessous. Architecture courte et état exact : [audit/club-pulse-pivot/HANDOFF_FOR_CODEX.md](audit/club-pulse-pivot/HANDOFF_FOR_CODEX.md).
> Les sections sur la détection d'opportunités et l'activation décrivent du code conservé mais **retiré du parcours visible**.

> **Statut.** Prototype durci autour de préoccupations de production — **pas** un système en production. Monde de
> démonstration **fictif** (150 membres générés + personnages de scène). Un seul processus. Chaque affirmation de ce
> document renvoie à du code ou à un test ; la direction des dépendances est **vérifiée** par `tests/test_architecture.py`.
> Les chemins sont relatifs à `prototype/`. Le prototype précédent (« Le Fil du Club ») : [ARCHITECTURE_FIL_DU_CLUB.md](ARCHITECTURE_FIL_DU_CLUB.md).

## 1. Ce que fait le système, en une boucle

```
OBSERVER ──► DÉTECTER ──► ACTIVER ──► APPRENDRE
observateur   detection    activation   apprentissage
(état du      (opportunités (machine d'états : accords privés,   (motifs vérifiés : seulement
 réseau)       prouvées,     refus → replanification,            après un résultat CONFIRMÉ
               pièges        délais, résultat déclaré)           par le bénéficiaire)
               évités)
```
Le membre (PWA `/app`) et le Club (console `/console`) voient deux **projections** du même état, chacune filtrée par la
politique de confidentialité pour **ce** spectateur.

## 2. Couches et dépendances autorisées

```
 web/pulse/app.html, console.html            (navigateur : DOM construit par createTextNode, jamais innerHTML)
          │ HTTP JSON (même origine ; CSP par empreintes)
 ┌────────▼──────────────────────────────────────────────────────────────────────────────┐
 │ ADAPTATEURS  app/main.py · app/pulse_api.py · app/observabilite.py · app/protections.py │  seuls à connaître FastAPI
 └────────┬──────────────────────────────────────────────────────────────────────────────┘
          │ appels de méthodes ; erreurs métier typées (intelligence/erreurs.py)
 ┌────────▼──────────────────────────────────────────────────────────────────────────────┐
 │ SERVICE   intelligence/club_pulse.py (commandes, état du monde, verrou)                  │
 │           vues_essai.py · vues_intelligence.py (qui voit quoi) · demo.py (scène rejouable) │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ DOMAINE   essai (actions, créneaux, accords) · observateur · detection · modele · erreurs │
 │ PRIVÉ     identite (coffre, pseudonymes) · politique (portées, rendu) · acces (sessions) │
 │ IA        ia.py : Intelligence (unique point d'entrée) → Apertus | repli déterministe    │  seule frontière réseau
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ BIBLIOTHÈQUES HISTORIQUES (app/, sans HTTP) : models, taxonomy, parser_rules, matching,  │
 │ agenda, parser_llm (validation des sorties)   ·   adaptateurs/club/synthese.verifier     │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ PLATEFORME  plateforme/memoire.py (journal d'événements SQLite), affirmations (statuts)   │  n'importe rien du projet
 └───────────────────────────────────────────────────────────────────────────────────────┘
```

| Règle (vérifiée par `tests/test_architecture.py`) | Pourquoi |
|---|---|
| `plateforme/` n'importe rien de `app/`, `intelligence/`, `adaptateurs/` | le journal est une fondation, pas un client |
| `intelligence/` n'importe ni FastAPI/Starlette/uvicorn, ni un adaptateur HTTP | le domaine se teste et se rejoue sans serveur |
| dans `intelligence/`, seul `ia.py` importe `httpx` | une seule frontière réseau, un seul contrat d'erreur |
| seul `ia.py` construit `Apertus(...)` (`Intelligence.depuis_environnement`) | le reste du code ne teste jamais « est-ce Apertus ? » |
| `app/pulse_api.py` n'importe ni le moteur, ni la détection, ni le coffre | l'API valide, authentifie, appelle le service, traduit l'erreur — rien d'autre |
| les bibliothèques de domaine de `app/` n'importent pas FastAPI | réutilisables par `intelligence/` sans tirer HTTP |

**Dette assumée.** Les bibliothèques de domaine historiques vivent dans `app/` à côté des adaptateurs HTTP (héritage du
premier prototype). La règle ci-dessus empêche que cela devienne un couplage ; le déplacement vers un paquet `domaine/`
est un changement mécanique non fait pour ne pas casser le prototype précédent encore servi.

## 3. Cycle d'une requête

```
navigateur ─► MiddlewareRequete (identifiant X-Request-ID, une ligne JSON, 500 JSON sans message d'exception)
          ─► Protections (corps ≤ 64 Kio → sinon 413 ; en-têtes ; CSP sur /app et /console ; no-store sur l'API)
          ─► routeur pulse_api : schéma Pydantic borné (422) → authentification (X-Pulse-Session, 401) →
             limitation (429) → au_monde(f) :
                 capture le monde courant UNE fois, prend son verrou (RLock), exécute la commande ou la projection,
                 traduit ErreurMetier → 401/403/404/409/422/429 à UN endroit
          ─► ClubPulse.commande(...) ─► Moteur.@atomique (transaction SQLite : tout ou rien) ─► Memoire.ajouter(Evt)
          ─► Vues.projection(spectateur) ─► Rendu (politique : nom, organisation, contact, texte) ─► JSON
```

## 4. Modèle du domaine

| Entité | Où | Invariants (testés) | Cycle de vie |
|---|---|---|---|
| **Organisation → Adhésion → Personne** | `identite.py` | l'identité ne quitte jamais le coffre ; le moteur voit `MEMBRE-xxx` et un texte nettoyé | importée d'une source d'adhésion (synthétique, CSV ; API du Club : non connectée, lève `NonConnecte`) |
| **Profil pseudonymisé** | `app/models.Profil` via `Coffre.pseudonymiser` | aucun nom, courriel, téléphone, URL, mot de l'organisation dans les textes libres | recalculé à chaque modification (révision → nouvelle analyse) |
| **Opportunité** | `modele.Opportunite` | chaque signal cite un extrait MOT POUR MOT ; tout sollicité accepte les introductions, est disponible et doit consentir ; aucun doublon (mêmes personnes, mêmes capacités) | calculée (jamais stockée) : l'analyse est versionnée par (événements, besoins, révision des profils, jour) |
| **Activation** | `activation.Moteur` | I1–I7 ci-dessous, vérifiés après CHAQUE pas de 25 marches aléatoires | machine d'états, § 5 |
| **Note privée** | `ClubPulse.notes` | visible de son seul auteur ; traitée localement sauf `APERTUS_NOTES_PRIVEES=1` | capturée → propositions → partagées une à une par l'auteur |
| **Motif (mémoire vérifiée)** | `apprentissage` | n'existe qu'après un résultat CONFIRMÉ ou PARTIEL déclaré par le bénéficiaire ; anonymisé | vérifié → reconfirmé ; frais 365 jours |

### Invariants de l'activation (`tests/test_invariants.py`)
I1 toute transition du journal est permise par `TRANSITIONS` · I2 pas d'`ACTIVEE` sans TOUS les accords · I3 pas de
résultat sans déclaration du bénéficiaire ni contribution · I4 rien après un état final · I5 un refus n'est jamais
relancé · I6 au plus `BUDGET_ATTENTION` = 2 sollicitations ouvertes par personne · I7 un motif a une preuve confirmée.

## 5. Machine d'états de l'activation

```
DETECTEE → EVALUEE → PLANIFIEE → EN_ATTENTE_ACCORD → ACTIVEE → TERMINEE → RESULTAT_{CONFIRME | PARTIEL | NEGATIF | INCONNU}
                                     │  refus / silence 4 j                          (21 j sans déclaration → INCONNU,
                                     ▼                                                 jamais « réussi »)
                                  BLOQUEE → REPLANIFICATION → ALTERNATIVE_PROPOSEE → EN_ATTENTE_ACCORD
                                                     └──────→ ABANDONNEE (aucune alternative éligible : dit pourquoi)
  + REJETEE, EN_PAUSE (reprise vers l'état d'origine), ANNULEE (depuis tout état non final)
```
- Transition interdite, geste répété, réponse d'une personne non sollicitée → `Conflit` (409) / `Interdit` (403), jamais
  un état incohérent (tests : doublon, concurrence, nouvel essai, annulation, pause).
- Chaque commande est **atomique** (`@atomique` → `Memoire.transaction()`) : une erreur au milieu d'une commande
  n'écrit rien (régression corrigée : `lancer` pouvait laisser une activation en attente sans sollicitation).
- Les agents (Détecteur, Garde, Planificateur, Coordinateur, Vérificateur, Mémoire) sont des **services déterministes
  nommés** dans le journal ; aucun n'est un modèle de langage.

## 6. Journal d'événements (source de vérité du cycle de vie)

- `plateforme/memoire.py` : table SQLite `evenements(seq, id UNIQUE, donnees)` ; **ajout seul**.
- **Ordre** : `seq` (auto-incrément). **Idempotence** : `id` = empreinte du contenu ; un événement rejoué à l'identique
  est ignoré (test). Deux gestes identiques restent deux faits : le moteur ajoute un compteur `n` au contenu.
- **Rejeu** : l'état d'une activation est le repli de ses événements ; la démonstration se rejoue à l'identique
  (`test_meme_graine_meme_journal`, `Demo.rejouer`). La latence des appels IA est exclue du journal pour qu'il reste
  rejouable à l'octet.
- **Versionnage** : le plan d'une activation est versionné (`ACTIVATION_PLAN.version`) ; les événements n'ont pas de
  numéro de schéma (limite : une migration de format devrait l'ajouter — voir ADR 0005).
- **Types** (Club Pulse) : `ACTIVATION`, `ACTIVATION_PLAN`, `SOLLICITATION_PRIVEE`, `REPONSE`, `CONTRIBUTION_RECUE`,
  `COLLABORATION`, `RESULTAT_DECLARE`, `RETRAIT_CONSENTEMENT`, `MOTIF_VERIFIE`, `MOTIF_RECONFIRME`, `APPEL_IA`,
  `RENCONTRE`, `INTRO_DECLINEE`, `HORLOGE`.
- **Hors journal (dit franchement)** : notes privées, préférences de visibilité, coffre d'identités, sessions — en
  mémoire du processus de démonstration, perdus au redémarrage. En production : magasins séparés et chiffrés (ADR 0002).

## 7. Identité, confidentialité, classification

Le moteur ne voit **jamais** une identité : `Coffre.pseudonymiser` remplace nom et organisation par `MEMBRE-xxx` et une
clé d'organisation, et `nettoyer()` retire des textes libres courriels, téléphones, URL, noms et mots de l'organisation.
Chaque écran est rendu **pour un spectateur** (`politique.Rendu`) : nom, organisation, contact et texte ne sont révélés
que si la portée le permet (`PRIVE`, `CLUB_DECOUVRABLE`, `RELATIONS`, `SUR_CONSENTEMENT`, `ACTIVATION`, `PUBLIC`) ;
consentement **orienté** (qui voit qui) ; agrégats **k-anonymes** (k = 3).

| Classe | Exemples | UI du membre | API | Vers l'IA | Journaux | Analytique |
|---|---|---|---|---|---|---|
| PUBLIC | libellés de capacités, événements du Club | oui | oui | oui | non (inutile) | oui |
| CLUB | capacités déclarées « découvrables », motifs anonymisés | membres | membres | pseudonymisé | non | agrégé (k ≥ 3) |
| PRIVÉ | notes de rencontre, recherches non publiées | auteur seul | auteur seul | **local par défaut** (`APERTUS_NOTES_PRIVEES=1` pour l'envoyer) | **jamais** | jamais |
| SENSIBLE | refus, silence, raison d'un refus | jamais (ni au demandeur, ni au Club) | jamais | jamais | jamais | compte agrégé seulement |
| IDENTITÉ | nom, courriel, organisation | selon la portée et l'accord | selon la portée | **jamais** (pseudonymes) | **jamais** | jamais |
| AUDIT | transitions, agents, appels IA (métadonnées) | console : sans « qui a décliné » | console | non | identifiants techniques seulement | oui |

Vérifié par : `test_identite_confidentialite_ia.py`, `test_securite_pulse.py`, `test_observabilite.py` (démonstration
complète au niveau DEBUG : aucun jeton, code, nom, note ni courriel dans les journaux), `eval/benchmark_pulse.py`
(0 fuite sur 754 écrans, 0 identité sur 1 950 contrôles du moteur).

## 8. Frontière IA

`Intelligence` est l'**unique** point d'entrée des 4 tâches de langage (comprendre une demande, capturer une rencontre,
expliquer une opportunité, rédiger une sollicitation). Le fournisseur est choisi **une fois** (`depuis_environnement`) :
Apertus si `APERTUS_BASE_URL`, `APERTUS_API_KEY`, `APERTUS_MODEL` sont définis, sinon repli déterministe **déclaré**.

| Panne | Comportement | Test |
|---|---|---|
| délai, 429, 5xx, réseau | ≤ 3 tentatives, recul exponentiel + gigue (≤ 4 s), puis repli visible | `test_frontiere_ia.py` |
| 4xx | pas de nouvel essai | idem |
| 3 pannes de suite | disjoncteur : 60 s sans appel, repli déclaré, puis nouvel essai | idem |
| JSON invalide, tronqué, hors schéma, vide | sortie REJETÉE → repli | idem |
| entité inventée, nombre inventé | sortie REJETÉE (vérification de fidélité aux faits) | idem |
| courriel, téléphone, URL dans la sortie | sortie REJETÉE (le modèle n'en reçoit aucun) | idem |
| bogue de NOTRE code | **non masqué** : seule `ErreurFournisseur` est rattrapée | idem |
| injection dans un profil | reste du contenu ; aucune donnée à fuiter ; sortie filtrée | idem |

Prompts versionnés : `prompts/*_v1.md` (la version est tracée dans chaque `AppelIA`). Chaque appel est journalisé par ses
**métadonnées** (tâche, fournisseur, modèle, version du prompt, statut, repli, durée) — jamais l'entrée ni la sortie.
**Apertus n'a pas été appelé dans cet environnement** (aucun identifiant) : `eval/resultats_apertus.md` le dit.

## 9. Concurrence

- **Un monde = un `RLock`** : chaque requête s'exécute entière sous le verrou du monde qu'elle a capturé (`au_monde`) ;
  une réinitialisation concurrente ne mélange pas deux mondes. Tests : deux acceptations simultanées → 200 + 409 ;
  acceptation contre annulation → état final cohérent.
- **Transactions** : `Memoire.transaction()` (réentrante, validation par la plus externe, annulation + cache vidé sur erreur).
- **Limite** : un seul processus. Plusieurs instances exigeraient un magasin partagé (PostgreSQL : verrou par activation,
  contrainte d'unicité sur `(activation, étape, membre)` pour les réponses) et un limiteur partagé.

## 10. Configuration (centralisée, erreurs explicites)

| Variable | Effet | Défaut |
|---|---|---|
| `HACKVS_SECRET` | signe sessions et codes d'invitation (≥ 32 caractères, sinon erreur au démarrage) | aléatoire par processus |
| `HACKVS_CONSOLE_JETON` | jeton exact exigé par la console | absent : en-tête `X-Pulse-Console` seulement (démo locale) |
| `APERTUS_BASE_URL`, `APERTUS_API_KEY`, `APERTUS_MODEL` | active Apertus | absent : repli déterministe |
| `APERTUS_DELAI_S` | délai d'un appel à Apertus (secondes) | 30 |
| `APERTUS_NOTES_PRIVEES=1` | autorise l'envoi des notes privées à Apertus | non |
| `HACKVS_JOURNAL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` (autre valeur : erreur au démarrage) | `INFO` |
| `HACKVS_MODE` | `demo` seulement pour Club Pulse | `demo` |

Lecture : `intelligence/reglages.py` (secrets, IA) et `app/observabilite.niveau_depuis_env`. Aucune valeur secrète par défaut.

## 11. Observabilité

Une ligne JSON par requête et par fait (transition, appel IA), portant l'identifiant de requête (`X-Request-ID`,
renvoyé au client et cité dans les messages d'erreur 5xx). Liste **fermée** de champs ; jamais de corps, d'en-tête, de
message d'exception, de texte libre. `app/observabilite.py`, testé par `tests/test_observabilite.py`.

## 12. Passage à l'échelle — réponses honnêtes

| Question | Réponse mesurée ou raisonnée |
|---|---|
| 160 membres (le Club visé) ? | analyse complète ≈ 5 ms (`eval/performance_pulse.md`) : recalculée à chaque changement |
| 1 000 / 5 000 membres ? | ≈ 150 ms / ≈ 4,5 s : croissance plus que linéaire (intérêts latents × offreurs d'une capacité) ; au-delà : analyse incrémentale par membre modifié |
| plusieurs instances ? | non supporté : état en mémoire + SQLite local ; voir § 9 |
| journal qui grossit ? | cache désérialisé par incrément ; projections recalculées par repli : instantanés à ajouter au-delà de ~10⁵ événements (non mesuré) |
| coût d'Apertus ? | au plus un appel par geste ; relire une page ne rappelle pas le modèle (test) ; non mesuré sans identifiants |
